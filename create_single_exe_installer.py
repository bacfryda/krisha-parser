"""
Создаёт ОДИН .exe установщик который содержит всё внутри.
При запуске автоматически устанавливает программу.
"""
import os
import sys
import subprocess
import base64
import zipfile
from pathlib import Path

def create_installer_script():
    """Создаёт Python скрипт установщика."""
    
    installer_code = '''"""
Krisha Parser Bot - Автоматический установщик
Распаковывает и устанавливает программу автоматически.
"""
import os
import sys
import zipfile
import tempfile
import shutil
import subprocess
import base64
from pathlib import Path
import ctypes

def is_admin():
    """Проверяет права администратора."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def request_admin():
    """Запрашивает права администратора."""
    if not is_admin():
        print("Требуются права администратора...")
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit(0)

def extract_embedded_data():
    """Извлекает встроенные данные."""
    print("📦 Распаковка файлов...")
    
    # Данные встроены в конец этого скрипта
    # Ищем маркер начала данных
    with open(sys.executable if getattr(sys, 'frozen', False) else __file__, 'rb') as f:
        content = f.read()
        marker = b'__EMBEDDED_DATA_START__'
        pos = content.find(marker)
        if pos == -1:
            raise Exception("Встроенные данные не найдены!")
        
        # Извлекаем данные после маркера
        data = content[pos + len(marker):]
        
        # Создаём временную папку
        temp_dir = tempfile.mkdtemp(prefix='krisha_installer_')
        zip_path = os.path.join(temp_dir, 'data.zip')
        
        # Сохраняем zip
        with open(zip_path, 'wb') as zf:
            zf.write(data)
        
        # Распаковываем
        extract_dir = os.path.join(temp_dir, 'extracted')
        with zipfile.ZipFile(zip_path, 'r') as zf:
            zf.extractall(extract_dir)
        
        return extract_dir

def install_program(source_dir):
    """Устанавливает программу."""
    print("\\n🔧 Установка программы...")
    
    # Папка установки
    install_dir = os.path.join(os.environ['ProgramFiles'], 'Krisha Parser Bot')
    print(f"📁 Папка: {install_dir}")
    
    # Создаём папку
    os.makedirs(install_dir, exist_ok=True)
    
    # Копируем файлы
    print("📦 Копирование файлов...")
    for item in os.listdir(source_dir):
        src = os.path.join(source_dir, item)
        dst = os.path.join(install_dir, item)
        if os.path.isdir(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
    
    print("✅ Файлы скопированы")
    
    # Проверка Node.js
    print("\\n🔍 Проверка Node.js...")
    try:
        subprocess.run(['node', '--version'], check=True, capture_output=True)
        print("✅ Node.js установлен")
        
        # Установка npm зависимостей
        print("📦 Установка WhatsApp сервера...")
        wa_server_dir = os.path.join(install_dir, 'wa-server')
        if os.path.exists(wa_server_dir):
            subprocess.run(
                ['npm', 'install'],
                cwd=wa_server_dir,
                check=True,
                capture_output=True
            )
            print("✅ WhatsApp сервер установлен")
    except:
        print("⚠️  Node.js не установлен")
        print("   Скачайте с https://nodejs.org/")
    
    # Создание ярлыка
    print("\\n🔗 Создание ярлыка...")
    desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
    shortcut = os.path.join(desktop, 'Krisha Parser Bot.lnk')
    exe_path = os.path.join(install_dir, 'KrishaParser', 'KrishaParser.exe')
    
    ps_script = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{shortcut}')
$Shortcut.TargetPath = '{exe_path}'
$Shortcut.WorkingDirectory = '{os.path.join(install_dir, "KrishaParser")}'
$Shortcut.Description = 'Krisha Parser Bot'
$Shortcut.Save()
"""
    
    try:
        subprocess.run(
            ['powershell', '-Command', ps_script],
            check=True,
            capture_output=True
        )
        print("✅ Ярлык создан")
    except:
        print("⚠️  Не удалось создать ярлык")
    
    # Регистрация в Windows
    print("\\n📝 Регистрация программы...")
    try:
        subprocess.run([
            'reg', 'add',
            r'HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\KrishaParserBot',
            '/v', 'DisplayName', '/t', 'REG_SZ', '/d', 'Krisha Parser Bot', '/f'
        ], check=True, capture_output=True)
        
        subprocess.run([
            'reg', 'add',
            r'HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\KrishaParserBot',
            '/v', 'DisplayVersion', '/t', 'REG_SZ', '/d', '1.0', '/f'
        ], check=True, capture_output=True)
        
        print("✅ Программа зарегистрирована")
    except:
        print("⚠️  Не удалось зарегистрировать")
    
    return install_dir, exe_path

def main():
    """Главная функция установщика."""
    print("=" * 60)
    print("  KRISHA PARSER BOT - УСТАНОВКА")
    print("=" * 60)
    print()
    
    # Проверка прав администратора
    if not is_admin():
        print("⚠️  Требуются права администратора!")
        print("   Перезапуск с правами администратора...")
        request_admin()
        return
    
    try:
        # Извлекаем данные
        source_dir = extract_embedded_data()
        
        # Устанавливаем
        install_dir, exe_path = install_program(source_dir)
        
        # Очистка временных файлов
        print("\\n🧹 Очистка...")
        shutil.rmtree(os.path.dirname(source_dir), ignore_errors=True)
        
        print("\\n" + "=" * 60)
        print("  ✅ УСТАНОВКА ЗАВЕРШЕНА!")
        print("=" * 60)
        print()
        print(f"📁 Программа установлена в: {install_dir}")
        print("🖥️  Ярлык создан на рабочем столе")
        print()
        print("⚠️  ВАЖНО: Программа работает до 30 марта 2026")
        print()
        
        # Предложение запустить
        response = input("Запустить программу сейчас? (Y/N): ")
        if response.upper() == 'Y':
            subprocess.Popen([exe_path])
        
        print("\\nНажмите Enter для выхода...")
        input()
        
    except Exception as e:
        print(f"\\n❌ Ошибка установки: {e}")
        import traceback
        traceback.print_exc()
        print("\\nНажмите Enter для выхода...")
        input()
        sys.exit(1)

if __name__ == '__main__':
    main()

__EMBEDDED_DATA_START__'''
    
    return installer_code

def create_data_archive():
    """Создаёт архив с данными программы."""
    print("📦 Создание архива данных...")
    
    archive_path = 'installer_data.zip'
    
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Добавляем программу
        print("  + KrishaParser/")
        for root, dirs, files in os.walk("dist/KrishaParser"):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, "dist")
                zipf.write(file_path, arcname)
        
        # Добавляем wa-server
        print("  + wa-server/")
        for root, dirs, files in os.walk("wa-server"):
            if 'node_modules' in root or 'wa_auth_data' in root:
                continue
            for file in files:
                if file.endswith('.log'):
                    continue
                file_path = os.path.join(root, file)
                zipf.write(file_path, file_path)
    
    size_mb = os.path.getsize(archive_path) / (1024 * 1024)
    print(f"✅ Архив создан: {size_mb:.1f} MB")
    
    return archive_path

def build_single_exe():
    """Собирает один .exe установщик."""
    print("\\n🔨 Сборка установщика...")
    
    # Создаём скрипт установщика
    installer_code = create_installer_script()
    
    with open('_installer_main.py', 'w', encoding='utf-8') as f:
        f.write(installer_code)
    
    # Создаём архив данных
    data_archive = create_data_archive()
    
    # Добавляем данные в конец скрипта
    print("\\n📎 Встраивание данных...")
    with open('_installer_main.py', 'ab') as f:
        with open(data_archive, 'rb') as df:
            f.write(df.read())
    
    # Собираем с PyInstaller
    print("\\n🔧 Компиляция установщика...")
    print("⏳ Это займёт несколько минут...\\n")
    
    cmd = [
        'pyinstaller',
        '--onefile',
        '--windowed',
        '--name=KrishaParserBot_Setup',
        '--icon=NONE',
        '--clean',
        '_installer_main.py'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        exe_path = 'dist/KrishaParserBot_Setup.exe'
        if os.path.exists(exe_path):
            size_mb = os.path.getsize(exe_path) / (1024 * 1024)
            print(f"\\n✅ Установщик создан!")
            print(f"📦 Файл: {exe_path}")
            print(f"📏 Размер: {size_mb:.1f} MB")
            
            # Очистка
            print("\\n🧹 Очистка временных файлов...")
            os.remove('_installer_main.py')
            os.remove(data_archive)
            if os.path.exists('_installer_main.spec'):
                os.remove('_installer_main.spec')
            if os.path.exists('build'):
                shutil.rmtree('build')
            
            return True
    
    print(f"\\n❌ Ошибка сборки:")
    print(result.stderr)
    return False

def main():
    """Главная функция."""
    print("=" * 60)
    print("  СОЗДАНИЕ ЕДИНОГО .EXE УСТАНОВЩИКА")
    print("  Krisha Parser Bot")
    print("=" * 60)
    print()
    
    # Проверяем сборку
    if not os.path.exists("dist/KrishaParser"):
        print("❌ Сборка не найдена!")
        print("Сначала запустите: python build_protected.py")
        return False
    
    print("✅ Сборка найдена")
    
    # Собираем установщик
    if not build_single_exe():
        return False
    
    print("\\n" + "=" * 60)
    print("  🎉 ГОТОВО!")
    print("=" * 60)
    print()
    print("📋 ЧТО ДАЛЬШЕ:")
    print("  1. Передай другу файл: dist/KrishaParserBot_Setup.exe")
    print("  2. Друг запускает .exe")
    print("  3. Программа устанавливается автоматически")
    print("  4. Ярлык появляется на рабочем столе")
    print()
    print("⚠️  ВАЖНО:")
    print("  - Один файл, всё внутри")
    print("  - Автоматическая установка")
    print("  - Работает до 30 марта 2026")
    
    return True

if __name__ == "__main__":
    try:
        os.chdir(os.path.dirname(os.path.abspath(__file__)))
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\\n\\n⚠️  Прервано")
        sys.exit(1)
    except Exception as e:
        print(f"\\n\\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
