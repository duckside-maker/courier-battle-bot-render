#!/bin/bash
# Скрипт запуска бота на Render.com
# БИТВА КУРЬЕРОВ - Telegram Bot

set -e

echo "🚀 === ЗАПУСК БОТА БИТВА КУРЬЕРОВ ==="
echo "Время: $(date '+%Y-%m-%d %H:%M:%S')"
echo

# Проверка переменных окружения
echo "🔍 Проверка конфигурации..."

if [ -z "$PORT" ]; then
    echo "⚠️  Переменная PORT не установлена, используем по умолчанию: 10000"
    export PORT=10000
else
    echo "✅ PORT: $PORT"
fi

if [ -z "$BOT_TOKEN" ]; then
    echo "❌ ОШИБКА: Переменная BOT_TOKEN не установлена"
    echo "📋 Установите BOT_TOKEN в переменных окружения Render"
    exit 1
else
    echo "✅ BOT_TOKEN: ${BOT_TOKEN:0:15}..."
fi

if [ -z "$ADMIN_ID" ]; then
    echo "❌ ОШИБКА: Переменная ADMIN_ID не установлена"
    echo "📋 Установите ADMIN_ID в переменных окружения Render"
    exit 1
else
    echo "✅ ADMIN_ID: $ADMIN_ID"
fi

echo "✅ Конфигурация проверена успешно"
echo

# Проверка Python и зависимостей
echo "🐍 Проверка Python окружения..."

python_version=$(python3 --version 2>&1)
echo "📍 Python: $python_version"

# Проверка установленных пакетов
echo "📦 Проверка зависимостей..."
python3 -c "
import telebot
import flask
import sqlite3
print('✅ Все основные модули доступны')
" 2>/dev/null || {
    echo "⚠️  Некоторые модули недоступны, устанавливаем зависимости..."
    pip install -q pyTelegramBotAPI Flask requests Pillow numpy opencv-python
}

echo "✅ Зависимости готовы"
echo

# Создание директории для данных
echo "📁 Подготовка рабочей директории..."
mkdir -p data
echo "✅ Директория data готова"

# Создание базы данных (если не существует)
if [ ! -f "courier_battle_bot.db" ]; then
    echo "🗃️  Создание базы данных..."
    python3 -c "
import sqlite3
conn = sqlite3.connect('courier_battle_bot.db')
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS applications (
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
)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    added_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS bot_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE UNIQUE,
    total_apps INTEGER DEFAULT 0,
    favorites INTEGER DEFAULT 0,
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP
)''')
conn.commit()
conn.close()
print('✅ База данных создана успешно')
"
    echo "✅ База данных инициализирована"
else
    echo "✅ База данных уже существует"
fi

# Создание тестового видео (если не существует)
if [ ! -f "welcome_video.mp4" ]; then
    echo "🎥 Создание тестового видео..."
    python3 -c "
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import os

try:
    width, height = 512, 512
    fps = 30
    duration = 3
    
    frames = []
    for i in range(fps * duration):
        img = Image.new('RGB', (width, height), color='#FF6B6B')
        draw = ImageDraw.Draw(img)
        
        try:
            font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 40)
        except:
            font = ImageFont.load_default()
        
        text = 'БИТВА КУРЬЕРОВ'
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        x = (width - text_width) // 2
        y = (height - text_height) // 2
        
        draw.text((x, y), text, fill='white', font=font)
        
        frame = np.array(img)
        frames.append(frame)
    
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter('welcome_video.mp4', fourcc, fps, (width, height))
    
    for frame in frames:
        out.write(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
    
    out.release()
    print('✅ Тестовое видео создано')
    
except Exception as e:
    print(f'⚠️  Ошибка создания видео: {e}')
    with open('welcome_video.mp4', 'wb') as f:
        f.write(b'')
    print('✅ Создана пустая заглушка для видео')
"
    echo "✅ Видео готово"
else
    echo "✅ Видео уже существует"
fi

echo
echo "🎯 === ГОТОВНОСТЬ К ЗАПУСКУ ==="
echo "🌐 Порт: $PORT"
echo "🤖 Bot Token: ${BOT_TOKEN:0:15}..."
echo "👑 Admin ID: $ADMIN_ID"
echo "💾 База данных: courier_battle_bot.db"
echo "🎥 Видео: welcome_video.mp4"
echo

# Проверка доступности порта
echo "🔍 Проверка порта $PORT..."
if command -v netstat &> /dev/null; then
    netstat -tlnp 2>/dev/null | grep ":$PORT " && {
        echo "⚠️  Порт $PORT уже используется"
        echo "🔄 Попытка освобождения порта..."
    } || echo "✅ Порт $PORT свободен"
else
    echo "⚠️  netstat недоступен, пропускаем проверку порта"
fi

echo
echo "🚀 === ЗАПУСК ПРИЛОЖЕНИЯ ==="
echo "🌍 Host: 0.0.0.0"
echo "🔌 Port: $PORT"
echo "🔧 Mode: Production"
echo "⏰ Время запуска: $(date '+%Y-%m-%d %H:%M:%S')"
echo

# Установка обработчика сигналов для корректного завершения
trap 'echo; echo "🛑 Получен сигнал остановки..."; echo "⏹️  Корректное завершение бота..."; exit 0' SIGTERM SIGINT

# Запуск основного приложения
echo "🎉 БИТВА КУРЬЕРОВ запускается..."
echo "📡 Ожидание входящих сообщений..."
echo "📊 Health check доступен по адресу: /health"
echo "🔗 Webhook endpoint: /webhook"
echo

# Запуск через render_bot.py
exec python3 render_bot.py