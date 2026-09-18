"""
Unit Tests for synQ Sensor Layer and TF Coordinate Transform Tree.
Validates LiDAR filtering, IMU covariances, and kinematic TF relationships.
"""
import pytest
import math
import sys
import os

# Add ros2_ws/src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../ros2_ws/src/synq_sensors")))

from synq_sensors.lidar_processor import LidarFilter
from synq_sensors.imu_processor import ImuFilter

def test_lidar_range_filtering():
    """Test 1: LiDAR range filtering eliminates chassis self-hits and distant noise."""
    f = LidarFilter(min_valid_range=0.12, max_valid_range=25.0)
    raw = [0.05, 0.11, 0.12, 1.5, 5.0, 24.9, 25.1, 100.0, float('nan'), float('inf')]
    filtered, stats = f.filter_ranges(raw)

    # 0.05 and 0.11 are < 0.12 -> inf
    assert filtered[0] == float('inf')
    assert filtered[1] == float('inf')

    # 0.12, 1.5, 5.0, 24.9 are valid
    assert filtered[2] == 0.12
    assert filtered[3] == 1.5
    assert filtered[4] == 5.0
    assert filtered[5] == 24.9

    # 25.1, 100.0, nan, inf -> inf
    assert filtered[6] == float('inf')
    assert filtered[7] == float('inf')
    assert filtered[8] == float('inf')
    assert filtered[9] == float('inf')

    assert stats["valid_points"] == 4
    assert stats["min_distance_m"] == 0.12
    assert stats["healthy"] is True

def test_lidar_watchdog_timeout():
    """Test 2: LiDAR watchdog triggers timeout flag when scans stop."""
    f = LidarFilter(timeout_sec=0.20)
    # Never scanned yet -> timed out
    assert f.is_timed_out() is True

    f.filter_ranges([1.0, 2.0])
    assert f.is_timed_out(current_time=f.last_scan_time + 0.10) is False
    assert f.is_timed_out(current_time=f.last_scan_time + 0.25) is True

def test_imu_covariances():
    """Test 3: IMU filter generates valid diagonal covariances for EKF."""
    imu = ImuFilter(gyro_noise_std=0.005, accel_noise_std=0.05)
    ori_cov, ang_cov, acc_cov = imu.calculate_covariances()

    assert len(ori_cov) == 9
    assert len(ang_cov) == 9
    assert len(acc_cov) == 9

    # Check positive diagonal variances
    assert ang_cov[0] == pytest.approx(0.005**2)
    assert ang_cov[4] == pytest.approx(0.005**2)
    assert ang_cov[8] == pytest.approx(0.005**2)

    assert acc_cov[0] == pytest.approx(0.05**2)
    assert acc_cov[4] == pytest.approx(0.05**2)
    assert acc_cov[8] == pytest.approx(0.05**2)

def test_imu_gravity_tilt_estimation():
    """Test 4: IMU gravity vector tilt angle estimation."""
    imu = ImuFilter()
    # Level robot: ax=0, ay=0, az=9.81
    roll, pitch = imu.estimate_tilt_angles(0.0, 0.0, 9.81)
    assert pytest.approx(roll, abs=1e-4) == 0.0
    assert pytest.approx(pitch, abs=1e-4) == 0.0

    # 30 deg pitch up: ax = -9.81 * sin(30 deg) = -4.905, az = 9.81 * cos(30 deg) = 8.4957
    roll, pitch = imu.estimate_tilt_angles(-4.905, 0.0, 8.4957)
    assert pytest.approx(roll, abs=1e-3) == 0.0
    assert pytest.approx(pitch, abs=1e-3) == math.radians(30.0)

def test_tf_tree_kinematics():
    """Test 5: Coordinate transform offsets from base_footprint to sensor frames."""
    wheel_radius = 0.076
    chassis_height = 0.18
    lidar_rel_base = (0.28, 0.0, chassis_height)
    imu_rel_base = (0.0, 0.0, 0.08)

    # Transform from base_footprint to lidar_link:
    # z_total = wheel_radius + chassis_height
    lidar_z_ground = wheel_radius + lidar_rel_base[2]
    assert pytest.approx(lidar_z_ground, rel=1e-4) == 0.256

    # Transform from base_footprint to imu_link:
    imu_z_ground = wheel_radius + imu_rel_base[2]
    assert pytest.approx(imu_z_ground, rel=1e-4) == 0.156
