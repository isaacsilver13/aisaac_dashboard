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
_CACHE_SECONDS = 60.0
_cache: dict[str, tuple[float, list[dict[str, Any]]]] = {}


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
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    response.raise_for_status()
    body = response.json()
    node = ((body.get("data") or {}).get("app") or {}).get("releases", {}).get("nodes")
    if node is None:
        raise ValueError(f"Fly returned no releases for {app}")
    _cache[app] = (time.monotonic(), node)
    return node
