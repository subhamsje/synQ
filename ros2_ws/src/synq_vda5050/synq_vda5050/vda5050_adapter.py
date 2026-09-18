import json
import time
from typing import Optional, Dict, Any, Tuple

from fms.vda5050.vda5050_serializer import (
    VDA5050Header,
    VDA5050Order,
    VDA5050State,
    VDA5050InstantActions,
    VDA5050Serializer
)
from synq_interfaces.types import (
    MissionGoal,
    MissionPhaseEnum,
    Pose2D,
    RobotSafetyStatus,
    SafetyStateEnum
)
from synq_executive.mission_executive import MissionExecutive


class VDA5050Adapter:
    """
    Bi-directional VDA 5050 v2.0.0 Protocol Adapter for synQ-AMR.
    Translates MQTT VDA 5050 orders to internal ROS 2 actions and
    serializes robot telemetry back to standard VDA 5050 State messages.
    """

    def __init__(self, executive: MissionExecutive, serial_number: str = "synq-amr-01"):
        self.executive = executive
        self.serial_number = serial_number
        self.header_id_counter = 0
        self.current_order_id = ""
        self.current_order_update_id = 0
        self.last_node_id = "N_0_0"

    def handle_order_message(self, json_payload: str) -> Tuple[bool, str]:
        """Parses incoming VDA 5050 Order and translates to MissionGoal."""
        try:
            order: VDA5050Order = VDA5050Serializer.deserialize_order(json_payload)
        except Exception as e:
            return False, f"Malformed VDA 5050 Order JSON: {str(e)}"

        if order.header.serialNumber != self.serial_number:
            return False, f"Order addressed to {order.header.serialNumber}, but local serial is {self.serial_number}"

        if len(order.nodes) < 2:
            return False, "Order must contain at least 2 nodes (start/pick and end/drop)"

        self.current_order_id = order.orderId
        self.current_order_update_id = order.orderUpdateId

        # Extract pick and drop coordinates
        start_node = order.nodes[0]
        end_node = order.nodes[-1]

        pick_pos = start_node.nodePosition
        drop_pos = end_node.nodePosition

        pick_pose = Pose2D(x=pick_pos.x, y=pick_pos.y, yaw=pick_pos.theta) if pick_pos else Pose2D(0.0, 0.0)
        drop_pose = Pose2D(x=drop_pos.x, y=drop_pos.y, yaw=drop_pos.theta) if drop_pos else Pose2D(1.0, 1.0)

        # Extract any payload actions (e.g. liftUp)
        payload_action = ""
        if end_node.actions:
            payload_action = end_node.actions[0].actionType

        mission_goal = MissionGoal(
            mission_id=order.orderId,
            mission_type="PICK_DROP",
            pick_pose=pick_pose,
            drop_pose=drop_pose,
            payload_action=payload_action
        )

        return self.executive.submit_mission(mission_goal)

    def handle_instant_actions(self, json_payload: str) -> Tuple[bool, str]:
        """Handles emergency stop, pause, or order cancellation instant actions."""
        try:
            instant_actions: VDA5050InstantActions = VDA5050Serializer.deserialize_instant_actions(json_payload)
        except Exception as e:
            return False, f"Malformed InstantActions JSON: {str(e)}"

        for action in instant_actions.actions:
            atype = action.actionType.lower()
            if atype in ["instantstop", "estop"]:
                self.executive.update_safety_status(
                    RobotSafetyStatus(safety_state=SafetyStateEnum.SAFETY_ESTOP)
                )
                return True, "Emergency E-Stop activated via VDA 5050 InstantActions"
            elif atype in ["cancelorder", "abort"]:
                self.executive.preempt_mission("Cancelled via VDA 5050 InstantActions")
                return True, "Order successfully cancelled"

        return True, "Actions processed"

    def generate_vda5050_state_json(self) -> str:
        """Serializes current AMR telemetry into a VDA 5050 v2.0.0 State message."""
        self.header_id_counter += 1
        is_driving = self.executive.current_phase in [
            MissionPhaseEnum.NAVIGATING_TO_PICK,
            MissionPhaseEnum.NAVIGATING_TO_DROP,
            MissionPhaseEnum.NAVIGATING_TO_CHARGE
        ]

        estop_active = self.executive.safety_status.safety_state == SafetyStateEnum.SAFETY_ESTOP

        state = VDA5050State(
            header=VDA5050Header(
                headerId=self.header_id_counter,
                timestamp=VDA5050Serializer.current_timestamp_iso(),
                serialNumber=self.serial_number
            ),
            orderId=self.current_order_id,
            orderUpdateId=self.current_order_update_id,
            lastNodeId=self.last_node_id,
            lastNodeSequenceId=0,
            driving=is_driving,
            operatingMode="AUTOMATIC",
            batteryState={
                "batteryCharge": round(self.executive.battery_pct, 1),
                "charging": self.executive.current_phase == MissionPhaseEnum.CHARGING
            },
            agvPosition={
                "x": round(self.executive.current_pose.x, 3),
                "y": round(self.executive.current_pose.y, 3),
                "theta": round(self.executive.current_pose.yaw, 3),
                "positionInitialized": True
            },
            velocity={
                "vx": 1.0 if is_driving else 0.0,
                "vy": 0.0,
                "omega": 0.0
            },
            safetyState={
                "eStop": "ACTIVE" if estop_active else "NONE",
                "fieldViolation": estop_active
            },
            errors=[]
        )
        return VDA5050Serializer.serialize_state(state)
