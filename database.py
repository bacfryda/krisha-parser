"""SQLite база для хранения спарсенных номеров и диалогов."""
import sqlite3
import os
from datetime import datetime
from app_paths import APP_DIR

DB_PATH = os.path.join(APP_DIR, "phones.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS phones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT UNIQUE NOT NULL,
            listing_url TEXT,
            listing_title TEXT,
            price TEXT,
            parsed_at TEXT NOT NULL,
            message_sent INTEGER DEFAULT 0,
            replied INTEGER DEFAULT 0,
            no_whatsapp INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL,
            role TEXT NOT NULL,
            message TEXT NOT NULL,
            created_at TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            FOREIGN KEY (phone) REFERENCES phones(phone)
        );
        CREATE TABLE IF NOT EXISTS parsed_urls (
            url TEXT PRIMARY KEY NOT NULL,
            parsed_at TEXT NOT NULL
        );
    """)
    # Миграция — добавляем колонки если их нет
    try:
        conn.execute("ALTER TABLE phones ADD COLUMN no_whatsapp INTEGER DEFAULT 0")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # колонка уже есть
    try:
        conn.execute("ALTER TABLE conversations ADD COLUMN is_read INTEGER DEFAULT 0")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # колонка уже есть
    try:
        conn.execute("ALTER TABLE phones ADD COLUMN sent_at TEXT")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # колонка уже есть
    conn.close()


def add_phone(phone: str, listing_url: str = "", listing_title: str = "", price: str = "") -> bool:
    """Добавить номер. Возвращает True если новый, False если дубликат."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO phones (phone, listing_url, listing_title, price, parsed_at) VALUES (?, ?, ?, ?, ?)",
            (phone, listing_url, listing_title, price, datetime.now().isoformat()),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def is_url_parsed(url: str) -> bool:
    """Проверяет, парсили ли мы уже это объявление."""
    conn = get_connection()
    row = conn.execute("SELECT 1 FROM parsed_urls WHERE url = ?", (url,)).fetchone()
    conn.close()
    return row is not None


def mark_url_parsed(url: str):
    """Отмечает URL как спарсенный."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO parsed_urls (url, parsed_at) VALUES (?, ?)",
            (url, datetime.now().isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def is_phone_exists(phone: str) -> bool:
    """Проверяет, есть ли номер в базе."""
    conn = get_connection()
    row = conn.execute("SELECT 1 FROM phones WHERE phone = ?", (phone,)).fetchone()
    conn.close()
    return row is not None


def mark_sent(phone: str):
    conn = get_connection()
    conn.execute(
        "UPDATE phones SET message_sent = 1, sent_at = ? WHERE phone = ?",
        (datetime.now().isoformat(), phone),
    )
    conn.commit()
    conn.close()


def mark_no_whatsapp(phone: str):
    """Пометить номер как не имеющий WhatsApp."""
    conn = get_connection()
    conn.execute("UPDATE phones SET no_whatsapp = 1 WHERE phone = ?", (phone,))
    conn.commit()
    conn.close()


def mark_replied(phone: str):
    conn = get_connection()
    # Пробуем и с + и без + (номера могут храниться в разных форматах)
    bare = phone.lstrip('+')
    conn.execute("UPDATE phones SET replied = 1 WHERE phone = ? OR phone = ?", (phone, bare))
    conn.commit()
    conn.close()


def get_unsent_phones() -> list:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM phones WHERE message_sent = 0 AND no_whatsapp = 0").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_phones() -> list:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM phones ORDER BY parsed_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats() -> dict:
    conn = get_connection()
    row = conn.execute("""
        SELECT
            COUNT(*) as total,
            COALESCE(SUM(CASE WHEN message_sent = 1 THEN 1 ELSE 0 END), 0) as sent,
            COALESCE(SUM(CASE WHEN replied = 1 THEN 1 ELSE 0 END), 0) as replied,
            COALESCE(SUM(CASE WHEN no_whatsapp = 1 THEN 1 ELSE 0 END), 0) as no_wa
        FROM phones
    """).fetchone()
    conn.close()
    return {"total": row[0], "sent": row[1], "replied": row[2], "no_wa": row[3]}


def get_sent_today_count() -> int:
    """Кол-во рассылочных сообщений за сегодня (phones с message_sent=1 и sent_at сегодня)."""
    conn = get_connection()
    today = datetime.now().strftime("%Y-%m-%d")
    row = conn.execute(
        "SELECT COUNT(*) FROM phones WHERE message_sent = 1 AND sent_at LIKE ?",
        (today + "%",),
    ).fetchone()
    conn.close()
    return row[0] if row else 0



def add_conversation(phone: str, role: str, message: str):
    conn = get_connection()
    conn.execute(
        "INSERT INTO conversations (phone, role, message, created_at) VALUES (?, ?, ?, ?)",
        (phone, role, message, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()


def get_conversation(phone: str) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT role, message FROM conversations WHERE phone = ? ORDER BY created_at", (phone,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_conversation_full(phone: str) -> list:
    """Получить полную историю диалога с датами."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT role, message, created_at FROM conversations WHERE phone = ? ORDER BY created_at",
        (phone,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_conversations_phones() -> list:
    """Получить список всех номеров с диалогами + кол-во сообщений и дату последнего."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT phone, COUNT(*) as msg_count, MAX(created_at) as last_at,
               SUM(CASE WHEN role = 'user' AND is_read = 0 THEN 1 ELSE 0 END) as unread_count
        FROM conversations GROUP BY phone ORDER BY last_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_chat_read(phone: str):
    """Пометить все сообщения в чате как прочитанные."""
    conn = get_connection()
    conn.execute("UPDATE conversations SET is_read = 1 WHERE phone = ? AND role = 'user'", (phone,))
    conn.commit()
    conn.close()


def clear_conversation(phone: str):
    """Очистить историю диалога с номером."""
    conn = get_connection()
    conn.execute("DELETE FROM conversations WHERE phone = ?", (phone,))
    conn.commit()
    conn.close()


def get_db_structure() -> dict:
    """Получить структуру БД — таблицы, колонки, кол-во записей."""
    conn = get_connection()
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    result = {}
    for t in tables:
        name = t["name"]
        cols = conn.execute(f"PRAGMA table_info({name})").fetchall()
        count = conn.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0]
        result[name] = {
            "columns": [{"name": c["name"], "type": c["type"], "pk": bool(c["pk"])} for c in cols],
            "count": count,
        }
    conn.close()
    return result


def clear_all_conversations():
    """Очистить ВСЮ историю диалогов."""
    conn = get_connection()
    conn.execute("DELETE FROM conversations")
    conn.commit()
    conn.close()


def clear_parsed_urls():
    """Очистить историю спарсенных URL."""
    conn = get_connection()
    conn.execute("DELETE FROM parsed_urls")
    conn.commit()
    conn.close()
