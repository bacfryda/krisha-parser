#!/bin/bash
echo "========================================"
echo "  🏠 Krisha Parser Bot — Запуск"
echo "========================================"
echo ""

if [ ! -d "venv" ]; then
    echo "❌ venv не найден! Сначала: ./setup.sh"
    exit 1
fi

if [ ! -d "wa-server/node_modules" ]; then
    echo "❌ Node зависимости не установлены! Сначала: ./setup.sh"
    exit 1
fi

# Запуск WA-сервера в фоне
echo "[1/2] Запускаем WhatsApp сервер..."
cd wa-server && node server.js &
WA_PID=$!
cd ..
echo "  ✅ WA-сервер запущен (PID: $WA_PID, порт 3457)"
sleep 3

# Запуск GUI
echo "[2/2] Запускаем GUI..."
echo ""
source venv/bin/activate
python3 main.py

# Когда GUI закроется — убиваем WA-сервер
echo ""
echo "Завершаем WA-сервер..."
kill $WA_PID 2>/dev/null
echo "✅ Всё остановлено. До встречи!"
