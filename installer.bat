@echo off
chcp 65001 >nul
title Установка Krisha Parser Bot
color 0A

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║         УСТАНОВКА KRISHA PARSER BOT v1.0                   ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

:: Проверка прав администратора
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ❌ Требуются права администратора!
    echo    Запустите установщик от имени администратора.
    pause
    exit /b 1
)

:: Установка в Program Files
set "INSTALL_DIR=%ProgramFiles%\Krisha Parser Bot"
echo 📁 Папка установки: %INSTALL_DIR%
echo.

:: Создаём папку
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: Копируем файлы
echo 📦 Копирование файлов...
xcopy /E /I /Y /Q "KrishaParser" "%INSTALL_DIR%" >nul
xcopy /E /I /Y /Q "wa-server" "%INSTALL_DIR%\wa-server" >nul
copy /Y "README.txt" "%INSTALL_DIR%\" >nul 2>&1

echo ✅ Файлы скопированы
echo.

:: Проверка Node.js
echo 🔍 Проверка Node.js...
node --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ⚠️  Node.js не установлен!
    echo.
    echo 📥 Установите Node.js вручную:
    echo    1. Откройте https://nodejs.org/
    echo    2. Скачайте LTS версию
    echo    3. Установите Node.js
    echo    4. Перезапустите компьютер
    echo.
    set "NODE_INSTALLED=0"
) else (
    echo ✅ Node.js установлен
    set "NODE_INSTALLED=1"
)
echo.

:: Установка npm зависимостей
if "%NODE_INSTALLED%"=="1" (
    echo 📦 Установка WhatsApp сервера...
    cd /d "%INSTALL_DIR%\wa-server"
    call npm install >nul 2>&1
    if %errorLevel% equ 0 (
        echo ✅ WhatsApp сервер установлен
    ) else (
        echo ⚠️  Ошибка установки WhatsApp сервера
    )
    echo.
)

:: Создание ярлыка на рабочем столе
echo 🔗 Создание ярлыка...
set "DESKTOP=%USERPROFILE%\Desktop"
set "SHORTCUT=%DESKTOP%\Krisha Parser Bot.lnk"

powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%SHORTCUT%'); $Shortcut.TargetPath = '%INSTALL_DIR%\KrishaParser.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.Description = 'Krisha Parser Bot'; $Shortcut.Save()"

if exist "%SHORTCUT%" (
    echo ✅ Ярлык создан на рабочем столе
) else (
    echo ⚠️  Не удалось создать ярлык
)
echo.

:: Создание записи в реестре для удаления
echo 📝 Регистрация программы...
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\KrishaParserBot" /v "DisplayName" /t REG_SZ /d "Krisha Parser Bot" /f >nul
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\KrishaParserBot" /v "DisplayVersion" /t REG_SZ /d "1.0" /f >nul
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\KrishaParserBot" /v "Publisher" /t REG_SZ /d "Your Company" /f >nul
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\KrishaParserBot" /v "InstallLocation" /t REG_SZ /d "%INSTALL_DIR%" /f >nul
reg add "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\KrishaParserBot" /v "UninstallString" /t REG_SZ /d "%INSTALL_DIR%\uninstall.bat" /f >nul
echo ✅ Программа зарегистрирована
echo.

:: Создание деинсталлятора
echo @echo off > "%INSTALL_DIR%\uninstall.bat"
echo title Удаление Krisha Parser Bot >> "%INSTALL_DIR%\uninstall.bat"
echo echo Удаление Krisha Parser Bot... >> "%INSTALL_DIR%\uninstall.bat"
echo rd /s /q "%INSTALL_DIR%" >> "%INSTALL_DIR%\uninstall.bat"
echo del /f /q "%DESKTOP%\Krisha Parser Bot.lnk" >> "%INSTALL_DIR%\uninstall.bat"
echo reg delete "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\KrishaParserBot" /f >> "%INSTALL_DIR%\uninstall.bat"
echo echo Программа удалена. >> "%INSTALL_DIR%\uninstall.bat"
echo pause >> "%INSTALL_DIR%\uninstall.bat"

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║              ✅ УСТАНОВКА ЗАВЕРШЕНА!                       ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
echo 📋 Программа установлена в: %INSTALL_DIR%
echo 🖥️  Ярлык создан на рабочем столе
echo.
echo 📖 ЧТО ДАЛЬШЕ:
echo    1. Запустите программу с рабочего стола
echo    2. Авторизуйтесь на Krisha.kz
echo    3. Подключите WhatsApp
echo    4. Начните парсинг
echo.
echo ⚠️  ВАЖНО: Программа работает до 30 марта 2026
echo.

:: Предложение запустить программу
set /p "LAUNCH=Запустить программу сейчас? (Y/N): "
if /i "%LAUNCH%"=="Y" (
    start "" "%INSTALL_DIR%\KrishaParser.exe"
)

echo.
echo Нажмите любую клавишу для выхода...
pause >nul
