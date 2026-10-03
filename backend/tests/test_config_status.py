import asyncio

import httpx

from app import main


def test_config_status_reports_set_or_not_never_values(monkeypatch):
    monkeypatch.setattr(main.settings, "dashboard_read_token", "read")
    monkeypatch.setattr(main.settings, "fly_api_token", "super-secret")
    monkeypatch.setattr(main.settings, "github_token", "")

    async def get(token):
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
            return await c.get("/api/v1/config-status", headers={"X-Dashboard-Token": token})

    assert asyncio.run(get("nope")).status_code == 401
    response = asyncio.run(get("read"))
    items = {i["key"]: i["configured"] for i in response.json()["items"]}
    assert items["fly_api_token"] is True and items["github_token"] is False
    assert "super-secret" not in response.text
