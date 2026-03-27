"""
Тесты для Human Behavior Module.
- Property 2: _human_delay выдерживает заданный диапазон (Req 2.1)
- Property 3: _human_scroll скроллит в допустимом диапазоне (Req 2.2)
"""
import pytest
import time
from unittest.mock import MagicMock, patch


def test_human_delay_within_range():
    """_human_delay выдерживает заданный диапазон."""
    import parser_playwright as pp

    min_s, max_s = 0.01, 0.05
    start = time.time()
    pp._human_delay(min_s, max_s)
    elapsed = time.time() - start

    assert elapsed >= min_s * 0.9  # небольшой допуск
    assert elapsed <= max_s + 0.1  # допуск на overhead


def test_human_delay_default_params():
    """_human_delay с дефолтными параметрами не падает."""
    import parser_playwright as pp
    with patch("parser_playwright.time.sleep") as mock_sleep:
        pp._human_delay()
    mock_sleep.assert_called_once()
    delay = mock_sleep.call_args[0][0]
    assert 1.0 <= delay <= 3.0


def test_human_scroll_calls_evaluate():
    """_human_scroll вызывает page.evaluate с window.scrollBy."""
    import parser_playwright as pp
    mock_page = MagicMock()

    with patch("parser_playwright.time.sleep"):
        pp._human_scroll(mock_page)

    # Первый вызов — scrollBy вниз
    first_call = mock_page.evaluate.call_args_list[0][0][0]
    assert "window.scrollBy" in first_call


def test_human_scroll_exception_safe():
    """_human_scroll не бросает исключение при ошибке."""
    import parser_playwright as pp
    mock_page = MagicMock()
    mock_page.evaluate.side_effect = Exception("page error")

    # Не должен бросить
    pp._human_scroll(mock_page)
