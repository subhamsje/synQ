from enum import Enum
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import time


class EventSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    DAILY_SUMMARY = "DAILY_SUMMARY"


class EventType(str, Enum):
    # Robot Lifecycle & Hardware
    ROBOT_REGISTERED = "robot.registered"
    ROBOT_TELEMETRY_UPDATED = "robot.telemetry.updated"
    ROBOT_STATE_CHANGED = "robot.state.changed"
    ROBOT_FAULT = "robot.fault"
    ROBOT_RECOVERED = "robot.recovered"
    ROBOT_OFFLINE = "robot.offline"

    # Missions & Material Flow
    MISSION_CREATED = "mission.created"
    MISSION_ASSIGNED = "mission.assigned"
    MISSION_STARTED = "mission.started"
    MISSION_PROGRESS = "mission.progress"
    MISSION_COMPLETED = "mission.completed"
    MISSION_FAILED = "mission.failed"
    MISSION_PREEMPTED = "mission.preempted"
    MISSION_REALLOCATED = "mission.reallocated"

    # Traffic, CBS & Navigation
    ROUTE_PLANNED = "route.planned"
    ROUTE_CONFLICT_DETECTED = "route.conflict.detected"
    ROUTE_REPLANNED = "route.replanned"
    OBSTACLE_DETECTED = "obstacle.detected"
    OBSTACLE_CLEARED = "obstacle.cleared"
    AISLE_BLOCKED = "aisle.blocked"
    AISLE_CLEARED = "aisle.cleared"

    # Energy & Safety
    BATTERY_WARNING = "battery.warning"
    BATTERY_RECOVERY_TRIGGERED = "battery.recovery.triggered"
    ESTOP_TRIGGERED = "safety.estop.triggered"
    ESTOP_CLEARED = "safety.estop.cleared"

    # SLA & Flow Intelligence
    SLA_BREACH_WARNING = "sla.breach.warning"
    SLA_PRESERVED = "sla.preserved"
    CONGESTION_DETECTED = "traffic.congestion.detected"

    # Health & Maintenance
    MAINTENANCE_PREDICTED = "maintenance.predicted"
    HEALTH_DEGRADATION_DETECTED = "health.degradation.detected"


class OperationalEvent(BaseModel):
    event_id: str
    event_type: EventType
    severity: EventSeverity = EventSeverity.INFO
    source_entity: str  # e.g., "AMR-07", "FMS-DISPATCH", "CBS-ROUTER", "FACILITY-MONITOR"
    message: str
    timestamp: float = Field(default_factory=time.time)
    metadata: Dict[str, Any] = Field(default_factory=dict)
