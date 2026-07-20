"""CollaborationRepository — repository for research collaborations and requests."""
from __future__ import annotations

from .base  import BaseRepository, NotFoundError, PermissionError
from .specs import Specs
from .cache import DEFAULT_TTL


class CollaborationRepository(BaseRepository):
    collection   = "collaborations"
    event_prefix = "collaboration"
    cache_ttl    = DEFAULT_TTL

    def _scope_query(self, filters: dict) -> dict:
        if self._ctx.is_admin or self._ctx.user_id == "system":
            return filters
        uid = self._ctx.user_id
        filters["$or"] = [
            {"initiator_id": uid},
            {"recipient_id": uid},
            {"members": uid},
            {"user_id": uid},
        ]
        return filters

    async def list_collaborations(self, *, page: int = 1, page_size: int = 20) -> list[dict]:
        spec = Specs.active().with_sort(("updated_at", -1)).page(page, page_size)
        return await self.find_many(spec)

    async def get_collaboration(self, collab_id: str) -> dict | None:
        return await self.find_one(doc_id=collab_id)

    async def create_collaboration(self, data: dict) -> dict:
        data.setdefault("user_id", self._ctx.user_id)
        return await self.create(data)

    async def update_collaboration(self, collab_id: str, updates: dict) -> dict:
        return await self.update(collab_id, updates)


class CollaborationRequestRepository(BaseRepository):
    collection   = "collaboration_requests"
    event_prefix = "collaboration_request"
    cache_ttl    = DEFAULT_TTL

    def _scope_query(self, filters: dict) -> dict:
        if self._ctx.is_admin or self._ctx.user_id == "system":
            return filters
        uid = self._ctx.user_id
        filters["$or"] = [
            {"sender_id": uid},
            {"recipient_id": uid},
            {"user_id": uid},
        ]
        return filters

    async def list_requests(self, *, direction: str = "all") -> list[dict]:
        uid = self._ctx.user_id
        if direction == "sent":
            filt = {"sender_id": uid}
        elif direction == "received":
            filt = {"recipient_id": uid}
        else:
            filt = {"$or": [{"sender_id": uid}, {"recipient_id": uid}]}
        return await self.raw_find(filt, limit=100)

    async def create_request(self, data: dict) -> dict:
        data.setdefault("sender_id", self._ctx.user_id)
        return await self.create(data)
