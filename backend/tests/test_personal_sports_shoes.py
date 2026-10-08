import asyncio
from datetime import datetime, timezone

import httpx
import pytest

from app import main, personal_digest, personal_shoes, personal_sports, personal_store

NOW = datetime(2026, 10, 7, 14, 0, tzinfo=timezone.utc)  # 09:00 CDT

RAW = [
    {"id": "1", "league": "NFL", "home": "Chicago Bears", "away": "Detroit Lions",
     "start_at": "2026-10-08T00:20:00Z", "status": "scheduled", "url": "https://x/?a=1&b=2"},
    {"id": "2", "league": "NCAAF", "home": "Ohio State", "away": "Iowa", "home_rank": 3,
     "home_conference": "Big Ten", "away_conference": "Big Ten", "poll_date": "2026-10-05",
     "start_at": "2026-10-07T20:00:00Z"},
    {"id": "3", "league": "NCAAF", "home": "Tulane", "away": "Rice",
     "home_conference": "AAC", "away_conference": "AAC", "start_at": "2026-10-07T21:00:00Z"},
    {"id": "bad", "league": "CURLING", "home": "a", "away": "b",
     "start_at": "2026-10-07T00:00:00Z"},
]
WATCH = {"kind": "search", "name": "AJ1", "keywords": "aj1", "size": None,
         "condition": None, "max_price": None, "url": None}
LISTING = {"key": "k1", "title": "AJ1 High", "price": 140, "url": "https://e/1", "source": "ebay"}

READ = {"X-Dashboard-Token": "read"}
WRITE = {"X-Dashboard-Write-Token": "write"}


@pytest.fixture(autouse=True)
def configured(monkeypatch, tmp_path):
    personal_store.configure(str(tmp_path / "p.db"))
    monkeypatch.setattr(personal_sports, "PROVIDER", None)
    monkeypatch.setattr(personal_shoes, "PROVIDER", None)
    monkeypatch.setattr(main.settings, "dashboard_read_token", "read")
    monkeypatch.setattr(main.settings, "dashboard_write_token", "write")


def _request(method, url, **kwargs):
    async def run():
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, url, **kwargs)

    return asyncio.run(run())


def test_endpoints_require_tokens():
    assert _request("GET", "/api/v1/personal/sports").status_code == 401
    assert _request("GET", "/api/v1/personal/shoes").status_code == 401
    # a read token must not unlock writes
    r = _request("POST", "/api/v1/personal/shoes/watches", headers=READ, json={})
    assert r.status_code == 401


def test_unconfigured_provider_reports_not_configured():
    assert personal_sports.refresh() == "not_configured"
    body = _request("GET", "/api/v1/personal/sports", headers=READ).json()
    assert body["configured"] is False and body["events"] == []
    assert body["last_error"] == "not_configured" and body["official_links"]["NFL"]


def test_normalize_drops_bad_rows_and_filters():
    assert personal_sports.refresh(lambda: RAW) == "ok"
    assert len(personal_store.list_events()) == 3  # unknown league dropped
    assert [e["id"] for e in personal_store.list_events(team="chicago bears")] == ["1"]
    assert [e["id"] for e in personal_store.list_events(conference="Big Ten")] == ["2"]
    assert [e["id"] for e in personal_store.list_events(top_25_only=True)] == ["2"]
    assert [e["id"] for e in personal_store.list_events(league="NCAAF")] == ["2", "3"]


def test_failed_refresh_keeps_last_snapshot():
    personal_sports.refresh(lambda: RAW)

    def boom():
        raise RuntimeError("secret upstream body")

    assert personal_sports.refresh(boom) == "fetch_failed"
    assert len(personal_store.list_events()) == 3
    row = personal_store.sports_refreshes()[0]
    assert row["last_error"] == "fetch_failed" and row["last_ok_at"]  # no upstream text stored


def test_top_25_unavailable_when_poll_is_stale():
    personal_sports.refresh(lambda: RAW)
    assert personal_sports.query(top_25_only=True, now=NOW)["events"][0]["id"] == "2"
    stale = personal_sports.query(top_25_only=True, now=datetime(2026, 10, 30, tzinfo=timezone.utc))
    assert stale["events"] == [] and stale["rankings"]["current"] is False


def test_priority_events_window():
    personal_sports.refresh(lambda: RAW)
    assert [e["id"] for e in personal_sports.priority_events(NOW)] == ["1"]


def test_shoe_watch_crud_and_validation():
    bad = {"kind": "search", "name": "x", "url": "javascript:alert(1)"}
    r = _request("POST", "/api/v1/personal/shoes/watches", headers=WRITE, json=bad)
    assert r.status_code == 422
    ok = {"kind": "release", "name": "AJ1", "url": "https://example.com/launch"}
    r = _request("POST", "/api/v1/personal/shoes/watches", headers=WRITE, json=ok)
    assert r.status_code == 201
    assert len(_request("GET", "/api/v1/personal/shoes", headers=READ).json()["watches"]) == 1
    url = f"/api/v1/personal/shoes/watches/{r.json()['id']}"
    assert _request("DELETE", url, headers=WRITE).status_code == 204
    assert _request("GET", "/api/v1/personal/shoes", headers=READ).json()["watches"] == []
    assert _request("DELETE", "/api/v1/personal/shoes/watches/99", headers=WRITE).status_code == 404


def test_listing_price_change_detection_and_cap():
    personal_store.create_watch({**WATCH, "max_price": 150.0})
    over = {"key": "k2", "title": "AJ1 Low", "price": 400, "url": "https://e/2"}
    assert personal_shoes.refresh(lambda w: [LISTING, over]) == "ok"
    assert [r["listing_key"] for r in personal_store.list_listings()] == ["k1"]  # cap applied
    assert personal_shoes.refresh(lambda w: [LISTING]) == "ok"  # same price: not a change
    row = personal_store.list_listings()[0]
    assert row["prev_price"] is None
    assert personal_shoes.refresh(lambda w: [{**LISTING, "price": 120}]) == "ok"
    row = personal_store.list_listings()[0]
    assert row["price"] == 120.0 and row["prev_price"] == 140.0
    assert [h["price"] for h in personal_store.price_history(row["id"])] == [140.0, 140.0, 120.0]


def test_price_history_is_bounded():
    wid = personal_store.create_watch(WATCH)
    item = personal_shoes.normalize(LISTING)
    for i in range(personal_store.MAX_SNAPSHOTS + 10):
        personal_store.observe_listing(wid, {**item, "price": float(i)})
    lid = personal_store.list_listings()[0]["id"]
    assert len(personal_store.price_history(lid)) == personal_store.MAX_SNAPSHOTS


def test_digest_includes_games_and_shoes_and_is_idempotent(monkeypatch):
    personal_sports.refresh(lambda: RAW)
    personal_store.create_watch(WATCH)
    personal_shoes.refresh(lambda w: [LISTING])
    monkeypatch.setattr(personal_shoes, "PROVIDER", lambda w: [LISTING])
    monkeypatch.setattr(
        personal_shoes, "recent_changes", lambda now: personal_store.list_listings()
    )
    monkeypatch.setattr(personal_sports, "PROVIDER", lambda: RAW)
    sent = []

    def send(subject, text, body):
        sent.append((text, body))
        return True

    noop = lambda: None  # noqa: E731
    assert personal_digest.run(NOW, send=send, refresh=noop)["status"] == "sent"
    text, body = sent[0]
    assert "Detroit Lions at Chicago Bears" in text and "AJ1 High" in text
    assert "&amp;b=2" in body  # urls are escaped in html
    assert personal_digest.run(NOW, send=send, refresh=noop)["status"] == "already_handled"
    assert len(sent) == 1


def test_digest_dry_run_sends_and_records_nothing():
    personal_sports.refresh(lambda: RAW)
    out = personal_digest.run(NOW, dry_run=True, send=lambda *a: pytest.fail("sent"))
    assert out["status"] == "dry_run" and "Chicago Bears" in out["text"]
    assert personal_store.get_run("2026-10-07") is None


def test_digest_dst_boundary():
    # 2026-11-01 is fall-back day: 13:30Z is 07:30 CST (too early); 14:00Z is 08:00 CST.
    def run(at):
        return personal_digest.run(at, send=lambda *a: True, refresh=lambda: None)["status"]

    assert run(datetime(2026, 11, 1, 13, 30, tzinfo=timezone.utc)) == "too_early"
    # 04:30Z is 23:30 CDT on Oct 31, before the clocks change, so it belongs to Oct 31
    late = datetime(2026, 11, 1, 4, 30, tzinfo=timezone.utc)
    assert personal_digest.local_date(late) == "2026-10-31"
    assert run(datetime(2026, 11, 1, 14, 0, tzinfo=timezone.utc)) == "sent"


def test_provider_urls_must_be_http():
    assert personal_shoes.normalize({**LISTING, "url": "javascript:alert(1)"}) is None
    bad = personal_sports.normalize({**RAW[0], "url": "javascript:alert(1)"})
    assert bad["url"] == personal_sports.OFFICIAL_LINKS["NFL"]


def test_unknown_price_becoming_known_is_not_new():
    wid = personal_store.create_watch(WATCH)
    item = personal_shoes.normalize(LISTING)
    personal_store.observe_listing(wid, {**item, "price": None})
    assert personal_store.observe_listing(wid, item) is True
    row = personal_store.list_listings()[0]
    assert row["sightings"] == 2 and row["prev_price"] is None
    _, text, _ = personal_digest.render([], None, NOW, [], [row])
    assert "(new)" not in text
