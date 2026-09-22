"""Formats a RepoActivity snapshot into a human-readable Coms status line.

Pure function, no I/O -- fully unit-testable without mocking httpx or sqlite.
"""

from __future__ import annotations

from .schemas import RepoActivity

_ICONS = {
    "success": "✅",
    "failure": "❌",
    "in_progress": "⚠️",
    "unknown": "⚠️",
}


def format_status_report(repo_activity: RepoActivity) -> str:
    icon = _ICONS.get(repo_activity.ci_status, "⚠️")
    message = f"{icon} {repo_activity.name}: CI {repo_activity.ci_status}"

    stale_count = sum(1 for pr in repo_activity.open_pull_requests if pr.stale)
    if stale_count:
        message += f" — {stale_count} stale PR{'s' if stale_count != 1 else ''}"

    if repo_activity.open_pr_count is not None and repo_activity.open_issue_count is not None:
        message += (
            f" · {repo_activity.open_pr_count} open PR(s), "
            f"{repo_activity.open_issue_count} open issue(s)"
        )

    if repo_activity.detail:
        message += f" ({repo_activity.detail})"

    return message
