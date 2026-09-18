import math
import time
from typing import Optional, Callable, Dict, Any, Tuple

from synq_interfaces.types import (
    PayloadTypeEnum,
    SafetyStateEnum,
    MissionPhaseEnum,
    PayloadStatus,
    RobotSafetyStatus,
    MissionGoal,
    MissionResult,
    MissionFeedback,
    Pose2D
)


class MissionExecutive:
    """
    synQ Mission Executive Engine.
    Executes high-level warehouse missions with Nav2 waypoint dispatch,
    payload interlock safety checks, dynamic battery routing, and E-Stop preemption.
    """

    def __init__(
        self,
        robot_id: str = "synq-amr-01",
        charge_dock_pose: Pose2D = Pose2D(x=1.0, y=1.0, yaw=0.0)
    ):
        self.robot_id = robot_id
        self.charge_dock_pose = charge_dock_pose
        
        # Internal state
        self.current_phase: MissionPhaseEnum = MissionPhaseEnum.IDLE
        self.active_mission: Optional[MissionGoal] = None
        self.mission_start_time: float = 0.0
        self.phase_elapsed_time: float = 0.0
        
        # Robot physical state
        self.current_pose: Pose2D = Pose2D(x=0.0, y=0.0, yaw=0.0)
        self.target_pose: Optional[Pose2D] = None
        self.battery_pct: float = 100.0
        self.safety_status: RobotSafetyStatus = RobotSafetyStatus()
        self.payload_status: PayloadStatus = PayloadStatus()
        
        # Callbacks
        self.feedback_callback: Optional[Callable[[MissionFeedback], None]] = None
        self.simulated_nav_speed: float = 1.0  # m/s simulated transit speed

    def register_feedback_callback(self, cb: Callable[[MissionFeedback], None]):
        self.feedback_callback = cb

    def update_pose(self, x: float, y: float, yaw: float = 0.0):
        self.current_pose = Pose2D(x=x, y=y, yaw=yaw)

    def update_battery(self, battery_pct: float):
        self.battery_pct = max(0.0, min(100.0, battery_pct))
        # Automatic low-battery emergency return to dock
        if self.battery_pct < 15.0 and self.current_phase not in [
            MissionPhaseEnum.NAVIGATING_TO_CHARGE,
            MissionPhaseEnum.CHARGING
        ]:
            self._reroute_to_charging("CRITICAL_BATTERY_LOW")

    def update_safety_status(self, safety: RobotSafetyStatus):
        self.safety_status = safety
        if safety.safety_state == SafetyStateEnum.SAFETY_ESTOP:
            if self.active_mission and self.current_phase != MissionPhaseEnum.FAILED:
                self.preempt_mission("E-STOP TRIGGERED BY SAFETY GUARDIAN")

    def update_payload_status(self, status: PayloadStatus):
        self.payload_status = status

    def submit_mission(self, mission: MissionGoal) -> Tuple[bool, str]:
        """Validates and begins execution of a new warehouse mission."""
        if self.safety_status.safety_state == SafetyStateEnum.SAFETY_ESTOP:
            return False, "Rejecting mission: Robot in E-STOP state"

        if self.battery_pct < 20.0 and mission.mission_type != "DOCK_CHARGE":
            return False, f"Rejecting mission: Battery level {self.battery_pct:.1f}% below 20% dispatch threshold"

        if self.active_mission is not None:
            return False, f"Rejecting mission: Robot busy executing mission {self.active_mission.mission_id}"

        # Check payload interlocks before starting
        if self.payload_status.position_pct > 0.0 and self.payload_status.payload_type == PayloadTypeEnum.SCISSOR_LIFT:
            return False, "Rejecting mission: Scissor lift must be lowered to 0% before transit"

        self.active_mission = mission
        self.mission_start_time = time.time()
        self.phase_elapsed_time = 0.0

        if mission.mission_type == "PICK_DROP":
            self.current_phase = MissionPhaseEnum.NAVIGATING_TO_PICK
            self.target_pose = mission.pick_pose
        elif mission.mission_type == "DOCK_CHARGE":
            self.current_phase = MissionPhaseEnum.NAVIGATING_TO_CHARGE
            self.target_pose = self.charge_dock_pose
        else:
            self.current_phase = MissionPhaseEnum.NAVIGATING_TO_PICK
            self.target_pose = mission.pick_pose

        self._emit_feedback(0.0)
        return True, "Mission accepted"

    def preempt_mission(self, reason: str) -> MissionResult:
        """Preempts and terminates the active mission."""
        elapsed = time.time() - self.mission_start_time if self.mission_start_time > 0 else 0.0
        mission_id = self.active_mission.mission_id if self.active_mission else "NONE"
        
        self.current_phase = MissionPhaseEnum.FAILED
        self.active_mission = None
        self.target_pose = None
        
        return MissionResult(
            success=False,
            result_message=f"Mission {mission_id} aborted: {reason}",
            execution_time_seconds=round(elapsed, 2)
        )

    def _reroute_to_charging(self, reason: str):
        """Forces preemption and sets destination to charging dock."""
        self.current_phase = MissionPhaseEnum.NAVIGATING_TO_CHARGE
        self.target_pose = self.charge_dock_pose
        self.phase_elapsed_time = 0.0
        if self.active_mission:
            self.active_mission = MissionGoal(
                mission_id=f"CHARGE_RESCUE_{int(time.time())}",
                mission_type="DOCK_CHARGE"
            )

    def _emit_feedback(self, progress_pct: float):
        if self.feedback_callback:
            elapsed = time.time() - self.mission_start_time if self.mission_start_time > 0 else 0.0
            feedback = MissionFeedback(
                current_phase=self.current_phase,
                progress_pct=round(progress_pct, 1),
                elapsed_time_sec=round(elapsed, 2)
            )
            self.feedback_callback(feedback)

    def tick(self, dt: float) -> Optional[MissionResult]:
        """
        Discrete time step execution engine.
        Advances navigation, payload actuation steps, and completes missions.
        """
        if not self.active_mission:
            return None

        # Safety interlock: if E-Stop occurs during tick, immediately abort
        if self.safety_status.safety_state == SafetyStateEnum.SAFETY_ESTOP:
            return self.preempt_mission("E-STOP triggered during execution")

        self.phase_elapsed_time += dt

        # State machine progression
        if self.current_phase == MissionPhaseEnum.NAVIGATING_TO_PICK:
            reached = self._advance_simulated_nav(dt)
            self._emit_feedback(25.0 if not reached else 40.0)
            if reached:
                self.current_phase = MissionPhaseEnum.ACTUATING_PAYLOAD_PICK
                self.phase_elapsed_time = 0.0

        elif self.current_phase == MissionPhaseEnum.ACTUATING_PAYLOAD_PICK:
            # Simulate payload pick operation (e.g. lift up 2.0s)
            self._emit_feedback(45.0)
            if self.phase_elapsed_time >= 2.0:
                self.current_phase = MissionPhaseEnum.NAVIGATING_TO_DROP
                self.target_pose = self.active_mission.drop_pose
                self.phase_elapsed_time = 0.0

        elif self.current_phase == MissionPhaseEnum.NAVIGATING_TO_DROP:
            reached = self._advance_simulated_nav(dt)
            self._emit_feedback(75.0 if not reached else 90.0)
            if reached:
                self.current_phase = MissionPhaseEnum.ACTUATING_PAYLOAD_DROP
                self.phase_elapsed_time = 0.0

        elif self.current_phase == MissionPhaseEnum.ACTUATING_PAYLOAD_DROP:
            # Simulate payload drop operation (e.g. lift down 2.0s)
            self._emit_feedback(95.0)
            if self.phase_elapsed_time >= 2.0:
                elapsed = time.time() - self.mission_start_time
                self.current_phase = MissionPhaseEnum.COMPLETED
                result = MissionResult(
                    success=True,
                    result_message=f"Mission {self.active_mission.mission_id} completed successfully",
                    execution_time_seconds=round(elapsed, 2)
                )
                self.active_mission = None
                self.target_pose = None
                return result

        elif self.current_phase == MissionPhaseEnum.NAVIGATING_TO_CHARGE:
            reached = self._advance_simulated_nav(dt)
            self._emit_feedback(80.0 if not reached else 100.0)
            if reached:
                self.current_phase = MissionPhaseEnum.CHARGING
                self.phase_elapsed_time = 0.0

        elif self.current_phase == MissionPhaseEnum.CHARGING:
            # Battery charges at 5% per second in fast dock
            self.battery_pct = min(100.0, self.battery_pct + 5.0 * dt)
            if self.battery_pct >= 95.0:
                elapsed = time.time() - self.mission_start_time
                self.current_phase = MissionPhaseEnum.IDLE
                result = MissionResult(
                    success=True,
                    result_message="Charging completed to >95%",
                    execution_time_seconds=round(elapsed, 2)
                )
                self.active_mission = None
                self.target_pose = None
                return result

        return None

    def _advance_simulated_nav(self, dt: float) -> bool:
        """Simulates linear movement toward target_pose."""
        if not self.target_pose:
            return True

        dx = self.target_pose.x - self.current_pose.x
        dy = self.target_pose.y - self.current_pose.y
        dist = math.hypot(dx, dy)

        if dist < 0.05:
            self.current_pose = self.target_pose
            return True

        step = min(dist, self.simulated_nav_speed * dt)
        self.current_pose.x += (dx / dist) * step
        self.current_pose.y += (dy / dist) * step
        return False
