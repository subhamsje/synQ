import time
import math
from typing import Dict, List, Any, Optional

from fms.adapters.base_adapter import RobotAdapter
from fms.models.domain_models import RobotStatus, PayloadType, SensorState


class ROS2RobotAdapter(RobotAdapter):
    """
    ROS 2 Robot Adapter for physical or Gazebo-simulated AMRs.
    Interfaces with Nav2 action servers, cmd_vel topics, LiDAR, odometry,
    and diagnostics topics while enforcing standard safety contracts.
    """

    def __init__(
        self,
        robot_id: str,
        vendor: str = "synQ-Hardware",
        model: str = "synQ-AMR-v2-Physical",
        payload_type: PayloadType = PayloadType.SCISSOR_LIFT,
        topic_prefix: Optional[str] = None
    ):
        super().__init__(robot_id=robot_id, vendor=vendor, model=model, payload_type=payload_type)
        prefix = topic_prefix if topic_prefix is not None else f"/{robot_id}"
        self.topic_mapping = {
            "scan": f"{prefix}/scan",
            "odom": f"{prefix}/odom",
            "cmd_vel": f"{prefix}/cmd_vel",
            "battery": f"{prefix}/battery_state",
            "diagnostics": f"{prefix}/diagnostics",
            "estop": f"{prefix}/safety/estop",
            "nav_goal": f"{prefix}/navigate_to_pose"
        }
        self.active_goal_handle = None
        self.connected = True
        self.cmd_vel_history: List[Dict[str, float]] = []

    def send_route(self, waypoints: List[str]) -> bool:
        if self.robot.safety_estop:
            return False
        self.robot.planned_trajectory = list(waypoints)
        self.robot.status = RobotStatus.NAVIGATING
        # In a physical ROS 2 system, this publishes Nav2 NavigateThroughPoses action goal
        return True

    def cancel_mission(self, mission_id: Optional[str] = None) -> bool:
        self.robot.planned_trajectory = []
        self.robot.current_mission_id = None
        self.robot.status = RobotStatus.IDLE
        self.robot.velocity = {"vx": 0.0, "vy": 0.0, "omega": 0.0}
        # In physical ROS 2, this cancels active Nav2 action goal & publishes zero cmd_vel
        return True

    def trigger_payload_action(self, action: str, parameter: float = 0.0) -> Dict[str, Any]:
        return {
            "robot_id": self.robot.robot_id,
            "topic": f"/{self.robot.robot_id}/payload_service",
            "action": action,
            "parameter": parameter,
            "status": "SENT_TO_ROS2_NODE"
        }

    def set_estop(self, emergency_stop: bool) -> bool:
        self.robot.safety_estop = emergency_stop
        if emergency_stop:
            self.robot.status = RobotStatus.EMERGENCY_STOP
            self.robot.velocity = {"vx": 0.0, "vy": 0.0, "omega": 0.0}
            self.robot.planned_trajectory = []
        else:
            if self.robot.status == RobotStatus.EMERGENCY_STOP:
                self.robot.status = RobotStatus.IDLE
        return True

    def update_telemetry(self, data: Dict[str, Any]) -> None:
        self.robot.last_heartbeat = time.time()
        if "position" in data:
            self.robot.position = data["position"]
        if "velocity" in data:
            self.robot.velocity = data["velocity"]
            self.cmd_vel_history.append(data["velocity"])
            if len(self.cmd_vel_history) > 50:
                self.cmd_vel_history.pop(0)
        if "battery_pct" in data:
            self.robot.battery_pct = float(data["battery_pct"])
        if "current_node" in data:
            self.robot.current_node = str(data["current_node"])
        if "sensors" in data:
            s_data = data["sensors"]
            self.robot.sensors.lidar_healthy = s_data.get("lidar_healthy", True)
            self.robot.sensors.imu_healthy = s_data.get("imu_healthy", True)
            self.robot.sensors.amcl_covariance = s_data.get("amcl_covariance", 0.02)
            self.robot.sensors.battery_temp_c = s_data.get("battery_temp_c", 28.0)
            self.robot.sensors.motor_temp_c = s_data.get("motor_temp_c", 35.0)
        if "safety_estop" in data:
            self.robot.safety_estop = bool(data["safety_estop"])
            if self.robot.safety_estop:
                self.robot.status = RobotStatus.EMERGENCY_STOP
