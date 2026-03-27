"""
Простой установщик - один .exe файл.
Распаковывает KrishaParserBot_Portable.zip и устанавливает.
"""
import os
import sys
import zipfile
import shutil
import subprocess
import ctypes
from pathlib import Path

def is_admin():
    """Проверяет права администратора."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def request_admin():
    """Запрашивает права администратора."""
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join(sys.argv), None, 1
        )
        sys.exit(0)

def find_archive():
    """Ищет архив рядом с установщиком."""
    # Папка где находится установщик
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Ищем архив
    archive_name = 'KrishaParserBot_Portable.zip'
    archive_path = os.path.join(base_dir, archive_name)
    
    if os.path.exists(archive_path):
        return archive_path
    
    # Ищем в текущей папке
    if os.path.exists(archive_name):
        return archive_name
    
    return None

def extract_archive(archive_path):
    """Распаковывает архив."""
    print("📦 Распаковка файлов...")
    
    # Создаём временную папку
    temp_dir = os.path.join(os.environ['TEMP'], 'krisha_install')
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir)
    
    # Распаковываем
    with zipfile.ZipFile(archive_path, 'r') as zf:
        zf.extractall(temp_dir)
    
    print("✅ Файлы распакованы")
    return temp_dir

def install_program(source_dir):
    """Устанавливает программу."""
    print("\n🔧 Установка программы...")
    
    # Папка установки
    install_dir = os.path.join(os.environ['ProgramFiles'], 'Krisha Parser Bot')
    print(f"📁 Папка: {install_dir}")
    
    # Создаём папку
    os.makedirs(install_dir, exist_ok=True)
    
    # Копируем KrishaParser
    print("📦 Копирование программы...")
    src_parser = os.path.join(source_dir, 'KrishaParser')
    dst_parser = os.path.join(install_dir, 'KrishaParser')
    if os.path.exists(dst_parser):
        shutil.rmtree(dst_parser)
    shutil.copytree(src_parser, dst_parser)
    
    # Копируем wa-server
    print("📦 Копирование WhatsApp сервера...")
    src_wa = os.path.join(source_dir, 'wa-server')
    dst_wa = os.path.join(install_dir, 'wa-server')
    if os.path.exists(dst_wa):
        shutil.rmtree(dst_wa)
    shutil.copytree(src_wa, dst_wa)
    
    print("✅ Файлы скопированы")
    
    # Проверка Node.js
    print("\n🔍 Проверка Node.js...")
    node_installed = False
    try:
        result = subprocess.run(['node', '--version'], check=True, capture_output=True, text=True)
        print(f"✅ Node.js установлен: {result.stdout.strip()}")
        node_installed = True
    except:
        print("⚠️  Node.js не установлен!")
        print("   Скачайте с https://nodejs.org/")
        print("   Установите и перезагрузите компьютер")
    
    # Установка npm зависимостей
    if node_installed:
        print("\n📦 Установка WhatsApp сервера...")
        try:
            subprocess.run(
                ['npm', 'install'],
                cwd=dst_wa,
                check=True,
                capture_output=True,
                timeout=300
            )
            print("✅ WhatsApp сервер установлен")
        except subprocess.TimeoutExpired:
            print("⚠️  Установка заняла слишком много времени")
        except Exception as e:
            print(f"⚠️  Ошибка установки: {e}")
    
    # Создание ярлыка
    print("\n🔗 Создание ярлыка...")
    desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
    shortcut = os.path.join(desktop, 'Krisha Parser Bot.lnk')
    exe_path = os.path.join(dst_parser, 'KrishaParser.exe')
    
    ps_script = f"""
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut('{shortcut}')
$Shortcut.TargetPath = '{exe_path}'
$Shortcut.WorkingDirectory = '{dst_parser}'
$Shortcut.Description = 'Krisha Parser Bot'
$Shortcut.Save()
"""
    
    try:
        subprocess.run(
            ['powershell', '-Command', ps_script],
            check=True,
            capture_output=True
        )
        print("✅ Ярлык создан на рабочем столе")
    except Exception as e:
        print(f"⚠️  Не удалось создать ярлык: {e}")
    
    # Регистрация в Windows
    print("\n📝 Регистрация программы...")
    try:
        # Создаём uninstall.bat
        uninstall_bat = os.path.join(install_dir, 'uninstall.bat')
        with open(uninstall_bat, 'w', encoding='utf-8') as f:
            f.write(f'''@echo off
title Удаление Krisha Parser Bot
echo Удаление Krisha Parser Bot...
rd /s /q "{install_dir}"
del /f /q "{shortcut}"
reg delete "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\KrishaParserBot" /f
echo Программа удалена.
pause
''')
        
        # Регистрируем в реестре
        subprocess.run([
            'reg', 'add',
            r'HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\KrishaParserBot',
            '/v', 'DisplayName', '/t', 'REG_SZ', '/d', 'Krisha Parser Bot', '/f'
        ], check=True, capture_output=True)
        
        subprocess.run([
            'reg', 'add',
            r'HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\KrishaParserBot',
            '/v', 'DisplayVersion', '/t', 'REG_SZ', '/d', '1.0', '/f'
        ], check=True, capture_output=True)
        
        subprocess.run([
            'reg', 'add',
            r'HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\KrishaParserBot',
            '/v', 'UninstallString', '/t', 'REG_SZ', '/d', uninstall_bat, '/f'
        ], check=True, capture_output=True)
        
        print("✅ Программа зарегистрирована")
    except Exception as e:
        print(f"⚠️  Не удалось зарегистрировать: {e}")
    
    return install_dir, exe_path

def main():
    """Главная функция."""
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
        # Ищем архив
        print("🔍 Поиск файлов...")
        archive_path = find_archive()
        
        if not archive_path:
            print("\n❌ Файл KrishaParserBot_Portable.zip не найден!")
            print("   Положите архив рядом с установщиком")
            input("\nНажмите Enter для выхода...")
            return
        
        print(f"✅ Найден: {os.path.basename(archive_path)}")
        
        # Распаковываем
        source_dir = extract_archive(archive_path)
        
        # Устанавливаем
        install_dir, exe_path = install_program(source_dir)
        
        # Очистка
        print("\n🧹 Очистка временных файлов...")
        shutil.rmtree(source_dir, ignore_errors=True)
        
        print("\n" + "=" * 60)
        print("  ✅ УСТАНОВКА ЗАВЕРШЕНА!")
        print("=" * 60)
        print()
        print(f"📁 Программа установлена в:")
        print(f"   {install_dir}")
        print()
        print("🖥️  Ярлык создан на рабочем столе:")
        print("   Krisha Parser Bot")
        print()
        print("📖 ЧТО ДАЛЬШЕ:")
        print("   1. Запустите программу с рабочего стола")
        print("   2. Авторизуйтесь на Krisha.kz")
        print("   3. Подключите WhatsApp")
        print("   4. Начните парсинг")
        print()
        print("⚠️  ВАЖНО: Программа работает до 30 марта 2026")
        print()
        
        # Предложение запустить
        response = input("Запустить программу сейчас? (Y/N): ")
        if response.upper() == 'Y':
            subprocess.Popen([exe_path])
        
    except Exception as e:
        print(f"\n❌ Ошибка установки: {e}")
        import traceback
        traceback.print_exc()
        input("\nНажмите Enter для выхода...")
        sys.exit(1)

if __name__ == '__main__':
    main()
