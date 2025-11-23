#!/usr/bin/env python3
"""
ТЕЛЕГРАМ БОТ БИТВА КУРЬЕРОВ - Render Edition
Версия для развертывания на Render.com
"""

import os
import sys
import sqlite3
import telebot
from telebot import types
import flask
from datetime import datetime
import io
import json

# Настройка Flask для вебхука
app = flask.Flask(__name__)
webhook_url = ""

# Конфигурация бота
BOT_TOKEN = "8542303018:AAF5Pqisa1ZfqHxibGx3zQV06verk2D4M6Y"
ADMIN_ID = 5982747122

# Создание экземпляра бота
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

# Состояния пользователей (простая FSM)
user_states = {}

# База данных
DATABASE = "courier_battle_bot.db"

def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Таблица заявок на участие
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            full_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            experience TEXT,
            city TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица логов действий админа
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            target_user_id INTEGER,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

@bot.message_handler(commands=['start'])
def handle_start(message):
    """Обработчик команды /start"""
    welcome_text = """
🚚 **Добро пожаловать в Битву Курьеров!**

📋 **Что нужно сделать:**
1. Нажмите "Подать заявку" 
2. Заполните все поля анкеты
3. Отправьте заявку

✅ **Требования:**
• Опыт работы курьером от 6 месяцев
• Собственный транспорт
• Готовность к соревнованию

👤 **Для участия необходимы:**
• ФИО
• Номер телефона  
• Город работы
• Описание опыта

💬 **Команды:**
/help - справка по боту
/status - проверить статус заявки
    """
    
    markup = types.InlineKeyboardMarkup()
    apply_btn = types.InlineKeyboardButton("📝 Подать заявку", callback_data="apply")
    status_btn = types.InlineKeyboardButton("📊 Мой статус", callback_data="status")
    markup.add(apply_btn, status_btn)
    
    bot.reply_to(message, welcome_text, reply_markup=markup, parse_mode='Markdown')

@bot.message_handler(commands=['help'])
def handle_help(message):
    """Обработчик команды /help"""
    help_text = """
ℹ️ **СПРАВКА ПО БОТУ**

📋 **Как подать заявку:**
1. Нажмите "Подать заявку"
2. Заполните анкету
3. Дождитесь обработки

🔍 **Статусы заявки:**
• ⏳ pending - заявка на рассмотрении
• ✅ approved - заявка одобрена
• ❌ rejected - заявка отклонена

📱 **Команды:**
/start - главное меню
/help - эта справка  
/status - статус вашей заявки

👨‍💼 **Админ-команды:**
/admin - панель администратора
    """
    bot.reply_to(message, help_text, parse_mode='Markdown')

@bot.message_handler(commands=['status'])
def handle_status(message):
    """Проверка статуса заявки"""
    user_id = message.from_user.id
    
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT status, created_at FROM applications WHERE user_id = ? ORDER BY created_at DESC LIMIT 1", (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        status, created_at = result
        status_emoji = {
            'pending': '⏳',
            'approved': '✅', 
            'rejected': '❌'
        }
        emoji = status_emoji.get(status, '❓')
        
        status_text = f"""
📊 **Статус вашей заявки:**

{emoji} **Статус:** {status.upper()}
📅 **Дата подачи:** {created_at}
        """
    else:
        status_text = """
❌ **Заявка не найдена**

Вы ещё не подавали заявку на участие.
Нажмите /start чтобы подать заявку.
        """
    
    bot.reply_to(message, status_text, parse_mode='Markdown')

@bot.message_handler(commands=['admin'])
def handle_admin_command(message):
    """Обработчик команды /admin (только для админа)"""
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ У вас нет прав для доступа к админ-панели")
        return
    
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("📋 Все заявки", callback_data="admin_all"),
        types.InlineKeyboardButton("⏳ На рассмотрении", callback_data="admin_pending")
    )
    markup.row(
        types.InlineKeyboardButton("✅ Одобренные", callback_data="admin_approved"),
        types.InlineKeyboardButton("❌ Отклонённые", callback_data="admin_rejected")
    )
    
    bot.reply_to(message, "👨‍💼 **АДМИН-ПАНЕЛЬ**\n\nВыберите категорию:", reply_markup=markup, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    """Обработчик inline кнопок"""
    bot.answer_callback_query(call.id)
    
    if call.data == "apply":
        handle_application_step1(call.message)
    elif call.data == "status":
        # Пересылаем команду /status
        handle_status(call.message)
    elif call.data.startswith("admin_"):
        handle_admin_callback(call)
    elif call.data.startswith("approve_"):
        approve_application(call.data.split("_")[1], call.from_user.id, call.message)
    elif call.data.startswith("reject_"):
        reject_application(call.data.split("_")[1], call.from_user.id, call.message)

def handle_application_step1(message):
    """Первый шаг заявки - ФИО"""
    user_states[message.from_user.id] = {'step': 'full_name'}
    
    bot.reply_to(message, """
📝 **ШАГ 1/4 - ЛИЧНЫЕ ДАННЫЕ**

👤 **Введите ваше полное имя:**
(Фамилия, имя, отчество)
    """, parse_mode='Markdown')

@bot.message_handler(func=lambda message: message.from_user.id in user_states and user_states[message.from_user.id]['step'] == 'full_name')
def handle_full_name(message):
    """Обработка ФИО"""
    full_name = message.text.strip()
    
    if len(full_name) < 3:
        bot.reply_to(message, "❌ Имя слишком короткое. Введите полное имя:")
        return
    
    user_states[message.from_user.id]['full_name'] = full_name
    user_states[message.from_user.id]['step'] = 'phone'
    
    bot.reply_to(message, f"✅ **Записано:** {full_name}\n\n📞 **ШАГ 2/4 - ТЕЛЕФОН**\n\nВведите ваш номер телефона:")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and user_states[message.from_user.id]['step'] == 'phone')
def handle_phone(message):
    """Обработка телефона"""
    phone = message.text.strip()
    
    # Простая валидация телефона
    if not any(char.isdigit() for char in phone) or len(phone) < 10:
        bot.reply_to(message, "❌ Неверный номер телефона. Введите корректный номер:")
        return
    
    user_states[message.from_user.id]['phone'] = phone
    user_states[message.from_user.id]['step'] = 'city'
    
    bot.reply_to(message, f"✅ **Записано:** {phone}\n\n🏙️ **ШАГ 3/4 - ГОРОД**\n\nВведите город, где планируете работать:")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and user_states[message.from_user.id]['step'] == 'city')
def handle_city(message):
    """Обработка города"""
    city = message.text.strip()
    
    if len(city) < 2:
        bot.reply_to(message, "❌ Название города слишком короткое. Введите корректный город:")
        return
    
    user_states[message.from_user.id]['city'] = city
    user_states[message.from_user.id]['step'] = 'experience'
    
    bot.reply_to(message, f"✅ **Записано:** {city}\n\n💼 **ШАГ 4/4 - ОПЫТ**\n\nОпишите ваш опыт работы курьером:\n(минимум 50 символов)")

@bot.message_handler(func=lambda message: message.from_user.id in user_states and user_states[message.from_user.id]['step'] == 'experience')
def handle_experience(message):
    """Обработка опыта и сохранение заявки"""
    experience = message.text.strip()
    
    if len(experience) < 50:
        bot.reply_to(message, "❌ Описание слишком короткое. Опишите подробнее ваш опыт (минимум 50 символов):")
        return
    
    user_id = message.from_user.id
    username = message.from_user.username or ""
    full_name = user_states[user_id]['full_name']
    phone = user_states[user_id]['phone']
    city = user_states[user_id]['city']
    
    # Сохраняем в БД
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    # Проверяем, есть ли уже заявка
    cursor.execute("SELECT id FROM applications WHERE user_id = ?", (user_id,))
    existing = cursor.fetchone()
    
    if existing:
        cursor.execute("""
            UPDATE applications 
            SET username = ?, full_name = ?, phone = ?, experience = ?, city = ?, status = 'pending'
            WHERE user_id = ?
        """, (username, full_name, phone, experience, city, user_id))
    else:
        cursor.execute("""
            INSERT INTO applications (user_id, username, full_name, phone, experience, city, status)
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
        """, (user_id, username, full_name, phone, experience, city))
    
    conn.commit()
    conn.close()
    
    # Удаляем состояние пользователя
    del user_states[user_id]
    
    bot.reply_to(message, f"""
🎉 **ЗАЯВКА ПОДАНА УСПЕШНО!**

✅ **Данные сохранены:**
👤 ФИО: {full_name}
📞 Телефон: {phone}
🏙️ Город: {city}
💼 Опыт: {experience[:100]}...

⏳ Ваша заявка отправлена на рассмотрение.
📊 Проверить статус: /status

Спасибо за участие в Битве Курьеров!
    """, parse_mode='Markdown')

def handle_admin_callback(call):
    """Обработка админ-колбэков"""
    if call.from_user.id != ADMIN_ID:
        return
    
    if call.data == "admin_all":
        show_admin_applications(call.message, "all")
    elif call.data == "admin_pending":
        show_admin_applications(call.message, "pending")
    elif call.data == "admin_approved":
        show_admin_applications(call.message, "approved")
    elif call.data == "admin_rejected":
        show_admin_applications(call.message, "rejected")

def show_admin_applications(message, status_filter):
    """Показ заявок в админке"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    if status_filter == "all":
        cursor.execute("""
            SELECT id, user_id, full_name, phone, city, status, created_at 
            FROM applications ORDER BY created_at DESC
        """)
    else:
        cursor.execute("""
            SELECT id, user_id, full_name, phone, city, status, created_at 
            FROM applications WHERE status = ? ORDER BY created_at DESC
        """, (status_filter,))
    
    applications = cursor.fetchall()
    conn.close()
    
    if not applications:
        bot.edit_message_text(
            f"📋 **ЗАЯВКИ - {status_filter.upper()}**\n\n❌ Заявок не найдено",
            message.chat.id, message.message_id,
            parse_mode='Markdown'
        )
        return
    
    text = f"📋 **ЗАЯВКИ - {status_filter.upper()}**\n\n"
    
    for app in applications[:10]:  # Показываем первые 10
        app_id, user_id, full_name, phone, city, status, created_at = app
        
        status_emoji = {
            'pending': '⏳',
            'approved': '✅',
            'rejected': '❌'
        }
        emoji = status_emoji.get(status, '❓')
        
        text += f"""
**{app_id}.** {emoji} {full_name}
👤 ID: `{user_id}`
📞 {phone}
🏙️ {city}
📅 {created_at}
        """
    
    markup = types.InlineKeyboardMarkup()
    
    # Добавляем кнопки для управления каждой заявкой
    for app in applications[:5]:  # Только для первых 5
        app_id = app[0]
        markup.row(
            types.InlineKeyboardButton(f"✅ {app_id}", callback_data=f"approve_{app_id}"),
            types.InlineKeyboardButton(f"❌ {app_id}", callback_data=f"reject_{app_id}")
        )
    
    bot.edit_message_text(text, message.chat.id, message.message_id, reply_markup=markup, parse_mode='Markdown')

def approve_application(app_id, admin_id, message):
    """Одобрение заявки"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute("UPDATE applications SET status = 'approved' WHERE id = ?", (app_id,))
    
    # Получаем данные заявки для уведомления
    cursor.execute("SELECT user_id, full_name FROM applications WHERE id = ?", (app_id,))
    app_data = cursor.fetchone()
    
    conn.commit()
    conn.close()
    
    # Логируем действие админа
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO admin_logs (admin_id, action, target_user_id, details)
        VALUES (?, 'approved', ?, ?)
    """, (admin_id, app_data[0] if app_data else 0, f"Application {app_id} approved"))
    conn.commit()
    conn.close()
    
    if app_data:
        user_id, full_name = app_data
        try:
            bot.send_message(user_id, f"""
✅ **ВАША ЗАЯВКА ОДОБРЕНА!**

Поздравляем, {full_name}!
Ваша заявка на участие в Битве Курьеров одобрена.

🏆 Скоро с вами свяжутся для дальнейших инструкций.

Удачи в соревновании!
            """, parse_mode='Markdown')
        except:
            pass  # Пользователь мог заблокировать бота
    
    bot.answer_callback_query(message.id, f"Заявка {app_id} одобрена ✅")
    
    # Обновляем список
    show_admin_applications(message, "pending")

def reject_application(app_id, admin_id, message):
    """Отклонение заявки"""
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    cursor.execute("UPDATE applications SET status = 'rejected' WHERE id = ?", (app_id,))
    
    # Получаем данные заявки
    cursor.execute("SELECT user_id, full_name FROM applications WHERE id = ?", (app_id,))
    app_data = cursor.fetchone()
    
    conn.commit()
    conn.close()
    
    # Логируем действие админа
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO admin_logs (admin_id, action, target_user_id, details)
        VALUES (?, 'rejected', ?, ?)
    """, (admin_id, app_data[0] if app_data else 0, f"Application {app_id} rejected"))
    conn.commit()
    conn.close()
    
    if app_data:
        user_id, full_name = app_data
        try:
            bot.send_message(user_id, f"""
❌ **ЗАЯВКА ОТКЛОНЕНА**

К сожалению, {full_name}, ваша заявка на участие в Битве Курьеров отклонена.

💡 **Возможные причины:**
• Недостаточный опыт работы
• Несоответствие требованиям
• Технические ограничения

Попробуйте подать заявку позже.
Удачи!
            """, parse_mode='Markdown')
        except:
            pass
    
    bot.answer_callback_query(message.id, f"Заявка {app_id} отклонена ❌")
    
    # Обновляем список
    show_admin_applications(message, "pending")

@app.route('/webhook', methods=['POST'])
def webhook():
    """Вебхук для получения обновлений от Telegram"""
    if flask.request.headers.get('content-type') == 'application/json':
        json_string = flask.request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return ''
    else:
        flask.abort(403)

@app.route('/health', methods=['GET'])
def health():
    """Проверка состояния сервера"""
    return {
        'status': 'ok',
        'bot': 'running',
        'version': 'render_1.0',
        'timestamp': datetime.now().isoformat()
    }

def main():
    """Основная функция запуска бота"""
    # Инициализация БД
    init_db()
    
    # Удаляем вебхук если он был установлен
    bot.remove_webhook()
    
    # Проверяем переменные окружения
    webhook_url = os.environ.get('WEBHOOK_URL', '')
    if webhook_url:
        # Устанавливаем вебхук
        bot.set_webhook(url=webhook_url)
        print(f"✅ Webhook установлен: {webhook_url}")
    else:
        print("⚠️ WEBHOOK_URL не установлен")
    
    # Запуск Flask приложения
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
    
    print("🚀 Бот запущен и готов к работе!")

if __name__ == '__main__':
    main()