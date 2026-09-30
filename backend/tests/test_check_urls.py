import httpx

from app.registry import get_registry
from scripts.check_urls import collect_targets, probe


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_probe_passes_on_2xx() -> None:
    with _client(lambda request: httpx.Response(200)) as client:
        result = probe(client, "https://x.example/health", retry_delay=0)

    assert result.status == "PASS"
    assert result.http_status == 200


def test_probe_retries_once_and_reports_slow() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ConnectError("waking")
        return httpx.Response(200)

    with _client(handler) as client:
        result = probe(client, "https://x.example/health", retry_delay=0)

    assert calls == 2
    assert result.status == "SLOW"


def test_probe_fails_with_error_after_two_attempts() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    with _client(handler) as client:
        result = probe(client, "https://x.example/health", retry_delay=0)

    assert result.status == "FAIL"
    assert "could not connect" in result.detail.lower()


def test_probe_fails_on_404_without_retry() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(404)

    with _client(handler) as client:
        result = probe(client, "https://x.example/health", retry_delay=0)

    assert calls == 1
    assert result.status == "FAIL"
    assert result.http_status == 404


def test_collect_targets_lists_every_configured_url_and_skips_push_only_apps() -> None:
    apps = get_registry("production")
    targets = collect_targets(apps)

    urls = {url for _, _, url in targets}
    assert "https://vinyl-api.fly.dev/health" in urls
    assert all(app_id != "nba-prediction" for app_id, _, _ in targets)
