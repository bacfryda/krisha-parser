"""Общие фикстуры для тестов миграции на Playwright."""
import sys
import os
from unittest.mock import MagicMock

# Добавляем корень проекта в sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Мокируем app_paths (зависит от frozen-сборки)
_mock_app_paths = MagicMock()
_mock_app_paths.APP_DIR = os.path.join(os.path.dirname(__file__), "..")

if "app_paths" not in sys.modules:
    sys.modules["app_paths"] = _mock_app_paths
