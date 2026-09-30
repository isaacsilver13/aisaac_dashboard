import importlib.util
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fly = _load("push_fly_costs")
neon = _load("push_neon_usage")

DAY_MS = 86_400_000
START = 1_788_220_800_000  # period start (ms)
NOW = START + 10 * DAY_MS


def _machine(state, events, cpus=1, memory_mb=256, cpu_kind="shared"):
    return {
        "state": state,
        "events": [{"type": t, "timestamp": ts} for t, ts in events],
        "config": {"guest": {"cpu_kind": cpu_kind, "cpus": cpus, "memory_mb": memory_mb}},
    }


def test_machine_price_matches_published_presets():
    assert round(fly.machine_monthly_price({"cpus": 1, "memory_mb": 256}), 2) == 1.95
    assert round(fly.machine_monthly_price({"cpus": 1, "memory_mb": 512}), 2) == 2.60
    assert round(fly.machine_monthly_price({"cpus": 2, "memory_mb": 1024}), 2) == 5.20
    assert fly.machine_monthly_price({"cpu_kind": "performance", "cpus": 1}) is None


def test_uptime_from_start_stop_pairs_and_clipped_to_period():
    machine = _machine(
        "stopped",
        [("start", START - DAY_MS), ("stop", START + DAY_MS), ("start", START + 5 * DAY_MS),
         ("exit", START + 6 * DAY_MS)],
    )
    # 1 day of the first run inside the period + 1 day for the second.
    assert fly.uptime_seconds(machine, START, NOW) == 2 * 86400


def test_started_machine_counts_to_now_and_ignores_orphan_stop():
    recent = _machine("started", [("start", START + 8 * DAY_MS)])
    assert fly.uptime_seconds(recent, START, NOW) == 2 * 86400
    assert fly.uptime_seconds(_machine("started", []), START, NOW) == 10 * 86400
    assert fly.uptime_seconds(_machine("stopped", [("stop", START + DAY_MS)]), START, NOW) == 0


def test_app_estimate_includes_volumes_and_dedicated_ip_only():
    machines = [_machine("stopped", [])]
    volumes = [{"size_gb": 2}]
    ips = [{"Type": "v4"}, {"Type": "shared_v4"}, {"Type": "v6"}]
    elapsed = 10 * 86400 / fly.MONTH_SECONDS
    expected = 2 * 0.15 * elapsed + 2.0 * elapsed
    assert abs(fly.app_estimate(machines, volumes, ips, START, NOW) - expected) < 1e-9


def test_build_payload_adds_unattributed_remainder():
    payload = fly.build_payload({"a": 1.0, "b": 2.0}, "2026-09", 10.30)
    assert payload["total_usd"] == 10.30
    assert payload["by_app"]["(unattributed)"] == 7.30
    assert payload["estimated"] is True


def test_build_payload_scales_down_when_estimates_exceed_invoice():
    payload = fly.build_payload({"a": 6.0, "b": 6.0}, "2026-09", 6.0)
    assert payload["by_app"] == {"a": 3.0, "b": 3.0}
    assert payload["total_usd"] == 6.0


def test_build_payload_without_invoice_sums_estimates():
    payload = fly.build_payload({"a": 1.234, "b": 2.0}, "2026-09", None)
    assert payload["total_usd"] == 3.23
    assert "(unattributed)" not in payload["by_app"]


def test_payloads_validate_against_backend_schemas():
    from app.schemas import NeonUsageIn, ProviderCostIn

    ProviderCostIn.model_validate(fly.build_payload({"a": 1.0}, "2026-09", 5.0))
    NeonUsageIn.model_validate(neon.build_payload({"p1": 3600.0}, {"p1": "gym-tracker"}, "2026-09"))


def test_neon_sums_legacy_and_v2_shapes_and_maps_names():
    response = {
        "projects": [
            {"project_id": "p1", "periods": [{"consumption": [
                {"compute_time_seconds": 3600}, {"compute_time_seconds": 1800}]}]},
            {"project_id": "p2", "periods": [{"consumption": [
                {"metrics": [{"metric_name": "compute_unit_seconds", "value": 7200}]}]}]},
            {"project_id": "p3", "periods": [{"consumption": [{"compute_unit_seconds": 360}]}]},
        ]
    }
    seconds = neon.project_seconds(response)
    assert seconds == {"p1": 5400.0, "p2": 7200.0, "p3": 360.0}
    payload = neon.build_payload(seconds, {"p1": "gym-tracker", "p2": "vinyl"}, "2026-09")
    assert payload["by_app"] == {"gym-tracker": 1.5, "p3": 0.1, "vinyl": 2.0}
    assert payload["total_compute_hours"] == 3.6


def test_post_metrics_needs_config():
    import push_common

    assert push_common.post_metrics("neon", {}, {}) is False
