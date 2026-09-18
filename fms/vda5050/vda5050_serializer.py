import json
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any


@dataclass
class VDA5050Header:
    headerId: int
    timestamp: str
    version: str = "2.0.0"
    manufacturer: str = "synQ-Robotics"
    serialNumber: str = "synq-amr-01"


@dataclass
class VDA5050NodePosition:
    x: float
    y: float
    theta: float = 0.0
    mapId: str = "warehouse_level_1"


@dataclass
class VDA5050Action:
    actionId: str
    actionType: str  # "liftUp", "liftDown", "startTransfer", "stopTransfer", "charge", "instantStop"
    blockingType: str = "HARD"  # "NONE", "SOFT", "HARD"
    actionParameters: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VDA5050Node:
    nodeId: str
    sequenceId: int
    released: bool = True
    nodePosition: Optional[VDA5050NodePosition] = None
    actions: List[VDA5050Action] = field(default_factory=list)


@dataclass
class VDA5050Edge:
    edgeId: str
    sequenceId: int
    startNodeId: str
    endNodeId: str
    released: bool = True
    maxSpeed: float = 1.5
    actions: List[VDA5050Action] = field(default_factory=list)


@dataclass
class VDA5050Order:
    header: VDA5050Header
    orderId: str
    orderUpdateId: int
    nodes: List[VDA5050Node]
    edges: List[VDA5050Edge] = field(default_factory=list)


@dataclass
class VDA5050State:
    header: VDA5050Header
    orderId: str
    orderUpdateId: int
    lastNodeId: str
    lastNodeSequenceId: int
    driving: bool
    operatingMode: str  # "AUTOMATIC", "MANUAL", "SERVICE"
    batteryState: Dict[str, Any]  # {"batteryCharge": float, "charging": bool}
    agvPosition: Dict[str, Any]  # {"x": float, "y": float, "theta": float, "positionInitialized": bool}
    velocity: Dict[str, float]  # {"vx": float, "vy": float, "omega": float}
    safetyState: Dict[str, Any]  # {"eStop": "NONE"|"ACTIVE", "fieldViolation": bool}
    errors: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class VDA5050InstantActions:
    header: VDA5050Header
    actions: List[VDA5050Action]


class VDA5050Serializer:
    """Utility to serialize and deserialize VDA 5050 v2.0.0 JSON payloads."""

    @staticmethod
    def current_timestamp_iso() -> str:
        return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

    @classmethod
    def create_order_from_nodes(
        cls,
        order_id: str,
        order_update_id: int,
        node_ids: List[str],
        manufacturer: str = "synQ-Robotics",
        serial_number: str = "synq-amr-01"
    ) -> VDA5050Order:
        header = VDA5050Header(
            headerId=1,
            timestamp=cls.current_timestamp_iso(),
            version="2.0.0",
            manufacturer=manufacturer,
            serialNumber=serial_number
        )
        nodes = [
            VDA5050Node(nodeId=nid, sequenceId=i * 2, released=True)
            for i, nid in enumerate(node_ids)
        ]
        edges = []
        for i in range(len(node_ids) - 1):
            edges.append(VDA5050Edge(
                edgeId=f"e_{node_ids[i]}_{node_ids[i+1]}",
                sequenceId=i * 2 + 1,
                startNodeId=node_ids[i],
                endNodeId=node_ids[i+1],
                released=True
            ))
        return VDA5050Order(
            header=header,
            orderId=order_id,
            orderUpdateId=order_update_id,
            nodes=nodes,
            edges=edges
        )

    @classmethod
    def serialize_order(cls, order: VDA5050Order) -> str:
        return json.dumps(asdict(order), indent=2)

    @classmethod
    def deserialize_order(cls, json_str: str) -> VDA5050Order:
        data = json.loads(json_str)
        header = VDA5050Header(**data["header"])
        nodes = []
        for n in data["nodes"]:
            pos = VDA5050NodePosition(**n["nodePosition"]) if n.get("nodePosition") else None
            actions = [VDA5050Action(**a) for a in n.get("actions", [])]
            nodes.append(VDA5050Node(
                nodeId=n["nodeId"],
                sequenceId=n["sequenceId"],
                released=n.get("released", True),
                nodePosition=pos,
                actions=actions
            ))
        edges = []
        for e in data.get("edges", []):
            actions = [VDA5050Action(**a) for a in e.get("actions", [])]
            edges.append(VDA5050Edge(
                edgeId=e["edgeId"],
                sequenceId=e["sequenceId"],
                startNodeId=e["startNodeId"],
                endNodeId=e["endNodeId"],
                released=e.get("released", True),
                maxSpeed=e.get("maxSpeed", 1.5),
                actions=actions
            ))
        return VDA5050Order(
            header=header,
            orderId=data["orderId"],
            orderUpdateId=data["orderUpdateId"],
            nodes=nodes,
            edges=edges
        )

    @classmethod
    def serialize_state(cls, state: VDA5050State) -> str:
        return json.dumps(asdict(state), indent=2)

    @classmethod
    def deserialize_instant_actions(cls, json_str: str) -> VDA5050InstantActions:
        data = json.loads(json_str)
        header = VDA5050Header(**data["header"])
        actions = [VDA5050Action(**a) for a in data.get("actions", [])]
        return VDA5050InstantActions(header=header, actions=actions)
