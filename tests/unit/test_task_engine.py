import pytest
from fms.tasks.task_engine import TaskEngine
from fms.models.domain_models import TaskStatus, PayloadType


def test_task_engine_lifecycle_and_transitions():
    te = TaskEngine()
    task = te.submit_task(
        task_id="TASK-100",
        pick_node="N_0_0",
        drop_node="N_2_2",
        required_payload=PayloadType.SCISSOR_LIFT,
        priority=1
    )
    assert task.status == TaskStatus.PENDING

    # Transition to ALLOCATING -> ASSIGNED
    assert te.transition_state("TASK-100", TaskStatus.ALLOCATING) is True
    assert te.transition_state("TASK-100", TaskStatus.ASSIGNED) is True

    # Transit to pickup
    assert te.transition_state("TASK-100", TaskStatus.IN_TRANSIT_PICKUP) is True

    # Cannot transition directly to COMPLETED from IN_TRANSIT_PICKUP
    assert te.transition_state("TASK-100", TaskStatus.COMPLETED) is False

    # Mark BLOCKED
    assert te.mark_blocked("TASK-100", reason="Aisle blocked by obstacle") is True
    assert te.get_task("TASK-100").status == TaskStatus.BLOCKED

    # Reassign to another AMR
    assert te.reassign_task("TASK-100", new_robot_id="synq-amr-03") is True
    assert te.get_task("TASK-100").assigned_robot_id == "synq-amr-03"
    assert te.get_task("TASK-100").status == TaskStatus.ASSIGNED
