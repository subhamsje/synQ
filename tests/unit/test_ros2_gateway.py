import pytest
import asyncio
from backend.gateway.ros2_gateway import ROS2Gateway, GatewayState
from fms.models.domain_models import RobotStatus


@pytest.mark.anyio
async def test_ros2_gateway_lifecycle():
    gw = ROS2Gateway()
    assert gw.state == GatewayState.CONNECTED

    ad = gw.register_robot("test-bot-01")
    assert ad is not None

    # Ingest nominal telemetry
    await gw.ingest_telemetry("test-bot-01", {
        "current_node": "N_2_2",
        "battery_pct": 75.0,
        "safety_estop": False
    })
    status = gw.get_status()
    assert status["connected_robots"] == 1
    assert status["robots"]["test-bot-01"]["battery"] == 75.0
    assert status["robots"]["test-bot-01"]["healthy"] is True

    # Dispatch trajectory
    success = await gw.dispatch_navigation_goal("test-bot-01", ["N_2_2", "N_2_3"])
    assert success is True
    assert ad.robot.status == RobotStatus.NAVIGATING

    # Emergency stop
    await gw.emergency_stop_robot("test-bot-01")
    assert ad.robot.safety_estop is True
    assert ad.robot.status == RobotStatus.EMERGENCY_STOP
