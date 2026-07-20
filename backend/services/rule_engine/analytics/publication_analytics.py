"""Deterministic publication trend analytics."""
from __future__ import annotations

from typing import Any

from ..statistics.stats_engine import StatsEngine
from ..utils.date_utils import parse_date, format_period, utcnow


def compute_publication_trends(
    publications: list[dict],
    period: str = "year",
    date_field: str = "published_at",
) -> dict[str, Any]:
    """Compute publication output over time with trend analysis."""
    if not publications:
        return {"total": 0, "periods": [], "trend": None, "growth_rate": None}

    # Build time-series
    points = []
    for p in publications:
        dt = parse_date(p.get(date_field))
        if dt:
            points.append({"date": dt.isoformat(), "value": 1})

    aggregated = StatsEngine.time_series_aggregate(points, period=period)

    counts = [a["sum"] for a in aggregated]
    trend = StatsEngine.linear_trend(counts) if len(counts) >= 3 else None
    growth = StatsEngine.growth_rate(counts[-2], counts[-1]) if len(counts) >= 2 else None

    # Type breakdown
    type_counts: dict[str, int] = {}
    for p in publications:
        t = p.get("manuscript_type") or p.get("type") or "unknown"
        type_counts[t] = type_counts.get(t, 0) + 1

    # Status breakdown
    status_counts: dict[str, int] = {}
    for p in publications:
        s = p.get("status") or "unknown"
        status_counts[s] = status_counts.get(s, 0) + 1

    return {
        "total": len(publications),
        "periods": aggregated,
        "trend": trend,
        "growth_rate_pct": growth,
        "type_breakdown": type_counts,
        "status_breakdown": status_counts,
        "peak_period": max(aggregated, key=lambda x: x["sum"])["period"] if aggregated else None,
        "avg_per_period": round(StatsEngine.mean(counts), 2) if counts else 0.0,
    }


def compute_productivity_rate(
    publications: list[dict],
    career_start_year: int | None = None,
    date_field: str = "published_at",
) -> dict[str, Any]:
    """Publications per year over the researcher's career."""
    if not publications or not career_start_year:
        return {"rate_per_year": 0.0, "career_years": 0, "total": len(publications)}

    current_year = utcnow().year
    career_years = max(current_year - career_start_year, 1)
    published = [p for p in publications if p.get("status") == "published"]

    return {
        "total_publications": len(publications),
        "published_count": len(published),
        "career_years": career_years,
        "rate_per_year": round(len(published) / career_years, 2),
        "rate_total_per_year": round(len(publications) / career_years, 2),
    }


def compute_collaboration_patterns(publications: list[dict]) -> dict[str, Any]:
    """Analyze co-authorship patterns across publications."""
    total = len(publications)
    if not total:
        return {"solo_pct": 0, "collaborative_pct": 0, "avg_authors": 0}

    author_counts = [int(p.get("author_count") or len(p.get("authors") or [1])) for p in publications]
    solo = sum(1 for c in author_counts if c <= 1)
    collaborative = total - solo
    international = sum(1 for p in publications if p.get("international_collaboration"))

    return {
        "total": total,
        "solo_count": solo,
        "collaborative_count": collaborative,
        "solo_pct": round(solo / total * 100, 1),
        "collaborative_pct": round(collaborative / total * 100, 1),
        "avg_authors_per_pub": round(StatsEngine.mean(author_counts), 1),
        "max_authors": max(author_counts, default=0),
        "international_collab_count": international,
        "international_collab_pct": round(international / total * 100, 1),
    }
