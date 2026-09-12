import asyncio

import httpx

from app import incidents, reports
from app.monitoring import Monitor
from app.schemas import AppDefinition


def test_check_app_normalizes_healthy_json() -> None:
    app = AppDefinition(
        id="fixture",
        name="Fixture",
        category="Test",
        description="Fixture service",
        product_url="https://example.com",
        health_url="https://health.example.com",
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "ok", "version": "1.2.3", "records": 7})

    transport = httpx.MockTransport(handler)
    async def run_check() -> object:
        async with httpx.AsyncClient(transport=transport) as client:
            return await Monitor().check_app(client, app)

    import asyncio

    result = asyncio.run(run_check())

    assert result.state == "up"
    assert result.metrics == {"version": "1.2.3", "records": 7}
    assert result.http_status == 200
    assert result.response_ms is not None


def test_check_app_classifies_provider_warning_as_degraded() -> None:
    app = AppDefinition(
        id="fixture",
        name="Fixture",
        category="Test",
        description="Fixture service",
        health_url="https://health.example.com",
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "unconfigured", "provider_status": "missing"})

    async def run_check() -> object:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await Monitor().check_app(client, app)

    import asyncio

    result = asyncio.run(run_check())

    assert result.state == "degraded"
    assert result.provider_state == "missing"


def test_check_app_unwraps_nested_health_payload() -> None:
    app = AppDefinition(
        id="nfl",
        name="NFL",
        category="Test",
        description="Fixture service",
        health_url="https://health.example.com/health",
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"data": {"status": "healthy", "scheduler": "running"}})

    async def run_check() -> object:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await Monitor().check_app(client, app)

    import asyncio

    result = asyncio.run(run_check())

    assert result.state == "up"
    assert result.metrics == {"scheduler": "running"}


def test_check_app_reports_page_failure_as_degraded() -> None:
    app = AppDefinition(
        id="fixture",
        name="Fixture",
        category="Test",
        description="Fixture service",
        product_url="https://app.example.com",
        health_url="https://health.example.com",
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "app.example.com":
            return httpx.Response(503)
        return httpx.Response(200, json={"status": "ok"})

    async def run_check() -> object:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await Monitor().check_app(client, app)

    import asyncio

    result = asyncio.run(run_check())

    assert result.state == "degraded"
    assert result.page_state == "down"


def test_check_app_allowlists_metrics_from_secondary_status_url() -> None:
    app = AppDefinition(
        id="betting",
        name="Betting",
        category="Test",
        description="Fixture service",
        health_url="https://health.example.com",
        metrics_url="https://status.example.com",
        metric_allowlist=("provider_status", "event_count"),
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.host == "status.example.com":
            return httpx.Response(
                200,
                json={"provider_status": "fixture", "event_count": 4, "secret": "omit"},
            )
        return httpx.Response(200, json={"status": "ok"})

    async def run_check() -> object:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await Monitor().check_app(client, app)

    import asyncio

    result = asyncio.run(run_check())

    assert result.state == "up"
    assert result.metrics == {"event_count": 4}
    assert result.provider_state == "fixture"
    assert result.metrics_state == "up"


def test_check_app_separates_readiness_from_liveness() -> None:
    app = AppDefinition(
        id="fixture",
        name="Fixture",
        category="Test",
        description="Fixture service",
        health_url="https://health.example.com/health",
        readiness_url="https://health.example.com/ready",
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/ready":
            return httpx.Response(503, json={"status": "down"})
        return httpx.Response(200, json={"status": "ok"})

    async def run_check() -> object:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await Monitor().check_app(client, app)

    import asyncio

    result = asyncio.run(run_check())

    assert result.state == "degraded"
    assert result.readiness == "down"


def test_check_app_classifies_timeout_without_leaking_exception() -> None:
    app = AppDefinition(
        id="fixture",
        name="Fixture",
        category="Test",
        description="Fixture service",
        health_url="https://health.example.com",
    )

    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("secret target details")

    async def run_check() -> object:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            return await Monitor().check_app(client, app)

    import asyncio

    result = asyncio.run(run_check())

    assert result.state == "down"
    assert result.detail == "Health check timed out."


def test_dashboard_uses_ttl_cache() -> None:
    app = AppDefinition(
        id="disabled",
        name="Disabled",
        category="Test",
        description="Disabled service",
        enabled=False,
    )
    monitor = Monitor(cache_ttl_seconds=30)

    import asyncio

    async def run_dashboard() -> tuple[list[object], list[object]]:
        first = await monitor.dashboard((app,))
        second = await monitor.dashboard((app,))
        return first, second

    first, second = asyncio.run(run_dashboard())

    assert first[0].cached is False
    assert second[0].cached is True
    assert second[0].state == "unavailable"


def test_push_target_reports_stale_without_a_heartbeat() -> None:
    app = AppDefinition(
        id="never-reported",
        name="Never Reported",
        category="Test",
        description="Fixture service",
        monitor_target="push",
    )

    transport = httpx.MockTransport(lambda r: httpx.Response(200))

    async def run_check() -> object:
        async with httpx.AsyncClient(transport=transport) as client:
            return await Monitor().check_app(client, app)

    result = asyncio.run(run_check())

    assert result.state == "stale"


def test_push_target_reflects_recent_heartbeat() -> None:
    reports.record_report("pushed-app", "ok", {"last_run_score": 1.0})
    app = AppDefinition(
        id="pushed-app",
        name="Pushed App",
        category="Test",
        description="Fixture service",
        monitor_target="push",
        metric_allowlist=("last_run_score",),
    )

    transport = httpx.MockTransport(lambda r: httpx.Response(200))

    async def run_check() -> object:
        async with httpx.AsyncClient(transport=transport) as client:
            return await Monitor().check_app(client, app)

    result = asyncio.run(run_check())

    assert result.state == "up"
    assert result.metrics == {"last_run_score": 1.0}


def test_dashboard_opens_incident_on_transition_to_down(tmp_path) -> None:
    incidents.configure(str(tmp_path / "incidents.db"))
    app = AppDefinition(
        id="flaky",
        name="Flaky",
        category="Test",
        description="Fixture service",
        health_url="https://health.example.com",
    )
    responses = iter([httpx.Response(200, json={"status": "ok"}), httpx.Response(503)])

    async def handler(request: httpx.Request) -> httpx.Response:
        return next(responses)

    monitor = Monitor(cache_ttl_seconds=0)

    async def run_dashboard() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            monitor._handle_transition(await monitor.check_app(client, app))
            monitor._handle_transition(await monitor.check_app(client, app))

    asyncio.run(run_dashboard())

    assert incidents.get_open_incident("flaky") is not None


def test_dashboard_resolves_incident_on_recovery(tmp_path) -> None:
    incidents.configure(str(tmp_path / "incidents.db"))
    incidents.open_incident("recovering", failure_type="down")
    monitor = Monitor()
    monitor._last_state["recovering"] = "down"

    from datetime import datetime, timezone

    from app.schemas import CheckResult

    result = CheckResult(
        app_id="recovering",
        name="Recovering",
        category="Test",
        description="Fixture",
        state="up",
        checked_at=datetime.now(timezone.utc),
    )

    monitor._handle_transition(result)

    assert incidents.get_open_incident("recovering") is None
