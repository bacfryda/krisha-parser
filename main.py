"""Krisha Parser Bot — точка входа."""
import sys
import os


def _first_run_setup():
    """При frozen-сборке: создаёт нужные папки и копирует ресурсы.
    Показывает окно прогресса при первом запуске.
    """
    from app_paths import APP_DIR, RESOURCE_DIR

    # Проверяем нужна ли первоначальная настройка
    wa_dst = os.path.join(APP_DIR, "wa-server")
    config_dst = os.path.join(APP_DIR, "config.json")
    needs_setup = not os.path.exists(wa_dst) or not os.path.exists(config_dst)

    if not needs_setup:
        # Просто создаём sessions если нет
        os.makedirs(os.path.join(APP_DIR, "sessions"), exist_ok=True)
        return

    # ── Показываем splash-окно ──
    from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QProgressBar
    from PyQt6.QtCore import Qt, QTimer
    from PyQt6.QtGui import QFont

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    splash = QWidget()
    splash.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
    splash.setFixedSize(420, 180)
    splash.setStyleSheet("background: #1e1e2e; border: 2px solid #00a884; border-radius: 12px;")

    lay = QVBoxLayout(splash)
    lay.setContentsMargins(30, 25, 30, 25)
    lay.setSpacing(12)

    icon_lbl = QLabel("K")
    icon_lbl.setFixedSize(36, 36)
    icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    icon_lbl.setStyleSheet(
        "background: #00a884; color: white; border-radius: 8px; "
        "font-size: 18px; font-weight: bold; border: none;"
    )
    lay.addWidget(icon_lbl, 0, Qt.AlignmentFlag.AlignCenter)

    title = QLabel("Krisha Parser Bot")
    title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    title.setStyleSheet("color: #cdd6f4; font-size: 16px; font-weight: bold; border: none;")
    lay.addWidget(title)

    status = QLabel("Первый запуск — подготовка файлов...")
    status.setAlignment(Qt.AlignmentFlag.AlignCenter)
    status.setStyleSheet("color: #a6adc8; font-size: 11px; border: none;")
    lay.addWidget(status)

    bar = QProgressBar()
    bar.setFixedHeight(6)
    bar.setRange(0, 0)  # indeterminate
    bar.setTextVisible(False)
    bar.setStyleSheet("""
        QProgressBar { background: #313244; border: none; border-radius: 3px; }
        QProgressBar::chunk { background: #00a884; border-radius: 3px; }
    """)
    lay.addWidget(bar)

    # Центрируем на экране
    screen = app.primaryScreen().geometry()
    splash.move(
        (screen.width() - splash.width()) // 2,
        (screen.height() - splash.height()) // 2,
    )
    splash.show()
    app.processEvents()

    # ── Копируем ресурсы ──
    import shutil

    # 1. sessions
    status.setText("Создание папки сессий...")
    app.processEvents()
    os.makedirs(os.path.join(APP_DIR, "sessions"), exist_ok=True)

    # 2. config.json
    if not os.path.exists(config_dst):
        config_src = os.path.join(RESOURCE_DIR, "config.json")
        if os.path.exists(config_src):
            status.setText("Копирование конфигурации...")
            app.processEvents()
            shutil.copy2(config_src, config_dst)

    # 3. wa-server (самое долгое — node_modules)
    if not os.path.exists(wa_dst):
        wa_src = os.path.join(RESOURCE_DIR, "wa-server")
        if os.path.exists(wa_src):
            status.setText("Установка WhatsApp сервера (это может занять минуту)...")
            app.processEvents()
            shutil.copytree(wa_src, wa_dst)

    # 4. logo файлы
    for logo_file in ("logo.ico", "logo.png"):
        dst = os.path.join(APP_DIR, logo_file)
        if not os.path.exists(dst):
            src = os.path.join(RESOURCE_DIR, logo_file)
            if os.path.exists(src):
                shutil.copy2(src, dst)

    status.setText("Готово! Запуск приложения...")
    app.processEvents()

    # Закрываем splash
    splash.close()
    splash.deleteLater()


def main():
    # Первоначальная настройка при frozen-запуске
    if getattr(sys, 'frozen', False):
        _first_run_setup()

    if "--cli" in sys.argv:
        # CLI режим (оставлен как fallback)
        from cli import main as cli_main
        cli_main()
    else:
        # GUI режим (по умолчанию)
        from gui import run_gui
        run_gui()


if __name__ == "__main__":
    main()
