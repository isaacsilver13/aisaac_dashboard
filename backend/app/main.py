from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

from . import incidents, reports
from .config import get_settings
from .monitoring import Monitor
from .registry import get_registry
from .schemas import DashboardResponse, IncidentOut, PushReportIn, ResolveIncidentIn

settings = get_settings()
incidents.configure(settings.incidents_db_path)
monitor = Monitor(cache_ttl_seconds=settings.cache_ttl_seconds, settings=settings)
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


@app.get("/api/v1/incidents", response_model=list[IncidentOut])
def list_incidents(app_id: Optional[str] = Query(default=None)) -> list[IncidentOut]:
    return [IncidentOut.model_validate(dict(row)) for row in incidents.list_incidents(app_id)]


@app.post("/api/v1/incidents/{incident_id}/resolve", status_code=204)
def resolve_incident(incident_id: int, payload: ResolveIncidentIn) -> None:
    incidents.resolve_incident(incident_id, notes=payload.notes)


@app.get("/api/v1/runbooks/{app_id}", response_class=PlainTextResponse)
def get_runbook(app_id: str) -> str:
    runbook_path = Path(settings.runbooks_dir).resolve() / f"{app_id}.md"
    if not runbook_path.is_file():
        raise HTTPException(404, "No runbook has been written for this app yet.")
    return runbook_path.read_text(encoding="utf-8")


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
