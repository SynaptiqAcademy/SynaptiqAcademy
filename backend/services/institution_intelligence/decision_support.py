"""Institution Intelligence Engine — Executive Decision Support (Phase XV).

Generates audience-specific executive recommendations with reasoning,
evidence, confidence, impact, and implementation difficulty.
"""
from __future__ import annotations

from .models import (
    ExecutiveRecommendation, InstitutionInput, InstitutionKPIs,
    RecommendationAudience,
)


def _sf(v, d: float = 0.0) -> float:
    try:
        return float(v) if v is not None else d
    except (TypeError, ValueError):
        return d


def _si(v, d: int = 0) -> int:
    try:
        return int(v) if v is not None else d
    except (TypeError, ValueError):
        return d


def _mean(vals: list[float]) -> float:
    return sum(vals) / len(vals) if vals else 0.0


def _rec(
    category: str, title: str, desc: str,
    audience: RecommendationAudience,
    reasoning: str, evidence: list[str],
    confidence: float = 0.75,
    impact: str = "high", difficulty: str = "medium",
    priority: str = "high", timeline: str = "3-6 months",
) -> ExecutiveRecommendation:
    return ExecutiveRecommendation(
        category=category, title=title, description=desc, audience=audience,
        reasoning=reasoning, evidence=evidence, confidence=confidence,
        expected_impact=impact, implementation_difficulty=difficulty,
        priority=priority, timeline=timeline,
    )


# ── Rector-level recommendations ─────────────────────────────────────────────

def _rector_recs(inp: InstitutionInput, kpis: InstitutionKPIs) -> list[ExecutiveRecommendation]:
    recs: list[ExecutiveRecommendation] = []

    if kpis.internationalization_score < 0.2:
        recs.append(_rec(
            "international_strategy",
            "Launch International Research Partnership Program",
            "Establish 5+ international research partnerships within 12 months to "
            "increase cross-border collaboration and global visibility.",
            RecommendationAudience.RECTOR,
            reasoning="Institutions with >30% international collaboration achieve 40% higher citation impact.",
            evidence=[f"Current internationalization score: {kpis.internationalization_score:.1%}",
                      "Benchmark target: ≥ 0.30"],
            confidence=0.82, impact="high", difficulty="medium",
            priority="critical", timeline="6-12 months",
        ))

    if kpis.grant_success_rate < 0.3:
        recs.append(_rec(
            "funding_strategy",
            "Establish Research Grants Office with Dedicated Grant Writers",
            "Hire 2-3 experienced grant writers; target EU Horizon, national research councils, and industry.",
            RecommendationAudience.RECTOR,
            reasoning="Institutions with dedicated grant offices achieve 25-40% higher success rates.",
            evidence=[f"Current grant success rate: {kpis.grant_success_rate:.0%}",
                      "Target: ≥ 0.40"],
            confidence=0.80, impact="very high", difficulty="medium",
            priority="critical", timeline="3-6 months",
        ))

    if kpis.reputation_score < 0.4:
        recs.append(_rec(
            "reputation_strategy",
            "Develop 5-Year Research Reputation Strategy",
            "Define institutional research priorities; invest in high-impact research clusters.",
            RecommendationAudience.RECTOR,
            reasoning="Strategic focus correlates with 30% improvement in reputation scores over 5 years.",
            evidence=[f"Current reputation score: {kpis.reputation_score:.2f}"],
            confidence=0.70, impact="high", difficulty="high",
            priority="high", timeline="12-24 months",
        ))

    if kpis.innovation_score < 0.2:
        recs.append(_rec(
            "innovation_strategy",
            "Create Industry Partnership and Technology Transfer Office",
            "Establish TTO; set patent filing targets; incentivise industry collaboration.",
            RecommendationAudience.RECTOR,
            confidence=0.72, impact="high", difficulty="high",
            reasoning="TTO reduces time-to-commercialisation by 60% for institutional IP.",
            evidence=[f"Innovation score: {kpis.innovation_score:.2f}"],
            priority="medium", timeline="12-18 months",
        ))

    return recs


# ── Dean-level recommendations ────────────────────────────────────────────────

def _dean_recs(inp: InstitutionInput, kpis: InstitutionKPIs) -> list[ExecutiveRecommendation]:
    recs: list[ExecutiveRecommendation] = []

    if kpis.faculty_performance < 0.4:
        recs.append(_rec(
            "faculty_development",
            "Implement Faculty Research Performance Support Program",
            "Offer protected research time, writing retreats, and peer mentoring for underperforming faculty.",
            RecommendationAudience.DEAN,
            reasoning="Protected research time increases publication rate by 35% within 2 years.",
            evidence=[f"Faculty performance score: {kpis.faculty_performance:.2f}"],
            confidence=0.78, impact="high", difficulty="low",
            priority="high", timeline="3-6 months",
        ))

    if kpis.doctoral_activity_score < 0.2:
        recs.append(_rec(
            "doctoral_recruitment",
            "Launch PhD Recruitment and Funding Campaign",
            "Target international PhD candidates; establish scholarship fund; partner with industry for co-funded PhDs.",
            RecommendationAudience.DEAN,
            reasoning="Doctoral candidates contribute significantly to publication output and innovation.",
            evidence=[f"Doctoral activity score: {kpis.doctoral_activity_score:.2f}"],
            confidence=0.75, impact="high", difficulty="medium",
            priority="high", timeline="6-12 months",
        ))

    if kpis.open_science_score < 0.3:
        recs.append(_rec(
            "open_science",
            "Adopt Open Science Policy and Mandate Open Access",
            "Implement institutional open access mandate; fund APC (article processing charges).",
            RecommendationAudience.DEAN,
            reasoning="Open access increases citation impact by 18% on average.",
            evidence=[f"Open science score: {kpis.open_science_score:.2f}"],
            confidence=0.82, impact="medium", difficulty="low",
            priority="medium", timeline="3-6 months",
        ))

    return recs


# ── Department head recommendations ──────────────────────────────────────────

def _dept_head_recs(inp: InstitutionInput, kpis: InstitutionKPIs) -> list[ExecutiveRecommendation]:
    recs: list[ExecutiveRecommendation] = []

    if kpis.collaboration_score < 0.3:
        recs.append(_rec(
            "collaboration",
            "Create Interdisciplinary Research Working Groups",
            "Establish 3-5 cross-departmental research clusters; host monthly collaboration events.",
            RecommendationAudience.DEPARTMENT_HEAD,
            reasoning="Cross-departmental collaboration increases grant competitiveness by 30%.",
            evidence=[f"Collaboration score: {kpis.collaboration_score:.2f}"],
            confidence=0.75, impact="medium", difficulty="low",
            priority="medium", timeline="1-3 months",
        ))

    if kpis.publication_growth < 0:
        recs.append(_rec(
            "publication_strategy",
            "Launch Departmental Publication Sprint",
            "Set quarterly publication targets; provide statistical and writing support; celebrate successes.",
            RecommendationAudience.DEPARTMENT_HEAD,
            reasoning="Structured publication targets increase output by 20-25% within 12 months.",
            evidence=[f"Publication growth: {kpis.publication_growth:.1%}"],
            confidence=0.72, impact="high", difficulty="low",
            priority="high", timeline="3-6 months",
        ))

    return recs


# ── Grant office recommendations ─────────────────────────────────────────────

def _grant_office_recs(inp: InstitutionInput, kpis: InstitutionKPIs) -> list[ExecutiveRecommendation]:
    recs: list[ExecutiveRecommendation] = []

    if kpis.grant_success_rate < 0.35:
        recs.append(_rec(
            "grant_strategy",
            "Implement Pre-Submission Grant Review Process",
            "Require internal review of all grants >€50K before submission; provide expert feedback.",
            RecommendationAudience.GRANT_OFFICE,
            reasoning="Internal review process increases success rate by 15-25%.",
            evidence=[f"Current success rate: {kpis.grant_success_rate:.0%}"],
            confidence=0.80, impact="high", difficulty="low",
            priority="critical", timeline="1-3 months",
        ))

    if kpis.research_income < 500000:
        recs.append(_rec(
            "funding_diversification",
            "Develop EU Horizon Europe Application Pipeline",
            "Identify and prepare 3+ collaborative Horizon Europe bids within 6 months.",
            RecommendationAudience.GRANT_OFFICE,
            reasoning="Horizon Europe offers €95B+ funding; most institutions are underrepresented.",
            evidence=[f"Current research income: €{kpis.research_income:,.0f}"],
            confidence=0.72, impact="very high", difficulty="medium",
            priority="high", timeline="3-6 months",
        ))

    return recs


# ── Research director recommendations ─────────────────────────────────────────

def _research_director_recs(inp: InstitutionInput, kpis: InstitutionKPIs) -> list[ExecutiveRecommendation]:
    recs: list[ExecutiveRecommendation] = []

    if kpis.q1_ratio < 0.3:
        recs.append(_rec(
            "publication_quality",
            "Target Q1 Journal Publication Strategy",
            "Work with researchers to identify suitable Q1 journals; provide pre-submission review and writing support.",
            RecommendationAudience.RESEARCH_DIRECTOR,
            reasoning="Q1 publications increase citation rate 3x compared to Q3/Q4 venues.",
            evidence=[f"Current Q1 ratio: {kpis.q1_ratio:.0%}"],
            confidence=0.78, impact="high", difficulty="medium",
            priority="high", timeline="6-12 months",
        ))

    if kpis.sustainability_score < 0.3:
        recs.append(_rec(
            "sustainability",
            "Diversify Research Funding Portfolio",
            "Map current funding concentration; identify gaps; target 5+ new funding organisations.",
            RecommendationAudience.RESEARCH_DIRECTOR,
            reasoning="Portfolio diversification reduces financial vulnerability by 40%.",
            evidence=[f"Sustainability score: {kpis.sustainability_score:.2f}"],
            confidence=0.74, impact="high", difficulty="medium",
            priority="high", timeline="6-12 months",
        ))

    return recs


# ── HR-level recommendations ──────────────────────────────────────────────────

def _hr_recs(inp: InstitutionInput, kpis: InstitutionKPIs) -> list[ExecutiveRecommendation]:
    recs: list[ExecutiveRecommendation] = []
    n = len(inp.researchers)
    early_career = sum(
        1 for r in inp.researchers
        if (r.get("position") or "").lower() in ("postdoc", "junior researcher", "assistant professor")
    )
    if n > 5 and early_career / n > 0.5:
        recs.append(_rec(
            "talent_retention",
            "Implement Early-Career Researcher Retention Program",
            "Offer career development paths, mentoring, and competitive packages for top early-career researchers.",
            RecommendationAudience.HR,
            reasoning="Early-career turnover costs 150-200% of annual salary to replace.",
            evidence=[f"Early-career ratio: {early_career / n:.0%}"],
            confidence=0.76, impact="high", difficulty="medium",
            priority="high", timeline="3-6 months",
        ))

    return recs


# ── Public function ───────────────────────────────────────────────────────────

def generate_recommendations(
    inp: InstitutionInput,
    kpis: InstitutionKPIs,
    audiences: list[RecommendationAudience] | None = None,
) -> list[ExecutiveRecommendation]:
    """Generate evidence-based executive recommendations."""
    all_recs: list[ExecutiveRecommendation] = []
    all_recs.extend(_rector_recs(inp, kpis))
    all_recs.extend(_dean_recs(inp, kpis))
    all_recs.extend(_dept_head_recs(inp, kpis))
    all_recs.extend(_grant_office_recs(inp, kpis))
    all_recs.extend(_research_director_recs(inp, kpis))
    all_recs.extend(_hr_recs(inp, kpis))

    if audiences:
        all_recs = [r for r in all_recs if r.audience in audiences]

    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    return sorted(all_recs, key=lambda r: priority_order.get(r.priority, 4))
