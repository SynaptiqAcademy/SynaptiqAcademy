"""Academic Career Intelligence — Career Roadmap Builder (Phase XVI).

Generates personalized 1/3/5/10-year roadmaps based on career stage and metrics.
Pure Python, deterministic.
"""
from __future__ import annotations

import datetime

from .models import (
    CareerProfile, CareerRoadmap, CareerStage, MilestoneType,
    RoadmapHorizon, RoadmapMilestone,
)

_CURRENT_YEAR = datetime.date.today().year


def _m(
    mtype: MilestoneType, desc: str, year: int,
    priority: str = "high",
    target_metric: str = "",
    target_value=None,
    resources: list[str] | None = None,
    criteria: str = "",
) -> RoadmapMilestone:
    return RoadmapMilestone(
        milestone_type=mtype,
        description=desc,
        year=year,
        priority=priority,
        target_metric=target_metric,
        target_value=target_value,
        resources=resources or [],
        success_criteria=criteria,
    )


# ── Stage-specific roadmap generators ────────────────────────────────────────

def _roadmap_phd(profile: CareerProfile, horizon: int) -> list[RoadmapMilestone]:
    ms: list[RoadmapMilestone] = []
    if horizon >= 1:
        ms.append(_m(MilestoneType.PUBLICATION, "Submit first journal article", 1,
                     "critical", "publication_count", 1,
                     ["Writing retreats", "Supervisor feedback"], "1 paper submitted"))
        ms.append(_m(MilestoneType.CONFERENCE, "Present at 1 international conference", 1,
                     "high", "conference_count", 1,
                     ["Conference funding", "Abstract submission guide"]))
        ms.append(_m(MilestoneType.SKILL, "Complete research methods training", 1,
                     "high", "skill_methods", "proficient"))
    if horizon >= 3:
        ms.append(_m(MilestoneType.PUBLICATION, "Publish 3 peer-reviewed papers", 3,
                     "critical", "publication_count", 3))
        ms.append(_m(MilestoneType.COLLABORATION, "Establish international collaboration", 2,
                     "medium", "international_collab_ratio", 0.2,
                     ["Erasmus+ mobility", "COST Action networks"]))
        ms.append(_m(MilestoneType.DEGREE, "Complete PhD dissertation", 3,
                     "critical", "degree", "PhD",
                     ["Writing support", "Thesis committee meetings"],
                     "Thesis submitted and defended"))
    if horizon >= 5:
        ms.append(_m(MilestoneType.PROMOTION, "Secure postdoctoral position", 4,
                     "critical", "career_stage", "postdoc"))
        ms.append(_m(MilestoneType.GRANT, "Apply for first competitive grant", 4,
                     "high", "grant_count", 1))
        ms.append(_m(MilestoneType.PUBLICATION, "Achieve h-index ≥ 4", 5,
                     "high", "h_index", 4))
    if horizon >= 10:
        ms.append(_m(MilestoneType.PROMOTION, "Secure lecturer or postdoc position", 7,
                     "high", "career_stage", "early_faculty"))
        ms.append(_m(MilestoneType.LEADERSHIP, "Lead a research project", 8,
                     "medium", "projects_led", 1))
        ms.append(_m(MilestoneType.PUBLICATION, "Achieve h-index ≥ 8", 10,
                     "high", "h_index", 8))
    return ms


def _roadmap_postdoc(profile: CareerProfile, horizon: int) -> list[RoadmapMilestone]:
    ms: list[RoadmapMilestone] = []
    if horizon >= 1:
        ms.append(_m(MilestoneType.PUBLICATION, "Publish 3 papers from postdoc research", 1,
                     "critical", "publication_count", profile.publication_count + 3))
        ms.append(_m(MilestoneType.GRANT, "Submit first independent grant application", 1,
                     "critical", "grant_count", profile.grant_count + 1))
        ms.append(_m(MilestoneType.MOBILITY, "Complete international research stay", 1,
                     "medium", "international_collab_ratio", 0.4))
    if horizon >= 3:
        ms.append(_m(MilestoneType.PROMOTION, "Apply for assistant professor positions", 2,
                     "critical", "career_stage", "assistant_professor"))
        ms.append(_m(MilestoneType.PUBLICATION, "Build publication portfolio to 10+ papers", 3,
                     "high", "publication_count", 10))
        ms.append(_m(MilestoneType.COLLABORATION, "Establish 3+ international collaborations", 3,
                     "medium", "collaboration_count", 3))
    if horizon >= 5:
        ms.append(_m(MilestoneType.LEADERSHIP, "Lead own research group", 4,
                     "high", "group_led", 1))
        ms.append(_m(MilestoneType.GRANT, "Win competitive research grant", 4,
                     "critical", "grant_income", 50000))
        ms.append(_m(MilestoneType.TEACHING, "Teach 2 university courses", 5,
                     "medium", "courses_taught", 2))
    if horizon >= 10:
        ms.append(_m(MilestoneType.PROMOTION, "Achieve associate professor level", 7,
                     "high", "career_stage", "associate_professor"))
        ms.append(_m(MilestoneType.PUBLICATION, "Achieve h-index ≥ 15", 10, "high", "h_index", 15))
    return ms


def _roadmap_early_faculty(profile: CareerProfile, horizon: int) -> list[RoadmapMilestone]:
    ms: list[RoadmapMilestone] = []
    if horizon >= 1:
        ms.append(_m(MilestoneType.PUBLICATION, "Publish 4+ papers per year", 1,
                     "critical", "publications_this_year", 4))
        ms.append(_m(MilestoneType.GRANT, "Win EU or national research grant", 1,
                     "critical", "grant_income", 100000))
        ms.append(_m(MilestoneType.TEACHING, "Develop 2 new courses", 1,
                     "medium", "courses", 2))
    if horizon >= 3:
        ms.append(_m(MilestoneType.PROMOTION, "Apply for associate professor", 3,
                     "high", "career_stage", "associate_professor"))
        ms.append(_m(MilestoneType.COLLABORATION, "Lead international research project", 2,
                     "high", "international_projects", 1))
        ms.append(_m(MilestoneType.PUBLICATION, "Achieve h-index ≥ 12", 3,
                     "high", "h_index", 12))
        ms.append(_m(MilestoneType.LEADERSHIP, "Supervise 2 PhD students", 3,
                     "medium", "phd_supervised", 2))
    if horizon >= 5:
        ms.append(_m(MilestoneType.GRANT, "Secure large multi-year grant (>€200K)", 4,
                     "critical", "grant_income", 200000))
        ms.append(_m(MilestoneType.PUBLICATION, "Publish in Nature/Science/top Q1", 5,
                     "high", "q1_papers", 1))
        ms.append(_m(MilestoneType.MOBILITY, "International visiting professor", 5,
                     "low", "mobility", 1))
    if horizon >= 10:
        ms.append(_m(MilestoneType.PROMOTION, "Achieve full professor", 8,
                     "critical", "career_stage", "professor"))
        ms.append(_m(MilestoneType.LEADERSHIP, "Establish research center", 9,
                     "medium", "center_led", 1))
        ms.append(_m(MilestoneType.PUBLICATION, "Achieve h-index ≥ 25", 10, "high", "h_index", 25))
    return ms


def _roadmap_senior(profile: CareerProfile, horizon: int) -> list[RoadmapMilestone]:
    ms: list[RoadmapMilestone] = []
    if horizon >= 1:
        ms.append(_m(MilestoneType.GRANT, "Lead major EU consortium grant", 1,
                     "critical", "grant_income", 500000))
        ms.append(_m(MilestoneType.LEADERSHIP, "Launch interdisciplinary research initiative", 1,
                     "high", "initiative", 1))
        ms.append(_m(MilestoneType.PUBLICATION, "Maintain 5+ publications per year", 1,
                     "high", "pub_rate", 5))
    if horizon >= 3:
        ms.append(_m(MilestoneType.LEADERSHIP, "Department research strategy leadership", 2,
                     "medium", "leadership_role", 1))
        ms.append(_m(MilestoneType.COLLABORATION, "Build international research network (10+ institutions)", 3,
                     "high", "partner_institutions", 10))
        ms.append(_m(MilestoneType.PUBLICATION, "Publish landmark review/monograph", 3,
                     "high", "landmark_pubs", 1))
    if horizon >= 5:
        ms.append(_m(MilestoneType.PROMOTION, "Research Director or Department Head", 5,
                     "medium", "leadership", "director"))
        ms.append(_m(MilestoneType.LEADERSHIP, "Establish doctoral school or research program", 5,
                     "medium", "program", 1))
    if horizon >= 10:
        ms.append(_m(MilestoneType.LEADERSHIP, "National/European research leadership role", 8,
                     "low", "advisory_role", 1))
        ms.append(_m(MilestoneType.PUBLICATION, "Achieve h-index ≥ 40 and 5000 citations", 10,
                     "medium", "h_index", 40))
    return ms


def _roadmap_generic(profile: CareerProfile, horizon: int) -> list[RoadmapMilestone]:
    ms: list[RoadmapMilestone] = []
    pub_target = profile.publication_count + horizon * 3
    h_target   = profile.h_index + horizon * 1.5
    for yr in range(1, min(horizon, 5) + 1):
        ms.append(_m(MilestoneType.PUBLICATION, f"Add {yr * 2} publications", yr,
                     "high", "publication_count", profile.publication_count + yr * 2))
    if horizon >= 3:
        ms.append(_m(MilestoneType.GRANT, "Secure competitive research funding", 2,
                     "high", "grant_count", profile.grant_count + 1))
        ms.append(_m(MilestoneType.COLLABORATION, "Establish international collaboration", 2,
                     "medium", "intl_ratio", 0.3))
    return ms


_GENERATORS = {
    CareerStage.PHD_CANDIDATE:    _roadmap_phd,
    CareerStage.POSTDOC:          _roadmap_postdoc,
    CareerStage.ASSISTANT_PROF:   _roadmap_early_faculty,
    CareerStage.LECTURER:         _roadmap_early_faculty,
    CareerStage.ASSOCIATE_PROF:   _roadmap_senior,
    CareerStage.PROFESSOR:        _roadmap_senior,
    CareerStage.SENIOR_RESEARCHER: _roadmap_senior,
}

_HORIZON_YEARS = {
    RoadmapHorizon.ONE_YEAR:   1,
    RoadmapHorizon.THREE_YEAR: 3,
    RoadmapHorizon.FIVE_YEAR:  5,
    RoadmapHorizon.TEN_YEAR:   10,
}

_STAGE_FOCUS = {
    CareerStage.PHD_CANDIDATE:    ["First publications", "PhD completion", "Conference presentations", "Methods training"],
    CareerStage.POSTDOC:          ["Grant writing", "Independent research", "Faculty job market", "International mobility"],
    CareerStage.ASSISTANT_PROF:   ["Publication volume", "Grant acquisition", "PhD supervision", "Tenure preparation"],
    CareerStage.ASSOCIATE_PROF:   ["Major grants", "Research group leadership", "International network", "Full professorship"],
    CareerStage.PROFESSOR:        ["EU consortia", "Doctoral school", "National leadership", "Legacy building"],
    CareerStage.LECTURER:         ["Teaching excellence", "Research establishment", "Publication record", "Grant applications"],
    CareerStage.SENIOR_RESEARCHER: ["Leadership roles", "Major grants", "Research direction", "Institutional impact"],
    CareerStage.RESEARCHER:       ["Publication record", "Grant applications", "Specialization", "Network building"],
}


def build_roadmap(profile: CareerProfile, horizon: RoadmapHorizon) -> CareerRoadmap:
    """Generate a personalized career roadmap."""
    h_years = _HORIZON_YEARS[horizon]
    gen     = _GENERATORS.get(profile.career_stage, _roadmap_generic)
    milestones = gen(profile, h_years)

    # Sort by year, then priority
    prio_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    milestones = sorted(milestones, key=lambda m: (m.year, prio_order.get(m.priority, 4)))

    focus = _STAGE_FOCUS.get(profile.career_stage,
                             ["Research output", "Grant funding", "Collaboration", "Skills"])

    summary = (
        f"This {h_years}-year roadmap for {profile.name or 'the researcher'} "
        f"({profile.career_stage.value.replace('_', ' ')}) focuses on "
        f"{', '.join(focus[:2]).lower()} to drive career advancement. "
        f"{len(milestones)} milestones are defined across {h_years} year(s)."
    )

    return CareerRoadmap(
        user_id=profile.user_id,
        career_stage=profile.career_stage,
        horizon=horizon,
        milestones=milestones,
        summary=summary,
        key_focus_areas=focus,
        estimated_completion_year=_CURRENT_YEAR + h_years,
    )
