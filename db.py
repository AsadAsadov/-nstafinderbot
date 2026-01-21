import os
import sqlite3
from datetime import datetime
from typing import Optional


def get_db_path() -> str:
    return os.getenv("DB_PATH", "/tmp/instafinder.db")


def get_connection() -> sqlite3.Connection:
    return sqlite3.connect(get_db_path())


def init_db() -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users(
                id INTEGER PRIMARY KEY,
                first_seen TEXT,
                searches_today INTEGER
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS favorites(
                user_id INTEGER,
                link TEXT,
                type TEXT
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS bot_texts(
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )
        conn.commit()


def get_user(user_id: int) -> Optional[tuple]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, first_seen, searches_today FROM users WHERE id=?", (user_id,))
        return cursor.fetchone()


def add_user(user_id: int) -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO users (id, first_seen, searches_today) VALUES (?, ?, ?)",
            (user_id, datetime.utcnow().isoformat(), 0),
        )
        conn.commit()


def reset_daily_searches() -> None:
    today = datetime.utcnow().strftime("%Y-%m-%d")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM bot_texts WHERE key='last_reset'")
        row = cursor.fetchone()
        if row and row[0] == today:
            return
        cursor.execute("UPDATE users SET searches_today=0")
        cursor.execute(
            "INSERT OR REPLACE INTO bot_texts (key, value) VALUES ('last_reset', ?)",
            (today,),
        )
        conn.commit()


def increment_search(user_id: int) -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT searches_today FROM users WHERE id=?", (user_id,))
        row = cursor.fetchone()
        count = row[0] if row else 0
        count += 1
        cursor.execute("UPDATE users SET searches_today=? WHERE id=?", (count, user_id))
        conn.commit()
        return count


def get_total_users() -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        return cursor.fetchone()[0]


def get_today_search_count() -> int:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT SUM(searches_today) FROM users")
        result = cursor.fetchone()[0]
        return int(result or 0)


def add_favorite(user_id: int, link: str, item_type: str) -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO favorites (user_id, link, type) VALUES (?, ?, ?)",
            (user_id, link, item_type),
        )
        conn.commit()


def remove_favorite(user_id: int, link: str) -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM favorites WHERE user_id=? AND link=?", (user_id, link))
        conn.commit()


def list_favorites(user_id: int) -> list[tuple]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT link, type FROM favorites WHERE user_id=?", (user_id,))
        return cursor.fetchall()


def set_bot_text(key: str, value: str) -> None:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO bot_texts (key, value) VALUES (?, ?)",
            (key, value),
        )
        conn.commit()


def get_bot_text(key: str) -> Optional[str]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM bot_texts WHERE key=?", (key,))
        row = cursor.fetchone()
        return row[0] if row else None
