"""Estimate Fly.io monthly cost per app and push it to the dashboard.

Fly has no billing API: invoices exist only in the dashboard's Billing page. So
per-app figures here are ESTIMATES built from the `fly` CLI:

  * compute: machine size x running time this month, from machine start/stop
    events (Fly keeps only recent events, so older uptime is undercounted;
    a machine still `started` with no start event is assumed up all month)
  * volumes: provisioned GB x $0.15/GB-month, prorated
  * dedicated IPv4: $2/month, prorated (shared IPv4 and IPv6 are free)

Pass the real month-to-date total from the dashboard's invoice preview with
--invoice-total (remembered for the rest of the month). The push then reports
that total; estimates that fall short of it appear as "(unattributed)", and
estimates that exceed it are scaled down to fit.

For a finished month (--month YYYY-MM) event history is gone, so the invoice is split
across apps in proportion to what each would cost always-on (machine sizes, volumes,
dedicated IPs). Fly bills by region and product, not app, so this is only a rough split.

    python scripts/push_fly_costs.py [--invoice-total 10.30] [--month 2026-09] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import push_common  # noqa: E402

# https://docs.fly.io/about/pricing (shared CPU, iad): 1 shared CPU ~ $1.30/mo,
# RAM ~ $2.60/GB/mo (matches the published 256MB/512MB/1GB presets).
CPU_MONTH = 1.30
RAM_GB_MONTH = 2.60
VOLUME_GB_MONTH = 0.15
DEDICATED_IPV4_MONTH = 2.00
MONTH_SECONDS = 30 * 86400
UNATTRIBUTED = "(unattributed)"
STATE_FILE = Path.home() / ".claude" / "aisaac_fly_invoice.json"


def machine_monthly_price(guest: dict[str, Any]) -> Optional[float]:
    """Monthly price of an always-on shared-CPU machine, or None if not priceable."""
    if guest.get("cpu_kind", "shared") != "shared":
        return None
    return guest.get("cpus", 1) * CPU_MONTH + guest.get("memory_mb", 256) / 1024 * RAM_GB_MONTH


def uptime_seconds(machine: dict[str, Any], period_start_ms: int, now_ms: int) -> float:
    """Seconds this machine ran since period_start, from its start/stop events."""
    events = sorted(machine.get("events") or [], key=lambda e: e.get("timestamp", 0))
    running_since: Optional[int] = None
    total_ms = 0
    for event in events:
        ts, kind = event.get("timestamp", 0), event.get("type")
        if kind == "start":
            running_since = ts
        elif kind in ("stop", "exit") and running_since is not None:
            total_ms += max(0, ts - max(running_since, period_start_ms))
            running_since = None
    if machine.get("state") == "started":
        total_ms += max(0, now_ms - max(running_since or period_start_ms, period_start_ms))
    return total_ms / 1000


def app_estimate(
    machines: list[dict[str, Any]],
    volumes: list[dict[str, Any]],
    ips: list[dict[str, Any]],
    period_start_ms: int,
    now_ms: int,
) -> float:
    elapsed = (now_ms - period_start_ms) / 1000 / MONTH_SECONDS
    cost = 0.0
    for machine in machines:
        price = machine_monthly_price(machine.get("config", {}).get("guest", {}))
        if price is not None:
            cost += price * uptime_seconds(machine, period_start_ms, now_ms) / MONTH_SECONDS
    cost += sum(v.get("size_gb", 0) * VOLUME_GB_MONTH * elapsed for v in volumes)
    cost += sum(DEDICATED_IPV4_MONTH * elapsed for ip in ips if ip.get("Type") == "v4")
    return cost


def app_weight(
    machines: list[dict[str, Any]], volumes: list[dict[str, Any]], ips: list[dict[str, Any]]
) -> float:
    """Monthly cost of an app's footprint if it ran all month."""
    weight = sum(
        machine_monthly_price(m.get("config", {}).get("guest", {})) or 0.0 for m in machines
    )
    weight += sum(v.get("size_gb", 0) * VOLUME_GB_MONTH for v in volumes)
    weight += sum(DEDICATED_IPV4_MONTH for ip in ips if ip.get("Type") == "v4")
    return weight


def split_invoice(weights: dict[str, float], period: str, invoice_total: float) -> dict[str, Any]:
    """Allocate a known invoice total across apps in proportion to their weights."""
    weight_sum = sum(weights.values())
    if weight_sum <= 0:
        by_app = {UNATTRIBUTED: invoice_total}
    else:
        by_app = {app: invoice_total * w / weight_sum for app, w in weights.items() if w > 0}
    return {
        "period": period,
        "total_usd": round(invoice_total, 2),
        "by_app": {app: round(cost, 2) for app, cost in sorted(by_app.items())},
        "estimated": True,
    }


def build_payload(
    estimates: dict[str, float], period: str, invoice_total: Optional[float]
) -> dict[str, Any]:
    estimated_sum = sum(estimates.values())
    if invoice_total is None:
        by_app, total = dict(estimates), estimated_sum
    else:
        total = invoice_total
        if estimated_sum > invoice_total and estimated_sum > 0:
            scale = invoice_total / estimated_sum
            by_app = {app: cost * scale for app, cost in estimates.items()}
        else:
            by_app = dict(estimates)
            remainder = invoice_total - estimated_sum
            if remainder >= 0.005:
                by_app[UNATTRIBUTED] = remainder
    return {
        "period": period,
        "total_usd": round(total, 2),
        "by_app": {app: round(cost, 2) for app, cost in sorted(by_app.items())},
        "estimated": True,
    }


def _fly_json(*args: str) -> Any:
    result = subprocess.run(["fly", *args, "--json"], capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"fly {' '.join(args)} failed: {result.stderr.strip()[:200]}")
    return json.loads(result.stdout or "null") or []


def _remembered_invoice(period: str) -> Optional[float]:
    try:
        saved = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return float(saved["total"]) if saved.get("period") == period else None
    except (OSError, ValueError, KeyError):
        return None


def report_past_month(period: str, invoice_total: float, dry_run: bool) -> int:
    weights = {}
    for app in _fly_json("apps", "list"):
        name = app["Name"]
        weights[name] = app_weight(
            _fly_json("machine", "list", "-a", name),
            _fly_json("volumes", "list", "-a", name),
            _fly_json("ips", "list", "-a", name),
        )
    payload = split_invoice(weights, period, invoice_total)
    print(json.dumps(payload, indent=2))
    if dry_run:
        return 0
    if not push_common.post_metrics("fly", payload, push_common.load_config()):
        print("Push failed (check AISAAC_DASHBOARD_URL / AISAAC_INTERNAL_SECRET).", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--invoice-total", type=float, help="month-to-date total from the Fly billing page"
    )
    parser.add_argument(
        "--month", help="YYYY-MM to report (default: current month); past months split by size"
    )
    parser.add_argument("--dry-run", action="store_true", help="print the payload, don't push")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    period = args.month or now.strftime("%Y-%m")
    if period != now.strftime("%Y-%m"):
        if args.invoice_total is None:
            parser.error("--month for a past month needs --invoice-total")
        return report_past_month(period, args.invoice_total, args.dry_run)
    start_ms, now_ms = int(start.timestamp() * 1000), int(now.timestamp() * 1000)

    if args.invoice_total is not None:
        STATE_FILE.write_text(json.dumps({"period": period, "total": args.invoice_total}))
    invoice = args.invoice_total if args.invoice_total is not None else _remembered_invoice(period)

    estimates = {}
    for app in _fly_json("apps", "list"):
        name = app["Name"]
        estimates[name] = app_estimate(
            _fly_json("machine", "list", "-a", name),
            _fly_json("volumes", "list", "-a", name),
            _fly_json("ips", "list", "-a", name),
            start_ms,
            now_ms,
        )

    payload = build_payload(estimates, period, invoice)
    print(json.dumps(payload, indent=2))
    if invoice is None:
        print("Note: no invoice total given; total is the sum of estimates.", file=sys.stderr)
    if args.dry_run:
        return 0
    if not push_common.post_metrics("fly", payload, push_common.load_config()):
        print("Push failed (check AISAAC_DASHBOARD_URL / AISAAC_INTERNAL_SECRET).", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
