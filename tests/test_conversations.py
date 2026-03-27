"""Тесты для conversations в database.py."""
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import database as db


@pytest.fixture(autouse=True)
def temp_db(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test.db")
    monkeypatch.setattr(db, "DB_PATH", test_db)
    db.init_db()
    yield


class TestConversations:
    def test_add_and_get(self):
        db.add_conversation("+77001234567", "user", "Привет")
        msgs = db.get_conversation("+77001234567")
        assert len(msgs) == 1
        assert msgs[0]["role"] == "user"
        assert msgs[0]["message"] == "Привет"

    def test_conversation_order(self):
        db.add_conversation("+77001234567", "user", "Первое")
        db.add_conversation("+77001234567", "assistant", "Второе")
        db.add_conversation("+77001234567", "user", "Третье")
        msgs = db.get_conversation("+77001234567")
        assert len(msgs) == 3
        assert msgs[0]["message"] == "Первое"
        assert msgs[2]["message"] == "Третье"

    def test_get_conversation_full_has_dates(self):
        db.add_conversation("+77001234567", "user", "Тест")
        msgs = db.get_conversation_full("+77001234567")
        assert len(msgs) == 1
        assert "created_at" in msgs[0]
        assert msgs[0]["created_at"] is not None

    def test_get_all_conversations_phones(self):
        db.add_conversation("+77001111111", "user", "Один")
        db.add_conversation("+77002222222", "user", "Два")
        db.add_conversation("+77001111111", "assistant", "Ответ")
        phones = db.get_all_conversations_phones()
        assert len(phones) == 2
        # Проверяем что есть msg_count
        for p in phones:
            assert "msg_count" in p
            assert "last_at" in p

    def test_clear_conversation(self):
        db.add_conversation("+77001234567", "user", "Тест")
        db.add_conversation("+77001234567", "assistant", "Ответ")
        db.clear_conversation("+77001234567")
        msgs = db.get_conversation("+77001234567")
        assert len(msgs) == 0

    def test_mark_replied(self):
        db.add_phone("+77001234567")
        db.mark_replied("+77001234567")
        phones = db.get_all_phones()
        assert phones[0]["replied"] == 1

    def test_get_sent_today_count(self):
        db.add_conversation("+77001234567", "assistant", "Привет")
        db.add_conversation("+77001234567", "assistant", "Как дела")
        db.add_conversation("+77001234567", "user", "Нормально")
        count = db.get_sent_today_count()
        assert count == 2  # только assistant


class TestDbStructure:
    def test_structure_has_tables(self):
        structure = db.get_db_structure()
        assert "phones" in structure
        assert "columns" in structure["phones"]
        assert "count" in structure["phones"]
