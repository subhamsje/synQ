import pytest
import time
from fms.observation.observation_loop import ObservationLoop
from fms.adapters.simulation_adapter import SimulationRobotAdapter
from fms.models.domain_models import RobotStatus, PayloadType


def test_observation_loop_anomaly_detection():
    loop = ObservationLoop()
    sim = SimulationRobotAdapter(robot_id="obs-bot-01", initial_node="N_0_0", battery_pct=95.0)
    loop.register_adapter("obs-bot-01", sim)

    # Initial cycle nominal
    anomalies = loop.evaluate_cycle()
    assert len(anomalies) == 0

    # Simulate AMCL localization drift
    sim.robot.sensors.amcl_covariance = 0.08
    anomalies = loop.evaluate_cycle()
    drift_anom = [a for a in anomalies if a["type"] == "LOCALIZATION_DRIFT"]
    assert len(drift_anom) == 1
    assert drift_anom[0]["severity"] == "WARNING"

    # Simulate sudden battery drop
    sim.robot.battery_pct = 70.0  # 25% drop from baseline 95.0
    anomalies = loop.evaluate_cycle()
    batt_anom = [a for a in anomalies if a["type"] == "RAPID_BATTERY_DROP"]
    assert len(batt_anom) == 1
