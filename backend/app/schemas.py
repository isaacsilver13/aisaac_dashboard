from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

HealthState = Literal["up", "degraded", "down", "unavailable"]
CheckKind = Literal["json", "page"]
MonitorTarget = Literal["health", "page"]


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
    timeout_seconds: float = Field(default=5.0, gt=0, le=30)
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
