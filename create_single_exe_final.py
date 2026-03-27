"""
Создаёт ОДИН .exe установщик из готовой сборки.
Использует уже рабочую сборку dist/KrishaParser.
"""
import os
import sys
import subprocess

def create_installer_exe():
    """Создаёт установщик с IExpress."""
    print("=" * 60)
    print("  СОЗДАНИЕ ОДНОГО .EXE УСТАНОВЩИКА")
    print("=" * 60)
    print()
    
    # Проверяем сборку
    if not os.path.exists("KrishaParser_Distribution/KrishaParser/KrishaParser.exe"):
        print("❌ Сборка не найдена: KrishaParser_Distribution/KrishaParser/KrishaParser.exe")
        return False
    
    print("✅ Сборка найдена")
    
    # Создаём скрипт установки
    print("\n📝 Создание скрипта установки...")
    
    install_script = '''@echo off
set "INSTALL_DIR=%ProgramFiles%\\KrishaParser"
set "DESKTOP=%USERPROFILE%\\Desktop"
set "TEMP_DIR=%TEMP%\\krisha_temp"

mkdir "%TEMP_DIR%" 2>nul
powershell -Command "Expand-Archive -Path 'data.zip' -DestinationPath '%TEMP_DIR%' -Force"

mkdir "%INSTALL_DIR%" 2>nul
xcopy /E /I /Y /Q "%TEMP_DIR%\\KrishaParser" "%INSTALL_DIR%\\KrishaParser"
xcopy /E /I /Y /Q "%TEMP_DIR%\\wa-server" "%INSTALL_DIR%\\wa-server"

node --version >nul 2>&1
if %errorLevel% equ 0 (
    cd /d "%INSTALL_DIR%\\wa-server"
    call npm install >nul 2>&1
)

powershell -Command "$WshShell = New-Object -ComObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%DESKTOP%\\Krisha Parser.lnk'); $Shortcut.TargetPath = '%INSTALL_DIR%\\KrishaParser\\KrishaParser.exe'; $Shortcut.WorkingDirectory = '%INSTALL_DIR%\\KrishaParser'; $Shortcut.Save()"

rd /s /q "%TEMP_DIR%" 2>nul

start "" "%INSTALL_DIR%\\KrishaParser\\KrishaParser.exe"
'''
    
    with open('install.bat', 'w') as f:
        f.write(install_script)
    
    # Создаём архив данных
    print("📦 Создание архива...")
    import zipfile
    
    with zipfile.ZipFile('data.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Программа
        for root, dirs, files in os.walk("KrishaParser_Distribution/KrishaParser"):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, "KrishaParser_Distribution")
                zipf.write(file_path, arcname)
        
        # wa-server
        for root, dirs, files in os.walk("wa-server"):
            if 'node_modules' in root or 'wa_auth_data' in root:
                continue
            for file in files:
                if file.endswith('.log'):
                    continue
                file_path = os.path.join(root, file)
                zipf.write(file_path, file_path)
    
    print("✅ Архив создан")
    
    # Создаём конфигурацию IExpress
    print("\n📝 Создание конфигурации IExpress...")
    
    current_dir = os.path.abspath(os.getcwd())
    output_path = os.path.join(current_dir, 'KrishaParser_Installer.exe')
    
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
InstallPrompt=Install Krisha Parser Bot?
DisplayLicense=
FinishMessage=
TargetName={output_path}
FriendlyName=Krisha Parser Bot
AppLaunched=cmd /c install.bat
PostInstallCmd=<None>
AdminQuietInstCmd=
UserQuietInstCmd=
SourceFiles=SourceFiles
FILE0="data.zip"
FILE1="install.bat"
[SourceFiles]
SourceFiles0={current_dir}\\
[SourceFiles0]
%FILE0%=
%FILE1%=
'''
    
    with open('config.sed', 'w') as f:
        f.write(config)
    
    # Собираем с IExpress
    print("\n🔨 Сборка установщика...")
    print("⏳ Подождите...\n")
    
    iexpress_path = os.path.join(os.environ['SystemRoot'], 'System32', 'iexpress.exe')
    
    try:
        subprocess.run([iexpress_path, '/N', 'config.sed'], check=True, capture_output=True, timeout=600)
        
        if os.path.exists('KrishaParser_Installer.exe'):
            size_mb = os.path.getsize('KrishaParser_Installer.exe') / (1024 * 1024)
            print(f"✅ Установщик создан!")
            print(f"📦 Файл: KrishaParser_Installer.exe")
            print(f"📏 Размер: {size_mb:.1f} MB")
            
            # Очистка
            os.remove('install.bat')
            os.remove('data.zip')
            os.remove('config.sed')
            
            return True
        else:
            print("❌ Установщик не создан")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def main():
    """Главная функция."""
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    if not create_installer_exe():
        return False
    
    print("\n" + "=" * 60)
    print("  🎉 ГОТОВО!")
    print("=" * 60)
    print()
    print("📦 ФАЙЛ: KrishaParser_Installer.exe")
    print()
    print("Друг запускает .exe → всё устанавливается → ярлык на рабочем столе")
    
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
