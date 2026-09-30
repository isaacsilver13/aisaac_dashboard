# AIsaac Dashboard

A standalone links and health dashboard for Isaac's applications.

## Structure

- `backend/` contains the FastAPI monitor and normalized health contract.
- `frontend/` contains the React dashboard.

The monitor checks configured public endpoints server-side. It does not access another application's database, local artifacts, authenticated data, or user financial data.

## Local development

```powershell
Set-Location backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
pytest
uvicorn app.main:app --reload
```

The dashboard backend uses port `8000`. The local Vinyl API should run on
port `8003` so the two health endpoints do not collide:

```powershell
Set-Location ../vinyl_api
python -m uvicorn vinyl_api.main:app --reload --port 8003
```

In another terminal:

```powershell
Set-Location frontend
npm install
npm run dev
```

Set `PROFILE=production` only when the dashboard should check the configured production endpoints. Production never uses localhost targets.

## Contract

A monitored service should expose a public liveness endpoint returning JSON with a `status` field. Optional scalar fields are surfaced as non-sensitive metrics. Services may also expose `provider_status`, `readiness`, or freshness fields, but the dashboard treats service liveness, readiness, provider state, and data freshness as separate signals.

The Betting Aggregator local profile uses `/api/v1/health` for process
liveness and `/api/v1/status` for provider/data state. The status endpoint is
read-only and must not return odds events, offers, credentials, quotas, or raw
provider errors.

The browser cannot provide arbitrary target URLs. All targets come from the profile registry in `backend/app/registry.py`.

## Adding or changing an app's URL

Every monitored URL lives in `backend/app/registry.py`, so a URL change is a one-line edit there. Each `AppDefinition` has a `local` and a `production` entry:

| Field | What it is |
|---|---|
| `product_url` | Where the card's click-through link goes (also page-checked). |
| `health_url` | Liveness endpoint. Returns JSON with a `status` field. |
| `readiness_url` | Optional. Readiness, tracked separately from liveness. |
| `metrics_url` + `metric_allowlist` | Optional. Only allowlisted scalar fields are shown. |

To change a URL, edit it in `registry.py`, then check it:

```powershell
Set-Location backend
python -m scripts.check_urls              # pings every URL in the production profile
python -m scripts.check_urls --profile local
python -m scripts.check_urls --ipv4       # if IPv6 to fly.dev is flaky on your network
```

The script prints `PASS` / `SLOW` / `FAIL` per URL and exits non-zero if any fail. `tests/test_registry.py` also guards against reintroducing retired hostnames.

To add an app, add an `AppDefinition` to both profiles (use `monitor_target="push"` for apps that report in with a heartbeat instead of exposing a public URL). Setting `enabled=False` on an entry stops it being checked and shows its card as "Not configured"; to remove an app from the dashboard entirely, delete its entry from that profile.

Most apps are single-container Fly apps, so their UI and API share one host. Vinyl is the exception (`vinyl-catalog` UI, `vinyl-api` API).

## Cold starts

Fly machines scale to zero. Each health check has a 10s timeout and retries once (connection error, timeout, or a 502/503/504) before an app is marked `down`. A response that needed the retry, or took more than about 3s, shows as **Slow / waking up** instead of down. A `down` card shows the error and the time of the last check.

## Current limitations

NBA Prediction is push-based (heartbeat only) and has no product URL in the production profile. The `local` profile still points at localhost ports and only works when those apps are running.
