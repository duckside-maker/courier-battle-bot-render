#!/usr/bin/env python3
"""
ТЕЛЕГРАМ БОТ БИТВА КУРЬЕРОВ - ИСПРАВЛЕННАЯ ВЕРСИЯ С ПРАВИЛЬНОЙ ЛОГИКОЙ КОМАНД
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
            phone TEXT,
            experience TEXT,
            transport TEXT,
            city TEXT,
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
    welcome_text = """🚚 **Добро пожаловать в Битву Курьеров!**

📋 **Что нужно сделать:**
• Подать заявку для участия в кастинге курьеров
• Указать ваш опыт работы и транспорт
• Дождаться звонка менеджера

📝 **Процесс подачи заявки займет 2-3 минуты**

📖 **Доступные команды:**
/start - главное меню
/status - статус вашей заявки
/cancel - отменить подачу заявки

👨‍💼 **Админ-команды:**
/admin - панель администратора"""
    
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
📱 Телефон: {app_record[3]}
🚗 Опыт: {app_record[4]}
🛺 Транспорт: {app_record[5]}
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
• {app[2]} - {app[5]} ({app[7]})"""
        
        bot.reply_to(message, admin_text, parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка при получении статистики: {str(e)}")

# ОБРАБОТЧИК CALLBACK QUERY (инлайн кнопки)
@bot.callback_query_handler(func=lambda call: True)
def handle_callback_query(call):
    """Обработчик callback запросов от inline кнопок"""
    if call.data == "start_application":
        # Начинаем процесс подачи заявки
        user_id = call.from_user.id
        user_states[user_id] = {
            "state": "waiting_full_name",
            "data": {}
        }
        
        bot.answer_callback_query(call.id)
        bot.send_message(call.message.chat.id, "📝 **Шаг 1/6: Ваше полное имя**\n\nВведите ваше полное имя:")

# ОБРАБОТЧИК ТЕКСТОВЫХ СООБЩЕНИЙ (ПРИОРИТЕТ НИЗКИЙ)
@bot.message_handler(content_types=['text'])
def handle_text_input(message):
    """Обработчик текстовых сообщений для подачи заявки"""
    user_id = message.from_user.id
    
    # КРИТИЧЕСКИ ВАЖНО: Проверяем, если это команда - сразу выходим!
    if message.text.startswith('/'):
        return
    
    # Если пользователь не подает заявку, игнорируем
    if user_id not in user_states:
        return
    
    user_state = user_states[user_id]
    state = user_state["state"]
    user_data = user_state["data"]
    
    # Обрабатываем каждый шаг анкеты
    try:
        if state == "waiting_full_name":
            user_data["full_name"] = message.text
            user_state["state"] = "waiting_phone"
            bot.reply_to(message, "📱 **Шаг 2/6: Ваш номер телефона**\n\nВведите номер телефона:")
            
        elif state == "waiting_phone":
            user_data["phone"] = message.text
            user_state["state"] = "waiting_experience"
            bot.reply_to(message, "🚗 **Шаг 3/6: Опыт работы**\n\nОпишите ваш опыт работы курьером (в годах и месяцах):")
            
        elif state == "waiting_experience":
            user_data["experience"] = message.text
            user_state["state"] = "waiting_transport"
            bot.reply_to(message, "🛺 **Шаг 4/6: Транспорт**\n\nКаким транспортом пользуетесь? (пешком, велосипед, автомобиль, скутер и т.д.):")
            
        elif state == "waiting_transport":
            user_data["transport"] = message.text
            user_state["state"] = "waiting_city"
            bot.reply_to(message, "📍 **Шаг 5/6: Город**\n\nВ каком городе планируете работать?")
            
        elif state == "waiting_city":
            user_data["city"] = message.text
            user_state["state"] = "waiting_confirmation"
            
            # Создаем сообщение для подтверждения
            confirm_text = f"""📋 **Шаг 6/6: Проверьте данные**

👤 **ФИО:** {user_data["full_name"]}
📱 **Телефон:** {user_data["phone"]}
🚗 **Опыт:** {user_data["experience"]}
🛺 **Транспорт:** {user_data["transport"]}
📍 **Город:** {user_data["city"]}

Все данные верны? Отправьте "ДА" чтобы подать заявку, или "НЕТ" чтобы начать заново."""
            
            bot.reply_to(message, confirm_text, parse_mode='Markdown')
            
        elif state == "waiting_confirmation":
            if message.text.upper() == "ДА":
                # Сохраняем заявку в БД
                try:
                    conn = sqlite3.connect('bot.db')
                    cursor = conn.cursor()
                    
                    # Добавляем пользователя если его нет
                    cursor.execute('''
                        INSERT OR IGNORE INTO users (id, username, first_name, last_name)
                        VALUES (?, ?, ?, ?)
                    ''', (user_id, message.from_user.username, message.from_user.first_name, message.from_user.last_name))
                    
                    # Добавляем заявку
                    cursor.execute('''
                        INSERT INTO applications (user_id, full_name, phone, experience, transport, city, status)
                        VALUES (?, ?, ?, ?, ?, ?, 'pending')
                    ''', (user_id, user_data["full_name"], user_data["phone"], 
                          user_data["experience"], user_data["transport"], user_data["city"]))
                    
                    conn.commit()
                    conn.close()
                    
                    # Успешное завершение
                    success_text = f"""🎉 **Заявка подана успешно!**

Спасибо, {user_data["full_name"]}! Ваша заявка принята и находится на рассмотрении.

📱 Менеджер свяжется с вами по номеру: {user_data["phone"]}

📋 Статус заявки можно проверить командой /status"""
                    
                    bot.reply_to(message, success_text, parse_mode='Markdown')
                    
                    # Удаляем состояние пользователя
                    del user_states[user_id]
                    
                except Exception as e:
                    bot.reply_to(message, f"❌ Ошибка при сохранении заявки: {str(e)}")
                    
            elif message.text.upper() == "НЕТ":
                # Сбрасываем заявку
                user_states[user_id]["state"] = "waiting_full_name"
                user_states[user_id]["data"] = {}
                bot.reply_to(message, "❌ Заявка сброшена. \n\n📝 Введите ваше полное имя:")
            else:
                bot.reply_to(message, "❓ Пожалуйста, ответьте ДА или НЕТ")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка при обработке: {str(e)}")

# ВЕБХУК
@app.route('/webhook', methods=['POST'])
def webhook():
    """Вебхук для получения обновлений от Telegram"""
    try:
        if flask.request.headers.get('content-type') == 'application/json':
            json_string = flask.request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return '', 200
        else:
            return 'invalid content type', 403
    except Exception as e:
        print(f"Webhook error: {str(e)}")
        return 'Error', 500

@app.route('/health', methods=['GET'])
def health():
    """Проверка состояния"""
    return {
        'status': 'ok',
        'bot': 'running',
        'version': 'commands_fixed_1.0',
        'timestamp': datetime.now().isoformat()
    }

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f"Запуск сервера на порту {port}")
    app.run(host='0.0.0.0', port=port, debug=False)