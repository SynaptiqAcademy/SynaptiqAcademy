"""Institution Intelligence Engine — Institution Knowledge Graph (Phase XV).

Builds a multi-entity knowledge graph:
Researchers ↔ Departments ↔ Publications ↔ Grants ↔ Topics ↔ Institutions ↔ Funding Orgs.
"""
from __future__ import annotations

from collections import defaultdict

from .models import (
    InstitutionInput, InstitutionKnowledgeGraph,
    KnowledgeGraphEdge, KnowledgeGraphNode,
)


def _node(nid: str, ntype: str, label: str, size: float = 1.0, **props) -> KnowledgeGraphNode:
    return KnowledgeGraphNode(
        node_id=nid, node_type=ntype, label=label,
        properties=dict(props), size=round(size, 2),
    )


def _edge(from_id: str, to_id: str, relation: str, weight: float = 1.0) -> KnowledgeGraphEdge:
    return KnowledgeGraphEdge(from_id=from_id, to_id=to_id,
                              relation=relation, weight=round(weight, 2))


def build_knowledge_graph(
    inp: InstitutionInput,
    max_nodes: int = 200,
) -> InstitutionKnowledgeGraph:
    """
    Build the institution knowledge graph from InstitutionInput.
    max_nodes limits output size for large institutions.
    """
    nodes: list[KnowledgeGraphNode] = []
    edges: list[KnowledgeGraphEdge] = []
    seen_nodes: set[str] = set()
    seen_edges: set[tuple[str, str, str]] = set()

    def _add_node(n: KnowledgeGraphNode) -> None:
        if n.node_id not in seen_nodes and len(nodes) < max_nodes:
            seen_nodes.add(n.node_id)
            nodes.append(n)

    def _add_edge(e: KnowledgeGraphEdge) -> None:
        key = (e.from_id, e.to_id, e.relation)
        if key not in seen_edges:
            seen_edges.add(key)
            edges.append(e)

    # ── Institution root node ──────────────────────────────────────────────────
    inst_id = "inst_root"
    _add_node(_node(inst_id, "institution", inp.name or "Institution",
                    size=5.0, country=inp.country, type=inp.institution_type))

    # ── Department nodes ───────────────────────────────────────────────────────
    dept_researcher_count: dict[str, int] = defaultdict(int)
    for r in inp.researchers:
        dept = r.get("department") or r.get("faculty") or "General"
        dept_researcher_count[dept] += 1

    dept_id_map: dict[str, str] = {}
    for dept_name, count in dept_researcher_count.items():
        did = f"dept_{dept_name.lower().replace(' ', '_')}"
        dept_id_map[dept_name] = did
        _add_node(_node(did, "department", dept_name,
                        size=1.0 + count * 0.1, researcher_count=count))
        _add_edge(_edge(inst_id, did, "has_department", weight=1.0))

    # ── Researcher nodes ───────────────────────────────────────────────────────
    topic_researchers: dict[str, list[str]] = defaultdict(list)
    for r in inp.researchers[:min(len(inp.researchers), 100)]:
        rid   = str(r.get("_id") or r.get("id") or "")
        name  = r.get("full_name") or r.get("name") or rid
        dept  = r.get("department") or r.get("faculty") or "General"
        h     = float(r.get("h_index") or 0)
        pubs  = int(r.get("publication_count") or 0)
        size  = 1.0 + min(h / 10, 3.0)
        rnode_id = f"researcher_{rid}"
        _add_node(_node(rnode_id, "researcher", name, size=size,
                        h_index=h, publication_count=pubs,
                        department=dept))
        # Edge: researcher ↔ department
        if dept in dept_id_map:
            _add_edge(_edge(dept_id_map[dept], rnode_id, "employs"))

        # Research area edges
        areas = r.get("research_areas") or r.get("domains") or []
        for area in areas[:3]:
            if area:
                topic_id = f"topic_{str(area).lower().replace(' ', '_')[:30]}"
                topic_researchers[area].append(rnode_id)
                if topic_id not in seen_nodes:
                    _add_node(_node(topic_id, "topic", str(area).title(), size=1.5))
                _add_edge(_edge(rnode_id, topic_id, "researches", weight=1.0))

    # ── Grant nodes ────────────────────────────────────────────────────────────
    funder_id_map: dict[str, str] = {}
    for g in inp.grants[:min(len(inp.grants), 50)]:
        gid    = str(g.get("_id") or g.get("id") or "")
        title  = g.get("title") or g.get("name") or gid
        amount = float(g.get("amount") or 0)
        size   = 1.0 + min(amount / 500000, 3.0)
        gnode_id = f"grant_{gid}"
        _add_node(_node(gnode_id, "grant", title[:40], size=size, amount=amount))
        _add_edge(_edge(inst_id, gnode_id, "received_grant"))

        # Funder node
        funder = g.get("funding_organization") or g.get("funder")
        if funder:
            fid = f"funder_{str(funder).lower().replace(' ', '_')[:20]}"
            funder_id_map[funder] = fid
            if fid not in seen_nodes:
                _add_node(_node(fid, "funding_org", str(funder), size=2.0))
            _add_edge(_edge(fid, gnode_id, "funds", weight=min(amount / 100000, 5.0)))

    # ── Project nodes ──────────────────────────────────────────────────────────
    for p in inp.projects[:min(len(inp.projects), 30)]:
        pid   = str(p.get("_id") or p.get("id") or "")
        title = p.get("title") or p.get("name") or pid
        ptype = p.get("type") or "research"
        pnode_id = f"project_{pid}"
        _add_node(_node(pnode_id, "project", title[:40], size=1.5, type=ptype))
        _add_edge(_edge(inst_id, pnode_id, "runs_project"))

    return InstitutionKnowledgeGraph(nodes=nodes, edges=edges)
