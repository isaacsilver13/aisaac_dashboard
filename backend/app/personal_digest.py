"""Daily digest: a pure renderer plus an exactly-once-per-local-day runner.

The scheduler (cron-job.org, 08:00 America/Chicago) only calls the endpoint; this
module decides whether to send. It sends when the Chicago local time is 8:00 or
later and no digest was sent for that local date, so a late or retried call still
delivers once and an early call (or DST drift) is a no-op.
"""

from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Callable, Optional
from zoneinfo import ZoneInfo

from . import personal_news, personal_store

TZ = ZoneInfo("America/Chicago")
SEND_HOUR = 8
MAX_ITEMS = 12
PER_TOPIC = 2


def local_date(now: datetime) -> str:
    """The idempotency key: the America/Chicago calendar date."""
    return now.astimezone(TZ).date().isoformat()


def render(items: list[dict], freshness: Optional[str], now: datetime) -> tuple[str, str, str]:
    """Return (subject, plaintext, html). Pure: no I/O."""
    day = now.astimezone(TZ).strftime("%a %b %d").replace(" 0", " ")
    subject = f"AIsaac digest — {day}"
    fresh = (
        f"News as of {datetime.fromisoformat(freshness).astimezone(TZ):%b %d %I:%M %p %Z}"
        if freshness else "News freshness unknown (no successful refresh yet)"
    )
    if not items:
        return subject, f"{subject}\n\nNo new reading picks.\n{fresh}\n", (
            f"<h2>{html.escape(subject)}</h2><p>No new reading picks.</p>"
            f"<p><small>{fresh}</small></p>"
        )
    lines = [subject, "", "Reading picks"]
    rows = []
    for it in items:
        lines.append(f"- [{it['topic']}] {it['title']} ({it['source']})\n  {it['url']}")
        rows.append(
            f"<li>[{html.escape(it['topic'])}] <a href=\"{html.escape(it['url'], quote=True)}\">"
            f"{html.escape(it['title'])}</a> <small>({html.escape(it['source'])})</small></li>"
        )
    lines += ["", fresh]
    body = (
        f"<h2>{html.escape(subject)}</h2><h3>Reading picks</h3><ul>{''.join(rows)}</ul>"
        f"<p><small>{fresh}</small></p>"
    )
    return subject, "\n".join(lines) + "\n", body


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
        subject, text, _ = render(pick_items(), personal_store.freshness_at(), now)
        return {"status": "dry_run", "local_date": key, "subject": subject, "text": text}
    if now.astimezone(TZ).hour < SEND_HOUR:
        return {"status": "too_early", "local_date": key}
    if not personal_store.claim_run(key):
        return {"status": "already_handled", "local_date": key}

    try:
        refresh()  # best effort: per-feed errors are isolated and the last snapshot is kept
        freshness = personal_store.freshness_at()
        subject, text, body = render(pick_items(), freshness, now)
        ok = send(subject, text, body)
    except Exception:  # release the slot so a retry can run; never leak details
        personal_store.finish_run(key, "failed", error="send_error")
        raise
    if ok:
        personal_store.finish_run(key, "sent", freshness)
        return {"status": "sent", "local_date": key}
    personal_store.finish_run(key, "skipped", freshness, "email_not_sent")
    return {"status": "skipped", "local_date": key}
