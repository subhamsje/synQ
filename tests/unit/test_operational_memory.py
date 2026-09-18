import pytest
import os
import tempfile
from backend.persistence.db import OperationalDatabase
from backend.persistence.seed_data import seed_operational_memory


@pytest.fixture
def temp_db():
    temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_file.close()
    database = OperationalDatabase(db_path=temp_file.name)
    yield database
    if os.path.exists(temp_file.name):
        os.remove(temp_file.name)


def test_seed_operational_memory(temp_db):
    seed_operational_memory(temp_db)

    robots = temp_db.get_all_robots()
    assert len(robots) == 12

    # Verify heterogeneous payload families
    payloads = set(r["payload_type"] for r in robots)
    assert "SCISSOR_LIFT" in payloads
    assert "ROLLER_CONVEYOR" in payloads
    assert "TOTE_GRIPPER" in payloads

    # Verify AMR-07 has lower battery health
    amr07 = temp_db.get_robot("AMR-07")
    assert amr07 is not None
    assert amr07["battery_health"] == 72.0

    # Verify AMR-03 localization health
    amr03 = temp_db.get_robot("AMR-03")
    assert amr03 is not None
    assert amr03["localization_health"] == 81.0

    # Verify missions count
    missions = temp_db.get_missions(limit=200)
    assert len(missions) >= 147

    # Verify latest snapshot
    snapshot = temp_db.get_latest_daily_snapshot()
    assert snapshot is not None
    assert snapshot["distance_km"] == 82.4
    assert snapshot["uptime_pct"] == 99.4
    assert snapshot["safety_incidents"] == 0


def test_record_mission_and_events(temp_db):
    temp_db.record_event(
        event_id="EVT-TEST-1",
        event_type="test.event",
        severity="INFO",
        source_entity="TEST-RUNNER",
        message="Running automated test",
        timestamp=1000.0,
        metadata={"key": "val"}
    )

    events = temp_db.get_events(limit=5)
    assert len(events) == 1
    assert events[0]["event_id"] == "EVT-TEST-1"
    assert events[0]["source_entity"] == "TEST-RUNNER"
