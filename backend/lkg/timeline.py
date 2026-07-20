"""Knowledge timeline — temporal events per entity, graph evolution over time."""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger("lkg.timeline")


async def entity_timeline(db, node_id: str) -> dict:
    """
    Return all temporal events for an entity node:
      - edges created/modified (grouped by year)
      - node versions
    Source: LKG database — all events are observed, not inferred.
    """
    node = await db.lkg_nodes.find_one({"node_id": node_id}, {"_id": 0})
    if not node:
        return {"node_id": node_id, "found": False, "events": []}

    # All edges involving this node
    edges = await db.lkg_edges.find(
        {"$or": [{"from_id": node_id}, {"to_id": node_id}]},
        {"_id": 0, "from_id": 1, "to_id": 1, "type": 1, "created_at": 1, "status": 1, "source": 1}
    ).sort("created_at", 1).to_list(500)

    # Group by year
    by_year: dict[int, list[dict]] = defaultdict(list)
    for edge in edges:
        dt = edge.get("created_at")
        if isinstance(dt, datetime):
            year = dt.year
        else:
            year = datetime.now(timezone.utc).year
        by_year[year].append({
            "type":        edge["type"],
            "other_node":  edge["to_id"] if edge["from_id"] == node_id else edge["from_id"],
            "direction":   "out" if edge["from_id"] == node_id else "in",
            "status":      edge.get("status", "verified"),
            "source":      edge.get("source", "unknown"),
            "date":        dt.isoformat() if isinstance(dt, datetime) else None,
        })

    timeline = [
        {"year": year, "events": events, "event_count": len(events)}
        for year, events in sorted(by_year.items())
    ]

    return {
        "node_id":      node_id,
        "label":        node.get("label"),
        "type":         node.get("type"),
        "found":        True,
        "timeline":     timeline,
        "total_events": len(edges),
        "first_event":  min((e.get("created_at") for e in edges if e.get("created_at")), default=None),
        "last_event":   max((e.get("created_at") for e in edges if e.get("created_at")), default=None),
        "source":       "Synaptiq LKG database — observed events only",
    }


async def graph_snapshot(db, year: Optional[int] = None, month: Optional[int] = None) -> dict:
    """
    Return graph statistics for a given time period.
    Used for the temporal slider — shows how the graph looked at a point in time.
    """
    q: dict = {}
    if year:
        start = datetime(year, month or 1, 1, tzinfo=timezone.utc)
        end   = datetime(year, month or 12, 28, 23, 59, 59, tzinfo=timezone.utc)
        q["created_at"] = {"$lte": end}

    node_count = await db.lkg_nodes.count_documents({"last_updated": {"$lte": q.get("created_at", {}).get("$lte", datetime.now(timezone.utc))}} if year else {})
    edge_count = await db.lkg_edges.count_documents(q if year else {})

    edge_type_pipeline = [
        *(  [{"$match": q}] if year else [] ),
        {"$group": {"_id": "$type", "count": {"$sum": 1}}},
    ]
    edge_types = {
        r["_id"]: r["count"]
        for r in await db.lkg_edges.aggregate(edge_type_pipeline).to_list(30)
    }

    return {
        "period":      {"year": year, "month": month},
        "node_count":  node_count,
        "edge_count":  edge_count,
        "edge_types":  edge_types,
        "source":      "Synaptiq LKG database",
    }


async def get_temporal_edges(db, node_id: str, year_start: int, year_end: int) -> list[dict]:
    """Return edges for a node within a time range. Used by timeline slider on frontend."""
    start = datetime(year_start, 1, 1, tzinfo=timezone.utc)
    end   = datetime(year_end, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    edges = await db.lkg_edges.find(
        {
            "$or": [{"from_id": node_id}, {"to_id": node_id}],
            "created_at": {"$gte": start, "$lte": end},
        },
        {"_id": 0}
    ).to_list(200)
    return edges
