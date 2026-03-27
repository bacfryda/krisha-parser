@echo off
chcp 65001 >nul
echo ========================================
echo   🏠 Krisha Parser Bot — Запуск
echo ========================================
echo.

:: Проверяем что setup был выполнен
if not exist "venv" (
    echo ❌ Виртуальное окружение не найдено!
    echo    Сначала запустите: setup.bat
    pause
    exit /b 1
)

if not exist "wa-server\node_modules" (
    echo ❌ Node.js зависимости не установлены!
    echo    Сначала запустите: setup.bat
    pause
    exit /b 1
)

:: ─── Запуск WA-сервера в фоне ──────────────────────────
echo [1/2] Запускаем WhatsApp сервер...
start "WA-Server" /min cmd /c "cd wa-server && node server.js"
echo   ✅ WA-сервер запущен (порт 3457)

:: Ждём пока сервер поднимется
timeout /t 3 /nobreak >nul

:: ─── Запуск GUI ────────────────────────────────────────
echo [2/2] Запускаем GUI...
echo.
call venv\Scripts\activate.bat
python main.py

:: Когда GUI закроется — убиваем WA-сервер
echo.
echo Завершаем WA-сервер...
taskkill /fi "WINDOWTITLE eq WA-Server" /f >nul 2>&1
echo ✅ Всё остановлено. До встречи!
pause
