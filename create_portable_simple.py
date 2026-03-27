"""
Создаёт ПРОСТОЙ портативный пакет.
Друг распаковывает и сразу запускает - БЕЗ установки.
"""
import os
import sys
import zipfile
import shutil

def create_portable():
    """Создаёт портативную версию."""
    print("=" * 60)
    print("  СОЗДАНИЕ ПОРТАТИВНОЙ ВЕРСИИ")
    print("  (БЕЗ УСТАНОВКИ)")
    print("=" * 60)
    print()
    
    # Проверяем сборку
    if not os.path.exists("dist/KrishaParser"):
        print("❌ Сборка не найдена!")
        print("Сначала запустите: python build_protected.py")
        return False
    
    print("✅ Сборка найдена")
    
    # Создаём портативную папку
    portable_dir = "KrishaParser_Portable_Final"
    if os.path.exists(portable_dir):
        shutil.rmtree(portable_dir)
    os.makedirs(portable_dir)
    
    # Копируем программу
    print("\n📦 Копирование программы...")
    shutil.copytree("dist/KrishaParser", os.path.join(portable_dir, "KrishaParser"))
    print("  ✅ Программа скопирована")
    
    # Копируем wa-server
    print("📦 Копирование WhatsApp сервера...")
    wa_dest = os.path.join(portable_dir, "wa-server")
    shutil.copytree("wa-server", wa_dest,
                    ignore=shutil.ignore_patterns('node_modules', 'wa_auth_data', '*.log'))
    print("  ✅ WhatsApp сервер скопирован")
    
    # Создаём bat-файл для запуска
    print("📝 Создание файлов запуска...")
    
    # Главный launcher
    launcher = os.path.join(portable_dir, "ЗАПУСТИТЬ.bat")
    with open(launcher, 'w', encoding='utf-8') as f:
        f.write('''@echo off
chcp 65001 >nul
title Krisha Parser Bot
cd /d "%~dp0"

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║         KRISHA PARSER BOT - ЗАПУСК                         ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

:: Проверка Node.js
node --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ⚠️  Node.js не установлен!
    echo    Скачайте с https://nodejs.org/
    echo.
    pause
)

:: Запуск программы
echo 🚀 Запуск программы...
start "" "KrishaParser\\KrishaParser.exe"

exit
''')
    
    # Установщик WhatsApp сервера
    wa_installer = os.path.join(portable_dir, "УСТАНОВИТЬ_WHATSAPP.bat")
    with open(wa_installer, 'w', encoding='utf-8') as f:
        f.write('''@echo off
chcp 65001 >nul
title Установка WhatsApp сервера
cd /d "%~dp0\\wa-server"

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║         УСТАНОВКА WHATSAPP СЕРВЕРА                         ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

:: Проверка Node.js
node --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ❌ Node.js не установлен!
    echo    Скачайте с https://nodejs.org/
    echo    Установите и перезагрузите компьютер
    echo.
    pause
    exit /b 1
)

echo 📦 Установка зависимостей...
call npm install

if %errorLevel% equ 0 (
    echo.
    echo ✅ WhatsApp сервер установлен!
) else (
    echo.
    echo ❌ Ошибка установки
)

echo.
pause
''')
    
    # README
    print("📝 Создание инструкции...")
    readme = os.path.join(portable_dir, "ЧИТАЙ_МЕНЯ.txt")
    with open(readme, 'w', encoding='utf-8') as f:
        f.write('''╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║         KRISHA PARSER BOT - ПОРТАТИВНАЯ ВЕРСИЯ                ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝

🚀 БЫСТРЫЙ СТАРТ (3 ШАГА):
═══════════════════════════════════════════════════════════════

ШАГ 1: Установите Node.js (если ещё нет)
   • Скачайте с https://nodejs.org/
   • Установите LTS версию
   • Перезагрузите компьютер

ШАГ 2: Установите WhatsApp сервер
   • Запустите: УСТАНОВИТЬ_WHATSAPP.bat
   • Дождитесь завершения установки

ШАГ 3: Запустите программу
   • Запустите: ЗАПУСТИТЬ.bat
   • Или: KrishaParser\\KrishaParser.exe

🎯 ПЕРВЫЙ ЗАПУСК ПРОГРАММЫ:
═══════════════════════════════════════════════════════════════
1. Откроется окно программы
2. Вкладка "Крыша" → Авторизуйтесь на Krisha.kz
3. Вкладка "WhatsApp" → Запустите сервер и подключите WhatsApp
4. Вкладка "Фильтры" → Настройте параметры поиска
5. Вкладка "Парсинг" → Начните парсинг

💻 СИСТЕМНЫЕ ТРЕБОВАНИЯ:
═══════════════════════════════════════════════════════════════
✓ Windows 10 или 11 (64-bit)
✓ 500 MB свободного места
✓ Google Chrome (для парсинга)
✓ Node.js 18+ (для WhatsApp)
✓ Интернет

📁 СТРУКТУРА ПАПОК:
═══════════════════════════════════════════════════════════════
KrishaParser_Portable_Final/
  ├── ЗАПУСТИТЬ.bat ⭐ Запуск программы
  ├── УСТАНОВИТЬ_WHATSAPP.bat ⭐ Установка WhatsApp
  ├── ЧИТАЙ_МЕНЯ.txt (этот файл)
  ├── KrishaParser/ (программа)
  │   └── KrishaParser.exe
  └── wa-server/ (WhatsApp сервер)

⚠️ ВАЖНО:
═══════════════════════════════════════════════════════════════
• Программа работает до 30 марта 2026 года
• Не изменяйте системную дату
• Не удаляйте файлы из папки KrishaParser
• Храните всю папку вместе

🔧 ЕСЛИ ЧТО-ТО НЕ РАБОТАЕТ:
═══════════════════════════════════════════════════════════════

Проблема: "Node.js не установлен"
Решение: Скачайте с https://nodejs.org/ и установите

Проблема: Программа не запускается
Решение: 
  • Установите Google Chrome
  • Проверьте антивирус (добавьте в исключения)
  • Запустите от имени администратора

Проблема: WhatsApp не подключается
Решение:
  • Запустите УСТАНОВИТЬ_WHATSAPP.bat
  • Проверьте что Node.js установлен
  • Перезапустите программу

📖 ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ:
═══════════════════════════════════════════════════════════════

Эта версия ПОРТАТИВНАЯ - не требует установки.
Можно запускать с флешки или любой папки.
Все данные хранятся в папке программы.

Для удаления - просто удалите всю папку.

═══════════════════════════════════════════════════════════════
  © 2026 Krisha Parser Bot | Версия 1.0
  Работает до: 30 марта 2026
═══════════════════════════════════════════════════════════════
''')
    
    print("  ✅ Файлы созданы")
    
    # Подсчёт размера
    print("\n📊 Подсчёт размера...")
    total_size = 0
    for root, dirs, files in os.walk(portable_dir):
        for file in files:
            total_size += os.path.getsize(os.path.join(root, file))
    
    size_mb = total_size / (1024 * 1024)
    
    print("\n" + "=" * 60)
    print("  🎉 ПОРТАТИВНАЯ ВЕРСИЯ ГОТОВА!")
    print("=" * 60)
    print()
    print(f"📁 Папка: {portable_dir}/")
    print(f"📏 Размер: {size_mb:.1f} MB")
    print()
    print("📋 ФАЙЛЫ:")
    print("  • ЗАПУСТИТЬ.bat - запуск программы")
    print("  • УСТАНОВИТЬ_WHATSAPP.bat - установка WhatsApp")
    print("  • ЧИТАЙ_МЕНЯ.txt - инструкция")
    print("  • KrishaParser/ - программа")
    print("  • wa-server/ - WhatsApp сервер")
    print()
    print("🎁 ЧТО ПЕРЕДАТЬ ДРУГУ:")
    print("  Заархивируй папку и передай другу")
    print()
    print("📖 ЧТО СКАЗАТЬ ДРУГУ:")
    print('  "Распакуй архив и запусти ЗАПУСТИТЬ.bat"')
    print('  "Сначала установи Node.js если нет"')
    print('  "Потом запусти УСТАНОВИТЬ_WHATSAPP.bat"')
    print()
    print("✅ ПРЕИМУЩЕСТВА:")
    print("  • Не требует установки")
    print("  • Можно запускать с флешки")
    print("  • Просто удалить (удалить папку)")
    print("  • Все данные в одной папке")
    
    return True

def create_archive(portable_dir):
    """Создаёт архив."""
    print("\n📦 Создание архива...")
    
    archive_name = "KrishaParser_Portable_FINAL.zip"
    
    with zipfile.ZipFile(archive_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(portable_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path)
                zipf.write(file_path, arcname)
    
    size_mb = os.path.getsize(archive_name) / (1024 * 1024)
    print(f"✅ Архив создан: {archive_name}")
    print(f"📏 Размер архива: {size_mb:.1f} MB")
    
    return archive_name

def main():
    """Главная функция."""
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Создаём портативную версию
    if not create_portable():
        return False
    
    # Создаём архив
    archive_name = create_archive("KrishaParser_Portable_Final")
    
    print("\n" + "=" * 60)
    print("  🎉 ВСЁ ГОТОВО!")
    print("=" * 60)
    print()
    print(f"📦 ПЕРЕДАЙ ДРУГУ: {archive_name}")
    print()
    print("📋 ИНСТРУКЦИЯ ДЛЯ ДРУГА:")
    print("  1. Распаковать архив")
    print("  2. Установить Node.js (если нет)")
    print("  3. Запустить УСТАНОВИТЬ_WHATSAPP.bat")
    print("  4. Запустить ЗАПУСТИТЬ.bat")
    print("  5. Готово!")
    
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
