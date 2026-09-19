"""
AutoMap End-to-End Pipeline Service
Coordinates the 7-stage Scan-to-Digital-Twin lifecycle:
SCAN → MAPPING → 3D RECONSTRUCTION → DETECTION → REVIEW/LABEL → MAP GENERATED → READY FOR AUTONOMOUS OPERATION
"""

import time
from typing import Dict, List, Any, Optional
from backend.automap.sensors import SensorDataStream, ScanKeyframe
from backend.automap.reconstruction import PointCloudReconstructor, BoundingBox3D
from backend.automap.semantic_detector import SemanticObjectDetector, SemanticObject
from backend.automap.generator import RepresentationGenerator
from backend.automap.world_model import unified_world_model
from fms.traffic.cbs_router import CBSRouter


class AutoMapService:
    def __init__(self):
        self.sensor_stream = SensorDataStream()
        self.reconstructor = PointCloudReconstructor()
        self.detector = SemanticObjectDetector(confidence_threshold=0.85)
        self.generator = RepresentationGenerator(facility_width=15.0, facility_height=15.0)

        self.current_stage: str = "IDLE"
        self.session_id: Optional[str] = None
        self.robot_id: str = "synq-amr-01"
        self.start_time: float = 0.0

        # Pipeline Cache
        self.keyframes: List[ScanKeyframe] = []
        self.raw_points_count: int = 0
        self.voxel_points_count: int = 0
        self.clusters: List[BoundingBox3D] = []
        self.detections: List[SemanticObject] = []
        self.generated_outputs: Dict[str, Any] = {}
        self.is_active_in_fms: bool = False

    def start_session(self, robot_id: str = "synq-amr-01", profile: str = "standard_hub") -> Dict[str, Any]:
        """Initiates AutoMap scan session."""
        self.session_id = f"MAP-SES-{int(time.time()) % 10000}"
        self.robot_id = robot_id
        self.start_time = time.time()
        self.current_stage = "SCANNING"
        self.is_active_in_fms = False
        self.generated_outputs = {}

        self.sensor_stream = SensorDataStream(robot_id=robot_id)
        # Generate synthetic scan run mimicking Gazebo / physical ROS 2 AMR run
        self.keyframes = self.sensor_stream.generate_synthetic_scan_run(facility_profile=profile)
        self.current_stage = "MAPPING"

        return {
            "session_id": self.session_id,
            "stage": self.current_stage,
            "robot_id": self.robot_id,
            "keyframes_recorded": len(self.keyframes),
            "start_time": self.start_time
        }

    def run_reconstruction_and_detection(self) -> Dict[str, Any]:
        """Runs 3D point cloud reconstruction and semantic detection."""
        if not self.keyframes:
            self.start_session(self.robot_id)

        # Stage: 3D Reconstruction
        self.current_stage = "3D_RECONSTRUCTION"
        recon_stats = self.reconstructor.process_keyframes(self.keyframes)
        self.raw_points_count = recon_stats["total_raw_points"]
        self.voxel_points_count = recon_stats["voxel_filtered_points"]

        self.clusters = self.reconstructor.extract_clusters()

        # Stage: Semantic Detection
        self.current_stage = "DETECTION"
        self.detections = self.detector.detect_objects(self.clusters, self.reconstructor.facility_bounds)

        # Move to Review Stage
        self.current_stage = "REVIEW_LABEL"

        unconfirmed = [d for d in self.detections if d.needs_confirmation]
        confirmed = [d for d in self.detections if not d.needs_confirmation]

        return {
            "session_id": self.session_id,
            "stage": self.current_stage,
            "reconstruction_stats": recon_stats,
            "clusters_count": len(self.clusters),
            "total_detected": len(self.detections),
            "needs_confirmation_count": len(unconfirmed),
            "auto_proposed_count": len(confirmed),
            "detections": [d.to_dict() for d in self.detections]
        }

    def get_session_status(self) -> Dict[str, Any]:
        """Returns status and progress metrics."""
        elapsed = time.time() - self.start_time if self.start_time else 0.0
        unconfirmed = [d for d in self.detections if d.needs_confirmation and d.status != "CONFIRMED"]
        return {
            "session_id": self.session_id or "NONE",
            "stage": self.current_stage,
            "robot_id": self.robot_id,
            "elapsed_seconds": round(elapsed, 1),
            "keyframes": len(self.keyframes),
            "raw_points": self.raw_points_count,
            "filtered_points": self.voxel_points_count,
            "detections_count": len(self.detections),
            "unconfirmed_count": len(unconfirmed),
            "is_active_in_fms": self.is_active_in_fms
        }

    def update_detection(
        self,
        object_id: str,
        semantic_type: Optional[str] = None,
        status: Optional[str] = None,
        label: Optional[str] = None,
        dimensions: Optional[Dict[str, float]] = None,
        position: Optional[Dict[str, float]] = None
    ) -> Optional[Dict[str, Any]]:
        """Human-in-the-loop operator correction and confirmation."""
        for d in self.detections:
            if d.id == object_id:
                if semantic_type:
                    d.semantic_type = semantic_type
                if status:
                    d.status = status
                    if status == "CONFIRMED":
                        d.needs_confirmation = False
                if label:
                    d.label = label
                if dimensions and "dimensions" in d.bounding_box:
                    d.bounding_box["dimensions"].update(dimensions)
                if position and "center" in d.bounding_box:
                    d.bounding_box["center"].update(position)
                return d.to_dict()
        return None

    def confirm_all_detections(self) -> int:
        """Approves all remaining proposed/unconfirmed objects."""
        confirmed_count = 0
        for d in self.detections:
            if d.status != "REJECTED":
                d.status = "CONFIRMED"
                d.needs_confirmation = False
                confirmed_count += 1
        return confirmed_count

    def generate_representations(self) -> Dict[str, Any]:
        """Compiles the 4 decoupled representations."""
        self.current_stage = "MAP_GENERATED"

        # 1. 3D Digital Twin
        dt_3d = self.generator.generate_3d_digital_twin(self.detections)

        # 2. 2D Nav2 Occupancy Grid
        nav2_grid = self.generator.generate_2d_nav2_occupancy_grid(self.detections)

        # 3. Semantic Warehouse Map
        sem_map = self.generator.generate_semantic_warehouse_map(self.detections)

        # 4. Navigation Topology Graph
        topo_graph = self.generator.generate_navigation_graph(self.detections)

        # 5. Build live WarehouseGraph
        wh_graph = self.generator.topology_engine.build_warehouse_graph(self.detections)

        self.generated_outputs = {
            "digital_twin_3d": dt_3d,
            "nav2_occupancy_2d": nav2_grid,
            "semantic_map": sem_map,
            "topology_graph": topo_graph
        }

        # Atomically update Unified World Model
        unified_world_model.update_world_model(
            digital_twin_3d=dt_3d,
            nav2_occupancy_2d=nav2_grid,
            semantic_map=sem_map,
            topology_graph=topo_graph,
            confirmed_objects=self.detections,
            warehouse_graph=wh_graph
        )

        return {
            "stage": self.current_stage,
            "generated_artifacts": list(self.generated_outputs.keys()),
            "racks_count": len(sem_map["racks"]),
            "stations_count": len(sem_map["workstations"]),
            "chargers_count": len(sem_map["charging_points"]),
            "restricted_zones_count": len(sem_map["restricted_zones"]),
            "nav2_resolution_m": nav2_grid["resolution"],
            "topology_nodes_count": topo_graph["total_nodes"],
            "topology_edges_count": topo_graph["total_edges"]
        }

    def activate_in_fms(self, fms_instance: Any = None) -> Dict[str, Any]:
        """Applies newly generated topology into live FMS and marks ready for operation."""
        if not self.generated_outputs:
            self.generate_representations()

        self.current_stage = "READY_FOR_AUTONOMOUS_OPERATION"
        self.is_active_in_fms = True

        # Build fresh dynamic graph from topology engine
        wh_graph = self.generator.topology_engine.build_warehouse_graph(self.detections)

        # If live FMS is provided, update its topology graph directly
        if fms_instance:
            if hasattr(fms_instance, "graph"):
                # Retain existing registered nodes if any
                for nid, n in wh_graph.nodes.items():
                    fms_instance.graph.nodes[nid] = n
                for src, edge_list in wh_graph.edges.items():
                    fms_instance.graph.edges[src] = edge_list
            if hasattr(fms_instance, "router"):
                fms_instance.router = CBSRouter(fms_instance.graph if hasattr(fms_instance, "graph") else wh_graph)
            if hasattr(fms_instance, "world_model"):
                fms_instance.world_model = unified_world_model

        return {
            "stage": self.current_stage,
            "status": "MAP_ACTIVATED",
            "message": "AutoMap generated digital-twin, Nav2 occupancy, and CBS topology are now active.",
            "operational_status": "READY_FOR_FLEET_MISSIONS"
        }

    def export_representation(self, rep_type: str) -> Dict[str, Any]:
        """Fetches one of the 4 decoupled representations."""
        if not self.generated_outputs:
            self.generate_representations()
        mapping = {
            "3d": "digital_twin_3d",
            "nav2": "nav2_occupancy_2d",
            "semantic": "semantic_map",
            "topology": "topology_graph"
        }
        key = mapping.get(rep_type.lower(), rep_type)
        return self.generated_outputs.get(key, {})


# Global Singleton Service
automap_service = AutoMapService()
