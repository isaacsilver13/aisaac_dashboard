# AIsaac Dashboard — Application Statistics Investigation

Status: draft
Scope: `repos/aisaac_dashboard` dashboard monitor and per-application pages; read-only inspection of each monitored application's existing public health/metrics contracts

## Goal

Determine why the six application pages expose too little useful data, define a safe and consistent statistic set for each application, and produce a narrowly scoped implementation recommendation backed by observed endpoint payloads and UI behavior.

The target experience is:

- every Overview page has a compact, decision-useful snapshot rather than only liveness and repository activity;
- every Data page has the application-specific figures it is permitted to expose, with clear freshness and history where the data type supports it; and
- absent, stale, unsupported, or deliberately withheld data is explicit rather than indistinguishable from an empty dashboard.

## Current evidence

- `frontend/src/components/application/OverviewTab.tsx` renders health signals plus repository and CI data, but not `result.metrics`; the application-specific metrics are isolated in `DataTab.tsx`.
- `backend/app/monitoring.py` only carries top-level scalar values and applies each registry entry's `metric_allowlist`. Nested values, arrays, and objects are discarded.
- `backend/app/registry.py` defines a `metrics_url` only for Vinyl, Betting Aggregator, and Gym Tracker in production. NFL Confidence and Portfolio Analysis therefore cannot currently provide a distinct metrics response through this path. NBA Prediction is push-based.
- `backend/app/health_history.py` persists numeric values only, so string, Boolean, and timestamp metrics can be shown as current values but cannot be charted.
- `CheckResult` contains `freshness`, but the monitor does not presently derive it from an endpoint field. Fields such as `generated_at` remain ordinary reported metric strings.

These observations are code-level hypotheses, not evidence that a particular production endpoint is wrong. The first phase must compare them with the currently deployed, safe public contracts.

## Constraints and non-goals

- Preserve the dashboard's boundary: server-side checks only against registry-configured public endpoints; no direct application databases, local artifacts, arbitrary browser-provided URLs, credentials, quotas, raw provider errors, or user financial data.
- Keep liveness, readiness, provider state, freshness, and application statistics as separate signals. A missing or stale metric must not silently change health state unless the existing contract says it should.
- Do not add a paid data source, deploy, alter production configuration, or change another repository during investigation.
- This is not a redesign of deployments, logs, repository analytics, or the command center.
- Limit metrics to low-cardinality, non-sensitive summaries. In particular, require an explicit privacy review before displaying any portfolio or user-level figure.

## Approach

1. Establish a reproducible baseline for all six applications.
   - Record the registry configuration for both local and production profiles: monitor target, health/readiness/metrics URLs, allowlist, and whether the app can report pushed data.
   - Query only the configured public endpoints in the active profile, save redacted status/payload schemas and response timing, and label every unavailable/cold-start response separately from a missing field.
   - Capture the current dashboard response and screenshot each Overview and Data tab at desktop and narrow widths. Note empty states, stale labels, hidden values, and mismatches between endpoint payloads and rendered rows.

2. Trace each statistic from source to screen.
   - For every observed field, trace endpoint or push payload -> monitor normalization -> allowlist -> `CheckResult` -> history storage -> frontend tab.
   - Classify fields as: health signal, safe current stat, safe numeric time series, display-only timestamp/string, sensitive, high-cardinality, or unavailable.
   - Identify the precise loss point for every useful field that fails to render (for example: no endpoint, wrong nesting, absent allowlist entry, unsupported type, fetch failure, or an overview-only presentation gap).

3. Define the minimum metric contract with the owning applications.
   - Establish a dashboard-wide baseline: checked time, liveness, response time, readiness/provider state when applicable, data freshness, and a small application-specific snapshot.
   - Propose three to five safe, decision-useful application metrics per app from its existing public contract. Prefer counts, last-success timestamps, bounded status summaries, and aggregate processing/coverage figures over raw records.
   - For each app, choose whether the source is its existing health response, an existing metrics/status endpoint, a new public read-only summary endpoint, or (for NBA Prediction) an authenticated push report. Document field names, types, units, freshness semantics, expected cadence, and the owner repository.
   - Obtain an explicit decision for any metric that could reveal financial, personal, provider-quota, or other sensitive information. Do not expose it by default.

4. Select the smallest compatible dashboard change.
   - If the endpoints already provide the approved fields, add only the necessary allowlist entries and display them as a shared compact metrics section on Overview, retaining the detailed Data table and charts.
   - If an endpoint has a safe but nested schema, extend normalization only for the documented shape; do not recursively flatten arbitrary payloads.
   - If an application lacks a safe summary endpoint, scope that endpoint change to its owning repository as a separately approved follow-up, rather than making AIsaac inspect private data.
   - Normalize freshness into its dedicated field only when the source semantics and timestamp format are documented. Decide which numeric metrics merit history, and retain current-only display for strings, Booleans, and timestamps.
   - Specify loading, empty, unavailable, stale, and unsupported-history states so that reduced data is intelligible.

5. Implement only after the contract is approved, then verify end-to-end.
   - Add focused backend tests for allowlists, normalization, freshness parsing, and numeric-history behavior.
   - Add frontend tests proving approved metrics are shown on both Overview and Data tabs and that empty/stale/sensitive states are clear.
   - Run the focused backend and frontend suites, lint/build checks, then manually inspect every application page against representative local fixtures. Before any production release, repeat the public endpoint and rendered-page smoke test without logging sensitive payloads.

## Deliverables from the investigation

- A per-application field inventory containing source URL or push report, current payload schema, render status, sensitivity classification, and recommended disposition.
- A small approved metric contract for each app, including freshness/cadence semantics and a decision log for excluded fields.
- A file-level implementation plan that names registry, monitor, history, API/type, frontend component, and test changes; application-repository changes are listed separately.
- A baseline-versus-proposed page comparison showing what a user will newly be able to see.

## Verification

- Automated: targeted monitoring, registry, history, and application-tab tests; backend `pytest` and `ruff check .`; frontend `npm run lint`, `npm run test`, and `npm run build` once code is approved.
- Manual: inspect all six Overview and Data tabs with populated, empty, stale, and unavailable fixtures at desktop and narrow widths; confirm no sensitive values appear in rendered DOM or network responses.
- Production smoke test (approval required): request only the configured public endpoints, validate field presence/type/freshness, and compare the rendered AIsaac pages without retaining raw payloads.

## Risks / decisions needed

- “Enough stats” needs a product definition: this plan proposes three to five approved application-specific metrics per app plus common health context. Confirm that target before implementation if a denser dashboard is desired.
- Several desired metrics may not exist in current public contracts. Those require separate, scoped work in the owning repositories and may require their own data/privacy review.
- NBA Prediction is push-only; without a reliable heartbeat/report publisher, it cannot gain live application statistics through polling.
- History remains opportunistic while the AIsaac process is not polling; charts must show gaps rather than implying continuous collection.
