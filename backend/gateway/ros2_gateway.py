import asyncio
import time
from typing import Dict, List, Optional, Any, Callable
from enum import Enum

from backend.events.event_bus import event_bus
from backend.events.event_types import EventType, EventSeverity
from fms.adapters.ros2_adapter import ROS2RobotAdapter
from fms.models.domain_models import RobotStatus


class GatewayState(str, Enum):
    CONNECTED = "CONNECTED"
    DISCONNECTED = "DISCONNECTED"
    DEGRADED = "DEGRADED"


class ROS2Gateway:
    """
    Bi-directional ROS 2 Hardware Gateway.
    Bridges between central FLTX operational orchestration and local ROS 2/Nav2 nodes.
    Supports topic mapping, heartbeat monitoring, deadman safety interlocks, and
    asynchronous telemetry ingestion.
    """

    def __init__(self):
        self.state = GatewayState.CONNECTED
        self.adapters: Dict[str, ROS2RobotAdapter] = {}
        self.telemetry_history: Dict[str, List[Dict[str, Any]]] = {}
        self.heartbeat_timeout_s: float = 3.0
        self.command_timeout_s: float = 5.0
        self._running = False

    def register_robot(self, robot_id: str, adapter: Optional[ROS2RobotAdapter] = None) -> ROS2RobotAdapter:
        if adapter is None:
            adapter = ROS2RobotAdapter(robot_id=robot_id)
        self.adapters[robot_id] = adapter
        self.telemetry_history[robot_id] = []
        return adapter

    def get_adapter(self, robot_id: str) -> Optional[ROS2RobotAdapter]:
        return self.adapters.get(robot_id)

    async def ingest_telemetry(self, robot_id: str, telemetry: Dict[str, Any]) -> None:
        """Receives telemetry packet from ROS 2 subscription or bridge."""
        if robot_id not in self.adapters:
            self.register_robot(robot_id)

        adapter = self.adapters[robot_id]
        adapter.update_telemetry(telemetry)

        # Record history
        record = {
            "timestamp": time.time(),
            "telemetry": telemetry
        }
        self.telemetry_history[robot_id].append(record)
        if len(self.telemetry_history[robot_id]) > 100:
            self.telemetry_history[robot_id].pop(0)

        # Check for safety / critical alerts
        if telemetry.get("safety_estop", False):
            await event_bus.publish(
                event_type=EventType.ROBOT_FAULT,
                source_entity=f"ROS2-GW:{robot_id}",
                message=f"Hardware E-STOP asserted on {robot_id}",
                severity=EventSeverity.CRITICAL,
                metadata={"robot_id": robot_id, "state": "EMERGENCY_STOP"}
            )
        elif telemetry.get("battery_pct", 100.0) < 18.0:
            await event_bus.publish(
                event_type=EventType.BATTERY_WARNING,
                source_entity=f"ROS2-GW:{robot_id}",
                message=f"Low battery warning ({telemetry[battery_pct]}%) on {robot_id}",
                severity=EventSeverity.WARNING,
                metadata={"robot_id": robot_id, "battery_pct": telemetry["battery_pct"]}
            )

    async def dispatch_navigation_goal(self, robot_id: str, waypoints: List[str]) -> bool:
        """Sends trajectory/action goal to robot Nav2 stack."""
        if robot_id not in self.adapters:
            return False
        adapter = self.adapters[robot_id]
        if adapter.robot.safety_estop:
            return False

        success = adapter.send_route(waypoints)
        if success:
            await event_bus.publish(
                event_type=EventType.MISSION_STARTED,
                source_entity=f"ROS2-GW:{robot_id}",
                message=f"Dispatched trajectory ({len(waypoints)} waypoints) to {robot_id}",
                severity=EventSeverity.INFO,
                metadata={"robot_id": robot_id, "waypoints": waypoints}
            )
        return success

    async def emergency_stop_robot(self, robot_id: str) -> bool:
        """Sends immediate zero-velocity command and asserts E-stop."""
        if robot_id == "ALL":
            for rid, adapter in self.adapters.items():
                adapter.set_estop(True)
            await event_bus.publish(
                event_type=EventType.ROBOT_FAULT,
                source_entity="ROS2-GW:SAFETY",
                message="FACILITY-WIDE EMERGENCY STOP ASSERTED",
                severity=EventSeverity.CRITICAL,
                metadata={"robot_id": "ALL"}
            )
            return True

        if robot_id in self.adapters:
            self.adapters[robot_id].set_estop(True)
            await event_bus.publish(
                event_type=EventType.ROBOT_FAULT,
                source_entity=f"ROS2-GW:{robot_id}",
                message=f"Emergency stop asserted on {robot_id}",
                severity=EventSeverity.CRITICAL,
                metadata={"robot_id": robot_id}
            )
            return True
        return False

    async def check_heartbeats(self) -> List[str]:
        """Watchdog checking for disconnected or unresponsive robots."""
        stale_robots = []
        for rid, adapter in self.adapters.items():
            if adapter.is_heartbeat_stale():
                stale_robots.append(rid)
                if adapter.robot.status != RobotStatus.ERROR:
                    adapter.robot.status = RobotStatus.ERROR
                    await event_bus.publish(
                        event_type=EventType.ROBOT_FAULT,
                        source_entity=f"ROS2-GW:{rid}",
                        message=f"Heartbeat timeout (> {self.heartbeat_timeout_s}s) on {rid}",
                        severity=EventSeverity.WARNING,
                        metadata={"robot_id": rid, "last_heartbeat": adapter.robot.last_heartbeat}
                    )
        return stale_robots

    def get_status(self) -> Dict[str, Any]:
        return {
            "gateway_state": self.state.value,
            "connected_robots": len(self.adapters),
            "heartbeat_timeout_s": self.heartbeat_timeout_s,
            "robots": {
                rid: {
                    "healthy": ad.is_healthy(),
                    "status": ad.robot.status.value,
                    "battery": ad.robot.battery_pct,
                    "estop": ad.robot.safety_estop,
                    "last_heartbeat": ad.robot.last_heartbeat
                }
                for rid, ad in self.adapters.items()
            }
        }


# Global singleton instance
ros2_gateway = ROS2Gateway()
