"""
Security Observability — Phase XXXV.6

Tracks all security-relevant events:
  - Failed login attempts
  - Permission violations
  - Prompt injection attempts
  - Suspicious AI requests
  - Rate limit hits
  - Abnormal usage patterns
  - Data export events
  - Privilege escalation attempts

Events are classified by severity (LOW → CRITICAL) and persisted to
MongoDB `obs_security` for compliance and forensic analysis.

Usage:
    from obs.security import get_security_observer
    await get_security_observer().record(
        event_type="permission.violation",
        user_id="u123",
        severity="HIGH",
        details={"attempted_resource": "/api/admin/users"},
    )
"""
from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

_COL = "obs_security"

# Event type constants
EVT_FAILED_LOGIN         = "auth.failed_login"
EVT_PERMISSION_VIOLATION = "auth.permission_violation"
EVT_PROMPT_INJECTION     = "ai.prompt_injection"
EVT_SUSPICIOUS_AI        = "ai.suspicious_request"
EVT_RATE_LIMIT           = "api.rate_limit_exceeded"
EVT_ABNORMAL_USAGE       = "api.abnormal_usage"
EVT_DATA_EXPORT          = "data.export"
EVT_PRIVILEGE_ESCALATION = "auth.privilege_escalation"
EVT_BRUTE_FORCE          = "auth.brute_force"
EVT_TOKEN_REUSE          = "auth.token_reuse"
EVT_CSRF_ATTEMPT         = "auth.csrf_attempt"

# Severity levels
SEV_LOW      = "LOW"
SEV_MEDIUM   = "MEDIUM"
SEV_HIGH     = "HIGH"
SEV_CRITICAL = "CRITICAL"

_SEV_RANK = {SEV_LOW: 0, SEV_MEDIUM: 1, SEV_HIGH: 2, SEV_CRITICAL: 3}


@dataclass
class SecurityEvent:
    event_id:    str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    timestamp:   str = field(default_factory=lambda: datetime.utcnow().isoformat())
    event_type:  str = ""
    severity:    str = SEV_LOW
    user_id:     str | None = None
    ip_address:  str | None = None
    user_agent:  str | None = None
    trace_id:    str | None = None
    path:        str | None = None
    method:      str | None = None
    details:     dict = field(default_factory=dict)
    resolved:    bool = False

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None and v is not False}


class SecurityObserver:

    def __init__(self, db: Any) -> None:
        self._db   = db
        self._lock = threading.Lock()
        # In-memory counters for fast alerting
        self._counts: dict[str, int] = {}

    async def record(
        self,
        event_type: str,
        severity:   str = SEV_LOW,
        user_id:    str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        trace_id:   str | None = None,
        path:       str | None = None,
        method:     str | None = None,
        details:    dict | None = None,
    ) -> str:
        evt = SecurityEvent(
            event_type=event_type, severity=severity,
            user_id=user_id, ip_address=ip_address, user_agent=user_agent,
            trace_id=trace_id, path=path, method=method,
            details=details or {},
        )
        with self._lock:
            self._counts[event_type] = self._counts.get(event_type, 0) + 1
        try:
            await self._db[_COL].insert_one(evt.to_dict())
        except Exception as exc:
            logger.debug("SecurityObserver.record error: %s", exc)
        # Update global metrics
        try:
            from obs.metrics import get_metrics, M_SEC_VIOLATIONS, M_SEC_INJECTIONS, M_SEC_FAILED_LOGIN
            m = get_metrics()
            m.inc("security.events", tags={"type": event_type, "severity": severity})
            if event_type == EVT_PERMISSION_VIOLATION:
                m.inc(M_SEC_VIOLATIONS)
            if event_type == EVT_PROMPT_INJECTION:
                m.inc(M_SEC_INJECTIONS)
            if event_type == EVT_FAILED_LOGIN:
                m.inc(M_SEC_FAILED_LOGIN)
        except Exception:
            pass
        if _SEV_RANK.get(severity, 0) >= _SEV_RANK[SEV_HIGH]:
            logger.warning("SECURITY [%s] %s user=%s path=%s details=%s",
                           severity, event_type, user_id, path, details)
        return evt.event_id

    async def query(
        self,
        event_type: str | None = None,
        severity:   str | None = None,
        user_id:    str | None = None,
        from_ts:    str | None = None,
        to_ts:      str | None = None,
        resolved:   bool | None = None,
        limit:      int = 100,
    ) -> list[dict]:
        try:
            filt: dict = {}
            if event_type: filt["event_type"] = event_type
            if severity:   filt["severity"]   = severity
            if user_id:    filt["user_id"]    = user_id
            if resolved is not None: filt["resolved"] = resolved
            if from_ts or to_ts:
                ts: dict = {}
                if from_ts: ts["$gte"] = from_ts
                if to_ts:   ts["$lte"] = to_ts
                filt["timestamp"] = ts
            return await self._db[_COL].find(
                filt, {"_id": 0}
            ).sort("timestamp", -1).limit(limit).to_list(limit)
        except Exception as exc:
            logger.debug("SecurityObserver.query error: %s", exc)
            return []

    def summary(self) -> dict:
        with self._lock:
            counts = dict(self._counts)
        return {
            "event_counts": counts,
            "total":        sum(counts.values()),
            "high_severity": sum(v for k, v in counts.items()
                                  if any(k.startswith(p) for p in ("auth.privilege", "ai.prompt", "auth.brute"))),
        }

    async def recent_high_severity(self, limit: int = 20) -> list[dict]:
        return await self.query(severity=SEV_HIGH, limit=limit)

    async def ensure_indexes(self) -> None:
        try:
            await self._db[_COL].create_index("timestamp")
            await self._db[_COL].create_index("user_id")
            await self._db[_COL].create_index("event_type")
            await self._db[_COL].create_index("severity")
        except Exception as exc:
            logger.debug("SecurityObserver.ensure_indexes: %s", exc)


# ── Singleton ─────────────────────────────────────────────────────────────────

_observer: SecurityObserver | None = None


def init_security(db: Any) -> SecurityObserver:
    global _observer
    _observer = SecurityObserver(db)
    return _observer


def get_security_observer() -> SecurityObserver | None:
    return _observer
