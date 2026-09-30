"""Claude Code statusline command that forwards subscription usage to the dashboard.

Claude Code pipes session JSON to a statusline command on stdin; when the
account is a Pro/Max subscription it includes `rate_limits.five_hour` and
`rate_limits.seven_day` (`used_percentage`, `resets_at` as epoch seconds).
See https://code.claude.com/docs/en/statusline.

This script prints a short status line and, at most once per PUSH_INTERVAL_S,
POSTs the figures to `/internal/metrics/claude`. It never raises: a failed
push must not break the statusline. Configuration (env vars, or the JSON file
~/.claude/aisaac_push.json with the same keys):

    AISAAC_DASHBOARD_URL       e.g. https://aisaac-dashboard.fly.dev
    AISAAC_INTERNAL_SECRET     the dashboard's INTERNAL_REPORT_SECRET
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

PUSH_INTERVAL_S = 300
STATE_FILE = Path.home() / ".claude" / "aisaac_push_state"
CONFIG_FILE = Path.home() / ".claude" / "aisaac_push.json"


def _window(raw: Any) -> Optional[dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    pct, resets = raw.get("used_percentage"), raw.get("resets_at")
    if not isinstance(pct, (int, float)) or not isinstance(resets, (int, float)):
        return None
    return {
        "used_pct": max(0.0, min(100.0, float(pct))),
        "resets_at": datetime.fromtimestamp(resets, tz=timezone.utc).isoformat(),
    }


def build_payload(data: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Map Claude Code statusline JSON to the dashboard's ClaudeUsageIn shape."""
    limits = data.get("rate_limits")
    if not isinstance(limits, dict):
        return None
    session, weekly = _window(limits.get("five_hour")), _window(limits.get("seven_day"))
    if session is None or weekly is None:
        return None
    return {"session": session, "weekly": weekly}


def format_line(payload: Optional[dict[str, Any]]) -> str:
    if payload is None:
        return ""
    return f"5h {payload['session']['used_pct']:.0f}% | 7d {payload['weekly']['used_pct']:.0f}%"


def _config() -> dict[str, str]:
    config: dict[str, str] = {}
    try:
        config.update(json.loads(CONFIG_FILE.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        pass
    for key in ("AISAAC_DASHBOARD_URL", "AISAAC_INTERNAL_SECRET"):
        if os.environ.get(key):
            config[key] = os.environ[key]
    return config


def _due(now: float) -> bool:
    try:
        return now - float(STATE_FILE.read_text()) >= PUSH_INTERVAL_S
    except (OSError, ValueError):
        return True


def push(payload: dict[str, Any], config: dict[str, str]) -> bool:
    url, secret = config.get("AISAAC_DASHBOARD_URL"), config.get("AISAAC_INTERNAL_SECRET")
    if not url or not secret:
        return False
    request = urllib.request.Request(
        f"{url.rstrip('/')}/internal/metrics/claude",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "X-Internal-Secret": secret},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=3):
            return True
    except Exception:
        return False


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    payload = build_payload(data if isinstance(data, dict) else {})
    print(format_line(payload))
    now = time.time()
    if payload is not None and _due(now) and push(payload, _config()):
        try:
            STATE_FILE.write_text(str(now))
        except OSError:
            pass


if __name__ == "__main__":
    main()
