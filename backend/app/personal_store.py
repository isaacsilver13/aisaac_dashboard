"""Private news items, per-feed freshness and daily-digest runs.

Same SQLite-on-a-Fly-volume pattern as metrics_store.py. Migrations are
additive only (`CREATE TABLE IF NOT EXISTS`); nothing here ever drops data.
Feed state stores a short error *code*, never an upstream response body.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Iterator, Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS news_items (
    id INTEGER PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    topic TEXT NOT NULL,
    published_at TEXT NOT NULL,
    score REAL NOT NULL,
    why TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'new',
    first_seen_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_news_topic_score ON news_items (topic, score DESC);
CREATE INDEX IF NOT EXISTS idx_news_published ON news_items (published_at DESC);

CREATE TABLE IF NOT EXISTS news_sources (
    feed_url TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    last_ok_at TEXT,
    last_attempt_at TEXT,
    last_error TEXT
);

CREATE TABLE IF NOT EXISTS digest_runs (
    local_date TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    attempted_at TEXT NOT NULL,
    sent_at TEXT,
    freshness_at TEXT,
    error TEXT
);
"""

STATES = ("new", "saved", "dismissed")

_db_path: str = "./aisaac_personal.db"


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


def upsert_item(item: dict) -> None:
    """Insert a new article, or refresh score/title of a known URL; state is kept."""
    with _connect() as conn:
        conn.execute(
            "INSERT INTO news_items (url, title, source, topic, published_at, score, why, "
            "first_seen_at) VALUES (:url, :title, :source, :topic, :published_at, :score, :why, "
            ":now) ON CONFLICT(url) DO UPDATE SET title = excluded.title, "
            "score = excluded.score, why = excluded.why",
            {**item, "now": _now()},
        )


def list_items(
    topic: Optional[str] = None, state: Optional[str] = None, limit: int = 100
) -> list[dict]:
    """Newest-score-first; dismissed items are hidden unless asked for explicitly."""
    clauses, params = [], []
    if topic:
        clauses.append("topic = ?")
        params.append(topic)
    if state:
        clauses.append("state = ?")
        params.append(state)
    else:
        clauses.append("state != 'dismissed'")
    where = " WHERE " + " AND ".join(clauses)
    with _connect() as conn:
        rows = conn.execute(
            f"SELECT * FROM news_items{where} ORDER BY score DESC, published_at DESC LIMIT ?",
            (*params, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def set_state(item_id: int, state: str) -> bool:
    with _connect() as conn:
        return conn.execute(
            "UPDATE news_items SET state = ? WHERE id = ?", (state, item_id)
        ).rowcount == 1


def record_feed(feed_url: str, source: str, error: Optional[str]) -> None:
    """Freshness is separate from content: a failed fetch keeps `last_ok_at` and old items."""
    now = _now()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO news_sources (feed_url, source, last_ok_at, last_attempt_at, last_error) "
            "VALUES (?, ?, ?, ?, ?) ON CONFLICT(feed_url) DO UPDATE SET "
            "last_ok_at = COALESCE(excluded.last_ok_at, news_sources.last_ok_at), "
            "last_attempt_at = excluded.last_attempt_at, last_error = excluded.last_error",
            (feed_url, source, None if error else now, now, error),
        )


def list_feeds() -> list[dict]:
    with _connect() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM news_sources ORDER BY source")]


def freshness_at() -> Optional[str]:
    with _connect() as conn:
        row = conn.execute("SELECT MAX(last_ok_at) AS t FROM news_sources").fetchone()
    return row["t"]


def get_run(local_date: str) -> Optional[dict]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT * FROM digest_runs WHERE local_date = ?", (local_date,)
        ).fetchone()
    return dict(row) if row else None


def claim_run(local_date: str) -> bool:
    """Atomically take the day's send slot; False if already sent or another call holds it.

    A 'failed' or 'skipped' row may be re-claimed (retry), as may a 'sending' row left by a
    crashed call (older than the 10s send timeout by a wide margin); 'sent' never is.
    """
    now = _now()
    stale = (datetime.now(timezone.utc) - timedelta(minutes=15)).isoformat()
    with _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO digest_runs (local_date, status, attempted_at) "
            "VALUES (?, 'new', ?)",
            (local_date, now),
        )
        return conn.execute(
            "UPDATE digest_runs SET status = 'sending', attempted_at = ?, error = NULL "
            "WHERE local_date = ? AND (status IN ('new', 'failed', 'skipped') "
            "OR (status = 'sending' AND attempted_at < ?))",
            (now, local_date, stale),
        ).rowcount == 1


def finish_run(
    local_date: str, status: str, freshness_at: Optional[str] = None, error: Optional[str] = None
) -> None:
    with _connect() as conn:
        conn.execute(
            "UPDATE digest_runs SET status = ?, sent_at = ?, freshness_at = ?, error = ? "
            "WHERE local_date = ?",
            (status, _now() if status == "sent" else None, freshness_at, error, local_date),
        )
