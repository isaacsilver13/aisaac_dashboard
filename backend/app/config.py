from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    profile: Literal["local", "production"] = "local"
    cache_ttl_seconds: float = 20.0
    request_timeout_seconds: float = 5.0
    frontend_dist: str = "../frontend/dist"

    # SRE rollout: incident history, runbooks, alerting, and push heartbeats
    # from apps that can't be polled (see docs/sre-observability-design.md
    # at the workspace root).
    incidents_db_path: str = "./aisaac_incidents.db"
    runbooks_dir: str = "../runbooks"
    resend_api_key: str = ""
    alert_from_email: str = "AIsaac <onboarding@resend.dev>"
    alert_to_email: str = ""
    internal_report_secret: str = ""
    stale_report_after_hours: float = 26.0

    github_token: str = ""
    github_cache_ttl_seconds: float = 300.0

    # Coms rollout: push CI/PR/issue status from a GitHub Actions workflow,
    # recorded as history and (debounced) forwarded to ntfy.sh.
    ntfy_topic: str = ""
    coms_debounce_minutes: float = 10.0
    ci_events_db_path: str = "./aisaac_ci_events.db"

    # Financial figures (Claude usage, Neon/Fly costs) are pushed by external
    # jobs via /internal/metrics/{source}; reads need a separate token so a
    # browser-held token can never write.
    metrics_db_path: str = "./aisaac_metrics.db"
    dashboard_read_token: str = ""

    # Health check history (uptime/latency/trends). Recorded on every fresh check;
    # the optional poller (seconds, 0 = off) records without anyone viewing the
    # dashboard, but only while the Fly machine is awake.
    health_db_path: str = "./aisaac_health.db"
    health_retention_days: float = 30.0
    health_poll_interval_seconds: float = 0.0

    # Second-brain vault notes pushed by scripts/second_brain_push.py (read-token gated).
    second_brain_db_path: str = "./aisaac_second_brain.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
