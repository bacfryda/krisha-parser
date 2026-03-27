"""
Парсер krisha.kz через Playwright (sync API) + playwright-stealth.
Антидетект: случайные задержки, скроллинг, реальные клики по фильтрам.
CAPTCHA решается через 2Captcha API.

Миграция с Selenium (undetected_chromedriver) → Playwright — публичный API сохранён.
"""
import os
from app_paths import APP_DIR
import re
import time
import random
import json
import urllib.parse
import threading
import queue as _queue_mod
from bs4 import BeautifulSoup

from playwright.sync_api import sync_playwright, Playwright, Browser, BrowserContext, Page

from captcha_solver import solve_captcha, detect_captcha

BASE_URL = "https://krisha.kz"

# Глобальное состояние Playwright
_playwright: Playwright | None = None
_browser: Browser | None = None
_context: BrowserContext | None = None
_page: Page | None = None

# Обратная совместимость — gui.py импортирует _driver
_driver = None  # alias → _page

# Уникальный маркер для поиска окна Chrome (не совпадёт с Kiro IDE)
CHROME_WINDOW_MARKER = "KRISHA_PARSER_CHROME_7x9k2"

# Файл сессии (Playwright storage_state)
_SESSION_FILE = os.path.join(APP_DIR, "sessions", "krisha_playwright_state.json")

# ─── Playwright Thread (все PW-операции в одном потоке) ────────
_pw_thread: threading.Thread | None = None
_pw_queue: _queue_mod.Queue | None = None


def _pw_thread_loop(q: _queue_mod.Queue):
    """Рабочий цикл Playwright-потока: берёт задачи из очереди и выполняет."""
    while True:
        item = q.get()
        if item is None:
            break
        fn, args, kwargs, result_q = item
        try:
            result = fn(*args, **kwargs)
            result_q.put(("ok", result))
        except Exception as e:
            result_q.put(("err", e))


def _ensure_pw_thread():
    """Запускает Playwright-поток если ещё не запущен."""
    global _pw_thread, _pw_queue
    if _pw_thread is not None and _pw_thread.is_alive():
        return
    _pw_queue = _queue_mod.Queue()
    _pw_thread = threading.Thread(target=_pw_thread_loop, args=(_pw_queue,), daemon=True)
    _pw_thread.start()


def _run_in_pw_thread(fn, *args, **kwargs):
    """Выполняет функцию в Playwright-потоке и возвращает результат.
    Если уже в PW-потоке — вызывает напрямую."""
    _ensure_pw_thread()
    if threading.current_thread() is _pw_thread:
        return fn(*args, **kwargs)
    result_q: _queue_mod.Queue = _queue_mod.Queue()
    _pw_queue.put((fn, args, kwargs, result_q))
    status, value = result_q.get()
    if status == "err":
        raise value
    return value


def pw_thread(fn):
    """Декоратор: выполняет функцию в выделенном Playwright-потоке."""
    import functools
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        return _run_in_pw_thread(fn, *args, **kwargs)
    return wrapper


def normalize_phone(raw: str) -> str:
    """Приводит номер к формату +7XXXXXXXXXX."""
    if not raw:
        return ""
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return ""
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    if len(digits) == 10:
        digits = "7" + digits
    if not digits.startswith("7"):
        return "+" + digits
    return "+" + digits[:11]


def build_search_url(cfg: dict, page: int = 1) -> str:
    """Собирает URL поиска из конфига со всеми фильтрами."""
    k = cfg["krisha"]
    deal = k.get("deal_type", "sale")
    region_alias = k.get("region_alias", "")

    if deal == "rent":
        path = "/arenda/kvartiry/"
    else:
        path = "/prodazha/kvartiry/"

    if region_alias:
        path += f"{region_alias}/"

    params = []

    rooms = k.get("rooms", [])
    if rooms:
        for r in rooms:
            params.append(f"das[live.rooms]={r}")

    if k.get("price_from"):
        params.append(f"das[price][from]={k['price_from']}")
    if k.get("price_to"):
        params.append(f"das[price][to]={k['price_to']}")

    if k.get("has_photo"):
        params.append("das[_sys.hasphoto]=1")
    if k.get("novostroiki"):
        params.append("das[novostroiki]=1")
    if k.get("from_owner"):
        params.append("das[who]=1")
    if k.get("from_agent"):
        params.append("das[_sys.fromAgent]=1")

    for bt in k.get("building_type", []):
        params.append(f"das[flat.building]={bt}")

    if k.get("floor_from"):
        params.append(f"das[flat.floor][from]={k['floor_from']}")
    if k.get("floor_to"):
        params.append(f"das[flat.floor][to]={k['floor_to']}")

    if k.get("house_floors_from"):
        params.append(f"das[house.floor_num][from]={k['house_floors_from']}")
    if k.get("house_floors_to"):
        params.append(f"das[house.floor_num][to]={k['house_floors_to']}")

    if k.get("year_from"):
        params.append(f"das[house.year][from]={k['year_from']}")
    if k.get("year_to"):
        params.append(f"das[house.year][to]={k['year_to']}")

    if k.get("not_last_floor"):
        params.append("das[floor_not_last]=1")
    if k.get("not_first_floor"):
        params.append("das[floor_not_first]=1")

    if k.get("square_from"):
        params.append(f"das[live.square][from]={k['square_from']}")
    if k.get("square_to"):
        params.append(f"das[live.square][to]={k['square_to']}")

    if k.get("kitchen_from"):
        params.append(f"das[live.square_k][from]={k['kitchen_from']}")
    if k.get("kitchen_to"):
        params.append(f"das[live.square_k][to]={k['kitchen_to']}")

    if k.get("mortgage"):
        params.append(f"das[mortgage]={k['mortgage']}")

    if k.get("priv_dorm"):
        params.append(f"das[flat.priv_dorm]={k['priv_dorm']}")

    if k.get("has_change"):
        params.append("das[has_change]=1")

    for t in k.get("toilet", []):
        params.append(f"das[flat.toilet]={t}")

    for p in k.get("phone_line", []):
        params.append(f"das[flat.phone]={p}")

    if k.get("text_search"):
        params.append(f"_txt_={k['text_search']}")

    if page > 1:
        params.append(f"page={page}")

    url = BASE_URL + path
    if params:
        url += "?" + "&".join(params)
    return url


# ─── Утилиты: человекоподобное поведение ───────────────────────

def _human_delay(min_s=1.0, max_s=3.0):
    """Случайная пауза как у человека."""
    time.sleep(random.uniform(min_s, max_s))


def _human_scroll(page: Page):
    """Случайный скролл вниз-вверх."""
    try:
        scroll_y = random.randint(100, 400)
        page.evaluate(f"window.scrollBy(0, {scroll_y})")
        time.sleep(random.uniform(0.3, 0.8))
        if random.random() < 0.3:
            page.evaluate(f"window.scrollBy(0, -{random.randint(50, 150)})")
            time.sleep(random.uniform(0.2, 0.5))
    except Exception:
        pass


def _human_click(page: Page, locator_or_selector):
    """Клик с fallback на JS."""
    try:
        if isinstance(locator_or_selector, str):
            loc = page.locator(locator_or_selector)
        else:
            loc = locator_or_selector
        loc.scroll_into_view_if_needed()
        time.sleep(random.uniform(0.1, 0.4))
        loc.click()
    except Exception:
        try:
            if isinstance(locator_or_selector, str):
                page.evaluate(f'document.querySelector("{locator_or_selector}").click()')
        except Exception:
            pass


def _human_type(page: Page, locator_or_selector, text: str):
    """Печатает текст посимвольно как человек."""
    if isinstance(locator_or_selector, str):
        locator_or_selector = page.locator(locator_or_selector)
    locator_or_selector.fill("")
    time.sleep(random.uniform(0.2, 0.5))
    page.keyboard.type(str(text), delay=random.randint(50, 150))
    time.sleep(random.uniform(0.3, 0.6))


def _scroll_to(page: Page, locator_or_selector):
    """Скроллит к элементу чтобы он был видим."""
    try:
        if isinstance(locator_or_selector, str):
            loc = page.locator(locator_or_selector)
        else:
            loc = locator_or_selector
        loc.scroll_into_view_if_needed()
        _human_delay(0.3, 0.6)
    except Exception:
        pass


# ─── Драйвер ──────────────────────────────────────────────────

@pw_thread
def _get_driver() -> Page:
    """Создаёт или возвращает существующий Playwright Page."""
    global _playwright, _browser, _context, _page, _driver

    if _page is not None:
        try:
            _ = _page.url  # Проверка что page жив
            return _page
        except Exception:
            _cleanup_browser()

    _playwright = sync_playwright().start()
    _browser = _playwright.chromium.launch(
        headless=False,
        channel="chrome",
        args=[
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--disable-popup-blocking",
            "--lang=ru-RU,ru",
            "--window-position=-10000,-10000",
            "--window-size=1200,900",
            "--disable-extensions",
        ],
    )

    # Загружаем сессию если есть
    storage = _load_storage_state()
    _context = _browser.new_context(
        storage_state=storage,
        locale="ru-RU",
        viewport={"width": 1200, "height": 900},
    )
    _context.set_default_timeout(45000)

    _page = _context.new_page()

    # Антидетект
    from playwright_stealth import Stealth
    _stealth = Stealth()
    _stealth.apply_stealth_sync(_page)

    # Дополнительная JS-маскировка
    _page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'languages', {get: () => ['ru-RU', 'ru', 'en-US', 'en']});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        window.chrome = {runtime: {}};
    """)

    # Маркер для win32gui
    _page.evaluate(f"document.title = '{CHROME_WINDOW_MARKER}'")

    # Обратная совместимость
    _driver = _page

    return _page


def _detect_chrome_version() -> int | None:
    """Определяет установленную версию Chrome на Windows."""
    import subprocess as sp
    # Пробуем через реестр
    paths = [
        r'HKLM\SOFTWARE\Google\Chrome\BLBeacon',
        r'HKCU\SOFTWARE\Google\Chrome\BLBeacon',
        r'HKLM\SOFTWARE\WOW6432Node\Google\Chrome\BLBeacon',
    ]
    for reg_path in paths:
        try:
            result = sp.run(
                ['reg', 'query', reg_path, '/v', 'version'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'version' in line.lower() and 'REG_SZ' in line:
                        ver_str = line.strip().split()[-1]
                        major = int(ver_str.split('.')[0])
                        return major
        except Exception:
            continue
    # Пробуем через файл
    try:
        chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        if not os.path.exists(chrome_path):
            chrome_path = r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        if os.path.exists(chrome_path):
            result = sp.run(
                ['wmic', 'datafile', 'where', f'name="{chrome_path.replace(chr(92), chr(92)*2)}"',
                 'get', 'Version', '/value'],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.split('\n'):
                if 'Version=' in line:
                    ver_str = line.split('=')[1].strip()
                    return int(ver_str.split('.')[0])
    except Exception:
        pass
    return None


def _cleanup_browser():
    """Закрывает все Playwright ресурсы и обнуляет глобальные переменные."""
    global _playwright, _browser, _context, _page, _driver
    try:
        if _page:
            _page.close()
    except Exception:
        pass
    try:
        if _context:
            _context.close()
    except Exception:
        pass
    try:
        if _browser:
            _browser.close()
    except Exception:
        pass
    try:
        if _playwright:
            _playwright.stop()
    except Exception:
        pass
    _page = None
    _context = None
    _browser = None
    _playwright = None
    _driver = None


@pw_thread
def close_driver():
    """Закрывает браузер."""
    _cleanup_browser()


# ─── Session Manager ──────────────────────────────────────────

def _save_session():
    """Сохраняет cookies + localStorage через storage_state."""
    if _context is None:
        return
    try:
        os.makedirs(os.path.dirname(_SESSION_FILE), exist_ok=True)
        _context.storage_state(path=_SESSION_FILE)
    except Exception:
        pass


def _load_storage_state() -> str | None:
    """Загружает сохранённое состояние сессии."""
    if not os.path.exists(_SESSION_FILE):
        return None
    try:
        with open(_SESSION_FILE, "r", encoding="utf-8") as f:
            json.load(f)  # Валидация JSON
        return _SESSION_FILE
    except Exception:
        return None


def _load_cookies(driver=None):
    """Обратная совместимость — gui.py вызывает _load_cookies.
    В Playwright сессия загружается через storage_state при создании контекста,
    поэтому эта функция — no-op заглушка.
    """
    pass


@pw_thread
def save_session_if_logged(driver=None):
    """Сохраняет сессию если пользователь авторизован."""
    if driver is None:
        driver = _get_driver()
    if is_logged_in(driver):
        _save_session()


# ─── Auth Manager ─────────────────────────────────────────────

@pw_thread
def is_logged_in(driver=None) -> bool:
    """Проверяет авторизован ли пользователь на krisha.kz."""
    if driver is None:
        driver = _get_driver()
    try:
        current = driver.url or ""
        if "krisha.kz" not in current and "kolesa.kz" not in current:
            return False

        result = driver.evaluate("""() => {
            var nav = document.querySelector('nav, header, [class*="header"], [class*="nav"]');
            var searchArea = nav ? nav : document;
            var text = searchArea.textContent || '';

            if (text.indexOf('Кабинет') !== -1) return 'logged';
            if (text.indexOf('Избранное') !== -1 && text.indexOf('Сообщения') !== -1) return 'logged';

            if (text.indexOf('Регистрация') !== -1) return 'not_logged';

            var links = document.querySelectorAll('a');
            for (var i = 0; i < links.length; i++) {
                var t = (links[i].textContent || '').trim();
                if (t === 'Кабинет' || t.indexOf('Кабинет') !== -1) return 'logged';
            }
            for (var j = 0; j < links.length; j++) {
                var t2 = (links[j].textContent || '').trim();
                if (t2 === 'Регистрация') return 'not_logged';
            }

            return 'unknown';
        }""")
        if result == 'logged':
            return True
        if result == 'not_logged':
            return False
        # unknown — пробуем cookies как fallback
        cookies = _context.cookies() if _context else []
        cookie_names = {c["name"] for c in cookies}
        auth_cookies = {"krisha_id", "ssid", "kr_sess", "session_id", "user_id"}
        return bool(cookie_names & auth_cookies)
    except Exception:
        return False


@pw_thread
def open_login_page(driver=None):
    """Открывает страницу авторизации krisha.kz — кликает 'Личный кабинет'."""
    if driver is None:
        driver = _get_driver()
    try:
        current = driver.url
        if "krisha.kz" not in current:
            driver.goto("https://krisha.kz/prodazha/kvartiry/", wait_until="domcontentloaded")
            _human_delay(2.0, 3.0)
        clicked = driver.evaluate("""() => {
            var links = document.querySelectorAll('a');
            for (var i = 0; i < links.length; i++) {
                var t = (links[i].textContent || '').trim();
                if (t === 'Личный кабинет' || t === 'Войти') {
                    links[i].click();
                    return true;
                }
            }
            return false;
        }""")
        if not clicked:
            driver.goto("https://id.kolesa.kz/login?redirect_uri=https%3A%2F%2Fkrisha.kz",
                        wait_until="domcontentloaded")
        # Ждём загрузки страницы логина
        _human_delay(2.0, 4.0)
        # Дополнительно ждём networkidle для SPA
        try:
            driver.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
    except Exception:
        pass


@pw_thread
def type_in_focused(text: str, submit: bool = False):
    """Вводит текст в текущее активное поле на странице."""
    page = _get_driver()
    try:
        # Очищаем текущее поле
        page.keyboard.press("Control+a")
        _human_delay(0.2, 0.4)
        page.keyboard.press("Delete")
        _human_delay(0.1, 0.2)
        page.keyboard.type(str(text), delay=random.randint(30, 100))
        if submit:
            _human_delay(0.3, 0.6)
            page.keyboard.press("Enter")
        return True
    except Exception:
        pass
    return False


@pw_thread
def login_krisha(phone: str, password: str = "", log_fn=None) -> bool:
    """Авторизуется на krisha.kz через Playwright."""
    page = _get_driver()
    try:
        open_login_page(page)
        _human_delay(2.0, 3.0)
        _close_popups(page)

        # Ждём загрузки формы логина (SPA может рендерить с задержкой)
        current_url = page.url
        if log_fn:
            log_fn(f"  Страница: {current_url}")

        # Если не перешли на страницу логина — переходим напрямую
        if "id.kolesa.kz" not in current_url and "login" not in current_url:
            if log_fn:
                log_fn("  Переход на страницу логина напрямую...")
            page.goto("https://id.kolesa.kz/login?redirect_uri=https%3A%2F%2Fkrisha.kz",
                       wait_until="domcontentloaded")
            _human_delay(2.0, 3.0)
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass
            current_url = page.url
            if log_fn:
                log_fn(f"  Страница после перехода: {current_url}")

        # Ждём появления любого input на странице (до 15 сек)
        try:
            page.wait_for_selector("input", state="visible", timeout=15000)
        except Exception:
            if log_fn:
                log_fn("  Ожидание input истекло, пробую найти поле...")

        _close_popups(page)

        # Шаг 1: Ищем поле телефона (расширенные селекторы)
        phone_input = None
        for sel in [
            'input[type="tel"]',
            'input[name="phone"]',
            'input[inputmode="numeric"]',
            'input[inputmode="tel"]',
            'input[autocomplete="tel"]',
            'input[placeholder*="телефон" i]',
            'input[placeholder*="номер" i]',
            'input[placeholder*="phone" i]',
            'input[type="number"]',
            'input[type="text"]',
            'input:not([type="hidden"]):not([type="submit"]):not([type="button"]):not([type="checkbox"]):not([type="radio"])',
        ]:
            try:
                els = page.query_selector_all(sel)
                for el in els:
                    if el.is_visible():
                        phone_input = el
                        break
                if phone_input:
                    break
            except Exception:
                continue

        # Fallback: ищем любой видимый input внутри формы
        if not phone_input:
            try:
                forms = page.query_selector_all('form')
                for form in forms:
                    inputs = form.query_selector_all('input')
                    for inp in inputs:
                        if inp.is_visible():
                            inp_type = inp.get_attribute('type') or ''
                            if inp_type not in ('hidden', 'submit', 'button', 'checkbox', 'radio'):
                                phone_input = inp
                                break
                    if phone_input:
                        break
            except Exception:
                pass

        # Fallback 2: любой видимый input на странице
        if not phone_input:
            try:
                all_inputs = page.query_selector_all('input')
                for inp in all_inputs:
                    try:
                        if inp.is_visible():
                            inp_type = (inp.get_attribute('type') or '').lower()
                            if inp_type not in ('hidden', 'submit', 'button', 'checkbox', 'radio', 'file'):
                                phone_input = inp
                                break
                    except Exception:
                        continue
            except Exception:
                pass

        if not phone_input:
            if log_fn:
                log_fn("  Поле телефона не найдено")
                # Отладка: логируем что видим на странице
                try:
                    all_inputs = page.query_selector_all('input')
                    log_fn(f"  Всего input: {len(all_inputs)}")
                    for i, inp in enumerate(all_inputs[:10]):
                        attrs = page.evaluate("""(el) => {
                            return {
                                type: el.type || '', name: el.name || '',
                                placeholder: el.placeholder || '',
                                id: el.id || '', className: el.className || '',
                                visible: el.offsetHeight > 0,
                                rect: el.getBoundingClientRect().toJSON()
                            }
                        }""", inp)
                        log_fn(f"    [{i}]: {attrs}")
                except Exception as dbg_err:
                    log_fn(f"  Ошибка отладки: {dbg_err}")
                # Логируем фрагмент HTML
                try:
                    body_html = page.evaluate("() => document.body.innerHTML.substring(0, 2000)")
                    log_fn(f"  HTML (первые 2000): {body_html[:500]}")
                except Exception:
                    pass
            return False

        # Вводим телефон
        phone_input.scroll_into_view_if_needed()
        phone_input.click()
        _human_delay(0.3, 0.6)
        phone_input.fill("")
        _human_delay(0.2, 0.4)
        page.keyboard.type(str(phone), delay=random.randint(50, 150))
        if log_fn:
            log_fn("  Телефон введён")

        _human_delay(0.5, 1.0)

        # Нажимаем "Продолжить" / "Войти"
        submit_btn = None
        for sel in [
            'button[type="submit"]',
            'button[class*="submit"]',
            'input[type="submit"]',
        ]:
            try:
                els = page.query_selector_all(sel)
                for el in els:
                    if el.is_visible():
                        submit_btn = el
                        break
                if submit_btn:
                    break
            except Exception:
                continue

        if not submit_btn:
            try:
                buttons = page.query_selector_all("button")
                for b in buttons:
                    txt = (b.text_content() or "").strip().lower()
                    if ("продолжить" in txt or "войти" in txt or "далее" in txt) and b.is_visible():
                        submit_btn = b
                        break
            except Exception:
                pass

        if submit_btn:
            submit_btn.click()
            if log_fn:
                log_fn("  Нажал 'Продолжить'")
        else:
            page.keyboard.press("Enter")
            if log_fn:
                log_fn("  Нажал Enter")

        _human_delay(3.0, 5.0)

        # Шаг 2: Если есть поле пароля — вводим
        if password:
            pwd_input = None
            for sel in [
                'input[type="password"]',
                'input[name="password"]',
                'input[placeholder*="пароль"]',
                'input[placeholder*="Пароль"]',
            ]:
                try:
                    els = page.query_selector_all(sel)
                    for el in els:
                        if el.is_visible():
                            pwd_input = el
                            break
                    if pwd_input:
                        break
                except Exception:
                    continue

            if pwd_input:
                pwd_input.scroll_into_view_if_needed()
                pwd_input.click()
                _human_delay(0.3, 0.6)
                pwd_input.fill("")
                page.keyboard.type(str(password), delay=random.randint(50, 150))
                if log_fn:
                    log_fn("  Пароль введён")
                _human_delay(0.5, 1.0)

                # Нажимаем войти
                try:
                    buttons = page.query_selector_all("button")
                    for b in buttons:
                        txt = (b.text_content() or "").strip().lower()
                        if ("войти" in txt or "продолжить" in txt) and b.is_visible():
                            b.click()
                            break
                    else:
                        page.keyboard.press("Enter")
                except Exception:
                    page.keyboard.press("Enter")

                _human_delay(3.0, 5.0)
                if log_fn:
                    log_fn("  Ожидаю авторизацию...")
            else:
                if log_fn:
                    log_fn("  Поле пароля не найдено — возможно SMS-код")

        # Проверяем результат
        for check_attempt in range(5):
            _human_delay(1.5, 2.5)
            if is_logged_in(page):
                _save_session()
                if log_fn:
                    log_fn("  Авторизация успешна!")
                try:
                    page.goto("https://krisha.kz/prodazha/kvartiry/")
                    _human_delay(1.5, 2.5)
                except Exception:
                    pass
                return True
            if log_fn and check_attempt < 4:
                log_fn(f"  Проверка авторизации ({check_attempt+1}/5)...")

        if log_fn:
            log_fn("  Авторизация не подтверждена — проверьте данные")
        return False

    except Exception as e:
        if log_fn:
            log_fn(f"  Ошибка авторизации: {e}")
        return False


# ─── Popup Closer ─────────────────────────────────────────────

def _close_popups(page: Page):
    """Закрывает попапы, модалки, cookie-баннеры, оверлеи — оптимизированная версия."""
    try:
        page.evaluate("""() => {
            // Единый проход: кликаем кнопки закрытия
            var closeSels = '[class*="close"],[data-dismiss="modal"],[aria-label="Close"],[aria-label="close"],.kr-popup__close,.kr-modal__close';
            document.querySelectorAll(closeSels).forEach(function(el) {
                try { if (el.offsetHeight > 0 && el.offsetWidth > 0) el.click(); } catch(e) {}
            });

            // Кнопки по тексту (только button и a, не все элементы)
            var dismissTexts = ['закрыть','понятно','скрыть подсказку','нет, спасибо','не сейчас','пропустить','скрыть','got it','dismiss'];
            document.querySelectorAll('a, button').forEach(function(el) {
                var t = (el.textContent || '').trim().toLowerCase();
                if (dismissTexts.indexOf(t) !== -1 && el.offsetHeight > 0) {
                    try { el.click(); } catch(e) {}
                }
            });

            // Скрываем оверлеи и бэкдропы
            document.querySelectorAll('.modal-backdrop,[class*="overlay"],[class*="backdrop"],[class*="cookie-banner"],[class*="consent"],.kr-popup,.kr-modal').forEach(function(el) {
                try { el.style.display = 'none'; } catch(e) {}
            });

            // Скрываем fixed попапы (не nav/header)
            document.querySelectorAll('[style*="position: fixed"],[style*="position:fixed"]').forEach(function(el) {
                var cls = (el.className || '').toLowerCase();
                var id = (el.id || '').toLowerCase();
                if (cls.indexOf('nav') !== -1 || cls.indexOf('header') !== -1) return;
                if (id.indexOf('nav') !== -1 || id.indexOf('header') !== -1) return;
                if (cls.indexOf('popup') !== -1 || cls.indexOf('modal') !== -1 ||
                    cls.indexOf('banner') !== -1 || cls.indexOf('cookie') !== -1 ||
                    cls.indexOf('overlay') !== -1 || cls.indexOf('hint') !== -1 ||
                    cls.indexOf('promo') !== -1 || cls.indexOf('toast') !== -1) {
                    el.style.display = 'none';
                }
            });

            // Восстанавливаем скролл
            document.body.style.overflow = '';
            document.body.style.position = '';
            document.body.classList.remove('modal-open', 'no-scroll', 'popup-open');
            document.documentElement.style.overflow = '';
        }""")
    except Exception:
        pass


# ─── Вспомогательные функции фильтров ─────────────────────────

def _fill_input(page: Page, field_name: str, value, log_fn=None):
    """Заполняет input поле по name или id. После ввода нажимает Tab для триггера AJAX."""
    if not value:
        return
    value = str(value).strip()
    if not value:
        return
    try:
        el = None
        # По id
        el = page.query_selector(f'#{field_name}')
        if not el:
            el = page.query_selector(f'[name="{field_name}"]')
        if not el:
            # XPath fallback
            el = page.query_selector(f'input[name="{field_name}"]')
        if el:
            el.scroll_into_view_if_needed()
            el.click()
            # Очищаем через Ctrl+A + Delete
            page.keyboard.press("Control+a")
            _human_delay(0.1, 0.2)
            page.keyboard.press("Delete")
            _human_delay(0.1, 0.3)
            page.keyboard.type(str(value), delay=random.randint(50, 150))
            # Tab для blur — триггерит AJAX обновление счётчика
            page.keyboard.press("Tab")
            _human_delay(0.3, 0.6)
    except Exception as e:
        if log_fn:
            log_fn(f"  -- input {field_name}: {e}")


def _css_escape(s: str) -> str:
    """Экранирует спецсимволы CSS в строке для использования в селекторах."""
    import re
    return re.sub(r'([\[\].#:>~+,(){}|^$*=!])', r'\\\1', s)


def _set_checkbox(page: Page, field_name: str, should_check: bool, log_fn=None):
    """Устанавливает чекбокс."""
    if not should_check:
        return
    esc = _css_escape(field_name)
    try:
        cb = page.query_selector(f'#{esc}-checkbox-0')
        if not cb:
            cb = page.query_selector(f'input[name="{field_name}"][type="checkbox"]')

        if cb:
            is_checked = cb.is_checked()
            if should_check and not is_checked:
                # Кликаем по label (не по скрытому input)
                try:
                    label = page.query_selector(f'label[for="{field_name}-checkbox-0"]')
                    if label:
                        label.scroll_into_view_if_needed()
                        label.click()
                    else:
                        cb.scroll_into_view_if_needed()
                        page.evaluate("el => el.click()", cb)
                except Exception:
                    cb.scroll_into_view_if_needed()
                    page.evaluate("el => el.click()", cb)
                _human_delay(0.2, 0.5)
    except Exception as e:
        if log_fn:
            log_fn(f"  -- checkbox {field_name}: {e}")


def _select_option(page: Page, field_name: str, value, log_fn=None):
    """Выбирает опцию в select (обычном или multiple)."""
    if not value:
        return
    value = str(value)
    try:
        # Krisha использует кастомные select — скрытый <select> + видимый UI
        page.evaluate(f"""() => {{
            var sel = document.querySelector('select[name="{field_name}"]');
            if (sel) {{
                var opts = sel.options;
                for (var i = 0; i < opts.length; i++) {{
                    if (opts[i].value === '{value}') {{
                        opts[i].selected = true;
                        sel.dispatchEvent(new Event('change', {{bubbles: true}}));
                        break;
                    }}
                }}
            }}
        }}""")
        _human_delay(0.2, 0.5)

        # Также пробуем кликнуть по видимому UI элементу (кастомный dropdown)
        try:
            container = page.query_selector(f'div[data-field="{field_name}"]')
            if container:
                trigger = container.query_selector('.dropdown-toggle, .select2-choice, .btn')
                if trigger:
                    trigger.click()
                    _human_delay(0.3, 0.6)
                    option_el = page.query_selector(f'li[data-value="{value}"], a[data-value="{value}"]')
                    if option_el:
                        option_el.click()
                        _human_delay(0.2, 0.5)
        except Exception:
            pass

    except Exception as e:
        if log_fn:
            log_fn(f"  -- select {field_name}={value}: {e}")


# ─── Применение фильтров реальными кликами ─────────────────────

def _apply_filters(page: Page, cfg: dict, log_fn=None):
    """
    Применяет все фильтры из конфига реальными кликами по DOM элементам.
    Работает на странице поиска krisha.kz (уже загруженной).
    """
    k = cfg["krisha"]
    applied = 0

    _human_delay(1.0, 2.0)

    def _get_nb_total():
        try:
            return page.evaluate("""() => {
                var el = document.querySelector('.nb-total');
                return el ? (el.textContent || '').trim() : '';
            }""") or ""
        except Exception:
            return ""

    def _wait_nb_update(old_val, timeout=5):
        """Ждёт пока nb-total обновится (AJAX) или таймаут."""
        start = time.time()
        while time.time() - start < timeout:
            cur = _get_nb_total()
            if cur and cur != old_val:
                return cur
            time.sleep(0.3)
        return _get_nb_total()

    # ── Комнаты (button-select labels) ──
    rooms = k.get("rooms", [])
    if rooms:
        old_nb = _get_nb_total()
        for room_val in rooms:
            try:
                # Через XPath — надёжнее для спецсимволов
                el = page.query_selector(f'div#das\\[live\\.rooms\\] label[class*="das[live.rooms]-{room_val}"]')
                if not el:
                    el = page.locator(f'//div[@id="das[live.rooms]"]//label[contains(@class, "das[live.rooms]-{room_val}")]').first
                if not el:
                    el = page.locator(f'//input[@name="das[live.rooms]" and @value="{room_val}"]/parent::label').first
                if el:
                    try:
                        el.scroll_into_view_if_needed()
                        el.click()
                    except Exception:
                        pass
                    applied += 1
                    _human_delay(0.3, 0.8)
            except Exception as e:
                if log_fn:
                    log_fn(f"  -- Комнаты {room_val}: {e}")
        _wait_nb_update(old_nb)

    # ── Цена ──
    price_from = k.get("price_from", "")
    price_to = k.get("price_to", "")
    if price_from or price_to:
        old_nb = _get_nb_total()
        _fill_input(page, 'das[price][from]', price_from, log_fn)
        _fill_input(page, 'das[price][to]', price_to, log_fn)
        try:
            page.evaluate("""() => {
                var body = document.querySelector('label.control-label, .search-form-bottom-middle');
                if (body) body.click();
            }""")
        except Exception:
            pass
        _wait_nb_update(old_nb)
    else:
        _fill_input(page, 'das[price][from]', "", log_fn)
        _fill_input(page, 'das[price][to]', "", log_fn)

    # ── Чекбоксы ──
    checkboxes_to_set = [
        ('das[_sys.hasphoto]', k.get("has_photo", False)),
        ('das[novostroiki]', k.get("novostroiki", False)),
        ('das[who]', k.get("from_owner", False)),
        ('das[_sys.fromAgent]', k.get("from_agent", False)),
        ('das[floor_not_last]', k.get("not_last_floor", False)),
        ('das[floor_not_first]', k.get("not_first_floor", False)),
        ('das[has_change]', k.get("has_change", False)),
    ]
    any_checkbox = any(v for _, v in checkboxes_to_set)
    if any_checkbox:
        old_nb = _get_nb_total()
    for name, val in checkboxes_to_set:
        _set_checkbox(page, name, val, log_fn)
    if any_checkbox:
        _wait_nb_update(old_nb)

    _human_scroll(page)
    _human_delay(0.5, 1.0)

    # ── Тип дома (multiple select) ──
    building_types = k.get("building_type", [])
    if building_types:
        old_nb = _get_nb_total()
        for bt in building_types:
            _select_option(page, 'das[flat.building]', bt, log_fn)
        _wait_nb_update(old_nb)

    # ── Этаж ──
    floor_from = k.get("floor_from", "")
    floor_to = k.get("floor_to", "")
    if floor_from or floor_to:
        old_nb = _get_nb_total()
        _fill_input(page, 'das[flat.floor][from]', floor_from, log_fn)
        _fill_input(page, 'das[flat.floor][to]', floor_to, log_fn)
        try:
            page.evaluate("""() => {
                var body = document.querySelector('label.control-label, .search-form-bottom-middle');
                if (body) body.click();
            }""")
        except Exception:
            pass
        _wait_nb_update(old_nb)
    else:
        _fill_input(page, 'das[flat.floor][from]', "", log_fn)
        _fill_input(page, 'das[flat.floor][to]', "", log_fn)

    # ── Этажей в доме ──
    _fill_input(page, 'das[house.floor_num][from]', k.get("house_floors_from", ""), log_fn)
    _fill_input(page, 'das[house.floor_num][to]', k.get("house_floors_to", ""), log_fn)

    _human_scroll(page)

    # ── Год постройки ──
    _fill_input(page, 'das[house.year][from]', k.get("year_from", ""), log_fn)
    _fill_input(page, 'das[house.year][to]', k.get("year_to", ""), log_fn)

    # ── Площадь ──
    sq_from = k.get("square_from", "")
    sq_to = k.get("square_to", "")
    if sq_from or sq_to:
        old_nb = _get_nb_total()
        _fill_input(page, 'das[live.square][from]', sq_from, log_fn)
        _fill_input(page, 'das[live.square][to]', sq_to, log_fn)
        try:
            page.evaluate("""() => {
                var body = document.querySelector('label.control-label, .search-form-bottom-middle');
                if (body) body.click();
            }""")
        except Exception:
            pass
        _wait_nb_update(old_nb)
    else:
        _fill_input(page, 'das[live.square][from]', "", log_fn)
        _fill_input(page, 'das[live.square][to]', "", log_fn)

    # ── Площадь кухни ──
    _fill_input(page, 'das[live.square_k][from]', k.get("kitchen_from", ""), log_fn)
    _fill_input(page, 'das[live.square_k][to]', k.get("kitchen_to", ""), log_fn)

    _human_scroll(page)

    # ── В залоге (select) ──
    if k.get("mortgage"):
        old_nb = _get_nb_total()
        _select_option(page, 'das[mortgage]', k["mortgage"], log_fn)
        _wait_nb_update(old_nb)

    # ── Бывшее общежитие (select) ──
    if k.get("priv_dorm"):
        old_nb = _get_nb_total()
        _select_option(page, 'das[flat.priv_dorm]', k["priv_dorm"], log_fn)
        _wait_nb_update(old_nb)

    # ── Санузел (multiple select) ──
    toilets = k.get("toilet", [])
    if toilets:
        old_nb = _get_nb_total()
        for t in toilets:
            _select_option(page, 'das[flat.toilet]', t, log_fn)
        _wait_nb_update(old_nb)

    # ── Телефон (multiple select) ──
    phones = k.get("phone_line", [])
    if phones:
        old_nb = _get_nb_total()
        for p in phones:
            _select_option(page, 'das[flat.phone]', p, log_fn)
        _wait_nb_update(old_nb)

    _human_delay(0.5, 1.5)

    if log_fn:
        total_filters = (
            len(rooms)
            + bool(k.get("price_from")) + bool(k.get("price_to"))
            + k.get("has_photo", False) + k.get("novostroiki", False)
            + k.get("from_owner", False) + k.get("from_agent", False)
            + len(k.get("building_type", []))
            + bool(k.get("floor_from")) + bool(k.get("floor_to"))
            + bool(k.get("square_from")) + bool(k.get("square_to"))
            + k.get("not_last_floor", False) + k.get("not_first_floor", False)
            + bool(k.get("mortgage")) + bool(k.get("priv_dorm"))
            + k.get("has_change", False)
            + len(k.get("toilet", [])) + len(k.get("phone_line", []))
        )
        log_fn(f"  -- Фильтров задано: {total_filters}")


# ─── Основные функции парсинга ─────────────────────────────────

def _get_results_count(page: Page, log_fn=None) -> int:
    """Считывает кол-во результатов с кнопки 'Показать результаты (N)'."""
    try:
        count = page.evaluate("""() => {
            var nbTotal = document.querySelector('.nb-total');
            if (nbTotal) {
                var t = nbTotal.textContent || '';
                var m = t.replace(/[()]/g, '').replace(/\\s/g, '');
                if (m && /^\\d+$/.test(m)) return parseInt(m, 10);
                var digits = t.replace(/[^\\d]/g, '');
                if (digits) return parseInt(digits, 10);
            }
            var btn = document.querySelector('button.search-btn-main, button.btn-submit');
            if (btn) {
                var txt = btn.textContent || '';
                var m2 = txt.match(/\\((\\d[\\d\\s]*\\d?)\\)/);
                if (m2) return parseInt(m2[1].replace(/\\s/g, ''), 10);
                var m3 = txt.match(/(\\d[\\d\\s]+\\d)/);
                if (m3) return parseInt(m3[1].replace(/\\s/g, ''), 10);
            }
            var btns = document.querySelectorAll('button');
            for (var i = 0; i < btns.length; i++) {
                var t2 = btns[i].textContent || '';
                if (t2.indexOf('результат') !== -1 || t2.indexOf('Показать') !== -1) {
                    var m4 = t2.match(/\\((\\d[\\d\\s]*\\d?)\\)/);
                    if (m4) return parseInt(m4[1].replace(/\\s/g, ''), 10);
                }
            }
            return 0;
        }""")
        if count and count > 0:
            if log_fn:
                log_fn(f"  Кнопка показывает: {count} квартир")
            return count
    except Exception:
        pass
    return 0


def _get_page_results_count(page: Page) -> int:
    """Считывает кол-во результатов со страницы результатов."""
    try:
        count = page.evaluate("""() => {
            if (window.data && window.data.search && window.data.search.nbTotal) {
                var nb = window.data.search.nbTotal.replace(/\\s/g, '');
                if (/^\\d+$/.test(nb)) return parseInt(nb, 10);
            }
            if (window.data && window.data.search && window.data.search.analytics &&
                window.data.search.analytics.default && window.data.search.analytics.default.count) {
                return window.data.search.analytics.default.count;
            }
            var nbEl = document.querySelector('.search-results-nb span, .a-search-subtitle span');
            if (nbEl) {
                var digits = nbEl.textContent.replace(/[^\\d]/g, '');
                if (digits) return parseInt(digits, 10);
            }
            var subtitle = document.querySelector('.search-results-nb, .a-search-subtitle');
            if (subtitle) {
                var t = subtitle.textContent || '';
                var m = t.match(/(\\d[\\d\\s\\u00a0]*\\d)/);
                if (m) return parseInt(m[1].replace(/[\\s\\u00a0]/g, ''), 10);
            }
            var nbTotal = document.querySelector('.nb-total');
            if (nbTotal) {
                var digits2 = nbTotal.textContent.replace(/[^\\d]/g, '');
                if (digits2) return parseInt(digits2, 10);
            }
            var h1 = document.querySelector('h1');
            if (h1) {
                var m2 = h1.textContent.match(/(\\d[\\d\\s\\u00a0]+)\\s*(объявлен|квартир)/i);
                if (m2) return parseInt(m2[1].replace(/[\\s\\u00a0]/g, ''), 10);
            }
            return 0;
        }""")
        return count or 0
    except Exception:
        return 0


def _click_search_button(page: Page, log_fn=None, **_kwargs):
    """Нажимает кнопку 'Показать результаты'."""
    try:
        # Патчим action формы — добавляем регион из текущего URL
        page.evaluate("""() => {
            var form = document.getElementById('a-search-form');
            if (!form) form = document.querySelector('form[action*="/kvartiry/"]');
            if (form) {
                var path = window.location.pathname;
                if (path && !path.endsWith('/')) path += '/';
                if (path && path.indexOf('/kvartiry/') !== -1) {
                    form.action = path;
                }
            }
        }""")
        _human_delay(0.2, 0.4)

        btn = None
        # 1. Точный селектор
        try:
            el = page.query_selector("button.search-btn-main")
            if el and el.is_visible():
                btn = el
        except Exception:
            pass

        # 2. Fallback
        if not btn:
            for sel in ["button.btn-submit", "button[type='submit']"]:
                try:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        btn = el
                        break
                except Exception:
                    continue

        # 3. По тексту
        if not btn:
            try:
                buttons = page.query_selector_all("button")
                for b in buttons:
                    txt = (b.text_content() or "").lower()
                    if ("показать" in txt or "результат" in txt) and b.is_visible():
                        btn = b
                        break
            except Exception:
                pass

        if btn:
            btn.scroll_into_view_if_needed()
            _human_delay(0.3, 0.8)
            btn.click()
            if log_fn:
                log_fn("  Нажал 'Показать результаты'")
        else:
            if log_fn:
                log_fn("  Кнопка не найдена")

        _human_delay(3.0, 5.0)

    except Exception as e:
        if log_fn:
            log_fn(f"  -- Кнопка поиска: {e}")


def _go_next_page_click(page: Page, page_num: int, log_fn=None) -> bool:
    """Переходит на следующую страницу кликом по пагинации."""
    try:
        _human_scroll(page)
        _human_delay(0.5, 1.0)

        # Скроллим вниз к пагинации
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        _human_delay(1.0, 2.0)

        pager_link = None

        # 1. По номеру страницы в пагинаторе
        try:
            links = page.query_selector_all(
                'a.paginator__btn, a.page-link, nav a, [class*="paginator"] a'
            )
            for link in links:
                if (link.text_content() or "").strip() == str(page_num) and link.is_visible():
                    pager_link = link
                    break
        except Exception:
            pass

        # 2. Кнопка "Следующая" / ">"
        if not pager_link:
            try:
                next_btn = page.query_selector(
                    'a.paginator__btn--next, a[rel="next"], [class*="next"]'
                )
                if next_btn and next_btn.is_visible():
                    pager_link = next_btn
            except Exception:
                pass

        # 3. По data-page
        if not pager_link:
            try:
                pager_link = page.query_selector(f'a[data-page="{page_num}"]')
            except Exception:
                pass

        # 4. JS fallback
        if not pager_link:
            try:
                clicked = page.evaluate(f"""() => {{
                    var links = document.querySelectorAll('a');
                    for (var i = 0; i < links.length; i++) {{
                        var t = links[i].textContent.trim();
                        if (t === '{page_num}' && links[i].offsetHeight > 0) {{
                            links[i].scrollIntoView({{block: 'center'}});
                            links[i].click();
                            return true;
                        }}
                    }}
                    for (var j = 0; j < links.length; j++) {{
                        var t2 = links[j].textContent.trim().toLowerCase();
                        if ((t2 === '>' || t2 === 'следующая' || t2 === 'далее') && links[j].offsetHeight > 0) {{
                            links[j].scrollIntoView({{block: 'center'}});
                            links[j].click();
                            return true;
                        }}
                    }}
                    return false;
                }}""")
                if clicked:
                    if log_fn:
                        log_fn(f"  Страница {page_num}: JS клик по пагинации")
                    return True
            except Exception:
                pass

        if pager_link:
            pager_link.scroll_into_view_if_needed()
            _human_delay(0.5, 1.0)
            pager_link.click()
            if log_fn:
                log_fn(f"  Страница {page_num}: клик по пагинации")
            return True
        else:
            if log_fn:
                log_fn(f"  Страница {page_num}: пагинация не найдена")
            return False

    except Exception as e:
        if log_fn:
            log_fn(f"  -- Пагинация: {e}")
        return False


def _collect_cards(page: Page) -> list[dict]:
    """Собирает карточки объявлений с текущей страницы."""
    try:
        soup = BeautifulSoup(page.content(), "html.parser")
        results = []

        cards = soup.select("a.a-card__title")
        if not cards:
            cards = soup.select("div[data-id] a[href*='/a/show/']")

        for card in cards:
            href = card.get("href", "")
            title = card.get_text(strip=True)
            if not href:
                continue
            full_url = BASE_URL + href if href.startswith("/") else href

            price = ""
            is_developer = False
            parent = card.find_parent("div", {"data-id": True})
            if parent:
                price_el = parent.select_one(".a-card__price")
                if price_el:
                    price = price_el.get_text(strip=True)

                # Определяем застройщика — метка "Новостройка" (зелёный бейдж)
                parent_text = parent.get_text(separator=" ", strip=True).lower()
                if "новостройка" in parent_text:
                    is_developer = True

                # Проверяем бейджи/метки с классами
                for badge in parent.select("[class*='badge'], [class*='label'], [class*='tag'], "
                                          "[class*='novo'], [class*='new-build']"):
                    badge_text = badge.get_text(strip=True).lower()
                    if "новостройка" in badge_text or "новостройки" in badge_text:
                        is_developer = True
                        break

            results.append({
                "url": full_url, "title": title, "price": price,
                "is_developer": is_developer,
            })

        return results
    except Exception:
        return []


@pw_thread
def get_listings(cfg: dict, log_fn=None, stop_flag=None,
                  captcha_key: str = "") -> list[dict]:
    """
    Собирает объявления со страниц поиска.
    Открывает krisha.kz, кликает фильтры как человек, собирает карточки.
    """
    page = _get_driver()
    max_pages = cfg["krisha"].get("max_pages", 3)
    k = cfg["krisha"]
    listings = []

    # Определяем базовый URL (тип сделки + регион)
    deal = k.get("deal_type", "sale")
    region_alias = k.get("region_alias", "")
    if deal == "rent":
        path = "/arenda/kvartiry/"
    else:
        path = "/prodazha/kvartiry/"
    if region_alias:
        path += f"{region_alias}/"

    search_url = BASE_URL + path

    if log_fn:
        log_fn(f"  Открываю {search_url}")

    try:
        page.goto(search_url)
    except Exception as e:
        if log_fn:
            log_fn(f"  Ошибка загрузки: {e}")
        return listings

    _human_delay(2.0, 4.0)
    _close_popups(page)

    # Проверяем CAPTCHA
    if detect_captcha(page):
        if log_fn:
            log_fn("  CAPTCHA на странице поиска...")
        solve_captcha(page, captcha_key, log_fn=log_fn)
        _human_delay(2.0, 3.0)

    # Применяем фильтры реальными кликами
    if log_fn:
        log_fn("  Применяю фильтры...")
    _apply_filters(page, cfg, log_fn=log_fn)

    _human_delay(1.0, 2.0)
    _human_scroll(page)

    expected_count = _get_results_count(page, log_fn)

    if expected_count == 0 and log_fn:
        log_fn("  ВНИМАНИЕ: счётчик результатов = 0, фильтры могли не примениться")

    _click_search_button(page, log_fn)

    # Проверяем CAPTCHA после клика
    if detect_captcha(page):
        if log_fn:
            log_fn("  CAPTCHA после поиска...")
        solve_captcha(page, captcha_key, log_fn=log_fn)
        _human_delay(2.0, 3.0)

    _close_popups(page)

    if log_fn:
        if expected_count > 0:
            log_fn(f"  Ожидаемое кол-во: {expected_count} квартир")

    # Верификация: считываем кол-во на странице результатов
    page_count = _get_page_results_count(page)
    if expected_count > 0 and page_count > 0:
        if page_count > expected_count * 1.5:
            if log_fn:
                log_fn(f"  ФИЛЬТР СЛЕТЕЛ! Ожидали {expected_count}, на странице {page_count}")
                log_fn(f"  Пробую повторно...")
            page.goto(search_url)
            _human_delay(2.0, 4.0)
            _close_popups(page)
            _apply_filters(page, cfg, log_fn=log_fn)
            _human_delay(1.0, 2.0)
            expected_count = _get_results_count(page, log_fn)
            _click_search_button(page, log_fn)
            _close_popups(page)
            page_count = _get_page_results_count(page)
            if expected_count > 0 and page_count > 0 and page_count > expected_count * 1.5:
                if log_fn:
                    log_fn(f"  Фильтр снова слетел ({page_count} vs {expected_count}). Продолжаю.")
        elif page_count != expected_count and log_fn:
            log_fn(f"  Кол-во на странице: {page_count} (кнопка показывала {expected_count})")

    # Собираем карточки с первой страницы
    cards = _collect_cards(page)
    if cards:
        listings.extend(cards)
        if log_fn:
            log_fn(f"  Страница 1/{max_pages}: {len(cards)} карточек")
    else:
        if log_fn:
            log_fn("  Страница 1: объявления не найдены")
        return listings

    # Остальные страницы
    for page_num in range(2, max_pages + 1):
        if stop_flag and stop_flag():
            break

        _human_delay(2.0, 4.0)
        _human_scroll(page)

        if not _go_next_page_click(page, page_num, log_fn):
            break

        _human_delay(3.0, 5.0)
        _close_popups(page)

        if detect_captcha(page):
            solve_captcha(page, captcha_key, log_fn=log_fn)
            _human_delay(2.0, 3.0)

        current_count = _get_page_results_count(page)
        if expected_count > 0 and current_count > 0:
            if current_count > expected_count * 1.5:
                if log_fn:
                    log_fn(f"  ФИЛЬТР СЛЕТЕЛ! Было {expected_count}, стало {current_count}. Стоп.")
                break
            elif current_count != expected_count:
                if log_fn:
                    log_fn(f"  Кол-во изменилось: {expected_count} -> {current_count}")

        cards = _collect_cards(page)
        if cards:
            listings.extend(cards)
            if log_fn:
                log_fn(f"  Страница {page_num}/{max_pages}: {len(cards)} карточек")
        else:
            if log_fn:
                log_fn(f"  Страница {page_num}: пусто")
            break

    return listings


# ─── Извлечение телефона ───────────────────────────────────────

def _click_listing_card(page: Page, listing_url: str, log_fn=None) -> bool:
    """Кликает по карточке объявления на странице результатов."""
    try:
        from urllib.parse import urlparse
        path = urlparse(listing_url).path

        link = page.query_selector(f'a[href="{path}"]')
        if not link:
            link = page.query_selector(f'a[href*="{path}"]')

        if not link:
            try:
                ad_id = path.rstrip('/').split('/')[-1]
                if ad_id.isdigit():
                    container = page.query_selector(f'div[data-id="{ad_id}"]')
                    if container:
                        link = container.query_selector('a')
            except Exception:
                pass

        if link and link.is_visible():
            link.scroll_into_view_if_needed()
            _human_delay(0.5, 1.5)
            link.click()
            if log_fn:
                log_fn("  Кликнул по карточке")
            return True

    except Exception:
        pass
    return False


def _go_back_to_results(page: Page, log_fn=None):
    """Возвращается на страницу результатов через кнопку 'Назад' браузера."""
    try:
        _human_delay(1.0, 2.0)
        page.go_back()
        _human_delay(2.0, 3.5)
        _close_popups(page)
    except Exception as e:
        if log_fn:
            log_fn(f"  -- Ошибка возврата: {e}")


def _click_show_phone(page: Page, log_fn=None) -> bool:
    """Кликает кнопку 'Показать телефон' на krisha.kz."""

    # 0. Проверяем — может телефон уже виден
    try:
        visible_phone = page.evaluate("""() => {
            var phones = document.querySelectorAll('.offer__contacts-phones p, .a-phones p, [class*="phone"] p');
            for (var i = 0; i < phones.length; i++) {
                var t = phones[i].textContent.trim();
                if (/^\\+?[78]\\d{10}/.test(t)) {
                    return t;
                }
            }
            return null;
        }""")
        if visible_phone:
            if log_fn:
                log_fn(f"  [phone-btn] Телефон уже виден: {visible_phone}")
            return True
    except Exception:
        pass

    # 1. Убираем всё что может перекрывать кнопку
    _close_popups(page)
    _human_delay(0.3, 0.5)
    try:
        page.evaluate("""() => {
            document.querySelectorAll('[class*="modal"], [class*="popup"], [class*="dialog"], [role="dialog"]').forEach(function(m) {
                var t = (m.textContent || '').toLowerCase();
                if (t.indexOf('продлить') !== -1 || t.indexOf('оплатить') !== -1 ||
                    t.indexOf('к оплате') !== -1 || t.indexOf('номер карты') !== -1 ||
                    t.indexOf('cvv') !== -1 || t.indexOf('заметк') !== -1) {
                    try { m.style.display = 'none'; } catch(e) {}
                }
            });
            document.querySelectorAll('.modal-backdrop, [class*="backdrop"], [class*="overlay"]').forEach(function(el) {
                try { el.style.display = 'none'; } catch(e) {}
            });
            document.body.classList.remove('modal-open', 'no-scroll', 'popup-open');
            document.body.style.overflow = '';
            document.documentElement.style.overflow = '';
        }""")
    except Exception:
        pass
    _human_delay(0.2, 0.4)

    # 2. Главный способ — JS клик по button.show-phones
    try:
        result = page.evaluate("""() => {
            var btn = document.querySelector('button.show-phones');
            if (btn) {
                btn.scrollIntoView({behavior: 'smooth', block: 'center'});
                return 'found';
            }
            return 'not_found';
        }""")
        if result == 'found':
            _human_delay(0.5, 1.0)
            try:
                btn = page.query_selector("button.show-phones")
                if btn:
                    btn.click()
            except Exception:
                page.evaluate("document.querySelector('button.show-phones').click()")
            if log_fn:
                log_fn("  [phone-btn] button.show-phones -> клик")
            return True
    except Exception:
        pass

    # 3. Fallback — ищем внутри .a-phones контейнера
    try:
        result = page.evaluate("""() => {
            var container = document.querySelector('.a-phones, .offer__contacts');
            if (!container) return null;
            var btns = container.querySelectorAll('button, a');
            var blacklist = ['оплатить', 'продлить', 'написать', 'сообщение', 'номер карты'];
            for (var i = 0; i < btns.length; i++) {
                var el = btns[i];
                var t = (el.textContent || '').trim().toLowerCase();
                var skip = false;
                for (var b = 0; b < blacklist.length; b++) {
                    if (t.indexOf(blacklist[b]) !== -1) { skip = true; break; }
                }
                if (skip) continue;
                if (t.indexOf('показать') !== -1 || t.indexOf('телефон') !== -1 ||
                    el.closest('.a-phones__hidden')) {
                    el.scrollIntoView({behavior: 'smooth', block: 'center'});
                    el.click();
                    return 'clicked';
                }
            }
            return null;
        }""")
        if result == 'clicked':
            if log_fn:
                log_fn("  [phone-btn] fallback внутри .a-phones -> клик")
            return True
    except Exception:
        pass

    # 4. Широкий JS поиск
    try:
        clicked = page.evaluate("""() => {
            var keywords = ['показать телефон', 'показать номер'];
            var blacklist = ['оплатить', 'продлить', 'написать', 'сообщение', 'номер карты'];
            var all = document.querySelectorAll('button, a');
            for (var i = 0; i < all.length; i++) {
                var el = all[i];
                if (el.offsetHeight <= 0 && el.offsetWidth <= 0) continue;
                var t = (el.textContent || '').trim().toLowerCase();
                var skip = false;
                for (var b = 0; b < blacklist.length; b++) {
                    if (t.indexOf(blacklist[b]) !== -1) { skip = true; break; }
                }
                if (skip) continue;
                if (el.closest('[class*="modal"], [role="dialog"]')) continue;
                for (var k = 0; k < keywords.length; k++) {
                    if (t.indexOf(keywords[k]) !== -1) {
                        el.scrollIntoView({behavior: 'smooth', block: 'center'});
                        el.click();
                        return true;
                    }
                }
            }
            return false;
        }""")
        if clicked:
            if log_fn:
                log_fn("  [phone-btn] JS широкий поиск -> клик")
            return True
    except Exception:
        pass

    # Не найдена
    if log_fn:
        try:
            from datetime import datetime
            html = page.content()
            filename = f"debug_no_phone_btn_{datetime.now().strftime('%H%M%S')}.html"
            filepath = os.path.join(APP_DIR, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html)
            log_fn(f"  [phone-btn] НЕ НАЙДЕНА. HTML сохранён: {filename}")

            contacts_html = page.evaluate("""() => {
                var c = document.querySelector('.offer__contacts, .a-phones');
                return c ? c.innerHTML.substring(0, 500) : 'контейнер не найден';
            }""")
            log_fn(f"  [phone-btn] DOM контактов: {contacts_html[:200]}...")
        except Exception as e:
            log_fn(f"  [phone-btn] Кнопка не найдена (ошибка сохранения HTML: {e})")
    return False


def _extract_phone_from_page(page: Page, log_fn=None) -> str | None:
    """Извлекает номер телефона со страницы после клика 'Показать телефон'."""

    for attempt in range(3):

        # 1. ТОЧНЫЙ селектор krisha.kz
        try:
            phone_text = page.evaluate("""() => {
                var container = document.querySelector('.offer__contacts-phones');
                if (container) {
                    var p = container.querySelector('p');
                    if (p) return p.textContent.trim();
                }
                return null;
            }""")
            if phone_text and re.search(r"\d{7,}", phone_text.replace(" ", "")):
                phone = normalize_phone(phone_text)
                if phone and len(phone) >= 11:
                    if log_fn:
                        log_fn(f"  [extract] .offer__contacts-phones p -> {phone}")
                    return phone
        except Exception:
            pass

        # 2. Через BeautifulSoup
        soup = BeautifulSoup(page.content(), "html.parser")
        container = soup.select_one(".offer__contacts-phones")
        if container:
            first_p = container.find("p")
            if first_p:
                text = first_p.get_text(strip=True)
                if re.search(r"\d{7,}", text.replace(" ", "")):
                    phone = normalize_phone(text)
                    if phone and len(phone) >= 11:
                        if log_fn:
                            log_fn(f"  [extract] BS .offer__contacts-phones p -> {phone}")
                        return phone

        # 3. tel: ссылки
        for link in soup.select("a[href^='tel:']"):
            raw = link.get("href", "").replace("tel:", "").strip()
            phone = normalize_phone(raw)
            if phone and len(phone) >= 11:
                if log_fn:
                    log_fn(f"  [extract] tel: ссылка -> {phone}")
                return phone

        # 4. data-phone атрибуты
        for attr in ["data-phone", "data-phone-number", "data-value"]:
            for el in soup.select(f"[{attr}]"):
                raw = el.get(attr, "")
                if raw and re.search(r"\d{7,}", raw.replace(" ", "")):
                    phone = normalize_phone(raw)
                    if phone and len(phone) >= 11:
                        if log_fn:
                            log_fn(f"  [extract] {attr} -> {phone}")
                        return phone

        # 5. Другие контейнеры телефона
        phone_selectors = [
            ".offer__contacts-loaded p",
            ".offer__contacts-phones__number",
            ".offer__advert-short-info__phone",
            ".phones__item",
            ".phone-number",
            "[class*='contacts-phones'] p",
        ]
        for sel in phone_selectors:
            for el in soup.select(sel):
                text = el.get_text(strip=True)
                if "показать" in text.lower() or "сообщ" in text.lower():
                    continue
                if re.search(r"\d{3}", text):
                    phone = normalize_phone(text)
                    if phone and len(phone) >= 11:
                        if log_fn:
                            log_fn(f"  [extract] CSS '{sel}' -> {phone}")
                        return phone

        # 6. JS — ищем видимые номера
        try:
            js_phone = page.evaluate("""() => {
                var telLinks = document.querySelectorAll('a[href^="tel:"]');
                for (var i = 0; i < telLinks.length; i++) {
                    var href = telLinks[i].href.replace('tel:', '').trim();
                    if (href.length >= 10) return href;
                }
                var phoneRe = /(?:\\+?7|8)[\\s\\-]?\\(?\\d{3}\\)?[\\s\\-]?\\d{3}[\\s\\-]?\\d{2}[\\s\\-]?\\d{2}/;
                var containers = document.querySelectorAll(
                    '.offer__contacts-phones, .offer__contacts-loaded, [class*="phone"]'
                );
                for (var j = 0; j < containers.length; j++) {
                    var t = containers[j].textContent || '';
                    if (t.toLowerCase().indexOf('показать') !== -1) continue;
                    var m = t.match(phoneRe);
                    if (m) return m[0];
                }
                return null;
            }""")
            if js_phone:
                phone = normalize_phone(js_phone)
                if phone and len(phone) >= 11:
                    if log_fn:
                        log_fn(f"  [extract] JS -> {phone}")
                    return phone
        except Exception:
            pass

        # 7. Regex по body
        try:
            page_text = page.evaluate("document.body.textContent")
            phones = re.findall(
                r"(?:\+?7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}",
                page_text,
            )
            if phones:
                phone = normalize_phone(phones[0])
                if phone and len(phone) >= 11:
                    if log_fn:
                        log_fn(f"  [extract] regex body -> {phone}")
                    return phone
        except Exception:
            pass

        # Ждём AJAX
        if attempt < 2:
            if log_fn:
                log_fn(f"  [extract] Попытка {attempt+1}/3 — номер пока не появился, жду...")
            _human_delay(1.5, 2.5)

    if log_fn:
        log_fn("  [extract] Номер не найден после 3 попыток")
    return None


@pw_thread
def extract_phone(listing_url: str, log_fn=None,
                   stop_flag=None, captcha_key: str = "") -> str | None:
    """
    Открывает объявление напрямую, забирает телефон, возвращается назад.
    """
    page = _get_driver()

    try:
        if stop_flag and stop_flag():
            return None

        if log_fn:
            log_fn(f"  [1/6] Открываю объявление...")

        # ШАГ 1: Открываем объявление напрямую
        try:
            page.goto(listing_url)
            time.sleep(4.0)
        except Exception as e:
            if log_fn:
                log_fn(f"  ❌ Ошибка загрузки: {e}")
            return None

        if log_fn:
            log_fn("  [2/6] Объявление открыто, закрываю попапы...")

        # ШАГ 2: АГРЕССИВНОЕ закрытие ВСЕХ попапов
        for close_attempt in range(10):
            if stop_flag and stop_flag():
                return None

            closed = page.evaluate("""() => {
                var closed = false;

                var modals = document.querySelectorAll(
                    '[class*="modal"], [class*="Modal"], [class*="popup"], [class*="Popup"], ' +
                    '[class*="dialog"], [class*="Dialog"], [role="dialog"], [role="alertdialog"], ' +
                    '[class*="overlay"], [class*="backdrop"], [class*="note"], [class*="Note"], ' +
                    '[class*="hint"], [class*="Hint"]'
                );
                for (var i = 0; i < modals.length; i++) {
                    try {
                        modals[i].remove();
                        closed = true;
                    } catch(e) {
                        try {
                            modals[i].style.display = 'none';
                            closed = true;
                        } catch(e2) {}
                    }
                }

                var closers = document.querySelectorAll(
                    '[class*="close"], [class*="Close"], ' +
                    '[aria-label*="lose"], [aria-label*="Закрыть"], ' +
                    'button svg, .modal-close, .popup-close'
                );
                for (var j = 0; j < closers.length; j++) {
                    if (closers[j].offsetHeight > 0) {
                        try {
                            closers[j].click();
                            closed = true;
                        } catch(e) {}
                    }
                }

                document.body.style.overflow = '';
                document.body.style.position = '';
                document.documentElement.style.overflow = '';
                document.body.classList.remove('modal-open', 'no-scroll', 'popup-open');

                return closed;
            }""")

            if closed:
                if log_fn:
                    log_fn(f"    Закрыл попап #{close_attempt + 1}")
                time.sleep(0.5)
            else:
                break

        if log_fn:
            log_fn("  [3/6] Скроллю к контактам...")

        # ШАГ 3: Медленный скролл к секции контактов
        if stop_flag and stop_flag():
            return None

        for _ in range(3):
            page.evaluate("window.scrollBy(0, 300)")
            time.sleep(0.7)

        page.evaluate("""() => {
            var contacts = document.querySelector('.offer__contacts, .a-phones, [class*="contact"]');
            if (contacts) {
                contacts.scrollIntoView({behavior: 'smooth', block: 'center'});
            }
        }""")
        time.sleep(2.0)

        if log_fn:
            log_fn("  [4/6] Ищу кнопку 'Показать телефон'...")

        # Кулдаун + rate-limit перед кликом — ждём чтобы рекапча была свежая
        from captcha_solver import (
            _last_captcha_solve_time, _CAPTCHA_COOLDOWN_SEC,
            _solve_timestamps, _MAX_SOLVES_PER_WINDOW, _RATE_WINDOW_SEC,
        )
        now = time.time()
        # Rate-limit: макс N решений за окно
        active = [t for t in _solve_timestamps if now - t < _RATE_WINDOW_SEC]
        if len(active) >= _MAX_SOLVES_PER_WINDOW:
            oldest = active[0]
            wait_sec = int(_RATE_WINDOW_SEC - (now - oldest)) + 5
            if wait_sec > 0:
                if log_fn:
                    log_fn(f"  -- Rate-limit: жду {wait_sec} сек перед кликом...")
                time.sleep(wait_sec)
        # Кулдаун между попытками
        elapsed = time.time() - _last_captcha_solve_time
        if _last_captcha_solve_time > 0 and elapsed < _CAPTCHA_COOLDOWN_SEC:
            wait_sec = int(_CAPTCHA_COOLDOWN_SEC - elapsed)
            if log_fn:
                log_fn(f"  -- Кулдаун: жду {wait_sec} сек перед кликом...")
            time.sleep(_CAPTCHA_COOLDOWN_SEC - elapsed)

        # ШАГ 4: Ищем кнопку "Показать телефон"
        if stop_flag and stop_flag():
            return None

        phone_btn_found = False

        # Способ 1: Прямой JS клик
        try:
            clicked = page.evaluate("""() => {
                var btn = document.querySelector('button.show-phones');
                if (btn && btn.offsetHeight > 0) {
                    btn.scrollIntoView({behavior: 'smooth', block: 'center'});
                    btn.click();
                    return 'clicked';
                }

                var contacts = document.querySelector('.offer__contacts, .a-phones');
                if (contacts) {
                    var btns = contacts.querySelectorAll('button, a');
                    for (var i = 0; i < btns.length; i++) {
                        var t = btns[i].textContent.toLowerCase();
                        if (t.indexOf('показать') !== -1 && t.indexOf('телефон') !== -1) {
                            btns[i].scrollIntoView({behavior: 'smooth', block: 'center'});
                            btns[i].click();
                            return 'clicked';
                        }
                    }
                }

                var allBtns = document.querySelectorAll('button, a');
                for (var j = 0; j < allBtns.length; j++) {
                    var txt = allBtns[j].textContent.toLowerCase();
                    if (txt.indexOf('показать') !== -1 && txt.indexOf('телефон') !== -1) {
                        if (!allBtns[j].closest('[class*="modal"]')) {
                            allBtns[j].scrollIntoView({behavior: 'smooth', block: 'center'});
                            allBtns[j].click();
                            return 'clicked';
                        }
                    }
                }

                return 'not_found';
            }""")

            if clicked == 'clicked':
                phone_btn_found = True
                if log_fn:
                    log_fn("  ✓ Кнопка найдена и кликнута (JS)")
                time.sleep(3.0)
        except Exception as e:
            if log_fn:
                log_fn(f"    JS клик не сработал: {e}")

        # Способ 2: Playwright fallback
        if not phone_btn_found:
            try:
                time.sleep(1.0)
                buttons = page.query_selector_all("button")
                for btn in buttons:
                    try:
                        if btn.is_visible():
                            text = (btn.text_content() or "").lower()
                            if "показать" in text and "телефон" in text:
                                btn.scroll_into_view_if_needed()
                                time.sleep(1.0)
                                btn.click()
                                phone_btn_found = True
                                if log_fn:
                                    log_fn("  ✓ Кнопка найдена и кликнута (Playwright)")
                                time.sleep(3.0)
                                break
                    except Exception:
                        continue
            except Exception as e:
                if log_fn:
                    log_fn(f"    Playwright клик не сработал: {e}")

        if not phone_btn_found:
            if log_fn:
                log_fn("  ⚠️ Кнопка НЕ НАЙДЕНА - сохраняю HTML для анализа...")
                try:
                    from datetime import datetime
                    html = page.content()
                    filename = f"debug_no_button_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                    filepath = os.path.join(APP_DIR, filename)
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(html)
                    log_fn(f"    HTML сохранён: {filename}")
                except Exception as e:
                    log_fn(f"    Ошибка сохранения HTML: {e}")

        if log_fn:
            log_fn("  [5/6] Извлекаю номер телефона...")

        # ШАГ 5: Извлекаем номер телефона (сначала пробуем без решения капчи)
        if stop_flag and stop_flag():
            return None

        time.sleep(1.0)
        phone = _extract_phone_from_page(page, log_fn=log_fn)

        # Проверяем заглушку krisha.kz — +76400058899 означает что телефон не раскрыт
        PLACEHOLDER_PHONE = "+76400058899"

        # Если телефон найден и это не заглушка — отлично, капча не нужна
        if phone and phone != PLACEHOLDER_PHONE:
            pass  # Всё ок, идём дальше
        else:
            # Телефон не найден или заглушка — пробуем решить капчу
            if detect_captcha(page):
                if log_fn:
                    if phone == PLACEHOLDER_PHONE:
                        log_fn("  ⚠️ Получена заглушка — пробую решить капчу...")
                    else:
                        log_fn("  ⚠️ CAPTCHA при раскрытии телефона...")
                solved = solve_captcha(page, captcha_key, log_fn=log_fn)
                if solved:
                    _human_delay(2.0, 3.0)
                    # После решения капчи повторно кликаем "Показать телефон"
                    try:
                        page.evaluate("""() => {
                            var btns = document.querySelectorAll('button, a');
                            for (var i = 0; i < btns.length; i++) {
                                var t = btns[i].textContent.toLowerCase();
                                if (t.indexOf('показать') !== -1 && t.indexOf('телефон') !== -1) {
                                    btns[i].click();
                                    return true;
                                }
                            }
                            return false;
                        }""")
                        time.sleep(3.0)
                    except Exception:
                        pass
                    phone2 = _extract_phone_from_page(page, log_fn=log_fn)
                    if phone2 and phone2 != PLACEHOLDER_PHONE:
                        phone = phone2
                    else:
                        phone = None  # Капча решена но телефон не появился
                else:
                    if phone == PLACEHOLDER_PHONE:
                        phone = None  # Заглушка + капча не решена
            else:
                if phone == PLACEHOLDER_PHONE:
                    phone = None  # Заглушка без капчи — пропускаем

        if phone:
            if log_fn:
                log_fn(f"  ✅ [6/6] Номер найден: {phone}")
        else:
            if log_fn:
                log_fn("  ❌ [6/6] Номер НЕ найден (заглушка или капча)")

        # Возвращаемся назад
        if log_fn:
            log_fn("  Возвращаюсь назад...")

        time.sleep(1.0)
        page.go_back()
        time.sleep(3.0)

        return phone

    except Exception as e:
        if log_fn:
            log_fn(f"  ❌ ОШИБКА: {e}")
        try:
            page.go_back()
            time.sleep(2.0)
        except Exception:
            pass
        return None
