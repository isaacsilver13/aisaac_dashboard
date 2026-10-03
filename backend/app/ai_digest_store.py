"""Daily AI news digests pushed by scripts/ai_digest_push.py.

Same SQLite-on-a-Fly-volume pattern as second_brain_store.py. One row per digest date; pushing the
same date again replaces it, and anything beyond the retention window is pruned on each save. The
payload is stored as the validated JSON the push script sent, so reads never fetch anything.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
from typing import Iterator, Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS digests (
    digest_date TEXT PRIMARY KEY, payload TEXT NOT NULL, pushed_at TEXT NOT NULL
);
"""

_db_path: str = "./aisaac_ai_digest.db"
_retention_days: int = 30


def configure(db_path: str, retention_days: int = 30) -> None:
    global _db_path, _retention_days
    _db_path = db_path
    _retention_days = retention_days
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


def save(digest_date: str, payload_json: str) -> None:
    cutoff = (date.fromisoformat(digest_date) - timedelta(days=_retention_days)).isoformat()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO digests (digest_date, payload, pushed_at) VALUES (?,?,?) "
            "ON CONFLICT(digest_date) DO UPDATE SET payload = excluded.payload, "
            "pushed_at = excluded.pushed_at",
            (digest_date, payload_json, datetime.now(timezone.utc).isoformat()),
        )
        conn.execute("DELETE FROM digests WHERE digest_date < ?", (cutoff,))


def _load(row: Optional[sqlite3.Row]) -> Optional[dict]:
    if row is None:
        return None
    return {**json.loads(row["payload"]), "pushed_at": row["pushed_at"]}


def latest() -> Optional[dict]:
    with _connect() as conn:
        return _load(
            conn.execute("SELECT * FROM digests ORDER BY digest_date DESC LIMIT 1").fetchone()
        )


def get(digest_date: str) -> Optional[dict]:
    with _connect() as conn:
        return _load(
            conn.execute("SELECT * FROM digests WHERE digest_date = ?", (digest_date,)).fetchone()
        )


def dates() -> list[str]:
    with _connect() as conn:
        return [
            r["digest_date"]
            for r in conn.execute("SELECT digest_date FROM digests ORDER BY digest_date DESC")
        ]


def last_pushed_at() -> Optional[str]:
    with _connect() as conn:
        row = conn.execute("SELECT MAX(pushed_at) AS p FROM digests").fetchone()
    return row["p"]
