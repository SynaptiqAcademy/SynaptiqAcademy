"""Institution Intelligence Engine — Organizational Intelligence (Phase XV).

Detects underperforming departments, high performers, emerging groups,
declining areas, overloaded supervisors, inactive/high-potential researchers, etc.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from .models import InstitutionInput, OrganizationalInsight, RiskLevel


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


# ── Department-level detectors ────────────────────────────────────────────────

def _department_insights(inp: InstitutionInput) -> list[OrganizationalInsight]:
    insights: list[OrganizationalInsight] = []
    dept_map: dict[str, list[dict]] = defaultdict(list)
    for r in inp.researchers:
        dept = r.get("department") or r.get("faculty") or "General"
        dept_map[dept].append(r)

    global_pub_per_r = sum(_si(r.get("publication_count", 0)) for r in inp.researchers) / max(len(inp.researchers), 1)

    for dept, members in dept_map.items():
        n   = len(members)
        pub = sum(_si(r.get("publication_count", 0)) for r in members)
        h   = _mean([_sf(r.get("h_index", 0)) for r in members])
        pub_per_r = pub / max(n, 1)

        if pub_per_r > global_pub_per_r * 1.5 and h > 8:
            insights.append(OrganizationalInsight(
                insight_type="high_performing_department",
                entity_id=dept, entity_name=dept,
                severity=RiskLevel.MINIMAL,
                message=f"Department '{dept}' is a high performer: {pub_per_r:.1f} pubs/researcher, avg h-index {h:.1f}.",
                evidence=[f"Publications per researcher: {pub_per_r:.1f}", f"Average h-index: {h:.1f}"],
                recommendation="Invest further; use as model for other departments.",
                confidence=0.85,
            ))
        elif pub_per_r < global_pub_per_r * 0.5 and n > 2:
            insights.append(OrganizationalInsight(
                insight_type="underperforming_department",
                entity_id=dept, entity_name=dept,
                severity=RiskLevel.HIGH,
                message=f"Department '{dept}' publishes at {pub_per_r:.1f} pubs/researcher — below institutional average ({global_pub_per_r:.1f}).",
                evidence=[f"Publications per researcher: {pub_per_r:.1f}",
                          f"Institutional average: {global_pub_per_r:.1f}"],
                recommendation="Schedule strategic review; investigate workload and support needs.",
                confidence=0.8,
            ))

    return insights


# ── Researcher-level detectors ────────────────────────────────────────────────

def _researcher_insights(inp: InstitutionInput) -> list[OrganizationalInsight]:
    insights: list[OrganizationalInsight] = []
    n      = len(inp.researchers)
    h_vals = [_sf(r.get("h_index", 0)) for r in inp.researchers]
    avg_h  = _mean(h_vals)
    pub_vals = [_si(r.get("publication_count", 0)) for r in inp.researchers]
    avg_pub  = _mean([float(p) for p in pub_vals])

    for r in inp.researchers:
        rid   = str(r.get("_id") or r.get("id") or "")
        name  = r.get("full_name") or r.get("name") or rid
        h     = _sf(r.get("h_index", 0))
        pubs  = _si(r.get("publication_count", 0))
        pos   = (r.get("position") or "").lower()
        avail = _sf(r.get("availability", 1.0))

        # Inactive researcher
        if pubs == 0:
            insights.append(OrganizationalInsight(
                insight_type="inactive_researcher",
                entity_id=rid, entity_name=name,
                severity=RiskLevel.MEDIUM,
                message=f"{name} has no recorded publications.",
                evidence=["Publication count: 0"],
                recommendation="Engage with researcher to understand barriers; consider mentoring or workload review.",
                confidence=0.75,
            ))

        # High-potential (early career, above average)
        elif ("student" in pos or "postdoc" in pos or "early" in pos or "junior" in pos) and pubs > avg_pub * 1.5:
            insights.append(OrganizationalInsight(
                insight_type="high_potential_researcher",
                entity_id=rid, entity_name=name,
                severity=RiskLevel.MINIMAL,
                message=f"{name} is an early-career researcher outperforming peers ({pubs} pubs, h={h:.0f}).",
                evidence=[f"Publications: {pubs} (avg={avg_pub:.1f})", f"h-index: {h:.0f}"],
                recommendation="Offer mentoring, conference funding, and research leadership opportunities.",
                confidence=0.80,
            ))

        # Future academic leader
        if h > avg_h * 1.8 and pubs > avg_pub * 1.5:
            insights.append(OrganizationalInsight(
                insight_type="future_academic_leader",
                entity_id=rid, entity_name=name,
                severity=RiskLevel.MINIMAL,
                message=f"{name} shows characteristics of a future academic leader (h={h:.0f}, {pubs} pubs).",
                evidence=[f"h-index: {h:.0f} vs avg {avg_h:.1f}", f"Publications: {pubs}"],
                recommendation="Fast-track for leadership development; include in succession planning.",
                confidence=0.78,
            ))

        # Overloaded supervisor
        supervision_count = _si(r.get("supervision_count") or r.get("phd_students", 0))
        if supervision_count > 8:
            insights.append(OrganizationalInsight(
                insight_type="overloaded_supervisor",
                entity_id=rid, entity_name=name,
                severity=RiskLevel.HIGH,
                message=f"{name} is supervising {supervision_count} PhD candidates — above recommended threshold (8).",
                evidence=[f"PhD supervision count: {supervision_count}"],
                recommendation="Redistribute doctoral candidates; monitor completion rates.",
                confidence=0.85,
            ))

        # Retention risk (low availability + high performer)
        if avail < 0.3 and h > avg_h:
            insights.append(OrganizationalInsight(
                insight_type="retention_risk",
                entity_id=rid, entity_name=name,
                severity=RiskLevel.HIGH,
                message=f"{name} has high impact (h={h:.0f}) but very low availability — potential retention risk.",
                evidence=[f"Availability score: {avail:.2f}", f"h-index: {h:.0f}"],
                recommendation="Check workload; proactively offer support and career development.",
                confidence=0.70,
            ))

    return insights


# ── Research area detectors ───────────────────────────────────────────────────

def _area_insights(inp: InstitutionInput) -> list[OrganizationalInsight]:
    insights: list[OrganizationalInsight] = []

    area_map: dict[str, int] = defaultdict(int)
    for r in inp.researchers:
        for area in (r.get("research_areas") or r.get("domains") or []):
            if area:
                area_map[str(area).lower()] += 1

    if not area_map:
        return insights

    total = sum(area_map.values())
    avg   = total / max(len(area_map), 1)

    for area, count in area_map.items():
        if count > avg * 2:
            insights.append(OrganizationalInsight(
                insight_type="emerging_research_area",
                entity_id=area, entity_name=area.title(),
                severity=RiskLevel.MINIMAL,
                message=f"Research area '{area.title()}' has disproportionately high researcher density.",
                evidence=[f"Researcher count: {count}", f"Mean per area: {avg:.1f}"],
                recommendation="Formalise this area as an institutional strategic priority.",
                confidence=0.72,
            ))
        elif count == 1 and total > 10:
            insights.append(OrganizationalInsight(
                insight_type="declining_research_area",
                entity_id=area, entity_name=area.title(),
                severity=RiskLevel.LOW,
                message=f"Research area '{area.title()}' has only 1 researcher — fragile coverage.",
                evidence=[f"Researcher count: 1"],
                recommendation="Recruit or cross-train additional researchers; or consolidate with adjacent areas.",
                confidence=0.65,
            ))

    return insights


# ── Collaboration bottleneck detectors ────────────────────────────────────────

def _bottleneck_insights(inp: InstitutionInput) -> list[OrganizationalInsight]:
    insights: list[OrganizationalInsight] = []

    collab_vals = [_sf(r.get("international_collab_ratio", 0)) for r in inp.researchers]
    avg_intl = _mean(collab_vals)

    if avg_intl < 0.1 and len(inp.researchers) > 5:
        insights.append(OrganizationalInsight(
            insight_type="collaboration_bottleneck",
            entity_id="institution",
            entity_name="Institution-wide",
            severity=RiskLevel.MEDIUM,
            message=f"International collaboration ratio is very low ({avg_intl:.1%}) — institution risks research isolation.",
            evidence=[f"Avg international collab ratio: {avg_intl:.1%}"],
            recommendation="Set international partnership targets; fund researcher mobility programs.",
            confidence=0.80,
        ))

    # Funding gap detection
    funded = sum(1 for r in inp.researchers if _si(r.get("grant_count", 0)) > 0)
    n = len(inp.researchers)
    funded_ratio = funded / max(n, 1)
    if funded_ratio < 0.2 and n > 5:
        insights.append(OrganizationalInsight(
            insight_type="funding_gap",
            entity_id="institution",
            entity_name="Institution-wide",
            severity=RiskLevel.HIGH,
            message=f"Only {funded_ratio:.0%} of researchers have active grants — significant funding gap.",
            evidence=[f"Funded researchers: {funded}/{n}"],
            recommendation="Invest in grant writing support; target EU and national research grants.",
            confidence=0.82,
        ))

    return insights


# ── Public function ───────────────────────────────────────────────────────────

def detect_organizational_insights(inp: InstitutionInput) -> list[OrganizationalInsight]:
    """Detect all organizational intelligence insights from InstitutionInput."""
    insights: list[OrganizationalInsight] = []
    insights.extend(_department_insights(inp))
    insights.extend(_researcher_insights(inp))
    insights.extend(_area_insights(inp))
    insights.extend(_bottleneck_insights(inp))
    # Sort: critical first
    level_order = {
        RiskLevel.CRITICAL: 0, RiskLevel.HIGH: 1, RiskLevel.MEDIUM: 2,
        RiskLevel.LOW: 3, RiskLevel.MINIMAL: 4,
    }
    return sorted(insights, key=lambda i: level_order.get(i.severity, 5))
