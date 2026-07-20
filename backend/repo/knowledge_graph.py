"""
KnowledgeGraphRepository — bounded-context repository for LKG nodes and edges.
"""
from __future__ import annotations

from .base   import BaseRepository, PermissionError
from .cache  import DEFAULT_TTL
from .specs  import QuerySpec


class KnowledgeGraphNodeRepository(BaseRepository):
    collection   = "lkg_nodes"
    event_prefix = "kg"
    cache_ttl    = DEFAULT_TTL

    def _scope_query(self, filters: dict) -> dict:
        # Nodes are scoped to workspace + user; admins see all
        if self._ctx.is_admin or self._ctx.user_id == "system":
            return filters
        if self._ctx.workspace_id:
            filters["$or"] = [
                {"user_id": self._ctx.user_id},
                {"workspace_id": self._ctx.workspace_id},
                {"visibility": "public"},
            ]
        else:
            filters["$or"] = [
                {"user_id": self._ctx.user_id},
                {"visibility": "public"},
            ]
        return filters

    async def list_nodes(
        self,
        *,
        node_type: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        filt: dict = {}
        if node_type:
            filt["type"] = node_type
        spec = QuerySpec(filt, limit=limit)
        return await self.find_many(spec)

    async def get_node(self, node_id: str) -> dict | None:
        return await self.find_one(doc_id=node_id)

    async def search_nodes(self, query: str, *, limit: int = 20) -> list[dict]:
        filt = {
            "$or": [
                {"label": {"$regex": query, "$options": "i"}},
                {"content": {"$regex": query, "$options": "i"}},
                {"tags": {"$elemMatch": {"$regex": query, "$options": "i"}}},
            ]
        }
        spec = QuerySpec(filt, limit=limit)
        return await self.find_many(spec)


class KnowledgeGraphEdgeRepository(BaseRepository):
    collection   = "lkg_edges"
    event_prefix = "kg"
    cache_ttl    = DEFAULT_TTL

    def _scope_query(self, filters: dict) -> dict:
        if self._ctx.is_admin or self._ctx.user_id == "system":
            return filters
        filters["user_id"] = self._ctx.user_id
        return filters

    async def get_edges_for_node(self, node_id: str) -> list[dict]:
        spec = QuerySpec({
            "$or": [{"source_id": node_id}, {"target_id": node_id}]
        }, limit=500)
        return await self.find_many(spec)
