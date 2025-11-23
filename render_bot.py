#!/usr/bin/env python3
"""
ТЕЛЕГРАМ БОТ БИТВА КУРЬЕРОВ - Исправленная версия на основе работающего теста
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

# Инициализация БД при запуске
init_db()

@bot.message_handler(commands=['start'])
def handle_start(message):
    """Команда /start"""
    welcome_text = """🚚 **Добро пожаловать в Битву Курьеров!**

📋 **Что нужно сделать:**
1. Нажмите "Подать заявку" 
2. Заполните все поля анкеты
3. Отправьте заявку

✅ **Требования:**
• Опыт работы курьером от 6 месяцев
• Собственный транспорт
• Готовность работать по гибкому графику

💰 **Преимущества:**
• Высокий заработок
• Гибкий график
• Дружная команда

📞 **Контакты:**
@duckside14 - менеджер по персоналу

📖 **Доступные команды:**
/start - главное меню
/status - статус вашей заявки

👨‍💼 **Админ-команды:**
/admin - панель администратора"""
    
    bot.reply_to(message, welcome_text, parse_mode='Markdown')

@bot.message_handler(commands=['status'])
def handle_status(message):
    """Проверка статуса заявки"""
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
        status_text = "❌ **Заявка не найдена**\n\nВы еще не подавали заявку. Нажмите /start чтобы подать заявку."
    
    bot.reply_to(message, status_text, parse_mode='Markdown')

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
        'version': 'fixed_full_1.0',
        'timestamp': datetime.now().isoformat()
    }

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f"Запуск сервера на порту {port}")
    app.run(host='0.0.0.0', port=port, debug=False)