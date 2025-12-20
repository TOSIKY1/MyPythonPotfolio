import telebot
import sqlite3
import os
from telebot import types
from datetime import datetime, timedelta

bot = telebot.TeleBot('8269132930:AAGNrQrb3bbFWyczNKlBNEIgOS7eds8CcOc')
password = '123'

def init_db():
    conn = sqlite3.connect('bot_database.sql')
    cur = conn.cursor()
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS catalog (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name_ctl TEXT NOT NULL,
            price INTEGER NOT NULL,
            description TEXT,
            photo TEXT
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            total_price INTEGER,
            created DATE,
            customer_name TEXT,
            customer_phone TEXT,
            status TEXT DEFAULT 'new'
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            item_id INTEGER,
            quantity INTEGER,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (item_id) REFERENCES catalog(id)
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            username TEXT
        )
    ''')
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS basket (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            item_id INTEGER,
            quantity INTEGER,
            FOREIGN KEY (item_id) REFERENCES catalog(id)
        )
    ''')
    
    conn.commit()
    cur.close()
    conn.close()

init_db()

user_states = {}

def is_admin(user_id):
    conn = sqlite3.connect('bot_database.sql')
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM admins WHERE user_id = ?", (user_id,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    return result is not None

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup()
    strt1 = types.InlineKeyboardButton('Catalog', callback_data='ctl')
    strt2 = types.InlineKeyboardButton('Support', callback_data='hlp')
    strt3 = types.InlineKeyboardButton('Basket', callback_data='bsk')
    
    if is_admin(message.from_user.id):
        strt4 = types.InlineKeyboardButton('Admin Panel', callback_data='admin_panel')
        markup.row(strt1)
        markup.row(strt2, strt3)
        markup.row(strt4)
    else:
        markup.row(strt1)
        markup.row(strt2, strt3)
    
    bot.send_message(
        message.chat.id,
        f'{message.from_user.first_name}, Welcome to our bakery! What would you like to order?',
        reply_markup=markup
    )

@bot.message_handler(content_types=['text'])
def handle_text(message):
    if message.text.lower() == 'admin':
        msg = bot.send_message(message.chat.id, 'Enter password:')
        bot.register_next_step_handler(msg, check_password)
    else:
        bot.send_message(message.chat.id, 'Use menu buttons.')

def check_password(message):
    if message.text == password:
        add_admin(message)
        admin_panel(message)
    else:
        bot.send_message(message.chat.id, 'Incorrect password.')

def add_admin(message):
    conn = sqlite3.connect('bot_database.sql')
    cur = conn.cursor()
    try:
        cur.execute("INSERT OR IGNORE INTO admins (user_id, username) VALUES (?, ?)",
                   (message.from_user.id, message.from_user.username))
        conn.commit()
    except:
        pass
    cur.close()
    conn.close()

def admin_panel(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    adminbtn1 = types.InlineKeyboardButton('Edit/Delete position', callback_data='edit')
    adminbtn2 = types.InlineKeyboardButton('Analytics', callback_data='analytics')
    adminbtn3 = types.InlineKeyboardButton('Orders', callback_data='view_orders')
    adminbtn4 = types.InlineKeyboardButton('Add position', callback_data='addposs')
    back_btn = types.InlineKeyboardButton('Back', callback_data='back_to_main')
    markup.add(adminbtn1, adminbtn4, adminbtn2, adminbtn3, back_btn)
    bot.send_message(message.chat.id, 'Admin Panel', reply_markup=markup)

@bot.callback_query_handler(func=lambda callback: True)
def handle_callback(callback):
    data = callback.data
    
    if data == 'ctl':
        show_catalog(callback)
    elif data == 'bsk':
        show_basket(callback)
    elif data == 'hlp':
        show_support(callback)
    elif data == 'admin_panel':
        admin_panel(callback.message)
    elif data == 'edit':
        edit_menu(callback)
    elif data == 'addposs':
        add_position(callback)
    elif data == 'analytics':
        send_analytics(callback)
    elif data == 'view_orders':
        view_orders(callback)
    elif data.startswith('item_'):
        item_id = data.split('_')[1]
        show_item_card(callback, item_id)
    elif data.startswith('addcart_'):
        item_id = data.split('_')[1]
        add_to_cart(callback, item_id)
    elif data.startswith('delcart_'):
        basket_id = data.split('_')[1]
        delete_from_cart(callback, basket_id)
    elif data.startswith('delitem_'):
        item_id = data.split('_')[1]
        delete_item(callback, item_id)
    elif data.startswith('edititem_'):
        item_id = data.split('_')[1]
        edit_item_start(callback, item_id)
    elif data.startswith('order_'):
        order_id = data.split('_')[1]
        view_order_details(callback, order_id)
    elif data.startswith('status_'):
        parts = data.split('_')
        order_id = parts[1]
        status = parts[2]
        change_order_status(callback, order_id, status)
    elif data == 'checkout':
        start_checkout(callback)
    elif data == 'back_to_main':
        start(callback.message)
    elif data == 'back_to_admin':
        admin_panel(callback.message)
    elif data == 'back_to_basket':
        show_basket(callback)
    elif data == 'back_to_catalog':
        show_catalog(callback)
    elif data == 'back_to_orders':
        view_orders(callback)
    elif data == 'clear_basket':
        clear_basket(callback)

def show_catalog(callback):
    conn = sqlite3.connect('bot_database.sql')
    cur = conn.cursor()
    cur.execute("SELECT id, name_ctl, price FROM catalog ORDER BY name_ctl")
    items = cur.fetchall()
    cur.close()
    conn.close()

    if not items:
        markup = types.InlineKeyboardMarkup()
        back_btn = types.InlineKeyboardButton('Back', callback_data='back_to_main')
        markup.add(back_btn)
        bot.send_message(callback.message.chat.id, "Catalog is empty.", reply_markup=markup)
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    for item in items:
        item_id, name, price = item
        markup.add(
            types.InlineKeyboardButton(
                text=f"{name} — {price} ₽",
                callback_data=f"item_{item_id}"
            )
        )
    
    back_btn = types.InlineKeyboardButton('Back', callback_data='back_to_main')
    markup.add(back_btn)
    
    bot.edit_message_text(
        "Choose product:",
        callback.message.chat.id,
        callback.message.message_id,
        reply_markup=markup
    )

def show_item_card(callback, item_id):
    conn = sqlite3.connect('bot_database.sql')
    cur = conn.cursor()
    cur.execute("SELECT name_ctl, price, description, photo FROM catalog WHERE id = ?", (item_id,))
    item = cur.fetchone()
    cur.close()
    conn.close()

    if not item:
        bot.answer_callback_query(callback.id, "Product not found.")
        return

    name, price, description, photo = item

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Add to basket", callback_data=f"addcart_{item_id}"))
    
    if is_admin(callback.from_user.id):
        markup.add(
            types.InlineKeyboardButton("Edit", callback_data=f"edititem_{item_id}"),
            types.InlineKeyboardButton("Delete", callback_data=f"delitem_{item_id}")
        )
    
    back_btn = types.InlineKeyboardButton('Back', callback_data='ctl')
    markup.add(back_btn)

    if photo and photo.startswith('AgAC'):
        try:
            bot.send_photo(
                callback.message.chat.id,
                photo,
                caption=f"**{name}**\n\nPrice: {price} ₽\n\n{description}",
                reply_markup=markup,
                parse_mode='Markdown'
            )
        except:
            bot.send_message(
                callback.message.chat.id,
                f"**{name}**\n\nPrice: {price} ₽\n\n{description}",
                reply_markup=markup,
                parse_mode='Markdown'
            )
    else:
        bot.send_message(
            callback.message.chat.id,
            f"**{name}**\n\nPrice: {price} ₽\n\n{description}",
            reply_markup=markup,
            parse_mode='Markdown'
        )

def add_to_cart(callback, item_id):
    user_id = callback.from_user.id
    
    conn = sqlite3.connect('bot_database.sql')
    cur = conn.cursor()
    
    cur.execute("SELECT id, quantity FROM basket WHERE user_id = ? AND item_id = ?", (user_id, item_id))
    row = cur.fetchone()

    if row:
        basket_id, qty = row
        cur.execute("UPDATE basket SET quantity = ? WHERE id = ?", (qty + 1, basket_id))
    else:
        cur.execute("INSERT INTO basket (user_id, item_id, quantity) VALUES (?, ?, ?)", (user_id, item_id, 1))

    conn.commit()
    cur.close()
    conn.close()
    
    bot.answer_callback_query(callback.id, "Added to basket ✓")

def show_basket(callback):
    user_id = callback.from_user.id
    
    conn = sqlite3.connect('bot_database.sql')
    cur = conn.cursor()
    
    cur.execute("""
        SELECT b.id, b.item_id, b.quantity, c.name_ctl, c.price 
        FROM basket b 
        JOIN catalog c ON b.item_id = c.id 
        WHERE b.user_id = ?
    """, (user_id,))
    
    basket_items = cur.fetchall()
    
    if not basket_items:
        markup = types.InlineKeyboardMarkup()
        back_btn = types.InlineKeyboardButton('Back', callback_data='back_to_main')
        markup.add(back_btn)
        bot.send_message(callback.message.chat.id, "Your basket is empty.", reply_markup=markup)
        return

    text = "**Your basket:**\n\n"
    total = 0
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for b_id, item_id, qty, name, price in basket_items:
        subtotal = price * qty
        total += subtotal
        text += f"• {name} x{qty} = {subtotal} ₽\n"
        markup.add(
            types.InlineKeyboardButton(
                f"✗ Remove {name}",
                callback_data=f"delcart_{b_id}"
            )
        )

    text += f"\n**Total: {total} ₽**"
    
    checkout_btn = types.InlineKeyboardButton('✅ Checkout', callback_data='checkout')
    clear_btn = types.InlineKeyboardButton('🗑 Clear basket', callback_data='clear_basket')
    back_btn = types.InlineKeyboardButton('Back', callback_data='back_to_main')
    
    markup.row(checkout_btn)
    markup.row(clear_btn)
    markup.row(back_btn)

    bot.edit_message_text(
        text,
        callback.message.chat.id,
        callback.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )

def delete_from_cart(callback, basket_id):
    conn = sqlite3.connect('bot_database.sql')
    cur = conn.cursor()
    cur.execute("DELETE FROM basket WHERE id = ?", (basket_id,))
    conn.commit()
    cur.close()
    conn.close()
    
    bot.answer_callback_query(callback.id, "Removed from basket")
    show_basket(callback)

def clear_basket(callback):
    user_id = callback.from_user.id
    
    conn = sqlite3.connect('bot_database.sql')
    cur = conn.cursor()
    cur.execute("DELETE FROM basket WHERE user_id = ?", (user_id,))
    conn.commit()
    cur.close()
    conn.close()
    
    bot.answer_callback_query(callback.id, "Basket cleared")
    show_basket(callback)

def show_support(callback):
    markup = types.InlineKeyboardMarkup()
    back_btn = types.InlineKeyboardButton('Back', callback_data='back_to_main')
    markup.add(back_btn)
    
    bot.edit_message_text(
        "🛠 **Support**\n\nFor assistance, contact:\n@bakery_support\n\nPhone: +7 (999) 123-45-67\nEmail: support@bakery.com",
        callback.message.chat.id,
        callback.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )

def edit_menu(callback):
    conn = sqlite3.connect('bot_database.sql')
    cur = conn.cursor()
    cur.execute("SELECT id, name_ctl, price FROM catalog ORDER BY name_ctl")
    items = cur.fetchall()
    cur.close()
    conn.close()

    if not items:
        markup = types.InlineKeyboardMarkup()
        back_btn = types.InlineKeyboardButton('Back', callback_data='back_to_admin')
        markup.add(back_btn)
        bot.send_message(callback.message.chat.id, "Catalog is empty.", reply_markup=markup)
        return

    markup = types.InlineKeyboardMarkup(row_width=1)
    for item in items:
        item_id, name, price = item
        markup.add(
            types.InlineKeyboardButton(
                text=f"{name} — {price} ₽",
                callback_data=f"edititem_{item_id}"
            )
        )
    
    back_btn = types.InlineKeyboardButton('Back', callback_data='back_to_admin')
    markup.add(back_btn)
    
    bot.edit_message_text(
        "Select product to edit:",
        callback.message.chat.id,
        callback.message.message_id,
        reply_markup=markup
    )

def add_position(callback):
    msg = bot.send_message(callback.message.chat.id, "Enter product name:")
    bot.register_next_step_handler(msg, process_add_name)

def process_add_name(message):
    user_states[message.from_user.id] = {'name': message.text}
    msg = bot.send_message(message.chat.id, "Enter price (numbers only):")
    bot.register_next_step_handler(msg, process_add_price)

def process_add_price(message):
    if not message.text.isdigit():
        msg = bot.send_message(message.chat.id, "Please enter numbers only. Enter price:")
        bot.register_next_step_handler(msg, process_add_price)
        return
    
    user_id = message.from_user.id
    if user_id not in user_states:
        user_states[user_id] = {}
    user_states[user_id]['price'] = int(message.text)
    
    msg = bot.send_message(message.chat.id, "Enter description:")
    bot.register_next_step_handler(msg, process_add_description)

def process_add_description(message):
    user_id = message.from_user.id
    if user_id not in user_states:
        user_states[user_id] = {}
    user_states[user_id]['description'] = message.text
    
    msg = bot.send_message(message.chat.id, "Send photo (or send 'skip' to continue without photo):")
    bot.register_next_step_handler(msg, process_add_photo)

def process_add_photo(message):
    user_id = message.from_user.id
    
    if message.text and message.text.lower() == 'skip':
        photo = None
    elif message.photo:
        photo = message.photo[-1].file_id
    else:
        msg = bot.send_message(message.chat.id, "Please send a photo or 'skip':")
        bot.register_next_step_handler(msg, process_add_photo)
        return
    
    conn = sqlite3.connect('bot_database.sql')
    cur = conn.cursor()
    
    cur.execute(
        "INSERT INTO catalog (name_ctl, price, description, photo) VALUES (?, ?, ?, ?)",
        (
            user_states[user_id]['name'],
            user_states[user_id]['price'],
            user_states[user_id]['description'],
            photo
        )
    )
    conn.commit()
    cur.close()
    conn.close()
    
    if user_id in user_states:
        del user_states[user_id]
    
    markup = types.InlineKeyboardMarkup()
    back_btn = types.InlineKeyboardButton('Back to Admin', callback_data='back_to_admin')
    markup.add(back_btn)
    
    bot.send_message(message.chat.id, "✅ Product added successfully!", reply_markup=markup)

def delete_item(callback, item_id):
    conn = sqlite3.connect('bot_database.sql')
    cur = conn.cursor()
    
    cur.execute("SELECT name_ctl FROM catalog WHERE id = ?", (item_id,))
    item_name = cur.fetchone()[0]
    
    cur.execute("DELETE FROM catalog WHERE id = ?", (item_id,))
    cur.execute("DELETE FROM basket WHERE item_id = ?", (item_id,))
    
    conn.commit()
    cur.close()
    conn.close()
    
    bot.answer_callback_query(callback.id, f"Deleted: {item_name}")
    edit_menu(callback)

def edit_item_start(callback, item_id):
    conn = sqlite3.connect('bot_database.sql')
    cur = conn.cursor()
    cur.execute("SELECT name_ctl, price, description FROM catalog WHERE id = ?", (item_id,))
    item = cur.fetchone()
    cur.close()
    conn.close()
    
    if not item:
        bot.answer_callback_query(callback.id, "Product not found.")
        return
    
    name, price, description = item
    user_states[callback.from_user.id] = {'edit_item_id': item_id}
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton('Edit Name', callback_data=f'editfield_name_{item_id}'),
        types.InlineKeyboardButton('Edit Price', callback_data=f'editfield_price_{item_id}')
    )
    markup.add(
        types.InlineKeyboardButton('Edit Description', callback_data=f'editfield_desc_{item_id}'),
        types.InlineKeyboardButton('Edit Photo', callback_data=f'editfield_photo_{item_id}')
    )
    markup.add(types.InlineKeyboardButton('Back', callback_data='edit'))
    
    bot.edit_message_text(
        f"**Edit Product**\n\nName: {name}\nPrice: {price} ₽\nDescription: {description}\n\nSelect what to edit:",
        callback.message.chat.id,
        callback.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('editfield_'))
def handle_edit_field(callback):
    parts = callback.data.split('_')
    field = parts[1]
    item_id = parts[2]
    
    if field == 'name':
        msg = bot.send_message(callback.message.chat.id, "Enter new name:")
        bot.register_next_step_handler(msg, process_edit_name, item_id)
    elif field == 'price':
        msg = bot.send_message(callback.message.chat.id, "Enter new price:")
        bot.register_next_step_handler(msg, process_edit_price, item_id)
    elif field == 'desc':
        msg = bot.send_message(callback.message.chat.id, "Enter new description:")
        bot.register_next_step_handler(msg, process_edit_description, item_id)
    elif field == 'photo':
        msg = bot.send_message(callback.message.chat.id, "Send new photo (or 'skip' to remove):")
        bot.register_next_step_handler(msg, process_edit_photo, item_id)

def process_edit_name(message, item_id):
    conn = sqlite3.connect('bot_database.sql')
    cur = conn.cursor()
    cur.execute("UPDATE catalog SET name_ctl = ? WHERE id = ?", (message.text, item_id))
    conn.commit()
    cur.close()
    conn.close()
    
    bot.send_message(message.chat.id, "✅ Name updated!")
    edit_item_start(message, item_id)

def process_edit_price(message, item_id):
    if not message.text.isdigit():
        msg = bot.send_message(message.chat.id, "Please enter numbers only. Enter price:")
        bot.register_next_step_handler(msg, process_edit_price, item_id)
        return
    
    conn = sqlite3.connect('bot_database.sql')
    cur = conn.cursor()
    cur.execute("UPDATE catalog SET price = ? WHERE id = ?", (int(message.text), item_id))
    conn.commit()
    cur.close()
    conn.close()
    
    bot.send_message(message.chat.id, "✅ Price updated!")
    edit_item_start(message, item_id)

def process_edit_description(message, item_id):
    conn = sqlite3.connect('bot_database.sql')
    cur = conn.cursor()
    cur.execute("UPDATE catalog SET description = ? WHERE id = ?", (message.text, item_id))
    conn.commit()
    cur.close()
    conn.close()
    
    bot.send_message(message.chat.id, "✅ Description updated!")
    edit_item_start(message, item_id)

def process_edit_photo(message, item_id):
    if message.text and message.text.lower() == 'skip':
        photo = None
    elif message.photo:
        photo = message.photo[-1].file_id
    else:
        msg = bot.send_message(message.chat.id, "Please send a photo or 'skip':")
        bot.register_next_step_handler(msg, process_edit_photo, item_id)
        return
    
    conn = sqlite3.connect('bot_database.sql')
    cur = conn.cursor()
    cur.execute("UPDATE catalog SET photo = ? WHERE id = ?", (photo, item_id))
    conn.commit()
    cur.close()
    conn.close()
    
    bot.send_message(message.chat.id, "✅ Photo updated!")
    edit_item_start(message, item_id)

def start_checkout(callback):
    user_id = callback.from_user.id
    
    conn = sqlite3.connect('bot_database.sql')
    cur = conn.cursor()
    cur.execute("""
        SELECT SUM(c.price * b.quantity) 
        FROM basket b 
        JOIN catalog c ON b.item_id = c.id 
        WHERE b.user_id = ?
    """, (user_id,))
    
    total = cur.fetchone()[0]
    
    if not total:
        bot.answer_callback_query(callback.id, "Your basket is empty.")
        return
    
    msg = bot.send_message(callback.message.chat.id, "Please enter your name:")
    bot.register_next_step_handler(msg, process_checkout_name, user_id, total)

def process_checkout_name(message, user_id, total):
    user_states[user_id] = {'name': message.text, 'total': total}
    msg = bot.send_message(message.chat.id, "Please enter your phone number:")
    bot.register_next_step_handler(msg, process_checkout_phone, user_id)

def process_checkout_phone(message, user_id):
    phone = message.text
    name = user_states[user_id]['name']
    total = user_states[user_id]['total']
    
    conn = sqlite3.connect('bot_database.sql')
    cur = conn.cursor()
    
    cur.execute(
        "INSERT INTO orders (user_id, total_price, created, customer_name, customer_phone) VALUES (?, ?, ?, ?, ?)",
        (user_id, total, datetime.now().date(), name, phone)
    )
    
    order_id = cur.lastrowid
    
    cur.execute("SELECT item_id, quantity FROM basket WHERE user_id = ?", (user_id,))
    basket_items = cur.fetchall()
    
    for item_id, quantity in basket_items:
        cur.execute(
            "INSERT INTO order_items (order_id, item_id, quantity) VALUES (?, ?, ?)",
            (order_id, item_id, quantity)
        )
    
    cur.execute("DELETE FROM basket WHERE user_id = ?", (user_id,))
    
    conn.commit()
    cur.close()
    conn.close()
    
    if user_id in user_states:
        del user_states[user_id]
    
    notify_admins(order_id, user_id, total, name, phone)
    
    markup = types.InlineKeyboardMarkup()
    back_btn = types.InlineKeyboardButton('Back to Main', callback_data='back_to_main')
    markup.add(back_btn)
    
    bot.send_message(
        message.chat.id,
        f"✅ Order placed successfully!\n\nOrder #{order_id}\nTotal: {total} ₽\n\nWe will contact you soon.",
        reply_markup=markup
    )

def notify_admins(order_id, user_id, total, name, phone):
    conn = sqlite3.connect('bot_database.sql')
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM admins")
    admins = cur.fetchall()
    cur.close()
    conn.close()
    
    order_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    notification_text = (
        f"🆕 **New Order!**\n\n"
        f"Order ID: #{order_id}\n"
        f"Customer: {name}\n"
        f"Phone: {phone}\n"
        f"User ID: {user_id}\n"
        f"Total: {total} ₽\n"
        f"Time: {order_time}"
    )
    
    for admin in admins:
        try:
            bot.send_message(admin[0], notification_text, parse_mode='Markdown')
        except:
            continue

def view_orders(callback):
    conn = sqlite3.connect('bot_database.sql')
    cur = conn.cursor()
    
    cur.execute("""
        SELECT id, customer_name, total_price, created, status 
        FROM orders 
        ORDER BY created DESC, id DESC 
        LIMIT 20
    """)
    
    orders = cur.fetchall()
    cur.close()
    conn.close()
    
    if not orders:
        markup = types.InlineKeyboardMarkup()
        back_btn = types.InlineKeyboardButton('Back', callback_data='back_to_admin')
        markup.add(back_btn)
        bot.edit_message_text(
            "No orders yet.",
            callback.message.chat.id,
            callback.message.message_id,
            reply_markup=markup
        )
        return
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for order in orders:
        order_id, name, total, created, status = order
        status_icon = {
            'new': '🆕',
            'processing': '🔄',
            'completed': '✅',
            'cancelled': '❌'
        }.get(status, '📝')
        
        markup.add(
            types.InlineKeyboardButton(
                text=f"{status_icon} Order #{order_id} - {name} - {total} ₽",
                callback_data=f"order_{order_id}"
            )
        )
    
    back_btn = types.InlineKeyboardButton('Back', callback_data='back_to_admin')
    markup.add(back_btn)
    
    bot.edit_message_text(
        "**Recent Orders:**",
        callback.message.chat.id,
        callback.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )

def view_order_details(callback, order_id):
    conn = sqlite3.connect('bot_database.sql')
    cur = conn.cursor()
    
    cur.execute("""
        SELECT o.id, o.customer_name, o.customer_phone, o.total_price, o.created, o.status,
               c.name_ctl, oi.quantity, c.price
        FROM orders o
        JOIN order_items oi ON o.id = oi.order_id
        JOIN catalog c ON oi.item_id = c.id
        WHERE o.id = ?
    """, (order_id,))
    
    items = cur.fetchall()
    
    if not items:
        bot.answer_callback_query(callback.id, "Order not found.")
        return
    
    order_info = items[0]
    order_id, name, phone, total, created, status = order_info[:6]
    
    text = f"**Order #{order_id}**\n\n"
    text += f"Customer: {name}\n"
    text += f"Phone: {phone}\n"
    text += f"Date: {created}\n"
    text += f"Status: {status}\n\n"
    text += "**Items:**\n"
    
    for item in items:
        _, _, _, _, _, _, item_name, quantity, price = item
        subtotal = price * quantity
        text += f"• {item_name} x{quantity} = {subtotal} ₽\n"
    
    text += f"\n**Total: {total} ₽**"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    status_buttons = [
        ('🆕 New', f'status_{order_id}_new'),
        ('🔄 Processing', f'status_{order_id}_processing'),
        ('✅ Completed', f'status_{order_id}_completed'),
        ('❌ Cancelled', f'status_{order_id}_cancelled')
    ]
    
    row = []
    for btn_text, btn_data in status_buttons:
        row.append(types.InlineKeyboardButton(btn_text, callback_data=btn_data))
        if len(row) == 2:
            markup.row(*row)
            row = []
    
    back_btn = types.InlineKeyboardButton('Back to Orders', callback_data='back_to_orders')
    markup.row(back_btn)
    
    bot.edit_message_text(
        text,
        callback.message.chat.id,
        callback.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )

def change_order_status(callback, order_id, status):
    conn = sqlite3.connect('bot_database.sql')
    cur = conn.cursor()
    cur.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
    conn.commit()
    cur.close()
    conn.close()
    
    bot.answer_callback_query(callback.id, f"Status changed to {status}")
    view_order_details(callback, order_id)

def send_analytics(callback):
    conn = sqlite3.connect('bot_database.sql')
    cur = conn.cursor()
    
    today = datetime.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    cur.execute("SELECT COUNT(*), COALESCE(SUM(total_price),0) FROM orders WHERE created = ?", (today,))
    day_orders, day_sum = cur.fetchone()
    
    cur.execute("SELECT COUNT(*), COALESCE(SUM(total_price),0) FROM orders WHERE created >= ?", (week_ago,))
    week_orders, week_sum = cur.fetchone()
    
    cur.execute("SELECT COUNT(*), COALESCE(SUM(total_price),0) FROM orders WHERE created >= ?", (month_ago,))
    month_orders, month_sum = cur.fetchone()
    
    cur.execute("SELECT COUNT(*) FROM orders WHERE status = 'new'")
    new_orders = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM orders WHERE status = 'processing'")
    processing_orders = cur.fetchone()[0]
    
    cur.execute('''
        SELECT c.name_ctl, SUM(oi.quantity) as qty
        FROM order_items oi
        JOIN catalog c ON oi.item_id = c.id
        JOIN orders o ON oi.order_id = o.id
        WHERE o.created >= ?
        GROUP BY oi.item_id
        ORDER BY qty DESC
        LIMIT 5
    ''', (month_ago,))
    
    top_items = cur.fetchall()
    
    cur.close()
    conn.close()
    
    text = "📊 **Analytics**\n\n"
    text += f"Today: {day_orders} orders, {day_sum} ₽\n"
    text += f"Last 7 days: {week_orders} orders, {week_sum} ₽\n"
    text += f"Last 30 days: {month_orders} orders, {month_sum} ₽\n\n"
    
    text += "📦 **Order Status**\n"
    text += f"New: {new_orders}\n"
    text += f"Processing: {processing_orders}\n\n"
    
    text += "🏆 **Top Products (30 days)**\n"
    if top_items:
        for i, (name, qty) in enumerate(top_items, 1):
            text += f"{i}. {name} — {qty} pcs\n"
    else:
        text += "No sales data yet.\n"
    
    markup = types.InlineKeyboardMarkup()
    back_btn = types.InlineKeyboardButton('Back', callback_data='back_to_admin')
    markup.add(back_btn)
    
    bot.edit_message_text(
        text,
        callback.message.chat.id,
        callback.message.message_id,
        reply_markup=markup,
        parse_mode='Markdown'
    )

if __name__ == '__main__':
    print("Bot is running...")
    bot.polling(none_stop=True)