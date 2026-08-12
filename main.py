# requirements: pyTelegramBotAPI
import random
import time
import telebot
from telebot import types

TOKEN = "8834330502:AAF2i1TcCB8rG23EPfnP5dqtoKfEvqweOaA"
bot = telebot.TeleBot(TOKEN)
ADMIN_ID = 574241586

players = {}
alliances = {}
market_lots = {}

COUNTRIES = {
    "1": {"name": "Римская Империя", "bonus": "⚔️ +15% атака в PvP"},
    "2": {"name": "Османский Султанат", "bonus": "💰 +20% налоги с крестьян"},
    "3": {"name": "Сёгунат Токугава", "bonus": "🏭 Шахты дешевле на 20%"},
}

def init_player(uid, username, country_id):
    c_name = COUNTRIES[country_id]["name"]
    players[uid] = {"username": username, "country": c_name, "gold": 300, "mines": 1, "mine_lvl": 1, "army": 5, "land": 10, "shield_until": 0, "alliance": None}

def get_random_enemy(exclude_uid):
    now = time.time()
    all_enemies = [k for k, v in players.items() if k != exclude_uid and v.get("shield_until", 0) < now]
    return random.choice(all_enemies) if all_enemies else None

def calculate_income(uid):
    p = players[uid]
    mult = 1.2 if p["country"] == "Османский Султанат" else 1.0
    if p.get("alliance") and p["alliance"] in alliances: mult += (alliances[p["alliance"]]["level"] * 0.05)
    p["gold"] += int(p["mines"] * 5 * p.get("mine_lvl", 1) * mult)

def send_main_menu(cid, uid):
    calculate_income(uid)
    p = players[uid]
    now = time.time()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(types.KeyboardButton("⛏️ Собрать Налоги"), types.KeyboardButton("🏢 Развитие Державы"), types.KeyboardButton("⚔️ Напасть на Игрока (PvP)"), types.KeyboardButton("🤝 Альянсы и Кланы"), types.KeyboardButton("🛍️ Рынок Торговли (Stars)"), types.KeyboardButton("🏆 Top Империй"), types.KeyboardButton("🛡️ Магазин Щитов"), types.KeyboardButton("🏢 Императорский Банк"))
    sh_status = f"⏳ Активен (еще {int((p['shield_until'] - now) // 60)} мин)" if p.get("shield_until", 0) > now else "❌ Отсутствует"
    ally_text = f"🛡️ [{p['alliance']}]" if p.get("alliance") else "❌ Нет"
    txt = f"🏰 *Держава:* {p['country']}\n👑 *Правитель:* @{p['username']}\n🤝 *Альянс:* {ally_text}\n\n💰 *Казна:* {p['gold']}💰\n🏭 *Шахты:* {p['mines']} шт. (Ур. {p.get('mine_lvl', 1)})\n⚔️ *Армия:* {p['army']} воинов\n🗺️ *Земли:* {p['land']} секторов\n🛡️ *Щит империи:* {sh_status}\n\nКаковы будут ваши великие указы? 👇"
    bot.send_message(cid, txt, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(commands=["start"])
def start(msg):
    uid = msg.from_user.id
    if uid in players:
        send_main_menu(msg.chat.id, uid)
    else:
        markup = types.InlineKeyboardMarkup(row_width=1)
        for k, v in COUNTRIES.items(): markup.add(types.InlineKeyboardButton(f"{v['name']} ({v['bonus']})", callback_data=f"select_{k}"))
        bot.send_message(msg.chat.id, "🌍 *Добро пожаловать в Глобальную Мировую Стратегию!*\n\nВыберите фракцию:", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(commands=["admin"])
def admin_panel(msg):
    if msg.from_user.id != ADMIN_ID: return
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("📊 Статистика серверов", callback_data="adm_stats"), types.InlineKeyboardButton("🎁 Раздать всем по 2000💰", callback_data="adm_gift"))
    bot.send_message(msg.chat.id, "⚙ *Панель Создателя:*", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(content_types=["text"])
def game_router(msg):
    uid = msg.from_user.id
    if uid not in players: return
    p = players[uid]
    if msg.text == "⛏️ Собрать Налоги":
        if random.randint(1, 100) <= 15:
            ev = random.choice([{"t": "🌾 *Урожайный год!* +300💰!", "g": 300}, {"t": "🌋 *Извержение вулкана!* -150💰.", "g": -150}, {"t": "🏴‍☠️ *Набег пиратов!* +150💰!", "g": 150}])
            p["gold"] = max(0, p["gold"] + ev["g"])
            bot.send_message(msg.chat.id, ev["t"], parse_mode="Markdown")
        p["gold"] += (15 if p["country"] == "Османский Султанат" else 10)
        bot.send_message(msg.chat.id, "📢 Налоги успешно зачислены в казну!")
        send_main_menu(msg.chat.id, uid)
    elif msg.text == "🏢 Развитие Державы":
        markup = types.InlineKeyboardMarkup(row_width=1)
        m_cost = (80 if p["country"] == "Сёгунат Токугава" else 100) + (p["mines"] * 50)
        markup.add(types.InlineKeyboardButton(f"🏭 Построить шахту ({m_cost}💰)", callback_data="buy_mine"), types.InlineKeyboardButton(f"📈 Повысить уровень шахт ({p.get('mine_lvl', 1) * 300}💰)", callback_data="up_mine"), types.InlineKeyboardButton("⚔️ Нанять 5 воинов (50💰)", callback_data="buy_army"))
        bot.send_message(msg.chat.id, "🏗️ *Строительство и Наем:*", reply_markup=markup, parse_mode="Markdown")
    elif msg.text == "⚔️ Напасть на Игрока (PvP)":
        if p["army"] < 5:
            bot.send_message(msg.chat.id, "❌ Соберите минимум 5 солдат.")
            return
        enemy_uid = get_random_enemy(uid)
        if not enemy_uid:
            bot.send_message(msg.chat.id, "🏳️ Нет доступных целей для войны.")
            return
        e = players[enemy_uid]
        win_chance = int(((p["army"] * (1.15 if p["country"] == "Римская Империя" else 1.0)) / ((p["army"] * (1.15 if p["country"] == "Римская Империя" else 1.0)) + (e["army"] * (1.15 if e["country"] == "Римская Империя" else 1.0)))) * 100)
        if random.randint(1, 100) <= win_chance:
            stolen = int(e["gold"] * 0.3)
            p["gold"], p["land"], e["gold"], e["army"], e["land"] = p["gold"] + stolen, p["land"] + 1, max(0, e["gold"] - stolen), max(0, e["army"] - 3), max(1, e["land"] - 1)
            bot.send_message(msg.chat.id, f"⚔️ *🔥 ПОБЕДА!*\n\nНаграблено: *+{stolen}💰*.")
            bot.send_message(enemy_uid, f"🚨 *На вашу страну напали!* Потери: -{stolen}💰")
        else:
            p["army"] -= max(1, p["army"] // 2)
            bot.send_message(msg.chat.id, "💀 *РАЗГРОМ!* Ваши полки разбиты.")
        send_main_menu(msg.chat.id, uid)
    elif msg.text == "🤝 Альянсы и Кланы":
        markup = types.InlineKeyboardMarkup(row_width=1)
        if not p.get("alliance"):
            markup.add(types.InlineKeyboardButton("➕ Создать альянс (1000💰)", callback_data="all_create"), types.InlineKeyboardButton("🚪 Список всех альянсов", callback_data="all_list"))
            bot.send_message(msg.chat.id, "🤝 *Военно-политические Альянсы:*", reply_markup=markup, parse_mode="Markdown")
        else:
            al = alliances.get(p["alliance"], {"level": 1, "members": []})
            markup.add(types.InlineKeyboardButton(f"📈 Повысить уровень клана ({al['level'] * 2000}💰)", callback_data="all_upgrade"), types.InlineKeyboardButton("🚪 Выйти из альянса", callback_data="all_leave"))
            bot.send_message(msg.chat.id, f"🤝 *Ваш Альянс: {p['alliance']}*\n📊 Уровень: {al['level']}\n👥 Участников: {len(al['members'])}\n📈 Бонус: +{al['level']*5}% к шахтам!", reply_markup=markup, parse_mode="Markdown")
    elif msg.text == "🛍️ Рынок Торговли (Stars)":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("➕ Выставить лот: 2000💰 за 10 ⭐️", callback_data="mkt_sell_2000"), types.InlineKeyboardButton("🛒 Посмотреть активные лоты", callback_data="mkt_view"))
        bot.send_message(msg.chat.id, "🛍️ *Глобальный аукцион:*", reply_markup=markup, parse_mode="Markdown")
    elif msg.text == "🏆 Топ Империй":
        sorted_players = sorted(players.items(), key=lambda x: x[1]["gold"], reverse=True)[:10]
        text = "🏆 *ГЛОБАЛЬНЫЙ ТОП-10 ПРАВИТЕЛЕЙ:*\n\n"
        for i, (p_id, p_data) in enumerate(sorted_players, 1): text += f"{i}. @{p_data['username']} — *{p_data['gold']}💰* ({p_data['country']})\n"
        bot.send_message(msg.chat.id, text, parse_mode="Markdown")
    elif msg.text == "🛡️ Магазин Щитов":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("⏳ Мирный договор на 1 час — 200💰", callback_data="shield_1h"), types.InlineKeyboardButton("💎 Вечный купол защиты — 50 ⭐️", callback_data="shield_stars"))
        bot.send_message(msg.chat.id, "🛡️ *Магазин Защиты:*", reply_markup=markup, parse_mode="Markdown")
    elif msg.text == "🏢 Императорский Банк":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("📦 1000 золото — 10 ⭐️", callback_data="s_1000"), types.InlineKeyboardButton("🦏 5000 золото — 40 ⭐️", callback_data="s_5000"))
        bot.send_message(msg.chat.id, "🏦 *Банк:*", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = call.from_user.id
    cid = call.message.chat.id
    if call.data == "adm_stats":
        if uid == ADMIN_ID: bot.answer_callback_query(call.id, f"Игроков: {len(players)}\nКланов: {len(alliances)}", show_alert=True)
        return
    elif call.data == "adm_gift":
        if uid == ADMIN_ID:
            for p_id in players: players[p_id]["gold"] += 2000
            bot.answer_callback_query(call.id, "Ресурсы розданы!", show_alert=True)
        return
    if call.data.startswith("select_"):
        init_player(uid, call.from_user.username or f"id_{uid}", call.data.split("_")[-1])
        bot.delete_message(cid, call.message.message_id)
        send_main_menu(cid, uid)
        return
    if uid not in players: return
    p = players[uid]
    if call.data == "buy_mine":
        cost = (80 if p["country"] == "Сёгунат Токугава" else 100) + (p["mines"] * 50)
        if p["gold"] >= cost:
            p["gold"], p["mines"] = p["gold"] - cost, p["mines"] + 1
            bot.answer_callback_query(call.id, "🏢 Шахта построена!", show_alert=True)
            bot.delete_message(cid, call.message.message_id)
            send_main_menu(cid, uid)
        else: bot.answer_callback_query(call.id, "❌ Не хватает золота!", show_alert=True)
    elif call.data == "up_mine":
        cost = p.get("mine_lvl", 1) * 300
        if p["gold"] >= cost:
