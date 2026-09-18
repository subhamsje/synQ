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

