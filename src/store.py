from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS requests (
    thread_id TEXT PRIMARY KEY,
    request_id TEXT NOT NULL UNIQUE,
    revision INTEGER NOT NULL,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS processed_messages (
    message_id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    request_id TEXT,
    result_status TEXT NOT NULL,
    processed_at TEXT NOT NULL,
    reply_sent INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_processed_thread ON processed_messages(thread_id);
"""

class SQLiteStore:
    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        self.conn = sqlite3.connect(self.path, timeout=10, isolation_level=None, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            yield self.conn
            self.conn.execute("COMMIT")
        except Exception:
            self.conn.execute("ROLLBACK")
            raise

    def message_seen(self, message_id: str, conn: sqlite3.Connection | None = None) -> bool:
        c = conn or self.conn
        return c.execute("SELECT 1 FROM processed_messages WHERE message_id=?", (message_id,)).fetchone() is not None

    def get_request(self, thread_id: str, conn: sqlite3.Connection | None = None) -> dict[str, Any] | None:
        c = conn or self.conn
        row = c.execute("SELECT * FROM requests WHERE thread_id=?", (thread_id,)).fetchone()
        if not row:
            return None
        return {**dict(row), "payload": json.loads(row["payload_json"])}

    def upsert_request(self, *, thread_id: str, request_id: str, revision: int, payload: dict[str, Any], status: str, conn: sqlite3.Connection | None = None) -> None:
        c = conn or self.conn
        now = datetime.now(timezone.utc).isoformat()
        c.execute(
            """INSERT INTO requests(thread_id, request_id, revision, payload_json, status, updated_at)
               VALUES(?,?,?,?,?,?)
               ON CONFLICT(thread_id) DO UPDATE SET request_id=excluded.request_id, revision=excluded.revision,
                 payload_json=excluded.payload_json, status=excluded.status, updated_at=excluded.updated_at""",
            (thread_id, request_id, revision, json.dumps(payload, ensure_ascii=False, sort_keys=True), status, now),
        )

    def record_message(self, *, message_id: str, thread_id: str, request_id: str | None, result_status: str, conn: sqlite3.Connection | None = None) -> None:
        c = conn or self.conn
        now = datetime.now(timezone.utc).isoformat()
        c.execute(
            "INSERT INTO processed_messages(message_id,thread_id,request_id,result_status,processed_at) VALUES(?,?,?,?,?)",
            (message_id, thread_id, request_id, result_status, now),
        )

    def mark_reply_sent(self, message_id: str) -> None:
        self.conn.execute("UPDATE processed_messages SET reply_sent=1 WHERE message_id=?", (message_id,))
