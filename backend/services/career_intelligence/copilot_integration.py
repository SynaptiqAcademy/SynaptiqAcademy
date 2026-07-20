"""Academic Career Intelligence — Academic Copilot Integration (Phase XVI).

Generates proactive suggestions that link career intelligence insights with the
Academic Copilot's multi-engine orchestration capabilities.
"""
from __future__ import annotations

from .models import CareerProfile, CareerStage, CopilotSuggestion


def _s(category: str, suggestion: str, action: str,
        urgency: str = "medium", benefit: str = "") -> CopilotSuggestion:
    return CopilotSuggestion(category=category, suggestion=suggestion,
                             action=action, urgency=urgency, benefit=benefit)


def generate_copilot_suggestions(profile: CareerProfile) -> list[dict]:
    """
    Return proactive Copilot suggestions tailored to career stage and gaps.
    These feed directly into the Academic Copilot's proactive advisor.
    """
    suggestions: list[CopilotSuggestion] = []

    # Writing & publication suggestions
    if profile.publication_count < 5:
        suggestions.append(_s(
            "writing",
            "Your publication count is below average for your career stage.",
            "Use the Manuscript Intelligence engine to draft or review a new paper.",
            urgency="high",
            benefit="A new publication can significantly increase your citation count and h-index.",
        ))
    else:
        suggestions.append(_s(
            "writing",
            "Maintain momentum by targeting high-impact journals.",
            "Use the Journal Matching engine to identify optimal submission targets.",
            urgency="medium",
            benefit="Strategic journal selection can increase citations by 2–3×.",
        ))

    # Grant suggestions
    if profile.grant_count == 0:
        suggestions.append(_s(
            "funding",
            "You have no recorded grant funding.",
            "Use the Grant Lifecycle engine to find open calls and draft your first application.",
            urgency="critical",
            benefit="A funded grant strengthens your promotion case and opens new research pathways.",
        ))

    # Literature review
    if profile.research_areas:
        area = profile.research_areas[0]
        suggestions.append(_s(
            "literature",
            f"Consider conducting a systematic literature review in {area}.",
            "Use the Literature Review Intelligence engine to accelerate review synthesis.",
            urgency="medium",
            benefit="Review papers attract 3–5× more citations than typical empirical articles.",
        ))

    # Collaboration
    if profile.collaboration_count < 5:
        suggestions.append(_s(
            "collaboration",
            "Your collaboration network appears limited.",
            "Use the Collaboration Intelligence engine to find matching co-authors.",
            urgency="high",
            benefit="Collaborative papers have 1.7× higher citation impact on average.",
        ))

    # Research gap
    if profile.research_areas:
        suggestions.append(_s(
            "research_gap",
            "Identify unexplored opportunities in your research area.",
            "Use the Research Gap Intelligence engine to find your next high-impact topic.",
            urgency="medium",
            benefit="Filling research gaps establishes priority and attracts early citations.",
        ))

    # Skill-based suggestions
    if not profile.statistical_expertise:
        suggestions.append(_s(
            "skills",
            "Statistical expertise is not detected in your profile.",
            "Use the Statistical Intelligence engine to validate your data analyses.",
            urgency="high",
            benefit="Rigorous statistics prevents desk rejection and strengthens reviewer confidence.",
        ))

    # Stage-specific
    if profile.career_stage == CareerStage.PHD_CANDIDATE:
        suggestions.append(_s(
            "career_planning",
            "As a PhD candidate, your dissertation timeline is critical.",
            "Schedule a roadmap review using the Career Roadmap feature.",
            urgency="high",
            benefit="Structured milestones reduce time-to-completion by an average of 6 months.",
        ))
    elif profile.career_stage == CareerStage.POSTDOC:
        suggestions.append(_s(
            "career_planning",
            "Postdoc window is typically 2–4 years — plan your transition now.",
            "Use the Promotion Readiness assessment to identify gaps for assistant professor roles.",
            urgency="critical",
            benefit="Early preparation improves success rate for tenure-track applications by 40%.",
        ))
    elif profile.career_stage in (CareerStage.ASSISTANT_PROF, CareerStage.LECTURER):
        suggestions.append(_s(
            "career_planning",
            "Focus on building your research identity before your next review.",
            "Use the Skill Gap Analyzer to identify and close critical competency gaps.",
            urgency="high",
            benefit="Strong competency profiles correlate with successful tenure review outcomes.",
        ))

    return [s.to_dict() for s in suggestions[:8]]
