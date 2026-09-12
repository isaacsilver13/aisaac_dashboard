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


@lru_cache
def get_settings() -> Settings:
    return Settings()
