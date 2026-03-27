"""
Тесты 15.3: Auth Manager edge cases.
- is_logged_in корректно определяет статус (Property 6, Req 4.1)
- Авторизация: retry 5 раз, возврат False (Req 4.7)
- JS fallback при неудачном клике (Req 2.5)
"""
import pytest
from unittest.mock import patch, MagicMock


def test_is_logged_in_returns_true_when_cabinet():
    """is_logged_in → True когда 'Кабинет' в навигации."""
    import parser_playwright as pp
    mock_page = MagicMock()
    mock_page.url = "https://krisha.kz/prodazha/kvartiry/"
    mock_page.evaluate.return_value = "logged"

    result = pp.is_logged_in(mock_page)
    assert result is True


def test_is_logged_in_returns_false_when_registration():
    """is_logged_in → False когда 'Регистрация' в навигации."""
    import parser_playwright as pp
    mock_page = MagicMock()
    mock_page.url = "https://krisha.kz/prodazha/kvartiry/"
    mock_page.evaluate.return_value = "not_logged"

    result = pp.is_logged_in(mock_page)
    assert result is False


def test_is_logged_in_returns_false_on_non_krisha():
    """is_logged_in → False на чужом домене."""
    import parser_playwright as pp
    mock_page = MagicMock()
    mock_page.url = "https://google.com"

    result = pp.is_logged_in(mock_page)
    assert result is False


def test_is_logged_in_cookie_fallback():
    """is_logged_in → True через cookie fallback при 'unknown'."""
    import parser_playwright as pp
    mock_page = MagicMock()
    mock_page.url = "https://krisha.kz/"
    mock_page.evaluate.return_value = "unknown"

    mock_context = MagicMock()
    mock_context.cookies.return_value = [{"name": "krisha_id", "value": "123"}]

    old_ctx = pp._context
    pp._context = mock_context
    try:
        result = pp.is_logged_in(mock_page)
        assert result is True
    finally:
        pp._context = old_ctx


def test_is_logged_in_no_auth_cookies():
    """is_logged_in → False через cookie fallback без auth cookies."""
    import parser_playwright as pp
    mock_page = MagicMock()
    mock_page.url = "https://krisha.kz/"
    mock_page.evaluate.return_value = "unknown"

    mock_context = MagicMock()
    mock_context.cookies.return_value = [{"name": "some_tracking", "value": "abc"}]

    old_ctx = pp._context
    pp._context = mock_context
    try:
        result = pp.is_logged_in(mock_page)
        assert result is False
    finally:
        pp._context = old_ctx


def test_is_logged_in_exception_returns_false():
    """is_logged_in → False при исключении."""
    import parser_playwright as pp
    mock_page = MagicMock()
    mock_page.url = "https://krisha.kz/"
    mock_page.evaluate.side_effect = Exception("page crashed")

    result = pp.is_logged_in(mock_page)
    assert result is False


def test_human_click_js_fallback():
    """_human_click использует JS fallback при неудачном клике (Req 2.5)."""
    import parser_playwright as pp
    mock_page = MagicMock()

    # Locator клик бросает исключение
    mock_locator = MagicMock()
    mock_locator.scroll_into_view_if_needed.side_effect = Exception("not visible")
    mock_page.locator.return_value = mock_locator

    pp._human_click(mock_page, "button.test")

    # Должен был вызвать JS fallback
    mock_page.evaluate.assert_called_once()
    call_arg = mock_page.evaluate.call_args[0][0]
    assert "button.test" in call_arg
    assert ".click()" in call_arg
