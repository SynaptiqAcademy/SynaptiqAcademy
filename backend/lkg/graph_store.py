"""MongoDB-native graph storage for the Living Knowledge Graph.

Collections:
  lkg_nodes  — all entity nodes
  lkg_edges  — all directed relationships
  lkg_jobs   — ingestion job history

Key design:
  - node_id is the stable external identifier (not MongoDB _id)
  - upsert_node / upsert_edge are idempotent — safe to call repeatedly
  - get_subgraph uses BFS via repeated queries (MongoDB $graphLookup limited to same collection)
  - Indexes are created by ensure_indexes() called once at startup
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from .models import LKGEdge, LKGNode

logger = logging.getLogger("lkg.store")


# ── Index setup ───────────────────────────────────────────────────────────────

async def ensure_indexes(db) -> None:
    try:
        await db.lkg_nodes.create_index("node_id",  unique=True)
        await db.lkg_nodes.create_index("type")
        await db.lkg_nodes.create_index([("label", "text")])
        await db.lkg_edges.create_index("from_id")
        await db.lkg_edges.create_index("to_id")
        await db.lkg_edges.create_index([("from_id", 1), ("type", 1)])
        await db.lkg_edges.create_index([("to_id", 1),   ("type", 1)])
        await db.lkg_edges.create_index([("from_id", 1), ("to_id", 1), ("type", 1)], unique=True)
        logger.info("LKG indexes ensured")
    except Exception as exc:
        logger.warning("LKG index creation error (non-blocking): %s", exc)


# ── Node operations ───────────────────────────────────────────────────────────

async def upsert_node(db, node: LKGNode | dict) -> str:
    """Create or update a node. Returns node_id."""
    doc = node.to_doc() if isinstance(node, LKGNode) else node
    doc.setdefault("last_updated", datetime.now(timezone.utc))
    node_id = doc["node_id"]
    await db.lkg_nodes.update_one(
        {"node_id": node_id},
        {"$set": doc, "$inc": {"version": 0}},  # version bump handled in $setOnInsert
        upsert=True,
    )
    return node_id


async def get_node(db, node_id: str) -> Optional[dict]:
    doc = await db.lkg_nodes.find_one({"node_id": node_id}, {"_id": 0})
    return doc


async def list_nodes(db, node_type: Optional[str] = None, limit: int = 100, skip: int = 0) -> list[dict]:
    q = {"type": node_type} if node_type else {}
    return await db.lkg_nodes.find(q, {"_id": 0}).skip(skip).limit(limit).to_list(limit)


async def search_nodes(db, query: str, types: Optional[list[str]] = None, limit: int = 20) -> list[dict]:
    """Full-text search over node labels and metadata."""
    q: dict[str, Any] = {"$text": {"$search": query}}
    if types:
        q["type"] = {"$in": types}
    try:
        return await db.lkg_nodes.find(q, {"_id": 0, "score": {"$meta": "textScore"}}).sort(
            [("score", {"$meta": "textScore"})]
        ).limit(limit).to_list(limit)
    except Exception:
        # Fallback to regex if text index not ready
        regex_q: dict = {"label": {"$regex": query, "$options": "i"}}
        if types:
            regex_q["type"] = {"$in": types}
        return await db.lkg_nodes.find(regex_q, {"_id": 0}).limit(limit).to_list(limit)


# ── Edge operations ───────────────────────────────────────────────────────────

async def upsert_edge(db, edge: LKGEdge | dict) -> None:
    """Create or update a directed edge. Identified by (from_id, to_id, type)."""
    doc = edge.to_doc() if isinstance(edge, LKGEdge) else edge
    doc.setdefault("created_at", datetime.now(timezone.utc))
    await db.lkg_edges.update_one(
        {"from_id": doc["from_id"], "to_id": doc["to_id"], "type": doc["type"]},
        {"$set": doc},
        upsert=True,
    )


async def get_edges(db, node_id: str, direction: str = "both", edge_types: Optional[list[str]] = None) -> list[dict]:
    """Get all edges for a node. direction: 'out' | 'in' | 'both'."""
    q_parts = []
    if direction in ("out", "both"):
        q_parts.append({"from_id": node_id})
    if direction in ("in", "both"):
        q_parts.append({"to_id": node_id})
    q: dict = {"$or": q_parts} if len(q_parts) > 1 else q_parts[0]
    if edge_types:
        q["type"] = {"$in": edge_types}
    return await db.lkg_edges.find(q, {"_id": 0}).limit(200).to_list(200)


# ── Graph traversal ───────────────────────────────────────────────────────────

async def get_neighbors(db, node_id: str, depth: int = 1, limit: int = 50) -> dict:
    """
    BFS from a node to a given depth.
    Returns {nodes: [...], edges: [...]}.
    depth=1: immediate neighbors only.
    depth=2: neighbors of neighbors.
    Capped at `limit` total nodes to keep responses fast.
    """
    visited_nodes = {node_id}
    collected_edges: list[dict] = []
    frontier = {node_id}

    for _ in range(depth):
        if not frontier:
            break
        edges = await db.lkg_edges.find(
            {"$or": [{"from_id": {"$in": list(frontier)}}, {"to_id": {"$in": list(frontier)}}]},
            {"_id": 0}
        ).limit(limit * 3).to_list(limit * 3)

        new_frontier = set()
        for e in edges:
            collected_edges.append(e)
            for nid in (e["from_id"], e["to_id"]):
                if nid not in visited_nodes and len(visited_nodes) < limit:
                    visited_nodes.add(nid)
                    new_frontier.add(nid)
        frontier = new_frontier

    # Deduplicate edges
    seen_edges: set[tuple] = set()
    unique_edges = []
    for e in collected_edges:
        key = (e["from_id"], e["to_id"], e["type"])
        if key not in seen_edges:
            seen_edges.add(key)
            unique_edges.append(e)

    # Fetch node details for all visited nodes
    nodes = await db.lkg_nodes.find(
        {"node_id": {"$in": list(visited_nodes)}}, {"_id": 0}
    ).to_list(limit)

    return {"nodes": nodes, "edges": unique_edges}


async def get_subgraph(db, node_id: str, depth: int = 2, limit: int = 60) -> dict:
    """Extract a visualizable subgraph anchored on a node."""
    seed = await get_node(db, node_id)
    if not seed:
        return {"nodes": [], "edges": []}

    result = await get_neighbors(db, node_id, depth=depth, limit=limit)
    # Ensure seed node is in the list
    if not any(n["node_id"] == node_id for n in result["nodes"]):
        result["nodes"].insert(0, seed)

    return result


async def find_path(db, from_id: str, to_id: str, max_depth: int = 4) -> list[dict]:
    """
    BFS shortest path between two nodes.
    Returns list of edges forming the path, or [] if not found.
    """
    if from_id == to_id:
        return []

    # BFS
    queue    = [(from_id, [])]
    visited  = {from_id}
    depth    = 0

    while queue and depth < max_depth:
        next_queue = []
        depth += 1
        for current, path in queue:
            edges = await db.lkg_edges.find(
                {"from_id": current}, {"_id": 0}
            ).limit(30).to_list(30)
            for edge in edges:
                if edge["to_id"] == to_id:
                    return path + [edge]
                if edge["to_id"] not in visited:
                    visited.add(edge["to_id"])
                    next_queue.append((edge["to_id"], path + [edge]))
        queue = next_queue

    return []  # No path found within max_depth


# ── Graph statistics ──────────────────────────────────────────────────────────

async def get_stats(db) -> dict:
    """Returns high-level graph statistics."""
    try:
        node_count = await db.lkg_nodes.count_documents({})
        edge_count = await db.lkg_edges.count_documents({})
        types_pipeline = [{"$group": {"_id": "$type", "count": {"$sum": 1}}}]
        type_counts = {r["_id"]: r["count"] for r in await db.lkg_nodes.aggregate(types_pipeline).to_list(50)}
        return {
            "total_nodes":  node_count,
            "total_edges":  edge_count,
            "node_types":   type_counts,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.error("Stats error: %s", exc)
        return {"total_nodes": 0, "total_edges": 0, "node_types": {}}
