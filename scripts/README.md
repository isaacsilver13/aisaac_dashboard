# Push scripts

These run outside the dashboard and push figures to `POST /internal/metrics/{source}`.
The dashboard holds no Claude, Neon or Fly credentials.

## One-time setup

1. On the dashboard's Fly app, set `INTERNAL_REPORT_SECRET` (write) and `DASHBOARD_READ_TOKEN`
   (read, the token you type into the Command Center once).
2. Create `~/.claude/aisaac_push.json` (or export the same env vars):

   ```json
   { "AISAAC_DASHBOARD_URL": "https://aisaac-dashboard.fly.dev", "AISAAC_INTERNAL_SECRET": "<INTERNAL_REPORT_SECRET>" }
   ```

## Claude session / weekly usage — `claude_statusline_push.py`

Registered as the Claude Code `statusLine` command in `~/.claude/settings.json`. Claude Code pipes
`rate_limits` (`five_hour` / `seven_day`: `used_percentage`, `resets_at`) to it; it prints
`5h 12% | 7d 55%` and pushes at most every 5 minutes. Only updates while a Claude Code session is
open, and only on Pro/Max plans.

## Neon compute hours per project — `push_neon_usage.py`

Neon's API reports usage, not dollars. Needs `NEON_API_KEY` (and `NEON_ORG_ID` for org projects).
Tries the v2 consumption endpoint, then the legacy one. Schedule daily:
`python scripts/push_neon_usage.py` (`--dry-run` to preview).

## Fly.io monthly cost — `push_fly_costs.py`

Fly has no billing API, so per-app figures are **estimates** from the `fly` CLI (machine run time,
volumes, dedicated IPs). Give it the real month-to-date total from the dashboard's invoice preview:

```
python scripts/push_fly_costs.py --invoice-total 10.30
```

The total is remembered for the month, so a scheduled `python scripts/push_fly_costs.py` keeps the
estimates fresh. Any gap between the estimates and the invoice shows as `(unattributed)`.
Autostopped machines have little event history, so compute is undercounted; expect most of the
invoice to land in `(unattributed)` until you refine the estimate.
