# Runbook: Vinyl

## `/health/ready` failing (database unreachable)
1. Check the Fly volume is attached and has free space: `fly volumes list -a vinyl-api`.
2. `fly logs -a vinyl-api` — look for `sqlite3.OperationalError` (disk full or locked file).
3. Restart the machine: `fly machine restart <id> -a vinyl-api`. Since this is a single always-on
   machine by design (SQLite single-writer), there's no second instance to fail over to.

## `/health` up but writes failing
- Check `VINYL_API_KEY` is still set: `fly secrets list -a vinyl-api`. If it was ever cleared, the
  app fails open with no auth (known risk) rather than crashing — check for unexpected write volume
  as a sign of this before assuming it's just a client bug.

## Known issue
`POST /listings/bulk` upserts on `listing_id` (fixed 2026-09) — if you see rapidly growing DB size
again, check whether a new insert path was added that bypasses the upsert query in `main.py`.
