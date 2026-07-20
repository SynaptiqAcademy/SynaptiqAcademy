"""AcademicMemory — persistent, permission-aware per-user academic memory.

Stores interaction history, preferences, writing style, research interests.
Private by design: each user only sees their own memory.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from services.academic.models import AcademicMemoryRecord, AcademicUserProfile

logger = logging.getLogger("synaptiq.academic.memory")

_COLL_INTERACTIONS = "academic_memory_interactions"
_COLL_PROFILES = "academic_memory_profiles"
_MAX_INTERACTIONS_PER_USER = 200
_RECENT_WINDOW = 10


class AcademicMemory:
    """Per-user academic interaction memory."""

    def __init__(self, db: Any) -> None:
        self._db = db

    # ── Record interactions ────────────────────────────────────────────────────

    async def record_interaction(
        self,
        user_id: str,
        feature: str,
        domain: str = "",
        methodology: str = "",
        quality_score: float = 0.0,
        detected_weaknesses: list[str] | None = None,
        topics: list[str] | None = None,
    ) -> None:
        """Store an interaction record for future personalization."""
        if not user_id:
            return
        record = {
            "user_id": user_id,
            "feature": feature,
            "domain": domain,
            "methodology": methodology,
            "quality_score": quality_score,
            "detected_weaknesses": detected_weaknesses or [],
            "topics": topics or [],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        try:
            await self._db[_COLL_INTERACTIONS].insert_one(record)
            await self._evict_old_interactions(user_id)
            await self._update_profile(user_id, record)
        except Exception as exc:
            logger.debug("AcademicMemory.record_interaction failed: %s", exc)

    # ── Retrieve context ───────────────────────────────────────────────────────

    async def get_recent_interactions(
        self,
        user_id: str,
        feature: str | None = None,
        limit: int = _RECENT_WINDOW,
    ) -> list[dict]:
        """Return the N most recent interactions for this user."""
        try:
            query: dict = {"user_id": user_id}
            if feature:
                query["feature"] = feature
            docs = await self._db[_COLL_INTERACTIONS].find(query).sort(
                "timestamp", -1
            ).limit(limit).to_list(length=limit)
            for d in docs:
                d.pop("_id", None)
            return docs
        except Exception as exc:
            logger.debug("AcademicMemory.get_recent_interactions: %s", exc)
            return []

    async def get_user_profile(self, user_id: str) -> AcademicUserProfile:
        """Return the user's academic profile, or a fresh empty profile."""
        try:
            doc = await self._db[_COLL_PROFILES].find_one({"user_id": user_id})
            if doc:
                doc.pop("_id", None)
                return AcademicUserProfile(
                    user_id=user_id,
                    interaction_count=doc.get("interaction_count", 0),
                    primary_domain=doc.get("primary_domain", ""),
                    preferred_methodology=doc.get("preferred_methodology", ""),
                    active_research_topics=doc.get("active_research_topics", []),
                    preferred_journals=doc.get("preferred_journals", []),
                    known_weaknesses=doc.get("known_weaknesses", []),
                    avg_quality_score=doc.get("avg_quality_score", 0.0),
                    last_seen=doc.get("last_seen", ""),
                )
        except Exception as exc:
            logger.debug("AcademicMemory.get_user_profile: %s", exc)
        return AcademicUserProfile(user_id=user_id)

    async def get_memory_summary(self, user_id: str) -> dict:
        """Return a human-readable summary of the user's academic memory."""
        profile = await self.get_user_profile(user_id)
        recent = await self.get_recent_interactions(user_id, limit=5)
        return {
            "profile": profile.to_dict(),
            "recent_interactions": recent,
            "interaction_count": profile.interaction_count,
        }

    async def clear_memory(self, user_id: str) -> int:
        """Delete all memory for a user. Returns number of deleted records."""
        count = 0
        try:
            result = await self._db[_COLL_INTERACTIONS].delete_many({"user_id": user_id})
            count += result.deleted_count
            await self._db[_COLL_PROFILES].delete_many({"user_id": user_id})
        except Exception as exc:
            logger.warning("AcademicMemory.clear_memory failed: %s", exc)
        return count

    async def get_stats(self) -> dict:
        """Return aggregate memory statistics for the admin dashboard."""
        try:
            total_interactions = await self._db[_COLL_INTERACTIONS].count_documents({})
            total_users = await self._db[_COLL_PROFILES].count_documents({})
            pipeline = [
                {"$group": {"_id": "$domain", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 10},
            ]
            domain_docs = await self._db[_COLL_INTERACTIONS].aggregate(pipeline).to_list(length=10)
            domains = {d["_id"]: d["count"] for d in domain_docs if d["_id"]}

            weakness_pipeline = [
                {"$unwind": "$detected_weaknesses"},
                {"$group": {"_id": "$detected_weaknesses", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 10},
            ]
            weakness_docs = await self._db[_COLL_INTERACTIONS].aggregate(
                weakness_pipeline
            ).to_list(length=10)
            common_weaknesses = {d["_id"]: d["count"] for d in weakness_docs}

            return {
                "total_interactions": total_interactions,
                "total_users": total_users,
                "top_domains": domains,
                "most_common_weaknesses": common_weaknesses,
            }
        except Exception:
            return {"total_interactions": 0, "total_users": 0}

    # ── Internal helpers ───────────────────────────────────────────────────────

    async def _evict_old_interactions(self, user_id: str) -> None:
        """Keep only the most recent _MAX_INTERACTIONS_PER_USER records."""
        try:
            count = await self._db[_COLL_INTERACTIONS].count_documents({"user_id": user_id})
            if count <= _MAX_INTERACTIONS_PER_USER:
                return
            oldest_docs = await self._db[_COLL_INTERACTIONS].find(
                {"user_id": user_id}
            ).sort("timestamp", 1).limit(count - _MAX_INTERACTIONS_PER_USER).to_list(
                length=count - _MAX_INTERACTIONS_PER_USER
            )
            ids = [d["_id"] for d in oldest_docs]
            if ids:
                await self._db[_COLL_INTERACTIONS].delete_many({"_id": {"$in": ids}})
        except Exception as exc:
            logger.debug("Eviction failed: %s", exc)

    async def _update_profile(self, user_id: str, record: dict) -> None:
        """Incrementally update the user profile from a new interaction."""
        now = datetime.now(timezone.utc).isoformat()
        try:
            existing = await self._db[_COLL_PROFILES].find_one({"user_id": user_id})
            if existing:
                old_count = existing.get("interaction_count", 0)
                old_avg = existing.get("avg_quality_score", 0.0)
                new_count = old_count + 1
                new_avg = (old_avg * old_count + record.get("quality_score", 0)) / new_count
                update = {
                    "$inc": {"interaction_count": 1},
                    "$set": {
                        "avg_quality_score": round(new_avg, 3),
                        "last_seen": now,
                    },
                }
                if record.get("domain"):
                    update["$set"]["primary_domain"] = record["domain"]
                if record.get("topics"):
                    update["$addToSet"] = {
                        "active_research_topics": {"$each": record["topics"][:5]}
                    }
                if record.get("detected_weaknesses"):
                    update.setdefault("$addToSet", {})
                    update["$addToSet"]["known_weaknesses"] = {
                        "$each": record["detected_weaknesses"][:3]
                    }
                await self._db[_COLL_PROFILES].update_one(
                    {"user_id": user_id}, update
                )
            else:
                await self._db[_COLL_PROFILES].insert_one({
                    "user_id": user_id,
                    "interaction_count": 1,
                    "primary_domain": record.get("domain", ""),
                    "preferred_methodology": record.get("methodology", ""),
                    "active_research_topics": record.get("topics", [])[:5],
                    "preferred_journals": [],
                    "known_weaknesses": record.get("detected_weaknesses", [])[:3],
                    "avg_quality_score": record.get("quality_score", 0.0),
                    "last_seen": now,
                    "created_at": now,
                })
        except Exception as exc:
            logger.debug("Profile update failed: %s", exc)
