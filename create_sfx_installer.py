"""
Создаёт самораспаковывающийся .exe установщик с помощью 7-Zip SFX.
ОДИН файл - друг запускает и всё устанавливается автоматически и скрыто.
"""
import os
import sys
import subprocess
import shutil
import zipfile

def find_7zip():
    """Ищет 7-Zip на компьютере."""
    possible_paths = [
        r"C:\Program Files\7-Zip\7z.exe",
        r"C:\Program Files (x86)\7-Zip\7z.exe",
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None

def create_installer_script():
    """Создаёт скрипт установщика."""
    script = '''@echo off
chcp 65001 >nul
title Установка...

:: Скрытая установка
set "INSTALL_DIR=%ProgramFiles%\\KrishaParser"
set "DESKTOP=%USERPROFILE%\\Desktop"

:: Создаём папку скрыто
mkdir "%INSTALL_DIR%" 2>nul

:: Копируем файлы скрыто
xcopy /E /I /Y /Q "KrishaParser" "%INSTALL_DIR%\\KrishaParser" >nul 2>&1
xcopy /E /I /Y /Q "wa-server" "%INSTALL_DIR%\\wa-server" >nul 2>&1

:: Устанавливаем WhatsApp сервер скрыто
cd /d "%INSTALL_DIR%\\wa-server"
call npm install >nul 2>&1

:: Создаём ярлык
powershell -WindowStyle Hidden -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%DESKTOP%\\Krisha Parser.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\\KrishaParser\\KrishaParser.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%\\KrishaParser'; $Shortcut.Save()" >nul 2>&1

:: Скрываем папку установки
attrib +h "%INSTALL_DIR%" >nul 2>&1

:: Запускаем программу
start "" "%INSTALL_DIR%\\KrishaParser\\KrishaParser.exe"

:: Самоудаление установщика
(goto) 2>nul & del "%~f0"
'''
    
    with open('install_script.bat', 'w', encoding='utf-8') as f:
        f.write(script)
    
    return 'install_script.bat'

def create_sfx_config():
    """Создаёт конфигурацию для SFX."""
    config = ''';!@Install@!UTF-8!
Title="Krisha Parser Bot"
BeginPrompt="Установить Krisha Parser Bot?"
RunProgram="install_script.bat"
;!@InstallEnd@!
'''
    
    with open('sfx_config.txt', 'w', encoding='utf-8') as f:
        f.write(config)
    
    return 'sfx_config.txt'

def create_archive():
    """Создаёт архив с программой."""
    print("📦 Создание архива...")
    
    archive_name = 'installer_data.7z'
    
    # Используем 7-Zip для создания архива
    seven_zip = find_7zip()
    if not seven_zip:
        print("❌ 7-Zip не найден!")
        print("Установите 7-Zip с https://www.7-zip.org/")
        return None
    
    # Создаём архив
    cmd = [
        seven_zip, 'a',
        '-t7z',  # Формат 7z
        '-mx9',  # Максимальное сжатие
        archive_name,
        'dist/KrishaParser',
        'wa-server',
        'install_script.bat'
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0 and os.path.exists(archive_name):
        size_mb = os.path.getsize(archive_name) / (1024 * 1024)
        print(f"✅ Архив создан: {size_mb:.1f} MB")
        return archive_name
    else:
        print(f"❌ Ошибка создания архива: {result.stderr}")
        return None

def create_sfx_installer(archive_name):
    """Создаёт SFX установщик."""
    print("\n🔨 Создание SFX установщика...")
    
    seven_zip = find_7zip()
    sfx_module = os.path.join(os.path.dirname(seven_zip), '7zSD.sfx')
    
    if not os.path.exists(sfx_module):
        print(f"❌ SFX модуль не найден: {sfx_module}")
        return None
    
    # Объединяем SFX модуль + конфиг + архив
    output_exe = 'KrishaParser_Setup.exe'
    
    try:
        with open(output_exe, 'wb') as out:
            # SFX модуль
            with open(sfx_module, 'rb') as f:
                out.write(f.read())
            
            # Конфигурация
            with open('sfx_config.txt', 'rb') as f:
                out.write(f.read())
            
            # Архив
            with open(archive_name, 'rb') as f:
                out.write(f.read())
        
        if os.path.exists(output_exe):
            size_mb = os.path.getsize(output_exe) / (1024 * 1024)
            print(f"✅ SFX установщик создан: {size_mb:.1f} MB")
            return output_exe
        else:
            print("❌ Не удалось создать установщик")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None

def cleanup():
    """Очистка временных файлов."""
    print("\n🧹 Очистка...")
    
    files_to_remove = [
        'install_script.bat',
        'sfx_config.txt',
        'installer_data.7z'
    ]
    
    for file in files_to_remove:
        if os.path.exists(file):
            os.remove(file)

def main():
    """Главная функция."""
    print("=" * 60)
    print("  СОЗДАНИЕ SFX УСТАНОВЩИКА")
    print("  (ОДИН .EXE - АВТОМАТИЧЕСКАЯ УСТАНОВКА)")
    print("=" * 60)
    print()
    
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Проверяем 7-Zip
    print("🔍 Проверка 7-Zip...")
    seven_zip = find_7zip()
    if not seven_zip:
        print("❌ 7-Zip не найден!")
        print("\n📥 Установите 7-Zip:")
        print("  1. Скачайте с https://www.7-zip.org/")
        print("  2. Установите 7-Zip")
        print("  3. Запустите этот скрипт снова")
        return False
    
    print(f"✅ 7-Zip найден: {seven_zip}")
    
    # Проверяем сборку
    if not os.path.exists("dist/KrishaParser"):
        print("\n❌ Сборка не найдена!")
        print("Сначала запустите: python build_protected.py")
        return False
    
    print("✅ Сборка найдена")
    
    # Создаём скрипт установщика
    print("\n📝 Создание скрипта установщика...")
    create_installer_script()
    print("✅ Скрипт создан")
    
    # Создаём конфигурацию SFX
    print("📝 Создание конфигурации SFX...")
    create_sfx_config()
    print("✅ Конфигурация создана")
    
    # Создаём архив
    archive_name = create_archive()
    if not archive_name:
        return False
    
    # Создаём SFX установщик
    installer_exe = create_sfx_installer(archive_name)
    if not installer_exe:
        return False
    
    # Очистка
    cleanup()
    
    print("\n" + "=" * 60)
    print("  🎉 ГОТОВО!")
    print("=" * 60)
    print()
    print(f"📦 ПЕРЕДАЙ ДРУГУ: {installer_exe}")
    print()
    print("📋 ЧТО ДРУГ ДОЛЖЕН СДЕЛАТЬ:")
    print("  1. Запустить .exe файл")
    print("  2. Нажать 'Да' на установку")
    print("  3. Всё! Программа установится автоматически")
    print("  4. Ярлык появится на рабочем столе")
    print()
    print("✅ ОСОБЕННОСТИ:")
    print("  • Один файл")
    print("  • Автоматическая установка")
    print("  • Скрытая папка установки")
    print("  • Не видно процесс установки")
    print("  • Программа запустится сама")
    
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
