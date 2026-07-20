"""Rule-based inference engine — derives implicit relationships and insights.

No LLM calls. All reasoning is graph-structural + property overlap.
"""
from __future__ import annotations
import asyncio
from .graph_adapter import get_adapter
from .semantic_search import _tokenise
from lkg.unified import get_unified_graph


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _entity_keywords(entity: dict) -> set[str]:
    props = entity.get("properties", {})
    text = " ".join([
        entity.get("label", ""),
        " ".join(props.get("research_interests", [])),
        " ".join(props.get("expertise", [])),
        " ".join(props.get("keywords", [])),
        " ".join(props.get("topics", [])),
        props.get("research_area", ""),
    ])
    return set(_tokenise(text))


async def infer_collaborator_suggestions(entity_id: str, db, limit: int = 10) -> list[dict]:
    """FOAF + keyword overlap: researchers who share collaborators or keywords."""
    adapter = get_adapter()
    entity = await adapter.get_entity(entity_id, db)
    if not entity:
        return []

    entity_kws = _entity_keywords(entity)
    rels = await adapter.get_relationships(entity_id, "both", ["COLLABORATES_WITH", "MEMBER_OF", "WORKS_AT"], db)

    known_ids: set[str] = {entity_id}
    second_degree_ids: set[str] = set()

    for r in rels:
        neighbor = r.get("to_id") if r.get("from_id") == entity_id else r.get("from_id")
        if neighbor:
            known_ids.add(neighbor)
            neighbor_rels = await adapter.get_relationships(neighbor, "both", ["COLLABORATES_WITH"], db)
            for nr in neighbor_rels:
                second = nr.get("to_id") if nr.get("from_id") == neighbor else nr.get("from_id")
                if second and second not in known_ids:
                    second_degree_ids.add(second)

    # Also pull researchers from same research area
    area = entity.get("properties", {}).get("research_area", "")
    if area:
        area_candidates = await get_unified_graph().find_nodes(db, {
            "entity_type": {"$in": ["researcher", "educator"]},
            "properties.research_area": {"$regex": area[:30], "$options": "i"},
            "entity_id": {"$nin": list(known_ids)},
        }, limit=50)
        for c in area_candidates:
            second_degree_ids.add(c.get("node_id") or c.get("entity_id", ""))

    scored: list[tuple[float, dict]] = []
    for cid in list(second_degree_ids)[:100]:
        candidate = await adapter.get_entity(cid, db)
        if not candidate:
            continue
        cand_kws = _entity_keywords(candidate)
        score = _jaccard(entity_kws, cand_kws)
        if score > 0:
            candidate["inference_score"] = round(score, 4)
            candidate["inference_reason"] = _collab_reason(entity_kws, cand_kws, known_ids, cid)
            scored.append((score, candidate))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored[:limit]]


def _collab_reason(kws_a: set, kws_b: set, known_ids: set, cid: str) -> str:
    shared = kws_a & kws_b
    if shared:
        return f"Shared expertise: {', '.join(list(shared)[:3])}"
    return "Mutual collaboration network"


async def infer_related_entities(entity_id: str, entity_type: str, db,
                                  limit: int = 10) -> list[dict]:
    """Find entities of same type with overlapping keyword profiles."""
    adapter = get_adapter()
    entity = await adapter.get_entity(entity_id, db)
    if not entity:
        return []

    kws = _entity_keywords(entity)
    if not kws:
        return []

    sample_kws = list(kws)[:5]
    or_conditions = [{"label": {"$regex": kw, "$options": "i"}} for kw in sample_kws]
    or_conditions += [{"properties.keywords": {"$regex": kw, "$options": "i"}} for kw in sample_kws[:3]]

    candidates = await get_unified_graph().find_nodes(db, {
        "entity_type": entity_type,
        "entity_id": {"$ne": entity_id},
        "$or": or_conditions,
    }, limit=100)

    scored: list[tuple[float, dict]] = []
    for c in candidates:
        c_kws = _entity_keywords(c)
        score = _jaccard(kws, c_kws)
        if score > 0:
            c.pop("_id", None)
            c["inference_score"] = round(score, 4)
            scored.append((score, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored[:limit]]


async def infer_expertise_gaps(researcher_id: str, db) -> dict:
    """Identify topics in the researcher's network they don't cover directly."""
    adapter = get_adapter()
    entity = await adapter.get_entity(researcher_id, db)
    if not entity:
        return {"gaps": [], "strengths": []}

    own_kws = _entity_keywords(entity)

    rels = await adapter.get_relationships(researcher_id, "both",
                                            ["COLLABORATES_WITH", "MEMBER_OF"], db)
    network_kws: set[str] = set()
    for r in rels[:20]:
        neighbor_id = r.get("to_id") if r.get("from_id") == researcher_id else r.get("from_id")
        if neighbor_id:
            n = await adapter.get_entity(neighbor_id, db)
            if n:
                network_kws |= _entity_keywords(n)

    gaps     = list(network_kws - own_kws)[:10]
    strengths = list(own_kws)[:10]

    return {
        "gaps":      gaps,
        "strengths": strengths,
        "coverage":  round(len(own_kws & network_kws) / max(len(network_kws), 1), 2),
    }


async def infer_grant_partners(researcher_id: str, db, limit: int = 8) -> list[dict]:
    """Suggest potential grant consortium partners via complementary expertise."""
    adapter = get_adapter()
    entity = await adapter.get_entity(researcher_id, db)
    if not entity:
        return []

    kws = _entity_keywords(entity)
    candidates = await get_unified_graph().find_nodes(db, {
        "entity_type": {"$in": ["researcher", "institution"]},
        "entity_id": {"$ne": researcher_id},
    }, limit=200)

    scored: list[tuple[float, dict]] = []
    for c in candidates:
        c_kws = _entity_keywords(c)
        overlap = _jaccard(kws, c_kws)
        complement = len(c_kws - kws) / max(len(c_kws), 1)
        score = overlap * 0.4 + complement * 0.6
        if score > 0.05:
            c.pop("_id", None)
            c["inference_score"] = round(score, 4)
            c["inference_reason"] = "Complementary expertise for consortium"
            scored.append((score, c))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored[:limit]]
