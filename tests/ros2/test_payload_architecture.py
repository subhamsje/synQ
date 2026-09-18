import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../ros2_ws/src/synq_interfaces')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../ros2_ws/src/synq_payload')))

from synq_interfaces.types import PayloadTypeEnum
from synq_payload.payload_driver import (
    PayloadHardwareManager,
    ScissorLiftDriver,
    RollerConveyorDriver,
    ToteGripperDriver
)


def test_payload_identification_unladen():
    """Verify hardware manager behavior when no payload module is attached."""
    mgr = PayloadHardwareManager()
    ident = mgr.identify_payload()
    assert ident["detected"] is False
    assert ident["payload_type"] == PayloadTypeEnum.NONE
    assert ident["speed_limit"] == 1.5

    # Executing action without payload returns graceful error
    success, msg = mgr.execute_action("LIFT_UP", 10.0)
    assert success is False
    assert "No modular payload attached" in msg


def test_scissor_lift_actuation_and_safety_speed_interlock():
    """Verify scissor lift elevation and hardware speed interlock at height."""
    mgr = PayloadHardwareManager()
    lift = ScissorLiftDriver(serial_number="SYNQ-LIFT-007")
    ident = mgr.attach_payload(lift)

    assert ident["detected"] is True
    assert ident["payload_type"] == PayloadTypeEnum.SCISSOR_LIFT
    assert ident["serial_number"] == "SYNQ-LIFT-007"
    assert mgr.get_max_transit_speed() == 1.2

    # Raise lift
    success, msg = mgr.execute_action("LIFT_UP", 50.0)
    assert success is True
    status = mgr.get_status()
    assert status.position_pct == 50.0

    # Hard safety interlock: cannot drive while elevated
    assert mgr.get_max_transit_speed() == 0.0

    # Lower lift back to transit height
    success, msg = mgr.execute_action("LIFT_DOWN", 0.0)
    assert success is True
    assert mgr.get_status().position_pct == 0.0
    assert mgr.get_max_transit_speed() == 1.2


def test_roller_conveyor_transfer_and_transit_interlock():
    """Verify roller conveyor transfer states and detach safety lock."""
    mgr = PayloadHardwareManager()
    conv = RollerConveyorDriver(serial_number="SYNQ-CONV-042")
    mgr.attach_payload(conv)

    # Start roller transfer
    success, _ = mgr.execute_action("START_TRANSFER", 75.0)
    assert success is True
    status = mgr.get_status()
    assert status.is_busy is True

    # AMR must not move while conveyor is running
    assert mgr.get_max_transit_speed() == 0.0

    # Detach attempt must be rejected while conveyor is running
    detached = mgr.detach_payload()
    assert detached is False

    # Stop conveyor
    mgr.execute_action("STOP")
    assert mgr.get_status().is_busy is False
    assert mgr.get_max_transit_speed() == 1.4

    # Now detach succeeds
    detached = mgr.detach_payload()
    assert detached is True
    assert mgr.identify_payload()["detected"] is False


def test_tote_gripper_clamping():
    """Verify tote gripper clamping and speed governing."""
    mgr = PayloadHardwareManager()
    gripper = ToteGripperDriver()
    mgr.attach_payload(gripper)

    # Clamp tote
    success, _ = mgr.execute_action("CLAMP", 65.0)
    assert success is True
    status = mgr.get_status()
    assert status.is_locked is True
    assert status.position_pct == 65.0

    # Speed limit throttled for laden transit
    assert mgr.get_max_transit_speed() == 1.0

    # Release tote
    mgr.execute_action("RELEASE")
    status = mgr.get_status()
    assert status.is_locked is False
    assert mgr.get_max_transit_speed() == 1.3
