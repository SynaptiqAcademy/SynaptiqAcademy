"""Trend discovery — emerging topics, declining areas, growth velocity."""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone, timedelta

from lkg.unified import get_unified_graph


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cutoff(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


async def discover_emerging_topics(db, window_days: int = 30, top_n: int = 15) -> list[dict]:
    """Topics whose entities grew fastest in the last `window_days`."""
    recent_cutoff = _cutoff(window_days)
    older_cutoff  = _cutoff(window_days * 2)
    unified       = get_unified_graph()

    type_filter = ["topic", "research_area", "keyword"]

    recent_agg, older_agg = await asyncio.gather(
        unified.aggregate_nodes_by_label_and_filter(
            db,
            lkg_match={"type": {"$in": type_filter}, "created_at": {"$gte": recent_cutoff}},
            akg_match={"entity_type": {"$in": type_filter}, "created_at": {"$gte": recent_cutoff}},
        ),
        unified.aggregate_nodes_by_label_and_filter(
            db,
            lkg_match={"type": {"$in": type_filter},
                       "created_at": {"$gte": older_cutoff, "$lt": recent_cutoff}},
            akg_match={"entity_type": {"$in": type_filter},
                       "created_at": {"$gte": older_cutoff, "$lt": recent_cutoff}},
        ),
    )

    recent_map = {item["_id"]: item["count"] for item in recent_agg}
    older_map  = {item["_id"]: item["count"] for item in older_agg}

    trends = []
    for label, recent_count in recent_map.items():
        older_count = older_map.get(label, 0)
        growth = (recent_count - older_count) / max(older_count, 1) * 100
        trends.append({
            "label":        label,
            "recent_count": recent_count,
            "older_count":  older_count,
            "growth_rate":  round(growth, 1),
            "trend":        "emerging" if growth > 50 else "stable" if growth > 0 else "declining",
        })

    trends.sort(key=lambda x: x["growth_rate"], reverse=True)
    return trends[:top_n]


async def discover_hot_research_areas(db, top_n: int = 10) -> list[dict]:
    """Research areas with the most new relationships added recently."""
    try:
        return await get_unified_graph().discover_hot_research_areas(db, top_n=top_n, days=30)
    except Exception:
        return []


async def get_institutional_growth(db, top_n: int = 10) -> list[dict]:
    """Institutions gaining the most new researcher affiliations."""
    return await get_unified_graph().get_institutional_growth(db, top_n=top_n)


async def get_collaboration_trends(db) -> dict:
    """Monthly collaboration creation counts for the last 6 months."""
    return await get_unified_graph().get_collaboration_trends(db)


async def get_full_trend_report(db) -> dict:
    emerging, hot_areas, inst_growth, collab_trend = await asyncio.gather(
        discover_emerging_topics(db),
        discover_hot_research_areas(db),
        get_institutional_growth(db),
        get_collaboration_trends(db),
    )
    return {
        "emerging_topics":      emerging,
        "hot_research_areas":   hot_areas,
        "institutional_growth": inst_growth,
        "collaboration_trends": collab_trend,
        "generated_at":         _now(),
    }
