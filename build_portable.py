"""
Сборка Krisha Parser Bot в портативный EXE через PyInstaller.

Результат: dist/KrishaParser/ — папка с KrishaParser.exe и всеми зависимостями.

Запуск:
    python build_portable.py
"""
import os
import sys
import shutil
import subprocess

ROOT = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(ROOT, "dist", "KrishaParser")


def check_pyinstaller():
    """Проверяет наличие PyInstaller."""
    try:
        import PyInstaller
        return True
    except ImportError:
        print("❌ PyInstaller не установлен!")
        print("   pip install pyinstaller")
        return False


def build():
    """Запускает PyInstaller сборку."""
    print("=" * 60)
    print("🔨 Сборка Krisha Parser Bot")
    print("=" * 60)

    if not check_pyinstaller():
        return False

    # Определяем разделитель для --add-data (Windows = ;  Unix = :)
    sep = ";" if sys.platform == "win32" else ":"

    # Файлы данных для включения в сборку
    datas = [
        f"config.json{sep}.",
        f"logo.ico{sep}.",
        f"logo.png{sep}.",
    ]

    # wa-server целиком (server.js + node_modules)
    wa_server_path = os.path.join(ROOT, "wa-server")
    if os.path.exists(wa_server_path):
        datas.append(f"wa-server{sep}wa-server")
    else:
        print(f"⚠️ wa-server не найден: {wa_server_path}")

    # Все Python модули проекта как hidden imports
    hidden_imports = [
        # Проектные модули
        "app_paths",
        "license_check",
        "config",
        "database",
        "parser",
        "parser_playwright",
        "parser_headless",
        "parser_webengine",
        "browser",
        "captcha_solver",
        "ai_bot",
        "wa_client",
        "wa_controller",
        "wa_web",
        "whatsapp",
        "gui",
        # PyQt6
        "PyQt6",
        "PyQt6.QtCore",
        "PyQt6.QtGui",
        "PyQt6.QtWidgets",
        "PyQt6.sip",
        # Selenium / UC
        "selenium",
        "selenium.webdriver",
        "selenium.webdriver.common.by",
        "selenium.webdriver.common.keys",
        "selenium.webdriver.common.action_chains",
        "selenium.webdriver.support.ui",
        "selenium.webdriver.support.expected_conditions",
        "selenium.webdriver.chrome.service",
        "selenium.webdriver.chrome.options",
        "undetected_chromedriver",
        "undetected_chromedriver.patcher",
        # Другие зависимости
        "requests",
        "bs4",
        "beautifulsoup4",
        "openai",
        "rich",
        "rich.console",
        "questionary",
        "sqlite3",
        "json",
        "base64",
        "ctypes",
        "ctypes.wintypes",
    ]

    # Формируем команду
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",           # Без консоли
        "--name=KrishaParser",
    ]

    # Иконка
    icon_path = os.path.join(ROOT, "logo.ico")
    if os.path.exists(icon_path):
        cmd.append(f"--icon={icon_path}")

    # Data files
    for d in datas:
        cmd.extend(["--add-data", d])

    # Hidden imports
    for h in hidden_imports:
        cmd.extend(["--hidden-import", h])

    # Собираем все подмодули PyQt6
    cmd.extend(["--collect-submodules", "PyQt6"])
    cmd.extend(["--collect-submodules", "undetected_chromedriver"])

    # Точка входа
    cmd.append("main.py")

    print(f"\n📦 Команда: {' '.join(cmd[:10])}...")
    print(f"   Data files: {len(datas)}")
    print(f"   Hidden imports: {len(hidden_imports)}")
    print()

    # Запускаем сборку
    result = subprocess.run(cmd, cwd=ROOT)

    if result.returncode != 0:
        print(f"\n❌ Сборка завершилась с ошибкой (код {result.returncode})")
        return False

    print(f"\n✅ Сборка завершена!")
    print(f"📁 Результат: {DIST_DIR}")

    # Проверяем результат
    exe_path = os.path.join(DIST_DIR, "KrishaParser.exe")
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"📦 KrishaParser.exe: {size_mb:.1f} MB")
    else:
        print(f"⚠️ EXE не найден: {exe_path}")
        return False

    return True


def main():
    if not build():
        sys.exit(1)

    print("\n" + "=" * 60)
    print("✅ Готово! Теперь запустите install.py для установки:")
    print("   python install.py")
    print("=" * 60)


if __name__ == "__main__":
    main()
