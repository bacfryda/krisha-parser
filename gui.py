"""
Krisha Parser Bot — 3 режима:
  1. Парсинг — браузер Krisha.kz, парсит и сохраняет в БД
  2. Рассылка — WhatsApp Web (визуал) + wa-server (отправка)
  3. AI Риелтор — WhatsApp Web + wa-server + DeepSeek AI бот
"""
import sys, os, time, subprocess, base64, threading
from app_paths import APP_DIR
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QTabWidget, QPushButton, QLabel, QTextEdit,
    QGroupBox, QFormLayout, QLineEdit, QCheckBox, QComboBox,
    QSpinBox, QListWidget, QListWidgetItem, QProgressBar, QFrame, QStackedWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QScrollArea,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap, QColor

from config import (
    load_config, save_config,
    REGIONS, BUILDING_TYPES, TOILET_TYPES, PHONE_LINE_TYPES,
    MORTGAGE_OPTIONS, PRIV_DORM_OPTIONS,
)
from database import (
    init_db, add_phone, mark_sent, mark_no_whatsapp, get_unsent_phones,
    get_all_phones, get_stats, get_sent_today_count,
    add_conversation, mark_replied,
    is_url_parsed, mark_url_parsed, is_phone_exists,
    get_conversation_full, get_all_conversations_phones,
    clear_conversation, clear_all_conversations, mark_chat_read,
    clear_parsed_urls,
)
from parser_playwright import (
    get_listings, extract_phone, close_driver,
    _get_driver as get_playwright_driver, CHROME_WINDOW_MARKER,
    is_logged_in as is_krisha_logged_in, open_login_page as open_krisha_login,
    save_session_if_logged as save_krisha_session,
    login_krisha as krisha_login,
)
from ai_bot import generate_first_message
import wa_client

SESSION_DIR = os.path.join(APP_DIR, "sessions")


def _normalize_phone(phone: str) -> str:
    """Нормализует номер телефона — всегда с +."""
    phone = phone.strip()
    if phone and not phone.startswith('+'):
        phone = '+' + phone
    return phone


def _styled_confirm(parent, title: str, text: str) -> bool:
    """Кастомный диалог подтверждения в стиле приложения (без Windows-хрома)."""
    from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel

    dlg = QDialog(parent)
    dlg.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
    dlg.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    dlg.setModal(True)

    # Внешний контейнер с тенью
    outer = QWidget(dlg)
    outer.setStyleSheet("""
        QWidget { background: #1e1e2e; border: 1px solid #45475a; border-radius: 10px; }
    """)
    dlg_root = QVBoxLayout(dlg)
    dlg_root.setContentsMargins(0, 0, 0, 0)
    dlg_root.addWidget(outer)

    lay = QVBoxLayout(outer)
    lay.setContentsMargins(24, 20, 24, 20)
    lay.setSpacing(16)

    # Заголовок
    lbl_title = QLabel(title)
    lbl_title.setStyleSheet("color: #cdd6f4; font-size: 15px; font-weight: bold; background: transparent; border: none;")
    lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lay.addWidget(lbl_title)

    # Текст
    lbl_text = QLabel(text)
    lbl_text.setStyleSheet("color: #a6adc8; font-size: 12px; background: transparent; border: none;")
    lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl_text.setWordWrap(True)
    lay.addWidget(lbl_text)

    # Кнопки
    btn_row = QWidget()
    btn_row.setStyleSheet("background: transparent; border: none;")
    bl = QHBoxLayout(btn_row)
    bl.setContentsMargins(0, 0, 0, 0)
    bl.setSpacing(12)

    btn_no = QPushButton("Отмена")
    btn_no.setFixedHeight(34)
    btn_no.setMinimumWidth(100)
    btn_no.setStyleSheet("""
        QPushButton { background: #313244; color: #cdd6f4; border: 1px solid #45475a;
                      border-radius: 6px; font-size: 12px; padding: 0 16px; }
        QPushButton:hover { background: #45475a; }
    """)
    btn_no.clicked.connect(dlg.reject)

    btn_yes = QPushButton("Подтвердить")
    btn_yes.setFixedHeight(34)
    btn_yes.setMinimumWidth(100)
    btn_yes.setStyleSheet("""
        QPushButton { background: #00a884; color: #ffffff; border: none;
                      border-radius: 6px; font-size: 12px; font-weight: bold; padding: 0 16px; }
        QPushButton:hover { background: #06cf9c; }
    """)
    btn_yes.clicked.connect(dlg.accept)
    btn_yes.setDefault(True)

    bl.addStretch()
    bl.addWidget(btn_no)
    bl.addWidget(btn_yes)
    bl.addStretch()
    lay.addWidget(btn_row)

    dlg.setFixedWidth(360)
    dlg.adjustSize()
    return dlg.exec() == 1


def _styled_info(parent, title: str, text: str):
    """Кастомный информационный диалог в стиле приложения."""
    from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel

    dlg = QDialog(parent)
    dlg.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
    dlg.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    dlg.setModal(True)

    outer = QWidget(dlg)
    outer.setStyleSheet("""
        QWidget { background: #1e1e2e; border: 1px solid #45475a; border-radius: 10px; }
    """)
    dlg_root = QVBoxLayout(dlg)
    dlg_root.setContentsMargins(0, 0, 0, 0)
    dlg_root.addWidget(outer)

    lay = QVBoxLayout(outer)
    lay.setContentsMargins(24, 20, 24, 20)
    lay.setSpacing(16)

    lbl_title = QLabel(title)
    lbl_title.setStyleSheet("color: #cdd6f4; font-size: 15px; font-weight: bold; background: transparent; border: none;")
    lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lay.addWidget(lbl_title)

    lbl_text = QLabel(text)
    lbl_text.setStyleSheet("color: #a6adc8; font-size: 12px; background: transparent; border: none;")
    lbl_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl_text.setWordWrap(True)
    lay.addWidget(lbl_text)

    btn_ok = QPushButton("OK")
    btn_ok.setFixedHeight(34)
    btn_ok.setFixedWidth(120)
    btn_ok.setStyleSheet("""
        QPushButton { background: #00a884; color: #ffffff; border: none;
                      border-radius: 6px; font-size: 12px; font-weight: bold; }
        QPushButton:hover { background: #06cf9c; }
    """)
    btn_ok.clicked.connect(dlg.accept)

    btn_wrap = QHBoxLayout()
    btn_wrap.addStretch()
    btn_wrap.addWidget(btn_ok)
    btn_wrap.addStretch()
    lay.addLayout(btn_wrap)

    dlg.setFixedWidth(360)
    dlg.adjustSize()
    dlg.exec()


class MainWindow(QMainWindow):
    MODE_PARSE = 0
    MODE_WA = 1

    # Сигнал для передачи статуса wa-server из фонового потока в GUI
    _wa_status_signal = pyqtSignal(dict)
    # Сигнал для логирования из фонового потока
    _log_signal = pyqtSignal(str)
    # Сигнал для выполнения callable в GUI потоке
    _invoke_signal = pyqtSignal(object)
    # Сигнал для обновления мессенджера из фонового потока
    _refresh_messenger_signal = pyqtSignal()
    # Сигнал для результатов парсинга из фонового потока
    _parse_result_signal = pyqtSignal(list)
    # Сигнал для результата извлечения телефона
    _phone_result_signal = pyqtSignal(str, dict)  # phone_or_empty, listing
    # Сигнал: Chrome запущен, можно встраивать
    _chrome_ready_signal = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        init_db()

        # Информация об экране и DPI
        screen_info = self._get_screen_info()
        self._screen_info = screen_info
        self._dpi_scale = screen_info["dpi_scale"]
        self._initial_viewport = (screen_info["width"], screen_info["height"])

        # Состояние
        self._parsing = False
        self._parse_stop = False
        self._parse_listings = []
        self._parse_index = 0
        self._parse_new_count = 0
        self._parse_thread = None
        self._mail_queue = []
        self._mail_idx = 0
        self._mail_stop = False
        self._current_mode = self.MODE_PARSE
        self.krisha_authorized = False
        self.wa_server_ready = False
        self._wa_process = None
        self._qr_dialog = None

        # Автозапуск wa-server
        self._start_wa_server()

        # Подключаем сигнал wa-server статуса
        self._wa_status_signal.connect(self._on_wa_status)
        self._log_signal.connect(self.log)
        self._invoke_signal.connect(self._on_invoke)
        self._refresh_messenger_signal.connect(self._after_sync)
        self._parse_result_signal.connect(self._on_parse_listings_ready)
        self._phone_result_signal.connect(self._on_phone_extracted)
        self._chrome_ready_signal.connect(self._embed_chrome)

        self.setWindowTitle("Krisha Parser Bot v3.0")
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setMinimumSize(900, 600)
        self._drag_pos = None
        self._build_ui()
        self._apply_styles()

        # Таймеры
        self.auth_timer = QTimer()
        self.auth_timer.timeout.connect(self._check_auth)
        self.auth_timer.start(10000)

        self.wa_check_timer = QTimer()
        self.wa_check_timer.timeout.connect(self._poll_wa_server)
        self.wa_check_timer.start(5000)

        self.popup_timer = QTimer()
        self.popup_timer.timeout.connect(self._kill_popups)
        self.popup_timer.start(15000)

        # Таймер синхронизации входящих (всегда работает когда WA подключён)
        self.sync_timer = QTimer()
        self.sync_timer.timeout.connect(self._sync_incoming_tick)

        # Таймер обновления мессенджера (GUI-поток, гарантированно работает)
        self._msg_refresh_timer = QTimer()
        self._msg_refresh_timer.timeout.connect(self._messenger_auto_refresh)
        self._msg_needs_refresh = False

        self.log("🏠 Krisha Parser Bot v3.0 запущен")
        self.log("⏳ Запуск wa-server...")
        self._update_mode_ui()

        # Запускаем Chrome в фоне и встраиваем в приложение
        self._chrome_hwnd = None
        self._chrome_embedded = False
        self._embed_retries = 0
        self._launch_chrome_bg()

        # Показать диалог авторизации через 4 сек (дать время на автоавторизацию)
        QTimer.singleShot(4000, self._show_auth_dialog)

    # ═══════════════════════════════════════════════════════════════
    #  WA-Server (автозапуск + QR)
    # ═══════════════════════════════════════════════════════════════

    def _start_wa_server(self):
        """Запускает node server.js как фоновый процесс."""
        # Убиваем старый процесс на порту 3457 если остался
        if sys.platform == "win32":
            try:
                result = subprocess.run(
                    ["netstat", "-ano"],
                    capture_output=True, text=True, timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                for line in result.stdout.splitlines():
                    if ":3457" in line and "LISTENING" in line:
                        parts = line.split()
                        pid = parts[-1]
                        if pid.isdigit():
                            subprocess.run(
                                ["taskkill", "/F", "/PID", pid],
                                capture_output=True, timeout=5,
                                creationflags=subprocess.CREATE_NO_WINDOW,
                            )
                        break
            except Exception:
                pass

        wa_dir = os.path.join(APP_DIR, "wa-server")

        # Удаляем lock-файлы Puppeteer (остаются после аварийного завершения)
        session_dir = os.path.join(wa_dir, "wa_auth_data", "session")
        for lock_name in ("SingletonLock", "SingletonSocket", "SingletonCookie", "lockfile"):
            lock_file = os.path.join(session_dir, lock_name)
            try:
                if os.path.exists(lock_file):
                    os.remove(lock_file)
            except Exception:
                pass

        # Убиваем зависшие headless Chrome процессы от wa-server
        if sys.platform == "win32":
            try:
                result = subprocess.run(
                    ["wmic", "process", "where",
                     "commandline like '%wa_auth_data%' and name='chrome.exe'",
                     "get", "processid"],
                    capture_output=True, text=True, timeout=5,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                for line in result.stdout.splitlines():
                    pid = line.strip()
                    if pid.isdigit():
                        subprocess.run(
                            ["taskkill", "/F", "/PID", pid],
                            capture_output=True, timeout=5,
                            creationflags=subprocess.CREATE_NO_WINDOW,
                        )
            except Exception:
                pass

        # Ищем встроенный node.exe рядом с wa-server, иначе системный
        bundled_node = os.path.join(wa_dir, "node.exe")
        node_exe = bundled_node if os.path.isfile(bundled_node) else "node"

        # Лог wa-server в файл для диагностики
        self._wa_log_path = os.path.join(wa_dir, "wa_server.log")
        try:
            self._wa_log_file = open(self._wa_log_path, "w", encoding="utf-8")
            self._wa_process = subprocess.Popen(
                [node_exe, "server.js"],
                cwd=wa_dir,
                stdout=self._wa_log_file,
                stderr=self._wa_log_file,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
        except FileNotFoundError:
            self._wa_process = None

        # Проверяем через 3 сек что процесс не упал
        QTimer.singleShot(3000, self._check_wa_process)

    def _check_wa_process(self):
        """Проверяет что wa-server процесс жив."""
        if self._wa_process is None:
            self.log("⚠️ wa-server: node не найден! Установите Node.js")
            return
        rc = self._wa_process.poll()
        if rc is not None:
            err_msg = ""
            try:
                with open(self._wa_log_path, "r", encoding="utf-8") as f:
                    err_msg = f.read()[-500:]
            except Exception:
                pass
            self.log(f"⚠️ wa-server упал (код {rc})")
            if err_msg:
                for line in err_msg.strip().splitlines()[-5:]:
                    self.log(f"  | {line}")
        else:
            self.log("✅ wa-server запущен (порт 3457)")

    def _close_qr_dialog(self):
        """Закрывает QR-диалог если открыт."""
        if hasattr(self, '_qr_dialog') and self._qr_dialog:
            try:
                self._qr_dialog.close()
            except Exception:
                pass
            self._qr_dialog = None

    # ═══════════════════════════════════════════════════════════════
    #  Разлогин / Авторизация
    # ═══════════════════════════════════════════════════════════════

    def _logout_krisha(self):
        if not _styled_confirm(self, "Выход из Krisha.kz",
                "Выйти из аккаунта Krisha.kz?\nПридётся авторизоваться заново."):
            return
        self.krisha_authorized = False
        self.lbl_krisha.setText("Крыша: не авторизован")
        self.lbl_krisha.setStyleSheet("color: #ffa726; font-size: 11px;")
        self.log("  Выход из Krisha.kz...")

        def _bg():
            try:
                from parser_playwright import _run_in_pw_thread, _page
                def _do_logout():
                    if _page:
                        _page.goto("https://krisha.kz/logout")
                        import time as _t
                        _t.sleep(2)
                        _page.goto("https://krisha.kz/prodazha/kvartiry/")
                _run_in_pw_thread(_do_logout)
            except Exception:
                pass
            self._invoke_signal.emit(lambda: self.log("  Вышли из Krisha.kz"))
        threading.Thread(target=_bg, daemon=True).start()

    def _logout_whatsapp(self):
        # Проверяем есть ли сессия
        wa_auth = os.path.join(APP_DIR, "wa-server", "wa_auth_data")
        wa_has_session = os.path.exists(wa_auth) and os.listdir(wa_auth) if os.path.exists(wa_auth) else False
        if not self.wa_server_ready and not wa_has_session:
            _styled_info(self, "WhatsApp",
                "Сессия WhatsApp не найдена.\n\n"
                "Для авторизации переключитесь в режим WhatsApp —\n"
                "появится QR-код.\n"
                "Отсканируйте его телефоном:\n"
                "WhatsApp > Настройки > Связанные устройства.")
            return
        if not _styled_confirm(self, "Выход из WhatsApp",
                "Удалить сессию WhatsApp?\nПридётся заново отсканировать QR-код."):
            return
        self.wa_server_ready = False
        self.lbl_wa.setText("WA: выход...")
        self.lbl_wa.setStyleSheet("font-size: 11px; color: #ffa726;")
        self.log("🚪 Выход из WhatsApp — подождите...")

        def _do_logout():
            import shutil

            # Graceful shutdown — сервер сам закроет WA-клиент
            try:
                import requests
                requests.post("http://localhost:3457/shutdown", timeout=3)
            except Exception:
                pass

            # Ждём завершения процесса
            proc = self._wa_process
            if proc and proc.poll() is None:
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    try:
                        proc.kill()
                    except Exception:
                        pass
            self._wa_process = None

            # Удаляем сессию wa-server
            wa_auth = os.path.join(APP_DIR, "wa-server", "wa_auth_data")
            if os.path.exists(wa_auth):
                try:
                    shutil.rmtree(wa_auth, ignore_errors=True)
                except Exception:
                    pass

            # Обновляем UI из главного потока
            self._invoke_signal.emit(self._after_wa_logout)

        threading.Thread(target=_do_logout, daemon=True).start()

    def _after_wa_logout(self):
        """Вызывается в главном потоке после фонового разлогина WA."""
        self.lbl_wa.setText("WA: ожидание")
        self.lbl_wa.setStyleSheet("font-size: 11px; color: #cdd6f4;")
        self._msg_qr_bar.setVisible(False)
        self._qr_logged = False
        self._wa_status_count = 0
        self._wa_wait_logged = False
        # Сбрасываем оверлей в начальное состояние
        if hasattr(self, '_wa_overlay_qr'):
            self._wa_overlay_qr.setVisible(False)
            self._wa_overlay_dots.setVisible(True)
            self._wa_overlay_title.setText("Подключение к WhatsApp")
            self._wa_overlay_hint.setText("Ожидание инициализации сервера\nQR-код появится автоматически")
        # Показываем оверлей загрузки
        if hasattr(self, '_msg_stack'):
            self._msg_stack.setCurrentIndex(0)
        self._start_wa_server()
        if not self.auth_timer.isActive():
            self.auth_timer.start(10000)
        if not self.wa_check_timer.isActive():
            self.wa_check_timer.start(5000)
        self.log("🚪 Вышли из WhatsApp — отсканируйте QR-код заново")

    def _show_auth_dialog(self):
        """Показывает диалог авторизации при первом запуске."""
        wa_auth = os.path.join(APP_DIR, "wa-server", "wa_auth_data")
        wa_has_session = os.path.exists(wa_auth) and os.listdir(wa_auth) if os.path.exists(wa_auth) else False

        if self.wa_server_ready:
            return
        if wa_has_session:
            return

        _styled_info(self, "Требуется авторизация",
            "1. Krisha.kz — авторизуйтесь в браузере\n"
            "   для получения номеров телефонов.\n\n"
            "2. WhatsApp — переключитесь на WhatsApp,\n"
            "   дождитесь QR-кода и отсканируйте его."
        )

    # ═══════════════════════════════════════════════════════════════
    #  UI
    # ═══════════════════════════════════════════════════════════════

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Кастомный title bar ─────────────────────────────────
        title_bar = QWidget()
        title_bar.setObjectName("titleBar")
        title_bar.setFixedHeight(32)
        title_bar.setStyleSheet("""
            #titleBar { background: #11111b; border-bottom: 1px solid #313244; }
        """)
        tbl = QHBoxLayout(title_bar)
        tbl.setContentsMargins(10, 0, 4, 0)
        tbl.setSpacing(0)

        title_icon = QLabel("K")
        title_icon.setFixedSize(20, 20)
        title_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_icon.setStyleSheet(
            "background: #00a884; color: white; border-radius: 4px; "
            "font-size: 11px; font-weight: bold;"
        )
        tbl.addWidget(title_icon)
        tbl.addSpacing(8)

        title_lbl = QLabel("Krisha Parser Bot v3.0")
        title_lbl.setStyleSheet("color: #6c7086; font-size: 12px; font-weight: bold;")
        tbl.addWidget(title_lbl)
        tbl.addStretch()

        btn_minimize = QPushButton("—")
        btn_minimize.setFixedSize(36, 26)
        btn_minimize.setStyleSheet("""
            QPushButton { background: transparent; color: #6c7086; border: none;
                          font-size: 14px; font-weight: bold; }
            QPushButton:hover { background: #313244; color: #cdd6f4; }
        """)
        btn_minimize.clicked.connect(self.showMinimized)
        tbl.addWidget(btn_minimize)

        self._is_maximized = False
        btn_maximize = QPushButton("☐")
        btn_maximize.setFixedSize(36, 26)
        btn_maximize.setStyleSheet("""
            QPushButton { background: transparent; color: #6c7086; border: none;
                          font-size: 13px; }
            QPushButton:hover { background: #313244; color: #cdd6f4; }
        """)
        def _toggle_max():
            if self._is_maximized:
                self.showNormal()
                self._is_maximized = False
            else:
                self.showMaximized()
                self._is_maximized = True
        btn_maximize.clicked.connect(_toggle_max)
        tbl.addWidget(btn_maximize)

        btn_close = QPushButton("✕")
        btn_close.setFixedSize(36, 26)
        btn_close.setStyleSheet("""
            QPushButton { background: transparent; color: #6c7086; border: none;
                          font-size: 13px; }
            QPushButton:hover { background: #e53935; color: white; }
        """)
        btn_close.clicked.connect(self.close)
        tbl.addWidget(btn_close)

        # Drag support
        title_bar.mousePressEvent = self._title_mouse_press
        title_bar.mouseMoveEvent = self._title_mouse_move
        title_bar.mouseReleaseEvent = self._title_mouse_release
        title_bar.mouseDoubleClickEvent = lambda e: _toggle_max()

        root.addWidget(title_bar)

        # ── Верхняя панель ──────────────────────────────────────
        toolbar = QWidget()
        toolbar.setObjectName("toolbar")
        toolbar.setFixedHeight(36)
        tb = QHBoxLayout(toolbar)
        tb.setContentsMargins(6, 2, 6, 2)
        tb.setSpacing(4)

        # Режимы
        self.btn_mode_parse = QPushButton("Парсинг")
        self.btn_mode_parse.setCheckable(True)
        self.btn_mode_parse.setChecked(True)
        self.btn_mode_parse.setFixedHeight(26)
        self.btn_mode_parse.clicked.connect(lambda: self._switch_mode(self.MODE_PARSE))

        self.btn_mode_wa = QPushButton("WhatsApp")
        self.btn_mode_wa.setCheckable(True)
        self.btn_mode_wa.setFixedHeight(26)
        self.btn_mode_wa.clicked.connect(lambda: self._switch_mode(self.MODE_WA))

        tb.addWidget(self.btn_mode_parse)
        tb.addWidget(self.btn_mode_wa)
        tb.addSpacing(8)

        # Статусы
        self.lbl_krisha = QLabel("Крыша: ожидание")
        self.lbl_krisha.setStyleSheet("font-size: 11px;")
        self.lbl_wa = QLabel("WA: ожидание")
        self.lbl_wa.setStyleSheet("font-size: 11px;")
        tb.addWidget(self.lbl_krisha)
        tb.addWidget(self.lbl_wa)
        tb.addSpacing(8)

        # Действия — Парсинг
        self.btn_start = QPushButton("Парсить")
        self.btn_start.setFixedHeight(26)
        self.btn_start.clicked.connect(self._on_start_parse)
        self.btn_stop = QPushButton("Стоп")
        self.btn_stop.setFixedHeight(26)
        self.btn_stop.clicked.connect(self._on_stop_parse)
        self.btn_stop.setEnabled(False)
        tb.addWidget(self.btn_start)
        tb.addWidget(self.btn_stop)

        # Действия — WhatsApp (скрыты в режиме парсинга)
        self.btn_mailing = QPushButton("Рассылка")
        self.btn_mailing.setFixedHeight(26)
        self.btn_mailing.setCheckable(True)
        self.btn_mailing.clicked.connect(self._on_toggle_mailing)
        self.btn_mailing.setVisible(False)

        self.btn_ai_bot = QPushButton("AI Бот")
        self.btn_ai_bot.setFixedHeight(26)
        self.btn_ai_bot.setCheckable(True)
        self.btn_ai_bot.clicked.connect(self._on_toggle_ai_bot)
        self.btn_ai_bot.setVisible(False)

        tb.addWidget(self.btn_mailing)
        tb.addWidget(self.btn_ai_bot)

        self.progress = QProgressBar()
        self.progress.setTextVisible(True)
        self.progress.setFormat("%v / %m")
        self.progress.setFixedHeight(18)
        tb.addWidget(self.progress, 1)

        self.lbl_stats = QLabel("—")
        self.lbl_stats.setStyleSheet("font-size: 11px;")
        tb.addWidget(self.lbl_stats)

        # Кнопка разлогина
        from PyQt6.QtWidgets import QMenu
        self.btn_logout = QPushButton("Выход")
        self.btn_logout.setFixedHeight(26)
        self.btn_logout.setToolTip("Выйти из аккаунтов")
        self.btn_logout.setStyleSheet("""
            QPushButton { background: #45475a; color: #cf6679; border: 1px solid #cf6679;
                          border-radius: 4px; padding: 3px 10px; font-size: 11px; }
            QPushButton:hover { background: #cf6679; color: #1e1e2e; }
            QPushButton::menu-indicator { width: 0px; }
        """)
        logout_menu = QMenu(self)
        logout_menu.setStyleSheet("""
            QMenu { background: #1e1e2e; color: #cdd6f4; border: 1px solid #45475a; padding: 4px; }
            QMenu::item { padding: 6px 16px; }
            QMenu::item:selected { background: #45475a; }
            QMenu::separator { height: 1px; background: #313244; margin: 4px 8px; }
        """)
        act_krisha = logout_menu.addAction("Выйти из Крыши")
        act_krisha.triggered.connect(self._logout_krisha)
        logout_menu.addSeparator()
        act_wa = logout_menu.addAction("Выйти из WhatsApp")
        act_wa.triggered.connect(self._logout_whatsapp)
        self.btn_logout.setMenu(logout_menu)
        tb.addWidget(self.btn_logout)

        root.addWidget(toolbar)

        # ── Центр: браузер (стек) ──────────────────────────────
        self.browser_stack = QStackedWidget()

        # Chrome host — контейнер для встроенного Chrome
        self._chrome_host = QWidget()
        self._chrome_host.setObjectName("chromeHost")
        self._chrome_host.setStyleSheet("background: #1e1e2e;")
        # Передаём фокус Chrome при клике на контейнер
        self._chrome_host.mousePressEvent = self._chrome_host_clicked
        self._chrome_host.setFocusPolicy(Qt.FocusPolicy.ClickFocus)

        # Оверлей загрузки поверх Chrome host
        self._loading_overlay = QWidget(self._chrome_host)
        self._loading_overlay.setObjectName("loadingOverlay")
        self._loading_overlay.setStyleSheet("""
            #loadingOverlay { background: #1e1e2e; }
        """)
        lo_lay = QVBoxLayout(self._loading_overlay)
        lo_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lo_lay.setSpacing(16)

        # Анимированные точки
        self._loading_dots_label = QLabel("Загрузка браузера")
        self._loading_dots_label.setStyleSheet(
            "color: #6c7086; font-size: 18px; font-weight: bold; background: transparent;"
        )
        self._loading_dots_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lo_lay.addWidget(self._loading_dots_label)

        # Полоска прогресса (анимированная)
        self._loading_bar = QProgressBar()
        self._loading_bar.setFixedWidth(300)
        self._loading_bar.setFixedHeight(4)
        self._loading_bar.setRange(0, 0)  # indeterminate
        self._loading_bar.setTextVisible(False)
        self._loading_bar.setStyleSheet("""
            QProgressBar { background: #313244; border: none; border-radius: 2px; }
            QProgressBar::chunk { background: #00a884; border-radius: 2px; }
        """)
        lo_lay.addWidget(self._loading_bar, 0, Qt.AlignmentFlag.AlignCenter)

        self._loading_hint = QLabel("Подождите, идет запуск Chrome...")
        self._loading_hint.setStyleSheet(
            "color: #45475a; font-size: 11px; background: transparent;"
        )
        self._loading_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lo_lay.addWidget(self._loading_hint)

        # Таймер анимации точек
        self._loading_dot_count = 0
        self._loading_dot_timer = QTimer()
        self._loading_dot_timer.timeout.connect(self._animate_loading_dots)
        self._loading_dot_timer.start(800)

        self.browser_stack.addWidget(self._chrome_host)  # index 0

        # Мессенджер (Рассылка + AI Риелтор)
        self.messenger = self._make_messenger()
        self.browser_stack.addWidget(self.messenger)  # index 1

        # ── Боковая панель (справа) — фиксированная ─────────────
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self.browser_stack, 4)

        self.side_tabs = QTabWidget()
        self.side_tabs.setObjectName("sideTabs")
        self.side_tabs.setMinimumWidth(200)
        self.side_tabs.setMaximumWidth(350)

        self.log_text = QTextEdit()
        self.log_text.setObjectName("logText")
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont("Consolas", 9))
        self.side_tabs.addTab(self.log_text, "Лог")

        self.filters_tab = self._create_filters_tab()
        self.side_tabs.addTab(self.filters_tab, "Фильтры")

        self.settings_tab = self._create_settings_tab()
        self.side_tabs.addTab(self.settings_tab, "Настройки")

        self.db_tab = self._create_db_tab()
        self.side_tabs.addTab(self.db_tab, "База")

        body.addWidget(self.side_tabs, 1)
        root.addLayout(body)

        self.statusBar().showMessage("Выберите режим и нажмите Старт")
        self._update_stats()


    # ═══════════════════════════════════════════════════════════════
    #  Режимы
    # ═══════════════════════════════════════════════════════════════

    def _switch_mode(self, mode):
        if self._parsing:
            self.log("⚠️ Дождитесь завершения парсинга")
            self._update_mode_ui()
            return
        self._current_mode = mode
        is_parse = mode == self.MODE_PARSE
        is_wa = mode == self.MODE_WA

        # Показать/скрыть кнопки
        self.btn_start.setVisible(is_parse)
        self.btn_stop.setVisible(is_parse)
        self.btn_mailing.setVisible(is_wa)
        self.btn_ai_bot.setVisible(is_wa)

        if is_parse:
            self.browser_stack.setCurrentIndex(0)
            self.log("🔄 Режим: Парсинг")
            QTimer.singleShot(200, self._focus_chrome)
        else:
            self.browser_stack.setCurrentIndex(1)
            self._messenger_refresh_chats()
            self.log("🔄 Режим: WhatsApp")
        self._update_mode_ui()

    def _update_mode_ui(self):
        m = self._current_mode
        self.btn_mode_parse.setChecked(m == self.MODE_PARSE)
        self.btn_mode_wa.setChecked(m == self.MODE_WA)

    def _animate_loading_dots(self):
        """Анимация точек на оверлее загрузки."""
        if not self._loading_overlay.isVisible():
            self._loading_dot_timer.stop()
            return
        self._loading_dot_count = (self._loading_dot_count + 1) % 4
        dots = "." * self._loading_dot_count
        self._loading_dots_label.setText(f"Загрузка браузера{dots}")
        # Подгоняем размер оверлея под родителя
        self._loading_overlay.setGeometry(self._chrome_host.rect())
        self._loading_overlay.raise_()

    def _hide_loading_overlay(self):
        """Скрывает оверлей загрузки после встраивания Chrome."""
        if hasattr(self, '_loading_overlay') and self._loading_overlay:
            self._loading_overlay.hide()
        if hasattr(self, '_loading_dot_timer'):
            self._loading_dot_timer.stop()

    def _chrome_host_clicked(self, event):
        """При клике на область Chrome — передаём ему фокус."""
        self._focus_chrome()

    def _focus_chrome(self):
        """Передаёт фокус клавиатуры встроенному Chrome через Win32 API.
        Chrome использует дочернее окно Chrome_RenderWidgetHostHWND для рендера —
        именно ему нужно передать фокус для ввода с клавиатуры.
        """
        if not self._chrome_embedded or not self._chrome_hwnd:
            return
        try:
            import ctypes
            import ctypes.wintypes

            user32 = ctypes.windll.user32

            WNDENUMPROC = ctypes.WINFUNCTYPE(
                ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM
            )

            # Ищем дочернее окно рендера (Chrome_RenderWidgetHostHWND)
            render_hwnd = None

            def _find_render(hwnd, _lp):
                nonlocal render_hwnd
                buf = ctypes.create_unicode_buffer(256)
                user32.GetClassNameW(hwnd, buf, 256)
                cls = buf.value
                if cls == "Chrome_RenderWidgetHostHWND":
                    render_hwnd = hwnd
                    return False
                return True

            cb = WNDENUMPROC(_find_render)
            user32.EnumChildWindows(self._chrome_hwnd, cb, 0)

            target = render_hwnd or self._chrome_hwnd

            # Привязываем потоки для SetFocus
            current_thread = user32.GetCurrentThreadId()
            target_thread = user32.GetWindowThreadProcessId(
                target, ctypes.byref(ctypes.wintypes.DWORD(0))
            )
            attached = False
            if current_thread != target_thread:
                user32.AttachThreadInput(current_thread, target_thread, True)
                attached = True

            user32.SetForegroundWindow(self._chrome_hwnd)
            user32.SetFocus(target)

            if attached:
                user32.AttachThreadInput(current_thread, target_thread, False)

            # Сохраняем render hwnd для быстрого доступа
            self._chrome_render_hwnd = render_hwnd
        except Exception:
            pass

    def _install_chrome_focus_hook(self):
        """Устанавливает нативный хук: при клике в области Chrome передаёт фокус."""
        try:
            from PyQt6.QtCore import QAbstractNativeEventFilter

            class ChromeFocusFilter(QAbstractNativeEventFilter):
                def __init__(self, main_win):
                    super().__init__()
                    self.main_win = main_win

                def nativeEventFilter(self, event_type, message):
                    # На Windows event_type = b'windows_generic_MSG'
                    if event_type == b'windows_generic_MSG':
                        import ctypes
                        import ctypes.wintypes

                        class MSG(ctypes.Structure):
                            _fields_ = [
                                ("hwnd", ctypes.wintypes.HWND),
                                ("message", ctypes.c_uint),
                                ("wParam", ctypes.wintypes.WPARAM),
                                ("lParam", ctypes.wintypes.LPARAM),
                                ("time", ctypes.wintypes.DWORD),
                                ("pt", ctypes.wintypes.POINT),
                            ]

                        msg = MSG.from_address(int(message))
                        WM_LBUTTONDOWN = 0x0201

                        if msg.message == WM_LBUTTONDOWN:
                            mw = self.main_win
                            if (mw._chrome_embedded and mw._chrome_hwnd
                                    and mw._current_mode == mw.MODE_PARSE):
                                # Проверяем что клик в области chrome_host
                                host = mw._chrome_host
                                if host.underMouse():
                                    QTimer.singleShot(50, mw._focus_chrome)

                    return False, 0  # не блокируем событие

            self._chrome_focus_filter = ChromeFocusFilter(self)
            QApplication.instance().installNativeEventFilter(self._chrome_focus_filter)
        except Exception:
            pass

    def _on_start_parse(self):
        self._start_parsing()

    def _on_stop_parse(self):
        self._parse_stop = True
        self.log("  Останавливаем парсинг...")

    def _on_toggle_mailing(self):
        """Включить/выключить рассылку (toggle) с подтверждением."""
        if self.btn_mailing.isChecked():
            if _styled_confirm(self, "Рассылка", "Запустить рассылку?"):
                self._start_mailing()
            else:
                self.btn_mailing.setChecked(False)
        else:
            if _styled_confirm(self, "Рассылка", "Остановить рассылку?"):
                self._mail_stop = True
                self.log("⏹ Останавливаем рассылку...")
            else:
                self.btn_mailing.setChecked(True)

    def _on_toggle_ai_bot(self):
        """Включить/выключить AI бота с подтверждением."""
        if self.btn_ai_bot.isChecked():
            if _styled_confirm(self, "AI Бот", "Включить AI бота?"):
                self._start_ai_bot()
            else:
                self.btn_ai_bot.setChecked(False)
        else:
            if _styled_confirm(self, "AI Бот", "Выключить AI бота?"):
                self._stop_ai_bot()
            else:
                self.btn_ai_bot.setChecked(True)

    def _set_running(self, running):
        # Для парсинга
        if self._current_mode == self.MODE_PARSE:
            self.btn_start.setEnabled(not running)
            self.btn_stop.setEnabled(running)
            self.btn_mode_parse.setEnabled(not running)
            self.btn_mode_wa.setEnabled(not running)

    # ═══════════════════════════════════════════════════════════════
    #  Авторизация
    # ═══════════════════════════════════════════════════════════════

    def _check_auth(self):
        # WA-server проверяется отдельным таймером _poll_wa_server
        if self.krisha_authorized and self.wa_server_ready:
            self.auth_timer.stop()

    def _check_krisha_auth(self):
        """Проверяет авторизацию на krisha.kz из фонового потока."""
        def _bg():
            try:
                logged = is_krisha_logged_in()
                self._invoke_signal.emit(lambda: self._on_krisha_auth_result(logged))
            except Exception:
                self._invoke_signal.emit(lambda: self._on_krisha_auth_result(False))
        threading.Thread(target=_bg, daemon=True).start()

    def _on_krisha_auth_result(self, logged_in: bool):
        """Обработка результата проверки авторизации krisha.kz."""
        if logged_in:
            self.krisha_authorized = True
            self.lbl_krisha.setText("Крыша: авторизован")
            self.lbl_krisha.setStyleSheet("color: #4caf50; font-size: 11px;")
            self.log("  Krisha.kz: авторизован")
        else:
            self.krisha_authorized = False
            self.lbl_krisha.setText("Крыша: не авторизован")
            self.lbl_krisha.setStyleSheet("color: #ffa726; font-size: 11px;")
            self.log("  Krisha.kz: не авторизован — для получения номеров нужно войти")
            # Показываем диалог
            self._show_krisha_login_prompt()

    def _show_krisha_login_prompt(self):
        """Диалог авторизации krisha.kz — ввод телефона/пароля."""
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit

        dlg = QDialog(self)
        dlg.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        dlg.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        dlg.setModal(True)

        outer = QWidget(dlg)
        outer.setStyleSheet("""
            QWidget { background: #1e1e2e; border: 1px solid #45475a; border-radius: 10px; }
        """)
        dlg_root = QVBoxLayout(dlg)
        dlg_root.setContentsMargins(0, 0, 0, 0)
        dlg_root.addWidget(outer)

        lay = QVBoxLayout(outer)
        lay.setContentsMargins(24, 20, 24, 20)
        lay.setSpacing(12)

        lbl_title = QLabel("Авторизация Krisha.kz")
        lbl_title.setStyleSheet("color: #cdd6f4; font-size: 15px; font-weight: bold; background: transparent; border: none;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(lbl_title)

        lbl_hint = QLabel("Для получения номеров телефонов нужно войти.\nВведите логин и пароль — браузер заполнит форму за вас.")
        lbl_hint.setStyleSheet("color: #a6adc8; font-size: 11px; background: transparent; border: none;")
        lbl_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_hint.setWordWrap(True)
        lay.addWidget(lbl_hint)

        input_style = """
            QLineEdit { background: #313244; color: #cdd6f4; border: 1px solid #45475a;
                        border-radius: 6px; padding: 8px 12px; font-size: 13px; }
            QLineEdit:focus { border-color: #00a884; }
        """

        phone_input = QLineEdit()
        phone_input.setPlaceholderText("Номер телефона (напр. 77071234567)")
        phone_input.setStyleSheet(input_style)
        lay.addWidget(phone_input)

        pwd_input = QLineEdit()
        pwd_input.setPlaceholderText("Пароль")
        pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        pwd_input.setStyleSheet(input_style)
        lay.addWidget(pwd_input)

        lbl_note = QLabel("Введите телефон и пароль от аккаунта Krisha.kz.\nБраузер заполнит форму автоматически.")
        lbl_note.setStyleSheet("color: #6c7086; font-size: 10px; background: transparent; border: none;")
        lbl_note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl_note.setWordWrap(True)
        lay.addWidget(lbl_note)

        # Кнопки
        btn_row = QWidget()
        btn_row.setStyleSheet("background: transparent; border: none;")
        bl = QHBoxLayout(btn_row)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(12)

        btn_skip = QPushButton("Пропустить")
        btn_skip.setFixedHeight(34)
        btn_skip.setMinimumWidth(100)
        btn_skip.setStyleSheet("""
            QPushButton { background: #313244; color: #cdd6f4; border: 1px solid #45475a;
                          border-radius: 6px; font-size: 12px; padding: 0 16px; }
            QPushButton:hover { background: #45475a; }
        """)
        btn_skip.clicked.connect(dlg.reject)

        btn_login = QPushButton("Войти")
        btn_login.setFixedHeight(34)
        btn_login.setMinimumWidth(100)
        btn_login.setStyleSheet("""
            QPushButton { background: #00a884; color: #ffffff; border: none;
                          border-radius: 6px; font-size: 12px; font-weight: bold; padding: 0 16px; }
            QPushButton:hover { background: #06cf9c; }
        """)
        btn_login.setDefault(True)

        bl.addStretch()
        bl.addWidget(btn_skip)
        bl.addWidget(btn_login)
        bl.addStretch()
        lay.addWidget(btn_row)

        dlg.setFixedWidth(400)
        dlg.adjustSize()

        # Обработка кнопки "Войти"
        def _do_login():
            phone = phone_input.text().strip()
            if not phone:
                return
            pwd = pwd_input.text().strip()
            dlg.accept()
            self.log(f"  Авторизация krisha.kz: {phone[:4]}***...")
            def _bg():
                try:
                    result = krisha_login(
                        phone, pwd,
                        log_fn=lambda m: self._log_signal.emit(m),
                    )
                    self._invoke_signal.emit(lambda: self._on_login_done(result))
                except Exception as e:
                    self._log_signal.emit(f"  Ошибка: {e}")
            threading.Thread(target=_bg, daemon=True).start()

        btn_login.clicked.connect(_do_login)
        pwd_input.returnPressed.connect(_do_login)

        result = dlg.exec()
        if result == 0:
            # Пропустили — всё равно запускаем проверку
            pass

        # Периодически проверяем авторизацию
        if not hasattr(self, '_krisha_auth_check_timer') or not self._krisha_auth_check_timer.isActive():
            self._krisha_auth_check_timer = QTimer()
            self._krisha_auth_check_timer.timeout.connect(self._recheck_krisha_auth)
            self._krisha_auth_check_timer.start(5000)

    def _on_login_done(self, success: bool):
        """Результат авторизации Krisha.kz."""
        if success:
            self.krisha_authorized = True
            self.lbl_krisha.setText("Крыша: авторизован")
            self.lbl_krisha.setStyleSheet("color: #4caf50; font-size: 11px;")
            self.log("  Krisha.kz: авторизация успешна!")
            if hasattr(self, '_krisha_auth_check_timer'):
                self._krisha_auth_check_timer.stop()
        else:
            self.log("  Krisha.kz: авторизация не удалась — проверьте логин/пароль")
            self.lbl_krisha.setText("Крыша: ошибка входа")
            self.lbl_krisha.setStyleSheet("color: #f38ba8; font-size: 11px;")

    def _recheck_krisha_auth(self):
        """Периодическая проверка — залогинился ли пользователь."""
        def _bg():
            try:
                logged = is_krisha_logged_in()
                self._invoke_signal.emit(lambda: self._on_recheck_krisha(logged))
            except Exception:
                pass
        threading.Thread(target=_bg, daemon=True).start()

    def _on_recheck_krisha(self, logged_in: bool):
        if logged_in:
            self.krisha_authorized = True
            self.lbl_krisha.setText("Крыша: авторизован")
            self.lbl_krisha.setStyleSheet("color: #4caf50; font-size: 11px;")
            self.log("  Krisha.kz: авторизация успешна!")
            if hasattr(self, '_krisha_auth_check_timer'):
                self._krisha_auth_check_timer.stop()
            # Сохраняем cookies для следующего запуска
            def _save():
                try:
                    save_krisha_session()
                except Exception:
                    pass
            threading.Thread(target=_save, daemon=True).start()

    def _poll_wa_server(self):
        """Отдельный таймер — проверяет wa-server каждые 3 сек (асинхронно)."""
        if self.wa_server_ready:
            self.wa_check_timer.stop()
            return

        # Защита от параллельных запросов
        if getattr(self, '_wa_polling', False):
            return
        self._wa_polling = True

        # Лог что таймер работает (первые 3 раза)
        if not hasattr(self, '_poll_count'):
            self._poll_count = 0
        self._poll_count += 1
        if self._poll_count <= 3:
            self.log(f"🔄 WA-poll #{self._poll_count}...")

        # Запрос в фоновом потоке — НЕ блокирует GUI
        def _bg():
            try:
                import requests
                r = requests.get("http://localhost:3457/status", timeout=2)
                st = r.json()
            except Exception as e:
                st = {"_error": str(e)}
            self._wa_polling = False
            self._wa_status_signal.emit(st)

        threading.Thread(target=_bg, daemon=True).start()

    def _on_wa_status(self, st):
        """Обработка статуса WA в главном потоке."""
        if self.wa_server_ready:
            return

        # Отладка — всегда логируем что получили от wa-server
        has_ready = st.get("ready", False)
        has_qr64 = bool(st.get("qr_base64"))
        has_qr = bool(st.get("qr"))
        has_err = bool(st.get("error"))

        # Лог для диагностики (первые 5 раз)
        if not hasattr(self, '_wa_status_count'):
            self._wa_status_count = 0
        self._wa_status_count += 1
        if self._wa_status_count <= 5 or has_qr64 or has_ready:
            self.log(f"🔍 WA-статус #{self._wa_status_count}: ready={has_ready} qr64={has_qr64} qr={has_qr} err={has_err}")

        if has_ready:
            self.wa_server_ready = True
            self._qr_logged = False
            phone = st.get("phone", "?")
            self.log(f"✅ WA-сервер подключён! Номер: {phone}")
            self.lbl_wa.setText(f"WA: {phone}")
            self.lbl_wa.setStyleSheet("color: #4caf50; font-size: 11px;")
            self._msg_qr_bar.setVisible(False)
            # Скрываем QR в оверлее
            if hasattr(self, '_wa_overlay_qr'):
                self._wa_overlay_qr.setVisible(False)
                self._wa_overlay_dots.setVisible(True)
            # Показываем мессенджер вместо оверлея
            if hasattr(self, '_msg_stack'):
                self._msg_stack.setCurrentIndex(1)
            # Запускаем синхронизацию входящих
            if not self.sync_timer.isActive():
                self.sync_timer.start(7000)
                self._msg_refresh_timer.start(5000)
                self.log("🔄 Синхронизация входящих запущена")
            # Закрываем QR-диалог если открыт
            if hasattr(self, '_qr_dialog') and self._qr_dialog:
                try:
                    self._qr_dialog.close()
                except Exception:
                    pass
                self._qr_dialog = None
            if self.krisha_authorized:
                self.auth_timer.stop()
                self.log("🎉 Всё готово! Krisha + WA-сервер подключены")
                self.statusBar().showMessage("Готов к работе")
            else:
                self.log("⏳ WA-сервер подключён, ожидание Krisha.kz...")
        elif has_qr64:
            self.lbl_wa.setText("WA: QR")
            self.lbl_wa.setStyleSheet("color: #ffa726; font-size: 11px;")
            qr_data = st["qr_base64"]

            # Показываем QR в оверлее (НЕ в мессенджере — мессенджер только после авторизации)
            self._set_qr_on_overlay(qr_data)
            self._msg_qr_bar.setVisible(False)
            if hasattr(self, '_msg_stack'):
                self._msg_stack.setCurrentIndex(0)  # оверлей с QR

            # Автопереключение на вкладку WA чтобы QR был виден
            if self.browser_stack.currentIndex() == 0:
                self.browser_stack.setCurrentIndex(1)
                self._current_mode = self.MODE_WA
                self._update_mode_ui()
            if not getattr(self, '_qr_logged', False):
                self._qr_logged = True
                self.log("📷 QR-код wa-server — отсканируйте для подключения рассылки и AI бота")
        elif has_qr:
            self.lbl_wa.setText("WA: QR (генерация...)")
            self.lbl_wa.setStyleSheet("color: #ffa726; font-size: 11px;")
        elif has_err:
            self.lbl_wa.setText("WA: запуск...")
            self.lbl_wa.setStyleSheet("color: #78909c; font-size: 11px;")
        else:
            if not getattr(self, '_wa_wait_logged', False):
                self._wa_wait_logged = True
                self.log("⏳ WA-сервер: ожидание инициализации...")
            self.lbl_wa.setText("WA: ожидание")

    def _set_qr_on_bar(self, qr_base64: str):
        """Показывает QR-код в баре над WA-браузером."""
        try:
            if "," in qr_base64:
                _, data = qr_base64.split(",", 1)
            else:
                data = qr_base64
            img_bytes = base64.b64decode(data)
            pixmap = QPixmap()
            ok = pixmap.loadFromData(img_bytes)
            if ok and not pixmap.isNull():
                self.wa_qr_img.setPixmap(pixmap.scaled(
                    110, 110, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))
            else:
                self.log("⚠️ QR: не удалось декодировать изображение")
        except Exception as e:
            self.log(f"⚠️ QR ошибка: {e}")

    def _set_qr_on_overlay(self, qr_base64: str):
        """Показывает QR-код в оверлее загрузки."""
        try:
            if "," in qr_base64:
                _, data = qr_base64.split(",", 1)
            else:
                data = qr_base64
            img_bytes = base64.b64decode(data)
            pixmap = QPixmap()
            ok = pixmap.loadFromData(img_bytes)
            if ok and not pixmap.isNull():
                self._wa_overlay_qr.setPixmap(pixmap.scaled(
                    250, 250, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))
                self._wa_overlay_qr.setVisible(True)
                self._wa_overlay_title.setText("Отсканируйте QR-код")
                self._wa_overlay_hint.setText(
                    "WhatsApp > Связанные устройства > Привязка устройства"
                )
                self._wa_overlay_dots.setVisible(False)
        except Exception as e:
            self.log(f"⚠️ QR overlay ошибка: {e}")

    def _show_qr_dialog(self, qr_base64: str):
        """Показывает QR-код в отдельном окне (гарантированно видно)."""
        from PyQt6.QtWidgets import QDialog

        # Если диалог уже открыт — обновляем QR
        if hasattr(self, '_qr_dialog') and self._qr_dialog and self._qr_dialog.isVisible():
            self._update_qr_dialog_image(qr_base64)
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("WA-сервер: QR-код")
        dlg.setFixedSize(380, 440)
        dlg.setStyleSheet("QDialog { background: #1e1e2e; }")

        lay = QVBoxLayout(dlg)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(12)

        title = QLabel("Авторизация WA-сервера")
        title.setStyleSheet("color: #ffa726; font-size: 15px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(title)

        self._qr_dialog_img = QLabel()
        self._qr_dialog_img.setFixedSize(280, 280)
        self._qr_dialog_img.setStyleSheet("background: white; border-radius: 8px;")
        self._qr_dialog_img.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._qr_dialog_img, 0, Qt.AlignmentFlag.AlignCenter)

        hint = QLabel(
            "Откройте WhatsApp на телефоне:\n"
            "Настройки > Связанные устройства > Привязка\n"
            "и отсканируйте этот QR-код"
        )
        hint.setStyleSheet("color: #78909c; font-size: 11px;")
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hint.setWordWrap(True)
        lay.addWidget(hint)

        self._qr_dialog = dlg
        self._update_qr_dialog_image(qr_base64)
        dlg.show()

    def _update_qr_dialog_image(self, qr_base64: str):
        """Обновляет QR-картинку в диалоге."""
        try:
            if "," in qr_base64:
                _, data = qr_base64.split(",", 1)
            else:
                data = qr_base64
            img_bytes = base64.b64decode(data)
            pixmap = QPixmap()
            if pixmap.loadFromData(img_bytes) and not pixmap.isNull():
                self._qr_dialog_img.setPixmap(pixmap.scaled(
                    260, 260, Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))
        except Exception:
            pass

    def _on_krisha_auth(self, result):
        pass  # Krisha auth через Playwright, не нужна проверка

    def _kill_popups(self):
        pass  # Попапы закрываются через _close_popups


    # ═══════════════════════════════════════════════════════════════
    #  Режим 1: Парсинг
    # ═══════════════════════════════════════════════════════════════

    def _start_parsing(self):
        # Проверяем авторизацию перед парсингом
        if not self.krisha_authorized:
            self.log("  Проверяю авторизацию krisha.kz...")
            self._save_filters()

            def _bg_check():
                try:
                    logged = is_krisha_logged_in()
                    self._invoke_signal.emit(lambda: self._start_parsing_after_auth(logged))
                except Exception:
                    self._invoke_signal.emit(lambda: self._start_parsing_after_auth(False))
            threading.Thread(target=_bg_check, daemon=True).start()
            return

        self._do_start_parsing()

    def _start_parsing_after_auth(self, logged_in: bool):
        """Продолжение парсинга после проверки авторизации."""
        if logged_in:
            self.krisha_authorized = True
            self.lbl_krisha.setText("Крыша: авторизован")
            self.lbl_krisha.setStyleSheet("color: #4caf50; font-size: 11px;")
            self._do_start_parsing()
        else:
            self.log("  Krisha.kz: не авторизован — номера не будут доступны")
            self._show_krisha_login_prompt()

    def _do_start_parsing(self):
        """Запускает парсинг (авторизация уже проверена)."""
        self._save_filters()
        self._parsing = True
        self._parse_stop = False
        self._parse_new_count = 0
        self._set_running(True)

        self.log("  Парсинг Krisha.kz...")

        captcha_key = self.cfg.get("captcha", {}).get("anticaptcha_api_key", "")
        cfg_copy = {
            "krisha": dict(self.cfg["krisha"]),
        }

        def _bg():
            try:
                # Драйвер уже запущен при старте приложения
                listings = get_listings(
                    cfg_copy,
                    log_fn=lambda m: self._log_signal.emit(m),
                    stop_flag=lambda: self._parse_stop,
                    captcha_key=captcha_key,
                )
                self._parse_result_signal.emit(listings)
            except Exception as e:
                self._log_signal.emit(f"  Ошибка парсинга: {e}")
                self._parse_result_signal.emit([])

        self._parse_thread = threading.Thread(target=_bg, daemon=True)
        self._parse_thread.start()

    def _on_parse_listings_ready(self, listings):
        """Вызывается в GUI потоке когда собран список объявлений."""
        if not self._parsing:
            return
        self._parse_listings = listings
        self._parse_index = 0
        self.log(f"  Найдено {len(listings)} объявлений")
        if not listings:
            self._finish_parsing()
            return
        self._parse_next()

    def _parse_next(self):
        if self._parse_stop:
            self.log("  Парсинг остановлен")
            self._finish_parsing()
            return
        i = self._parse_index
        total = len(self._parse_listings)
        if i >= total:
            self._finish_parsing()
            return

        listing = self._parse_listings[i]
        self._parse_index += 1
        max_listings = self.cfg.get("krisha", {}).get("max_listings", 60)
        self.progress.setMaximum(max_listings)
        self.progress.setValue(i + 1)
        url = listing["url"]
        title = listing.get("title", "")[:50]

        if is_url_parsed(url):
            self.log(f"({i+1}/{total}) >> Уже: {title}")
            QTimer.singleShot(100, self._parse_next)
            return

        self.log(f"({i+1}/{total}) {title}...")

        captcha_key = self.cfg.get("captcha", {}).get("anticaptcha_api_key", "")

        def _bg():
            try:
                phone = extract_phone(
                    url,
                    log_fn=lambda m: self._log_signal.emit(m),
                    stop_flag=lambda: self._parse_stop,
                    captcha_key=captcha_key,
                )
                self._phone_result_signal.emit(phone or "", listing)
            except Exception as e:
                self._log_signal.emit(f"  Ошибка: {e}")
                self._phone_result_signal.emit("", listing)

        threading.Thread(target=_bg, daemon=True).start()

    def _on_phone_extracted(self, phone: str, listing: dict):
        """Вызывается в GUI потоке когда извлечён телефон."""
        if not self._parsing:
            return

        url = listing["url"]
        price = listing.get("price", "")
        mark_url_parsed(url)

        if phone:
            if is_phone_exists(phone):
                self.log(f"  >> В базе: {phone}")
            else:
                is_new = add_phone(phone, url, listing.get("title", ""), price)
                if is_new:
                    self._parse_new_count += 1
                    self.log(f"  + Новый: {phone}")
                    self._update_stats()
        else:
            self.log("  -- Номер не найден")

        QTimer.singleShot(3000, self._parse_next)

    def _finish_parsing(self):
        self.log(f"  Парсинг завершён. Новых: {self._parse_new_count}")
        self._parsing = False
        self._parse_thread = None
        self._set_running(False)
        self.progress.setValue(0)
        self._update_stats()
        self._refresh_phones()

    # ═══════════════════════════════════════════════════════════════
    #  Экран и DPI
    # ═══════════════════════════════════════════════════════════════

    def _get_screen_info(self) -> dict:
        """Возвращает информацию об экране: resolution, dpi_scale.

        Fallback на {"width": 1200, "height": 900, "dpi_scale": 1.0}
        при недоступном экране. Clamp dpi_scale: ≤0 → 1.0, >4.0 → 4.0.
        """
        fallback = {"width": 1200, "height": 900, "dpi_scale": 1.0}
        try:
            screen = QApplication.primaryScreen()
            if screen is None:
                return fallback
            geo = screen.availableGeometry()
            dpi_scale = screen.devicePixelRatio()
            # Clamp dpi_scale
            if dpi_scale <= 0:
                dpi_scale = 1.0
            elif dpi_scale > 4.0:
                dpi_scale = 4.0
            return {
                "width": geo.width(),
                "height": geo.height(),
                "dpi_scale": dpi_scale,
            }
        except Exception:
            return fallback

    def _compute_toolbar_offset(self) -> int:
        """Вычисляет toolbar offset с учётом DPI scale.

        Читает toolbar_offset из self.cfg (default 155).
        Валидация: если не число или вне диапазона 50–300, используется 155.
        Возвращает int(base_offset * self._dpi_scale).
        """
        base_offset = self.cfg.get("toolbar_offset", 155)
        try:
            base_offset = int(base_offset)
        except (TypeError, ValueError):
            base_offset = 155
        if base_offset < 50 or base_offset > 300:
            base_offset = 155
        return int(base_offset * self._dpi_scale)

    # ═══════════════════════════════════════════════════════════════
    #  Встраивание Chrome (поиск по уникальному заголовку окна)
    # ═══════════════════════════════════════════════════════════════

    def _launch_chrome_bg(self):
        """Запускает Playwright Chrome в фоновом потоке, затем встраивает."""
        # Вычисляем viewport до запуска фонового потока (GUI-поток)
        vw, vh = self._initial_viewport
        bs = self.browser_stack
        if bs.width() > 50 and bs.height() > 50:
            vw, vh = bs.width(), bs.height()
        else:
            vw = int(self._screen_info["width"] * 0.75)
            vh = int(self._screen_info["height"] * 0.75)

        def _bg():
            try:
                from parser_playwright import _run_in_pw_thread, _load_cookies

                def _pw_init():
                    from parser_playwright import _get_driver, CHROME_WINDOW_MARKER as marker
                    driver = _get_driver(viewport_width=vw, viewport_height=vh)
                    driver.goto("https://krisha.kz/prodazha/kvartiry/")
                    import time as _t
                    _t.sleep(2)
                    try:
                        _load_cookies(driver)
                        _t.sleep(1)
                    except Exception:
                        pass
                    try:
                        driver.evaluate(f"document.title = '{marker}'")
                    except Exception:
                        pass
                    _t.sleep(0.5)

                _run_in_pw_thread(_pw_init)
                self._chrome_ready_signal.emit()
            except Exception as e:
                self._log_signal.emit(f"  Ошибка запуска Chrome: {e}")
        threading.Thread(target=_bg, daemon=True).start()

    def _embed_chrome(self):
        """Находит окно Chrome по уникальному заголовку и встраивает в _chrome_host."""
        if self._chrome_embedded:
            return
        try:
            import ctypes
            import ctypes.wintypes

            user32 = ctypes.windll.user32

            # --- Ищем окно по заголовку (содержит CHROME_WINDOW_MARKER) ---
            WNDENUMPROC = ctypes.WINFUNCTYPE(
                ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM
            )
            target_hwnd = None

            def _enum_cb(hwnd, _lp):
                nonlocal target_hwnd
                # Ищем и скрытые окна (мы скрыли Chrome через SW_HIDE)
                buf = ctypes.create_unicode_buffer(512)
                user32.GetWindowTextW(hwnd, buf, 512)
                title = buf.value
                if CHROME_WINDOW_MARKER in title:
                    target_hwnd = hwnd
                    return False  # нашли — прекращаем
                return True

            cb_ref = WNDENUMPROC(_enum_cb)
            user32.EnumWindows(cb_ref, 0)

            if not target_hwnd:
                self._embed_retries += 1
                if self._embed_retries < 30:
                    # Переставляем заголовок из фонового потока и пробуем снова
                    def _remark():
                        from parser_playwright import _run_in_pw_thread, _page
                        def _do_remark():
                            if _page:
                                _page.evaluate(
                                    f"document.title = '{CHROME_WINDOW_MARKER}'"
                                )
                        try:
                            _run_in_pw_thread(_do_remark)
                        except Exception:
                            pass
                        import time as _t
                        _t.sleep(0.3)
                        self._chrome_ready_signal.emit()
                    threading.Thread(target=_remark, daemon=True).start()
                else:
                    self.log("  -- Chrome окно не найдено (по заголовку)")
                return

            self._embed_retries = 0
            chrome_hwnd = target_hwnd
            host_hwnd = int(self._chrome_host.winId())

            # Константы Win32
            GWL_STYLE = -16
            GWL_EXSTYLE = -20
            WS_CHILD = 0x40000000
            WS_VISIBLE = 0x10000000
            WS_CAPTION = 0x00C00000
            WS_THICKFRAME = 0x00040000
            WS_BORDER = 0x00800000
            WS_DLGFRAME = 0x00400000
            WS_EX_WINDOWEDGE = 0x00000100
            WS_EX_DLGMODALFRAME = 0x00000001
            SWP_FRAMECHANGED = 0x0020
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOZORDER = 0x0004
            SW_SHOW = 5

            # Типы
            user32.SetParent.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.HWND]
            user32.SetParent.restype = ctypes.wintypes.HWND
            user32.GetWindowLongPtrW.argtypes = [ctypes.wintypes.HWND, ctypes.c_int]
            user32.GetWindowLongPtrW.restype = ctypes.c_long
            user32.SetWindowLongPtrW.argtypes = [
                ctypes.wintypes.HWND, ctypes.c_int, ctypes.c_long
            ]
            user32.SetWindowLongPtrW.restype = ctypes.c_long
            user32.MoveWindow.argtypes = [
                ctypes.wintypes.HWND, ctypes.c_int, ctypes.c_int,
                ctypes.c_int, ctypes.c_int, ctypes.wintypes.BOOL,
            ]
            user32.ShowWindow.argtypes = [ctypes.wintypes.HWND, ctypes.c_int]
            user32.SetWindowPos.argtypes = [
                ctypes.wintypes.HWND, ctypes.wintypes.HWND,
                ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                ctypes.c_uint,
            ]

            # Убираем рамку, делаем дочерним
            style = user32.GetWindowLongPtrW(chrome_hwnd, GWL_STYLE)
            style = (style & ~WS_CAPTION & ~WS_THICKFRAME
                     & ~WS_BORDER & ~WS_DLGFRAME)
            style = style | WS_CHILD | WS_VISIBLE
            user32.SetWindowLongPtrW(chrome_hwnd, GWL_STYLE, style)

            ex_style = user32.GetWindowLongPtrW(chrome_hwnd, GWL_EXSTYLE)
            ex_style = ex_style & ~WS_EX_WINDOWEDGE & ~WS_EX_DLGMODALFRAME
            user32.SetWindowLongPtrW(chrome_hwnd, GWL_EXSTYLE, ex_style)

            # Встраиваем в контейнер
            user32.SetParent(chrome_hwnd, host_hwnd)

            self._chrome_hwnd = chrome_hwnd
            self._chrome_embedded = True

            # Ждём layout finalization перед MoveWindow (showMaximized может не
            # успеть обновить геометрию виджетов к этому моменту)
            def _finalize_embed():
                w = self.browser_stack.width()
                h = self.browser_stack.height()
                tb = self._compute_toolbar_offset()
                dpi = self._dpi_scale
                pw = int(w * dpi)   # физические пиксели для Win32
                ph = int(h * dpi)

                # Применяем стиль + размер одним вызовом SetWindowPos
                HWND_TOP = 0
                SWP_SHOWWINDOW = 0x0040
                user32.SetWindowPos(
                    chrome_hwnd, HWND_TOP,
                    0, -tb, max(pw, 100), max(ph, 100) + tb,
                    SWP_FRAMECHANGED | SWP_SHOWWINDOW,
                )

                self.log(f"  Chrome встроен (host: {self._chrome_host.width()}x{self._chrome_host.height()}, stack: {w}x{h})")

                # Скрываем оверлей загрузки только после применения корректных размеров
                self._hide_loading_overlay()

                # Передаём фокус Chrome и устанавливаем хук
                QTimer.singleShot(500, self._focus_chrome)
                self._install_chrome_focus_hook()

                # Ресайзим Chrome (обновляет все дочерние окна)
                self._resize_browser(pw, ph + tb)

                # Принудительный resize через 500мс — layout может быть ещё не финализирован
                def _delayed_resize():
                    self._last_chrome_size = None  # сбросить кэш
                    self._resize_chrome()
                QTimer.singleShot(500, _delayed_resize)

                # Таймер подгонки размера (редкий — основной ресайз через resizeEvent)
                self._chrome_resize_timer = QTimer()
                self._chrome_resize_timer.timeout.connect(self._resize_chrome)
                self._chrome_resize_timer.start(2000)

                # Проверяем авторизацию на krisha.kz через 2 сек
                QTimer.singleShot(2000, self._check_krisha_auth)

            # Даём Qt event loop время финализировать layout
            QTimer.singleShot(50, _finalize_embed)

        except Exception as e:
            self.log(f"  -- Не удалось встроить Chrome: {e}")
            self._embed_retries += 1
            if self._embed_retries < 30:
                QTimer.singleShot(1000, self._embed_chrome)

    def _resize_browser(self, w, h):
        """Ресайзит Chrome через Win32 MoveWindow + планирует viewport.
        
        w, h — физические пиксели (уже с учётом DPI).
        """
        tb = self._compute_toolbar_offset()
        hwnd = self._chrome_hwnd
        if hwnd:
            try:
                import ctypes
                ctypes.windll.user32.MoveWindow(hwnd, 0, -tb, max(w, 100), max(h, 100) + tb, True)
            except Exception:
                pass
        # Viewport в логических пикселях для Playwright
        dpi = self._dpi_scale
        lw = int(w / dpi) if dpi > 0 else w
        lh = int(h / dpi) if dpi > 0 else h
        self._schedule_viewport(lw, lh + tb)

    def _schedule_viewport(self, w, h):
        """Планирует обновление Playwright viewport с задержкой."""
        self._pending_viewport = (max(w, 100), max(h, 100))
        if not hasattr(self, '_viewport_timer'):
            self._viewport_timer = QTimer()
            self._viewport_timer.setSingleShot(True)
            self._viewport_timer.timeout.connect(self._apply_viewport)
        self._viewport_timer.start(300)

    def _apply_viewport(self):
        """Применяет Playwright viewport после окончания ресайза."""
        vp = getattr(self, '_pending_viewport', None)
        if not vp:
            return
        w, h = vp
        def _bg():
            try:
                from parser_playwright import _run_in_pw_thread, _page
                def _do_resize():
                    if _page:
                        _page.set_viewport_size({"width": max(w, 100), "height": max(h, 100)})
                _run_in_pw_thread(_do_resize)
            except Exception:
                pass
        threading.Thread(target=_bg, daemon=True).start()

    def _resize_chrome(self):
        """Подгоняет размер встроенного Chrome под контейнер."""
        if not self._chrome_embedded or not self._chrome_hwnd:
            return
        w = self.browser_stack.width()
        h = self.browser_stack.height()
        if w > 50 and h > 50:
            tb = self._compute_toolbar_offset()
            dpi = self._dpi_scale
            pw = int(w * dpi)   # физические пиксели для Win32
            ph = int(h * dpi)
            try:
                import ctypes
                ctypes.windll.user32.MoveWindow(
                    self._chrome_hwnd, 0, -tb,
                    max(pw, 100), max(ph, 100) + tb, True
                )
            except Exception:
                pass
            # Viewport в логических пикселях (Playwright сам учитывает DPI)
            new_size = (w, h + tb)
            if getattr(self, '_last_chrome_size', None) != new_size:
                self._last_chrome_size = new_size
                self._schedule_viewport(w, h + tb)

    # ═══════════════════════════════════════════════════════════════
    #  Режим 2: Рассылка (через wa-server)
    # ═══════════════════════════════════════════════════════════════

    def _start_mailing(self):
        self.log("📨 Проверяю WA-сервер...")
        def _bg():
            try:
                st = wa_client.get_status()
                ready = st.get("ready", False)
            except Exception:
                ready = False
            self._invoke_signal.emit(lambda: self._start_mailing_after_check(ready))
        threading.Thread(target=_bg, daemon=True).start()

    def _start_mailing_after_check(self, wa_ready):
        if not wa_ready:
            self.log("⚠️ WA-сервер не готов! Проверьте подключение.")
            self.btn_mailing.setChecked(False)
            return

        # Проверяем дневной лимит
        daily_limit = self.cfg["whatsapp"].get("daily_limit", 50)
        sent_today = get_sent_today_count()
        remaining = daily_limit - sent_today
        if remaining <= 0:
            self.log(f"⛔ Дневной лимит исчерпан ({sent_today}/{daily_limit})")
            self.btn_mailing.setChecked(False)
            return

        unsent = get_unsent_phones()
        if not unsent:
            self.log("📭 Нет номеров для рассылки")
            self.btn_mailing.setChecked(False)
            return

        # Ограничиваем очередь дневным лимитом
        if len(unsent) > remaining:
            unsent = unsent[:remaining]
            self.log(f"📊 Лимит: осталось {remaining} из {daily_limit} на сегодня")

        self._mail_queue = unsent
        self._mail_idx = 0
        self._mail_stop = False
        self._mail_sent_session = 0
        self.btn_mailing.setChecked(True)
        self.btn_mailing.setStyleSheet(
            "QPushButton { background: #00a884; color: white; border: 1px solid #00a884; "
            "border-radius: 4px; padding: 3px 10px; font-size: 11px; }"
        )

        delay = self.cfg["whatsapp"].get("message_delay_seconds", 30)
        self.log(f"📨 Рассылка: {len(unsent)} номеров (пауза {delay} сек, лимит {daily_limit}/сутки)")
        self._mail_next()

    def _mail_next(self):
        if self._mail_stop:
            self.log("⏹ Рассылка остановлена")
            self._finish_mailing()
            return
        i = self._mail_idx
        total = len(self._mail_queue)
        if i >= total:
            self._finish_mailing()
            return

        # Проверяем дневной лимит на лету
        daily_limit = self.cfg["whatsapp"].get("daily_limit", 50)
        sent_today = get_sent_today_count()
        if sent_today >= daily_limit:
            self.log(f"⛔ Дневной лимит достигнут ({sent_today}/{daily_limit})")
            self._finish_mailing()
            return

        entry = self._mail_queue[i]
        self._mail_idx += 1
        phone = entry["phone"]
        self.progress.setMaximum(total)
        self.progress.setValue(i + 1)
        self.log(f"📨 ({i+1}/{total}) → {phone}")

        use_ai = bool(self.cfg["deepseek"]["api_key"])
        cfg_copy = dict(self.cfg)
        first_msg = self.cfg["whatsapp"]["first_message"]
        listing_title = entry.get("listing_title", "")
        price = entry.get("price", "")

        def _bg():
            # Проверяем WA перед отправкой
            try:
                st = wa_client.get_status()
                if not st.get("ready"):
                    self._invoke_signal.emit(lambda: self._mail_send_result(phone, None, "wa_down", entry))
                    return
            except Exception:
                self._invoke_signal.emit(lambda: self._mail_send_result(phone, None, "wa_down", entry))
                return

            # Проверяем есть ли номер в WhatsApp
            try:
                registered = wa_client.check_phone(phone)
                if not registered:
                    self._invoke_signal.emit(lambda: self._mail_send_result(phone, None, "no_wa", entry))
                    return
            except Exception:
                pass  # если проверка не удалась — пробуем отправить

            if use_ai:
                try:
                    msg = generate_first_message(listing_title, price, cfg_copy)
                except Exception:
                    msg = first_msg
            else:
                msg = first_msg

            # Защита от пустого сообщения
            if not msg or not msg.strip():
                msg = first_msg
            if not msg or not msg.strip():
                msg = "Здравствуйте! Увидел ваше объявление на Крыше. Могу помочь с продажей вашей недвижимости. Интересно?"

            result = wa_client.send_message(phone, msg)
            self._invoke_signal.emit(lambda: self._mail_send_result(phone, msg, result, entry))

        threading.Thread(target=_bg, daemon=True).start()

    def _mail_send_result(self, phone, msg, result, entry):
        """Обработка результата отправки в главном потоке."""
        if result == "wa_down":
            self.log("⚠️ WA потерял соединение, пропускаю...")
        elif result == "no_wa":
            mark_no_whatsapp(phone)
            self.log(f"  📵 Нет WhatsApp: {phone} (помечен)")
        elif isinstance(result, dict):
            if result.get("success"):
                mark_sent(phone)
                conv_phone = _normalize_phone(phone)
                add_conversation(conv_phone, "assistant", msg)
                self.log(f"  ✅ Доставлено: {phone}")
                if self._current_mode == self.MODE_WA:
                    self._messenger_refresh_chats()
            elif result.get("error") == "not_registered":
                mark_no_whatsapp(phone)
                self.log(f"  📵 Не в WhatsApp: {phone} (помечен)")
            else:
                self.log(f"  ❌ Ошибка: {result.get('error', '?')}")

        self._update_stats()
        self._mail_delay_with_stop()

    def _mail_delay_with_stop(self):
        """Задержка между сообщениями с возможностью быстрого стопа."""
        delay = self.cfg["whatsapp"].get("message_delay_seconds", 30)
        self._mail_delay_remaining = delay
        self._mail_delay_timer = QTimer()
        self._mail_delay_timer.timeout.connect(self._mail_delay_tick)
        self._mail_delay_timer.start(1000)  # тикаем каждую секунду

    def _mail_delay_tick(self):
        if self._mail_stop:
            self._mail_delay_timer.stop()
            self.log("⏹ Рассылка остановлена")
            self._finish_mailing()
            return
        self._mail_delay_remaining -= 1
        if self._mail_delay_remaining <= 0:
            self._mail_delay_timer.stop()
            self._mail_next()

    def _finish_mailing(self):
        self.log("✅ Рассылка завершена")
        self._mail_queue = []
        self.btn_mailing.setChecked(False)
        self.btn_mailing.setStyleSheet("")
        self.progress.setValue(0)
        self._update_stats()
        self._refresh_phones()
        self._messenger_refresh_chats()


    # ═══════════════════════════════════════════════════════════════
    #  Синхронизация входящих (всегда работает когда WA подключён)
    # ═══════════════════════════════════════════════════════════════

    def _sync_incoming_tick(self):
        """Забирает входящие из wa-server, сохраняет в БД. Работает всегда."""
        if not self.wa_server_ready:
            return
        if getattr(self, '_sync_processing', False):
            return
        self._sync_processing = True
        ai_on = self.btn_ai_bot.isChecked()
        cfg_copy = dict(self.cfg) if ai_on else None
        log = self._log_signal.emit

        # Диагностика — каждый 30-й тик логируем что sync работает
        self._sync_tick_count = getattr(self, '_sync_tick_count', 0) + 1
        if self._sync_tick_count % 30 == 1:
            log(f"🔄 Sync tick #{self._sync_tick_count} (ai_on={ai_on})")

        def _bg():
            try:
                self._sync_work(ai_on, cfg_copy, log)
            finally:
                self._sync_processing = False

        threading.Thread(target=_bg, daemon=True).start()

    def _sync_work(self, ai_on, cfg_copy, log):
        """Фоновая синхронизация входящих + опционально AI ответы."""
        try:
            unread = wa_client.get_unread()
        except Exception as e:
            log(f"⚠️ Ошибка синхронизации: {e}")
            return
        if not unread:
            return
        log(f"📬 Получено {len(unread)} чатов с непрочитанными")

        had_messages = False

        for phone, messages in unread.items():
            # Пропускаем невалидные ключи (raw chatId вместо номера)
            if not phone:
                continue
            if '@' in phone:
                log(f"⚠️ Пропуск невалидного ключа: {phone}")
                continue

            # LID-контакты приходят как "lid:12345..." — принимаем их тоже
            is_lid = phone.startswith("lid:")

            if not is_lid:
                # Пропускаем невалидные номера (слишком длинные — не реальные телефоны)
                digits = phone.lstrip('+').replace(' ', '')
                if len(digits) > 15 or len(digits) < 10:
                    log(f"⚠️ Пропуск невалидного номера: {phone}")
                    continue

            # Помечаем как прочитанные на wa-server
            try:
                wa_client.mark_read(phone)
            except Exception:
                pass

            # Для LID-контактов используем phone как есть, для обычных — нормализуем
            if is_lid:
                norm_phone = phone  # "lid:12345..."
            else:
                norm_phone = _normalize_phone(phone)

            for msg_data in messages:
                body = msg_data.get("body", "")
                if not body:
                    continue

                log(f"💬 Входящее от {norm_phone}: {body[:60]}...")
                had_messages = True

                # Сохраняем в БД (всегда)
                add_conversation(norm_phone, "user", body)
                mark_replied(norm_phone)

                # AI ответ (только если бот включён)
                if ai_on and cfg_copy:
                    log(f"🤖 Генерирую AI ответ для {norm_phone}...")
                    try:
                        from ai_bot import get_ai_response
                        ai_reply = get_ai_response(norm_phone, body, cfg_copy)
                        log(f"🤖 AI → {norm_phone}: {ai_reply[:60]}...")

                        result = wa_client.send_message(phone, ai_reply)
                        if result.get("success"):
                            log(f"✅ Ответ доставлен: {norm_phone}")
                        else:
                            log(f"❌ Ошибка отправки: {result.get('error', '?')}")
                    except Exception as e:
                        log(f"❌ AI ошибка ({norm_phone}): {e}")
                elif ai_on:
                    log(f"⚠️ ai_on=True но cfg_copy=None!")
                else:
                    log(f"ℹ️ AI бот выключен, пропускаю ответ")

        if had_messages:
            self._msg_needs_refresh = True
            # Сигнал в GUI-поток для немедленного обновления мессенджера
            try:
                self._refresh_messenger_signal.emit()
            except Exception:
                pass

    def _after_sync(self):
        """Вызывается в GUI-потоке после синхронизации входящих."""
        self._messenger_refresh_chats()
        self._update_stats()

    def _messenger_auto_refresh(self):
        """Таймер GUI — обновляет мессенджер только если появились новые сообщения."""
        # Проверяем флаг от sync — новые сообщения пришли
        if getattr(self, '_msg_needs_refresh', False):
            self._msg_needs_refresh = False
            self._messenger_refresh_chats()
            self._update_stats()
            return

        if self._current_mode != self.MODE_WA:
            return

        if not self._msg_selected_phone:
            return

        # Проверяем кол-во сообщений в БД — если изменилось, обновляем диалог
        msgs = get_conversation_full(self._msg_selected_phone)
        new_count = len(msgs)
        old_count = getattr(self, '_msg_last_count', -1)
        if new_count != old_count:
            self._msg_last_count = new_count
            self._messenger_load_messages(self._msg_selected_phone)

    def _animate_wa_dots(self):
        """Анимация точек на оверлее загрузки WA."""
        dots = ["", ".", "..", "..."]
        self._wa_dot_step = (self._wa_dot_step + 1) % len(dots)
        if hasattr(self, '_wa_overlay_dots'):
            self._wa_overlay_dots.setText(dots[self._wa_dot_step])

    # ═══════════════════════════════════════════════════════════════
    #  AI Бот (через wa-server + DeepSeek)
    # ═══════════════════════════════════════════════════════════════

    def _start_ai_bot(self):
        if not self.wa_server_ready:
            self.log("⚠️ WA-сервер не подключён!")
            self.btn_ai_bot.setChecked(False)
            return
        if not self.cfg["deepseek"]["api_key"]:
            self.log("⚠️ Задайте API ключ DeepSeek в настройках!")
            self.btn_ai_bot.setChecked(False)
            return
        self.btn_ai_bot.setChecked(True)
        self.btn_ai_bot.setStyleSheet(
            "QPushButton { background: #00a884; color: white; border: 1px solid #00a884; "
            "border-radius: 4px; padding: 3px 10px; font-size: 11px; }"
        )
        self._messenger_update_ai_status("AI Бот: работает")
        self.log("🤖 AI Бот включён — отвечает на входящие")

    def _stop_ai_bot(self):
        self.btn_ai_bot.setChecked(False)
        self.btn_ai_bot.setStyleSheet("")
        self._messenger_update_ai_status("AI Бот: выключен")
        self.log("🤖 AI Бот выключен")

    # ═══════════════════════════════════════════════════════════════
    #  Утилиты
    # ═══════════════════════════════════════════════════════════════

    def log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{ts}] {msg}")

    def _on_invoke(self, fn):
        """Выполняет callable в GUI-потоке (слот для _invoke_signal)."""
        try:
            fn()
        except Exception as e:
            self.log(f"⚠️ invoke ошибка: {e}")

    def _update_stats(self):
        s = get_stats()
        today = get_sent_today_count()
        limit = self.cfg["whatsapp"].get("daily_limit", 50)
        self.lbl_stats.setText(
            f"Всего: {s['total']} | Отпр: {s['sent']} | Отв: {s['replied']} | "
            f"Сегодня: {today}/{limit}"
        )

    def _refresh_phones(self):
        self._load_db_table()

    def _create_db_tab(self):
        tab = QWidget()
        lay = QVBoxLayout(tab)
        lay.setContentsMargins(4, 4, 4, 4)
        lay.setSpacing(4)

        # Фильтры
        filt_row = QWidget()
        fl = QHBoxLayout(filt_row)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.setSpacing(4)

        self.db_filter = QComboBox()
        self.db_filter.addItem("Все", "all")
        self.db_filter.addItem("Не отправлено", "unsent")
        self.db_filter.addItem("Отправлено", "sent")
        self.db_filter.addItem("С ответом", "replied")
        self.db_filter.addItem("Нет WhatsApp", "no_wa")
        self.db_filter.currentIndexChanged.connect(self._load_db_table)
        fl.addWidget(QLabel("Фильтр:"))
        fl.addWidget(self.db_filter)

        self.db_search = QLineEdit()
        self.db_search.setPlaceholderText("Поиск по номеру...")
        self.db_search.textChanged.connect(self._load_db_table)
        fl.addWidget(self.db_search)

        fl.addStretch()
        self.db_count_lbl = QLabel("0")
        self.db_count_lbl.setStyleSheet("color: #78909c; font-size: 11px;")
        fl.addWidget(self.db_count_lbl)

        lay.addWidget(filt_row)

        # Таблица
        self.db_table = QTableWidget()
        self.db_table.setColumnCount(5)
        self.db_table.setHorizontalHeaderLabels(["Телефон", "Статус", "Объявление", "Цена", "Дата"])
        self.db_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.db_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.db_table.setAlternatingRowColors(True)
        self.db_table.verticalHeader().setVisible(False)
        self.db_table.verticalHeader().setDefaultSectionSize(22)
        h = self.db_table.horizontalHeader()
        h.setStretchLastSection(True)
        h.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        h.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.db_table.setStyleSheet("""
            QTableWidget { background: #11111b; color: #cdd6f4; gridline-color: #313244; font-size: 11px; }
            QTableWidget::item { padding: 2px 4px; }
            QTableWidget::item:selected { background: #45475a; }
            QHeaderView::section { background: #181825; color: #a6adc8; border: 1px solid #313244; padding: 3px; font-size: 10px; }
            QTableWidget::item:alternate { background: #181825; }
        """)
        self.db_table.doubleClicked.connect(self._on_db_double_click)
        lay.addWidget(self.db_table)

        # Кнопки
        btn_row = QWidget()
        bl = QHBoxLayout(btn_row)
        bl.setContentsMargins(0, 0, 0, 0)
        bl.setSpacing(4)

        btn_refresh = QPushButton("Обновить")
        btn_refresh.clicked.connect(self._load_db_table)
        bl.addWidget(btn_refresh)

        btn_del = QPushButton("Удалить")
        btn_del.clicked.connect(self._delete_selected_phones)
        bl.addWidget(btn_del)

        btn_reset = QPushButton("Сбросить статус")
        btn_reset.clicked.connect(self._reset_selected_status)
        bl.addWidget(btn_reset)

        btn_export = QPushButton("📥 Экспорт Excel")
        btn_export.setStyleSheet("""
            QPushButton { background: #1e6f50; color: #ffffff; border: none;
                          border-radius: 4px; padding: 3px 12px; font-size: 11px; font-weight: bold; }
            QPushButton:hover { background: #00a884; }
        """)
        btn_export.clicked.connect(self._export_db_to_excel)
        bl.addWidget(btn_export)

        bl.addStretch()
        lay.addWidget(btn_row)

        # Загрузить при старте
        QTimer.singleShot(500, self._load_db_table)

        return tab

    def _load_db_table(self):
        filt = self.db_filter.currentData() if hasattr(self, 'db_filter') else "all"
        search = self.db_search.text().strip() if hasattr(self, 'db_search') else ""

        all_phones = get_all_phones()

        # Фильтрация
        if filt == "unsent":
            all_phones = [p for p in all_phones if not p["message_sent"] and not p.get("no_whatsapp")]
        elif filt == "sent":
            all_phones = [p for p in all_phones if p["message_sent"]]
        elif filt == "replied":
            all_phones = [p for p in all_phones if p["replied"]]
        elif filt == "no_wa":
            all_phones = [p for p in all_phones if p.get("no_whatsapp")]

        if search:
            all_phones = [p for p in all_phones if search in p.get("phone", "")]

        self.db_table.setRowCount(len(all_phones))
        for i, p in enumerate(all_phones):
            # Телефон
            self.db_table.setItem(i, 0, QTableWidgetItem(p.get("phone", "")))

            # Статус
            if p.get("no_whatsapp"):
                status = "Нет WA"
            elif p.get("replied"):
                status = "Ответил"
            elif p.get("message_sent"):
                status = "Отправлено"
            else:
                status = "Ожидает"
            item_status = QTableWidgetItem(status)
            self.db_table.setItem(i, 1, item_status)

            # Объявление
            title = (p.get("listing_title") or "")[:50]
            item_title = QTableWidgetItem(title)
            item_title.setToolTip(p.get("listing_url", ""))
            self.db_table.setItem(i, 2, item_title)

            # Цена
            self.db_table.setItem(i, 3, QTableWidgetItem(p.get("price", "")))

            # Дата
            date_str = (p.get("parsed_at") or "")[:10]
            self.db_table.setItem(i, 4, QTableWidgetItem(date_str))

        self.db_count_lbl.setText(f"{len(all_phones)} шт.")

    def _export_db_to_excel(self):
        """Экспортирует данные из таблицы в Excel файл."""
        from PyQt6.QtWidgets import QFileDialog
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        except ImportError:
            _styled_info(self, "Ошибка", "Модуль openpyxl не установлен.\npip install openpyxl")
            return

        # Получаем данные с текущим фильтром
        filt = self.db_filter.currentData() if hasattr(self, 'db_filter') else "all"
        search = self.db_search.text().strip() if hasattr(self, 'db_search') else ""
        all_phones = get_all_phones()

        if filt == "unsent":
            all_phones = [p for p in all_phones if not p["message_sent"] and not p.get("no_whatsapp")]
        elif filt == "sent":
            all_phones = [p for p in all_phones if p["message_sent"]]
        elif filt == "replied":
            all_phones = [p for p in all_phones if p["replied"]]
        elif filt == "no_wa":
            all_phones = [p for p in all_phones if p.get("no_whatsapp")]
        if search:
            all_phones = [p for p in all_phones if search in p.get("phone", "")]

        if not all_phones:
            _styled_info(self, "Экспорт", "Нет данных для экспорта.")
            return

        # Диалог сохранения
        from datetime import datetime as _dt
        default_name = f"krisha_phones_{_dt.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить Excel", default_name,
            "Excel файлы (*.xlsx);;Все файлы (*)"
        )
        if not path:
            return

        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Телефоны"

            # Заголовки
            headers = ["Телефон", "Статус", "Объявление", "Ссылка", "Цена", "Дата"]
            header_fill = PatternFill(start_color="1e6f50", end_color="1e6f50", fill_type="solid")
            header_font = Font(bold=True, color="FFFFFF", size=11)
            thin_border = Border(
                left=Side(style='thin', color='313244'),
                right=Side(style='thin', color='313244'),
                top=Side(style='thin', color='313244'),
                bottom=Side(style='thin', color='313244'),
            )

            for col_idx, h in enumerate(headers, 1):
                cell = ws.cell(row=1, column=col_idx, value=h)
                cell.font = header_font
                cell.fill = header_fill
                cell.alignment = Alignment(horizontal='center')
                cell.border = thin_border

            # Данные
            for row_idx, p in enumerate(all_phones, 2):
                phone = p.get("phone", "")
                if p.get("no_whatsapp"):
                    status = "Нет WA"
                elif p.get("replied"):
                    status = "Ответил"
                elif p.get("message_sent"):
                    status = "Отправлено"
                else:
                    status = "Ожидает"
                title = p.get("listing_title", "") or ""
                url = p.get("listing_url", "") or ""
                price = p.get("price", "") or ""
                date_str = (p.get("parsed_at") or "")[:10]

                ws.cell(row=row_idx, column=1, value=phone).border = thin_border
                ws.cell(row=row_idx, column=2, value=status).border = thin_border
                ws.cell(row=row_idx, column=3, value=title).border = thin_border
                url_cell = ws.cell(row=row_idx, column=4, value=url)
                url_cell.border = thin_border
                if url:
                    url_cell.hyperlink = url
                    url_cell.font = Font(color="0563C1", underline="single")
                ws.cell(row=row_idx, column=5, value=price).border = thin_border
                ws.cell(row=row_idx, column=6, value=date_str).border = thin_border

            # Ширина колонок
            ws.column_dimensions['A'].width = 18
            ws.column_dimensions['B'].width = 14
            ws.column_dimensions['C'].width = 40
            ws.column_dimensions['D'].width = 45
            ws.column_dimensions['E'].width = 16
            ws.column_dimensions['F'].width = 12

            # Автофильтр
            ws.auto_filter.ref = f"A1:F{len(all_phones) + 1}"

            wb.save(path)
            self.log(f"📥 Экспорт: {len(all_phones)} записей → {os.path.basename(path)}")
            _styled_info(self, "Экспорт завершён",
                         f"Сохранено {len(all_phones)} записей\n{os.path.basename(path)}")
        except Exception as e:
            self.log(f"  Ошибка экспорта: {e}")
            _styled_info(self, "Ошибка экспорта", str(e))

    def _on_db_double_click(self, index):
        """Открыть диалог при двойном клике на номер, или объявление при клике на другие колонки."""
        row = index.row()
        col = index.column()
        phone_item = self.db_table.item(row, 0)
        if not phone_item:
            return
        phone = phone_item.text()
        if col <= 1:
            # Клик на телефон/статус — открыть мессенджер с этим чатом
            self._msg_selected_phone = phone
            self._messenger_refresh_chats()
            # Выбрать чат в списке
            for i in range(self._msg_chat_list.count()):
                if self._msg_chat_list.item(i).data(Qt.ItemDataRole.UserRole) == phone:
                    self._msg_chat_list.setCurrentRow(i)
                    break
            # Переключить на WhatsApp (мессенджер)
            self._switch_mode(self.MODE_WA)
        else:
            # Клик на объявление/цену/дату — открыть URL в системном браузере
            title_item = self.db_table.item(row, 2)
            if title_item:
                url = title_item.toolTip()
                if url:
                    import webbrowser
                    webbrowser.open(url)

    def _delete_selected_phones(self):
        rows = set(idx.row() for idx in self.db_table.selectedIndexes())
        if not rows:
            return
        from database import get_connection
        conn = get_connection()
        for row in rows:
            phone_item = self.db_table.item(row, 0)
            if phone_item:
                phone = phone_item.text()
                conn.execute("DELETE FROM phones WHERE phone = ?", (phone,))
                conn.execute("DELETE FROM conversations WHERE phone = ?", (phone,))
        conn.commit()
        conn.close()
        self.log(f"🗑 Удалено {len(rows)} записей")
        self._load_db_table()
        self._update_stats()

    def _reset_selected_status(self):
        rows = set(idx.row() for idx in self.db_table.selectedIndexes())
        if not rows:
            return
        from database import get_connection
        conn = get_connection()
        for row in rows:
            phone_item = self.db_table.item(row, 0)
            if phone_item:
                phone = phone_item.text()
                conn.execute("UPDATE phones SET message_sent = 0, replied = 0 WHERE phone = ?", (phone,))
        conn.commit()
        conn.close()
        self.log(f"↩ Сброшен статус у {len(rows)} записей")
        self._load_db_table()
        self._update_stats()

    # ═══════════════════════════════════════════════════════════════
    #  Мессенджер (WhatsApp-стиль, index 1 в browser_stack)
    # ═══════════════════════════════════════════════════════════════

    def _make_messenger(self):
        container = QWidget()
        container.setObjectName("waContainer")
        # Master stylesheet for the entire messenger — overrides global dark theme
        container.setStyleSheet("""
            QWidget#waContainer { background: #efeae2; }
            QWidget#waQrBar { background: #f0f2f5; border-bottom: 2px solid #00a884; }
            QWidget#waLeftPanel { background: #ffffff; border-right: 1px solid #e9edef; }
            QWidget#waLeftHeader { background: #f0f2f5; }
            QWidget#waSearchWrap { background: #ffffff; }
            QWidget#waRightPanel { background: #efeae2; }
            QWidget#waRightHeader { background: #f0f2f5; border-bottom: 1px solid #e9edef; }
            QWidget#waInputBar { background: #f0f2f5; }
            QWidget#waBottomBar { background: #f0f2f5; border-top: 1px solid #e9edef; }
            QLabel#waLbl { color: #111b21; }
            QLabel#waLblGray { color: #667781; }
            QLabel#waLblGreen { color: #00a884; }
        """)
        outer = QVBoxLayout(container)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ── QR-бар (сверху, скрыт по умолчанию) ──
        self._msg_qr_bar = QWidget()
        self._msg_qr_bar.setObjectName("waQrBar")
        self._msg_qr_bar.setVisible(False)
        qr_lay = QHBoxLayout(self._msg_qr_bar)
        qr_lay.setContentsMargins(16, 10, 16, 10)
        qr_lay.setSpacing(16)

        self.wa_qr_img = QLabel()
        self.wa_qr_img.setFixedSize(120, 120)
        self.wa_qr_img.setStyleSheet("background: white; border-radius: 6px;")
        qr_lay.addWidget(self.wa_qr_img)

        qr_info = QVBoxLayout()
        self.wa_qr_status = QLabel("Отсканируйте QR-код")
        self.wa_qr_status.setStyleSheet("color: #00a884; font-size: 14px; font-weight: bold;")
        qr_info.addWidget(self.wa_qr_status)
        qr_hint = QLabel(
            "WhatsApp > Связанные устройства > Привязка устройства\n"
            "Отсканируйте QR-код для подключения рассылки и AI бота"
        )
        qr_hint.setStyleSheet("color: #8696a0; font-size: 11px;")
        qr_hint.setWordWrap(True)
        qr_info.addWidget(qr_hint)
        qr_info.addStretch()
        qr_lay.addLayout(qr_info, 1)
        outer.addWidget(self._msg_qr_bar)

        # ── Основная область ──
        main_area = QWidget()
        main_area.setObjectName("waContainer")
        main_lay = QHBoxLayout(main_area)
        main_lay.setContentsMargins(0, 0, 0, 0)
        main_lay.setSpacing(0)

        # ── Левая панель: список чатов ──
        left = QWidget()
        left.setObjectName("waLeftPanel")
        left.setFixedWidth(300)
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(0)

        header_left = QWidget()
        header_left.setObjectName("waLeftHeader")
        header_left.setFixedHeight(50)
        hl = QHBoxLayout(header_left)
        hl.setContentsMargins(16, 0, 10, 0)
        lbl_chats = QLabel("Чаты")
        lbl_chats.setStyleSheet("color: #111b21; font-size: 16px; font-weight: bold;")
        hl.addWidget(lbl_chats)
        hl.addStretch()
        btn_clear_all = QPushButton("Очистить все")
        btn_clear_all.setFixedHeight(24)
        btn_clear_all.setStyleSheet(
            "QPushButton { background: #e9edef; color: #e53935; border: none; "
            "border-radius: 4px; padding: 2px 8px; font-size: 10px; }"
            "QPushButton:hover { background: #e53935; color: white; }"
        )
        btn_clear_all.clicked.connect(self._messenger_clear_all_chats)
        hl.addWidget(btn_clear_all)
        hl.addSpacing(6)
        self._msg_chat_count = QLabel("0")
        self._msg_chat_count.setStyleSheet("color: #667781; font-size: 11px;")
        hl.addWidget(self._msg_chat_count)
        left_lay.addWidget(header_left)

        search_wrap = QWidget()
        search_wrap.setObjectName("waSearchWrap")
        search_wrap.setFixedHeight(40)
        sw_lay = QHBoxLayout(search_wrap)
        sw_lay.setContentsMargins(10, 4, 10, 4)
        self._msg_search = QLineEdit()
        self._msg_search.setPlaceholderText("Поиск или новый чат")
        self._msg_search.setStyleSheet(
            "QLineEdit { background: #f0f2f5; color: #111b21; border: none; "
            "border-radius: 8px; padding: 6px 12px; font-size: 12px; }"
            "QLineEdit::placeholder { color: #8696a0; }"
        )
        self._msg_search.textChanged.connect(self._messenger_filter_chats)
        sw_lay.addWidget(self._msg_search)
        left_lay.addWidget(search_wrap)

        self._msg_chat_list = QListWidget()
        self._msg_chat_list.setWordWrap(False)
        self._msg_chat_list.setTextElideMode(Qt.TextElideMode.ElideRight)
        self._msg_chat_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._msg_chat_list.setStyleSheet("""
            QListWidget { background: #ffffff; border: none; outline: none; }
            QListWidget::item {
                padding: 10px 16px; border-bottom: 1px solid #e9edef;
                color: #111b21; min-height: 32px;
            }
            QListWidget::item:selected { background: #f0f2f5; }
            QListWidget::item:hover { background: #f5f6f6; }
        """)
        self._msg_chat_list.currentRowChanged.connect(self._messenger_on_chat_selected)
        left_lay.addWidget(self._msg_chat_list)

        main_lay.addWidget(left)

        # ── Правая панель: переписка ──
        right = QWidget()
        right.setObjectName("waRightPanel")
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)

        header_right = QWidget()
        header_right.setObjectName("waRightHeader")
        header_right.setFixedHeight(50)
        hr = QHBoxLayout(header_right)
        hr.setContentsMargins(16, 0, 10, 0)

        avatar = QLabel("W")
        avatar.setFixedSize(36, 36)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet(
            "background: #00a884; color: white; border-radius: 18px; "
            "font-size: 16px; font-weight: bold;"
        )
        hr.addWidget(avatar)
        hr.addSpacing(10)

        self._msg_current_phone = QLabel("Выберите чат")
        self._msg_current_phone.setStyleSheet("color: #111b21; font-size: 14px; font-weight: bold;")
        hr.addWidget(self._msg_current_phone)
        hr.addStretch()
        self._msg_count_lbl = QLabel("")
        self._msg_count_lbl.setStyleSheet("color: #667781; font-size: 11px;")
        hr.addWidget(self._msg_count_lbl)

        btn_clear = QPushButton("Очистить контекст")
        btn_clear.setFixedHeight(28)
        btn_clear.setStyleSheet(
            "QPushButton { background: #e9edef; color: #e53935; border: none; "
            "border-radius: 6px; padding: 4px 12px; font-size: 11px; }"
            "QPushButton:hover { background: #e53935; color: white; }"
        )
        btn_clear.clicked.connect(self._messenger_clear_chat)
        hr.addWidget(btn_clear)
        right_lay.addWidget(header_right)

        self._msg_display = QTextEdit()
        self._msg_display.setObjectName("waDisplay")
        self._msg_display.setReadOnly(True)
        self._msg_display.setStyleSheet(
            "QTextEdit { background: #efeae2; color: #111b21; border: none; padding: 8px; "
            "selection-background-color: #bcd4e6; font-family: Segoe UI, sans-serif; }"
        )
        right_lay.addWidget(self._msg_display)

        # ── Поле ввода сообщения ──
        input_bar = QWidget()
        input_bar.setObjectName("waInputBar")
        input_bar.setFixedHeight(52)
        ib = QHBoxLayout(input_bar)
        ib.setContentsMargins(12, 8, 12, 8)
        ib.setSpacing(8)

        self._msg_input = QLineEdit()
        self._msg_input.setPlaceholderText("Введите сообщение...")
        self._msg_input.setStyleSheet(
            "QLineEdit { background: #ffffff; color: #111b21; border: 1px solid #e9edef; "
            "border-radius: 8px; padding: 8px 14px; font-size: 13px; }"
            "QLineEdit:focus { border-color: #00a884; }"
            "QLineEdit::placeholder { color: #8696a0; }"
        )
        self._msg_input.returnPressed.connect(self._messenger_send_message)
        ib.addWidget(self._msg_input, 1)

        btn_send = QPushButton("->")
        btn_send.setFixedSize(36, 36)
        btn_send.setStyleSheet(
            "QPushButton { background: #00a884; color: white; border: none; "
            "border-radius: 18px; font-size: 16px; font-weight: bold; }"
            "QPushButton:hover { background: #06cf9c; }"
            "QPushButton:disabled { background: #e9edef; color: #8696a0; }"
        )
        btn_send.clicked.connect(self._messenger_send_message)
        self._msg_send_btn = btn_send
        ib.addWidget(btn_send)

        right_lay.addWidget(input_bar)

        bottom_bar = QWidget()
        bottom_bar.setObjectName("waBottomBar")
        bottom_bar.setFixedHeight(28)
        bb = QHBoxLayout(bottom_bar)
        bb.setContentsMargins(16, 0, 16, 0)
        self._msg_ai_status = QLabel("AI Бот: выключен")
        self._msg_ai_status.setStyleSheet("color: #667781; font-size: 10px;")
        bb.addWidget(self._msg_ai_status)
        bb.addStretch()
        hint = QLabel("Сообщения синхронизируются с контекстом AI бота")
        hint.setStyleSheet("color: #8696a0; font-size: 10px;")
        bb.addWidget(hint)
        right_lay.addWidget(bottom_bar)

        main_lay.addWidget(right, 1)

        # ── Оверлей загрузки (показывается пока WA не подключён) ──
        self._wa_overlay = QWidget()
        self._wa_overlay.setStyleSheet("background: #1e1e2e;")
        ov_lay = QVBoxLayout(self._wa_overlay)
        ov_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ov_lay.setSpacing(0)

        # Иконка
        ov_icon = QLabel("W")
        ov_icon.setFixedSize(56, 56)
        ov_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        ov_icon.setStyleSheet(
            "background: #00a884; color: #ffffff; border-radius: 28px; "
            "font-size: 24px; font-weight: bold;"
        )
        ov_lay.addWidget(ov_icon, 0, Qt.AlignmentFlag.AlignCenter)
        ov_lay.addSpacing(16)

        # Заголовок
        self._wa_overlay_title = QLabel("Подключение к WhatsApp")
        self._wa_overlay_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._wa_overlay_title.setStyleSheet("color: #cdd6f4; font-size: 15px; font-weight: bold; background: transparent;")
        ov_lay.addWidget(self._wa_overlay_title)
        ov_lay.addSpacing(8)

        # QR-код в оверлее (скрыт по умолчанию)
        self._wa_overlay_qr = QLabel()
        self._wa_overlay_qr.setFixedSize(260, 260)
        self._wa_overlay_qr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._wa_overlay_qr.setStyleSheet("background: white; border-radius: 12px;")
        self._wa_overlay_qr.setVisible(False)
        ov_lay.addWidget(self._wa_overlay_qr, 0, Qt.AlignmentFlag.AlignCenter)
        ov_lay.addSpacing(8)

        # Анимированные точки
        self._wa_overlay_dots = QLabel("")
        self._wa_overlay_dots.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._wa_overlay_dots.setStyleSheet("color: #00a884; font-size: 24px; letter-spacing: 6px; background: transparent;")
        ov_lay.addWidget(self._wa_overlay_dots)
        ov_lay.addSpacing(12)

        # Подсказка
        self._wa_overlay_hint = QLabel("Ожидание инициализации сервера\nQR-код появится автоматически")
        self._wa_overlay_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._wa_overlay_hint.setStyleSheet("color: #585b70; font-size: 11px; background: transparent;")
        self._wa_overlay_hint.setWordWrap(True)
        ov_lay.addWidget(self._wa_overlay_hint)

        # Таймер анимации точек
        self._wa_dot_step = 0
        self._wa_dot_timer = QTimer()
        self._wa_dot_timer.timeout.connect(self._animate_wa_dots)
        self._wa_dot_timer.start(700)

        # Стек: 0 = оверлей загрузки, 1 = основной мессенджер
        self._msg_stack = QStackedWidget()
        self._msg_stack.addWidget(self._wa_overlay)
        self._msg_stack.addWidget(main_area)
        # Показываем оверлей если WA ещё не подключён
        if self.wa_server_ready:
            self._msg_stack.setCurrentIndex(1)
        else:
            self._msg_stack.setCurrentIndex(0)
        outer.addWidget(self._msg_stack, 1)

        self._msg_phones_data = []
        self._msg_selected_phone = None

        return container


    def _messenger_refresh_chats(self):
        """Обновить список чатов в мессенджере."""
        phones = get_all_conversations_phones()
        # Подгрузить последнее сообщение для каждого чата
        self._msg_phones_data = []
        for p in phones:
            last_msgs = get_conversation_full(p["phone"])
            last_msg = last_msgs[-1]["message"][:50] if last_msgs else ""
            last_role = last_msgs[-1]["role"] if last_msgs else ""
            self._msg_phones_data.append({
                "phone": p["phone"],
                "msg_count": p["msg_count"],
                "last_at": p["last_at"],
                "last_msg": last_msg,
                "last_role": last_role,
                "unread_count": p.get("unread_count", 0),
            })
        self._messenger_render_chat_list()
        # Обновить текущий открытый чат
        if self._msg_selected_phone:
            self._messenger_load_messages(self._msg_selected_phone)

    def _messenger_render_chat_list(self):
        search = self._msg_search.text().strip()
        self._msg_chat_list.blockSignals(True)
        old_phone = self._msg_selected_phone
        self._msg_chat_list.clear()

        filtered = self._msg_phones_data
        if search:
            filtered = [p for p in filtered if search in p["phone"]]

        for p in filtered:
            ts = (p["last_at"] or "")[:16].replace("T", " ")
            prefix = "AI: " if p["last_role"] == "assistant" else ""
            # Убираем переносы строк, обрезаем превью
            preview = (prefix + p["last_msg"]).replace("\n", " ").replace("\r", "")[:60]
            
            # Добавляем бейдж непрочитанных
            unread = p.get("unread_count", 0)
            if unread > 0:
                phone_text = f'🟢 {p["phone"]} ({unread})'
            else:
                phone_text = p["phone"]
            
            item = QListWidgetItem(f'{phone_text}\n{preview}')
            item.setData(Qt.ItemDataRole.UserRole, p["phone"])
            item.setToolTip(f'{p["msg_count"]} сообщ. | {ts}')
            
            # Выделяем непрочитанные жирным + зелёным фоном
            if unread > 0:
                font = item.font()
                font.setBold(True)
                item.setFont(font)
                item.setBackground(QColor("#e8f5e9"))  # светло-зелёный фон
            
            self._msg_chat_list.addItem(item)

        # Восстановить выбор
        for i in range(self._msg_chat_list.count()):
            if self._msg_chat_list.item(i).data(Qt.ItemDataRole.UserRole) == old_phone:
                self._msg_chat_list.setCurrentRow(i)
                break

        self._msg_chat_list.blockSignals(False)
        self._msg_chat_count.setText(f"{len(filtered)}")

    def _messenger_filter_chats(self):
        self._messenger_render_chat_list()

    def _messenger_on_chat_selected(self, row):
        if row < 0:
            self._msg_selected_phone = None
            self._msg_current_phone.setText("Выберите чат")
            self._msg_display.clear()
            self._msg_count_lbl.setText("")
            return
        item = self._msg_chat_list.item(row)
        if not item:
            return
        phone = item.data(Qt.ItemDataRole.UserRole)
        self._msg_selected_phone = phone
        self._msg_last_count = -1  # сбросить чтобы auto_refresh обновил
        self._msg_current_phone.setText(phone)
        self._messenger_load_messages(phone)
        
        # Помечаем чат как прочитанный
        mark_chat_read(phone)
        # Обновляем список чатов чтобы убрать бейдж
        self._messenger_render_chat_list()

    def _messenger_load_messages(self, phone):
        msgs = get_conversation_full(phone)
        self._msg_count_lbl.setText(f"{len(msgs)} сообщ.")

        if not msgs:
            self._msg_display.setHtml(
                '<body style="margin:0;padding:0;background:#efeae2;">'
                '<p style="color:#8696a0;text-align:center;margin-top:120px;font-size:14px;">'
                'Выберите чат слева</p></body>'
            )
            return

        parts = []
        prev_role = None
        for m in msgs:
            ts = (m.get("created_at") or "")[:16].replace("T", " ")
            role = m["role"]
            text = (m["message"]
                    .replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;")
                    .replace("\n", "<br>"))
            gap = "1" if role == prev_role else "8"
            if role == "user":
                # Входящее — белый бабл, прижат влево
                parts.append(
                    f'<table width="100%" cellspacing="0" cellpadding="0" '
                    f'style="margin-top:{gap}px;"><tr>'
                    f'<td width="75%"><table cellspacing="0" cellpadding="0" '
                    f'align="left" style="background:#ffffff;border-radius:8px;">'
                    f'<tr><td style="padding:6px 12px 4px 12px;">'
                    f'<span style="color:#111b21;font-size:13px;">{text}</span><br>'
                    f'<span style="color:#667781;font-size:9px;">{ts}</span>'
                    f'</td></tr></table></td>'
                    f'<td width="25%"></td></tr></table>'
                )
            else:
                # Исходящее — зелёный бабл, прижат вправо
                parts.append(
                    f'<table width="100%" cellspacing="0" cellpadding="0" '
                    f'style="margin-top:{gap}px;"><tr>'
                    f'<td width="25%"></td>'
                    f'<td width="75%"><table cellspacing="0" cellpadding="0" '
                    f'align="right" style="background:#d9fdd3;border-radius:8px;">'
                    f'<tr><td style="padding:6px 12px 4px 12px;">'
                    f'<span style="color:#111b21;font-size:13px;">{text}</span><br>'
                    f'<span style="color:#667781;font-size:9px;">{ts}</span>'
                    f'</td></tr></table></td></tr></table>'
                )
            prev_role = role

        html = (
            '<body style="margin:0;padding:6px 10px;background:#efeae2;">'
            + "".join(parts)
            + '</body>'
        )
        self._msg_display.setHtml(html)
        # Скролл вниз с задержкой — дать QTextEdit отрендерить HTML
        QTimer.singleShot(50, self._scroll_msg_to_bottom)

    def _scroll_msg_to_bottom(self):
        sb = self._msg_display.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _messenger_send_message(self):
        """Отправить сообщение из мессенджера."""
        phone = self._msg_selected_phone
        text = self._msg_input.text().strip()
        if not phone or not text:
            return
        if not self.wa_server_ready:
            self.log("⚠️ WA-сервер не подключён — отправка невозможна")
            return

        self._msg_input.clear()
        self._msg_send_btn.setEnabled(False)
        conv_phone = _normalize_phone(phone)

        def _bg():
            try:
                result = wa_client.send_message(phone, text)
                if result.get("success"):
                    add_conversation(conv_phone, "assistant", text)
                    self._log_signal.emit(f"📤 Отправлено → {phone}: {text[:50]}...")
                else:
                    err = result.get("error", "?")
                    self._log_signal.emit(f"❌ Ошибка отправки: {err}")
            except Exception as e:
                self._log_signal.emit(f"❌ Ошибка: {e}")
            self._invoke_signal.emit(self._messenger_after_send)

        threading.Thread(target=_bg, daemon=True).start()

    def _messenger_after_send(self):
        self._msg_send_btn.setEnabled(True)
        self._messenger_refresh_chats()

    def _messenger_clear_chat(self):
        phone = self._msg_selected_phone
        if not phone:
            return
        clear_conversation(phone)
        self.log(f"🗑 Очищен диалог с {phone}")
        self._messenger_refresh_chats()
        self._msg_display.clear()
        self._msg_current_phone.setText("Выберите чат")
        self._msg_count_lbl.setText("")

    def _messenger_clear_all_chats(self):
        if not _styled_confirm(self, "Очистить все чаты", "Удалить ВСЮ историю диалогов?"):
            return
        clear_all_conversations()
        self._msg_selected_phone = None
        self.log("🗑 Все диалоги очищены")
        self._messenger_refresh_chats()
        self._msg_display.clear()
        self._msg_current_phone.setText("Выберите чат")
        self._msg_count_lbl.setText("")

    def _messenger_update_ai_status(self, text):
        if hasattr(self, '_msg_ai_status'):
            self._msg_ai_status.setText(text)

    # ═══════════════════════════════════════════════════════════════
    #  Фильтры
    # ═══════════════════════════════════════════════════════════════

    def _range_row(self, val_from, val_to, suffix=""):
        w = QWidget()
        lay = QHBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        f = QLineEdit(val_from)
        f.setPlaceholderText("от")
        f.setFixedWidth(70)
        t = QLineEdit(val_to)
        t.setPlaceholderText("до")
        t.setFixedWidth(70)
        lay.addWidget(f)
        lay.addWidget(QLabel("—"))
        lay.addWidget(t)
        if suffix:
            lay.addWidget(QLabel(suffix))
        lay.addStretch()
        return w, f, t

    def _create_filters_tab(self):
        from PyQt6.QtWidgets import QScrollArea

        k = self.cfg["krisha"]
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("filtersTab")

        tab = QWidget()
        grid = QVBoxLayout(tab)
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setSpacing(10)

        # ── Группа 1: Основное ──────────────────────────────────
        g1 = QGroupBox("Основное")
        f1 = QFormLayout(g1)
        f1.setSpacing(6)
        f1.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.f_deal = QComboBox()
        self.f_deal.addItem("Продажа", "sale")
        self.f_deal.addItem("Аренда", "rent")
        self.f_deal.setCurrentIndex(0 if k.get("deal_type") == "sale" else 1)
        f1.addRow("Сделка:", self.f_deal)

        self.f_region = QComboBox()
        for alias, label in REGIONS.items():
            self.f_region.addItem(label, alias)
        idx = list(REGIONS.keys()).index(k.get("region_alias", "")) if k.get("region_alias", "") in REGIONS else 0
        self.f_region.setCurrentIndex(idx)
        f1.addRow("Регион:", self.f_region)

        rooms_w = QWidget()
        rooms_lay = QHBoxLayout(rooms_w)
        rooms_lay.setContentsMargins(0, 0, 0, 0)
        rooms_lay.setSpacing(6)
        self.f_rooms = {}
        for v, lb in [("1", "1"), ("2", "2"), ("3", "3"), ("4", "4"), ("5.100", "5+")]:
            cb = QCheckBox(lb)
            cb.setChecked(v in k.get("rooms", []))
            self.f_rooms[v] = cb
            rooms_lay.addWidget(cb)
        rooms_lay.addStretch()
        f1.addRow("Комнаты:", rooms_w)

        pw, self.f_price_from, self.f_price_to = self._range_row(
            k.get("price_from", ""), k.get("price_to", ""), "тг"
        )
        f1.addRow("Цена:", pw)

        self.f_pages = QSpinBox()
        self.f_pages.setRange(1, 500)
        self.f_pages.setValue(k.get("max_listings", 60))
        self.f_pages.setFixedWidth(60)
        f1.addRow("Объявлений:", self.f_pages)

        grid.addWidget(g1)

        # ── Группа 2: Параметры дома ────────────────────────────
        g2 = QGroupBox("Параметры дома")
        f2 = QFormLayout(g2)
        f2.setSpacing(6)
        f2.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        build_w = QWidget()
        build_lay = QHBoxLayout(build_w)
        build_lay.setContentsMargins(0, 0, 0, 0)
        build_lay.setSpacing(6)
        self.f_building = {}
        for v, lb in BUILDING_TYPES.items():
            cb = QCheckBox(lb)
            cb.setChecked(v in k.get("building_type", []))
            self.f_building[v] = cb
            build_lay.addWidget(cb)
        build_lay.addStretch()
        f2.addRow("Тип дома:", build_w)

        fw, self.f_floor_from, self.f_floor_to = self._range_row(
            k.get("floor_from", ""), k.get("floor_to", "")
        )
        f2.addRow("Этаж:", fw)

        hw, self.f_hfloor_from, self.f_hfloor_to = self._range_row(
            k.get("house_floors_from", ""), k.get("house_floors_to", "")
        )
        f2.addRow("Этажей в доме:", hw)

        yw, self.f_year_from, self.f_year_to = self._range_row(
            k.get("year_from", ""), k.get("year_to", "")
        )
        f2.addRow("Год постройки:", yw)

        grid.addWidget(g2)

        # ── Группа 3: Площадь ───────────────────────────────────
        g3 = QGroupBox("Площадь")
        f3 = QFormLayout(g3)
        f3.setSpacing(6)
        f3.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        sw, self.f_sq_from, self.f_sq_to = self._range_row(
            k.get("square_from", ""), k.get("square_to", ""), "м²"
        )
        f3.addRow("Общая:", sw)

        kw, self.f_kit_from, self.f_kit_to = self._range_row(
            k.get("kitchen_from", ""), k.get("kitchen_to", ""), "м²"
        )
        f3.addRow("Кухня:", kw)

        toilet_w = QWidget()
        toilet_lay = QHBoxLayout(toilet_w)
        toilet_lay.setContentsMargins(0, 0, 0, 0)
        toilet_lay.setSpacing(6)
        self.f_toilet = {}
        for v, lb in TOILET_TYPES.items():
            cb = QCheckBox(lb)
            cb.setChecked(v in k.get("toilet", []))
            self.f_toilet[v] = cb
            toilet_lay.addWidget(cb)
        toilet_lay.addStretch()
        f3.addRow("Санузел:", toilet_w)

        grid.addWidget(g3)

        # ── Группа 4: Дополнительно ─────────────────────────────
        g4 = QGroupBox("Дополнительно")
        f4 = QFormLayout(g4)
        f4.setSpacing(6)
        f4.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        flags1 = QWidget()
        fl1 = QHBoxLayout(flags1)
        fl1.setContentsMargins(0, 0, 0, 0)
        fl1.setSpacing(8)
        self.f_photo = QCheckBox("Фото")
        self.f_photo.setChecked(k.get("has_photo", False))
        self.f_novo = QCheckBox("Новостройки")
        self.f_novo.setChecked(k.get("novostroiki", False))
        self.f_exchange = QCheckBox("Обмен")
        self.f_exchange.setChecked(k.get("has_change", False))
        fl1.addWidget(self.f_photo)
        fl1.addWidget(self.f_novo)
        fl1.addWidget(self.f_exchange)
        fl1.addStretch()
        f4.addRow("Опции:", flags1)

        flags2 = QWidget()
        fl2 = QHBoxLayout(flags2)
        fl2.setContentsMargins(0, 0, 0, 0)
        fl2.setSpacing(8)
        self.f_owner = QCheckBox("Хозяева")
        self.f_owner.setChecked(k.get("from_owner", False))
        self.f_agent = QCheckBox("Агенты")
        self.f_agent.setChecked(k.get("from_agent", False))
        fl2.addWidget(self.f_owner)
        fl2.addWidget(self.f_agent)
        fl2.addStretch()
        f4.addRow("Продавец:", flags2)

        flags3 = QWidget()
        fl3 = QHBoxLayout(flags3)
        fl3.setContentsMargins(0, 0, 0, 0)
        fl3.setSpacing(8)
        self.f_not_first = QCheckBox("Не первый")
        self.f_not_first.setChecked(k.get("not_first_floor", False))
        self.f_not_last = QCheckBox("Не последний")
        self.f_not_last.setChecked(k.get("not_last_floor", False))
        fl3.addWidget(self.f_not_first)
        fl3.addWidget(self.f_not_last)
        fl3.addStretch()
        f4.addRow("Этаж:", flags3)

        self.f_skip_developers = QCheckBox("Пропускать застройщиков")
        self.f_skip_developers.setChecked(k.get("skip_developers", False))
        self.f_skip_developers.setToolTip("Пропускать объявления от застройщиков и компаний")
        f4.addRow("", self.f_skip_developers)

        self.f_mortgage = QComboBox()
        for v, lb in MORTGAGE_OPTIONS.items():
            self.f_mortgage.addItem(lb, v)
        f4.addRow("Ипотека:", self.f_mortgage)

        self.f_dorm = QComboBox()
        for v, lb in PRIV_DORM_OPTIONS.items():
            self.f_dorm.addItem(lb, v)
        f4.addRow("Общежитие:", self.f_dorm)

        self.f_text = QLineEdit(k.get("text_search", ""))
        self.f_text.setPlaceholderText("Ключевые слова...")
        f4.addRow("Поиск:", self.f_text)

        self.f_phone_line = {}

        grid.addWidget(g4)

        # ── Кнопки ──────────────────────────────────────────────
        btn_row = QWidget()
        btn_lay = QHBoxLayout(btn_row)
        btn_lay.setContentsMargins(0, 0, 0, 0)
        btn_lay.setSpacing(10)
        btn_lay.addStretch()

        btn_reset = QPushButton("Сбросить историю")
        btn_reset.setObjectName("btnRed")
        btn_reset.setFixedHeight(30)
        btn_reset.setFixedWidth(180)
        btn_reset.setToolTip("Очистить список спарсенных объявлений — парсер пройдётся заново")
        btn_reset.clicked.connect(self._reset_parsed_urls)
        btn_lay.addWidget(btn_reset)

        btn_save = QPushButton("Сохранить фильтры")
        btn_save.setObjectName("btnGreen")
        btn_save.setFixedHeight(30)
        btn_save.setFixedWidth(180)
        btn_save.clicked.connect(self._save_filters)
        btn_lay.addWidget(btn_save)

        btn_open = QPushButton("Открыть на Крыше")
        btn_open.setFixedHeight(30)
        btn_open.setFixedWidth(180)
        btn_open.clicked.connect(self._open_filters_url)
        btn_lay.addWidget(btn_open)

        btn_lay.addStretch()
        grid.addWidget(btn_row)

        scroll.setWidget(tab)
        return scroll

    def _save_filters(self):
        k = self.cfg["krisha"]
        k["deal_type"] = self.f_deal.currentData()
        k["region_alias"] = self.f_region.currentData()
        k["region"] = self.f_region.currentText()
        k["rooms"] = [v for v, cb in self.f_rooms.items() if cb.isChecked()]
        k["price_from"] = self.f_price_from.text().strip()
        k["price_to"] = self.f_price_to.text().strip()
        k["max_listings"] = self.f_pages.value()
        k["has_photo"] = self.f_photo.isChecked()
        k["novostroiki"] = self.f_novo.isChecked()
        k["from_owner"] = self.f_owner.isChecked()
        k["from_agent"] = self.f_agent.isChecked()
        k["not_last_floor"] = self.f_not_last.isChecked()
        k["not_first_floor"] = self.f_not_first.isChecked()
        k["has_change"] = self.f_exchange.isChecked()
        k["building_type"] = [v for v, cb in self.f_building.items() if cb.isChecked()]
        k["floor_from"] = self.f_floor_from.text().strip()
        k["floor_to"] = self.f_floor_to.text().strip()
        k["house_floors_from"] = self.f_hfloor_from.text().strip()
        k["house_floors_to"] = self.f_hfloor_to.text().strip()
        k["year_from"] = self.f_year_from.text().strip()
        k["year_to"] = self.f_year_to.text().strip()
        k["square_from"] = self.f_sq_from.text().strip()
        k["square_to"] = self.f_sq_to.text().strip()
        k["kitchen_from"] = self.f_kit_from.text().strip()
        k["kitchen_to"] = self.f_kit_to.text().strip()
        k["mortgage"] = self.f_mortgage.currentData()
        k["priv_dorm"] = self.f_dorm.currentData()
        k["toilet"] = [v for v, cb in self.f_toilet.items() if cb.isChecked()]
        k["text_search"] = self.f_text.text().strip()
        k["skip_developers"] = self.f_skip_developers.isChecked()
        save_config(self.cfg)
        self.log("✅ Фильтры сохранены")

    def _open_filters_url(self):
        self._save_filters()
        from parser_playwright import build_search_url
        url = build_search_url(self.cfg)
        import webbrowser
        webbrowser.open(url)
        self.log(f"  {url}")

    def _reset_parsed_urls(self):
        if not _styled_confirm(self, "Сбросить историю парсинга",
                "Очистить список спарсенных объявлений?\n\n"
                "Парсер пройдётся заново по всем страницам с текущими фильтрами."):
            return
        clear_parsed_urls()
        self.log("🗑 История парсинга очищена — парсер пройдётся заново")


    # ═══════════════════════════════════════════════════════════════
    #  Настройки
    # ═══════════════════════════════════════════════════════════════

    def _create_settings_tab(self):
        from PyQt6.QtWidgets import QScrollArea, QDoubleSpinBox

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("settingsTab")

        tab = QWidget()
        root = QVBoxLayout(tab)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(10)

        # ── WhatsApp ──
        g1 = QGroupBox("WhatsApp Рассылка")
        f1 = QFormLayout(g1)
        f1.setSpacing(6)
        f1.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.s_first_msg = QTextEdit()
        self.s_first_msg.setObjectName("logText")
        self.s_first_msg.setPlainText(self.cfg["whatsapp"].get("first_message", ""))
        self.s_first_msg.setMaximumHeight(80)
        f1.addRow("Сообщение:", self.s_first_msg)

        self.s_delay = QSpinBox()
        self.s_delay.setRange(5, 300)
        self.s_delay.setValue(self.cfg["whatsapp"].get("message_delay_seconds", 30))
        self.s_delay.setSuffix(" сек")
        f1.addRow("Задержка:", self.s_delay)

        self.s_daily_limit = QSpinBox()
        self.s_daily_limit.setRange(1, 256)
        self.s_daily_limit.setValue(self.cfg["whatsapp"].get("daily_limit", 50))
        self.s_daily_limit.setToolTip("Максимум сообщений в сутки (1-256). Больше 256 — риск бана.")
        f1.addRow("Лимит/сутки:", self.s_daily_limit)

        root.addWidget(g1)

        # ── 2Captcha ──
        g_captcha = QGroupBox("2Captcha (решение CAPTCHA)")
        f_captcha = QFormLayout(g_captcha)
        f_captcha.setSpacing(6)
        f_captcha.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        captcha_row = QWidget()
        cr = QHBoxLayout(captcha_row)
        cr.setContentsMargins(0, 0, 0, 0)
        self.s_captcha_key = QLineEdit(
            self.cfg.get("captcha", {}).get("anticaptcha_api_key", "")
        )
        self.s_captcha_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.s_captcha_key.setPlaceholderText("API ключ anti-captcha.com")
        self.s_show_captcha_key = QPushButton("*")
        self.s_show_captcha_key.setFixedWidth(32)
        self.s_show_captcha_key.setCheckable(True)
        self.s_show_captcha_key.toggled.connect(
            lambda on: self.s_captcha_key.setEchoMode(
                QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password
            )
        )
        cr.addWidget(self.s_captcha_key, 1)
        cr.addWidget(self.s_show_captcha_key)
        f_captcha.addRow("API ключ:", captcha_row)

        captcha_hint = QLabel("Получить ключ: anti-captcha.com. Нужен для автоматического решения CAPTCHA при парсинге.")
        captcha_hint.setStyleSheet("color: #78909c; font-size: 10px;")
        captcha_hint.setWordWrap(True)
        f_captcha.addRow("", captcha_hint)

        root.addWidget(g_captcha)

        # ── DeepSeek API ──
        g2 = QGroupBox("DeepSeek API")
        f2 = QFormLayout(g2)
        f2.setSpacing(6)
        f2.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        key_row = QWidget()
        kr = QHBoxLayout(key_row)
        kr.setContentsMargins(0, 0, 0, 0)
        self.s_api_key = QLineEdit(self.cfg["deepseek"].get("api_key", ""))
        self.s_api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.s_api_key.setPlaceholderText("sk-...")
        self.s_show_key = QPushButton("*")
        self.s_show_key.setFixedWidth(32)
        self.s_show_key.setCheckable(True)
        self.s_show_key.toggled.connect(
            lambda on: self.s_api_key.setEchoMode(
                QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password
            )
        )
        kr.addWidget(self.s_api_key, 1)
        kr.addWidget(self.s_show_key)
        f2.addRow("API ключ:", key_row)

        self.s_model = QComboBox()
        self.s_model.setEditable(True)
        self.s_model.addItems(["deepseek-chat", "deepseek-reasoner"])
        cur = self.cfg["deepseek"].get("model", "deepseek-chat")
        idx = self.s_model.findText(cur)
        if idx >= 0:
            self.s_model.setCurrentIndex(idx)
        else:
            self.s_model.setCurrentText(cur)
        f2.addRow("Модель:", self.s_model)

        self.s_temperature = QDoubleSpinBox()
        self.s_temperature.setRange(0.0, 2.0)
        self.s_temperature.setSingleStep(0.1)
        self.s_temperature.setDecimals(1)
        self.s_temperature.setValue(self.cfg["deepseek"].get("temperature", 0.7))
        f2.addRow("Temperature:", self.s_temperature)

        self.s_max_tokens = QSpinBox()
        self.s_max_tokens.setRange(50, 2000)
        self.s_max_tokens.setSingleStep(50)
        self.s_max_tokens.setValue(self.cfg["deepseek"].get("max_tokens", 300))
        f2.addRow("Max tokens:", self.s_max_tokens)

        root.addWidget(g2)

        # ── AI Системный промпт ──
        g3 = QGroupBox("AI Риелтор — Системный промпт")
        g3_lay = QVBoxLayout(g3)
        g3_lay.setSpacing(4)

        prompt_hint = QLabel(
            "Инструкция для AI бота. Определяет его поведение, стиль, имя и правила общения."
        )
        prompt_hint.setStyleSheet("color: #78909c; font-size: 10px;")
        prompt_hint.setWordWrap(True)
        g3_lay.addWidget(prompt_hint)

        self.s_system_prompt = QTextEdit()
        self.s_system_prompt.setObjectName("logText")
        default_prompt = (
            "Ты — опытный риелтор с 10-летним стажем работы на рынке недвижимости Казахстана.\n"
            "Тебя зовут Асхат. Ты работаешь в агентстве недвижимости.\n\n"
            "Твоя задача — вести диалог с потенциальными клиентами, которые разместили объявления на Крыше.\n"
            "Ты пишешь первым, предлагая свои услуги. Твоя цель — договориться о встрече или звонке.\n\n"
            "Правила общения:\n"
            "- Пиши коротко, по делу, как в WhatsApp (не длинные простыни текста)\n"
            "- Будь вежливым, но не навязчивым\n"
            "- Используй разговорный стиль, без канцеляризмов\n"
            "- Если человек отказывается — вежливо попрощайся, не дави\n"
            "- Если человек интересуется — расскажи о преимуществах работы с риелтором\n"
            "- Не выдумывай конкретные цифры и адреса\n"
            "- Отвечай ТОЛЬКО на русском языке\n"
            "- Максимум 2-3 предложения в сообщении"
        )
        saved_prompt = self.cfg["deepseek"].get("system_prompt", "").strip()
        self.s_system_prompt.setPlainText(saved_prompt or default_prompt)
        self.s_system_prompt.setMinimumHeight(200)
        self.s_system_prompt.setStyleSheet(
            "QTextEdit { background: #11111b; color: #cdd6f4; border: 1px solid #45475a; "
            "border-radius: 4px; font-family: Consolas; font-size: 11px; padding: 6px; }"
        )
        g3_lay.addWidget(self.s_system_prompt)

        root.addWidget(g3)

        # ── Кнопка сохранить ──
        btn_save = QPushButton("Сохранить настройки")
        btn_save.setObjectName("btnGreen")
        btn_save.setFixedHeight(30)
        btn_save.clicked.connect(self._save_settings)
        root.addWidget(btn_save)

        root.addStretch()
        scroll.setWidget(tab)
        return scroll

    def _save_settings(self):
        self.cfg["whatsapp"]["first_message"] = self.s_first_msg.toPlainText().strip()
        self.cfg["whatsapp"]["message_delay_seconds"] = self.s_delay.value()
        self.cfg["whatsapp"]["daily_limit"] = self.s_daily_limit.value()
        if "captcha" not in self.cfg:
            self.cfg["captcha"] = {}
        self.cfg["captcha"]["anticaptcha_api_key"] = self.s_captcha_key.text().strip()
        self.cfg["deepseek"]["api_key"] = self.s_api_key.text().strip()
        self.cfg["deepseek"]["model"] = self.s_model.currentText()
        self.cfg["deepseek"]["temperature"] = self.s_temperature.value()
        self.cfg["deepseek"]["max_tokens"] = self.s_max_tokens.value()
        self.cfg["deepseek"]["system_prompt"] = self.s_system_prompt.toPlainText().strip()
        save_config(self.cfg)
        self.log("  Настройки сохранены")

    # ═══════════════════════════════════════════════════════════════
    #  Перетаскивание окна (кастомный title bar)
    # ═══════════════════════════════════════════════════════════════

    def _title_mouse_press(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def _title_mouse_move(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            if self._is_maximized:
                self.showNormal()
                self._is_maximized = False
                # Корректируем позицию чтобы мышь осталась на title bar
                self._drag_pos.setX(int(self.width() / 2))
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def _title_mouse_release(self, event):
        self._drag_pos = None
        # Перерисовываем Chrome после перетаскивания окна
        self._last_chrome_size = None
        QTimer.singleShot(50, self._resize_chrome)

    # ═══════════════════════════════════════════════════════════════
    #  Стили
    # ═══════════════════════════════════════════════════════════════

    def _apply_styles(self):
        self.setStyleSheet("""
            QMainWindow { background: #1e1e2e; color: #cdd6f4; }
            #toolbar { background: #181825; border-bottom: 1px solid #313244; }
            #sideTabs, #sideTabs QWidget { background: #1e1e2e; color: #cdd6f4; }

            QPushButton {
                background: #313244; color: #cdd6f4; border: 1px solid #45475a;
                border-radius: 4px; padding: 3px 10px; font-size: 11px;
            }
            QPushButton:hover { background: #45475a; }
            QPushButton:checked { background: #546e7a; color: #ffffff; border-color: #546e7a; }
            QPushButton:disabled { background: #1e1e2e; color: #585b70; border-color: #313244; }
            QPushButton#btnGreen { background: #546e7a; color: #ffffff; border-color: #546e7a; }
            QPushButton#btnGreen:hover { background: #607d8b; }

            QTabWidget::pane { border: 1px solid #313244; background: #1e1e2e; }
            QTabBar::tab {
                background: #181825; color: #a6adc8; padding: 6px 12px;
                border: 1px solid #313244; border-bottom: none; border-radius: 4px 4px 0 0;
                min-width: 70px; font-size: 11px;
            }
            QTabBar::tab:selected { background: #1e1e2e; color: #cdd6f4; }

            QTextEdit#logText, QListWidget#sideList {
                background: #11111b; color: #90a4ae; border: 1px solid #313244;
                border-radius: 4px; font-family: Consolas; font-size: 11px;
            }

            QLineEdit, QSpinBox, QComboBox {
                background: #313244; color: #cdd6f4; border: 1px solid #45475a;
                border-radius: 4px; padding: 3px 6px;
            }
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus { border-color: #607d8b; }

            QGroupBox {
                color: #78909c; border: 1px solid #313244; border-radius: 6px;
                margin-top: 8px; padding-top: 14px; font-weight: bold;
            }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 4px; }

            QCheckBox { color: #cdd6f4; spacing: 4px; }
            QCheckBox::indicator { width: 14px; height: 14px; border-radius: 3px; border: 1px solid #45475a; background: #313244; }
            QCheckBox::indicator:checked { background: #607d8b; border-color: #607d8b; }

            QLabel { color: #bac2de; font-size: 11px; }

            QProgressBar {
                background: #313244; border: 1px solid #45475a; border-radius: 4px;
                text-align: center; color: #cdd6f4; height: 18px;
            }
            QProgressBar::chunk { background: #546e7a; border-radius: 3px; }

            QStatusBar { background: #181825; color: #a6adc8; border-top: 1px solid #313244; }

            QSplitter::handle { background: #313244; height: 3px; }

            QFrame[frameShape="5"] { color: #313244; }
        """)

    # ═══════════════════════════════════════════════════════════════
    #  Ресайз / Закрытие
    # ═══════════════════════════════════════════════════════════════

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_chrome()
        # Подгоняем оверлей загрузки под размер chrome_host
        if hasattr(self, '_loading_overlay') and self._loading_overlay.isVisible():
            self._loading_overlay.setGeometry(self._chrome_host.rect())

    def closeEvent(self, event):
        self._save_filters()
        save_config(self.cfg)
        self._parse_stop = True
        self.sync_timer.stop()
        self._msg_refresh_timer.stop()
        self.auth_timer.stop()
        self.wa_check_timer.stop()
        self.popup_timer.stop()
        self._wa_dot_timer.stop()
        if hasattr(self, '_loading_dot_timer'):
            self._loading_dot_timer.stop()
        if hasattr(self, '_krisha_auth_check_timer'):
            self._krisha_auth_check_timer.stop()
        if hasattr(self, '_chrome_resize_timer'):
            self._chrome_resize_timer.stop()

        # Отцепляем Chrome перед закрытием
        if self._chrome_hwnd:
            try:
                import ctypes
                import ctypes.wintypes
                user32 = ctypes.windll.user32
                user32.SetParent.argtypes = [ctypes.wintypes.HWND, ctypes.wintypes.HWND]
                user32.SetParent(self._chrome_hwnd, None)
            except Exception:
                pass

        # Закрываем Playwright драйвер
        try:
            close_driver()
        except Exception:
            pass

        # Убиваем wa-server мгновенно
        proc = self._wa_process
        if proc and proc.poll() is None:
            try:
                proc.kill()
            except Exception:
                pass

        # Закрываем лог-файл
        if hasattr(self, '_wa_log_file') and self._wa_log_file:
            try:
                self._wa_log_file.close()
            except Exception:
                pass

        # Шлём shutdown в фоне (fire-and-forget)
        def _bg():
            try:
                import requests as req
                req.post("http://localhost:3457/shutdown", timeout=0.5)
            except Exception:
                pass
        threading.Thread(target=_bg, daemon=True).start()

        event.accept()



def run_gui():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    win = MainWindow()
    win.showMaximized()
    sys.exit(app.exec())


if __name__ == "__main__":
    run_gui()
