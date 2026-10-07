# AIsaac Dashboard — Personal Feeds and Daily Digest Claude Handoff

Status: ready for implementation
Scope: `repos/aisaac_dashboard` only (FastAPI backend, React frontend, Fly configuration, GitHub Actions)

## Objective

Implement the private Sports, News, Shoes, and daily email digest experience
described in the canonical plan:

- [Personal feeds and daily digest plan](2026-10-07-personal-feeds-and-daily-digest.md)

Also preserve and include the completed Command Center Central-time refresh
timestamp change described below.

## Starting point and branch policy

- Work from the current checked-out AIsaac branch and preserve all unrelated
  existing working-tree changes, especially the CI-observability work.
- **Do not merge, cherry-pick, rebase onto, or otherwise incorporate
  `origin/feature/ai-digest`.** It is an older, unmerged AI-news-only feature
  and is not the implementation base for this project.
- Do not deploy, enable a scheduled workflow, set Fly/GitHub secrets, create a
  provider account, or incur paid usage without explicit user approval.
- Inspect `CLAUDE.md`, `README.md`, and the canonical plan before editing.

## Required carried change: Command Center timestamps

These completed, uncommitted changes must travel with the personal-feeds work
and be included in the final commit/PR:

- `frontend/src/time.ts`: adds `centralTimestamp`, which formats a precise
  `America/Chicago` timestamp as `Jan 1, 2026 12:30:00PM CST`.
- `frontend/src/pages/CommandCenter.tsx`: uses it for both **Last updated** and
  **Last checked**.
- `frontend/src/time.test.ts`: locks the expected winter CST and summer CDT
  output.

The formatter intentionally emits `CDT` during daylight saving time; that is
the correct abbreviation for `America/Chicago` rather than a mislabeled CST.

Already verified for this carried change:

```powershell
Set-Location frontend
npm run test -- --run src/time.test.ts
npm run lint
npm run build
```

All passed. Vite reported only the project’s existing large-bundle warning.

## Implementation sequence

1. **Provider spike and decisions**
   - Perform the canonical plan’s fixture-backed provider spike first.
   - Verify current terms, attribution, coverage, quotas, and free-tier status
     from authoritative provider documentation before selecting any source.
   - Record approved/rejected providers, gaps, limits, and fixture provenance
     in a new concise document under `docs/`.
   - Do not scrape sites, use undocumented endpoints, provision credentials, or
     add a paid dependency. Keep a feature unavailable or use an official link
     when no compliant source exists.

2. **Foundation**
   - Add a token-gated `personal/` backend boundary, typed domain models,
     fixture providers, safe configuration status, and a non-destructive SQLite
     store on the existing Fly volume.
   - Use explicit migrations (`CREATE TABLE IF NOT EXISTS` plus indexes) and
     persist source freshness/error/provenance separately from rendered data.
   - Keep all reads behind `DASHBOARD_READ_TOKEN` and state changes behind
     `DASHBOARD_WRITE_TOKEN`; expose neither provider credentials nor raw
     upstream errors to the browser.

3. **Vertical slices**
   - Implement Sports, then News, then Shoes exactly as scoped by the
     canonical plan. Use fixture-backed automated tests before optional live
     smoke checks.
   - Preserve last successful snapshots when a refresh fails. Refresh only on
     explicit page load/manual action; do not add an implicit background
     poller.
   - Reuse the current React conventions: `Table`, theme tokens, Iconoir,
     Motion, responsive navigation, loading/empty/error/stale states, and
     source links/attribution.

4. **Digest**
   - Create a pure renderer with plaintext and HTML output plus an idempotency
     key based on the `America/Chicago` local date.
   - Add the internal, secret-protected send endpoint and `digest_runs` record
     so retries and DST overlap cannot send duplicate messages.
   - Add a manually dispatchable/no-send test path. A future scheduler may
     invoke hourly, but the server must only send at local 8:00 AM and must not
     be activated without approval.

5. **UX and operations**
   - Add token-protected Sports, News, Shoes destinations, a compact Today
     view, and Settings indicators for only configured/not-configured state.
   - Do not expose address, sender, credentials, upstream payloads, or personal
     preferences outside the private dashboard.

## Required verification

- Backend tests for store migration, authorization, normalization, filters,
  freshness/error preservation, source deduplication, and digest idempotency
  including DST/retry cases.
- Frontend tests for token-gated states, loading/empty/error/stale views,
  filters, save/dismiss controls, responsiveness, and the carried timestamp
  formatter.
- Run:

```powershell
Set-Location backend
pytest
ruff check .

Set-Location ..\frontend
npm run lint
npm run test
npm run build
```

- Manually test locally with fixtures: dashboard refresh, sports/news filters,
  a shoe-watch change, and a no-send digest dry run. Do not use live provider
  calls in CI.
- Obtain an independent review of meaningful implementation changes before a
  PR. Report exactly what was verified and any unavailable provider or
  production-only validation.

## Definition of done

The feature is complete only after the canonical plan’s provider gate has
recorded its decisions, each shipped vertical has fixture-backed coverage and
safe private UX, the digest is demonstrably idempotent in no-send mode, the
Central-time timestamp change remains intact, and the required checks pass.
Production scheduling and secrets remain disabled pending explicit approval.
