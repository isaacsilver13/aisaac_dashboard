"""Push the signed-in Codex account's included-usage windows to AIsaac.

The script asks the local Codex app-server for ``account/rateLimits/read``;
it never reads Codex credentials or sends an account identifier to AIsaac.
Run it periodically (for example, every two hours) on the computer where
Codex is signed in. Configuration is shared with the other push scripts:
``AISAAC_DASHBOARD_URL`` and ``AISAAC_INTERNAL_SECRET``.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import threading
from datetime import datetime, timezone
from typing import Any, Optional

from push_common import load_config, post_metrics


def _window(raw: Any) -> Optional[dict[str, Any]]:
    if not isinstance(raw, dict):
        return None
    used, resets = raw.get("usedPercent"), raw.get("resetsAt")
    if not isinstance(used, (int, float)) or not isinstance(resets, (int, float)):
        return None
    return {
        "used_pct": max(0.0, min(100.0, float(used))),
        "resets_at": datetime.fromtimestamp(resets, tz=timezone.utc).isoformat(),
    }


def build_payload(response: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Convert the public app-server rate-limit response to AIsaac's schema."""
    limits = response.get("rateLimits")
    if not isinstance(limits, dict):
        return None
    primary = _window(limits.get("primary"))
    if primary is None:
        return None
    payload: dict[str, Any] = {"primary": primary}
    secondary = _window(limits.get("secondary"))
    if secondary is not None:
        payload["secondary"] = secondary
    plan_type = limits.get("planType")
    if isinstance(plan_type, str):
        payload["plan_type"] = plan_type
    return payload


def _read_response(process: subprocess.Popen[str], request_id: int) -> dict[str, Any]:
    while True:
        line = process.stdout.readline() if process.stdout else ""
        if not line:
            raise RuntimeError("Codex app-server closed before replying.")
        message = json.loads(line)
        if message.get("id") != request_id:
            continue
        if "error" in message:
            raise RuntimeError("Codex app-server rejected the usage request.")
        result = message.get("result")
        if not isinstance(result, dict):
            raise RuntimeError("Codex app-server returned an invalid usage response.")
        return result


def read_rate_limits() -> dict[str, Any]:
    """Read account limits through Codex's local app-server protocol."""
    # which() resolves the npm ``codex.cmd`` shim that Popen cannot find by bare name on Windows.
    codex = shutil.which("codex")
    if codex is None:
        raise RuntimeError("The codex CLI was not found on PATH.")
    process = subprocess.Popen(
        [codex, "app-server"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        bufsize=1,
    )
    # A hung app-server must not block a scheduled run forever; killing it ends the read.
    watchdog = threading.Timer(30, process.kill)
    watchdog.start()
    try:
        if process.stdin is None:
            raise RuntimeError("Could not open Codex app-server input.")

        def send(request_id: int, method: str, params: dict[str, Any]) -> dict[str, Any]:
            request = {"id": request_id, "method": method, "params": params}
            process.stdin.write(json.dumps(request) + "\n")
            process.stdin.flush()
            return _read_response(process, request_id)

        send(1, "initialize", {"clientInfo": {"name": "AIsaac", "version": "1.0"}})
        return send(2, "account/rateLimits/read", {"excludeResetCreditDetails": True})
    finally:
        watchdog.cancel()
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run", action="store_true", help="Print the normalized snapshot without posting it."
    )
    args = parser.parse_args()
    try:
        payload = build_payload(read_rate_limits())
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"Could not read Codex usage: {error}")
        return 1
    if payload is None:
        print("Codex did not return an included-usage window for this account.")
        return 1
    if args.dry_run:
        print(json.dumps(payload, indent=2))
        return 0
    if not post_metrics("codex", payload, load_config()):
        print("Could not push Codex usage to AIsaac.")
        return 1
    print("Pushed Codex usage to AIsaac.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
