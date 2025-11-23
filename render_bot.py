#!/usr/bin/env python3
"""
ТЕЛЕГРАМ БОТ БИТВА КУРЬЕРОВ - ФИНАЛЬНАЯ ВЕРСИЯ
Версия: clean_messages_v3.0
"""

import telebot
import flask
import os
import sqlite3
from datetime import datetime

# Конфигурация
BOT_TOKEN = "8542303018:AAF5Pqisa1ZfqHxibGx3zQV06verk2D4M6Y"
ADMIN_ID = 5982747122

# Flask приложение
app = flask.Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

# Словарь состояний пользователей
user_states = {}

# База данных
def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            full_name TEXT,
            age TEXT,
            phone TEXT,
            email TEXT,
            city TEXT,
            video_message TEXT,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Инициализация БД
init_db()

# ОБРАБОТЧИКИ КОМАНД (ПРИОРИТЕТ ВЫСОКИЙ)

@bot.message_handler(commands=['start'])
def handle_start(message):
    """Команда /start"""
    
    # Проверяем, есть ли уже заявка от пользователя
    try:
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM applications WHERE user_id = ?', (message.from_user.id,))
        existing_app = cursor.fetchone()
        conn.close()
        
        if existing_app:
            # Уже есть заявка - показываем статус
            bot.reply_to(message, """🚚 **Добро пожаловать на БИТВУ КУРЬЕРОВ!**

🎯 **У вас уже есть поданая заявка!**

📋 **Ваша заявка находится на рассмотрении.**

📖 **Доступные команды:**
/status - статус вашей заявки

💡 **Хотите узнать статус заявки?** - используйте /status""", parse_mode='Markdown')
            return
    
    except Exception as e:
        # В случае ошибки продолжаем как обычно
        pass
    
    # Если заявки нет, показываем приветствие для новых пользователей
    welcome_text = """🚚 **Добро пожаловать на БИТВУ КУРЬЕРОВ!**

С 15 декабря 2025г. по 15 января 2026г. 100 участников со всей России будут сражаться за звание Чемпиона в сфере курьерской доставки и приз в размере 1 000 000рублей💥

Участникам предстоит испытать множество эмоций, проверить себя на прочность, научиться работать в команде или наоборот, доказать всем что и один в поле - воин и даже обрести популярность😎

Шоу «БИТВА КУРЬЕРОВ» это real-life формат, без прекрас и навязанного luxury, ежедневные трансляции на RuTube, YouTube и VK Видео.

Участие в проекте достойно оплачивается!
+ Каждый участник проекта, гарантировано получит мини-приз, стоимостью 50.000 рублей, и возможность получить 1 из 5 суперпризов:
🏆 1.000.000 рублей
2️⃣ 500.000 рублей
3️⃣ 400.000 рублей
4️⃣ 300.000 рублей
5️⃣ 200.000 рублей

Залетай в проект, не упускай возможности🦾

📖 **Доступные команды:**
/status - статус вашей заявки"""
    
    # Создаем inline keyboard с кнопкой "ПОГНАЛИ"
    markup = telebot.types.InlineKeyboardMarkup()
    start_button = telebot.types.InlineKeyboardButton(
        text="🚀 ПОГНАЛИ!", 
        callback_data="start_application"
    )
    markup.add(start_button)
    
    bot.reply_to(message, welcome_text, parse_mode='Markdown', reply_markup=markup)

@bot.message_handler(commands=['status'])
def handle_status(message):
    """Проверка статуса заявки"""
    try:
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM applications WHERE user_id = ?', (message.from_user.id,))
        app_record = cursor.fetchone()
        conn.close()
        
        if app_record:
            status_text = f"""📋 **Статус вашей заявки:**

👤 ФИО: {app_record[2]}
📅 Возраст: {app_record[3]}
📱 Телефон: {app_record[4]}
📧 Email: {app_record[5]}
📍 Город: {app_record[6]}
📊 Статус: {app_record[7]}

🕐 Подана: {app_record[8]}

💡 Статус "pending" означает, что ваша заявка находится на рассмотрении."""
        else:
            status_text = """❌ **Заявка не найдена**

Вы еще не подавали заявку. Нажмите /start чтобы подать заявку."""
        
        bot.reply_to(message, status_text, parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка при получении статуса: {str(e)}")

@bot.message_handler(commands=['cancel'])
def handle_cancel_command(message):
    """Обработчик команды /cancel - отмена подачи заявки"""
    user_id = message.from_user.id
    
    if user_id in user_states:
        del user_states[user_id]
        bot.reply_to(message, "✅ **Подача заявки отменена**\n\nЧтобы начать заново, нажмите /start")
    else:
        bot.reply_to(message, "ℹ️ Вы не подаете заявку в данный момент.")

@bot.message_handler(commands=['admin'])
def handle_admin_command(message):
    """Обработчик команды /admin (только для админа)"""
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ У вас нет прав для доступа к админ-панели")
        return
    
    try:
        # Получаем статистику из БД
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM applications')
        total_apps = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM applications WHERE status = 'pending'")
        pending_apps = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM applications WHERE status = 'approved'")
        approved_apps = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM applications WHERE status = 'rejected'")
        rejected_apps = cursor.fetchone()[0]
        
        cursor.execute('SELECT * FROM applications ORDER BY created_at DESC LIMIT 5')
        recent_apps = cursor.fetchall()
        
        conn.close()
        
        # Формируем отчет
        admin_text = f"""👨‍💼 **ПАНЕЛЬ АДМИНИСТРАТОРА**

📊 **Статистика заявок:**
• Всего подано: {total_apps}
• На рассмотрении: {pending_apps}
• Одобрено: {approved_apps}
• Отклонено: {rejected_apps}

📋 **Последние 5 заявок:**"""
        
        for app in recent_apps:
            admin_text += f"""
• {app[2]} - {app[5]} - {app[6]} ({app[7]})"""
        
        bot.reply_to(message, admin_text, parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка при получении статистики: {str(e)}")

# ОБРАБОТЧИК CALLBACK QUERY (инлайн кнопки)
@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    """Обработчик callback запросов от inline кнопок"""
    if call.data == "start_application":
        user_id = call.from_user.id
        
        # Проверяем, есть ли уже заявка от пользователя
        try:
            conn = sqlite3.connect('bot.db')
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM applications WHERE user_id = ?', (user_id,))
            existing_app = cursor.fetchone()
            conn.close()
            
            if existing_app:
                bot.answer_callback_query(call.id)
                bot.send_message(call.message.chat.id, """❌ **У вас уже есть поданая заявка!**

📋 **Ваша заявка находится на рассмотрении.**

💡 **Хотите узнать статус заявки?** - используйте /status""", parse_mode='Markdown')
                return
                
        except Exception as e:
            # В случае ошибки продолжаем как обычно
            pass
        
        # Если заявки нет, начинаем процесс подачи заявки
        user_states[user_id] = {
            "state": "waiting_full_name",
            "data": {}
        }
        
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "📝 **Шаг 1/6: ФИО**\n\nВведите ваше ФИО:")

# ОБРАБОТЧИК ВИДЕОСООБЩЕНИЙ
@bot.message_handler(content_types=['video'])
def handle_video_input(message):
    """Обработчик видеосообщений"""
    user_id = message.from_user.id
    
    if user_id not in user_states:
        bot.reply_to(message, "❌ Начните подачу заявки с команды /start")
        return
    
    user_state = user_states[user_id]
    
    if user_state["state"] != "waiting_video":
        bot.reply_to(message, "❌ Видеосообщение не требуется на данном этапе. Сначала заполните анкету полностью.")
        return
    
    # Проверяем длительность видео
    video_duration = message.video.duration
    
    if video_duration > 60:
        bot.reply_to(message, f"❌ Видео слишком длинное ({video_duration} сек). Максимальная длительность - 60 секунд.")
        return
    
    # Сохраняем данные в БД
    user_data = user_state["data"]
    
    try:
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        
        # Проверяем, есть ли уже заявка от пользователя
        cursor.execute('SELECT id FROM applications WHERE user_id = ?', (user_id,))
        existing_app = cursor.fetchone()
        
        if existing_app:
            # Обновляем существующую заявку
            cursor.execute('''
                UPDATE applications 
                SET full_name = ?, age = ?, phone = ?, email = ?, city = ?, video_message = ?, status = 'pending'
                WHERE user_id = ?
            ''', (
                user_data["full_name"],
                user_data["age"],
                user_data["phone"],
                user_data["email"],
                user_data["city"],
                f"video_file_id: {message.video.file_id}",
                user_id
            ))
        else:
            # Создаем новую заявку
            cursor.execute('''
                INSERT INTO applications (user_id, full_name, age, phone, email, city, video_message, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
            ''', (
                user_id,
                user_data["full_name"],
                user_data["age"],
                user_data["phone"],
                user_data["email"],
                user_data["city"],
                f"video_file_id: {message.video.file_id}"
            ))
        
        # Сохраняем пользователя в таблицу users
        cursor.execute('''
            INSERT OR REPLACE INTO users (id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        ''', (
            user_id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name
        ))
        
        conn.commit()
        conn.close()
        
        # Очищаем состояние пользователя
        del user_states[user_id]
        
        # Отправляем сообщение об успешной подаче
        success_text = f"""✅ **Заявка подана успешно!**

📋 **Ваши данные:**
👤 ФИО: {user_data["full_name"]}
📅 Возраст: {user_data["age"]}
📱 Телефон: {user_data["phone"]}
📧 Email: {user_data["email"]}
📍 Город: {user_data["city"]}

🎥 **Видеосообщение принято** ({video_duration} сек)

⏳ **Следующие шаги:**
• Ваша заявка направлена на рассмотрение
• Можете проверить статус командой /status

🚀 **Удачи в Битве Курьеров!**"""
        
        bot.reply_to(message, success_text, parse_mode='Markdown')
        
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка при сохранении заявки: {str(e)}")

# ОБРАБОТЧИК ТЕКСТОВЫХ СООБЩЕНИЙ (НИЗКИЙ ПРИОРИТЕТ)
@bot.message_handler(content_types=['text'])
def handle_text_input(message):
    """Обработчик текстовых сообщений"""
    
    # Игнорируем команды - они обрабатываются выше
    if message.text.startswith('/'):
        return
    
    user_id = message.from_user.id
    
    if user_id not in user_states:
        bot.reply_to(message, "❌ Начните подачу заявки с команды /start")
        return
    
    user_state = user_states[user_id]
    user_data = user_state["data"]
    state = user_state["state"]
    
    if state == "waiting_full_name":
        user_data["full_name"] = message.text
        user_state["state"] = "waiting_age"
        bot.reply_to(message, "📅 **Шаг 2/6: Возраст**\n\nСколько вам лет? (от 16 до 80)")
        
    elif state == "waiting_age":
        try:
            age = int(message.text)
            if age < 16 or age > 80:
                bot.reply_to(message, "❌ Возраст должен быть от 16 до 80 лет.")
                return
            user_data["age"] = age
            user_state["state"] = "waiting_phone"
            bot.reply_to(message, "📱 **Шаг 3/6: Телефон**\n\nВведите ваш номер телефона:")
        except ValueError:
            bot.reply_to(message, "❌ Введите корректный возраст (число).")
            
    elif state == "waiting_phone":
        user_data["phone"] = message.text
        user_state["state"] = "waiting_email"
        bot.reply_to(message, "📧 **Шаг 4/6: Email**\n\nВведите ваш email адрес:")
        
    elif state == "waiting_email":
        email = message.text
        if "@" not in email or "." not in email:
            bot.reply_to(message, "❌ Введите корректный email адрес.")
            return
        user_data["email"] = email
        user_state["state"] = "waiting_city"
        bot.reply_to(message, "📍 **Шаг 5/6: Город**\n\nОткуда Вы (город)?")
        
    elif state == "waiting_city":
        user_data["city"] = message.text
        user_state["state"] = "waiting_video"
        
        # Создаем сообщение для подтверждения
        confirm_text = f"""📋 **Шаг 6/6: Видеосообщение**

🎥 **Перед подачей заявки**

📎 Чтобы прикрепить видео нажмите на скрепку📎 и загрузите или снимите видео, видео-кружок не учитывается ❌

Отправьте короткое видеосообщение (до 30 сек), расскажите о себе и почему вам интересен этот проект. Данное видео предназначается для отборочного жюри и не будет транслироваться в открытых источниках

📎 После отправки видео ваша заявка будет подана автоматически!"""
        
        bot.reply_to(message, confirm_text, parse_mode='Markdown')
        
    elif state == "waiting_video":
        bot.reply_to(message, "❌ Необходимо отправить видеосообщение! Нажмите на иконку микрофона и сделайте короткое видео.")

# Flask маршруты

@app.route('/webhook', methods=['POST'])
def webhook():
    """Webhook для получения обновлений от Telegram"""
    json_string = flask.request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return 'OK'

@app.route('/health')
def health_check():
    """Проверка состояния бота"""
    return {
        'status': 'healthy',
        'version': 'clean_messages_v3.0',
        'uptime': datetime.now().isoformat()
    }

if __name__ == '__main__':
    # Устанавливаем webhook
    bot.remove_webhook()
    bot.set_webhook(url='https://courier-battle-bot.onrender.com/webhook')
    
    # Запускаем Flask сервер
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False)