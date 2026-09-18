from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from fms.topology.warehouse_graph import WarehouseGraph
from fms.traffic.cbs_router import CBSRouter, AgentPlan


@dataclass
class RobotAgent:
    robot_id: str
    current_node: str
    battery_pct: float = 100.0
    payload_type: str = "BASE"  # "BASE", "SCISSOR_LIFT", "ROLLER_CONVEYOR", "TOTE_GRIPPER"
    is_busy: bool = False
    current_mission_id: Optional[str] = None
    planned_trajectory: List[str] = field(default_factory=list)


@dataclass
class WarehouseOrder:
    order_id: str
    pick_node: str
    drop_node: str
    required_payload: str = "ANY"  # "SCISSOR_LIFT", "ROLLER_CONVEYOR", "TOTE_GRIPPER", "ANY"
    priority: int = 1


class FleetManager:
    """
    synQ Fleet Management System (FMS) Coordinator.
    Allocates warehouse orders to suitable AMRs and orchestrates
    multi-robot Conflict-Based Search routing.
    """

    def __init__(self, graph: WarehouseGraph):
        self.graph = graph
        self.router = CBSRouter(graph)
        self.robots: Dict[str, RobotAgent] = {}
        self.active_orders: Dict[str, WarehouseOrder] = {}

    def register_robot(self, robot: RobotAgent):
        self.robots[robot.robot_id] = robot

    def submit_order(self, order: WarehouseOrder) -> Optional[str]:
        """
        Assigns order to the best matching idle robot.
        Returns robot_id if assigned, or None if queued/no matching robot.
        """
        candidates = []
        for rid, bot in self.robots.items():
            if bot.is_busy or bot.battery_pct < 20.0:
                continue
            # Check payload compatibility
            if order.required_payload != "ANY" and bot.payload_type != order.required_payload:
                continue

            dist = self.graph.get_distance(bot.current_node, order.pick_node)
            candidates.append((dist, rid))

        if not candidates:
            return None

        # Select closest robot
        candidates.sort()
        best_robot_id = candidates[0][1]
        robot = self.robots[best_robot_id]
        
        robot.is_busy = True
        robot.current_mission_id = order.order_id
        self.active_orders[order.order_id] = order
        return best_robot_id

    def coordinate_trajectories(self, plans: List[AgentPlan]) -> Optional[Dict[str, List[str]]]:
        """Executes multi-agent CBS routing for all active AMR movements."""
        routes = self.router.plan(plans)
        if routes:
            for aid, path in routes.items():
                if aid in self.robots:
                    self.robots[aid].planned_trajectory = path
        return routes
