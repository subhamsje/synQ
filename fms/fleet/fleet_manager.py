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
    pick_entity: Optional[str] = None
    drop_entity: Optional[str] = None


class FleetManager:
    """
    synQ Fleet Management System (FMS) Coordinator.
    Allocates warehouse orders to suitable AMRs, resolves semantic entities
    from the Unified World Model, monitors battery/energy state, and orchestrates
    multi-robot Conflict-Based Search routing.
    """

    def __init__(self, graph: WarehouseGraph, world_model: Optional[Any] = None):
        self.graph = graph
        self.router = CBSRouter(graph)
        self.robots: Dict[str, RobotAgent] = {}
        self.active_orders: Dict[str, WarehouseOrder] = {}
        self.world_model = world_model

    def register_robot(self, robot: RobotAgent):
        self.robots[robot.robot_id] = robot

    def submit_order(self, order: WarehouseOrder) -> Optional[str]:
        """
        Assigns order to the best matching idle robot.
        Resolves semantic entity IDs to topological approach nodes via World Model.
        Returns robot_id if assigned, or None if queued/no matching robot.
        """
        # Resolve semantic entity targets if present
        if self.world_model:
            if order.pick_entity:
                order.pick_node = self.world_model.resolve_entity_approach(order.pick_entity)
            elif order.pick_node:
                order.pick_node = self.world_model.resolve_entity_approach(order.pick_node)

            if order.drop_entity:
                order.drop_node = self.world_model.resolve_entity_approach(order.drop_entity)
            elif order.drop_node:
                order.drop_node = self.world_model.resolve_entity_approach(order.drop_node)

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

    def dispatch_charging_if_needed(self, robot_id: str) -> Optional[List[str]]:
        """
        Energy-aware dispatch: If robot battery is below 20%, preemptively
        routes the unit to the nearest available charging dock.
        """
        bot = self.robots.get(robot_id)
        if not bot or bot.battery_pct >= 20.0 or (bot.current_mission_id and "CHARGE" in bot.current_mission_id):
            return None

        # Find nearest charge node
        charge_node = None
        if self.world_model and hasattr(self.world_model, "charger_nodes") and self.world_model.charger_nodes:
            charge_node = self.world_model.charger_nodes[0]
        else:
            for nid, node in self.graph.nodes.items():
                if getattr(node, "node_type", "") == "CHARGE":
                    charge_node = nid
                    break

        if not charge_node:
            return None

        # Compute collision-free path to charging station
        route = self.router.space_time_a_star(
            agent_id=robot_id,
            start_node=bot.current_node,
            goal_node=charge_node,
            constraints=set()
        )
        if route:
            bot.planned_trajectory = route
            bot.current_mission_id = f"CHARGE-{robot_id}"
            bot.is_busy = True
            return route
        return None

    def coordinate_trajectories(self, plans: List[AgentPlan]) -> Optional[Dict[str, List[str]]]:
        """Executes multi-agent CBS routing for all active AMR movements."""
        routes = self.router.plan(plans)
        if routes:
            for aid, path in routes.items():
                if aid in self.robots:
                    self.robots[aid].planned_trajectory = path
        return routes

    def evaluate_dispatch_decision(self, order: WarehouseOrder) -> Dict[str, Any]:
        """
        Evaluates task assignment decision factors across all fleet candidates.
        Produces a complete decision trace with rejected alternatives and rationale.
        """
        candidates_evaluation = []
        eligible = []

        for rid, bot in self.robots.items():
            dist = self.graph.get_distance(bot.current_node, order.pick_node)
            payload_ok = (order.required_payload == "ANY" or bot.payload_type == order.required_payload)
            batt_ok = (bot.battery_pct >= 20.0)
            avail_ok = (not bot.is_busy)

            rejection_reasons = []
            if not avail_ok:
                rejection_reasons.append(f"Unit busy executing task {bot.current_mission_id or 'UNKNOWN'}")
            if not batt_ok:
                rejection_reasons.append(f"Battery level ({bot.battery_pct:.1f}%) below minimum 20% dispatch threshold")
            if not payload_ok:
                rejection_reasons.append(f"Payload mismatch: Equipped with {bot.payload_type}, requires {order.required_payload}")

            # Cost calculation: distance + battery penalty if < 40%
            battery_penalty = max(0.0, (40.0 - bot.battery_pct) * 0.1)
            cost_score = round(dist + battery_penalty, 2)

            is_eligible = avail_ok and batt_ok and payload_ok
            eval_entry = {
                "robot_id": rid,
                "current_node": bot.current_node,
                "payload_type": bot.payload_type,
                "payload_match": payload_ok,
                "battery_pct": bot.battery_pct,
                "battery_sufficient": batt_ok,
                "is_busy": bot.is_busy,
                "distance_to_pickup_m": round(dist, 2),
                "cost_score": cost_score,
                "is_eligible": is_eligible,
                "decision": "PENDING",
                "rejection_reason": "; ".join(rejection_reasons) if rejection_reasons else None
            }
            candidates_evaluation.append(eval_entry)
            if is_eligible:
                eligible.append((cost_score, dist, rid, eval_entry))

        selected_id = None
        rationale = ""

        if eligible:
            eligible.sort()
            winner_entry = eligible[0][3]
            winner_entry["decision"] = "SELECTED"
            selected_id = winner_entry["robot_id"]

            for _, _, rid, entry in eligible[1:]:
                entry["decision"] = "REJECTED"
                entry["rejection_reason"] = f"Higher transit cost score ({entry['cost_score']} vs {winner_entry['cost_score']})"

            for entry in candidates_evaluation:
                if entry["decision"] == "PENDING":
                    entry["decision"] = "REJECTED"

            rationale = (
                f"Assigned {selected_id}: Optimal composite cost score ({winner_entry['cost_score']}) "
                f"with {winner_entry['distance_to_pickup_m']}m transit distance and matching {winner_entry['payload_type']} payload."
            )
        else:
            for entry in candidates_evaluation:
                entry["decision"] = "REJECTED"
            rationale = "No available AMR satisfied physical payload and battery operational constraints."

        return {
            "order_id": order.order_id,
            "pick_node": order.pick_node,
            "drop_node": order.drop_node,
            "required_payload": order.required_payload,
            "selected_robot": selected_id,
            "candidates": candidates_evaluation,
            "decision_rationale": rationale,
            "constraints": [
                f"Payload must match {order.required_payload}",
                "Battery must exceed 20.0% dispatch cutoff",
                "Unit must not have concurrent active task assignment"
            ]
        }

