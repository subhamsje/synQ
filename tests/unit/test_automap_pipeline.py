"""
Unit and Integration Tests for synQ AutoMap Scan-to-Digital-Twin Pipeline
Verifies:
- Sensor abstraction and keyframe recording (/scan, /camera/depth/points, /odom, /tf)
- 3D point cloud accumulation and voxel filtering
- Semantic object detection with human-in-the-loop uncertainty modeling (<0.85 -> Needs Confirmation)
- Generation of 4 strictly decoupled representations:
  1. 3D Digital Twin (Three.js)
  2. 2D Nav2 Occupancy Grid (ROS 2 map_server)
  3. Semantic Warehouse Map (JSON entities)
  4. Navigation Topology Graph (FMS CBS roadmap)
- REST API endpoints and state machine lifecycle
"""

import pytest
from fastapi.testclient import TestClient
from backend.api.app import app
from backend.automap.sensors import SensorDataStream, RobotPose, ScanKeyframe
from backend.automap.reconstruction import PointCloudReconstructor, BoundingBox3D
from backend.automap.semantic_detector import SemanticObjectDetector, SemanticObject
from backend.automap.generator import RepresentationGenerator
from backend.automap.automap_service import AutoMapService


@pytest.fixture
def test_client():
    return TestClient(app)


def test_sensor_stream_and_keyframes():
    stream = SensorDataStream(robot_id="synq-amr-01")
    assert stream.topic_mapping["scan_2d"] == "/synq-amr-01/scan"
    assert stream.topic_mapping["point_cloud"] == "/synq-amr-01/camera/depth/points"

    stream.start_recording()
    pose = RobotPose(x=2.0, y=3.0, yaw=0.0)
    fake_scan = {
        "angle_min": -1.57,
        "angle_increment": 0.05,
        "ranges": [1.5, 2.0, 3.5, 0.05, 50.0],  # Includes valid and out-of-range
        "range_min": 0.1,
        "range_max": 30.0
    }
    stream.ingest_ros2_scan(fake_scan, pose)
    assert len(stream.keyframes) == 1
    kf = stream.keyframes[0]
    assert kf.point_count == 3  # 3 valid ranges
    assert len(kf.points) == 3

    # Generate synthetic scan run
    keyframes = stream.generate_synthetic_scan_run()
    assert len(keyframes) > 10
    assert stream.odometry_history[0].frame_id == "map"


def test_point_cloud_reconstruction():
    stream = SensorDataStream()
    keyframes = stream.generate_synthetic_scan_run()

    reconstructor = PointCloudReconstructor(voxel_size=0.2)
    stats = reconstructor.process_keyframes(keyframes)

    assert stats["total_raw_points"] > 1000
    assert stats["voxel_filtered_points"] > 0
    assert stats["voxel_filtered_points"] <= stats["total_raw_points"]
    assert stats["compression_ratio"] >= 1.0

    clusters = reconstructor.extract_clusters(distance_threshold=0.8, min_cluster_points=4)
    assert len(clusters) > 0
    for c in clusters:
        assert isinstance(c, BoundingBox3D)
        assert c.width > 0.0
        assert c.depth > 0.0
        assert c.height >= 0.0


def test_semantic_detection_and_uncertainty_thresholds():
    detector = SemanticObjectDetector(confidence_threshold=0.85)

    fake_boxes = [
        # Rack profile: tall and long
        BoundingBox3D(
            box_id="b1", cx=4.0, cy=2.5, cz=1.6,
            width=4.5, depth=1.2, height=3.0,
            point_count=35, density=5.0,
            min_point=(1.75, 1.9, 0.1), max_point=(6.25, 3.1, 3.1)
        ),
        # Charger profile: low profile near corner
        BoundingBox3D(
            box_id="b2", cx=0.8, cy=0.8, cz=0.2,
            width=1.0, depth=1.0, height=0.4,
            point_count=20, density=8.0,
            min_point=(0.3, 0.3, 0.0), max_point=(1.3, 1.3, 0.4)
        ),
        # Ambiguous obstacle in aisle
        BoundingBox3D(
            box_id="b3", cx=7.5, cy=5.0, cz=0.4,
            width=0.8, depth=0.8, height=0.7,
            point_count=8, density=3.0,
            min_point=(7.1, 4.6, 0.1), max_point=(7.9, 5.4, 0.8)
        )
    ]

    bounds = {"min_x": 0.0, "max_x": 15.0, "min_y": 0.0, "max_y": 15.0}
    detections = detector.detect_objects(fake_boxes, bounds)

    # Verify types detected
    types = [d.semantic_type for d in detections]
    assert "rack" in types
    assert "charger" in types
    assert "obstacle" in types
    assert "restricted_zone" in types

    # Verify uncertainty handling: obstacle must be flagged NEEDS_CONFIRMATION
    obs = next(d for d in detections if d.semantic_type == "obstacle")
    assert obs.needs_confirmation is True
    assert obs.status == "NEEDS_CONFIRMATION"
    assert obs.confidence < 0.85
    assert obs.confirmation_reason is not None

    # Charger should be auto-proposed with high confidence
    chg = next(d for d in detections if d.semantic_type == "charger")
    assert chg.needs_confirmation is False
    assert chg.confidence >= 0.85


def test_representation_generator_decoupling():
    gen = RepresentationGenerator(facility_width=15.0, facility_height=15.0)

    sample_objects = [
        SemanticObject(
            id="RACK-A", semantic_type="rack", label="Rack Bay A",
            confidence=0.92, needs_confirmation=False, confirmation_reason=None,
            status="CONFIRMED",
            bounding_box={"center": {"x": 4.0, "y": 2.5, "z": 1.5}, "dimensions": {"width": 4.5, "depth": 1.2, "height": 3.0}}
        ),
        SemanticObject(
            id="CHG-01", semantic_type="charger", label="Charging Dock C1",
            confidence=0.95, needs_confirmation=False, confirmation_reason=None,
            status="CONFIRMED",
            bounding_box={"center": {"x": 0.8, "y": 0.8, "z": 0.2}, "dimensions": {"width": 1.0, "depth": 1.0, "height": 0.4}}
        )
    ]

    # 1. 3D Digital Twin
    twin_3d = gen.generate_3d_digital_twin(sample_objects)
    assert twin_3d["metadata"]["format"] == "synq-3d-digital-twin-v1"
    assert len(twin_3d["meshes"]) == 2
    assert len(twin_3d["perimeter_walls"]) == 4

    # 2. 2D Nav2 Occupancy Grid
    nav2 = gen.generate_2d_nav2_occupancy_grid(sample_objects, resolution=0.05)
    assert nav2["format"] == "nav2_costmap_2d"
    assert nav2["resolution"] == 0.05
    assert "image: synq_warehouse_occupancy.pgm" in nav2["yaml_spec"]
    assert len(nav2["occupied_regions"]) > 0

    # 3. Semantic Map
    sem = gen.generate_semantic_warehouse_map(sample_objects)
    assert len(sem["racks"]) == 1
    assert len(sem["charging_points"]) == 1

    # 4. Navigation Topology Graph
    topo = gen.generate_navigation_graph(sample_objects)
    assert topo["total_nodes"] == 16
    assert topo["total_edges"] == 24
    assert len(topo["edges"]) == 24


def test_automap_service_workflow():
    service = AutoMapService()
    assert service.current_stage == "IDLE"

    # Stage 1 & 2: Start Scan
    start_res = service.start_session(robot_id="synq-amr-01")
    assert start_res["stage"] == "MAPPING"
    assert start_res["keyframes_recorded"] > 0

    # Stage 3 & 4: Reconstruction & Detection
    recon_res = service.run_reconstruction_and_detection()
    assert recon_res["stage"] == "REVIEW_LABEL"
    assert recon_res["total_detected"] > 0
    assert recon_res["needs_confirmation_count"] > 0

    # Stage 5: Operator confirmation & update
    first_det = recon_res["detections"][0]
    updated = service.update_detection(
        object_id=first_det["id"],
        status="CONFIRMED"
    )
    assert updated["status"] == "CONFIRMED"
    assert updated["needs_confirmation"] is False

    # Confirm all
    confirmed_count = service.confirm_all_detections()
    assert confirmed_count >= len(service.detections) - 1

    # Stage 6: Generate Representations
    gen_res = service.generate_representations()
    assert gen_res["stage"] == "MAP_GENERATED"
    assert len(gen_res["generated_artifacts"]) == 4

    # Stage 7: Activate in FMS
    act_res = service.activate_in_fms()
    assert act_res["stage"] == "READY_FOR_AUTONOMOUS_OPERATION"
    assert act_res["status"] == "MAP_ACTIVATED"
    assert service.is_active_in_fms is True


def test_automap_api_endpoints(test_client):
    # Test session start
    r1 = test_client.post("/api/v1/automap/session/start", json={"robot_id": "synq-amr-01", "profile": "standard_hub"})
    assert r1.status_code == 200
    data1 = r1.json()
    assert data1["stage"] == "MAPPING"

    # Test status
    r2 = test_client.get("/api/v1/automap/session/status")
    assert r2.status_code == 200
    assert r2.json()["keyframes"] > 0

    # Test reconstruction
    r3 = test_client.post("/api/v1/automap/reconstruct")
    assert r3.status_code == 200
    data3 = r3.json()
    assert data3["stage"] == "REVIEW_LABEL"
    assert "detections" in data3
    assert len(data3["detections"]) > 0

    # Test update detection
    target_id = data3["detections"][0]["id"]
    r4 = test_client.post("/api/v1/automap/detections/update", json={
        "object_id": target_id,
        "status": "CONFIRMED"
    })
    assert r4.status_code == 200
    assert r4.json()["status"] == "CONFIRMED"

    # Test confirm all
    r5 = test_client.post("/api/v1/automap/detections/confirm-all")
    assert r5.status_code == 200
    assert r5.json()["status"] == "SUCCESS"

    # Test generate
    r6 = test_client.post("/api/v1/automap/generate")
    assert r6.status_code == 200
    assert r6.json()["stage"] == "MAP_GENERATED"

    # Test activate
    r7 = test_client.post("/api/v1/automap/activate")
    assert r7.status_code == 200
    assert r7.json()["status"] == "MAP_ACTIVATED"

    # Test export endpoints
    for rep in ["3d", "nav2", "semantic", "topology"]:
        r_exp = test_client.get(f"/api/v1/automap/export/{rep}")
        assert r_exp.status_code == 200
