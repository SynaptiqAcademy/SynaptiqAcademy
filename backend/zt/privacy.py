"""
Privacy Center — Phase XXXV.8 (GDPR / FERPA compliance)

Researchers can: view their data, export it, request deletion,
correct their Digital Twin, reset AI memory, disconnect providers, manage consent.
"""
from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

_COL = "zt_privacy_requests"


class PrivacyRequestType(str, Enum):
    ACCESS        = "access"        # Right to access (GDPR Art. 15)
    PORTABILITY   = "portability"   # Right to data portability (Art. 20)
    ERASURE       = "erasure"       # Right to be forgotten (Art. 17)
    RECTIFICATION = "rectification" # Right to correction (Art. 16)
    RESTRICTION   = "restriction"   # Right to restrict processing (Art. 18)
    OBJECTION     = "objection"     # Right to object (Art. 21)
    AI_MEMORY_RESET = "ai_memory_reset"
    TWIN_CORRECTION = "twin_correction"
    CONSENT_WITHDRAW= "consent_withdraw"
    PROVIDER_DISCONNECT = "provider_disconnect"


class RequestStatus(str, Enum):
    PENDING     = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED   = "completed"
    REJECTED    = "rejected"
    EXPIRED     = "expired"


@dataclass
class PrivacyRequest:
    request_id:   str
    user_id:      str
    request_type: PrivacyRequestType
    status:       RequestStatus       = RequestStatus.PENDING
    details:      dict                = field(default_factory=dict)
    created_at:   str                 = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str | None          = None
    response:     str                 = ""
    legal_basis:  str                 = ""

    def to_dict(self) -> dict:
        return {
            "request_id":   self.request_id,
            "user_id":      self.user_id,
            "request_type": self.request_type,
            "status":       self.status,
            "details":      self.details,
            "created_at":   self.created_at,
            "completed_at": self.completed_at,
            "response":     self.response,
            "legal_basis":  self.legal_basis,
        }


class PrivacyCenter:

    def __init__(self, db: Any) -> None:
        self._db  = db
        self._col = db[_COL]

    async def ensure_indexes(self) -> None:
        try:
            await self._col.create_index("request_id", unique=True)
            await self._col.create_index([("user_id", 1), ("status", 1)])
            await self._col.create_index([("request_type", 1), ("status", 1)])
            await self._col.create_index("created_at")
        except Exception as exc:
            logger.debug("Privacy index: %s", exc)

    async def submit_request(
        self,
        user_id:      str,
        request_type: PrivacyRequestType,
        details:      dict | None = None,
        legal_basis:  str         = "",
    ) -> PrivacyRequest:
        req = PrivacyRequest(
            request_id   = "prv_" + secrets.token_hex(8),
            user_id      = user_id,
            request_type = request_type,
            details      = details or {},
            legal_basis  = legal_basis,
        )
        await self._col.insert_one(req.to_dict())
        logger.info("Privacy request submitted: %s for user %s", request_type, user_id)
        return req

    async def process_request(
        self,
        request_id: str,
        status:     RequestStatus,
        response:   str = "",
    ) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        update: dict = {"status": status, "response": response}
        if status in (RequestStatus.COMPLETED, RequestStatus.REJECTED):
            update["completed_at"] = now
        r = await self._col.update_one({"request_id": request_id}, {"$set": update})
        return r.modified_count > 0

    async def list_requests(
        self,
        user_id:      str | None          = None,
        status:       RequestStatus | None = None,
        request_type: PrivacyRequestType | None = None,
        limit:        int                  = 100,
    ) -> list[dict]:
        filt: dict = {}
        if user_id:
            filt["user_id"] = user_id
        if status:
            filt["status"] = status
        if request_type:
            filt["request_type"] = request_type

        docs = []
        async for doc in self._col.find(filt).sort("created_at", -1).limit(limit):
            doc.pop("_id", None)
            docs.append(doc)
        return docs

    async def get_request(self, request_id: str) -> dict | None:
        doc = await self._col.find_one({"request_id": request_id})
        if doc:
            doc.pop("_id", None)
        return doc

    async def user_data_summary(self, user_id: str, db: Any) -> dict:
        """
        Returns a summary of data held about a user (for GDPR Art. 15 access requests).
        Queries collection counts — never returns raw personal data.
        """
        summary: dict = {"user_id": user_id, "collections": {}}
        collections_to_check = [
            "publications", "manuscripts", "collaborations", "projects",
            "teaching_lessons", "ai_abstract_generations", "research_gap_reviews",
            "literary_reviews", "grant_applications", "timeline_events",
            "obs_audit", "obs_cost",
        ]
        for col_name in collections_to_check:
            try:
                count = await db[col_name].count_documents(
                    {"$or": [{"user_id": user_id}, {"owner_id": user_id}]}
                )
                if count > 0:
                    summary["collections"][col_name] = count
            except Exception:
                pass
        summary["generated_at"] = datetime.now(timezone.utc).isoformat()
        return summary


# ── Singleton ─────────────────────────────────────────────────────────────────

_center: PrivacyCenter | None = None


def init_privacy_center(db: Any) -> PrivacyCenter:
    global _center
    _center = PrivacyCenter(db)
    return _center


def get_privacy_center() -> PrivacyCenter:
    if _center is None:
        raise RuntimeError("PrivacyCenter not initialised")
    return _center
