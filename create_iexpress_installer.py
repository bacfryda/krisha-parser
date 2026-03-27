"""
Создаёт самораспаковывающийся установщик с помощью IExpress (встроен в Windows).
ОДИН .exe файл - автоматическая скрытая установка.
"""
import os
import sys
import subprocess
import shutil
import zipfile

def create_installer_script():
    """Создаёт скрипт установщика."""
    script = '''@echo off
:: Скрытая установка без вывода
set "INSTALL_DIR=%ProgramFiles%\\KrishaParser"
set "DESKTOP=%USERPROFILE%\\Desktop"
set "TEMP_DIR=%TEMP%\\krisha_install"

:: Создаём временную папку
if not exist "%TEMP_DIR%" mkdir "%TEMP_DIR%"

:: Распаковываем архив
powershell -Command "Expand-Archive -Path 'installer_package.zip' -DestinationPath '%TEMP_DIR%' -Force" >nul 2>&1

:: Создаём папку установки
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: Копируем файлы из временной папки
xcopy /E /I /Y /Q "%TEMP_DIR%\\KrishaParser" "%INSTALL_DIR%\\KrishaParser" >nul 2>&1
xcopy /E /I /Y /Q "%TEMP_DIR%\\wa-server" "%INSTALL_DIR%\\wa-server" >nul 2>&1

:: Проверка Node.js и установка npm
node --version >nul 2>&1
if %errorLevel% equ 0 (
    cd /d "%INSTALL_DIR%\\wa-server"
    call npm install >nul 2>&1
)

:: Создаём ярлык на рабочем столе
powershell -WindowStyle Hidden -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%DESKTOP%\\Krisha Parser.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\\KrishaParser\\KrishaParser.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%\\KrishaParser'; $Shortcut.Description = 'Krisha Parser Bot'; $Shortcut.Save()" 2>nul

:: Скрываем папку установки от посторонних глаз
attrib +h "%INSTALL_DIR%" 2>nul

:: Очистка временных файлов
rd /s /q "%TEMP_DIR%" 2>nul

:: Запускаем программу
start "" "%INSTALL_DIR%\\KrishaParser\\KrishaParser.exe"

exit
'''
    
    with open('install.bat', 'w', encoding='cp1251') as f:
        f.write(script)
    
    return 'install.bat'

def create_archive():
    """Создаёт архив с программой."""
    print("📦 Создание архива...")
    
    archive_name = 'installer_package.zip'
    
    with zipfile.ZipFile(archive_name, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
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
        
        # Добавляем скрипт установки
        print("  + install.bat")
        zipf.write('install.bat', 'install.bat')
    
    size_mb = os.path.getsize(archive_name) / (1024 * 1024)
    print(f"✅ Архив создан: {size_mb:.1f} MB")
    
    return archive_name

def create_iexpress_config():
    """Создаёт конфигурацию для IExpress."""
    
    # Получаем абсолютные пути
    current_dir = os.path.abspath(os.getcwd())
    archive_path = os.path.join(current_dir, 'installer_package.zip')
    output_path = os.path.join(current_dir, 'KrishaParser_Setup.exe')
    
    config = f'''[Version]
Class=IEXPRESS
SEDVersion=3
[Options]
PackagePurpose=InstallApp
ShowInstallProgramWindow=0
HideExtractAnimation=1
UseLongFileName=1
InsideCompressed=0
CAB_FixedSize=0
CAB_ResvCodeSigning=0
RebootMode=N
InstallPrompt=%InstallPrompt%
DisplayLicense=%DisplayLicense%
FinishMessage=%FinishMessage%
TargetName=%TargetName%
FriendlyName=%FriendlyName%
AppLaunched=%AppLaunched%
PostInstallCmd=%PostInstallCmd%
AdminQuietInstCmd=%AdminQuietInstCmd%
UserQuietInstCmd=%UserQuietInstCmd%
SourceFiles=SourceFiles
[Strings]
InstallPrompt=Install Krisha Parser Bot?
DisplayLicense=
FinishMessage=
TargetName={output_path}
FriendlyName=Krisha Parser Bot Installer
AppLaunched=cmd /c install.bat
PostInstallCmd=<None>
AdminQuietInstCmd=
UserQuietInstCmd=
FILE0="installer_package.zip"
FILE1="install.bat"
[SourceFiles]
SourceFiles0={current_dir}\\
[SourceFiles0]
%FILE0%=
%FILE1%=
'''
    
    with open('iexpress_config.sed', 'w', encoding='cp1251') as f:
        f.write(config)
    
    return 'iexpress_config.sed'

def build_with_iexpress(config_file):
    """Собирает установщик с помощью IExpress."""
    print("\n🔨 Сборка установщика с IExpress...")
    print("⏳ Это займёт несколько минут...")
    
    # IExpress встроен в Windows
    iexpress_path = os.path.join(os.environ['SystemRoot'], 'System32', 'iexpress.exe')
    
    if not os.path.exists(iexpress_path):
        print(f"❌ IExpress не найден: {iexpress_path}")
        return False
    
    # Запускаем IExpress
    cmd = [iexpress_path, '/N', config_file]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=600)
        
        # Проверяем результат
        if os.path.exists('KrishaParser_Setup.exe'):
            size_mb = os.path.getsize('KrishaParser_Setup.exe') / (1024 * 1024)
            print(f"\n✅ Установщик создан!")
            print(f"📦 Файл: KrishaParser_Setup.exe")
            print(f"📏 Размер: {size_mb:.1f} MB")
            return True
        else:
            print("\n❌ Установщик не создан")
            return False
            
    except subprocess.TimeoutExpired:
        print("\n❌ Превышено время ожидания")
        return False
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Ошибка сборки: {e}")
        print(f"Вывод: {e.output}")
        return False
    except Exception as e:
        print(f"\n❌ Неожиданная ошибка: {e}")
        return False

def cleanup():
    """Очистка временных файлов."""
    print("\n🧹 Очистка...")
    
    files_to_remove = [
        'install.bat',
        'installer_package.zip',
        'iexpress_config.sed'
    ]
    
    for file in files_to_remove:
        if os.path.exists(file):
            try:
                os.remove(file)
            except:
                pass

def main():
    """Главная функция."""
    print("=" * 60)
    print("  СОЗДАНИЕ АВТОМАТИЧЕСКОГО УСТАНОВЩИКА")
    print("  (ОДИН .EXE - СКРЫТАЯ УСТАНОВКА)")
    print("=" * 60)
    print()
    
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Проверяем сборку
    if not os.path.exists("dist/KrishaParser"):
        print("❌ Сборка не найдена!")
        print("Сначала запустите: python build_protected.py")
        return False
    
    print("✅ Сборка найдена")
    
    # Создаём скрипт установщика
    print("\n📝 Создание скрипта установщика...")
    create_installer_script()
    print("✅ Скрипт создан")
    
    # Создаём архив
    archive_name = create_archive()
    if not archive_name:
        return False
    
    # Создаём конфигурацию IExpress
    print("\n📝 Создание конфигурации IExpress...")
    config_file = create_iexpress_config()
    print("✅ Конфигурация создана")
    
    # Собираем установщик
    if not build_with_iexpress(config_file):
        return False
    
    # Очистка
    cleanup()
    
    print("\n" + "=" * 60)
    print("  🎉 ГОТОВО!")
    print("=" * 60)
    print()
    print("📦 ПЕРЕДАЙ ДРУГУ: KrishaParser_Setup.exe")
    print()
    print("📋 ЧТО ДРУГ ДОЛЖЕН СДЕЛАТЬ:")
    print("  1. Запустить KrishaParser_Setup.exe")
    print("  2. Нажать 'Да' на вопрос об установке")
    print("  3. ВСЁ! Программа установится автоматически")
    print()
    print("✅ ОСОБЕННОСТИ:")
    print("  • ОДИН файл .exe")
    print("  • Автоматическая установка")
    print("  • Скрытая папка (C:\\Program Files\\KrishaParser)")
    print("  • Не видно процесс установки")
    print("  • Ярлык на рабочем столе")
    print("  • Программа запустится сама")
    print("  • Папка скрыта от посторонних глаз")
    print()
    print("⚠️  ВАЖНО:")
    print("  • Программа работает до 30 марта 2026")
    print("  • Папка установки скрыта (attrib +h)")
    print("  • Не видна в проводнике без показа скрытых файлов")
    
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
