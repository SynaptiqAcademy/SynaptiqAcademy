"""Academic Knowledge Graph adapter — routes all operations through UnifiedGraphService.

Sprint 1.4: replaced MongoDBGraphAdapter with UnifiedAdapter that delegates to
lkg.unified.UnifiedGraphService (canonical lkg_nodes / lkg_edges collections).

Sprint 1.6: removed dead MongoDBGraphAdapter class; only UnifiedAdapter remains.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from datetime import datetime, timezone


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Abstract interface ─────────────────────────────────────────────────────────

class GraphAdapter(ABC):
    """All graph persistence operations go through this contract."""

    @abstractmethod
    async def upsert_entity(self, entity_id: str, entity_type: str, label: str,
                             properties: dict, db) -> dict: ...

    @abstractmethod
    async def get_entity(self, entity_id: str, db) -> dict | None: ...

    @abstractmethod
    async def delete_entity(self, entity_id: str, db) -> bool: ...

    @abstractmethod
    async def list_entities(self, entity_type: str | None, page: int, limit: int, db) -> dict: ...

    @abstractmethod
    async def upsert_relationship(self, from_id: str, to_id: str, rel_type: str,
                                   properties: dict, db) -> dict: ...

    @abstractmethod
    async def get_relationships(self, entity_id: str, direction: str,
                                 rel_types: list[str] | None, db) -> list: ...

    @abstractmethod
    async def delete_relationship(self, rel_id: str, db) -> bool: ...

    @abstractmethod
    async def get_neighbors(self, entity_id: str, depth: int,
                             rel_types: list[str] | None, db) -> dict: ...

    @abstractmethod
    async def count_entities(self, db) -> int: ...

    @abstractmethod
    async def count_relationships(self, db) -> int: ...


# ── UnifiedAdapter ────────────────────────────────────────────────────────────

class UnifiedAdapter(GraphAdapter):
    """
    Routes all graph writes through lkg.unified.UnifiedGraphService
    (canonical lkg_nodes / lkg_edges collections).

    Drop-in replacement for the retired MongoDBGraphAdapter.
    """

    def _clean(self, doc: dict) -> dict:
        if doc:
            doc.pop("_id", None)
        return doc

    async def upsert_entity(self, entity_id: str, entity_type: str, label: str,
                             properties: dict, db) -> dict:
        from lkg.unified import get_unified_graph
        return await get_unified_graph().upsert_entity(
            db, entity_type, label, properties,
            source="akg_router", node_id=entity_id,
        )

    async def get_entity(self, entity_id: str, db) -> dict | None:
        from lkg.unified import get_unified_graph
        return await get_unified_graph().get_entity(db, entity_id)

    async def delete_entity(self, entity_id: str, db) -> bool:
        from lkg.unified import get_unified_graph
        return await get_unified_graph().delete_entity(db, entity_id)

    async def list_entities(self, entity_type: str | None, page: int, limit: int, db) -> dict:
        from lkg.unified import get_unified_graph
        r = await get_unified_graph().list_entities(db, entity_type, page, limit)
        return {
            "results": r["nodes"],
            "total":   r["total"],
            "page":    r["page"],
            "pages":   max(1, -(-r["total"] // limit)),
        }

    async def upsert_relationship(self, from_id: str, to_id: str, rel_type: str,
                                   properties: dict, db) -> dict:
        from lkg.unified import get_unified_graph
        return await get_unified_graph().upsert_relationship(
            db, from_id, to_id, rel_type, properties, source="akg_router",
        )

    async def get_relationships(self, entity_id: str, direction: str,
                                 rel_types: list[str] | None, db) -> list:
        from lkg.unified import get_unified_graph
        return await get_unified_graph().get_relationships(
            db, entity_id, direction, rel_types,
        )

    async def delete_relationship(self, rel_id: str, db) -> bool:
        from lkg.unified import get_unified_graph
        try:
            from_id, to_id, rel_type = rel_id.split("::", 2)
            return await get_unified_graph().delete_relationship(db, from_id, to_id, rel_type)
        except (ValueError, AttributeError):
            try:
                from bson import ObjectId
                r = await db["lkg_edges"].delete_one({"_id": ObjectId(rel_id)})
                return bool(r.deleted_count)
            except Exception:
                return False

    async def get_neighbors(self, entity_id: str, depth: int,
                             rel_types: list[str] | None, db) -> dict:
        from lkg.unified import get_unified_graph
        return await get_unified_graph().get_neighbors(db, entity_id, depth, rel_types)

    async def count_entities(self, db) -> int:
        from lkg.unified import get_unified_graph
        return await get_unified_graph().count_nodes(db, {})

    async def count_relationships(self, db) -> int:
        from lkg.unified import get_unified_graph
        return await get_unified_graph().count_edges(db, {})


# ── Singleton ─────────────────────────────────────────────────────────────────

_ADAPTER: GraphAdapter = UnifiedAdapter()


def get_adapter() -> GraphAdapter:
    """Return the active graph adapter. Delegates to lkg.unified.UnifiedGraphService."""
    return _ADAPTER
