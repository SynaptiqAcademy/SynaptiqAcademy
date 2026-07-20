"""Academic Knowledge Graph — Knowledge Discovery (Phase XVII).

Automatically discovers:
  - Knowledge clusters (topic communities)
  - Topic evolution signals
  - Interdisciplinary bridges
  - Methodological trends
  - New research areas
  - Research schools
  - Citation communities
"""
from __future__ import annotations

from collections import Counter

from .graph_store import AcademicKnowledgeGraph
from .models import KnowledgeCluster, NodeType, RelType


# ── Knowledge clusters ────────────────────────────────────────────────────────

def discover_knowledge_clusters(
    graph: AcademicKnowledgeGraph,
    min_size: int = 2,
) -> list[KnowledgeCluster]:
    """
    Group topic/keyword/concept nodes into thematic clusters using
    shared-neighbor analysis. Two topics are in the same cluster if they
    share ≥ 2 researchers or publications.
    """
    topic_types = {NodeType.TOPIC.value, NodeType.KEYWORD.value,
                   NodeType.CONCEPT.value, NodeType.DOMAIN.value}
    topics = [n for n in graph.all_nodes() if n.node_type.value in topic_types]

    if not topics:
        return []

    # Build adjacency between topics via shared neighbors
    # Two topics share a neighbor if a researcher/publication points to both
    topic_adj: dict[str, set[str]] = {t.node_id: set() for t in topics}
    topic_set = {t.node_id for t in topics}

    for node in graph.all_nodes():
        if node.node_type.value in topic_types:
            continue
        # Find all topic neighbors of this non-topic node
        connected_topics = [nb for nb in graph.neighbors(node.node_id, direction="both")
                            if nb in topic_set]
        for i in range(len(connected_topics)):
            for j in range(i + 1, len(connected_topics)):
                topic_adj[connected_topics[i]].add(connected_topics[j])
                topic_adj[connected_topics[j]].add(connected_topics[i])

    # BFS to find connected components of topics
    visited: set[str] = set()
    raw_clusters: list[list[str]] = []
    for t in topics:
        if t.node_id in visited:
            continue
        component: list[str] = []
        stack = [t.node_id]
        while stack:
            nid = stack.pop()
            if nid in visited:
                continue
            visited.add(nid)
            component.append(nid)
            for nb in topic_adj.get(nid, set()):
                if nb not in visited:
                    stack.append(nb)
        raw_clusters.append(component)

    raw_clusters.sort(key=lambda c: -len(c))

    result: list[KnowledgeCluster] = []
    for idx, cluster_ids in enumerate(raw_clusters):
        if len(cluster_ids) < min_size:
            continue
        labels = [graph.get_node(nid).label for nid in cluster_ids if graph.get_node(nid)]
        # Theme = most connected topic label
        best = max(cluster_ids, key=lambda nid: graph.degree(nid), default=cluster_ids[0])
        best_node = graph.get_node(best)
        coherence = min(len(cluster_ids) / max(len(topics), 1) * 5, 1.0)
        result.append(KnowledgeCluster(
            cluster_id=idx,
            theme=best_node.label if best_node else f"Cluster {idx}",
            node_ids=cluster_ids,
            labels=labels,
            coherence=round(coherence, 3),
            size=len(cluster_ids),
        ))

    return result[:20]


# ── Topic evolution ───────────────────────────────────────────────────────────

def detect_topic_evolution(
    graph: AcademicKnowledgeGraph,
    top_k: int = 10,
) -> list[dict]:
    """
    Detect topics gaining or losing connectivity.
    Proxy: topics with high degree and many researcher connections are "rising".
    Topics with few connections are "declining" or "niche".
    """
    topic_types = {NodeType.TOPIC.value, NodeType.KEYWORD.value,
                   NodeType.CONCEPT.value}
    researcher_types = {NodeType.RESEARCHER.value, NodeType.STUDENT.value,
                        NodeType.SUPERVISOR.value}
    pub_types = {NodeType.PUBLICATION.value}

    results = []
    for node in graph.all_nodes():
        if node.node_type.value not in topic_types:
            continue
        neighbors = graph.neighbors(node.node_id, direction="in")
        researcher_count = sum(1 for nb in neighbors
                                if graph.get_node(nb) and
                                graph.get_node(nb).node_type.value in researcher_types)
        pub_count = sum(1 for nb in neighbors
                        if graph.get_node(nb) and
                        graph.get_node(nb).node_type.value in pub_types)
        total = researcher_count + pub_count
        trend = "rising" if researcher_count >= 2 else ("stable" if pub_count >= 1 else "niche")
        results.append({
            "topic":             node.label,
            "node_id":           node.node_id,
            "researcher_count":  researcher_count,
            "publication_count": pub_count,
            "total_connections": total,
            "trend":             trend,
            "evolution_score":   round(min(total / 10.0, 1.0), 3),
        })

    results.sort(key=lambda r: -r["evolution_score"])
    return results[:top_k]


# ── Interdisciplinary bridges ─────────────────────────────────────────────────

def find_interdisciplinary_bridges(
    graph: AcademicKnowledgeGraph,
    top_k: int = 10,
) -> list[dict]:
    """
    Nodes (researchers, publications, methods) that connect multiple topic clusters.
    High betweenness across topic boundaries = interdisciplinary bridge.
    """
    topic_types = {NodeType.TOPIC.value, NodeType.KEYWORD.value,
                   NodeType.DOMAIN.value, NodeType.CONCEPT.value}
    bridge_candidates = {NodeType.RESEARCHER.value, NodeType.PUBLICATION.value,
                         NodeType.METHOD.value}
    results = []
    for node in graph.all_nodes():
        if node.node_type.value not in bridge_candidates:
            continue
        # Count distinct topic domains reachable
        topic_neighbors: set[str] = set()
        for nb in graph.neighbors(node.node_id, direction="both"):
            nb_node = graph.get_node(nb)
            if nb_node and nb_node.node_type.value in topic_types:
                topic_neighbors.add(nb_node.label)
        if len(topic_neighbors) >= 2:
            bridge_score = round(min(len(topic_neighbors) / 5.0, 1.0), 3)
            results.append({
                "node_id":        node.node_id,
                "label":          node.label,
                "node_type":      node.node_type.value,
                "topic_domains":  list(topic_neighbors)[:10],
                "bridge_score":   bridge_score,
                "reason": f"Connects {len(topic_neighbors)} research domains.",
            })

    results.sort(key=lambda r: -r["bridge_score"])
    return results[:top_k]


# ── Methodological trends ─────────────────────────────────────────────────────

def detect_methodological_trends(
    graph: AcademicKnowledgeGraph,
    top_k: int = 10,
) -> list[dict]:
    """Identify methods gaining adoption (high in-degree growth proxy)."""
    method_types = {NodeType.METHOD.value, NodeType.STATISTICAL_METHOD.value,
                    NodeType.AI_MODEL.value, NodeType.SOFTWARE.value}
    results = []
    for node in graph.all_nodes():
        if node.node_type.value not in method_types:
            continue
        in_deg = graph.in_degree(node.node_id)
        if in_deg == 0:
            continue
        results.append({
            "method":        node.label,
            "node_id":       node.node_id,
            "node_type":     node.node_type.value,
            "usage_count":   in_deg,
            "trend_score":   round(min(in_deg / 10.0, 1.0), 3),
            "trend_label":   "hot" if in_deg >= 5 else "rising" if in_deg >= 2 else "emerging",
        })

    results.sort(key=lambda r: -r["trend_score"])
    return results[:top_k]


# ── New research areas ────────────────────────────────────────────────────────

def find_new_research_areas(
    graph: AcademicKnowledgeGraph,
    top_k: int = 10,
) -> list[dict]:
    """
    Topics that appear in the graph with low historical density but are
    gaining connections (high out-degree relative to in-degree = new + growing).
    """
    topic_types = {NodeType.TOPIC.value, NodeType.KEYWORD.value,
                   NodeType.CONCEPT.value}
    results = []
    for node in graph.all_nodes():
        if node.node_type.value not in topic_types:
            continue
        out_deg = graph.out_degree(node.node_id)
        in_deg  = graph.in_degree(node.node_id)
        total   = out_deg + in_deg
        if total == 0:
            continue
        novelty = out_deg / max(total, 1)  # high if more outgoing (expanding topic)
        score   = round(novelty * min(total / 5.0, 1.0), 3)
        if score > 0:
            results.append({
                "topic":         node.label,
                "node_id":       node.node_id,
                "novelty_score": score,
                "connections":   total,
                "expanding":     out_deg >= in_deg,
            })

    results.sort(key=lambda r: -r["novelty_score"])
    return results[:top_k]


# ── Citation communities ──────────────────────────────────────────────────────

def identify_citation_communities(
    graph: AcademicKnowledgeGraph,
    top_k: int = 5,
) -> list[dict]:
    """
    Clusters of publications that mutually cite each other.
    Uses weakly connected subgraph of publication–cites–publication edges.
    """
    pub_nodes = {n.node_id for n in graph.nodes_by_type(NodeType.PUBLICATION)}
    if not pub_nodes:
        return []

    # Build subgraph adjacency among publications via CITES edges
    adj: dict[str, set[str]] = {nid: set() for nid in pub_nodes}
    for edge in graph.edges_by_rel(RelType.CITES):
        if edge.source in pub_nodes and edge.target in pub_nodes:
            adj[edge.source].add(edge.target)
            adj[edge.target].add(edge.source)

    visited: set[str] = set()
    communities: list[list[str]] = []
    for nid in pub_nodes:
        if nid in visited:
            continue
        comp: list[str] = []
        stack = [nid]
        while stack:
            v = stack.pop()
            if v in visited:
                continue
            visited.add(v)
            comp.append(v)
            for w in adj.get(v, set()):
                if w not in visited:
                    stack.append(w)
        if len(comp) >= 2:
            communities.append(comp)

    communities.sort(key=lambda c: -len(c))
    results = []
    for idx, members in enumerate(communities[:top_k]):
        labels = [graph.get_node(nid).label[:60] for nid in members if graph.get_node(nid)]
        results.append({
            "community_id": idx,
            "size":         len(members),
            "publications": labels[:5],
            "cohesion":     round(min(len(members) / 10.0, 1.0), 3),
        })
    return results
