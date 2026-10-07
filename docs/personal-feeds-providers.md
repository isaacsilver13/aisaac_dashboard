# Personal feeds — providers, status and digest scheduling

Plan: [personal feeds and daily digest](plans/2026-10-07-personal-feeds-and-daily-digest.md).

## Shipped (stage 1)

| Area | Status | Source |
| --- | --- | --- |
| News | Live | Public RSS/Atom allowlist in `backend/app/personal_news.py` (`FEEDS`): Federal Reserve, SEC, NPR (Economy/Business/Technology/Politics), Ars Technica, arXiv (math, stat.ML), Quanta. Headlines + links only; every item links to the publisher. |
| Daily digest | Built, **not scheduled** | `personal_digest.py`, `POST /internal/daily-digest/send` |
| Sports | **Deferred** | Provider spike not done. ESPN's public JSON endpoints are undocumented, so excluded by the plan's rules. Needs a documented free-tier provider per league (NFL, NBA, MLB postseason, college + AP Top 25) or official-scoreboard links. |
| Shoes | **Deferred** | eBay Browse API needs production approval; otherwise user-managed official release links. No scraping. |

Feed liveness was checked once on 2026-10-07 (all 10 returned HTTP 200 and parsed). Each publisher's
reuse terms still need a read before relying on this beyond personal use; the app stores only titles and URLs.
Feed fetch errors are stored as a short code (`fetch_failed` / `parse_failed`), never the upstream body.

## Digest behaviour

- The endpoint sends only when Chicago local time is >= 08:00 **and** no digest was sent for that local date
  (`digest_runs`, primary key = `America/Chicago` date). Early calls return `too_early`; repeats return
  `already_handled`; an unconfigured/failed email leaves the day retryable.
- `?dry_run=true` renders and returns the digest without sending or writing anything.
- Needs `RESEND_API_KEY`, `ALERT_TO_EMAIL`, a verified `ALERT_FROM_EMAIL`, `INTERNAL_REPORT_SECRET`.
  Resend's default `onboarding@resend.dev` sender only delivers to the Resend account owner.

## Scheduling (manual, needs your approval — nothing is activated)

Use one daily job at [cron-job.org](https://cron-job.org) instead of an hourly GitHub Actions ping:

- URL: `https://aisaac-dashboard.fly.dev/internal/daily-digest/send` (method POST)
- Header: `X-Internal-Secret: <INTERNAL_REPORT_SECRET>` — note this stores the secret with a third party;
  consider a dedicated value if you rotate it separately.
- Schedule: every day 08:00, timezone **America/Chicago** (cron-job.org handles DST).
- Timeout 30 s (a cold Fly start plus feed refresh). Enable failure notifications.
- First run `?dry_run=true`, then one manual send, then enable the schedule after a few days of review.
