import time
import math
from typing import Dict, List, Any, Optional

from fms.adapters.base_adapter import RobotAdapter
from fms.models.domain_models import RobotStatus, PayloadType, SensorState
from backend.agent.robot_state import robot_state, RobotState


class ROS2RobotAdapter(RobotAdapter):
    """
    ROS 2 Robot Adapter for physical or Gazebo-simulated AMRs.
    Interfaces with Nav2 action servers, cmd_vel topics, LiDAR, odometry,
    and diagnostics topics while enforcing standard safety contracts.
    
    Also syncs telemetry to the centralized RobotState manager for
    dashboard consumption.
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
        
        # Ensure the robot exists in the centralized state manager
        state = robot_state.get_state(robot_id)
        if state is None:
            state = robot_state.register_robot(
                robot_id=robot_id,
                node="N_0_0",
                position={"x": 0.0, "y": 0.0, "theta": 0.0},
                velocity={"vx": 0.0, "vy": 0.0, "omega": 0.0},
                battery={"pct": 100.0, "temp_c": 25.0, "charging": False},
                status=RobotStatus.IDLE,
                payload=str(payload_type),
                current_mission=None,
                trajectory=[]
            )

    def send_route(self, waypoints: List[str]) -> bool:
        if self.robot.safety_estop:
            return False
        self.robot.planned_trajectory = list(waypoints)
        self.robot.status = RobotStatus.NAVIGATING
        
        # Sync to centralized state
        robot_state.update_state(
            self.robot.robot_id,
            status="NAVIGATING",
            mission=robot_state.get_state(self.robot.robot_id).current_mission if robot_state.get_state(self.robot.robot_id) else None,
            trajectory=waypoints
        )
        
        # In a physical ROS 2 system, this publishes Nav2 NavigateThroughPoses action goal
        return True

    def cancel_mission(self, mission_id: Optional[str] = None) -> bool:
        self.robot.planned_trajectory = []
        self.robot.current_mission_id = None
        self.robot.status = RobotStatus.IDLE
        self.robot.velocity = {"vx": 0.0, "vy": 0.0, "omega": 0.0}
        
        # Sync to centralized state
        robot_state.update_state(
            self.robot.robot_id,
            status="IDLE",
            mission=None,
            velocity={"vx": 0.0, "vy": 0.0, "omega": 0.0},
            trajectory=[]
        )
        
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
        
        # Sync to centralized state
        robot_state.update_state(
            self.robot.robot_id,
            emergency_stop=emergency_stop
        )
        
        return True

    def update_telemetry(self, data: Dict[str, Any]) -> None:
        """Update robot state from ROS 2 topics and sync to centralized state."""
        self.robot.last_heartbeat = time.time()
        
        # Extract position (from odometry)
        if "position" in data:
            pos = data["position"]
            self.robot.position = pos
            robot_state.update_state(
                self.robot.robot_id,
                position={"x": float(pos.get("x", 0.0)), "y": float(pos.get("y", 0.0)), "theta": float(pos.get("theta", 0.0))},
                source={"source": "odom"}
            )
        
        # Extract velocity (from odom twist)
        if "velocity" in data:
            vel = data["velocity"]
            self.robot.velocity = vel
            self.cmd_vel_history.append(vel)
            if len(self.cmd_vel_history) > 50:
                self.cmd_vel_history.pop(0)
            robot_state.update_state(
                self.robot.robot_id,
                velocity={"vx": float(vel.get("vx", 0.0)), "vy": float(vel.get("vy", 0.0)), "omega": float(vel.get("omega", 0.0))},
                source={"source": "odom"}
            )
        
        # Extract battery state
        if "battery_pct" in data:
            battery_pct = float(data["battery_pct"])
            temp_c = data.get("battery_temp_c")
            charging = data.get("charging", False)
            self.robot.battery_pct = battery_pct
            robot_state.update_state(
                self.robot.robot_id,
                battery_pct=battery_pct,
                battery_temp_c=temp_c,
                charging=charging
            )
        
        # Extract node assignment
        if "current_node" in data:
            node = str(data["current_node"])
            self.robot.current_node = node
            robot_state.update_state(self.robot.robot_id, node=node, source={"source": "odom"})
        
        # Extract sensor states
        if "sensors" in data:
            s_data = data["sensors"]
            self.robot.sensors.lidar_healthy = s_data.get("lidar_healthy", True)
            self.robot.sensors.imu_healthy = s_data.get("imu_healthy", True)
            self.robot.sensors.amcl_covariance = s_data.get("amcl_covariance", 0.02)
            if "battery_temp_c" in s_data:
                self.robot.sensors.battery_temp_c = s_data["battery_temp_c"]
            if "motor_temp_c" in s_data:
                self.robot.sensors.motor_temp_c = s_data["motor_temp_c"]
            
            # Update centralized state with sensor info
            robot_state.update_state(
                self.robot.robot_id,
                battery_temp_c=s_data.get("battery_temp_c", 28.0),
                sensors={
                    "lidar_blindzone": s_data.get("lidar_blindzone_active", False),
                    "imu_tilt": s_data.get("imu_tilt_warning", False),
                    "min_distance": s_data.get("min_obstacle_distance", 10.0)
                }
            )
        
        # Extract emergency stop state
        if "safety_estop" in data:
            estop_active = bool(data["safety_estop"])
            self.robot.safety_estop = estop_active
            if estop_active:
                self.robot.status = RobotStatus.EMERGENCY_STOP
            robot_state.update_state(self.robot.robot_id, emergency_stop=estop_active)
        
        # Extract status from various sources
        if "status" in data:
            status_val = data["status"]
            if isinstance(status_val, str):
                try:
                    status_enum = RobotStatus(status_val)
                except ValueError:
                    status_enum = RobotStatus.IDLE
            else:
                status_enum = RobotStatus.IDLE
            self.robot.status = status_enum
            robot_state.update_state(self.robot.robot_id, status=status_enum.value)
        
        # Extract mission info
        if "mission_id" in data:
            self.robot.current_mission_id = data["mission_id"]
            robot_state.update_state(self.robot.robot_id, mission=data["mission_id"])
        
        # Extract payload info
        if "payload_type" in data:
            self.robot.payload_type = data["payload_type"]
            robot_state.update_state(self.robot.robot_id, payload=data["payload_type"])
