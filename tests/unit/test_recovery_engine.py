import pytest
import asyncio
from backend.recovery.recovery_engine import AutonomousRecoveryEngine
from fms.topology.warehouse_graph import WarehouseGraph
from fms.fleet.fleet_manager import FleetManager, RobotAgent, WarehouseOrder


@pytest.mark.anyio
async def test_recovery_engine_aisle_block():
    graph = WarehouseGraph.create_standard_warehouse_grid()
    fms = FleetManager(graph)
    bot = RobotAgent(robot_id="synq-amr-01", current_node="N_0_0", planned_trajectory=["N_0_0", "N_0_1", "N_0_2"])
    fms.register_robot(bot)

    engine = AutonomousRecoveryEngine(fms=fms, graph=graph)
    res = await engine.recover_aisle_block("N_0_1")

    assert res["status"] == "RESOLVED_AUTONOMOUSLY"
    assert "synq-amr-01" in res["affected_robots"]
    assert "N_0_1" not in bot.planned_trajectory


@pytest.mark.anyio
async def test_recovery_engine_robot_failure():
    graph = WarehouseGraph.create_standard_warehouse_grid()
    fms = FleetManager(graph)
    bot1 = RobotAgent(robot_id="synq-amr-01", current_node="N_0_0", is_busy=True, current_mission_id="ORD-999", payload_type="SCISSOR_LIFT")
    bot2 = RobotAgent(robot_id="synq-amr-02", current_node="N_0_1", is_busy=False, battery_pct=90.0, payload_type="SCISSOR_LIFT")
    fms.register_robot(bot1)
    fms.register_robot(bot2)
    fms.active_orders["ORD-999"] = WarehouseOrder(order_id="ORD-999", pick_node="N_0_2", drop_node="N_2_2", required_payload="SCISSOR_LIFT")

    engine = AutonomousRecoveryEngine(fms=fms, graph=graph)
    res = await engine.recover_robot_failure("synq-amr-01")

    assert res["recovery_status"] == "REALLOCATED"
    assert res["reassigned_to"] == "synq-amr-02"
    assert bot2.is_busy is True
    assert bot2.current_mission_id == "ORD-999"


@pytest.mark.anyio
async def test_recovery_engine_low_battery():
    graph = WarehouseGraph.create_standard_warehouse_grid()
    fms = FleetManager(graph)
    bot = RobotAgent(robot_id="synq-amr-03", current_node="N_2_2", battery_pct=14.0)
    fms.register_robot(bot)

    engine = AutonomousRecoveryEngine(fms=fms, graph=graph)
    res = await engine.recover_low_battery("synq-amr-03", dock_node="N_0_0")

    assert res["incident_type"] == "BATTERY_CRITICAL_RECOVERY"
    assert res["charging_dock"] == "N_0_0"
    assert bot.planned_trajectory[-1] == "N_0_0"
