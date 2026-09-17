# Runbook: Portfolio Analysis

## `/health/ready` failing
- Confirm the Postgres database is reachable (`DATABASE_URL` secret) — this app has no other
  external dependency; readiness only checks DB connectivity.

## Positions look wrong after an import
- The ingestion/economics rules that turn a raw Fidelity CSV row into a position live in
  `backend/ingestion/` and `backend/economics/` (not `backend/app/`) — check
  `backend/scripts/reconcile_positions.py` and `reconcile_valuation.py` first; they compare
  computed output against the golden numbers in `docs/spec-handoff.md` and will usually
  pinpoint which symbol/rule diverged before you need to read the accounting code itself.
- Re-uploading the same export file is safe and idempotent (replaces its rows, doesn't duplicate).
