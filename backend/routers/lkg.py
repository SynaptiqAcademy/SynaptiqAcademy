"""
Living Knowledge Graph API — /api/lkg/*

All endpoints are read-only or admin-gated writes.
Ingestion runs are admin-only.
"""
from __future__ import annotations

import logging
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from auth_utils import get_current_user
from db import get_db
from zt.deps import require_admin_dep as require_admin

from lkg import (
    graph_store,
    reasoning,
    analytics as lkg_analytics,
    timeline as lkg_timeline,
    search as lkg_search,
    insights as lkg_insights,
    discovery as lkg_discovery,
)
from lkg.graph_store import ensure_indexes
from lkg.ingestion import InternalConnector, OpenAlexConnector, CrossRefConnector
from repo.shim import make_db_proxy

logger  = logging.getLogger("lkg.router")
router  = APIRouter(prefix="/api/lkg", tags=["living-knowledge-graph"])

# ─────────────────────────────────────────────────────────────────────────── #
#  Stats                                                                       #
# ─────────────────────────────────────────────────────────────────────────── #

@router.get("/stats")
async def get_stats(user=Depends(get_current_user), db=Depends(get_db)):
    """Platform-wide graph statistics (node/edge counts, type breakdown)."""
    db = make_db_proxy(db, user)
    return await graph_store.get_stats(db)


# ─────────────────────────────────────────────────────────────────────────── #
#  Node CRUD                                                                   #
# ─────────────────────────────────────────────────────────────────────────── #

@router.get("/nodes")
async def list_nodes(
    node_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    skip:  int = Query(0, ge=0),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """List LKG nodes, optionally filtered by type."""
    db = make_db_proxy(db, user)
    return {"nodes": await graph_store.list_nodes(db, node_type, limit, skip)}


@router.get("/nodes/{node_id:path}")
async def get_node(node_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    """Get a single node by its stable node_id."""
    db = make_db_proxy(db, user)
    node = await graph_store.get_node(db, node_id)
    if not node:
        raise HTTPException(404, "Node not found")
    return node


@router.get("/nodes/{node_id:path}/edges")
async def get_node_edges(
    node_id:    str,
    direction:  str = Query("both", regex="^(in|out|both)$"),
    edge_types: Optional[str] = Query(None, description="Comma-separated edge types"),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Get all edges for a node."""
    db = make_db_proxy(db, user)
    types = [t.strip() for t in edge_types.split(",")] if edge_types else None
    return {"edges": await graph_store.get_edges(db, node_id, direction, types)}


@router.get("/nodes/{node_id:path}/neighbors")
async def get_neighbors(
    node_id: str,
    depth:   int = Query(1, ge=1, le=3),
    limit:   int = Query(50, ge=1, le=200),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """BFS neighbors up to given depth."""
    db = make_db_proxy(db, user)
    return await graph_store.get_neighbors(db, node_id, depth, limit)


@router.get("/nodes/{node_id:path}/subgraph")
async def get_subgraph(
    node_id: str,
    depth:   int = Query(2, ge=1, le=3),
    limit:   int = Query(60, ge=1, le=150),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Return subgraph for visual explorer (nodes + edges within depth)."""
    db = make_db_proxy(db, user)
    return await graph_store.get_subgraph(db, node_id, depth, limit)


@router.get("/nodes/{node_id:path}/timeline")
async def get_node_timeline(node_id: str, user=Depends(get_current_user), db=Depends(get_db)):
    """Full temporal timeline of events for this node."""
    db = make_db_proxy(db, user)
    return await lkg_timeline.entity_timeline(db, node_id)


# ─────────────────────────────────────────────────────────────────────────── #
#  Path finding                                                                #
# ─────────────────────────────────────────────────────────────────────────── #

@router.get("/path")
async def find_path(
    from_id:   str = Query(...),
    to_id:     str = Query(...),
    max_depth: int = Query(4, ge=2, le=6),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Find shortest path between two nodes."""
    db = make_db_proxy(db, user)
    result = await graph_store.find_path(db, from_id, to_id, max_depth)
    if not result:
        return {"found": False, "from_id": from_id, "to_id": to_id}
    return {"found": True, "path": result}


# ─────────────────────────────────────────────────────────────────────────── #
#  Search                                                                      #
# ─────────────────────────────────────────────────────────────────────────── #

@router.get("/search")
async def search(
    q:     str = Query(..., min_length=2),
    types: Optional[str] = Query(None, description="Comma-separated node types to filter"),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Natural language search across LKG nodes."""
    db = make_db_proxy(db, user)
    return await lkg_search.natural_language_search(db, q, limit)


# ─────────────────────────────────────────────────────────────────────────── #
#  Analytics                                                                   #
# ─────────────────────────────────────────────────────────────────────────── #

@router.get("/analytics/topic-trends")
async def topic_trends(
    months: int = Query(12, ge=1, le=36),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    return {"trends": await lkg_analytics.topic_trends(db, months)}


@router.get("/analytics/entity-growth")
async def entity_growth(
    node_type: str = Query("publication"),
    months:    int = Query(12, ge=1, le=36),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    return {"growth": await lkg_analytics.entity_growth(db, node_type, months)}


@router.get("/analytics/collaboration-density")
async def collab_density(user=Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    return await lkg_analytics.collaboration_density(db)


# ─────────────────────────────────────────────────────────────────────────── #
#  Graph snapshot (temporal slider)                                            #
# ─────────────────────────────────────────────────────────────────────────── #

@router.get("/snapshot")
async def graph_snapshot(
    year:  Optional[int] = Query(None),
    month: Optional[int] = Query(None),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    return await lkg_timeline.graph_snapshot(db, year, month)


# ─────────────────────────────────────────────────────────────────────────── #
#  Reasoning                                                                   #
# ─────────────────────────────────────────────────────────────────────────── #

@router.get("/reasoning/communities")
async def detect_communities(
    edge_types: Optional[str] = Query(None),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    types = [t.strip() for t in edge_types.split(",")] if edge_types else None
    return {"communities": await reasoning.detect_communities(db, types)}


@router.get("/reasoning/centrality")
async def degree_centrality(
    node_type: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    return {"centrality": await reasoning.degree_centrality(db, node_type, limit)}


# ─────────────────────────────────────────────────────────────────────────── #
#  Insights                                                                    #
# ─────────────────────────────────────────────────────────────────────────── #

@router.get("/insights/me")
async def my_insights(user=Depends(get_current_user), db=Depends(get_db)):
    """AI insights for the authenticated researcher from graph data."""
    db = make_db_proxy(db, user)
    return await lkg_insights.generate_user_insights(db, str(user["_id"]))


@router.get("/insights/platform")
async def platform_insights(user=Depends(get_current_user), db=Depends(get_db)):
    """Platform-wide graph insights."""
    db = make_db_proxy(db, user)
    return await lkg_insights.generate_platform_insights(db)


# ─────────────────────────────────────────────────────────────────────────── #
#  Discovery                                                                   #
# ─────────────────────────────────────────────────────────────────────────── #

@router.get("/discovery/collaborators")
async def discover_collaborators(user=Depends(get_current_user), db=Depends(get_db)):
    """Discover potential collaborators via friend-of-friend graph reasoning."""
    db = make_db_proxy(db, user)
    return await lkg_discovery.discover_hidden_collaborations(db, str(user["_id"]))


@router.get("/discovery/topics")
async def discover_topics(user=Depends(get_current_user), db=Depends(get_db)):
    """Discover emerging research topics, with user overlap if authenticated."""
    db = make_db_proxy(db, user)
    return await lkg_discovery.discover_emerging_topics(db, str(user["_id"]))


@router.get("/discovery/funding")
async def discover_funding(user=Depends(get_current_user), db=Depends(get_db)):
    """Discover funding opportunities linked to user's research topics."""
    db = make_db_proxy(db, user)
    return await lkg_discovery.discover_funding_opportunities(db, str(user["_id"]))


@router.get("/discovery/reviewers/{manuscript_id}")
async def discover_reviewers(
    manuscript_id: str,
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Discover candidate reviewers for a manuscript based on topic overlap."""
    db = make_db_proxy(db, user)
    return await lkg_discovery.discover_potential_reviewers(db, manuscript_id)


# ─────────────────────────────────────────────────────────────────────────── #
#  User-specific graph views                                                   #
# ─────────────────────────────────────────────────────────────────────────── #

@router.get("/my-node")
async def my_node(user=Depends(get_current_user), db=Depends(get_db)):
    """Get the authenticated user's researcher node in the LKG."""
    db = make_db_proxy(db, user)
    node_id = f"researcher:platform:{user['_id']}"
    node    = await graph_store.get_node(db, node_id)
    if not node:
        return {
            "found": False,
            "node_id": node_id,
            "message": "Your profile is not yet in the knowledge graph. Run ORCID sync or wait for the next ingestion cycle.",
        }
    return {"found": True, "node": node}


@router.get("/my-subgraph")
async def my_subgraph(
    depth: int = Query(2, ge=1, le=3),
    user=Depends(get_current_user),
    db=Depends(get_db),
):
    """Get the authenticated user's ego subgraph for the visual explorer."""
    db = make_db_proxy(db, user)
    node_id = f"researcher:platform:{user['_id']}"
    return await graph_store.get_subgraph(db, node_id, depth, 80)


# ─────────────────────────────────────────────────────────────────────────── #
#  Ingestion — admin only                                                      #
# ─────────────────────────────────────────────────────────────────────────── #

class IngestRequest(BaseModel):
    connector: str  # "internal" | "openalex" | "crossref" | "all"
    topics:    list[str] = []


@router.post("/admin/ingest")
async def run_ingestion(
    body: IngestRequest,
    user=Depends(require_admin),
    db=Depends(get_db),
):
    """Trigger LKG ingestion pipeline (admin only)."""
    db = make_db_proxy(db, user)
    await ensure_indexes(db)
    results = []

    connectors_to_run = []
    if body.connector in ("internal", "all"):
        connectors_to_run.append(InternalConnector())
    if body.connector in ("openalex", "all"):
        connectors_to_run.append(OpenAlexConnector())
    if body.connector in ("crossref", "all"):
        connectors_to_run.append(CrossRefConnector())

    if not connectors_to_run:
        raise HTTPException(400, f"Unknown connector: {body.connector}. Use internal, openalex, crossref, or all.")

    for connector in connectors_to_run:
        kwargs = {}
        if body.topics:
            kwargs["topics"] = body.topics
        try:
            result = await connector.ingest(db, **kwargs)
            results.append(result.to_dict())
            logger.info("Ingestion %s complete: %s", connector.name, result.to_dict())
        except Exception as exc:
            results.append({"connector": connector.name, "error": str(exc)})

    return {"results": results}


@router.post("/admin/init-indexes")
async def init_indexes(user=Depends(require_admin), db=Depends(get_db)):
    """Ensure all LKG MongoDB indexes exist (idempotent)."""
    db = make_db_proxy(db, user)
    await ensure_indexes(db)
    return {"status": "ok", "message": "LKG indexes ensured"}


@router.get("/admin/jobs")
async def list_ingestion_jobs(user=Depends(require_admin), db=Depends(get_db)):
    """List recent LKG ingestion job records."""
    db = make_db_proxy(db, user)
    jobs = await db.lkg_jobs.find({}, {"_id": 0}).sort("started_at", -1).limit(20).to_list(20)
    return {"jobs": jobs}
