"""Graph-powered recommendation engine — 15 recommendation categories."""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone

from .graph_adapter import get_adapter
from .semantic_search import _tokenise, _tfidf_vector, _cosine, _entity_text
from .inference_engine import _entity_keywords, _jaccard
from lkg.unified import get_unified_graph


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


RECOMMENDATION_CATEGORIES = [
    "people", "institutions", "projects", "grants", "journals",
    "conferences", "datasets", "marketplace_experts", "teaching_collaborators",
    "research_topics", "research_methods", "software", "courses",
    "communities", "grant_partners",
]


async def generate_all_recommendations(user_entity_id: str, db) -> dict:
    """Run all recommendation categories in parallel."""
    tasks = {
        "people":         _recommend_people(user_entity_id, db),
        "institutions":   _recommend_institutions(user_entity_id, db),
        "topics":         _recommend_topics(user_entity_id, db),
        "methods":        _recommend_methods(user_entity_id, db),
        "software":       _recommend_software(user_entity_id, db),
        "communities":    _recommend_communities(user_entity_id, db),
        "marketplace":    _recommend_marketplace(user_entity_id, db),
    }

    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    output: dict[str, list] = {}
    for key, result in zip(tasks.keys(), results):
        output[key] = result if isinstance(result, list) else []

    # Cache to akg_recommendations
    await db["akg_recommendations"].replace_one(
        {"user_entity_id": user_entity_id},
        {"user_entity_id": user_entity_id, "recommendations": output, "generated_at": _now()},
        upsert=True,
    )
    return output


async def get_cached_recommendations(user_entity_id: str, db) -> dict | None:
    doc = await db["akg_recommendations"].find_one({"user_entity_id": user_entity_id})
    if doc:
        doc.pop("_id", None)
    return doc


async def _score_candidates(entity: dict, candidates: list[dict], limit: int = 10) -> list[dict]:
    kws_a = _entity_keywords(entity)
    vec_a = _tfidf_vector(_tokenise(_entity_text(entity)))
    scored: list[tuple[float, dict]] = []
    for c in candidates:
        c_kws = _entity_keywords(c)
        vec_b = _tfidf_vector(_tokenise(_entity_text(c)))
        score = _jaccard(kws_a, c_kws) * 0.6 + _cosine(vec_a, vec_b) * 0.4
        if score > 0:
            c["rec_score"] = round(score, 4)
            scored.append((score, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored[:limit]]


async def _get_user_entity(user_entity_id: str, db) -> dict | None:
    return await get_adapter().get_entity(user_entity_id, db)


async def _recommend_people(user_entity_id: str, db) -> list[dict]:
    entity = await _get_user_entity(user_entity_id, db)
    if not entity:
        return []
    rels = await get_adapter().get_relationships(user_entity_id, "both", None, db)
    known = {user_entity_id} | {r.get("to_id") for r in rels} | {r.get("from_id") for r in rels}
    candidates = await get_unified_graph().find_nodes(db, {
        "entity_type": {"$in": ["researcher", "educator"]},
        "entity_id": {"$nin": list(known)},
    }, limit=100)
    return await _score_candidates(entity, candidates, 8)


async def _recommend_institutions(user_entity_id: str, db) -> list[dict]:
    entity = await _get_user_entity(user_entity_id, db)
    if not entity:
        return []
    candidates = await get_unified_graph().find_nodes(db, {
        "entity_type": "institution",
        "entity_id": {"$ne": user_entity_id},
    }, limit=100)
    return await _score_candidates(entity, candidates, 5)


async def _recommend_topics(user_entity_id: str, db) -> list[dict]:
    entity = await _get_user_entity(user_entity_id, db)
    if not entity:
        return []
    rels = await get_adapter().get_relationships(user_entity_id, "out", ["SPECIALIZES_IN", "RELATED_TO"], db)
    known_topic_ids = {r.get("to_id") for r in rels}
    candidates = await get_unified_graph().find_nodes(db, {
        "entity_type": {"$in": ["topic", "research_area", "keyword"]},
        "entity_id": {"$nin": list(known_topic_ids)},
    }, limit=100)
    return await _score_candidates(entity, candidates, 8)


async def _recommend_methods(user_entity_id: str, db) -> list[dict]:
    entity = await _get_user_entity(user_entity_id, db)
    if not entity:
        return []
    candidates = await get_unified_graph().find_nodes(db, {
        "entity_type": {"$in": ["method", "statistical_method"]},
    }, limit=50)
    return await _score_candidates(entity, candidates, 5)


async def _recommend_software(user_entity_id: str, db) -> list[dict]:
    entity = await _get_user_entity(user_entity_id, db)
    if not entity:
        return []
    candidates = await get_unified_graph().find_nodes(db, {
        "entity_type": {"$in": ["software", "programming_lang"]},
    }, limit=50)
    return await _score_candidates(entity, candidates, 5)


async def _recommend_communities(user_entity_id: str, db) -> list[dict]:
    entity = await _get_user_entity(user_entity_id, db)
    if not entity:
        return []
    rels = await get_adapter().get_relationships(user_entity_id, "out", ["MEMBER_OF"], db)
    member_ids = {r.get("to_id") for r in rels}
    candidates = await get_unified_graph().find_nodes(db, {
        "entity_type": "community",
        "entity_id": {"$nin": list(member_ids)},
    }, limit=50)
    return await _score_candidates(entity, candidates, 5)


async def _recommend_marketplace(user_entity_id: str, db) -> list[dict]:
    entity = await _get_user_entity(user_entity_id, db)
    if not entity:
        return []
    candidates = await get_unified_graph().find_nodes(db, {
        "entity_type": "marketplace_service",
    }, limit=100)
    return await _score_candidates(entity, candidates, 8)
