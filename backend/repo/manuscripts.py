"""ManuscriptRepository — bounded-context repository for manuscript management."""
from __future__ import annotations

from .base  import BaseRepository, NotFoundError, PermissionError, _serialize
from .specs import QuerySpec, Specs
from .cache import SHORT_TTL


class ManuscriptRepository(BaseRepository):
    collection   = "manuscripts"
    event_prefix = "manuscript"
    cache_ttl    = SHORT_TTL

    def _scope_query(self, filters: dict) -> dict:
        if self._ctx.is_admin or self._ctx.user_id == "system":
            return filters
        filters["$or"] = [
            {"user_id": self._ctx.user_id},
            {"collaborators": self._ctx.user_id},
        ]
        return filters

    def _can_write(self, doc: dict) -> bool:
        if self._ctx.is_admin:
            return True
        uid = self._ctx.user_id
        return (
            str(doc.get("user_id", "")) == uid
            or uid in (doc.get("collaborators") or [])
        )

    async def list_manuscripts(self, *, page: int = 1, page_size: int = 20) -> list[dict]:
        spec = Specs.active().with_sort(("updated_at", -1)).page(page, page_size)
        return await self.find_many(spec)

    async def get_manuscript(self, ms_id: str) -> dict | None:
        return await self.find_one(doc_id=ms_id)

    async def create_manuscript(self, data: dict) -> dict:
        data.setdefault("user_id", self._ctx.user_id)
        return await self.create(data)

    async def update_manuscript(self, ms_id: str, updates: dict) -> dict:
        return await self.update(ms_id, updates)

    async def delete_manuscript(self, ms_id: str) -> dict:
        return await self.delete(ms_id)

    async def search(self, query: str, *, limit: int = 20) -> list[dict]:
        filt = {
            "$or": [
                {"title": {"$regex": query, "$options": "i"}},
                {"abstract": {"$regex": query, "$options": "i"}},
                {"keywords": {"$in": [query]}},
            ],
        }
        return await self.raw_find(filt, limit=limit)


class ManuscriptVersionRepository(BaseRepository):
    collection   = "manuscript_versions"
    event_prefix = "manuscript_version"

    def _scope_query(self, filters: dict) -> dict:
        if self._ctx.is_admin or self._ctx.user_id == "system":
            return filters
        filters["user_id"] = self._ctx.user_id
        return filters

    async def list_versions(self, manuscript_id: str) -> list[dict]:
        return await self.raw_find(
            {"manuscript_id": manuscript_id},
            limit=50,
        )

    async def add_version(self, manuscript_id: str, data: dict) -> dict:
        data["manuscript_id"] = manuscript_id
        data.setdefault("user_id", self._ctx.user_id)
        return await self.create(data)
