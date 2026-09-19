"""
synQ Unified World Model Coordinator
Maintains synchronized, decoupled operational representations across:
1. 3D Digital Twin (Three.js WebGL spatial scene)
2. 2D Nav2 Occupancy & Costmap (ROS 2 nav_msgs/OccupancyGrid & YAML/PGM)
3. Semantic Scene Graph (FMS & Mission Executive Entity Ontology)
4. Navigation Topology Graph (Conflict-Based Search & VDA 5050 Roadmap)

Provides fast spatial queries, entity-to-approach resolution, and capability lookups.
"""

import math
import time
from typing import Dict, List, Any, Optional, Tuple, Set
from backend.automap.semantic_detector import SemanticObject
from fms.topology.warehouse_graph import WarehouseGraph


class UnifiedWorldModel:
    """
    Central synchronization and query engine for the 4 representations of the warehouse.
    """

    def __init__(self, facility_id: str = "FAC-AUSTIN-01"):
        self.facility_id = facility_id
        self.version = "3.0.0-unified"
        self.last_updated: float = time.time()

        # 4 Core Synchronized Representations
        self.digital_twin_3d: Dict[str, Any] = {}
        self.nav2_occupancy_2d: Dict[str, Any] = {}
        self.semantic_scene_graph: Dict[str, Any] = {}
        self.topology_graph: Dict[str, Any] = {}

        # Live WarehouseGraph instance for CBS routing
        self.live_warehouse_graph: Optional[WarehouseGraph] = None

        # Fast Indexing Caches
        self.entity_registry: Dict[str, SemanticObject] = {}
        self.entity_to_approach_node: Dict[str, str] = {}
        self.approach_to_entity: Dict[str, str] = {}
        self.charger_nodes: List[str] = []
        self.capability_index: Dict[str, List[str]] = {}

    def update_world_model(
        self,
        digital_twin_3d: Dict[str, Any],
        nav2_occupancy_2d: Dict[str, Any],
        semantic_map: Dict[str, Any],
        topology_graph: Dict[str, Any],
        confirmed_objects: List[SemanticObject],
        warehouse_graph: Optional[WarehouseGraph] = None
    ):
        """Atomically updates all 4 synchronized representations and rebuilds indices."""
        self.digital_twin_3d = digital_twin_3d
        self.nav2_occupancy_2d = nav2_occupancy_2d
        self.semantic_scene_graph = semantic_map
        self.topology_graph = topology_graph
        self.live_warehouse_graph = warehouse_graph
        self.last_updated = time.time()

        # Clear and rebuild indices
        self.entity_registry.clear()
        self.entity_to_approach_node.clear()
        self.approach_to_entity.clear()
        self.charger_nodes.clear()
        self.capability_index.clear()

        for obj in confirmed_objects:
            if obj.status == "REJECTED":
                continue

            self.entity_registry[obj.id] = obj

            # Index capabilities
            for cap in obj.capabilities:
                cap_norm = cap.upper()
                if cap_norm not in self.capability_index:
                    self.capability_index[cap_norm] = []
                self.capability_index[cap_norm].append(obj.id)

            # Map approach node
            if obj.approach_node_id:
                self.entity_to_approach_node[obj.id] = obj.approach_node_id
                self.approach_to_entity[obj.approach_node_id] = obj.id

        # Index charging nodes from topology
        for n in topology_graph.get("nodes", []):
            if n.get("node_type") == "CHARGE":
                self.charger_nodes.append(n["node_id"])

    def resolve_entity_approach(self, entity_id_or_node: str) -> str:
        """
        Resolves a semantic entity ID (e.g. 'RACK-A', 'CHG-01', 'STA-P1') to its
        physical topological approach node in the navigation roadmap.
        If already a node ID, returns unchanged.
        """
        # 1. Direct approach node lookup
        if entity_id_or_node in self.entity_to_approach_node:
            return self.entity_to_approach_node[entity_id_or_node]

        # 2. Case-insensitive lookup
        for eid, nid in self.entity_to_approach_node.items():
            if eid.upper() == entity_id_or_node.upper():
                return nid

        # 3. Check if target is a charging dock
        for obj_id, obj in self.entity_registry.items():
            if obj.semantic_type == "charger" and (obj_id in entity_id_or_node or entity_id_or_node in obj.label):
                if obj.approach_node_id:
                    return obj.approach_node_id

        # 4. Return as-is (assuming it's already a valid roadmap node ID)
        return entity_id_or_node

    def find_nearest_charging_dock(self, x: float, y: float) -> Optional[str]:
        """Finds the closest charging dock approach node to an AMR position."""
        if not self.charger_nodes:
            return None

        # Look up node positions from topology graph
        node_map = {n["node_id"]: n for n in self.topology_graph.get("nodes", [])}
        best_node = None
        min_dist = float("inf")

        for cn in self.charger_nodes:
            node_info = node_map.get(cn)
            if node_info:
                d = math.hypot(node_info["x"] - x, node_info["y"] - y)
                if d < min_dist:
                    min_dist = d
                    best_node = cn

        return best_node

    def get_entities_by_capability(self, capability: str) -> List[Dict[str, Any]]:
        """Finds all semantic entities supporting a requested operational capability."""
        cap_norm = capability.upper()
        entity_ids = self.capability_index.get(cap_norm, [])
        res = []
        for eid in entity_ids:
            obj = self.entity_registry.get(eid)
            if obj:
                res.append(obj.to_dict())
        return res

    def get_summary(self) -> Dict[str, Any]:
        """Returns high-level status of the Unified World Model."""
        return {
            "facility_id": self.facility_id,
            "version": self.version,
            "last_updated": self.last_updated,
            "representations": {
                "digital_twin_3d": bool(self.digital_twin_3d),
                "nav2_occupancy_2d": bool(self.nav2_occupancy_2d),
                "semantic_scene_graph": bool(self.semantic_scene_graph),
                "topology_graph": bool(self.topology_graph)
            },
            "indexed_entities_count": len(self.entity_registry),
            "charging_docks_count": len(self.charger_nodes),
            "topology_nodes_count": len(self.topology_graph.get("nodes", [])),
            "topology_edges_count": len(self.topology_graph.get("edges", []))
        }


# Global Unified World Model Instance
unified_world_model = UnifiedWorldModel()
