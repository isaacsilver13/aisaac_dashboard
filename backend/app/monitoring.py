from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

import httpx

from .schemas import AppDefinition, CheckResult, HealthState


class Monitor:
    def __init__(self, cache_ttl_seconds: float = 20.0) -> None:
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: tuple[float, list[CheckResult]] | None = None

    async def dashboard(
        self, apps: tuple[AppDefinition, ...], force_refresh: bool = False
    ) -> list[CheckResult]:
        now = time.monotonic()
        if not force_refresh and self._cache and now - self._cache[0] < self.cache_ttl_seconds:
            return [result.model_copy(update={"cached": True}) for result in self._cache[1]]

        async with httpx.AsyncClient(follow_redirects=True) as client:
            results = list(await asyncio.gather(*(self.check_app(client, app) for app in apps)))
        self._cache = (time.monotonic(), results)
        return results

    async def check_app(self, client: httpx.AsyncClient, app: AppDefinition) -> CheckResult:
        checked_at = datetime.now(timezone.utc)
        if not app.enabled:
            return self._unavailable(app, checked_at, "Not configured for this environment.")
        if app.monitor_target == "page":
            return await self._check_page(client, app, checked_at)
        if app.health_url is None:
            return self._unavailable(app, checked_at, "No health endpoint is configured.")

        started = time.perf_counter()
        try:
            response = await client.get(str(app.health_url), timeout=app.timeout_seconds)
        except httpx.TimeoutException:
            return self._failure(app, checked_at, started, "Health check timed out.")
        except httpx.HTTPError:
            return self._failure(app, checked_at, started, "Health check could not connect.")

        response_ms = round((time.perf_counter() - started) * 1000, 1)
        if response.status_code < 200 or response.status_code >= 300:
            return self._failure(
                app,
                checked_at,
                started,
                f"Endpoint returned HTTP {response.status_code}.",
                response.status_code,
            )

        payload: dict[str, Any] = {}
        if app.check_kind == "json":
            try:
                parsed = response.json()
            except ValueError:
                return self._failure(
                    app,
                    checked_at,
                    started,
                    "Endpoint returned invalid JSON.",
                    response.status_code,
                )
            if isinstance(parsed, dict):
                payload = parsed

        normalized_payload = self._unwrap_payload(payload)
        state = self._state_from_payload(normalized_payload)
        detail = self._detail_from_payload(normalized_payload)
        readiness = await self._check_readiness(client, app)
        if state == "up" and readiness == "down":
            state = "degraded"
        provider_state = self._string_value(
            normalized_payload.get("provider_status") or normalized_payload.get("provider_state")
        )
        metrics = self._metrics_from_payload(normalized_payload, app.metric_allowlist)
        metrics_state, metrics, metrics_provider_state = await self._check_metrics(
            client, app, metrics
        )
        if provider_state is None:
            provider_state = metrics_provider_state
        if state == "up" and metrics_state == "down":
            state = "degraded"
        page_state = await self._check_page_state(client, app)
        if state == "up" and page_state == "down":
            state = "degraded"
        return CheckResult(
            app_id=app.id,
            name=app.name,
            category=app.category,
            description=app.description,
            product_url=app.product_url,
            state=state,
            checked_at=checked_at,
            response_ms=response_ms,
            http_status=response.status_code,
            readiness=readiness,
            provider_state=provider_state,
            page_state=page_state,
            metrics_state=metrics_state,
            metrics=metrics,
            detail=detail,
        )

    async def _check_page(
        self, client: httpx.AsyncClient, app: AppDefinition, checked_at: datetime
    ) -> CheckResult:
        if app.product_url is None:
            return self._unavailable(app, checked_at, "No page endpoint is configured.")
        started = time.perf_counter()
        try:
            response = await client.get(str(app.product_url), timeout=app.timeout_seconds)
        except httpx.TimeoutException:
            return self._failure(app, checked_at, started, "Page check timed out.")
        except httpx.HTTPError:
            return self._failure(app, checked_at, started, "Page check could not connect.")
        if response.status_code < 200 or response.status_code >= 300:
            return self._failure(
                app,
                checked_at,
                started,
                f"Page returned HTTP {response.status_code}.",
                response.status_code,
            )
        return CheckResult(
            app_id=app.id,
            name=app.name,
            category=app.category,
            description=app.description,
            product_url=app.product_url,
            state="up",
            page_state="up",
            checked_at=checked_at,
            response_ms=round((time.perf_counter() - started) * 1000, 1),
            http_status=response.status_code,
        )

    async def _check_page_state(
        self, client: httpx.AsyncClient, app: AppDefinition
    ) -> HealthState | None:
        if app.product_url is None:
            return None
        try:
            response = await client.get(str(app.product_url), timeout=app.timeout_seconds)
        except httpx.HTTPError:
            return "down"
        return "up" if 200 <= response.status_code < 300 else "down"

    @staticmethod
    def _state_from_payload(payload: dict[str, Any]) -> HealthState:
        status = str(payload.get("status", "ok")).lower()
        if status in {"ok", "healthy", "up", "ready"}:
            return "up"
        if status in {"degraded", "warning", "unconfigured"}:
            return "degraded"
        return "down"

    @staticmethod
    def _unwrap_payload(payload: dict[str, Any]) -> dict[str, Any]:
        nested = payload.get("data")
        return nested if isinstance(nested, dict) else payload

    @staticmethod
    def _detail_from_payload(payload: dict[str, Any]) -> str | None:
        for key in ("message", "detail", "error"):
            value = payload.get(key)
            if isinstance(value, str) and value:
                return value[:240]
        return None

    @staticmethod
    def _metrics_from_payload(
        payload: dict[str, Any], allowlist: tuple[str, ...]
    ) -> dict[str, Any]:
        reserved = {"status", "message", "detail", "error", "provider_status", "provider_state"}
        return {
            key: value
            for key, value in payload.items()
            if key not in reserved
            and (not allowlist or key in allowlist)
            and isinstance(value, (str, int, float, bool))
        }

    async def _check_metrics(
        self,
        client: httpx.AsyncClient,
        app: AppDefinition,
        metrics: dict[str, Any],
    ) -> tuple[HealthState | None, dict[str, Any], str | None]:
        if app.metrics_url is None:
            return None, metrics, None
        try:
            response = await client.get(str(app.metrics_url), timeout=app.timeout_seconds)
            if response.status_code < 200 or response.status_code >= 300:
                return "down", metrics, None
            payload = response.json()
        except (httpx.HTTPError, ValueError):
            return "down", metrics, None
        if not isinstance(payload, dict):
            return "down", metrics, None
        normalized = self._unwrap_payload(payload)
        provider_state = self._string_value(
            normalized.get("provider_status") or normalized.get("provider_state")
        )
        return (
            "up",
            {**metrics, **self._metrics_from_payload(normalized, app.metric_allowlist)},
            provider_state,
        )

    async def _check_readiness(
        self, client: httpx.AsyncClient, app: AppDefinition
    ) -> HealthState | None:
        if app.readiness_url is None:
            return None
        try:
            response = await client.get(str(app.readiness_url), timeout=app.timeout_seconds)
        except httpx.HTTPError:
            return "down"
        if response.status_code < 200 or response.status_code >= 300:
            return "down"
        try:
            payload = response.json()
        except ValueError:
            return "down"
        return self._state_from_payload(payload if isinstance(payload, dict) else {})

    @staticmethod
    def _string_value(value: Any) -> str | None:
        return value if isinstance(value, str) else None

    @staticmethod
    def _unavailable(app: AppDefinition, checked_at: datetime, detail: str) -> CheckResult:
        return CheckResult(
            app_id=app.id,
            name=app.name,
            category=app.category,
            description=app.description,
            product_url=app.product_url,
            state="unavailable",
            checked_at=checked_at,
            detail=detail,
        )

    @staticmethod
    def _failure(
        app: AppDefinition,
        checked_at: datetime,
        started: float,
        detail: str,
        http_status: int | None = None,
    ) -> CheckResult:
        return CheckResult(
            app_id=app.id,
            name=app.name,
            category=app.category,
            description=app.description,
            product_url=app.product_url,
            state="down",
            checked_at=checked_at,
            response_ms=round((time.perf_counter() - started) * 1000, 1),
            http_status=http_status,
            detail=detail,
        )
