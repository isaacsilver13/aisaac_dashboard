"""Ping every URL in the AIsaac registry and report PASS / SLOW / FAIL.

Run from backend/ after changing an app's URL:

    python -m scripts.check_urls                     # PROFILE env var, default production
    python -m scripts.check_urls --profile local
    python -m scripts.check_urls --ipv4              # if IPv6 to fly.dev is flaky locally

Exit code is 1 if any URL fails, so it can gate CI or a deploy.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import dataclass

import httpx

from app.monitoring import RETRYABLE_STATUSES
from app.registry import get_registry
from app.schemas import AppDefinition

SLOW_AFTER_SECONDS = 3.0
URL_FIELDS = ("product_url", "health_url", "readiness_url", "metrics_url")


@dataclass(frozen=True)
class ProbeResult:
    status: str  # PASS | SLOW | FAIL
    http_status: int | None
    seconds: float
    detail: str = ""


def collect_targets(apps: tuple[AppDefinition, ...]) -> list[tuple[str, str, str]]:
    """Return (app_id, field, url) for every URL of every enabled, non-push app."""
    targets = []
    for app in apps:
        if not app.enabled or app.monitor_target == "push":
            continue
        for field in URL_FIELDS:
            url = getattr(app, field)
            if url is not None:
                targets.append((app.id, field, str(url)))
    return targets


def probe(
    client: httpx.Client, url: str, timeout: float = 10.0, retry_delay: float = 2.0
) -> ProbeResult:
    """GET a URL, retrying once so a Fly cold start reads SLOW instead of FAIL."""
    started = time.perf_counter()
    error = ""
    for attempt in range(2):
        if attempt:
            time.sleep(retry_delay)
        try:
            response = client.get(url, timeout=timeout)
        except httpx.TimeoutException:
            error = "Timed out."
            continue
        except httpx.HTTPError:
            error = "Could not connect."
            continue
        elapsed = time.perf_counter() - started
        if attempt == 0 and response.status_code in RETRYABLE_STATUSES:
            error = f"HTTP {response.status_code}."
            continue
        if not 200 <= response.status_code < 300:
            detail = f"HTTP {response.status_code}."
            return ProbeResult("FAIL", response.status_code, elapsed, detail)
        slow = attempt > 0 or elapsed >= SLOW_AFTER_SECONDS
        detail = "Needed a retry (waking up)." if attempt > 0 else ""
        return ProbeResult("SLOW" if slow else "PASS", response.status_code, elapsed, detail)
    return ProbeResult("FAIL", None, time.perf_counter() - started, error)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--profile", default=os.environ.get("PROFILE", "production"))
    parser.add_argument("--ipv4", action="store_true", help="force IPv4 connections")
    args = parser.parse_args(argv)

    targets = collect_targets(get_registry(args.profile))
    transport = httpx.HTTPTransport(local_address="0.0.0.0") if args.ipv4 else None
    failures = 0
    print(f"Checking {len(targets)} URLs (profile: {args.profile})")
    with httpx.Client(follow_redirects=True, transport=transport) as client:
        for app_id, field, url in targets:
            result = probe(client, url)
            failures += result.status == "FAIL"
            code = result.http_status if result.http_status is not None else "---"
            print(
                f"{result.status:5} {app_id:20} {field:14} {code!s:>3} "
                f"{result.seconds:5.1f}s  {url}  {result.detail}".rstrip()
            )
    print(f"\n{len(targets) - failures}/{len(targets)} reachable, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
