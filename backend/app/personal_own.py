"""Your own purchases, watchlist, open bids/asks and listings from connected accounts.

Read-only. `FETCHERS` maps a provider to a callable (refresh_token) -> raw item dicts; it is empty
until a provider's API is wired in. Failures keep the last stored rows.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

from . import personal_store, personal_vault

logger = logging.getLogger("aisaac.personal")

KINDS = ("purchase", "watch", "bid", "listing", "sale")
Fetcher = Callable[[str], list[dict]]
FETCHERS: dict[str, Fetcher] = {}  # ponytail: add eBay/StockX fetchers once docs are read


def normalize(provider: str, raw: dict) -> Optional[dict]:
    url = str(raw.get("url") or "")
    if raw.get("kind") not in KINDS or not raw.get("id") or not raw.get("title"):
        return None
    try:
        price = float(raw["price"]) if raw.get("price") is not None else None
    except (TypeError, ValueError):
        price = None
    return {
        "provider": provider,
        "kind": raw["kind"],
        "external_id": str(raw["id"]),
        "title": str(raw["title"]),
        "price": price,
        "url": url if url.startswith(("http://", "https://")) else None,
        "occurred_at": raw.get("occurred_at"),
    }


def refresh(key: str, fetchers: Optional[dict[str, Fetcher]] = None) -> dict[str, str]:
    """Per-provider result: 'ok', 'not_connected' or 'fetch_failed'."""
    results = {}
    for provider, fetch in (FETCHERS if fetchers is None else fetchers).items():
        try:
            token = personal_vault.load_token(provider, key)
        except personal_vault.VaultError:
            results[provider] = "fetch_failed"
            continue
        if token is None:
            results[provider] = "not_connected"
            continue
        try:
            items = [i for i in (normalize(provider, r) for r in fetch(token)) if i]
        except Exception:
            logger.warning("own-data refresh failed", exc_info=True)
            results[provider] = "fetch_failed"
            continue
        for item in items:
            personal_store.upsert_own_item(item)
        results[provider] = "ok"
    return results
