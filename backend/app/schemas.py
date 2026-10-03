from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

HealthState = Literal["up", "slow", "degraded", "down", "unavailable", "stale"]
CheckKind = Literal["json", "page"]
MonitorTarget = Literal["health", "page", "push"]


class AppDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(pattern=r"^[a-z0-9-]+$")
    name: str
    category: str
    description: str
    product_url: Optional[HttpUrl] = None
    health_url: Optional[HttpUrl] = None
    readiness_url: Optional[HttpUrl] = None
    metrics_url: Optional[HttpUrl] = None
    check_kind: CheckKind = "json"
    monitor_target: MonitorTarget = "health"
    metric_allowlist: tuple[str, ...] = ()
    timeout_seconds: float = Field(default=10.0, gt=0, le=30)
    enabled: bool = True
    # Fly app that hosts this service; enables the Deployments tab (needs FLY_API_TOKEN).
    fly_app: Optional[str] = Field(default=None, pattern=r"^[a-z0-9-]+$")


class CheckResult(BaseModel):
    app_id: str
    name: str
    category: str
    description: str
    product_url: Optional[HttpUrl] = None
    state: HealthState
    checked_at: datetime
    response_ms: Optional[float] = None
    http_status: Optional[int] = None
    readiness: Optional[HealthState] = None
    provider_state: Optional[str] = None
    freshness: Optional[datetime] = None
    page_state: Optional[HealthState] = None
    metrics_state: Optional[HealthState] = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    detail: Optional[str] = None
    cached: bool = False


class DashboardResponse(BaseModel):
    profile: str
    refreshed_at: datetime
    results: list[CheckResult]


class PushReportIn(BaseModel):
    app_id: str = Field(pattern=r"^[a-z0-9-]+$")
    status: str = "ok"
    metrics: dict[str, Any] = Field(default_factory=dict)


class IncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    app_id: str
    failure_type: str
    started_at: str
    resolved_at: Optional[str] = None
    notes: Optional[str] = None


class ResolveIncidentIn(BaseModel):
    notes: Optional[str] = None


CiStatus = Literal["success", "failure", "in_progress", "unknown"]


class RepoDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(pattern=r"^[a-z0-9-]+$")
    name: str
    category: str
    owner: str
    repo: str
    stale_days: int = Field(default=14, gt=0)
    enabled: bool = True


class PullRequestSummary(BaseModel):
    number: int
    title: str
    url: str
    opened_at: datetime
    stale: bool = False


class RepoActivity(BaseModel):
    repo_id: str
    name: str
    category: str
    owner: str
    repo: str
    ci_status: CiStatus = "unknown"
    open_issue_count: Optional[int] = None
    open_pr_count: Optional[int] = None
    open_pull_requests: list[PullRequestSummary] = Field(default_factory=list)
    commits_last_7d: Optional[int] = None
    last_commit_at: Optional[datetime] = None
    checked_at: datetime
    cached: bool = False
    detail: Optional[str] = None


class AgentDefinition(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str = Field(pattern=r"^[a-z0-9-]+$")
    name: str
    domain: str
    description: str
    scope: tuple[str, ...] = ()


class AgentSummary(BaseModel):
    id: str
    name: str
    domain: str
    description: str
    scope: tuple[str, ...] = ()
    last_run_at: Optional[datetime] = None
    last_run_note: Optional[str] = None


class CIReportIn(BaseModel):
    app_id: str = Field(pattern=r"^[a-z0-9-]+$")
    repo: str
    event_type: str
    ci_status: CiStatus = "unknown"
    details: str = ""


class CIEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    app_id: str
    repo: str
    event_type: str
    ci_status: CiStatus
    details: str
    received_at: str
    notified: bool


class UsageWindow(BaseModel):
    used_pct: float = Field(ge=0, le=100)
    resets_at: datetime


class ClaudeUsageIn(BaseModel):
    session: UsageWindow
    weekly: UsageWindow


class ProviderCostIn(BaseModel):
    period: str = Field(description="Billing month, e.g. 2026-09")
    total_usd: float = Field(ge=0)
    by_app: dict[str, float] = Field(default_factory=dict)
    estimated: bool = Field(
        default=True,
        description="True when per-app figures are estimates rather than invoice lines.",
    )


class NeonUsageIn(BaseModel):
    period: str = Field(description="Billing period label, e.g. 2026-09")
    total_compute_hours: float = Field(ge=0)
    by_app: dict[str, float] = Field(default_factory=dict, description="Compute hours per project")


class ClaudeUsageOut(ClaudeUsageIn):
    reported_at: datetime


class ProviderCostOut(ProviderCostIn):
    reported_at: datetime


class NeonUsageOut(NeonUsageIn):
    reported_at: datetime


class FinancialSnapshot(BaseModel):
    claude: Optional[ClaudeUsageOut] = None
    neon: Optional[NeonUsageOut] = None
    fly: Optional[ProviderCostOut] = None
    detail: Optional[str] = None


class NoteIn(BaseModel):
    path: str = Field(pattern=r"^(wikis|knowledge|projects|questions)/.+\.md$")
    folder: str
    title: str
    aliases: list[str] = []
    status: Optional[str] = None
    body: str


class SecondBrainSyncIn(BaseModel):
    """Whole-vault sync. `meta` holds card figures (last commit, drafts, broken links)."""

    meta: dict[str, Any] = {}
    notes: list[NoteIn]


DigestCategory = Literal["building", "technique", "systems", "research", "news"]
_CITATION = re.compile(r"\[(\d+)\]")


class DigestItemIn(BaseModel):
    """One cited item.

    `url`, `title` and `source` come from the fetched feed, never from the LLM.
    """

    id: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=300)
    url: HttpUrl
    source: str = Field(min_length=1, max_length=100)
    published_at: Optional[datetime] = None
    category: DigestCategory
    priority: int = Field(ge=1, le=5)
    summary: str = Field(min_length=1, max_length=1200)
    why_it_matters: str = Field(default="", max_length=600)


class DigestIn(BaseModel):
    """A finished daily digest. `headline` cites items as [id], which must exist in `items`."""

    digest_date: date
    generated_at: datetime
    model: str = Field(min_length=1, max_length=100)
    headline: str = Field(default="", max_length=1500)
    items: list[DigestItemIn] = Field(max_length=100)
    source_stats: dict[str, Any] = {}

    @model_validator(mode="after")
    def _citations_resolve(self) -> "DigestIn":
        ids = [item.id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("Item ids must be unique.")
        unknown = {int(n) for n in _CITATION.findall(self.headline)} - set(ids)
        if unknown:
            raise ValueError(f"Headline cites unknown item ids: {sorted(unknown)}.")
        return self
