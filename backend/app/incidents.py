"""Minimal incident history store.

AIsaac was fully stateless until this rollout -- this is its first
persistence layer. SQLite on a Fly volume in production (same pattern as
vinyl_api), a local file in dev. Deliberately small: one table, no ORM,
since the data volume here is tiny (a handful of incidents per app at most).
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator, Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS incidents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    app_id TEXT NOT NULL,
    failure_type TEXT NOT NULL,
    started_at TEXT NOT NULL,
    resolved_at TEXT,
    notes TEXT
);
CREATE INDEX IF NOT EXISTS ix_incidents_app_open
    ON incidents (app_id, resolved_at);
"""

_db_path: str = "./aisaac_incidents.db"


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


def get_open_incident(app_id: str) -> Optional[sqlite3.Row]:
    with _connect() as conn:
        return conn.execute(
            "SELECT * FROM incidents WHERE app_id = ? AND resolved_at IS NULL "
            "ORDER BY started_at DESC LIMIT 1",
            (app_id,),
        ).fetchone()


def open_incident(app_id: str, failure_type: str) -> int:
    with _connect() as conn:
        cursor = conn.execute(
            "INSERT INTO incidents (app_id, failure_type, started_at) VALUES (?, ?, ?)",
            (app_id, failure_type, _now()),
        )
        return cursor.lastrowid


def resolve_incident(incident_id: int, notes: Optional[str] = None) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE incidents SET resolved_at = ?, notes = COALESCE(?, notes) WHERE id = ?",
            (_now(), notes, incident_id),
        )


def list_incidents(app_id: Optional[str] = None, limit: int = 50) -> list[sqlite3.Row]:
    with _connect() as conn:
        if app_id:
            return conn.execute(
                "SELECT * FROM incidents WHERE app_id = ? ORDER BY started_at DESC LIMIT ?",
                (app_id, limit),
            ).fetchall()
        return conn.execute(
            "SELECT * FROM incidents ORDER BY started_at DESC LIMIT ?", (limit,)
        ).fetchall()
