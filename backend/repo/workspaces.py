"""
WorkspaceRepository — bounded-context repository for research workspaces.
"""
from __future__ import annotations

from .base   import BaseRepository, NotFoundError, PermissionError
from .cache  import DEFAULT_TTL
from .specs  import QuerySpec, Specs


class WorkspaceRepository(BaseRepository):
    collection   = "workspaces"
    event_prefix = "workspace"
    cache_ttl    = DEFAULT_TTL

    def _scope_query(self, filters: dict) -> dict:
        if self._ctx.is_admin or self._ctx.user_id == "system":
            return filters
        # Users see workspaces they own OR are a member of
        filters["$or"] = [
            {"user_id": self._ctx.user_id},
            {"members": self._ctx.user_id},
        ]
        return filters

    async def list_workspaces(self, *, page: int = 1, page_size: int = 20) -> list[dict]:
        spec = Specs.active().with_sort(("updated_at", -1)).page(page, page_size)
        return await self.find_many(spec)

    async def get_workspace(self, workspace_id: str) -> dict | None:
        return await self.find_one(doc_id=workspace_id)

    async def add_member(self, workspace_id: str, member_user_id: str) -> dict:
        ws = await self.find_one(doc_id=workspace_id, bypass_cache=True)
        if not ws:
            raise NotFoundError(f"Workspace {workspace_id} not found")
        if not self._can_write(ws):
            raise PermissionError("Only workspace owner can add members")
        members = ws.get("members", [])
        if member_user_id not in members:
            members.append(member_user_id)
        return await self.update(workspace_id, {"members": members})

    async def remove_member(self, workspace_id: str, member_user_id: str) -> dict:
        ws = await self.find_one(doc_id=workspace_id, bypass_cache=True)
        if not ws:
            raise NotFoundError(f"Workspace {workspace_id} not found")
        if not self._can_write(ws):
            raise PermissionError("Only workspace owner can remove members")
        members = [m for m in ws.get("members", []) if m != member_user_id]
        return await self.update(workspace_id, {"members": members})

    async def get_active_workspace(self) -> dict | None:
        ws_id = self._ctx.workspace_id
        if ws_id:
            return await self.find_one(doc_id=ws_id)
        return await self.find_one(QuerySpec({"user_id": self._ctx.user_id}, [("updated_at", -1)]))
