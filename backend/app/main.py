import hmac
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from . import ci_events, incidents, metrics_store, notify, reports, second_brain_store
from .agents_registry import get_agents
from .config import get_settings
from .github_monitor import GitHubMonitor
from .github_registry import get_repos
from .monitoring import Monitor
from .registry import get_registry
from .schemas import (
    AgentSummary,
    CIEventOut,
    CIReportIn,
    ClaudeUsageIn,
    ClaudeUsageOut,
    DashboardResponse,
    FinancialSnapshot,
    IncidentOut,
    NeonUsageIn,
    NeonUsageOut,
    ProviderCostIn,
    ProviderCostOut,
    PushReportIn,
    RepoActivity,
    ResolveIncidentIn,
    SecondBrainSyncIn,
)

settings = get_settings()
incidents.configure(settings.incidents_db_path)
ci_events.configure(settings.ci_events_db_path)
metrics_store.configure(settings.metrics_db_path)
second_brain_store.configure(settings.second_brain_db_path)
_last_notified_at: dict[str, float] = {}
monitor = Monitor(cache_ttl_seconds=settings.cache_ttl_seconds, settings=settings)
github_monitor = GitHubMonitor(
    token=settings.github_token, cache_ttl_seconds=settings.github_cache_ttl_seconds
)
app = FastAPI(title="AIsaac Dashboard", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "aisaac-dashboard"}


@app.get("/api/v1/dashboard", response_model=DashboardResponse)
async def dashboard(force_refresh: bool = Query(default=False)) -> DashboardResponse:
    apps = get_registry(settings.profile)
    results = await monitor.dashboard(apps, force_refresh=force_refresh)
    return DashboardResponse(
        profile=settings.profile,
        refreshed_at=datetime.now(timezone.utc),
        results=results,
    )


def _require_internal_secret(x_internal_secret: Optional[str] = Header(default=None)) -> None:
    if not settings.internal_report_secret:
        raise HTTPException(503, "Push reporting is not configured on this deployment.")
    if x_internal_secret != settings.internal_report_secret:
        raise HTTPException(401, "Invalid or missing internal report secret.")


@app.post("/internal/report", status_code=204, dependencies=[Depends(_require_internal_secret)])
def internal_report(payload: PushReportIn) -> None:
    reports.record_report(payload.app_id, payload.status, payload.metrics)


def _require_read_token(x_dashboard_token: Optional[str] = Header(default=None)) -> None:
    if not settings.dashboard_read_token:
        raise HTTPException(503, "Financial figures are not configured on this deployment.")
    if not hmac.compare_digest(x_dashboard_token or "", settings.dashboard_read_token):
        raise HTTPException(401, "Invalid or missing dashboard token.")


_METRIC_MODELS = {"claude": ClaudeUsageIn, "neon": NeonUsageIn, "fly": ProviderCostIn}


@app.post(
    "/internal/metrics/{source}",
    status_code=204,
    dependencies=[Depends(_require_internal_secret)],
)
def internal_metrics(source: str, payload: dict) -> None:
    model = _METRIC_MODELS.get(source)
    if model is None:
        raise HTTPException(404, f"Unknown metrics source '{source}'.")
    try:
        parsed = model.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(422, exc.errors(include_url=False, include_context=False)) from exc
    metrics_store.save(source, parsed.model_dump_json())


@app.get(
    "/api/v1/command-center/financials",
    response_model=FinancialSnapshot,
    dependencies=[Depends(_require_read_token)],
)
def financials() -> FinancialSnapshot:
    def _load(source: str, out_model):
        row = metrics_store.load(source)
        if row is None:
            return None
        return out_model.model_validate(
            {**json.loads(row["payload"]), "reported_at": row["reported_at"]}
        )

    claude = _load("claude", ClaudeUsageOut)
    neon = _load("neon", NeonUsageOut)
    fly = _load("fly", ProviderCostOut)
    missing = [n for n, v in (("claude", claude), ("neon", neon), ("fly", fly)) if v is None]
    return FinancialSnapshot(
        claude=claude,
        neon=neon,
        fly=fly,
        detail=f"No data reported yet for: {', '.join(missing)}." if missing else None,
    )


@app.get("/api/v1/incidents", response_model=list[IncidentOut])
def list_incidents(app_id: Optional[str] = Query(default=None)) -> list[IncidentOut]:
    return [IncidentOut.model_validate(dict(row)) for row in incidents.list_incidents(app_id)]


@app.post("/api/v1/incidents/{incident_id}/resolve", status_code=204)
def resolve_incident(incident_id: int, payload: ResolveIncidentIn) -> None:
    incidents.resolve_incident(incident_id, notes=payload.notes)


@app.get("/api/v1/agents", response_model=list[AgentSummary])
def list_agents() -> list[AgentSummary]:
    return [AgentSummary(**agent.model_dump()) for agent in get_agents()]


@app.get("/api/v1/analytics", response_model=list[RepoActivity])
async def analytics(force_refresh: bool = Query(default=False)) -> list[RepoActivity]:
    repos = get_repos()
    return await github_monitor.activity(repos, force_refresh=force_refresh)


@app.post("/internal/ci-report", status_code=204, dependencies=[Depends(_require_internal_secret)])
def internal_ci_report(payload: CIReportIn) -> None:
    now = time.monotonic()
    last = _last_notified_at.get(payload.app_id)
    should_notify = last is None or (now - last) >= settings.coms_debounce_minutes * 60

    ci_events.record_event(
        app_id=payload.app_id,
        repo=payload.repo,
        event_type=payload.event_type,
        ci_status=payload.ci_status,
        details=payload.details,
        notified=should_notify,
    )

    if should_notify:
        message = payload.details or f"[{payload.repo}] {payload.event_type}: {payload.ci_status}"
        notify.send_coms_notification(settings, message)
        _last_notified_at[payload.app_id] = now


@app.get("/api/v1/coms", response_model=list[CIEventOut])
def list_coms_events(app_id: Optional[str] = Query(default=None)) -> list[CIEventOut]:
    return [
        CIEventOut(**{**dict(row), "notified": bool(row["notified"])})
        for row in ci_events.list_events(app_id)
    ]


@app.get("/api/v1/runbooks/{app_id}", response_class=PlainTextResponse)
def get_runbook(app_id: str) -> str:
    runbook_path = Path(settings.runbooks_dir).resolve() / f"{app_id}.md"
    if not runbook_path.is_file():
        raise HTTPException(404, "No runbook has been written for this app yet.")
    return runbook_path.read_text(encoding="utf-8")


@app.post(
    "/internal/second-brain/sync",
    status_code=204,
    dependencies=[Depends(_require_internal_secret)],
)
def second_brain_sync(payload: SecondBrainSyncIn) -> None:
    second_brain_store.replace_all(payload.meta, [n.model_dump() for n in payload.notes])


@app.get("/api/v1/second-brain/summary", dependencies=[Depends(_require_read_token)])
def second_brain_summary() -> dict:
    return second_brain_store.summary() or {"counts": {}, "pushed_at": None}


@app.get("/api/v1/second-brain/notes", dependencies=[Depends(_require_read_token)])
def second_brain_notes(q: str = "", folder: str = "") -> list[dict]:
    return second_brain_store.list_notes(q, folder)


@app.get("/api/v1/second-brain/notes/{path:path}", dependencies=[Depends(_require_read_token)])
def second_brain_note(path: str) -> dict:
    note = second_brain_store.get_note(path)
    if note is None:
        raise HTTPException(404, "No such note.")
    return note


frontend_dist = Path(settings.frontend_dist).resolve()
if frontend_dist.is_dir():
    assets = frontend_dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def frontend(path: str) -> FileResponse:
        requested = frontend_dist / path
        if path and requested.is_file() and frontend_dist in requested.parents:
            return FileResponse(requested)
        return FileResponse(frontend_dist / "index.html")
