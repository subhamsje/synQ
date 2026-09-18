import pytest
import asyncio
from backend.events.event_bus import OperationalEventBus
from backend.events.event_types import EventType, EventSeverity, OperationalEvent


@pytest.mark.anyio
async def test_event_bus_publish_and_subscribe():
    bus = OperationalEventBus()
    received_events = []

    def handler(event: OperationalEvent):
        received_events.append(event)

    bus.subscribe("mission.completed", handler)

    evt = await bus.publish(
        event_type=EventType.MISSION_COMPLETED,
        source_entity="AMR-01",
        message="Mission TASK-1001 finished.",
        severity=EventSeverity.INFO,
        metadata={"duration_s": 240.0}
    )

    assert len(received_events) == 1
    assert received_events[0].event_type == EventType.MISSION_COMPLETED
    assert received_events[0].source_entity == "AMR-01"
    assert received_events[0].metadata["duration_s"] == 240.0


@pytest.mark.anyio
async def test_event_bus_wildcard_matching():
    bus = OperationalEventBus()
    robot_events = []
    all_events = []

    bus.subscribe("robot.*", lambda e: robot_events.append(e))
    bus.subscribe("*", lambda e: all_events.append(e))

    await bus.publish(EventType.ROBOT_FAULT, "AMR-07", "Battery degraded", EventSeverity.WARNING)
    await bus.publish(EventType.MISSION_STARTED, "AMR-02", "Started TASK-200", EventSeverity.INFO)

    assert len(robot_events) == 1
    assert robot_events[0].source_entity == "AMR-07"
    assert len(all_events) == 2


@pytest.mark.anyio
async def test_event_bus_severity_filtering():
    bus = OperationalEventBus()
    await bus.publish(EventType.MISSION_CREATED, "DISPATCH", "Created", EventSeverity.INFO)
    await bus.publish(EventType.ROBOT_FAULT, "AMR-03", "Fault", EventSeverity.CRITICAL)

    recent_critical = bus.get_recent_events(limit=10, min_severity=EventSeverity.CRITICAL)
    assert len(recent_critical) == 1
    assert recent_critical[0].severity == EventSeverity.CRITICAL
