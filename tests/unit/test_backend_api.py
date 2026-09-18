import pytest
from starlette.testclient import TestClient

from backend.api.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_healthcheck(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "HEALTHY"
    assert data["registered_amrs"] >= 3


def test_warehouse_topology(client):
    response = client.get("/api/v1/warehouse/topology")
    assert response.status_code == 200
    data = response.json()
    assert len(data["nodes"]) == 16
    assert len(data["edges"]) == 24


def test_fleet_status(client):
    response = client.get("/api/v1/fleet")
    assert response.status_code == 200
    data = response.json()
    assert "fleet" in data
    assert len(data["fleet"]) == 3
    robot_ids = [r["robot_id"] for r in data["fleet"]]
    assert "synq-amr-01" in robot_ids


def test_order_creation_and_routing(client):
    order_data = {
        "order_id": "API-ORD-101",
        "pick_node": "N_1_1",
        "drop_node": "N_2_2",
        "required_payload": "SCISSOR_LIFT",
        "priority": 1
    }
    response = client.post("/api/v1/orders", json=order_data)
    assert response.status_code == 200
    data = response.json()
    assert data["order_id"] == "API-ORD-101"
    assert data["assigned_amr"] == "synq-amr-01"
    assert data["status"] == "DISPATCHED"
    assert len(data["route"]) > 0
    assert "decision_trace" in data
    assert "cbs_trace" in data
    assert data["decision_trace"]["selected_robot"] == "synq-amr-01"


def test_order_preview_endpoint(client):
    preview_data = {
        "order_id": "PREVIEW-ORD-01",
        "pick_node": "N_0_1",
        "drop_node": "N_2_2",
        "required_payload": "SCISSOR_LIFT",
        "priority": 1
    }
    response = client.post("/api/v1/orders/preview", json=preview_data)
    assert response.status_code == 200
    data = response.json()
    assert data["order_id"] == "PREVIEW-ORD-01"
    assert "candidates" in data
    assert "decision_rationale" in data
    assert "constraints" in data


def test_simulate_cbs_conflict_endpoint(client):
    response = client.post("/api/v1/cbs/simulate-conflict")
    assert response.status_code == 200
    data = response.json()
    assert "scenario" in data
    assert "routes" in data
    assert "cbs_trace" in data
    assert data["cbs_trace"]["resolved"] is True


def test_inject_obstacle_endpoint(client):
    obs_data = {
        "x": 5.0,
        "y": 5.0,
        "radius": 1.0
    }
    response = client.post("/api/v1/navigation/inject-obstacle", json=obs_data)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "OBSTACLE_DETECTED"
    assert "recovery_pipeline" in data
    assert len(data["recovery_pipeline"]) == 5


def test_payload_action_endpoint(client):
    payload_cmd = {
        "action_name": "LIFT_UP",
        "parameter": 75.0
    }
    response = client.post("/api/v1/robots/synq-amr-01/payload", json=payload_cmd)
    assert response.status_code == 200
    data = response.json()
    assert data["action"] == "LIFT_UP"
    assert data["status"] == "EXECUTED"


def test_estop_endpoint(client):
    response = client.post("/api/v1/robots/ALL/estop")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ESTOP_TRIGGERED"
    assert "synq-amr-01" in data["affected_robots"]

def test_frontend_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "synQ" in response.text
    assert "Digital Twin" in response.text


def test_daily_report_api(client):
    res = client.get("/api/v1/reports/daily")
    assert res.status_code == 200
    data = res.json()
    assert "report" in data
    assert "SYSTEM HEALTH" in data["report"]
    assert "FLEET PERFORMANCE" in data["report"]


def test_whatsapp_api(client):
    res = client.get("/api/v1/notifications/whatsapp?severity=DAILY_SUMMARY")
    assert res.status_code == 200
    data = res.json()
    assert data["channel"] == "WHATSAPP"
    assert "*synQ — Daily Operations*" in data["formatted_message"]


def test_analytics_and_health_api(client):
    res_a = client.get("/api/v1/analytics")
    assert res_a.status_code == 200
    assert "fleet_health" in res_a.json()

    res_h = client.get("/api/v1/health")
    assert res_h.status_code == 200
    assert "fleet_health" in res_h.json()
    assert len(res_h.json()["fleet_health"]) == 12


def test_agent_query_and_what_if_api(client):
    res_q = client.post("/api/v1/agent/query", json={"query": "Why was productivity lower yesterday?"})
    assert res_q.status_code == 200
    data_q = res_q.json()
    assert data_q["query_type"] == "HISTORICAL_ROOT_CAUSE"
    assert len(data_q["contributing_factors"]) == 3

    res_w = client.post("/api/v1/agent/what-if", json={"robot_id": "AMR-07", "duration_hours": 2.0})
    assert res_w.status_code == 200
    data_w = res_w.json()
    assert data_w["target_robot"] == "AMR-07"
    assert data_w["simulated_throughput"] < 147


def test_demo_portal_and_scenarios_api(client):
    res_demo = client.get("/demo")
    assert res_demo.status_code == 200
    assert "FLTX Live Facility Demo Portal" in res_demo.text

    res_scenarios = client.get("/api/v1/demo/scenarios")
    assert res_scenarios.status_code == 200
    assert len(res_scenarios.json()["scenarios"]) == 6

    res_run = client.post("/api/v1/demo/run-scenario/BLOCK_AISLE_C04")
    assert res_run.status_code == 200
    assert res_run.json()["status"] == "EXECUTED"

    res_qr = client.get("/api/v1/demo/qr")
    assert res_qr.status_code == 200
    assert "image/svg+xml" in res_qr.headers["content-type"]


def test_gateway_and_observation_api(client):
    res_gw = client.get("/api/v1/gateway/status")
    assert res_gw.status_code == 200
    assert res_gw.json()["gateway_state"] == "CONNECTED"
    assert res_gw.json()["connected_robots"] >= 3

    res_obs = client.get("/api/v1/observation/anomalies")
    assert res_obs.status_code == 200
    assert "anomalies" in res_obs.json()


def test_tasks_api(client):
    res_tasks = client.get("/api/v1/tasks")
    assert res_tasks.status_code == 200
    assert "tasks" in res_tasks.json()


def test_autonomous_recovery_endpoints(client):
    # Aisle block recovery
    res_aisle = client.post("/api/v1/recovery/aisle-block", json={"blocked_node_id": "N_1_1"})
    assert res_aisle.status_code == 200
    assert res_aisle.json()["status"] == "RESOLVED_AUTONOMOUSLY"

    # Robot fault recovery
    res_fault = client.post("/api/v1/recovery/robot-fault", json={"failed_robot_id": "synq-amr-01"})
    assert res_fault.status_code == 200
    assert "recovery_status" in res_fault.json()

    # Low battery recovery
    res_batt = client.post("/api/v1/recovery/low-battery", json={"robot_id": "synq-amr-02", "dock_node": "N_0_0"})
    assert res_batt.status_code == 200
    assert res_batt.json()["incident_type"] == "BATTERY_CRITICAL_RECOVERY"


