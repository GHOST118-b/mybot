# requirements: pyTelegramBotAPI
import random
import time
import telebot
from telebot import types

TOKEN = """8834330502:AAF2i1TcCB8rG23EPfnP5dqtoKfEvqweOaA"""
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
    players[uid] = {
        "username": username,
        "country": c_name,
        "gold": 300,
        "mines": 1,
        "mine_lvl": 1,
        "army": 5,
        "land": 10,
        "shield_until": 0,
        "alliance": None
    }

def get_random_enemy(exclude_uid):
    now = time.time()
    all_enemies = [
        k for k, v in players.items() 
        if k != exclude_uid and v.get("shield_until", 0) < now
    ]
    return random.choice(all_enemies) if all_enemies else None

def send_main_menu(cid, uid):
    p = players[uid]
    now = time.time()
    
    mult = 1.2 if p["country"] == "Османский Султанат" else 1.0
    if p.get("alliance") and p["alliance"] in alliances:
        mult += (alliances[p["alliance"]]["level"] * 0.05)
        
    base_income = p["mines"] * 5 * p.get("mine_lvl", 1)
    p["gold"] += int(base_income * mult)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("⛏️ Собрать Налоги"), 
        types.KeyboardButton("🏢 Развитие Державы"), 
        types.KeyboardButton("⚔️ Напасть на Игрока (PvP)"), 
        types.KeyboardButton("🤝 Альянсы и Кланы"),
        types.KeyboardButton("🛍️ Рынок Торговли (Stars)"),
        types.KeyboardButton("🏆 Top Империй"),
        types.KeyboardButton("🛡️ Магазин Щитов"),
        types.KeyboardButton("🏢 Императорский Банк")
    )
    
    shield_status = "❌ Отсутствует"
    if p.get("shield_until", 0) > now:
        remains = int((p["shield_until"] - now) // 60)
        shield_status = f"⏳ Активен (еще {remains} мин)"

    ally_text = f"🛡️ [{p['alliance']}]" if p.get("alliance") else "❌ Нет"

    txt = (
        f"🏰 *Держава:* {p['country']}\n"
        f"👑 *Правитель:* @{p['username']}\n"
        f"🤝 *Альянс:* {ally_text}\n\n"
        f"💰 *Казна:* {p['gold']}💰\n"
        f"🏭 *Шахты:* {p['mines']} шт. (Ур. {p.get('mine_lvl', 1)})\n"
        f"⚔️ *Армия:* {p['army']} воинов\n"
        f"🗺️ *Земли:* {p['land']} секторов\n"
        f"🛡️ *Щит империи:* {shield_status}\n\n"
        f"Каковы будут ваши великие указы? 👇"
    )
    bot.send_message(cid, txt, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(commands=["start"])
def start(msg):
    uid = msg.from_user.id
    if uid in players:
        send_main_menu(msg.chat.id, uid)
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    for k, v in COUNTRIES.items():
        markup.add(types.InlineKeyboardButton(f"{v['name']} ({v['bonus']})", callback_data=f"select_{k}"))
    bot.send_message(msg.chat.id, "🌍 *Добро пожаловать в Глобальную Мировую Стратегию!*\n\nВыберите фракцию:", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(commands=["admin"])
def admin_panel(msg):
    if msg.from_user.id != ADMIN_ID: return
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📊 Статистика серверов", callback_data="adm_stats"),
        types.InlineKeyboardButton("🎁 Раздать всем по 2000💰", callback_data="adm_gift")
    )
    bot.send_message(msg.chat.id, "⚙ *Панель Создателя:*", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(content_types=["text"])
def game_router(msg):
    uid = msg.from_user.id
    if uid not in players: return
    p = players[uid]

    if msg.text == "⛏️ Собрать Налоги":
        if random.randint(1, 100) <= 15:
            events = [
                {"t": "🌾 *Урожайный год!* Народ ликует. Вы получаете сверхприбыль +300💰!", "g": 300},
                {"t": "🌋 *Извержение вулкана!* Часть хранилищ уничтожена, казна теряет -150💰.", "g": -150},
                {"t": "🏴‍☠️ *Набег пиратов!* Вы успешно отбились, забрав их золото +150💰!", "g": 150}
            ]
            ev = random.choice(events)
            p["gold"] = max(0, p["gold"] + ev["g"])
            bot.send_message(msg.chat.id, ev["t"], parse_mode="Markdown")
        
        inc = 15 if p["country"] == "Османский Султанат" else 10
        p["gold"] += inc
        bot.send_message(msg.chat.id, f"📢 Налоги собраны! В казну добавлено *+{inc}💰*")
        send_main_menu(msg.chat.id, uid)
        
    elif msg.text == "🏢 Развитие Державы":
        markup = types.InlineKeyboardMarkup(row_width=1)
        base_cost = 80 if p["country"] == "Сёгунат Токугава" else 100
        m_cost = base_cost + (p["mines"] * 50)
        up_cost = p.get("mine_lvl", 1) * 300
        markup.add(
            types.InlineKeyboardButton(f"🏭 Построить шахту ({m_cost}💰)", callback_data="buy_mine"), 
            types.InlineKeyboardButton(f"📈 Повысить уровень шахт ({up_cost}💰)", callback_data="up_mine"), 
            types.InlineKeyboardButton("⚔️ Нанять 5 воинов (50💰)", callback_data="buy_army")
        )
        bot.send_message(msg.chat.id, "🏗️ *Строительство и Наем:*", reply_markup=markup, parse_mode="Markdown")
        
    elif msg.text == "⚔️ Напасть на Игрока (PvP)":
        if p["army"] < 5:
            bot.send_message(msg.chat.id, "❌ Ваша армия слишком мала! Соберите минимум 5 солдат.")
            return
        enemy_uid = get_random_enemy(uid)
        if not enemy_uid:
            bot.send_message(msg.chat.id, "🏳️ Нет доступных целей для войны (все под куполами щитов или в офлайне).")
            return
            
        e = players[enemy_uid]
        my_power = p["army"] * (1.15 if p["country"] == "Римская Империя" else 1.0)
        enemy_power = e["army"] * (1.15 if e["country"] == "Римская Империя" else 1.0)
        win_chance = int((my_power / (my_power + enemy_power)) * 100)
        
        if random.randint(1, 100) <= win_chance:
            stolen = int(e["gold"] * 0.3)
            p["gold"] += stolen
            p["land"] += 1
            e["gold"] = max(0, e["gold"] - stolen)
            e["army"] = max(0, e["army"] - 3)
            e["land"] = max(1, e["land"] - 1)
            bot.send_message(msg.chat.id, f"⚔️ *🔥 ПОБЕДА!*\n\nВы разбили армию {e['country']} игрока @{e['username']}.\n💰 Награблено: *+{stolen}💰*.")
            bot.send_message(enemy_uid, f"🚨 *На вашу страну напали!*\n\nВойска {p['country']} игрока @{p['username']} прорвали оборону! Потери: -{stolen}💰")
        else:
            lost = max(1, p["army"] // 2)
            p["army"] -= lost
            bot.send_message(msg.chat.id, f"💀 *РАЗГРОМ!*\n\nВойска государства {e['country']} отбили штурм. Потери: -{lost} воинов.")
        send_main_menu(msg.chat.id, uid)

    elif msg.text == "🤝 Альянсы и Кланы":
        markup = types.InlineKeyboardMarkup(row_width=1)
        if not p.get("alliance"):
            markup.add(
                types.InlineKeyboardButton("➕ Создать новый альянс (1000💰)", callback_data="all_create"),
                types.InlineKeyboardButton("🚪 Список всех альянсов", callback_data="all_list")
            )
            bot.send_message(msg.chat.id, "🤝 *Военно-политические Альянсы:*", reply_markup=markup, parse_mode="Markdown")
        else:
            al_name = p["alliance"]
            al = alliances.get(al_name, {"level": 1, "members": []})
            up_c = al["level"] * 2000
            markup.add(
                types.InlineKeyboardButton(f"📈 Повысить уровень клана ({up_c}💰)", callback_data="all_upgrade"),
                types.InlineKeyboardButton("🚪 Выйти из альянса", callback_data="all_leave")
            )
            bot.send_message(msg.chat.id, f"🤝 *Ваш Альянс: {al_name}*\n📊 Уровень союза: {al['level']}\n👥 Всего участников: {len(al['members'])}\n📈 Экономический бонус: +{al['level']*5}% к доходу шахт!", reply_markup=markup, parse_mode="Markdown")

    elif msg.text == "🛍️ Рынок Торговли (Stars)":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("➕ Выставить лот: 2000💰 за 10 ⭐️", callback_data="mkt_sell_2000"),
            types.InlineKeyboardButton("🛒 Посмотреть активные лоты", callback_data="mkt_view")
        )
        bot.send_message(msg.chat.id, "🛍️ *Глобальный межрыночный аукцион:*", reply_markup=markup, parse_mode="Markdown")

    elif msg.text == "🏆 Top Империй":
        sorted_players = sorted(players.items(), key=lambda x: x["gold"], reverse=True)[:10]
        text = "🏆 *ГЛОБАЛЬНЫЙ ТОП-10 ПРАВИТЕЛЕЙ МИРА:*\n\n"
        for i, (p_id, p_data) in enumerate(sorted_players, 1):
            text += f"{i}. @{p_data['username']} — *{p_data['gold']}💰* ({p_data['country']})\n"
        bot.send_message(msg.chat.id, text, parse_mode="Markdown")

    elif msg.text == "🛡️ Магазин Щитов":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("⏳ Мирный договор на 1 час — 200💰", callback_data="shield_1h"),
            types.InlineKeyboardButton("💎 Вечный купол защиты — 50 ⭐️", callback_data="shield_stars")
        )
        bot.send_message(msg.chat.id, "🛡️ *Магазин Защиты:*", reply_markup=markup, parse_mode="Markdown")

    elif msg.text == "🏢 Императорский Банк":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("📦 1000 золото — 10 ⭐️", callback_data="s_1000"), 
            types.InlineKeyboardButton("🦏 5000 золото — 40 ⭐️", callback_data="s_5000")
        )
        bot.send_message(msg.chat.id, "🏦 *Банк:*", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
