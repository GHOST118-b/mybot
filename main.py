import asyncio
import logging
import random
from datetime import datetime

import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.exceptions import TelegramBadRequest


# ============================================================
# НАСТРОЙКИ
# ============================================================

BOT_TOKEN = "8834330502:AAFp8TzJ6VxpnPYJB_Ghlu14exrTwdA8lkA"

# ============================================================
# ВАЖНО:
# Здесь укажи свой Telegram ID.
# Например:
# ADMIN_ID = 123456789
# ============================================================

ADMIN_ID = 123456789

DB_NAME = "state_simulator.db"

logging.basicConfig(level=logging.INFO)

bot = Bot(BOT_TOKEN)
dp = Dispatcher()


# ============================================================
# БАЗА ДАННЫХ
# ============================================================

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute("""
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            state_name TEXT,
            ruler_name TEXT,

            money INTEGER DEFAULT 10000,
            population INTEGER DEFAULT 1000,
            army INTEGER DEFAULT 100,

            level INTEGER DEFAULT 1,
            buildings INTEGER DEFAULT 0,

            tax INTEGER DEFAULT 10,
            jobs INTEGER DEFAULT 100,

            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,

            banned INTEGER DEFAULT 0,
            muted INTEGER DEFAULT 0,

            created_at TEXT
        )
        """)

        await db.commit()


async def get_player(user_id: int):
    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute(
            "SELECT * FROM players WHERE user_id = ?",
            (user_id,)
        )

        return await cursor.fetchone()


async def create_player(
    user_id: int,
    username: str,
    state_name: str,
    ruler_name: str
):
    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute("""
        INSERT INTO players (
            user_id,
            username,
            state_name,
            ruler_name,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """, (
            user_id,
            username,
            state_name,
            ruler_name,
            datetime.now().isoformat()
        ))

        await db.commit()


async def update_player(user_id: int, field: str, value):
    allowed = {
        "money",
        "population",
        "army",
        "level",
        "buildings",
        "tax",
        "jobs",
        "wins",
        "losses",
        "banned",
        "muted",
        "state_name",
        "ruler_name",
    }

    if field not in allowed:
        return

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute(
            f"UPDATE players SET {field} = ? WHERE user_id = ?",
            (value, user_id)
        )

        await db.commit()


# ============================================================
# ПРОВЕРКИ
# ============================================================

async def is_banned(user_id: int):
    player = await get_player(user_id)

    if not player:
        return False

    return player["banned"] == 1


async def is_muted(user_id: int):
    player = await get_player(user_id)

    if not player:
        return False

    return player["muted"] == 1


async def require_player(message: Message):

    player = await get_player(message.from_user.id)

    if not player:
        await message.answer(
            "❌ Сначала создай государство:\n"
            "/start"
        )
        return None

    if player["banned"]:
        await message.answer("🚫 Вы заблокированы.")
        return None

    if player["muted"]:
        await message.answer("🔇 Вы получили мут.")
        return None

    return player


# ============================================================
# КЛАВИАТУРЫ
# ============================================================

def main_keyboard():

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📊 Государство",
                    callback_data="stats"
                ),
                InlineKeyboardButton(
                    text="💰 Экономика",
                    callback_data="economy"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🪖 Армия",
                    callback_data="army"
                ),
                InlineKeyboardButton(
                    text="🏗️ Строительство",
                    callback_data="build"
                )
            ],
            [
                InlineKeyboardButton(
                    text="👥 Население",
                    callback_data="population"
                ),
                InlineKeyboardButton(
                    text="⚔️ Война",
                    callback_data="war"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💵 Собрать налоги",
                    callback_data="tax"
                ),
            ]
        ]
    )


# ============================================================
# START
# ============================================================

@dp.message(Command("start"))
async def start(message: Message):

    user_id = message.from_user.id

    if await is_banned(user_id):
        await message.answer("🚫 Вы заблокированы.")
        return

    player = await get_player(user_id)

    if player:

        await message.answer(
            f"👑 Добро пожаловать обратно, правитель!\n\n"
            f"🏳️ Государство: {player['state_name']}\n"
            f"👤 Правитель: {player['ruler_name']}\n\n"
            f"Выберите действие:",
            reply_markup=main_keyboard()
        )

        return

    await message.answer(
        "🏛️ **СИМУЛЯТОР ГОСУДАРСТВА**\n\n"
        "Ты начинаешь с небольшого государства.\n"
        "Развивай экономику, нанимай армию,\n"
        "строи здания и воюй с другими государствами.\n\n"
        "Для создания государства напиши:\n\n"
        "/create НазваниеГосударства | ИмяПравителя\n\n"
        "Пример:\n"
        "/create Россия | Александр",
        parse_mode="Markdown"
    )


# ============================================================
# СОЗДАНИЕ ГОСУДАРСТВА
# ============================================================

@dp.message(Command("create"))
async def create_state(message: Message):

    if await is_banned(message.from_user.id):
        return

    player = await get_player(message.from_user.id)

    if player:
        await message.answer("❌ У тебя уже есть государство.")
        return

    text = message.text.replace("/create", "", 1).strip()

    if "|" not in text:

        await message.answer(
            "❌ Используй:\n"
            "/create Название | Имя правителя"
        )

        return

    state_name, ruler_name = text.split("|", 1)

    state_name = state_name.strip()
    ruler_name = ruler_name.strip()

    if len(state_name) < 2 or len(ruler_name) < 2:

        await message.answer(
            "❌ Название государства и имя правителя "
            "должны содержать минимум 2 символа."
        )

        return

    await create_player(
        message.from_user.id,
        message.from_user.username or "unknown",
        state_name,
        ruler_name
    )

    await message.answer(
        f"🎉 Государство создано!\n\n"
        f"🏳️ {state_name}\n"
        f"👑 Правитель: {ruler_name}\n\n"
        f"💰 Казна: 10 000\n"
        f"👥 Население: 1 000\n"
        f"🪖 Армия: 100\n\n"
        f"Начинай развитие!",
        reply_markup=main_keyboard()
    )


# ============================================================
# СТАТИСТИКА
# ============================================================

async def stats_text(player):

    return (
        f"🏛️ **{player['state_name']}**\n\n"
        f"👑 Правитель: {player['ruler_name']}\n\n"
        f"💰 Казна: {player['money']:,}\n"
        f"👥 Население: {player['population']:,}\n"
        f"🪖 Армия: {player['army']:,}\n"
        f"🏗️ Здания: {player['buildings']}\n"
        f"📈 Уровень: {player['level']}\n"
        f"💵 Налог: {player['tax']}%\n"
        f"💼 Рабочие места: {player['jobs']:,}\n\n"
        f"🏆 Победы: {player['wins']}\n"
        f"💀 Поражения: {player['losses']}"
    )


@dp.message(Command("stats"))
async def stats(message: Message):

    player = await require_player(message)

    if not player:
        return

    await message.answer(
        await stats_text(player),
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )


# ============================================================
# ЭКОНОМИКА
# ============================================================

@dp.message(Command("economy"))
async def economy(message: Message):

    player = await require_player(message)

    if not player:
        return

    income = (
        player["population"]
        * player["tax"]
        // 100
    )

    expenses = player["army"] * 2

    profit = income - expenses

    await message.answer(
        f"💰 **Экономика государства**\n\n"
        f"📈 Доход от налогов: +{income:,}\n"
        f"🪖 Содержание армии: -{expenses:,}\n"
        f"💵 Прибыль за цикл: {profit:,}\n\n"
        f"💰 Казна: {player['money']:,}",
        parse_mode="Markdown"
    )


@dp.message(Command("tax"))
async def collect_tax(message: Message):

    player = await require_player(message)

    if not player:
        return

    income = (
        player["population"]
        * player["tax"]
        // 100
    )

    new_money = player["money"] + income

    await update_player(
        message.from_user.id,
        "money",
        new_money
    )

    await message.answer(
        f"💵 Налоги собраны!\n\n"
        f"Государство получило: +{income:,}\n"
        f"💰 Теперь в казне: {new_money:,}"
    )


# ============================================================
# ИЗМЕНЕНИЕ НАЛОГОВ
# ============================================================

@dp.message(Command("settax"))
async def set_tax(message: Message):

    player = await require_player(message)

    if not player:
        return

    args = message.text.split()

    if len(args) != 2:

        await message.answer(
            "Использование:\n"
            "/settax 15"
        )

        return

    try:
        tax = int(args[1])
    except ValueError:
        await message.answer("❌ Укажи число.")
        return

    if tax < 0 or tax > 50:

        await message.answer(
            "❌ Налог может быть от 0 до 50%."
        )

        return

    await update_player(
        message.from_user.id,
        "tax",
        tax
    )

    await message.answer(
        f"💵 Налог установлен: {tax}%"
    )


# ============================================================
# АРМИЯ
# ============================================================

@dp.message(Command("army"))
async def army(message: Message):

    player = await require_player(message)

    if not player:
        return

    await message.answer(
        f"🪖 **Армия {player['state_name']}**\n\n"
        f"Солдаты: {player['army']:,}\n\n"
        f"Найм:\n"
        f"/recruit 100\n\n"
        f"Стоимость одного солдата: 50 монет.",
        parse_mode="Markdown"
    )


@dp.message(Command("recruit"))
async def recruit(message: Message):

    player = await require_player(message)

    if not player:
        return

    args = message.text.split()

    if len(args) != 2:

        await message.answer(
            "Использование:\n"
            "/recruit 100"
        )

        return

    try:
        amount = int(args[1])
    except ValueError:

        await message.answer("❌ Укажи количество.")
        return

    if amount <= 0:
        await message.answer("❌ Количество должно быть больше 0.")
        return

    price = amount * 50

    if player["money"] < price:

        await message.answer(
            f"❌ Недостаточно денег.\n"
            f"Нужно: {price:,}"
        )

        return

    if player["population"] - amount < 100:

        await message.answer(
            "❌ Нельзя забрать столько людей в армию."
        )

        return

    await update_player(
        message.from_user.id,
        "money",
        player["money"] - price
    )

    await update_player(
        message.from_user.id,
        "army",
        player["army"] + amount
    )

    await update_player(
        message.from_user.id,
        "population",
        player["population"] - amount
    )

    await message.answer(
        f"🪖 Нанято солдат: {amount:,}\n"
        f"💰 Потрачено: {price:,}"
    )


# ============================================================
# СТРОИТЕЛЬСТВО
# ============================================================

@dp.message(Command("build"))
async def build(message: Message):

    player = await require_player(message)

    if not player:
        return

    price = 5000

    if player["money"] < price:

        await message.answer(
            f"❌ Для строительства нужно {price:,} монет."
        )

        return

    await update_player(
        message.from_user.id,
        "money",
        player["money"] - price
    )

    await update_player(
        message.from_user.id,
        "buildings",
        player["buildings"] + 1
    )

    await update_player(
        message.from_user.id,
        "jobs",
        player["jobs"] + 100
    )

    await update_player(
        message.from_user.id,
        "level",
        player["level"] + 1
    )

    await message.answer(
        "🏗️ Новое здание построено!\n\n"
        "📈 Уровень государства увеличен.\n"
        "💼 Создано 100 рабочих мест."
    )


# ============================================================
# НАСЕЛЕНИЕ
# ============================================================

@dp.message(Command("population"))
async def population(message: Message):

    player = await require_player(message)

    if not player:
        return

    growth = max(
        10,
        player["population"] // 100
    )

    new_population = player["population"] + growth

    await update_player(
        message.from_user.id,
        "population",
        new_population
    )

    await message.answer(
        f"👥 Население выросло!\n\n"
        f"+{growth:,} человек\n"
        f"Теперь: {new_population:,}"
    )


# ============================================================
# ВОЙНА
# ============================================================

@dp.message(Command("war"))
async def war(message: Message):

    player = await require_player(message)

    if not player:
        return

    async with aiosqlite.connect(DB_NAME) as db:
        db.row_factory = aiosqlite.Row

        cursor = await db.execute("""
        SELECT *
        FROM players
        WHERE user_id != ?
        AND banned = 0
        ORDER BY RANDOM()
        LIMIT 1
        """, (message.from_user.id,))

        enemy = await cursor.fetchone()

    if not enemy:

        await message.answer(
            "⚔️ Пока нет других государств для войны."
        )

        return

    if player["army"] < 50:

        await message.answer(
            "❌ Для войны нужно минимум 50 солдат."
        )

        return

    # Случайный боевой коэффициент
    player_power = player["army"] * random.uniform(0.7, 1.3)
    enemy_power = enemy["army"] * random.uniform(0.7, 1.3)

    if player_power >= enemy_power:

        reward = random.randint(2000, 7000)

        await update_player(
            message.from_user.id,
            "money",
            player["money"] + reward
        )

        await update_player(
            message.from_user.id,
            "wins",
            player["wins"] + 1
        )

        losses = max(
            10,
            player["army"] // 10
        )

        await update_player(
            message.from_user.id,
            "army",
            max(0, player["army"] - losses)
        )

        await update_player(
            enemy["user_id"],
            "losses",
            enemy["losses"] + 1
        )

        enemy_losses = max(
            10,
            enemy["army"] // 10
        )

        await update_player(
            enemy["user_id"],
            "army",
            max(0, enemy["army"] - enemy_losses)
        )

        await message.answer(
            f"🏆 **ПОБЕДА!**\n\n"
            f"⚔️ Противник: {enemy['state_name']}\n"
            f"💰 Добыча: +{reward:,}\n"
            f"🪖 Потери: {losses}",
            parse_mode="Markdown"
        )

    else:

        losses = max(
            20,
            player["army"] // 5
        )

        await update_player(
            message.from_user.id,
            "army",
            max(0, player["army"] - losses)
        )

        await update_player(
            message.from_user.id,
            "losses",
            player["losses"] + 1
        )

        await update_player(
            enemy["user_id"],
            "wins",
            enemy["wins"] + 1
        )

        await message.answer(
            f"💀 **ПОРАЖЕНИЕ!**\n\n"
            f"⚔️ Противник: {enemy['state_name']}\n"
            f"🪖 Потери: {losses}",
            parse_mode="Markdown"
        )


# ============================================================
# АДМИН: ПРОВЕРКА
# ============================================================

def admin_only(message: Message):

    return message.from_user.id == ADMIN_ID


# ============================================================
# ADMIN BAN
# ============================================================

@dp.message(Command("ban"))
async def admin_ban(message: Message):

    if not admin_only(message):

        await message.answer("❌ Нет доступа.")
        return

    args = message.text.split()

    if len(args) != 2:

        await message.answer(
            "Использование:\n"
            "/ban USER_ID"
        )

        return

    try:
        user_id = int(args[1])
    except ValueError:

        await message.answer("❌ ID должен быть числом.")
        return

    await update_player(
        user_id,
        "banned",
        1
    )

    await message.answer(
        f"🚫 Пользователь {user_id} заблокирован."
    )


# ============================================================
# ADMIN UNBAN
# ============================================================

@dp.message(Command("unban"))
async def admin_unban(message: Message):

    if not admin_only(message):
        return

    args = message.text.split()

    if len(args) != 2:
        await message.answer("/unban USER_ID")
        return

    user_id = int(args[1])

    await update_player(
        user_id,
        "banned",
        0
    )

    await message.answer(
        f"✅ Пользователь {user_id} разблокирован."
    )


# ============================================================
# ADMIN MUTE
# ============================================================

@dp.message(Command("mute"))
async def admin_mute(message: Message):

    if not admin_only(message):
        return

    args = message.text.split()

    if len(args) != 2:
        await message.answer("/mute USER_ID")
        return

    user_id = int(args[1])

    await update_player(
        user_id,
        "muted",
        1
    )

    await message.answer(
        f"🔇 Пользователь {user_id} получил мут."
    )


# ============================================================
# ADMIN UNMUTE
# ============================================================

@dp.message(Command("unmute"))
async def admin_unmute(message: Message):

    if not admin_only(message):
        return

    args = message.text.split()

    if len(args) != 2:
        await message.answer("/unmute USER_ID")
        return

    user_id = int(args[1])

    await update_player(
        user_id,
        "muted",
        0
    )

    await message.answer(
        f"🔊 Мут с пользователя {user_id} снят."
    )


# ============================================================
# ADMIN GIVE MONEY
# ============================================================

@dp.message(Command("givemoney"))
async def give_money(message: Message):

    if not admin_only(message):
        return

    args = message.text.split()

    if len(args) != 3:
        await message.answer(
            "/givemoney USER_ID AMOUNT"
        )
        return

    user_id = int(args[1])
    amount = int(args[2])

    player = await get_player(user_id)

    if not player:
        await message.answer("❌ Игрок не найден.")
        return

    await update_player(
        user_id,
        "money",
        player["money"] + amount
    )

    await message.answer(
        f"💰 Выдано {amount:,} монет игроку {user_id}."
    )


# ============================================================
# ADMIN GIVE ARMY
# ============================================================

@dp.message(Command("givearmy"))
async def give_army(message: Message):

    if not admin_only(message):
        return

    args = message.text.split()

    if len(args) != 3:
        await message.answer(
            "/givearmy USER_ID AMOUNT"
        )
        return

    user_id = int(args[1])
    amount = int(args[2])

    player = await get_player(user_id)

    if not player:
        await message.answer("❌ Игрок не найден.")
        return

    await update_player(
        user_id,
        "army",
        player["army"] + amount
    )

    await message.answer(
        f"🪖 Выдано солдат: {amount:,}"
    )


# ============================================================
# ADMIN GIVE POPULATION
# ============================================================

@dp.message(Command("givepopulation"))
async def give_population(message: Message):

    if not admin_only(message):
        return

    args = message.text.split()

    if len(args) != 3:
        await message.answer(
            "/givepopulation USER_ID AMOUNT"
        )
        return

    user_id = int(args[1])
    amount = int(args[2])

    player = await get_player(user_id)

    if not player:
        await message.answer("❌ Игрок не найден.")
        return

    await update_player(
        user_id,
        "population",
        player["population"] + amount
    )

    await message.answer(
        f"👥 Население увеличено на {amount:,}."
    )


# ============================================================
# ADMIN SET LEVEL
# ============================================================

@dp.message(Command("setlevel"))
async def set_level(message: Message):

    if not admin_only(message):
        return

    args = message.text.split()

    if len(args) != 3:
        await message.answer(
            "/setlevel USER_ID LEVEL"
        )
        return

    user_id = int(args[1])
    level = int(args[2])

    await update_player(
        user_id,
        "level",
        level
    )

    await message.answer(
        f"📈 Уровень игрока изменён на {level}."
    )


# ============================================================
# ADMIN GIVE BUILDINGS
# ============================================================

@dp.message(Command("givebuildings"))
async def give_buildings(message: Message):

    if not admin_only(message):
        return

    args = message.text.split()

    if len(args) != 3:
        await message.answer(
            "/givebuildings USER_ID AMOUNT"
        )
        return

    user_id = int(args[1])
    amount = int(args[2])

    player = await get_player(user_id)

    if not player:
        await message.answer("❌ Игрок не найден.")
        return

    await update_player(
        user_id,
        "buildings",
        player["buildings"] + amount
    )

    await message.answer(
        f"🏗️ Выдано зданий: {amount}"
    )


# ============================================================
# ADMIN INFO
# ============================================================

@dp.message(Command("player"))
async def admin_player(message: Message):

    if not admin_only(message):
        return

    args = message.text.split()

    if len(args) != 2:
        await message.answer(
            "/player USER_ID"
        )
        return

    user_id = int(args[1])

    player = await get_player(user_id)

    if not player:

        await message.answer(
            "❌ Игрок не найден."
        )

        return

    await message.answer(
        await stats_text(player),
        parse_mode="Markdown"
    )


# ============================================================
# ADMIN PLAYERS
# ============================================================

@dp.message(Command("players"))
async def admin_players(message: Message):

    if not admin_only(message):
        return

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute(
            "SELECT user_id, username, state_name FROM players"
        )

        players = await cursor.fetchall()

    if not players:

        await message.answer(
            "📭 Игроков пока нет."
        )

        return

    text = "👥 **Игроки:**\n\n"

    for user_id, username, state_name in players:

        text += (
            f"🆔 `{user_id}`\n"
            f"👤 @{username}\n"
            f"🏳️ {state_name}\n\n"
        )

    await message.answer(
        text,
        parse_mode="Markdown"
    )


# ============================================================
# ADMIN DELETE STATE
# ============================================================

@dp.message(Command("deleteplayer"))
async def delete_player(message: Message):

    if not admin_only(message):
        return

    args = message.text.split()

    if len(args) != 2:

        await message.answer(
            "/deleteplayer USER_ID"
        )

        return

    user_id = int(args[1])

    async with aiosqlite.connect(DB_NAME) as db:

        await db.execute(
            "DELETE FROM players WHERE user_id = ?",
            (user_id,)
        )

        await db.commit()

    await message.answer(
        f"🗑️ Государство игрока {user_id} удалено."
    )


# ============================================================
# ADMIN BROADCAST
# ============================================================

@dp.message(Command("broadcast"))
async def broadcast(message: Message):

    if not admin_only(message):
        return

    text = message.text.replace(
        "/broadcast",
        "",
        1
    ).strip()

    if not text:

        await message.answer(
            "Использование:\n"
            "/broadcast Текст сообщения"
        )

        return

    async with aiosqlite.connect(DB_NAME) as db:

        cursor = await db.execute(
            "SELECT user_id FROM players"
        )

        users = await cursor.fetchall()

    success = 0
    failed = 0

    for (user_id,) in users:

        try:

            await bot.send_message(
                user_id,
                f"📢 **Сообщение администрации**\n\n{text}",
                parse_mode="Markdown"
            )

            success += 1

        except Exception:

            failed += 1

        await asyncio.sleep(0.05)

    await message.answer(
        f"📢 Рассылка завершена.\n\n"
        f"✅ Отправлено: {success}\n"
        f"❌ Ошибок: {failed}"
    )


# ============================================================
# ADMIN PANEL
# ============================================================

@dp.message(Command("admin"))
async def admin_panel(message: Message):

    if not admin_only(message):

        await message.answer(
            "❌ У тебя нет прав администратора."
        )

        return

    await message.answer(
        "👑 **ПАНЕЛЬ АДМИНИСТРАТОРА**\n\n"

        "🚫 /ban USER_ID\n"
        "✅ /unban USER_ID\n"
        "🔇 /mute USER_ID\n"
        "🔊 /unmute USER_ID\n\n"

        "💰 /givemoney USER_ID AMOUNT\n"
        "🪖 /givearmy USER_ID AMOUNT\n"
        "👥 /givepopulation USER_ID AMOUNT\n"
        "🏗️ /givebuildings USER_ID AMOUNT\n"
        "📈 /setlevel USER_ID LEVEL\n\n"

        "👤 /player USER_ID\n"
        "👥 /players\n"
        "🗑️ /deleteplayer USER_ID\n"
        "📢 /broadcast TEXT",
        parse_mode="Markdown"
    )


# ============================================================
# CALLBACKS
# ============================================================

@dp.callback_query(F.data == "stats")
async def callback_stats(callback: CallbackQuery):

    player = await get_player(callback.from_user.id)

    if not player:
        await callback.answer(
            "Сначала создай государство.",
            show_alert=True
        )
        return

    await callback.message.edit_text(
        await stats_text(player),
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )

    await callback.answer()


@dp.callback_query(F.data == "economy")
async def callback_economy(callback: CallbackQuery):

    player = await get_player(callback.from_user.id)

    if not player:
        await callback.answer(
            "Создай государство.",
            show_alert=True
        )
        return

    income = (
        player["population"]
        * player["tax"]
        // 100
    )

    expenses = player["army"] * 2

    await callback.message.edit_text(
        f"💰 **Экономика**\n\n"
        f"📈 Доход: +{income:,}\n"
        f"🪖 Армия: -{expenses:,}\n"
        f"💵 Баланс: {income - expenses:,}",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )

    await callback.answer()


@dp.callback_query(F.data == "army")
async def callback_army(callback: CallbackQuery):

    player = await get_player(callback.from_user.id)

    if not player:
        await callback.answer(
            "Создай государство.",
            show_alert=True
        )
        return

    await callback.message.edit_text(
        f"🪖 **Армия**\n\n"
        f"Солдаты: {player['army']:,}\n\n"
        f"Чтобы нанять войско:\n"
        f"/recruit 100",
        parse_mode="Markdown",
        reply_markup=main_keyboard()
    )

    await callback.answer()


@dp.callback_query(F.data == "build")
async def callback_build(callback: CallbackQuery):

    await callback.message.answer(
        "🏗️ Строительство стоит 5 000 монет.\n\n"
        "Команда:\n"
        "/build"
    )

    await callback.answer()


@dp.callback_query(F.data == "population")
async def callback_population(callback: CallbackQuery):

    await callback.message.answer(
        "👥 Население развивается автоматически.\n\n"
        "Также можно использовать:\n"
        "/population"
    )

    await callback.answer()


@dp.callback_query(F.data == "war")
async def callback_war(callback: CallbackQuery):

    await callback.message.answer(
        "⚔️ Чтобы начать войну, используй:\n"
        "/war"
    )

    await callback.answer()


@dp.callback_query(F.data == "tax")
async def callback_tax(callback: CallbackQuery):

    player = await get_player(callback.from_user.id)

    if not player:
        await callback.answer(
            "Создай государство.",
            show_alert=True
        )
        return

    income = (
        player["population"]
        * player["tax"]
        // 100
    )

    await update_player(
        callback.from_user.id,
        "money",
        player["money"] + income
    )

    await callback.answer(
        f"+{income:,} монет",
        show_alert=True
    )


# ============================================================
# НЕИЗВЕСТНЫЕ КОМАНДЫ / ПРОВЕРКА МУТА
# ============================================================

@dp.message()
async def all_messages(message: Message):

    if await is_banned(message.from_user.id):

        await message.answer(
            "🚫 Вы заблокированы."
        )

        return

    if await is_muted(message.from_user.id):

        await message.answer(
            "🔇 Вы находитесь в муте."
        )

        return

    # Если это обычный текст
    if message.text:

        await message.answer(
            "🤖 Я не понял команду.\n\n"
            "Используй /start"
        )


# ============================================================
# ЗАПУСК
# ============================================================

async def main():

    await init_db()

    print("================================")
    print("🏛️ STATE SIMULATOR BOT")
    print("🤖 Бот запущен")
    print("================================")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
