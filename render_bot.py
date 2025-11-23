#!/usr/bin/env python3
"""
Минимальная версия бота для диагностики
"""

import telebot
import flask
import os

# Конфигурация
BOT_TOKEN = "8542303018:AAF5Pqisa1ZfqHxibGx3zQV06verk2D4M6Y"

# Flask приложение
app = flask.Flask(__name__)
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

@bot.message_handler(commands=['start'])
def handle_start(message):
    """Простая команда /start"""
    bot.reply_to(message, "✅ Бот работает! Привет!")

@app.route('/webhook', methods=['POST'])
def webhook():
    """Простой webhook для тестирования"""
    try:
        if flask.request.headers.get('content-type') == 'application/json':
            json_string = flask.request.get_data().decode('utf-8')
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            return '', 200
        else:
            return 'invalid content type', 403
    except Exception as e:
        print(f"Error: {e}")
        return 'Error', 500

@app.route('/health', methods=['GET'])
def health():
    """Проверка состояния"""
    return {
        'status': 'ok',
        'bot': 'running',
        'version': 'test_minimal_1.0',
        'timestamp': '2025-11-23T12:01:50'
    }

if __name__ == '__main__':
    # Получаем порт из переменной окружения Render
    port = int(os.environ.get('PORT', 10000))
    print(f"Запуск сервера на порту {port}")
    app.run(host='0.0.0.0', port=port, debug=False)