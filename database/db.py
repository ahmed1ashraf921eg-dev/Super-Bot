import os
import sqlite3
from typing import Any, Dict, List, Optional

from config import DB_PATH, DEFAULT_BOT_MODE


def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db() -> None:
    with get_connection() as conn:
        # 1. جدول إعدادات البوت العامة
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )

        # 2. جدول المستخدمين والاشتراكات وطلبات الانضمام
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                full_name TEXT,
                username TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                expires_at INTEGER,
                paused_remaining_seconds INTEGER,
                created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
            );
            """
        )

        # 3. جدول الأزرار المتداخلة اللانهائية
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS buttons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                parent_id INTEGER NULL,
                title TEXT NOT NULL,
                content_text TEXT,
                media_type TEXT,
                media_file_id TEXT,
                url TEXT,
                position INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
                FOREIGN KEY (parent_id) REFERENCES buttons(id) ON DELETE CASCADE
            );
            """
        )

        # تهيئة الإعدادات الافتراضية إذا لم تكن موجودة
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES ('bot_mode', ?);",
            (DEFAULT_BOT_MODE,),
        )
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES ('welcome_text', ?);",
            ("أهلاً بك في البوت! اختر من القائمة التالية:",),
        )
        conn.commit()


# --- دوال الإعدادات ---
def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    with get_connection() as conn:
        row = conn.execute("SELECT value FROM settings WHERE key = ?;", (key,)).fetchone()
        return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value;",
            (key, value),
        )
        conn.commit()


# --- دوال المستخدمين ---
def upsert_user(user_id: int, full_name: str, username: Optional[str], status: str = "active") -> None:
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO users (user_id, full_name, username, status)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                full_name = excluded.full_name,
                username = excluded.username;
            """,
            (user_id, full_name, username, status),
        )
        conn.commit()


def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE user_id = ?;", (user_id,)).fetchone()
        return dict(row) if row else None


def set_user_status(user_id: int, status: str) -> None:
    with get_connection() as conn:
        conn.execute("UPDATE users SET status = ? WHERE user_id = ?;", (status, user_id))
        conn.commit()


# --- دوال الأزرار ---
def get_buttons_by_parent(parent_id: Optional[int] = None) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        if parent_id is None:
            rows = conn.execute(
                "SELECT * FROM buttons WHERE parent_id IS NULL AND is_active = 1 ORDER BY position ASC, id ASC;"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM buttons WHERE parent_id = ? AND is_active = 1 ORDER BY position ASC, id ASC;",
                (parent_id,),
            ).fetchall()
        return [dict(r) for r in rows]


def get_button(button_id: int) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM buttons WHERE id = ?;", (button_id,)).fetchone()
        return dict(row) if row else None


def add_button(
    title: str,
    parent_id: Optional[int] = None,
    content_text: Optional[str] = None,
    media_type: Optional[str] = None,
    media_file_id: Optional[str] = None,
    url: Optional[str] = None,
) -> int:
    with get_connection() as conn:
        if parent_id is None:
            row = conn.execute("SELECT COALESCE(MAX(position), -1) + 1 AS next_pos FROM buttons WHERE parent_id IS NULL;").fetchone()
        else:
            row = conn.execute(
                "SELECT COALESCE(MAX(position), -1) + 1 AS next_pos FROM buttons WHERE parent_id = ?;",
                (parent_id,),
            ).fetchone()
        next_pos = row["next_pos"]
        cursor = conn.execute(
            """
            INSERT INTO buttons (parent_id, title, content_text, media_type, media_file_id, url, position)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (parent_id, title, content_text, media_type, media_file_id, url, next_pos),
        )
        conn.commit()
        return int(cursor.lastrowid)