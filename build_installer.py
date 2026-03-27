"""
Скрипт для создания профессионального установщика.
Использует Inno Setup для создания .exe установщика.
"""
import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_inno_setup():
    """Проверяет установлен ли Inno Setup."""
    print("🔍 Проверка Inno Setup...")
    
    # Стандартные пути установки Inno Setup
    possible_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe",
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"  ✅ Inno Setup найден: {path}")
            return path
    
    print("  ❌ Inno Setup не найден!")
    print("\n📥 Установите Inno Setup:")
    print("  1. Скачайте с https://jrsoftware.org/isdl.php")
    print("  2. Установите Inno Setup 6")
    print("  3. Запустите этот скрипт снова")
    return None


def prepare_files():
    """Подготавливает файлы для установщика."""
    print("\n📦 Подготовка файлов...")
    
    # Проверяем что сборка выполнена
    if not os.path.exists("dist/KrishaParser"):
        print("  ❌ Сборка не найдена!")
        print("  Сначала запустите: python build_protected.py")
        return False
    
    print("  ✅ Сборка найдена")
    
    # Создаём иконку если её нет (простая заглушка)
    if not os.path.exists("icon.ico"):
        print("  ⚠️  icon.ico не найден, создаю заглушку...")
        # Копируем стандартную иконку Windows
        try:
            shutil.copy(
                r"C:\Windows\System32\imageres.dll",
                "icon.ico"
            )
        except:
            print("  ⚠️  Не удалось создать иконку, продолжаю без неё...")
    
    # Создаём изображения для мастера если их нет
    if not os.path.exists("wizard_image.bmp"):
        print("  ℹ️  wizard_image.bmp не найден (необязательно)")
    
    if not os.path.exists("wizard_small.bmp"):
        print("  ℹ️  wizard_small.bmp не найден (необязательно)")
    
    return True


def build_installer(iscc_path):
    """Собирает установщик с помощью Inno Setup."""
    print("\n🔨 Сборка установщика...")
    print("⏳ Это может занять несколько минут...\n")
    
    # Создаём папку для вывода
    os.makedirs("installer_output", exist_ok=True)
    
    # Запускаем Inno Setup Compiler
    try:
        result = subprocess.run(
            [iscc_path, "installer_script.iss"],
            check=True,
            capture_output=True,
            text=True,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )
        
        print(result.stdout)
        
        # Проверяем что установщик создан
        installer_path = "installer_output/KrishaParserBot_Setup.exe"
        if os.path.exists(installer_path):
            size_mb = os.path.getsize(installer_path) / (1024 * 1024)
            print(f"\n✅ Установщик создан успешно!")
            print(f"📦 Файл: {installer_path}")
            print(f"📏 Размер: {size_mb:.1f} MB")
            print("\n🎉 ГОТОВО!")
            print("\n📋 ЧТО ДАЛЬШЕ:")
            print("  1. Передайте файл KrishaParserBot_Setup.exe другу")
            print("  2. Друг запускает установщик")
            print("  3. Установщик всё сделает автоматически:")
            print("     - Установит программу")
            print("     - Установит Node.js (если нужно)")
            print("     - Установит WhatsApp сервер")
            print("     - Создаст ярлык на рабочем столе")
            print("\n⚠️  ВАЖНО:")
            print("  - Программа работает до 30 марта 2026")
            print("  - Требуется подключение к интернету при установке")
            return True
        else:
            print("\n❌ Установщик не найден после сборки!")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Ошибка при сборке установщика:")
        print(e.stderr)
        return False
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        return False


def main():
    """Главная функция."""
    print("=" * 60)
    print("  СОЗДАНИЕ УСТАНОВЩИКА")
    print("  Krisha Parser Bot")
    print("=" * 60)
    print()
    
    # Проверяем Inno Setup
    iscc_path = check_inno_setup()
    if not iscc_path:
        return False
    
    # Подготавливаем файлы
    if not prepare_files():
        return False
    
    # Собираем установщик
    if not build_installer(iscc_path):
        return False
    
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
