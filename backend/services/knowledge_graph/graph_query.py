"""Academic Knowledge Graph — Graph Query Engine (Phase XVII).

Supports complex multi-hop queries:
  - query_by_topic      — all nodes connected to a topic label
  - query_connected     — k-hop neighborhood of a node
  - query_path          — shortest path between two nodes (BFS)
  - query_type_filter   — nodes of a type matching a keyword
  - complex_query       — structured dict-based query

Pure Python BFS/DFS traversal.
"""
from __future__ import annotations

from collections import deque

from .graph_store import AcademicKnowledgeGraph
from .models import KGQueryResult, NodeType, QueryScope, RelType


# ── Helpers ───────────────────────────────────────────────────────────────────

def _node_matches_keyword(label: str, keyword: str) -> bool:
    return keyword.lower() in label.lower()


def _node_to_dict(graph: AcademicKnowledgeGraph, node_id: str) -> dict:
    node = graph.get_node(node_id)
    if not node:
        return {}
    return {
        "node_id":   node_id,
        "label":     node.label,
        "node_type": node.node_type.value,
        "degree":    graph.degree(node_id),
        "properties": node.properties,
    }


# ── Query functions ───────────────────────────────────────────────────────────

def query_by_topic(
    graph: AcademicKnowledgeGraph,
    topic: str,
    scope: QueryScope = QueryScope.ALL,
    max_hops: int = 2,
    max_results: int = 50,
) -> KGQueryResult:
    """
    Find all nodes connected (within max_hops) to any topic node
    whose label contains the query string.
    """
    topic_types = {NodeType.TOPIC.value, NodeType.KEYWORD.value,
                   NodeType.CONCEPT.value, NodeType.DOMAIN.value}
    scope_types = _scope_to_types(scope)

    # 1. Find matching topic nodes
    seed_ids: list[str] = []
    for node in graph.all_nodes():
        if node.node_type.value in topic_types and _node_matches_keyword(node.label, topic):
            seed_ids.append(node.node_id)

    if not seed_ids:
        return KGQueryResult(
            query=topic, scope=scope.value,
            nodes=[], total=0,
            reasoning=f"No topic nodes found matching '{topic}'.",
        )

    # 2. BFS from seeds up to max_hops
    visited: set[str] = set(seed_ids)
    frontier: list[str] = list(seed_ids)
    for _ in range(max_hops):
        next_frontier: list[str] = []
        for nid in frontier:
            for nb in graph.neighbors(nid, direction="both"):
                if nb not in visited:
                    visited.add(nb)
                    next_frontier.append(nb)
        frontier = next_frontier

    # 3. Filter by scope, sorted by degree
    results: list[dict] = []
    for nid in visited:
        node = graph.get_node(nid)
        if not node:
            continue
        if scope_types and node.node_type.value not in scope_types:
            continue
        results.append(_node_to_dict(graph, nid))

    results.sort(key=lambda r: -r.get("degree", 0))
    results = results[:max_results]

    return KGQueryResult(
        query=topic,
        scope=scope.value,
        nodes=results,
        total=len(results),
        reasoning=(f"Found {len(seed_ids)} topic node(s) matching '{topic}'; "
                   f"expanded {max_hops} hops to {len(results)} result(s)."),
    )


def query_connected(
    graph: AcademicKnowledgeGraph,
    node_id: str,
    rel_type: str | None = None,
    depth: int = 1,
    direction: str = "both",
    max_results: int = 100,
) -> KGQueryResult:
    """Return the k-hop neighborhood of a node."""
    if not graph.get_node(node_id):
        return KGQueryResult(query=node_id, scope="connected",
                             nodes=[], total=0,
                             reasoning=f"Node '{node_id}' not found.")

    visited: set[str] = {node_id}
    frontier = [node_id]
    for _ in range(depth):
        nxt: list[str] = []
        for nid in frontier:
            for nb in graph.neighbors(nid, rel_type=rel_type, direction=direction):
                if nb not in visited:
                    visited.add(nb)
                    nxt.append(nb)
        frontier = nxt

    visited.discard(node_id)
    results = [_node_to_dict(graph, nid) for nid in list(visited)[:max_results]]
    results.sort(key=lambda r: -r.get("degree", 0))

    return KGQueryResult(
        query=node_id,
        scope="connected",
        nodes=results,
        total=len(results),
        reasoning=f"{depth}-hop neighborhood: {len(results)} node(s).",
    )


def query_path(
    graph: AcademicKnowledgeGraph,
    source_id: str,
    target_id: str,
    max_depth: int = 6,
) -> KGQueryResult:
    """Find the shortest path between two nodes using BFS."""
    if source_id == target_id:
        return KGQueryResult(query=f"{source_id}→{target_id}", scope="path",
                             paths=[[source_id]], total=1,
                             reasoning="Source and target are the same node.")

    visited: set[str] = {source_id}
    queue: deque[list[str]] = deque([[source_id]])
    found_path: list[str] = []

    while queue:
        path = queue.popleft()
        if len(path) > max_depth:
            break
        last = path[-1]
        for nb in graph.neighbors(last, direction="both"):
            if nb == target_id:
                found_path = path + [nb]
                break
            if nb not in visited:
                visited.add(nb)
                queue.append(path + [nb])
        if found_path:
            break

    if not found_path:
        return KGQueryResult(query=f"{source_id}→{target_id}", scope="path",
                             paths=[], total=0,
                             reasoning=f"No path found within {max_depth} hops.")

    # Convert to readable labels
    path_labels = [graph.get_node(nid).label for nid in found_path if graph.get_node(nid)]
    return KGQueryResult(
        query=f"{source_id}→{target_id}",
        scope="path",
        nodes=[_node_to_dict(graph, nid) for nid in found_path],
        paths=[found_path],
        total=len(found_path),
        reasoning=f"Path length {len(found_path) - 1}: {' → '.join(path_labels)}",
    )


def query_type_filter(
    graph: AcademicKnowledgeGraph,
    keyword: str,
    node_type: NodeType | str | None = None,
    max_results: int = 50,
) -> KGQueryResult:
    """Find nodes whose label contains keyword, optionally filtered by type."""
    nt = (NodeType(node_type) if isinstance(node_type, str) and node_type else
          node_type if isinstance(node_type, NodeType) else None)

    results: list[dict] = []
    nodes_to_search = (graph.nodes_by_type(nt) if nt else graph.all_nodes())
    for node in nodes_to_search:
        if _node_matches_keyword(node.label, keyword):
            results.append(_node_to_dict(graph, node.node_id))

    results.sort(key=lambda r: -r.get("degree", 0))
    results = results[:max_results]

    return KGQueryResult(
        query=keyword,
        scope=nt.value if nt else "all",
        nodes=results,
        total=len(results),
        reasoning=f"Keyword '{keyword}' matched {len(results)} node(s).",
    )


def complex_query(
    graph: AcademicKnowledgeGraph,
    query: dict,
    max_results: int = 50,
) -> KGQueryResult:
    """
    Execute a structured query.

    Supported query dict keys:
      topic:       str      — match topic nodes by keyword
      node_type:   str      — filter by NodeType
      rel_type:    str      — only return nodes with this relationship type
      keyword:     str      — label keyword filter
      scope:       str      — QueryScope value
      depth:       int      — hop depth for expansion (default 1)
      source_id:   str      — start node for path/connected queries
      target_id:   str      — end node for path queries
    """
    topic     = query.get("topic")
    keyword   = query.get("keyword") or query.get("label")
    node_type = query.get("node_type")
    rel_type  = query.get("rel_type")
    scope_str = query.get("scope", "all")
    depth     = int(query.get("depth", 1))
    source_id = query.get("source_id")
    target_id = query.get("target_id")

    try:
        scope = QueryScope(scope_str)
    except ValueError:
        scope = QueryScope.ALL

    if source_id and target_id:
        return query_path(graph, source_id, target_id)

    if source_id:
        return query_connected(graph, source_id, rel_type=rel_type, depth=depth)

    if topic:
        return query_by_topic(graph, topic, scope=scope, max_hops=depth,
                               max_results=max_results)

    if keyword:
        return query_type_filter(graph, keyword, node_type=node_type,
                                  max_results=max_results)

    return KGQueryResult(query=str(query), scope=scope.value,
                         nodes=[], total=0,
                         reasoning="No valid query parameters provided.")


# ── Scope mapping ─────────────────────────────────────────────────────────────

def _scope_to_types(scope: QueryScope) -> set[str]:
    mapping = {
        QueryScope.RESEARCHERS:  {NodeType.RESEARCHER.value, NodeType.STUDENT.value,
                                   NodeType.SUPERVISOR.value},
        QueryScope.PUBLICATIONS: {NodeType.PUBLICATION.value},
        QueryScope.GRANTS:       {NodeType.GRANT.value},
        QueryScope.INSTITUTIONS: {NodeType.INSTITUTION.value, NodeType.DEPARTMENT.value,
                                   NodeType.RESEARCH_CENTER.value},
        QueryScope.TOPICS:       {NodeType.TOPIC.value, NodeType.KEYWORD.value,
                                   NodeType.CONCEPT.value, NodeType.DOMAIN.value},
        QueryScope.METHODS:      {NodeType.METHOD.value, NodeType.STATISTICAL_METHOD.value},
        QueryScope.ALL:          set(),
    }
    return mapping.get(scope, set())
