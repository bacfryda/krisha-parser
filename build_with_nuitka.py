"""
Сборка с Nuitka - самый мощный компилятор Python.
Создаёт настоящий машинный код, а не упакованный Python.
"""
import os
import sys
import subprocess
import shutil

def build_main_app():
    """Собирает основное приложение с Nuitka."""
    print("=" * 60)
    print("  СБОРКА С NUITKA")
    print("  Krisha Parser Bot")
    print("=" * 60)
    print()
    
    print("🔧 Компиляция основного приложения...")
    print("⏳ Это займёт 10-15 минут (первый раз)...")
    print()
    
    # Команда для Nuitka
    cmd = [
        'python', '-m', 'nuitka',
        '--standalone',  # Создать автономную папку
        '--enable-plugin=pyqt6',  # Поддержка PyQt6
        '--windows-disable-console',  # Без консоли
        '--output-dir=nuitka_build',  # Папка вывода
        '--output-filename=KrishaParser.exe',  # Имя файла
        '--company-name=KrishaParser',
        '--product-name=Krisha Parser Bot',
        '--file-version=1.0.0.0',
        '--product-version=1.0.0.0',
        '--file-description=Krisha Parser Bot',
        '--assume-yes-for-downloads',  # Автоматически скачивать зависимости
        '--show-progress',  # Показывать прогресс
        '--show-memory',  # Показывать использование памяти
        'main.py'
    ]
    
    try:
        result = subprocess.run(cmd, check=True, text=True)
        
        # Проверяем результат
        exe_path = os.path.join('nuitka_build', 'main.dist', 'KrishaParser.exe')
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"\n✅ Сборка завершена!")
            print(f"📦 Файл: {exe_path}")
            print(f"📏 Размер: {size_mb:.1f} MB")
            
            # Копируем в dist для совместимости
            dist_dir = 'dist/KrishaParser_Nuitka'
            if os.path.exists(dist_dir):
                shutil.rmtree(dist_dir)
            shutil.copytree('nuitka_build/main.dist', dist_dir)
            
            print(f"\n📁 Скопировано в: {dist_dir}/")
            return True
        else:
            print("\n❌ Файл не найден после сборки!")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Ошибка компиляции!")
        print(f"Код ошибки: {e.returncode}")
        return False
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_portable_package():
    """Создаёт портативный пакет."""
    print("\n📦 Создание портативного пакета...")
    
    source_dir = 'dist/KrishaParser_Nuitka'
    if not os.path.exists(source_dir):
        print("❌ Сборка не найдена!")
        return False
    
    # Создаём финальную папку
    final_dir = 'KrishaParser_Portable_Nuitka'
    if os.path.exists(final_dir):
        shutil.rmtree(final_dir)
    os.makedirs(final_dir)
    
    # Копируем программу
    print("  📦 Копирование программы...")
    shutil.copytree(source_dir, os.path.join(final_dir, 'KrishaParser'))
    
    # Копируем wa-server
    print("  📦 Копирование WhatsApp сервера...")
    wa_dest = os.path.join(final_dir, 'wa-server')
    shutil.copytree('wa-server', wa_dest, 
                    ignore=shutil.ignore_patterns('node_modules', 'wa_auth_data', '*.log'))
    
    # Создаём bat-файл для запуска
    print("  📝 Создание launcher.bat...")
    launcher = os.path.join(final_dir, 'Запустить.bat')
    with open(launcher, 'w', encoding='utf-8') as f:
        f.write('''@echo off
cd /d "%~dp0"
start "" "KrishaParser\\KrishaParser.exe"
''')
    
    # Создаём README
    print("  📝 Создание README.txt...")
    readme = os.path.join(final_dir, 'README.txt')
    with open(readme, 'w', encoding='utf-8') as f:
        f.write('''KRISHA PARSER BOT
=================

ЗАПУСК:
-------
Запустите файл: Запустить.bat
Или: KrishaParser\\KrishaParser.exe

ПЕРВЫЙ ЗАПУСК:
--------------
1. Авторизуйтесь на Krisha.kz (вкладка "Крыша")
2. Подключите WhatsApp (вкладка "WhatsApp")
3. Настройте фильтры
4. Начните парсинг

ВАЖНО:
------
• Программа работает до 30 марта 2026
• Требуется Google Chrome
• Требуется Node.js для WhatsApp

© 2026 Krisha Parser Bot
''')
    
    print(f"\n✅ Портативный пакет создан: {final_dir}/")
    
    # Подсчёт размера
    total_size = 0
    for root, dirs, files in os.walk(final_dir):
        for file in files:
            total_size += os.path.getsize(os.path.join(root, file))
    
    size_mb = total_size / (1024 * 1024)
    print(f"📏 Размер: {size_mb:.1f} MB")
    
    return True

def main():
    """Главная функция."""
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Проверяем что main.py существует
    if not os.path.exists('main.py'):
        print("❌ main.py не найден!")
        return False
    
    # Собираем
    if not build_main_app():
        return False
    
    # Создаём портативный пакет
    if not create_portable_package():
        return False
    
    print("\n" + "=" * 60)
    print("  🎉 ГОТОВО!")
    print("=" * 60)
    print()
    print("📁 Портативная версия: KrishaParser_Portable_Nuitka/")
    print()
    print("📋 ЧТО ДАЛЬШЕ:")
    print("  1. Заархивируй папку KrishaParser_Portable_Nuitka")
    print("  2. Передай архив другу")
    print("  3. Друг распаковывает и запускает Запустить.bat")
    print()
    print("✅ Преимущества Nuitka:")
    print("  • Настоящий машинный код (не Python)")
    print("  • Быстрее работает")
    print("  • Меньше проблем с антивирусами")
    print("  • Стабильнее PyInstaller")
    
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
