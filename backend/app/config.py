from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    profile: Literal["local", "production"] = "local"
    cache_ttl_seconds: float = 20.0
    request_timeout_seconds: float = 5.0
    frontend_dist: str = "../frontend/dist"


@lru_cache
def get_settings() -> Settings:
    return Settings()
