"""Research Area Impact Aggregator.

Groups a user's publications by OpenAlex concepts / topics, then computes
per-area metrics: total citations, average, growth rate, and a topic impact
score. Used by GET /api/citations/research-areas.
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional


def _now_year() -> int:
    return datetime.now(timezone.utc).year


def _area_impact_score(
    total_citations: int,
    pub_count: int,
    growth_rate: float,
) -> float:
    """Simple 0–100 score for a research area. Not the same as the user composite."""
    volume   = min(100.0, 100.0 * (1.0 - math.exp(-math.log1p(total_citations) / 3.5)))
    breadth  = min(100.0, pub_count * 12.5)   # 8 pubs = max
    momentum = min(100.0, max(0.0, growth_rate * 2.0))  # 50% growth = max
    return round(0.50 * volume + 0.30 * breadth + 0.20 * momentum, 1)


def aggregate_research_areas(
    publications: list[dict],
    snapshots: list[dict],
) -> list[dict]:
    """Compute per-research-area citation metrics.

    Args:
        publications: raw docs from db.publications with keys:
                      id, title, year, citations, concepts, topics
        snapshots:    latest snapshot per publication from publication_citations:
                      {pub_id, delta, count, prev_count}

    Returns list of area dicts sorted by total_citations desc.
    """
    current_year = _now_year()

    # index snapshots by pub_id for O(1) lookup
    snap_by_pub: dict[str, dict] = {}
    for s in snapshots:
        pub_id = s.get("pub_id") or s.get("_id")
        if pub_id and pub_id not in snap_by_pub:
            snap_by_pub[str(pub_id)] = s

    # group by area label
    areas: dict[str, dict] = defaultdict(lambda: {
        "publications":      [],
        "total_citations":   0,
        "total_delta":       0,
        "prev_total":        0,
        "year_citations":    {},
    })

    for p in publications:
        pub_id  = str(p.get("id") or p.get("_id") or "")
        cites   = int(p.get("citations") or 0)
        yr      = p.get("year")
        snap    = snap_by_pub.get(pub_id) or {}
        delta   = int(snap.get("delta") or 0)
        prev    = int(snap.get("prev_count") or 0)

        # use topics first, fall back to concepts
        labels = list(p.get("topics") or []) + list(p.get("concepts") or [])
        if not labels:
            labels = ["Uncategorised"]

        # weight concepts by order (first concept = primary area)
        for i, label in enumerate(labels[:3]):
            bucket = areas[label]
            bucket["publications"].append(pub_id)
            bucket["total_citations"]  += cites
            bucket["total_delta"]      += delta
            bucket["prev_total"]       += prev
            if yr and isinstance(yr, int):
                bucket["year_citations"][yr] = bucket["year_citations"].get(yr, 0) + cites

    results = []
    for label, bucket in areas.items():
        pub_count  = len(set(bucket["publications"]))
        total_cit  = bucket["total_citations"]
        total_del  = bucket["total_delta"]
        prev_tot   = bucket["prev_total"]
        yc         = bucket["year_citations"]

        avg_cit = round(total_cit / max(1, pub_count), 1)

        # growth rate: delta / previous total
        if prev_tot > 0:
            growth_rate = round((total_del / prev_tot) * 100, 1)
        else:
            growth_rate = 0.0

        # recent vs old trend (compare last 3 years vs prior 3 years)
        if yc:
            recent_yrs = sorted(yc.keys())[-3:]
            older_yrs  = sorted(yc.keys())[:-3] if len(yc) > 3 else []
            recent_sum = sum(yc[y] for y in recent_yrs)
            older_sum  = sum(yc[y] for y in older_yrs) if older_yrs else 0
            if older_sum > 0:
                trend_ratio = (recent_sum - older_sum) / older_sum
            elif recent_sum > 0:
                trend_ratio = 1.0
            else:
                trend_ratio = 0.0
        else:
            trend_ratio = 0.0

        # classify trend
        if trend_ratio > 0.5:
            trend = "rising"
        elif trend_ratio > 0.0:
            trend = "growing"
        elif trend_ratio < -0.3:
            trend = "declining"
        else:
            trend = "stable"

        # emerging: few pubs but positive growth
        if pub_count <= 3 and trend_ratio > 0.2:
            trend = "emerging"

        score = _area_impact_score(total_cit, pub_count, growth_rate)

        results.append({
            "area":             label,
            "publication_count": pub_count,
            "total_citations":  total_cit,
            "avg_citations":    avg_cit,
            "growth_rate":      growth_rate,
            "trend":            trend,
            "impact_score":     score,
            "year_citations":   sorted(
                [{"year": y, "citations": c} for y, c in yc.items()],
                key=lambda x: x["year"],
            ),
        })

    results.sort(key=lambda x: x["total_citations"], reverse=True)

    # label top / fastest / declining / emerging for the UI
    if results:
        results[0]["is_top"] = True
    if len(results) >= 2:
        fastest = max(results, key=lambda x: x["growth_rate"])
        fastest["is_fastest"] = True

    return results


def classify_areas(areas: list[dict]) -> dict:
    """Split area list into UI categories: top, emerging, declining, growing."""
    top       = [a for a in areas if a.get("is_top")][:3]
    fastest   = sorted([a for a in areas if a["growth_rate"] > 0], key=lambda x: x["growth_rate"], reverse=True)[:3]
    declining = [a for a in areas if a["trend"] == "declining"][:3]
    emerging  = [a for a in areas if a["trend"] == "emerging"][:5]

    return {
        "top_areas":      top or areas[:3],
        "fastest_growing": fastest,
        "declining":       declining,
        "emerging":        emerging,
    }
