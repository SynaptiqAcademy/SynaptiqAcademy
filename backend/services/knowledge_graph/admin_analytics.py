"""Academic Knowledge Graph — Admin Dashboard Analytics (Phase XVII)."""
from __future__ import annotations

from .graph_analytics import compute_graph_stats, pagerank
from .graph_store import AcademicKnowledgeGraph
from .models import NodeType


def admin_dashboard(graph: AcademicKnowledgeGraph, top_k: int = 10) -> dict:
    """Build the complete admin dashboard payload."""
    stats = compute_graph_stats(graph)

    # Most influential researchers
    pr = pagerank(graph)
    max_pr = max(pr.values()) if pr else 1.0

    researcher_types = {NodeType.RESEARCHER.value, NodeType.SUPERVISOR.value}
    researchers = []
    for node in graph.nodes_by_type(NodeType.RESEARCHER):
        researchers.append({
            "node_id":   node.node_id,
            "label":     node.label,
            "influence": round(pr.get(node.node_id, 0) / max(max_pr, 1e-9), 4),
            "degree":    graph.degree(node.node_id),
        })
    researchers.sort(key=lambda r: -r["influence"])

    # Most influential institutions
    institutions = []
    for node in graph.nodes_by_type(NodeType.INSTITUTION):
        institutions.append({
            "node_id":   node.node_id,
            "label":     node.label,
            "influence": round(pr.get(node.node_id, 0) / max(max_pr, 1e-9), 4),
            "degree":    graph.degree(node.node_id),
        })
    institutions.sort(key=lambda r: -r["influence"])

    # Fastest growing topics (by degree)
    topics = []
    for node in graph.nodes_by_type(NodeType.TOPIC):
        deg = graph.degree(node.node_id)
        topics.append({
            "node_id": node.node_id,
            "label":   node.label,
            "degree":  deg,
            "growth":  round(min(deg / 10.0, 1.0), 3),
        })
    topics.sort(key=lambda t: -t["degree"])

    # Emerging research fields (keywords with recent growth)
    from .knowledge_discovery import find_new_research_areas
    emerging = find_new_research_areas(graph, top_k=top_k)

    # Graph health indicators
    density   = stats.density
    health    = "excellent" if density > 0.1 else "good" if density > 0.01 else "sparse"

    return {
        "graph_stats":            stats.to_dict(),
        "graph_health":           health,
        "top_researchers":        researchers[:top_k],
        "top_institutions":       institutions[:top_k],
        "fastest_growing_topics": topics[:top_k],
        "emerging_fields":        emerging[:top_k],
        "node_type_distribution": stats.node_type_counts,
        "edge_type_distribution": stats.edge_type_counts,
        "summary": {
            "total_nodes":       stats.total_nodes,
            "total_edges":       stats.total_edges,
            "communities":       stats.connected_components,
            "largest_community": stats.largest_component_size,
        },
    }
