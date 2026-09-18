import time
from dataclasses import dataclass
from typing import Tuple

from synq_interfaces.types import SafetyStateEnum, RobotSafetyStatus


@dataclass
class SafetyVerdict:
    state: SafetyStateEnum
    safe_vx: float
    safe_vy: float
    safe_wz: float
    reason: str


class SafetySupervisor:
    """
    Independent Safety Supervisor Node for synQ-AMR.
    Intercepts /cmd_vel_nav from Nav2 and enforces hardware safety boundaries:
    - 3-zone dynamic LiDAR proximity fields (Normal, Slowdown, Emergency Stop)
    - Dynamic roll/pitch tilt limits
    - Localization divergence watchdog
    - Heartbeat deadman timer
    """

    def __init__(
        self,
        estop_distance: float = 0.40,
        slowdown_distance: float = 1.00,
        max_tilt_deg: float = 8.0,
        max_loc_covariance: float = 0.50,
        heartbeat_timeout_sec: float = 0.25
    ):
        self.estop_distance = estop_distance
        self.slowdown_distance = slowdown_distance
        self.max_tilt_deg = max_tilt_deg
        self.max_loc_covariance = max_loc_covariance
        self.heartbeat_timeout_sec = heartbeat_timeout_sec

        self.last_heartbeat_time = time.time()
        self.manual_estop = False

    def trigger_manual_estop(self):
        self.manual_estop = True

    def reset_manual_estop(self):
        self.manual_estop = False

    def evaluate_safety(
        self,
        cmd_vx: float,
        cmd_vy: float,
        cmd_wz: float,
        min_lidar_distance: float,
        imu_tilt_deg: float,
        loc_covariance_trace: float,
        current_time: float
    ) -> SafetyVerdict:
        """Evaluates all safety boundaries and scales or zeroes velocity output."""
        
        # 1. Manual E-Stop Check
        if self.manual_estop:
            return SafetyVerdict(
                state=SafetyStateEnum.SAFETY_ESTOP,
                safe_vx=0.0, safe_vy=0.0, safe_wz=0.0,
                reason="MANUAL_ESTOP_ACTIVE"
            )

        # 2. Heartbeat Watchdog
        if (current_time - self.last_heartbeat_time) > self.heartbeat_timeout_sec:
            return SafetyVerdict(
                state=SafetyStateEnum.SAFETY_ESTOP,
                safe_vx=0.0, safe_vy=0.0, safe_wz=0.0,
                reason="HEARTBEAT_DEADMAN_TIMEOUT"
            )

        # 3. Dynamic Tilt Rollover Check
        if imu_tilt_deg > self.max_tilt_deg:
            return SafetyVerdict(
                state=SafetyStateEnum.SAFETY_ESTOP,
                safe_vx=0.0, safe_vy=0.0, safe_wz=0.0,
                reason=f"EXCESSIVE_TILT_{imu_tilt_deg:.1f}_DEG"
            )

        # 4. Localization Loss Check
        if loc_covariance_trace > self.max_loc_covariance:
            return SafetyVerdict(
                state=SafetyStateEnum.SAFETY_SLOWDOWN,
                safe_vx=min(cmd_vx, 0.15),
                safe_vy=min(cmd_vy, 0.15),
                safe_wz=min(cmd_wz, 0.20),
                reason="LOCALIZATION_UNCERTAINTY_HIGH"
            )

        # 5. Proximity Safety Fields
        if min_lidar_distance < self.estop_distance:
            return SafetyVerdict(
                state=SafetyStateEnum.SAFETY_ESTOP,
                safe_vx=0.0, safe_vy=0.0, safe_wz=0.0,
                reason=f"LIDAR_PROXIMITY_ESTOP_{min_lidar_distance:.2f}M"
            )

        if min_lidar_distance < self.slowdown_distance:
            # Linear scaling of velocity between estop and slowdown thresholds
            scale = (min_lidar_distance - self.estop_distance) / (self.slowdown_distance - self.estop_distance)
            scale = max(0.2, min(1.0, scale))
            return SafetyVerdict(
                state=SafetyStateEnum.SAFETY_SLOWDOWN,
                safe_vx=cmd_vx * scale,
                safe_vy=cmd_vy * scale,
                safe_wz=cmd_wz * scale,
                reason=f"LIDAR_PROXIMITY_SLOWDOWN_{min_lidar_distance:.2f}M"
            )

        # All systems nominal
        return SafetyVerdict(
            state=SafetyStateEnum.SAFETY_NORMAL,
            safe_vx=cmd_vx,
            safe_vy=cmd_vy,
            safe_wz=cmd_wz,
            reason="NOMINAL"
        )
