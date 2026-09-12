# Runbook: Gym Tracker

## `/health/ready` failing
- Confirm the Neon Postgres project hasn't been suspended (Neon Free scales compute to zero after
  inactivity and has a monthly compute allowance) — check the Neon dashboard.
- This app uses the sync `psycopg` driver for both the app and Alembic, so there's no driver
  mismatch to debug here (unlike betting_aggregator) — a connection failure is either a bad
  `DATABASE_URL` secret or Neon-side.

## Login broken for a specific user
- If any account was ever created outside the normal `/auth/register` endpoint (e.g. a manual
  provisioning script), verify its `password_hash` is a real bcrypt hash. `verify_password()` is
  guarded against malformed hashes and fails closed rather than crashing, but the account still
  won't be able to log in — this exact bug already happened once in vinyl_app's provisioning
  tooling.
