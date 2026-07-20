"""Academic Knowledge Graph — Visualization Builder (Phase XVII).

Returns serializable dicts for 10 visualization types:
  1. full_overview            — sampled full graph
  2. research_network         — researcher nodes + collab edges
  3. citation_network         — publication nodes + cites edges
  4. institution_network      — institution hierarchy
  5. grant_network            — grants + agencies + researchers
  6. methodology_network      — methods + publications
  7. topic_evolution          — topic nodes + growth trends
  8. research_communities     — community-coloured graph
  9. collaboration_graph      — researcher collaborations only
 10. concept_map              — topics, keywords, concepts + bridges
"""
from __future__ import annotations

from .graph_store import AcademicKnowledgeGraph
from .models import NodeType, RelType, VizType


def _node_d(nid: str, label: str, ntype: str, degree: int = 0, **extra) -> dict:
    return {"id": nid, "label": label[:50], "type": ntype, "degree": degree, **extra}


def _edge_d(source: str, target: str, rel: str, weight: float = 1.0) -> dict:
    return {"source": source, "target": target, "relation": rel, "weight": weight}


def _build_subgraph(
    graph: AcademicKnowledgeGraph,
    node_types: set[str],
    rel_types: set[str] | None = None,
    max_nodes: int = 200,
    max_edges: int = 500,
) -> tuple[list[dict], list[dict]]:
    """Extract nodes and edges matching type filters."""
    nodes: list[dict] = []
    seen_ids: set[str] = set()
    for node in graph.all_nodes():
        if node.node_type.value in node_types:
            nodes.append(_node_d(node.node_id, node.label, node.node_type.value,
                                  graph.degree(node.node_id)))
            seen_ids.add(node.node_id)
            if len(nodes) >= max_nodes:
                break

    edges: list[dict] = []
    for edge in graph.all_edges():
        if edge.source not in seen_ids or edge.target not in seen_ids:
            continue
        if rel_types and edge.rel_type.value not in rel_types:
            continue
        edges.append(_edge_d(edge.source, edge.target, edge.rel_type.value, edge.weight))
        if len(edges) >= max_edges:
            break

    return nodes, edges


# ── 10 visualization functions ────────────────────────────────────────────────

def full_overview_viz(graph: AcademicKnowledgeGraph, max_nodes: int = 200) -> dict:
    nodes = [_node_d(n.node_id, n.label, n.node_type.value, graph.degree(n.node_id))
             for n in graph.all_nodes()[:max_nodes]]
    seen = {n["id"] for n in nodes}
    edges = [_edge_d(e.source, e.target, e.rel_type.value)
             for e in graph.all_edges()
             if e.source in seen and e.target in seen][:500]
    return {"type": VizType.FULL_OVERVIEW.value, "nodes": nodes, "edges": edges,
            "total_nodes": graph.node_count(), "total_edges": graph.edge_count()}


def research_network_viz(graph: AcademicKnowledgeGraph) -> dict:
    researcher_types = {NodeType.RESEARCHER.value, NodeType.STUDENT.value,
                        NodeType.SUPERVISOR.value}
    collab_rels = {RelType.COLLABORATES_WITH.value, RelType.COAUTHORS.value,
                   RelType.SUPERVISES.value}
    nodes, edges = _build_subgraph(graph, researcher_types, collab_rels)
    return {"type": VizType.RESEARCH_NETWORK.value, "nodes": nodes, "edges": edges}


def citation_network_viz(graph: AcademicKnowledgeGraph) -> dict:
    nodes, edges = _build_subgraph(
        graph, {NodeType.PUBLICATION.value}, {RelType.CITES.value}
    )
    return {"type": VizType.CITATION_NETWORK.value, "nodes": nodes, "edges": edges}


def institution_network_viz(graph: AcademicKnowledgeGraph) -> dict:
    inst_types = {NodeType.INSTITUTION.value, NodeType.DEPARTMENT.value,
                  NodeType.RESEARCH_CENTER.value, NodeType.LABORATORY.value,
                  NodeType.COUNTRY.value}
    nodes, edges = _build_subgraph(graph, inst_types, {RelType.BELONGS_TO.value})
    return {"type": VizType.INSTITUTION_NETWORK.value, "nodes": nodes, "edges": edges}


def grant_network_viz(graph: AcademicKnowledgeGraph) -> dict:
    grant_types = {NodeType.GRANT.value, NodeType.FUNDING_AGENCY.value,
                   NodeType.RESEARCHER.value, NodeType.SUPERVISOR.value}
    rels = {RelType.FUNDED_BY.value, RelType.PARTICIPATES_IN.value, RelType.SHARES_GRANT.value}
    nodes, edges = _build_subgraph(graph, grant_types, rels)
    return {"type": VizType.GRANT_NETWORK.value, "nodes": nodes, "edges": edges}


def methodology_network_viz(graph: AcademicKnowledgeGraph) -> dict:
    method_types = {NodeType.METHOD.value, NodeType.STATISTICAL_METHOD.value,
                    NodeType.AI_MODEL.value, NodeType.SOFTWARE.value,
                    NodeType.PUBLICATION.value}
    rels = {RelType.USES_METHOD.value, RelType.IMPLEMENTS.value, RelType.SHARES_METHODOLOGY.value}
    nodes, edges = _build_subgraph(graph, method_types, rels, max_nodes=150)
    return {"type": VizType.METHODOLOGY_NETWORK.value, "nodes": nodes, "edges": edges}


def topic_evolution_viz(graph: AcademicKnowledgeGraph) -> dict:
    topic_types = {NodeType.TOPIC.value, NodeType.KEYWORD.value, NodeType.CONCEPT.value,
                   NodeType.DOMAIN.value}
    nodes = []
    for node in graph.all_nodes():
        if node.node_type.value in topic_types:
            deg  = graph.degree(node.node_id)
            in_d = graph.in_degree(node.node_id)
            nodes.append({
                "id":    node.node_id,
                "label": node.label,
                "type":  node.node_type.value,
                "connections": deg,
                "incoming":    in_d,
                "trend": "rising" if in_d >= 2 else "stable",
            })
    nodes.sort(key=lambda n: -n["connections"])
    return {"type": VizType.TOPIC_EVOLUTION.value, "topics": nodes[:100]}


def research_communities_viz(
    graph: AcademicKnowledgeGraph,
    community_map: dict[str, int] | None = None,
) -> dict:
    if community_map is None:
        from .community_detection import detect_communities
        community_map = detect_communities(graph)

    nodes = []
    for node in graph.all_nodes()[:200]:
        community = community_map.get(node.node_id, -1)
        nodes.append({**_node_d(node.node_id, node.label, node.node_type.value,
                                 graph.degree(node.node_id)),
                       "community": community})

    seen = {n["id"] for n in nodes}
    edges = [_edge_d(e.source, e.target, e.rel_type.value)
             for e in graph.all_edges()
             if e.source in seen and e.target in seen][:400]
    return {"type": VizType.RESEARCH_COMMUNITIES.value, "nodes": nodes, "edges": edges,
            "num_communities": len(set(community_map.values())) if community_map else 0}


def collaboration_graph_viz(graph: AcademicKnowledgeGraph) -> dict:
    researcher_types = {NodeType.RESEARCHER.value, NodeType.STUDENT.value,
                        NodeType.SUPERVISOR.value}
    collab_rels = {RelType.COLLABORATES_WITH.value}
    nodes, edges = _build_subgraph(graph, researcher_types, collab_rels, max_nodes=150)
    return {"type": VizType.COLLABORATION_GRAPH.value, "nodes": nodes, "edges": edges}


def concept_map_viz(graph: AcademicKnowledgeGraph) -> dict:
    concept_types = {NodeType.TOPIC.value, NodeType.KEYWORD.value, NodeType.CONCEPT.value,
                     NodeType.DOMAIN.value, NodeType.RESEARCH_QUESTION.value,
                     NodeType.HYPOTHESIS.value}
    rels = {RelType.SHARES_KEYWORD.value, RelType.SHARES_RESEARCH_INTEREST.value,
            RelType.INFLUENCES.value, RelType.EXTENDS.value, RelType.SUPPORTS.value}
    nodes, edges = _build_subgraph(graph, concept_types, rels, max_nodes=150)
    return {"type": VizType.CONCEPT_MAP.value, "nodes": nodes, "edges": edges}


# ── Dispatch ──────────────────────────────────────────────────────────────────

def build_visualization(
    viz_type: str,
    graph: AcademicKnowledgeGraph,
    community_map: dict[str, int] | None = None,
    max_nodes: int = 200,
) -> dict:
    try:
        vt = VizType(viz_type)
    except ValueError:
        return {"error": f"Unknown visualization type: {viz_type}"}

    if vt == VizType.FULL_OVERVIEW:
        return full_overview_viz(graph, max_nodes)
    if vt == VizType.RESEARCH_NETWORK:
        return research_network_viz(graph)
    if vt == VizType.CITATION_NETWORK:
        return citation_network_viz(graph)
    if vt == VizType.INSTITUTION_NETWORK:
        return institution_network_viz(graph)
    if vt == VizType.GRANT_NETWORK:
        return grant_network_viz(graph)
    if vt == VizType.METHODOLOGY_NETWORK:
        return methodology_network_viz(graph)
    if vt == VizType.TOPIC_EVOLUTION:
        return topic_evolution_viz(graph)
    if vt == VizType.RESEARCH_COMMUNITIES:
        return research_communities_viz(graph, community_map)
    if vt == VizType.COLLABORATION_GRAPH:
        return collaboration_graph_viz(graph)
    if vt == VizType.CONCEPT_MAP:
        return concept_map_viz(graph)
    return {"error": f"Unhandled viz type: {viz_type}"}
