"""Academic Knowledge Graph — Graph Analytics (Phase XVII).

Pure Python implementations of:
  - Degree / in-degree / out-degree
  - Iterative PageRank (Brin & Page, 1998)
  - Approximate betweenness centrality (BFS sampling)
  - Approximate closeness centrality (BFS-based)
  - Composite knowledge influence score
  - GraphStats summary

All scores normalized to [0, 1].
"""
from __future__ import annotations

import math
from collections import deque

from .graph_store import AcademicKnowledgeGraph
from .models import GraphStats, NodeAnalytics, NodeType


# ── PageRank ──────────────────────────────────────────────────────────────────

def pagerank(
    graph: AcademicKnowledgeGraph,
    damping: float = 0.85,
    iterations: int = 50,
    tolerance: float = 1e-6,
) -> dict[str, float]:
    """Iterative PageRank. Returns node_id → normalized rank."""
    node_ids = graph.all_node_ids()
    N = len(node_ids)
    if N == 0:
        return {}

    ranks: dict[str, float] = {nid: 1.0 / N for nid in node_ids}
    dangling_nodes: set[str] = {nid for nid in node_ids if graph.out_degree(nid) == 0}

    for _ in range(iterations):
        dangling_sum = sum(ranks[nid] for nid in dangling_nodes)
        new_ranks: dict[str, float] = {}
        max_delta = 0.0
        for nid in node_ids:
            in_sum = 0.0
            for eid in graph._in.get(nid, []):
                edge = graph._edges.get(eid)
                if edge:
                    od = graph.out_degree(edge.source)
                    if od > 0:
                        in_sum += ranks[edge.source] / od
            # Dangling contribution distributed uniformly
            r = (1 - damping) / N + damping * (in_sum + dangling_sum / N)
            new_ranks[nid] = r
            max_delta = max(max_delta, abs(r - ranks[nid]))
        ranks = new_ranks
        if max_delta < tolerance:
            break

    return ranks


# ── Centrality ────────────────────────────────────────────────────────────────

def _bfs_distances(graph: AcademicKnowledgeGraph, start: str) -> dict[str, int]:
    """BFS from start; returns {node_id: shortest_path_length}."""
    dist: dict[str, int] = {start: 0}
    q = deque([start])
    while q:
        node = q.popleft()
        d    = dist[node]
        for neighbor in graph.neighbors(node, direction="both"):
            if neighbor not in dist:
                dist[neighbor] = d + 1
                q.append(neighbor)
    return dist


def degree_centrality(graph: AcademicKnowledgeGraph) -> dict[str, float]:
    """Degree centrality normalized by (N-1)."""
    N = graph.node_count()
    if N <= 1:
        return {nid: 0.0 for nid in graph.all_node_ids()}
    return {nid: graph.degree(nid) / (N - 1) for nid in graph.all_node_ids()}


def closeness_centrality(
    graph: AcademicKnowledgeGraph,
    sample_nodes: list[str] | None = None,
) -> dict[str, float]:
    """
    Closeness centrality: 1 / (avg shortest path to all reachable nodes).
    Uses sampled BFS for performance on large graphs.
    """
    node_ids = graph.all_node_ids()
    N = len(node_ids)
    if N <= 1:
        return {nid: 0.0 for nid in node_ids}

    targets = sample_nodes or node_ids
    closeness: dict[str, float] = {}
    for nid in node_ids:
        dist = _bfs_distances(graph, nid)
        reachable_dists = [d for tid, d in dist.items() if tid != nid]
        if not reachable_dists:
            closeness[nid] = 0.0
        else:
            avg = sum(reachable_dists) / len(reachable_dists)
            closeness[nid] = 1.0 / avg if avg > 0 else 0.0

    # Normalize to [0, 1]
    max_c = max(closeness.values()) if closeness else 1.0
    return {nid: v / max(max_c, 1e-9) for nid, v in closeness.items()}


def betweenness_centrality_approx(
    graph: AcademicKnowledgeGraph,
    sample_size: int = 100,
) -> dict[str, float]:
    """
    Approximate betweenness via BFS from sampled source nodes.
    Returns normalized scores in [0, 1].
    """
    node_ids = graph.all_node_ids()
    N = len(node_ids)
    if N <= 2:
        return {nid: 0.0 for nid in node_ids}

    bet: dict[str, float] = {nid: 0.0 for nid in node_ids}
    sources = node_ids[:sample_size]

    for src in sources:
        # BFS to find shortest path counts
        dist:   dict[str, int]       = {src: 0}
        sigma:  dict[str, int]       = {src: 1}
        pred:   dict[str, list[str]] = {src: []}
        q = deque([src])

        while q:
            v = q.popleft()
            for w in graph.neighbors(v, direction="both"):
                if w not in dist:
                    dist[w]  = dist[v] + 1
                    sigma[w] = 0
                    pred[w]  = []
                    q.append(w)
                if dist[w] == dist[v] + 1:
                    sigma[w] = sigma.get(w, 0) + sigma.get(v, 0)
                    pred[w]  = pred.get(w, []) + [v]

        # Back-propagation
        delta: dict[str, float] = {nid: 0.0 for nid in node_ids}
        visited = sorted(dist, key=lambda x: -dist[x])
        for w in visited:
            for v in pred.get(w, []):
                sv = sigma.get(v, 0)
                sw = sigma.get(w, 0)
                if sw > 0:
                    delta[v] += (sv / sw) * (1 + delta.get(w, 0))
            if w != src:
                bet[w] = bet.get(w, 0) + delta.get(w, 0)

    # Normalize
    max_bet = max(bet.values()) if bet else 1.0
    return {nid: v / max(max_bet, 1e-9) for nid, v in bet.items()}


# ── Composite influence ───────────────────────────────────────────────────────

def knowledge_influence_scores(
    graph: AcademicKnowledgeGraph,
    pr: dict[str, float] | None = None,
    bc: dict[str, float] | None = None,
    dc: dict[str, float] | None = None,
) -> dict[str, float]:
    """
    Composite knowledge influence = 0.4*PageRank + 0.3*Betweenness + 0.3*Degree.
    Accepts pre-computed metrics to avoid redundant computation.
    """
    if pr is None:
        pr = pagerank(graph)
    if dc is None:
        dc = degree_centrality(graph)
    if bc is None:
        bc = betweenness_centrality_approx(graph)

    # Normalize PageRank to [0,1]
    max_pr = max(pr.values()) if pr else 1.0
    pr_n   = {nid: v / max(max_pr, 1e-9) for nid, v in pr.items()}

    scores: dict[str, float] = {}
    for nid in graph.all_node_ids():
        scores[nid] = round(
            pr_n.get(nid, 0) * 0.4 +
            bc.get(nid,  0)  * 0.3 +
            dc.get(nid,  0)  * 0.3,
            6,
        )
    return scores


# ── Full analytics per node ───────────────────────────────────────────────────

def compute_node_analytics(
    graph: AcademicKnowledgeGraph,
    pr:   dict[str, float] | None = None,
    bc:   dict[str, float] | None = None,
    cc:   dict[str, float] | None = None,
    dc:   dict[str, float] | None = None,
    influence: dict[str, float] | None = None,
    top_k: int = 50,
) -> list[NodeAnalytics]:
    """
    Compute per-node analytics for the top_k most influential nodes.
    Pass pre-computed metrics to avoid redundant BFS passes.
    """
    if pr is None:
        pr = pagerank(graph)
    if dc is None:
        dc = degree_centrality(graph)
    if bc is None:
        bc = betweenness_centrality_approx(graph)
    if cc is None:
        cc = closeness_centrality(graph)
    if influence is None:
        influence = knowledge_influence_scores(graph, pr, bc, dc)

    max_pr = max(pr.values()) if pr else 1.0

    results: list[NodeAnalytics] = []
    for nid in graph.all_node_ids():
        node = graph.get_node(nid)
        if not node:
            continue
        results.append(NodeAnalytics(
            node_id=nid,
            label=node.label,
            node_type=node.node_type.value,
            degree=graph.degree(nid),
            in_degree=graph.in_degree(nid),
            out_degree=graph.out_degree(nid),
            pagerank=round(pr.get(nid, 0) / max(max_pr, 1e-9), 6),
            betweenness=round(bc.get(nid, 0), 6),
            closeness=round(cc.get(nid, 0), 6),
            centrality_score=round(influence.get(nid, 0), 6),
        ))

    results.sort(key=lambda x: -x.centrality_score)
    return results[:top_k]


# ── GraphStats summary ────────────────────────────────────────────────────────

def compute_graph_stats(graph: AcademicKnowledgeGraph) -> GraphStats:
    """Compute summary statistics for the graph."""
    N = graph.node_count()
    E = graph.edge_count()

    density = (2 * E) / max(N * (N - 1), 1)
    degrees = [graph.degree(nid) for nid in graph.all_node_ids()]
    avg_deg = sum(degrees) / max(N, 1)
    max_deg = max(degrees) if degrees else 0

    # Node type distribution
    type_counts: dict[str, int] = {}
    for nt in NodeType:
        cnt = len(graph._type_idx.get(nt.value, set()))
        if cnt:
            type_counts[nt.value] = cnt

    # Edge type distribution
    from .models import RelType
    edge_counts: dict[str, int] = {}
    for rt in RelType:
        cnt = len(graph._rel_idx.get(rt.value, []))
        if cnt:
            edge_counts[rt.value] = cnt

    # Connected components (undirected BFS)
    visited: set[str] = set()
    components: list[int] = []
    for start in graph.all_node_ids():
        if start not in visited:
            comp_size = 0
            q = deque([start])
            while q:
                v = q.popleft()
                if v in visited:
                    continue
                visited.add(v)
                comp_size += 1
                for w in graph.neighbors(v, direction="both"):
                    if w not in visited:
                        q.append(w)
            components.append(comp_size)

    return GraphStats(
        total_nodes=N,
        total_edges=E,
        density=round(density, 6),
        avg_degree=round(avg_deg, 2),
        max_degree=max_deg,
        node_type_counts=type_counts,
        edge_type_counts=edge_counts,
        connected_components=len(components),
        largest_component_size=max(components) if components else 0,
    )
