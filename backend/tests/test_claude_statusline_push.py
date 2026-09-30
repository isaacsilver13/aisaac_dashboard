import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "claude_statusline_push.py"
spec = importlib.util.spec_from_file_location("claude_statusline_push", SCRIPT)
push_script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(push_script)

SAMPLE = {
    "rate_limits": {
        "five_hour": {"used_percentage": 23.5, "resets_at": 1738425600},
        "seven_day": {"used_percentage": 41.2, "resets_at": 1738857600},
    }
}


def test_build_payload_converts_epoch_to_iso():
    payload = push_script.build_payload(SAMPLE)
    assert payload["session"]["used_pct"] == 23.5
    assert payload["session"]["resets_at"] == "2025-02-01T16:00:00+00:00"
    assert payload["weekly"]["used_pct"] == 41.2


def test_build_payload_none_when_rate_limits_missing_or_partial():
    assert push_script.build_payload({}) is None
    partial = {"rate_limits": {"five_hour": SAMPLE["rate_limits"]["five_hour"]}}
    assert push_script.build_payload(partial) is None


def test_payload_matches_backend_schema():
    from app.schemas import ClaudeUsageIn

    ClaudeUsageIn.model_validate(push_script.build_payload(SAMPLE))


def test_format_line():
    assert push_script.format_line(push_script.build_payload(SAMPLE)) == "5h 24% | 7d 41%"
    assert push_script.format_line(None) == ""


def test_push_needs_config():
    assert push_script.push({"session": {}, "weekly": {}}, {}) is False
