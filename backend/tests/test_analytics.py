import asyncio
from datetime import datetime, timezone

import httpx

from app import main
from app.main import app
from app.schemas import RepoActivity


async def _request(method: str, path: str, **kwargs) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path, **kwargs)


def test_analytics_endpoint_returns_github_monitor_output(monkeypatch) -> None:
    fixture = RepoActivity(
        repo_id="nfl-confidence",
        name="NFL Confidence",
        category="Sports",
        owner="isaacsilver13",
        repo="NFL_Confidence",
        ci_status="success",
        open_issue_count=2,
        open_pr_count=1,
        checked_at=datetime.now(timezone.utc),
    )

    async def fake_activity(repos, force_refresh=False):
        return [fixture]

    monkeypatch.setattr(main.github_monitor, "activity", fake_activity)

    response = asyncio.run(_request("GET", "/api/v1/analytics"))

    assert response.status_code == 200
    activity = response.json()
    assert activity == [fixture.model_dump(mode="json")]
