"""
Парсер krisha.kz через QWebEngineView (встроенный браузер GUI).
Парсинг идёт прямо в левом окне приложения — пользователь видит всё в реальном времени.
Никакого Selenium, никакого отдельного окна.
"""
import re
import time
from PyQt6.QtCore import QUrl, QEventLoop, QTimer
from parser import build_search_url, normalize_phone


def _run_js(page, script: str, timeout_ms: int = 10000):
    """Выполняет JS на странице и возвращает результат синхронно."""
    result = [None]
    done = [False]

    def callback(val):
        result[0] = val
        done[0] = True

    page.runJavaScript(script, callback)

    # Ждём результат с таймаутом
    loop = QEventLoop()
    elapsed = 0
    step = 50
    while not done[0] and elapsed < timeout_ms:
        QTimer.singleShot(step, loop.quit)
        loop.exec()
        elapsed += step

    return result[0]


def _load_url(browser, url: str, wait_sec: float = 3.0):
    """Загружает URL в браузер и ждёт загрузки."""
    done = [False]

    def on_load(ok):
        done[0] = True

    browser.loadFinished.connect(on_load)
    browser.setUrl(QUrl.fromUserInput(url))

    loop = QEventLoop()
    elapsed = 0
    step = 100
    max_wait = int(wait_sec * 1000) + 15000  # wait_sec + 15 сек на загрузку
    while not done[0] and elapsed < max_wait:
        QTimer.singleShot(step, loop.quit)
        loop.exec()
        elapsed += step

    try:
        browser.loadFinished.disconnect(on_load)
    except Exception:
        pass

    # Доп. пауза для AJAX
    _sleep_ms(int(wait_sec * 1000))


def _sleep_ms(ms: int):
    """Неблокирующая пауза (не замораживает GUI)."""
    loop = QEventLoop()
    QTimer.singleShot(ms, loop.quit)
    loop.exec()


def collect_listings(browser, cfg: dict, log_fn=None) -> list[dict]:
    """Собирает объявления со страниц поиска прямо в встроенном браузере."""
    max_pages = cfg["krisha"].get("max_pages", 3)
    listings = []

    # Строим URL первой страницы с фильтрами
    first_url = build_search_url(cfg, 1)

    if log_fn:
        # Показываем кол-во параметров фильтра
        param_count = first_url.count("das[") if "?" in first_url else 0
        log_fn(f"🔗 Загрузка с {param_count} фильтрами...")

    # Загружаем URL с фильтрами напрямую
    _load_url(browser, first_url, wait_sec=3)

    # Проверяем что URL содержит наши параметры (не был редиректнут)
    actual_url = _run_js(browser.page(), "window.location.href", timeout_ms=3000) or ""
    if "das[" not in actual_url and "das%5B" not in actual_url and "?" in first_url:
        if log_fn:
            log_fn("⚠️ Фильтры могли не примениться, пробую ещё раз...")
        # Повторная попытка — иногда первая загрузка редиректит
        _sleep_ms(1000)
        _load_url(browser, first_url, wait_sec=3)

    # Закрываем попапы
    _run_js(browser.page(), """
        document.querySelectorAll('[class*="close"], [data-dismiss="modal"]').forEach(el => {
            try { if(el.offsetHeight > 0) el.click(); } catch(e) {}
        });
        document.body.style.overflow = '';
    """)

    # Логируем финальный URL для диагностики
    final_url = _run_js(browser.page(), "window.location.href", timeout_ms=3000) or ""
    if log_fn:
        # Показываем только параметры
        if "?" in final_url:
            params_part = final_url.split("?", 1)[1]
            param_count = params_part.count("das")
            log_fn(f"🔗 Фильтров в URL: {param_count}")
        else:
            log_fn("🔗 URL без фильтров")

    # Собираем карточки с первой страницы
    cards_data = _collect_cards(browser)
    if cards_data:
        listings.extend(cards_data)
        if log_fn:
            log_fn(f"📄 Страница 1/{max_pages}: {len(cards_data)} карточек")
    else:
        if log_fn:
            log_fn("📄 Страница 1: объявления не найдены")
        return listings

    # Остальные страницы
    for page_num in range(2, max_pages + 1):
        _sleep_ms(2000)
        url = build_search_url(cfg, page_num)
        if log_fn:
            log_fn(f"📄 Страница {page_num}/{max_pages}: загрузка...")

        _load_url(browser, url, wait_sec=3)

        _run_js(browser.page(), """
            document.querySelectorAll('[class*="close"], [data-dismiss="modal"]').forEach(el => {
                try { if(el.offsetHeight > 0) el.click(); } catch(e) {}
            });
            document.body.style.overflow = '';
        """)

        cards_data = _collect_cards(browser)
        if cards_data:
            listings.extend(cards_data)
            if log_fn:
                log_fn(f"  ✅ {len(cards_data)} карточек")
        else:
            if log_fn:
                log_fn("  ⚠️ Объявления не найдены")
            break

    return listings


def _collect_cards(browser) -> list[dict]:
    """Собирает карточки объявлений с текущей страницы."""
    return _run_js(browser.page(), """
    (function() {
        var results = [];
        var cards = document.querySelectorAll('a.a-card__title');
        if (!cards.length) {
            cards = document.querySelectorAll('div[data-id] a[href*="/a/show/"]');
        }
        cards.forEach(function(card) {
            var href = card.getAttribute('href') || '';
            var title = card.textContent.trim();
            var price = '';
            var parent = card.closest('div[data-id]');
            if (parent) {
                var priceEl = parent.querySelector('.a-card__price');
                if (priceEl) price = priceEl.textContent.trim();
            }
            if (href) {
                var fullUrl = href.startsWith('/') ? 'https://krisha.kz' + href : href;
                results.push({url: fullUrl, title: title, price: price});
            }
        });
        return results;
    })();
    """, timeout_ms=10000) or []



def _detect_captcha(browser) -> bool:
    """Проверяет есть ли reCAPTCHA на странице."""
    result = _run_js(browser.page(), """
    (function() {
        if (document.querySelector('iframe[src*="recaptcha"]')) return true;
        if (document.querySelector('.g-recaptcha')) return true;
        if (document.querySelector('#recaptcha')) return true;
        var text = document.body.innerText || '';
        if (text.indexOf('Я не робот') !== -1 || text.indexOf('not a robot') !== -1) return true;
        return false;
    })();
    """, timeout_ms=3000)
    return bool(result)


def _wait_captcha_solved(browser, log_fn=None, timeout_sec=120) -> bool:
    """Ждёт пока пользователь решит капчу вручную. Возвращает True если решена."""
    if log_fn:
        log_fn("🛑 Обнаружена CAPTCHA — решите её вручную в браузере слева")
    elapsed = 0
    while elapsed < timeout_sec * 1000:
        _sleep_ms(2000)
        elapsed += 2000
        if not _detect_captcha(browser):
            if log_fn:
                log_fn("✅ CAPTCHA решена, продолжаю...")
            _sleep_ms(1500)
            return True
    if log_fn:
        log_fn(f"⏰ Таймаут CAPTCHA ({timeout_sec} сек)")
    return False


def extract_phone(browser, listing_url: str, log_fn=None) -> str | None:
    """
    Открывает объявление в встроенном браузере, кликает 'Показать телефон',
    забирает номер — всё видно пользователю в реальном времени.
    """
    _load_url(browser, listing_url, wait_sec=2.5)

    # Проверяем капчу на странице
    if _detect_captcha(browser):
        solved = _wait_captcha_solved(browser, log_fn=log_fn, timeout_sec=120)
        if not solved:
            return None

    # Закрываем попапы
    _run_js(browser.page(), """
        document.querySelectorAll('[class*="close"], [data-dismiss="modal"]').forEach(el => {
            try { if(el.offsetHeight > 0) el.click(); } catch(e) {}
        });
        document.body.style.overflow = '';
    """)

    # Кликаем "Показать телефон"
    clicked = _run_js(browser.page(), """
    (function() {
        // По CSS селекторам
        var selectors = [
            'button.show-phones',
            'button[class*="phone"]',
            '.offer__contacts-phones__btn',
            '[data-id="show-phone"]',
            'button.phones-show',
            '.show-phone-btn',
            'a[class*="phone"]'
        ];
        for (var i = 0; i < selectors.length; i++) {
            var el = document.querySelector(selectors[i]);
            if (el && el.offsetHeight > 0) {
                el.click();
                return 'clicked_css';
            }
        }
        // По тексту кнопок
        var buttons = document.querySelectorAll('button, a');
        for (var j = 0; j < buttons.length; j++) {
            var text = buttons[j].textContent.toLowerCase();
            if ((text.indexOf('телефон') !== -1 || text.indexOf('показать') !== -1 || text.indexOf('позвонить') !== -1) && buttons[j].offsetHeight > 0) {
                buttons[j].click();
                return 'clicked_text';
            }
        }
        return 'not_found';
    })();
    """, timeout_ms=5000)

    if clicked and 'clicked' in str(clicked):
        if log_fn:
            log_fn("  🔘 Кликнул 'Показать телефон'")
        _sleep_ms(2500)  # Ждём AJAX загрузку номера

        # Проверяем капчу
        if _detect_captcha(browser):
            solved = _wait_captcha_solved(browser, log_fn=log_fn, timeout_sec=120)
            if not solved:
                return None

    # Извлекаем номер
    phone_data = _run_js(browser.page(), """
    (function() {
        // 1. tel: ссылки
        var telLinks = document.querySelectorAll('a[href^="tel:"]');
        for (var i = 0; i < telLinks.length; i++) {
            var raw = telLinks[i].getAttribute('href').replace('tel:', '').trim();
            if (raw && raw.replace(/\\D/g, '').length >= 10) return raw;
        }

        // 2. data-phone атрибуты
        var phoneEls = document.querySelectorAll('[data-phone]');
        for (var j = 0; j < phoneEls.length; j++) {
            var dp = phoneEls[j].getAttribute('data-phone');
            if (dp) return dp;
        }

        // 3. Элементы с классом phone
        var phoneClasses = document.querySelectorAll('[class*="phone"] a, [class*="phone"] span, .offer__advert-short-info__phone');
        for (var k = 0; k < phoneClasses.length; k++) {
            var txt = phoneClasses[k].textContent.trim();
            if (/\\d{3}/.test(txt)) return txt;
        }

        // 4. Регулярка по body
        var bodyText = document.body.innerText;
        var match = bodyText.match(/(?:\\+?7|8)[\\s\\-]?\\(?\\d{3}\\)?[\\s\\-]?\\d{3}[\\s\\-]?\\d{2}[\\s\\-]?\\d{2}/);
        if (match) return match[0];

        return null;
    })();
    """, timeout_ms=5000)

    if phone_data:
        phone = normalize_phone(str(phone_data))
        if phone and len(phone) >= 11:
            return phone

    return None
