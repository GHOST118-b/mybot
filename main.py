# requirements: pyTelegramBotAPI
import random
import telebot
from telebot import types

# Свежий рабочий токен с защитой от переносов строк
TOKEN = """8834330502:AAF2i1TcCB8rG23EPfnP5dqtoKfEvqweOaA"""

bot = telebot.TeleBot(TOKEN)

# Хранение данных игроков в оперативной памяти (RAM) хостинга
players = {}

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
        "gold": 250,
        "mines": 1,
        "army": 5,
        "land": 10
    }

def get_random_enemy(exclude_uid):
    all_enemies = [k for k in players.keys() if k != exclude_uid]
    return random.choice(all_enemies) if all_enemies else None

def send_main_menu(cid, uid):
    p = players[uid]
    # Начисление пассивного золота при каждом открытии меню
    mult = 1.2 if p["country"] == "Османский Султанат" else 1.0
    p["gold"] += int(p["mines"] * 5 * mult)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("⛏️ Собрать Налоги"), 
        types.KeyboardButton("🏢 Развитие Державы"), 
        types.KeyboardButton("⚔️ Напасть на Игрока (PvP)"), 
        types.KeyboardButton("🏦 Императорский Банк")
    )
    txt = (
        f"🏰 *Держава:* {p['country']}\n"
        f"👑 *Правитель:* @{p['username']}\n\n"
        f"💰 *Казна:* {p['gold']}💰\n"
        f"🏭 *Шахты:* {p['mines']} шт.\n"
        f"⚔️ *Армия:* {p['army']} воинов\n"
        f"🗺️ *Земли:* {p['land']} секторов\n\n"
        f"Приказы для генералов: 👇"
    )
    bot.send_message(cid, txt, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(commands=["start"])
def start(msg):
    uid = msg.from_user.id
    if uid in players:
        send_main_menu(msg.chat.id, uid)
        return
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("Римская Империя (⚔️)", callback_data="select_1"), 
        types.InlineKeyboardButton("Османский Султанат (💰)", callback_data="select_2"), 
        types.InlineKeyboardButton("Сёгунат Токугава (🏭)", callback_data="select_3")
    )
    bot.send_message(msg.chat.id, "🌍 *Великая Карта Мира!*\n\nВыберите фракцию для старта игры:", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(content_types=["text"])
def game_router(msg):
    uid = msg.from_user.id
    if uid not in players: return
    p = players[uid]

    if msg.text == "⛏️ Собрать Налоги":
        inc = 15 if p["country"] == "Османский Султанат" else 10
        p["gold"] += inc
        bot.send_message(msg.chat.id, f"📢 Налоги собраны! В казну добавлено *+{inc}💰*")
        send_main_menu(msg.chat.id, uid)
        
    elif msg.text == "🏢 Развитие Державы":
        markup = types.InlineKeyboardMarkup(row_width=1)
        m_cost = (80 if p["country"] == "Сёгунат Токугава" else 100) + (p["mines"] * 50)
        markup.add(
            types.InlineKeyboardButton(f"🏭 Построить шахту ({m_cost}💰)", callback_data="buy_mine"), 
            types.InlineKeyboardButton("⚔️ Нанять 5 воинов (50💰)", callback_data="buy_army")
        )
        bot.send_message(msg.chat.id, "🏗️ *Строительство и Наем войск:*", reply_markup=markup, parse_mode="Markdown")
        
    elif msg.text == "⚔️ Напасть на Игрока (PvP)":
        if p["army"] < 5:
            bot.send_message(msg.chat.id, "❌ Ваша армия слишком мала! Наберите минимум 5 солдат.")
            return
        enemy_uid = get_random_enemy(uid)
        if not enemy_uid:
            bot.send_message(msg.chat.id, "🏳️ В мире пока нет других государств. Позовите друзей в своего бота!")
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
            bot.send_message(msg.chat.id, f"⚔️ *🔥 ПОБЕДА!*\n\nВы разбили армию фракции {e['country']} игрока @{e['username']}.\n💰 Награблено ресурсов: *+{stolen}💰*.")
            bot.send_message(enemy_uid, f"🚨 *На вашу страну напали!*\n\nВойска {p['country']} игрока @{p['username']} прорвали оборону! Потери казны: -{stolen}💰")
        else:
            lost = max(1, p["army"] // 2)
            p["army"] -= lost
            bot.send_message(msg.chat.id, f"💀 *РАЗГРОМ В ПОХОДЕ!*\n\nВойска державы {e['country']} отбили штурм. Ваши потери: -{lost} воинов.")
        send_main_menu(msg.chat.id, uid)
        
    elif msg.text == "🏦 Императорский Банк":
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("📦 1000 золота — 10 ⭐️", callback_data="s_1000"), 
            types.InlineKeyboardButton("🦏 5000 золота — 40 ⭐️", callback_data="s_5000")
        )
        bot.send_message(msg.chat.id, "🏦 *Императорский Банк:*\n\nПокупка золота за Telegram Stars:", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    uid = call.from_user.id
    if call.data.startswith("select_"):
        init_player(uid, call.from_user.username or f"id_{uid}", call.data.split("_")[1])
        bot.delete_message(call.message.chat.id, call.message.message_id)
        send_main_menu(call.message.chat.id, uid)
        return
        
    if uid not in players: return
    p = players[uid]
    
    if call.data == "buy_mine":
        cost = (80 if p["country"] == "Сёгунат Токугава" else 100) + (p["mines"] * 50)
        if p["gold"] >= cost:
            p["gold"] -= cost
            p["mines"] += 1
            bot.answer_callback_query(call.id, "Шахта построена! 🏢")
        else: bot.answer_callback_query(call.id, "❌ Не хватает золота в казне!", show_alert=True)
        
    elif call.data == "buy_army":
        if p["gold"] >= 50:
            p["gold"] -= 50
            p["army"] += 5
            bot.answer_callback_query(call.id, "Рекруты наняты! ⚔️")
        else: bot.answer_callback_query(call.id, "❌ Мало золота на содержание армии!", show_alert=True)
        
    elif call.data.startswith("s_"):
        bot.answer_callback_query(call.id)
        val = int(call.data.split("_")[1])
        bot.send_invoice(chat_id=call.message.chat.id, title=f"Купить {val} золота", description="Игровые ресурсы.", invoice_payload=f"g_{val}", provider_token="", currency="XTR", prices=[types.LabeledPrice(label="Stars", amount=10 if val == 1000 else 40)])

@bot.shipping_query_handler(func=lambda q: True)
def shipping(q): bot.answer_shipping_query(q.id, ok=True)

@bot.pre_checkout_query_handler(func=lambda q: True)
def checkout(q): bot.answer_pre_checkout_query(q.id, ok=True)

@bot.message_handler(content_types=["successful_payment"])
def got_payment(msg):
    uid = msg.from_user.id
    if uid not in players: return
    val = int(msg.successful_payment.invoice_payload.split("_")[1])
    players[uid]["gold"] += val
    bot.send_message(msg.chat.id, f"👑 *Казначей:* Доставлено пополнение *+{val}💰* золота!")
    send_main_menu(msg.chat.id, uid)

if __name__ == "__main__":
    bot.infinity_polling()
