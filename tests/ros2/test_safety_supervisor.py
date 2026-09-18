import time
import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../ros2_ws/src/synq_interfaces')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../ros2_ws/src/synq_safety')))

from synq_interfaces.types import SafetyStateEnum
from synq_safety.safety_supervisor import SafetySupervisor


def test_nominal_motion_unaltered():
    """Verify that under safe conditions, velocity commands pass through unscaled."""
    supervisor = SafetySupervisor()
    now = time.time()
    supervisor.last_heartbeat_time = now

    verdict = supervisor.evaluate_safety(
        cmd_vx=1.2,
        cmd_vy=0.5,
        cmd_wz=0.3,
        min_lidar_distance=3.5,
        imu_tilt_deg=1.2,
        loc_covariance_trace=0.04,
        current_time=now
    )

    assert verdict.state == SafetyStateEnum.SAFETY_NORMAL
    assert verdict.safe_vx == 1.2
    assert verdict.safe_vy == 0.5
    assert verdict.safe_wz == 0.3
    assert verdict.reason == "NOMINAL"


def test_lidar_slowdown_field_scaling():
    """Verify that an obstacle in the warning field (0.4m to 1.0m) scales down velocity."""
    supervisor = SafetySupervisor()
    now = time.time()
    supervisor.last_heartbeat_time = now

    # At 0.70m (halfway between 0.40m and 1.00m) -> scale factor is 0.5
    verdict = supervisor.evaluate_safety(
        cmd_vx=1.0,
        cmd_vy=0.8,
        cmd_wz=0.4,
        min_lidar_distance=0.70,
        imu_tilt_deg=0.5,
        loc_covariance_trace=0.02,
        current_time=now
    )

    assert verdict.state == SafetyStateEnum.SAFETY_SLOWDOWN
    assert 0.0 < verdict.safe_vx < 1.0
    assert 0.0 < verdict.safe_vy < 0.8
    assert "SLOWDOWN" in verdict.reason


def test_lidar_estop_field_zeroing():
    """Verify that an obstacle violating the critical safety buffer (<0.40m) instantly zeroes velocity."""
    supervisor = SafetySupervisor()
    now = time.time()
    supervisor.last_heartbeat_time = now

    verdict = supervisor.evaluate_safety(
        cmd_vx=1.5,
        cmd_vy=1.0,
        cmd_wz=1.0,
        min_lidar_distance=0.25,
        imu_tilt_deg=0.2,
        loc_covariance_trace=0.01,
        current_time=now
    )

    assert verdict.state == SafetyStateEnum.SAFETY_ESTOP
    assert verdict.safe_vx == 0.0
    assert verdict.safe_vy == 0.0
    assert verdict.safe_wz == 0.0
    assert "PROXIMITY_ESTOP" in verdict.reason


def test_excessive_tilt_rollover_halt():
    """Verify that AMR halts immediately if tilt exceeds allowable physical threshold."""
    supervisor = SafetySupervisor()
    now = time.time()
    supervisor.last_heartbeat_time = now

    verdict = supervisor.evaluate_safety(
        cmd_vx=1.0,
        cmd_vy=0.0,
        cmd_wz=0.0,
        min_lidar_distance=5.0,
        imu_tilt_deg=9.5,  # Exceeds 8.0 deg
        loc_covariance_trace=0.02,
        current_time=now
    )

    assert verdict.state == SafetyStateEnum.SAFETY_ESTOP
    assert verdict.safe_vx == 0.0
    assert "EXCESSIVE_TILT" in verdict.reason


def test_deadman_heartbeat_timeout():
    """Verify deadman switch halts robot if controller heartbeat goes silent."""
    supervisor = SafetySupervisor()
    past_time = 1000.0
    supervisor.last_heartbeat_time = past_time

    # Evaluate 0.5s later (exceeds 0.25s timeout)
    verdict = supervisor.evaluate_safety(
        cmd_vx=1.0,
        cmd_vy=0.0,
        cmd_wz=0.0,
        min_lidar_distance=5.0,
        imu_tilt_deg=0.0,
        loc_covariance_trace=0.02,
        current_time=past_time + 0.50
    )

    assert verdict.state == SafetyStateEnum.SAFETY_ESTOP
    assert verdict.safe_vx == 0.0
    assert "HEARTBEAT_DEADMAN_TIMEOUT" in verdict.reason
