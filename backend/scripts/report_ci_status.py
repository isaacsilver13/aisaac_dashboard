"""Polls the repos in github_registry and pushes a Coms status report.

Run from `backend/` (so `app` is importable) with the backend package
installed, e.g. from the `aisaac-report.yml` GitHub Actions workflow:

    cd backend && pip install -e . && python scripts/report_ci_status.py

Reads GITHUB_TOKEN (repo-read PAT), INTERNAL_REPORT_SECRET, and
AISAAC_DASHBOARD_URL from the environment; posts one CIReportIn-shaped
payload per repo to {AISAAC_DASHBOARD_URL}/internal/ci-report.
"""

from __future__ import annotations

import asyncio
import os
import sys

import httpx

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.github_monitor import GitHubMonitor  # noqa: E402
from app.github_registry import get_repos  # noqa: E402
from app.report_template import format_status_report  # noqa: E402


async def main() -> None:
    github_token = os.environ["GITHUB_TOKEN"]
    internal_report_secret = os.environ["INTERNAL_REPORT_SECRET"]
    dashboard_url = os.environ["AISAAC_DASHBOARD_URL"].rstrip("/")

    monitor = GitHubMonitor(token=github_token)
    activity = await monitor.activity(get_repos())

    async with httpx.AsyncClient(timeout=10.0) as client:
        for repo_activity in activity:
            payload = {
                "app_id": repo_activity.repo_id,
                "repo": f"{repo_activity.owner}/{repo_activity.repo}",
                "event_type": "status_report",
                "ci_status": repo_activity.ci_status,
                "details": format_status_report(repo_activity),
            }
            response = await client.post(
                f"{dashboard_url}/internal/ci-report",
                json=payload,
                headers={"X-Internal-Secret": internal_report_secret},
            )
            response.raise_for_status()
            print(f"Reported {payload['app_id']}: {payload['details']}")


if __name__ == "__main__":
    asyncio.run(main())
