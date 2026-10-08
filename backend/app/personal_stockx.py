"""StockX: your active listings and sales, plus lowest-ask price tracking. Read-only.

Endpoints and fields come from StockX's published swagger (/v2/selling/listings,
/v2/selling/orders/history, /v2/catalog/*) and auth docs (refresh grant on accounts.stockx.com,
`x-api-key` header). The public API is seller-side only: no buyer purchase history, watchlist or
buy-side bids exist, so those are not fetched.
"""

from __future__ import annotations

import time
from typing import Callable, Optional

import httpx

API = "https://api.stockx.com/v2"
TOKEN_URL = "https://accounts.stockx.com/oauth/token"
MAX_PAGES = 5  # 5 x 100 rows per list
PACE = 1.05  # seconds between API calls: StockX allows 1 request/second, 25k/day
SIZES = ("10", "10.5")  # the only sizes watches may track

_tokens: dict[str, tuple[str, float]] = {}  # refresh token -> (access token, expiry); 12h lifetime
_last_call = 0.0


def _pace() -> None:
    # ponytail: process-wide spacing; a shared limiter if more than one worker ever calls StockX
    global _last_call
    wait = PACE - (time.monotonic() - _last_call)
    if wait > 0:
        time.sleep(wait)
    _last_call = time.monotonic()


def _headers(client_id, client_secret, api_key, refresh_token, post) -> dict:
    cached = _tokens.get(refresh_token)
    if not cached or time.time() >= cached[1]:
        _pace()
        grant = post(
            TOKEN_URL,
            data={
                "grant_type": "refresh_token",
                "client_id": client_id,
                "client_secret": client_secret,
                "audience": "gateway.stockx.com",
                "refresh_token": refresh_token,
            },
            timeout=10,
        )
        grant.raise_for_status()
        body = grant.json()
        cached = (body["access_token"], time.time() + int(body.get("expires_in", 43200)) - 300)
        _tokens[refresh_token] = cached
    return {"Authorization": f"Bearer {cached[0]}", "x-api-key": api_key}


def _json(get, path: str, params: Optional[dict], headers: dict):
    _pace()
    response = get(f"{API}{path}", params=params, headers=headers, timeout=10)
    response.raise_for_status()
    return response.json()


def _pages(get, path: str, params: dict, headers: dict, rows_key: str):
    for page in range(1, MAX_PAGES + 1):
        body = _json(get, path, {**params, "pageNumber": page, "pageSize": 100}, headers)
        yield from body.get(rows_key, [])
        if not body.get("hasNextPage"):
            return


def _title(row: dict) -> str:
    product, variant = row.get("product") or {}, row.get("variant") or {}
    return " ".join(filter(None, [product.get("productName"), variant.get("variantValue")]))


def make_fetcher(
    client_id: str, client_secret: str, api_key: str,
    get: Callable = httpx.get, post: Callable = httpx.post,
) -> Optional[Callable[[str], list[dict]]]:
    """Own data: active listings (asks) and sales history."""
    if not (client_id and client_secret and api_key):
        return None

    def fetch(refresh_token: str) -> list[dict]:
        headers = _headers(client_id, client_secret, api_key, refresh_token, post)
        items = [
            {
                "kind": "listing", "id": r.get("listingId"), "title": _title(r),
                "price": r.get("amount"), "occurred_at": r.get("createdAt"),
            }
            for r in _pages(get, "/selling/listings", {"listingStatuses": "ACTIVE"}, headers,
                            "listings")
        ]
        items += [
            {
                "kind": "sale", "id": r.get("orderNumber"), "title": _title(r),
                "price": (r.get("payout") or {}).get("salePrice") or r.get("amount"),
                "occurred_at": r.get("createdAt"),
            }
            for r in _pages(get, "/selling/orders/history", {}, headers, "orders")
        ]
        return items

    return fetch


def _size_matches(variant: dict, size: str) -> bool:
    chart = variant.get("sizeChart") or {}
    conversions = [chart.get("defaultConversion") or {}, *chart.get("availableConversions", [])]
    return variant.get("variantValue") == size or any(
        c.get("size") == size and c.get("type") == "us m" for c in conversions
    )


def make_market_provider(
    client_id: str, client_secret: str, api_key: str, load_token: Callable[[], Optional[str]],
    get: Callable = httpx.get, post: Callable = httpx.post,
) -> Optional[Callable[[dict], list[dict]]]:
    """Shoe-watch provider: lowest ask for the watch's size on the best catalog match.

    The match is the first catalog search hit, so use a style code in the watch keywords; the
    listing title shows which product was matched.
    """
    if not (client_id and client_secret and api_key):
        return None

    def provider(watch: dict) -> list[dict]:
        refresh_token = load_token()
        size = watch.get("size")
        if refresh_token is None:
            raise LookupError("stockx not connected")  # surfaces as fetch_failed, not a fresh "ok"
        if size not in SIZES:
            return []
        headers = _headers(client_id, client_secret, api_key, refresh_token, post)
        found = _json(get, "/catalog/search",
                      {"query": watch.get("keywords") or watch["name"], "pageSize": 1}, headers)
        if not found.get("products"):
            return []
        product = found["products"][0]
        variants = _json(get, f"/catalog/products/{product['productId']}/variants", None, headers)
        variant = next((v for v in variants if _size_matches(v, size)), None)
        if variant is None:
            return []
        market = _json(
            get, f"/catalog/products/{product['productId']}/variants/{variant['variantId']}"
            "/market-data", {"currencyCode": "USD"}, headers,
        )
        return [{
            "key": variant["variantId"],
            "title": f"{product.get('title') or watch['name']} · size {size}",
            "price": market.get("lowestAskAmount"),
            "condition": "New",
            "source": "StockX",
            "url": f"https://stockx.com/{product['urlKey']}",
        }]

    return provider
