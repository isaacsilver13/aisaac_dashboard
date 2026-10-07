# AIsaac Dashboard — Private Sports, News, Shoes, and Daily Digest

Status: draft
Scope: `repos/aisaac_dashboard` (FastAPI backend, React frontend, Fly deployment)

## Goal

Extend AIsaac into a private personal-interest dashboard with three first-class
areas:

1. Sports: Chicago Bears, Bulls, and White Sox first; NFL and NBA league-wide;
   MLB postseason coverage; and college football and basketball.  Users can
   filter college matchups by conference and whether either team is AP Top 25.
2. News: ranked, source-linked reading recommendations for economics, finance,
   technology, mathematics, data science, and politics.
3. Shoes: saved searches and listings, product/release links, restock/release
   watches, and price-change watches.

The dashboard refreshes these views on demand. A separate idempotent daily job
generates and emails one digest at 8:00 AM America/Chicago.

## Constraints and non-goals

- This remains a single-user private dashboard. All personal-feed reads require
  `DASHBOARD_READ_TOKEN`; state-changing actions require the separate
  `DASHBOARD_WRITE_TOKEN`; the scheduler endpoint uses only
  `INTERNAL_REPORT_SECRET`.
- Use only free/public sources whose current terms, coverage, attribution, and
  rate limits permit this use. Do not scrape websites or use undocumented
  endpoints. No paid plans, betting/odds data, account connections, checkout,
  or purchase automation.
- Provider credentials, recipient addresses, and saved personal preferences stay
  in environment variables or the existing Fly secret workflow, never source
  control. Browser clients never receive upstream credentials.
- Scheduled digest generation is the one scheduled refresh. Dashboard data
  otherwise refreshes only from an explicit page load/refresh control. The
  digest identifies its content freshness.
- Do not modify the unrelated in-progress CI-observability changes currently in
  the working tree.

## Provider decision gate

Before product code is written, run a short, fixture-backed integration spike
and record the result in `docs/`:

| Need | Required evidence | Initial candidate / fallback |
| --- | --- | --- |
| NFL, NBA, MLB, college schedules and results | Covers requested leagues and team IDs; legal reuse; documented rate limits; dates/statuses | A documented sports-data provider with a free tier. If none covers a league, ship that league as a manually configured official-scoreboard link rather than scrape it. |
| College ranking and conferences | AP Top 25 (or clearly labeled equivalent) with poll date, team identity, and conference metadata | A documented college-football/basketball data source; keep rankings unavailable rather than infer them. |
| Topic news | Stable RSS/Atom feeds or documented free API; canonical URL/date/source; redistribution rules | Configured RSS/Atom allowlist. GDELT may be evaluated only as a discovery/ranking input, with links back to publishers. |
| Marketplace listings | Search, listing URL, image and price reuse explicitly permitted; production access available | eBay Browse API. It supports search and price/condition filters, but production access is subject to eBay approval, so it is not a guaranteed dependency. |
| Shoe releases/restocks | Licensed feed/API or retailer-provided links usable under its terms | Curated official launch-calendar links configured by the user. Do not build retailer/marketplace scrapers. |

The provider adapter boundary makes the dashboard independent of a particular
vendor. No provider key is requested or provisioned until the spike passes. The
existing eBay documentation says its Browse API requires an application token
and that production access is subject to approval; it is appropriate only after
that approval. [eBay Browse API](https://developer.ebay.com/api-docs/buy/api-browse.html)

## Architecture

Add a `personal_store.py` SQLite store on the existing Fly volume and a
`personal/` backend package:

- `providers/`: small typed clients and normalizers for sports, rankings, RSS,
  listings, and releases. Each has a fixture client for tests.
- `refresh.py`: on-demand orchestration, bounded parallel upstream calls,
  provider-specific TTLs, error isolation, and freshness records. Persist the
  last successful normalized snapshot so a temporary provider failure does not
  erase useful content.
- `personal_store.py`: migrations guarded by `CREATE TABLE IF NOT EXISTS` and
  explicit indexes; no automatic destructive migration.
- `digest.py`: a pure renderer that selects the saved/up-to-date snapshot,
  applies user preferences, creates a plaintext and HTML email, and returns an
  idempotency key of `America/Chicago` local date.

Initial tables:

- `preferences` — one private profile: topics, teams, leagues, conference and
  Top-25 defaults, and digest settings.
- `sports_events`, `team_aliases`, `rankings`, and `sports_refreshes` —
  normalized matchups/results, provider IDs, conference/ranking metadata, and
  freshness/provenance.
- `news_items`, `news_sources`, `news_preferences`, and `news_refreshes` —
  canonical URL, title, source, publication time, topic scores, saved/dismissed
  state, and provenance.
- `shoe_watches`, `shoe_listings`, `shoe_releases`, and `listing_snapshots` —
  saved queries/links, alerts criteria, observed prices, source, and availability
  state. Retain a bounded price history.
- `digest_runs` — local date, attempted/sent time, snapshot freshness, result,
  and provider errors. The unique local-date key prevents duplicate emails.

Expose versioned, token-gated API routes under `/api/v1/personal/`:

- `GET /sports` with league, team, date window, conference, and
  `top_25_only` filters; `POST /sports/refresh` triggers an on-demand refresh.
- `GET /news`; `POST /news/refresh`; write-token routes to save/dismiss an
  article and set topic preferences.
- `GET /shoes`; write-token routes to create/edit/archive saved searches and
  release links; `POST /shoes/refresh` refreshes only enabled watches.
- `GET/PATCH /preferences` for the single profile.
- `POST /internal/daily-digest/send`, restricted to the internal secret, which
  performs the digest refresh/render/send sequence idempotently.

## Delivery phases

1. **Foundation and provider spike**
   - Document approved sources, attribution, quota/backoff behavior, payload
     fixtures, and the coverage gaps for each requested league.
   - Add typed domain models, personal SQLite configuration, migration tests,
     token dependencies, fixture-backed provider interfaces, and per-provider
     freshness/error records.
   - Add Settings status indicators that expose only “configured/not
     configured,” consistent with the existing dashboard.

2. **Sports vertical slice**
   - Implement Bears, Bulls, and White Sox next-game/recent-result cards and
     league scoreboards for NFL, NBA, and MLB postseason.
   - Add college football/basketball matchup list with date, league, conference,
     and `top_25_only` filters. A matchup matches when either ranked team is in
     the selected Top 25 poll; show the poll date and an unavailable state when
     a ranking source is not current.
   - Add empty/loading/error/stale states and source links. Persist snapshots so
     pages can render their last successful data while a refresh fails.

3. **News vertical slice**
   - Build a source allowlist and topic classifier using source/topic mapping,
     keywords, recency, and explicit save/dismiss feedback—no paid LLM or
     undisclosed recommendation model.
   - Deduplicate by canonical URL, keep headlines/excerpts only where feed
     terms permit, and always link to the original publisher. Add filters for
     the six requested topics, save/dismiss controls, and “why recommended.”

4. **Shoes vertical slice**
   - Implement saved watch definitions (keywords, size, condition, price cap,
     and source), eBay-backed listing search only if approved, and user-managed
     official release/restock links otherwise.
   - Show listing price, shipping where supplied, condition, source, observed
     time, outbound link, and price history. Detect price/availability changes
     during a dashboard or digest refresh; never purchase, bid, sign in, or
     automate retailer actions.

5. **Daily email digest and scheduling**
   - Extend the existing Resend integration with a reusable send function;
     retain `ALERT_TO_EMAIL` as the private recipient and configure a verified
     sender before production delivery.
   - Build a concise digest: priority team games/results, Top-25 college games,
     selected news, and changed shoe watches, with freshness timestamps and
     direct dashboard/source links.
   - Add a GitHub Actions scheduler that invokes the protected internal endpoint
     hourly. The server evaluates `ZoneInfo("America/Chicago")`, sends only at
     local 8:00 AM, and `digest_runs` prevents retries or DST overlap from
     sending a second digest. This avoids a fixed UTC cron drifting across DST.
   - Add a dry-run workflow/manual dispatch and a no-send local mode. Do not
     activate the scheduled workflow or set Fly/GitHub secrets without explicit
     approval.

6. **Private UX, operations, and rollout**
   - Add Sports, News, and Shoes sidebar destinations plus a compact “Today”
     section on Overview; use the existing Table, token, Iconoir, Motion, and
     responsive mobile patterns.
   - Add a settings panel for preferences, source status, digest state, and
     “refresh now.” Never display credentials or raw upstream error bodies.
   - Roll out locally with fixtures, then configured free sources, then a
     one-time manual digest. Observe source freshness and email idempotency for
     several days before enabling the schedule.

## Verification

- Backend unit tests for normalization, filters, conference/top-25 semantics,
  deduplication, provider errors, TTL/freshness, store migrations, authorization,
  and exactly-once digest behavior across retries and DST boundaries.
- Contract tests against recorded, redacted provider fixtures. Live smoke tests
  are opt-in and rate-limited; no CI job should depend on an external provider.
- Frontend Vitest coverage for loading, empty, stale, error, filters, saved
  state, mobile navigation, and token-required views.
- Run focused backend tests, `ruff check .`, `npm run lint`, `npm run test`, and
  `npm run build`. Manually verify local dashboard refresh, every filter, one
  watch change, and a digest dry run with no email send.
- Before a production change, independently review the implementation and verify
  the deployed private token gate, source attribution, digest recipient/sender,
  and one scheduled send at 8:00 AM America/Chicago.

## Open decisions resolved as assumptions

- “Daily at 8:00 AM” means America/Chicago and uses the currently configured
  `ALERT_TO_EMAIL`; no email address needs to be placed in this plan.
- “Around the league” means schedules, scores/results, standings where an
  approved source supports them, and source-linked news—not odds, predictions,
  wagers, or live play-by-play.
- “Recommendations” means transparent preference/rules-based ranking in v1.
  Personalized ML, generated article summaries, purchase alerts outside the
  daily digest, and multi-user sharing are deferred.
