"""
Security Monitor — Phase XXXV.8

Detects anomalies, credential abuse, privilege escalation, data exfiltration,
impossible travel, and other threat signals.
"""
from __future__ import annotations

import logging
import secrets
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

_COL = "zt_security_events"


class AnomalyType(str, Enum):
    CREDENTIAL_ABUSE       = "credential_abuse"
    PRIVILEGE_ESCALATION   = "privilege_escalation"
    SUSPICIOUS_AI_USAGE    = "suspicious_ai_usage"
    EXCESSIVE_API_USAGE    = "excessive_api_usage"
    DATA_EXFILTRATION      = "data_exfiltration"
    IMPOSSIBLE_TRAVEL      = "impossible_travel"
    MULTIPLE_FAILED_LOGINS = "multiple_failed_logins"
    INSTITUTION_VIOLATION  = "institution_violation"
    ANOMALOUS_BEHAVIOR     = "anomalous_behavior"
    MASS_DATA_ACCESS       = "mass_data_access"
    OFF_HOURS_ADMIN        = "off_hours_admin"


class EventSeverity(str, Enum):
    INFO     = "info"
    WARNING  = "warning"
    HIGH     = "high"
    CRITICAL = "critical"


@dataclass
class SecurityEvent:
    event_id:     str
    event_type:   AnomalyType
    severity:     EventSeverity
    subject_id:   str
    description:  str
    ip:           str        = ""
    path:         str        = ""
    metadata:     dict       = field(default_factory=dict)
    timestamp:    str        = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    resolved:     bool       = False
    resolved_at:  str | None = None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


class SecurityMonitor:

    def __init__(self, db: Any) -> None:
        self._db           = db
        self._col          = db[_COL]
        # In-memory sliding windows (user_id → deque of timestamps)
        self._request_window:  dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        self._failed_auths:    dict[str, int]    = defaultdict(int)
        self._ai_requests:     dict[str, int]    = defaultdict(int)
        self._ip_user_map:     dict[str, set]    = defaultdict(set)   # ip → user_ids
        self._event_buffer:    deque             = deque(maxlen=5000)

    async def ensure_indexes(self) -> None:
        try:
            await self._col.create_index("event_id", unique=True)
            await self._col.create_index([("subject_id", 1), ("timestamp", -1)])
            await self._col.create_index([("event_type", 1), ("severity", 1)])
            await self._col.create_index("timestamp")
        except Exception as exc:
            logger.debug("Security monitor index: %s", exc)

    async def record_event(
        self,
        event_type:  AnomalyType,
        severity:    EventSeverity,
        subject_id:  str,
        description: str,
        ip:          str       = "",
        path:        str       = "",
        metadata:    dict | None = None,
    ) -> SecurityEvent:
        evt = SecurityEvent(
            event_id    = "zse_" + secrets.token_hex(8),
            event_type  = event_type,
            severity    = severity,
            subject_id  = subject_id,
            description = description,
            ip          = ip,
            path        = path,
            metadata    = metadata or {},
        )
        self._event_buffer.append(evt.to_dict())
        try:
            await self._col.insert_one(evt.to_dict())
        except Exception as exc:
            logger.debug("Security event persist: %s", exc)
        if severity in (EventSeverity.HIGH, EventSeverity.CRITICAL):
            logger.warning("SECURITY EVENT [%s] %s: %s", severity, event_type, description)
        return evt

    # ── Signal tracking ───────────────────────────────────────────────────────

    def track_request(self, user_id: str, ip: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._request_window[user_id].append(now)
        self._ip_user_map[ip].add(user_id)

    def track_failed_auth(self, user_id: str) -> int:
        self._failed_auths[user_id] += 1
        return self._failed_auths[user_id]

    def reset_failed_auth(self, user_id: str) -> None:
        self._failed_auths[user_id] = 0

    def track_ai_request(self, user_id: str) -> int:
        self._ai_requests[user_id] += 1
        return self._ai_requests[user_id]

    def failed_auth_count(self, user_id: str) -> int:
        return self._failed_auths.get(user_id, 0)

    # ── Anomaly detection ─────────────────────────────────────────────────────

    async def check_anomalies(
        self,
        user_id: str,
        ip:      str  = "",
        path:    str  = "",
    ) -> list[SecurityEvent]:
        events: list[SecurityEvent] = []

        # Multiple failed logins
        fails = self._failed_auths.get(user_id, 0)
        if fails >= 10:
            evt = await self.record_event(
                AnomalyType.MULTIPLE_FAILED_LOGINS, EventSeverity.CRITICAL,
                user_id, f"{fails} consecutive failed login attempts", ip=ip,
            )
            events.append(evt)
        elif fails >= 5:
            evt = await self.record_event(
                AnomalyType.MULTIPLE_FAILED_LOGINS, EventSeverity.HIGH,
                user_id, f"{fails} failed login attempts", ip=ip,
            )
            events.append(evt)

        # Excessive API usage (>200 requests in window)
        req_count = len(self._request_window.get(user_id, []))
        if req_count > 500:
            evt = await self.record_event(
                AnomalyType.EXCESSIVE_API_USAGE, EventSeverity.HIGH,
                user_id, f"{req_count} requests in window", ip=ip, path=path,
            )
            events.append(evt)

        # Suspicious AI usage (>100 AI requests)
        ai_count = self._ai_requests.get(user_id, 0)
        if ai_count > 200:
            evt = await self.record_event(
                AnomalyType.SUSPICIOUS_AI_USAGE, EventSeverity.WARNING,
                user_id, f"{ai_count} AI requests in session", ip=ip,
            )
            events.append(evt)

        # Same IP used by many users (possible credential sharing)
        ip_users = self._ip_user_map.get(ip, set())
        if len(ip_users) > 20:
            evt = await self.record_event(
                AnomalyType.CREDENTIAL_ABUSE, EventSeverity.WARNING,
                user_id, f"IP {ip} shared by {len(ip_users)} users", ip=ip,
            )
            events.append(evt)

        return events

    async def list_events(
        self,
        subject_id:  str | None = None,
        event_type:  AnomalyType | None = None,
        severity:    EventSeverity | None = None,
        limit:       int = 100,
    ) -> list[dict]:
        filt: dict = {}
        if subject_id:
            filt["subject_id"] = subject_id
        if event_type:
            filt["event_type"] = event_type
        if severity:
            filt["severity"] = severity

        docs = []
        async for doc in self._col.find(filt).sort("timestamp", -1).limit(limit):
            doc.pop("_id", None)
            docs.append(doc)
        return docs

    async def resolve_event(self, event_id: str) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        r   = await self._col.update_one(
            {"event_id": event_id},
            {"$set": {"resolved": True, "resolved_at": now}},
        )
        return r.modified_count > 0

    def summary(self) -> dict:
        events = list(self._event_buffer)
        return {
            "total_events":   len(events),
            "critical":       sum(1 for e in events if e.get("severity") == EventSeverity.CRITICAL),
            "high":           sum(1 for e in events if e.get("severity") == EventSeverity.HIGH),
            "warning":        sum(1 for e in events if e.get("severity") == EventSeverity.WARNING),
            "active_users":   len(self._request_window),
            "flagged_users":  sum(1 for c in self._failed_auths.values() if c >= 3),
        }

    def recent_buffer(self, limit: int = 50) -> list[dict]:
        return list(self._event_buffer)[-limit:]


# ── Singleton ─────────────────────────────────────────────────────────────────

_monitor: SecurityMonitor | None = None


def init_monitoring(db: Any) -> SecurityMonitor:
    global _monitor
    _monitor = SecurityMonitor(db)
    return _monitor


def get_monitor() -> SecurityMonitor:
    if _monitor is None:
        raise RuntimeError("SecurityMonitor not initialised")
    return _monitor
