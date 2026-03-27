"""
Тесты 15.1: Инициализация и восстановление браузера.
- stealth_sync вызывается при создании страницы (Req 1.2)
- Аргументы запуска Chromium корректны (Req 1.3, 1.5)
- Восстановление после падения браузера (Req 1.7)
- _get_driver() идемпотентность (Property 1, Req 1.6)
"""
import pytest
from unittest.mock import patch, MagicMock, PropertyMock


@pytest.fixture(autouse=True)
def _reset_globals():
    """Сбрасываем глобальное состояние перед каждым тестом."""
    import parser_playwright as pp
    pp._playwright = None
    pp._browser = None
    pp._context = None
    pp._page = None
    pp._driver = None
    yield
    pp._playwright = None
    pp._browser = None
    pp._context = None
    pp._page = None
    pp._driver = None


def _build_mocks():
    """Создаёт полный набор моков для Playwright."""
    mock_pw = MagicMock()
    mock_browser = MagicMock()
    mock_context = MagicMock()
    mock_page = MagicMock()

    mock_pw.chromium.launch.return_value = mock_browser
    mock_browser.new_context.return_value = mock_context
    mock_context.new_page.return_value = mock_page
    mock_page.url = "about:blank"

    return mock_pw, mock_browser, mock_context, mock_page


@patch("parser_playwright.sync_playwright")
@patch("parser_playwright._load_storage_state", return_value=None)
def test_stealth_sync_called_on_page_creation(mock_storage, mock_sp):
    """stealth_sync вызывается при создании страницы (Req 1.2)."""
    mock_pw, mock_browser, mock_context, mock_page = _build_mocks()
    mock_sp.return_value.start.return_value = mock_pw

    import parser_playwright as pp
    mock_stealth_instance = MagicMock()
    mock_stealth_cls = MagicMock(return_value=mock_stealth_instance)
    with patch.dict("sys.modules", {"playwright_stealth": MagicMock(Stealth=mock_stealth_cls)}):
        page = pp._get_driver()

    mock_stealth_instance.apply_stealth_sync.assert_called_once_with(mock_page)
    assert page is mock_page


@patch("parser_playwright.sync_playwright")
@patch("parser_playwright._load_storage_state", return_value=None)
def test_chromium_launch_args(mock_storage, mock_sp):
    """Аргументы запуска Chromium содержат антидетект флаги (Req 1.3, 1.5)."""
    mock_pw, mock_browser, mock_context, mock_page = _build_mocks()
    mock_sp.return_value.start.return_value = mock_pw

    import parser_playwright as pp
    with patch.dict("sys.modules", {"playwright_stealth": MagicMock()}):
        pp._get_driver()

    call_kwargs = mock_pw.chromium.launch.call_args
    args_list = call_kwargs.kwargs.get("args", [])

    assert "--no-sandbox" in args_list
    assert "--disable-blink-features=AutomationControlled" in args_list
    assert "--disable-infobars" in args_list
    assert call_kwargs.kwargs.get("headless") is False
    assert call_kwargs.kwargs.get("channel") == "chrome"


@patch("parser_playwright.sync_playwright")
@patch("parser_playwright._load_storage_state", return_value=None)
def test_recovery_after_browser_crash(mock_storage, mock_sp):
    """Восстановление после падения браузера (Req 1.7)."""
    mock_pw, mock_browser, mock_context, mock_page = _build_mocks()
    mock_sp.return_value.start.return_value = mock_pw

    import parser_playwright as pp
    dead_page = MagicMock()
    type(dead_page).url = PropertyMock(side_effect=Exception("browser crashed"))
    pp._page = dead_page

    with patch.dict("sys.modules", {"playwright_stealth": MagicMock()}):
        page = pp._get_driver()

    assert page is mock_page
    assert pp._page is mock_page


@patch("parser_playwright.sync_playwright")
@patch("parser_playwright._load_storage_state", return_value=None)
def test_get_driver_idempotent(mock_storage, mock_sp):
    """_get_driver() идемпотентность — повторный вызов возвращает тот же объект (Req 1.6)."""
    mock_pw, mock_browser, mock_context, mock_page = _build_mocks()
    mock_sp.return_value.start.return_value = mock_pw

    import parser_playwright as pp
    with patch.dict("sys.modules", {"playwright_stealth": MagicMock()}):
        page1 = pp._get_driver()
        page2 = pp._get_driver()

    assert page1 is page2
    mock_pw.chromium.launch.assert_called_once()


@patch("parser_playwright.sync_playwright")
@patch("parser_playwright._load_storage_state", return_value=None)
def test_driver_alias_set(mock_storage, mock_sp):
    """_driver устанавливается как alias на _page (Req 11.2, 11.3)."""
    mock_pw, mock_browser, mock_context, mock_page = _build_mocks()
    mock_sp.return_value.start.return_value = mock_pw

    import parser_playwright as pp
    with patch.dict("sys.modules", {"playwright_stealth": MagicMock()}):
        pp._get_driver()

    assert pp._driver is pp._page


@patch("parser_playwright.sync_playwright")
@patch("parser_playwright._load_storage_state", return_value=None)
def test_chrome_window_marker_set(mock_storage, mock_sp):
    """Маркер CHROME_WINDOW_MARKER устанавливается в title (Req 10.1)."""
    mock_pw, mock_browser, mock_context, mock_page = _build_mocks()
    mock_sp.return_value.start.return_value = mock_pw

    import parser_playwright as pp
    with patch.dict("sys.modules", {"playwright_stealth": MagicMock()}):
        pp._get_driver()

    calls = [str(c) for c in mock_page.evaluate.call_args_list]
    marker_calls = [c for c in calls if pp.CHROME_WINDOW_MARKER in c]
    assert len(marker_calls) > 0, "CHROME_WINDOW_MARKER не установлен через page.evaluate"
