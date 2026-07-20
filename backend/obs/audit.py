"""
Immutable Audit Log — Phase XXXV.6

Every important platform action is recorded here with:
  who, what, when, where, why, before/after state, AI involvement,
  evidence, approval status, mission context, and trace ID.

Records are NEVER updated or deleted — only appended.
The `obs_audit` collection has no TTL (compliance-grade retention).

Usage:
    from obs.audit import get_audit
    await get_audit().log(
        who="user:u123",
        action="manuscript.submitted",
        resource="manuscript:m456",
        trace_id=get_trace_id(),
        details={"journal": "Nature"},
        requires_human_approval=True,
    )
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

_COL = "obs_audit"


# ── Record type ───────────────────────────────────────────────────────────────

@dataclass
class AuditRecord:
    record_id:       str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp:       str = field(default_factory=lambda: datetime.utcnow().isoformat())
    who:             str = ""          # "user:<id>" | "agent:<name>" | "system"
    action:          str = ""          # verb.noun  e.g. "file.uploaded"
    resource:        str = ""          # "file:<id>" | "mission:<id>"
    resource_type:   str = ""
    resource_id:     str = ""
    # Context
    trace_id:        str | None = None
    mission_id:      str | None = None
    workspace_id:    str | None = None
    user_id:         str | None = None
    institution:     str | None = None
    correlation_id:  str | None = None
    # State
    before:          dict | None = None
    after:           dict | None = None
    details:         dict = field(default_factory=dict)
    # AI involvement
    ai_involved:     bool = False
    ai_provider:     str | None = None
    ai_model:        str | None = None
    evidence:        list = field(default_factory=list)
    # Approval
    requires_human_approval: bool = False
    approved_by:     str | None = None
    # Outcome
    status:          str = "success"   # success | failure | pending
    error:           str | None = None
    # Classification
    category:        str = "general"   # general | security | ai | mission | data | billing
    severity:        str = "info"      # info | warning | critical

    def to_dict(self) -> dict:
        d = self.__dict__.copy()
        return {k: v for k, v in d.items() if v is not None and v != [] and v != {}}


# ── Audit Logger ──────────────────────────────────────────────────────────────

class AuditLogger:

    def __init__(self, db: Any) -> None:
        self._db = db

    async def log(
        self,
        who:       str,
        action:    str,
        resource:  str = "",
        *,
        trace_id:           str | None = None,
        mission_id:         str | None = None,
        workspace_id:       str | None = None,
        user_id:            str | None = None,
        institution:        str | None = None,
        correlation_id:     str | None = None,
        before:             dict | None = None,
        after:              dict | None = None,
        details:            dict | None = None,
        ai_involved:        bool = False,
        ai_provider:        str | None = None,
        ai_model:           str | None = None,
        evidence:           list | None = None,
        requires_human_approval: bool = False,
        approved_by:        str | None = None,
        status:             str = "success",
        error:              str | None = None,
        category:           str = "general",
        severity:           str = "info",
    ) -> str:
        """Append an immutable audit record. Returns record_id."""
        # Parse resource into type/id
        parts = resource.split(":", 1) if ":" in resource else [resource, ""]
        rec = AuditRecord(
            who=who, action=action, resource=resource,
            resource_type=parts[0], resource_id=parts[1] if len(parts) > 1 else "",
            trace_id=trace_id, mission_id=mission_id, workspace_id=workspace_id,
            user_id=user_id, institution=institution, correlation_id=correlation_id,
            before=before, after=after, details=details or {},
            ai_involved=ai_involved, ai_provider=ai_provider, ai_model=ai_model,
            evidence=evidence or [],
            requires_human_approval=requires_human_approval, approved_by=approved_by,
            status=status, error=error, category=category, severity=severity,
        )
        try:
            await self._db[_COL].insert_one(rec.to_dict())
        except Exception as exc:
            logger.warning("AuditLogger.log error: %s", exc)
        return rec.record_id

    async def log_from_context(
        self, who: str, action: str, resource: str = "", **kwargs: Any
    ) -> str:
        """Auto-populate trace context fields."""
        try:
            from obs.tracer import get_context_dict
            ctx = get_context_dict()
            kwargs.setdefault("trace_id",      ctx.get("trace_id"))
            kwargs.setdefault("mission_id",    ctx.get("mission_id"))
            kwargs.setdefault("workspace_id",  ctx.get("workspace_id"))
            kwargs.setdefault("user_id",       ctx.get("user_id"))
            kwargs.setdefault("institution",   ctx.get("institution"))
            kwargs.setdefault("correlation_id", ctx.get("correlation_id"))
        except Exception:
            pass
        return await self.log(who, action, resource, **kwargs)

    async def query(
        self,
        user_id:       str | None = None,
        action:        str | None = None,
        resource_type: str | None = None,
        category:      str | None = None,
        trace_id:      str | None = None,
        mission_id:    str | None = None,
        from_ts:       str | None = None,
        to_ts:         str | None = None,
        status:        str | None = None,
        severity:      str | None = None,
        limit:         int = 100,
    ) -> list[dict]:
        try:
            filt: dict = {}
            if user_id:       filt["user_id"]       = user_id
            if action:        filt["action"]         = action
            if resource_type: filt["resource_type"]  = resource_type
            if category:      filt["category"]       = category
            if trace_id:      filt["trace_id"]       = trace_id
            if mission_id:    filt["mission_id"]     = mission_id
            if status:        filt["status"]         = status
            if severity:      filt["severity"]       = severity
            if from_ts or to_ts:
                ts_f: dict = {}
                if from_ts: ts_f["$gte"] = from_ts
                if to_ts:   ts_f["$lte"] = to_ts
                filt["timestamp"] = ts_f
            return await self._db[_COL].find(
                filt, {"_id": 0}
            ).sort("timestamp", -1).limit(limit).to_list(limit)
        except Exception as exc:
            logger.warning("AuditLogger.query error: %s", exc)
            return []

    async def get_record(self, record_id: str) -> dict | None:
        try:
            return await self._db[_COL].find_one({"record_id": record_id}, {"_id": 0})
        except Exception:
            return None

    async def ensure_indexes(self) -> None:
        try:
            await self._db[_COL].create_index("timestamp")
            await self._db[_COL].create_index("user_id")
            await self._db[_COL].create_index("trace_id")
            await self._db[_COL].create_index("action")
            await self._db[_COL].create_index("mission_id")
            await self._db[_COL].create_index("category")
        except Exception as exc:
            logger.debug("AuditLogger.ensure_indexes: %s", exc)


# ── Singleton ─────────────────────────────────────────────────────────────────

_audit: AuditLogger | None = None


def init_audit(db: Any) -> AuditLogger:
    global _audit
    _audit = AuditLogger(db)
    return _audit


def get_audit() -> AuditLogger | None:
    return _audit
