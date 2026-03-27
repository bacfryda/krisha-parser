#!/bin/bash
echo "========================================"
echo "  🏠 Krisha Parser Bot — Установка"
echo "========================================"
echo ""

# Проверяем Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 не найден! Установите Python 3.10+"
    exit 1
fi

# Проверяем Node.js
if ! command -v node &> /dev/null; then
    echo "❌ Node.js не найден! Установите Node.js 18+"
    exit 1
fi

echo "✅ Python найден: $(python3 --version)"
echo "✅ Node.js найден: $(node --version)"
echo ""

# ─── Python venv ───────────────────────────────────────
echo "[1/4] Создаём виртуальное окружение Python..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "  ✅ venv создан"
else
    echo "  ℹ️  venv уже существует"
fi

# Ставим зависимости
echo "[2/4] Устанавливаем Python зависимости..."
source venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements.txt
echo "  ✅ Python зависимости установлены"
echo ""

# ─── Node.js зависимости ───────────────────────────────
echo "[3/4] Устанавливаем Node.js зависимости (wa-server)..."
cd wa-server
npm install
cd ..
echo "  ✅ Node.js зависимости установлены"
echo ""

# ─── Инициализация ─────────────────────────────────────
echo "[4/4] Инициализация базы данных..."
source venv/bin/activate
python3 -c "from database import init_db; init_db(); print('  ✅ База данных готова')"
echo ""

echo "========================================"
echo "  ✅ Установка завершена!"
echo "========================================"
echo ""
echo "Для запуска: ./start.sh"
