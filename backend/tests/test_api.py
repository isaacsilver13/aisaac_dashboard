import asyncio

import httpx

from app import incidents, main
from app.main import app


def test_master_health_endpoint() -> None:
    async def request_health() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.get("/health")

    response = asyncio.run(request_health())

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "aisaac-dashboard"}


async def _request(method: str, path: str, **kwargs) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path, **kwargs)


def test_internal_report_requires_configured_secret(monkeypatch) -> None:
    monkeypatch.setattr(main.settings, "internal_report_secret", "")

    response = asyncio.run(
        _request("POST", "/internal/report", json={"app_id": "nba-prediction", "status": "ok"})
    )

    assert response.status_code == 503


def test_internal_report_rejects_wrong_secret(monkeypatch) -> None:
    monkeypatch.setattr(main.settings, "internal_report_secret", "correct-secret")

    response = asyncio.run(
        _request(
            "POST",
            "/internal/report",
            json={"app_id": "nba-prediction", "status": "ok"},
            headers={"x-internal-secret": "wrong"},
        )
    )

    assert response.status_code == 401


def test_internal_report_accepts_correct_secret(monkeypatch) -> None:
    monkeypatch.setattr(main.settings, "internal_report_secret", "correct-secret")

    response = asyncio.run(
        _request(
            "POST",
            "/internal/report",
            json={"app_id": "nba-prediction", "status": "ok", "metrics": {"score": 1}},
            headers={"x-internal-secret": "correct-secret"},
        )
    )

    assert response.status_code == 204


def test_incidents_endpoints_open_list_and_resolve(tmp_path) -> None:
    incidents.configure(str(tmp_path / "incidents.db"))
    incidents.open_incident("vinyl", failure_type="down")

    listed = asyncio.run(_request("GET", "/api/v1/incidents"))
    assert listed.status_code == 200
    assert listed.json()[0]["app_id"] == "vinyl"

    incident_id = listed.json()[0]["id"]
    resolved = asyncio.run(
        _request("POST", f"/api/v1/incidents/{incident_id}/resolve", json={"notes": "done"})
    )
    assert resolved.status_code == 204
    assert incidents.get_open_incident("vinyl") is None


def test_runbook_returns_404_when_missing(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(main.settings, "runbooks_dir", str(tmp_path))

    response = asyncio.run(_request("GET", "/api/v1/runbooks/nonexistent-app"))

    assert response.status_code == 404


def test_runbook_returns_content_when_present(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(main.settings, "runbooks_dir", str(tmp_path))
    (tmp_path / "vinyl.md").write_text("# Runbook: Vinyl\n", encoding="utf-8")

    response = asyncio.run(_request("GET", "/api/v1/runbooks/vinyl"))

    assert response.status_code == 200
    assert "Runbook: Vinyl" in response.text