"""Тесты для config.py."""
import json
import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import load_config, save_config, DEFAULT_CONFIG, _deep_merge, _deep_copy


class TestDeepMerge:
    def test_simple_merge(self):
        base = {"a": 1, "b": 2}
        _deep_merge(base, {"b": 3, "c": 4})
        assert base == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self):
        base = {"x": {"a": 1, "b": 2}, "y": 10}
        _deep_merge(base, {"x": {"b": 99}})
        assert base["x"]["a"] == 1
        assert base["x"]["b"] == 99
        assert base["y"] == 10

    def test_missing_keys_preserved(self):
        base = {"x": {"a": 1, "b": 2, "c": 3}}
        _deep_merge(base, {"x": {"a": 100}})
        assert base["x"]["b"] == 2
        assert base["x"]["c"] == 3


class TestDeepCopy:
    def test_independent_copy(self):
        orig = {"a": [1, 2], "b": {"c": 3}}
        copy = _deep_copy(orig)
        copy["a"].append(3)
        copy["b"]["c"] = 99
        assert orig["a"] == [1, 2]
        assert orig["b"]["c"] == 3


class TestLoadSaveConfig:
    def test_default_config_has_all_sections(self):
        cfg = DEFAULT_CONFIG
        assert "krisha" in cfg
        assert "whatsapp" in cfg
        assert "captcha" in cfg
        assert "deepseek" in cfg

    def test_default_config_krisha_fields(self):
        k = DEFAULT_CONFIG["krisha"]
        assert "deal_type" in k
        assert "rooms" in k
        assert "max_pages" in k
        assert isinstance(k["rooms"], list)
        assert isinstance(k["max_pages"], int)
