from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import get_settings
from .monitoring import Monitor
from .registry import get_registry
from .schemas import DashboardResponse

settings = get_settings()
monitor = Monitor(cache_ttl_seconds=settings.cache_ttl_seconds)
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
