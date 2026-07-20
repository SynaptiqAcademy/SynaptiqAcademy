"""Research Collaboration Intelligence — Admin Analytics (Phase XIV).

Platform-level analytics: collaboration statistics, research communities,
international collaboration rates, interdisciplinary metrics.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .models import CollabMatch, ResearcherProfile, ResearchNetwork


def _safe_div(a: float, b: float) -> float:
    return round(a / b, 3) if b else 0.0


def platform_collaboration_stats(
    profiles: list[ResearcherProfile],
    matches: list[CollabMatch],
) -> dict:
    if not profiles:
        return {"message": "No profiles available"}

    avg_h_index  = _safe_div(sum(p.h_index for p in profiles), len(profiles))
    avg_pubs     = _safe_div(sum(p.publication_count for p in profiles), len(profiles))
    avg_collab   = _safe_div(sum(p.collaboration_count for p in profiles), len(profiles))
    avg_intl     = _safe_div(sum(p.international_collab_ratio for p in profiles), len(profiles))
    avg_impact   = _safe_div(sum(p.impact_score for p in profiles), len(profiles))

    avg_match    = _safe_div(sum(m.overall_score for m in matches), len(matches)) if matches else 0.0

    return {
        "total_researchers":          len(profiles),
        "total_match_pairs_computed": len(matches),
        "average_h_index":            round(avg_h_index, 2),
        "average_publications":       round(avg_pubs, 1),
        "average_collaboration_count": round(avg_collab, 1),
        "average_international_ratio": round(avg_intl, 3),
        "average_impact_score":        round(avg_impact, 3),
        "average_compatibility_score": round(avg_match, 3),
    }


def top_collaborators(
    profiles: list[ResearcherProfile],
    top_n: int = 10,
) -> list[dict]:
    ranked = sorted(profiles, key=lambda p: -(p.collaboration_count + p.impact_score))
    return [
        {
            "user_id":             p.user_id,
            "name":                p.name,
            "institution":         p.institution,
            "collaboration_count": p.collaboration_count,
            "impact_score":        round(p.impact_score, 3),
            "h_index":             p.h_index,
            "international_ratio": round(p.international_collab_ratio, 3),
        }
        for p in ranked[:top_n]
    ]


def top_institutions(
    profiles: list[ResearcherProfile],
    top_n: int = 10,
) -> list[dict]:
    inst_stats: dict[str, dict] = defaultdict(lambda: {
        "count": 0, "total_impact": 0.0, "total_h": 0.0, "countries": set(),
    })

    for p in profiles:
        if p.institution:
            s = inst_stats[p.institution]
            s["count"]        += 1
            s["total_impact"] += p.impact_score
            s["total_h"]      += p.h_index
            s["countries"].add(p.country)

    result = [
        {
            "institution":    inst,
            "researcher_count": s["count"],
            "avg_impact":      _safe_div(s["total_impact"], s["count"]),
            "avg_h_index":     round(_safe_div(s["total_h"], s["count"]), 2),
            "countries_covered": len(s["countries"]),
        }
        for inst, s in inst_stats.items()
    ]
    return sorted(result, key=lambda x: -(x["researcher_count"] * x["avg_impact"]))[:top_n]


def research_communities(network: ResearchNetwork) -> list[dict]:
    return sorted(network.clusters, key=lambda c: -c["size"])[:10]


def international_collaboration_map(profiles: list[ResearcherProfile]) -> dict:
    country_counts: Counter = Counter()
    country_intl_sum: dict[str, float] = defaultdict(float)
    country_n: dict[str, int] = defaultdict(int)

    for p in profiles:
        if p.country:
            country_counts[p.country] += 1
            country_intl_sum[p.country] += p.international_collab_ratio
            country_n[p.country] += 1

    countries = [
        {
            "country":         c,
            "researcher_count": country_counts[c],
            "avg_intl_ratio":   _safe_div(country_intl_sum[c], country_n[c]),
        }
        for c in country_counts
    ]
    return {
        "countries": sorted(countries, key=lambda x: -x["researcher_count"]),
        "total_countries": len(country_counts),
        "most_international": max(countries, key=lambda x: x["avg_intl_ratio"])["country"]
        if countries else "",
    }


def interdisciplinary_metrics(profiles: list[ResearcherProfile]) -> dict:
    all_domains: list[str] = []
    multi_domain_researchers = 0

    for p in profiles:
        all_domains.extend(p.domains)
        if len(set(p.domains)) >= 3:
            multi_domain_researchers += 1

    domain_counts = Counter(all_domains)
    top_domains = [{"domain": d, "count": c} for d, c in domain_counts.most_common(10)]
    cross_domain_pairs: Counter = Counter()
    for p in profiles:
        unique_domains = list(set(p.domains))
        for i in range(len(unique_domains)):
            for j in range(i + 1, len(unique_domains)):
                key = tuple(sorted([unique_domains[i], unique_domains[j]]))
                cross_domain_pairs[key] += 1

    return {
        "multi_domain_researchers": multi_domain_researchers,
        "multi_domain_ratio": _safe_div(multi_domain_researchers, len(profiles)),
        "top_research_domains": top_domains,
        "top_interdisciplinary_pairs": [
            {"pair": list(pair), "count": count}
            for pair, count in cross_domain_pairs.most_common(5)
        ],
        "unique_domains": len(domain_counts),
    }


def grant_collaboration_stats(profiles: list[ResearcherProfile]) -> dict:
    with_grants = [p for p in profiles if p.competency_graph and p.competency_graph.grant_success_rate > 0]
    avg_success = _safe_div(
        sum(p.competency_graph.grant_success_rate for p in with_grants), len(with_grants)
    ) if with_grants else 0.0

    return {
        "researchers_with_grant_history": len(with_grants),
        "grant_history_ratio": _safe_div(len(with_grants), len(profiles)),
        "average_grant_success_rate": round(avg_success, 3),
    }
