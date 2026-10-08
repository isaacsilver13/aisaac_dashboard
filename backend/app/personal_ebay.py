"""eBay Browse API price search using an application token (client-credentials flow).

Public listings only; no eBay account is involved. Endpoint shapes follow eBay's documented
OAuth token and Browse item_summary/search APIs but have not been exercised against the live
service (no keys yet), so treat the first real run as a smoke test.
"""

from __future__ import annotations

import time
from typing import Callable, Optional

import httpx

TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
SEARCH_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"
SCOPE = "https://api.ebay.com/oauth/api_scope"
LIMIT = 25

_token: tuple[str, float] = ("", 0.0)  # cached: minting is capped at 1,000 a day


def _app_token(client_id: str, client_secret: str, post=httpx.post, now=time.time) -> str:
    global _token
    if _token[0] and now() < _token[1]:
        return _token[0]
    response = post(
        TOKEN_URL,
        data={"grant_type": "client_credentials", "scope": SCOPE},
        auth=(client_id, client_secret),
        timeout=10,
    )
    response.raise_for_status()
    body = response.json()
    _token = (body["access_token"], now() + int(body.get("expires_in", 7200)) - 60)
    return _token[0]


def make_provider(
    client_id: str, client_secret: str, get=httpx.get, post=httpx.post
) -> Optional[Callable[[dict], list[dict]]]:
    """A shoes provider, or None when credentials are missing."""
    if not client_id or not client_secret:
        return None

    def provider(watch: dict) -> list[dict]:
        token = _app_token(client_id, client_secret, post)
        response = get(
            SEARCH_URL,
            params={"q": watch.get("keywords") or watch["name"], "limit": LIMIT},
            headers={"Authorization": f"Bearer {token}", "X-EBAY-C-MARKETPLACE-ID": "EBAY_US"},
            timeout=10,
        )
        response.raise_for_status()
        out = []
        for item in response.json().get("itemSummaries", []):
            price = item.get("price") or {}
            usd = price.get("currency", "USD") == "USD"
            out.append({
                "key": item.get("itemId"),
                "title": item.get("title"),
                "price": price.get("value") if usd else None,
                "condition": item.get("condition"),
                "source": "eBay",
                "url": item.get("itemWebUrl"),
            })
        return out

    return provider
