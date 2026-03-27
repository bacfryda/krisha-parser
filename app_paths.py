"""
Централизованное определение путей для Krisha Parser Bot.

При frozen-сборке (PyInstaller):
  - APP_DIR = папка рядом с .exe (для записываемых данных: config, db, sessions)
  - RESOURCE_DIR = sys._MEIPASS (для readonly ресурсов, упакованных внутрь)

При обычном запуске (python main.py):
  - APP_DIR = RESOURCE_DIR = папка со скриптами
"""
import sys
import os


def _get_app_dir() -> str:
    """Рабочая директория приложения — рядом с EXE или рядом с main.py."""
    if getattr(sys, 'frozen', False):
        # PyInstaller: данные храним рядом с exe
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _get_resource_dir() -> str:
    """Директория ресурсов (readonly) — _MEIPASS при frozen, иначе рядом с main.py."""
    if getattr(sys, 'frozen', False):
        return getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


APP_DIR = _get_app_dir()
RESOURCE_DIR = _get_resource_dir()

# При frozen-сборке: Playwright ищет браузеры рядом с exe
if getattr(sys, 'frozen', False):
    pw_browsers = os.path.join(APP_DIR, "ms-playwright")
    if os.path.exists(pw_browsers):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = pw_browsers
