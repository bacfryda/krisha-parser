"""
Создаёт ПРОФЕССИОНАЛЬНЫЙ установщик с Inno Setup.
Красивый интерфейс, логотип, правильная установка/удаление.
"""
import os
import sys
import subprocess
import shutil
from PIL import Image, ImageDraw, ImageFont

def create_logo():
    """Создаёт логотип программы."""
    print("🎨 Создание логотипа...")
    
    # Создаём иконку 256x256
    size = 256
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Фон - градиент синий
    for i in range(size):
        color = (30 + i//4, 100 + i//4, 200 - i//4)
        draw.rectangle([0, i, size, i+1], fill=color)
    
    # Рисуем дом (крыша)
    house_color = (255, 255, 255)
    # Крыша
    draw.polygon([(128, 50), (220, 120), (36, 120)], fill=house_color)
    # Стены
    draw.rectangle([60, 120, 196, 220], fill=house_color)
    # Окно
    draw.rectangle([90, 140, 130, 180], fill=(100, 150, 255))
    # Дверь
    draw.rectangle([140, 170, 180, 220], fill=(150, 100, 50))
    
    # Буква K
    try:
        font = ImageFont.truetype("arial.ttf", 80)
    except:
        font = ImageFont.load_default()
    
    draw.text((95, 90), "K", fill=(255, 200, 0), font=font)
    
    # Сохраняем как PNG
    img.save('logo.png', 'PNG')
    
    # Конвертируем в ICO
    img_ico = img.resize((256, 256), Image.Resampling.LANCZOS)
    img_ico.save('logo.ico', format='ICO', sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
    
    print("✅ Логотип создан: logo.ico")
    return 'logo.ico'

def check_inno_setup():
    """Проверяет Inno Setup."""
    possible_paths = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
        r"C:\Program Files\Inno Setup 5\ISCC.exe",
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None

def create_inno_script():
    """Создаёт скрипт Inno Setup."""
    
    current_dir = os.path.abspath(os.getcwd())
    
    script = f'''#define MyAppName "Krisha Parser Bot"
#define MyAppVersion "1.0"
#define MyAppPublisher "Krisha Parser"
#define MyAppURL "https://krisha.kz"
#define MyAppExeName "KrishaParser.exe"

[Setup]
AppId={{{{B8F9C3D2-1A4E-4F5B-9C8D-2E3F4A5B6C7D}}}}
AppName={{#MyAppName}}
AppVersion={{#MyAppVersion}}
AppPublisher={{#MyAppPublisher}}
AppPublisherURL={{#MyAppURL}}
AppSupportURL={{#MyAppURL}}
AppUpdatesURL={{#MyAppURL}}
DefaultDirName={{autopf}}\\KrishaParser
DefaultGroupName={{#MyAppName}}
AllowNoIcons=yes
LicenseFile=
OutputDir={current_dir}
OutputBaseFilename=KrishaParser_Setup_Professional
SetupIconFile={current_dir}\\logo.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={{app}}\\{{#MyAppExeName}}
UninstallDisplayName={{#MyAppName}}
PrivilegesRequired=admin
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "russian"; MessagesFile: "compiler:Languages\\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{{cm:CreateDesktopIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"; Flags: checked
Name: "quicklaunchicon"; Description: "{{cm:CreateQuickLaunchIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"; Flags: unchecked

[Files]
Source: "{current_dir}\\dist\\KrishaParser\\*"; DestDir: "{{app}}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{current_dir}\\wa-server\\package.json"; DestDir: "{{app}}\\wa-server"; Flags: ignoreversion
Source: "{current_dir}\\wa-server\\server.js"; DestDir: "{{app}}\\wa-server"; Flags: ignoreversion

[Icons]
Name: "{{group}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"
Name: "{{autodesktop}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"

[Run]
Filename: "{{app}}\\{{#MyAppExeName}}"; Description: "Launch {{#MyAppName}}"; Flags: nowait postinstall skipifsilent
Name: "{{group}}\\{{cm:UninstallProgram,{{#MyAppName}}}}"; Filename: "{{uninstallexe}}"
Name: "{{autodesktop}}\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"; Tasks: desktopicon; IconFilename: "{current_dir}\\logo.ico"
Name: "{{userappdata}}\\Microsoft\\Internet Explorer\\Quick Launch\\{{#MyAppName}}"; Filename: "{{app}}\\{{#MyAppExeName}}"; Tasks: quicklaunchicon; IconFilename: "{current_dir}\\logo.ico"

[Run]
Filename: "{{cmd}}"; Parameters: "/c npm install"; WorkingDir: "{{app}}\\wa-server"; StatusMsg: "Installing WhatsApp server..."; Flags: runhidden waituntilterminated; Check: NodeJSInstalled
Filename: "{{app}}\\{{#MyAppExeName}}"; Description: "{{cm:LaunchProgram,{{#StringChange(MyAppName, '&', '&&')}}}}"; Flags: nowait postinstall skipifsilent

[Code]
function NodeJSInstalled: Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('cmd.exe', '/c node --version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) and (ResultCode = 0);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    if not NodeJSInstalled then
    begin
      MsgBox('Node.js не установлен. Скачайте с https://nodejs.org/', mbInformation, MB_OK);
    end;
  end;
end;

[UninstallDelete]
Type: filesandordirs; Name: "{{app}}\\wa-server\\node_modules"
Type: filesandordirs; Name: "{{app}}\\wa-server\\wa_auth_data"
Type: filesandordirs; Name: "{{app}}\\sessions"
Type: files; Name: "{{app}}\\*.db"
Type: files; Name: "{{app}}\\*.log"
'''
    
    with open('installer_professional.iss', 'w', encoding='utf-8-sig') as f:
        f.write(script)
    
    print("✅ Скрипт Inno Setup создан")
    return 'installer_professional.iss'

def build_installer(iscc_path, script_file):
    """Собирает установщик."""
    print("\n🔨 Сборка профессионального установщика...")
    print("⏳ Это займёт несколько минут...\n")
    
    try:
        result = subprocess.run(
            [iscc_path, script_file],
            check=True,
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        
        print(result.stdout)
        
        # Проверяем результат
        if os.path.exists('KrishaParser_Setup_Professional.exe'):
            size_mb = os.path.getsize('KrishaParser_Setup_Professional.exe') / (1024 * 1024)
            print(f"\n✅ Установщик создан!")
            print(f"📦 Файл: KrishaParser_Setup_Professional.exe")
            print(f"📏 Размер: {size_mb:.1f} MB")
            return True
        else:
            print("\n❌ Установщик не создан")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Ошибка сборки:")
        print(e.stderr)
        return False

def main():
    """Главная функция."""
    print("=" * 60)
    print("  СОЗДАНИЕ ПРОФЕССИОНАЛЬНОГО УСТАНОВЩИКА")
    print("  С КРАСИВЫМ ИНТЕРФЕЙСОМ И ЛОГОТИПОМ")
    print("=" * 60)
    print()
    
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Проверяем сборку
    if not os.path.exists("dist/KrishaParser"):
        print("❌ Сборка не найдена!")
        print("Сначала запустите: python rebuild_working.py")
        return False
    
    print("✅ Сборка найдена")
    
    # Создаём логотип
    try:
        create_logo()
    except Exception as e:
        print(f"⚠️  Не удалось создать логотип: {e}")
        print("   Продолжаю без логотипа...")
    
    # Проверяем Inno Setup
    print("\n🔍 Проверка Inno Setup...")
    iscc_path = check_inno_setup()
    
    if not iscc_path:
        print("❌ Inno Setup не найден!")
        print("\n📥 УСТАНОВИТЕ INNO SETUP:")
        print("  1. Скачайте с https://jrsoftware.org/isdl.php")
        print("  2. Установите Inno Setup 6")
        print("  3. Запустите этот скрипт снова")
        print("\n⚠️  Без Inno Setup невозможно создать профессиональный установщик")
        return False
    
    print(f"✅ Inno Setup найден: {iscc_path}")
    
    # Создаём скрипт
    print("\n📝 Создание скрипта установщика...")
    script_file = create_inno_script()
    
    # Собираем
    if not build_installer(iscc_path, script_file):
        return False
    
    print("\n" + "=" * 60)
    print("  🎉 ПРОФЕССИОНАЛЬНЫЙ УСТАНОВЩИК ГОТОВ!")
    print("=" * 60)
    print()
    print("📦 ПЕРЕДАЙ ДРУГУ: KrishaParser_Setup_Professional.exe")
    print()
    print("✅ ОСОБЕННОСТИ:")
    print("  • Красивый современный интерфейс")
    print("  • Логотип программы")
    print("  • Выбор языка (русский/английский)")
    print("  • Выбор папки установки")
    print("  • Создание ярлыков (рабочий стол, меню)")
    print("  • Автоматическая установка WhatsApp сервера")
    print("  • Правильное удаление через Панель управления")
    print("  • Прогресс установки")
    print("  • Запуск после установки")
    print()
    print("📋 ЧТО ДРУГ УВИДИТ:")
    print("  1. Красивое окно установки с логотипом")
    print("  2. Выбор языка")
    print("  3. Лицензионное соглашение (опционально)")
    print("  4. Выбор папки установки")
    print("  5. Выбор компонентов")
    print("  6. Прогресс установки")
    print("  7. Завершение с запуском программы")
    
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
