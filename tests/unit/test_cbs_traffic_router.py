import pytest
from fms.topology.warehouse_graph import WarehouseGraph
from fms.traffic.cbs_router import CBSRouter, AgentPlan, ConflictType
from fms.fleet.fleet_manager import FleetManager, RobotAgent, WarehouseOrder


def test_warehouse_graph_topology():
    """Verify graph generation, node counts, and edge connectivity."""
    grid = WarehouseGraph.create_standard_warehouse_grid()
    assert len(grid.nodes) == 16
    # 4 rows * 3 horizontal edges + 4 cols * 3 vertical edges = 24 bidirectional edges = 48 directed
    total_edges = sum(len(e) for e in grid.edges.values())
    assert total_edges == 48

    dist = grid.get_distance("N_0_0", "N_0_3")
    assert dist == 15.0


def test_single_agent_space_time_a_star():
    """Verify optimal shortest path finding in space-time domain without obstacles."""
    grid = WarehouseGraph.create_standard_warehouse_grid()
    router = CBSRouter(grid)

    path = router.space_time_a_star(
        agent_id="synq-1",
        start_node="N_0_0",
        goal_node="N_0_3",
        constraints=set()
    )

    assert path == ["N_0_0", "N_0_1", "N_0_2", "N_0_3"]


def test_cbs_resolves_head_on_collision():
    """
    Verify Conflict-Based Search prevents head-on edge collision and vertex conflict.
    synq-1: N_0_0 -> N_0_2
    synq-2: N_0_2 -> N_0_0
    """
    grid = WarehouseGraph.create_standard_warehouse_grid()
    router = CBSRouter(grid)

    plans = [
        AgentPlan(agent_id="synq-1", start_node="N_0_0", goal_node="N_0_2"),
        AgentPlan(agent_id="synq-2", start_node="N_0_2", goal_node="N_0_0")
    ]

    routes = router.plan(plans)
    assert routes is not None
    assert "synq-1" in routes
    assert "synq-2" in routes

    p1 = routes["synq-1"]
    p2 = routes["synq-2"]

    max_len = max(len(p1), len(p2))
    # Assert zero vertex conflicts at any time step
    for t in range(max_len):
        node1 = p1[min(t, len(p1) - 1)]
        node2 = p2[min(t, len(p2) - 1)]
        assert node1 != node2, f"Vertex collision at node {node1} at timestep t={t}"

    # Assert zero edge swap conflicts
    for t in range(max_len - 1):
        u1 = p1[min(t, len(p1) - 1)]
        v1 = p1[min(t + 1, len(p1) - 1)]
        u2 = p2[min(t, len(p2) - 1)]
        v2 = p2[min(t + 1, len(p2) - 1)]
        assert not (u1 == v2 and v1 == u2 and u1 != v1), f"Edge collision {u1} <-> {v1} at t={t}"


def test_fleet_manager_order_assignment_and_payload_matching():
    """Verify smart order assignment matching payload type and battery threshold."""
    grid = WarehouseGraph.create_standard_warehouse_grid()
    fms = FleetManager(grid)

    # Register 3 robots
    bot1 = RobotAgent(robot_id="AMR-LIFT-1", current_node="N_0_0", battery_pct=90.0, payload_type="SCISSOR_LIFT")
    bot2 = RobotAgent(robot_id="AMR-CONV-1", current_node="N_1_1", battery_pct=85.0, payload_type="ROLLER_CONVEYOR")
    bot3 = RobotAgent(robot_id="AMR-LIFT-LOW", current_node="N_0_1", battery_pct=15.0, payload_type="SCISSOR_LIFT")

    fms.register_robot(bot1)
    fms.register_robot(bot2)
    fms.register_robot(bot3)

    # Order 1: Conveyor transfer
    order_conv = WarehouseOrder(
        order_id="ORD-01",
        pick_node="N_1_2",
        drop_node="N_2_2",
        required_payload="ROLLER_CONVEYOR"
    )
    assigned_bot = fms.submit_order(order_conv)
    assert assigned_bot == "AMR-CONV-1"
    assert bot2.is_busy is True

    # Order 2: Pallet lift (bot3 should be skipped due to <20% battery)
    order_lift = WarehouseOrder(
        order_id="ORD-02",
        pick_node="N_0_2",
        drop_node="N_2_2",
        required_payload="SCISSOR_LIFT"
    )
    assigned_lift = fms.submit_order(order_lift)
    assert assigned_lift == "AMR-LIFT-1"
    assert bot1.is_busy is True
