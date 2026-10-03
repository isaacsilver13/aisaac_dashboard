"""Release history for a Fly app (Deployments tab). Read-only GraphQL query."""

from __future__ import annotations

import time
from typing import Any

import httpx

FLY_GRAPHQL = "https://api.fly.io/graphql"
_QUERY = (
    "query($n:String!,$k:Int!){app(name:$n){releases(first:$k){nodes"
    "{version status description reason createdAt imageRef}}}}"
)
FLY_LOGS = "https://api.fly.io/api/v1/apps/{app}/logs"
_CACHE_SECONDS = 60.0
_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}


def _auth(token: str) -> str:
    """Macaroon tokens (`fly tokens create`, fm*) use the FlyV1 scheme; legacy ones use Bearer."""
    if " " in token:
        return token
    return f"FlyV1 {token}" if token.startswith("fm") else f"Bearer {token}"


async def releases(
    client: httpx.AsyncClient, token: str, app: str, limit: int = 20
) -> list[dict[str, Any]]:
    """Newest-first releases. Raises httpx.HTTPError / ValueError on failure. Cached briefly."""
    hit = _cache.get(app)
    if hit and time.monotonic() - hit[0] < _CACHE_SECONDS:
        return hit[1]
    response = await client.post(
        FLY_GRAPHQL,
        json={"query": _QUERY, "variables": {"n": app, "k": limit}},
        headers={"Authorization": _auth(token)},
        timeout=10,
    )
    response.raise_for_status()
    body = response.json()
    node = ((body.get("data") or {}).get("app") or {}).get("releases", {}).get("nodes")
    if node is None:
        raise ValueError(f"Fly returned no releases for {app}")
    _cache[app] = (time.monotonic(), node)
    return node


async def logs(client: httpx.AsyncClient, token: str, app: str) -> list[dict[str, Any]]:
    """Most recent log lines (Fly returns the latest ~100), oldest first. Not cached."""
    response = await client.get(
        FLY_LOGS.format(app=app), headers={"Authorization": _auth(token)}, timeout=10
    )
    response.raise_for_status()
    rows = [(r.get("attributes") or {}) for r in response.json().get("data", [])]
    keys = ("timestamp", "level", "message", "instance", "region")
    return sorted(({k: a.get(k) for k in keys} for a in rows), key=lambda r: r["timestamp"] or "")
