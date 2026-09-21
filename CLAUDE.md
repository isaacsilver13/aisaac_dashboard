# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A standalone links-and-health dashboard for Isaac's other applications. `backend/` is a FastAPI monitor with a normalized health contract; `frontend/` is a React dashboard. The monitor only checks configured *public* endpoints server-side — it never accesses another app's database, local artifacts, authenticated data, or financial data.

## Commands

Backend (from `backend/`, Python >=3.11):
```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
pytest                          # full suite
pytest tests/test_file.py::test_name   # single test
ruff check .                    # lint
uvicorn app.main:app --reload   # run locally, port 8000
```

Frontend (from `frontend/`):
```
npm install
npm run dev      # vite dev server
npm run build    # tsc -b && vite build
npm run lint
npm run test     # vitest run
```

When running the dashboard locally alongside the Vinyl API, start Vinyl API on port 8003 (`uvicorn vinyl_api.main:app --reload --port 8003` from the `vinyl/api` repo) so it doesn't collide with the dashboard's own port 8000.

Set `PROFILE=production` only to check real production endpoints — production never targets localhost.

## Architecture

- `backend/app/registry.py` is the source of truth for monitored targets — **the browser cannot supply arbitrary target URLs**; every profile/service entry the frontend can query comes from this registry.
- `backend/app/monitoring.py` performs the actual health checks; `backend/app/incidents.py` + the SQLite file at `INCIDENTS_DB_PATH` (mounted as a Fly volume at `/data` in prod) track incident history; `backend/app/alerts.py` handles push heartbeats/alerting; `backend/app/reports.py` builds surfaced report data; `backend/app/schemas.py` defines the normalized health contract.
- **The health contract distinguishes separate signals**: a monitored service exposes liveness via a `status` field, and may separately expose `provider_status`, `readiness`, or freshness fields — these are never conflated into one flag. The Betting Aggregator's local profile specifically uses `/api/v1/health` for process liveness and `/api/v1/status` for provider/data state; the status endpoint is read-only and must never return odds events, offers, credentials, quotas, or raw provider errors.
- `runbooks/` (bundled into the Docker image at `/app/runbooks`, read via `RUNBOOKS_DIR`) holds per-service incident runbooks (`betting-aggregator.md`, `gym-tracker.md`, `portfolio-analysis.md`, `vinyl.md`) served by the dashboard itself, not just static docs.
- The Betting Aggregator and NBA Prediction registry entries are intentionally disabled in the production profile until those apps have public monitoring URLs. Portfolio Analysis (formerly referred to as "Personal Finance") is registered in the `local` profile only — that app hasn't been deployed to Fly.io yet, so there's no real URL to point at. Don't "fix" this as if it were a bug; add the production entry once it's actually deployed.
- Single-container deploy: the Dockerfile builds the frontend (Node stage) then copies its `dist/` into the Python/uvicorn image alongside `backend/app`; Fly.io (`fly.toml`, app `aisaac-dashboard`) serves it as one process with a persistent volume for the incidents DB.
