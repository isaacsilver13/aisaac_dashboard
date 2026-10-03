import asyncio

import httpx
import pytest

from app import ai_digest_store, main

ITEM = {
    "id": 1,
    "title": "Building effective agents",
    "url": "https://example.com/agents",
    "source": "Example Blog",
    "published_at": "2026-10-02T12:00:00Z",
    "category": "systems",
    "priority": 5,
    "summary": "Argues for simple, composable patterns over heavy frameworks.",
    "why_it_matters": "Directly applicable to the dashboard digest pipeline.",
}
DIGEST = {
    "digest_date": "2026-10-03",
    "generated_at": "2026-10-03T11:00:00Z",
    "model": "anthropic/claude-sonnet-5-5",
    "headline": "Agent design guidance leads today [1].",
    "items": [ITEM, {**ITEM, "id": 2, "url": "https://example.com/two", "priority": 2}],
    "source_stats": {"Example Blog": {"fetched": 4, "error": None}},
}


@pytest.fixture(autouse=True)
def configured(monkeypatch, tmp_path):
    ai_digest_store.configure(str(tmp_path / "digest.db"), retention_days=30)
    monkeypatch.setattr(main.settings, "internal_report_secret", "write")
    monkeypatch.setattr(main.settings, "dashboard_read_token", "read")


def _request(method, url, **kwargs):
    async def run():
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, url, **kwargs)

    return asyncio.run(run())


def _sync(body=DIGEST, secret="write"):
    return _request(
        "POST", "/internal/ai-digest/sync", json=body, headers={"X-Internal-Secret": secret}
    )


def _get(url, token="read"):
    return _request("GET", url, headers={"X-Dashboard-Token": token} if token else {})


def test_round_trip_latest_dates_and_by_date():
    assert _sync().status_code == 204
    latest = _get("/api/v1/ai-digest").json()
    assert latest["digest_date"] == "2026-10-03"
    assert [i["id"] for i in latest["items"]] == [1, 2]
    assert latest["items"][0]["url"] == "https://example.com/agents"
    assert latest["pushed_at"]
    assert _get("/api/v1/ai-digest/dates").json() == ["2026-10-03"]
    assert _get("/api/v1/ai-digest/2026-10-03").json()["headline"].startswith("Agent design")


def test_empty_store_returns_empty_digest_not_an_error():
    body = _get("/api/v1/ai-digest").json()
    assert body["items"] == [] and body["digest_date"] is None


def test_latest_is_the_newest_date_and_same_date_replaces():
    _sync({**DIGEST, "digest_date": "2026-10-01", "headline": "Older [1]."})
    _sync()
    _sync({**DIGEST, "headline": "Replaced [2]."})
    assert _get("/api/v1/ai-digest").json()["headline"] == "Replaced [2]."
    assert _get("/api/v1/ai-digest/dates").json() == ["2026-10-03", "2026-10-01"]


def test_old_digests_are_pruned_past_retention():
    ai_digest_store.configure(ai_digest_store._db_path, retention_days=5)
    _sync({**DIGEST, "digest_date": "2026-09-20", "headline": ""})
    _sync()
    assert _get("/api/v1/ai-digest/dates").json() == ["2026-10-03"]


def test_auth_required_on_both_sides():
    assert _sync(secret="bad").status_code == 401
    for url in ("/api/v1/ai-digest", "/api/v1/ai-digest/dates", "/api/v1/ai-digest/2026-10-03"):
        assert _get(url, token="bad").status_code == 401
        assert _get(url, token=None).status_code == 401


def test_unknown_date_is_404_and_malformed_date_is_422():
    _sync()
    assert _get("/api/v1/ai-digest/2026-01-01").status_code == 404
    assert _get("/api/v1/ai-digest/not-a-date").status_code == 422


@pytest.mark.parametrize(
    "bad",
    [
        {**DIGEST, "headline": "Cites a missing item [9]."},
        {**DIGEST, "items": [ITEM, ITEM]},
        {**DIGEST, "items": [{**ITEM, "url": "javascript:alert(1)"}]},
        {**DIGEST, "items": [{**ITEM, "url": "not a url"}]},
        {**DIGEST, "items": [{**ITEM, "priority": 6}]},
        {**DIGEST, "items": [{**ITEM, "category": "gossip"}]},
    ],
)
def test_invalid_digests_are_rejected_and_not_stored(bad):
    assert _sync(bad).status_code == 422
    assert _get("/api/v1/ai-digest/dates").json() == []


def test_automations_reports_the_digest_job():
    assert _get("/api/v1/automations").json()  # sanity: endpoint works
    row = next(r for r in _get("/api/v1/automations").json() if r["id"] == "ai-digest")
    assert row["status"] == "never"
    _sync()
    row = next(r for r in _get("/api/v1/automations").json() if r["id"] == "ai-digest")
    assert row["status"] == "ok" and row["expected_hours"] == 26.0
