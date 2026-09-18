"""
Unit Tests for synQ Localization, Slip Rejection, and SLAM Map Validation.
"""
import pytest
import math
import os
import yaml
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../ros2_ws/src/synq_slam")))
from synq_slam.map_lifecycle_manager import LocalizationHealthMonitor, MapMetadataValidator

def test_amcl_convergence_healthy():
    """Test 1: Converged particle cloud indicates healthy localization."""
    monitor = LocalizationHealthMonitor(pos_divergence_threshold_m=0.40, yaw_divergence_threshold_rad=0.35)
    
    # 6x6 covariance matrix with small variances: var(x)=0.01, var(y)=0.01, var(yaw)=0.02
    cov = [0.0] * 36
    cov[0] = 0.01
    cov[7] = 0.01
    cov[35] = 0.02

    res = monitor.evaluate_pose_covariance(cov)
    assert res["is_localized"] is True
    assert res["requires_recovery"] is False
    assert pytest.approx(res["pos_uncertainty_m"], rel=1e-3) == math.sqrt(0.02)
    assert pytest.approx(res["yaw_uncertainty_rad"], rel=1e-3) == math.sqrt(0.02)

def test_amcl_divergence_kidnapped_robot():
    """Test 2: High particle cloud variance detects kidnapped robot / localization loss."""
    monitor = LocalizationHealthMonitor(pos_divergence_threshold_m=0.40, yaw_divergence_threshold_rad=0.35)
    
    # Large variance indicating diffuse particle cloud
    cov = [0.0] * 36
    cov[0] = 0.25
    cov[7] = 0.25
    cov[35] = 0.40

    res = monitor.evaluate_pose_covariance(cov)
    assert res["is_localized"] is False
    assert res["requires_recovery"] is True
    assert res["pos_uncertainty_m"] > 0.40
    assert res["yaw_uncertainty_rad"] > 0.35

def test_warehouse_map_metadata_validity():
    """Test 3: Validates map YAML configuration according to ROS 2 Nav2 standard."""
    map_yaml_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../simulation/worlds/maps/warehouse_map.yaml"))
    assert os.path.exists(map_yaml_path)

    with open(map_yaml_path, 'r') as f:
        meta = yaml.safe_load(f)

    assert MapMetadataValidator.validate_yaml_metadata(meta) is True
    assert meta["resolution"] == 0.05
    assert meta["origin"] == [-15.0, -10.0, 0.0]
    assert meta["occupied_thresh"] == 0.65
    assert meta["free_thresh"] == 0.25

def test_warehouse_map_file_existence_and_size():
    """Test 4: Checks underlying PGM occupancy grid raster file."""
    map_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../simulation/worlds/maps"))
    pgm_path = os.path.join(map_dir, "warehouse_map.pgm")
    assert os.path.exists(pgm_path)
    assert os.path.getsize(pgm_path) > 1000

    # Verify PGM header
    with open(pgm_path, 'r') as f:
        magic = f.readline().strip()
        dims = f.readline().strip()
        max_val = f.readline().strip()

    assert magic == "P2"
    assert dims == "600 400"
    assert max_val == "255"

def test_synthetic_ekf_slip_rejection():
    """
    Test 5: Synthetic EKF slip rejection simulation.
    When Mecanum wheels experience 40% rotational slip in raw odometry,
    fusing with high-trust gyro rate guarantees correct orientation estimation.
    """
    dt = 0.02  # 50 Hz
    total_time = 1.0
    steps = int(total_time / dt)

    ground_truth_yaw_rate = 0.5  # rad/s constant turn
    simulated_gyro_rate = ground_truth_yaw_rate  # clean IMU

    # Wheel odometry with severe slip: reports only 0.2 rad/s
    slipped_wheel_yaw_rate = 0.2

    # Simple 1D Kalman Filter for Yaw Rate:
    # State x: yaw_rate
    # Measurements: z_wheel (slipped, high variance R_wheel=1.0), z_imu (accurate, low variance R_imu=0.01)
    x = 0.0
    P = 1.0
    Q = 0.01
    R_wheel = 1.0
    R_imu = 0.005

    estimated_yaw_rates = []
    for _ in range(steps):
        # Predict
        P = P + Q
        # Update with IMU
        K_imu = P / (P + R_imu)
        x = x + K_imu * (simulated_gyro_rate - x)
        P = (1.0 - K_imu) * P

        # Update with Wheel
        K_wheel = P / (P + R_wheel)
        x = x + K_wheel * (slipped_wheel_yaw_rate - x)
        P = (1.0 - K_wheel) * P

        estimated_yaw_rates.append(x)

    # The steady-state estimate must reject the slipped wheel reading and stay close to true 0.5 rad/s
    final_estimate = estimated_yaw_rates[-1]
    assert pytest.approx(final_estimate, rel=0.05) == ground_truth_yaw_rate
