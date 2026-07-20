"""ExpertiseRepository — repository for expertise requests and reviews."""
from __future__ import annotations

from .base  import BaseRepository
from .specs import Specs, QuerySpec
from .cache import DEFAULT_TTL


class ExpertiseRequestRepository(BaseRepository):
    collection   = "expertise_requests"
    event_prefix = "expertise_request"
    cache_ttl    = DEFAULT_TTL

    def _scope_query(self, filters: dict) -> dict:
        if self._ctx.is_admin or self._ctx.user_id == "system":
            return filters
        uid = self._ctx.user_id
        filters["$or"] = [
            {"requester_id": uid},
            {"expert_id": uid},
            {"user_id": uid},
        ]
        return filters

    async def list_requests(self, *, status: str | None = None) -> list[dict]:
        extra: dict = {}
        if status:
            extra["status"] = status
        spec = QuerySpec(extra, [("created_at", -1)])
        return await self.find_many(spec)

    async def get_request(self, req_id: str) -> dict | None:
        return await self.find_one(doc_id=req_id)

    async def create_request(self, data: dict) -> dict:
        data.setdefault("requester_id", self._ctx.user_id)
        data.setdefault("user_id", self._ctx.user_id)
        return await self.create(data)

    async def update_request(self, req_id: str, updates: dict) -> dict:
        return await self.update(req_id, updates)
