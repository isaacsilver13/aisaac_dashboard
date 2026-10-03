import asyncio

import httpx
import pytest

from app import fly_client, main

RELEASE = {"version": 3, "status": "complete", "description": "Release", "reason": "",
           "createdAt": "2026-10-03T00:00:00Z", "imageRef": "registry.fly.io/x:1"}


@pytest.fixture(autouse=True)
def configured(monkeypatch):
    monkeypatch.setattr(main.settings, "profile", "production")
    monkeypatch.setattr(main.settings, "dashboard_read_token", "read")
    monkeypatch.setattr(main.settings, "fly_api_token", "fly")


def _get(app_id, token="read"):
    async def run():
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get(
                f"/api/v1/apps/{app_id}/deployments", headers={"X-Dashboard-Token": token}
            )

    return asyncio.run(run())


def test_requires_read_token_and_known_app():
    assert _get("vinyl", token="nope").status_code == 401
    assert _get("nope").status_code == 404


def test_app_without_fly_app_returns_empty():
    body = _get("nba-prediction").json()
    assert body == {"app_id": "nba-prediction", "fly_app": None, "releases": []}


def test_returns_releases_for_mapped_fly_app(monkeypatch):
    seen = {}

    async def fake(client, token, app, limit=20):
        seen["args"] = (token, app)
        return [RELEASE]

    monkeypatch.setattr(fly_client, "releases", fake)
    body = _get("vinyl").json()
    assert body["fly_app"] == "vinyl-catalog" and body["releases"] == [RELEASE]
    assert seen["args"] == ("fly", "vinyl-catalog")


def test_fly_failure_is_502(monkeypatch):
    async def boom(*a, **k):
        raise httpx.ConnectError("down")

    monkeypatch.setattr(fly_client, "releases", boom)
    assert _get("vinyl").status_code == 502
