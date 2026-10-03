import asyncio
import hmac
import json
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from . import (
    automations,
    ci_events,
    fly_client,
    health_history,
    incidents,
    metrics_store,
    notify,
    reports,
    second_brain_store,
)
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
health_history.configure(settings.health_db_path, settings.health_retention_days)
_last_notified_at: dict[str, float] = {}
monitor = Monitor(cache_ttl_seconds=settings.cache_ttl_seconds, settings=settings)
github_monitor = GitHubMonitor(
    token=settings.github_token, cache_ttl_seconds=settings.github_cache_ttl_seconds
)
async def _poll_health(interval: float) -> None:
    while True:
        try:
            await monitor.dashboard(get_registry(settings.profile), force_refresh=True)
        except Exception:
            logging.getLogger("aisaac.monitoring").exception("Health poll failed")
        await asyncio.sleep(interval)


@asynccontextmanager
async def lifespan(_: FastAPI):
    poller = None
    if settings.health_poll_interval_seconds > 0:
        poller = asyncio.create_task(_poll_health(settings.health_poll_interval_seconds))
    yield
    if poller:
        poller.cancel()


app = FastAPI(title="AIsaac Dashboard", version="0.1.0", lifespan=lifespan)


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


@app.get("/api/v1/apps/{app_id}/health-history")
def app_health_history(
    app_id: str, range: health_history.Range = Query(default="24h")
) -> dict:
    if app_id not in {a.id for a in get_registry(settings.profile)}:
        raise HTTPException(404, "Unknown application.")
    return health_history.history(app_id, range)


@app.get("/api/v1/apps/{app_id}/metrics-history")
def app_metrics_history(
    app_id: str, range: health_history.Range = Query(default="24h")
) -> dict:
    if app_id not in {a.id for a in get_registry(settings.profile)}:
        raise HTTPException(404, "Unknown application.")
    return health_history.metrics_history(app_id, range)


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


async def _fly_lookup(app_id: str, call) -> dict:
    """Shared by the Fly-backed tabs: resolve the app, then run `call(client, token, fly_app)`."""
    definition = next((a for a in get_registry(settings.profile) if a.id == app_id), None)
    if definition is None:
        raise HTTPException(404, "Unknown application.")
    if not definition.fly_app:
        return {"app_id": app_id, "fly_app": None, "items": []}
    if not settings.fly_api_token:
        raise HTTPException(503, "Fly access is not configured on this deployment.")
    try:
        async with httpx.AsyncClient() as client:
            items = await call(client, settings.fly_api_token, definition.fly_app)
    except (httpx.HTTPError, ValueError):
        logging.getLogger("aisaac.fly").exception("Fly lookup failed for %s", app_id)
        raise HTTPException(502, "Could not read from Fly.")
    return {"app_id": app_id, "fly_app": definition.fly_app, "items": items}


@app.get("/api/v1/apps/{app_id}/deployments", dependencies=[Depends(_require_read_token)])
async def app_deployments(app_id: str) -> dict:
    out = await _fly_lookup(app_id, fly_client.releases)
    return {"app_id": out["app_id"], "fly_app": out["fly_app"], "releases": out["items"]}


@app.get("/api/v1/apps/{app_id}/logs", dependencies=[Depends(_require_read_token)])
async def app_logs(app_id: str) -> dict:
    out = await _fly_lookup(app_id, fly_client.logs)
    return {"app_id": out["app_id"], "fly_app": out["fly_app"], "lines": out["items"]}


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


# (setting, label, what it enables). Values are never returned, only whether each is set.
_CONFIG_CHECKS = (
    ("dashboard_read_token", "Dashboard read token", "Knowledge, financials, deployments, logs"),
    ("internal_report_secret", "Internal report secret", "Push jobs and heartbeats"),
    ("fly_api_token", "Fly API token", "Deployments and logs tabs"),
    ("github_token", "GitHub token", "Repo, PR and CI data (rate limits without it)"),
    ("resend_api_key", "Resend API key", "Email alerts"),
    ("alert_to_email", "Alert recipient", "Email alerts"),
    ("ntfy_topic", "ntfy topic", "CI push notifications"),
)


@app.get("/api/v1/config-status", dependencies=[Depends(_require_read_token)])
def config_status() -> dict:
    items = [
        {
            "key": key, "label": label, "used_for": used_for,
            "configured": bool(getattr(settings, key)),
        }
        for key, label, used_for in _CONFIG_CHECKS
    ]
    items.append({
        "key": "health_poll_interval_seconds", "label": "Health poller",
        "used_for": "Records health history without anyone viewing the dashboard",
        "configured": settings.health_poll_interval_seconds > 0,
    })
    return {"profile": settings.profile, "items": items}


@app.get("/api/v1/automations", dependencies=[Depends(_require_read_token)])
def automations_status() -> list[dict]:
    return automations.snapshot(settings.health_poll_interval_seconds)


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
