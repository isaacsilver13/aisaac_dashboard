import asyncio
import sqlite3

import httpx
import pytest

from app import (
    main,
    personal_connect,
    personal_ebay,
    personal_own,
    personal_shoes,
    personal_store,
    personal_vault,
)

KEY = "test-encryption-key"
SPEC = personal_connect.ProviderSpec(
    authorize_url="https://auth.example/authorize",
    token_url="https://auth.example/token",
    scopes=("read",),
    client_id="cid",
    client_secret="csecret",
)
READ = {"X-Dashboard-Token": "read"}
WRITE = {"X-Dashboard-Write-Token": "write"}


@pytest.fixture(autouse=True)
def configured(monkeypatch, tmp_path):
    personal_store.configure(str(tmp_path / "p.db"))
    monkeypatch.setattr(personal_connect, "SPECS", {"demo": SPEC})
    monkeypatch.setattr(main.settings, "dashboard_read_token", "read")
    monkeypatch.setattr(main.settings, "dashboard_write_token", "write")
    monkeypatch.setattr(main.settings, "token_encryption_key", KEY)
    monkeypatch.setattr(main.settings, "public_base_url", "http://localhost:8000")
    monkeypatch.setattr(personal_ebay, "_token", ("", 0.0))
    return tmp_path


def _request(method, url, **kwargs):
    async def run():
        transport = httpx.ASGITransport(app=main.app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.request(method, url, **kwargs)

    return asyncio.run(run())


def test_vault_encrypts_at_rest_and_round_trips(configured):
    personal_vault.save_token("demo", "refresh-secret", KEY)
    raw = sqlite3.connect(configured / "p.db").execute("SELECT token_enc FROM oauth_connections")
    assert "refresh-secret" not in raw.fetchone()[0]
    assert personal_vault.load_token("demo", KEY) == "refresh-secret"
    with pytest.raises(personal_vault.VaultError):
        personal_vault.load_token("demo", "wrong-key")
    assert personal_vault.load_token("absent", KEY) is None
    with pytest.raises(personal_vault.VaultError):
        personal_vault.save_token("demo", "x", "")


def test_state_is_signed_scoped_and_expires():
    state = personal_connect.make_state("demo", KEY, now=1000)
    assert personal_connect.check_state(state, "demo", KEY, now=1100)
    assert not personal_connect.check_state(state, "other", KEY, now=1100)
    assert not personal_connect.check_state(state, "demo", "wrong", now=1100)
    assert not personal_connect.check_state(state, "demo", KEY, now=1000 + 601)
    tampered = state[:-1] + ("1" if state[-1] == "0" else "0")
    assert not personal_connect.check_state(tampered, "demo", KEY, now=1100)
    assert not personal_connect.check_state("garbage", "demo", KEY)
    assert not personal_connect.check_state("demo.².ab.é", "demo", KEY)  # non-ASCII: no crash


def test_connect_start_requires_write_token_and_config():
    assert _request("GET", "/api/v1/personal/connect/demo", headers=READ).status_code == 401
    ok = _request("GET", "/api/v1/personal/connect/demo", headers=WRITE)
    assert ok.status_code == 200
    url = ok.json()["url"]
    assert url.startswith("https://auth.example/authorize?") and "state=demo." in url
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fapi%2Fv1%2Fpersonal" in url
    assert _request("GET", "/api/v1/personal/connect/unknown", headers=WRITE).status_code == 501


def test_callback_stores_encrypted_token_and_rejects_bad_state():
    state = personal_connect.make_state("demo", KEY)
    seen = {}

    def exchange(spec, code, redirect):
        seen.update(code=code, redirect=redirect)
        return "refresh-1"

    personal_connect.complete("demo", "abc", state, KEY, "http://localhost:8000", exchange)
    assert seen["code"] == "abc" and seen["redirect"].endswith("/connect/demo/callback")
    assert personal_vault.load_token("demo", KEY) == "refresh-1"

    with pytest.raises(personal_connect.ConnectError):
        personal_connect.complete("demo", "abc", "bad", KEY, "http://x", exchange)

    def boom(spec, code, redirect):
        raise RuntimeError("provider said: secret detail")

    with pytest.raises(personal_connect.ConnectError) as err:
        personal_connect.complete("demo", "abc", state, KEY, "http://x", boom)
    assert "secret detail" not in str(err.value)

    bad = _request("GET", "/api/v1/personal/connect/demo/callback?code=a&state=nope")
    assert bad.status_code == 400 and "secret" not in bad.text.lower()


def test_connections_never_expose_tokens_and_disconnect():
    personal_vault.save_token("demo", "refresh-secret", KEY)
    r = _request("GET", "/api/v1/personal/connections", headers=READ)
    assert r.status_code == 200 and "refresh-secret" not in r.text
    by = {c["provider"]: c for c in r.json()["connections"]}
    assert by["demo"] == {"provider": "demo", "available": True, "connected": True}
    assert by["ebay"]["available"] is False  # no spec yet
    assert _request("DELETE", "/api/v1/personal/connections/demo", headers=READ).status_code == 401
    assert _request("DELETE", "/api/v1/personal/connections/demo", headers=WRITE).status_code == 204
    assert _request("DELETE", "/api/v1/personal/connections/demo", headers=WRITE).status_code == 404


def test_own_refresh_normalizes_and_keeps_rows_on_failure():
    personal_vault.save_token("demo", "tok", KEY)
    raw = [
        {"kind": "purchase", "id": 1, "title": "AJ1", "price": "150", "url": "https://x/1"},
        {"kind": "watch", "id": 2, "title": "Dunk", "url": "javascript:alert(1)"},
        {"kind": "bogus", "id": 3, "title": "x"},
    ]
    assert personal_own.refresh(KEY, {"demo": lambda t: raw}) == {"demo": "ok"}
    items = {i["external_id"]: i for i in personal_store.list_own_items()}
    assert set(items) == {"1", "2"} and items["1"]["price"] == 150.0 and items["2"]["url"] is None

    def boom(token):
        raise RuntimeError("upstream body")

    assert personal_own.refresh(KEY, {"demo": boom}) == {"demo": "fetch_failed"}
    assert len(personal_store.list_own_items()) == 2
    assert personal_own.refresh(KEY, {"stockx": lambda t: raw}) == {"stockx": "not_connected"}
    # a second sighting updates in place instead of duplicating
    personal_own.refresh(KEY, {"demo": lambda t: raw})
    assert len(personal_store.list_own_items()) == 2


def test_own_endpoints_require_read_token_and_filter():
    assert _request("GET", "/api/v1/personal/own").status_code == 401
    personal_store.upsert_own_item(personal_own.normalize(
        "demo", {"kind": "bid", "id": "b1", "title": "Bid", "price": 90}))
    body = _request("GET", "/api/v1/personal/own?kind=bid", headers=READ).json()
    assert [i["title"] for i in body["items"]] == ["Bid"]
    assert _request("GET", "/api/v1/personal/own?kind=nope", headers=READ).status_code == 422


class _Resp:
    def __init__(self, body):
        self._body = body

    def raise_for_status(self):
        pass

    def json(self):
        return self._body


def test_ebay_provider_mints_once_and_normalizes():
    posts, gets = [], []

    def post(url, **kw):
        posts.append(kw)
        return _Resp({"access_token": "app-tok", "expires_in": 7200})

    def get(url, **kw):
        gets.append(kw)
        return _Resp({"itemSummaries": [
            {"itemId": "v1|1|0", "title": "AJ1 High",
             "price": {"value": "140.00", "currency": "USD"},
             "itemWebUrl": "https://www.ebay.com/itm/1", "condition": "New"},
            {"itemId": "v1|2|0", "title": "AJ1 EU", "price": {"value": "99", "currency": "EUR"},
             "itemWebUrl": "javascript:alert(1)"},
        ]})

    provider = personal_ebay.make_provider("cid", "sec", get=get, post=post)
    watch = {"name": "AJ1", "keywords": "air jordan 1"}
    listings = [personal_shoes.normalize(x) for x in provider(watch)]
    provider(watch)
    assert len(posts) == 1  # app token cached
    assert gets[0]["params"]["q"] == "air jordan 1"
    assert gets[0]["headers"]["Authorization"] == "Bearer app-tok"
    assert listings[0]["price"] == 140.0 and listings[0]["source"] == "eBay"
    assert listings[1] is None  # non-http url rejected by the shoes boundary
    assert personal_ebay.make_provider("", "") is None


def test_real_specs_follow_provider_docs(monkeypatch):
    assert personal_connect.make_specs("", "", "", "", "", "") == {}
    assert "ebay" not in personal_connect.make_specs("i", "s", "RU", " ", "", "")  # no scopes
    specs = personal_connect.make_specs("eid", "esec", "My-RuName", "s1 s2", "xid", "xsec")
    monkeypatch.setattr(personal_connect, "SPECS", specs)

    ebay = personal_connect.authorize_link("ebay", KEY, "http://localhost:8000")
    assert ebay.startswith("https://auth.ebay.com/oauth2/authorize?")
    assert "redirect_uri=My-RuName" in ebay and "scope=s1+s2" in ebay

    sx = personal_connect.authorize_link("stockx", KEY, "http://localhost:8000")
    assert sx.startswith("https://accounts.stockx.com/authorize?")
    assert "audience=gateway.stockx.com" in sx and "scope=offline_access+openid" in sx
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fapi%2Fv1%2Fpersonal" in sx

    calls = []

    def post(url, **kw):
        calls.append((url, kw))
        return _Resp({"refresh_token": "r"})

    monkeypatch.setattr(personal_connect.httpx, "post", post)
    assert personal_connect._http_exchange(specs["ebay"], "c", "ignored") == "r"
    assert calls[0][1]["auth"] == ("eid", "esec")
    assert calls[0][1]["data"]["redirect_uri"] == "My-RuName"
    personal_connect._http_exchange(specs["stockx"], "c", "http://cb")
    assert calls[1][1]["auth"] is None and calls[1][1]["data"]["client_secret"] == "xsec"


@pytest.fixture
def stockx(monkeypatch):
    from app import personal_stockx

    monkeypatch.setattr(personal_stockx, "_pace", lambda: None)
    monkeypatch.setattr(personal_stockx, "_tokens", {})
    return personal_stockx


def test_stockx_fetcher_lists_asks_and_sales(stockx):
    posts, gets = [], []

    def post(url, **kw):
        posts.append((url, kw))
        return _Resp({"access_token": "acc", "expires_in": 43200})

    def get(url, **kw):
        gets.append((url, kw))
        if url.endswith("/selling/listings"):
            return _Resp({"hasNextPage": False, "listings": [
                {"listingId": "L1", "amount": "210", "createdAt": "2026-10-01T00:00:00.000Z",
                 "product": {"productName": "Jordan 4"}, "variant": {"variantValue": "10"}}]})
        return _Resp({"hasNextPage": False, "orders": [
            {"orderNumber": "O1", "amount": "190", "createdAt": "2026-09-01T00:00:00.000Z",
             "payout": {"salePrice": "200"}, "product": {"productName": "Dunk"},
             "variant": {"variantValue": "10.5"}}]})

    fetch = stockx.make_fetcher("cid", "sec", "key", get=get, post=post)
    items = fetch("rt")
    assert len(posts) == 1 and posts[0][1]["data"]["audience"] == "gateway.stockx.com"
    assert gets[0][1]["headers"] == {"Authorization": "Bearer acc", "x-api-key": "key"}
    assert gets[0][1]["params"]["listingStatuses"] == "ACTIVE"
    assert gets[1][0].endswith("/selling/orders/history")
    rows = [personal_own.normalize("stockx", i) for i in items]
    assert [(r["kind"], r["title"], r["price"]) for r in rows] == [
        ("listing", "Jordan 4 10", 210.0), ("sale", "Dunk 10.5", 200.0)]
    fetch("rt")
    assert len(posts) == 1  # access token cached
    assert stockx.make_fetcher("cid", "sec", "") is None


def test_stockx_market_provider_finds_size_and_lowest_ask(stockx):
    gets = []

    def get(url, **kw):
        gets.append((url, kw.get("params")))
        if url.endswith("/catalog/search"):
            return _Resp({"products": [{"productId": "P1", "urlKey": "aj4", "title": "AJ4"}]})
        if url.endswith("/variants"):
            return _Resp([
                {"variantId": "V9", "variantValue": "9", "sizeChart": {}},
                {"variantId": "V105", "variantValue": "10.5", "sizeChart": {}}])
        return _Resp({"lowestAskAmount": "180", "highestBidAmount": "150"})

    provider = stockx.make_market_provider(
        "cid", "sec", "key", lambda: "rt", get=get,
        post=lambda *a, **k: _Resp({"access_token": "acc"}))
    watch = {"name": "AJ4", "keywords": "FV5029-006", "size": "10.5"}
    raw = provider(watch)
    assert gets[0][1]["query"] == "FV5029-006"
    assert gets[2][0].endswith("/variants/V105/market-data")
    listing = personal_shoes.normalize(raw[0])
    assert listing["price"] == 180.0 and listing["url"] == "https://stockx.com/aj4"
    assert listing["title"] == "AJ4 · size 10.5" and listing["source"] == "StockX"
    assert provider({**watch, "size": "11"}) == []  # only 10 / 10.5 are tracked
    with pytest.raises(LookupError):
        stockx.make_market_provider("cid", "sec", "key", lambda: None, get=get)(watch)


def test_stockx_watch_requires_size_10_or_10_5_and_refreshes():
    body = {"kind": "stockx", "name": "AJ4", "keywords": "FV5029-006"}
    url = "/api/v1/personal/shoes/watches"
    assert _request("POST", url, headers=WRITE, json={**body, "size": "11"}).status_code == 422
    assert _request("POST", url, headers=WRITE, json=body).status_code == 422
    assert _request("POST", url, headers=WRITE, json={**body, "size": "10"}).status_code == 201
    seen = []

    def stockx_provider(watch):
        seen.append(watch["size"])
        return [{"key": "V10", "title": "AJ4 · size 10", "price": 200,
                 "source": "StockX", "url": "https://stockx.com/aj4"}]

    assert personal_shoes.refresh(stockx=stockx_provider) == "ok"
    assert seen == ["10"] and personal_store.list_listings()[0]["price"] == 200.0
