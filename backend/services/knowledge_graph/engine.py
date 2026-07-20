"""Academic Knowledge Graph Intelligence Engine — Async singleton facade (Phase XVII)."""
from __future__ import annotations

import asyncio
import time
from typing import Any

from .admin_analytics    import admin_dashboard
from .community_detection import detect_communities, profile_communities
from .copilot_integration import enrich_copilot_context, graph_enhanced_recommendation
from .embedding_engine   import embed_all, embed_node, similar_nodes
from .graph_analytics    import (
    betweenness_centrality_approx, closeness_centrality, compute_graph_stats,
    compute_node_analytics, degree_centrality, knowledge_influence_scores, pagerank,
)
from .graph_builder      import import_platform_data
from .graph_query        import complex_query, query_by_topic, query_path, query_type_filter
from .graph_store        import AcademicKnowledgeGraph, create_graph
from .knowledge_discovery import (
    detect_methodological_trends, detect_topic_evolution,
    discover_knowledge_clusters, find_interdisciplinary_bridges,
    find_new_research_areas, identify_citation_communities,
)
from .models             import NodeType, QueryScope, RelType, VizType
from .semantic_reasoner  import (
    detect_isolated_researchers, discover_citation_paths,
    find_emerging_topics, find_foundational_publications,
    find_hidden_collaborators, find_influential_methods,
    find_interdisciplinary_opportunities, identify_future_collaborations,
)
from .telemetry          import get_telemetry
from .visualization_builder import build_visualization


class KnowledgeGraphEngine:
    """
    Unified facade for the Academic Knowledge Graph Intelligence Engine.

    Holds a single AcademicKnowledgeGraph instance that evolves over the server
    lifetime. All method calls are synchronous and safe to call from async contexts.
    """

    def __init__(self) -> None:
        self._graph: AcademicKnowledgeGraph = create_graph()
        # Cached analytics (invalidated on import)
        self._pr_cache:  dict[str, float]            | None = None
        self._comm_cache: dict[str, int]             | None = None
        self._emb_cache:  dict[str, Any]             | None = None

    @property
    def graph(self) -> AcademicKnowledgeGraph:
        return self._graph

    def _invalidate_cache(self) -> None:
        self._pr_cache   = None
        self._comm_cache = None
        self._emb_cache  = None

    # ── Data ingestion ────────────────────────────────────────────────────────

    def import_data(self, data: dict) -> dict:
        t0 = time.monotonic()
        tel = get_telemetry()
        try:
            result = import_platform_data(self._graph, data)
            self._invalidate_cache()
            tel.inc("import_calls")
            tel.inc("nodes_added", result.get("nodes_added", 0))
            tel.inc("edges_added", result.get("edges_added", 0))
            return result
        except Exception:
            tel.inc("errors")
            raise
        finally:
            tel.record_latency(time.monotonic() - t0)

    def add_node(self, node_type: str, label: str, properties: dict | None = None) -> dict:
        try:
            nt = NodeType(node_type)
        except ValueError:
            nt = NodeType.CONCEPT
        node = self._graph.get_or_create_node(nt, label, properties)
        self._invalidate_cache()
        get_telemetry().inc("nodes_added")
        return node.to_dict()

    def add_edge(self, source_id: str, target_id: str, rel_type: str,
                 weight: float = 1.0) -> dict:
        try:
            rt = RelType(rel_type)
        except ValueError:
            rt = RelType.INFLUENCES
        edge = self._graph.add_edge(source_id, target_id, rt, weight)
        if edge:
            self._invalidate_cache()
            get_telemetry().inc("edges_added")
            return edge.to_dict()
        return {"error": "One or both nodes not found."}

    # ── Graph stats ───────────────────────────────────────────────────────────

    def graph_stats(self) -> dict:
        return compute_graph_stats(self._graph).to_dict()

    def node_info(self, node_id: str) -> dict:
        node = self._graph.get_node(node_id)
        if not node:
            return {"error": f"Node '{node_id}' not found."}
        return {**node.to_dict(), "degree": self._graph.degree(node_id),
                "in_degree": self._graph.in_degree(node_id),
                "out_degree": self._graph.out_degree(node_id)}

    # ── Analytics ─────────────────────────────────────────────────────────────

    def run_pagerank(self) -> dict[str, float]:
        t0 = time.monotonic()
        tel = get_telemetry()
        try:
            if self._pr_cache is None:
                self._pr_cache = pagerank(self._graph)
            tel.inc("pagerank_runs")
            return self._pr_cache
        finally:
            tel.record_latency(time.monotonic() - t0)

    def top_nodes_by_influence(self, top_k: int = 20, node_type: str | None = None) -> list[dict]:
        pr = self.run_pagerank()
        dc = degree_centrality(self._graph)
        bc = betweenness_centrality_approx(self._graph)
        results = compute_node_analytics(self._graph, pr=pr, bc=bc, dc=dc, top_k=top_k)
        if node_type:
            results = [r for r in results if r.node_type == node_type]
        return [r.to_dict() for r in results[:top_k]]

    # ── Community detection ───────────────────────────────────────────────────

    def detect_communities(self) -> dict:
        t0 = time.monotonic()
        tel = get_telemetry()
        try:
            if self._comm_cache is None:
                self._comm_cache = detect_communities(self._graph)
            communities = profile_communities(self._graph, self._comm_cache)
            tel.inc("community_runs")
            return {
                "community_map": self._comm_cache,
                "communities":   [c.to_dict() for c in communities],
                "total":         len(communities),
            }
        finally:
            tel.record_latency(time.monotonic() - t0)

    # ── Embeddings ────────────────────────────────────────────────────────────

    def embed_node(self, node_id: str, dim: int = 16) -> dict:
        tel = get_telemetry()
        emb = embed_node(self._graph, node_id, dim)
        tel.inc("embedding_runs")
        return emb.to_dict() if emb else {"error": f"Node '{node_id}' not found."}

    def similar_nodes(
        self,
        node_id: str,
        top_k: int = 10,
        node_type: str | None = None,
    ) -> list[dict]:
        tel = get_telemetry()
        nt = NodeType(node_type) if node_type else None
        if self._emb_cache is None:
            self._emb_cache = embed_all(self._graph)
        result = similar_nodes(self._graph, node_id, top_k=top_k,
                                node_type_filter=nt, embeddings=self._emb_cache)
        tel.inc("embedding_runs")
        return result

    # ── Semantic reasoning ────────────────────────────────────────────────────

    def hidden_collaborators(self, researcher_id: str, max_results: int = 10) -> list[dict]:
        tel = get_telemetry()
        tel.inc("reasoning_calls")
        return [r.to_dict() for r in find_hidden_collaborators(self._graph, researcher_id, max_results)]

    def emerging_topics(self, top_k: int = 10) -> list[dict]:
        tel = get_telemetry()
        tel.inc("reasoning_calls")
        return find_emerging_topics(self._graph, top_k)

    def isolated_researchers(self) -> list[dict]:
        tel = get_telemetry()
        tel.inc("reasoning_calls")
        return detect_isolated_researchers(self._graph)

    def influential_methods(self, top_k: int = 10) -> list[dict]:
        tel = get_telemetry()
        tel.inc("reasoning_calls")
        return find_influential_methods(self._graph, top_k)

    def foundational_publications(self, top_k: int = 10) -> list[dict]:
        tel = get_telemetry()
        tel.inc("reasoning_calls")
        return find_foundational_publications(self._graph, top_k)

    def interdisciplinary_opportunities(self, researcher_id: str, top_k: int = 5) -> list[dict]:
        tel = get_telemetry()
        tel.inc("reasoning_calls")
        return find_interdisciplinary_opportunities(self._graph, researcher_id, top_k)

    def citation_paths(self, source_id: str, target_id: str, max_depth: int = 5) -> list[list[str]]:
        tel = get_telemetry()
        tel.inc("reasoning_calls")
        return discover_citation_paths(self._graph, source_id, target_id, max_depth)

    def future_collaborations(self, researcher_id: str, top_k: int = 10) -> list[dict]:
        tel = get_telemetry()
        tel.inc("reasoning_calls")
        return identify_future_collaborations(self._graph, researcher_id, top_k)

    # ── Knowledge discovery ───────────────────────────────────────────────────

    def knowledge_clusters(self) -> list[dict]:
        tel = get_telemetry()
        tel.inc("discovery_calls")
        return [c.to_dict() for c in discover_knowledge_clusters(self._graph)]

    def topic_evolution(self, top_k: int = 10) -> list[dict]:
        tel = get_telemetry()
        tel.inc("discovery_calls")
        return detect_topic_evolution(self._graph, top_k)

    def interdisciplinary_bridges(self, top_k: int = 10) -> list[dict]:
        tel = get_telemetry()
        tel.inc("discovery_calls")
        return find_interdisciplinary_bridges(self._graph, top_k)

    def methodological_trends(self, top_k: int = 10) -> list[dict]:
        tel = get_telemetry()
        tel.inc("discovery_calls")
        return detect_methodological_trends(self._graph, top_k)

    def new_research_areas(self, top_k: int = 10) -> list[dict]:
        tel = get_telemetry()
        tel.inc("discovery_calls")
        return find_new_research_areas(self._graph, top_k)

    def citation_communities(self, top_k: int = 5) -> list[dict]:
        tel = get_telemetry()
        tel.inc("discovery_calls")
        return identify_citation_communities(self._graph, top_k)

    # ── Queries ───────────────────────────────────────────────────────────────

    def query(self, query_dict: dict) -> dict:
        tel = get_telemetry()
        tel.inc("queries")
        return complex_query(self._graph, query_dict).to_dict()

    def query_topic(self, topic: str, scope: str = "all", depth: int = 2) -> dict:
        tel = get_telemetry()
        tel.inc("queries")
        try:
            sc = QueryScope(scope)
        except ValueError:
            sc = QueryScope.ALL
        return query_by_topic(self._graph, topic, scope=sc, max_hops=depth).to_dict()

    def query_path(self, source_id: str, target_id: str) -> dict:
        tel = get_telemetry()
        tel.inc("queries")
        return query_path(self._graph, source_id, target_id).to_dict()

    def search_nodes(self, keyword: str, node_type: str | None = None) -> dict:
        tel = get_telemetry()
        tel.inc("queries")
        return query_type_filter(self._graph, keyword, node_type=node_type).to_dict()

    # ── Visualization ─────────────────────────────────────────────────────────

    def visualize(self, viz_type: str, community_map: dict | None = None,
                  max_nodes: int = 200) -> dict:
        tel = get_telemetry()
        tel.inc("viz_builds")
        if community_map is None and self._comm_cache:
            community_map = self._comm_cache
        return build_visualization(viz_type, self._graph, community_map, max_nodes)

    # ── Copilot integration ───────────────────────────────────────────────────

    def copilot_enrich(
        self,
        query: str,
        researcher_node_id: str | None = None,
    ) -> dict:
        tel = get_telemetry()
        tel.inc("copilot_enrichments")
        return enrich_copilot_context(self._graph, query, researcher_node_id)

    def copilot_recommend(
        self,
        researcher_node_id: str,
        recommendation_type: str = "collaboration",
    ) -> list[dict]:
        tel = get_telemetry()
        tel.inc("copilot_enrichments")
        return graph_enhanced_recommendation(self._graph, researcher_node_id, recommendation_type)

    # ── Admin ─────────────────────────────────────────────────────────────────

    def admin_dashboard(self, top_k: int = 10) -> dict:
        tel = get_telemetry()
        tel.inc("admin_calls")
        return admin_dashboard(self._graph, top_k)

    def admin_reset_graph(self) -> dict:
        self._graph.clear()
        self._invalidate_cache()
        return {"status": "cleared", "message": "Knowledge Graph reset."}


# ── Async singleton ───────────────────────────────────────────────────────────

_engine_instance: KnowledgeGraphEngine | None = None
_engine_lock = asyncio.Lock()


async def get_kg_engine() -> KnowledgeGraphEngine:
    global _engine_instance
    async with _engine_lock:
        if _engine_instance is None:
            _engine_instance = KnowledgeGraphEngine()
    return _engine_instance


def reset_kg_engine() -> None:
    global _engine_instance
    _engine_instance = None
