"""
Тесты для captcha_solver.py.
- Property 11: detect_captcha определяет наличие reCAPTCHA (Req 9.1)
- Property 12: _find_recaptcha_sitekey извлекает ключ (Req 9.2)
"""
import pytest
from unittest.mock import MagicMock
from captcha_solver import detect_captcha, _find_recaptcha_sitekey


class TestDetectCaptcha:
    """Property 11: detect_captcha определяет наличие reCAPTCHA."""

    def test_detects_recaptcha_iframe(self):
        page = MagicMock()
        page.query_selector_all.side_effect = lambda sel: (
            [MagicMock()] if "recaptcha" in sel else []
        )
        assert detect_captcha(page) is True

    def test_detects_grecaptcha_div(self):
        page = MagicMock()
        def qs(sel):
            if "g-recaptcha" in sel:
                return [MagicMock()]
            return []
        page.query_selector_all.side_effect = qs
        assert detect_captcha(page) is True

    def test_detects_text_not_robot(self):
        page = MagicMock()
        page.query_selector_all.return_value = []
        page.evaluate.return_value = "Подтвердите что Я не робот"
        assert detect_captcha(page) is True

    def test_no_captcha(self):
        page = MagicMock()
        page.query_selector_all.return_value = []
        page.evaluate.return_value = "Обычная страница без капчи"
        assert detect_captcha(page) is False

    def test_exception_returns_false(self):
        page = MagicMock()
        page.query_selector_all.side_effect = Exception("error")
        assert detect_captcha(page) is False


class TestFindRecaptchaSitekey:
    """Property 12: _find_recaptcha_sitekey извлекает ключ."""

    def test_from_data_sitekey(self):
        page = MagicMock()
        el = MagicMock()
        el.get_attribute.return_value = "6LcXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
        page.query_selector_all.side_effect = lambda sel: (
            [el] if "data-sitekey" in sel else []
        )
        result = _find_recaptcha_sitekey(page)
        assert result == "6LcXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

    def test_from_iframe_src(self):
        page = MagicMock()
        el_no_sitekey = MagicMock()
        el_no_sitekey.get_attribute.return_value = None
        iframe = MagicMock()
        iframe.get_attribute.return_value = (
            "https://www.google.com/recaptcha/api2/anchor?k=6LcABCDEFGHIJKLMNOPQRSTU"
        )

        def qs(sel):
            if "data-sitekey" in sel:
                return []  # нет div с data-sitekey
            if "recaptcha" in sel:
                return [iframe]
            return []

        page.query_selector_all.side_effect = qs
        result = _find_recaptcha_sitekey(page)
        assert result == "6LcABCDEFGHIJKLMNOPQRSTU"

    def test_from_page_source(self):
        page = MagicMock()
        page.query_selector_all.return_value = []
        page.content.return_value = '''
            <script>
                grecaptcha.render('captcha', {sitekey: "6LcTESTKEYXXXXXXXXXXXXXXXXXXXXXX"});
            </script>
        '''
        result = _find_recaptcha_sitekey(page)
        assert result == "6LcTESTKEYXXXXXXXXXXXXXXXXXXXXXX"

    def test_no_sitekey_found(self):
        page = MagicMock()
        page.query_selector_all.return_value = []
        page.content.return_value = "<html><body>No captcha</body></html>"
        result = _find_recaptcha_sitekey(page)
        assert result is None
