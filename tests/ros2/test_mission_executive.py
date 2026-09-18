import os
import sys
import pytest

# Insert synq_interfaces and synq_executive paths
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../ros2_ws/src/synq_interfaces')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../ros2_ws/src/synq_executive')))

from synq_interfaces.types import (
    PayloadTypeEnum,
    SafetyStateEnum,
    MissionPhaseEnum,
    PayloadStatus,
    RobotSafetyStatus,
    MissionGoal,
    MissionResult,
    MissionFeedback,
    Pose2D
)
from synq_executive.mission_executive import MissionExecutive


def test_mission_submission_and_progression():
    """Verify complete lifecycle progression of a standard warehouse PICK_DROP mission."""
    exec_node = MissionExecutive(robot_id="synq-01", charge_dock_pose=Pose2D(0.0, 0.0))
    exec_node.simulated_nav_speed = 5.0  # Speed up for test

    feedbacks = []
    exec_node.register_feedback_callback(lambda fb: feedbacks.append(fb.current_phase))

    goal = MissionGoal(
        mission_id="MISSION-101",
        mission_type="PICK_DROP",
        pick_pose=Pose2D(x=2.0, y=0.0),
        drop_pose=Pose2D(x=4.0, y=0.0),
        payload_action="LIFT_PICK"
    )

    success, msg = exec_node.submit_mission(goal)
    assert success is True
    assert exec_node.current_phase == MissionPhaseEnum.NAVIGATING_TO_PICK

    result = None
    max_steps = 100
    for _ in range(max_steps):
        result = exec_node.tick(0.2)
        if result is not None:
            break

    assert result is not None, "Mission timed out without completing"
    assert result.success is True
    assert "completed successfully" in result.result_message
    assert exec_node.current_phase == MissionPhaseEnum.COMPLETED

    # Verify key phase progression occurred
    assert MissionPhaseEnum.NAVIGATING_TO_PICK in feedbacks
    assert MissionPhaseEnum.ACTUATING_PAYLOAD_PICK in feedbacks
    assert MissionPhaseEnum.NAVIGATING_TO_DROP in feedbacks
    assert MissionPhaseEnum.ACTUATING_PAYLOAD_DROP in feedbacks


def test_mission_rejected_when_scissor_lift_raised():
    """Verify physical safety interlock: robot cannot start mission with raised scissor lift."""
    exec_node = MissionExecutive(robot_id="synq-01")
    exec_node.update_payload_status(
        PayloadStatus(
            payload_type=PayloadTypeEnum.SCISSOR_LIFT,
            position_pct=45.0,  # Lift raised
            is_locked=True
        )
    )

    goal = MissionGoal(
        mission_id="MISSION-LIFT-FAIL",
        mission_type="PICK_DROP",
        pick_pose=Pose2D(x=2.0, y=2.0),
        drop_pose=Pose2D(x=5.0, y=5.0)
    )

    success, msg = exec_node.submit_mission(goal)
    assert success is False
    assert "Scissor lift must be lowered" in msg


def test_mission_preempted_on_safety_estop():
    """Verify emergency stop immediate preemption during active mission."""
    exec_node = MissionExecutive(robot_id="synq-01")
    goal = MissionGoal(
        mission_id="MISSION-ESTOP-TEST",
        mission_type="PICK_DROP",
        pick_pose=Pose2D(x=10.0, y=0.0),
        drop_pose=Pose2D(x=20.0, y=0.0)
    )

    success, _ = exec_node.submit_mission(goal)
    assert success is True

    # Advance one step
    exec_node.tick(0.1)
    assert exec_node.current_phase == MissionPhaseEnum.NAVIGATING_TO_PICK

    # Trigger E-STOP from safety supervisor
    exec_node.update_safety_status(
        RobotSafetyStatus(safety_state=SafetyStateEnum.SAFETY_ESTOP)
    )

    assert exec_node.current_phase == MissionPhaseEnum.FAILED
    assert exec_node.active_mission is None


def test_low_battery_auto_dock_charge():
    """Verify automatic mission preemption and docking when battery dips below threshold."""
    dock_pose = Pose2D(x=1.0, y=1.0)
    exec_node = MissionExecutive(robot_id="synq-01", charge_dock_pose=dock_pose)
    exec_node.simulated_nav_speed = 10.0

    goal = MissionGoal(
        mission_id="PATROL-LONG",
        mission_type="PICK_DROP",
        pick_pose=Pose2D(x=50.0, y=50.0),
        drop_pose=Pose2D(x=60.0, y=60.0)
    )
    exec_node.submit_mission(goal)
    assert exec_node.current_phase == MissionPhaseEnum.NAVIGATING_TO_PICK

    # Simulate battery drain event below 15%
    exec_node.update_battery(12.0)
    assert exec_node.current_phase == MissionPhaseEnum.NAVIGATING_TO_CHARGE
    assert exec_node.target_pose == dock_pose

    # Advance until docked and charged
    result = None
    for _ in range(200):
        result = exec_node.tick(0.5)
        if result is not None:
            break

    assert result is not None
    assert result.success is True
    assert "Charging completed" in result.result_message
    assert exec_node.battery_pct >= 95.0
