"""Research Collaboration Intelligence — Research Network Analyzer (Phase XIV).

Pure-Python graph analysis: degree centrality, community detection,
bridge identification, and network metrics. No external graph library required.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from .models import (
    NetworkEdge, NetworkNode, NetworkNodeType, ResearcherProfile, ResearchNetwork,
)
from .matching_engine import match_researchers


def _degree_centrality(adj: dict[str, set[str]]) -> dict[str, float]:
    n = len(adj)
    if n <= 1:
        return {k: 0.0 for k in adj}
    return {node: len(neighbors) / (n - 1) for node, neighbors in adj.items()}


def _label_propagation(adj: dict[str, set[str]], iterations: int = 10) -> dict[str, str]:
    """Fast community detection via label propagation."""
    labels = {node: node for node in adj}
    for _ in range(iterations):
        changed = False
        for node in list(adj.keys()):
            nbrs = adj[node]
            if not nbrs:
                continue
            # Count neighbour labels
            label_freq: dict[str, int] = defaultdict(int)
            for nbr in nbrs:
                label_freq[labels[nbr]] += 1
            best = max(label_freq, key=lambda l: (label_freq[l], l))
            if best != labels[node]:
                labels[node] = best
                changed = True
        if not changed:
            break
    return labels


def _graph_density(adj: dict[str, set[str]]) -> float:
    n = len(adj)
    if n <= 1:
        return 0.0
    edges = sum(len(nbrs) for nbrs in adj.values()) // 2
    max_edges = n * (n - 1) // 2
    return round(edges / max_edges, 4) if max_edges else 0.0


def _bfs_diameter(adj: dict[str, set[str]], sample_size: int = 10) -> int:
    """Estimate diameter via BFS from a sample of nodes."""
    nodes = list(adj.keys())[:sample_size]
    max_dist = 0
    for start in nodes:
        visited = {start: 0}
        queue = [start]
        while queue:
            curr = queue.pop(0)
            for nbr in adj[curr]:
                if nbr not in visited:
                    visited[nbr] = visited[curr] + 1
                    queue.append(nbr)
        if visited:
            max_dist = max(max_dist, max(visited.values()))
    return max_dist


def _bridge_nodes(adj: dict[str, set[str]], centrality: dict[str, float]) -> list[str]:
    """Nodes connecting two otherwise disconnected communities."""
    bridges: list[str] = []
    for node, nbrs in adj.items():
        # A bridge node has neighbours from distinct clusters/components
        if len(nbrs) >= 2:
            community_set = set()
            for nbr in nbrs:
                community_set.add(nbr)
            # Heuristic: bridge if it has high centrality AND connects different groups
            if centrality.get(node, 0) > 0.3 and len(nbrs) >= 3:
                bridges.append(node)
    return sorted(bridges, key=lambda n: -centrality.get(n, 0))[:5]


def build_network(
    profiles: list[ResearcherProfile],
    similarity_threshold: float = 0.35,
) -> ResearchNetwork:
    """Build a research collaboration network from researcher profiles."""
    if not profiles:
        return ResearchNetwork()

    # Build adjacency list based on similarity threshold
    adj: dict[str, set[str]] = {p.user_id: set() for p in profiles}
    edges: list[NetworkEdge] = []

    profile_map = {p.user_id: p for p in profiles}

    for i, pa in enumerate(profiles):
        for pb in profiles[i + 1:]:
            m = match_researchers(pa, pb)
            if m.overall_score >= similarity_threshold:
                adj[pa.user_id].add(pb.user_id)
                adj[pb.user_id].add(pa.user_id)
                edges.append(NetworkEdge(
                    from_id=pa.user_id,
                    to_id=pb.user_id,
                    weight=m.overall_score,
                    edge_type=m.collab_type.value,
                ))

    centrality = _degree_centrality(adj)
    labels     = _label_propagation(adj)

    # Identify isolated nodes
    isolated = [n for n, nbrs in adj.items() if not nbrs]

    # Build cluster metadata
    cluster_groups: dict[str, list[str]] = defaultdict(list)
    for node, label in labels.items():
        cluster_groups[label].append(node)
    clusters = [
        {
            "cluster_id": cid,
            "members": members,
            "size": len(members),
        }
        for cid, members in cluster_groups.items()
        if len(members) >= 2
    ]

    # Build nodes
    nodes: list[NetworkNode] = []
    for p in profiles:
        nodes.append(NetworkNode(
            node_id=p.user_id,
            node_type=NetworkNodeType.RESEARCHER,
            label=p.name or p.user_id,
            centrality=round(centrality.get(p.user_id, 0.0), 4),
            cluster_id=labels.get(p.user_id, p.user_id),
            connections=len(adj.get(p.user_id, set())),
            metadata={
                "institution": p.institution,
                "country": p.country,
                "h_index": p.h_index,
                "domains": p.domains[:3],
            },
        ))

    most_central = sorted(
        centrality.keys(),
        key=lambda n: -centrality[n],
    )[:5]

    bridges = _bridge_nodes(adj, centrality)
    density = _graph_density(adj)
    diameter = _bfs_diameter(adj)

    return ResearchNetwork(
        nodes=nodes,
        edges=edges,
        clusters=clusters,
        density=density,
        diameter_estimate=diameter,
        most_central=most_central,
        isolated_nodes=isolated,
        bridge_nodes=bridges,
    )


def analyze_researcher_position(
    source: ResearcherProfile,
    network: ResearchNetwork,
) -> dict:
    """Summarise a researcher's position within the network."""
    node = next((n for n in network.nodes if n.node_id == source.user_id), None)
    if not node:
        return {"message": "Researcher not in network"}

    edge_count = node.connections
    all_edges  = len(network.edges)
    cluster_size = next(
        (c["size"] for c in network.clusters if source.user_id in c["members"]), 1
    )

    return {
        "centrality":      node.centrality,
        "connections":     edge_count,
        "cluster_id":      node.cluster_id,
        "cluster_size":    cluster_size,
        "is_bridge":       source.user_id in network.bridge_nodes,
        "is_isolated":     source.user_id in network.isolated_nodes,
        "is_central":      source.user_id in network.most_central,
        "network_density": network.density,
    }
