"""Research Collaboration Intelligence — Collaboration Insight Generator (Phase XIV).

Generates personalized, benchmarked insights about a researcher's
collaboration patterns and network health.
"""
from __future__ import annotations

from .models import CollabInsight, InsightSeverity, ResearcherProfile

# Platform benchmarks (academic sector medians)
_BENCHMARKS = {
    "international_collab_ratio":  0.30,
    "unique_institutions":         3.0,
    "collaboration_count":         8.0,
    "industry_collab_ratio":       0.10,
    "h_index_per_year":            1.5,
    "publications_per_year":       3.0,
    "methods_diversity":           2.0,
    "domain_diversity":            3.0,
}


def _insight(
    insight_type: str,
    message: str,
    severity: InsightSeverity,
    metric_value: float,
    benchmark: float,
    recommendation: str,
) -> CollabInsight:
    return CollabInsight(
        insight_type=insight_type,
        message=message,
        severity=severity,
        metric_value=metric_value,
        benchmark_value=benchmark,
        recommendation=recommendation,
    )


def generate_insights(
    source: ResearcherProfile,
    all_profiles: list[ResearcherProfile],
    n_collaborators: int | None = None,
) -> list[CollabInsight]:
    insights: list[CollabInsight] = []

    # ── International collaboration ───────────────────────────────────────────
    intl = source.international_collab_ratio
    bench_intl = _BENCHMARKS["international_collab_ratio"]
    if intl < bench_intl * 0.5:
        insights.append(_insight(
            "international_collaboration",
            f"Your international collaboration rate ({intl:.0%}) is well below "
            f"the academic benchmark ({bench_intl:.0%}).",
            InsightSeverity.WARNING,
            intl, bench_intl,
            "Reach out to researchers in other countries. International co-authorships "
            "generate 40-60% more citations on average.",
        ))
    elif intl >= bench_intl * 1.5:
        insights.append(_insight(
            "international_collaboration",
            f"Your international collaboration rate ({intl:.0%}) is above benchmark. "
            f"Excellent global reach.",
            InsightSeverity.INFO,
            intl, bench_intl,
            "Maintain your international network — consider applying for international grants.",
        ))

    # ── Same-institution concentration ────────────────────────────────────────
    if all_profiles:
        same_inst = sum(
            1 for p in all_profiles
            if p.institution.lower() == source.institution.lower()
            and p.user_id != source.user_id
        )
        total_collab = max(source.collaboration_count, 1)
        same_ratio = min(same_inst / total_collab, 1.0)
        if same_ratio > 0.7 and source.collaboration_count > 2:
            insights.append(_insight(
                "institution_concentration",
                f"You collaborate mostly within your institution "
                f"({same_ratio:.0%} of collaborations).",
                InsightSeverity.WARNING,
                same_ratio, 0.5,
                "Expand your network beyond your institution to strengthen funding applications "
                "and increase citation diversity.",
            ))

    # ── Publication co-author diversity ───────────────────────────────────────
    if source.collaboration_count < 3 and source.publication_count > 5:
        insights.append(_insight(
            "co_author_diversity",
            f"You publish mainly with the same co-authors "
            f"({source.collaboration_count} unique collaborators).",
            InsightSeverity.WARNING,
            float(source.collaboration_count), _BENCHMARKS["collaboration_count"],
            "Diversify your co-author network. More diverse authorship correlates with "
            "higher citation counts and journal acceptance rates.",
        ))

    # ── Methods diversity ─────────────────────────────────────────────────────
    methods_count = len(source.methods) + len(source.statistical_expertise)
    bench_methods = _BENCHMARKS["methods_diversity"]
    if methods_count < bench_methods:
        insights.append(_insight(
            "methodological_diversity",
            f"Your research methods portfolio ({methods_count} listed) is limited.",
            InsightSeverity.OPPORTUNITY,
            float(methods_count), bench_methods,
            "Add complementary methodological skills (e.g., mixed methods, Bayesian analysis) "
            "to strengthen grant proposals and widen co-authorship opportunities.",
        ))

    # ── Domain breadth ────────────────────────────────────────────────────────
    domain_count = len(source.domains)
    bench_domains = _BENCHMARKS["domain_diversity"]
    if domain_count >= bench_domains * 1.5:
        insights.append(_insight(
            "domain_diversity",
            f"Your research spans {domain_count} domains — excellent interdisciplinary breadth.",
            InsightSeverity.INFO,
            float(domain_count), bench_domains,
            "Leverage your interdisciplinary profile to build diverse research teams.",
        ))

    # ── Research network statistical gap ─────────────────────────────────────
    if source.statistical_expertise and len(source.statistical_expertise) < 2:
        insights.append(_insight(
            "statistical_expertise_gap",
            "Your collaboration network may lack statistical diversity.",
            InsightSeverity.OPPORTUNITY,
            float(len(source.statistical_expertise)), 3.0,
            "Partner with a statistician or data scientist to strengthen "
            "methodology sections in manuscripts and grant proposals.",
        ))

    # ── Industry partnership gap ──────────────────────────────────────────────
    has_industry = "industry" in " ".join(source.keywords).lower()
    if not has_industry and source.career_stage.value in ("mid_career", "senior"):
        insights.append(_insight(
            "industry_collaboration",
            "Your collaboration network has no identified industry partners.",
            InsightSeverity.OPPORTUNITY,
            0.0, _BENCHMARKS["industry_collab_ratio"],
            "Industry partnerships open KTT funding streams, patent opportunities, "
            "and real-world impact pathways.",
        ))

    # ── High impact positive insight ──────────────────────────────────────────
    if source.impact_score > 0.7:
        insights.append(_insight(
            "research_impact",
            f"Your research impact score is high ({source.impact_score:.2f}/1.0). "
            "You are well positioned to lead cross-institutional research teams.",
            InsightSeverity.INFO,
            source.impact_score, 0.5,
            "Use your impact score to attract junior researchers and secure PI roles on grants.",
        ))

    # ── Low availability warning ──────────────────────────────────────────────
    if source.availability < 0.3:
        insights.append(_insight(
            "availability",
            f"Your stated availability is low ({source.availability:.0%}). "
            "This may reduce your collaboration opportunities.",
            InsightSeverity.WARNING,
            source.availability, 0.5,
            "Update your availability in your profile to attract the right collaborators "
            "at the right time.",
        ))

    return insights
