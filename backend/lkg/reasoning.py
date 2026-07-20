"""Graph reasoning — infer new relationships, detect communities, compute centrality.

All inferred relationships are labeled status="inferred" so users always know
they were derived by graph reasoning, not directly observed.

EVIDENCE POLICY: No relationship is labeled "verified" unless it comes from a
confirmed external source. Inferred edges are never presented as facts.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Optional

from .graph_store import upsert_edge
from .models import LKGEdge

logger = logging.getLogger("lkg.reasoning")


# ── Inference: friend-of-friend ───────────────────────────────────────────────

async def infer_collaborations(db, node_type: str = "researcher", limit: int = 200) -> list[dict]:
    """
    A co-authors with B. B co-authors with C. Infer A might collaborate with C.
    Produces edges labeled status='inferred', confidence='low'.
    Returns list of newly inferred edge dicts.
    Returns without saving — caller decides whether to persist.
    """
    # Load all CO_AUTHORED edges
    edges = await db.lkg_edges.find(
        {"type": "CO_AUTHORED"}, {"_id": 0, "from_id": 1, "to_id": 1}
    ).limit(5000).to_list(5000)

    # Build adjacency
    adj: dict[str, set[str]] = defaultdict(set)
    for e in edges:
        adj[e["from_id"]].add(e["to_id"])
        adj[e["to_id"]].add(e["from_id"])

    inferred: list[dict] = []
    existing_pairs: set[tuple[str, str]] = {(e["from_id"], e["to_id"]) for e in edges}

    for node, neighbors in adj.items():
        for neighbor in neighbors:
            for fof in adj.get(neighbor, set()):
                if fof == node:
                    continue
                pair = (min(node, fof), max(node, fof))
                if (node, fof) not in existing_pairs and (fof, node) not in existing_pairs:
                    inferred.append({
                        "from_id":    node,
                        "to_id":      fof,
                        "type":       "COLLABORATES_WITH",
                        "via":        neighbor,
                        "source":     "lkg_reasoning",
                        "confidence": "low",
                        "status":     "inferred",
                        "evidence":   {"via_node": neighbor, "pattern": "friend_of_friend"},
                    })
                    existing_pairs.add(pair)
                    if len(inferred) >= limit:
                        return inferred

    return inferred


async def infer_citation_suggestions(db, manuscript_id: str) -> list[dict]:
    """
    Papers in the same research topics as a manuscript often cite shared references.
    Returns candidate citations labeled 'inferred', not 'verified'.
    """
    # Get the manuscript node
    ms_node_id = f"manuscript:platform:{manuscript_id}"
    ms_node    = await db.lkg_nodes.find_one({"node_id": ms_node_id})
    if not ms_node:
        return []

    # Find topic edges for this manuscript
    topic_edges = await db.lkg_edges.find(
        {"from_id": ms_node_id, "type": "BELONGS_TO_TOPIC"}, {"to_id": 1}
    ).to_list(10)
    topic_ids = [e["to_id"] for e in topic_edges]

    if not topic_ids:
        return []

    # Find other manuscripts in the same topics
    sibling_edges = await db.lkg_edges.find(
        {"to_id": {"$in": topic_ids}, "type": "BELONGS_TO_TOPIC", "from_id": {"$ne": ms_node_id}},
        {"from_id": 1}
    ).limit(20).to_list(20)
    sibling_ids = list({e["from_id"] for e in sibling_edges})

    # Publications cited by siblings but not by this manuscript
    my_citations = {
        e["to_id"] for e in
        await db.lkg_edges.find(
            {"from_id": ms_node_id, "type": "CITED"}, {"to_id": 1}
        ).to_list(100)
    }

    candidate_citations: list[dict] = []
    for sibling in sibling_ids[:10]:
        sib_cites = await db.lkg_edges.find(
            {"from_id": sibling, "type": "CITED"}, {"to_id": 1}
        ).limit(5).to_list(5)
        for ce in sib_cites:
            if ce["to_id"] not in my_citations:
                candidate_citations.append({
                    "publication_node_id": ce["to_id"],
                    "via_manuscript":      sibling,
                    "confidence":          "low",
                    "status":              "inferred",
                    "reasoning":           "Cited by manuscripts in the same research topics",
                })

    return candidate_citations[:10]


# ── Community detection (Union-Find) ─────────────────────────────────────────

async def detect_communities(db, edge_types: Optional[list[str]] = None) -> list[dict]:
    """
    Union-Find community detection on researcher co-authorship graph.
    Returns list of {community_id, members, size} — purely observed, not inferred.
    """
    etypes = edge_types or ["CO_AUTHORED", "COLLABORATES_WITH"]
    edges = await db.lkg_edges.find(
        {"type": {"$in": etypes}, "status": {"$ne": "inferred"}},
        {"from_id": 1, "to_id": 1}
    ).limit(20000).to_list(20000)

    parent: dict[str, str] = {}

    def find(x: str) -> str:
        if parent.setdefault(x, x) != x:
            parent[x] = find(parent[x])  # path compression
        return parent[x]

    def union(x: str, y: str) -> None:
        parent[find(x)] = find(y)

    for e in edges:
        union(e["from_id"], e["to_id"])

    # Group by root
    groups: dict[str, list[str]] = defaultdict(list)
    for node in parent:
        groups[find(node)].append(node)

    communities = [
        {"community_id": root, "members": members, "size": len(members)}
        for root, members in groups.items()
        if len(members) > 1
    ]
    communities.sort(key=lambda c: c["size"], reverse=True)
    return communities[:50]


# ── Degree centrality ─────────────────────────────────────────────────────────

async def degree_centrality(db, node_type: Optional[str] = None, limit: int = 20) -> list[dict]:
    """
    Degree centrality = number of edges (in + out) per node.
    Returns top nodes by degree.
    """
    pipeline = [
        {"$group": {"_id": "$from_id", "out_degree": {"$sum": 1}}},
    ]
    out_degrees = {r["_id"]: r["out_degree"] for r in await db.lkg_edges.aggregate(pipeline).to_list(10000)}

    pipeline2 = [
        {"$group": {"_id": "$to_id", "in_degree": {"$sum": 1}}},
    ]
    in_degrees = {r["_id"]: r["in_degree"] for r in await db.lkg_edges.aggregate(pipeline2).to_list(10000)}

    all_nodes = set(out_degrees) | set(in_degrees)
    centrality = [
        {
            "node_id": n,
            "degree":  out_degrees.get(n, 0) + in_degrees.get(n, 0),
            "out":     out_degrees.get(n, 0),
            "in":      in_degrees.get(n, 0),
        }
        for n in all_nodes
    ]
    centrality.sort(key=lambda x: x["degree"], reverse=True)

    if node_type:
        node_ids = [c["node_id"] for c in centrality[:200]]
        typed = await db.lkg_nodes.find(
            {"node_id": {"$in": node_ids}, "type": node_type}, {"node_id": 1, "label": 1, "_id": 0}
        ).to_list(200)
        typed_map = {n["node_id"]: n["label"] for n in typed}
        centrality = [
            {**c, "label": typed_map[c["node_id"]]}
            for c in centrality if c["node_id"] in typed_map
        ]

    return centrality[:limit]
