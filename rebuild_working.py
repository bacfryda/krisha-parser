"""
Пересборка с правильными параметрами PyInstaller.
Исправляет PyQt6 DLL проблему.
"""
import os
import sys
import subprocess
import shutil

def clean():
    """Очистка."""
    print("🧹 Очистка...")
    for d in ['build', 'dist', '__pycache__']:
        if os.path.exists(d):
            shutil.rmtree(d, ignore_errors=True)
    for f in ['KrishaParser.spec']:
        if os.path.exists(f):
            os.remove(f)

def build():
    """Сборка."""
    print("\n🔨 Сборка...")
    
    cmd = [
        'pyinstaller',
        '--onedir',
        '--windowed',
        '--name=KrishaParser',
        '--add-data=config.json;.',
        '--hidden-import=PyQt6',
        '--hidden-import=PyQt6.QtCore',
        '--hidden-import=PyQt6.QtGui',
        '--hidden-import=PyQt6.QtWidgets',
        '--hidden-import=selenium',
        '--hidden-import=undetected_chromedriver',
        '--hidden-import=requests',
        '--hidden-import=sqlite3',
        '--collect-all=PyQt6',
        '--copy-metadata=PyQt6',
        '--collect-binaries=PyQt6',
        '--collect-data=PyQt6',
        '--noconfirm',
        'main.py'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print("❌ Ошибка:")
        print(result.stderr)
        return False
    
    if os.path.exists('dist/KrishaParser/KrishaParser.exe'):
        print("✅ Сборка завершена")
        return True
    
    return False

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    clean()
    if build():
        print("\n✅ Готово: dist/KrishaParser/")
        return True
    return False

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
