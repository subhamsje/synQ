import pytest
from backend.demo.scenario_runner import FacilityScenarioRunner
from backend.demo.qr_generator import QRGenerator
from backend.demo.demo_gatekeeper import DemoGatekeeper


def test_scenario_runner_scenarios_list():
    runner = FacilityScenarioRunner()
    scenarios = runner.get_available_scenarios()
    assert len(scenarios) == 6
    ids = [s["id"] for s in scenarios]
    assert "BLOCK_AISLE_C04" in ids
    assert "DISABLE_ROBOT_AMR07" in ids
    assert "DEGRADE_BATTERY" in ids
    assert "CONGEST_CORRIDOR" in ids
    assert "ADD_URGENT_TASK" in ids
    assert "BURST_10_TASKS" in ids


@pytest.mark.anyio
async def test_run_aisle_block_scenario():
    runner = FacilityScenarioRunner()
    res = await runner.run_scenario("BLOCK_AISLE_C04")
    assert res["status"] == "EXECUTED"
    assert res["sla_status"] == "PRESERVED"
    assert len(res["narrative"]) == 5


@pytest.mark.anyio
async def test_run_disable_robot_scenario():
    runner = FacilityScenarioRunner()
    res = await runner.run_scenario("DISABLE_ROBOT_AMR07")
    assert res["status"] == "EXECUTED"
    assert res["reassigned_tasks"] == 3
    assert res["missions_canceled"] == 0


def test_qr_code_svg_generation():
    svg = QRGenerator.generate_demo_qr_svg("http://localhost:8000/demo")
    assert "<svg" in svg
    assert "</svg>" in svg
    assert "fltx-qr-code" in svg


def test_demo_gatekeeper_safety():
    assert DemoGatekeeper.is_path_safe_for_demo("/demo") is True
    assert DemoGatekeeper.is_path_safe_for_demo("/api/v1/demo/scenarios") is True
    assert DemoGatekeeper.is_path_safe_for_demo("/api/v1/robots/ALL/estop") is False
    assert DemoGatekeeper.is_path_safe_for_demo("/api/v1/robots/AMR-01/payload") is False
