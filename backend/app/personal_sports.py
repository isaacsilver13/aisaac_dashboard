"""Private sports schedule/results behind a provider boundary.

No live provider is approved yet (see docs/personal-feeds-providers.md), so `PROVIDER` is None
and the page shows official scoreboard links. A provider is a callable returning raw event
dicts; `normalize` is the only place that shape is interpreted. Rankings are never inferred.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Callable, Optional

from . import personal_store

logger = logging.getLogger("aisaac.personal")

LEAGUES = ("NFL", "NBA", "MLB", "NCAAF", "NCAAB")
PRIORITY_TEAMS = {"Chicago Bears": "NFL", "Chicago Bulls": "NBA", "Chicago White Sox": "MLB"}
OFFICIAL_LINKS = {
    "NFL": "https://www.nfl.com/scores/",
    "NBA": "https://www.nba.com/games",
    "MLB": "https://www.mlb.com/scores",
    "NCAAF": "https://www.ncaa.com/scoreboard/football/fbs",
    "NCAAB": "https://www.ncaa.com/scoreboard/basketball-men/d1",
}
POLL_MAX_AGE = timedelta(days=8)
STATUSES = ("scheduled", "live", "final", "postponed")

Provider = Callable[[], list[dict]]
PROVIDER: Optional[Provider] = None  # ponytail: wire a documented provider here once approved


def _int(value) -> Optional[int]:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def normalize(raw: dict) -> Optional[dict]:
    """Return a store-ready event, or None when the row is unusable."""
    league = str(raw.get("league", "")).upper()
    if league not in LEAGUES or not raw.get("id") or not raw.get("home") or not raw.get("away"):
        return None
    try:
        start = datetime.fromisoformat(str(raw["start_at"]).replace("Z", "+00:00"))
    except (KeyError, ValueError):
        return None
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    url = str(raw.get("url") or "")
    status = str(raw.get("status", "scheduled")).lower()
    rank_h, rank_a = _int(raw.get("home_rank")), _int(raw.get("away_rank"))
    ranked = any(r is not None for r in (rank_h, rank_a))
    return {
        "id": str(raw["id"]),
        "league": league,
        "home": str(raw["home"]),
        "away": str(raw["away"]),
        "home_score": _int(raw.get("home_score")),
        "away_score": _int(raw.get("away_score")),
        "status": status if status in STATUSES else "scheduled",
        "start_at": start.astimezone(timezone.utc).isoformat(),
        "home_conference": raw.get("home_conference"),
        "away_conference": raw.get("away_conference"),
        "home_rank": rank_h,
        "away_rank": rank_a,
        "poll_date": raw.get("poll_date") if ranked else None,
        "url": url if url.startswith(("http://", "https://")) else OFFICIAL_LINKS[league],
    }


def refresh(provider: Optional[Provider] = None) -> str:
    """Returns 'ok', 'not_configured' or 'fetch_failed'; the last good snapshot always stays."""
    provider = provider or PROVIDER
    if provider is None:
        personal_store.record_refresh("sports_refreshes", "sports", "not_configured")
        return "not_configured"
    try:
        events = [e for e in map(normalize, provider()) if e]
    except Exception:  # never surface upstream detail
        logger.warning("sports refresh failed", exc_info=True)
        personal_store.record_refresh("sports_refreshes", "sports", "fetch_failed")
        return "fetch_failed"
    for event in events:
        personal_store.upsert_event(event)
    personal_store.record_refresh("sports_refreshes", "sports", None)
    return "ok"


def rankings_status(now: Optional[datetime] = None) -> dict:
    """Top-25 is 'current' only when the stored poll date is recent; otherwise unavailable."""
    now = now or datetime.now(timezone.utc)
    poll = personal_store.latest_poll_date()
    current = False
    if poll:
        try:
            current = now.date() - date.fromisoformat(poll[:10]) <= POLL_MAX_AGE
        except ValueError:
            current = False
    return {"poll_date": poll, "current": current}


def query(
    league=None, team=None, conference=None, top_25_only=False, date_from=None, date_to=None,
    now: Optional[datetime] = None,
) -> dict:
    ranks = rankings_status(now)
    events = [] if top_25_only and not ranks["current"] else personal_store.list_events(
        league, team, conference, top_25_only, date_from, date_to
    )
    return {"events": events, "rankings": ranks}


def priority_events(now: datetime, days: int = 2) -> list[dict]:
    """Priority-team games from the last day to `days` ahead, for cards and the digest."""
    lo, hi = (now - timedelta(days=1)).isoformat(), (now + timedelta(days=days)).isoformat()
    out = []
    for team in PRIORITY_TEAMS:
        out += personal_store.list_events(team=team, date_from=lo, date_to=hi)
    return sorted(out, key=lambda e: e["start_at"])
