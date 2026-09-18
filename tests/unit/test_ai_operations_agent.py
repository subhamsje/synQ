import pytest
from backend.persistence.db import db
from backend.persistence.seed_data import seed_operational_memory
from backend.agent.operations_agent import OperationsAgent
from backend.agent.what_if_simulator import WhatIfSimulator


@pytest.fixture(scope="module", autouse=True)
def ensure_db_seeded():
    seed_operational_memory(db)


def test_ask_fltx_productivity_query():
    agent = OperationsAgent(db)
    res = agent.ask("Why was productivity lower yesterday?")

    assert res["query_type"] == "HISTORICAL_ROOT_CAUSE"
    assert "Mission throughput ↓ 14%" in res["headline"]
    assert len(res["contributing_factors"]) == 3
    assert any("Aisle C04" in f["factor"] for f in res["contributing_factors"])
    assert any("AMR-07" in f["factor"] for f in res["contributing_factors"])
    assert len(res["candidate_actions"]) == 3


def test_ask_fltx_reassignment_query():
    agent = OperationsAgent(db)
    res = agent.ask("Why did you reassign AMR-07?")

    assert res["query_type"] == "DECISION_REASONING"
    assert res["sla_preserved"] is True
    assert len(res["decision_steps"]) == 5
    assert any("AMR-02" in s["detail"] for s in res["decision_steps"])


def test_ask_fltx_recent_activity():
    agent = OperationsAgent(db)
    res = agent.ask("What happened in the last hour?")

    assert res["query_type"] == "OPERATIONAL_ACTIVITY"
    assert res["summary"]["missions_completed"] == 31
    assert "8.4 meters" in res["highlight_event"]


def test_what_if_simulation_standalone():
    simulator = WhatIfSimulator()
    sim = simulator.simulate_robot_unavailability("AMR-07", duration_hours=2.0)

    assert sim["target_robot"] == "AMR-07"
    assert sim["baseline_throughput"] == 147
    assert sim["simulated_throughput"] < 147
    assert "AMR-02" in sim["recommended_mitigation"]
