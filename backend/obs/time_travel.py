"""
Time Travel Debugging — Phase XXXV.6

Given a Trace ID, reconstructs the complete execution timeline:
  - HTTP request (from obs_traces)
  - All spans (from obs_spans)
  - Structured logs (from obs_logs)
  - Audit records (from obs_audit)
  - Security events (from obs_security)
  - Worker jobs (from worker_jobs)
  - AI cost records (from obs_cost)

All entries are merged into a single chronological timeline so operators
can replay exactly what happened during any request or mission.

Usage:
    traveler = TimeTraveler(db)
    result = await traveler.rebuild("trace-id-here")
    # result.timeline is a sorted list of timestamped events
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TimelineEvent:
    timestamp: str
    category:  str    # trace | span | log | audit | security | worker | cost
    source:    str
    summary:   str
    details:   dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "category":  self.category,
            "source":    self.source,
            "summary":   self.summary,
            "details":   self.details,
        }


@dataclass
class TimeTravelResult:
    trace_id:  str
    trace:     dict | None
    spans:     list[dict]
    logs:      list[dict]
    audit:     list[dict]
    security:  list[dict]
    jobs:      list[dict]
    costs:     list[dict]
    timeline:  list[dict]
    rebuilt_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    error:     str | None = None

    def to_dict(self) -> dict:
        return {
            "trace_id":   self.trace_id,
            "trace":      self.trace,
            "spans":      self.spans,
            "logs":       self.logs,
            "audit":      self.audit,
            "security":   self.security,
            "jobs":       self.jobs,
            "costs":      self.costs,
            "timeline":   self.timeline,
            "rebuilt_at": self.rebuilt_at,
            "error":      self.error,
            "summary": {
                "span_count":  len(self.spans),
                "log_count":   len(self.logs),
                "audit_count": len(self.audit),
                "job_count":   len(self.jobs),
                "cost_total":  round(sum(c.get("cost_usd", 0) for c in self.costs), 6),
            },
        }


class TimeTraveler:

    def __init__(self, db: Any) -> None:
        self._db = db

    async def rebuild(self, trace_id: str) -> TimeTravelResult:
        """Reconstruct the full execution timeline for a given trace ID."""
        events: list[TimelineEvent] = []

        # 1. Root trace
        trace = None
        try:
            trace = await self._db["obs_traces"].find_one(
                {"trace_id": trace_id}, {"_id": 0}
            )
            if trace:
                events.append(TimelineEvent(
                    timestamp=trace.get("started_at", ""),
                    category="trace",
                    source="obs_traces",
                    summary=f"{trace.get('method', 'REQ')} {trace.get('path', '/')} — trace started",
                    details=trace,
                ))
        except Exception as exc:
            logger.debug("TimeTraveler trace fetch: %s", exc)

        # 2. Spans
        spans: list[dict] = []
        try:
            spans = await self._db["obs_spans"].find(
                {"trace_id": trace_id}, {"_id": 0}
            ).sort("started_at", 1).to_list(500)
            for s in spans:
                events.append(TimelineEvent(
                    timestamp=s.get("started_at", ""),
                    category="span",
                    source="obs_spans",
                    summary=f"[{s.get('component', '?')}] {s.get('name', '?')} ({s.get('duration_ms', 0):.0f}ms) — {s.get('status', '?')}",
                    details=s,
                ))
        except Exception as exc:
            logger.debug("TimeTraveler spans fetch: %s", exc)

        # 3. Structured logs
        logs: list[dict] = []
        try:
            logs = await self._db["obs_logs"].find(
                {"trace_id": trace_id}, {"_id": 0}
            ).sort("timestamp", 1).to_list(500)
            for lg in logs:
                events.append(TimelineEvent(
                    timestamp=lg.get("timestamp", ""),
                    category="log",
                    source="obs_logs",
                    summary=f"[{lg.get('level', 'LOG')}] {lg.get('logger', '?')}: {lg.get('message', '')[:120]}",
                    details=lg,
                ))
        except Exception as exc:
            logger.debug("TimeTraveler logs fetch: %s", exc)

        # 4. Audit records
        audit: list[dict] = []
        try:
            audit = await self._db["obs_audit"].find(
                {"trace_id": trace_id}, {"_id": 0}
            ).sort("timestamp", 1).to_list(200)
            for a in audit:
                events.append(TimelineEvent(
                    timestamp=a.get("timestamp", ""),
                    category="audit",
                    source="obs_audit",
                    summary=f"AUDIT {a.get('who', '?')} → {a.get('action', '?')} on {a.get('resource', '?')}",
                    details=a,
                ))
        except Exception as exc:
            logger.debug("TimeTraveler audit fetch: %s", exc)

        # 5. Security events
        security: list[dict] = []
        try:
            security = await self._db["obs_security"].find(
                {"trace_id": trace_id}, {"_id": 0}
            ).sort("timestamp", 1).to_list(100)
            for se in security:
                events.append(TimelineEvent(
                    timestamp=se.get("timestamp", ""),
                    category="security",
                    source="obs_security",
                    summary=f"SECURITY [{se.get('severity', '?')}] {se.get('event_type', '?')}",
                    details=se,
                ))
        except Exception as exc:
            logger.debug("TimeTraveler security fetch: %s", exc)

        # 6. Worker jobs
        jobs: list[dict] = []
        try:
            jobs = await self._db["worker_jobs"].find(
                {"correlation_id": trace_id}, {"_id": 0}
            ).sort("created_at", 1).to_list(100)
            for j in jobs:
                ts = j.get("queued_at") or j.get("created_at") or ""
                events.append(TimelineEvent(
                    timestamp=ts,
                    category="worker",
                    source="worker_jobs",
                    summary=f"JOB {j.get('job_type', '?')} [{j.get('status', '?')}] (attempt {j.get('attempt', 0)})",
                    details=j,
                ))
        except Exception as exc:
            logger.debug("TimeTraveler jobs fetch: %s", exc)

        # 7. Cost records
        costs: list[dict] = []
        try:
            costs = await self._db["obs_cost"].find(
                {"trace_id": trace_id}, {"_id": 0}
            ).sort("timestamp", 1).to_list(100)
            for c in costs:
                events.append(TimelineEvent(
                    timestamp=c.get("timestamp", ""),
                    category="cost",
                    source="obs_cost",
                    summary=f"AI COST ${c.get('cost_usd', 0):.6f} — {c.get('provider', '?')}/{c.get('model', '?')}",
                    details=c,
                ))
        except Exception as exc:
            logger.debug("TimeTraveler costs fetch: %s", exc)

        # Sort all events chronologically
        events.sort(key=lambda e: e.timestamp or "")
        timeline = [e.to_dict() for e in events]

        return TimeTravelResult(
            trace_id=trace_id,
            trace=trace,
            spans=spans,
            logs=logs,
            audit=audit,
            security=security,
            jobs=jobs,
            costs=costs,
            timeline=timeline,
        )

    async def find_trace_id(self, mission_id: str) -> list[str]:
        """Find all trace IDs associated with a mission."""
        try:
            docs = await self._db["obs_traces"].find(
                {"mission_id": mission_id}, {"_id": 0, "trace_id": 1}
            ).limit(50).to_list(50)
            return [d["trace_id"] for d in docs]
        except Exception:
            return []


# ── Singleton ─────────────────────────────────────────────────────────────────

_traveler: TimeTraveler | None = None


def init_time_travel(db: Any) -> TimeTraveler:
    global _traveler
    _traveler = TimeTraveler(db)
    return _traveler


def get_time_traveler() -> TimeTraveler | None:
    return _traveler
