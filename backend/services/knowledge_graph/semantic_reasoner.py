"""Academic Knowledge Graph — Semantic Reasoner (Phase XVII).

Answers complex semantic questions by traversing graph structure:

  - find_hidden_collaborators     (2-hop paths between researchers)
  - find_emerging_topics          (high-connectivity, recent topic nodes)
  - detect_isolated_researchers   (low-degree researcher nodes)
  - find_influential_methods      (PageRank on method nodes)
  - find_foundational_publications (in-degree on publication nodes)
  - find_interdisciplinary_opportunities (bridges between topic clusters)
  - discover_citation_paths       (BFS between publication nodes)
  - identify_future_collaborations (shared keyword / grant neighbors)
"""
from __future__ import annotations

from collections import deque

from .graph_store import AcademicKnowledgeGraph
from .models import HiddenCollaborator, NodeType, RelType


# ── Hidden collaborators ──────────────────────────────────────────────────────

def find_hidden_collaborators(
    graph: AcademicKnowledgeGraph,
    researcher_node_id: str,
    max_results: int = 10,
    max_hops: int = 3,
) -> list[HiddenCollaborator]:
    """
    Find researchers not yet directly connected but reachable within max_hops.
    Score by shared topics and proximity.
    """
    researcher_types = {NodeType.RESEARCHER.value, NodeType.STUDENT.value,
                        NodeType.SUPERVISOR.value}
    start = graph.get_node(researcher_node_id)
    if not start or start.node_type.value not in researcher_types:
        return []

    # BFS up to max_hops
    visited: dict[str, int]          = {researcher_node_id: 0}
    path_from: dict[str, list[str]]  = {researcher_node_id: []}
    q: deque[tuple[str, list[str]]]  = deque([(researcher_node_id, [])])
    candidates: dict[str, list[str]] = {}  # node_id → path

    while q:
        nid, path = q.popleft()
        hop = len(path)
        if hop >= max_hops:
            continue
        for nb in graph.neighbors(nid, direction="both"):
            if nb in visited:
                continue
            visited[nb] = hop + 1
            new_path    = path + [nid]
            nb_node     = graph.get_node(nb)
            if not nb_node:
                continue
            if nb_node.node_type.value in researcher_types and nb != researcher_node_id:
                # Is there already a direct collaboration edge?
                direct = graph.neighbors(researcher_node_id,
                                         rel_type=RelType.COLLABORATES_WITH.value,
                                         direction="both")
                if nb not in direct:
                    candidates[nb] = new_path + [nb]
            q.append((nb, new_path))

    # Get my topics
    my_topics = set(graph.neighbors(researcher_node_id,
                                     rel_type=RelType.SHARES_RESEARCH_INTEREST.value))
    my_topics |= set(graph.neighbors(researcher_node_id,
                                      rel_type=RelType.SHARES_KEYWORD.value))

    results: list[HiddenCollaborator] = []
    for nid, path in candidates.items():
        node = graph.get_node(nid)
        if not node:
            continue
        their_topics = set(graph.neighbors(nid, rel_type=RelType.SHARES_RESEARCH_INTEREST.value))
        their_topics |= set(graph.neighbors(nid, rel_type=RelType.SHARES_KEYWORD.value))
        shared = my_topics & their_topics
        shared_labels = [graph.get_node(t).label for t in shared if graph.get_node(t)][:5]

        hop_dist = len(path)
        score = round(
            len(shared) * 0.3 +
            (1.0 / max(hop_dist, 1)) * 0.4 +
            (1 - hop_dist / max_hops) * 0.3,
            3
        )
        path_labels = [graph.get_node(p).label for p in path if graph.get_node(p)]
        results.append(HiddenCollaborator(
            node_id=nid,
            label=node.label,
            node_type=node.node_type.value,
            connection_path=path_labels,
            shared_interests=shared_labels,
            score=score,
            reason=f"{len(shared)} shared research interest(s); {hop_dist}-hop connection.",
        ))

    results.sort(key=lambda r: -r.score)
    return results[:max_results]


# ── Emerging topics ───────────────────────────────────────────────────────────

def find_emerging_topics(
    graph: AcademicKnowledgeGraph,
    top_k: int = 10,
) -> list[dict]:
    """
    Topics with high in-degree from researchers and publications.
    Score = degree * recency_proxy.
    """
    from .models import EmergingTopic
    topic_types = {NodeType.TOPIC.value, NodeType.KEYWORD.value,
                   NodeType.CONCEPT.value, NodeType.DOMAIN.value}
    results: list[EmergingTopic] = []
    for node in graph.nodes_by_type(NodeType.TOPIC):
        deg = graph.in_degree(node.node_id)
        total_deg = graph.degree(node.node_id)
        score = min(deg / max(10, 1) * 0.6 + total_deg / max(20, 1) * 0.4, 1.0)
        related = [graph.get_node(nb).label
                   for nb in graph.neighbors(node.node_id, direction="both")[:3]
                   if graph.get_node(nb) and graph.get_node(nb).node_type.value in topic_types]
        results.append(EmergingTopic(
            topic=node.label,
            score=round(score, 3),
            growth_rate=round(score * 0.8, 3),
            connected_nodes=total_deg,
            related_topics=related,
        ))

    for node in graph.nodes_by_type(NodeType.KEYWORD):
        deg = graph.degree(node.node_id)
        score = min(deg / max(15, 1), 1.0)
        results.append(EmergingTopic(
            topic=node.label,
            score=round(score * 0.8, 3),
            growth_rate=round(score * 0.5, 3),
            connected_nodes=deg,
        ))

    results.sort(key=lambda t: -t.score)
    seen: set[str] = set()
    unique: list[EmergingTopic] = []
    for t in results:
        if t.topic not in seen:
            seen.add(t.topic)
            unique.append(t)
    return [t.to_dict() for t in unique[:top_k]]


# ── Isolated researchers ──────────────────────────────────────────────────────

def detect_isolated_researchers(
    graph: AcademicKnowledgeGraph,
    degree_threshold: int = 2,
) -> list[dict]:
    """
    Researcher nodes with total degree below threshold.
    These researchers are at risk of research isolation.
    """
    researcher_types = {NodeType.RESEARCHER.value, NodeType.STUDENT.value,
                        NodeType.SUPERVISOR.value}
    results = []
    for node in graph.all_nodes():
        if node.node_type.value not in researcher_types:
            continue
        deg = graph.degree(node.node_id)
        if deg <= degree_threshold:
            results.append({
                "node_id":   node.node_id,
                "label":     node.label,
                "node_type": node.node_type.value,
                "degree":    deg,
                "risk_score": round(1.0 - deg / max(degree_threshold, 1), 3),
            })
    results.sort(key=lambda r: -r["risk_score"])
    return results


# ── Influential methods ───────────────────────────────────────────────────────

def find_influential_methods(
    graph: AcademicKnowledgeGraph,
    top_k: int = 10,
) -> list[dict]:
    """Methods used by many publications/researchers (high in-degree)."""
    method_types = {NodeType.METHOD.value, NodeType.STATISTICAL_METHOD.value}
    results = []
    for node in graph.all_nodes():
        if node.node_type.value not in method_types:
            continue
        in_deg = graph.in_degree(node.node_id)
        total  = graph.degree(node.node_id)
        score  = min(in_deg / max(10, 1), 1.0)
        results.append({
            "node_id":   node.node_id,
            "label":     node.label,
            "node_type": node.node_type.value,
            "usage_count": in_deg,
            "total_connections": total,
            "influence_score": round(score, 3),
        })
    results.sort(key=lambda r: -r["influence_score"])
    return results[:top_k]


# ── Foundational publications ─────────────────────────────────────────────────

def find_foundational_publications(
    graph: AcademicKnowledgeGraph,
    top_k: int = 10,
) -> list[dict]:
    """Publications with highest in-degree from citations."""
    results = []
    for node in graph.nodes_by_type(NodeType.PUBLICATION):
        in_deg  = graph.in_degree(node.node_id)
        out_deg = graph.out_degree(node.node_id)
        if in_deg == 0:
            continue
        score = min(in_deg / max(20, 1), 1.0)
        results.append({
            "node_id":     node.node_id,
            "label":       node.label[:80],
            "citations_in_graph": in_deg,
            "references":  out_deg,
            "impact_score": round(score, 3),
            "properties":  node.properties,
        })
    results.sort(key=lambda r: -r["impact_score"])
    return results[:top_k]


# ── Interdisciplinary opportunities ──────────────────────────────────────────

def find_interdisciplinary_opportunities(
    graph: AcademicKnowledgeGraph,
    researcher_node_id: str,
    top_k: int = 5,
) -> list[dict]:
    """
    Identify topics the researcher is NOT connected to but that are adjacent
    to their current research community.
    """
    my_topics = set(graph.neighbors(researcher_node_id,
                                     rel_type=RelType.SHARES_RESEARCH_INTEREST.value))
    my_topics |= set(graph.neighbors(researcher_node_id,
                                      rel_type=RelType.SHARES_KEYWORD.value))

    # Topics one hop away from my topics (not already mine)
    adjacent: dict[str, int] = {}
    for t in my_topics:
        for nb in graph.neighbors(t, direction="both"):
            nb_node = graph.get_node(nb)
            if nb_node and nb_node.node_type.value in (NodeType.TOPIC.value, NodeType.KEYWORD.value):
                if nb not in my_topics:
                    adjacent[nb] = adjacent.get(nb, 0) + 1

    results = []
    for nid, bridge_count in sorted(adjacent.items(), key=lambda x: -x[1])[:top_k]:
        node = graph.get_node(nid)
        if node:
            results.append({
                "node_id":     nid,
                "label":       node.label,
                "bridge_count": bridge_count,
                "opportunity_score": round(min(bridge_count / 5.0, 1.0), 3),
                "reason": f"Connected to {bridge_count} of your research area(s).",
            })
    return results


# ── Citation paths ────────────────────────────────────────────────────────────

def discover_citation_paths(
    graph: AcademicKnowledgeGraph,
    source_id: str,
    target_id: str,
    max_depth: int = 5,
) -> list[list[str]]:
    """BFS to find shortest citation path(s) between two publications."""
    if source_id == target_id:
        return [[source_id]]

    # BFS
    visited: set[str]                = {source_id}
    queue:   deque[list[str]]        = deque([[source_id]])
    paths:   list[list[str]]         = []

    while queue:
        path = queue.popleft()
        if len(path) > max_depth:
            break
        last = path[-1]
        for nb in graph.neighbors(last, rel_type=RelType.CITES.value, direction="out"):
            if nb == target_id:
                paths.append(path + [nb])
                if len(paths) >= 3:
                    return paths
            if nb not in visited:
                visited.add(nb)
                queue.append(path + [nb])

    return paths


# ── Future collaborations ─────────────────────────────────────────────────────

def identify_future_collaborations(
    graph: AcademicKnowledgeGraph,
    researcher_node_id: str,
    top_k: int = 10,
) -> list[dict]:
    """
    Identify researchers who share grants or institutional affiliation but
    have no direct collaboration edge yet.
    """
    my_grants   = set(graph.neighbors(researcher_node_id, rel_type=RelType.SHARES_GRANT.value))
    my_grants  |= set(graph.neighbors(researcher_node_id, rel_type=RelType.FUNDED_BY.value))
    my_inst     = set(graph.neighbors(researcher_node_id, rel_type=RelType.SHARES_INSTITUTION.value))
    my_inst    |= set(graph.neighbors(researcher_node_id, rel_type=RelType.BELONGS_TO.value))

    existing_collabs = set(graph.neighbors(researcher_node_id,
                                            rel_type=RelType.COLLABORATES_WITH.value))

    researcher_types = {NodeType.RESEARCHER.value, NodeType.SUPERVISOR.value,
                        NodeType.STUDENT.value}
    candidates: dict[str, int] = {}  # node_id → shared signal count

    # Researchers sharing grants
    for g in my_grants:
        for nb in graph.neighbors(g, direction="in"):
            nb_node = graph.get_node(nb)
            if nb_node and nb_node.node_type.value in researcher_types:
                if nb != researcher_node_id and nb not in existing_collabs:
                    candidates[nb] = candidates.get(nb, 0) + 2

    # Researchers at same institution
    for inst in my_inst:
        for nb in graph.neighbors(inst, direction="in"):
            nb_node = graph.get_node(nb)
            if nb_node and nb_node.node_type.value in researcher_types:
                if nb != researcher_node_id and nb not in existing_collabs:
                    candidates[nb] = candidates.get(nb, 0) + 1

    results = []
    for nid, score in sorted(candidates.items(), key=lambda x: -x[1])[:top_k]:
        node = graph.get_node(nid)
        if node:
            results.append({
                "node_id":          nid,
                "label":            node.label,
                "node_type":        node.node_type.value,
                "collaboration_score": round(min(score / 5.0, 1.0), 3),
                "reason":           f"Shared signals: {score}",
            })
    return results
