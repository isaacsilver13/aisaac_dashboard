# AIsaac Dashboard — Scheduled CI Observability

Status: complete
Scope: `aisaac_dashboard` GitHub status-report workflow and dashboard automation status

## Goal

Make the existing GitHub repository status report run daily, visible as a stale-able automation, and quiet unless the latest observed CI run has failed.

## Constraints and non-goals

- The workflow remains read-only against GitHub and only posts its existing report payload to AIsaac.
- It must not deploy, mutate other repositories, create issues, or attempt remediation.
- Fly configuration drift is excluded: it needs a separately approved read-only Fly job and a reliable live-versus-committed comparison contract.

## Approach

1. Run `aisaac-report.yml` daily at 15:15 UTC and prevent overlapping reports.
2. Mark CI reports stale after 26 hours in the dashboard automation snapshot.
3. Notify the configured `NTFY_TOPIC` subscriber only when a reported latest CI result is `failure`; retain the existing per-app debounce for repeated reports.
4. Document the cadence, thresholds, notification owner, and manual response path.

## Verification

- Automated: `ruff check` and `compileall` pass for the touched backend files. Focused pytest was attempted with an explicit repository-local base temp directory, but this Windows sandbox terminated it at its 30-second command ceiling without a test result; run the focused tests in normal local/CI execution.
- Manual: inspected the workflow YAML for its UTC schedule, least-privilege permissions, and concurrency guard.

## Risks / decisions needed

- GitHub Actions scheduled runs can be delayed by GitHub. The 26-hour freshness threshold intentionally allows for a daily run plus delay.
- A workflow failure before it posts a report is surfaced by GitHub Actions itself; it cannot create an AIsaac CI event.
