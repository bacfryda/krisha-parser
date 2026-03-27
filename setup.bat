@echo off
chcp 65001 >nul
echo ========================================
echo   🏠 Krisha Parser Bot — Установка
echo ========================================
echo.

:: Проверяем Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден! Установите Python 3.10+ с python.org
    pause
    exit /b 1
)

:: Проверяем Node.js
node --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Node.js не найден! Установите Node.js 18+ с nodejs.org
    pause
    exit /b 1
)

echo ✅ Python найден
echo ✅ Node.js найден
echo.

:: ─── Python venv ───────────────────────────────────────
echo [1/4] Создаём виртуальное окружение Python...
if not exist "venv" (
    python -m venv venv
    echo   ✅ venv создан
) else (
    echo   ℹ️  venv уже существует
)

:: Активируем venv и ставим зависимости
echo [2/4] Устанавливаем Python зависимости...
call venv\Scripts\activate.bat
pip install --upgrade pip >nul 2>&1
pip install -r requirements.txt
echo   ✅ Python зависимости установлены
echo.

:: ─── Node.js зависимости ───────────────────────────────
echo [3/4] Устанавливаем Node.js зависимости (wa-server)...
cd wa-server
call npm install
cd ..
echo   ✅ Node.js зависимости установлены
echo.

:: ─── Инициализация ─────────────────────────────────────
echo [4/4] Инициализация базы данных...
call venv\Scripts\activate.bat
python -c "from database import init_db; init_db(); print('  ✅ База данных готова')"
echo.

echo ========================================
echo   ✅ Установка завершена!
echo ========================================
echo.
echo Для запуска используйте: start.bat
echo.
pause
