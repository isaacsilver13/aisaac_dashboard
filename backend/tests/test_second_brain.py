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


import sqlite3  # noqa: E402

APPS = {
    "path": "wikis/apps/index.md",
    "folder": "wikis",
    "title": "Apps Wiki",
    "aliases": ["Apps Wiki"],
    "status": "approved",
    "frontmatter": {"type": "wiki-index", "updated": "2026-10-02"},
    "body": "# Apps\n\nMap of apps. See [[Gym Tracker|gym]], [[gym tracker#Setup]], [[Nope]]"
    " and [[Apps Wiki]].",
}
GYM = {
    "path": "projects/gym-tracker.md",
    "folder": "projects",
    "title": "Gym Tracker",
    "aliases": ["Gym Tracker"],
    "status": "active",
    "frontmatter": {},
    "body": "# Gym\n\nBack to [[Apps Wiki]].",
}
LONE = {
    **GYM,
    "path": "questions/lone.md",
    "folder": "questions",
    "title": "Lone",
    "aliases": [],
    "body": "",
}


def _api(*notes):
    assert _sync({"meta": {}, "notes": list(notes)}).status_code == 204


def test_links_backlinks_unresolved_and_previews():
    _api(APPS, GYM)
    note = _get("/api/v1/second-brain/notes/wikis/apps/index.md").json()
    assert note["link_map"] == {
        "gym tracker": GYM["path"],
        "nope": None,
        "apps wiki": APPS["path"],
    }
    assert [r["path"] for r in note["links"]] == [GYM["path"]]  # self-link excluded
    assert [r["path"] for r in note["backlinks"]] == [GYM["path"]]
    assert note["previews"][GYM["path"]] == "Back to Apps Wiki."
    assert note["frontmatter"]["updated"] == "2026-10-02"
    assert note["portal"] == "wikis/apps"


def test_note_without_links_has_empty_lists():
    _api(LONE)
    note = _get("/api/v1/second-brain/notes/questions/lone.md").json()
    assert note["links"] == [] and note["backlinks"] == [] and note["link_map"] == {}


def test_duplicate_names_prefer_wikis_over_projects():
    clash = {**GYM, "path": "wikis/apps/gym.md", "folder": "wikis", "body": ""}
    _api(GYM, clash, APPS)
    note = _get("/api/v1/second-brain/notes/wikis/apps/index.md").json()
    assert note["link_map"]["gym tracker"] == "wikis/apps/gym.md"


def test_graph_portals_and_list_updated():
    _api(APPS, GYM, LONE)
    g = _get("/api/v1/second-brain/graph").json()
    assert {n["path"] for n in g["nodes"]} == {APPS["path"], GYM["path"], LONE["path"]}
    assert sorted(g["edges"]) == [[GYM["path"], APPS["path"]], [APPS["path"], GYM["path"]]]
    ids = {p["id"]: p for p in _get("/api/v1/second-brain/portals").json()}
    assert ids["wikis/apps"]["index_path"] == APPS["path"]
    assert ids["wikis/apps"]["title"] == "Apps Wiki" and ids["wikis/apps"]["count"] == 1
    assert ids["wikis/apps"]["description"].startswith("Map of apps.")
    assert ids["projects"]["index_path"] is None
    listed = {n["path"]: n for n in _get("/api/v1/second-brain/notes").json()}
    assert listed[APPS["path"]]["updated"] == "2026-10-02"


def test_old_schema_db_still_serves_before_resync(tmp_path):
    db = tmp_path / "old.db"
    conn = sqlite3.connect(db)
    conn.executescript(
        "CREATE TABLE notes (path TEXT PRIMARY KEY, folder TEXT NOT NULL, title TEXT NOT NULL,"
        " aliases TEXT NOT NULL, status TEXT, body TEXT NOT NULL);"
        "INSERT INTO notes VALUES ('wikis/apps/index.md','wikis','Apps','[]',NULL,'# Apps');"
    )
    conn.commit()
    conn.close()
    second_brain_store.configure(str(db))
    note = _get("/api/v1/second-brain/notes/wikis/apps/index.md").json()
    assert note["frontmatter"] == {} and note["link_map"] == {} and note["links"] == []
    assert _get("/api/v1/second-brain/graph").json()["edges"] == []
    assert _get("/api/v1/second-brain/portals").status_code == 200


def test_new_endpoints_require_the_read_token():
    for url in ("/api/v1/second-brain/graph", "/api/v1/second-brain/portals"):
        assert _get(url, token="bad").status_code == 401
        assert _get(url, token=None).status_code == 401
