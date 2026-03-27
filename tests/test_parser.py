"""Тесты для parser.py — normalize_phone и build_search_url."""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from parser_playwright import normalize_phone, build_search_url


class TestNormalizePhone:
    def test_standard_format(self):
        assert normalize_phone("+77001234567") == "+77001234567"

    def test_with_8(self):
        assert normalize_phone("87001234567") == "+77001234567"

    def test_with_spaces(self):
        assert normalize_phone("+7 700 123 45 67") == "+77001234567"

    def test_with_dashes(self):
        assert normalize_phone("+7-700-123-45-67") == "+77001234567"

    def test_with_parens(self):
        assert normalize_phone("+7(700)1234567") == "+77001234567"

    def test_ten_digits(self):
        assert normalize_phone("7001234567") == "+77001234567"

    def test_empty_string(self):
        assert normalize_phone("") == ""

    def test_no_digits(self):
        assert normalize_phone("abc") == ""

    def test_short_number(self):
        result = normalize_phone("123")
        assert result.startswith("+")

    def test_already_plus7(self):
        assert normalize_phone("+77771234567") == "+77771234567"


class TestBuildSearchUrl:
    def _cfg(self, **overrides):
        base = {
            "krisha": {
                "deal_type": "sale",
                "region_alias": "",
                "rooms": [],
                "price_from": "",
                "price_to": "",
                "has_photo": False,
                "novostroiki": False,
                "from_owner": False,
                "from_agent": False,
                "building_type": [],
                "floor_from": "",
                "floor_to": "",
                "house_floors_from": "",
                "house_floors_to": "",
                "year_from": "",
                "year_to": "",
                "not_last_floor": False,
                "not_first_floor": False,
                "square_from": "",
                "square_to": "",
                "kitchen_from": "",
                "kitchen_to": "",
                "mortgage": "",
                "priv_dorm": "",
                "has_change": False,
                "toilet": [],
                "phone_line": [],
                "text_search": "",
                "max_pages": 3,
            }
        }
        base["krisha"].update(overrides)
        return base

    def test_default_sale_url(self):
        url = build_search_url(self._cfg())
        assert "krisha.kz/prodazha/kvartiry/" in url

    def test_rent_url(self):
        url = build_search_url(self._cfg(deal_type="rent"))
        assert "krisha.kz/arenda/kvartiry/" in url

    def test_region_in_path(self):
        url = build_search_url(self._cfg(region_alias="almaty"))
        assert "kvartiry/almaty/" in url

    def test_rooms_filter(self):
        url = build_search_url(self._cfg(rooms=[1, 2]))
        assert "das[live.rooms]=1" in url
        assert "das[live.rooms]=2" in url

    def test_price_filter(self):
        url = build_search_url(self._cfg(price_from="5000000", price_to="10000000"))
        assert "das[price][from]=5000000" in url
        assert "das[price][to]=10000000" in url

    def test_page_param(self):
        url = build_search_url(self._cfg(), page=3)
        assert "page=3" in url

    def test_page_1_no_param(self):
        url = build_search_url(self._cfg(), page=1)
        assert "page=" not in url

    def test_has_photo(self):
        url = build_search_url(self._cfg(has_photo=True))
        assert "das[_sys.hasphoto]=1" in url

    def test_from_owner(self):
        url = build_search_url(self._cfg(from_owner=True))
        assert "das[who]=1" in url
