Ниже — готовый «фикс-пакет»: исправленный код (с дописанными кусками, обработкой ошибок и безопасностью) + список того, что ещё стоит добавить.

---

## Что обязательно сделать прямо сейчас (безопасность)

1. **Срочно перевыпустите токен бота в @BotFather.** Токен из кода уже считается скомпрометированным.
2. **Не храните токен и ADMIN_ID в коде.** Используйте переменные окружения (`.env` + `os.getenv`).
3. **Не выкладывайте этот код в публичный репозиторий.** В `.gitignore` добавьте:
   ```text
   .env
   *.pyc
   __pycache__/
   ```

---

## Исправленный и безопасный код (минимальный рабочий вариант)

```python
import os
import random
import time
import logging
from typing import Optional, Dict, Any

import telebot
from telebot import types

# --- Конфигурация из переменных окружения ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()}

if not TOKEN:
    raise ValueError("Не задан TELEGRAM_BOT_TOKEN в переменных окружения")

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(TOKEN)

# --- Игровые данные (в памяти, для прототипа) ---
players: Dict[int, Dict[str, Any]] = {}
alliances: Dict[str, Dict[str, Any]] = {}
market_lots: Dict[int, Any] = {}

COUNTRIES = {
    "1": {"name": "Римская Империя", "bonus": "⚔️ +15% атака в PvP"},
    "2": {"name": "Османский Султанат", "bonus": "💰 +20% налоги с крестьян"},
    "3": {"name": "Сёгунат Токугава", "bonus": "🏭 Шахты дешевле на 20%"},
}

def init_player(uid: int, username: Optional[str], country_id: str) -> None:
    c_name = COUNTRIES[country_id]["name"]
    players[uid] = {
        "username": username or f"id_{uid}",
        "country": c_name,
        "gold": 300,
        "mines": 1,
        "mine_lvl": 1,
        "army": 5,
        "land": 10,
        "shield_until": 0,
        "alliance": None,
    }

def get_random_enemy(exclude_uid: int) -> Optional[int]:
    now = time.time()
    all_enemies = [
        k for k, v in players.items()
        if k != exclude_uid and v.get("shield_until", 0) < now
    ]
    return random.choice(all_enemies) if all_enemies else None

def calculate_income(uid: int) -> None:
    p = players[uid]
    mult = 1.2 if p["country"] == "Османский Султанат" else 1.0
    ally = p.get("alliance")
    if ally and ally in alliances:
        mult += alliances[ally]["level"] * 0.05
    p["gold"] += int(p["mines"] * 5 * p.get("mine_lvl", 1) * mult)

def send_main_menu(cid: int, uid: int) -> None:
    calculate_income(uid)
    p = players[uid]
    now = time.time()

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        "⛏️ Собрать Налоги",
        "🏢 Развитие Державы",
        "⚔️ Напасть на Игрока (PvP)",
        "🤝 Альянсы и Кланы",
        "🛍️ Рынок Торговли (Stars)",
        "🏆 Top Империй",
        "🛡️ Магазин Щитов",
        "🏢 Императорский Банк",
    ]
    for btn in buttons:
        markup.add(types.KeyboardButton(btn))

    sh_status = (
        f"⏳ Активен (еще {int((p['shield_until'] - now) // 60)} мин)"
        if p.get("shield_until", 0) > now else "❌ Отсутствует"
    )
    ally_text = f"🛡️ [{p['alliance']}]" if p.get("alliance") else "❌ Нет"

    txt = (
        f"🏰 *Держава:* {p['country']}\n"
        f"👑 *Правитель:* @{p['username']}\n"
        f"🤝 *Альянс:* {ally_text}\n\n"
        f"💰 *Казна:* {p['gold']}💰\n"
        f"🏭 *Шахты:* {p['mines']} шт. (Ур. {p.get('mine_lvl', 1)})\n"
        f"⚔️ *Армия:* {p['army']} воинов\n"
        f"🗺️ *Земли:* {p['land']} секторов\n"
        f"🛡️ *Щит империи:* {sh_status}\n\n"
        "Каковы будут ваши великие указы? 👇"
    )

    try:
        bot.send_message(cid, txt, reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        logger.error("Ошибка отправки меню: %s", e)

@bot.message_handler(commands=["start"])
def start(msg):
    uid = msg.from_user.id
    if uid in players:
        send_main_menu(msg.chat.id, uid)
    else:
        markup = types.InlineKeyboardMarkup(row_width=1)
        for k, v in COUNTRIES.items():
            markup.add(
                types.InlineKeyboardButton(
                    f"{v['name']} ({v['bonus']})",
                    callback_data=f"select_{k}"
                )
            )
        try:
            bot.send_message(
                msg.chat.id,
                "🌍 *Добро пожаловать в Глобальную Мировую Стратегию!*\n\nВыберите фракцию:",
                reply_markup=markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error("Ошибка в start: %s", e)

@bot.message_handler(commands=["admin"])
def admin_panel(msg):
    if msg.from_user.id not in ADMIN_IDS:
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📊 Статистика серверов", callback_data="adm_stats"),
        types.InlineKeyboardButton("🎁 Раздать всем по 2000💰", callback_data="adm_gift")
    )
    try:
        bot.send_message(
            msg.chat.id,
            "⚙ *Панель Создателя:*",
            reply_markup=markup,
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error("Ошибка в admin_panel: %s", e)

@bot.message_handler(content_types=["text"])
def game_router(msg):
    uid = msg.from_user.id
    if uid not in players:
        return

    text = msg.text.strip()
    p = players[uid]

    if text == "⛏️ Собрать Налоги":
        event = None
        chance = random.randint(1, 100)
        if chance <= 15:
            ev_opts = [
                {"t": "🌾 *Урожайный год!* +300💰!", "g": 300},
                {"t": "🌋 *Извержение вулкана!* -150💰.", "g": -150},
                {"t": "🏴‍☠️ *Набег пиратов!* +150💰!", "g": 150}
            ]
            event = random.choice(ev_opts)
            p["gold"] = max(0, p["gold"] + event["g"])
            try:
                bot.send_message(msg.chat.id, event["t"], parse_mode="Markdown")
            except Exception as e:
                logger.error("Ошибка при отправке события: %s", e)

        tax_bonus = 15 if p["country"] == "Османский Султанат" else 10
        p["gold"] += tax_bonus
        try:
            bot.send_message(msg.chat.id, "📢 Налоги успешно зачислены в казну!")
        except Exception as e:
            logger.error("Ошибка при отправке сообщения о налогах: %s", e)
        send_main_menu(msg.chat.id, uid)

    elif text == "🏢 Развитие Державы":
        m_cost = (80 if p["country"] == "Сёгунат Токугава" else 100) + (p["mines"] * 50)
        up_cost = p.get("mine_lvl", 1) * 300
        army_cost = 50

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton(f"🏭 Построить шахту ({m_cost}💰)", callback_data="buy_mine"),
            types.InlineKeyboardButton(f"📈 Повысить уровень шахт ({up_cost}💰)", callback_data="up_mine"),
            types.InlineKeyboardButton("⚔️ Нанять 5 воинов ({})💰".format(army_cost), callback_data="buy_army")
        )
        try:
            bot.send_message(
                msg.chat.id,
                "🏗️ *Строительство и Наем:*",
                reply_markup=markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error("Ошибка в развитии державы: %s", e)

    elif text == "⚔️ Напасть на Игрока (PvP)":
        if p["army"] < 5:
            try:
                bot.send_message(msg.chat.id, "❌ Соберите минимум 5 солдат.")
            except Exception as e:
                logger.error("Ошибка сообщения о недостатке армии: %s", e)
            return

        enemy_uid = get_random_enemy(uid)
        if not enemy_uid:
            try:
                bot.send_message(msg.chat.id, "🏳️ Нет доступных целей для войны.")
            except Exception as e:
                logger.error("Ошибка: нет целей для войны: %s", e)
            return

        e = players[enemy_uid]
        atk_mult = 1.15 if p["country"] == "Римская Империя" else 1.0
        def_mult = 1.15 if e["country"] == "Римская Империя" else 1.0

        atk = p["army"] * atk_mult
        defense = e["army"] * def_mult

        win_chance = int((atk / (atk + defense)) * 100)

        if random.randint(1, 100) <= win_chance:
            stolen = int(e["gold"] * 0.3)
            p["gold"] += stolen
            p["land"] += 1
            e["gold"] = max(0, e["gold"] - stolen)
            e["army"] = max(0, e["army"] - 3)
            e["land"] = max(1, e["land"] - 1)

            try:
                bot.send_message(
                    msg.chat.id,
                    f"⚔️ *🔥 ПОБЕДА!*\n\nНаграблено: *+{stolen}💰*.",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error("Ошибка сообщения о победе: %s", e)

            # Отправка уведомления врагу (может не сработать, если он не писал боту)
            try:
                bot.send_message(
                    enemy_uid,
                    f"🚨 *На вашу страну напали!* Потери: -{stolen}💰",
                    parse_mode="Markdown"
                )
            except Exception as e:
                # Это нормально, если бот не может написать пользователю
                logger.warning("Не удалось отправить уведомление врагу (возможно, он заблокировал бота): %s", e)
        else:
            loss = max(1, p["army"] // 2)
            p["army"] -= loss
            try:
                bot.send_message(
                    msg.chat.id,
                    "💀 *РАЗГРОМ!* Ваши полки разбиты.",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logger.error("Ошибка сообщения о поражении: %s", e)

        send_main_menu(msg.chat.id, uid)

    # Остальные ветки (Альянсы, Рынок, Топ, Щиты, Банк) — аналогично:
    # лучше вынести их в отдельные функции или хотя бы добавить try/except и strip().
    # Для краткости не дублирую весь код, но принцип тот же.

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = call.from_user.id
    cid = call.message.chat.id

    try:
        # Админка
        if call.data == "adm_stats":
            if uid in ADMIN_IDS:
                bot.answer_callback_query(
                    call.id,
                    f"Игроков: {len(players)}\nКланов: {len(alliances)}",
                    show_alert=True
                )
            return
        elif call.data == "adm_gift":
            if uid in ADMIN_IDS:
                for p_id in players:
                    players[p_id]["gold"] += 2000
                bot.answer_callback_query(call.id, "Ресурсы розданы!", show_alert=True)
            return

        # Выбор страны
        if call.data.startswith("select_"):
            country_id = call.data.split("_")[-1]
            if country_id not in COUNTRIES:
                return
            username = call.from_user.username or f"id_{uid}"
            init_player(uid, username, country_id)
            try:
                bot.delete_message(cid, call.message.message_id)
            except Exception:
                pass  # Сообщение могло уже быть удалено
            send_main_menu(cid, uid)
            return

        if uid not in players:
            bot.answer_callback_query(call.id, "Сначала начните игру (/start)", show_alert=True)
            return

        p = players[uid]

        # Покупка шахты
        if call.data == "buy_mine":
            cost = (80 if p["country"] == "Сёгунат Токугава" else 100) + (p["mines"] * 50)
            if p["gold"] >= cost:
                p["gold"] -= cost
                p["mines"] += 1
                bot.answer_callback_query(call.id, "🏢 Шахта построена!", show_alert=True)
                try:
                    bot.delete_message(cid, call.message.message_id)
                except Exception:
                    pass
                send_main_menu(cid, uid)
            else:
                bot.answer_callback_query(call.id, "❌ Не хватает золота!", show_alert=True)
            return

        # Улучшение шахты — ДОПИСАНО
        if call.data == "up_mine":
            cost = p.get("mine_lvl", 1) * 300
            if p["gold"] >= cost:
                p["gold"] -= cost
                p["mine_lvl"] = p.get("mine_lvl", 1) + 1
                bot.answer_callback_query(call.id, "🏭 Уровень шахты повышен!", show_alert=True)
                try:
                    bot.delete_message(cid, call.message.message_id)
                except Exception:
                    pass
                send_main_menu(cid, uid)
            else:
                bot.answer_callback_query(call.id, "❌ Не хватает золота!", show_alert=True)
            return

        # Нанять армию (заглушка, можно дописать)
        if call.data == "buy"
