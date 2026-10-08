"""Daily digest: a pure renderer plus an exactly-once-per-local-day runner.

The scheduler (cron-job.org, 08:00 America/Chicago) only calls the endpoint; this
module decides whether to send. It sends when the Chicago local time is 8:00 or
later and no digest was sent for that local date, so a late or retried call still
delivers once and an early call (or DST drift) is a no-op.
"""

from __future__ import annotations

import html
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional
from zoneinfo import ZoneInfo

from . import personal_news, personal_shoes, personal_sports, personal_store

TZ = ZoneInfo("America/Chicago")
SEND_HOUR = 8
MAX_ITEMS = 12
PER_TOPIC = 2


def local_date(now: datetime) -> str:
    """The idempotency key: the America/Chicago calendar date."""
    return now.astimezone(TZ).date().isoformat()


def _fmt(value: str) -> str:
    local = datetime.fromisoformat(value).astimezone(TZ)
    return local.strftime("%a %b %d %I:%M %p").replace(" 0", " ")


def _game_line(g: dict) -> str:
    score = ""
    if g["home_score"] is not None and g["away_score"] is not None:
        score = f" {g['away_score']}-{g['home_score']}"
    return f"{g['away']} at {g['home']}{score} ({g['status']}, {_fmt(g['start_at'])})"


def _shoe_line(x: dict) -> str:
    price = f"${x['price']:.2f}" if x["price"] is not None else "price n/a"
    if x.get("prev_price") is not None:
        was = f" (was ${x['prev_price']:.2f})"
    else:
        was = " (new)" if x.get("sightings", 1) == 1 else ""
    return f"{x['title']} - {price}{was}"


def _section(title: str, rows: list[tuple[str, str]]) -> tuple[list[str], str]:
    """(plaintext lines, html) for a list of (label, url) rows."""
    lines = ["", title] + [f"- {label}\n  {url}" for label, url in rows]
    items = "".join(
        f'<li><a href="{html.escape(url, quote=True)}">{html.escape(label)}</a></li>'
        for label, url in rows
    )
    return lines, f"<h3>{html.escape(title)}</h3><ul>{items}</ul>"


def render(
    items: list[dict], freshness: Optional[str], now: datetime,
    games: Optional[list[dict]] = None, shoes: Optional[list[dict]] = None,
) -> tuple[str, str, str]:
    """Return (subject, plaintext, html). Pure: no I/O."""
    day = now.astimezone(TZ).strftime("%a %b %d").replace(" 0", " ")
    subject = f"AIsaac digest — {day}"
    fresh = (
        f"News as of {datetime.fromisoformat(freshness).astimezone(TZ):%b %d %I:%M %p %Z}"
        if freshness else "News freshness unknown (no successful refresh yet)"
    )
    lines, parts = [subject], [f"<h2>{html.escape(subject)}</h2>"]
    sections = [
        ("Games", [(_game_line(g), g["url"]) for g in games or []]),
        ("Shoe watches", [(_shoe_line(x), x["url"]) for x in shoes or []]),
        ("Reading picks", [(f"[{i['topic']}] {i['title']} ({i['source']})", i["url"])
                           for i in items]),
    ]
    for title, rows in sections:
        if rows:
            more_lines, more_html = _section(title, rows)
            lines += more_lines
            parts.append(more_html)
    if not items:
        lines += ["", "No new reading picks."]
        parts.append("<p>No new reading picks.</p>")
    lines += ["", fresh]
    parts.append(f"<p><small>{html.escape(fresh)}</small></p>")
    return subject, "\n".join(lines) + "\n", "".join(parts)


def pick_games(now: datetime) -> list[dict]:
    """Priority-team games plus today's Top-25 college games (only while rankings are current)."""
    games = personal_sports.priority_events(now)
    if personal_sports.rankings_status(now)["current"]:
        lo = (now - timedelta(days=1)).isoformat()
        hi = (now + timedelta(days=1)).isoformat()
        seen = {g["id"] for g in games}
        games += [g for g in personal_store.list_events(top_25_only=True, date_from=lo, date_to=hi)
                  if g["id"] not in seen]
    return games[:MAX_ITEMS]


def pick_items() -> list[dict]:
    """Saved items first, then top-scored new ones, at most PER_TOPIC per topic for variety."""
    candidates = personal_store.list_items(state="saved", limit=200) + personal_store.list_items(
        state="new", limit=200
    )
    counts: dict[str, int] = {}
    picked = []
    for item in candidates:
        if counts.get(item["topic"], 0) < PER_TOPIC:
            counts[item["topic"]] = counts.get(item["topic"], 0) + 1
            picked.append(item)
    return picked[:MAX_ITEMS]


def run(
    now: Optional[datetime] = None,
    *,
    dry_run: bool = False,
    send: Callable[[str, str, str], bool],
    refresh: Callable[[], None] = personal_news.refresh,
) -> dict:
    """Refresh, render and (unless dry_run) send once for today's Chicago date."""
    now = now or datetime.now(timezone.utc)
    key = local_date(now)
    if dry_run:
        subject, text, _ = render(
            pick_items(), personal_store.freshness_at(), now,
            pick_games(now), personal_shoes.recent_changes(now),
        )
        return {"status": "dry_run", "local_date": key, "subject": subject, "text": text}
    if now.astimezone(TZ).hour < SEND_HOUR:
        return {"status": "too_early", "local_date": key}
    if not personal_store.claim_run(key):
        return {"status": "already_handled", "local_date": key}

    try:
        refresh()  # best effort: per-feed errors are isolated and the last snapshot is kept
        personal_sports.refresh()
        personal_shoes.refresh()
        freshness = personal_store.freshness_at()
        subject, text, body = render(
            pick_items(), freshness, now, pick_games(now), personal_shoes.recent_changes(now)
        )
        ok = send(subject, text, body)
    except Exception:  # release the slot so a retry can run; never leak details
        personal_store.finish_run(key, "failed", error="send_error")
        raise
    if ok:
        personal_store.finish_run(key, "sent", freshness)
        return {"status": "sent", "local_date": key}
    personal_store.finish_run(key, "skipped", freshness, "email_not_sent")
    return {"status": "skipped", "local_date": key}
