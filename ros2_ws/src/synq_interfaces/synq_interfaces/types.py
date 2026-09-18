from dataclasses import dataclass, field
from enum import IntEnum, Enum
from typing import Optional, Tuple


class PayloadTypeEnum(IntEnum):
    NONE = 0
    SCISSOR_LIFT = 1
    ROLLER_CONVEYOR = 2
    TOTE_GRIPPER = 3


class SafetyStateEnum(IntEnum):
    SAFETY_NORMAL = 0
    SAFETY_SLOWDOWN = 1
    SAFETY_ESTOP = 2


class MissionPhaseEnum(str, Enum):
    IDLE = "IDLE"
    NAVIGATING_TO_PICK = "NAVIGATING_TO_PICK"
    ACTUATING_PAYLOAD_PICK = "ACTUATING_PAYLOAD_PICK"
    NAVIGATING_TO_DROP = "NAVIGATING_TO_DROP"
    ACTUATING_PAYLOAD_DROP = "ACTUATING_PAYLOAD_DROP"
    NAVIGATING_TO_CHARGE = "NAVIGATING_TO_CHARGE"
    CHARGING = "CHARGING"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"


@dataclass
class PayloadType:
    type: PayloadTypeEnum = PayloadTypeEnum.NONE
    payload_serial_number: str = ""
    weight_kg: float = 0.0


@dataclass
class PayloadStatus:
    payload_type: PayloadTypeEnum = PayloadTypeEnum.NONE
    is_locked: bool = False
    is_busy: bool = False
    position_pct: float = 0.0
    temperature_c: float = 25.0
    error_code: str = ""


@dataclass
class RobotSafetyStatus:
    safety_state: SafetyStateEnum = SafetyStateEnum.SAFETY_NORMAL
    lidar_blindzone_active: bool = False
    imu_tilt_warning: bool = False
    localization_lost: bool = False
    min_obstacle_distance: float = 10.0


@dataclass
class Pose2D:
    x: float
    y: float
    yaw: float = 0.0


@dataclass
class MissionGoal:
    mission_id: str
    mission_type: str  # "PICK_DROP", "DOCK_CHARGE", "INVENTORY_PATROL"
    pick_pose: Optional[Pose2D] = None
    drop_pose: Optional[Pose2D] = None
    payload_action: str = ""
    payload_param: float = 0.0


@dataclass
class MissionFeedback:
    current_phase: MissionPhaseEnum
    progress_pct: float
    elapsed_time_sec: float


@dataclass
class MissionResult:
    success: bool
    result_message: str
    execution_time_seconds: float
