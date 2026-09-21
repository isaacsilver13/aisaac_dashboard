from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone

import httpx

from . import github_client
from .schemas import CiStatus, PullRequestSummary, RepoActivity, RepoDefinition


def _ci_status(status: str | None, conclusion: str | None) -> CiStatus:
    if status is not None and status != "completed":
        return "in_progress"
    if conclusion == "success":
        return "success"
    if conclusion is not None:
        return "failure"
    return "unknown"


class GitHubMonitor:
    def __init__(
        self, token: str, cache_ttl_seconds: float = 300.0, timeout_seconds: float = 10.0
    ) -> None:
        self.token = token
        self.cache_ttl_seconds = cache_ttl_seconds
        self.timeout_seconds = timeout_seconds
        self._cache: tuple[float, list[RepoActivity]] | None = None

    async def activity(
        self, repos: tuple[RepoDefinition, ...], force_refresh: bool = False
    ) -> list[RepoActivity]:
        now = time.monotonic()
        if not force_refresh and self._cache and now - self._cache[0] < self.cache_ttl_seconds:
            return [activity.model_copy(update={"cached": True}) for activity in self._cache[1]]

        enabled_repos = [repo for repo in repos if repo.enabled]
        async with httpx.AsyncClient(follow_redirects=True) as client:
            results = list(
                await asyncio.gather(*(self._check_repo(client, repo) for repo in enabled_repos))
            )
        self._cache = (time.monotonic(), results)
        return results

    async def _check_repo(self, client: httpx.AsyncClient, repo: RepoDefinition) -> RepoActivity:
        checked_at = datetime.now(timezone.utc)
        owner, name, timeout = repo.owner, repo.repo, self.timeout_seconds
        run_status, issue_count, pull_requests, commit_activity = await asyncio.gather(
            github_client.get_latest_run_status(client, self.token, owner, name, timeout),
            github_client.get_open_issue_count(client, self.token, owner, name, timeout),
            github_client.get_open_pull_requests(
                client, self.token, owner, name, timeout, repo.stale_days
            ),
            github_client.get_commit_activity(client, self.token, owner, name, timeout),
        )

        ci_status: CiStatus = "unknown"
        if run_status is not None:
            ci_status = _ci_status(*run_status)

        commits_last_7d = commit_activity[0] if commit_activity is not None else None
        last_commit_at = commit_activity[1] if commit_activity is not None else None

        detail = None
        if not self.token:
            detail = "No GitHub token configured; live GitHub data is unavailable."

        return RepoActivity(
            repo_id=repo.id,
            name=repo.name,
            category=repo.category,
            owner=repo.owner,
            repo=repo.repo,
            ci_status=ci_status,
            open_issue_count=issue_count,
            open_pr_count=None if pull_requests is None else len(pull_requests),
            open_pull_requests=[PullRequestSummary(**pr) for pr in (pull_requests or [])],
            commits_last_7d=commits_last_7d,
            last_commit_at=last_commit_at,
            checked_at=checked_at,
            detail=detail,
        )
