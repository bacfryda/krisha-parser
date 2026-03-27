"""
Создаёт РАБОЧИЙ пакет с правильной структурой.
Гарантированно работает - проверенная структура.
"""
import os
import sys
import zipfile
import shutil

def create_package():
    """Создаёт финальный пакет."""
    print("=" * 60)
    print("  СОЗДАНИЕ РАБОЧЕГО ПАКЕТА")
    print("=" * 60)
    print()
    
    # Проверяем сборку
    if not os.path.exists("dist/KrishaParser"):
        print("❌ Сборка не найдена!")
        return False
    
    print("✅ Сборка найдена")
    
    # Создаём финальную папку
    package_dir = "KrishaParser_FINAL"
    if os.path.exists(package_dir):
        shutil.rmtree(package_dir)
    os.makedirs(package_dir)
    
    # Копируем программу
    print("\n📦 Копирование программы...")
    shutil.copytree("dist/KrishaParser", os.path.join(package_dir, "KrishaParser"))
    
    # Копируем wa-server
    print("📦 Копирование WhatsApp сервера...")
    wa_dest = os.path.join(package_dir, "wa-server")
    shutil.copytree("wa-server", wa_dest,
                    ignore=shutil.ignore_patterns('node_modules', 'wa_auth_data', '*.log'))
    
    # Создаём установщик
    print("📝 Создание установщика...")
    installer_bat = os.path.join(package_dir, "УСТАНОВИТЬ.bat")
    with open(installer_bat, 'w', encoding='utf-8') as f:
        f.write('''@echo off
chcp 65001 >nul
title Установка Krisha Parser Bot
color 0A

echo.
echo ============================================================
echo          УСТАНОВКА KRISHA PARSER BOT
echo ============================================================
echo.

:: Проверка прав администратора
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo ⚠️  Требуются права администратора!
    echo    Запустите от имени администратора
    pause
    exit /b 1
)

set "INSTALL_DIR=%ProgramFiles%\\KrishaParser"
set "DESKTOP=%USERPROFILE%\\Desktop"

echo 📁 Папка установки: %INSTALL_DIR%
echo.

:: Создаём папку
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: Копируем файлы
echo 📦 Копирование файлов...
xcopy /E /I /Y /Q "KrishaParser" "%INSTALL_DIR%\\KrishaParser" >nul
xcopy /E /I /Y /Q "wa-server" "%INSTALL_DIR%\\wa-server" >nul
echo ✅ Файлы скопированы
echo.

:: Проверка Node.js
echo 🔍 Проверка Node.js...
node --version >nul 2>&1
if %errorLevel% equ 0 (
    echo ✅ Node.js установлен
    echo.
    echo 📦 Установка WhatsApp сервера...
    cd /d "%INSTALL_DIR%\\wa-server"
    call npm install >nul 2>&1
    if %errorLevel% equ 0 (
        echo ✅ WhatsApp сервер установлен
    )
) else (
    echo ⚠️  Node.js не установлен
    echo    Скачайте с https://nodejs.org/
)
echo.

:: Создаём ярлык
echo 🔗 Создание ярлыка...
powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%DESKTOP%\\Krisha Parser.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\\KrishaParser\\KrishaParser.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%\\KrishaParser'; $Shortcut.Description = 'Krisha Parser Bot'; $Shortcut.Save()"
echo ✅ Ярлык создан
echo.

:: Регистрация
echo 📝 Регистрация программы...
reg add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\KrishaParser" /v "DisplayName" /t REG_SZ /d "Krisha Parser Bot" /f >nul
reg add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\KrishaParser" /v "DisplayVersion" /t REG_SZ /d "1.0" /f >nul
reg add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\KrishaParser" /v "Publisher" /t REG_SZ /d "Krisha Parser" /f >nul
reg add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\KrishaParser" /v "InstallLocation" /t REG_SZ /d "%INSTALL_DIR%" /f >nul
reg add "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\KrishaParser" /v "UninstallString" /t REG_SZ /d "%INSTALL_DIR%\\УДАЛИТЬ.bat" /f >nul
echo ✅ Программа зарегистрирована
echo.

:: Создаём деинсталлятор
echo @echo off > "%INSTALL_DIR%\\УДАЛИТЬ.bat"
echo title Удаление Krisha Parser Bot >> "%INSTALL_DIR%\\УДАЛИТЬ.bat"
echo echo Удаление программы... >> "%INSTALL_DIR%\\УДАЛИТЬ.bat"
echo rd /s /q "%INSTALL_DIR%" >> "%INSTALL_DIR%\\УДАЛИТЬ.bat"
echo del /f /q "%DESKTOP%\\Krisha Parser.lnk" >> "%INSTALL_DIR%\\УДАЛИТЬ.bat"
echo reg delete "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\KrishaParser" /f >> "%INSTALL_DIR%\\УДАЛИТЬ.bat"
echo echo Программа удалена >> "%INSTALL_DIR%\\УДАЛИТЬ.bat"
echo pause >> "%INSTALL_DIR%\\УДАЛИТЬ.bat"

echo.
echo ============================================================
echo              УСТАНОВКА ЗАВЕРШЕНА!
echo ============================================================
echo.
echo 📁 Программа установлена в: %INSTALL_DIR%
echo 🖥️  Ярлык создан на рабочем столе
echo.
echo ⚠️  ВАЖНО: Программа работает до 30 марта 2026
echo.

set /p "LAUNCH=Запустить программу? (Y/N): "
if /i "%LAUNCH%"=="Y" (
    start "" "%INSTALL_DIR%\\KrishaParser\\KrishaParser.exe"
)

pause
''')
    
    # Создаём launcher
    print("📝 Создание launcher...")
    launcher_bat = os.path.join(package_dir, "ЗАПУСТИТЬ.bat")
    with open(launcher_bat, 'w', encoding='utf-8') as f:
        f.write('''@echo off
cd /d "%~dp0"
start "" "KrishaParser\\KrishaParser.exe"
''')
    
    # Создаём README
    print("📝 Создание README...")
    readme = os.path.join(package_dir, "ЧИТАЙ_МЕНЯ.txt")
    with open(readme, 'w', encoding='utf-8') as f:
        f.write('''╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║         KRISHA PARSER BOT - ИНСТРУКЦИЯ                        ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝

🚀 УСТАНОВКА (РЕКОМЕНДУЕТСЯ):
═══════════════════════════════════════════════════════════════
1. Запустите УСТАНОВИТЬ.bat ОТ ИМЕНИ АДМИНИСТРАТОРА
2. Следуйте инструкциям
3. Ярлык появится на рабочем столе
4. Программа зарегистрируется в Windows

🎯 ПОРТАТИВНЫЙ ЗАПУСК (БЕЗ УСТАНОВКИ):
═══════════════════════════════════════════════════════════════
1. Запустите ЗАПУСТИТЬ.bat
2. Программа запустится без установки

💻 СИСТЕМНЫЕ ТРЕБОВАНИЯ:
═══════════════════════════════════════════════════════════════
• Windows 10/11 (64-bit)
• 500 MB свободного места
• Google Chrome
• Node.js (для WhatsApp)

⚠️ ВАЖНО:
═══════════════════════════════════════════════════════════════
• Программа работает до 30 марта 2026
• Для WhatsApp нужен Node.js с https://nodejs.org/

© 2026 Krisha Parser Bot
''')
    
    # Подсчёт размера
    print("\n📊 Подсчёт размера...")
    total_size = 0
    for root, dirs, files in os.walk(package_dir):
        for file in files:
            total_size += os.path.getsize(os.path.join(root, file))
    
    size_mb = total_size / (1024 * 1024)
    
    print("\n✅ Пакет создан!")
    print(f"📁 Папка: {package_dir}/")
    print(f"📏 Размер: {size_mb:.1f} MB")
    
    return package_dir

def create_archive(package_dir):
    """Создаёт архив."""
    print("\n📦 Создание архива...")
    
    archive_name = "KrishaParser_FINAL.zip"
    
    with zipfile.ZipFile(archive_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path)
                zipf.write(file_path, arcname)
    
    size_mb = os.path.getsize(archive_name) / (1024 * 1024)
    print(f"✅ Архив создан: {archive_name}")
    print(f"📏 Размер: {size_mb:.1f} MB")
    
    return archive_name

def main():
    """Главная функция."""
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Создаём пакет
    package_dir = create_package()
    if not package_dir:
        return False
    
    # Создаём архив
    archive_name = create_archive(package_dir)
    
    print("\n" + "=" * 60)
    print("  🎉 ГОТОВО!")
    print("=" * 60)
    print()
    print(f"📦 ПЕРЕДАЙ ДРУГУ: {archive_name}")
    print()
    print("📋 ИНСТРУКЦИЯ ДЛЯ ДРУГА:")
    print("  1. Распаковать архив")
    print("  2. Запустить УСТАНОВИТЬ.bat от имени администратора")
    print("  3. Следовать инструкциям")
    print("  4. Готово!")
    print()
    print("✅ ОСОБЕННОСТИ:")
    print("  • Правильная установка в Program Files")
    print("  • Ярлык на рабочем столе")
    print("  • Регистрация в Windows")
    print("  • Удаление через Панель управления")
    print("  • Можно запускать без установки (ЗАПУСТИТЬ.bat)")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
