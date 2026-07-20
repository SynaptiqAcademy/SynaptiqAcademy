"""Global Activity Timeline — unified event feed across all platform modules."""
from __future__ import annotations

import threading
import time

from .models import ActivityEvent

_MAX_EVENTS = 10_000


class ActivityTimeline:
    def __init__(self):
        self._lock    = threading.Lock()
        self._events: list[ActivityEvent] = []

    def record_event(
        self,
        event_type:  str,
        entity_type: str  = "",
        entity_id:   str  = "",
        user_cohort: str  = "general",
        description: str  = "",
        project_id:  str  = "",
        metadata:    dict | None = None,
    ) -> ActivityEvent:
        event = ActivityEvent(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            user_cohort=user_cohort,
            description=description,
            project_id=project_id,
            metadata=metadata or {},
        )
        with self._lock:
            self._events.append(event)
            if len(self._events) > _MAX_EVENTS:
                self._events.pop(0)
        return event

    def get_timeline(
        self,
        user_cohort:  str | None       = None,
        event_types:  list[str] | None = None,
        entity_types: list[str] | None = None,
        project_id:   str | None       = None,
        since:        float | None     = None,
        limit:        int               = 50,
    ) -> list[ActivityEvent]:
        with self._lock:
            events = list(self._events)
        if user_cohort:
            events = [e for e in events if e.user_cohort in (user_cohort, "general")]
        if event_types:
            events = [e for e in events if e.event_type in event_types]
        if entity_types:
            events = [e for e in events if e.entity_type in entity_types]
        if project_id:
            events = [e for e in events if e.project_id == project_id]
        if since:
            events = [e for e in events if e.timestamp >= since]
        return list(reversed(events))[:limit]

    def get_project_timeline(self, project_id: str, limit: int = 50) -> list[ActivityEvent]:
        return self.get_timeline(project_id=project_id, limit=limit)

    def get_recent_activity(self, limit: int = 20) -> list[ActivityEvent]:
        with self._lock:
            return list(reversed(self._events[-limit:]))

    def count_since(self, since: float) -> int:
        with self._lock:
            return sum(1 for e in self._events if e.timestamp >= since)

    def summary(self) -> dict:
        with self._lock:
            by_type: dict[str, int] = {}
            for e in self._events:
                by_type[e.event_type] = by_type.get(e.event_type, 0) + 1
        return {"total_events": len(self._events), "by_type": by_type}
