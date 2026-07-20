"""
TwinRepository — bounded-context repository for Digital Research Twin data.
"""
from __future__ import annotations

from .base   import BaseRepository, NotFoundError, PermissionError
from .cache  import DEFAULT_TTL
from .specs  import QuerySpec


class TwinRepository(BaseRepository):
    collection   = "twin_profiles"
    event_prefix = "twin"
    cache_ttl    = DEFAULT_TTL

    def _scope_query(self, filters: dict) -> dict:
        # Twin data is strictly private — only owner and system see it
        if self._ctx.user_id == "system" or self._ctx.is_super_admin:
            return filters
        filters["user_id"] = self._ctx.user_id
        return filters

    def _can_read(self, doc: dict) -> bool:
        if self._ctx.is_super_admin or self._ctx.user_id == "system":
            return True
        return str(doc.get("user_id", "")) == self._ctx.user_id

    def _can_write(self, doc: dict) -> bool:
        if self._ctx.is_super_admin or self._ctx.user_id == "system":
            return True
        return str(doc.get("user_id", "")) == self._ctx.user_id

    async def get_twin(self, user_id: str | None = None) -> dict | None:
        uid = user_id or self._ctx.user_id
        if uid != self._ctx.user_id and not self._ctx.is_super_admin:
            raise PermissionError("Cannot access another user's twin")
        doc = await self._col.find_one({"user_id": uid, "deleted_at": None})
        from .base import _serialize
        return _serialize(doc)

    async def get_goals(self, user_id: str | None = None) -> list[dict]:
        twin = await self.get_twin(user_id)
        if not twin:
            return []
        return twin.get("goals", [])

    async def get_simulations(self, user_id: str | None = None) -> list[dict]:
        spec = QuerySpec(
            {"user_id": user_id or self._ctx.user_id, "deleted_at": None},
            limit=20,
        )
        cursor = self._db["twin_simulations"].find(spec.filters).limit(20)
        docs   = await cursor.to_list(length=20)
        from .base import _serialize
        return [_serialize(d) for d in docs]

    async def update_twin(self, updates: dict, user_id: str | None = None) -> dict:
        uid = user_id or self._ctx.user_id
        if uid != self._ctx.user_id and not self._ctx.is_super_admin:
            raise PermissionError("Cannot update another user's twin")

        existing = await self._col.find_one({"user_id": uid})
        if existing:
            doc_id = str(existing["_id"])
            return await self.update(doc_id, updates)
        # Create if not exists
        return await self.create({"user_id": uid, **updates})
