"""Academic Knowledge Graph — Community Detection (Phase XVII).

Algorithms:
  - Label propagation (async / synchronous variant)
  - Connected components (BFS-based)
  - Community profiling (dominant types, key nodes, cohesion)

Pure Python, deterministic seed for reproducibility.
"""
from __future__ import annotations

from collections import Counter, deque

from .graph_store import AcademicKnowledgeGraph
from .models import NodeType, ResearchCommunity


# ── Label propagation ─────────────────────────────────────────────────────────

def detect_communities(
    graph: AcademicKnowledgeGraph,
    max_iterations: int = 20,
    weight_edges: bool = True,
) -> dict[str, int]:
    """
    Label propagation community detection.
    Returns node_id → community_id (0-indexed integers).

    Each node adopts the label most common among its neighbors.
    Ties broken by lowest label value (deterministic).
    """
    node_ids = graph.all_node_ids()
    if not node_ids:
        return {}

    # Initialize: each node gets its own label (use position index for determinism)
    id_to_idx = {nid: i for i, nid in enumerate(node_ids)}
    labels: dict[str, int] = dict(id_to_idx)

    for _ in range(max_iterations):
        changed = False
        for nid in node_ids:
            neighbors = graph.neighbors(nid, direction="both")
            if not neighbors:
                continue
            if weight_edges:
                neighbor_labels = Counter(labels[nb] for nb in neighbors if nb in labels)
            else:
                neighbor_labels = Counter(labels[nb] for nb in neighbors if nb in labels)
            if not neighbor_labels:
                continue
            max_count = max(neighbor_labels.values())
            # Deterministic tie-break: choose smallest label
            best = min(lbl for lbl, cnt in neighbor_labels.items() if cnt == max_count)
            if labels[nid] != best:
                labels[nid] = best
                changed = True
        if not changed:
            break

    # Re-index community IDs to compact 0-based integers
    unique = sorted(set(labels.values()))
    remap  = {old: new for new, old in enumerate(unique)}
    return {nid: remap[lbl] for nid, lbl in labels.items()}


# ── Connected components ──────────────────────────────────────────────────────

def connected_components(graph: AcademicKnowledgeGraph) -> list[set[str]]:
    """Return list of node sets, each set being a weakly connected component."""
    visited: set[str] = set()
    components: list[set[str]] = []
    for start in graph.all_node_ids():
        if start in visited:
            continue
        component: set[str] = set()
        q = deque([start])
        while q:
            v = q.popleft()
            if v in visited:
                continue
            visited.add(v)
            component.add(v)
            for w in graph.neighbors(v, direction="both"):
                if w not in visited:
                    q.append(w)
        components.append(component)
    components.sort(key=lambda c: -len(c))
    return components


# ── Community profiling ───────────────────────────────────────────────────────

def _cohesion(graph: AcademicKnowledgeGraph, node_ids: list[str]) -> float:
    """Internal edge density within the community."""
    node_set = set(node_ids)
    n = len(node_set)
    if n <= 1:
        return 1.0
    internal = 0
    for nid in node_ids:
        for nb in graph.neighbors(nid, direction="both"):
            if nb in node_set:
                internal += 1
    internal //= 2
    max_edges = n * (n - 1) // 2
    return round(internal / max(max_edges, 1), 4)


def _dominant_topics(graph: AcademicKnowledgeGraph, node_ids: list[str], top_k: int = 5) -> list[str]:
    """Find most common topic/keyword/domain labels in a community."""
    topic_types = {NodeType.TOPIC.value, NodeType.KEYWORD.value,
                   NodeType.DOMAIN.value, NodeType.CONCEPT.value}
    topics: list[str] = []
    for nid in node_ids:
        node = graph.get_node(nid)
        if node and node.node_type.value in topic_types:
            topics.append(node.label)
        # Also check topic neighbors
        for nb in graph.neighbors(nid, direction="out"):
            nb_node = graph.get_node(nb)
            if nb_node and nb_node.node_type.value in topic_types:
                topics.append(nb_node.label)
    most_common = Counter(topics).most_common(top_k)
    return [t for t, _ in most_common]


def _key_nodes(graph: AcademicKnowledgeGraph, node_ids: list[str], top_k: int = 5) -> tuple[list[str], list[str]]:
    """Return (labels, node_ids) of the highest-degree nodes in the community."""
    scored = sorted(node_ids, key=lambda nid: -graph.degree(nid))[:top_k]
    labels = [graph.get_node(nid).label for nid in scored if graph.get_node(nid)]
    return labels, scored


def profile_communities(
    graph: AcademicKnowledgeGraph,
    community_map: dict[str, int],
) -> list[ResearchCommunity]:
    """
    Build ResearchCommunity objects from a node→community_id mapping.
    Only returns communities with ≥ 2 members.
    """
    groups: dict[int, list[str]] = {}
    for nid, cid in community_map.items():
        groups.setdefault(cid, []).append(nid)

    communities: list[ResearchCommunity] = []
    for cid, members in sorted(groups.items(), key=lambda x: -len(x[1])):
        if len(members) < 2:
            continue
        topics            = _dominant_topics(graph, members)
        key_labels, key_nids = _key_nodes(graph, members)
        cohesion          = _cohesion(graph, members)
        communities.append(ResearchCommunity(
            community_id=cid,
            size=len(members),
            dominant_topics=topics,
            key_nodes=key_labels,
            key_node_ids=key_nids,
            cohesion_score=cohesion,
            node_ids=members,
        ))

    return communities
