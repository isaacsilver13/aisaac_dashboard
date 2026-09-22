from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx

GITHUB_API_BASE = "https://api.github.com"


def _headers(token: str) -> dict[str, str]:
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


async def get_latest_run_status(
    client: httpx.AsyncClient, token: str, owner: str, repo: str, timeout: float
) -> Optional[tuple[str, Optional[str]]]:
    """Returns (status, conclusion) for the most recent workflow run, or None on failure."""
    try:
        response = await client.get(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/actions/runs",
            params={"per_page": 1},
            headers=_headers(token),
            timeout=timeout,
        )
        response.raise_for_status()
        payload: dict[str, Any] = response.json()
    except (httpx.HTTPError, ValueError):
        return None
    runs = payload.get("workflow_runs") or []
    if not runs:
        return None
    latest = runs[0]
    return latest.get("status"), latest.get("conclusion")


async def get_open_issue_count(
    client: httpx.AsyncClient, token: str, owner: str, repo: str, timeout: float
) -> Optional[int]:
    try:
        response = await client.get(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/issues",
            params={"state": "open", "per_page": 100},
            headers=_headers(token),
            timeout=timeout,
        )
        response.raise_for_status()
        items: list[dict[str, Any]] = response.json()
    except (httpx.HTTPError, ValueError):
        return None
    return sum(1 for item in items if "pull_request" not in item)


async def get_open_pull_requests(
    client: httpx.AsyncClient, token: str, owner: str, repo: str, timeout: float, stale_days: int
) -> Optional[list[dict[str, Any]]]:
    try:
        response = await client.get(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/pulls",
            params={"state": "open", "per_page": 100},
            headers=_headers(token),
            timeout=timeout,
        )
        response.raise_for_status()
        items: list[dict[str, Any]] = response.json()
    except (httpx.HTTPError, ValueError):
        return None

    now = datetime.now(timezone.utc)
    stale_after = timedelta(days=stale_days)
    summaries = []
    for item in items:
        opened_at = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
        summaries.append(
            {
                "number": item["number"],
                "title": item["title"],
                "url": item["html_url"],
                "opened_at": opened_at,
                "stale": now - opened_at > stale_after,
            }
        )
    return summaries


async def get_commit_activity(
    client: httpx.AsyncClient, token: str, owner: str, repo: str, timeout: float
) -> Optional[tuple[int, Optional[datetime]]]:
    """Returns (commit count in the last 7 days, timestamp of the latest commit)."""
    since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    try:
        response = await client.get(
            f"{GITHUB_API_BASE}/repos/{owner}/{repo}/commits",
            params={"since": since, "per_page": 100},
            headers=_headers(token),
            timeout=timeout,
        )
        response.raise_for_status()
        items: list[dict[str, Any]] = response.json()
    except (httpx.HTTPError, ValueError):
        return None

    last_commit_at: Optional[datetime] = None
    if items:
        latest_raw = items[0]["commit"]["committer"]["date"]
        last_commit_at = datetime.fromisoformat(latest_raw.replace("Z", "+00:00"))
    return len(items), last_commit_at
