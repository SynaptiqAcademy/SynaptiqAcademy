"""Academic Knowledge Graph — Graph Builder (Phase XVII).

Transforms platform data (researchers, publications, grants, institutions, etc.)
into Knowledge Graph nodes and edges. Pure Python, no external dependencies.
"""
from __future__ import annotations

from .graph_store import AcademicKnowledgeGraph
from .models import NodeType, RelType


# ── Helper ────────────────────────────────────────────────────────────────────

def _s(v, d="") -> str:
    return str(v).strip() if v else d


def _lst(v) -> list:
    return v if isinstance(v, list) else []


# ── Builder functions ─────────────────────────────────────────────────────────

def add_researcher(graph: AcademicKnowledgeGraph, user: dict) -> str:
    """
    Add a researcher node (and institutional/departmental edges) to the graph.
    Returns the node_id.
    """
    uid    = _s(user.get("_id") or user.get("id") or user.get("user_id"), "")
    name   = _s(user.get("full_name") or user.get("name"), "Unknown")
    pos    = _s(user.get("position") or user.get("user_type"), "researcher")

    # Determine node type from position
    pos_l = pos.lower()
    if "student" in pos_l or "phd" in pos_l or "doctoral" in pos_l:
        nt = NodeType.STUDENT
    elif "supervisor" in pos_l or "professor" in pos_l or "associate" in pos_l:
        nt = NodeType.SUPERVISOR
    else:
        nt = NodeType.RESEARCHER

    node_id = f"researcher_{uid}" if uid else None
    props = {
        "institution":   _s(user.get("institution")),
        "department":    _s(user.get("department")),
        "h_index":       user.get("h_index", 0),
        "publications":  user.get("publication_count", 0),
        "country":       _s(user.get("country")),
    }

    if node_id:
        node = graph.add_node(node_id, nt, name, props)
    else:
        node = graph.get_or_create_node(nt, name, props)
        node_id = node.node_id

    # Institution node + belongs_to edge
    inst_name = _s(user.get("institution"))
    if inst_name:
        inst_node = graph.get_or_create_node(NodeType.INSTITUTION, inst_name,
                                              {"country": props["country"]})
        graph.add_edge(node_id, inst_node.node_id, RelType.BELONGS_TO)

    # Department node + belongs_to edge
    dept_name = _s(user.get("department") or user.get("faculty"))
    if dept_name:
        dept_node = graph.get_or_create_node(NodeType.DEPARTMENT, dept_name)
        graph.add_edge(node_id, dept_node.node_id, RelType.BELONGS_TO)

    # Country node
    country = _s(user.get("country"))
    if country:
        cnode = graph.get_or_create_node(NodeType.COUNTRY, country)
        graph.add_edge(inst_node.node_id if inst_name else node_id,
                       cnode.node_id, RelType.BELONGS_TO)

    # Research areas → topic/keyword nodes
    for area in _lst(user.get("research_areas") or user.get("domains")):
        t = graph.get_or_create_node(NodeType.TOPIC, str(area))
        graph.add_edge(node_id, t.node_id, RelType.SHARES_RESEARCH_INTEREST)

    # Methods → method nodes
    for meth in _lst(user.get("research_methods")):
        m = graph.get_or_create_node(NodeType.METHOD, str(meth))
        graph.add_edge(node_id, m.node_id, RelType.USES_METHOD)

    # Programming skills → programming language nodes
    for lang in _lst(user.get("programming_skills")):
        l = graph.get_or_create_node(NodeType.PROGRAMMING_LANGUAGE, str(lang))
        graph.add_edge(node_id, l.node_id, RelType.IMPLEMENTS)

    # Statistical expertise → statistical method nodes
    for stat in _lst(user.get("statistical_expertise")):
        s = graph.get_or_create_node(NodeType.STATISTICAL_METHOD, str(stat))
        graph.add_edge(node_id, s.node_id, RelType.USES_METHOD)

    return node_id


def add_publication(graph: AcademicKnowledgeGraph, pub: dict, author_node_ids: list[str] | None = None) -> str:
    """Add a publication node and all related edges."""
    pid   = _s(pub.get("_id") or pub.get("id") or pub.get("doi"), "")
    title = _s(pub.get("title"), "Untitled Publication")
    props = {
        "year":        pub.get("year") or pub.get("publication_year", 0),
        "citations":   pub.get("citation_count", 0),
        "doi":         _s(pub.get("doi")),
        "abstract":    _s(pub.get("abstract"))[:500],
    }

    node_id = f"pub_{pid}" if pid else None
    if node_id:
        pub_node = graph.add_node(node_id, NodeType.PUBLICATION, title, props)
    else:
        pub_node = graph.get_or_create_node(NodeType.PUBLICATION, title, props)
        node_id = pub_node.node_id

    # Author edges
    for aut_id in (author_node_ids or []):
        if graph.get_node(aut_id):
            graph.add_edge(aut_id, node_id, RelType.WRITES)

    # Authors from dict
    for author in _lst(pub.get("authors")):
        aname = _s(author.get("name") or author) if isinstance(author, dict) else _s(author)
        if aname:
            anode = graph.get_or_create_node(NodeType.RESEARCHER, aname)
            graph.add_edge(anode.node_id, node_id, RelType.WRITES)

    # Journal → published_in
    journal = _s(pub.get("journal") or pub.get("venue"))
    if journal:
        j = graph.get_or_create_node(NodeType.JOURNAL, journal)
        graph.add_edge(node_id, j.node_id, RelType.PUBLISHED_IN)

    # Keywords
    for kw in _lst(pub.get("keywords")):
        k = graph.get_or_create_node(NodeType.KEYWORD, str(kw))
        graph.add_edge(node_id, k.node_id, RelType.SHARES_KEYWORD)

    # Methods used
    for meth in _lst(pub.get("methods")):
        m = graph.get_or_create_node(NodeType.METHOD, str(meth))
        graph.add_edge(node_id, m.node_id, RelType.USES_METHOD)

    # Cited publications
    for cited in _lst(pub.get("references") or pub.get("citations")):
        cited_id = _s(cited.get("id") or cited) if isinstance(cited, dict) else _s(cited)
        if cited_id:
            cnode = graph.get_or_create_node(NodeType.PUBLICATION, cited_id,
                                              {"title": cited_id})
            graph.add_edge(node_id, cnode.node_id, RelType.CITES)

    return node_id


def add_grant(graph: AcademicKnowledgeGraph, grant: dict, pi_node_ids: list[str] | None = None) -> str:
    """Add a grant node and related edges."""
    gid   = _s(grant.get("_id") or grant.get("id"), "")
    title = _s(grant.get("title") or grant.get("name"), "Untitled Grant")
    props = {
        "amount":   grant.get("amount", 0),
        "currency": _s(grant.get("currency"), "EUR"),
        "year":     grant.get("year", 0),
        "status":   _s(grant.get("status"), "active"),
    }

    node_id = f"grant_{gid}" if gid else None
    if node_id:
        grant_node = graph.add_node(node_id, NodeType.GRANT, title, props)
    else:
        grant_node = graph.get_or_create_node(NodeType.GRANT, title, props)
        node_id = grant_node.node_id

    # PI edges
    for pi_id in (pi_node_ids or []):
        if graph.get_node(pi_id):
            graph.add_edge(pi_id, node_id, RelType.FUNDED_BY)

    # Funding agency
    agency = _s(grant.get("funding_agency") or grant.get("funder"))
    if agency:
        fa = graph.get_or_create_node(NodeType.FUNDING_AGENCY, agency)
        graph.add_edge(node_id, fa.node_id, RelType.FUNDED_BY)

    # Topics
    for topic in _lst(grant.get("topics") or grant.get("research_areas")):
        t = graph.get_or_create_node(NodeType.TOPIC, str(topic))
        graph.add_edge(node_id, t.node_id, RelType.SHARES_KEYWORD)

    # Participating researchers
    for participant in _lst(grant.get("investigators") or grant.get("team")):
        pname = _s(participant.get("name") or participant) if isinstance(participant, dict) else _s(participant)
        if pname:
            pnode = graph.get_or_create_node(NodeType.RESEARCHER, pname)
            graph.add_edge(pnode.node_id, node_id, RelType.PARTICIPATES_IN)
            graph.add_edge(pnode.node_id, node_id, RelType.SHARES_GRANT)

    return node_id


def add_institution(graph: AcademicKnowledgeGraph, inst: dict) -> str:
    """Add an institution node with department sub-nodes."""
    iid   = _s(inst.get("_id") or inst.get("id"), "")
    name  = _s(inst.get("name"), "Unknown Institution")
    props = {
        "country":    _s(inst.get("country")),
        "type":       _s(inst.get("type"), "university"),
        "website":    _s(inst.get("website")),
    }

    node_id = f"inst_{iid}" if iid else None
    if node_id:
        graph.add_node(node_id, NodeType.INSTITUTION, name, props)
    else:
        node = graph.get_or_create_node(NodeType.INSTITUTION, name, props)
        node_id = node.node_id

    for dept in _lst(inst.get("departments")):
        dname = _s(dept.get("name") or dept) if isinstance(dept, dict) else _s(dept)
        if dname:
            d = graph.get_or_create_node(NodeType.DEPARTMENT, dname)
            graph.add_edge(d.node_id, node_id, RelType.BELONGS_TO)

    return node_id


def add_collaboration(graph: AcademicKnowledgeGraph, collab: dict) -> None:
    """Add a collaboration edge between two researchers/nodes."""
    r1_id = _s(collab.get("researcher_1_id") or collab.get("user_id_1"))
    r2_id = _s(collab.get("researcher_2_id") or collab.get("user_id_2"))
    if r1_id and r2_id:
        r1 = graph.get_or_create_node(NodeType.RESEARCHER, r1_id)
        r2 = graph.get_or_create_node(NodeType.RESEARCHER, r2_id)
        graph.add_edge(r1.node_id, r2.node_id, RelType.COLLABORATES_WITH)
        graph.add_edge(r2.node_id, r1.node_id, RelType.COLLABORATES_WITH)


def add_conference(graph: AcademicKnowledgeGraph, conf: dict, paper_node_ids: list[str] | None = None) -> str:
    """Add a conference node and presented_at edges."""
    cname = _s(conf.get("name") or conf.get("title"), "Unknown Conference")
    cnode = graph.get_or_create_node(NodeType.CONFERENCE, cname,
                                      {"year": conf.get("year", 0),
                                       "location": _s(conf.get("location"))})
    for pid in (paper_node_ids or []):
        if graph.get_node(pid):
            graph.add_edge(pid, cnode.node_id, RelType.PRESENTED_AT)
    return cnode.node_id


# ── Bulk import ───────────────────────────────────────────────────────────────

def import_platform_data(graph: AcademicKnowledgeGraph, data: dict) -> dict:
    """
    Bulk import platform data into the Knowledge Graph.

    data keys (all optional):
      researchers: list[dict]
      publications: list[dict]
      grants:       list[dict]
      institutions: list[dict]
      collaborations: list[dict]
      conferences:  list[dict]
    """
    counts = {"nodes_before": graph.node_count(), "edges_before": graph.edge_count()}

    researcher_ids: dict[str, str] = {}  # original_id -> graph node_id

    for r in data.get("researchers") or []:
        uid = _s(r.get("_id") or r.get("id") or r.get("user_id"), "")
        nid = add_researcher(graph, r)
        if uid:
            researcher_ids[uid] = nid

    for p in data.get("publications") or []:
        # Map author IDs to graph node IDs
        author_nids = [researcher_ids[aid] for aid in _lst(p.get("author_ids"))
                       if aid in researcher_ids]
        add_publication(graph, p, author_nids)

    for g in data.get("grants") or []:
        pi_nids = [researcher_ids[pid] for pid in _lst(g.get("pi_ids"))
                   if pid in researcher_ids]
        add_grant(graph, g, pi_nids)

    for i in data.get("institutions") or []:
        add_institution(graph, i)

    for c in data.get("collaborations") or []:
        add_collaboration(graph, c)

    for conf in data.get("conferences") or []:
        paper_nids = [f"pub_{_s(p)}" for p in _lst(conf.get("paper_ids"))]
        add_conference(graph, conf, [p for p in paper_nids if graph.get_node(p)])

    counts.update({
        "nodes_after":  graph.node_count(),
        "edges_after":  graph.edge_count(),
        "nodes_added":  graph.node_count() - counts["nodes_before"],
        "edges_added":  graph.edge_count() - counts["edges_before"],
    })
    return counts
