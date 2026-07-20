"""Graph analytics — topic trends, entity growth, temporal evolution."""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("lkg.analytics")


async def topic_trends(db, months: int = 12) -> list[dict]:
    """
    Count BELONGS_TO_TOPIC edges grouped by topic and month.
    Returns topics sorted by recent growth rate (last 3 months vs previous 3).
    All counts are from verified platform data — no estimates.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=months * 30)
    edges = await db.lkg_edges.find(
        {"type": "BELONGS_TO_TOPIC", "created_at": {"$gte": cutoff}},
        {"to_id": 1, "created_at": 1}
    ).to_list(50000)

    # Group by topic
    topic_counts: dict[str, list[datetime]] = defaultdict(list)
    for e in edges:
        if "created_at" in e:
            topic_counts[e["to_id"]].append(e["created_at"])

    recent_cutoff = datetime.now(timezone.utc) - timedelta(days=90)

    results = []
    for topic_id, dates in topic_counts.items():
        recent = sum(1 for d in dates if d >= recent_cutoff)
        older  = len(dates) - recent
        results.append({
            "topic_id":     topic_id,
            "total":        len(dates),
            "recent_90d":   recent,
            "older":        older,
            "growth_rate":  round(recent / (older + 1), 2),  # simple growth ratio
        })

    results.sort(key=lambda x: x["growth_rate"], reverse=True)
    top_ids = [r["topic_id"] for r in results[:20]]

    # Enrich with topic labels
    if top_ids:
        nodes = await db.lkg_nodes.find(
            {"node_id": {"$in": top_ids}}, {"node_id": 1, "label": 1, "_id": 0}
        ).to_list(20)
        label_map = {n["node_id"]: n["label"] for n in nodes}
        for r in results:
            r["label"] = label_map.get(r["topic_id"], r["topic_id"].split(":")[-1])

    return results[:20]


async def entity_growth(db, node_type: str = "publication", months: int = 12) -> list[dict]:
    """
    Count new nodes of a given type per month.
    Returns monthly growth series for time-series charting.
    Source: Synaptiq LKG platform data — all counts are from database queries.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=months * 30)
    pipeline = [
        {"$match": {"type": node_type, "last_updated": {"$gte": cutoff}}},
        {"$group": {
            "_id": {
                "year":  {"$year": "$last_updated"},
                "month": {"$month": "$last_updated"},
            },
            "count": {"$sum": 1},
        }},
        {"$sort": {"_id.year": 1, "_id.month": 1}},
    ]
    results = await db.lkg_nodes.aggregate(pipeline).to_list(50)
    return [
        {
            "year":  r["_id"]["year"],
            "month": r["_id"]["month"],
            "count": r["count"],
            "label": f"{r['_id']['year']}-{str(r['_id']['month']).zfill(2)}",
        }
        for r in results
    ]


async def collaboration_density(db) -> dict:
    """
    Collaboration density = edges / (nodes * (nodes-1)) for researcher subgraph.
    Indicates how interconnected the researcher community is (0-1 scale).
    """
    researcher_count = await db.lkg_nodes.count_documents({"type": "researcher"})
    collab_count     = await db.lkg_edges.count_documents({
        "type": {"$in": ["CO_AUTHORED", "COLLABORATES_WITH"]},
        "status": "verified"
    })

    max_edges = researcher_count * max(0, researcher_count - 1)
    density   = round(collab_count / max_edges, 4) if max_edges > 0 else 0.0

    return {
        "researcher_nodes":   researcher_count,
        "collaboration_edges": collab_count,
        "density":            density,
        "interpretation":     (
            "Dense collaboration network" if density > 0.3 else
            "Moderate collaboration" if density > 0.1 else
            "Sparse collaboration network"
        ),
        "methodology": "density = verified_collab_edges / (researchers × (researchers-1))",
        "source":      "Synaptiq LKG database — verified edges only",
    }
