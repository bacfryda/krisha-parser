"""
Скрипт сборки Krisha Parser Bot в инсталлятор.

Шаг 1: PyInstaller → exe + _internal/
Шаг 2: Копирование wa-server + встроенный Node.js
Шаг 3: Playwright browsers
Шаг 4: Inno Setup скрипт

Запуск: python build_release.py
"""
import subprocess
import sys
import os
import shutil
import urllib.request
import zipfile
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST = os.path.join(ROOT, "dist", "KrishaParser")
BUILD = os.path.join(ROOT, "build")

PYTHON_FILES = [
    "main.py", "gui.py", "parser_playwright.py", "config.py",
    "database.py", "captcha_solver.py", "ai_bot.py", "wa_client.py",
    "app_paths.py",
]

DATA_FILES = [
    "config.json", "logo.ico", "logo.png",
]


def step1_pyinstaller():
    """Собираем exe через PyInstaller."""
    print("=" * 60)
    print("ШАГ 1: PyInstaller")
    print("=" * 60)

    # Чистим старую сборку
    for d in [DIST, BUILD]:
        if os.path.exists(d):
            shutil.rmtree(d)

    # Формируем --add-data для ресурсов
    add_data = []
    for f in DATA_FILES:
        src = os.path.join(ROOT, f)
        if os.path.exists(src):
            add_data.extend(["--add-data", f"{src};."])

    # Включаем JS файлы playwright_stealth
    try:
        import playwright_stealth
        stealth_dir = os.path.dirname(playwright_stealth.__file__)
        stealth_js = os.path.join(stealth_dir, "js")
        if os.path.exists(stealth_js):
            add_data.extend(["--add-data", f"{stealth_js};playwright_stealth/js"])
    except ImportError:
        print("⚠️ playwright_stealth не найден")

    # Включаем JS файлы playwright_recaptcha (если есть data файлы)
    try:
        import playwright_recaptcha
        recaptcha_dir = os.path.dirname(playwright_recaptcha.__file__)
        add_data.extend(["--add-data", f"{recaptcha_dir};playwright_recaptcha"])
    except ImportError:
        pass

    # Скрытые импорты
    hidden = [
        "--hidden-import", "playwright",
        "--hidden-import", "playwright.sync_api",
        "--hidden-import", "playwright_recaptcha",
        "--hidden-import", "playwright_recaptcha.recaptchav2",
        "--hidden-import", "bs4",
        "--hidden-import", "requests",
        "--hidden-import", "openpyxl",
        "--hidden-import", "pydub",
        "--hidden-import", "speech_recognition",
    ]

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        "--name", "KrishaParser",
        "--icon", os.path.join(ROOT, "logo.ico"),
        *add_data,
        *hidden,
        os.path.join(ROOT, "main.py"),
    ]

    print(f"Команда: {' '.join(cmd[:10])}...")
    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        print("ОШИБКА: PyInstaller не удался!")
        sys.exit(1)

    print("✅ PyInstaller завершён")


def step2_copy_wa_server():
    """Копируем wa-server в dist."""
    print("\n" + "=" * 60)
    print("ШАГ 2: Копирование wa-server")
    print("=" * 60)

    wa_src = os.path.join(ROOT, "wa-server")
    wa_dst = os.path.join(DIST, "wa-server")

    if os.path.exists(wa_dst):
        shutil.rmtree(wa_dst)

    if not os.path.exists(wa_src):
        print("ОШИБКА: wa-server не найден!")
        sys.exit(1)

    # Копируем только нужное (без логов и кэша)
    def ignore_fn(directory, files):
        ignored = set()
        for f in files:
            if f in ("wa_server.log", "wa_auth_data", ".cache", "node_modules"):
                # node_modules нужен, но wa_auth_data — нет
                if f == "wa_auth_data":
                    ignored.add(f)
                elif f == "wa_server.log":
                    ignored.add(f)
            if f.endswith(".log"):
                ignored.add(f)
        return ignored

    shutil.copytree(wa_src, wa_dst, ignore=ignore_fn)
    print(f"✅ wa-server скопирован ({wa_dst})")

    # Встраиваем node.exe в wa-server
    _bundle_node(wa_dst)


NODE_VERSION = "22.16.0"  # LTS


def _bundle_node(wa_dst: str):
    """Скачивает node.exe (Windows x64) и кладёт в wa-server."""
    node_dst = os.path.join(wa_dst, "node.exe")
    if os.path.isfile(node_dst):
        print("  node.exe уже есть, пропускаю")
        return

    zip_name = f"node-v{NODE_VERSION}-win-x64.zip"
    url = f"https://nodejs.org/dist/v{NODE_VERSION}/{zip_name}"
    print(f"  Скачиваю Node.js v{NODE_VERSION}...")

    tmp = tempfile.mkdtemp()
    zip_path = os.path.join(tmp, zip_name)
    try:
        urllib.request.urlretrieve(url, zip_path)
        with zipfile.ZipFile(zip_path, "r") as zf:
            # Ищем node.exe внутри архива
            node_entry = None
            for name in zf.namelist():
                if name.endswith("/node.exe"):
                    node_entry = name
                    break
            if not node_entry:
                print("  ⚠️ node.exe не найден в архиве")
                return
            # Извлекаем только node.exe
            with zf.open(node_entry) as src, open(node_dst, "wb") as dst:
                shutil.copyfileobj(src, dst)
        print(f"  ✅ node.exe встроен ({os.path.getsize(node_dst) // (1024*1024)} МБ)")
    except Exception as e:
        print(f"  ⚠️ Не удалось скачать Node.js: {e}")
        print("  Пользователю потребуется установить Node.js вручную")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def step3_copy_playwright_browsers():
    """Копируем Playwright browsers."""
    print("\n" + "=" * 60)
    print("ШАГ 3: Playwright browsers")
    print("=" * 60)

    # Playwright хранит браузеры в %LOCALAPPDATA%\ms-playwright
    local_app = os.environ.get("LOCALAPPDATA", "")
    pw_browsers = os.path.join(local_app, "ms-playwright")

    if not os.path.exists(pw_browsers):
        print("⚠️ Playwright browsers не найдены в", pw_browsers)
        print("   Запустите: playwright install chromium")
        return

    dst = os.path.join(DIST, "ms-playwright")
    if os.path.exists(dst):
        shutil.rmtree(dst)

    # Копируем только chromium
    for item in os.listdir(pw_browsers):
        if "chromium" in item.lower():
            src_path = os.path.join(pw_browsers, item)
            dst_path = os.path.join(dst, item)
            print(f"  Копирую {item}...")
            shutil.copytree(src_path, dst_path)

    if os.path.exists(dst):
        print(f"✅ Playwright browsers скопированы")
    else:
        print("⚠️ Chromium не найден в ms-playwright")


def step4_create_inno_script():
    """Создаём Inno Setup скрипт."""
    print("\n" + "=" * 60)
    print("ШАГ 4: Создание Inno Setup скрипта")
    print("=" * 60)

    iss_content = r"""
[Setup]
AppName=Krisha Parser Bot
AppVersion=3.0
AppPublisher=KrishaParser
DefaultDirName={autopf}\KrishaParser
DefaultGroupName=Krisha Parser Bot
OutputDir=..\installer_output
OutputBaseFilename=KrishaParser_Setup
Compression=lzma2/ultra64
SolidCompression=yes
SetupIconFile=..\logo.ico
UninstallDisplayIcon={app}\KrishaParser.exe
PrivilegesRequired=lowest
WizardStyle=modern

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительно:"

[Files]
Source: "KrishaParser\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Krisha Parser Bot"; Filename: "{app}\KrishaParser.exe"
Name: "{autodesktop}\Krisha Parser Bot"; Filename: "{app}\KrishaParser.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\KrishaParser.exe"; Description: "Запустить Krisha Parser Bot"; Flags: nowait postinstall skipifsilent
"""

    iss_path = os.path.join(ROOT, "dist", "installer.iss")
    with open(iss_path, "w", encoding="utf-8") as f:
        f.write(iss_content.strip())

    print(f"✅ Inno Setup скрипт создан: {iss_path}")
    print()
    print("Для создания инсталлятора:")
    print(f'  1. Установите Inno Setup: https://jrsoftware.org/isdl.php')
    print(f'  2. Откройте {iss_path} в Inno Setup')
    print(f'  3. Нажмите Compile (Ctrl+F9)')
    print(f'  4. Инсталлятор появится в dist/installer_output/')


def main():
    print("🏗️ Сборка Krisha Parser Bot")
    print()

    step1_pyinstaller()
    step2_copy_wa_server()
    step3_copy_playwright_browsers()
    step4_create_inno_script()

    print("\n" + "=" * 60)
    print("✅ СБОРКА ЗАВЕРШЕНА")
    print("=" * 60)
    print(f"\nПапка сборки: {DIST}")
    print(f"Для теста: запустите {os.path.join(DIST, 'KrishaParser.exe')}")


if __name__ == "__main__":
    main()
