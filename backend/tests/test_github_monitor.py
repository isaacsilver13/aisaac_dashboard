import asyncio
from datetime import datetime, timedelta, timezone

import httpx

from app.github_monitor import GitHubMonitor
from app.schemas import RepoDefinition


def _repo(**overrides) -> RepoDefinition:
    defaults = dict(id="fixture", name="Fixture", category="Test", owner="acme", repo="widgets")
    defaults.update(overrides)
    return RepoDefinition(**defaults)


def test_check_repo_reports_success_from_latest_run() -> None:
    repo = _repo()

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/actions/runs"):
            run = {"status": "completed", "conclusion": "success"}
            return httpx.Response(200, json={"workflow_runs": [run]})
        if request.url.path.endswith("/issues"):
            return httpx.Response(200, json=[])
        if request.url.path.endswith("/pulls"):
            return httpx.Response(200, json=[])
        if request.url.path.endswith("/commits"):
            return httpx.Response(200, json=[])
        return httpx.Response(404)

    async def run() -> object:
        monitor = GitHubMonitor(token="fixture-token")
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await monitor._check_repo(client, repo)

    result = asyncio.run(run())

    assert result.ci_status == "success"
    assert result.open_issue_count == 0
    assert result.open_pr_count == 0
    assert result.commits_last_7d == 0


def test_check_repo_reports_failure_conclusion() -> None:
    repo = _repo()

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/actions/runs"):
            run = {"status": "completed", "conclusion": "failure"}
            return httpx.Response(200, json={"workflow_runs": [run]})
        return httpx.Response(200, json=[])

    async def run() -> object:
        monitor = GitHubMonitor(token="fixture-token")
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await monitor._check_repo(client, repo)

    result = asyncio.run(run())

    assert result.ci_status == "failure"


def test_check_repo_filters_pull_requests_out_of_issue_count() -> None:
    repo = _repo()

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/actions/runs"):
            return httpx.Response(200, json={"workflow_runs": []})
        if request.url.path.endswith("/issues"):
            return httpx.Response(
                200,
                json=[{"pull_request": {}}, {"title": "a real issue"}],
            )
        if request.url.path.endswith("/pulls"):
            return httpx.Response(200, json=[])
        if request.url.path.endswith("/commits"):
            return httpx.Response(200, json=[])
        return httpx.Response(404)

    async def run() -> object:
        monitor = GitHubMonitor(token="fixture-token")
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await monitor._check_repo(client, repo)

    result = asyncio.run(run())

    assert result.open_issue_count == 1


def test_check_repo_flags_stale_pull_requests() -> None:
    repo = _repo(stale_days=3)
    stale_dt = datetime.now(timezone.utc) - timedelta(days=10)
    stale_opened_at = stale_dt.isoformat().replace("+00:00", "Z")
    fresh_opened_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/actions/runs"):
            return httpx.Response(200, json={"workflow_runs": []})
        if request.url.path.endswith("/issues"):
            return httpx.Response(200, json=[])
        if request.url.path.endswith("/pulls"):
            stale_pr = {
                "number": 1,
                "title": "stale one",
                "html_url": "https://x/1",
                "created_at": stale_opened_at,
            }
            fresh_pr = {
                "number": 2,
                "title": "fresh one",
                "html_url": "https://x/2",
                "created_at": fresh_opened_at,
            }
            return httpx.Response(200, json=[stale_pr, fresh_pr])
        if request.url.path.endswith("/commits"):
            return httpx.Response(200, json=[])
        return httpx.Response(404)

    async def run() -> object:
        monitor = GitHubMonitor(token="fixture-token")
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await monitor._check_repo(client, repo)

    result = asyncio.run(run())

    assert result.open_pr_count == 2
    by_number = {pr.number: pr for pr in result.open_pull_requests}
    assert by_number[1].stale is True
    assert by_number[2].stale is False


def test_check_repo_soft_fails_on_http_error() -> None:
    repo = _repo()

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    async def run() -> object:
        monitor = GitHubMonitor(token="fixture-token")
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await monitor._check_repo(client, repo)

    result = asyncio.run(run())

    assert result.ci_status == "unknown"
    assert result.open_issue_count is None
    assert result.open_pr_count is None
    assert result.commits_last_7d is None


def test_activity_uses_ttl_cache(monkeypatch) -> None:
    import app.github_monitor as gm

    repo = _repo()

    async def handler(request: httpx.Request) -> httpx.Response:
        is_actions = "actions" in str(request.url)
        return httpx.Response(200, json={"workflow_runs": []} if is_actions else [])

    original_client = httpx.AsyncClient

    def patched_client(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return original_client(*args, **kwargs)

    monkeypatch.setattr(gm.httpx, "AsyncClient", patched_client)

    monitor = GitHubMonitor(token="fixture-token", cache_ttl_seconds=30)

    async def run() -> tuple[list[object], list[object]]:
        first = await monitor.activity((repo,))
        second = await monitor.activity((repo,))
        return first, second

    first, second = asyncio.run(run())

    assert first[0].cached is False
    assert second[0].cached is True


def test_check_repo_flags_missing_token() -> None:
    repo = _repo()

    async def handler(request: httpx.Request) -> httpx.Response:
        is_actions = "actions" in str(request.url)
        return httpx.Response(200, json={"workflow_runs": []} if is_actions else [])

    async def run() -> object:
        monitor = GitHubMonitor(token="")
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await monitor._check_repo(client, repo)

    result = asyncio.run(run())

    assert result.detail == "No GitHub token configured; live GitHub data is unavailable."
