> **Status (2026-10-03):** this is the Phase 0 snapshot taken before the redesign. Since then the theme/Iconoir/sidebar/Table foundation, health history, all five application tabs, Settings, Automations, Tasks, GitHub detail and Motion have shipped (PRs #5-#16). Gaps and risks below that are not mentioned in the README or CLAUDE.md should be re-checked before relying on them.

# AIsaac Dashboard — Phase 0 Audit (2026-10-03, master @ 8bb1656)

Source: code-only read (no live Fly/GitHub checks). Backend details come from a subagent read; spot-verify before relying on a specific line.

## Repository Summary
Single deployable: FastAPI backend (request-driven, no scheduler) serving a Vite/React SPA from the same origin, one Fly machine (`aisaac-dashboard`, ewr, 1GB volume at `/data`, auto-stop, min 0). Three raw-sqlite DBs. Frontend is plain global CSS, dark-only, 5 routes, local `useState` + one fetch hook.

## Existing Structure
- **Frontend** (`frontend/src`): React 19, react-router-dom 7, Vite 8, Vitest 5, TS 6, recharts 3, lucide-react 1.43. No Tailwind/UI lib/state lib. Routes: `/` CommandCenter, `/agents`, `/analytics`, `/tasks`, `/coms` (no 404, no nesting, no lazy). `api.ts` plain fetch wrappers; `hooks/useAsyncData.ts` fetches once on mount (no polling/cache/abort). `components/primitives` (Badge, Card, StatusDot, Stat, Skeleton, EmptyState, ErrorState, PageHeader, SectionHeader, Divider, `Tone`), `components/layout` (AppShell, Sidebar, MobileTopBar, MobileDrawer), page-specific dirs (dashboard, analytics, coms).
- **Backend** (`backend/app`, ~1.7k LOC): `main.py` endpoints, `registry.py` (6 apps, static per-profile tuples), `github_registry.py`, `monitoring.py`, `github_client/monitor.py`, `ci_events.py`, `incidents.py`, `alerts.py` (Resend), `notify.py` (ntfy), `reports.py` (in-memory heartbeats), `metrics_store.py` (latest push snapshot per source).
- **Deploy**: multi-stage Dockerfile (Node 22 build → python 3.12-slim; Python deps hand-listed, NOT read from pyproject), CI `ci-deploy.yml` on master (ruff, pytest, FE lint/test/build, `flyctl deploy`).

## Reusable Assets (Keep)
- `useAsyncData`, `api.ts`/`types.ts`, `Tone` + Badge/StatusDot/Stat/Skeleton/EmptyState/ErrorState/PageHeader/SectionHeader, Card (variant use TBD).
- Backend: registry model, monitoring state machine (up/slow/degraded/down/unavailable/stale), incidents, ci_events, GitHub monitor, internal-push pattern (`/internal/*` + secret), runbooks endpoint, existing tests (~79 backend, 9 FE files).
- Cold-start handling (10s timeout + retry; `slow` = waking, never an incident) and the CLAUDE.md health contract (liveness/provider/readiness/freshness stay separate) — preserve.

## Refactor / Replacement Candidates
| Item | Call | Why |
|---|---|---|
| `styles.css` (493 lines, dark-only, legacy + `ui-*` blocks, hardcoded hex, light-theme leftovers e.g. `.app-card` bg) | Replace | No theme layer; need light+dark token system |
| `theme/tokens.ts` | Refactor/Replace | Imported nowhere; drifted from CSS vars; pick ONE token source |
| `AppShell`/`Sidebar`/`MobileDrawer`/`navItems` | Refactor | Shell fetches dashboard itself; needs collapsible, grouped nav, new IA |
| Pages (5) | Replace/re-map | Current routes ≠ target IA; Tasks page is derived open-PRs, not tasks; Coms ≈ future Automations/Logs input |
| `AppCard` (151), `FinancialsPanel` (207) | Refactor | Large, own fetch/inline mutations |
| `StatusBadge` + `CiStatusBadge` | Refactor | Duplicates; fold onto `Tone`/StatusDot |
| `Analytics` inline `<table>` | Replace | Only table; no sort/filter; build one shared Table |
| `CommitActivityChart` | Keep, wrap | recharts works; needs shared chart shell |
| `MobileDrawer` | Unknown | Hand-rolled focus trap; decide if generic Drawer replaces it |
| `fonts` (Google `@import`, Manrope/DM Mono) | Replace | Spec is Inter; render-blocking import |

## Backend Capabilities
Exists: `GET /api/v1/dashboard` (live poll, 20s cache: state, response_ms, http_status, readiness, provider_state, page_state, metrics_state, allowlisted scalar `metrics`), incidents (list/resolve), analytics (per-repo CI status, open PR/issue counts, commits_7d, last_commit), coms (CI event feed), agents (static), runbooks, financials (token-gated claude/neon/fly latest snapshot), `/internal/{report,metrics,ci-report}`.
Not exposed: per-app detail, any history/time series, deployments, logs, tasks, automations, settings.

## Missing Capabilities
- **Health history/uptime/latency/sparklines**: nothing persisted; check results never stored; polling only happens when `/dashboard` is hit (incidents/alerts also only then; transition state in-memory so first check after restart opens nothing). Needs a table + poller (machine auto-stops).
- **Data freshness**: `CheckResult.freshness` declared but never populated; `generated_at`/freshness pass through as strings only.
- **Deployments**: no version/SHA/release anywhere; no GitHub deployments/releases use. Fly access would break the "dashboard holds no Fly credentials" rule → push from outside or re-decide.
- **Logs**: none. Would be a push source or Fly-credential decision.
- **GitHub**: has Actions latest run, open issues/PRs, 7d commits only (capped at 100, no pagination, errors swallowed, no rate-limit handling, 24 calls/refresh). Missing: commit/PR time series, releases, contributors, languages, branches, run history, metadata; dashboard repo itself unregistered.
- **Tasks/Automations**: no backend concept. Automations today = manual GH Action, externally scheduled push scripts (no in-repo scheduler), Claude statusline push. Agents `last_run_*` always null.
- **Settings/app metadata**: registry is code-only (no env/version/repo link on app; joined to GitHub by id); adding apps needs redeploy.
- **Frontend**: Table, filters, Drawer, Toast, command palette, theme toggle/persistence, URL-synced filters, polling.

## Dependency Assessment
- Present: react-router, recharts, lucide-react. Absent: Iconoir, Motion, any table/date/UI lib.
- **Iconoir vs lucide (decision deferred to you)**: lucide is used in 15 files / 24 icons, so swapping is a small mechanical change (most are named imports; nav uses `LucideIcon` type). Keeping both = overlap; spec says Iconoir sole. Check Iconoir has equivalents for the 24 (not verified here).
- **Motion** (`motion/react`): clean add, no existing animation lib; current motion is CSS keyframes (`rise`, `spin`, `ui-shimmer`). Existing reduced-motion block covers only skeleton + interactive card, NOT `rise`/spin/transitions.
- Tables: TanStack Table not installed; decide hand-rolled sort/filter vs lib. Dates: none; native `Intl` likely enough.
- All deps pinned `"latest"` (lockfile present; CI uses `npm ci`, Dockerfile uses `npm install` → image can drift from CI).

## Gap Matrix
| Area | Exists | Partial | Missing | Notes |
|---|---|---|---|---|
| Shell | | ✓ | | Grid shell + mobile drawer; shell does own fetch |
| Sidebar | | ✓ | | Fixed 5 items, no collapse/sub-nav |
| Tables | | | ✓ | One unsortable table; no component |
| Health | | ✓ | | Live state only; no history/trends |
| Deployments | | | ✓ | No data source |
| Data | | ✓ | | Only passthrough metrics; freshness field dead |
| Logs | | | ✓ | No source |
| GitHub | | ✓ | | Counts + CI only; no time series/detail |
| Tasks | | | ✓ | Current page is open-PR list |
| Automations | | ✓ | | Scripts/GH Action exist, no run model |
| Settings | | | ✓ | Registry is code |
| Design system | | ✓ | | Primitives + `Tone` exist; tokens split/dark-only |
| Motion | | ✓ | | CSS only; reduced-motion incomplete |

## Technical Risks
1. No metrics persistence; `METRICS_DB_PATH` unset in fly.toml → defaults off-volume, snapshots likely lost on redeploy (verify).
2. Lazy polling + auto-stop machine: history/uptime needs a poller and wake strategy (the 30s Fly `/health` check may keep it warm — unverified).
3. SQLite single-writer, single machine; no pruning on incidents/ci_events.
4. Security gaps to be aware of before widening API: all `/api/v1` unauthenticated incl. `POST incidents/{id}/resolve` (no existence check); internal secret uses `!=` not `hmac`; runbook path param only lightly sanitized.
5. Dockerfile hand-lists Python deps: any new backend dep must go in both pyproject and Dockerfile; CI deploy gated on `ruff check`.
6. Duplicate fetches (shell + CommandCenter; Analytics + Tasks); no cache/abort on FE.
7. FE test gaps: no page/routing/layout/AppCard tests; no e2e/visual.
8. Architecture constraint: monitor only hits public endpoints configured in registry; browser never supplies URLs; no other apps' DBs/credentials.
9. No router 404; unlazy bundle; `theme-color` meta stale.
10. nba-prediction is push-only and nothing in this repo sends its heartbeat; nfl/nba have no runbooks.

## Recommended Implementation Architecture
- Keep single-origin SPA + FastAPI. Add nested routes matching the IA (`/apps/:id/{overview,health,deployments,data,logs}`, `/github/...`, `/tasks`, `/automations`, `/settings`) under one layout route; lazy-load pages.
- One token source: CSS variables with `data-theme` light/dark (move `tokens.ts` values into CSS or generate one from the other); self-host Inter.
- Shared primitives built once: `Table` (sort/filter/search), `Drawer`, `Toast`, `Tabs`, `TimeRangePicker`, chart wrapper (recharts), `StatusIndicator` (fold the two badges). Extend, don't duplicate, existing primitives.
- Lift data fetching to a single provider/hook layer (shared dashboard fetch, optional polling) so the shell and pages stop double-fetching.
- Backend grows by additive endpoints (`/apps/:id`, `/apps/:id/health-history`), backed by a new history table written by a poller; deployments/logs via new `/internal/*` push sources to keep the no-credentials rule.

## Phase 1 Recommendation
Frontend foundation only, no new backend: (a) token layer + light/dark + Inter + theme toggle; (b) new shell/collapsible Sidebar with the target nav and route skeleton (stub pages, 404); (c) shared `Table` replacing the Analytics table as proof; (d) icon decision applied (Iconoir swap or keep). Defer Motion to Phase 2 apart from the sidebar collapse. Ship health-history storage as the first backend phase after that, since Health/Overview trends depend on it.

## Second Brain (shipped, master f918e01 / PR #4)
Already built: `second_brain_store.py` (SQLite on `/data`), `POST /internal/second-brain/sync`, token-gated `GET /api/v1/second-brain/{summary,notes,notes/{path}}`, `scripts/second_brain_push.py` (refuses secret-like notes), frontend `pages/SecondBrain.tsx` (search + wikilink nav, route `/second-brain`), `SecondBrainPanel` on Command Center, `token.ts` (shared read-token storage), `react-markdown` installed.
- **Redesign work**: move it to `/knowledge` under the new nav, rebuild its list on the shared `Table`, restyle with tokens/Iconoir. Reuse `token.ts`, `secondBrain.ts` and the existing endpoints; no backend change.
- Source decision stands: push model, token-gated, markdown lib already chosen.

## Decisions recorded (2026-10-03)
- Icons: Iconoir (remove lucide after migration).
- Deployments/Logs: Fly-credentialed pull is allowed (supersedes the push-only assumption; CLAUDE.md "no Fly credentials" rule will need updating).
- Second Brain: keep the existing push model (`second_brain_push.py` -> `/internal/second-brain/sync` -> store), token-gated, markdown library; update cycle out of scope. Supersedes the earlier GitHub-hosted preference.
- NBA heartbeat and dashboard self-registration: not now.

## Open questions
None outstanding.
