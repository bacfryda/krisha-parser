"""
Python клиент для WhatsApp Web.js сервера.

Общается с Node.js сервером по HTTP.
Все операции WhatsApp идут через whatsapp-web.js (реверс-инжиниренный протокол),
а не через DOM-парсинг.
"""
import requests
from typing import Optional

WA_SERVER_URL = "http://localhost:3457"


def get_status() -> dict:
    """Получить статус WhatsApp: ready, qr, phone, name."""
    try:
        r = requests.get(f"{WA_SERVER_URL}/status", timeout=2)
        return r.json()
    except requests.RequestException:
        return {"ready": False, "qr": None, "error": "Сервер не запущен"}


def is_ready() -> bool:
    """Подключён ли WhatsApp."""
    status = get_status()
    return status.get("ready", False)


def get_qr() -> Optional[str]:
    """Получить QR-код для авторизации (или None если уже авторизован)."""
    status = get_status()
    return status.get("qr")


def send_message(phone: str, message: str) -> dict:
    """
    Отправить сообщение.
    Возвращает: {success: bool, error?: str, delivered?: bool}
    """
    try:
        r = requests.post(
            f"{WA_SERVER_URL}/send",
            json={"phone": phone, "message": message},
            timeout=30,
        )
        data = r.json()
        if r.status_code != 200:
            return {"success": False, "error": data.get("error", f"HTTP {r.status_code}")}
        return data
    except requests.RequestException as e:
        return {"success": False, "error": str(e)}


def check_phone(phone: str) -> bool:
    """Проверить зарегистрирован ли номер в WhatsApp."""
    try:
        r = requests.get(f"{WA_SERVER_URL}/check/{phone}", timeout=10)
        data = r.json()
        return data.get("registered", False)
    except requests.RequestException:
        return False


def get_unread() -> dict:
    """
    Получить непрочитанные сообщения.
    Возвращает: {phone: [{from, body, timestamp, isRead}]}
    """
    try:
        r = requests.get(f"{WA_SERVER_URL}/unread", timeout=10)
        return r.json()
    except requests.RequestException:
        return {}


def get_chat_history(phone: str) -> list:
    """Получить историю чата с номером."""
    try:
        r = requests.get(f"{WA_SERVER_URL}/chat/{phone}", timeout=10)
        data = r.json()
        if isinstance(data, list):
            return data
        return []
    except requests.RequestException:
        return []


def mark_read(phone: str):
    """Пометить сообщения от номера как прочитанные."""
    try:
        requests.post(f"{WA_SERVER_URL}/mark-read", json={"phone": phone}, timeout=5)
    except requests.RequestException:
        pass
