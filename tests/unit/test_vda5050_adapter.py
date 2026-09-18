import json
import pytest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../ros2_ws/src/synq_interfaces')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../ros2_ws/src/synq_executive')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../ros2_ws/src/synq_vda5050')))

from fms.vda5050.vda5050_serializer import (
    VDA5050Header,
    VDA5050NodePosition,
    VDA5050Action,
    VDA5050Node,
    VDA5050Edge,
    VDA5050Order,
    VDA5050Serializer
)
from synq_executive.mission_executive import MissionExecutive
from synq_vda5050.vda5050_adapter import VDA5050Adapter
from synq_interfaces.types import MissionPhaseEnum, SafetyStateEnum


def test_vda5050_order_serialization_and_deserialization():
    """Verify standard VDA 5050 v2.0.0 JSON schema roundtrip."""
    header = VDA5050Header(
        headerId=10,
        timestamp="2026-09-18T12:00:00Z",
        serialNumber="synq-amr-01"
    )
    node1 = VDA5050Node(
        nodeId="N1",
        sequenceId=0,
        nodePosition=VDA5050NodePosition(x=2.5, y=3.0, theta=0.0)
    )
    node2 = VDA5050Node(
        nodeId="N2",
        sequenceId=2,
        nodePosition=VDA5050NodePosition(x=10.0, y=3.0, theta=1.57),
        actions=[VDA5050Action(actionId="act_1", actionType="liftUp", actionParameters={"height_pct": 50.0})]
    )
    edge = VDA5050Edge(
        edgeId="E1",
        sequenceId=1,
        startNodeId="N1",
        endNodeId="N2",
        maxSpeed=1.2
    )

    order = VDA5050Order(
        header=header,
        orderId="ORD_VDA_999",
        orderUpdateId=0,
        nodes=[node1, node2],
        edges=[edge]
    )

    json_str = VDA5050Serializer.serialize_order(order)
    assert "ORD_VDA_999" in json_str

    deserialized = VDA5050Serializer.deserialize_order(json_str)
    assert deserialized.orderId == "ORD_VDA_999"
    assert len(deserialized.nodes) == 2
    assert deserialized.nodes[1].actions[0].actionType == "liftUp"


def test_vda5050_adapter_receives_order():
    """Verify that incoming VDA 5050 order triggers internal MissionExecutive."""
    exec_node = MissionExecutive(robot_id="synq-amr-01")
    adapter = VDA5050Adapter(executive=exec_node, serial_number="synq-amr-01")

    order_payload = json.dumps({
        "header": {
            "headerId": 1,
            "timestamp": "2026-09-18T12:00:00Z",
            "version": "2.0.0",
            "manufacturer": "synQ",
            "serialNumber": "synq-amr-01"
        },
        "orderId": "VDA_MISSION_001",
        "orderUpdateId": 0,
        "nodes": [
            {
                "nodeId": "PICK_STATION",
                "sequenceId": 0,
                "nodePosition": {"x": 5.0, "y": 0.0, "theta": 0.0, "mapId": "wh1"}
            },
            {
                "nodeId": "DROP_STATION",
                "sequenceId": 1,
                "nodePosition": {"x": 15.0, "y": 0.0, "theta": 0.0, "mapId": "wh1"}
            }
        ]
    })

    success, msg = adapter.handle_order_message(order_payload)
    assert success is True
    assert exec_node.current_phase == MissionPhaseEnum.NAVIGATING_TO_PICK
    assert exec_node.active_mission.mission_id == "VDA_MISSION_001"


def test_vda5050_instant_actions_estop():
    """Verify that instantStop triggers immediate safety E-Stop in the robot."""
    exec_node = MissionExecutive(robot_id="synq-amr-01")
    adapter = VDA5050Adapter(executive=exec_node, serial_number="synq-amr-01")

    instant_payload = json.dumps({
        "header": {
            "headerId": 2,
            "timestamp": "2026-09-18T12:00:00Z",
            "version": "2.0.0",
            "manufacturer": "synQ",
            "serialNumber": "synq-amr-01"
        },
        "actions": [
            {
                "actionId": "estop_1",
                "actionType": "instantStop"
            }
        ]
    })

    success, msg = adapter.handle_instant_actions(instant_payload)
    assert success is True
    assert exec_node.safety_status.safety_state == SafetyStateEnum.SAFETY_ESTOP


def test_vda5050_state_serialization_schema():
    """Verify that robot state generates compliant VDA 5050 telemetry JSON."""
    exec_node = MissionExecutive(robot_id="synq-amr-01")
    exec_node.update_pose(x=4.25, y=7.80, yaw=1.57)
    exec_node.update_battery(88.5)

    adapter = VDA5050Adapter(executive=exec_node, serial_number="synq-amr-01")
    state_json = adapter.generate_vda5050_state_json()
    data = json.loads(state_json)

    assert data["header"]["serialNumber"] == "synq-amr-01"
    assert data["agvPosition"]["x"] == 4.25
    assert data["agvPosition"]["y"] == 7.80
    assert data["batteryState"]["batteryCharge"] == 88.5
    assert data["operatingMode"] == "AUTOMATIC"
    assert data["safetyState"]["eStop"] == "NONE"
