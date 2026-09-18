import pytest
from backend.persistence.db import db
from backend.persistence.seed_data import seed_operational_memory
from backend.analytics.analytics_engine import FleetAnalyticsEngine
from backend.health.health_engine import PredictiveHealthEngine


@pytest.fixture(scope="module", autouse=True)
def ensure_db_seeded():
    seed_operational_memory(db)


def test_fleet_analytics_metrics():
    engine = FleetAnalyticsEngine(db)
    metrics = engine.get_summary_metrics(window_hours=24.0)

    assert metrics["facility_name"] == "Austin Hub — Warehouse 01"
    assert metrics["fleet_health"]["total_robots"] == 12
    assert metrics["fleet_health"]["system_uptime_pct"] == 99.4
    assert metrics["fleet_health"]["safety_events"] == 0

    assert metrics["performance"]["missions_completed"] >= 147
    assert metrics["performance"]["total_distance_km"] >= 80.0

    assert metrics["autonomy_events"]["cbs_conflicts_resolved"] >= 6
    assert len(metrics["attention_required"]) >= 2
    assert len(metrics["robot_performance"]) == 12


def test_predictive_health_scoring():
    engine = PredictiveHealthEngine(db)
    health_list = engine.evaluate_fleet_health()

    assert len(health_list) == 12

    # Verify AMR-07 battery alert
    amr07_eval = next(h for h in health_list if h["robot_id"] == "AMR-07")
    assert amr07_eval["subsystems"]["battery_health"] == 72.0
    assert amr07_eval["overall_status"] == "ATTENTION_REQUIRED"
    assert any("Battery inspection recommended" in r["action"] for r in amr07_eval["recommendations"])

    # Verify AMR-03 localization alert
    amr03_eval = next(h for h in health_list if h["robot_id"] == "AMR-03")
    assert amr03_eval["subsystems"]["localization_health"] == 81.0
    assert any("Verify landmark reflectivity" in r["action"] for r in amr03_eval["recommendations"])
