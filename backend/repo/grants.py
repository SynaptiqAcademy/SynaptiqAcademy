"""
GrantRepository — bounded-context repository for grant applications and opportunities.
"""
from __future__ import annotations

from datetime import datetime, timezone

from .base   import BaseRepository, NotFoundError, PermissionError
from .cache  import DEFAULT_TTL
from .specs  import QuerySpec, Specs


class GrantRepository(BaseRepository):
    collection   = "grants"
    event_prefix = "grant"
    cache_ttl    = DEFAULT_TTL

    def _scope_query(self, filters: dict) -> dict:
        if self._ctx.is_admin or self._ctx.user_id == "system":
            return filters
        # Researchers see their own applications + open opportunities
        filters["$or"] = [
            {"user_id": self._ctx.user_id},
            {"status": "open"},               # public opportunities
            {"team_members": self._ctx.user_id},
        ]
        return filters

    async def list_grants(
        self,
        *,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[dict]:
        spec = Specs.active().with_sort(("deadline", 1)).page(page, page_size)
        if status:
            spec = spec.and_(Specs.by_status(status))
        return await self.find_many(spec)

    async def get_grant(self, grant_id: str) -> dict | None:
        return await self.find_one(doc_id=grant_id)

    async def list_open_opportunities(self, *, limit: int = 50) -> list[dict]:
        spec = QuerySpec(
            {"status": "open", "deleted_at": None},
            sort=[("deadline", 1)],
            limit=limit,
        )
        # Bypass user scoping — open opportunities are public within the platform
        cursor = self._col.find(spec.filters).sort(spec.sort).limit(limit)
        docs   = await cursor.to_list(length=limit)
        from .base import _serialize
        return [_serialize(d) for d in docs]

    async def submit_application(self, grant_id: str) -> dict:
        grant = await self.find_one(doc_id=grant_id, bypass_cache=True)
        if not grant:
            raise NotFoundError(f"Grant {grant_id} not found")
        if grant.get("status") != "draft":
            raise ValueError(f"Can only submit a draft application (got {grant['status']!r})")
        if not self._can_write(grant):
            raise PermissionError(f"Cannot submit grant {grant_id}")
        return await self.update(grant_id, {"status": "submitted", "submitted_at": datetime.now(timezone.utc)})

    async def upcoming_deadlines(self, days: int = 30) -> list[dict]:
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) + timedelta(days=days)
        spec = QuerySpec(
            {"deadline": {"$lte": cutoff}, "status": {"$in": ["open", "draft"]}, "deleted_at": None},
            sort=[("deadline", 1)],
            limit=100,
        )
        return await self.find_many(spec)
