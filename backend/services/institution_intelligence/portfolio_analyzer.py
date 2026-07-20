"""Institution Intelligence Engine — Research Portfolio Analyzer (Phase XV).

Evaluates research balance, maturity, diversity, and strategic alignment.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from .models import InstitutionInput, PortfolioArea


def _sf(v: Any, d: float = 0.0) -> float:
    try:
        return float(v) if v is not None else d
    except (TypeError, ValueError):
        return d


def _si(v: Any, d: int = 0) -> int:
    try:
        return int(v) if v is not None else d
    except (TypeError, ValueError):
        return d


def _mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


# Global research trends (used for alignment scoring)
_GLOBAL_TRENDS = {
    "artificial intelligence", "machine learning", "deep learning",
    "climate change", "sustainability", "green energy",
    "bioinformatics", "genomics", "precision medicine",
    "quantum computing", "cybersecurity",
    "public health", "epidemiology", "global health",
    "data science", "big data",
}

_NATIONAL_PRIORITIES = {
    "digital transformation", "smart cities", "e-health",
    "renewable energy", "water management", "food security",
}

_EU_PRIORITIES = {
    "green deal", "digital europe", "health", "inclusive growth",
    "security", "space", "food systems",
}


def _maturity(pubs: int, avg_pubs: float, researchers: int) -> str:
    share = pubs / max(avg_pubs, 1)
    if researchers <= 1:
        return "emerging"
    if share > 2.0:
        return "mature"
    if share > 1.0:
        return "growing"
    if researchers == 1:
        return "emerging"
    return "declining"


def _strategic_priority(area: str, growth: float, researchers: int) -> str:
    if area.lower() in _GLOBAL_TRENDS or area.lower() in _EU_PRIORITIES:
        return "invest"
    if growth > 0.1 and researchers >= 3:
        return "grow"
    if growth < -0.1:
        return "divest"
    return "maintain"


def _alignment(area: str) -> float:
    name = area.lower()
    score = 0.3  # baseline
    if any(t in name for t in _GLOBAL_TRENDS):
        score += 0.4
    if any(t in name for t in _EU_PRIORITIES):
        score += 0.2
    if any(t in name for t in _NATIONAL_PRIORITIES):
        score += 0.1
    return min(score, 1.0)


def analyse_portfolio(inp: InstitutionInput) -> list[PortfolioArea]:
    """Build research portfolio analysis for all detected research areas."""
    researchers = inp.researchers

    # Group researchers by research area
    area_researchers: dict[str, list[dict]] = defaultdict(list)
    for r in researchers:
        areas = r.get("research_areas") or r.get("domains") or []
        for area in areas:
            if area:
                area_researchers[str(area).lower()].append(r)

    if not area_researchers:
        return []

    # Compute avg publications per area (for relative comparison)
    total_pubs  = sum(_si(r.get("publication_count", 0)) for r in researchers)
    n_areas     = max(len(area_researchers), 1)
    avg_pubs_per_area = total_pubs / n_areas

    portfolio: list[PortfolioArea] = []
    for area, members in area_researchers.items():
        pub_count   = sum(_si(r.get("publication_count", 0)) for r in members)
        cite_count  = sum(_si(r.get("citation_count", 0)) for r in members)
        grant_count = sum(_si(r.get("grant_count", 0)) for r in members)
        n_members   = len(members)
        growth      = _mean([_sf(r.get("publication_growth", 0)) for r in members])

        portfolio.append(PortfolioArea(
            name=area.title(),
            publication_count=pub_count,
            citation_count=cite_count,
            researcher_count=n_members,
            grant_count=grant_count,
            growth_rate=round(growth, 3),
            maturity=_maturity(pub_count, avg_pubs_per_area, n_members),
            strategic_priority=_strategic_priority(area, growth, n_members),
            alignment_score=round(_alignment(area), 3),
        ))

    # Sort: invest first, then by publication count
    priority_order = {"invest": 0, "grow": 1, "maintain": 2, "divest": 3}
    return sorted(portfolio, key=lambda p: (priority_order.get(p.strategic_priority, 4), -p.publication_count))


def portfolio_summary(portfolio: list[PortfolioArea]) -> dict:
    """Return a summary view of the portfolio."""
    if not portfolio:
        return {
            "total_areas": 0,
            "invest": 0, "grow": 0, "maintain": 0, "divest": 0,
            "average_alignment": 0.0,
            "top_areas": [],
            "emerging_areas": [],
            "declining_areas": [],
        }
    invest  = sum(1 for p in portfolio if p.strategic_priority == "invest")
    grow    = sum(1 for p in portfolio if p.strategic_priority == "grow")
    maintain = sum(1 for p in portfolio if p.strategic_priority == "maintain")
    divest  = sum(1 for p in portfolio if p.strategic_priority == "divest")
    avg_align = _mean([p.alignment_score for p in portfolio])
    top     = sorted(portfolio, key=lambda p: -p.publication_count)[:5]
    emerging = [p for p in portfolio if p.maturity == "emerging"][:5]
    declining = [p for p in portfolio if p.maturity == "declining"][:5]
    return {
        "total_areas":        len(portfolio),
        "invest":             invest,
        "grow":               grow,
        "maintain":           maintain,
        "divest":             divest,
        "average_alignment":  round(avg_align, 3),
        "top_areas":          [p.to_dict() for p in top],
        "emerging_areas":     [p.to_dict() for p in emerging],
        "declining_areas":    [p.to_dict() for p in declining],
    }
