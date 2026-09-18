import time
from typing import Dict, List, Any, Optional

from fms.adapters.base_adapter import RobotAdapter
from fms.models.domain_models import RobotStatus, PayloadType
from fms.vda5050.vda5050_serializer import VDA5050Serializer, VDA5050Order, VDA5050State, VDA5050Header, VDA5050Node


class VDA5050RobotAdapter(RobotAdapter):
    """
    VDA 5050 v3.0 standard adapter for heterogeneous industrial AMRs/AGVs.
    Converts central FLTX dispatch commands into VDA 5050 JSON Order & InstantAction topics,
    and maps incoming vehicle State messages back to normalized FLTX domain models.
    """

    def __init__(
        self,
        robot_id: str,
        vendor: str = "Vendor-X-Industrial",
        model: str = "VDA-AGV-500",
        payload_type: PayloadType = PayloadType.ROLLER_CONVEYOR
    ):
        super().__init__(robot_id=robot_id, vendor=vendor, model=model, payload_type=payload_type)
        self.order_update_id: int = 0
        self.last_vda_state: Optional[VDA5050State] = None

    def send_route(self, waypoints: List[str]) -> bool:
        if self.robot.safety_estop:
            return False
        self.order_update_id += 1
        order = VDA5050Serializer.create_order_from_nodes(
            order_id=f"ORD-{int(time.time())}-{self.order_update_id}",
            order_update_id=self.order_update_id,
            node_ids=waypoints
        )
        self.robot.planned_trajectory = list(waypoints)
        self.robot.status = RobotStatus.NAVIGATING
        return True

    def cancel_mission(self, mission_id: Optional[str] = None) -> bool:
        self.robot.planned_trajectory = []
        self.robot.current_mission_id = None
        self.robot.status = RobotStatus.IDLE
        return True

    def trigger_payload_action(self, action: str, parameter: float = 0.0) -> Dict[str, Any]:
        return {
            "robot_id": self.robot.robot_id,
            "vda5050_action": {
                "actionType": action,
                "actionId": f"ACT-{int(time.time())}",
                "blockingType": "HARD",
                "actionParameters": [{"key": "param", "value": parameter}]
            },
            "status": "QUEUED_IN_VDA5050"
        }

    def set_estop(self, emergency_stop: bool) -> bool:
        self.robot.safety_estop = emergency_stop
        if emergency_stop:
            self.robot.status = RobotStatus.EMERGENCY_STOP
            self.robot.planned_trajectory = []
        else:
            if self.robot.status == RobotStatus.EMERGENCY_STOP:
                self.robot.status = RobotStatus.IDLE
        return True

    def update_telemetry(self, data: Dict[str, Any]) -> None:
        self.robot.last_heartbeat = time.time()
        # If raw VDA 5050 state JSON dictionary is supplied
        if "batteryState" in data:
            batt = data["batteryState"]
            self.robot.battery_pct = float(batt.get("batteryCharge", self.robot.battery_pct))
        if "lastNodeId" in data and data["lastNodeId"]:
            self.robot.current_node = str(data["lastNodeId"])
        if "safetyState" in data:
            safety = data["safetyState"]
            self.robot.safety_estop = bool(safety.get("eStop", False))
            if self.robot.safety_estop:
                self.robot.status = RobotStatus.EMERGENCY_STOP
        if "driving" in data:
            if not self.robot.safety_estop:
                self.robot.status = RobotStatus.NAVIGATING if data["driving"] else RobotStatus.IDLE
