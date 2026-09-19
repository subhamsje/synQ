"""
Unit and Integration Tests for synQ Open-Source Robotics Stack & Autonomy Layer
Verifies:
1. Point cloud downsampling, RANSAC planar segmentation, and bounding box extraction
2. Semantic entity classification, capability tagging, and operator confirmation
3. Dynamic Voronoi corridor topology generation (NO hardcoded grids)
4. Unified World Model 4-representation synchronization
5. FMS semantic order resolution, capability matching, and battery-aware charging dispatch
6. Multi-robot CBS routing over dynamically generated topologies
7. ROS 2 telemetry synchronization and VDA 5050 message contracts
"""

import pytest
import math
from backend.automap.sensors import SensorDataStream, ScanKeyframe, RobotPose
from backend.automap.reconstruction import PointCloudReconstructor, BoundingBox3D
from backend.automap.semantic_detector import SemanticObjectDetector, SemanticObject
from backend.automap.topology_generator import AutomaticTopologyGenerator
from backend.automap.generator import RepresentationGenerator
from backend.automap.world_model import UnifiedWorldModel, unified_world_model
from fms.fleet.fleet_manager import FleetManager, RobotAgent, WarehouseOrder
from fms.traffic.cbs_router import CBSRouter, AgentPlan
from fms.adapters.ros2_adapter import ROS2RobotAdapter
from fms.models.domain_models import PayloadType, RobotStatus
from fms.vda5050.vda5050_serializer import VDA5050Serializer, VDA5050Order


class TestRoboticsStackIntegration:

    @pytest.fixture
    def setup_pipeline(self):
        sensor_stream = SensorDataStream()
        keyframes = sensor_stream.generate_synthetic_scan_run(facility_profile="standard_hub")
        reconstructor = PointCloudReconstructor(voxel_size=0.20)
        detector = SemanticObjectDetector(confidence_threshold=0.85)
        generator = RepresentationGenerator(facility_width=15.0, facility_height=15.0)
        return {
            "stream": sensor_stream,
            "keyframes": keyframes,
            "reconstructor": reconstructor,
            "detector": detector,
            "generator": generator
        }

    def test_point_cloud_reconstruction_and_ransac(self, setup_pipeline):
        """Verifies voxel downsampling, RANSAC ground plane isolation, and clustering."""
        p = setup_pipeline
        stats = p["reconstructor"].process_keyframes(p["keyframes"])
        assert stats["total_raw_points"] > 500
        assert stats["voxel_filtered_points"] > 0
        assert stats["compression_ratio"] >= 1.0
        assert stats["bounds"]["max_x"] > stats["bounds"]["min_x"]

        # Verify ground plane segmentation occurred
        assert len(p["reconstructor"].ground_inliers) > 0
        assert len(p["reconstructor"].non_ground_points) > 0

        # Cluster extraction
        boxes = p["reconstructor"].extract_clusters()
        assert len(boxes) >= 4
        for box in boxes:
            assert isinstance(box, BoundingBox3D)
            assert box.width > 0 and box.depth > 0 and box.height > 0
            assert box.density > 0

    def test_semantic_detection_capabilities_and_confirmation(self, setup_pipeline):
        """Verifies semantic classification, capability tagging, and uncertainty gating."""
        p = setup_pipeline
        p["reconstructor"].process_keyframes(p["keyframes"])
        boxes = p["reconstructor"].extract_clusters()
        objects = p["detector"].detect_objects(boxes, p["reconstructor"].facility_bounds)

        assert len(objects) >= 5
        types = set(obj.semantic_type for obj in objects)
        assert "rack" in types
        assert "charger" in types
        assert "conveyor" in types or "pick_station" in types

        # Verify rich capabilities and clearance
        for obj in objects:
            assert isinstance(obj.capabilities, list)
            assert obj.clearance_envelope_m > 0
            if obj.semantic_type == "charger":
                assert "FAST_CHARGE_60KW" in obj.capabilities
                assert obj.docking_vector is not None

        # Verify uncertainty modeling
        unconfirmed = [o for o in objects if o.needs_confirmation]
        assert len(unconfirmed) >= 1  # Obstacle or restricted zone flagged
        for u in unconfirmed:
            assert u.confidence < 0.85
            assert u.confirmation_reason is not None

    def test_automatic_navigation_topology_generation(self, setup_pipeline):
        """Verifies that navigation topology is dynamically derived rather than hardcoded."""
        p = setup_pipeline
        p["reconstructor"].process_keyframes(p["keyframes"])
        boxes = p["reconstructor"].extract_clusters()
        objects = p["detector"].detect_objects(boxes, p["reconstructor"].facility_bounds)

        topo_gen = AutomaticTopologyGenerator(facility_width=15.0, facility_height=15.0)
        topo_data = topo_gen.generate_topology(objects)

        assert topo_data["total_nodes"] > 0
        assert topo_data["total_edges"] > 0
        assert topo_data["generation_method"] == "voronoi_corridor_extraction"

        node_types = set(n["node_type"] for n in topo_data["nodes"])
        assert "TRANSIT" in node_types
        assert "PICK" in node_types or "CHARGE" in node_types

        # Verify entity approach nodes were created
        entity_ref_nodes = [n for n in topo_data["nodes"] if "entity_ref" in n]
        assert len(entity_ref_nodes) >= 2

        # Verify graph build
        graph = topo_gen.build_warehouse_graph(objects)
        assert len(graph.nodes) == topo_data["total_nodes"]
        assert len(graph.edges) > 0

    def test_unified_world_model_synchronization(self, setup_pipeline):
        """Verifies that all 4 operational representations are synchronized atomically."""
        p = setup_pipeline
        p["reconstructor"].process_keyframes(p["keyframes"])
        boxes = p["reconstructor"].extract_clusters()
        objects = p["detector"].detect_objects(boxes, p["reconstructor"].facility_bounds)

        # Confirm all objects
        for obj in objects:
            obj.status = "CONFIRMED"
            obj.needs_confirmation = False

        dt_3d = p["generator"].generate_3d_digital_twin(objects)
        nav2 = p["generator"].generate_2d_nav2_occupancy_grid(objects)
        sem_map = p["generator"].generate_semantic_warehouse_map(objects)
        topo = p["generator"].generate_navigation_graph(objects)
        wh_graph = p["generator"].topology_engine.build_warehouse_graph(objects)

        wm = UnifiedWorldModel(facility_id="TEST-FAC-01")
        wm.update_world_model(
            digital_twin_3d=dt_3d,
            nav2_occupancy_2d=nav2,
            semantic_map=sem_map,
            topology_graph=topo,
            confirmed_objects=objects,
            warehouse_graph=wh_graph
        )

        summary = wm.get_summary()
        assert summary["representations"]["digital_twin_3d"] is True
        assert summary["representations"]["nav2_occupancy_2d"] is True
        assert summary["representations"]["semantic_scene_graph"] is True
        assert summary["representations"]["topology_graph"] is True
        assert summary["indexed_entities_count"] > 0

        # Verify resolution of semantic entity to approach node
        first_obj = objects[0]
        resolved_node = wm.resolve_entity_approach(first_obj.id)
        assert resolved_node is not None

        # Verify nearest charging dock lookup
        nearest_charger = wm.find_nearest_charging_dock(1.0, 1.0)
        assert nearest_charger is not None

        # Verify capability query
        charge_entities = wm.get_entities_by_capability("FAST_CHARGE_60KW")
        assert len(charge_entities) >= 1

    def test_fms_semantic_order_dispatch_and_cbs_routing(self, setup_pipeline):
        """Verifies FMS task allocation with semantic entity targets, capability matching, and CBS routing."""
        p = setup_pipeline
        p["reconstructor"].process_keyframes(p["keyframes"])
        boxes = p["reconstructor"].extract_clusters()
        objects = p["detector"].detect_objects(boxes, p["reconstructor"].facility_bounds)

        for obj in objects:
            obj.status = "CONFIRMED"
            obj.needs_confirmation = False

        # Generate world model
        topo_data = p["generator"].generate_navigation_graph(objects)
        wh_graph = p["generator"].topology_engine.build_warehouse_graph(objects)
        wm = UnifiedWorldModel()
        wm.update_world_model(
            digital_twin_3d={},
            nav2_occupancy_2d={},
            semantic_map={},
            topology_graph=topo_data,
            confirmed_objects=objects,
            warehouse_graph=wh_graph
        )

        # Initialize FMS with dynamic graph and world model
        fms = FleetManager(graph=wh_graph, world_model=wm)

        # Get two valid nodes from the generated graph
        node_ids = list(wh_graph.nodes.keys())
        assert len(node_ids) >= 2
        start_node, end_node = node_ids[0], node_ids[-1]

        # Register AMRs with different capabilities
        bot1 = RobotAgent(robot_id="AMR-ALPHA", current_node=start_node, battery_pct=95.0, payload_type="SCISSOR_LIFT")
        bot2 = RobotAgent(robot_id="AMR-BETA", current_node=end_node, battery_pct=85.0, payload_type="ROLLER_CONVEYOR")
        fms.register_robot(bot1)
        fms.register_robot(bot2)

        # 1. Order with semantic entity target
        rack_obj = next((o for o in objects if o.semantic_type == "rack"), None)
        assert rack_obj is not None

        order = WarehouseOrder(
            order_id="ORD-SEM-01",
            pick_node="",
            drop_node=end_node,
            pick_entity=rack_obj.id,
            required_payload="SCISSOR_LIFT"
        )

        assigned_robot = fms.submit_order(order)
        assert assigned_robot == "AMR-ALPHA"
        assert order.pick_node == rack_obj.approach_node_id

        # 2. Multi-AMR CBS conflict resolution over dynamic graph
        plan1 = AgentPlan(agent_id="AMR-ALPHA", start_node=start_node, goal_node=end_node)
        plan2 = AgentPlan(agent_id="AMR-BETA", start_node=end_node, goal_node=start_node)
        routes = fms.coordinate_trajectories([plan1, plan2])
        assert routes is not None
        assert "AMR-ALPHA" in routes
        assert "AMR-BETA" in routes

    def test_battery_aware_preemptive_charging_dispatch(self, setup_pipeline):
        """Verifies that low-battery AMRs (<20%) are automatically rerouted to charging docks."""
        p = setup_pipeline
        p["reconstructor"].process_keyframes(p["keyframes"])
        boxes = p["reconstructor"].extract_clusters()
        objects = p["detector"].detect_objects(boxes, p["reconstructor"].facility_bounds)

        wh_graph = p["generator"].topology_engine.build_warehouse_graph(objects)
        topo_data = p["generator"].generate_navigation_graph(objects)
        wm = UnifiedWorldModel()
        wm.update_world_model({}, {}, {}, topo_data, objects, wh_graph)

        fms = FleetManager(graph=wh_graph, world_model=wm)
        start_node = list(wh_graph.nodes.keys())[0]

        # Register robot with critical battery (14%)
        crit_bot = RobotAgent(robot_id="AMR-LOW-BATT", current_node=start_node, battery_pct=14.0)
        fms.register_robot(crit_bot)

        route = fms.dispatch_charging_if_needed("AMR-LOW-BATT")
        assert route is not None
        assert len(route) >= 1
        assert "CHARGE" in crit_bot.current_mission_id

    def test_ros2_adapter_and_vda5050_telemetry_sync(self):
        """Verifies ROS 2 adapter telemetry synchronization and VDA 5050 order generation."""
        adapter = ROS2RobotAdapter(robot_id="synq-amr-test", payload_type=PayloadType.SCISSOR_LIFT)

        # Ingest simulated ROS 2 topics
        telemetry = {
            "position": {"x": 4.5, "y": 7.2, "theta": 1.57},
            "velocity": {"vx": 0.8, "vy": 0.0, "omega": 0.1},
            "battery_pct": 89.5,
            "current_node": "WAYPOINT_X45_Y72",
            "safety_estop": False,
            "status": "NAVIGATING"
        }
        adapter.update_telemetry(telemetry)

        assert adapter.robot.position["x"] == 4.5
        assert adapter.robot.velocity["vx"] == 0.8
        assert adapter.robot.battery_pct == 89.5
        assert adapter.robot.status == RobotStatus.NAVIGATING

        # VDA 5050 serialization check
        vda_order = VDA5050Serializer.create_order_from_nodes(
            order_id="ORD-VDA-TEST",
            order_update_id=1,
            node_ids=["WAYPOINT_X45_Y72", "NODE_RACK_A"]
        )
        assert vda_order.orderId == "ORD-VDA-TEST"
        assert len(vda_order.nodes) == 2
        assert len(vda_order.edges) == 1
