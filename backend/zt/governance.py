"""
Data Governance Engine — Phase XXXV.8

Tracks ownership, retention, classification, lineage, and consent for every data object.
"""
from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from .classification import ClassificationLevel

logger = logging.getLogger(__name__)

_COL_GOV     = "zt_governance"
_COL_LINEAGE = "zt_lineage"


@dataclass
class GovernanceRecord:
    object_id:    str
    object_type:  str                    # e.g. "manuscript", "twin", "ai_output"
    owner_id:     str
    classification: ClassificationLevel  = ClassificationLevel.INTERNAL
    created_at:   str                    = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at:   str                    = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    retain_until: str | None             = None
    delete_policy: str                   = "manual"  # manual | auto | on_request
    source:       str                    = "user"     # user | ai | import | system
    evidence:     list[str]              = field(default_factory=list)
    consent_ids:  list[str]              = field(default_factory=list)
    lineage_ids:  list[str]              = field(default_factory=list)
    metadata:     dict                   = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "object_id":      self.object_id,
            "object_type":    self.object_type,
            "owner_id":       self.owner_id,
            "classification": self.classification,
            "created_at":     self.created_at,
            "updated_at":     self.updated_at,
            "retain_until":   self.retain_until,
            "delete_policy":  self.delete_policy,
            "source":         self.source,
            "evidence":       self.evidence,
            "consent_ids":    self.consent_ids,
            "lineage_ids":    self.lineage_ids,
            "metadata":       self.metadata,
        }


@dataclass
class LineageRecord:
    lineage_id:  str
    object_id:   str
    operation:   str       # read | write | ai_inference | export | graph_update
    actor_id:    str
    timestamp:   str       = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    inputs:      list[str] = field(default_factory=list)   # upstream object_ids
    outputs:     list[str] = field(default_factory=list)   # downstream object_ids
    model:       str | None= None
    prompt_hash: str | None= None
    trace_id:    str | None= None

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


class DataGovernanceEngine:

    def __init__(self, db: Any) -> None:
        self._db      = db
        self._gov_col = db[_COL_GOV]
        self._lin_col = db[_COL_LINEAGE]

    async def ensure_indexes(self) -> None:
        try:
            await self._gov_col.create_index("object_id", unique=True)
            await self._gov_col.create_index([("owner_id", 1), ("object_type", 1)])
            await self._gov_col.create_index("classification")
            await self._lin_col.create_index("lineage_id", unique=True)
            await self._lin_col.create_index([("object_id", 1), ("timestamp", -1)])
            await self._lin_col.create_index("actor_id")
        except Exception as exc:
            logger.debug("Governance index: %s", exc)

    async def register(
        self,
        object_id:      str,
        object_type:    str,
        owner_id:       str,
        classification: ClassificationLevel = ClassificationLevel.INTERNAL,
        source:         str                 = "user",
        retain_days:    int | None          = None,
        evidence:       list[str] | None    = None,
        metadata:       dict | None         = None,
    ) -> GovernanceRecord:
        retain_until = None
        if retain_days:
            retain_until = (datetime.now(timezone.utc) + timedelta(days=retain_days)).isoformat()

        rec = GovernanceRecord(
            object_id      = object_id,
            object_type    = object_type,
            owner_id       = owner_id,
            classification = classification,
            source         = source,
            retain_until   = retain_until,
            evidence       = evidence or [],
            metadata       = metadata or {},
        )
        try:
            await self._gov_col.insert_one(rec.to_dict())
        except Exception:
            pass   # idempotent — may already exist
        return rec

    async def get(self, object_id: str) -> dict | None:
        doc = await self._gov_col.find_one({"object_id": object_id})
        if doc:
            doc.pop("_id", None)
        return doc

    async def record_lineage(
        self,
        object_id:   str,
        operation:   str,
        actor_id:    str,
        inputs:      list[str] | None = None,
        outputs:     list[str] | None = None,
        model:       str | None       = None,
        prompt_hash: str | None       = None,
        trace_id:    str | None       = None,
    ) -> str:
        lineage_id = "lin_" + secrets.token_hex(8)
        rec = LineageRecord(
            lineage_id  = lineage_id,
            object_id   = object_id,
            operation   = operation,
            actor_id    = actor_id,
            inputs      = inputs or [],
            outputs     = outputs or [],
            model       = model,
            prompt_hash = prompt_hash,
            trace_id    = trace_id,
        )
        try:
            await self._lin_col.insert_one(rec.to_dict())
        except Exception as exc:
            logger.debug("Lineage persist: %s", exc)
        return lineage_id

    async def get_lineage(self, object_id: str, limit: int = 50) -> list[dict]:
        docs = []
        async for doc in self._lin_col.find({"object_id": object_id}).sort("timestamp", -1).limit(limit):
            doc.pop("_id", None)
            docs.append(doc)
        return docs

    async def list_by_owner(self, owner_id: str, limit: int = 100) -> list[dict]:
        docs = []
        async for doc in self._gov_col.find({"owner_id": owner_id}).sort("created_at", -1).limit(limit):
            doc.pop("_id", None)
            docs.append(doc)
        return docs

    async def update_classification(
        self, object_id: str, level: ClassificationLevel
    ) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        r   = await self._gov_col.update_one(
            {"object_id": object_id},
            {"$set": {"classification": level, "updated_at": now}},
        )
        return r.modified_count > 0


# ── Singleton ─────────────────────────────────────────────────────────────────

_engine: DataGovernanceEngine | None = None


def init_governance(db: Any) -> DataGovernanceEngine:
    global _engine
    _engine = DataGovernanceEngine(db)
    return _engine


def get_governance() -> DataGovernanceEngine:
    if _engine is None:
        raise RuntimeError("DataGovernanceEngine not initialised")
    return _engine
