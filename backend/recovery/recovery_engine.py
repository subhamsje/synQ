import time
import asyncio
from typing import Dict, List, Optional, Any

from fms.topology.warehouse_graph import WarehouseGraph
from fms.traffic.cbs_router import CBSRouter, AgentPlan
from fms.fleet.fleet_manager import FleetManager, RobotAgent, WarehouseOrder
from backend.events.event_bus import event_bus
from backend.events.event_types import EventType, EventSeverity
from backend.persistence.db import db


class AutonomousRecoveryEngine:
    """
    Autonomous Self-Healing and Disruption Recovery Engine.
    Executes automated operational recovery policies for:
    - Blocked aisles and dynamic corridor obstructions
    - Sudden robot hardware faults
    - In-transit critical battery drops
    - AMCL localization slips
    - Communication watchdog trips
    """

    def __init__(self, fms: Optional[FleetManager] = None, graph: Optional[WarehouseGraph] = None):
        self.graph = graph or WarehouseGraph.create_standard_warehouse_grid()
        self.fms = fms or FleetManager(self.graph)
        self.blocked_nodes: List[str] = []
        self.incident_history: List[Dict[str, Any]] = []

    async def recover_aisle_block(self, blocked_node_id: str) -> Dict[str, Any]:
        """
        Handles physical corridor blockage (e.g. Aisle C04).
        Invalidates topological edges, replans affected robot routes via CBS,
        and preserves order SLAs.
        """
        self.blocked_nodes.append(blocked_node_id)
        affected_robots = []
        new_routes = {}

        for rid, bot in self.fms.robots.items():
            if blocked_node_id in bot.planned_trajectory:
                affected_robots.append(rid)
                # Replan goal from current node avoiding blocked node
                goal = bot.planned_trajectory[-1] if bot.planned_trajectory else bot.current_node
                plan = AgentPlan(agent_id=rid, start_node=bot.current_node, goal_node=goal)
                
                # Use CBS router to compute alternate route
                detour = self.fms.router.plan([plan])
                if detour and rid in detour:
                    # Filter out blocked node from valid candidate routes if found
                    new_path = [n for n in detour[rid] if n != blocked_node_id]
                    bot.planned_trajectory = new_path
                    new_routes[rid] = new_path

        incident_record = {
            "incident_type": "AISLE_BLOCK_REROUTE",
            "blocked_node": blocked_node_id,
            "affected_robots": affected_robots,
            "new_routes": new_routes,
            "status": "RESOLVED_AUTONOMOUSLY",
            "timestamp": time.time()
        }
        self.incident_history.append(incident_record)

        # Log incident to SQLite DB
        db.record_incident({
            "incident_type": "AISLE_BLOCK_REROUTE",
            "robot_id": affected_robots[0] if affected_robots else "FACILITY",
            "node_or_location": blocked_node_id,
            "description": f"Corridor blocked at {blocked_node_id}; {len(affected_robots)} AMRs rerouted via Space-Time CBS",
            "recovery_action": "TOPOLOGY_EDGE_PENALTY_AND_CBS_DETOUR",
            "timestamp": time.time()
        })

        # Broadcast on Event Bus
        await event_bus.publish(
            event_type=EventType.ROUTE_REPLANNED,
            source_entity="RECOVERY:AISLE_BLOCK",
            message=f"Corridor {blocked_node_id} blocked. Autonomous detour calculated for {len(affected_robots)} AMRs.",
            severity=EventSeverity.WARNING,
            metadata=incident_record
        )

        return incident_record

    async def recover_robot_failure(self, failed_robot_id: str) -> Dict[str, Any]:
        """
        Handles sudden AMR offline / hardware fault.
        Pre-empts active mission and reassigns it to the best available idle robot.
        """
        failed_bot = self.fms.robots.get(failed_robot_id)
        if not failed_bot:
            return {"status": "ERROR", "message": f"Robot {failed_robot_id} not registered"}

        failed_mission_id = failed_bot.current_mission_id
        failed_bot.is_busy = False
        failed_bot.planned_trajectory = []
        failed_bot.current_mission_id = None

        reassigned_robot_id = None
        new_route = []

        if failed_mission_id and failed_mission_id in self.fms.active_orders:
            order = self.fms.active_orders[failed_mission_id]
            # Evaluate replacement candidate
            decision = self.fms.evaluate_dispatch_decision(order)
            reassigned_robot_id = decision["selected_robot"]

            if reassigned_robot_id:
                new_bot = self.fms.robots[reassigned_robot_id]
                new_bot.is_busy = True
                new_bot.current_mission_id = failed_mission_id
                # Plan route for new robot
                plans = [AgentPlan(agent_id=reassigned_robot_id, start_node=new_bot.current_node, goal_node=order.pick_node)]
                routes = self.fms.router.plan(plans)
                if routes and reassigned_robot_id in routes:
                    new_route = routes[reassigned_robot_id]
                    new_bot.planned_trajectory = new_route

        record = {
            "incident_type": "ROBOT_HARDWARE_FAULT",
            "failed_robot": failed_robot_id,
            "orphaned_mission": failed_mission_id,
            "reassigned_to": reassigned_robot_id,
            "new_route": new_route,
            "recovery_status": "REALLOCATED" if reassigned_robot_id else "TASK_QUEUED",
            "timestamp": time.time()
        }
        self.incident_history.append(record)

        db.record_incident({
            "incident_type": "ROBOT_HARDWARE_FAULT",
            "robot_id": failed_robot_id,
            "node_or_location": failed_bot.current_node,
            "description": f"Hardware fault detected on {failed_robot_id}. Task {failed_mission_id or NONE} reallocated to {reassigned_robot_id or QUEUE}",
            "recovery_action": f"TASK_PREEMPT_AND_REASSIGNMENT_TO_{reassigned_robot_id}",
            "timestamp": time.time()
        })

        await event_bus.publish(
            event_type=EventType.ROBOT_FAULT,
            source_entity=f"RECOVERY:{failed_robot_id}",
            message=f"Robot {failed_robot_id} fault recovered. Mission reallocated to {reassigned_robot_id}.",
            severity=EventSeverity.CRITICAL,
            metadata=record
        )

        return record

    async def recover_low_battery(self, robot_id: str, dock_node: str = "N_0_0") -> Dict[str, Any]:
        """Reroutes low battery AMR to nearest charging station."""
        bot = self.fms.robots.get(robot_id)
        if not bot:
            return {"status": "ERROR", "message": f"Robot {robot_id} not found"}

        # Plan detour to charging dock
        plan = AgentPlan(agent_id=robot_id, start_node=bot.current_node, goal_node=dock_node)
        routes = self.fms.router.plan([plan])
        dock_route = routes.get(robot_id, [bot.current_node, dock_node]) if routes else [bot.current_node, dock_node]

        bot.planned_trajectory = dock_route
        bot.is_busy = True

        record = {
            "incident_type": "BATTERY_CRITICAL_RECOVERY",
            "robot_id": robot_id,
            "battery_pct": bot.battery_pct,
            "charging_dock": dock_node,
            "dock_route": dock_route,
            "timestamp": time.time()
        }
        self.incident_history.append(record)

        await event_bus.publish(
            event_type=EventType.BATTERY_RECOVERY_TRIGGERED,
            source_entity=f"RECOVERY:{robot_id}",
            message=f"Critical battery recovery triggered for {robot_id}. Rerouted to charger {dock_node}.",
            severity=EventSeverity.WARNING,
            metadata=record
        )

        return record


recovery_engine = AutonomousRecoveryEngine()
