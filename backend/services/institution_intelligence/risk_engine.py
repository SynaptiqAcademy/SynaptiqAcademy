"""Institution Intelligence Engine — Risk Intelligence (Phase XV).

Identifies strategic risks across 10 risk dimensions. Pure Python.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from .models import InstitutionInput, InstitutionRisk, RiskLevel, RiskType


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


def _severity(risk_score: float) -> RiskLevel:
    if risk_score >= 0.8:
        return RiskLevel.CRITICAL
    if risk_score >= 0.6:
        return RiskLevel.HIGH
    if risk_score >= 0.4:
        return RiskLevel.MEDIUM
    if risk_score >= 0.2:
        return RiskLevel.LOW
    return RiskLevel.MINIMAL


def _risk(
    risk_type: RiskType,
    probability: float,
    impact: float,
    description: str,
    evidence: list[str],
    mitigation: str,
    entity_name: str = "Institution",
) -> InstitutionRisk:
    score = round(probability * 0.5 + impact * 0.5, 3)
    return InstitutionRisk(
        risk_type=risk_type,
        severity=_severity(score),
        entity_name=entity_name,
        description=description,
        evidence=evidence,
        mitigation=mitigation,
        probability=round(probability, 3),
        impact=round(impact, 3),
        risk_score=score,
    )


# ── Individual risk detectors ─────────────────────────────────────────────────

def _research_decline_risk(inp: InstitutionInput) -> list[InstitutionRisk]:
    risks: list[InstitutionRisk] = []
    growths = [_sf(r.get("publication_growth", 0)) for r in inp.researchers
               if r.get("publication_growth") is not None]
    if not growths:
        return risks
    avg_growth = _mean(growths)
    if avg_growth < -0.05:
        prob = min(abs(avg_growth) * 5, 1.0)
        risks.append(_risk(
            RiskType.RESEARCH_DECLINE,
            probability=prob, impact=0.8,
            description=f"Average publication growth is negative ({avg_growth:.1%}).",
            evidence=[f"Average publication growth: {avg_growth:.1%}", "Declining researcher output detected"],
            mitigation="Investigate root causes; review workload, resources, and incentives.",
        ))
    return risks


def _grant_dependency_risk(inp: InstitutionInput) -> list[InstitutionRisk]:
    risks: list[InstitutionRisk] = []
    if not inp.grants:
        return risks
    funder_map: dict[str, float] = defaultdict(float)
    for g in inp.grants:
        funder = g.get("funding_organization") or g.get("funder") or "Unknown"
        funder_map[funder] += _sf(g.get("amount", 0))
    total = sum(funder_map.values())
    if total == 0:
        return risks
    for funder, amount in funder_map.items():
        share = amount / total
        if share > 0.6:
            risks.append(_risk(
                RiskType.GRANT_DEPENDENCY,
                probability=0.75, impact=min(share, 1.0),
                description=f"Over {share:.0%} of grant income depends on a single funder: {funder}.",
                evidence=[f"Funder '{funder}': {share:.0%} of total income"],
                mitigation="Diversify funding sources; target EU, national, and industry grants.",
                entity_name=funder,
            ))
    return risks


def _publication_concentration_risk(inp: InstitutionInput) -> list[InstitutionRisk]:
    risks: list[InstitutionRisk] = []
    dept_map: dict[str, int] = defaultdict(int)
    for r in inp.researchers:
        dept = r.get("department") or "General"
        dept_map[dept] += _si(r.get("publication_count", 0))
    total = sum(dept_map.values())
    if total == 0:
        return risks
    for dept, pubs in dept_map.items():
        share = pubs / total
        if share > 0.7 and len(dept_map) > 1:
            risks.append(_risk(
                RiskType.PUBLICATION_CONCENTRATION,
                probability=0.6, impact=0.7,
                description=f"Department '{dept}' accounts for {share:.0%} of all publications.",
                evidence=[f"Publications from '{dept}': {pubs}/{total}"],
                mitigation="Invest in publication support for other departments.",
                entity_name=dept,
            ))
    return risks


def _staff_turnover_risk(inp: InstitutionInput) -> list[InstitutionRisk]:
    risks: list[InstitutionRisk] = []
    n = len(inp.researchers)
    if n < 3:
        return risks
    early_career = sum(
        1 for r in inp.researchers
        if (r.get("position") or "").lower() in ("postdoc", "junior researcher", "assistant professor")
    )
    ratio = early_career / n
    if ratio > 0.5:
        risks.append(_risk(
            RiskType.STAFF_TURNOVER,
            probability=0.65, impact=0.6,
            description=f"{ratio:.0%} of researchers are in early-career / transitional roles — high turnover risk.",
            evidence=[f"Early-career ratio: {ratio:.0%}", f"Count: {early_career}/{n}"],
            mitigation="Create tenure-track pathways; offer career development and retention packages.",
        ))
    return risks


def _isolation_risk(inp: InstitutionInput) -> list[InstitutionRisk]:
    risks: list[InstitutionRisk] = []
    intl_vals = [_sf(r.get("international_collab_ratio", 0)) for r in inp.researchers]
    avg_intl  = _mean(intl_vals)
    if avg_intl < 0.1 and len(inp.researchers) > 5:
        risks.append(_risk(
            RiskType.RESEARCH_ISOLATION,
            probability=0.70, impact=0.65,
            description=f"Institutional international collaboration ratio is critically low ({avg_intl:.1%}).",
            evidence=[f"Average international collaboration ratio: {avg_intl:.1%}"],
            mitigation="Establish international partnership targets; support mobility grants.",
        ))
    return risks


def _low_collaboration_risk(inp: InstitutionInput) -> list[InstitutionRisk]:
    risks: list[InstitutionRisk] = []
    collab_vals = [_sf(r.get("collaboration_count", 0)) for r in inp.researchers]
    avg = _mean(collab_vals)
    if avg < 2 and len(inp.researchers) > 3:
        risks.append(_risk(
            RiskType.LOW_COLLABORATION,
            probability=0.60, impact=0.55,
            description=f"Average collaboration count per researcher is very low ({avg:.1f}).",
            evidence=[f"Mean collaboration count: {avg:.1f}"],
            mitigation="Create internal collaboration programs; form interdisciplinary research clusters.",
        ))
    return risks


def _funding_instability_risk(inp: InstitutionInput) -> list[InstitutionRisk]:
    risks: list[InstitutionRisk] = []
    if not inp.grants:
        if len(inp.researchers) > 3:
            risks.append(_risk(
                RiskType.FUNDING_INSTABILITY,
                probability=0.80, impact=0.85,
                description="No active grants recorded — institution faces critical funding instability.",
                evidence=["Grant count: 0"],
                mitigation="Urgently establish grant application strategy; hire grant writing support.",
            ))
        return risks
    amounts = [_sf(g.get("amount", 0)) for g in inp.grants if _sf(g.get("amount", 0)) > 0]
    if not amounts:
        return risks
    avg = _mean(amounts)
    if avg == 0:
        return risks
    # High variance = instability
    variance = _mean([(a - avg) ** 2 for a in amounts])
    cv = (variance ** 0.5) / avg
    if cv > 1.5:
        risks.append(_risk(
            RiskType.FUNDING_INSTABILITY,
            probability=0.55, impact=0.65,
            description=f"High variability in grant amounts (CV={cv:.1f}) — unpredictable funding pipeline.",
            evidence=[f"Grant amount coefficient of variation: {cv:.1f}"],
            mitigation="Diversify grant portfolio; target recurring grants and framework programmes.",
        ))
    return risks


def _doctoral_risk(inp: InstitutionInput) -> list[InstitutionRisk]:
    risks: list[InstitutionRisk] = []
    n = max(len(inp.researchers), 1)
    phd_count = sum(
        1 for r in inp.researchers
        if "phd" in (r.get("position") or "").lower()
    )
    if phd_count / n < 0.05 and n > 10:
        risks.append(_risk(
            RiskType.LOW_DOCTORAL_RECRUITMENT,
            probability=0.65, impact=0.60,
            description=f"PhD candidate ratio is very low ({phd_count / n:.0%}) — future research pipeline at risk.",
            evidence=[f"PhD candidates: {phd_count}/{n}"],
            mitigation="Launch doctoral recruitment campaigns; offer competitive stipends and research opportunities.",
        ))
    return risks


def _strategic_vulnerability_risk(inp: InstitutionInput) -> list[InstitutionRisk]:
    risks: list[InstitutionRisk] = []
    # Count unique research areas
    areas: set[str] = set()
    for r in inp.researchers:
        for a in (r.get("research_areas") or r.get("domains") or []):
            if a:
                areas.add(str(a).lower())
    n = len(inp.researchers)
    if len(areas) < 3 and n > 5:
        risks.append(_risk(
            RiskType.STRATEGIC_VULNERABILITY,
            probability=0.60, impact=0.70,
            description=f"Institution covers only {len(areas)} research area(s) — limited strategic portfolio.",
            evidence=[f"Unique research areas: {len(areas)}"],
            mitigation="Invest in diversification; hire in emerging research areas.",
        ))
    return risks


def _talent_retention_risk(inp: InstitutionInput) -> list[InstitutionRisk]:
    risks: list[InstitutionRisk] = []
    h_vals = [_sf(r.get("h_index", 0)) for r in inp.researchers]
    avg_h  = _mean(h_vals)
    avail_vals = [_sf(r.get("availability", 1.0)) for r in inp.researchers]
    avg_avail  = _mean(avail_vals)
    if avg_h > 8 and avg_avail < 0.4:
        risks.append(_risk(
            RiskType.TALENT_RETENTION,
            probability=0.65, impact=0.75,
            description=f"High-impact researchers (avg h={avg_h:.1f}) show low availability — retention risk.",
            evidence=[f"Average h-index: {avg_h:.1f}", f"Average availability: {avg_avail:.2f}"],
            mitigation="Review workload; offer flexible conditions; implement retention bonuses.",
        ))
    return risks


# ── Public function ───────────────────────────────────────────────────────────

def detect_risks(inp: InstitutionInput) -> list[InstitutionRisk]:
    """Detect all institutional risks."""
    risks: list[InstitutionRisk] = []
    risks.extend(_research_decline_risk(inp))
    risks.extend(_grant_dependency_risk(inp))
    risks.extend(_publication_concentration_risk(inp))
    risks.extend(_staff_turnover_risk(inp))
    risks.extend(_isolation_risk(inp))
    risks.extend(_low_collaboration_risk(inp))
    risks.extend(_funding_instability_risk(inp))
    risks.extend(_doctoral_risk(inp))
    risks.extend(_strategic_vulnerability_risk(inp))
    risks.extend(_talent_retention_risk(inp))

    level_order = {
        RiskLevel.CRITICAL: 0, RiskLevel.HIGH: 1, RiskLevel.MEDIUM: 2,
        RiskLevel.LOW: 3, RiskLevel.MINIMAL: 4,
    }
    return sorted(risks, key=lambda r: level_order.get(r.severity, 5))
