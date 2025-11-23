#!/bin/bash
# Скрипт настройки вебхука для Telegram бота
# Использование: ./setup_webhook.sh

set -e

BOT_TOKEN="8542303018:AAF5Pqisa1ZfqHxibGx3zQV06verk2D4M6Y"
ADMIN_ID="5982747122"

echo "🔧 Настройка вебхука для БИТВА КУРЬЕРОВ"
echo "========================================"

# Проверка переменных окружения
RENDER_URL="${RENDER_EXTERNAL_URL:-https://courier-battle-bot.onrender.com}"
WEBHOOK_URL="${RENDER_URL}/webhook"

echo "📋 Информация о вебхуке:"
echo "   • URL: ${WEBHOOK_URL}"
echo "   • Token: ${BOT_TOKEN:0:15}..."
echo

# Установка вебхука
echo "🔗 Установка вебхука..."

response=$(curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"${WEBHOOK_URL}\", \"max_connections\": 40}")

echo "📡 Ответ Telegram API:"
echo "$response" | jq '.' 2>/dev/null || echo "$response"

# Проверка успешности
success=$(echo "$response" | jq -r '.ok')
if [ "$success" = "true" ]; then
    webhook_id=$(echo "$response" | jq -r '.result.id')
    echo "✅ Вебхук успешно установлен!"
    echo "   • ID: $webhook_id"
    echo "   • URL: $WEBHOOK_URL"
else
    echo "❌ Ошибка установки вебхука"
    error_msg=$(echo "$response" | jq -r '.description')
    echo "   • Ошибка: $error_msg"
    exit 1
fi

# Получение информации о вебхуке
echo
echo "📊 Текущий статус вебхука:"

webhook_info=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo")
echo "$webhook_info" | jq '.' 2>/dev/null || echo "$webhook_info"

# Проверка работоспособности бота
echo
echo "🤖 Тестирование бота..."

bot_info=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getMe")
bot_success=$(echo "$bot_info" | jq -r '.ok')
bot_username=$(echo "$bot_info" | jq -r '.result.username')

if [ "$bot_success" = "true" ]; then
    echo "✅ Бот готов к работе: @${bot_username}"
else
    echo "❌ Ошибка подключения к боту"
    exit 1
fi

# Проверка админа
echo
echo "👑 Проверка администратора..."

admin_info=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getChat?chat_id=${ADMIN_ID}")
admin_success=$(echo "$admin_info" | jq -r '.ok')

if [ "$admin_success" = "true" ]; then
    admin_name=$(echo "$admin_info" | jq -r '.result.first_name // "Unknown"')
    echo "✅ Администратор найден: ${admin_name} (${ADMIN_ID})"
else
    echo "⚠️  Администратор не найден или бот не добавлен в чат"
fi

echo
echo "🎉 Настройка вебхука завершена!"
echo "🔗 Вебхук URL: ${WEBHOOK_URL}"
echo "🤖 Бот: @${bot_username}"
echo "📱 Для тестирования отправьте /start"

echo
echo "💡 Следующие шаги:"
echo "1. Откройте чат с ботом @${bot_username}"
echo "2. Отправьте /start"
echo "3. Протестируйте все функции"
echo "4. Отправьте /admin с ID ${ADMIN_ID} для доступа к админ панели"

echo
echo "📖 Для устранения неполадок проверьте:"
echo "• Логи в Render Dashboard"
echo "• Health check: ${WEBHOOK_URL%"/webhook"}/health"