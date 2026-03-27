"""
Тесты 15.2: Session Manager edge cases.
- Повреждённый JSON файл сессии → None (Req 3.3)
- Отсутствующий файл сессии → None (Req 3.3)
- Сессия round-trip (Property 5, Req 3.1, 3.2, 3.4)
"""
import pytest
import os
import json
import tempfile
from unittest.mock import patch, MagicMock


def test_load_storage_state_missing_file():
    """Отсутствующий файл сессии → None."""
    import parser_playwright as pp
    with patch.object(pp, "_SESSION_FILE", "/nonexistent/path/session.json"):
        result = pp._load_storage_state()
    assert result is None


def test_load_storage_state_corrupted_json():
    """Повреждённый JSON файл сессии → None."""
    import parser_playwright as pp
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("{corrupted json!!! not valid")
        tmp_path = f.name
    try:
        with patch.object(pp, "_SESSION_FILE", tmp_path):
            result = pp._load_storage_state()
        assert result is None
    finally:
        os.unlink(tmp_path)


def test_load_storage_state_valid_json():
    """Валидный JSON файл сессии → путь к файлу."""
    import parser_playwright as pp
    state = {"cookies": [{"name": "test", "value": "123"}], "origins": []}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(state, f)
        tmp_path = f.name
    try:
        with patch.object(pp, "_SESSION_FILE", tmp_path):
            result = pp._load_storage_state()
        assert result == tmp_path
    finally:
        os.unlink(tmp_path)


def test_load_storage_state_empty_file():
    """Пустой файл сессии → None."""
    import parser_playwright as pp
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        tmp_path = f.name
    try:
        with patch.object(pp, "_SESSION_FILE", tmp_path):
            result = pp._load_storage_state()
        assert result is None
    finally:
        os.unlink(tmp_path)
