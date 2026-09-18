import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, Optional

from synq_interfaces.types import (
    PayloadTypeEnum,
    PayloadStatus
)


class AbstractPayloadDriver(ABC):
    """Base class for all synQ modular payload hardware drivers."""

    def __init__(self, serial_number: str):
        self.serial_number = serial_number
        self.is_busy = False
        self.error_code = ""
        self.temperature_c = 26.0

    @abstractmethod
    def get_payload_type(self) -> PayloadTypeEnum:
        pass

    @abstractmethod
    def get_weight_kg(self) -> float:
        pass

    @abstractmethod
    def get_status(self) -> PayloadStatus:
        pass

    @abstractmethod
    def execute_command(self, action: str, parameter: float) -> Tuple[bool, str]:
        pass

    @abstractmethod
    def get_transit_speed_limit(self) -> float:
        """Returns max allowable AMR ground speed given current payload state."""
        pass


class ScissorLiftDriver(AbstractPayloadDriver):
    """
    Scissor Lift Module:
    Vertical stroke: 0.0 to 0.80m (0-100%).
    Carries up to 150 kg pallets/totes.
    Safety interlock: Transit velocity capped to 0.0m/s if lift is raised >5%.
    """

    def __init__(self, serial_number: str = "SYNQ-LIFT-2026-001"):
        super().__init__(serial_number)
        self.current_height_pct = 0.0  # 0 to 100%
        self.is_locked = True

    def get_payload_type(self) -> PayloadTypeEnum:
        return PayloadTypeEnum.SCISSOR_LIFT

    def get_weight_kg(self) -> float:
        return 42.5

    def get_status(self) -> PayloadStatus:
        return PayloadStatus(
            payload_type=PayloadTypeEnum.SCISSOR_LIFT,
            is_locked=self.is_locked,
            is_busy=self.is_busy,
            position_pct=self.current_height_pct,
            temperature_c=self.temperature_c,
            error_code=self.error_code
        )

    def execute_command(self, action: str, parameter: float) -> Tuple[bool, str]:
        action = action.upper()
        if action in ["LIFT_UP", "SET_HEIGHT"]:
            target_pct = max(0.0, min(100.0, parameter))
            self.current_height_pct = target_pct
            return True, f"Scissor lift moved to {target_pct:.1f}%"
        elif action in ["LIFT_DOWN", "LOWER"]:
            self.current_height_pct = 0.0
            return True, "Scissor lift fully lowered to transit height"
        elif action == "LOCK":
            self.is_locked = True
            return True, "Hydraulic / ball-screw brake locked"
        elif action == "UNLOCK":
            self.is_locked = False
            return True, "Lock released"
        return False, f"Unknown action '{action}' for ScissorLiftDriver"

    def get_transit_speed_limit(self) -> float:
        if self.current_height_pct > 5.0:
            return 0.0  # Hard stop: do not drive while lift is raised
        return 1.2  # Max safe transit speed unladen/lowered


class RollerConveyorDriver(AbstractPayloadDriver):
    """
    Active Roller Conveyor Module:
    Bidirectional powered rollers for automated transfer to rack/ASRS stations.
    Safety interlock: AMR cannot drive while rollers are transferring.
    """

    def __init__(self, serial_number: str = "SYNQ-CONV-2026-002"):
        super().__init__(serial_number)
        self.roller_speed_pct = 0.0  # -100% to +100%
        self.optical_sensor_triggered = False

    def get_payload_type(self) -> PayloadTypeEnum:
        return PayloadTypeEnum.ROLLER_CONVEYOR

    def get_weight_kg(self) -> float:
        return 38.0

    def get_status(self) -> PayloadStatus:
        return PayloadStatus(
            payload_type=PayloadTypeEnum.ROLLER_CONVEYOR,
            is_locked=True,
            is_busy=abs(self.roller_speed_pct) > 0.01,
            position_pct=abs(self.roller_speed_pct),
            temperature_c=self.temperature_c,
            error_code=self.error_code
        )

    def execute_command(self, action: str, parameter: float) -> Tuple[bool, str]:
        action = action.upper()
        if action in ["START_TRANSFER", "ROLL_FORWARD"]:
            self.roller_speed_pct = max(10.0, min(100.0, parameter if parameter > 0 else 50.0))
            self.is_busy = True
            return True, f"Conveyor spinning forward at {self.roller_speed_pct:.1f}%"
        elif action in ["ROLL_REVERSE"]:
            self.roller_speed_pct = -max(10.0, min(100.0, parameter if parameter > 0 else 50.0))
            self.is_busy = True
            return True, f"Conveyor spinning reverse at {abs(self.roller_speed_pct):.1f}%"
        elif action in ["STOP", "STOP_TRANSFER"]:
            self.roller_speed_pct = 0.0
            self.is_busy = False
            return True, "Conveyor stopped"
        return False, f"Unknown action '{action}' for RollerConveyorDriver"

    def get_transit_speed_limit(self) -> float:
        if abs(self.roller_speed_pct) > 0.01:
            return 0.0  # Cannot drive while roller motor is moving crates
        return 1.4  # Full speed when conveyor stationary


class ToteGripperDriver(AbstractPayloadDriver):
    """
    Parallel Tote Gripper Module:
    Electric clamp mechanism for retrieving warehouse bins and cartons.
    """

    def __init__(self, serial_number: str = "SYNQ-GRIP-2026-003"):
        super().__init__(serial_number)
        self.clamp_position_pct = 0.0  # 0% = full open (60cm), 100% = full closed (20cm)
        self.clamped = False

    def get_payload_type(self) -> PayloadTypeEnum:
        return PayloadTypeEnum.TOTE_GRIPPER

    def get_weight_kg(self) -> float:
        return 32.0

    def get_status(self) -> PayloadStatus:
        return PayloadStatus(
            payload_type=PayloadTypeEnum.TOTE_GRIPPER,
            is_locked=self.clamped,
            is_busy=self.is_busy,
            position_pct=self.clamp_position_pct,
            temperature_c=self.temperature_c,
            error_code=self.error_code
        )

    def execute_command(self, action: str, parameter: float) -> Tuple[bool, str]:
        action = action.upper()
        if action in ["CLAMP", "GRIP"]:
            self.clamp_position_pct = max(0.0, min(100.0, parameter if parameter > 0 else 80.0))
            self.clamped = True
            return True, f"Gripper clamped at {self.clamp_position_pct:.1f}%"
        elif action in ["RELEASE", "OPEN"]:
            self.clamp_position_pct = 0.0
            self.clamped = False
            return True, "Gripper opened"
        return False, f"Unknown action '{action}' for ToteGripperDriver"

    def get_transit_speed_limit(self) -> float:
        # If carrying a clamped tote, safely limit speed
        return 1.0 if self.clamped else 1.3


class PayloadHardwareManager:
    """
    Central Manager for dynamic hot/cold swapping of synQ payloads.
    Emulates the 1-Wire DS2431 digital identification bus, queries current module,
    and returns system-wide constraints to Nav2 and the chassis controller.
    """

    def __init__(self):
        self.active_driver: Optional[AbstractPayloadDriver] = None

    def attach_payload(self, driver: AbstractPayloadDriver) -> Dict[str, Any]:
        self.active_driver = driver
        return self.identify_payload()

    def detach_payload(self) -> bool:
        if self.active_driver and self.active_driver.is_busy:
            return False  # Cannot detach while module is actively moving!
        self.active_driver = None
        return True

    def identify_payload(self) -> Dict[str, Any]:
        if self.active_driver is None:
            return {
                "detected": False,
                "payload_type": PayloadTypeEnum.NONE,
                "serial_number": "",
                "weight_kg": 0.0,
                "speed_limit": 1.5
            }
        return {
            "detected": True,
            "payload_type": self.active_driver.get_payload_type(),
            "serial_number": self.active_driver.serial_number,
            "weight_kg": self.active_driver.get_weight_kg(),
            "speed_limit": self.active_driver.get_transit_speed_limit()
        }

    def execute_action(self, action: str, param: float = 0.0) -> Tuple[bool, str]:
        if self.active_driver is None:
            return False, "No modular payload attached to hardware bay"
        return self.active_driver.execute_command(action, param)

    def get_status(self) -> PayloadStatus:
        if self.active_driver is None:
            return PayloadStatus(payload_type=PayloadTypeEnum.NONE)
        return self.active_driver.get_status()

    def get_max_transit_speed(self) -> float:
        if self.active_driver is None:
            return 1.5  # Unladen base chassis max speed
        return self.active_driver.get_transit_speed_limit()
