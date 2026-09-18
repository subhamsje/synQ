import pytest
from fms.models.domain_models import (
    Robot, RobotStatus, PayloadType, RobotCapability, SensorState,
    Task, TaskStatus, Route, Incident, IncidentType, HealthRecord
)


def test_robot_initialization_and_availability():
    bot = Robot(
        robot_id="synq-amr-01",
        vendor="synQ-Robotics",
        model="FLTX-v2",
        status=RobotStatus.IDLE,
        battery_pct=92.0,
        payload_type=PayloadType.SCISSOR_LIFT
    )
    assert bot.is_available_for_dispatch() is True

    # When busy or low battery
    bot.status = RobotStatus.NAVIGATING
    assert bot.is_available_for_dispatch() is False

    bot.status = RobotStatus.IDLE
    bot.battery_pct = 15.0
    assert bot.is_available_for_dispatch() is False

    bot.battery_pct = 80.0
    bot.safety_estop = True
    assert bot.is_available_for_dispatch() is False


def test_task_domain_model():
    task = Task(
        task_id="TASK-001",
        pick_node="N_0_0",
        drop_node="N_3_3",
        required_payload=PayloadType.ROLLER_CONVEYOR,
        priority=2
    )
    assert task.status == TaskStatus.PENDING
    assert task.pick_node == "N_0_0"
    assert task.required_payload == PayloadType.ROLLER_CONVEYOR


def test_incident_domain_model():
    incident = Incident(
        incident_id="INC-01",
        incident_type=IncidentType.AISLE_BLOCK_REROUTE,
        robot_id="synq-amr-02",
        node_or_location="N_1_1",
        description="Pallet dropped in aisle",
        recovery_action="REROUTE_VIA_C04"
    )
    assert incident.resolved is True
    assert incident.incident_type == IncidentType.AISLE_BLOCK_REROUTE
