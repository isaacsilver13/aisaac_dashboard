from app import incidents


def test_open_and_resolve_incident(tmp_path) -> None:
    incidents.configure(str(tmp_path / "incidents.db"))

    assert incidents.get_open_incident("vinyl") is None

    incident_id = incidents.open_incident("vinyl", failure_type="down")
    open_incident = incidents.get_open_incident("vinyl")

    assert open_incident is not None
    assert open_incident["id"] == incident_id
    assert open_incident["resolved_at"] is None

    incidents.resolve_incident(incident_id, notes="Fixed the volume.")

    assert incidents.get_open_incident("vinyl") is None
    history = incidents.list_incidents("vinyl")
    assert history[0]["resolved_at"] is not None
    assert history[0]["notes"] == "Fixed the volume."


def test_list_incidents_across_apps(tmp_path) -> None:
    incidents.configure(str(tmp_path / "incidents.db"))
    incidents.open_incident("vinyl", failure_type="down")
    incidents.open_incident("gym-tracker", failure_type="degraded")

    all_incidents = incidents.list_incidents()

    assert {row["app_id"] for row in all_incidents} == {"vinyl", "gym-tracker"}
    assert incidents.list_incidents("vinyl") and len(incidents.list_incidents("vinyl")) == 1
