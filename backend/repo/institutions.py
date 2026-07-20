"""
InstitutionRepository — bounded-context repository for institutions.
"""
from __future__ import annotations

from .base   import BaseRepository, NotFoundError, PermissionError
from .cache  import LONG_TTL
from .specs  import QuerySpec, Specs


class InstitutionRepository(BaseRepository):
    collection   = "institutions"
    event_prefix = "institution"
    cache_ttl    = LONG_TTL  # institution records are stable

    def _scope_query(self, filters: dict) -> dict:
        # Institutions are readable by all authenticated users
        # but only writable by admins (enforced in _can_write)
        return filters

    def _can_write(self, doc: dict) -> bool:
        return self._ctx.is_admin or self._ctx.can_access_institution(
            doc.get("institution_id") or str(doc.get("_id", ""))
        )

    async def get_institution(self, inst_id: str) -> dict | None:
        return await self.find_one(doc_id=inst_id)

    async def get_by_name(self, name: str) -> dict | None:
        doc = await self._col.find_one({"name": {"$regex": f"^{name}$", "$options": "i"}, "deleted_at": None})
        from .base import _serialize
        return _serialize(doc)

    async def list_institutions(self, *, page: int = 1, page_size: int = 50) -> list[dict]:
        spec = Specs.active().with_sort(("name", 1)).page(page, page_size)
        return await self.find_many(spec)

    async def search(self, query: str, *, limit: int = 20) -> list[dict]:
        filt = {
            "$or": [
                {"name":    {"$regex": query, "$options": "i"}},
                {"country": {"$regex": query, "$options": "i"}},
            ],
            "deleted_at": None,
        }
        cursor = self._col.find(filt).limit(limit)
        docs   = await cursor.to_list(length=limit)
        from .base import _serialize
        return [_serialize(d) for d in docs]

    async def get_members(self, inst_id: str, *, page: int = 1, page_size: int = 50) -> list[dict]:
        if not (self._ctx.is_admin or self._ctx.can_access_institution(inst_id)):
            raise PermissionError("Cannot list members of this institution")
        # Delegate to UserRepository if you need full user docs;
        # here we return just the membership records in this collection's members array
        inst = await self.find_one(doc_id=inst_id)
        if not inst:
            raise NotFoundError(f"Institution {inst_id} not found")
        members = inst.get("members", [])
        start   = (page - 1) * page_size
        return members[start : start + page_size]
