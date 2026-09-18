"""
synQ AMR Mecanum Kinematics Engine
Standard 4-Wheel Independent Drive in O-Shape Configuration.

Coordinate Conventions:
- Robot Frame:
  +X: Forward
  +Y: Lateral Left
  +Z: Upward (Yaw theta: Counter-Clockwise positive)
- Wheels:
  fl: Front-Left  (+Lx, +Ly)
  fr: Front-Right (+Lx, -Ly)
  rl: Rear-Left   (-Lx, +Ly)
  rr: Rear-Right  (-Lx, -Ly)
"""
from dataclasses import dataclass
from typing import Tuple
import math

@dataclass(frozen=True)
class WheelSpeeds:
    fl: float  # Front-Left  (rad/s)
    fr: float  # Front-Right (rad/s)
    rl: float  # Rear-Left   (rad/s)
    rr: float  # Rear-Right  (rad/s)

@dataclass(frozen=True)
class Twist2D:
    vx: float     # Linear X velocity (m/s)
    vy: float     # Linear Y velocity / lateral strafe (m/s)
    omega: float  # Angular Z velocity (rad/s)

class MecanumKinematics:
    def __init__(self, wheel_radius: float = 0.076, half_wheelbase_x: float = 0.25, half_track_y: float = 0.20):
        """
        Initialize Mecanum drive physical parameters.
        
        :param wheel_radius: Radius R of Mecanum wheels in meters (default: 0.076m / 152mm dia)
        :param half_wheelbase_x: Longitudinal distance Lx from robot center to axle in meters
        :param half_track_y: Transverse distance Ly from robot center to wheel contact point in meters
        """
        if wheel_radius <= 0:
            raise ValueError("Wheel radius must be strictly positive")
        if half_wheelbase_x <= 0 or half_track_y <= 0:
            raise ValueError("Chassis geometry (Lx, Ly) must be strictly positive")
            
        self.r = float(wheel_radius)
        self.lx = float(half_wheelbase_x)
        self.ly = float(half_track_y)
        self.k_geom = self.lx + self.ly

    def inverse_kinematics(self, twist: Twist2D) -> WheelSpeeds:
        """
        Converts desired body twist (vx, vy, omega) to individual wheel angular velocities (rad/s).
        
        Standard O-shape roller configuration equations:
        w_fl = (1/R) * (vx - vy - (Lx + Ly)*omega)
        w_fr = (1/R) * (vx + vy + (Lx + Ly)*omega)
        w_rl = (1/R) * (vx + vy - (Lx + Ly)*omega)
        w_rr = (1/R) * (vx - vy + (Lx + Ly)*omega)
        """
        w_fl = (twist.vx - twist.vy - self.k_geom * twist.omega) / self.r
        w_fr = (twist.vx + twist.vy + self.k_geom * twist.omega) / self.r
        w_rl = (twist.vx + twist.vy - self.k_geom * twist.omega) / self.r
        w_rr = (twist.vx - twist.vy + self.k_geom * twist.omega) / self.r
        return WheelSpeeds(fl=w_fl, fr=w_fr, rl=w_rl, rr=w_rr)

    def forward_kinematics(self, wheels: WheelSpeeds) -> Twist2D:
        """
        Converts individual wheel angular velocities (rad/s) to robot body twist (vx, vy, omega).
        
        vx    = (R/4) * (w_fl + w_fr + w_rl + w_rr)
        vy    = (R/4) * (-w_fl + w_fr + w_rl - w_rr)
        omega = (R / (4 * (Lx + Ly))) * (-w_fl + w_fr - w_rl + w_rr)
        """
        vx = (self.r / 4.0) * (wheels.fl + wheels.fr + wheels.rl + wheels.rr)
        vy = (self.r / 4.0) * (-wheels.fl + wheels.fr + wheels.rl - wheels.rr)
        omega = (self.r / (4.0 * self.k_geom)) * (-wheels.fl + wheels.fr - wheels.rl + wheels.rr)
        return Twist2D(vx=vx, vy=vy, omega=omega)

    def compute_odometry_delta(self, d_ticks: Tuple[float, float, float, float], ticks_per_rev: int = 4096) -> Tuple[float, float, float]:
        """
        Computes planar displacement delta (dx, dy, dtheta) in robot local frame from incremental wheel encoder ticks.
        """
        rad_per_tick = (2.0 * math.pi) / float(ticks_per_rev)
        d_rad_fl = d_ticks[0] * rad_per_tick
        d_rad_fr = d_ticks[1] * rad_per_tick
        d_rad_rl = d_ticks[2] * rad_per_tick
        d_rad_rr = d_ticks[3] * rad_per_tick

        dx = (self.r / 4.0) * (d_rad_fl + d_rad_fr + d_rad_rl + d_rad_rr)
        dy = (self.r / 4.0) * (-d_rad_fl + d_rad_fr + d_rad_rl - d_rad_rr)
        dtheta = (self.r / (4.0 * self.k_geom)) * (-d_rad_fl + d_rad_fr - d_rad_rl + d_rad_rr)
        return dx, dy, dtheta
