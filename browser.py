# DEPRECATED: используйте parser_playwright.py
# Этот модуль использовал undetected_chromedriver (Selenium).
# Вся функциональность перенесена в parser_playwright.py (Playwright sync API).
"""Общий антидетект браузер — DEPRECATED.

Используйте parser_playwright.py вместо этого модуля.
Selenium/undetected_chromedriver заменён на Playwright + playwright-stealth.
"""

import warnings

warnings.warn(
    "browser.py is deprecated. Use parser_playwright.py instead.",
    DeprecationWarning,
    stacklevel=2,
)


def get_driver():
    """DEPRECATED: используйте parser_playwright._get_driver()"""
    raise NotImplementedError(
        "browser.py is deprecated. Use parser_playwright._get_driver() instead."
    )


def close_driver():
    """DEPRECATED: используйте parser_playwright.close_driver()"""
    raise NotImplementedError(
        "browser.py is deprecated. Use parser_playwright.close_driver() instead."
    )
