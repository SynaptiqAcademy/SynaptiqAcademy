"""AcademicKnowledgeGraph — MongoDB-backed entity and relationship store.

Stores researchers, publications, institutions, journals, conferences, grants,
topics, methods and the links between them. Queries return contextual
information injected into academic context for richer reasoning.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("synaptiq.academic.graph")

_ENTITIES_COLL = "academic_kg_entities"
_RELATIONS_COLL = "academic_kg_relations"

# Valid entity types
ENTITY_TYPES = frozenset({
    "researcher", "publication", "institution", "journal",
    "conference", "grant", "topic", "keyword", "method",
})

# Valid relation types
RELATION_TYPES = frozenset({
    "authored_by", "cites", "affiliated_with", "funded_by",
    "published_in", "presented_at", "co_authored", "related_topic",
    "uses_method", "reviews_for",
})


class AcademicKnowledgeGraph:
    """Lightweight graph store for academic entities and relationships."""

    def __init__(self, db: Any) -> None:
        self._db = db

    # ── Entity CRUD ────────────────────────────────────────────────────────────

    async def upsert_entity(
        self,
        entity_type: str,
        external_id: str,
        properties: dict,
        user_id: str = "platform",
    ) -> str:
        """Create or update an entity. Returns the stored _id."""
        if entity_type not in ENTITY_TYPES:
            raise ValueError(f"Unknown entity type: {entity_type}")
        doc = {
            "_id": f"{entity_type}:{external_id}",
            "type": entity_type,
            "external_id": external_id,
            "user_id": user_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            **properties,
        }
        try:
            await self._db[_ENTITIES_COLL].replace_one(
                {"_id": doc["_id"]}, doc, upsert=True
            )
        except Exception as exc:
            logger.debug("KG upsert_entity failed: %s", exc)
        return doc["_id"]

    async def get_entity(self, entity_type: str, external_id: str) -> dict | None:
        try:
            doc = await self._db[_ENTITIES_COLL].find_one(
                {"_id": f"{entity_type}:{external_id}"}
            )
            if doc:
                doc.pop("_id", None)
            return doc
        except Exception:
            return None

    async def add_relation(
        self,
        from_type: str, from_id: str,
        relation: str,
        to_type: str, to_id: str,
        properties: dict | None = None,
    ) -> None:
        if relation not in RELATION_TYPES:
            raise ValueError(f"Unknown relation type: {relation}")
        doc = {
            "from_id": f"{from_type}:{from_id}",
            "relation": relation,
            "to_id": f"{to_type}:{to_id}",
            "created_at": datetime.now(timezone.utc).isoformat(),
            **(properties or {}),
        }
        try:
            await self._db[_RELATIONS_COLL].update_one(
                {"from_id": doc["from_id"], "relation": relation, "to_id": doc["to_id"]},
                {"$set": doc},
                upsert=True,
            )
        except Exception as exc:
            logger.debug("KG add_relation failed: %s", exc)

    # ── Query methods ──────────────────────────────────────────────────────────

    async def get_related_topics(self, keyword: str, limit: int = 10) -> list[str]:
        """Return topic names related to a keyword."""
        try:
            docs = await self._db[_ENTITIES_COLL].find(
                {"type": "topic", "$text": {"$search": keyword}}
            ).limit(limit).to_list(length=limit)
            return [d.get("name", d.get("external_id", "")) for d in docs]
        except Exception:
            # Text index may not exist — fallback to regex
            try:
                docs = await self._db[_ENTITIES_COLL].find(
                    {"type": "topic", "name": {"$regex": keyword, "$options": "i"}}
                ).limit(limit).to_list(length=limit)
                return [d.get("name", "") for d in docs]
            except Exception:
                return []

    async def get_user_research_topics(self, user_id: str, limit: int = 10) -> list[str]:
        """Return topics this user has interacted with."""
        try:
            docs = await self._db[_ENTITIES_COLL].find(
                {"type": "topic", "user_id": user_id}
            ).sort("updated_at", -1).limit(limit).to_list(length=limit)
            return [d.get("name", d.get("external_id", "")) for d in docs]
        except Exception:
            return []

    async def get_recommended_journals(self, topic: str, limit: int = 5) -> list[str]:
        """Return journal names relevant to a topic."""
        try:
            docs = await self._db[_ENTITIES_COLL].find(
                {"type": "journal", "topics": {"$elemMatch": {"$regex": topic, "$options": "i"}}}
            ).limit(limit).to_list(length=limit)
            return [d.get("name", "") for d in docs]
        except Exception:
            return []

    async def record_user_topic(self, user_id: str, topic: str) -> None:
        """Record that a user engaged with a topic."""
        await self.upsert_entity(
            entity_type="topic",
            external_id=f"{user_id}:{topic.lower().replace(' ', '_')}",
            properties={"name": topic, "user_id": user_id},
            user_id=user_id,
        )

    async def get_stats(self) -> dict:
        """Return graph statistics for the admin dashboard."""
        try:
            entity_count = await self._db[_ENTITIES_COLL].count_documents({})
            relation_count = await self._db[_RELATIONS_COLL].count_documents({})
            type_pipeline = [{"$group": {"_id": "$type", "count": {"$sum": 1}}}]
            type_docs = await self._db[_ENTITIES_COLL].aggregate(type_pipeline).to_list(length=20)
            type_dist = {d["_id"]: d["count"] for d in type_docs}
            return {
                "total_entities": entity_count,
                "total_relations": relation_count,
                "entity_types": type_dist,
            }
        except Exception as exc:
            logger.warning("KG stats failed: %s", exc)
            return {"total_entities": 0, "total_relations": 0, "entity_types": {}}
