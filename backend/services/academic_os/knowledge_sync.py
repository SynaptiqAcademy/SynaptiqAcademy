"""Knowledge Synchronization — cross-module sync events for data consistency."""
from __future__ import annotations

import threading
import time

from .models import SyncEvent, SyncChangeType

_MAX_EVENTS     = 5_000
_MAX_QUEUE_DEPTH = 200

# Module → which other modules should be notified of its changes
_SYNC_MAP: dict[str, list[str]] = {
    "project_center":      ["knowledge_graph", "analytics", "career", "institution"],
    "manuscript":          ["project_center", "knowledge_graph", "publishing"],
    "citation_monitoring": ["research_impact", "career", "institution"],
    "grant":               ["project_center", "career", "institution", "analytics"],
    "collaboration":       ["project_center", "reputation", "analytics"],
    "knowledge_graph":     ["copilot", "recommendation_engine", "search"],
    "career":              ["dashboard", "reputation", "analytics"],
    "institution":         ["analytics", "benchmarking", "dashboard"],
    "publication":         ["project_center", "citation_monitoring", "career", "research_impact"],
    "teaching":            ["career", "reputation", "analytics"],
    "reputation":          ["dashboard", "recommendation_engine"],
}


class KnowledgeSync:
    def __init__(self):
        self._lock    = threading.Lock()
        self._log:    list[SyncEvent]   = []
        self._queue:  list[SyncEvent]   = []
        self._results: dict[str, dict]  = {}  # sync_id → processing results

    # ── Emit ──────────────────────────────────────────────────────────────────

    def emit(
        self,
        source_module:  str,
        entity_type:    str,
        entity_id:      str,
        change_type:    str,
        payload:        dict | None = None,
        target_modules: list[str] | None = None,
    ) -> SyncEvent:
        targets = target_modules or _SYNC_MAP.get(source_module, [])
        event   = SyncEvent(
            source_module=source_module,
            target_modules=targets,
            entity_type=entity_type,
            entity_id=entity_id,
            change_type=change_type,
            payload=payload or {},
            status="pending",
        )
        with self._lock:
            self._log.append(event)
            if len(self._log) > _MAX_EVENTS:
                self._log.pop(0)
            self._queue.append(event)
            if len(self._queue) > _MAX_QUEUE_DEPTH:
                self._queue.pop(0)
        return event

    # ── Processing ────────────────────────────────────────────────────────────

    def process_pending(self, max_batch: int = 20) -> list[dict]:
        """Process queued sync events — marks them processed with placeholder results."""
        with self._lock:
            batch = self._queue[:max_batch]
            self._queue = self._queue[max_batch:]

        processed = []
        now = time.time()
        for event in batch:
            result = {m: "propagated" for m in event.target_modules}
            event.status       = "processed"
            event.processed_at = now
            event.results      = result
            with self._lock:
                self._results[event.sync_id] = result
            processed.append(event.to_dict())
        return processed

    def get_event(self, sync_id: str) -> SyncEvent | None:
        with self._lock:
            for e in self._log:
                if e.sync_id == sync_id:
                    return e
        return None

    def get_log(
        self,
        source_module: str | None = None,
        entity_type:   str | None = None,
        limit:         int         = 50,
    ) -> list[SyncEvent]:
        with self._lock:
            events = list(self._log)
        if source_module:
            events = [e for e in events if e.source_module == source_module]
        if entity_type:
            events = [e for e in events if e.entity_type == entity_type]
        return list(reversed(events))[:limit]

    def get_targets(self, source_module: str) -> list[str]:
        return list(_SYNC_MAP.get(source_module, []))

    def queue_depth(self) -> int:
        with self._lock:
            return len(self._queue)

    def stats(self) -> dict:
        with self._lock:
            total    = len(self._log)
            pending  = len(self._queue)
            by_type: dict[str, int] = {}
            for e in self._log:
                by_type[e.change_type] = by_type.get(e.change_type, 0) + 1
        return {"total_events": total, "pending": pending, "by_change_type": by_type}
