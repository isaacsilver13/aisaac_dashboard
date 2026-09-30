"""Push Neon compute hours per project (current calendar month) to the dashboard.

Neon's API reports usage, not dollars, so this pushes compute hours only. Needs
a Neon API key with read access: NEON_API_KEY (and NEON_ORG_ID for org projects).

Tries the v2 consumption endpoint first (Launch plans and above), then falls
back to the legacy endpoint (Free / legacy plans). Compute hours are
compute-unit seconds / 3600 (v2) or `compute_time_seconds` / 3600 (legacy).

    python scripts/push_neon_usage.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import push_common  # noqa: E402

API = "https://console.neon.tech/api/v2"


def _get(path: str, params: dict[str, Any], key: str) -> dict[str, Any]:
    query = urllib.parse.urlencode(params, doseq=True)
    request = urllib.request.Request(
        f"{API}{path}?{query}",
        headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def _item_seconds(item: dict[str, Any]) -> float:
    """Compute seconds from one consumption row, tolerating v2 and legacy shapes."""
    for field in ("compute_unit_seconds", "compute_time_seconds"):
        if isinstance(item.get(field), (int, float)):
            return float(item[field])
    for metric in item.get("metrics") or []:
        if metric.get("metric_name") == "compute_unit_seconds":
            return float(metric.get("value") or 0)
    return 0.0


def project_seconds(response: dict[str, Any]) -> dict[str, float]:
    """{project_id: total compute seconds} summed over all periods and timeframes."""
    totals: dict[str, float] = {}
    for project in response.get("projects", []):
        seconds = sum(
            _item_seconds(item)
            for period in project.get("periods", [])
            for item in period.get("consumption", [])
        )
        totals[project["project_id"]] = totals.get(project["project_id"], 0.0) + seconds
    return totals


def build_payload(
    seconds_by_project: dict[str, float], names: dict[str, str], period: str
) -> dict[str, Any]:
    by_app = {
        names.get(pid, pid): round(seconds / 3600, 3) for pid, seconds in seconds_by_project.items()
    }
    return {
        "period": period,
        "total_compute_hours": round(sum(by_app.values()), 3),
        "by_app": dict(sorted(by_app.items())),
    }


def fetch_project_names(key: str, org_id: Optional[str]) -> dict[str, str]:
    params: dict[str, Any] = {"limit": 400}
    if org_id:
        params["org_id"] = org_id
    return {p["id"]: p["name"] for p in _get("/projects", params, key).get("projects", [])}


def fetch_seconds(
    key: str, org_id: Optional[str], start: datetime, end: datetime
) -> dict[str, float]:
    base: dict[str, Any] = {
        "from": start.isoformat().replace("+00:00", "Z"),
        "to": end.isoformat().replace("+00:00", "Z"),
        "granularity": "daily",
        "limit": 100,
    }
    if org_id:
        base["org_id"] = org_id
    try:
        v2_params = {**base, "metrics": "compute_unit_seconds"}
        return project_seconds(_get("/consumption_history/v2/projects", v2_params, key))
    except urllib.error.HTTPError as exc:
        if exc.code not in (400, 403, 404):
            raise
    return project_seconds(_get("/consumption_history/projects", base, key))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="print the payload, don't push")
    args = parser.parse_args()

    key = os.environ.get("NEON_API_KEY")
    if not key:
        print("NEON_API_KEY is not set.", file=sys.stderr)
        return 2
    org_id = os.environ.get("NEON_ORG_ID")
    now = datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    seconds = fetch_seconds(key, org_id, start, now)
    payload = build_payload(seconds, fetch_project_names(key, org_id), now.strftime("%Y-%m"))
    print(json.dumps(payload, indent=2))
    if args.dry_run:
        return 0
    if not push_common.post_metrics("neon", payload, push_common.load_config()):
        print("Push failed (check AISAAC_DASHBOARD_URL / AISAAC_INTERNAL_SECRET).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
