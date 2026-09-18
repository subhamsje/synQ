"""
Unit Tests for FLTX AMR Core Python Node.
Validates state machine transitions, payload speed limits, kinematics, and E-Stop handling.
"""
import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../ros2_ws/src/fltx_amr")))
from fltx_amr.amr_node import FLTXAmrCore

def test_fltx_amr_initialization():
    amr = FLTXAmrCore(robot_id="FLTX-01")
    assert amr.robot_id == "FLTX-01"
    assert amr.state == "IDLE"
    assert amr.active_payload == "NONE"
    assert amr.battery_soc == 100.0
    assert amr.max_speed == 1.5
    assert amr.estop_active is False

def test_fltx_amr_payload_constraints():
    amr = FLTXAmrCore()
    # Attach Scissor Lift
    amr.attach_payload("SCISSOR_LIFT")
    assert amr.active_payload == "SCISSOR_LIFT"
    assert amr.max_speed == 0.8

    # Apply velocity exceeding payload speed cap
    amr.apply_velocity(vx=1.2, vy=0.0, omega=0.0)
    assert pytest.approx(amr.vx, rel=1e-3) == 0.8
    assert amr.state == "NAVIGATING"

    # Attach Roller Conveyor
    amr.attach_payload("ROLLER_CONVEYOR")
    assert amr.max_speed == 1.0

def test_fltx_amr_estop_handling():
    amr = FLTXAmrCore()
    amr.apply_velocity(vx=0.5, vy=0.0, omega=0.0)
    assert amr.state == "NAVIGATING"

    # Trigger E-Stop
    amr.set_estop(True)
    assert amr.state == "ESTOP"
    assert amr.vx == 0.0
    assert amr.vy == 0.0

    # Commands during E-Stop are ignored
    amr.apply_velocity(vx=1.0, vy=0.0, omega=0.0)
    assert amr.vx == 0.0

    # Reset E-Stop
    amr.set_estop(False)
    assert amr.state == "IDLE"

def test_fltx_amr_kinematics_and_battery_drain():
    amr = FLTXAmrCore()
    amr.apply_velocity(vx=1.0, vy=0.0, omega=0.0)
    
    # Step forward 2.0 seconds
    amr.update_step(dt=2.0)
    assert pytest.approx(amr.x, rel=1e-3) == 2.0
    assert pytest.approx(amr.y, abs=1e-4) == 0.0
    assert amr.battery_soc < 100.0
    
    telemetry = amr.get_telemetry()
    assert telemetry["position"]["x"] == 2.0
    assert telemetry["state"] == "NAVIGATING"
