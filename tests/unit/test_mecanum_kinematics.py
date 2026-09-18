"""
Unit Tests for synQ Mecanum Kinematics Engine.
Strict mathematical validation of forward and inverse kinematics across all holonomic vectors.
"""
import pytest
import math
import sys
import os

# Add ros2_ws/src/synq_drive to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../ros2_ws/src/synq_drive")))

from synq_drive.kinematics import MecanumKinematics, Twist2D, WheelSpeeds

@pytest.fixture
def kinematics():
    # Standard synQ-AMR dimensions: R=0.076m (152mm dia), Lx=0.25m, Ly=0.20m
    return MecanumKinematics(wheel_radius=0.076, half_wheelbase_x=0.25, half_track_y=0.20)

def test_pure_forward(kinematics):
    """Test 1: Forward translation (vx > 0, vy = 0, omega = 0). All wheels must rotate forward at identical speed."""
    twist = Twist2D(vx=1.0, vy=0.0, omega=0.0)
    wheels = kinematics.inverse_kinematics(twist)
    expected_rad_s = 1.0 / 0.076

    assert pytest.approx(wheels.fl, rel=1e-5) == expected_rad_s
    assert pytest.approx(wheels.fr, rel=1e-5) == expected_rad_s
    assert pytest.approx(wheels.rl, rel=1e-5) == expected_rad_s
    assert pytest.approx(wheels.rr, rel=1e-5) == expected_rad_s

    # Roundtrip FK verification
    recovered_twist = kinematics.forward_kinematics(wheels)
    assert pytest.approx(recovered_twist.vx, rel=1e-5) == 1.0
    assert pytest.approx(recovered_twist.vy, abs=1e-6) == 0.0
    assert pytest.approx(recovered_twist.omega, abs=1e-6) == 0.0

def test_pure_reverse(kinematics):
    """Test 2: Reverse translation (vx < 0, vy = 0, omega = 0). All wheels rotate backward."""
    twist = Twist2D(vx=-0.8, vy=0.0, omega=0.0)
    wheels = kinematics.inverse_kinematics(twist)
    expected_rad_s = -0.8 / 0.076

    assert pytest.approx(wheels.fl, rel=1e-5) == expected_rad_s
    assert pytest.approx(wheels.fr, rel=1e-5) == expected_rad_s
    assert pytest.approx(wheels.rl, rel=1e-5) == expected_rad_s
    assert pytest.approx(wheels.rr, rel=1e-5) == expected_rad_s

def test_pure_left_strafe(kinematics):
    """Test 3: Pure lateral left strafe (vx = 0, vy > 0, omega = 0). FL/RR reverse, FR/RL forward."""
    twist = Twist2D(vx=0.0, vy=0.5, omega=0.0)
    wheels = kinematics.inverse_kinematics(twist)
    expected_mag = 0.5 / 0.076

    assert pytest.approx(wheels.fl, rel=1e-5) == -expected_mag
    assert pytest.approx(wheels.fr, rel=1e-5) == expected_mag
    assert pytest.approx(wheels.rl, rel=1e-5) == expected_mag
    assert pytest.approx(wheels.rr, rel=1e-5) == -expected_mag

    recovered_twist = kinematics.forward_kinematics(wheels)
    assert pytest.approx(recovered_twist.vx, abs=1e-6) == 0.0
    assert pytest.approx(recovered_twist.vy, rel=1e-5) == 0.5
    assert pytest.approx(recovered_twist.omega, abs=1e-6) == 0.0

def test_pure_right_strafe(kinematics):
    """Test 4: Pure lateral right strafe (vx = 0, vy < 0, omega = 0). FL/RR forward, FR/RL reverse."""
    twist = Twist2D(vx=0.0, vy=-0.5, omega=0.0)
    wheels = kinematics.inverse_kinematics(twist)
    expected_mag = 0.5 / 0.076

    assert pytest.approx(wheels.fl, rel=1e-5) == expected_mag
    assert pytest.approx(wheels.fr, rel=1e-5) == -expected_mag
    assert pytest.approx(wheels.rl, rel=1e-5) == -expected_mag
    assert pytest.approx(wheels.rr, rel=1e-5) == expected_mag

def test_pure_rotation_ccw(kinematics):
    """Test 5: Pure Counter-Clockwise rotation (vx = 0, vy = 0, omega > 0). Left wheels reverse, Right wheels forward."""
    omega_cmd = 1.0  # rad/s
    twist = Twist2D(vx=0.0, vy=0.0, omega=omega_cmd)
    wheels = kinematics.inverse_kinematics(twist)
    expected_mag = ((0.25 + 0.20) * omega_cmd) / 0.076

    assert pytest.approx(wheels.fl, rel=1e-5) == -expected_mag
    assert pytest.approx(wheels.fr, rel=1e-5) == expected_mag
    assert pytest.approx(wheels.rl, rel=1e-5) == -expected_mag
    assert pytest.approx(wheels.rr, rel=1e-5) == expected_mag

    recovered_twist = kinematics.forward_kinematics(wheels)
    assert pytest.approx(recovered_twist.vx, abs=1e-6) == 0.0
    assert pytest.approx(recovered_twist.vy, abs=1e-6) == 0.0
    assert pytest.approx(recovered_twist.omega, rel=1e-5) == omega_cmd

def test_diagonal_forward_left(kinematics):
    """
    Test 6: 45-degree diagonal motion forward-left (vx = vy = 0.5 m/s, omega = 0).
    In O-shape Mecanum: FL and RR wheels must be stationary (0.0 rad/s),
    while FR and RL rotate at 2 * v / R.
    """
    twist = Twist2D(vx=0.5, vy=0.5, omega=0.0)
    wheels = kinematics.inverse_kinematics(twist)

    assert pytest.approx(wheels.fl, abs=1e-6) == 0.0
    assert pytest.approx(wheels.rr, abs=1e-6) == 0.0
    assert pytest.approx(wheels.fr, rel=1e-5) == (2.0 * 0.5) / 0.076
    assert pytest.approx(wheels.rl, rel=1e-5) == (2.0 * 0.5) / 0.076

    recovered_twist = kinematics.forward_kinematics(wheels)
    assert pytest.approx(recovered_twist.vx, rel=1e-5) == 0.5
    assert pytest.approx(recovered_twist.vy, rel=1e-5) == 0.5
    assert pytest.approx(recovered_twist.omega, abs=1e-6) == 0.0

def test_combined_holonomic_trajectory(kinematics):
    """Test 7: Combined simultaneous longitudinal, lateral, and rotational motion."""
    twist = Twist2D(vx=0.6, vy=-0.3, omega=0.4)
    wheels = kinematics.inverse_kinematics(twist)
    recovered_twist = kinematics.forward_kinematics(wheels)

    assert pytest.approx(recovered_twist.vx, rel=1e-5) == 0.6
    assert pytest.approx(recovered_twist.vy, rel=1e-5) == -0.3
    assert pytest.approx(recovered_twist.omega, rel=1e-5) == 0.4

def test_odometry_delta_integration(kinematics):
    """Test 8: Forward displacement calculated from encoder ticks."""
    # 4096 ticks per revolution on all 4 wheels = 1 full wheel revolution
    ticks_1_rev = (4096, 4096, 4096, 4096)
    dx, dy, dtheta = kinematics.compute_odometry_delta(ticks_1_rev, ticks_per_rev=4096)
    expected_distance = 2.0 * math.pi * 0.076

    assert pytest.approx(dx, rel=1e-4) == expected_distance
    assert pytest.approx(dy, abs=1e-6) == 0.0
    assert pytest.approx(dtheta, abs=1e-6) == 0.0
