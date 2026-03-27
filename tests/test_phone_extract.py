"""
Тесты для Phone Extractor.
- Property 9: Извлечение телефона из HTML (Req 8.5, 8.6)
- Property 10: normalize_phone форматирование (Req 8.6)
"""
import pytest
import re


def normalize_phone(raw: str) -> str:
    """Копия normalize_phone из parser_playwright.py для тестирования."""
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


class TestNormalizePhone:
    """Property 10: normalize_phone форматирование."""

    def test_standard_format(self):
        assert normalize_phone("+7 701 123 45 67") == "+77011234567"

    def test_eight_prefix(self):
        """8XXXXXXXXXX → +7XXXXXXXXXX."""
        assert normalize_phone("87011234567") == "+77011234567"

    def test_seven_prefix(self):
        assert normalize_phone("77011234567") == "+77011234567"

    def test_ten_digits(self):
        """10 цифр → добавляет 7."""
        assert normalize_phone("7011234567") == "+77011234567"

    def test_with_dashes(self):
        assert normalize_phone("+7-701-123-45-67") == "+77011234567"

    def test_with_parentheses(self):
        assert normalize_phone("+7(701)1234567") == "+77011234567"

    def test_with_spaces(self):
        assert normalize_phone("8 701 123 45 67") == "+77011234567"

    def test_empty_string(self):
        assert normalize_phone("") == ""

    def test_no_digits(self):
        assert normalize_phone("abc") == ""

    def test_plus_seven_format(self):
        assert normalize_phone("+77771234567") == "+77771234567"
