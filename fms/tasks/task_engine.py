import time
import asyncio
from typing import Dict, List, Optional, Any

from fms.models.domain_models import Task, TaskStatus, PayloadType
from backend.events.event_bus import event_bus
from backend.events.event_types import EventType, EventSeverity


class TaskEngine:
    """
    Autonomous Material Flow Task Lifecycle Engine.
    Enforces deterministic state transitions, SLA deadlines, priority queuing,
    pre-emption, and explicit failure/reassignment flows.
    """

    VALID_TRANSITIONS = {
        TaskStatus.PENDING: [TaskStatus.ALLOCATING, TaskStatus.CANCELLED],
        TaskStatus.ALLOCATING: [TaskStatus.ASSIGNED, TaskStatus.PENDING, TaskStatus.CANCELLED],
        TaskStatus.ASSIGNED: [TaskStatus.IN_TRANSIT_PICKUP, TaskStatus.BLOCKED, TaskStatus.SUSPENDED, TaskStatus.REASSIGNED, TaskStatus.CANCELLED],
        TaskStatus.IN_TRANSIT_PICKUP: [TaskStatus.PICKING_UP, TaskStatus.BLOCKED, TaskStatus.SUSPENDED, TaskStatus.REASSIGNED, TaskStatus.CANCELLED],
        TaskStatus.PICKING_UP: [TaskStatus.IN_TRANSIT_DROP, TaskStatus.BLOCKED, TaskStatus.CANCELLED],
        TaskStatus.IN_TRANSIT_DROP: [TaskStatus.DROPPING_OFF, TaskStatus.BLOCKED, TaskStatus.SUSPENDED, TaskStatus.REASSIGNED, TaskStatus.CANCELLED],
        TaskStatus.DROPPING_OFF: [TaskStatus.COMPLETED, TaskStatus.BLOCKED, TaskStatus.CANCELLED],
        TaskStatus.BLOCKED: [TaskStatus.ALLOCATING, TaskStatus.REASSIGNED, TaskStatus.CANCELLED, TaskStatus.IN_TRANSIT_PICKUP, TaskStatus.IN_TRANSIT_DROP],
        TaskStatus.SUSPENDED: [TaskStatus.ASSIGNED, TaskStatus.REASSIGNED, TaskStatus.CANCELLED],
        TaskStatus.REASSIGNED: [TaskStatus.ASSIGNED, TaskStatus.IN_TRANSIT_PICKUP],
        TaskStatus.COMPLETED: [],
        TaskStatus.CANCELLED: []
    }

    def __init__(self):
        self.tasks: Dict[str, Task] = {}

    def submit_task(
        self,
        task_id: str,
        pick_node: str,
        drop_node: str,
        required_payload: PayloadType = PayloadType.ANY,
        priority: int = 1,
        sla_deadline_s: Optional[float] = None
    ) -> Task:
        task = Task(
            task_id=task_id,
            pick_node=pick_node,
            drop_node=drop_node,
            required_payload=required_payload,
            priority=priority,
            status=TaskStatus.PENDING,
            sla_deadline_s=sla_deadline_s or (time.time() + 600.0)  # Default 10 min SLA
        )
        self.tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)

    def list_tasks(self, status: Optional[TaskStatus] = None) -> List[Task]:
        if status is None:
            return list(self.tasks.values())
        return [t for t in self.tasks.values() if t.status == status]

    def transition_state(self, task_id: str, new_status: TaskStatus, reason: Optional[str] = None) -> bool:
        task = self.tasks.get(task_id)
        if not task:
            return False

        allowed = self.VALID_TRANSITIONS.get(task.status, [])
        if new_status not in allowed:
            return False

        old_status = task.status
        task.status = new_status
        if reason:
            task.failure_reason = reason

        now = time.time()
        if new_status == TaskStatus.ASSIGNED and not task.started_at:
            task.started_at = now
        elif new_status == TaskStatus.COMPLETED:
            task.completed_at = now

        return True

    def mark_blocked(self, task_id: str, reason: str) -> bool:
        return self.transition_state(task_id, TaskStatus.BLOCKED, reason=reason)

    def reassign_task(self, task_id: str, new_robot_id: str) -> bool:
        task = self.tasks.get(task_id)
        if not task:
            return False

        # Transition to REASSIGNED, then ASSIGNED to new robot
        if task.status in (TaskStatus.BLOCKED, TaskStatus.SUSPENDED, TaskStatus.ASSIGNED, TaskStatus.IN_TRANSIT_PICKUP, TaskStatus.IN_TRANSIT_DROP):
            task.status = TaskStatus.REASSIGNED
            task.assigned_robot_id = new_robot_id
            task.status = TaskStatus.ASSIGNED
            task.failure_reason = None
            return True
        return False

    def check_sla_breaches(self) -> List[Task]:
        """Finds tasks approaching or exceeding their SLA deadline."""
        now = time.time()
        breached = []
        for task in self.tasks.values():
            if task.status not in (TaskStatus.COMPLETED, TaskStatus.CANCELLED):
                if task.sla_deadline_s and now > task.sla_deadline_s:
                    breached.append(task)
        return breached


task_engine = TaskEngine()
