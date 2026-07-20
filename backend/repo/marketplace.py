"""MarketplaceRepository — repository for academic marketplace listings and orders."""
from __future__ import annotations

from .base  import BaseRepository, PermissionError
from .specs import Specs, QuerySpec
from .cache import DEFAULT_TTL


class MarketplaceListingRepository(BaseRepository):
    collection   = "marketplace_listings"
    event_prefix = "marketplace_listing"
    cache_ttl    = DEFAULT_TTL

    def _scope_query(self, filters: dict) -> dict:
        # Listings are public for reads; writes scoped to owner
        return filters

    def _can_write(self, doc: dict) -> bool:
        if self._ctx.is_admin:
            return True
        return str(doc.get("user_id", "")) == self._ctx.user_id

    async def list_listings(
        self,
        *,
        category: str | None = None,
        status: str = "active",
        page: int = 1,
        page_size: int = 20,
    ) -> list[dict]:
        extra: dict = {"status": status}
        if category:
            extra["category"] = category
        spec = QuerySpec(extra, [("created_at", -1)]).page(page, page_size)
        return await self.find_many(spec)

    async def get_listing(self, listing_id: str) -> dict | None:
        return await self.find_one(doc_id=listing_id)

    async def create_listing(self, data: dict) -> dict:
        data.setdefault("user_id", self._ctx.user_id)
        data.setdefault("status", "active")
        return await self.create(data)

    async def update_listing(self, listing_id: str, updates: dict) -> dict:
        return await self.update(listing_id, updates)

    async def my_listings(self, *, page: int = 1, page_size: int = 20) -> list[dict]:
        spec = QuerySpec(
            {"user_id": self._ctx.user_id},
            [("created_at", -1)],
        ).page(page, page_size)
        return await self.find_many(spec)
