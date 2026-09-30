# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A standalone links-and-health dashboard for Isaac's other applications. `backend/` is a FastAPI monitor with a normalized health contract; `frontend/` is a React dashboard. The monitor only checks configured *public* endpoints server-side — it never accesses another app's database, local artifacts, authenticated data, or financial data. **One narrow exception:** Claude usage and Neon/Fly cost figures are *pushed* by external jobs to `POST /internal/metrics/{source}` (`claude`, `neon`, `fly`; guarded by `INTERNAL_REPORT_SECRET`, stored by `metrics_store.py`) and served from `GET /api/v1/command-center/financials`, which requires `DASHBOARD_READ_TOKEN` (a separate read-only token sent as `X-Dashboard-Token`). The dashboard holds no Claude, Neon or Fly credentials; the pushing scripts live in `scripts/` (see `scripts/README.md`). Neon is reported as compute hours per project (its API has no dollars), and Fly cost is an estimate reconciled to a manually entered invoice total (Fly has no billing API).

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
- Production registry entries: NFL Confidence, Betting Aggregator, Gym Tracker, Portfolio Analysis and Vinyl are all deployed on Fly.io and monitored. NFL, Betting, Gym and Portfolio are **single-container apps** — one Fly host serves both the UI and the `/api/v1/*` API (`nfl-confidence-web`, `betting-aggregator-api`, `isilver-gym-tracker-api`, `portfolio-analysis-api`), so every URL for those apps uses that one host; the old `-web`/`-api` split hostnames no longer exist (`tests/test_registry.py` guards this). Vinyl is still split (`vinyl-catalog` UI + `vinyl-api`). NBA Prediction is push-based (heartbeat only) with no product URL in production — that is intentional, not a bug.
- Fly machines scale to zero, so `monitoring.py` gives each health check a 10s timeout and retries once (connection error, timeout, or 502/503/504) before reporting `down`. A response that needed the retry, or took over ~3s, is reported as `slow` ("waking up") — a non-failing state that never opens an incident. `down` results carry the error in `detail` and the check time in `checked_at`.
- Single-container deploy: the Dockerfile builds the frontend (Node stage) then copies its `dist/` into the Python/uvicorn image alongside `backend/app`; Fly.io (`fly.toml`, app `aisaac-dashboard`) serves it as one process with a persistent volume for the incidents DB.
