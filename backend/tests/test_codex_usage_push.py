import importlib.util
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "push_codex_usage.py"
sys.path.insert(0, str(SCRIPT.parent))
spec = importlib.util.spec_from_file_location("push_codex_usage", SCRIPT)
push_script = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(push_script)


def test_build_payload_normalizes_codex_rate_limits():
    payload = push_script.build_payload({
        "rateLimits": {
            "primary": {"usedPercent": 42.5, "resetsAt": 1791663010},
            "secondary": {"usedPercent": 12, "resetsAt": 1792000000},
            "planType": "plus",
        }
    })

    assert payload is not None
    assert payload["primary"]["used_pct"] == 42.5
    assert payload["secondary"]["used_pct"] == 12.0
    assert payload["plan_type"] == "plus"


def test_build_payload_rejects_missing_primary_window():
    assert push_script.build_payload({"rateLimits": {"primary": None}}) is None
