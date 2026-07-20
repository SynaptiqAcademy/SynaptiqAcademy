"""InstitutionMembershipRepository — repository for institution membership management."""
from __future__ import annotations

from .base  import BaseRepository, PermissionError
from .specs import QuerySpec
from .cache import DEFAULT_TTL


class InstitutionMembershipRepository(BaseRepository):
    collection   = "institution_memberships"
    event_prefix = "institution_membership"
    cache_ttl    = DEFAULT_TTL

    def _scope_query(self, filters: dict) -> dict:
        if self._ctx.is_admin or self._ctx.user_id == "system":
            return filters
        # Researchers see their own membership; institution admins see all in their institution
        if self._ctx.role == "institution_admin" and self._ctx.institution:
            filters["institution"] = self._ctx.institution
        else:
            filters["user_id"] = self._ctx.user_id
        return filters

    async def get_membership(self, user_id: str) -> dict | None:
        return await self.raw_find({"user_id": user_id, "deleted_at": None}, limit=1) \
            and (await self.raw_find({"user_id": user_id, "deleted_at": None}, limit=1))[0] or None

    async def list_institution_members(
        self, institution: str, *, page: int = 1, page_size: int = 50
    ) -> list[dict]:
        spec = QuerySpec({"institution": institution}, [("joined_at", -1)]).page(page, page_size)
        return await self.find_many(spec)

    async def create_membership(self, data: dict) -> dict:
        data.setdefault("user_id", self._ctx.user_id)
        return await self.create(data)

    async def update_membership(self, membership_id: str, updates: dict) -> dict:
        return await self.update(membership_id, updates)

    async def remove_membership(self, membership_id: str) -> dict:
        return await self.delete(membership_id)
