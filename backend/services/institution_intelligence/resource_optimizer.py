"""Institution Intelligence Engine — Resource Optimization (Phase XV).

Recommends optimal allocation of grants, equipment, labs, staffing, etc.
"""
from __future__ import annotations

from collections import defaultdict

from .models import InstitutionInput, InstitutionKPIs, ResourceAllocation


def _sf(v, d: float = 0.0) -> float:
    try:
        return float(v) if v is not None else d
    except (TypeError, ValueError):
        return d


def _mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def _alloc(
    category: str, target: str,
    current: float, recommended: float,
    reasoning: str, roi: float = 0.5, priority: str = "medium",
) -> ResourceAllocation:
    change = "increase" if recommended > current else ("decrease" if recommended < current else "maintain")
    return ResourceAllocation(
        category=category, target=target,
        current_allocation=current, recommended_allocation=recommended,
        change_direction=change, reasoning=reasoning,
        expected_roi=roi, priority=priority,
    )


def optimise_resources(inp: InstitutionInput, kpis: InstitutionKPIs) -> list[ResourceAllocation]:
    """Generate resource allocation recommendations."""
    allocs: list[ResourceAllocation] = []
    n = max(len(inp.researchers), 1)
    total_grants = len(inp.grants)

    # ── Grant allocation ──────────────────────────────────────────────────────
    dept_map: dict[str, list[float]] = defaultdict(list)
    for r in inp.researchers:
        dept = r.get("department") or "General"
        dept_map[dept].append(_sf(r.get("h_index", 0)))

    if dept_map:
        avg_h = {d: _mean(h) for d, h in dept_map.items()}
        top_dept = max(avg_h, key=avg_h.get)
        bottom_dept = min(avg_h, key=avg_h.get)
        allocs.append(_alloc(
            "grant_allocation", top_dept,
            current=0.0, recommended=0.35,
            reasoning=f"'{top_dept}' has highest research impact (avg h={avg_h[top_dept]:.1f}). Concentrate resources for maximum ROI.",
            roi=0.85, priority="high",
        ))
        if bottom_dept != top_dept:
            allocs.append(_alloc(
                "capacity_building", bottom_dept,
                current=0.0, recommended=0.20,
                reasoning=f"'{bottom_dept}' shows potential but needs investment (avg h={avg_h[bottom_dept]:.1f}).",
                roi=0.55, priority="medium",
            ))

    # ── Laboratory utilization ────────────────────────────────────────────────
    lab_utilisation = _sf(inp.metadata.get("lab_utilisation_ratio", 0.6))
    if lab_utilisation < 0.7:
        allocs.append(_alloc(
            "laboratory_utilization", "Shared Research Laboratories",
            current=lab_utilisation, recommended=0.80,
            reasoning="Under-utilised labs represent wasted capital investment. Introduce shared booking system.",
            roi=0.65, priority="medium",
        ))

    # ── Research staffing ─────────────────────────────────────────────────────
    phd_count = sum(1 for r in inp.researchers if "phd" in (r.get("position") or "").lower())
    phd_ratio = phd_count / n
    if phd_ratio < 0.15:
        allocs.append(_alloc(
            "research_staffing", "PhD Candidate Recruitment",
            current=phd_ratio, recommended=0.20,
            reasoning="Increasing PhD density drives publication output and innovation at lower cost.",
            roi=0.70, priority="high",
        ))

    # ── International partnerships ────────────────────────────────────────────
    intl = kpis.internationalization_score
    if intl < 0.25:
        allocs.append(_alloc(
            "international_partnerships", "International Collaboration Funding",
            current=intl, recommended=0.30,
            reasoning="International co-authorship increases citation impact by 35-50%.",
            roi=0.80, priority="high",
        ))

    # ── Training priorities ────────────────────────────────────────────────────
    if kpis.grant_success_rate < 0.35:
        allocs.append(_alloc(
            "training", "Grant Writing Training Programme",
            current=0.0, recommended=0.10,
            reasoning="Grant writing training raises success rate by 15-25%; high ROI investment.",
            roi=0.90, priority="critical",
        ))

    # ── Industry partnerships ─────────────────────────────────────────────────
    if kpis.innovation_score < 0.25:
        allocs.append(_alloc(
            "industry_partnerships", "Industry Co-Innovation Fund",
            current=kpis.innovation_score, recommended=0.30,
            reasoning="Industry co-funding diversifies income and accelerates technology transfer.",
            roi=0.72, priority="medium",
        ))

    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    return sorted(allocs, key=lambda a: priority_order.get(a.priority, 4))
