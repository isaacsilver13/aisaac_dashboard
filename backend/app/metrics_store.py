"""Latest pushed snapshot per financial/usage source (claude, neon, fly).

Same SQLite-on-a-Fly-volume pattern as incidents.py. Only the most recent
payload per source is kept: these are point-in-time figures pushed by
external jobs, and the app never holds provider credentials itself.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator, Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS metric_snapshots (
    source TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    reported_at TEXT NOT NULL
);
"""

_db_path: str = "./aisaac_metrics.db"


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


def save(source: str, payload_json: str) -> None:
    with _connect() as conn:
        conn.execute(
            "INSERT INTO metric_snapshots (source, payload, reported_at) VALUES (?, ?, ?) "
            "ON CONFLICT(source) DO UPDATE SET payload = excluded.payload, "
            "reported_at = excluded.reported_at",
            (source, payload_json, datetime.now(timezone.utc).isoformat()),
        )


def load(source: str) -> Optional[sqlite3.Row]:
    with _connect() as conn:
        return conn.execute(
            "SELECT payload, reported_at FROM metric_snapshots WHERE source = ?", (source,)
        ).fetchone()
