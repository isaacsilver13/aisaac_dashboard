"""What the dashboard knows about its automations: when each last ran, and whether that is late.

Nothing here schedules anything. Push jobs run externally (scripts/ or a GitHub Action) and the
dashboard only sees their last report. `expected_hours` is the cadence we expect, used purely to
flag a job as stale; adjust it here if a job's real schedule differs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from . import ci_events, health_history, metrics_store, second_brain_store

# (id, name, metrics source, expected_hours)
_PUSH_JOBS = (
    ("claude-usage", "Claude usage push", "claude", 2.0),
    ("codex-usage", "Codex usage push", "codex", 2.0),
    ("neon-usage", "Neon usage push", "neon", 26.0),
    ("fly-costs", "Fly cost push", "fly", 26.0),
)


def _age_hours(iso: str, now: datetime) -> float:
    return (now - datetime.fromisoformat(iso)).total_seconds() / 3600


def _row(
    id_: str, name: str, kind: str, detail: str, last: Optional[str], expected: Optional[float],
    now: datetime,
) -> dict[str, Any]:
    if last is None:
        status = "never"
    elif expected is not None and _age_hours(last, now) > expected:
        status = "stale"
    else:
        status = "ok"
    return {
        "id": id_, "name": name, "kind": kind, "detail": detail,
        "last_run_at": last, "expected_hours": expected, "status": status,
    }


def snapshot(poll_interval_seconds: float, now: Optional[datetime] = None) -> list[dict[str, Any]]:
    now = now or datetime.now(timezone.utc)
    rows = []
    for id_, name, source, expected in _PUSH_JOBS:
        stored = metrics_store.load(source)
        rows.append(_row(
            id_, name, "push", "scripts/ via /internal/metrics",
            stored["reported_at"] if stored else None, expected, now,
        ))
    brain = second_brain_store.summary()
    rows.append(_row(
        "second-brain", "Second brain sync", "push", "scripts/second_brain_push.py",
        brain["pushed_at"] if brain else None, 26.0, now,
    ))
    events = ci_events.list_events(limit=1)
    rows.append(_row(
        "ci-events", "CI event reports", "event", "GitHub Actions daily workflow",
        events[0]["received_at"] if events else None, 26.0, now,
    ))
    if poll_interval_seconds > 0:
        last = health_history.latest()
        rows.append(_row(
            "health-poll", "Health poller", "poller",
            f"in-process, every {poll_interval_seconds:g}s",
            last, poll_interval_seconds * 3 / 3600, now,
        ))
    else:
        rows.append({
            "id": "health-poll", "name": "Health poller", "kind": "poller",
            "detail": "disabled (HEALTH_POLL_INTERVAL_SECONDS=0)", "last_run_at": None,
            "expected_hours": None, "status": "disabled",
        })
    return rows
