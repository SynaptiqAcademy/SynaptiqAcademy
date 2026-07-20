"""Research Collaboration Intelligence — Academic Social Graph Builder (Phase XIV).

Builds a multi-entity graph connecting researchers, institutions, topics,
methods, projects, and grants from profile and network data.
"""
from __future__ import annotations

from .models import (
    NetworkEdge, NetworkNode, NetworkNodeType, ResearcherProfile, ResearchNetwork,
)


def build_social_graph(
    profiles: list[ResearcherProfile],
    include_topic_nodes: bool = True,
    include_method_nodes: bool = True,
    include_institution_nodes: bool = True,
) -> ResearchNetwork:
    """Build a full academic social graph from researcher profiles."""
    nodes: list[NetworkNode]  = []
    edges: list[NetworkEdge]  = []
    seen_nodes: set[str] = set()

    def _add_node(node_id: str, ntype: NetworkNodeType, label: str, meta: dict | None = None) -> None:
        if node_id not in seen_nodes:
            nodes.append(NetworkNode(
                node_id=node_id, node_type=ntype, label=label,
                metadata=meta or {}, cluster_id=ntype.value,
            ))
            seen_nodes.add(node_id)

    def _add_edge(from_id: str, to_id: str, weight: float = 1.0, etype: str = "connects") -> None:
        edges.append(NetworkEdge(from_id=from_id, to_id=to_id, weight=weight, edge_type=etype))

    # ── Researcher nodes ──────────────────────────────────────────────────────
    for p in profiles:
        _add_node(p.user_id, NetworkNodeType.RESEARCHER, p.name or p.user_id, {
            "institution": p.institution,
            "country": p.country,
            "h_index": p.h_index,
            "domains": p.domains[:3],
        })

        # ── Institution nodes ─────────────────────────────────────────────────
        if include_institution_nodes and p.institution:
            inst_id = f"inst:{p.institution.lower().replace(' ', '_')}"
            _add_node(inst_id, NetworkNodeType.INSTITUTION, p.institution,
                      {"country": p.country})
            _add_edge(p.user_id, inst_id, weight=1.0, etype="affiliated_with")

        # ── Topic (domain) nodes ──────────────────────────────────────────────
        if include_topic_nodes:
            for domain in p.domains[:5]:
                topic_id = f"topic:{domain.lower().replace(' ', '_')}"
                _add_node(topic_id, NetworkNodeType.TOPIC, domain)
                _add_edge(p.user_id, topic_id, weight=0.9, etype="researches")

            for kw in p.keywords[:3]:
                kw_id = f"topic:{kw.lower().replace(' ', '_')}"
                _add_node(kw_id, NetworkNodeType.TOPIC, kw)
                _add_edge(p.user_id, kw_id, weight=0.7, etype="keyword")

        # ── Method nodes ──────────────────────────────────────────────────────
        if include_method_nodes:
            for method in (p.methods + p.statistical_expertise)[:4]:
                method_id = f"method:{method.lower().replace(' ', '_')}"
                _add_node(method_id, NetworkNodeType.METHOD, method)
                _add_edge(p.user_id, method_id, weight=0.8, etype="uses")

    # ── Researcher-Researcher edges (shared topic/institution proximity) ───────
    profile_map: dict[str, ResearcherProfile] = {p.user_id: p for p in profiles}
    for i, pa in enumerate(profiles):
        for pb in profiles[i + 1:]:
            shared = pa.all_interests() & pb.all_interests()
            if shared:
                weight = min(len(shared) / 5.0, 1.0)
                _add_edge(pa.user_id, pb.user_id, weight=weight, etype="co_researcher")

    # ── Node centrality (degree) ──────────────────────────────────────────────
    degree: dict[str, int] = {}
    for e in edges:
        degree[e.from_id] = degree.get(e.from_id, 0) + 1
        degree[e.to_id]   = degree.get(e.to_id,   0) + 1

    total_nodes = max(len(nodes), 1)
    for node in nodes:
        node.centrality = round(degree.get(node.node_id, 0) / total_nodes, 4)
        node.connections = degree.get(node.node_id, 0)

    return ResearchNetwork(nodes=nodes, edges=edges)
