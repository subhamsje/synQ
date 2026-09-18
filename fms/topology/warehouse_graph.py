import math
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Set


@dataclass
class WarehouseNode:
    node_id: str
    x: float
    y: float
    node_type: str = "TRANSIT"  # "TRANSIT", "PICK", "DROP", "CHARGE", "STAGING"
    allowed_payloads: Set[str] = field(default_factory=lambda: {"ANY"})


@dataclass
class WarehouseEdge:
    source_id: str
    target_id: str
    distance: float
    max_speed: float = 1.5
    bidirectional: bool = True


class WarehouseGraph:
    """
    Topological roadmap representation of a smart automated warehouse.
    Supports distance queries, neighbor lookups, and graph validation.
    """

    def __init__(self):
        self.nodes: Dict[str, WarehouseNode] = {}
        self.edges: Dict[str, List[WarehouseEdge]] = {}

    def add_node(self, node_id: str, x: float, y: float, node_type: str = "TRANSIT", allowed_payloads: Optional[Set[str]] = None):
        self.nodes[node_id] = WarehouseNode(
            node_id=node_id,
            x=x,
            y=y,
            node_type=node_type,
            allowed_payloads=allowed_payloads or {"ANY"}
        )
        if node_id not in self.edges:
            self.edges[node_id] = []

    def add_edge(self, source_id: str, target_id: str, max_speed: float = 1.5, bidirectional: bool = True):
        if source_id not in self.nodes or target_id not in self.nodes:
            raise ValueError(f"Both nodes {source_id} and {target_id} must exist in graph")

        p1 = self.nodes[source_id]
        p2 = self.nodes[target_id]
        dist = math.hypot(p2.x - p1.x, p2.y - p1.y)

        edge_fwd = WarehouseEdge(source_id=source_id, target_id=target_id, distance=dist, max_speed=max_speed, bidirectional=bidirectional)
        self.edges[source_id].append(edge_fwd)

        if bidirectional:
            edge_rev = WarehouseEdge(source_id=target_id, target_id=source_id, distance=dist, max_speed=max_speed, bidirectional=bidirectional)
            self.edges[target_id].append(edge_rev)

    def get_neighbors(self, node_id: str) -> List[Tuple[str, float]]:
        """Returns list of (neighbor_id, edge_traversal_time)."""
        res = []
        for edge in self.edges.get(node_id, []):
            time_cost = edge.distance / max(0.1, edge.max_speed)
            res.append((edge.target_id, time_cost))
        return res

    def get_distance(self, u: str, v: str) -> float:
        n1 = self.nodes[u]
        n2 = self.nodes[v]
        return math.hypot(n2.x - n1.x, n2.y - n1.y)

    @classmethod
    def create_standard_warehouse_grid(cls) -> "WarehouseGraph":
        """
        Builds a canonical 4x4 warehouse topological grid
        with picking aisles, packaging stations, and charging docks.
        """
        g = cls()
        # Create 16 nodes on a 5m grid (0,0) to (15, 15)
        for r in range(4):
            for c in range(4):
                nid = f"N_{r}_{c}"
                x = float(c * 5.0)
                y = float(r * 5.0)
                ntype = "TRANSIT"
                if r == 0 and c == 0:
                    ntype = "CHARGE"
                elif r == 3 and c == 3:
                    ntype = "CHARGE"
                elif r == 1:
                    ntype = "PICK"
                elif r == 2:
                    ntype = "DROP"
                g.add_node(nid, x, y, node_type=ntype)

        # Connect grid edges
        for r in range(4):
            for c in range(4):
                curr = f"N_{r}_{c}"
                if c < 3:
                    right = f"N_{r}_{c+1}"
                    g.add_edge(curr, right, max_speed=1.5, bidirectional=True)
                if r < 3:
                    down = f"N_{r+1}_{c}"
                    g.add_edge(curr, down, max_speed=1.5, bidirectional=True)

        return g
