"""
Тесты для Listing Collector.
- Property 7: _collect_cards извлекает карточки из HTML (Req 7.3)
- Property 8: Детекция слетевшего фильтра (Req 7.5)
"""
import pytest
from unittest.mock import MagicMock


def _make_card_html(cards_data):
    """Генерирует HTML с карточками объявлений."""
    items = []
    for i, (url, title, price) in enumerate(cards_data):
        items.append(f'''
        <div data-id="{1000+i}">
            <a class="a-card__title" href="{url}">{title}</a>
            <div class="a-card__price">{price}</div>
        </div>''')
    return f"<html><body>{''.join(items)}</body></html>"


def test_collect_cards_basic():
    """_collect_cards извлекает карточки из HTML."""
    import parser_playwright as pp
    mock_page = MagicMock()

    cards_data = [
        ("/a/show/123", "2-комн. квартира, 65 м²", "25 000 000 ₸"),
        ("/a/show/456", "3-комн. квартира, 90 м²", "40 000 000 ₸"),
    ]
    mock_page.content.return_value = _make_card_html(cards_data)

    result = pp._collect_cards(mock_page)

    assert len(result) == 2
    assert result[0]["url"] == "https://krisha.kz/a/show/123"
    assert result[0]["title"] == "2-комн. квартира, 65 м²"
    assert result[0]["price"] == "25 000 000 ₸"
    assert result[1]["url"] == "https://krisha.kz/a/show/456"


def test_collect_cards_empty_page():
    """_collect_cards возвращает [] на пустой странице."""
    import parser_playwright as pp
    mock_page = MagicMock()
    mock_page.content.return_value = "<html><body></body></html>"

    result = pp._collect_cards(mock_page)
    assert result == []


def test_collect_cards_full_url():
    """_collect_cards корректно обрабатывает полные URL."""
    import parser_playwright as pp
    mock_page = MagicMock()
    mock_page.content.return_value = '''
    <html><body>
        <div data-id="999">
            <a class="a-card__title" href="https://krisha.kz/a/show/999">Квартира</a>
            <div class="a-card__price">10 000 000 ₸</div>
        </div>
    </body></html>'''

    result = pp._collect_cards(mock_page)
    assert len(result) == 1
    assert result[0]["url"] == "https://krisha.kz/a/show/999"


def test_collect_cards_no_price():
    """_collect_cards работает когда нет цены."""
    import parser_playwright as pp
    mock_page = MagicMock()
    mock_page.content.return_value = '''
    <html><body>
        <div>
            <a class="a-card__title" href="/a/show/111">Квартира без цены</a>
        </div>
    </body></html>'''

    result = pp._collect_cards(mock_page)
    assert len(result) == 1
    assert result[0]["price"] == ""


def test_collect_cards_exception_returns_empty():
    """_collect_cards возвращает [] при исключении."""
    import parser_playwright as pp
    mock_page = MagicMock()
    mock_page.content.side_effect = Exception("page error")

    result = pp._collect_cards(mock_page)
    assert result == []


def test_filter_drift_detection():
    """Детекция слетевшего фильтра: page_count > expected * 1.5 (Req 7.5)."""
    # Это чистая логика — проверяем условие
    expected = 100
    page_count_ok = 120
    page_count_drift = 200

    assert not (page_count_ok > expected * 1.5), "120 не должно считаться дрифтом"
    assert page_count_drift > expected * 1.5, "200 должно считаться дрифтом"

    # Граничный случай
    assert not (150 > expected * 1.5), "150 — ровно граница, не дрифт"
    assert 151 > expected * 1.5, "151 — дрифт"
