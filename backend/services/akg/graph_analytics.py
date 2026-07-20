"""Graph analytics — degree centrality, PageRank influence, community detection, trends."""
from __future__ import annotations
import asyncio
from .graph_adapter import get_adapter
from lkg.unified import get_unified_graph


async def compute_degree_centrality(db, entity_type: str | None = None,
                                     top_n: int = 20) -> list[dict]:
    """Degree centrality: nodes with most relationships."""
    unified = get_unified_graph()

    out_pipeline = [{"$group": {"_id": "$from_id", "out_degree": {"$sum": 1}}}]
    in_pipeline  = [{"$group": {"_id": "$to_id",   "in_degree":  {"$sum": 1}}}]
    out_agg, in_agg = await asyncio.gather(
        unified.aggregate_edges(db, out_pipeline),
        unified.aggregate_edges(db, in_pipeline),
    )

    out_map: dict[str, int] = {item["_id"]: item["out_degree"] for item in out_agg if item["_id"]}
    in_map:  dict[str, int] = {item["_id"]: item["in_degree"]  for item in in_agg  if item["_id"]}
    all_ids = set(out_map) | set(in_map)

    scored: list[tuple[int, str]] = []
    for eid in all_ids:
        total = out_map.get(eid, 0) + in_map.get(eid, 0)
        scored.append((total, eid))
    scored.sort(reverse=True)

    top_ids = [eid for _, eid in scored[:top_n]]
    results = []
    for eid in top_ids:
        entity = await get_adapter().get_entity(eid, db)
        if entity:
            etype = entity.get("type") or entity.get("entity_type")
            if entity_type and etype != entity_type:
                continue
            entity["degree"]     = out_map.get(eid, 0) + in_map.get(eid, 0)
            entity["out_degree"] = out_map.get(eid, 0)
            entity["in_degree"]  = in_map.get(eid, 0)
            results.append(entity)
    return results[:top_n]


async def compute_influence_score(db, top_n: int = 20) -> list[dict]:
    """PageRank-inspired influence: nodes cited/referenced often score higher."""
    in_pipeline = [
        {"$group": {"_id": "$to_id", "in_degree": {"$sum": 1}}},
        {"$sort": {"in_degree": -1}},
        {"$limit": top_n * 2},
    ]
    agg = await get_unified_graph().aggregate_edges(db, in_pipeline)
    agg.sort(key=lambda x: x.get("in_degree", 0), reverse=True)

    results = []
    for item in agg:
        entity = await get_adapter().get_entity(item["_id"], db)
        if entity:
            entity["influence_score"] = item["in_degree"]
            results.append(entity)
        if len(results) >= top_n:
            break
    return results


async def detect_communities(db, max_iterations: int = 5) -> list[dict]:
    """Label propagation community detection — delegates to unified service."""
    communities = await get_unified_graph().detect_communities(db, max_nodes=5000)
    return [
        {
            "community_id": c["community_id"],
            "size":         c["size"],
            "member_ids":   c["members"][:5],
        }
        for c in communities
        if c["size"] > 1
    ]


async def compute_collaboration_density(db) -> dict:
    """How densely connected is the collaboration network?"""
    unified = get_unified_graph()
    researcher_count, collab_count = await asyncio.gather(
        unified.count_nodes(db, {"entity_type": {"$in": ["researcher", "educator"]}}),
        unified.count_edges(db, {"rel_type": "COLLABORATES_WITH"}),
    )
    max_possible = researcher_count * (researcher_count - 1) / 2 if researcher_count > 1 else 1
    density = round(collab_count / max_possible, 6) if max_possible else 0.0
    return {
        "researcher_count":    researcher_count,
        "collaboration_count": collab_count,
        "density":             density,
        "density_label":       "Dense" if density > 0.1 else "Sparse" if density < 0.01 else "Moderate",
    }


async def get_network_overview(db) -> dict:
    unified = get_unified_graph()
    entity_count, rel_count, by_node_type, by_edge_type = await asyncio.gather(
        unified.count_nodes(db, {}),
        unified.count_edges(db, {}),
        unified.group_nodes_by_type(db),
        unified.group_edges_by_type(db),
    )

    density_info = await compute_collaboration_density(db)

    return {
        "total_entities":      entity_count,
        "total_relationships": rel_count,
        "avg_degree":          round(rel_count * 2 / max(entity_count, 1), 2),
        "entities_by_type":    by_node_type,
        "relationships_by_type": by_edge_type,
        "collaboration_density": density_info,
    }
