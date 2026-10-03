"""Second-brain vault notes pushed by scripts/second_brain_push.py.

Same SQLite-on-a-Fly-volume pattern as metrics_store.py. Each sync replaces the
whole set (the vault is the source of truth), so deletions propagate. Reads never
touch the filesystem: a path is only ever looked up as a key.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Iterator, Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS notes (
    path TEXT PRIMARY KEY, folder TEXT NOT NULL, title TEXT NOT NULL,
    aliases TEXT NOT NULL, status TEXT, body TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS meta (
    id INTEGER PRIMARY KEY CHECK (id = 1), payload TEXT NOT NULL, pushed_at TEXT NOT NULL
);
"""

_db_path: str = "./aisaac_second_brain.db"


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


def replace_all(meta: dict, notes: list[dict]) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM notes")
        conn.executemany(
            "INSERT INTO notes (path, folder, title, aliases, status, body) VALUES (?,?,?,?,?,?)",
            [
                (
                    n["path"],
                    n["folder"],
                    n["title"],
                    json.dumps(n["aliases"]),
                    n["status"],
                    n["body"],
                )
                for n in notes
            ],
        )
        conn.execute(
            "INSERT INTO meta (id, payload, pushed_at) VALUES (1, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET payload = excluded.payload, "
            "pushed_at = excluded.pushed_at",
            (json.dumps(meta), datetime.now(timezone.utc).isoformat()),
        )


def summary() -> Optional[dict]:
    with _connect() as conn:
        row = conn.execute("SELECT payload, pushed_at FROM meta WHERE id = 1").fetchone()
        if row is None:
            return None
        counts = {
            r["folder"]: r["n"]
            for r in conn.execute("SELECT folder, COUNT(*) AS n FROM notes GROUP BY folder")
        }
    return {**json.loads(row["payload"]), "counts": counts, "pushed_at": row["pushed_at"]}


def list_notes(q: str = "", folder: str = "") -> list[dict]:
    sql, args = "SELECT path, folder, title, aliases, status FROM notes WHERE 1=1", []
    if folder:
        sql += " AND folder = ?"
        args.append(folder)
    if q:
        sql += " AND (title LIKE ? OR aliases LIKE ? OR body LIKE ?)"
        args += [f"%{q}%"] * 3
    with _connect() as conn:
        rows = conn.execute(sql + " ORDER BY folder, title LIMIT 500", args).fetchall()
    return [{**dict(r), "aliases": json.loads(r["aliases"])} for r in rows]


def get_note(path: str) -> Optional[dict]:
    with _connect() as conn:
        r = conn.execute("SELECT * FROM notes WHERE path = ?", (path,)).fetchone()
    return None if r is None else {**dict(r), "aliases": json.loads(r["aliases"])}
