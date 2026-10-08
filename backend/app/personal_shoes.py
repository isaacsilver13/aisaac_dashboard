"""User-managed shoe watches: official release links plus optional listing search.

No marketplace provider is approved (eBay Browse needs production approval), so `PROVIDER` is
None and watches are saved searches/release links the user opens themselves. The dashboard never
buys, bids, signs in or scrapes. A provider takes a watch and returns raw listing dicts.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

from . import personal_store

logger = logging.getLogger("aisaac.personal")

KINDS = ("search", "release", "stockx")
Provider = Callable[[dict], list[dict]]
PROVIDER: Optional[Provider] = None  # eBay Browse search, for "search" watches
STOCKX_PROVIDER: Optional[Provider] = None  # StockX lowest ask, for "stockx" watches


def matches(watch: dict, listing: dict) -> bool:
    cap = watch.get("max_price")
    return cap is None or listing.get("price") is None or listing["price"] <= cap


def normalize(raw: dict) -> Optional[dict]:
    url = str(raw.get("url") or "")
    if not raw.get("key") or not raw.get("title") or not url.startswith(("http://", "https://")):
        return None
    try:
        price = float(raw["price"]) if raw.get("price") is not None else None
    except (TypeError, ValueError):
        price = None
    return {
        "key": str(raw["key"]),
        "title": str(raw["title"]),
        "price": price,
        "condition": raw.get("condition"),
        "source": str(raw.get("source", "marketplace")),
        "url": url,
    }


def refresh(provider: Optional[Provider] = None, stockx: Optional[Provider] = None) -> str:
    """Refresh search and StockX watches. Returns 'ok', 'not_configured' or 'fetch_failed'."""
    providers = {"search": provider or PROVIDER, "stockx": stockx or STOCKX_PROVIDER}
    if not any(providers.values()):
        personal_store.record_refresh("sports_refreshes", "shoes", "not_configured")
        return "not_configured"
    failed = False
    for watch in personal_store.list_watches():
        fetch = providers.get(watch["kind"])
        if fetch is None:
            continue
        try:
            listings = [x for x in map(normalize, fetch(watch)) if x]
        except Exception:
            logger.warning("shoe refresh failed", exc_info=True)
            failed = True
            continue
        for listing in listings:
            if matches(watch, listing):
                personal_store.observe_listing(watch["id"], listing)
    personal_store.record_refresh("sports_refreshes", "shoes", "fetch_failed" if failed else None)
    return "fetch_failed" if failed else "ok"


def recent_changes(now: Optional[datetime] = None, hours: int = 24) -> list[dict]:
    now = now or datetime.now(timezone.utc)
    return personal_store.list_listings(changed_since=(now - timedelta(hours=hours)).isoformat())
