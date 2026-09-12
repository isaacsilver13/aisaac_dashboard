from datetime import datetime, timedelta, timezone

from app import reports


def test_record_and_get_report() -> None:
    reports.record_report("nba-prediction", "ok", {"last_run_score": 0.42})

    report = reports.get_report("nba-prediction", stale_after_hours=26.0)

    assert report is not None
    assert report.status == "ok"
    assert report.metrics == {"last_run_score": 0.42}


def test_missing_report_returns_none() -> None:
    assert reports.get_report("never-reported", stale_after_hours=26.0) is None


def test_stale_report_is_treated_as_missing() -> None:
    reports.record_report("stale-app", "ok", {})
    reports._reports["stale-app"].received_at = datetime.now(timezone.utc) - timedelta(hours=48)

    assert reports.get_report("stale-app", stale_after_hours=26.0) is None
