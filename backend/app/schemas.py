from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

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
