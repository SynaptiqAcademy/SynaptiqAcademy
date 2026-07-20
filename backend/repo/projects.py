"""ProjectRepository — bounded-context repository for research projects."""
from __future__ import annotations

from .base  import BaseRepository, NotFoundError, PermissionError, _serialize
from .specs import Specs
from .cache import DEFAULT_TTL


class ProjectRepository(BaseRepository):
    collection   = "projects"
    event_prefix = "project"
    cache_ttl    = DEFAULT_TTL

    def _scope_query(self, filters: dict) -> dict:
        if self._ctx.is_admin or self._ctx.user_id == "system":
            return filters
        uid = self._ctx.user_id
        filters["$or"] = [
            {"user_id": uid},
            {"owner_id": uid},
            {"members": uid},
            {"collaborators": uid},
        ]
        return filters

    def _can_write(self, doc: dict) -> bool:
        if self._ctx.is_admin:
            return True
        uid = self._ctx.user_id
        return (
            str(doc.get("user_id", "")) == uid
            or str(doc.get("owner_id", "")) == uid
            or uid in (doc.get("members") or [])
        )

    async def list_projects(self, *, page: int = 1, page_size: int = 20) -> list[dict]:
        spec = Specs.active().with_sort(("updated_at", -1)).page(page, page_size)
        return await self.find_many(spec)

    async def get_project(self, project_id: str) -> dict | None:
        return await self.find_one(doc_id=project_id)

    async def create_project(self, data: dict) -> dict:
        data.setdefault("user_id", self._ctx.user_id)
        data.setdefault("owner_id", self._ctx.user_id)
        return await self.create(data)

    async def update_project(self, project_id: str, updates: dict) -> dict:
        return await self.update(project_id, updates)

    async def delete_project(self, project_id: str) -> dict:
        return await self.delete(project_id)

    async def add_member(self, project_id: str, member_id: str) -> dict:
        doc = await self.find_one(doc_id=project_id, bypass_cache=True)
        if not doc:
            raise NotFoundError(f"Project {project_id} not found")
        if not self._can_write(doc):
            raise PermissionError("Only project owner can add members")
        members = list(set(doc.get("members", []) + [member_id]))
        return await self.update(project_id, {"members": members})
