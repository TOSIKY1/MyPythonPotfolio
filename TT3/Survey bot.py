import telebot
import sqlite3
import os
from telebot import types
from openpyxl import Workbook

BOT_TOKEN = "7556898981:AAHQiiTYPlTVSa_bQ4IU6UqN8-iVTkBsB1Y"
bot = telebot.TeleBot(BOT_TOKEN)

QUESTIONS = [
    "Do you currently have any insurance?",
    "Are you satisfied with your current insurance provider?",
    "Do you feel your insurance covers all your needs?",
    "Have you ever filed an insurance claim?",
    "Was the claim process easy for you?",
    "Do you think insurance is important for financial safety?",
    "Would you like to reduce your insurance expenses?",
    "Are you interested in additional insurance services?",
    "Do you prefer online communication with insurance companies?",
    "Do you trust insurance companies in general?",
    "Would you like to receive personalized insurance offers?",
    "Do you feel confident choosing insurance products?",
    "Would you like help understanding insurance terms?",
    "Do you plan to change your insurance provider soon?",
    "Do you want to improve your insurance coverage?",
    "Do you want to protect your family with insurance?",
    "Would you like to receive a free consultation?"
]

user_state = {}

def db_path():
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "survey.db")

def init_db():
    conn = sqlite3.connect(db_path())
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, tg_id INTEGER, name TEXT, phone TEXT, result TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS answers (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, question TEXT, answer TEXT)")
    conn.commit()
    conn.close()

def get_state(uid):
    if uid not in user_state:
        user_state[uid] = {"step": 0, "answers": {}, "name": None, "phone": None}
    return user_state[uid]

@bot.message_handler(commands=['start'])
def start(message):
    init_db()
    state = get_state(message.from_user.id)
    state["step"] = 0
    state["answers"] = {}
    state["name"] = None
    state["phone"] = None
    bot.send_message(message.chat.id, "Welcome to the Insurance Engagement Survey. What is your name?")
    bot.register_next_step_handler(message, get_name)

def get_name(message):
    state = get_state(message.from_user.id)
    state["name"] = message.text.strip()
    bot.send_message(message.chat.id, "Please enter your phone number.")
    bot.register_next_step_handler(message, get_phone)

def get_phone(message):
    state = get_state(message.from_user.id)
    state["phone"] = message.text.strip()
    ask_question(message.chat.id, message.from_user.id)

def ask_question(chat_id, uid):
    state = get_state(uid)
    if state["step"] >= len(QUESTIONS):
        finish_survey(chat_id, uid)
        return
    q = QUESTIONS[state["step"]]
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Yes", callback_data="yes"), 
               types.InlineKeyboardButton("No", callback_data="no"))
    bot.send_message(chat_id, q, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: True)
def answer_handler(call):
    uid = call.from_user.id
    state = get_state(uid)
    
    # Проверяем, не завершен ли уже опрос
    if state["step"] >= len(QUESTIONS):
        bot.answer_callback_query(call.id, "Survey already completed!")
        return
    
    # Проверяем, что step находится в допустимых пределах
    if 0 <= state["step"] < len(QUESTIONS):
        q = QUESTIONS[state["step"]]
        state["answers"][q] = call.data
        state["step"] += 1
        bot.answer_callback_query(call.id)
        ask_question(call.message.chat.id, uid)

def finish_survey(chat_id, uid):
    state = get_state(uid)
    yes_count = list(state["answers"].values()).count("yes")
    
    if yes_count >= 12:
        result = "High engagement. You are an ideal client for advanced insurance products."
    elif yes_count >= 7:
        result = "Medium engagement. You may benefit from personalized insurance offers."
    else:
        result = "Low engagement. You may need basic insurance guidance."
    
    conn = sqlite3.connect(db_path())
    cur = conn.cursor()
    cur.execute("INSERT INTO users (tg_id, name, phone, result) VALUES (?, ?, ?, ?)", 
                (uid, state["name"], state["phone"], result))
    user_id = cur.lastrowid
    
    for q, a in state["answers"].items():
        cur.execute("INSERT INTO answers (user_id, question, answer) VALUES (?, ?, ?)", 
                    (user_id, q, a))
    conn.commit()
    conn.close()
    
    bot.send_message(chat_id, "Survey completed.\n\nYour result:\n" + result)
    
    # Очищаем состояние пользователя
    if uid in user_state:
        del user_state[uid]

@bot.message_handler(commands=['export'])
def export_excel(message):
    if message.from_user.id != message.chat.id:
        return

    conn = sqlite3.connect(db_path())
    cur = conn.cursor()
    cur.execute("SELECT * FROM users")
    users = cur.fetchall()
    cur.execute("SELECT user_id, question, answer FROM answers")
    answers = cur.fetchall()
    conn.close()

    wb = Workbook()
    ws1 = wb.active
    ws1.title = "Users"
    ws1.append(["ID", "TG ID", "Name", "Phone", "Result"])
    for row in users:
        ws1.append(row)

    ws2 = wb.create_sheet("Answers")
    ws2.append(["User ID", "Question", "Answer"])
    for row in answers:
        ws2.append(row)

    filename = "/tmp/survey_export.xlsx"
    wb.save(filename)

    with open(filename, 'rb') as file:
        bot.send_document(message.chat.id, file)

    
    try:
        os.remove(filename)
    except:
        pass


@bot.message_handler(commands=['reset'])
def reset_survey(message):
    uid = message.from_user.id
    if uid in user_state:
        del user_state[uid]
    bot.send_message(message.chat.id, "Your survey progress has been reset. Use /start to begin again.")

@bot.message_handler(commands=['help'])
def help_command(message):
    help_text = """
Available commands:
/start - Start the survey
/reset - Reset your current survey progress
/export - Export survey results to Excel (admin only)
/help - Show this help message
"""
    bot.send_message(message.chat.id, help_text)

if __name__ == '__main__':
    bot.polling(none_stop=True)