"""
Centralized Robot State Model — Single Source of Truth for Dashboard.

This module provides the unified RobotState model that aggregates:
- Position (from odometry / GPS / map coordinate)
- Node (current graph node in warehouse)
- Battery (real-time SoC % from diagnostics)
- Status (IDLE|NAVIGATING|PICKING|DROPPING|CHARGING|ERROR|EMERGENCY_STOP)
- Payload (current attached payload type)
- Current Mission (active mission ID or None)
- Velocity (live vx, vy, omega from odometry)

All state changes flow through this canonical model, which is then projected
to the dashboard via WebSocket streaming.
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, List, Any, Optional, Callable
import time
import threading
from datetime import datetime


class RobotStatus(str, Enum):
    IDLE = "IDLE"
    NAVIGATING = "NAVIGATING"
    PICKING = "PICKING"
    DROPPING = "DROPPING"
    CHARGING = "CHARGING"
    MAINTENANCE = "MAINTENANCE"
    ERROR = "ERROR"
    EMERGENCY_STOP = "EMERGENCY_STOP"


@dataclass
class RobotState:
    """
    Canonical, aggregated state for an AMR unit.
    
    This is the single source of truth — all ROS2 topics, adapters,
    and simulation feeds update this object directly.
    """
    robot_id: str
    node: str = "N_0_0"
    position: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0, "theta": 0.0})
    velocity: Dict[str, float] = field(default_factory=lambda: {"vx": 0.0, "vy": 0.0, "omega": 0.0})
    battery: Dict[str, Any] = field(default_factory=lambda: {"pct": 100.0, "temp_c": 25.0, "charging": False})
    status: RobotStatus = RobotStatus.IDLE
    payload: str = "BASE"
    current_mission: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    last_update_source: str = "INIT"
    
    # Extended telemetry
    sensors: Dict[str, Any] = field(default_factory=lambda: {
        "lidar_blindzone_active": False,
        "imu_tilt_warning": False,
        "amcl_covariance": 0.02,
        "min_obstacle_distance": 10.0
    })
    trajectory: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dict for JSON/WS transmission."""
        d = asdict(self)
        d["status"] = self.status.value
        return d
    
    def update_position(self, x: float, y: float, theta: float, source: str = "odom"):
        """Update robot position from odometry or coordinate system."""
        self.position = {"x": x, "y": y, "theta": theta}
        self.timestamp = time.time()
        self.last_update_source = source
    
    def update_velocity(self, vx: float, vy: float, omega: float, source: str = "odom"):
        """Update velocity from odom twist."""
        self.velocity = {"vx": vx, "vy": vy, "omega": omega}
        self.timestamp = time.time()
        self.last_update_source = source
    
    def update_battery(self, pct: float, temp_c: Optional[float] = None, charging: bool = False):
        """Update battery state from diagnostics topic."""
        self.battery = {"pct": pct, "charging": charging}
        if temp_c is not None:
            self.battery["temp_c"] = temp_c
        self.timestamp = time.time()
        self.last_update_source = "battery"
    
    def set_status(self, status: RobotStatus, source: str = "local"):
        """Transition robot status (IDLE, NAVIGATING, etc.)"""
        self.status = status
        self.timestamp = time.time()
        self.last_update_source = source
    
    def set_emergency_stop(self, active: bool):
        """Activate or clear emergency stop."""
        if active:
            self.status = RobotStatus.EMERGENCY_STOP
            self.velocity = {"vx": 0.0, "vy": 0.0, "omega": 0.0}
        else:
            if self.status == RobotStatus.EMERGENCY_STOP:
                self.status = RobotStatus.IDLE
        self.timestamp = time.time()
        self.last_update_source = "estop"
    
    def set_mission(self, mission_id: Optional[str], trajectory: Optional[List[str]] = None):
        """Associate robot with active mission."""
        self.current_mission = mission_id
        if trajectory is not None:
            self.trajectory = trajectory
        self.timestamp = time.time()
        self.last_update_source = "mission"
    
    def set_payload(self, payload_type: str):
        """Update current payload type."""
        self.payload = payload_type
        self.timestamp = time.time()
        self.last_update_source = "payload"
    
    def set_node(self, node_id: str):
        """Update current graph node (for discrete path planning)."""
        self.node = node_id
        self.timestamp = time.time()
        self.last_update_source = "node"
    
    def set_sensors(self, lidar_blindzone: bool, imu_tilt: bool, min_distance: float):
        """Update sensor health/fault flags."""
        self.sensors["lidar_blindzone_active"] = lidar_blindzone
        self.sensors["imu_tilt_warning"] = imu_tilt
        self.sensors["min_obstacle_distance"] = min_distance


class RobotStateManager:
    """
    Thread-safe registry of all robot states in the facility.
    This is the single source of truth for the entire fleet.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._robots: Dict[str, RobotState] = {}
                    cls._instance._observers: List[Callable] = []
        return cls._instance
    
    def register_robot(self, robot_id: str, **initial_state) -> RobotState:
        """Register a new robot with initial state."""
        state = RobotState(robot_id=robot_id, **initial_state)
        self._robots[robot_id] = state
        return state
    
    def get_state(self, robot_id: str) -> Optional[RobotState]:
        """Get current state for a single robot."""
        return self._robots.get(robot_id)
    
    def get_all_states(self) -> Dict[str, RobotState]:
        """Get all robot states (copy for thread safety)."""
        return dict(self._robots)
    
    def subscribe(self, callback: Callable[[Dict[str, Any]], None]):
        """Register a callback to receive state updates."""
        if callback not in self._observers:
            self._observers.append(callback)
    
    def unsubscribe(self, callback: Callable[[Dict[str, Any]], None]):
        """Remove a state update callback."""
        if callback in self._observers:
            self._observers.remove(callback)
    
    def notify_observers(self, robot_id: str, state: RobotState):
        """Push state update to all observers."""
        payload = {"robot_id": robot_id, "state": state.to_dict(), "timestamp": state.timestamp}
        for cb in self._observers:
            try:
                cb(payload)
            except Exception:
                pass  # Don't let one observer break others
    
    def update_state(self, robot_id: str, **kwargs) -> Optional[RobotState]:
        """
        Update specific fields on a robot's state.
        Uses direct field updates for atomic changes.
        """
        state = self._robots.get(robot_id)
        if state is None:
            return None
        
        source_val = kwargs.pop("source", "manual")
        if isinstance(source_val, dict):
            source_val = source_val.get("source", "manual")
        elif not isinstance(source_val, str):
            source_val = "manual"

        if "position" in kwargs:
            state.update_position(**kwargs.pop("position"), source=source_val)
        if "velocity" in kwargs:
            state.update_velocity(**kwargs.pop("velocity"), source=source_val)
        if "battery_pct" in kwargs:
            state.update_battery(kwargs.pop("battery_pct"), kwargs.pop("battery_temp_c", None) if "battery_temp_c" in kwargs else None, kwargs.pop("charging", False))
        if "status" in kwargs:
            state.set_status(RobotStatus(kwargs.pop("status")))
        if "emergency_stop" in kwargs:
            state.set_emergency_stop(kwargs.pop("emergency_stop"))
        if "mission" in kwargs:
            state.set_mission(kwargs.pop("mission"), kwargs.pop("trajectory", None))
        if "payload" in kwargs:
            state.set_payload(kwargs.pop("payload"))
        if "node" in kwargs:
            state.set_node(kwargs.pop("node"))
        if "sensors" in kwargs:
            s = kwargs.pop("sensors")
            state.set_sensors(s.get("lidar_blindzone", False), s.get("imu_tilt", False), s.get("min_distance", 10.0))
        
        self.notify_observers(robot_id, state)
        return state
    
    def heartbeat(self, robot_id: str, **kwargs) -> Optional[RobotState]:
        """Update state and refresh timestamp (for regular telemetry updates)."""
        result = self.update_state(robot_id, **kwargs)
        if result:
            result.timestamp = time.time()
        return result


# Global singleton instance
robot_state = RobotStateManager()


def get_robot_state_dict() -> Dict[str, Any]:
    """Get all robot states as a flat dict suitable for dashboard consumption."""
    now = time.time()
    return {
        "timestamp": now,
        "robots": {
            rid: {
                **state.to_dict(),
                "healthy": state.status != RobotStatus.ERROR and state.status != RobotStatus.EMERGENCY_STOP
            }
            for rid, state in robot_state.get_all_states().items()
        }
    }