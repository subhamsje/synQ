"""
Bridge between FMS RobotAgent model and centralized RobotState model.

This module provides utilities to sync state between the legacy FMS RobotAgent
(which is used by FleetManager for dispatch decisions) and the new centralized
RobotState (which is the single source of truth for the dashboard).
"""

from typing import Dict, Any, Optional
import time

from backend.agent.robot_state import robot_state, RobotState
from fms.models.domain_models import RobotStatus, PayloadType as FmsPayloadType


def sync_fms_to_central_state(robot_id: str, force: bool = False) -> Optional[RobotState]:
    """
    Sync the FMS RobotAgent state to the centralized RobotState.
    
    This function should be called whenever the FMS robot state changes
    (dispatch, status update, etc.) to ensure the centralized state stays in sync.
    
    Args:
        robot_id: The robot identifier
        force: If True, create the state entry if it doesn't exist
    
    Returns:
        The updated RobotState, or None if robot not found
    """
    # Try to get from centralized state first
    state = robot_state.get_state(robot_id)
    
    if state is None:
        if not force:
            return None
        # Create new state entry
        state = robot_state.register_robot(robot_id=robot_id)
    
    return state


def get_robot_payload_from_state(robot_id: str) -> str:
    """Get payload type from centralized state for dashboard consumption."""
    state = robot_state.get_state(robot_id)
    if state:
        return state.payload
    return "BASE"


def update_status_from_fms(robot_id: str, fms_robot_status: str) -> bool:
    """
    Update centralized state status from FMS status string.
    Maps FMS RobotStatus enum values to centralized state.
    """
    status_map = {
        "IDLE": "IDLE",
        "NAVIGATING": "NAVIGATING",
        "PICKING": "PICKING",
        "DROPPING": "DROPPING",
        "CHARGING": "CHARGING",
        "MAINTENANCE": "MAINTENANCE",
        "ERROR": "ERROR",
        "EMERGENCY_STOP": "EMERGENCY_STOP"
    }
    
    central_status = status_map.get(fms_robot_status, "IDLE")
    return robot_state.update_state(robot_id, status=central_status) is not None


def payload_type_to_str(payload) -> str:
    """Convert PayloadType enum to string representation."""
    if isinstance(payload, str):
        return payload
    if hasattr(payload, 'value'):
        return payload.value if isinstance(payload.value, str) else str(payload.value)
    return str(payload)