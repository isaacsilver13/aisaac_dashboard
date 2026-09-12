"""In-memory store for pushed heartbeats from apps that can't be polled.

nba_prediction has no server at all; vinyl_app is Streamlit with no natural
place for custom JSON routes. Both push a small heartbeat here instead of
being polled. A report older than stale_report_after_hours is treated as
"stale/unknown" rather than "down" -- it's a different, honest state: we
simply haven't heard from the app recently, which is not the same claim as
having observed it failing.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Optional


@dataclass
class PushedReport:
    app_id: str
    status: str
    metrics: dict[str, Any]
    received_at: datetime


_reports: dict[str, PushedReport] = {}


def record_report(app_id: str, status: str, metrics: dict[str, Any]) -> None:
    _reports[app_id] = PushedReport(
        app_id=app_id,
        status=status,
        metrics=metrics,
        received_at=datetime.now(timezone.utc),
    )


def get_report(app_id: str, stale_after_hours: float) -> Optional[PushedReport]:
    report = _reports.get(app_id)
    if report is None:
        return None
    age = datetime.now(timezone.utc) - report.received_at
    if age > timedelta(hours=stale_after_hours):
        return None
    return report
