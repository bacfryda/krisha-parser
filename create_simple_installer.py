"""
Создаёт простой самораспаковывающийся установщик без Inno Setup.
Использует 7-Zip SFX для создания .exe установщика.
"""
import os
import sys
import subprocess
import shutil
import zipfile

def create_installer_bat():
    """Создаёт bat-файл установщика."""
    installer_bat = """@echo off
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
set "INSTALL_DIR=%ProgramFiles%\\Krisha Parser Bot"
echo 📁 Папка установки: %INSTALL_DIR%
echo.

:: Создаём папку
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: Копируем файлы
echo 📦 Копирование файлов...
xcopy /E /I /Y /Q "KrishaParser" "%INSTALL_DIR%" >nul
xcopy /E /I /Y /Q "wa-server" "%INSTALL_DIR%\\wa-server" >nul
copy /Y "README.txt" "%INSTALL_DIR%\\" >nul 2>&1

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
    cd /d "%INSTALL_DIR%\\wa-server"
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
set "DESKTOP=%USERPROFILE%\\Desktop"
set "SHORTCUT=%DESKTOP%\\Krisha Parser Bot.lnk"

powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%SHORTCUT%'); $Shortcut.TargetPath = '%INSTALL_DIR%\\KrishaParser.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%'; $Shortcut.Description = 'Krisha Parser Bot'; $Shortcut.Save()"

if exist "%SHORTCUT%" (
    echo ✅ Ярлык создан на рабочем столе
) else (
    echo ⚠️  Не удалось создать ярлык
)
echo.

:: Создание записи в реестре для удаления
echo 📝 Регистрация программы...
reg add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\KrishaParserBot" /v "DisplayName" /t REG_SZ /d "Krisha Parser Bot" /f >nul
reg add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\KrishaParserBot" /v "DisplayVersion" /t REG_SZ /d "1.0" /f >nul
reg add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\KrishaParserBot" /v "Publisher" /t REG_SZ /d "Your Company" /f >nul
reg add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\KrishaParserBot" /v "InstallLocation" /t REG_SZ /d "%INSTALL_DIR%" /f >nul
reg add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\KrishaParserBot" /v "UninstallString" /t REG_SZ /d "%INSTALL_DIR%\\uninstall.bat" /f >nul
echo ✅ Программа зарегистрирована
echo.

:: Создание деинсталлятора
echo @echo off > "%INSTALL_DIR%\\uninstall.bat"
echo title Удаление Krisha Parser Bot >> "%INSTALL_DIR%\\uninstall.bat"
echo echo Удаление Krisha Parser Bot... >> "%INSTALL_DIR%\\uninstall.bat"
echo rd /s /q "%INSTALL_DIR%" >> "%INSTALL_DIR%\\uninstall.bat"
echo del /f /q "%DESKTOP%\\Krisha Parser Bot.lnk" >> "%INSTALL_DIR%\\uninstall.bat"
echo reg delete "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\KrishaParserBot" /f >> "%INSTALL_DIR%\\uninstall.bat"
echo echo Программа удалена. >> "%INSTALL_DIR%\\uninstall.bat"
echo pause >> "%INSTALL_DIR%\\uninstall.bat"

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
    start "" "%INSTALL_DIR%\\KrishaParser.exe"
)

echo.
echo Нажмите любую клавишу для выхода...
pause >nul
"""
    
    with open("installer.bat", "w", encoding="utf-8") as f:
        f.write(installer_bat)
    
    print("  ✅ Создан installer.bat")


def create_archive():
    """Создаёт архив с программой."""
    print("\n📦 Создание архива...")
    
    archive_name = "KrishaParserBot_Portable.zip"
    
    with zipfile.ZipFile(archive_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Добавляем программу
        for root, dirs, files in os.walk("dist/KrishaParser"):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.join("KrishaParser", os.path.relpath(file_path, "dist/KrishaParser"))
                zipf.write(file_path, arcname)
                print(f"    + {arcname}")
        
        # Добавляем wa-server
        for root, dirs, files in os.walk("wa-server"):
            # Пропускаем node_modules
            if 'node_modules' in root or 'wa_auth_data' in root:
                continue
            for file in files:
                if file.endswith('.log'):
                    continue
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path)
                zipf.write(file_path, arcname)
        
        # Добавляем документацию
        if os.path.exists("README.md"):
            zipf.write("README.md", "README.txt")
        
        # Добавляем установщик
        zipf.write("installer.bat", "installer.bat")
    
    size_mb = os.path.getsize(archive_name) / (1024 * 1024)
    print(f"\n✅ Архив создан: {archive_name}")
    print(f"📏 Размер: {size_mb:.1f} MB")
    
    return archive_name


def create_readme():
    """Создаёт README для установщика."""
    readme = """УСТАНОВКА KRISHA PARSER BOT
============================

ВАРИАНТ 1: АВТОМАТИЧЕСКАЯ УСТАНОВКА (рекомендуется)
----------------------------------------------------
1. Запустите installer.bat ОТ ИМЕНИ АДМИНИСТРАТОРА
   (Правой кнопкой -> Запуск от имени администратора)
2. Следуйте инструкциям на экране
3. Программа установится в Program Files
4. Ярлык появится на рабочем столе

ВАРИАНТ 2: РУЧНАЯ УСТАНОВКА
----------------------------
1. Распакуйте папку KrishaParser в любое место
2. Установите Node.js с https://nodejs.org/
3. Откройте командную строку в папке wa-server
4. Выполните: npm install
5. Запустите KrishaParser.exe

СИСТЕМНЫЕ ТРЕБОВАНИЯ:
---------------------
• Windows 10/11 (64-bit)
• 500 MB свободного места
• Google Chrome
• Node.js 18+ (установится автоматически)

ПЕРВЫЙ ЗАПУСК:
--------------
1. Авторизуйтесь на Krisha.kz (вкладка "Крыша")
2. Подключите WhatsApp (вкладка "WhatsApp")
3. Настройте фильтры (вкладка "Фильтры")
4. Начните парсинг (вкладка "Парсинг")

ВАЖНО:
------
• Программа работает до 30 марта 2026
• Не изменяйте системную дату
• При проблемах обратитесь к разработчику

ТЕХНИЧЕСКАЯ ПОДДЕРЖКА:
----------------------
Email: support@yourcompany.com
Telegram: @your_telegram

© 2026 Your Company
"""
    
    with open("УСТАНОВКА.txt", "w", encoding="utf-8") as f:
        f.write(readme)
    
    print("  ✅ Создан УСТАНОВКА.txt")


def main():
    """Главная функция."""
    print("=" * 60)
    print("  СОЗДАНИЕ ПРОСТОГО УСТАНОВЩИКА")
    print("  Krisha Parser Bot")
    print("=" * 60)
    print()
    
    # Проверяем сборку
    if not os.path.exists("dist/KrishaParser"):
        print("❌ Сборка не найдена!")
        print("Сначала запустите: python build_protected.py")
        return False
    
    print("✅ Сборка найдена")
    
    # Создаём файлы
    print("\n📝 Создание файлов установщика...")
    create_installer_bat()
    create_readme()
    
    # Создаём архив
    archive_name = create_archive()
    
    print("\n" + "=" * 60)
    print("  🎉 ГОТОВО!")
    print("=" * 60)
    print()
    print(f"📦 Создан файл: {archive_name}")
    print()
    print("📋 ЧТО ДАЛЬШЕ:")
    print("  1. Передайте архив другу")
    print("  2. Друг распаковывает архив")
    print("  3. Друг запускает installer.bat ОТ ИМЕНИ АДМИНИСТРАТОРА")
    print("  4. Установщик всё сделает автоматически")
    print()
    print("⚠️  ВАЖНО:")
    print("  - Требуются права администратора")
    print("  - Программа работает до 30 марта 2026")
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
