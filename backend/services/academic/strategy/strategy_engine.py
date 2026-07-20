"""AcademicStrategyEngine — generates personalized academic roadmap recommendations."""
from __future__ import annotations

from services.academic.models import AcademicContext, AcademicUserProfile, StrategyRecommendation


class AcademicStrategyEngine:
    """Generates strategic next-step recommendations from academic context and user profile."""

    def generate(
        self,
        profile: AcademicUserProfile,
        context: AcademicContext | None = None,
    ) -> list[StrategyRecommendation]:
        recommendations: list[StrategyRecommendation] = []
        priority = 1

        # ── Publication roadmap ────────────────────────────────────────────────
        if profile.interaction_count >= 3:
            recommendations.append(StrategyRecommendation(
                type="next_publication",
                title="Identify your next publication target",
                description=(
                    f"Based on your research focus in {profile.primary_domain or 'your domain'}, "
                    "consider submitting a focused empirical study to a Q2-Q1 journal."
                ),
                priority=priority,
                rationale="Consistent publication activity strengthens research impact.",
                evidence=[
                    f"You have completed {profile.interaction_count} research interactions.",
                    f"Primary domain: {profile.primary_domain or 'not yet identified'}.",
                ],
            ))
            priority += 1

        # ── Journal targeting ──────────────────────────────────────────────────
        if profile.preferred_journals:
            recommendations.append(StrategyRecommendation(
                type="next_journal",
                title=f"Submit to {profile.preferred_journals[0]}",
                description=f"Based on your previous preferences, {profile.preferred_journals[0]} "
                            "aligns with your research domain.",
                priority=priority,
                rationale="Targeting familiar journals improves submission quality and acceptance rates.",
                evidence=[f"Preferred journals in memory: {', '.join(profile.preferred_journals[:3])}"],
            ))
            priority += 1

        # ── Methodology improvement ────────────────────────────────────────────
        if profile.known_weaknesses:
            top_weakness = profile.known_weaknesses[0].replace("_", " ").title()
            recommendations.append(StrategyRecommendation(
                type="methodology_improvement",
                title=f"Address recurring weakness: {top_weakness}",
                description=f"Your interactions frequently flag '{top_weakness}' as an area for improvement. "
                            "Consider a methodology workshop or consulting a statistician.",
                priority=priority,
                rationale="Addressing recurring weaknesses improves manuscript quality and reviewer reception.",
                evidence=[
                    f"Top weaknesses: {', '.join(w.replace('_', ' ') for w in profile.known_weaknesses[:3])}",
                ],
            ))
            priority += 1

        # ── Collaboration ─────────────────────────────────────────────────────
        if context and context.domain.value != "unknown":
            recommendations.append(StrategyRecommendation(
                type="missing_collaboration",
                title="Explore interdisciplinary collaboration",
                description=(
                    f"Your work in {context.domain.value.replace('_', ' ')} could benefit "
                    "from collaboration with complementary domains."
                ),
                priority=priority,
                rationale="Interdisciplinary collaboration increases citation impact and broadens research scope.",
                evidence=["Interdisciplinary papers show 30% higher citation rates on average."],
            ))
            priority += 1

        # ── Grant application ──────────────────────────────────────────────────
        if profile.interaction_count >= 5 and not _has_grant_strategy(recommendations):
            recommendations.append(StrategyRecommendation(
                type="next_grant",
                title="Prepare a research grant application",
                description=(
                    "Your research activity suggests readiness for external funding. "
                    "Explore national research council grants and EU Horizon calls."
                ),
                priority=priority,
                rationale="Funded research has higher institutional support and publication output.",
                evidence=[f"Research domain: {profile.primary_domain or 'academic'}"],
            ))
            priority += 1

        # ── Career progression ─────────────────────────────────────────────────
        if profile.avg_quality_score > 0.75:
            recommendations.append(StrategyRecommendation(
                type="career_progression",
                title="Build your research reputation",
                description=(
                    "Your high-quality output (avg score {:.0f}%) positions you well for "
                    "journal editorial roles or conference programme committee positions."
                ).format(profile.avg_quality_score * 100),
                priority=priority,
                rationale="Reviewer and editorial roles increase domain visibility and networking.",
                evidence=[
                    f"Average quality score: {profile.avg_quality_score:.1%}",
                    f"Interaction count: {profile.interaction_count}",
                ],
            ))

        return sorted(recommendations, key=lambda r: r.priority)

    def generate_next_steps(
        self, profile: AcademicUserProfile, context: AcademicContext | None = None
    ) -> list[StrategyRecommendation]:
        """Alias kept for backward compatibility."""
        return self.generate(profile, context)


def _has_grant_strategy(recommendations: list[StrategyRecommendation]) -> bool:
    return any(r.type == "next_grant" for r in recommendations)
