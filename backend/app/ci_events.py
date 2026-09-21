"""CI/PR/issue event history pushed via /internal/ci-report.

Follows incidents.py's persistence shape (SQLite on the same kind of Fly
volume) rather than reports.py's in-memory dict, because Coms history must
survive a restart.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator, Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS ci_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_id TEXT NOT NULL,
    repo TEXT NOT NULL,
    event_type TEXT NOT NULL,
    ci_status TEXT NOT NULL,
    details TEXT NOT NULL DEFAULT '',
    received_at TEXT NOT NULL,
    notified INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_ci_events_app_received
    ON ci_events (app_id, received_at);
"""

_db_path: str = "./aisaac_ci_events.db"


def configure(db_path: str) -> None:
    global _db_path
    _db_path = db_path
    with _connect() as conn:
        conn.executescript(_SCHEMA)


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(_db_path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_event(
    app_id: str,
    repo: str,
    event_type: str,
    ci_status: str,
    details: str,
    notified: bool,
) -> int:
    with _connect() as conn:
        cursor = conn.execute(
            "INSERT INTO ci_events (app_id, repo, event_type, ci_status, details, "
            "received_at, notified) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (app_id, repo, event_type, ci_status, details, _now(), int(notified)),
        )
        return cursor.lastrowid


def list_events(app_id: Optional[str] = None, limit: int = 50) -> list[sqlite3.Row]:
    with _connect() as conn:
        if app_id:
            return conn.execute(
                "SELECT * FROM ci_events WHERE app_id = ? ORDER BY received_at DESC LIMIT ?",
                (app_id, limit),
            ).fetchall()
        return conn.execute(
            "SELECT * FROM ci_events ORDER BY received_at DESC LIMIT ?", (limit,)
        ).fetchall()
