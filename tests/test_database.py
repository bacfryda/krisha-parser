"""Тесты для database.py."""
import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import database as db


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    """Каждый тест работает с временной БД."""
    test_db = str(tmp_path / "test.db")
    monkeypatch.setattr(db, "DB_PATH", test_db)
    db.init_db()
    yield test_db


class TestInitDb:
    def test_creates_tables(self):
        structure = db.get_db_structure()
        assert "phones" in structure
        assert "conversations" in structure
        assert "parsed_urls" in structure


class TestPhones:
    def test_add_phone_new(self):
        assert db.add_phone("+77001234567", "http://test.com", "Test", "10M") is True

    def test_add_phone_duplicate(self):
        db.add_phone("+77001234567")
        assert db.add_phone("+77001234567") is False

    def test_is_phone_exists(self):
        assert db.is_phone_exists("+77001234567") is False
        db.add_phone("+77001234567")
        assert db.is_phone_exists("+77001234567") is True

    def test_get_all_phones(self):
        db.add_phone("+77001111111")
        db.add_phone("+77002222222")
        phones = db.get_all_phones()
        assert len(phones) == 2

    def test_mark_sent(self):
        db.add_phone("+77001234567")
        db.mark_sent("+77001234567")
        phones = db.get_all_phones()
        assert phones[0]["message_sent"] == 1

    def test_mark_no_whatsapp(self):
        db.add_phone("+77001234567")
        db.mark_no_whatsapp("+77001234567")
        phones = db.get_all_phones()
        assert phones[0]["no_whatsapp"] == 1

    def test_get_unsent_phones(self):
        db.add_phone("+77001111111")
        db.add_phone("+77002222222")
        db.mark_sent("+77001111111")
        unsent = db.get_unsent_phones()
        assert len(unsent) == 1
        assert unsent[0]["phone"] == "+77002222222"

    def test_get_unsent_excludes_no_wa(self):
        db.add_phone("+77001111111")
        db.add_phone("+77002222222")
        db.mark_no_whatsapp("+77001111111")
        unsent = db.get_unsent_phones()
        assert len(unsent) == 1


class TestStats:
    def test_empty_stats(self):
        stats = db.get_stats()
        assert stats["total"] == 0
        assert stats["sent"] == 0
        assert stats["replied"] == 0
        assert stats["no_wa"] == 0

    def test_stats_counts(self):
        db.add_phone("+77001111111")
        db.add_phone("+77002222222")
        db.add_phone("+77003333333")
        db.mark_sent("+77001111111")
        db.mark_no_whatsapp("+77003333333")
        stats = db.get_stats()
        assert stats["total"] == 3
        assert stats["sent"] == 1
        assert stats["no_wa"] == 1


class TestParsedUrls:
    def test_url_not_parsed(self):
        assert db.is_url_parsed("http://test.com/1") is False

    def test_mark_and_check(self):
        db.mark_url_parsed("http://test.com/1")
        assert db.is_url_parsed("http://test.com/1") is True

    def test_mark_idempotent(self):
        db.mark_url_parsed("http://test.com/1")
        db.mark_url_parsed("http://test.com/1")  # no error
        assert db.is_url_parsed("http://test.com/1") is True
