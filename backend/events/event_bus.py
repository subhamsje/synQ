import asyncio
import uuid
import time
from typing import Dict, List, Callable, Any, Set
from collections import deque
import fnmatch

from backend.events.event_types import OperationalEvent, EventType, EventSeverity


class OperationalEventBus:
    """
    Central Asynchronous Event Bus for the FLTX Autonomous Platform.
    Enables decoupled publish-subscribe communication across Fleet Management,
    Health Monitoring, Analytics, Incident Recovery, and Notifications.
    """

    def __init__(self, history_limit: int = 1000):
        self.subscribers: Dict[str, List[Callable[[OperationalEvent], Any]]] = {}
        self.history: deque[OperationalEvent] = deque(maxlen=history_limit)
        self._lock = asyncio.Lock()

    def subscribe(self, pattern: str, handler: Callable[[OperationalEvent], Any]):
        """
        Subscribes a handler to an event pattern.
        Pattern examples: "robot.*", "mission.completed", "*".
        """
        if pattern not in self.subscribers:
            self.subscribers[pattern] = []
        self.subscribers[pattern].append(handler)

    def unsubscribe(self, pattern: str, handler: Callable[[OperationalEvent], Any]):
        if pattern in self.subscribers and handler in self.subscribers[pattern]:
            self.subscribers[pattern].remove(handler)

    async def publish(
        self,
        event_type: EventType,
        source_entity: str,
        message: str,
        severity: EventSeverity = EventSeverity.INFO,
        metadata: Dict[str, Any] = None,
        event_id: str = None
    ) -> OperationalEvent:
        """
        Constructs and asynchronously publishes an event to all matching subscribers.
        """
        if metadata is None:
            metadata = {}
        if event_id is None:
            event_id = f"EVT-{int(time.time()*1000)}-{uuid.uuid4().hex[:6]}"

        event = OperationalEvent(
            event_id=event_id,
            event_type=event_type,
            severity=severity,
            source_entity=source_entity,
            message=message,
            timestamp=time.time(),
            metadata=metadata
        )

        self.history.append(event)

        # Dispatch to matching subscribers
        matched_handlers: Set[Callable[[OperationalEvent], Any]] = set()
        for pattern, handlers in self.subscribers.items():
            if pattern == "*" or fnmatch.fnmatch(event.event_type.value, pattern):
                for h in handlers:
                    matched_handlers.add(h)

        for handler in matched_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    asyncio.create_task(handler(event))
                else:
                    handler(event)
            except Exception as e:
                print(f"[EventBus Error] Exception in handler {handler}: {e}")

        return event

    def get_recent_events(self, limit: int = 50, min_severity: EventSeverity = None) -> List[OperationalEvent]:
        events = list(self.history)
        if min_severity:
            sev_levels = {
                EventSeverity.INFO: 1,
                EventSeverity.DAILY_SUMMARY: 2,
                EventSeverity.WARNING: 3,
                EventSeverity.CRITICAL: 4
            }
            target_level = sev_levels.get(min_severity, 1)
            events = [e for e in events if sev_levels.get(e.severity, 1) >= target_level]

        return events[-limit:]


# Global Singleton Event Bus Instance
event_bus = OperationalEventBus()
