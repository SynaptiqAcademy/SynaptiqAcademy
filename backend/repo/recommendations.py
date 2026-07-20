"""
RecommendationRepository — bounded-context repository for proactive AI recommendations.
"""
from __future__ import annotations

from datetime import datetime, timezone

from .base   import BaseRepository
from .cache  import SHORT_TTL
from .specs  import QuerySpec


class RecommendationRepository(BaseRepository):
    collection   = "recommendations"
    event_prefix = "recommendation"
    cache_ttl    = SHORT_TTL

    def _scope_query(self, filters: dict) -> dict:
        if self._ctx.user_id == "system" or self._ctx.is_admin:
            return filters
        filters["user_id"] = self._ctx.user_id
        return filters

    async def list_recommendations(
        self,
        *,
        unactioned_only: bool = True,
        limit: int = 20,
    ) -> list[dict]:
        filt: dict = {}
        if unactioned_only:
            filt["actioned"] = {"$ne": True}
        spec = QuerySpec(filt, sort=[("created_at", -1)], limit=limit)
        return await self.find_many(spec)

    async def dismiss(self, rec_id: str) -> dict:
        return await self.update(rec_id, {
            "actioned": True,
            "action":   "dismissed",
            "actioned_at": datetime.now(timezone.utc),
        })

    async def accept(self, rec_id: str) -> dict:
        return await self.update(rec_id, {
            "actioned": True,
            "action":   "accepted",
            "actioned_at": datetime.now(timezone.utc),
        })

    async def feedback(self, rec_id: str, helpful: bool) -> dict:
        return await self.update(rec_id, {
            "feedback": "helpful" if helpful else "not_helpful",
            "feedback_at": datetime.now(timezone.utc),
        })
