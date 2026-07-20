"""
PublicationRepository — bounded-context repository for research publications.
"""
from __future__ import annotations

from .base   import BaseRepository, NotFoundError, PermissionError
from .cache  import DEFAULT_TTL
from .specs  import QuerySpec, Specs


class PublicationRepository(BaseRepository):
    collection   = "publications"
    event_prefix = "publication"
    cache_ttl    = DEFAULT_TTL

    def _scope_query(self, filters: dict) -> dict:
        if self._ctx.is_admin or self._ctx.user_id == "system":
            return filters
        # Researchers see their own publications + collaborators'
        filters["$or"] = [
            {"user_id": self._ctx.user_id},
            {"co_authors": self._ctx.user_id},
        ]
        return filters

    async def list_publications(
        self,
        *,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> list[dict]:
        spec = Specs.active().with_sort(("created_at", -1)).page(page, page_size)
        if status:
            spec = spec.and_(Specs.by_status(status))
        return await self.find_many(spec)

    async def get_publication(self, pub_id: str) -> dict | None:
        return await self.find_one(doc_id=pub_id)

    async def submit_for_review(self, pub_id: str) -> dict:
        pub = await self.find_one(doc_id=pub_id, bypass_cache=True)
        if not pub:
            raise NotFoundError(f"Publication {pub_id} not found")
        if pub.get("status") not in ("draft", "revision"):
            raise ValueError(f"Cannot submit publication with status {pub['status']!r}")
        if not self._can_write(pub):
            raise PermissionError(f"Cannot submit publication {pub_id}")
        return await self.update(pub_id, {"status": "in_review"})

    async def mark_published(self, pub_id: str, doi: str | None = None) -> dict:
        if not self._ctx.is_admin:
            raise PermissionError("Only admins can mark publications as published")
        updates: dict = {"status": "published"}
        if doi:
            updates["doi"] = doi
        doc = await self.update(pub_id, updates)
        # Emit published event (for reputation scoring, notifications, etc.)
        from events import get_bus, PublicationPublished
        get_bus().publish_sync(PublicationPublished(
            aggregate_id=pub_id,
            user_id=self._ctx.user_id,
            request_id=self._ctx.request_id,
            payload={"doi": doi},
        ))
        return doc

    async def list_by_keyword(self, keyword: str, *, limit: int = 20) -> list[dict]:
        filt = {
            "$or": [
                {"title":    {"$regex": keyword, "$options": "i"}},
                {"abstract": {"$regex": keyword, "$options": "i"}},
                {"keywords": {"$elemMatch": {"$regex": keyword, "$options": "i"}}},
            ]
        }
        spec = QuerySpec(filt, limit=limit)
        return await self.find_many(spec)
