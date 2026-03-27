"""
Пересборка с исправлением PyQt6 DLL проблемы.
"""
import os
import sys
import subprocess
import shutil

def clean_old_builds():
    """Очистка старых сборок."""
    print("🧹 Очистка старых сборок...")
    
    dirs_to_remove = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name, ignore_errors=True)
    
    files_to_remove = ['KrishaParser.spec']
    for file_name in files_to_remove:
        if os.path.exists(file_name):
            os.remove(file_name)
    
    print("✅ Очистка завершена")

def build_with_pyinstaller():
    """Сборка с PyInstaller с правильными параметрами."""
    print("\n🔨 Сборка с PyInstaller...")
    print("⏳ Это займёт 5-10 минут...\n")
    
    cmd = [
        'pyinstaller',
        '--onedir',  # Папка, не один файл (для PyQt6)
        '--windowed',  # Без консоли
        '--name=KrishaParser',
        '--clean',
        '--noconfirm',
        # PyQt6 параметры
        '--collect-all=PyQt6',
        '--collect-all=PyQt6.QtCore',
        '--collect-all=PyQt6.QtGui',
        '--collect-all=PyQt6.QtWidgets',
        '--copy-metadata=PyQt6',
        # Другие зависимости
        '--hidden-import=selenium',
        '--hidden-import=undetected_chromedriver',
        '--hidden-import=requests',
        '--hidden-import=sqlite3',
        '--hidden-import=anthropic',
        '--hidden-import=openai',
        # Данные
        '--add-data=config.json;.',
        'main.py'
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        
        if os.path.exists('dist/KrishaParser/KrishaParser.exe'):
            print("\n✅ Сборка завершена!")
            return True
        else:
            print("\n❌ .exe не найден")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Ошибка сборки:")
        print(e.stderr)
        return False

def test_exe():
    """Тест запуска .exe."""
    print("\n🧪 ТЕСТ 1: Проверка .exe...")
    
    exe_path = 'dist/KrishaParser/KrishaParser.exe'
    if not os.path.exists(exe_path):
        print("❌ ТЕСТ 1 ПРОВАЛЕН: .exe не найден")
        return False
    
    print(f"✅ ТЕСТ 1 ПРОЙДЕН: .exe существует")
    
    # Проверка размера
    size_mb = os.path.getsize(exe_path) / (1024 * 1024)
    print(f"   Размер: {size_mb:.1f} MB")
    
    # Проверка DLL
    dll_path = 'dist/KrishaParser/_internal/PyQt6/Qt6/bin'
    if os.path.exists(dll_path):
        print(f"✅ PyQt6 DLL найдены")
    else:
        print(f"⚠️  PyQt6 DLL не найдены")
    
    return True

def main():
    """Главная функция."""
    print("=" * 60)
    print("  ПЕРЕСБОРКА С ИСПРАВЛЕНИЕМ")
    print("=" * 60)
    print()
    
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Очистка
    clean_old_builds()
    
    # Сборка
    if not build_with_pyinstaller():
        return False
    
    # Тест
    if not test_exe():
        return False
    
    print("\n" + "=" * 60)
    print("  ✅ СБОРКА ЗАВЕРШЕНА")
    print("=" * 60)
    print()
    print("📁 Папка: dist/KrishaParser/")
    print("📦 Файл: dist/KrishaParser/KrishaParser.exe")
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
