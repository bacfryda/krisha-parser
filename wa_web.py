"""
Управление WhatsApp Web через JS injection в QWebEngineView.
Никакого бэкенда — всё прямо в встроенном браузере.
Печатает как человек, с задержкой между символами.
"""
import time
from PyQt6.QtCore import QEventLoop, QTimer, QUrl


def _run_js(page, script: str, timeout_ms: int = 15000):
    """Выполняет JS на странице и возвращает результат синхронно."""
    result = [None]
    done = [False]

    def callback(val):
        result[0] = val
        done[0] = True

    page.runJavaScript(script, callback)

    loop = QEventLoop()
    elapsed = 0
    step = 50
    while not done[0] and elapsed < timeout_ms:
        QTimer.singleShot(step, loop.quit)
        loop.exec()
        elapsed += step

    return result[0]


def _sleep_ms(ms: int):
    """Неблокирующая пауза."""
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def is_wa_ready(browser) -> bool:
    """Проверяет что WhatsApp Web загружен и авторизован."""
    result = _run_js(browser.page(), """
    (function() {
        // Если есть список чатов — авторизован
        var side = document.getElementById('side');
        if (side) return 'ready';
        // Если есть QR код — не авторизован
        var canvas = document.querySelector('canvas');
        if (canvas) return 'qr';
        return 'loading';
    })();
    """, timeout_ms=5000)
    return result == 'ready'



def open_chat_with_number(browser, phone: str, log_fn=None) -> bool:
    """
    Открывает чат с номером через URL wa.me.
    Возвращает True если чат открылся.
    """
    # Убираем + из номера
    clean_phone = phone.replace("+", "").replace(" ", "").replace("-", "")

    if log_fn:
        log_fn(f"  📱 WA: открываю чат с {clean_phone}...")

    # Используем wa.me URL — WhatsApp Web сам откроет чат
    url = f"https://web.whatsapp.com/send?phone={clean_phone}"
    browser.setUrl(QUrl(url))

    # Ждём загрузки чата (ищем поле ввода)
    for attempt in range(30):  # макс 15 сек
        _sleep_ms(500)
        result = _run_js(browser.page(), """
        (function() {
            // Проверяем что чат открылся — есть поле ввода сообщения
            var input = document.querySelector('div[contenteditable="true"][data-tab="10"]');
            if (input) return 'chat_ready';

            // Проверяем ошибку "номер не в WhatsApp"
            var body = document.body.innerText || '';
            if (body.indexOf('не зарегистрирован') !== -1 ||
                body.indexOf('not on WhatsApp') !== -1 ||
                body.indexOf('Phone number shared via url is invalid') !== -1) {
                return 'not_found';
            }

            // Кнопка "Продолжить в чат" (если номер не в контактах)
            var btns = document.querySelectorAll('a[href*="send"], button');
            for (var i = 0; i < btns.length; i++) {
                var txt = btns[i].textContent.toLowerCase();
                if (txt.indexOf('продолжить') !== -1 || txt.indexOf('continue') !== -1) {
                    btns[i].click();
                    return 'clicking_continue';
                }
            }

            return 'loading';
        })();
        """, timeout_ms=3000)

        if result == 'chat_ready':
            if log_fn:
                log_fn(f"  ✅ WA: чат открыт")
            return True
        elif result == 'not_found':
            if log_fn:
                log_fn(f"  ⚠️ WA: номер {clean_phone} не в WhatsApp")
            return False

    if log_fn:
        log_fn(f"  ❌ WA: не удалось открыть чат (таймаут)")
    return False


def type_and_send_message(browser, message: str, log_fn=None) -> bool:
    """
    Печатает сообщение в поле ввода как человек и отправляет.
    """
    if log_fn:
        log_fn(f"  ⌨️ WA: печатаю сообщение...")

    # Фокусируемся на поле ввода
    focused = _run_js(browser.page(), """
    (function() {
        var input = document.querySelector('div[contenteditable="true"][data-tab="10"]');
        if (!input) return 'no_input';
        input.focus();
        input.click();
        return 'focused';
    })();
    """, timeout_ms=3000)

    if focused != 'focused':
        if log_fn:
            log_fn("  ❌ WA: поле ввода не найдено")
        return False

    _sleep_ms(300)

    # Печатаем текст через clipboard (надёжнее чем посимвольно для кириллицы)
    # Вставляем текст через execCommand
    escaped_msg = message.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$").replace("'", "\\'").replace("\n", "\\n")

    typed = _run_js(browser.page(), f"""
    (function() {{
        var input = document.querySelector('div[contenteditable="true"][data-tab="10"]');
        if (!input) return 'no_input';
        input.focus();

        // Вставляем текст через InputEvent (как будто пользователь печатает)
        var text = '{escaped_msg}';
        document.execCommand('insertText', false, text);

        // Проверяем что текст появился
        if (input.textContent.length > 0) return 'typed';
        return 'empty';
    }})();
    """, timeout_ms=5000)

    if typed != 'typed':
        if log_fn:
            log_fn("  ❌ WA: не удалось ввести текст")
        return False

    _sleep_ms(500)

    # Нажимаем Enter для отправки
    sent = _run_js(browser.page(), """
    (function() {
        var input = document.querySelector('div[contenteditable="true"][data-tab="10"]');
        if (!input) return 'no_input';

        // Отправляем Enter
        var enterEvent = new KeyboardEvent('keydown', {
            key: 'Enter',
            code: 'Enter',
            keyCode: 13,
            which: 13,
            bubbles: true
        });
        input.dispatchEvent(enterEvent);
        return 'sent';
    })();
    """, timeout_ms=3000)

    if sent == 'sent':
        _sleep_ms(1000)  # Ждём отправки
        if log_fn:
            log_fn(f"  ✅ WA: сообщение отправлено")
        return True

    if log_fn:
        log_fn("  ❌ WA: не удалось отправить")
    return False



def send_message_to_phone(browser, phone: str, message: str, log_fn=None) -> bool:
    """
    Полный цикл: открыть чат → напечатать → отправить.
    """
    if not open_chat_with_number(browser, phone, log_fn):
        return False

    _sleep_ms(500)

    return type_and_send_message(browser, message, log_fn)


def get_unread_messages(browser, log_fn=None) -> list[dict]:
    """
    Собирает непрочитанные сообщения из списка чатов.
    Возвращает список {name, unread_count}.
    """
    # Сначала убедимся что мы на главном экране (список чатов)
    go_to_chat_list(browser)
    _sleep_ms(500)

    result = _run_js(browser.page(), """
    (function() {
        var unread = [];
        var side = document.getElementById('pane-side');
        if (!side) return unread;

        // Все строки чатов
        var rows = side.querySelectorAll('[role="listitem"]');
        if (!rows.length) {
            rows = side.querySelectorAll('[data-testid="cell-frame-container"]');
        }
        if (!rows.length) {
            // Фоллбэк — ищем все div-ы с aria-label содержащим "непрочитан"
            rows = side.querySelectorAll('div[class]');
        }

        rows.forEach(function(row) {
            // Ищем бейдж непрочитанных — это span с числом внутри маленького круглого элемента
            var found = false;
            var count = 0;

            // Способ 1: data-testid
            var badge = row.querySelector('[data-testid="icon-unread-count"]');
            if (badge) {
                count = parseInt(badge.textContent) || 1;
                found = true;
            }

            // Способ 2: aria-label с "непрочитан"
            if (!found) {
                var ariaEls = row.querySelectorAll('[aria-label]');
                for (var a = 0; a < ariaEls.length; a++) {
                    var label = ariaEls[a].getAttribute('aria-label') || '';
                    if (label.indexOf('непрочитан') !== -1 || label.indexOf('unread') !== -1) {
                        var m = label.match(/(\\d+)/);
                        count = m ? parseInt(m[1]) : 1;
                        found = true;
                        break;
                    }
                }
            }

            // Способ 3: маленький зелёный кружок с числом
            if (!found) {
                var spans = row.querySelectorAll('span');
                for (var s = 0; s < spans.length; s++) {
                    var txt = spans[s].textContent.trim();
                    if (/^\\d{1,3}$/.test(txt)) {
                        var rect = spans[s].getBoundingClientRect();
                        // Бейдж обычно маленький (< 30px)
                        if (rect.width > 0 && rect.width < 35 && rect.height > 0 && rect.height < 35) {
                            var cs = window.getComputedStyle(spans[s]);
                            var parentCs = window.getComputedStyle(spans[s].parentElement);
                            // Проверяем что это круглый элемент (бейдж)
                            if (parentCs.borderRadius && parseFloat(parentCs.borderRadius) > 5) {
                                count = parseInt(txt);
                                found = true;
                                break;
                            }
                        }
                    }
                }
            }

            if (found && count > 0) {
                // Ищем имя контакта
                var nameEl = row.querySelector('span[title]');
                var name = '';
                if (nameEl) {
                    name = nameEl.getAttribute('title') || nameEl.textContent.trim();
                }
                if (!name) {
                    var dirEl = row.querySelector('span[dir="auto"]');
                    if (dirEl) name = dirEl.textContent.trim();
                }
                if (name && name.length > 0 && name.length < 100) {
                    unread.push({name: name, unread_count: count});
                }
            }
        });

        return unread;
    })();
    """, timeout_ms=8000)

    if log_fn and result and len(result) > 0:
        log_fn(f"  👀 Найдено {len(result)} чатов с непрочитанными")

    return result if isinstance(result, list) else []


def open_chat_by_name(browser, name: str, log_fn=None) -> bool:
    """Открывает чат по имени контакта (кликает на него в списке)."""
    safe_name = name.replace("'", "\\'")
    result = _run_js(browser.page(), """
    (function() {
        var target = '""" + safe_name + """';
        var rows = document.querySelectorAll('#pane-side [role="listitem"], #pane-side [data-testid="cell-frame-container"]');
        for (var i = 0; i < rows.length; i++) {
            var nameEl = rows[i].querySelector('span[title]');
            if (nameEl && nameEl.getAttribute('title') === target) {
                rows[i].click();
                return 'opened';
            }
        }
        return 'not_found';
    })();
    """, timeout_ms=5000)

    if result == 'opened':
        _sleep_ms(1000)
        return True
    return False


def get_last_incoming_message(browser, log_fn=None) -> str | None:
    """Получает последнее входящее сообщение из открытого чата."""
    result = _run_js(browser.page(), """
    (function() {
        // Ищем все сообщения — входящие имеют class message-in
        var incoming = document.querySelectorAll('.message-in');
        if (!incoming.length) {
            // Фоллбэк — ищем по data-testid
            incoming = document.querySelectorAll('[data-testid="msg-container"]');
        }

        if (!incoming.length) return null;

        // Берём последнее входящее
        var last = incoming[incoming.length - 1];

        // Ищем текст сообщения
        var textEl = last.querySelector('.selectable-text span');
        if (!textEl) textEl = last.querySelector('[data-testid="balloon-text-content"]');
        if (!textEl) textEl = last.querySelector('span.selectable-text');
        if (!textEl) {
            // Фоллбэк — любой span с текстом внутри сообщения
            var spans = last.querySelectorAll('span');
            for (var i = 0; i < spans.length; i++) {
                var t = spans[i].textContent.trim();
                if (t.length > 2 && t.length < 5000 && !t.match(/^\\d{1,2}:\\d{2}$/)) {
                    textEl = spans[i];
                    break;
                }
            }
        }

        return textEl ? textEl.textContent.trim() : null;
    })();
    """, timeout_ms=5000)

    return result


def go_to_chat_list(browser):
    """Возвращается к списку чатов (нажимает Escape или кнопку назад)."""
    _run_js(browser.page(), """
    (function() {
        // Нажимаем Escape чтобы вернуться к списку
        document.dispatchEvent(new KeyboardEvent('keydown', {key: 'Escape', bubbles: true}));
    })();
    """)
    _sleep_ms(500)
