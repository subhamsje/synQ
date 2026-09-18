from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import time

from fms.models.domain_models import Robot, RobotStatus, PayloadType


class RobotAdapter(ABC):
    """
    Abstract Base Class for FLTX Normalized Robot Adapters.
    Every AMR in the facility—whether pure simulation, hardware-in-the-loop,
    physical ROS 2 AMR, or third-party VDA 5050 AGV—must implement this interface.
    """

    def __init__(self, robot_id: str, vendor: str, model: str, payload_type: PayloadType = PayloadType.BASE):
        self.robot = Robot(
            robot_id=robot_id,
            vendor=vendor,
            model=model,
            payload_type=payload_type,
            status=RobotStatus.IDLE
        )
        self.heartbeat_timeout_s: float = 3.0

    @abstractmethod
    def send_route(self, waypoints: List[str]) -> bool:
        """Dispatches navigation trajectory to the robot controller."""
        pass

    @abstractmethod
    def cancel_mission(self, mission_id: Optional[str] = None) -> bool:
        """Pre-empts or cancels the active task on the robot."""
        pass

    @abstractmethod
    def trigger_payload_action(self, action: str, parameter: float = 0.0) -> Dict[str, Any]:
        """Executes a payload action (e.g. scissor lift up, conveyor transfer, gripper clamp)."""
        pass

    @abstractmethod
    def set_estop(self, emergency_stop: bool) -> bool:
        """Commands emergency stop or clears emergency stop."""
        pass

    @abstractmethod
    def update_telemetry(self, data: Dict[str, Any]) -> None:
        """Ingests raw or simulated telemetry and normalizes it into self.robot."""
        pass

    def get_normalized_robot(self) -> Robot:
        """Returns the unified, normalized Robot instance."""
        return self.robot

    def is_heartbeat_stale(self) -> bool:
        """Returns True if telemetry has ceased for longer than heartbeat_timeout_s."""
        return (time.time() - self.robot.last_heartbeat) > self.heartbeat_timeout_s

    def is_healthy(self) -> bool:
        """Evaluates if the robot is operational (not in E-stop, not stale, sensors healthy)."""
        if self.robot.safety_estop:
            return False
        if self.is_heartbeat_stale():
            return False
        if not self.robot.sensors.lidar_healthy or not self.robot.sensors.imu_healthy:
            return False
        return True
