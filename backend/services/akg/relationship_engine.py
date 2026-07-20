"""Relationship (edge) management for the Academic Knowledge Graph."""
from __future__ import annotations
from .graph_adapter import get_adapter
from lkg.unified import get_unified_graph

RELATIONSHIP_TYPES: list[str] = [
    "AUTHORED",        "CO_AUTHORED",      "WORKS_AT",         "WORKED_AT",
    "COLLABORATES_WITH","MENTORS",          "SUPERVISES",       "MEMBER_OF",
    "LEADS",           "PARTICIPATES_IN",  "FUNDED_BY",        "PUBLISHED_IN",
    "REVIEWS",         "EDITS",            "CITES",            "CITED_BY",
    "USES_METHOD",     "USES_DATASET",     "USES_SOFTWARE",    "BELONGS_TO",
    "CONNECTED_TO",    "RELATED_TO",       "SIMILAR_TO",       "SPECIALIZES_IN",
    "TEACHES",         "STUDIES",          "ATTENDED",         "ORGANIZED",
    "VERIFIED_BY",     "RECOMMENDED_FOR",  "LOCATED_IN",       "AFFILIATED_WITH",
    "PRODUCES",        "EMPLOYS",          "INVESTIGATES",
]

RELATIONSHIP_META: dict[str, dict] = {
    "AUTHORED":          {"label": "authored",           "inverse": "AUTHORED_BY",     "bidirectional": False},
    "CO_AUTHORED":       {"label": "co-authored",        "inverse": "CO_AUTHORED",     "bidirectional": True},
    "WORKS_AT":          {"label": "works at",           "inverse": "EMPLOYS",         "bidirectional": False},
    "COLLABORATES_WITH": {"label": "collaborates with",  "inverse": "COLLABORATES_WITH","bidirectional": True},
    "MENTORS":           {"label": "mentors",            "inverse": "MENTORED_BY",     "bidirectional": False},
    "SUPERVISES":        {"label": "supervises",         "inverse": "SUPERVISED_BY",   "bidirectional": False},
    "MEMBER_OF":         {"label": "member of",          "inverse": "HAS_MEMBER",      "bidirectional": False},
    "LEADS":             {"label": "leads",              "inverse": "LED_BY",          "bidirectional": False},
    "FUNDED_BY":         {"label": "funded by",          "inverse": "FUNDS",           "bidirectional": False},
    "PUBLISHED_IN":      {"label": "published in",       "inverse": "PUBLISHES",       "bidirectional": False},
    "CITES":             {"label": "cites",              "inverse": "CITED_BY",        "bidirectional": False},
    "SIMILAR_TO":        {"label": "similar to",         "inverse": "SIMILAR_TO",      "bidirectional": True},
    "SPECIALIZES_IN":    {"label": "specializes in",     "inverse": "EXPERTISE_FROM",  "bidirectional": False},
    "TEACHES":           {"label": "teaches",            "inverse": "TAUGHT_BY",       "bidirectional": False},
    "AFFILIATED_WITH":   {"label": "affiliated with",    "inverse": "AFFILIATED_WITH", "bidirectional": True},
    "LOCATED_IN":        {"label": "located in",         "inverse": "CONTAINS",        "bidirectional": False},
    "RELATED_TO":        {"label": "related to",         "inverse": "RELATED_TO",      "bidirectional": True},
}


async def create_relationship(from_id: str, to_id: str, rel_type: str,
                               properties: dict, db) -> dict:
    if rel_type not in RELATIONSHIP_TYPES:
        return {"error": f"Unknown relationship type: {rel_type}"}
    adapter = get_adapter()
    from_ent = await adapter.get_entity(from_id, db)
    to_ent   = await adapter.get_entity(to_id,   db)
    if not from_ent:
        return {"error": f"Source entity not found: {from_id}"}
    if not to_ent:
        return {"error": f"Target entity not found: {to_id}"}
    return await adapter.upsert_relationship(from_id, to_id, rel_type, properties, db)


async def get_entity_relationships(entity_id: str, direction: str,
                                    rel_types: list[str] | None, db) -> dict:
    adapter = get_adapter()
    rels = await adapter.get_relationships(entity_id, direction, rel_types, db)

    entity_ids = set()
    for r in rels:
        entity_ids.add(r.get("from_id"))
        entity_ids.add(r.get("to_id"))
    entity_ids.discard(entity_id)

    entities = {}
    for eid in entity_ids:
        e = await adapter.get_entity(eid, db)
        if e:
            entities[eid] = e

    enriched = []
    for r in rels:
        r_copy = dict(r)
        other_id = r_copy.get("to_id") if r_copy.get("from_id") == entity_id else r_copy.get("from_id")
        r_copy["other_entity"] = entities.get(other_id, {})
        r_copy["direction"] = "out" if r_copy.get("from_id") == entity_id else "in"
        enriched.append(r_copy)

    return {"relationships": enriched, "count": len(enriched)}


async def delete_relationship(rel_id: str, db) -> bool:
    return await get_adapter().delete_relationship(rel_id, db)


async def get_relationship_stats(db) -> dict:
    unified = get_unified_graph()
    by_type = await unified.group_edges_by_type(db)
    total = sum(by_type.values())
    return {
        "total": total,
        "by_type": dict(sorted(by_type.items(), key=lambda x: -x[1])),
        "relationship_types": RELATIONSHIP_TYPES,
    }
