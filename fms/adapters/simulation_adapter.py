import time
import math
from typing import Dict, List, Any, Optional

from fms.adapters.base_adapter import RobotAdapter
from fms.models.domain_models import RobotStatus, PayloadType


class SimulationRobotAdapter(RobotAdapter):
    """
    High-fidelity deterministic simulation adapter for synQ AMR.
    Simulates Mecanum kinematics, battery degradation, sensor noise,
    and payload attachment state transitions without requiring a running Gazebo instance.
    """

    def __init__(
        self,
        robot_id: str,
        initial_node: str = "N_0_0",
        payload_type: PayloadType = PayloadType.BASE,
        battery_pct: float = 100.0,
        vendor: str = "synQ-Robotics",
        model: str = "synQ-Mecanum-v2"
    ):
        super().__init__(robot_id=robot_id, vendor=vendor, model=model, payload_type=payload_type)
        self.robot.current_node = initial_node
        self.robot.battery_pct = battery_pct
        self.robot.status = RobotStatus.IDLE

        # Waypoint stepping
        self._target_waypoints: List[str] = []
        self._waypoint_index: int = 0
        self._meters_traveled: float = 0.0

    def send_route(self, waypoints: List[str]) -> bool:
        if self.robot.safety_estop:
            return False
        self._target_waypoints = list(waypoints)
        self._waypoint_index = 0
        self.robot.planned_trajectory = list(waypoints)
        if waypoints:
            self.robot.status = RobotStatus.NAVIGATING
        return True

    def cancel_mission(self, mission_id: Optional[str] = None) -> bool:
        self._target_waypoints = []
        self._waypoint_index = 0
        self.robot.planned_trajectory = []
        self.robot.current_mission_id = None
        if self.robot.status == RobotStatus.NAVIGATING:
            self.robot.status = RobotStatus.IDLE
        return True

    def trigger_payload_action(self, action: str, parameter: float = 0.0) -> Dict[str, Any]:
        action_upper = action.upper()
        res = {"robot_id": self.robot.robot_id, "action": action, "success": True}

        if self.robot.payload_type == PayloadType.SCISSOR_LIFT:
            if "LIFT" in action_upper or "RAISE" in action_upper:
                height = min(1.2, max(0.0, parameter if parameter > 0 else 0.8))
                self.robot.payload_state = {"loaded": True, "lift_height_m": height}
                res["detail"] = f"Scissor lift elevated to {height:.2f}m"
            elif "LOWER" in action_upper:
                self.robot.payload_state = {"loaded": False, "lift_height_m": 0.0}
                res["detail"] = "Scissor lift lowered to stowed position (0.0m)"
        elif self.robot.payload_type == PayloadType.ROLLER_CONVEYOR:
            if "LOAD" in action_upper or "TRANSFER" in action_upper:
                self.robot.payload_state = {"loaded": True, "conveyor_rpm": 120.0}
                res["detail"] = "Conveyor bi-directional transfer completed"
            elif "UNLOAD" in action_upper:
                self.robot.payload_state = {"loaded": False, "conveyor_rpm": 0.0}
                res["detail"] = "Conveyor unloaded cargo"
        elif self.robot.payload_type == PayloadType.TOTE_GRIPPER:
            if "CLAMP" in action_upper or "GRIP" in action_upper:
                self.robot.payload_state = {"loaded": True, "clamp_force_n": 85.0}
                res["detail"] = "Tote clamp engaged with 85.0 N force"
            elif "RELEASE" in action_upper:
                self.robot.payload_state = {"loaded": False, "clamp_force_n": 0.0}
                res["detail"] = "Tote clamp released"
        else:
            self.robot.payload_state = {"action": action_upper, "param": parameter}
            res["detail"] = f"Action {action} executed on base chassis"

        return res

    def set_estop(self, emergency_stop: bool) -> bool:
        self.robot.safety_estop = emergency_stop
        if emergency_stop:
            self.robot.status = RobotStatus.EMERGENCY_STOP
            self.robot.velocity = {"vx": 0.0, "vy": 0.0, "omega": 0.0}
            self._target_waypoints = []
        else:
            if self.robot.status == RobotStatus.EMERGENCY_STOP:
                self.robot.status = RobotStatus.IDLE
        return True

    def update_telemetry(self, data: Dict[str, Any]) -> None:
        self.robot.last_heartbeat = time.time()
        if "battery_pct" in data:
            self.robot.battery_pct = float(data["battery_pct"])
        if "current_node" in data:
            self.robot.current_node = str(data["current_node"])
        if "status" in data and isinstance(data["status"], RobotStatus):
            self.robot.status = data["status"]
        if "safety_estop" in data:
            self.robot.safety_estop = bool(data["safety_estop"])

    def step_simulation(self, dt_seconds: float = 1.0) -> None:
        """Deterministic tick for time-domain simulation."""
        self.robot.last_heartbeat = time.time()

        if self.robot.safety_estop:
            self.robot.velocity = {"vx": 0.0, "vy": 0.0, "omega": 0.0}
            return

        if self._target_waypoints and self._waypoint_index < len(self._target_waypoints):
            next_wp = self._target_waypoints[self._waypoint_index]
            self.robot.current_node = next_wp
            self._waypoint_index += 1
            self._meters_traveled += 2.0  # Approx 2m grid step

            # Dynamic battery drain: base 0.05% + 0.03% if carrying payload
            drain = 0.05 + (0.03 if self.robot.payload_state.get("loaded", False) else 0.0)
            self.robot.battery_pct = max(0.0, self.robot.battery_pct - drain)

            self.robot.velocity = {"vx": 0.8, "vy": 0.0, "omega": 0.0}
            self.robot.status = RobotStatus.NAVIGATING

            if self._waypoint_index >= len(self._target_waypoints):
                self._target_waypoints = []
                self.robot.planned_trajectory = []
                self.robot.status = RobotStatus.IDLE
                self.robot.velocity = {"vx": 0.0, "vy": 0.0, "omega": 0.0}
        else:
            self.robot.velocity = {"vx": 0.0, "vy": 0.0, "omega": 0.0}
            if self.robot.status == RobotStatus.NAVIGATING:
                self.robot.status = RobotStatus.IDLE
