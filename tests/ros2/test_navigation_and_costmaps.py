import os
import sys
import yaml
import xml.etree.ElementTree as ET
import pytest

# Ensure ros2_ws packages can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../ros2_ws/src/synq_navigation')))
from synq_navigation.costmap_manager import CostmapManager


CONFIG_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../ros2_ws/src/synq_navigation/config/nav2_params.yaml')
)
BT_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../ros2_ws/src/synq_navigation/behavior_trees/synq_navigate_w_replanning_and_recovery.xml')
)


def test_nav2_params_yaml_validity_and_holonomic_kinematics():
    """Verify that nav2_params.yaml parses cleanly and strictly enforces holonomic MPPI limits."""
    assert os.path.exists(CONFIG_PATH), f"Config file not found at {CONFIG_PATH}"
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)

    assert "controller_server" in config
    assert "planner_server" in config
    assert "global_costmap" in config
    assert "local_costmap" in config

    controller_params = config["controller_server"]["ros__parameters"]
    follow_path_params = controller_params["FollowPath"]

    # Holonomic kinematics assertions
    assert follow_path_params["motion_model"] == "Omni", "MPPI controller must be configured for Omni (Mecanum) motion"
    assert follow_path_params["vy_max"] > 0.0, "Lateral vy_max must be positive for Mecanum strafing"
    assert follow_path_params["vy_min"] < 0.0, "Lateral vy_min must be negative for Mecanum strafing"
    assert follow_path_params["vx_max"] > 0.0
    assert follow_path_params["wz_max"] > 0.0

    # Smac Planner assertions
    planner_params = config["planner_server"]["ros__parameters"]
    assert "GridBased" in planner_params["planner_plugins"]
    assert planner_params["GridBased"]["plugin"] == "nav2_smac_planner/SmacPlanner2D"

    # Costmap inflation checks
    local_costmap_params = config["local_costmap"]["local_costmap"]["ros__parameters"]
    assert local_costmap_params["rolling_window"] is True
    assert local_costmap_params["inflation_layer"]["inflation_radius"] >= 0.50


def test_behavior_tree_xml_structure():
    """Verify that the Behavior Tree XML is well-formed and contains key recovery primitives."""
    assert os.path.exists(BT_PATH), f"BT XML not found at {BT_PATH}"
    tree = ET.parse(BT_PATH)
    root = tree.getroot()

    assert root.tag == "root"
    main_tree = root.find("BehaviorTree")
    assert main_tree is not None
    assert main_tree.get("ID") == "MainTree"

    # Find recovery node and pipeline sequence
    recovery_node = main_tree.find(".//RecoveryNode")
    assert recovery_node is not None
    assert int(recovery_node.get("number_of_retries", "0")) >= 3

    # Ensure compute path and follow path are present
    compute_path = main_tree.find(".//ComputePathToPose")
    follow_path = main_tree.find(".//FollowPath")
    assert compute_path is not None
    assert follow_path is not None

    # Ensure recovery actions exist
    clear_costmap = main_tree.find(".//ClearEntireCostmap")
    spin_node = main_tree.find(".//Spin")
    backup_node = main_tree.find(".//BackUp")
    assert clear_costmap is not None
    assert spin_node is not None
    assert backup_node is not None


def test_costmap_manager_inscribed_and_circumscribed_radii():
    """Verify geometry calculations for the 0.70m x 0.50m synQ chassis."""
    base_footprint = CostmapManager.BASE_FOOTPRINT
    inscribed = CostmapManager.compute_inscribed_radius(base_footprint)
    circumscribed = CostmapManager.compute_circumscribed_radius(base_footprint)

    # Inscribed radius is half-width = 0.25m
    assert pytest.approx(inscribed, rel=1e-3) == 0.25
    # Circumscribed radius is sqrt(0.35^2 + 0.25^2) = sqrt(0.1225 + 0.0625) = sqrt(0.185) ≈ 0.4301
    assert pytest.approx(circumscribed, rel=1e-3) == 0.4301


def test_costmap_manager_inflation_decay_profile():
    """Verify the exponential decay of inflation costs outside the inscribed radius."""
    inscribed_r = 0.25
    inflation_r = 0.65
    cost_scaling = 3.0

    # Within or at inscribed radius -> lethal cost (254)
    assert CostmapManager.compute_inflation_cost(0.10, inscribed_r, inflation_r, cost_scaling) == 254
    assert CostmapManager.compute_inflation_cost(0.25, inscribed_r, inflation_r, cost_scaling) == 254

    # Monotonic decreasing check in inflation zone
    cost_1 = CostmapManager.compute_inflation_cost(0.30, inscribed_r, inflation_r, cost_scaling)
    cost_2 = CostmapManager.compute_inflation_cost(0.40, inscribed_r, inflation_r, cost_scaling)
    cost_3 = CostmapManager.compute_inflation_cost(0.55, inscribed_r, inflation_r, cost_scaling)

    assert 254 > cost_1 > cost_2 > cost_3 > 0

    # Outside inflation radius -> free space (0)
    assert CostmapManager.compute_inflation_cost(0.66, inscribed_r, inflation_r, cost_scaling) == 0
    assert CostmapManager.compute_inflation_cost(1.00, inscribed_r, inflation_r, cost_scaling) == 0


def test_modular_payload_footprint_scaling():
    """Verify that modular payloads dynamically update footprint specifications."""
    base_specs = CostmapManager.get_specs_for_payload("BASE")
    lift_specs = CostmapManager.get_specs_for_payload("SCISSOR_LIFT")
    conveyor_specs = CostmapManager.get_specs_for_payload("ROLLER_CONVEYOR")
    gripper_specs = CostmapManager.get_specs_for_payload("TOTE_GRIPPER")

    assert lift_specs["circumscribed_radius"] > base_specs["circumscribed_radius"]
    assert conveyor_specs["circumscribed_radius"] > base_specs["circumscribed_radius"]
    assert gripper_specs["circumscribed_radius"] > base_specs["circumscribed_radius"]

    # Verify footprint string format
    assert base_specs["footprint_str"].startswith("[[0.35, 0.25]")
