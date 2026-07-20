"""
Institutional Risk Intelligence — 15 rule-based risk patterns.
All findings are observations, not definitive assessments.
"""
import asyncio
from datetime import datetime, timezone


def _flag(key: str, level: str, title: str, description: str, metric: str, value, threshold, action: str) -> dict:
    return {
        "key": key, "level": level, "title": title,
        "description": description, "metric": metric,
        "value": value, "threshold": threshold, "action": action,
        "detected_at": datetime.now(timezone.utc).isoformat(),
    }


async def detect_institutional_risks(institution: str, db) -> list:
    from services.iip.health_engine import compute_health_score
    from services.iip.publication_engine import get_publication_overview
    from services.iip.grant_engine import get_grant_overview
    from services.iip.faculty_engine import get_faculty_overview, get_at_risk_researchers
    from services.iip.collaboration_engine import get_collaboration_overview
    from services.iip.financial_engine import get_financial_overview

    health, pubs, grants, faculty_ov, collab, financial = await asyncio.gather(
        compute_health_score(institution, db),
        get_publication_overview(institution, db),
        get_grant_overview(institution, db),
        get_faculty_overview(institution, db),
        get_collaboration_overview(institution, db),
        get_financial_overview(institution, db),
    )

    at_risk = await get_at_risk_researchers(institution, db)
    flags = []

    # 1. Low overall health score
    if health["score"] < 50:
        flags.append(_flag(
            "low_institution_health", "critical",
            "Institution Health Score Below Threshold",
            f"Overall health score is {health['score']:.1f}/100, indicating systemic challenges.",
            "health_score", health["score"], 50,
            "Commission a comprehensive institutional review and prioritise underperforming indicators.",
        ))

    # 2. Publication output declining
    growth = pubs.get("growth_rate_pct", 0)
    if growth < -10:
        flags.append(_flag(
            "publication_decline", "high",
            "Publication Output Declining",
            f"Publication output fell {abs(growth):.1f}% year-on-year.",
            "publication_growth_pct", growth, -10,
            "Investigate barriers to publishing and consider targeted research support programmes.",
        ))

    # 3. Low Q1/Q2 publication rate
    q12_pct = pubs.get("q1q2_pct", 0)
    if pubs["total"] > 5 and q12_pct < 20:
        flags.append(_flag(
            "low_publication_quality", "medium",
            "Low Top-Quartile Publication Rate",
            f"Only {q12_pct:.1f}% of publications are in Q1/Q2 journals.",
            "q1q2_pct", q12_pct, 20,
            "Support faculty in targeting higher-impact journals; consider journal coaching.",
        ))

    # 4. Grant success rate low
    success_rate = grants.get("success_rate", 0)
    if grants["total"] > 3 and success_rate < 20:
        flags.append(_flag(
            "low_grant_success", "high",
            "Low Grant Success Rate",
            f"Grant approval rate is only {success_rate:.1f}%.",
            "grant_success_rate_pct", success_rate, 20,
            "Invest in grant writing support and pre-submission review processes.",
        ))

    # 5. High proportion at-risk researchers
    at_risk_pct = len(at_risk) / max(faculty_ov["total"], 1) * 100
    if at_risk_pct > 25:
        flags.append(_flag(
            "high_at_risk_faculty", "high",
            "High Proportion of Inactive Researchers",
            f"{at_risk_pct:.0f}% of researchers have not published in 3 years.",
            "inactive_researcher_pct", round(at_risk_pct, 1), 25,
            "Implement faculty engagement programme; identify barriers and provide targeted support.",
        ))

    # 6. Low international collaboration
    intl_pct = collab.get("international_pct", 0)
    if collab["total"] > 0 and intl_pct < 10:
        flags.append(_flag(
            "low_international_collaboration", "medium",
            "Limited International Collaboration",
            f"International collaborations represent only {intl_pct:.1f}% of total.",
            "international_collab_pct", intl_pct, 10,
            "Develop international partnership strategy; leverage existing global networks.",
        ))

    # 7. Funding concentration risk
    if financial.get("funding_dependency_risk") in ("high", "critical"):
        ci = financial.get("funding_concentration_index", 0)
        flags.append(_flag(
            "funding_concentration", "high",
            "High Funding Concentration Risk",
            f"Concentration index {ci:.2f} — heavy reliance on a small number of funders.",
            "herfindahl_concentration_index", ci, 0.25,
            "Diversify funding portfolio across multiple agencies and grant types.",
        ))

    # 8. Low faculty engagement
    eng = faculty_ov.get("engagement_rate", 100)
    if eng < 40:
        flags.append(_flag(
            "low_faculty_engagement", "medium",
            "Low Faculty Research Engagement",
            f"Only {eng:.1f}% of faculty published in the past year.",
            "faculty_engagement_rate_pct", eng, 40,
            "Review workload distribution; identify if administrative burden limits research time.",
        ))

    # 9. Low verification coverage
    health_indicators = {i["key"]: i["value"] for i in health.get("indicators", [])}
    ver_cov = health_indicators.get("verification_coverage", 100)
    if ver_cov < 30:
        flags.append(_flag(
            "low_verification", "medium",
            "Low Researcher Verification Coverage",
            f"Only {ver_cov:.0f}% of researchers are verified — credibility risk.",
            "verification_coverage_pct", ver_cov, 30,
            "Run institution-wide verification drive; consider mandatory verification for grants.",
        ))

    # 10. Low open access rate
    oa_pct = pubs.get("open_access_pct", 0)
    if pubs["total"] > 10 and oa_pct < 20:
        flags.append(_flag(
            "low_open_access", "low",
            "Low Open Access Publication Rate",
            f"Only {oa_pct:.1f}% of publications are open access.",
            "open_access_pct", oa_pct, 20,
            "Establish APC fund and policy requiring OA for publicly funded research.",
        ))

    # 11. No active grants
    if grants.get("submitted", 0) == 0 and grants.get("approved", 0) < 3:
        flags.append(_flag(
            "empty_grant_pipeline", "high",
            "Thin Grant Pipeline",
            "Fewer than 3 active grants and no submissions under review.",
            "pipeline_grant_count", grants.get("submitted", 0), 3,
            "Encourage proactive grant submissions; identify upcoming funding deadlines.",
        ))

    # 12. Income decline
    inc_growth = financial.get("income_growth_pct", 0)
    if inc_growth < -15:
        flags.append(_flag(
            "income_decline", "high",
            "Research Income Declining",
            f"Research income fell {abs(inc_growth):.1f}% year-on-year.",
            "income_growth_pct", inc_growth, -15,
            "Review grant strategy; identify departing PI and succession plan.",
        ))

    # 13. Low AI adoption
    ai_score = health_indicators.get("ai_adoption", 50)
    if ai_score < 20:
        flags.append(_flag(
            "low_ai_adoption", "low",
            "Low AI Tool Adoption",
            f"Estimated {ai_score:.0f}/100 AI adoption score — institution may lag in AI integration.",
            "ai_adoption_score", ai_score, 20,
            "Deliver AI literacy training; integrate AI tools into research workflow.",
        ))

    # 14. No departments with strong health
    dept_data = []  # placeholder — risk identified if no dept above threshold
    # (departments assessed in separate endpoint)

    # 15. Profile completeness low
    prof_complete = health_indicators.get("profile_completeness", 100)
    if prof_complete < 40:
        flags.append(_flag(
            "low_profile_completeness", "low",
            "Incomplete Researcher Profiles",
            f"Profile completeness score {prof_complete:.0f}/100 — many profiles missing key fields.",
            "profile_completeness_score", prof_complete, 40,
            "Send targeted profile completion requests; tie profile completeness to evaluation cycles.",
        ))

    return sorted(flags, key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(x["level"], 4))
