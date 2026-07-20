"""Institution Analytics — Benchmarking Engine.

Compares an institution's KPIs against all other institutions on the platform,
computing percentiles, identifying strengths and improvement areas.
"""
from __future__ import annotations

import asyncio
from typing import Any


async def benchmark_institution(institution_id: str, db) -> dict:
    """Compare this institution against all peers using cached KPI data."""
    # Get this institution's KPIs and all peer KPIs in parallel
    own_kpis_doc, peer_docs, top_institutions = await asyncio.gather(
        db.institution_kpis.find_one({"institution_id": institution_id}),
        db.institution_kpis.find(
            {"institution_id": {"$ne": institution_id}},
            {
                "institution_id": 1,
                "total_publications": 1,
                "total_citations": 1,
                "grant_success_rate": 1,
                "avg_impact_score": 1,
            },
        ).to_list(5000),
        db.institution_impact.find(
            {},
            {"institution_id": 1, "iis_total": 1},
        ).sort("iis_total", -1).limit(5).to_list(5),
    )

    own_kpis: dict[str, Any] = {}
    if own_kpis_doc:
        own_kpis_doc.pop("_id", None)
        own_kpis_doc.pop("cached_at", None)
        own_kpis = own_kpis_doc

    peer_count = len(peer_docs)

    metrics_config = [
        ("publications", "total_publications"),
        ("citations", "total_citations"),
        ("grants", "grant_success_rate"),
        ("impact", "avg_impact_score"),
    ]

    percentiles: dict[str, float] = {}
    strengths: list[str] = []
    improvement_areas: list[str] = []

    for label, field in metrics_config:
        own_value = float(own_kpis.get(field, 0) or 0)
        lower_count = sum(
            1 for p in peer_docs
            if float(p.get(field, 0) or 0) < own_value
        )
        pct = round((lower_count / max(peer_count - 1, 1)) * 100, 1) if peer_count > 1 else 50.0
        percentiles[label] = pct
        if pct > 75:
            strengths.append(label)
        elif pct < 25:
            improvement_areas.append(label)

    top_institutions_clean = [
        {"institution_id": t.get("institution_id", ""), "iis_total": t.get("iis_total", 0)}
        for t in top_institutions
    ]

    return {
        "institution_kpis": own_kpis,
        "percentiles": percentiles,
        "peer_count": peer_count,
        "strengths": strengths,
        "improvement_areas": improvement_areas,
        "top_institutions": top_institutions_clean,
    }


async def get_global_benchmarks(db) -> dict:
    """Compute platform-wide averages and quartiles across all institution KPIs."""
    all_docs = await db.institution_kpis.find(
        {},
        {
            "total_publications": 1,
            "total_citations": 1,
            "grant_success_rate": 1,
            "avg_impact_score": 1,
            "total_members": 1,
        },
    ).to_list(10000)

    if not all_docs:
        return {
            "institution_count": 0,
            "averages": {},
            "medians": {},
            "top_quartile_thresholds": {},
        }

    n = len(all_docs)
    fields = [
        "total_publications",
        "total_citations",
        "grant_success_rate",
        "avg_impact_score",
        "total_members",
    ]

    averages: dict[str, float] = {}
    medians: dict[str, float] = {}
    top_quartile: dict[str, float] = {}

    for field in fields:
        values = sorted(float(d.get(field, 0) or 0) for d in all_docs)
        avg = sum(values) / max(n, 1)
        averages[field] = round(avg, 2)

        mid = n // 2
        if n % 2 == 0 and n > 1:
            median = (values[mid - 1] + values[mid]) / 2
        else:
            median = values[mid]
        medians[field] = round(median, 2)

        q3_idx = int(n * 0.75)
        top_quartile[field] = round(values[min(q3_idx, n - 1)], 2)

    return {
        "institution_count": n,
        "averages": averages,
        "medians": medians,
        "top_quartile_thresholds": top_quartile,
    }
