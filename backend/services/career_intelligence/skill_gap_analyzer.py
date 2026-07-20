"""Academic Career Intelligence — Skill Gap Analyzer (Phase XVI).

Assesses 15 skill domains and identifies gaps relative to career stage expectations.
"""
from __future__ import annotations

from .models import (
    CareerProfile, CareerStage, SkillAssessment, SkillGap,
    SkillGapReport, SkillGapSeverity, SkillLevel,
)

# ── Skill domains & detection keywords ────────────────────────────────────────

_DOMAINS = [
    "research_methods",
    "statistics",
    "academic_writing",
    "programming",
    "machine_learning",
    "data_analysis",
    "grant_writing",
    "project_management",
    "teaching",
    "leadership",
    "open_science",
    "data_management",
    "peer_review",
    "presentation",
    "networking",
]

_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "research_methods":  ["cohort", "rct", "qualitative", "survey", "experiment", "simulation",
                          "longitudinal", "case study", "ethnography", "grounded theory"],
    "statistics":        ["regression", "bayesian", "anova", "multilevel", "survival",
                          "machine_learning_stats", "factor analysis", "structural equation"],
    "academic_writing":  [],   # inferred from publications
    "programming":       ["python", "r", "matlab", "julia", "java", "c++", "scala", "rust"],
    "machine_learning":  ["machine learning", "deep learning", "neural", "transformer",
                          "nlp", "computer vision", "reinforcement learning"],
    "data_analysis":     ["data analysis", "data science", "pandas", "numpy", "tableau",
                          "sql", "mongodb", "spss", "stata"],
    "grant_writing":     [],   # inferred from grant_count
    "project_management":[],   # inferred from leadership indicators
    "teaching":          [],   # inferred from teaching_areas
    "leadership":        [],   # inferred from supervision_count / admin role
    "open_science":      ["open science", "open access", "preprint", "github", "zenodo",
                          "orcid", "data sharing"],
    "data_management":   ["data management", "fair data", "rdm", "metadata",
                          "dmp", "data repository"],
    "peer_review":       [],   # inferred from review_count
    "presentation":      [],   # inferred from conference_count
    "networking":        [],   # inferred from collaboration_count
}

# Required level per career stage per domain (minimum to avoid gap)
_LEVEL_ORDER = [SkillLevel.NONE, SkillLevel.BEGINNER, SkillLevel.DEVELOPING,
                SkillLevel.PROFICIENT, SkillLevel.EXPERT]
_LEVEL_SCORE = {l: i / 4.0 for i, l in enumerate(_LEVEL_ORDER)}

_REQUIRED: dict[CareerStage, dict[str, SkillLevel]] = {
    CareerStage.PHD_CANDIDATE: {
        "research_methods": SkillLevel.PROFICIENT,
        "statistics":        SkillLevel.DEVELOPING,
        "academic_writing":  SkillLevel.DEVELOPING,
        "programming":       SkillLevel.BEGINNER,
        "data_analysis":     SkillLevel.DEVELOPING,
        "open_science":      SkillLevel.BEGINNER,
        "data_management":   SkillLevel.BEGINNER,
        "peer_review":       SkillLevel.BEGINNER,
        "presentation":      SkillLevel.DEVELOPING,
        "networking":        SkillLevel.BEGINNER,
    },
    CareerStage.POSTDOC: {
        "research_methods":  SkillLevel.PROFICIENT,
        "statistics":        SkillLevel.PROFICIENT,
        "academic_writing":  SkillLevel.PROFICIENT,
        "programming":       SkillLevel.DEVELOPING,
        "grant_writing":     SkillLevel.DEVELOPING,
        "project_management":SkillLevel.BEGINNER,
        "peer_review":       SkillLevel.DEVELOPING,
        "presentation":      SkillLevel.PROFICIENT,
        "networking":        SkillLevel.DEVELOPING,
        "open_science":      SkillLevel.DEVELOPING,
    },
    CareerStage.ASSISTANT_PROF: {
        "research_methods":  SkillLevel.EXPERT,
        "statistics":        SkillLevel.PROFICIENT,
        "academic_writing":  SkillLevel.EXPERT,
        "grant_writing":     SkillLevel.PROFICIENT,
        "teaching":          SkillLevel.PROFICIENT,
        "project_management":SkillLevel.DEVELOPING,
        "leadership":        SkillLevel.DEVELOPING,
        "networking":        SkillLevel.PROFICIENT,
        "peer_review":       SkillLevel.PROFICIENT,
        "open_science":      SkillLevel.PROFICIENT,
    },
    CareerStage.ASSOCIATE_PROF: {
        "research_methods":  SkillLevel.EXPERT,
        "academic_writing":  SkillLevel.EXPERT,
        "grant_writing":     SkillLevel.EXPERT,
        "teaching":          SkillLevel.PROFICIENT,
        "leadership":        SkillLevel.PROFICIENT,
        "project_management":SkillLevel.PROFICIENT,
        "networking":        SkillLevel.EXPERT,
    },
    CareerStage.PROFESSOR: {
        "academic_writing":  SkillLevel.EXPERT,
        "grant_writing":     SkillLevel.EXPERT,
        "leadership":        SkillLevel.EXPERT,
        "teaching":          SkillLevel.EXPERT,
        "networking":        SkillLevel.EXPERT,
        "project_management":SkillLevel.EXPERT,
    },
}

# Fallback requirement for stages not explicitly listed
_DEFAULT_REQUIRED: dict[str, SkillLevel] = {
    "research_methods": SkillLevel.DEVELOPING,
    "academic_writing": SkillLevel.DEVELOPING,
    "statistics":       SkillLevel.BEGINNER,
    "networking":       SkillLevel.BEGINNER,
    "peer_review":      SkillLevel.BEGINNER,
}

_DEVELOP_ACTIONS: dict[str, list[str]] = {
    "research_methods":  ["Complete research design course (Coursera/EdX)", "Read 'Research Design' by Creswell"],
    "statistics":        ["Enrol in advanced statistics MOOC", "Complete R/SPSS/Python stats workshop"],
    "academic_writing":  ["Attend academic writing retreat", "Use AI writing tools for drafts"],
    "programming":       ["Complete Python for Research (Coursera)", "Practice on Kaggle / GitHub"],
    "machine_learning":  ["Fast.ai Deep Learning course", "Andrew Ng ML Specialization"],
    "data_analysis":     ["Data Science with Python course", "Practice with open datasets"],
    "grant_writing":     ["Attend grant writing workshop", "Practice with internal small grants"],
    "project_management":["Complete PMP or Prince2 foundation", "Use task management tools (Trello, Asana)"],
    "teaching":          ["Observe peer teaching", "HEA fellowship programme"],
    "leadership":        ["Academic leadership course", "Volunteer for department committees"],
    "open_science":      ["Complete Open Science MOOC", "Register on OSF.io and Zenodo"],
    "data_management":   ["DMP training from your institution", "FAIRsharing.org resources"],
    "peer_review":       ["Join Publons reviewer recognition", "Request to co-review with supervisor"],
    "presentation":      ["Join Toastmasters or academic speaking club", "Present at journal clubs"],
    "networking":        ["Join ResearchGate, LinkedIn, and Twitter/X", "Attend 2+ conferences/year"],
}


# ── Skill assessment ──────────────────────────────────────────────────────────

def _infer_level(domain: str, profile: CareerProfile) -> tuple[SkillLevel, float, list[str]]:
    """Infer the current skill level for a domain from profile signals."""
    evidence: list[str] = []
    score = 0.0

    if domain == "academic_writing":
        pubs = profile.publication_count
        score = min(pubs / 20.0, 1.0)
        evidence.append(f"{pubs} publications")
    elif domain == "grant_writing":
        score = min(profile.grant_count / 5.0, 1.0) if profile.grant_count else 0.0
        evidence.append(f"{profile.grant_count} grants")
    elif domain == "peer_review":
        score = min(profile.review_count / 20.0, 1.0)
        evidence.append(f"{profile.review_count} peer reviews")
    elif domain == "presentation":
        score = min(profile.conference_count / 10.0, 1.0)
        evidence.append(f"{profile.conference_count} conferences")
    elif domain == "networking":
        score = min(profile.collaboration_count / 15.0, 1.0)
        evidence.append(f"{profile.collaboration_count} collaborations")
    elif domain == "teaching":
        score = 1.0 if profile.teaching_areas else 0.0
        evidence.append(f"{len(profile.teaching_areas)} teaching areas")
    elif domain == "leadership":
        # Leader signals: professor+ or has_supervision
        score = 0.8 if profile.career_stage in (CareerStage.PROFESSOR, CareerStage.ASSOCIATE_PROF,
                                                  CareerStage.SENIOR_RESEARCHER) else 0.3
        evidence.append(f"Career stage: {profile.career_stage.value}")
    elif domain == "project_management":
        score = 0.5 if profile.grant_count > 2 else 0.2
    else:
        keywords = _DOMAIN_KEYWORDS.get(domain, [])
        if not keywords:
            score = 0.0
        else:
            sources = (profile.research_areas + profile.research_methods +
                       profile.statistical_expertise + profile.programming_skills)
            text = " ".join(s.lower() for s in sources)
            hits = sum(1 for kw in keywords if kw in text)
            score = min(hits / max(len(keywords) * 0.3, 1), 1.0)
            if hits:
                evidence.append(f"Detected keywords: {hits}/{len(keywords)}")

    # Map score to level
    if score >= 0.85:
        level = SkillLevel.EXPERT
    elif score >= 0.60:
        level = SkillLevel.PROFICIENT
    elif score >= 0.35:
        level = SkillLevel.DEVELOPING
    elif score > 0.0:
        level = SkillLevel.BEGINNER
    else:
        level = SkillLevel.NONE

    if not evidence:
        evidence.append("Inferred from profile")

    return level, round(score, 3), evidence


def _gap_severity(current: SkillLevel, required: SkillLevel) -> SkillGapSeverity:
    ci = _LEVEL_ORDER.index(current)
    ri = _LEVEL_ORDER.index(required)
    gap = ri - ci
    if gap >= 3:
        return SkillGapSeverity.CRITICAL
    if gap >= 2:
        return SkillGapSeverity.MODERATE
    return SkillGapSeverity.MINOR


# ── Public function ───────────────────────────────────────────────────────────

def analyse_skill_gaps(profile: CareerProfile) -> SkillGapReport:
    """Assess all 15 skill domains and identify gaps for the researcher's career stage."""
    required_map = _REQUIRED.get(profile.career_stage, _DEFAULT_REQUIRED)

    assessments: list[SkillAssessment] = []
    gaps: list[SkillGap] = []

    for domain in _DOMAINS:
        level, score, evidence = _infer_level(domain, profile)
        assessments.append(SkillAssessment(domain=domain, current_level=level,
                                           level_score=score, evidence=evidence))

        required = required_map.get(domain)
        if required is None:
            continue

        ci = _LEVEL_ORDER.index(level)
        ri = _LEVEL_ORDER.index(required)
        if ci < ri:
            sev = _gap_severity(level, required)
            gaps.append(SkillGap(
                domain=domain,
                current_level=level,
                required_level=required,
                severity=sev,
                gap_score=round((ri - ci) / 4.0, 3),
                development_actions=_DEVELOP_ACTIONS.get(domain, ["Seek training or mentoring"])[:2],
            ))

    # Sort gaps: critical first
    sev_order = {SkillGapSeverity.CRITICAL: 0, SkillGapSeverity.MODERATE: 1, SkillGapSeverity.MINOR: 2}
    gaps.sort(key=lambda g: sev_order.get(g.severity, 3))

    # Overall skill score
    total_score = sum(a.level_score for a in assessments) / max(len(assessments), 1)

    # Top strengths: domains where level ≥ proficient
    strengths = sorted(
        [a.domain for a in assessments if a.current_level in (SkillLevel.PROFICIENT, SkillLevel.EXPERT)],
        key=lambda d: -next((a.level_score for a in assessments if a.domain == d), 0)
    )[:5]

    critical = [g.domain for g in gaps if g.severity == SkillGapSeverity.CRITICAL]

    return SkillGapReport(
        user_id=profile.user_id,
        career_stage=profile.career_stage,
        assessments=assessments,
        gaps=gaps,
        overall_skill_score=round(total_score, 3),
        top_strengths=strengths,
        critical_gaps=critical,
    )
