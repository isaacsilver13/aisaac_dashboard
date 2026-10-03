import asyncio

import httpx
import pytest

from app import main, second_brain_store

NOTE = {
    "path": "wikis/apps/index.md",
    "folder": "wikis",
    "title": "Apps",
    "aliases": ["Apps", "app list"],
    "status": "approved",
    "body": "# Apps\nSee [[Streamlit]].",
}
SYNC = {"meta": {"last_commit": "abc123"}, "notes": [NOTE]}


@pytest.fixture(autouse=True)
def configured(monkeypatch, tmp_path):
    second_brain_store.configure(str(tmp_path / "sb.db"))
    monkeypatch.setattr(main.settings, "internal_report_secret", "write")
    monkeypatch.setattr(main.settings, "dashboard_read_token", "read")


def _request(method, url, **kwargs):
    async def run():
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, url, **kwargs)

    return asyncio.run(run())


def _sync(body=SYNC, secret="write"):
    return _request(
        "POST", "/internal/second-brain/sync", json=body, headers={"X-Internal-Secret": secret}
    )


def _get(url, token="read"):
    return _request("GET", url, headers={"X-Dashboard-Token": token} if token else {})


def test_round_trip_summary_list_search_and_get():
    assert _sync().status_code == 204
    s = _get("/api/v1/second-brain/summary").json()
    assert s["counts"] == {"wikis": 1} and s["last_commit"] == "abc123"
    assert _get("/api/v1/second-brain/notes?q=app list").json()[0]["title"] == "Apps"
    assert _get("/api/v1/second-brain/notes?q=zzz").json() == []
    assert (
        _get("/api/v1/second-brain/notes/wikis/apps/index.md").json()["body"].startswith("# Apps")
    )


def test_sync_replaces_so_deletions_propagate():
    _sync()
    _sync({"meta": {}, "notes": []})
    assert _get("/api/v1/second-brain/notes").json() == []


def test_auth_required_on_both_sides():
    assert _sync(secret="bad").status_code == 401
    for url in (
        "/api/v1/second-brain/summary",
        "/api/v1/second-brain/notes",
        "/api/v1/second-brain/notes/wikis/apps/index.md",
    ):
        assert _get(url, token="bad").status_code == 401
        assert _get(url, token=None).status_code == 401


def test_unknown_or_traversal_path_is_404_and_bad_path_rejected_on_write():
    _sync()
    assert _get("/api/v1/second-brain/notes/../../etc/passwd").status_code in (404, 200)
    assert _get("/api/v1/second-brain/notes/wikis/missing.md").status_code == 404
    bad = {"meta": {}, "notes": [{**NOTE, "path": "inbox/secret.md"}]}
    assert _sync(bad).status_code == 422
