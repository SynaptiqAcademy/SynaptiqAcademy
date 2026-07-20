"""Deterministic citation trend analytics."""
from __future__ import annotations

import math
from typing import Any

from ..statistics.stats_engine import StatsEngine
from ..calculators.h_index import calculate_h_index, calculate_g_index, calculate_i10_index


def compute_citation_trends(
    snapshots: list[dict],
    period: str = "month",
) -> dict[str, Any]:
    """Compute citation accumulation trend from time-stamped snapshots.

    snapshots: list of {date, value} dicts — total citation count at a point in time.
    """
    if not snapshots:
        return {"total": 0, "periods": [], "trend": None, "growth_rate": None}

    ordered = sorted(snapshots, key=lambda x: x.get("date", ""))
    aggregated = StatsEngine.time_series_aggregate(ordered, period=period)
    counts = [a["sum"] for a in aggregated]
    trend = StatsEngine.linear_trend(counts) if len(counts) >= 3 else None
    growth = StatsEngine.growth_rate(counts[-2], counts[-1]) if len(counts) >= 2 else None

    return {
        "total_current": ordered[-1].get("value", 0) if ordered else 0,
        "periods": aggregated,
        "trend": trend,
        "growth_rate_pct": growth,
        "moving_avg_3": StatsEngine.moving_average(counts, 3)[-3:] if len(counts) >= 3 else counts,
    }


def compute_citation_velocity(
    snapshots: list[dict],
    window_days: int = 90,
) -> dict[str, Any]:
    """Compute recent citation velocity (new citations in last N days)."""
    from ..utils.date_utils import days_ago, parse_date
    cutoff = days_ago(window_days)

    total_start = 0
    total_end   = 0
    recent_pubs: list[dict] = []

    for snap in snapshots:
        dt = parse_date(snap.get("date"))
        if dt is None:
            continue
        val = float(snap.get("value") or 0)
        if dt < cutoff:
            total_start = max(total_start, val)
        else:
            total_end = max(total_end, val)
            recent_pubs.append(snap)

    delta = max(0.0, total_end - total_start)
    velocity = delta / window_days

    return {
        "window_days": window_days,
        "citations_gained": round(delta),
        "citations_per_day": round(velocity, 3),
        "citations_per_month": round(velocity * 30, 1),
    }


def compute_per_publication_stats(publications: list[dict]) -> dict[str, Any]:
    """Citation summary per publication."""
    citation_counts = [int(p.get("citation_count") or p.get("cited_by") or 0)
                       for p in publications]
    if not citation_counts:
        return {
            "h_index": 0, "g_index": 0, "i10_index": 0,
            "total": 0, "mean": 0, "max": 0, "median": 0,
        }
    return {
        "h_index": calculate_h_index(citation_counts),
        "g_index": calculate_g_index(citation_counts),
        "i10_index": calculate_i10_index(citation_counts),
        "total": sum(citation_counts),
        "mean": round(StatsEngine.mean(citation_counts), 2),
        "median": round(StatsEngine.median(citation_counts), 1),
        "max": max(citation_counts),
        "std_dev": round(StatsEngine.std_dev(citation_counts), 2),
        "p75": round(StatsEngine.percentile(citation_counts, 75), 1),
        "uncited_pct": round(
            sum(1 for c in citation_counts if c == 0) / len(citation_counts) * 100, 1
        ),
    }


def compute_citation_milestones(total_citations: int) -> dict[str, Any]:
    """Return the next citation milestone and progress toward it."""
    milestones = [10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000]
    current = total_citations
    next_milestone = next((m for m in milestones if m > current), None)
    prev_milestone = next((m for m in reversed(milestones) if m <= current), 0)

    if next_milestone:
        progress = (current - prev_milestone) / (next_milestone - prev_milestone)
    else:
        progress = 1.0

    achieved = [m for m in milestones if m <= current]
    return {
        "total": current,
        "next_milestone": next_milestone,
        "prev_milestone": prev_milestone,
        "progress_pct": round(progress * 100, 1),
        "milestones_achieved": achieved,
        "next_milestone_gap": (next_milestone - current) if next_milestone else 0,
    }
