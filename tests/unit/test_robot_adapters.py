import pytest
from fms.adapters import SimulationRobotAdapter, ROS2RobotAdapter, VDA5050RobotAdapter
from fms.models.domain_models import RobotStatus, PayloadType


def test_simulation_adapter_lifecycle():
    sim = SimulationRobotAdapter(
        robot_id="sim-bot-01",
        initial_node="N_0_0",
        payload_type=PayloadType.SCISSOR_LIFT,
        battery_pct=90.0
    )
    assert sim.get_normalized_robot().status == RobotStatus.IDLE
    assert sim.is_healthy() is True

    # Send route
    assert sim.send_route(["N_0_0", "N_0_1", "N_0_2"]) is True
    assert sim.get_normalized_robot().status == RobotStatus.NAVIGATING

    # Step simulation
    sim.step_simulation()
    assert sim.get_normalized_robot().current_node == "N_0_0"
    sim.step_simulation()
    assert sim.get_normalized_robot().current_node == "N_0_1"
    sim.step_simulation()
    assert sim.get_normalized_robot().current_node == "N_0_2"
    assert sim.get_normalized_robot().status == RobotStatus.IDLE

    # Trigger payload action
    res = sim.trigger_payload_action("LIFT", 0.75)
    assert res["success"] is True
    assert sim.get_normalized_robot().payload_state["lift_height_m"] == 0.75

    # E-stop
    sim.set_estop(True)
    assert sim.get_normalized_robot().safety_estop is True
    assert sim.get_normalized_robot().status == RobotStatus.EMERGENCY_STOP
    assert sim.is_healthy() is False


def test_ros2_adapter_telemetry_and_commands():
    ros_ad = ROS2RobotAdapter(
        robot_id="ros-bot-01",
        payload_type=PayloadType.ROLLER_CONVEYOR
    )
    assert ros_ad.topic_mapping["cmd_vel"] == "/ros-bot-01/cmd_vel"
    assert ros_ad.topic_mapping["scan"] == "/ros-bot-01/scan"

    # Ingest telemetry
    ros_ad.update_telemetry({
        "current_node": "N_1_1",
        "battery_pct": 84.0,
        "velocity": {"vx": 0.5, "vy": 0.0, "omega": 0.1},
        "sensors": {
            "lidar_healthy": True,
            "imu_healthy": True,
            "amcl_covariance": 0.015
        }
    })
    bot = ros_ad.get_normalized_robot()
    assert bot.current_node == "N_1_1"
    assert bot.battery_pct == 84.0
    assert bot.sensors.amcl_covariance == 0.015
    assert ros_ad.is_healthy() is True


def test_vda5050_adapter_order_and_state():
    vda_ad = VDA5050RobotAdapter(
        robot_id="vda-agv-01",
        payload_type=PayloadType.TOTE_GRIPPER
    )
    assert vda_ad.send_route(["N_0_0", "N_1_0"]) is True
    assert vda_ad.get_normalized_robot().status == RobotStatus.NAVIGATING

    # Ingest VDA 5050 state
    vda_ad.update_telemetry({
        "batteryState": {"batteryCharge": 79.5},
        "lastNodeId": "N_1_0",
        "driving": False,
        "safetyState": {"eStop": False}
    })
    bot = vda_ad.get_normalized_robot()
    assert bot.battery_pct == 79.5
    assert bot.current_node == "N_1_0"
    assert bot.status == RobotStatus.IDLE
