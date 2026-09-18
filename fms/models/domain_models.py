from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Any
import time


class RobotStatus(str, Enum):
    IDLE = "IDLE"
    NAVIGATING = "NAVIGATING"
    PICKING = "PICKING"
    DROPPING = "DROPPING"
    CHARGING = "CHARGING"
    MAINTENANCE = "MAINTENANCE"
    ERROR = "ERROR"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class PayloadType(str, Enum):
    BASE = "BASE"
    SCISSOR_LIFT = "SCISSOR_LIFT"
    ROLLER_CONVEYOR = "ROLLER_CONVEYOR"
    TOTE_GRIPPER = "TOTE_GRIPPER"
    ANY = "ANY"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    ALLOCATING = "ALLOCATING"
    ASSIGNED = "ASSIGNED"
    IN_TRANSIT_PICKUP = "IN_TRANSIT_PICKUP"
    PICKING_UP = "PICKING_UP"
    IN_TRANSIT_DROP = "IN_TRANSIT_DROP"
    DROPPING_OFF = "DROPPING_OFF"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    SUSPENDED = "SUSPENDED"
    REASSIGNED = "REASSIGNED"
    CANCELLED = "CANCELLED"


class IncidentType(str, Enum):
    OBSTACLE_COLLISION_AVOIDED = "OBSTACLE_COLLISION_AVOIDED"
    CBS_CROSSING_CONFLICT = "CBS_CROSSING_CONFLICT"
    BATTERY_CRITICAL_RECOVERY = "BATTERY_CRITICAL_RECOVERY"
    LOCALIZATION_SLIP_CORRECTED = "LOCALIZATION_SLIP_CORRECTED"
    AISLE_BLOCK_REROUTE = "AISLE_BLOCK_REROUTE"
    ROBOT_HARDWARE_FAULT = "ROBOT_HARDWARE_FAULT"
    COMMUNICATION_WATCHDOG_TRIP = "COMMUNICATION_WATCHDOG_TRIP"


@dataclass
class RobotCapability:
    payload_type: PayloadType = PayloadType.BASE
    max_payload_kg: float = 250.0
    max_velocity_mps: float = 1.2
    has_lidar_360: bool = True
    has_depth_camera: bool = True
    has_safety_lidar: bool = True


@dataclass
class SensorState:
    lidar_healthy: bool = True
    imu_healthy: bool = True
    amcl_covariance: float = 0.02
    battery_temp_c: float = 28.5
    motor_temp_c: float = 34.0
    last_scan_timestamp: float = field(default_factory=time.time)


@dataclass
class Robot:
    robot_id: str
    vendor: str = "synQ-Robotics"
    model: str = "FLTX-Mecanum-v2"
    status: RobotStatus = RobotStatus.IDLE
    current_node: str = "N_0_0"
    position: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0, "theta": 0.0})
    velocity: Dict[str, float] = field(default_factory=lambda: {"vx": 0.0, "vy": 0.0, "omega": 0.0})
    battery_pct: float = 100.0
    payload_type: PayloadType = PayloadType.BASE
    payload_state: Dict[str, Any] = field(default_factory=lambda: {"loaded": False, "actuator_pos": 0.0})
    current_mission_id: Optional[str] = None
    planned_trajectory: List[str] = field(default_factory=list)
    capabilities: RobotCapability = field(default_factory=RobotCapability)
    sensors: SensorState = field(default_factory=SensorState)
    safety_estop: bool = False
    last_heartbeat: float = field(default_factory=time.time)

    def is_available_for_dispatch(self) -> bool:
        return (
            self.status in (RobotStatus.IDLE, RobotStatus.CHARGING)
            and not self.safety_estop
            and self.battery_pct >= 20.0
            and self.current_mission_id is None
        )


@dataclass
class RouteSegment:
    segment_id: str
    source_node: str
    target_node: str
    distance_m: float
    expected_duration_s: float
    max_speed_mps: float = 1.2


@dataclass
class RouteReservation:
    reservation_id: str
    robot_id: str
    node_id: str
    time_step: int
    duration_s: float = 2.0


@dataclass
class Route:
    route_id: str
    robot_id: str
    waypoints: List[str]
    segments: List[RouteSegment] = field(default_factory=list)
    estimated_distance_m: float = 0.0
    estimated_duration_s: float = 0.0
    reservations: List[RouteReservation] = field(default_factory=list)


@dataclass
class CandidateEvaluation:
    robot_id: str
    current_node: str
    payload_type: str
    payload_match: bool
    battery_pct: float
    battery_sufficient: bool
    is_busy: bool
    distance_to_pickup_m: float
    cost_score: float
    is_eligible: bool
    decision: str  # "SELECTED", "REJECTED", "PENDING"
    rejection_reason: Optional[str] = None


@dataclass
class DecisionMatrix:
    order_id: str
    pick_node: str
    drop_node: str
    required_payload: str
    selected_robot: Optional[str]
    candidates: List[CandidateEvaluation]
    decision_rationale: str
    constraints: List[str] = field(default_factory=list)


@dataclass
class Task:
    task_id: str
    pick_node: str
    drop_node: str
    required_payload: PayloadType = PayloadType.ANY
    priority: int = 1
    status: TaskStatus = TaskStatus.PENDING
    assigned_robot_id: Optional[str] = None
    route: Optional[Route] = None
    decision_trace: Optional[Dict[str, Any]] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    sla_deadline_s: Optional[float] = None
    failure_reason: Optional[str] = None


@dataclass
class Mission:
    mission_id: str
    task: Task
    assigned_robot: str
    route_hops: List[str]
    active_segment_idx: int = 0
    estimated_eta_s: float = 0.0
    actual_start_time: float = field(default_factory=time.time)


@dataclass
class Incident:
    incident_id: str
    incident_type: IncidentType
    robot_id: str
    node_or_location: str
    description: str
    recovery_action: str
    timestamp: float = field(default_factory=time.time)
    resolved: bool = True


@dataclass
class HealthRecord:
    robot_id: str
    battery_health_score: float = 95.0
    motor_health_score: float = 98.0
    localization_score: float = 99.0
    navigation_score: float = 97.0
    overall_health_score: float = 97.2
    recommended_action: str = "Nominal operation"
    timestamp: float = field(default_factory=time.time)


@dataclass
class WarehouseFacilityState:
    facility_id: str = "Austin-Hub-01"
    active_robots: int = 12
    busy_robots: int = 0
    charging_robots: int = 0
    estop_active: bool = False
    blocked_edges: List[str] = field(default_factory=list)
    pending_tasks_count: int = 0
