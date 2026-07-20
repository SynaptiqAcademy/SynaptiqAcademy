"""AnalyticsRepository — repository for analytics, ai_requests, and usage data."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from .base  import BaseRepository
from .specs import QuerySpec
from .cache import SHORT_TTL


class AIRequestRepository(BaseRepository):
    """Append-only log of AI feature usage (no soft delete, no RLS on reads for admin)."""
    collection   = "ai_requests"
    event_prefix = "ai_request"
    cache_ttl    = SHORT_TTL

    def _scope_query(self, filters: dict) -> dict:
        if self._ctx.is_admin or self._ctx.user_id == "system":
            return filters
        filters["user_id"] = self._ctx.user_id
        return filters

    async def log_request(self, data: dict) -> dict:
        data.setdefault("user_id", self._ctx.user_id)
        return await self.create(data)

    async def usage_summary(self, days: int = 30) -> list[dict]:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        pipeline = [
            {"$match": {"user_id": self._ctx.user_id, "created_at": {"$gte": since}}},
            {"$group": {
                "_id": "$feature",
                "count": {"$sum": 1},
                "total_credits": {"$sum": "$credits"},
            }},
            {"$sort": {"count": -1}},
        ]
        return await self.raw_aggregate(pipeline)

    async def list_by_user(self, *, page: int = 1, page_size: int = 50) -> list[dict]:
        spec = QuerySpec(
            {"user_id": self._ctx.user_id},
            [("created_at", -1)],
        ).page(page, page_size)
        return await self.find_many(spec, bypass_cache=True)


class ResearchImpactRepository(BaseRepository):
    collection   = "research_impact"
    event_prefix = "research_impact"
    cache_ttl    = SHORT_TTL

    def _scope_query(self, filters: dict) -> dict:
        if self._ctx.is_admin or self._ctx.user_id == "system":
            return filters
        filters["user_id"] = self._ctx.user_id
        return filters

    async def get_impact(self, user_id: str | None = None) -> dict | None:
        uid = user_id or self._ctx.user_id
        docs = await self.raw_find({"user_id": uid}, limit=1)
        return docs[0] if docs else None

    async def upsert_impact(self, user_id: str, data: dict) -> dict:
        return await self.upsert({"user_id": user_id}, data)
