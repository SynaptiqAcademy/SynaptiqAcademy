"""Academic Career Intelligence — Career Risk Analyzer (Phase XVI)."""
from __future__ import annotations

from .models import CareerProfile, CareerRisk, CareerRiskType, CareerStage, RiskSeverity


def _severity(score: float) -> RiskSeverity:
    if score >= 0.75:
        return RiskSeverity.CRITICAL
    if score >= 0.55:
        return RiskSeverity.HIGH
    if score >= 0.35:
        return RiskSeverity.MEDIUM
    return RiskSeverity.LOW


def _risk(rt: CareerRiskType, score: float, desc: str, evidence: list[str], mitigation: str) -> CareerRisk:
    return CareerRisk(
        risk_type=rt,
        severity=_severity(score),
        description=desc,
        evidence=evidence,
        mitigation=mitigation,
        risk_score=round(score, 3),
    )


def detect_career_risks(profile: CareerProfile) -> list[CareerRisk]:
    """Detect up to 8 career risk signals from the researcher's profile."""
    risks: list[CareerRisk] = []
    years = max(profile.years_active, 1)

    # ── 1. Publication stagnation ──
    pub_per_year = profile.publication_count / years
    if pub_per_year < 1.0:
        score = max(0.3, 1.0 - pub_per_year)
        risks.append(_risk(
            CareerRiskType.PUBLICATION_STAGNATION,
            round(score, 3),
            "Publication rate below expectations for career stage.",
            [f"Only {pub_per_year:.1f} publications/year over {years} years"],
            "Set quarterly writing goals; use AI writing assistance; schedule manuscript retreats.",
        ))

    # ── 2. Low citation growth ──
    cites_per_pub = profile.citation_count / max(profile.publication_count, 1)
    if cites_per_pub < 5:
        score = max(0.3, 1.0 - cites_per_pub / 10.0)
        risks.append(_risk(
            CareerRiskType.LOW_CITATION_GROWTH,
            round(score, 3),
            "Citation impact is below average.",
            [f"{cites_per_pub:.1f} citations per publication"],
            "Target higher-impact journals; improve visibility via open access; share data and code publicly.",
        ))

    # ── 3. Limited collaboration ──
    if profile.collaboration_count < 3:
        score = max(0.25, 0.8 - profile.collaboration_count * 0.1)
        risks.append(_risk(
            CareerRiskType.LIMITED_COLLABORATION,
            round(score, 3),
            "Limited collaboration network restricts career mobility.",
            [f"Only {profile.collaboration_count} collaboration(s)"],
            "Join research consortia; attend 2+ conferences per year; use matchmaking platforms.",
        ))

    # ── 4. Low funding ──
    if profile.grant_count == 0 and profile.career_stage not in (
            CareerStage.UNDERGRADUATE, CareerStage.MASTER_STUDENT, CareerStage.PHD_CANDIDATE):
        risks.append(_risk(
            CareerRiskType.LOW_FUNDING,
            0.65,
            "No grant activity detected — dependency on institutional funding.",
            ["Zero competitive grants"],
            "Apply to national funding calls; partner with experienced grant applicants; use proposal templates.",
        ))
    elif profile.grant_income < 20_000 and profile.career_stage in (
            CareerStage.ASSOCIATE_PROF, CareerStage.PROFESSOR, CareerStage.SENIOR_RESEARCHER):
        risks.append(_risk(
            CareerRiskType.LOW_FUNDING,
            0.5,
            "Grant income is low relative to career stage expectations.",
            [f"Grant income: €{profile.grant_income:.0f}"],
            "Identify EU, national, and industry funding opportunities; build consortium partnerships.",
        ))

    # ── 5. Skill gaps (critical ones from skill gap report) ──
    has_programming = len(profile.programming_skills) > 0
    has_methods     = len(profile.research_methods) > 0
    if not has_programming and not has_methods:
        risks.append(_risk(
            CareerRiskType.SKILL_GAPS,
            0.55,
            "Limited evidence of quantitative or technical skill set.",
            ["No programming skills detected", "No research methods detected"],
            "Complete a data analysis or programming course; join a methods workshop.",
        ))

    # ── 6. Research isolation ──
    if profile.international_collab_ratio < 0.1 and profile.career_stage not in (
            CareerStage.UNDERGRADUATE, CareerStage.MASTER_STUDENT):
        risks.append(_risk(
            CareerRiskType.RESEARCH_ISOLATION,
            0.55,
            "Research activity appears geographically isolated.",
            [f"International collaboration ratio: {profile.international_collab_ratio:.2f}"],
            "Apply for international mobility grants (Erasmus+, Fulbright); join COST Actions or networks.",
        ))

    # ── 7. Career stagnation ──
    if profile.years_active >= 5 and profile.h_index < 5:
        score = min(0.8, 0.3 + (5 - profile.h_index) * 0.08)
        risks.append(_risk(
            CareerRiskType.CAREER_STAGNATION,
            round(score, 3),
            "H-index growth suggests limited career progression.",
            [f"H-index {profile.h_index:.0f} after {profile.years_active} years"],
            "Focus on high-impact publications; seek senior collaborators; diversify research portfolio.",
        ))

    # ── 8. Burnout indicator ──
    # High publication + low conference + low collab + low availability
    burnout_signals = 0
    if pub_per_year > 8:
        burnout_signals += 1
    if profile.conference_count == 0:
        burnout_signals += 1
    if profile.collaboration_count < 2:
        burnout_signals += 1
    if profile.availability < 0.3:
        burnout_signals += 2
    if burnout_signals >= 3:
        risks.append(_risk(
            CareerRiskType.BURNOUT_INDICATOR,
            0.6,
            "Profile signals suggest potential overwork or isolation.",
            [f"Availability: {profile.availability:.2f}",
             f"Conference attendance: {profile.conference_count}"],
            "Reduce workload; delegate tasks; prioritise wellbeing and collegial activities.",
        ))

    # Sort: critical first
    sev_order = {RiskSeverity.CRITICAL: 0, RiskSeverity.HIGH: 1,
                 RiskSeverity.MEDIUM: 2, RiskSeverity.LOW: 3}
    risks.sort(key=lambda r: sev_order.get(r.severity, 4))
    return risks
