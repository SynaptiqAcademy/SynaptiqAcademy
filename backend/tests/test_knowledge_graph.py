"""Test suite for Phase XVII — Academic Knowledge Graph Intelligence Engine.

Run: python -m pytest backend/tests/test_knowledge_graph.py -v
"""
import asyncio
import sys
import os
import pytest

# Ensure backend is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_simple_graph():
    """Return a small, well-connected graph for testing."""
    from services.knowledge_graph.graph_store import create_graph
    from services.knowledge_graph.models import NodeType, RelType

    g = create_graph()
    r1 = g.get_or_create_node(NodeType.RESEARCHER, "Alice")
    r2 = g.get_or_create_node(NodeType.RESEARCHER, "Bob")
    r3 = g.get_or_create_node(NodeType.RESEARCHER, "Carol")

    inst = g.get_or_create_node(NodeType.INSTITUTION, "MIT")
    dept = g.get_or_create_node(NodeType.DEPARTMENT, "CS Dept")

    t1 = g.get_or_create_node(NodeType.TOPIC, "Machine Learning")
    t2 = g.get_or_create_node(NodeType.TOPIC, "NLP")
    t3 = g.get_or_create_node(NodeType.KEYWORD, "deep learning")

    pub1 = g.get_or_create_node(NodeType.PUBLICATION, "Attention Is All You Need")
    pub2 = g.get_or_create_node(NodeType.PUBLICATION, "BERT: Pre-training of Transformers")
    m1   = g.get_or_create_node(NodeType.METHOD, "Transformer")
    grant1 = g.get_or_create_node(NodeType.GRANT, "NSF Grant 2024")
    agency = g.get_or_create_node(NodeType.FUNDING_AGENCY, "NSF")

    # Relationships
    g.add_edge(r1.node_id, r2.node_id, RelType.COLLABORATES_WITH)
    g.add_edge(r1.node_id, inst.node_id, RelType.BELONGS_TO)
    g.add_edge(r2.node_id, inst.node_id, RelType.BELONGS_TO)
    g.add_edge(r3.node_id, dept.node_id, RelType.BELONGS_TO)
    g.add_edge(r1.node_id, t1.node_id, RelType.SHARES_RESEARCH_INTEREST)
    g.add_edge(r2.node_id, t1.node_id, RelType.SHARES_RESEARCH_INTEREST)
    g.add_edge(r3.node_id, t2.node_id, RelType.SHARES_RESEARCH_INTEREST)
    g.add_edge(t1.node_id, t3.node_id, RelType.SHARES_KEYWORD)
    g.add_edge(r1.node_id, pub1.node_id, RelType.WRITES)
    g.add_edge(r2.node_id, pub2.node_id, RelType.WRITES)
    g.add_edge(pub2.node_id, pub1.node_id, RelType.CITES)
    g.add_edge(pub1.node_id, m1.node_id, RelType.USES_METHOD)
    g.add_edge(pub2.node_id, m1.node_id, RelType.USES_METHOD)
    g.add_edge(r1.node_id, grant1.node_id, RelType.PARTICIPATES_IN)
    g.add_edge(grant1.node_id, agency.node_id, RelType.FUNDED_BY)

    return g, {
        "r1": r1.node_id, "r2": r2.node_id, "r3": r3.node_id,
        "inst": inst.node_id, "dept": dept.node_id,
        "t1": t1.node_id, "t2": t2.node_id, "t3": t3.node_id,
        "pub1": pub1.node_id, "pub2": pub2.node_id,
        "m1": m1.node_id, "grant1": grant1.node_id, "agency": agency.node_id,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Models
# ═══════════════════════════════════════════════════════════════════════════════

class TestModels:
    def test_node_type_count(self):
        from services.knowledge_graph.models import NodeType
        assert len(NodeType) == 35

    def test_rel_type_count(self):
        from services.knowledge_graph.models import RelType
        assert len(RelType) == 26

    def test_viz_type_count(self):
        from services.knowledge_graph.models import VizType
        assert len(VizType) == 10

    def test_query_scope_count(self):
        from services.knowledge_graph.models import QueryScope
        assert len(QueryScope) == 7

    def test_node_to_dict(self):
        from services.knowledge_graph.models import Node, NodeType
        n = Node(node_id="n1", node_type=NodeType.RESEARCHER, label="Alice")
        d = n.to_dict()
        assert d["node_id"] == "n1"
        assert d["node_type"] == "researcher"
        assert d["label"] == "Alice"

    def test_edge_to_dict(self):
        from services.knowledge_graph.models import Edge, RelType
        e = Edge(edge_id="e1", source="n1", target="n2", rel_type=RelType.COLLABORATES_WITH)
        d = e.to_dict()
        assert d["rel_type"] == "collaborates_with"

    def test_graph_stats_to_dict(self):
        from services.knowledge_graph.models import GraphStats
        gs = GraphStats(total_nodes=5, total_edges=3, density=0.3)
        d = gs.to_dict()
        assert d["total_nodes"] == 5
        assert d["density"] == 0.3

    def test_hidden_collaborator_to_dict(self):
        from services.knowledge_graph.models import HiddenCollaborator
        hc = HiddenCollaborator(node_id="n1", label="Bob", node_type="researcher",
                                 score=0.75, reason="test")
        d = hc.to_dict()
        assert d["score"] == 0.75
        assert d["label"] == "Bob"

    def test_emerging_topic_to_dict(self):
        from services.knowledge_graph.models import EmergingTopic
        et = EmergingTopic(topic="ML", score=0.9, growth_rate=0.5)
        d = et.to_dict()
        assert d["topic"] == "ML"
        assert d["score"] == 0.9

    def test_knowledge_cluster_to_dict(self):
        from services.knowledge_graph.models import KnowledgeCluster
        kc = KnowledgeCluster(cluster_id=0, theme="AI", labels=["ML", "DL"], size=2)
        d = kc.to_dict()
        assert d["cluster_id"] == 0
        assert d["theme"] == "AI"

    def test_kg_query_result_to_dict(self):
        from services.knowledge_graph.models import KGQueryResult
        r = KGQueryResult(query="ML", scope="all", nodes=[{"id": "n1"}], total=1)
        d = r.to_dict()
        assert d["total"] == 1
        assert d["query"] == "ML"

    def test_graph_embedding_to_dict(self):
        from services.knowledge_graph.models import GraphEmbedding
        ge = GraphEmbedding(node_id="n1", vector=[0.1, 0.2], embedding_dim=2)
        d = ge.to_dict()
        assert len(d["vector"]) == 2

    def test_node_type_string_values(self):
        from services.knowledge_graph.models import NodeType
        assert NodeType.RESEARCHER.value == "researcher"
        assert NodeType.AI_MODEL.value == "ai_model"

    def test_rel_type_string_values(self):
        from services.knowledge_graph.models import RelType
        assert RelType.COLLABORATES_WITH.value == "collaborates_with"
        assert RelType.IMPLEMENTS.value == "implements"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Graph Store
# ═══════════════════════════════════════════════════════════════════════════════

class TestGraphStore:
    def test_empty_graph(self):
        from services.knowledge_graph.graph_store import create_graph
        g = create_graph()
        assert g.node_count() == 0
        assert g.edge_count() == 0

    def test_add_node(self):
        from services.knowledge_graph.graph_store import create_graph
        from services.knowledge_graph.models import NodeType
        g = create_graph()
        node = g.get_or_create_node(NodeType.RESEARCHER, "Alice")
        assert node.label == "Alice"
        assert g.node_count() == 1

    def test_get_or_create_idempotent(self):
        from services.knowledge_graph.graph_store import create_graph
        from services.knowledge_graph.models import NodeType
        g = create_graph()
        n1 = g.get_or_create_node(NodeType.RESEARCHER, "Alice")
        n2 = g.get_or_create_node(NodeType.RESEARCHER, "Alice")
        assert n1.node_id == n2.node_id
        assert g.node_count() == 1

    def test_add_edge(self):
        from services.knowledge_graph.graph_store import create_graph
        from services.knowledge_graph.models import NodeType, RelType
        g = create_graph()
        r1 = g.get_or_create_node(NodeType.RESEARCHER, "Alice")
        r2 = g.get_or_create_node(NodeType.RESEARCHER, "Bob")
        e = g.add_edge(r1.node_id, r2.node_id, RelType.COLLABORATES_WITH)
        assert e is not None
        assert g.edge_count() == 1

    def test_edge_deduplication(self):
        from services.knowledge_graph.graph_store import create_graph
        from services.knowledge_graph.models import NodeType, RelType
        g = create_graph()
        r1 = g.get_or_create_node(NodeType.RESEARCHER, "Alice")
        r2 = g.get_or_create_node(NodeType.RESEARCHER, "Bob")
        g.add_edge(r1.node_id, r2.node_id, RelType.COLLABORATES_WITH)
        g.add_edge(r1.node_id, r2.node_id, RelType.COLLABORATES_WITH)
        assert g.edge_count() == 1

    def test_degree(self):
        g, ids = make_simple_graph()
        deg = g.degree(ids["r1"])
        assert deg >= 2  # Alice collaborates + belongs_to + shares_interest + etc.

    def test_in_out_degree(self):
        from services.knowledge_graph.graph_store import create_graph
        from services.knowledge_graph.models import NodeType, RelType
        g = create_graph()
        r1 = g.get_or_create_node(NodeType.RESEARCHER, "Alice")
        r2 = g.get_or_create_node(NodeType.RESEARCHER, "Bob")
        g.add_edge(r1.node_id, r2.node_id, RelType.COLLABORATES_WITH)
        assert g.out_degree(r1.node_id) == 1
        assert g.in_degree(r2.node_id) == 1
        assert g.in_degree(r1.node_id) == 0

    def test_neighbors(self):
        g, ids = make_simple_graph()
        nbs = g.neighbors(ids["r1"], direction="out")
        assert len(nbs) > 0

    def test_nodes_by_type(self):
        g, _ = make_simple_graph()
        from services.knowledge_graph.models import NodeType
        researchers = list(g.nodes_by_type(NodeType.RESEARCHER))
        assert len(researchers) == 3

    def test_remove_node(self):
        from services.knowledge_graph.graph_store import create_graph
        from services.knowledge_graph.models import NodeType
        g = create_graph()
        n = g.get_or_create_node(NodeType.RESEARCHER, "Alice")
        g.remove_node(n.node_id)
        assert g.node_count() == 0

    def test_clear(self):
        g, _ = make_simple_graph()
        g.clear()
        assert g.node_count() == 0
        assert g.edge_count() == 0

    def test_find_node(self):
        from services.knowledge_graph.graph_store import create_graph
        from services.knowledge_graph.models import NodeType
        g = create_graph()
        g.get_or_create_node(NodeType.RESEARCHER, "Alice")
        found = g.find_node(NodeType.RESEARCHER, "Alice")
        assert found is not None
        assert found.label == "Alice"

    def test_all_edges(self):
        g, _ = make_simple_graph()
        edges = list(g.all_edges())
        assert len(edges) > 5

    def test_edges_by_rel(self):
        g, _ = make_simple_graph()
        from services.knowledge_graph.models import RelType
        cites = list(g.edges_by_rel(RelType.CITES))
        assert len(cites) >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Graph Builder
# ═══════════════════════════════════════════════════════════════════════════════

class TestGraphBuilder:
    def test_add_researcher(self):
        from services.knowledge_graph.graph_store import create_graph
        from services.knowledge_graph.graph_builder import add_researcher
        from services.knowledge_graph.models import NodeType
        g = create_graph()
        user = {
            "_id": "u1",
            "name": "Alice",
            "institution": "MIT",
            "department": "CS",
            "expertise_areas": ["Machine Learning"],
        }
        nid = add_researcher(g, user)
        assert nid is not None
        node = g.get_node(nid)
        assert node.node_type == NodeType.RESEARCHER

    def test_add_publication(self):
        from services.knowledge_graph.graph_store import create_graph
        from services.knowledge_graph.graph_builder import add_researcher, add_publication
        from services.knowledge_graph.models import NodeType
        g = create_graph()
        user = {"_id": "u1", "name": "Alice"}
        rid = add_researcher(g, user)
        pub = {
            "_id": "p1",
            "title": "Test Paper",
            "journal": "Nature",
            "keywords": ["AI", "ML"],
            "methods": ["deep learning"],
            "references": [],
        }
        pid = add_publication(g, pub, [rid])
        node = g.get_node(pid)
        assert node.node_type == NodeType.PUBLICATION

    def test_add_grant(self):
        from services.knowledge_graph.graph_store import create_graph
        from services.knowledge_graph.graph_builder import add_researcher, add_grant
        from services.knowledge_graph.models import NodeType
        g = create_graph()
        user = {"_id": "u1", "name": "Alice"}
        rid = add_researcher(g, user)
        grant = {"_id": "g1", "title": "NSF Award", "funding_agency": "NSF",
                  "amount": 100000}
        gid = add_grant(g, grant, [rid])
        node = g.get_node(gid)
        assert node.node_type == NodeType.GRANT

    def test_import_platform_data(self):
        from services.knowledge_graph.graph_store import create_graph
        from services.knowledge_graph.graph_builder import import_platform_data
        g = create_graph()
        data = {
            "researchers": [{"_id": "u1", "name": "Alice"},
                            {"_id": "u2", "name": "Bob"}],
            "publications": [{"_id": "p1", "title": "Test Paper", "keywords": []}],
        }
        result = import_platform_data(g, data)
        assert result["nodes_added"] >= 2

    def test_import_empty_data(self):
        from services.knowledge_graph.graph_store import create_graph
        from services.knowledge_graph.graph_builder import import_platform_data
        g = create_graph()
        result = import_platform_data(g, {})
        assert result["nodes_added"] == 0


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Graph Analytics
# ═══════════════════════════════════════════════════════════════════════════════

class TestGraphAnalytics:
    def test_pagerank_sums_to_1(self):
        from services.knowledge_graph.graph_analytics import pagerank
        g, _ = make_simple_graph()
        pr = pagerank(g)
        total = sum(pr.values())
        assert abs(total - 1.0) < 0.01

    def test_pagerank_non_negative(self):
        from services.knowledge_graph.graph_analytics import pagerank
        g, _ = make_simple_graph()
        pr = pagerank(g)
        assert all(v >= 0 for v in pr.values())

    def test_degree_centrality(self):
        from services.knowledge_graph.graph_analytics import degree_centrality
        g, ids = make_simple_graph()
        dc = degree_centrality(g)
        assert ids["r1"] in dc
        assert 0.0 <= dc[ids["r1"]] <= 1.0

    def test_closeness_centrality(self):
        from services.knowledge_graph.graph_analytics import closeness_centrality
        g, _ = make_simple_graph()
        cc = closeness_centrality(g)
        assert all(0.0 <= v <= 1.0 for v in cc.values())

    def test_betweenness_centrality(self):
        from services.knowledge_graph.graph_analytics import betweenness_centrality_approx
        g, _ = make_simple_graph()
        bc = betweenness_centrality_approx(g, sample_size=5)
        assert all(v >= 0 for v in bc.values())

    def test_compute_graph_stats(self):
        from services.knowledge_graph.graph_analytics import compute_graph_stats
        g, _ = make_simple_graph()
        stats = compute_graph_stats(g)
        assert stats.total_nodes > 0
        assert stats.total_edges > 0
        assert stats.density >= 0

    def test_graph_stats_connected_components(self):
        from services.knowledge_graph.graph_analytics import compute_graph_stats
        from services.knowledge_graph.graph_store import create_graph
        from services.knowledge_graph.models import NodeType
        g = create_graph()
        g.get_or_create_node(NodeType.RESEARCHER, "Isolated A")
        g.get_or_create_node(NodeType.RESEARCHER, "Isolated B")
        stats = compute_graph_stats(g)
        assert stats.connected_components == 2

    def test_compute_node_analytics(self):
        from services.knowledge_graph.graph_analytics import (
            compute_node_analytics, pagerank, degree_centrality,
            betweenness_centrality_approx,
        )
        g, _ = make_simple_graph()
        pr = pagerank(g)
        dc = degree_centrality(g)
        bc = betweenness_centrality_approx(g, sample_size=5)
        results = compute_node_analytics(g, pr=pr, bc=bc, dc=dc, top_k=5)
        assert len(results) <= 5
        for r in results:
            assert r.centrality_score >= 0

    def test_knowledge_influence_scores(self):
        from services.knowledge_graph.graph_analytics import (
            knowledge_influence_scores, pagerank, degree_centrality,
            betweenness_centrality_approx,
        )
        g, _ = make_simple_graph()
        pr = pagerank(g)
        dc = degree_centrality(g)
        bc = betweenness_centrality_approx(g, sample_size=5)
        scores = knowledge_influence_scores(g, pr, bc, dc)
        assert all(v >= 0 for v in scores.values())

    def test_empty_graph_pagerank(self):
        from services.knowledge_graph.graph_analytics import pagerank
        from services.knowledge_graph.graph_store import create_graph
        g = create_graph()
        pr = pagerank(g)
        assert pr == {}

    def test_single_node_pagerank(self):
        from services.knowledge_graph.graph_analytics import pagerank
        from services.knowledge_graph.graph_store import create_graph
        from services.knowledge_graph.models import NodeType
        g = create_graph()
        n = g.get_or_create_node(NodeType.RESEARCHER, "Solo")
        pr = pagerank(g)
        assert abs(pr[n.node_id] - 1.0) < 0.01


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Community Detection
# ═══════════════════════════════════════════════════════════════════════════════

class TestCommunityDetection:
    def test_detect_communities_returns_dict(self):
        from services.knowledge_graph.community_detection import detect_communities
        g, _ = make_simple_graph()
        cm = detect_communities(g)
        assert isinstance(cm, dict)
        assert len(cm) == g.node_count()

    def test_community_ids_are_ints(self):
        from services.knowledge_graph.community_detection import detect_communities
        g, _ = make_simple_graph()
        cm = detect_communities(g)
        for v in cm.values():
            assert isinstance(v, int)

    def test_connected_nodes_same_community(self):
        from services.knowledge_graph.community_detection import detect_communities
        from services.knowledge_graph.graph_store import create_graph
        from services.knowledge_graph.models import NodeType, RelType
        g = create_graph()
        r1 = g.get_or_create_node(NodeType.RESEARCHER, "A")
        r2 = g.get_or_create_node(NodeType.RESEARCHER, "B")
        r3 = g.get_or_create_node(NodeType.RESEARCHER, "C")  # isolated
        g.add_edge(r1.node_id, r2.node_id, RelType.COLLABORATES_WITH)
        cm = detect_communities(g)
        # A and B should share a community; C should be different
        assert cm[r1.node_id] == cm[r2.node_id]
        assert cm[r3.node_id] != cm[r1.node_id]

    def test_connected_components(self):
        from services.knowledge_graph.community_detection import connected_components
        g, _ = make_simple_graph()
        comps = connected_components(g)
        assert len(comps) >= 1

    def test_profile_communities(self):
        from services.knowledge_graph.community_detection import detect_communities, profile_communities
        g, _ = make_simple_graph()
        cm = detect_communities(g)
        comms = profile_communities(g, cm)
        assert isinstance(comms, list)

    def test_empty_graph_communities(self):
        from services.knowledge_graph.community_detection import detect_communities
        from services.knowledge_graph.graph_store import create_graph
        g = create_graph()
        assert detect_communities(g) == {}


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Embedding Engine
# ═══════════════════════════════════════════════════════════════════════════════

class TestEmbeddingEngine:
    def test_embed_node_returns_embedding(self):
        from services.knowledge_graph.embedding_engine import embed_node
        g, ids = make_simple_graph()
        emb = embed_node(g, ids["r1"])
        assert emb is not None
        assert len(emb.vector) == 16

    def test_embed_node_unit_length(self):
        import math
        from services.knowledge_graph.embedding_engine import embed_node
        g, ids = make_simple_graph()
        emb = embed_node(g, ids["r1"])
        norm = math.sqrt(sum(v ** 2 for v in emb.vector))
        assert abs(norm - 1.0) < 0.01

    def test_embed_nonexistent_node(self):
        from services.knowledge_graph.embedding_engine import embed_node
        g, _ = make_simple_graph()
        assert embed_node(g, "nonexistent_id") is None

    def test_embed_all(self):
        from services.knowledge_graph.embedding_engine import embed_all
        g, _ = make_simple_graph()
        embs = embed_all(g)
        assert len(embs) == g.node_count()

    def test_similar_nodes(self):
        from services.knowledge_graph.embedding_engine import similar_nodes
        g, ids = make_simple_graph()
        results = similar_nodes(g, ids["r1"], top_k=3)
        assert isinstance(results, list)
        assert len(results) <= 3

    def test_similar_nodes_have_scores(self):
        from services.knowledge_graph.embedding_engine import similar_nodes
        g, ids = make_simple_graph()
        results = similar_nodes(g, ids["r1"], top_k=5)
        for r in results:
            assert "similarity" in r
            assert -1.0 <= r["similarity"] <= 1.0

    def test_embed_node_type_filter(self):
        from services.knowledge_graph.embedding_engine import embed_all
        from services.knowledge_graph.models import NodeType
        g, _ = make_simple_graph()
        embs = embed_all(g, node_type_filter=NodeType.RESEARCHER)
        for nid, emb in embs.items():
            node = g.get_node(nid)
            assert node.node_type == NodeType.RESEARCHER


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Semantic Reasoner
# ═══════════════════════════════════════════════════════════════════════════════

class TestSemanticReasoner:
    def test_hidden_collaborators_returns_list(self):
        from services.knowledge_graph.semantic_reasoner import find_hidden_collaborators
        g, ids = make_simple_graph()
        results = find_hidden_collaborators(g, ids["r1"])
        assert isinstance(results, list)

    def test_hidden_collaborators_excludes_direct(self):
        from services.knowledge_graph.semantic_reasoner import find_hidden_collaborators
        from services.knowledge_graph.models import RelType
        g, ids = make_simple_graph()
        direct = set(g.neighbors(ids["r1"], rel_type=RelType.COLLABORATES_WITH.value))
        results = find_hidden_collaborators(g, ids["r1"])
        found_ids = {r.node_id for r in results}
        assert not (found_ids & direct)

    def test_hidden_collaborators_not_self(self):
        from services.knowledge_graph.semantic_reasoner import find_hidden_collaborators
        g, ids = make_simple_graph()
        results = find_hidden_collaborators(g, ids["r1"])
        assert ids["r1"] not in {r.node_id for r in results}

    def test_emerging_topics_returns_list(self):
        from services.knowledge_graph.semantic_reasoner import find_emerging_topics
        g, _ = make_simple_graph()
        results = find_emerging_topics(g)
        assert isinstance(results, list)

    def test_isolated_researchers(self):
        from services.knowledge_graph.semantic_reasoner import detect_isolated_researchers
        from services.knowledge_graph.graph_store import create_graph
        from services.knowledge_graph.models import NodeType
        g = create_graph()
        g.get_or_create_node(NodeType.RESEARCHER, "Isolated")
        results = detect_isolated_researchers(g)
        assert len(results) >= 1

    def test_influential_methods(self):
        from services.knowledge_graph.semantic_reasoner import find_influential_methods
        g, _ = make_simple_graph()
        results = find_influential_methods(g, top_k=5)
        assert isinstance(results, list)
        for r in results:
            assert "influence_score" in r

    def test_foundational_publications(self):
        from services.knowledge_graph.semantic_reasoner import find_foundational_publications
        g, _ = make_simple_graph()
        results = find_foundational_publications(g, top_k=5)
        assert isinstance(results, list)

    def test_foundational_pub_has_citations(self):
        from services.knowledge_graph.semantic_reasoner import find_foundational_publications
        g, _ = make_simple_graph()
        results = find_foundational_publications(g, top_k=5)
        for r in results:
            assert r["citations_in_graph"] >= 1

    def test_interdisciplinary_opportunities(self):
        from services.knowledge_graph.semantic_reasoner import find_interdisciplinary_opportunities
        g, ids = make_simple_graph()
        results = find_interdisciplinary_opportunities(g, ids["r3"])
        assert isinstance(results, list)

    def test_citation_paths_same_node(self):
        from services.knowledge_graph.semantic_reasoner import discover_citation_paths
        g, ids = make_simple_graph()
        paths = discover_citation_paths(g, ids["pub1"], ids["pub1"])
        assert paths == [[ids["pub1"]]]

    def test_citation_paths_direct(self):
        from services.knowledge_graph.semantic_reasoner import discover_citation_paths
        g, ids = make_simple_graph()
        # pub2 cites pub1
        paths = discover_citation_paths(g, ids["pub2"], ids["pub1"])
        assert len(paths) >= 1
        assert ids["pub1"] in paths[0]

    def test_citation_paths_no_path(self):
        from services.knowledge_graph.semantic_reasoner import discover_citation_paths
        g, ids = make_simple_graph()
        # pub1 does NOT cite pub2
        paths = discover_citation_paths(g, ids["pub1"], ids["pub2"])
        assert paths == []

    def test_future_collaborations(self):
        from services.knowledge_graph.semantic_reasoner import identify_future_collaborations
        g, ids = make_simple_graph()
        results = identify_future_collaborations(g, ids["r1"])
        assert isinstance(results, list)

    def test_hidden_collaborator_score_range(self):
        from services.knowledge_graph.semantic_reasoner import find_hidden_collaborators
        g, ids = make_simple_graph()
        results = find_hidden_collaborators(g, ids["r1"])
        for r in results:
            assert r.score >= 0.0

    def test_empty_graph_hidden_collabs(self):
        from services.knowledge_graph.semantic_reasoner import find_hidden_collaborators
        from services.knowledge_graph.graph_store import create_graph
        g = create_graph()
        assert find_hidden_collaborators(g, "nonexistent") == []


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Knowledge Discovery
# ═══════════════════════════════════════════════════════════════════════════════

class TestKnowledgeDiscovery:
    def test_discover_clusters_returns_list(self):
        from services.knowledge_graph.knowledge_discovery import discover_knowledge_clusters
        g, _ = make_simple_graph()
        results = discover_knowledge_clusters(g)
        assert isinstance(results, list)

    def test_cluster_has_theme(self):
        from services.knowledge_graph.knowledge_discovery import discover_knowledge_clusters
        g, _ = make_simple_graph()
        results = discover_knowledge_clusters(g)
        for c in results:
            assert "theme" in c.to_dict()
            assert c.size >= 2

    def test_topic_evolution(self):
        from services.knowledge_graph.knowledge_discovery import detect_topic_evolution
        g, _ = make_simple_graph()
        results = detect_topic_evolution(g, top_k=5)
        assert isinstance(results, list)

    def test_topic_evolution_has_trend(self):
        from services.knowledge_graph.knowledge_discovery import detect_topic_evolution
        g, _ = make_simple_graph()
        results = detect_topic_evolution(g)
        for r in results:
            assert "trend" in r
            assert r["trend"] in ("rising", "stable", "niche")

    def test_interdisciplinary_bridges(self):
        from services.knowledge_graph.knowledge_discovery import find_interdisciplinary_bridges
        g, _ = make_simple_graph()
        results = find_interdisciplinary_bridges(g)
        assert isinstance(results, list)

    def test_methodological_trends(self):
        from services.knowledge_graph.knowledge_discovery import detect_methodological_trends
        g, _ = make_simple_graph()
        results = detect_methodological_trends(g)
        assert isinstance(results, list)
        for r in results:
            assert "trend_label" in r

    def test_new_research_areas(self):
        from services.knowledge_graph.knowledge_discovery import find_new_research_areas
        g, _ = make_simple_graph()
        results = find_new_research_areas(g)
        assert isinstance(results, list)

    def test_citation_communities(self):
        from services.knowledge_graph.knowledge_discovery import identify_citation_communities
        g, _ = make_simple_graph()
        results = identify_citation_communities(g)
        assert isinstance(results, list)

    def test_empty_graph_no_clusters(self):
        from services.knowledge_graph.knowledge_discovery import discover_knowledge_clusters
        from services.knowledge_graph.graph_store import create_graph
        g = create_graph()
        assert discover_knowledge_clusters(g) == []


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Graph Query Engine
# ═══════════════════════════════════════════════════════════════════════════════

class TestGraphQuery:
    def test_query_by_topic_found(self):
        from services.knowledge_graph.graph_query import query_by_topic
        g, _ = make_simple_graph()
        result = query_by_topic(g, "Machine Learning")
        assert result.total > 0

    def test_query_by_topic_not_found(self):
        from services.knowledge_graph.graph_query import query_by_topic
        g, _ = make_simple_graph()
        result = query_by_topic(g, "quantum_graviton_xyz_12345")
        assert result.total == 0

    def test_query_connected(self):
        from services.knowledge_graph.graph_query import query_connected
        g, ids = make_simple_graph()
        result = query_connected(g, ids["r1"], depth=1)
        assert result.total > 0

    def test_query_path_direct(self):
        from services.knowledge_graph.graph_query import query_path
        g, ids = make_simple_graph()
        # pub2 cites pub1 → direct path
        result = query_path(g, ids["pub2"], ids["pub1"])
        assert result.total >= 1

    def test_query_path_no_connection(self):
        from services.knowledge_graph.graph_query import query_path
        from services.knowledge_graph.graph_store import create_graph
        from services.knowledge_graph.models import NodeType
        # Two completely isolated publication nodes — no path possible
        g2 = create_graph()
        p1 = g2.get_or_create_node(NodeType.PUBLICATION, "Paper Alpha")
        p2 = g2.get_or_create_node(NodeType.PUBLICATION, "Paper Beta")
        result = query_path(g2, p1.node_id, p2.node_id)
        assert result.total == 0

    def test_query_type_filter(self):
        from services.knowledge_graph.graph_query import query_type_filter
        g, _ = make_simple_graph()
        result = query_type_filter(g, "Alice")
        assert result.total == 1
        assert result.nodes[0]["label"] == "Alice"

    def test_complex_query_topic(self):
        from services.knowledge_graph.graph_query import complex_query
        g, _ = make_simple_graph()
        result = complex_query(g, {"topic": "Machine Learning"})
        assert isinstance(result.to_dict(), dict)

    def test_complex_query_path(self):
        from services.knowledge_graph.graph_query import complex_query
        g, ids = make_simple_graph()
        result = complex_query(g, {"source_id": ids["pub2"], "target_id": ids["pub1"]})
        assert isinstance(result.to_dict(), dict)

    def test_complex_query_empty(self):
        from services.knowledge_graph.graph_query import complex_query
        g, _ = make_simple_graph()
        result = complex_query(g, {})
        assert result.total == 0

    def test_query_by_topic_reasoning_filled(self):
        from services.knowledge_graph.graph_query import query_by_topic
        g, _ = make_simple_graph()
        result = query_by_topic(g, "Machine Learning")
        assert result.reasoning != ""


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Visualization Builder
# ═══════════════════════════════════════════════════════════════════════════════

class TestVisualizationBuilder:
    def _build(self, viz_type):
        from services.knowledge_graph.visualization_builder import build_visualization
        g, _ = make_simple_graph()
        return build_visualization(viz_type, g)

    def test_full_overview(self):
        result = self._build("full_overview")
        assert "nodes" in result
        assert "edges" in result
        assert result["type"] == "full_overview"

    def test_research_network(self):
        result = self._build("research_network")
        assert result["type"] == "research_network"
        assert "nodes" in result

    def test_citation_network(self):
        result = self._build("citation_network")
        assert result["type"] == "citation_network"

    def test_institution_network(self):
        result = self._build("institution_network")
        assert result["type"] == "institution_network"

    def test_grant_network(self):
        result = self._build("grant_network")
        assert result["type"] == "grant_network"

    def test_methodology_network(self):
        result = self._build("methodology_network")
        assert result["type"] == "methodology_network"

    def test_topic_evolution(self):
        result = self._build("topic_evolution")
        assert result["type"] == "topic_evolution"
        assert "topics" in result

    def test_research_communities(self):
        result = self._build("research_communities")
        assert result["type"] == "research_communities"
        assert "num_communities" in result

    def test_collaboration_graph(self):
        result = self._build("collaboration_graph")
        assert result["type"] == "collaboration_graph"

    def test_concept_map(self):
        result = self._build("concept_map")
        assert result["type"] == "concept_map"

    def test_invalid_viz_type(self):
        from services.knowledge_graph.visualization_builder import build_visualization
        g, _ = make_simple_graph()
        result = build_visualization("nonexistent_type", g)
        assert "error" in result


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Copilot Integration
# ═══════════════════════════════════════════════════════════════════════════════

class TestCopilotIntegration:
    def test_enrich_empty_graph(self):
        from services.knowledge_graph.copilot_integration import enrich_copilot_context
        from services.knowledge_graph.graph_store import create_graph
        g = create_graph()
        result = enrich_copilot_context(g, "machine learning")
        assert "copilot_context_text" in result
        assert result["graph_available"] is False

    def test_enrich_populated_graph(self):
        from services.knowledge_graph.copilot_integration import enrich_copilot_context
        g, _ = make_simple_graph()
        result = enrich_copilot_context(g, "Machine Learning")
        assert result["graph_available"] is True
        assert "copilot_context_text" in result

    def test_enrich_with_researcher(self):
        from services.knowledge_graph.copilot_integration import enrich_copilot_context
        g, ids = make_simple_graph()
        result = enrich_copilot_context(g, "NLP", researcher_node_id=ids["r1"])
        assert isinstance(result, dict)

    def test_graph_enhanced_recommendation_collab(self):
        from services.knowledge_graph.copilot_integration import graph_enhanced_recommendation
        g, ids = make_simple_graph()
        results = graph_enhanced_recommendation(g, ids["r1"], "collaboration")
        assert isinstance(results, list)

    def test_graph_enhanced_recommendation_topic(self):
        from services.knowledge_graph.copilot_integration import graph_enhanced_recommendation
        g, ids = make_simple_graph()
        results = graph_enhanced_recommendation(g, ids["r1"], "topic")
        assert isinstance(results, list)

    def test_graph_enhanced_recommendation_unknown(self):
        from services.knowledge_graph.copilot_integration import graph_enhanced_recommendation
        g, ids = make_simple_graph()
        results = graph_enhanced_recommendation(g, ids["r1"], "unknown_type")
        assert results == []

    def test_graph_enhanced_recommendation_bad_id(self):
        from services.knowledge_graph.copilot_integration import graph_enhanced_recommendation
        g, _ = make_simple_graph()
        results = graph_enhanced_recommendation(g, "nonexistent_id")
        assert results == []


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Telemetry
# ═══════════════════════════════════════════════════════════════════════════════

class TestTelemetry:
    def _fresh_telemetry(self):
        from services.knowledge_graph import telemetry as tel_mod
        # Reset singleton for isolation
        tel_mod.KGTelemetry._instance = None
        return tel_mod.get_telemetry()

    def test_initial_counters_zero(self):
        tel = self._fresh_telemetry()
        d = tel.to_dict()
        assert d["nodes_added"] == 0
        assert d["queries"] == 0

    def test_inc(self):
        tel = self._fresh_telemetry()
        tel.inc("queries", 3)
        assert tel.to_dict()["queries"] == 3

    def test_record_latency(self):
        tel = self._fresh_telemetry()
        tel.record_latency(0.05)
        d = tel.to_dict()
        assert d["avg_latency_seconds"] == 0.05

    def test_latency_cap(self):
        tel = self._fresh_telemetry()
        for i in range(600):
            tel.record_latency(0.01)
        assert len(tel.latencies) <= 500

    def test_singleton(self):
        from services.knowledge_graph.telemetry import get_telemetry
        t1 = get_telemetry()
        t2 = get_telemetry()
        assert t1 is t2

    def test_error_counter(self):
        tel = self._fresh_telemetry()
        tel.inc("errors")
        assert tel.to_dict()["errors"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# 13. Admin Analytics
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdminAnalytics:
    def test_dashboard_keys(self):
        from services.knowledge_graph.admin_analytics import admin_dashboard
        g, _ = make_simple_graph()
        result = admin_dashboard(g)
        assert "graph_stats" in result
        assert "top_researchers" in result
        assert "top_institutions" in result
        assert "fastest_growing_topics" in result

    def test_dashboard_health_field(self):
        from services.knowledge_graph.admin_analytics import admin_dashboard
        g, _ = make_simple_graph()
        result = admin_dashboard(g)
        assert result["graph_health"] in ("excellent", "good", "sparse")

    def test_dashboard_summary(self):
        from services.knowledge_graph.admin_analytics import admin_dashboard
        g, _ = make_simple_graph()
        result = admin_dashboard(g)
        summary = result["summary"]
        assert summary["total_nodes"] == g.node_count()
        assert summary["total_edges"] == g.edge_count()

    def test_empty_graph_dashboard(self):
        from services.knowledge_graph.admin_analytics import admin_dashboard
        from services.knowledge_graph.graph_store import create_graph
        g = create_graph()
        result = admin_dashboard(g)
        assert result["summary"]["total_nodes"] == 0


# ═══════════════════════════════════════════════════════════════════════════════
# 14. Engine Integration
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineIntegration:
    def _get_engine(self):
        from services.knowledge_graph.engine import KnowledgeGraphEngine
        return KnowledgeGraphEngine()

    def test_engine_starts_empty(self):
        engine = self._get_engine()
        stats = engine.graph_stats()
        assert stats["total_nodes"] == 0

    def test_engine_add_node(self):
        engine = self._get_engine()
        result = engine.add_node("researcher", "Alice")
        assert result["label"] == "Alice"
        assert engine.graph_stats()["total_nodes"] == 1

    def test_engine_add_edge(self):
        engine = self._get_engine()
        r1 = engine.add_node("researcher", "Alice")
        r2 = engine.add_node("researcher", "Bob")
        e = engine.add_edge(r1["node_id"], r2["node_id"], "collaborates_with")
        assert "edge_id" in e

    def test_engine_import(self):
        engine = self._get_engine()
        data = {"researchers": [{"_id": "u1", "name": "Alice"}]}
        result = engine.import_data(data)
        assert result["nodes_added"] >= 1

    def test_engine_pagerank(self):
        engine = self._get_engine()
        engine.import_data({"researchers": [{"_id": "u1", "name": "Alice"},
                                             {"_id": "u2", "name": "Bob"}]})
        pr = engine.run_pagerank()
        assert abs(sum(pr.values()) - 1.0) < 0.01

    def test_engine_communities(self):
        engine = self._get_engine()
        engine.add_node("researcher", "Alice")
        result = engine.detect_communities()
        assert "communities" in result

    def test_engine_embed_node(self):
        engine = self._get_engine()
        node = engine.add_node("researcher", "Alice")
        emb = engine.embed_node(node["node_id"])
        assert "vector" in emb

    def test_engine_hidden_collaborators(self):
        engine = self._get_engine()
        g, ids = make_simple_graph()
        # Inject the graph into engine
        engine._graph = g
        results = engine.hidden_collaborators(ids["r1"])
        assert isinstance(results, list)

    def test_engine_emerging_topics(self):
        engine = self._get_engine()
        engine._graph, _ = make_simple_graph()
        results = engine.emerging_topics()
        assert isinstance(results, list)

    def test_engine_knowledge_clusters(self):
        engine = self._get_engine()
        engine._graph, _ = make_simple_graph()
        results = engine.knowledge_clusters()
        assert isinstance(results, list)

    def test_engine_visualize(self):
        engine = self._get_engine()
        engine._graph, _ = make_simple_graph()
        result = engine.visualize("full_overview")
        assert "nodes" in result

    def test_engine_admin_dashboard(self):
        engine = self._get_engine()
        engine._graph, _ = make_simple_graph()
        result = engine.admin_dashboard()
        assert "graph_health" in result

    def test_engine_reset_graph(self):
        engine = self._get_engine()
        engine.add_node("researcher", "Alice")
        engine.admin_reset_graph()
        assert engine.graph_stats()["total_nodes"] == 0

    def test_engine_search_nodes(self):
        engine = self._get_engine()
        engine._graph, _ = make_simple_graph()
        result = engine.search_nodes("Alice")
        assert result["total"] >= 1


# ═══════════════════════════════════════════════════════════════════════════════
# 15. Async Singleton
# ═══════════════════════════════════════════════════════════════════════════════

class TestAsyncSingleton:
    def test_singleton_returns_same_instance(self):
        from services.knowledge_graph.engine import get_kg_engine, reset_kg_engine
        reset_kg_engine()

        async def _run():
            e1 = await get_kg_engine()
            e2 = await get_kg_engine()
            return e1 is e2

        result = asyncio.run(_run())
        assert result is True

    def test_reset_clears_singleton(self):
        from services.knowledge_graph.engine import get_kg_engine, reset_kg_engine
        reset_kg_engine()

        async def _run():
            e1 = await get_kg_engine()
            reset_kg_engine()
            e2 = await get_kg_engine()
            return e1 is not e2

        result = asyncio.run(_run())
        assert result is True


# ═══════════════════════════════════════════════════════════════════════════════
# 16. Plans Catalogue Credit Keys
# ═══════════════════════════════════════════════════════════════════════════════

class TestPlansCatalogueKG:
    def test_kg_credit_keys_present(self):
        from plans_catalogue import CREDIT_COSTS
        kg_keys = [
            "kg_import", "kg_add_node", "kg_add_edge", "kg_stats",
            "kg_analytics", "kg_communities", "kg_embeddings",
            "kg_reasoning", "kg_discovery", "kg_query",
            "kg_visualization", "kg_copilot",
        ]
        for key in kg_keys:
            assert key in CREDIT_COSTS, f"Missing credit key: {key}"

    def test_kg_credit_values_positive(self):
        from plans_catalogue import CREDIT_COSTS, get_credit_cost
        assert get_credit_cost("kg_import") > 0
        assert get_credit_cost("kg_reasoning") > 0
        assert get_credit_cost("kg_copilot") > 0


if __name__ == "__main__":
    import subprocess
    subprocess.run(["python", "-m", "pytest", __file__, "-v"])
