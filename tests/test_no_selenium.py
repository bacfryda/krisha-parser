"""
Тесты 15.4: Проверка отсутствия Selenium.
- Нет import selenium / undetected_chromedriver в parser_playwright.py (Req 12.1)
- CHROME_WINDOW_MARKER == "KRISHA_PARSER_CHROME_7x9k2" (Req 11.2)
- _driver доступен как глобальная переменная (Req 11.3)
- Обратная совместимость публичного API (Property 13, Req 11.1, 11.4)
"""
import pytest
import os
import inspect


def test_no_selenium_imports():
    """parser_playwright.py не содержит import selenium."""
    filepath = os.path.join(os.path.dirname(__file__), "..", "parser_playwright.py")
    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()
    assert "import selenium" not in source
    assert "from selenium" not in source


def test_no_undetected_chromedriver_imports():
    """parser_playwright.py не содержит import undetected_chromedriver."""
    filepath = os.path.join(os.path.dirname(__file__), "..", "parser_playwright.py")
    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()
    assert "import undetected_chromedriver" not in source
    assert "from undetected_chromedriver" not in source


def test_chrome_window_marker_value():
    """CHROME_WINDOW_MARKER == 'KRISHA_PARSER_CHROME_7x9k2'."""
    import parser_playwright as pp
    assert pp.CHROME_WINDOW_MARKER == "KRISHA_PARSER_CHROME_7x9k2"


def test_driver_global_exists():
    """_driver доступен как глобальная переменная."""
    import parser_playwright as pp
    assert hasattr(pp, "_driver")


def test_public_api_functions_exist():
    """Все публичные функции доступны для импорта (Req 11.1)."""
    import parser_playwright as pp

    required_functions = [
        "get_listings",
        "extract_phone",
        "close_driver",
        "_get_driver",
        "is_logged_in",
        "open_login_page",
        "login_krisha",
        "type_in_focused",
        "save_session_if_logged",
    ]
    for fn_name in required_functions:
        assert hasattr(pp, fn_name), f"Функция {fn_name} не найдена"
        assert callable(getattr(pp, fn_name)), f"{fn_name} не callable"


def test_public_api_signatures():
    """Сигнатуры публичных функций совместимы с gui.py (Req 11.4)."""
    import parser_playwright as pp

    # get_listings(cfg, log_fn, stop_flag, captcha_key)
    sig = inspect.signature(pp.get_listings)
    params = list(sig.parameters.keys())
    assert "cfg" in params
    assert "log_fn" in params
    assert "stop_flag" in params
    assert "captcha_key" in params

    # extract_phone(listing_url, log_fn, stop_flag, captcha_key)
    sig = inspect.signature(pp.extract_phone)
    params = list(sig.parameters.keys())
    assert "listing_url" in params
    assert "log_fn" in params

    # is_logged_in(driver=None)
    sig = inspect.signature(pp.is_logged_in)
    params = sig.parameters
    assert "driver" in params
    assert params["driver"].default is None

    # close_driver() — без аргументов
    sig = inspect.signature(pp.close_driver)
    assert len(sig.parameters) == 0


def test_captcha_solver_no_selenium():
    """captcha_solver.py не содержит import selenium."""
    filepath = os.path.join(os.path.dirname(__file__), "..", "captcha_solver.py")
    with open(filepath, "r", encoding="utf-8") as f:
        source = f.read()
    assert "import selenium" not in source
    assert "from selenium" not in source
    assert "By." not in source
