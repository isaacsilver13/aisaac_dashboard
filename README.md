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

## Current limitations

The Betting Aggregator and NBA Prediction entries are intentionally unavailable in the production profile until public monitoring URLs exist. Portfolio Analysis (formerly "Personal Finance") is registered in the `local` profile only until it's deployed to Fly.io.
