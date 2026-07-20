"""Academic Career Intelligence — Personalized Recommendation Engine (Phase XVI)."""
from __future__ import annotations

from .models import (
    CareerProfile, CareerRecommendation, CareerStage, RecommendationType,
)


def _r(rtype: RecommendationType, title: str, reason: str = "", priority: str = "medium",
       tags: list[str] | None = None, impact: str = "medium", time_inv: str = "") -> CareerRecommendation:
    return CareerRecommendation(
        rec_type=rtype,
        title=title,
        reason=reason,
        priority=priority,
        tags=tags or [],
        estimated_impact=impact,
        time_investment=time_inv,
    )


def _courses(profile: CareerProfile) -> list[CareerRecommendation]:
    recs = []
    if not profile.programming_skills:
        recs.append(_r(RecommendationType.COURSE,
                       "Python for Scientific Research (Coursera)",
                       "No programming skills detected; essential for modern research.",
                       "high", ["python", "data_analysis"], "high", "20 hours"))
    if not profile.statistical_expertise:
        recs.append(_r(RecommendationType.COURSE,
                       "Applied Statistics for Researchers (EdX)",
                       "No statistical expertise detected; critical for publication quality.",
                       "high", ["statistics"], "high", "30 hours"))
    if profile.grant_count == 0:
        recs.append(_r(RecommendationType.COURSE,
                       "Grant Writing Masterclass",
                       "No grants detected; competitive funding is essential for career growth.",
                       "critical", ["grant_writing", "funding"], "very_high", "15 hours"))
    if not profile.teaching_areas and profile.career_stage in (
            CareerStage.ASSISTANT_PROF, CareerStage.LECTURER, CareerStage.ASSOCIATE_PROF):
        recs.append(_r(RecommendationType.COURSE,
                       "HEA Fellowship Programme (Higher Education Academy)",
                       "Teaching certification expected at faculty level.",
                       "high", ["teaching", "pedagogy"], "medium", "40 hours"))
    if not recs:
        recs.append(_r(RecommendationType.COURSE,
                       "Academic Leadership and Management Course",
                       "Expand leadership skills for strategic career growth.",
                       "medium", ["leadership"], "medium", "20 hours"))
    return recs[:3]


def _conferences(profile: CareerProfile) -> list[CareerRecommendation]:
    recs = []
    areas = profile.research_areas[:2] if profile.research_areas else ["your field"]
    area  = areas[0]
    recs.append(_r(RecommendationType.CONFERENCE,
                   f"Top-tier international conference in {area}",
                   "Conferences build visibility, collaborations, and citation opportunities.",
                   "high", [area, "networking"], "high", "1 week"))
    if profile.career_stage in (CareerStage.PHD_CANDIDATE, CareerStage.POSTDOC):
        recs.append(_r(RecommendationType.CONFERENCE,
                       "Early Career Researcher Summit or doctoral symposium",
                       "Designed to help early-stage researchers build their academic network.",
                       "medium", ["early_career", "networking"], "medium", "2-3 days"))
    return recs[:2]


def _mentors(profile: CareerProfile) -> list[CareerRecommendation]:
    recs = []
    if profile.career_stage in (CareerStage.PHD_CANDIDATE, CareerStage.POSTDOC,
                                 CareerStage.ASSISTANT_PROF):
        recs.append(_r(RecommendationType.MENTOR,
                       "Seek a senior mentor in your primary research area",
                       "Mentorship from established researchers accelerates career development.",
                       "high", ["mentoring", "early_career"], "high", "Ongoing"))
    if profile.grant_count == 0:
        recs.append(_r(RecommendationType.MENTOR,
                       "Identify a grant-experienced mentor for co-authoring bids",
                       "Learning from successful grant writers significantly increases success rate.",
                       "high", ["grant", "mentoring"], "very_high", "Ongoing"))
    if not recs:
        recs.append(_r(RecommendationType.MENTOR,
                       "Join a peer mentoring group or professional society",
                       "Lateral peer networks are highly effective for mid-career researchers.",
                       "medium", ["networking", "mentoring"], "medium", "Ongoing"))
    return recs[:2]


def _funding(profile: CareerProfile) -> list[CareerRecommendation]:
    recs = []
    if profile.international_collab_ratio < 0.3:
        recs.append(_r(RecommendationType.FUNDING,
                       "Erasmus+ International Research Mobility Grant",
                       "International collaboration improves h-index and career mobility.",
                       "high", ["mobility", "international"], "high", "6–12 months"))
    if profile.career_stage in (CareerStage.POSTDOC, CareerStage.ASSISTANT_PROF):
        recs.append(_r(RecommendationType.FUNDING,
                       "Marie Skłodowska-Curie Actions Fellowship (EU)",
                       "Prestigious postdoctoral fellowship supporting international research.",
                       "critical", ["fellowship", "EU"], "very_high", "Application: 3 months"))
    if profile.career_stage in (CareerStage.ASSOCIATE_PROF, CareerStage.PROFESSOR,
                                 CareerStage.SENIOR_RESEARCHER):
        recs.append(_r(RecommendationType.FUNDING,
                       "ERC Consolidator / Advanced Grant (European Research Council)",
                       "Premier EU grant for established researchers; major career milestone.",
                       "critical", ["ERC", "EU", "major_grant"], "very_high", "6 months preparation"))
    if not recs:
        recs.append(_r(RecommendationType.FUNDING,
                       "National Research Foundation small grant scheme",
                       "Internal or national small grants are best starting point for funding track record.",
                       "high", ["seed_funding"], "medium", "2 months preparation"))
    return recs[:3]


def _topics(profile: CareerProfile) -> list[CareerRecommendation]:
    recs = []
    if profile.research_areas:
        topic = profile.research_areas[0]
        recs.append(_r(RecommendationType.TOPIC,
                       f"Explore AI-augmented methods in {topic}",
                       "AI tools are transforming research productivity in all disciplines.",
                       "medium", ["AI", topic], "high", "3–6 months"))
    if not profile.research_areas or len(profile.research_areas) < 3:
        recs.append(_r(RecommendationType.TOPIC,
                       "Diversify into an adjacent research area to broaden impact",
                       "Research diversification improves citation cross-coverage and collaboration opportunities.",
                       "medium", ["diversification"], "medium", "6–12 months"))
    return recs[:2]


def _reviewers(profile: CareerProfile) -> list[CareerRecommendation]:
    recs = []
    if profile.review_count < 5:
        recs.append(_r(RecommendationType.REVIEWER,
                       "Register as reviewer on Publons / Web of Science",
                       "Peer review visibility improves reputation and journal editor relationships.",
                       "medium", ["peer_review", "visibility"], "medium", "1 hour setup"))
    return recs


def _books(profile: CareerProfile) -> list[CareerRecommendation]:
    recs = []
    if profile.career_stage in (CareerStage.PHD_CANDIDATE, CareerStage.POSTDOC):
        recs.append(_r(RecommendationType.BOOK,
                       "'The PhD Journey' – A practical guide for doctoral researchers",
                       "Systematic approach to thesis completion and early career planning.",
                       "low", ["phd", "career"], "medium", "Self-paced"))
    if profile.career_stage in (CareerStage.ASSISTANT_PROF, CareerStage.LECTURER):
        recs.append(_r(RecommendationType.BOOK,
                       "'Advice for New Faculty Members' – Robert Boice",
                       "Evidence-based strategies for junior faculty productivity and wellbeing.",
                       "low", ["faculty", "productivity"], "medium", "Self-paced"))
    return recs


# ── Public function ───────────────────────────────────────────────────────────

def generate_recommendations(profile: CareerProfile) -> dict[str, list[dict]]:
    """
    Generate personalized career recommendations across 7 categories.
    Returns a dict of category → list of recommendation dicts.
    """
    categories: dict[str, list[CareerRecommendation]] = {
        "courses":         _courses(profile),
        "conferences":     _conferences(profile),
        "mentors":         _mentors(profile),
        "funding":         _funding(profile),
        "topics":          _topics(profile),
        "peer_review":     _reviewers(profile),
        "books":           _books(profile),
    }
    return {cat: [r.to_dict() for r in recs] for cat, recs in categories.items()}
