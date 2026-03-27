"""
Скрипт для сборки .exe файла с помощью PyInstaller.
Использует обфускацию для защиты кода.
"""
import os
import sys
import subprocess

def build():
    """Собирает .exe файл."""
    
    print("🔨 Сборка исполняемого файла...")
    
    # Проверяем что PyInstaller установлен
    try:
        import PyInstaller
    except ImportError:
        print("❌ PyInstaller не установлен!")
        print("Установите: pip install pyinstaller")
        return False
    
    # Параметры сборки
    cmd = [
        "pyinstaller",
        "--onefile",  # Один файл
        "--windowed",  # Без консоли
        "--name=KrishaParser",  # Имя файла
        "--icon=NONE",  # Без иконки
        "--clean",  # Очистить кеш
        # Скрываем импорты
        "--hidden-import=license_check",
        "--hidden-import=database",
        "--hidden-import=parser_playwright",
        "--hidden-import=wa_client",
        "--hidden-import=ai_bot",
        "--hidden-import=config",
        "--hidden-import=gui",
        # Добавляем файлы
        "--add-data=config.json;.",
        "main.py"
    ]
    
    try:
        result = subprocess.run(cmd, check=True, cwd=os.path.dirname(__file__))
        print("✅ Сборка завершена!")
        print("📦 Файл: dist/KrishaParser.exe")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Ошибка сборки: {e}")
        return False


if __name__ == "__main__":
    build()
