import telebot
import sqlite3
import os
import datetime
from telebot import types

BOT_TOKEN = "7556898981:AAHQiiTYPlTVSa_bQ4IU6UqN8-iVTkBsB1Y"  # ← ВСТАВЬ СЮДА СВОЙ ТОКЕН
bot = telebot.TeleBot(BOT_TOKEN)

# Состояния пользователей в памяти
user_state = {}


def get_db_path():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "user.db")


def init_db():
    conn = sqlite3.connect(get_db_path())
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            service_id INTEGER,
            FOREIGN KEY(service_id) REFERENCES services(id)
        )
    ''')

    cur.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            user_name TEXT,
            phone TEXT,
            doctor_id INTEGER,
            service_id INTEGER,
            date TEXT,
            time TEXT,
            status TEXT DEFAULT 'active'
        )
    ''')

    conn.commit()

    cur.execute("SELECT COUNT(*) FROM services")
    if cur.fetchone()[0] == 0:
        services = [("Therapist",), ("Dentist",), ("Cardiologist",)]
        cur.executemany("INSERT INTO services (name) VALUES (?)", services)

    cur.execute("SELECT COUNT(*) FROM doctors")
    if cur.fetchone()[0] == 0:
        doctors = [
            ("Dr. Smith", 1),
            ("Dr. Brown", 1),
            ("Dr. White", 2),
            ("Dr. Black", 2),
            ("Dr. Heart", 3),
        ]
        cur.executemany("INSERT INTO doctors (name, service_id) VALUES (?, ?)", doctors)

    conn.commit()
    conn.close()

def get_user_state(user_id):
    if user_id not in user_state:
        user_state[user_id] = {}
    return user_state[user_id]


def get_dates():
    """Следующие 60 дней, только будни."""
    today = datetime.date.today()
    dates = []
    for i in range(60):
        day = today + datetime.timedelta(days=i)
        if day.weekday() < 5:  # 0-4 — будни
            dates.append(day.strftime("%Y-%m-%d"))
    return dates


def get_times():
    """Слоты времени."""
    return ["09:00", "10:00", "11:00", "12:00", "14:00", "15:00", "16:00"]

@bot.message_handler(commands=['start'])
def start(message):
    init_db()

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = types.KeyboardButton('Make an appointment')
    btn2 = types.KeyboardButton('My appointments')
    markup.add(btn1, btn2)

    bot.send_message(message.chat.id, "Welcome to hospital!", reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def menu_handler(message):
    if message.text == "Make an appointment":
        start_new_appointment_flow(message)
    elif message.text == "My appointments":
        show_my_appointments(message)


def start_new_appointment_flow(message):
    state = get_user_state(message.from_user.id)
    state.clear()
    state["mode"] = "new"
    show_services(message.chat.id)

def show_services(chat_id):
    conn = sqlite3.connect(get_db_path())
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM services")
    services = cur.fetchall()
    conn.close()

    if not services:
        bot.send_message(chat_id, "No services found.")
        return

    markup = types.InlineKeyboardMarkup()
    for sid, name in services:
        markup.add(types.InlineKeyboardButton(name, callback_data=f"service_{sid}"))

    bot.send_message(chat_id, "Choose a service:", reply_markup=markup)

def show_doctors(chat_id, service_id):
    conn = sqlite3.connect(get_db_path())
    cur = conn.cursor()
    cur.execute("SELECT id, name FROM doctors WHERE service_id = ?", (service_id,))
    doctors = cur.fetchall()
    conn.close()

    if not doctors:
        bot.send_message(chat_id, "No doctors for this service yet.")
        return

    markup = types.InlineKeyboardMarkup()
    for did, name in doctors:
        markup.add(types.InlineKeyboardButton(name, callback_data=f"doctor_{did}"))

    bot.send_message(chat_id, "Choose a doctor:", reply_markup=markup)


def show_dates(chat_id, doctor_id, mode="new", appointment_id=0):
    dates = get_dates()
    markup = types.InlineKeyboardMarkup(row_width=3)

    for d in dates:
        cb = f"date_{doctor_id}_{d}_{mode}_{appointment_id}"
        markup.add(types.InlineKeyboardButton(d, callback_data=cb))

    bot.send_message(chat_id, "Choose a date:", reply_markup=markup)

def show_times(chat_id, doctor_id, date_str, mode="new", appointment_id=0):
    times = get_times()
    markup = types.InlineKeyboardMarkup(row_width=3)
    for t in times:
        cb = f"time_{doctor_id}_{date_str}_{mode}_{appointment_id}_{t}"
        markup.add(types.InlineKeyboardButton(t, callback_data=cb))

    bot.send_message(chat_id, f"Choose a time for {date_str}:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    data = call.data
    user_id = call.from_user.id
    state = get_user_state(user_id)

    # Выбор услуги
    if data.startswith("service_"):
        _, sid = data.split("_", 1)
        state["service_id"] = int(sid)
        bot.answer_callback_query(call.id)
        show_doctors(call.message.chat.id, int(sid))

    elif data.startswith("doctor_"):
        _, did = data.split("_", 1)
        state["doctor_id"] = int(did)
        bot.answer_callback_query(call.id)
        show_dates(
            call.message.chat.id,
            int(did),
            mode=state.get("mode", "new"),
            appointment_id=state.get("appointment_id", 0)
        )

    elif data.startswith("date_"):

        parts = data.split("_")
        doctor_id = int(parts[1])
        date_str = parts[2]
        mode = parts[3]
        appointment_id = int(parts[4])

        state["doctor_id"] = doctor_id
        state["date"] = date_str
        state["mode"] = mode
        state["appointment_id"] = appointment_id

        bot.answer_callback_query(call.id)
        show_times(call.message.chat.id, doctor_id, date_str, mode, appointment_id)

    elif data.startswith("time_"):

        parts = data.split("_")
        doctor_id = int(parts[1])
        date_str = parts[2]
        mode = parts[3]
        appointment_id = int(parts[4])
        time_str = parts[5]

        state["doctor_id"] = doctor_id
        state["date"] = date_str
        state["time"] = time_str
        state["mode"] = mode
        state["appointment_id"] = appointment_id

        bot.answer_callback_query(call.id)

        if mode == "new":
            ask_user_name(call.message)
        else:
            apply_reschedule(call.message, user_id)

    elif data.startswith("cancel_"):
        _, appt_id = data.split("_", 1)
        bot.answer_callback_query(call.id)
        cancel_appointment(call.message, int(appt_id))

    elif data.startswith("resched_"):
        _, appt_id = data.split("_", 1)
        bot.answer_callback_query(call.id)
        start_reschedule_flow(call.message, user_id, int(appt_id))

def ask_user_name(message):
    msg = bot.send_message(message.chat.id, "Enter your name:")
    bot.register_next_step_handler(msg, process_user_name)


def process_user_name(message):
    state = get_user_state(message.from_user.id)
    state["user_name"] = message.text.strip()
    msg = bot.send_message(message.chat.id, "Enter your phone number:")
    bot.register_next_step_handler(msg, process_user_phone)


def process_user_phone(message):
    state = get_user_state(message.from_user.id)
    state["phone"] = message.text.strip()

 
    finalize_new_appointment(message, message.from_user.id)

def finalize_new_appointment(message, user_id):
    state = get_user_state(user_id)

    service_id = state.get("service_id")
    doctor_id = state.get("doctor_id")
    date_str = state.get("date")
    time_str = state.get("time")
    user_name = state.get("user_name")
    phone = state.get("phone")

    if not all([service_id, doctor_id, date_str, time_str, user_name, phone]):
        bot.send_message(message.chat.id, "Error: not enough data to create appointment.")
        return

    conn = sqlite3.connect(get_db_path())
    cur = conn.cursor()
    cur.execute(
        '''
        INSERT INTO appointments (user_id, user_name, phone, doctor_id, service_id, date, time, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, 'active')
        ''',
        (user_id, user_name, phone, doctor_id, service_id, date_str, time_str)
    )
    conn.commit()
    conn.close()

    bot.send_message(
        message.chat.id,
        f"Your appointment is confirmed:\n"
        f"Service ID: {service_id}\n"
        f"Doctor ID: {doctor_id}\n"
        f"Date: {date_str}\nTime: {time_str}"
    )

    state.clear()

def show_my_appointments(message):
    conn = sqlite3.connect(get_db_path())
    cur = conn.cursor()

    cur.execute('''
        SELECT appointments.id, services.name, doctors.name, appointments.date, appointments.time
        FROM appointments
        JOIN services ON appointments.service_id = services.id
        JOIN doctors ON appointments.doctor_id = doctors.id
        WHERE appointments.user_id = ?
          AND appointments.status = 'active'
        ORDER BY appointments.date, appointments.time
    ''', (message.from_user.id,))

    rows = cur.fetchall()
    conn.close()

    if not rows:
        bot.send_message(message.chat.id, "You have no active appointments.")
        return

    text = "Your appointments:\n\n"
    markup = types.InlineKeyboardMarkup()

    for appt_id, service, doctor, date, time in rows:
        text += f"🩺 {service}\n👨‍⚕️ {doctor}\n📅 {date} ⏰ {time}\n\n"
        markup.add(
            types.InlineKeyboardButton(
                f"Cancel {date} {time}",
                callback_data=f"cancel_{appt_id}"
            )
        )
        markup.add(
            types.InlineKeyboardButton(
                f"Reschedule {date} {time}",
                callback_data=f"resched_{appt_id}"
            )
        )

    bot.send_message(message.chat.id, text, reply_markup=markup)


def cancel_appointment(message, appt_id):
    conn = sqlite3.connect(get_db_path())
    cur = conn.cursor()
    cur.execute("UPDATE appointments SET status = 'cancelled' WHERE id = ?", (appt_id,))
    conn.commit()
    conn.close()

    bot.send_message(message.chat.id, "Your appointment has been cancelled.")

def start_reschedule_flow(message, user_id, appt_id):
    state = get_user_state(user_id)
    state.clear()
    state["mode"] = "reschedule"
    state["appointment_id"] = appt_id

    conn = sqlite3.connect(get_db_path())
    cur = conn.cursor()
    cur.execute(
        '''
        SELECT doctor_id, service_id, date, time, user_name, phone
        FROM appointments WHERE id = ?
        ''',
        (appt_id,)
    )
    row = cur.fetchone()
    conn.close()

    if not row:
        bot.send_message(message.chat.id, "Appointment not found.")
        return

    doctor_id, service_id, date_str, time_str, user_name, phone = row
    state["doctor_id"] = doctor_id
    state["service_id"] = service_id
    state["user_name"] = user_name
    state["phone"] = phone

    bot.send_message(message.chat.id, "Choose a new date for this appointment:")
    show_dates(message.chat.id, doctor_id, mode="reschedule", appointment_id=appt_id)


def apply_reschedule(message, user_id):
    state = get_user_state(user_id)
    appt_id = state.get("appointment_id")
    date_str = state.get("date")
    time_str = state.get("time")

    if not appt_id or not date_str or not time_str:
        bot.send_message(message.chat.id, "Reschedule error. Please try again.")
        return

    conn = sqlite3.connect(get_db_path())
    cur = conn.cursor()
    cur.execute(
        "UPDATE appointments SET date = ?, time = ? WHERE id = ?",
        (date_str, time_str, appt_id)
    )
    conn.commit()
    conn.close()

    bot.send_message(
        message.chat.id,
        f"Your appointment has been rescheduled to:\nDate: {date_str}\nTime: {time_str}"
    )

    state.clear()

bot.polling(none_stop=True)
