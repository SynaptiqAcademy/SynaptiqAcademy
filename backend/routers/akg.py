"""Academic Knowledge Graph & Intelligence Platform — /api/akg (Phase IX)"""
from fastapi import APIRouter, Depends
from worker import enqueue_job
from worker.models import Job, Priority
from pydantic import BaseModel
from typing import Optional

from auth_utils import get_current_user
from db import get_db

from services.akg import (
    entity_registry,
    relationship_engine,
    graph_traversal,
    semantic_search,
    inference_engine,
    recommendation_engine,
    graph_analytics,
    trend_discovery,
    sync_engine,
)
from zt.deps import zt_check, zt_is_admin, zt_is_super_admin
from repo.shim import make_db_proxy

router       = APIRouter(prefix="/api/akg",       tags=["akg"])
admin_router = APIRouter(prefix="/api/admin/akg", tags=["admin-akg"])


# ── Pydantic models ───────────────────────────────────────────────────────────

class EntityIn(BaseModel):
    entity_type: str
    label: str
    properties: Optional[dict] = {}


class RelationshipIn(BaseModel):
    from_id: str
    to_id:   str
    rel_type: str
    properties: Optional[dict] = {}


class SearchIn(BaseModel):
    query: str
    entity_types: Optional[list[str]] = None
    limit: Optional[int] = 20


class TraversalIn(BaseModel):
    entity_id: str
    depth: Optional[int] = 2
    rel_types: Optional[list[str]] = None


class PathIn(BaseModel):
    from_id: str
    to_id:   str


# ── Schema endpoints (public info, auth still required) ───────────────────────

@router.get("/schema/entity-types")
async def get_entity_types(user=Depends(get_current_user)):
    return {"entity_types": entity_registry.ENTITY_TYPES}


@router.get("/schema/relationship-types")
async def get_relationship_types(user=Depends(get_current_user)):
    return {
        "relationship_types": relationship_engine.RELATIONSHIP_TYPES,
        "relationship_meta":  relationship_engine.RELATIONSHIP_META,
    }


# ── Entity endpoints ──────────────────────────────────────────────────────────

@router.post("/entities")
async def create_entity(data: EntityIn, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    result = await entity_registry.create_entity(data.entity_type, data.label, data.properties or {}, db)
    await _audit(str(user["_id"]), "create_entity", data.label, db)
    return result


@router.get("/entities")
async def list_entities(entity_type: Optional[str] = None, page: int = 1, limit: int = 20,
                         user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await entity_registry.list_entities(entity_type, page, min(limit, 100), db)


@router.get("/entities/stats")
async def entity_stats(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await entity_registry.get_entity_stats(db)


@router.get("/entities/search")
async def search_entities(q: str, entity_types: Optional[str] = None, limit: int = 20,
                           user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    types = entity_types.split(",") if entity_types else None
    return await semantic_search.semantic_search(q, db, types, min(limit, 50))


@router.get("/entities/suggestions")
async def label_suggestions(prefix: str, limit: int = 10,
                              user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await semantic_search.search_suggestions(prefix, db, limit)


@router.get("/entities/{entity_id}")
async def get_entity(entity_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    e = await entity_registry.get_entity(entity_id, db)
    return e or {"error": "Entity not found"}


@router.put("/entities/{entity_id}")
async def update_entity(entity_id: str, data: EntityIn,
                         user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    from services.akg.graph_adapter import get_adapter
    adapter = get_adapter()
    existing = await adapter.get_entity(entity_id, db)
    if not existing:
        return {"error": "Entity not found"}
    return await adapter.upsert_entity(entity_id, data.entity_type, data.label,
                                        data.properties or {}, db)


@router.delete("/entities/{entity_id}")
async def delete_entity(entity_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    zt_check(user, "admin", "admin")
    ok = await entity_registry.delete_entity(entity_id, db)
    return {"deleted": ok}


# ── Relationship endpoints ────────────────────────────────────────────────────

@router.post("/relationships")
async def create_relationship(data: RelationshipIn,
                               user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    result = await relationship_engine.create_relationship(
        data.from_id, data.to_id, data.rel_type, data.properties or {}, db
    )
    return result


@router.get("/relationships/{entity_id}")
async def get_entity_relationships(entity_id: str, direction: str = "both",
                                    rel_types: Optional[str] = None,
                                    user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    types = rel_types.split(",") if rel_types else None
    return await relationship_engine.get_entity_relationships(entity_id, direction, types, db)


@router.delete("/relationships/{rel_id}")
async def delete_relationship(rel_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    zt_check(user, "admin", "admin")
    ok = await relationship_engine.delete_relationship(rel_id, db)
    return {"deleted": ok}


@router.get("/relationships/stats/summary")
async def relationship_stats(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await relationship_engine.get_relationship_stats(db)


# ── Traversal endpoints ───────────────────────────────────────────────────────

@router.post("/traverse")
async def traverse_graph(data: TraversalIn, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await graph_traversal.explore_from(data.entity_id, db, data.depth or 2, data.rel_types)


@router.get("/traverse/{entity_id}")
async def traverse_entity(entity_id: str, depth: int = 2, rel_types: Optional[str] = None,
                           user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    types = rel_types.split(",") if rel_types else None
    return await graph_traversal.explore_from(entity_id, db, depth, types)


@router.post("/path")
async def find_path(data: PathIn, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await graph_traversal.find_shortest_path(data.from_id, data.to_id, db)


@router.get("/common-neighbors")
async def common_neighbors(entity_a: str, entity_b: str,
                            user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await graph_traversal.get_common_neighbors(entity_a, entity_b, db)


# ── Inference / AI Reasoning endpoints ───────────────────────────────────────

@router.get("/inference/collaborators/{entity_id}")
async def infer_collaborators(entity_id: str, limit: int = 10,
                               user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await inference_engine.infer_collaborator_suggestions(entity_id, db, limit)


@router.get("/inference/related/{entity_id}")
async def infer_related(entity_id: str, entity_type: str = "researcher",
                         limit: int = 10, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await inference_engine.infer_related_entities(entity_id, entity_type, db, limit)


@router.get("/inference/expertise-gaps/{entity_id}")
async def expertise_gaps(entity_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await inference_engine.infer_expertise_gaps(entity_id, db)


@router.get("/inference/grant-partners/{entity_id}")
async def grant_partners(entity_id: str, limit: int = 8,
                          user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await inference_engine.infer_grant_partners(entity_id, db, limit)


# ── Recommendation endpoints ──────────────────────────────────────────────────

@router.get("/recommendations/{entity_id}")
async def get_recommendations(entity_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    cached = await recommendation_engine.get_cached_recommendations(entity_id, db)
    if cached:
        return cached
    return await recommendation_engine.generate_all_recommendations(entity_id, db)


@router.post("/recommendations/{entity_id}/refresh")
async def refresh_recommendations(entity_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    await enqueue_job(Job(job_type="recommendation.generate", payload={"entity_id": entity_id},
                         user_id=str(user["_id"]), priority=Priority.NORMAL), db)
    return {"status": "Recommendations refresh queued"}


# ── Analytics endpoints ───────────────────────────────────────────────────────

@router.get("/analytics/overview")
async def graph_overview(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await graph_analytics.get_network_overview(db)


@router.get("/analytics/centrality")
async def degree_centrality(entity_type: Optional[str] = None, top_n: int = 20,
                             user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await graph_analytics.compute_degree_centrality(db, entity_type, top_n)


@router.get("/analytics/influence")
async def influence_scores(top_n: int = 20, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await graph_analytics.compute_influence_score(db, top_n)


@router.get("/analytics/communities")
async def communities(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await graph_analytics.detect_communities(db)


@router.get("/analytics/density")
async def collaboration_density(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await graph_analytics.compute_collaboration_density(db)


# ── Trend endpoints ───────────────────────────────────────────────────────────

@router.get("/trends")
async def all_trends(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await trend_discovery.get_full_trend_report(db)


@router.get("/trends/emerging-topics")
async def emerging_topics(window_days: int = 30, top_n: int = 15,
                           user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await trend_discovery.discover_emerging_topics(db, window_days, top_n)


@router.get("/trends/hot-areas")
async def hot_research_areas(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await trend_discovery.discover_hot_research_areas(db)


@router.get("/trends/institutional-growth")
async def institutional_growth(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await trend_discovery.get_institutional_growth(db)


@router.get("/trends/collaboration")
async def collaboration_trends(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await trend_discovery.get_collaboration_trends(db)


# ── Sync endpoints ────────────────────────────────────────────────────────────

@router.get("/sync/status")
async def sync_status(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await sync_engine.get_sync_status(db)


@router.post("/sync/trigger")
async def trigger_sync(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    await enqueue_job(Job(job_type="kg.update", payload={"scope": "full_sync"},
                         user_id=str(user["_id"]), priority=Priority.LOW), db)
    return {"status": "Full sync queued in background"}


# ── User-specific entity lookup ───────────────────────────────────────────────

@router.get("/me/entity")
async def my_entity(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    entity_id = f"user:{str(user['_id'])}"
    e = await entity_registry.get_entity(entity_id, db)
    return e or {"entity_id": entity_id, "entity_type": "researcher",
                 "label": user.get("name", ""), "synced": False}


@router.get("/me/graph")
async def my_graph(depth: int = 2, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    entity_id = f"user:{str(user['_id'])}"
    return await graph_traversal.explore_from(entity_id, db, depth)


@router.get("/me/recommendations")
async def my_recommendations(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    entity_id = f"user:{str(user['_id'])}"
    cached = await recommendation_engine.get_cached_recommendations(entity_id, db)
    if cached:
        return cached
    return await recommendation_engine.generate_all_recommendations(entity_id, db)


@router.get("/me/inference/collaborators")
async def my_collaborator_suggestions(limit: int = 10,
                                       user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    entity_id = f"user:{str(user['_id'])}"
    return await inference_engine.infer_collaborator_suggestions(entity_id, db, limit)


@router.get("/me/inference/expertise-gaps")
async def my_expertise_gaps(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    entity_id = f"user:{str(user['_id'])}"
    return await inference_engine.infer_expertise_gaps(entity_id, db)


# ── Admin endpoints ───────────────────────────────────────────────────────────

@admin_router.get("/stats")
async def admin_stats(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    zt_check(user, "admin", "admin")
    return await graph_analytics.get_network_overview(db)


@admin_router.post("/sync/full")
async def admin_full_sync(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    zt_check(user, "admin", "admin")
    await enqueue_job(Job(job_type="kg.update", payload={"scope": "full_sync"},
                         user_id=str(user["_id"]), priority=Priority.HIGH), db)
    return {"status": "Full AKG sync queued"}


@admin_router.get("/audit")
async def admin_audit(limit: int = 50, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    zt_check(user, "admin", "admin")
    cursor = db["akg_audit"].find({}).sort("at", -1).limit(limit)
    docs = await cursor.to_list(limit)
    for d in docs:
        d.pop("_id", None)
    return docs


@admin_router.delete("/entity/{entity_id}")
async def admin_delete_entity(entity_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    zt_check(user, "admin", "admin")
    ok = await entity_registry.delete_entity(entity_id, db)
    return {"deleted": ok}


@admin_router.get("/communities")
async def admin_communities(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    zt_check(user, "admin", "admin")
    return await graph_analytics.detect_communities(db)


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _audit(user_id: str, action: str, target: str, db):
    from datetime import datetime, timezone
    await db["akg_audit"].insert_one({
        "user_id": user_id, "action": action, "target": target,
        "at": datetime.now(timezone.utc).isoformat()
    })
