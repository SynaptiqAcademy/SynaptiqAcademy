"""Academic Knowledge Graph Intelligence Engine — Router (Phase XVII).

User endpoints:  /api/knowledge-graph/*
Admin endpoints: /api/admin/knowledge-graph/*
Public endpoint: /api/knowledge-graph/available-types  (no auth)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from auth_utils import get_current_user
from services.credits_service import consume_credits
from plans_catalogue import get_credit_cost
from services.knowledge_graph import get_kg_engine
from services.knowledge_graph.models import NodeType, RelType, QueryScope, VizType

router       = APIRouter(prefix="/api/knowledge-graph",       tags=["Knowledge Graph"])
admin_router = APIRouter(prefix="/api/admin/knowledge-graph", tags=["Admin: Knowledge Graph"])


# ── Pydantic models ───────────────────────────────────────────────────────────

class ImportDataRequest(BaseModel):
    data: dict


class AddNodeRequest(BaseModel):
    node_type:  str
    label:      str
    properties: dict | None = None


class AddEdgeRequest(BaseModel):
    source_id: str
    target_id: str
    rel_type:  str
    weight:    float = 1.0


class QueryRequest(BaseModel):
    query: dict


class TopicQueryRequest(BaseModel):
    topic:  str
    scope:  str = "all"
    depth:  int = 2


class PathQueryRequest(BaseModel):
    source_id: str
    target_id: str


class SearchRequest(BaseModel):
    keyword:   str
    node_type: str | None = None


class EmbedRequest(BaseModel):
    node_id: str
    dim:     int = 16


class SimilarNodesRequest(BaseModel):
    node_id:   str
    top_k:     int = 10
    node_type: str | None = None


class VizRequest(BaseModel):
    viz_type:  str
    max_nodes: int = 200


class CopilotEnrichRequest(BaseModel):
    query:              str
    researcher_node_id: str | None = None


class CopilotRecommendRequest(BaseModel):
    researcher_node_id:  str
    recommendation_type: str = "collaboration"


class CitationPathRequest(BaseModel):
    source_id: str
    target_id: str
    max_depth: int = 5


# ── Public ────────────────────────────────────────────────────────────────────

@router.get("/available-types")
async def available_types():
    """Return all supported node types, relationship types, viz types, and query scopes."""
    return {
        "node_types":       [e.value for e in NodeType],
        "relationship_types": [e.value for e in RelType],
        "viz_types":        [e.value for e in VizType],
        "query_scopes":     [e.value for e in QueryScope],
    }


# ── Data ingestion ────────────────────────────────────────────────────────────

@router.post("/import")
async def import_data(
    body: ImportDataRequest,
    current_user: dict = Depends(get_current_user),
):
    cost = get_credit_cost("kg_import", 10)
    await consume_credits(current_user["_id"], "kg_import")
    engine = await get_kg_engine()
    return engine.import_data(body.data)


@router.post("/nodes")
async def add_node(
    body: AddNodeRequest,
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "kg_add_node")
    engine = await get_kg_engine()
    return engine.add_node(body.node_type, body.label, body.properties)


@router.post("/edges")
async def add_edge(
    body: AddEdgeRequest,
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "kg_add_edge")
    engine = await get_kg_engine()
    return engine.add_edge(body.source_id, body.target_id, body.rel_type, body.weight)


# ── Graph info ────────────────────────────────────────────────────────────────

@router.get("/stats")
async def graph_stats(current_user: dict = Depends(get_current_user)):
    await consume_credits(current_user["_id"], "kg_stats")
    engine = await get_kg_engine()
    return engine.graph_stats()


@router.get("/nodes/{node_id}")
async def get_node(
    node_id: str,
    current_user: dict = Depends(get_current_user),
):
    engine = await get_kg_engine()
    result = engine.node_info(node_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ── Analytics ─────────────────────────────────────────────────────────────────

@router.get("/analytics/pagerank")
async def pagerank(
    top_k: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "kg_analytics")
    engine = await get_kg_engine()
    pr = engine.run_pagerank()
    sorted_pr = sorted(pr.items(), key=lambda x: -x[1])[:top_k]
    return {"pagerank": [{"node_id": k, "score": round(v, 6)} for k, v in sorted_pr]}


@router.get("/analytics/influence")
async def top_influence(
    top_k: int = Query(20, ge=1, le=100),
    node_type: str | None = Query(None),
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "kg_analytics")
    engine = await get_kg_engine()
    return {"nodes": engine.top_nodes_by_influence(top_k, node_type)}


# ── Community detection ───────────────────────────────────────────────────────

@router.get("/communities")
async def communities(current_user: dict = Depends(get_current_user)):
    await consume_credits(current_user["_id"], "kg_communities")
    engine = await get_kg_engine()
    return engine.detect_communities()


# ── Embeddings ────────────────────────────────────────────────────────────────

@router.post("/embeddings/node")
async def embed_node(
    body: EmbedRequest,
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "kg_embeddings")
    engine = await get_kg_engine()
    result = engine.embed_node(body.node_id, body.dim)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/embeddings/similar")
async def similar_nodes(
    body: SimilarNodesRequest,
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "kg_embeddings")
    engine = await get_kg_engine()
    return {"similar": engine.similar_nodes(body.node_id, body.top_k, body.node_type)}


# ── Semantic reasoning ────────────────────────────────────────────────────────

@router.get("/reasoning/hidden-collaborators")
async def hidden_collaborators(
    researcher_id: str = Query(...),
    max_results: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "kg_reasoning")
    engine = await get_kg_engine()
    return {"collaborators": engine.hidden_collaborators(researcher_id, max_results)}


@router.get("/reasoning/emerging-topics")
async def emerging_topics(
    top_k: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "kg_reasoning")
    engine = await get_kg_engine()
    return {"topics": engine.emerging_topics(top_k)}


@router.get("/reasoning/isolated-researchers")
async def isolated_researchers(current_user: dict = Depends(get_current_user)):
    await consume_credits(current_user["_id"], "kg_reasoning")
    engine = await get_kg_engine()
    return {"researchers": engine.isolated_researchers()}


@router.get("/reasoning/influential-methods")
async def influential_methods(
    top_k: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "kg_reasoning")
    engine = await get_kg_engine()
    return {"methods": engine.influential_methods(top_k)}


@router.get("/reasoning/foundational-publications")
async def foundational_publications(
    top_k: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "kg_reasoning")
    engine = await get_kg_engine()
    return {"publications": engine.foundational_publications(top_k)}


@router.get("/reasoning/interdisciplinary-opportunities")
async def interdisciplinary_opportunities(
    researcher_id: str = Query(...),
    top_k: int = Query(5, ge=1, le=20),
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "kg_reasoning")
    engine = await get_kg_engine()
    return {"opportunities": engine.interdisciplinary_opportunities(researcher_id, top_k)}


@router.post("/reasoning/citation-paths")
async def citation_paths(
    body: CitationPathRequest,
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "kg_reasoning")
    engine = await get_kg_engine()
    return {"paths": engine.citation_paths(body.source_id, body.target_id, body.max_depth)}


@router.get("/reasoning/future-collaborations")
async def future_collaborations(
    researcher_id: str = Query(...),
    top_k: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "kg_reasoning")
    engine = await get_kg_engine()
    return {"collaborations": engine.future_collaborations(researcher_id, top_k)}


# ── Knowledge discovery ───────────────────────────────────────────────────────

@router.get("/discovery/clusters")
async def knowledge_clusters(current_user: dict = Depends(get_current_user)):
    await consume_credits(current_user["_id"], "kg_discovery")
    engine = await get_kg_engine()
    return {"clusters": engine.knowledge_clusters()}


@router.get("/discovery/topic-evolution")
async def topic_evolution(
    top_k: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "kg_discovery")
    engine = await get_kg_engine()
    return {"topics": engine.topic_evolution(top_k)}


@router.get("/discovery/interdisciplinary-bridges")
async def interdisciplinary_bridges(
    top_k: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "kg_discovery")
    engine = await get_kg_engine()
    return {"bridges": engine.interdisciplinary_bridges(top_k)}


@router.get("/discovery/methodological-trends")
async def methodological_trends(
    top_k: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "kg_discovery")
    engine = await get_kg_engine()
    return {"trends": engine.methodological_trends(top_k)}


@router.get("/discovery/new-research-areas")
async def new_research_areas(
    top_k: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "kg_discovery")
    engine = await get_kg_engine()
    return {"areas": engine.new_research_areas(top_k)}


@router.get("/discovery/citation-communities")
async def citation_communities(
    top_k: int = Query(5, ge=1, le=20),
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "kg_discovery")
    engine = await get_kg_engine()
    return {"communities": engine.citation_communities(top_k)}


# ── Queries ───────────────────────────────────────────────────────────────────

@router.post("/query")
async def graph_query(
    body: QueryRequest,
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "kg_query")
    engine = await get_kg_engine()
    return engine.query(body.query)


@router.post("/query/topic")
async def topic_query(
    body: TopicQueryRequest,
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "kg_query")
    engine = await get_kg_engine()
    return engine.query_topic(body.topic, body.scope, body.depth)


@router.post("/query/path")
async def path_query(
    body: PathQueryRequest,
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "kg_query")
    engine = await get_kg_engine()
    return engine.query_path(body.source_id, body.target_id)


@router.post("/query/search")
async def search_query(
    body: SearchRequest,
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "kg_query")
    engine = await get_kg_engine()
    return engine.search_nodes(body.keyword, body.node_type)


# ── Visualization ─────────────────────────────────────────────────────────────

@router.post("/visualization")
async def visualization(
    body: VizRequest,
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "kg_visualization")
    engine = await get_kg_engine()
    return engine.visualize(body.viz_type, max_nodes=body.max_nodes)


# ── Copilot integration ───────────────────────────────────────────────────────

@router.post("/copilot/enrich")
async def copilot_enrich(
    body: CopilotEnrichRequest,
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "kg_copilot")
    engine = await get_kg_engine()
    return engine.copilot_enrich(body.query, body.researcher_node_id)


@router.post("/copilot/recommend")
async def copilot_recommend(
    body: CopilotRecommendRequest,
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "kg_copilot")
    engine = await get_kg_engine()
    return {"recommendations": engine.copilot_recommend(
        body.researcher_node_id, body.recommendation_type
    )}


# ── Admin endpoints ───────────────────────────────────────────────────────────

@admin_router.get("/dashboard")
async def admin_dashboard(
    top_k: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
):
    engine = await get_kg_engine()
    return engine.admin_dashboard(top_k)


@admin_router.get("/telemetry")
async def admin_telemetry(current_user: dict = Depends(get_current_user)):
    from services.knowledge_graph.telemetry import get_telemetry
    return get_telemetry().to_dict()


@admin_router.post("/reset")
async def admin_reset(current_user: dict = Depends(get_current_user)):
    engine = await get_kg_engine()
    return engine.admin_reset_graph()
