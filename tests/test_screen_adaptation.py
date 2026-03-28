"""Тесты для _get_screen_info(), _compute_toolbar_offset() и инициализации DPI-атрибутов."""
import sys
import os
from unittest.mock import MagicMock, patch

import pytest

# conftest.py уже добавляет корень проекта в sys.path и мокирует app_paths

# Импортируем класс один раз — gui.py загружается с замоканным app_paths
from gui import MainWindow


def _make_self(cfg=None, dpi_scale=1.0):
    """Создаёт MagicMock с нужными атрибутами для вызова методов MainWindow."""
    obj = MagicMock(spec=[])
    obj.cfg = cfg if cfg is not None else {}
    obj._dpi_scale = dpi_scale
    return obj


class FakeScreen:
    """Мок QScreen с настраиваемыми параметрами."""

    def __init__(self, width=1920, height=1080, dpi=1.0):
        self._width = width
        self._height = height
        self._dpi = dpi

    def availableGeometry(self):
        geo = MagicMock()
        geo.width.return_value = self._width
        geo.height.return_value = self._height
        return geo

    def devicePixelRatio(self):
        return self._dpi


# ═══════════════════════════════════════════════════════════════
#  _get_screen_info()
# ═══════════════════════════════════════════════════════════════

class TestGetScreenInfo:
    """Тесты для _get_screen_info()."""

    def test_returns_screen_dimensions(self):
        obj = _make_self()
        screen = FakeScreen(1920, 1080, 1.0)
        with patch("gui.QApplication") as mock_app:
            mock_app.primaryScreen.return_value = screen
            result = MainWindow._get_screen_info(obj)
        assert result["width"] == 1920
        assert result["height"] == 1080
        assert result["dpi_scale"] == 1.0

    def test_returns_2k_screen(self):
        obj = _make_self()
        screen = FakeScreen(2560, 1440, 1.25)
        with patch("gui.QApplication") as mock_app:
            mock_app.primaryScreen.return_value = screen
            result = MainWindow._get_screen_info(obj)
        assert result["width"] == 2560
        assert result["height"] == 1440
        assert result["dpi_scale"] == 1.25

    def test_fallback_when_screen_is_none(self):
        obj = _make_self()
        with patch("gui.QApplication") as mock_app:
            mock_app.primaryScreen.return_value = None
            result = MainWindow._get_screen_info(obj)
        assert result == {"width": 1200, "height": 900, "dpi_scale": 1.0}

    def test_fallback_on_exception(self):
        obj = _make_self()
        with patch("gui.QApplication") as mock_app:
            mock_app.primaryScreen.side_effect = RuntimeError("no display")
            result = MainWindow._get_screen_info(obj)
        assert result == {"width": 1200, "height": 900, "dpi_scale": 1.0}

    def test_dpi_scale_zero_clamped_to_one(self):
        obj = _make_self()
        screen = FakeScreen(1920, 1080, 0.0)
        with patch("gui.QApplication") as mock_app:
            mock_app.primaryScreen.return_value = screen
            result = MainWindow._get_screen_info(obj)
        assert result["dpi_scale"] == 1.0

    def test_dpi_scale_negative_clamped_to_one(self):
        obj = _make_self()
        screen = FakeScreen(1920, 1080, -0.5)
        with patch("gui.QApplication") as mock_app:
            mock_app.primaryScreen.return_value = screen
            result = MainWindow._get_screen_info(obj)
        assert result["dpi_scale"] == 1.0

    def test_dpi_scale_above_4_clamped(self):
        obj = _make_self()
        screen = FakeScreen(3840, 2160, 5.0)
        with patch("gui.QApplication") as mock_app:
            mock_app.primaryScreen.return_value = screen
            result = MainWindow._get_screen_info(obj)
        assert result["dpi_scale"] == 4.0


# ═══════════════════════════════════════════════════════════════
#  _compute_toolbar_offset()
# ═══════════════════════════════════════════════════════════════

class TestComputeToolbarOffset:
    """Тесты для _compute_toolbar_offset()."""

    def test_default_offset_at_dpi_1(self):
        obj = _make_self()
        assert MainWindow._compute_toolbar_offset(obj) == 155

    def test_default_offset_at_dpi_125(self):
        obj = _make_self(dpi_scale=1.25)
        assert MainWindow._compute_toolbar_offset(obj) == int(155 * 1.25)

    def test_config_override(self):
        obj = _make_self(cfg={"toolbar_offset": 200}, dpi_scale=1.0)
        assert MainWindow._compute_toolbar_offset(obj) == 200

    def test_config_override_with_dpi(self):
        obj = _make_self(cfg={"toolbar_offset": 200}, dpi_scale=1.5)
        assert MainWindow._compute_toolbar_offset(obj) == int(200 * 1.5)

    def test_config_below_50_uses_default(self):
        obj = _make_self(cfg={"toolbar_offset": 10})
        assert MainWindow._compute_toolbar_offset(obj) == 155

    def test_config_above_300_uses_default(self):
        obj = _make_self(cfg={"toolbar_offset": 500})
        assert MainWindow._compute_toolbar_offset(obj) == 155

    def test_config_zero_uses_default(self):
        obj = _make_self(cfg={"toolbar_offset": 0})
        assert MainWindow._compute_toolbar_offset(obj) == 155

    def test_config_non_numeric_uses_default(self):
        obj = _make_self(cfg={"toolbar_offset": "abc"})
        assert MainWindow._compute_toolbar_offset(obj) == 155

    def test_config_none_uses_default(self):
        obj = _make_self(cfg={"toolbar_offset": None})
        assert MainWindow._compute_toolbar_offset(obj) == 155

    def test_config_50_boundary(self):
        obj = _make_self(cfg={"toolbar_offset": 50})
        assert MainWindow._compute_toolbar_offset(obj) == 50

    def test_config_300_boundary(self):
        obj = _make_self(cfg={"toolbar_offset": 300})
        assert MainWindow._compute_toolbar_offset(obj) == 300
