"""Тесты для wa_client.py (мокаем HTTP)."""
import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import wa_client


def _mock_response(json_data, status_code=200):
    mock = MagicMock()
    mock.json.return_value = json_data
    mock.status_code = status_code
    return mock


class TestGetStatus:
    @patch("wa_client.requests.get")
    def test_ready(self, mock_get):
        mock_get.return_value = _mock_response({"ready": True, "phone": "77001234567"})
        st = wa_client.get_status()
        assert st["ready"] is True
        assert st["phone"] == "77001234567"

    @patch("wa_client.requests.get")
    def test_not_ready(self, mock_get):
        mock_get.return_value = _mock_response({"ready": False, "qr": "some_qr"})
        st = wa_client.get_status()
        assert st["ready"] is False

    @patch("wa_client.requests.get", side_effect=wa_client.requests.RequestException("conn refused"))
    def test_server_down(self, mock_get):
        st = wa_client.get_status()
        assert st["ready"] is False


class TestIsReady:
    @patch("wa_client.requests.get")
    def test_true(self, mock_get):
        mock_get.return_value = _mock_response({"ready": True})
        assert wa_client.is_ready() is True

    @patch("wa_client.requests.get")
    def test_false(self, mock_get):
        mock_get.return_value = _mock_response({"ready": False})
        assert wa_client.is_ready() is False


class TestSendMessage:
    @patch("wa_client.requests.post")
    def test_success(self, mock_post):
        mock_post.return_value = _mock_response({"success": True, "delivered": True})
        result = wa_client.send_message("+77001234567", "Привет")
        assert result["success"] is True

    @patch("wa_client.requests.post")
    def test_not_registered(self, mock_post):
        mock_post.return_value = _mock_response(
            {"success": False, "error": "not_registered"}
        )
        result = wa_client.send_message("+77001234567", "Привет")
        assert result["success"] is False

    @patch("wa_client.requests.post", side_effect=wa_client.requests.RequestException("timeout"))
    def test_network_error(self, mock_post):
        result = wa_client.send_message("+77001234567", "Привет")
        assert result["success"] is False
        assert "error" in result


class TestCheckPhone:
    @patch("wa_client.requests.get")
    def test_registered(self, mock_get):
        mock_get.return_value = _mock_response({"registered": True})
        assert wa_client.check_phone("+77001234567") is True

    @patch("wa_client.requests.get")
    def test_not_registered(self, mock_get):
        mock_get.return_value = _mock_response({"registered": False})
        assert wa_client.check_phone("+77001234567") is False


class TestGetUnread:
    @patch("wa_client.requests.get")
    def test_has_messages(self, mock_get):
        data = {"+77001234567": [{"body": "Привет", "timestamp": 123}]}
        mock_get.return_value = _mock_response(data)
        result = wa_client.get_unread()
        assert "+77001234567" in result

    @patch("wa_client.requests.get")
    def test_empty(self, mock_get):
        mock_get.return_value = _mock_response({})
        result = wa_client.get_unread()
        assert result == {}

    @patch("wa_client.requests.get", side_effect=wa_client.requests.RequestException("err"))
    def test_error(self, mock_get):
        result = wa_client.get_unread()
        assert result == {}


class TestMarkRead:
    @patch("wa_client.requests.post")
    def test_success(self, mock_post):
        mock_post.return_value = _mock_response({"success": True})
        wa_client.mark_read("+77001234567")  # no exception

    @patch("wa_client.requests.post", side_effect=wa_client.requests.RequestException("err"))
    def test_error_silent(self, mock_post):
        wa_client.mark_read("+77001234567")  # no exception
