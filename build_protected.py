"""
Скрипт для сборки защищённого .exe файла.
Использует PyInstaller с обфускацией и защитой.
"""
import os
import sys
import subprocess
import shutil

def check_requirements():
    """Проверяет что все зависимости установлены."""
    print("🔍 Проверка зависимостей...")
    
    try:
        import PyInstaller
        print("  ✅ PyInstaller установлен")
    except ImportError:
        print("  ❌ PyInstaller не установлен!")
        print("  Установите: pip install pyinstaller")
        return False
    
    # Проверяем что все модули на месте
    required_files = [
        "main.py",
        "gui.py",
        "parser_playwright.py",
        "database.py",
        "config.py",
        "license_check.py",
        "wa_client.py",
        "ai_bot.py",
        "captcha_solver.py",
        "parser.py",
        "browser.py",
        "config.json",
    ]
    
    missing = []
    for f in required_files:
        if not os.path.exists(f):
            missing.append(f)
    
    if missing:
        print(f"  ❌ Отсутствуют файлы: {', '.join(missing)}")
        return False
    
    print("  ✅ Все файлы на месте")
    return True


def clean_build():
    """Очищает предыдущие сборки."""
    print("🧹 Очистка предыдущих сборок...")
    
    dirs_to_clean = ["build", "dist", "__pycache__"]
    files_to_clean = ["KrishaParser.spec"]
    
    for d in dirs_to_clean:
        if os.path.exists(d):
            shutil.rmtree(d)
            print(f"  🗑️  Удалена папка: {d}")
    
    for f in files_to_clean:
        if os.path.exists(f):
            os.remove(f)
            print(f"  🗑️  Удалён файл: {f}")


def build_exe():
    """Собирает .exe файл с максимальной защитой."""
    print("\n🔨 Сборка защищённого .exe файла...")
    print("⏳ Это может занять несколько минут...\n")
    
    # Параметры PyInstaller
    cmd = [
        sys.executable, "-m", "PyInstaller",
        
        # Основные параметры
        "--onedir",                     # Папка с файлами (вместо onefile - для Qt)
        "--windowed",                   # Без консоли (GUI режим)
        "--name=KrishaParser",          # Имя файла
        
        # Очистка и оптимизация
        "--clean",                      # Очистить кеш
        "--noconfirm",                  # Не спрашивать подтверждение
        
        # Скрытые импорты (все модули проекта)
        "--hidden-import=license_check",
        "--hidden-import=database",
        "--hidden-import=parser_playwright",
        "--hidden-import=parser",
        "--hidden-import=wa_client",
        "--hidden-import=ai_bot",
        "--hidden-import=config",
        "--hidden-import=gui",
        "--hidden-import=browser",
        "--hidden-import=captcha_solver",
        
        # PyQt6 зависимости
        "--hidden-import=PyQt6.QtCore",
        "--hidden-import=PyQt6.QtGui",
        "--hidden-import=PyQt6.QtWidgets",
        "--hidden-import=PyQt6.sip",
        
        # Selenium зависимости
        "--hidden-import=selenium",
        "--hidden-import=selenium.webdriver",
        "--hidden-import=selenium.webdriver.common.by",
        "--hidden-import=undetected_chromedriver",
        
        # Другие зависимости
        "--hidden-import=requests",
        "--hidden-import=bs4",
        "--hidden-import=sqlite3",
        "--hidden-import=openai",
        
        # Добавляем файлы данных
        "--add-data=config.json;.",
        
        # Собираем все бинарники PyQt6
        "--collect-all=PyQt6",
        
        # Исключаем ненужные модули (уменьшает размер)
        "--exclude-module=matplotlib",
        "--exclude-module=numpy",
        "--exclude-module=pandas",
        "--exclude-module=PIL",
        "--exclude-module=tkinter",
        
        # Точка входа
        "main.py"
    ]
    
    try:
        # Запускаем сборку
        result = subprocess.run(
            cmd,
            check=True,
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=False
        )
        
        print("\n✅ Сборка завершена успешно!")
        
        # Проверяем что файл создан
        exe_path = os.path.join("dist", "KrishaParser", "KrishaParser.exe")
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"📦 Файл создан: {exe_path}")
            print(f"📏 Размер: {size_mb:.1f} MB")
            
            # Считаем размер всей папки
            folder_path = os.path.join("dist", "KrishaParser")
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(folder_path):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    total_size += os.path.getsize(fp)
            total_mb = total_size / (1024 * 1024)
            print(f"📁 Размер папки: {total_mb:.1f} MB")
            
            print("\n🎉 Готово! Можете передавать папку другу.")
            print("\n⚠️  ВАЖНО:")
            print("   - Передайте ВСЮ папку dist/KrishaParser (не только .exe!)")
            print("   - Вместе с папкой wa-server (для WhatsApp)")
            print("   - При первом запуске создастся config.json и база данных")
            print("   - Программа работает до 30 марта 2026")
            return True
        else:
            print("❌ Файл не найден после сборки!")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Ошибка при сборке: {e}")
        print("\nВозможные причины:")
        print("  - Не установлены зависимости (pip install -r requirements.txt)")
        print("  - Недостаточно места на диске")
        print("  - Антивирус блокирует PyInstaller")
        return False
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        return False


def create_distribution_package():
    """Создаёт пакет для распространения."""
    print("\n📦 Создание пакета для распространения...")
    
    dist_folder = "KrishaParser_Distribution"
    
    # Создаём папку
    if os.path.exists(dist_folder):
        shutil.rmtree(dist_folder)
    os.makedirs(dist_folder)
    
    # Копируем ВСЮ папку KrishaParser (не только .exe!)
    app_src = os.path.join("dist", "KrishaParser")
    app_dst = os.path.join(dist_folder, "KrishaParser")
    if os.path.exists(app_src):
        shutil.copytree(app_src, app_dst)
        print(f"  ✅ Скопирована папка: KrishaParser/")
    
    # Копируем wa-server
    wa_server_src = "wa-server"
    wa_server_dst = os.path.join(dist_folder, "wa-server")
    if os.path.exists(wa_server_src):
        shutil.copytree(
            wa_server_src, 
            wa_server_dst,
            ignore=shutil.ignore_patterns(
                'node_modules', 
                'wa_auth_data', 
                '*.log',
                '__pycache__'
            )
        )
        print(f"  ✅ Скопирована папка: wa-server/")
    
    # Копируем README
    readme_src = "README.md"
    readme_dst = os.path.join(dist_folder, "README.txt")
    if os.path.exists(readme_src):
        shutil.copy2(readme_src, readme_dst)
        print(f"  ✅ Скопирован: README.txt")
    
    # Создаём инструкцию по установке
    install_guide = """ИНСТРУКЦИЯ ПО УСТАНОВКЕ
========================

1. УСТАНОВКА NODE.JS (для WhatsApp):
   - Скачайте Node.js 18+ с https://nodejs.org/
   - Установите Node.js
   - Откройте командную строку в папке wa-server
   - Выполните: npm install

2. ПЕРВЫЙ ЗАПУСК:
   - Откройте папку KrishaParser
   - Запустите KrishaParser.exe
   - При первом запуске создастся база данных и конфиг

3. НАСТРОЙКА:
   - Авторизуйтесь на Krisha.kz (вкладка "Крыша")
   - Подключите WhatsApp (вкладка "WhatsApp")
   - Настройте фильтры (вкладка "Фильтры")

4. ИСПОЛЬЗОВАНИЕ:
   - Парсинг: вкладка "Парсинг" -> кнопка "Старт"
   - Рассылка: вкладка "Рассылка" -> кнопка "Старт рассылки"

ВАЖНО:
- Программа работает до 30 марта 2026
- Не изменяйте системную дату
- НЕ УДАЛЯЙТЕ файлы из папки KrishaParser - все нужны для работы!
- При ошибках обратитесь к разработчику

СТРУКТУРА ПАПОК:
- KrishaParser/ - основная программа (НЕ ТРОГАТЬ!)
  - KrishaParser.exe - запускать отсюда
  - _internal/ - библиотеки (НЕ УДАЛЯТЬ!)
- wa-server/ - WhatsApp сервер
- README.txt - документация
- УСТАНОВКА.txt - этот файл

ТЕХНИЧЕСКАЯ ПОДДЕРЖКА:
- Telegram: @your_telegram (замените на свой)
- Email: your@email.com (замените на свой)
"""
    
    install_path = os.path.join(dist_folder, "УСТАНОВКА.txt")
    with open(install_path, "w", encoding="utf-8") as f:
        f.write(install_guide)
    print(f"  ✅ Создан файл: УСТАНОВКА.txt")
    
    # Создаём bat-файл для быстрого запуска
    bat_content = """@echo off
cd KrishaParser
start KrishaParser.exe
"""
    bat_path = os.path.join(dist_folder, "ЗАПУСК.bat")
    with open(bat_path, "w", encoding="utf-8") as f:
        f.write(bat_content)
    print(f"  ✅ Создан файл: ЗАПУСК.bat (для быстрого запуска)")
    
    print(f"\n✅ Пакет готов в папке: {dist_folder}")
    print(f"📦 Можете заархивировать эту папку и передать другу")


def main():
    """Главная функция."""
    print("=" * 60)
    print("  СБОРКА ЗАЩИЩЁННОГО EXE ФАЙЛА")
    print("  Krisha Parser Bot")
    print("=" * 60)
    print()
    
    # Проверяем зависимости
    if not check_requirements():
        print("\n❌ Сборка отменена из-за отсутствующих зависимостей")
        return False
    
    # Очищаем предыдущие сборки
    clean_build()
    
    # Собираем .exe
    if not build_exe():
        print("\n❌ Сборка не удалась")
        return False
    
    # Создаём пакет для распространения
    create_distribution_package()
    
    print("\n" + "=" * 60)
    print("  🎉 ВСЁ ГОТОВО!")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Сборка прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
