#!/usr/bin/env python3
"""
ТЕЛЕГРАМ БОТ БИТВА КУРЬЕРОВ - Render Edition
Версия для развертывания на Render.com
"""

import os
import sys
import sqlite3
import telebot
import flask
from datetime import datetime
from telebot import types
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
user_data = {}

# База данных
DB_NAME = "courier_battle_bot.db"

def init_database():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Таблица заявок
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE,
            full_name TEXT NOT NULL,
            age INTEGER NOT NULL,
            phone TEXT NOT NULL,
            email TEXT NOT NULL,
            video_file_id TEXT,
            video_unique_id TEXT,
            is_favorite BOOLEAN DEFAULT FALSE,
            status TEXT DEFAULT 'pending',
            submitted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            admin_notes TEXT
        )
    """)
    
    # Таблица избранного
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id)
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована")

def create_test_video():
    """Создание тестового видео для приветствия"""
    import cv2
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    
    try:
        # Создание простого видео с текстом
        width, height = 512, 512
        fps = 30
        duration = 3  # 3 секунды
        
        # Создание кадров
        frames = []
        for i in range(fps * duration):
            # Создание изображения
            img = Image.new('RGB', (width, height), color='#FF6B6B')
            draw = ImageDraw.Draw(img)
            
            # Добавление текста
            try:
                # Попытка использовать системный шрифт
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 40)
            except:
                try:
                    font = ImageFont.load_default()
                except:
                    font = None
            
            text = "БИТВА КУРЬЕРОВ"
            if font:
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
            else:
                text_width, text_height = 200, 30
            
            x = (width - text_width) // 2
            y = (height - text_height) // 2
            
            draw.text((x, y), text, fill='white', font=font)
            
            # Конвертация в массив numpy
            frame = np.array(img)
            frames.append(frame)
        
        # Создание видео
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter('welcome_video.mp4', fourcc, fps, (width, height))
        
        for frame in frames:
            out.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        
        out.release()
        
        print("✅ Тестовое видео создано")
        return True
        
    except Exception as e:
        print(f"⚠️  Ошибка создания видео: {e}")
        # Создаем пустой файл как заглушку
        with open('welcome_video.mp4', 'wb') as f:
            f.write(b'')
        return False

@bot.message_handler(commands=['start'])
def start_command(message):
    """Обработчик команды /start"""
    user_id = message.from_user.id
    user_states[user_id] = 'start'
    
    try:
        # Отправка приветственного видео
        video_path = 'welcome_video.mp4'
        if os.path.exists(video_path):
            with open(video_path, 'rb') as video:
                bot.send_video(
                    chat_id=user_id,
                    video=video,
                    caption="🎯 **БИТВА КУРЬЕРОВ**\\n\\nПривет! Ты готов показать свои навыки курьера?",
                    parse_mode='Markdown'
                )
        else:
            bot.send_message(
                user_id,
                "🎯 **БИТВА КУРЬЕРОВ**\\n\\nПривет! Ты готов показать свои навыки курьера?",
                parse_mode='Markdown'
            )
        
        # Кнопка "ПОГНАЛИ"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🚀 ПОГНАЛИ", callback_data="start_form"))
        
        bot.send_message(
            user_id,
            "Нажми на кнопку, чтобы начать заполнение анкеты:",
            reply_markup=markup
        )
        
    except Exception as e:
        print(f"❌ Ошибка в start_command: {e}")
        bot.send_message(user_id, "Произошла ошибка. Попробуйте /start еще раз.")

@bot.callback_query_handler(func=lambda call: call.data == "start_form")
def start_form_callback(call):
    """Начало заполнения анкеты"""
    user_id = call.from_user.id
    user_states[user_id] = 'awaiting_name'
    user_data[user_id] = {}
    
    bot.send_message(
        user_id,
        "📝 **Заполнение анкеты**\\n\\n**1. Введите ваше ФИО:**\\n\\n*Подсказка: Иванов Иван Иванович*",
        parse_mode='Markdown'
    )

@bot.message_handler(content_types=['text'])
def handle_text_input(message):
    """Обработчик текстового ввода для анкеты"""
    user_id = message.from_user.id
    text = message.text.strip()
    
    if user_id not in user_states:
        return
    
    state = user_states[user_id]
    
    if state == 'awaiting_name':
        # Валидация ФИО
        if len(text.split()) >= 2:
            user_data[user_id]['full_name'] = text
            user_states[user_id] = 'awaiting_age'
            bot.send_message(
                user_id,
                "📝 **2. Введите ваш возраст:**\\n\\n*Подсказка: от 18 до 65 лет*",
                parse_mode='Markdown'
            )
        else:
            bot.send_message(user_id, "❌ Пожалуйста, введите полное ФИО (минимум имя и фамилию)")
    
    elif state == 'awaiting_age':
        # Валидация возраста
        try:
            age = int(text)
            if 16 <= age <= 80:
                user_data[user_id]['age'] = age
                user_states[user_id] = 'awaiting_phone'
                bot.send_message(
                    user_id,
                    "📝 **3. Введите ваш номер телефона:**\\n\\n*Подсказка: +7 *** *** ** **",
                    parse_mode='Markdown'
                )
            else:
                bot.send_message(user_id, "❌ Возраст должен быть от 16 до 80 лет")
        except ValueError:
            bot.send_message(user_id, "❌ Введите корректный возраст (число)")
    
    elif state == 'awaiting_phone':
        # Валидация телефона
        phone = text.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        if phone.startswith('+7') or phone.startswith('7') or phone.startswith('8'):
            if len(phone) >= 10:
                user_data[user_id]['phone'] = text
                user_states[user_id] = 'awaiting_email'
                bot.send_message(
                    user_id,
                    "📝 **4. Введите ваш email:**\\n\\n*Подсказка: example@domain.com*",
                    parse_mode='Markdown'
                )
            else:
                bot.send_message(user_id, "❌ Номер телефона слишком короткий")
        else:
            bot.send_message(user_id, "❌ Номер телефона должен начинаться с +7 или 8")
    
    elif state == 'awaiting_email':
        # Валидация email
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if re.match(email_pattern, text):
            user_data[user_id]['email'] = text
            user_states[user_id] = 'awaiting_video'
            bot.send_message(
                user_id,
                "📝 **5. Отправьте видео-кружок** (видео-сообщение)\\n\\nРасскажите в двух словах о себе и почему вы должны участвовать в «БИТВЕ КУРЬЕРОВ»\\n\\n*После отправки видео появится кнопка «УЧАСТВУЮ»*",
                parse_mode='Markdown'
            )
        else:
            bot.send_message(user_id, "❌ Введите корректный email адрес")

@bot.message_handler(content_types=['video_note'])
def handle_video_note(message):
    """Обработчик видео-кружка"""
    user_id = message.from_user.id
    
    if user_id not in user_states or user_states[user_id] != 'awaiting_video':
        return
    
    # Сохранение информации о видео
    user_data[user_id]['video_file_id'] = message.video_note.file_id
    user_data[user_id]['video_unique_id'] = message.video_note.file_unique_id
    
    # Проверка данных
    if all(key in user_data[user_id] for key in ['full_name', 'age', 'phone', 'email', 'video_file_id']):
        user_states[user_id] = 'ready_to_submit'
        
        # Кнопка "УЧАСТВУЮ"
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✅ УЧАСТВУЮ", callback_data="submit_application"))
        
        bot.send_message(
            user_id,
            "🎉 **Все данные заполнены!**\\n\\nПроверьте информацию и подтвердите участие:",
            parse_mode='Markdown'
        )
        
        # Краткое резюме данных
        data = user_data[user_id]
        summary = f"""**📋 Резюме вашей анкеты:**

👤 **ФИО:** {data['full_name']}
📅 **Возраст:** {data['age']} лет
📱 **Телефон:** {data['phone']}
📧 **Email:** {data['email']}
🎥 **Видео:** Прикреплено ✅"""
        
        bot.send_message(user_id, summary, parse_mode='Markdown', reply_markup=markup)
    else:
        bot.send_message(user_id, "❌ Ошибка: не все данные сохранены")

@bot.callback_query_handler(func=lambda call: call.data == "submit_application")
def submit_application_callback(call):
    """Сохранение заявки в базу данных"""
    user_id = call.from_user.id
    
    try:
        # Подключение к БД
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Проверка на дубликат
        cursor.execute("SELECT id FROM applications WHERE user_id = ?", (user_id,))
        existing = cursor.fetchone()
        
        if existing:
            bot.answer_callback_query(call.id, "❌ Анкета уже была отправлена ранее")
            return
        
        # Сохранение заявки
        data = user_data[user_id]
        cursor.execute("""
            INSERT INTO applications (user_id, full_name, age, phone, email, video_file_id, video_unique_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            data['full_name'],
            data['age'],
            data['phone'],
            data['email'],
            data['video_file_id'],
            data['video_unique_id']
        ))
        
        conn.commit()
        conn.close()
        
        # Очистка данных пользователя
        if user_id in user_states:
            del user_states[user_id]
        if user_id in user_data:
            del user_data[user_id]
        
        # Уведомление пользователя
        bot.answer_callback_query(call.id, "✅ Анкета отправлена!")
        bot.send_message(
            user_id,
            "🙏 **БЛАГОДАРИМ ЗА УДЕЛЕННОЕ ВРЕМЯ!**\\n\\nСкоро мы с вами свяжемся 😊",
            parse_mode='Markdown'
        )
        
        # Уведомление администратора
        admin_message = f"""📨 **Новая заявка на БИТВУ КУРЬЕРОВ**

👤 **Участник:** {data['full_name']}
📅 **Возраст:** {data['age']}
📱 **Телефон:** {data['phone']}
📧 **Email:** {data['email']}
🆔 **ID:** {user_id}
⏰ **Время подачи:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
        bot.send_message(ADMIN_ID, admin_message, parse_mode='Markdown')
        
    except Exception as e:
        print(f"❌ Ошибка сохранения заявки: {e}")
        bot.answer_callback_query(call.id, "❌ Произошла ошибка при сохранении анкеты")

# Админ функции
@bot.message_handler(commands=['admin'], func=lambda message: message.from_user.id == ADMIN_ID)
def admin_panel(message):
    """Админ панель"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Подсчет заявок
        cursor.execute("SELECT COUNT(*) FROM applications")
        total_apps = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM applications WHERE is_favorite = 1")
        favorites = cursor.fetchone()[0]
        
        conn.close()
        
        admin_text = f"""🛠️ **АДМИН ПАНЕЛЬ**

📊 **Статистика:**
• Всего заявок: {total_apps}
• Избранных: {favorites}

📋 **Доступные команды:**
/view_all - Просмотр всех заявок
/favorites - Избранные заявки  
/export - Экспорт данных в CSV
/stats - Детальная статистика
/contact - Связаться с участником"""
        
        bot.send_message(message.from_user.id, admin_text, parse_mode='Markdown')
        
    except Exception as e:
        print(f"❌ Ошибка в админ панели: {e}")
        bot.send_message(message.from_user.id, "❌ Ошибка загрузки админ панели")

@bot.message_handler(commands=['view_all'], func=lambda message: message.from_user.id == ADMIN_ID)
def view_all_applications(message):
    """Просмотр всех заявок"""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT user_id, full_name, age, phone, email, is_favorite, submitted_at 
            FROM applications ORDER BY submitted_at DESC
        """)
        
        applications = cursor.fetchall()
        conn.close()
        
        if not applications:
            bot.send_message(message.from_user.id, "📭 Пока нет заявок")
            return
        
        for app_data in applications:
            user_id, full_name, age, phone, email, is_favorite, submitted_at = app_data
            
            status = "⭐ Избранная" if is_favorite else "📝 Обычная"
            
            app_text = f"""**Заявка #{user_id}**

👤 **ФИО:** {full_name}
📅 **Возраст:** {age}
📱 **Телефон:** {phone}
📧 **Email:** {email}
{status}
⏰ **Подана:** {submitted_at}

🆔 ID: `{user_id}`"""
            
            # Кнопки для управления
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("⭐ Добавить в избранное", callback_data=f"fav_{user_id}"),
                types.InlineKeyboardButton("🎥 Видео", callback_data=f"video_{user_id}"),
                types.InlineKeyboardButton("📞 Связаться", callback_data=f"contact_{user_id}")
            )
            
            bot.send_message(
                message.from_user.id, 
                app_text, 
                parse_mode='Markdown',
                reply_markup=markup
            )
            
    except Exception as e:
        print(f"❌ Ошибка просмотра заявок: {e}")
        bot.send_message(message.from_user.id, "❌ Ошибка загрузки заявок")

@bot.callback_query_handler(func=lambda call: call.data.startswith("fav_"))
def toggle_favorite(call):
    """Добавление/удаление из избранного"""
    user_id = int(call.data.split("_")[1])
    
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        # Переключение статуса избранного
        cursor.execute("""
            UPDATE applications 
            SET is_favorite = NOT is_favorite 
            WHERE user_id = ?
        """, (user_id,))
        
        conn.commit()
        
        # Получение нового статуса
        cursor.execute("SELECT is_favorite FROM applications WHERE user_id = ?", (user_id,))
        is_fav = cursor.fetchone()[0]
        
        conn.close()
        
        status = "добавлена в избранное" if is_fav else "удалена из избранного"
        bot.answer_callback_query(call.id, f"✅ Заявка {status}")
        
    except Exception as e:
        print(f"❌ Ошибка избранного: {e}")
        bot.answer_callback_query(call.id, "❌ Ошибка обновления")

@bot.callback_query_handler(func=lambda call: call.data.startswith("video_"))
def show_video(call):
    """Просмотр видео заявки"""
    user_id = int(call.data.split("_")[1])
    
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("SELECT video_file_id, full_name FROM applications WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        conn.close()
        
        if result:
            video_file_id, full_name = result
            
            # Пересылаем видео админу
            bot.copy_message(
                chat_id=call.from_user.id,
                from_chat_id=call.from_user.id,
                message_id=0
            )
            
            # Или отправляем ссылку на просмотр
            bot.answer_callback_query(
                call.id, 
                f"🎥 Видео {full_name}",
                show_alert=True
            )
            
    except Exception as e:
        print(f"❌ Ошибка показа видео: {e}")
        bot.answer_callback_query(call.id, "❌ Ошибка загрузки видео")

# Flask маршрут для вебхука
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

@app.route('/health')
def health_check():
    """Проверка состояния приложения"""
    return flask.jsonify({
        'status': 'ok',
        'service': 'Courier Battle Bot',
        'version': 'render_1.0',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/')
def home():
    """Главная страница"""
    return f"""
    <h1>🚀 БИТВА КУРЬЕРОВ - Bot Service</h1>
    <p><strong>Статус:</strong> 🟢 Online</p>
    <p><strong>Время запуска:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    <p><strong>Bot Token:</strong> {BOT_TOKEN[:10]}...{BOT_TOKEN[-10:]}</p>
    <hr>
    <p><a href="/health">Health Check</a></p>
    """

if __name__ == "__main__":
    print("🚀 Инициализация бота...")
    
    # Инициализация БД
    init_database()
    
    # Создание тестового видео
    create_test_video()
    
    # Настройка порта для Render
    port = int(os.environ.get('PORT', 5000))
    
    # Запуск Flask приложения с обработкой Telegram обновлений
    print(f"🌐 Запуск веб-сервера на порту {port}")
    print(f"🤖 Bot Token: {BOT_TOKEN[:10]}...")
    print("✅ Бот готов к работе!")
    
    # Запуск Flask приложения
    app.run(host='0.0.0.0', port=port, debug=False)