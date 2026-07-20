"""FileRepository — bounded-context repository for file management."""
from __future__ import annotations

from .base  import BaseRepository, PermissionError
from .specs import Specs
from .cache import SHORT_TTL


class FileRepository(BaseRepository):
    collection   = "files"
    event_prefix = "file"
    cache_ttl    = SHORT_TTL

    def _scope_query(self, filters: dict) -> dict:
        if self._ctx.is_admin or self._ctx.user_id == "system":
            return filters
        uid = self._ctx.user_id
        filters["$or"] = [
            {"user_id": uid},
            {"owner_id": uid},
            {"shared_with": uid},
        ]
        return filters

    def _can_write(self, doc: dict) -> bool:
        if self._ctx.is_admin:
            return True
        uid = self._ctx.user_id
        return (
            str(doc.get("user_id", "")) == uid
            or str(doc.get("owner_id", "")) == uid
        )

    async def list_files(
        self,
        *,
        workspace_id: str | None = None,
        project_id: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> list[dict]:
        extra: dict = {}
        if workspace_id:
            extra["workspace_id"] = workspace_id
        if project_id:
            extra["project_id"] = project_id
        from .specs import QuerySpec
        spec = QuerySpec(extra, [("created_at", -1)]).page(page, page_size)
        return await self.find_many(spec)

    async def get_file(self, file_id: str) -> dict | None:
        return await self.find_one(doc_id=file_id)

    async def create_file_record(self, data: dict) -> dict:
        data.setdefault("user_id", self._ctx.user_id)
        return await self.create(data)

    async def update_file(self, file_id: str, updates: dict) -> dict:
        return await self.update(file_id, updates)

    async def delete_file(self, file_id: str) -> dict:
        return await self.delete(file_id)
