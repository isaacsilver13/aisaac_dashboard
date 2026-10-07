# CI observability

The AIsaac GitHub status report is a read-only daily observation of the repositories in `backend/app/github_registry.py`. It runs at 15:15 UTC through `.github/workflows/aisaac-report.yml` and posts the existing CI/PR/issue snapshot to the dashboard.

## Thresholds and ownership

| Signal | Threshold | Notification | Owner and response |
| --- | --- | --- | --- |
| Latest CI run | `failure` | Send a debounced notification to the subscriber of `NTFY_TOPIC` | The dashboard operator checks the linked repository's latest GitHub Actions run and its logs. |
| Latest CI run | `success`, `in_progress`, or `unknown` | Record in AIsaac only | No notification. `unknown` can mean no workflow or an unavailable GitHub response, so it is not treated as a failed build. |
| CI-report freshness | No report received for more than 26 hours | Mark `CI event reports` stale on `/automations` | The dashboard operator checks the scheduled workflow, then its `REPORT_GITHUB_TOKEN` and `INTERNAL_REPORT_SECRET` configuration if the workflow did not post. |

This workflow does not repair CI failures, create issues, or change another repository. GitHub Actions remains the source of truth for a scheduled workflow that fails before it can post an AIsaac event.
