from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parent / "data" / "chat.db"


class ChatStore:
    def __init__(self, db_path: Path = DB_PATH):
        self._db_path = db_path
        self._local = threading.local()

    @property
    def conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(str(self._db_path))
            self._local.conn.row_factory = sqlite3.Row
            self._local.conn.execute("PRAGMA journal_mode=WAL")
            self._local.conn.execute("PRAGMA foreign_keys=ON")
            self._init_db()
        return self._local.conn

    def _init_db(self) -> None:
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS chats (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL DEFAULT 'New Chat',
                character_path TEXT,
                character_type TEXT,
                character_name TEXT,
                created_at INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at INTEGER NOT NULL,
                FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE
            );
            CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id);
        """)
        self.conn.commit()

    def create_chat(
        self,
        chat_id: str,
        title: str = "New Chat",
        character_path: str | None = None,
        character_type: str | None = None,
        character_name: str | None = None,
    ) -> None:
        now = int(time.time() * 1000)
        self.conn.execute(
            "INSERT OR IGNORE INTO chats (id, title, character_path, character_type, character_name, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (chat_id, title, character_path, character_type, character_name, now, now),
        )
        self.conn.commit()

    def delete_chat(self, chat_id: str) -> None:
        self.conn.execute("DELETE FROM chats WHERE id = ?", (chat_id,))
        self.conn.commit()

    def add_message(self, chat_id: str, role: str, content: str) -> int:
        now = int(time.time() * 1000)
        cursor = self.conn.execute(
            "INSERT INTO messages (chat_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (chat_id, role, content, now),
        )
        self.conn.execute(
            "UPDATE chats SET updated_at = ? WHERE id = ?",
            (now, chat_id),
        )
        self.conn.commit()
        return cursor.lastrowid

    def get_messages(self, chat_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT role, content, created_at FROM messages WHERE chat_id = ? ORDER BY id ASC",
            (chat_id,),
        ).fetchall()
        return [{"role": row["role"], "content": row["content"], "created_at": row["created_at"]} for row in rows]

    def list_chats(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT id, title, character_path, character_type, character_name, created_at, updated_at "
            "FROM chats ORDER BY updated_at DESC"
        ).fetchall()
        return [dict(row) for row in rows]

    def chat_exists(self, chat_id: str) -> bool:
        row = self.conn.execute("SELECT 1 FROM chats WHERE id = ?", (chat_id,)).fetchone()
        return row is not None


_chat_store: ChatStore | None = None


def get_chat_store() -> ChatStore:
    global _chat_store
    if _chat_store is None:
        _chat_store = ChatStore()
    return _chat_store
