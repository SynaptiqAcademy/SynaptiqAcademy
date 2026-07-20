from __future__ import annotations

from typing import Any


def _fmt_list(items: list[str], max_items: int = 3) -> str:
    """Format a list of items as a human-readable comma-separated string."""
    shown = items[:max_items]
    result = ", ".join(shown)
    if len(items) > max_items:
        result += f" (+{len(items) - max_items} more)"
    return result


def explain_researcher(user_p: dict, cand_p: dict, sub_scores: dict) -> list[str]:
    """
    Return a list of human-readable bullet strings explaining the researcher match.
    Only includes factors that actually contributed (score > 0).
    """
    explanations: list[str] = []

    # Shared research areas
    user_areas = set(user_p.get("research_areas") or [])
    cand_areas = set(cand_p.get("research_areas") or [])
    shared_areas = sorted(user_areas & cand_areas)
    if shared_areas and sub_scores.get("area_score", 0) > 0:
        explanations.append(f"Shared research areas: {_fmt_list([a.title() for a in shared_areas])}")

    # Shared keywords
    user_kws = set(user_p.get("research_keywords") or [])
    cand_kws = set(cand_p.get("research_keywords") or [])
    shared_kws = user_kws & cand_kws
    if shared_kws and sub_scores.get("kw_score", 0) > 0:
        count = len(shared_kws)
        if count <= 3:
            explanations.append(f"Shared keywords: {_fmt_list(sorted(shared_kws))}")
        else:
            explanations.append(f"{count} shared keywords")

    # Shared methods
    user_methods = set(user_p.get("methods") or [])
    cand_methods = set(cand_p.get("methods") or [])
    shared_methods = sorted(user_methods & cand_methods)
    if shared_methods and sub_scores.get("method_score", 0) > 0:
        explanations.append(f"Shared methods: {_fmt_list([m.title() for m in shared_methods])}")

    # International collaboration
    user_country = (user_p.get("country") or "").strip().lower()
    cand_country = (cand_p.get("country") or "").strip().lower()
    diversity_score = sub_scores.get("diversity_score", 0)
    if user_country and cand_country and user_country != cand_country and diversity_score > 5:
        explanations.append("International collaboration opportunity (different countries)")

    # Career complement
    if sub_scores.get("complement_score", 0) > 7:
        explanations.append("Complementary career stages")

    # Reputation
    rep = cand_p.get("reputation_score", 0)
    if rep and sub_scores.get("rep_score", 0) > 0:
        explanations.append(f"Strong reputation score ({rep} points)")

    return explanations


def explain_project(user_p: dict, project: dict, sub_scores: dict) -> list[str]:
    """
    Return a list of human-readable bullet strings explaining the project match.
    """
    explanations: list[str] = []

    # Research area alignment
    user_areas = set(user_p.get("research_areas") or [])
    proj_areas = set(a.strip().lower() for a in (project.get("research_areas") or []))
    shared_areas = sorted(user_areas & proj_areas)
    if shared_areas and sub_scores.get("area_score", 0) > 0:
        explanations.append(f"Strong research area alignment: {_fmt_list([a.title() for a in shared_areas])}")

    # Keyword overlap
    user_kws = set(user_p.get("research_keywords") or [])
    proj_kws = set(k.strip().lower() for k in (project.get("keywords") or []))
    shared_kws = user_kws & proj_kws
    if shared_kws and sub_scores.get("kw_score", 0) > 0:
        explanations.append(f"Matching keywords: {_fmt_list(sorted(shared_kws))}")

    # Skill match
    user_skills = set(user_p.get("skills") or [])
    proj_skills = set(s.strip().lower() for s in (project.get("required_skills") or []))
    shared_skills = sorted(user_skills & proj_skills)
    if shared_skills and sub_scores.get("skill_score", 0) > 0:
        explanations.append(f"Matching skills: {_fmt_list([s.title() for s in shared_skills])}")

    # Project status
    status = (project.get("status") or "").lower()
    maturity_score = sub_scores.get("maturity_score", 0)
    if maturity_score > 0:
        if status == "recruiting":
            explanations.append("Actively recruiting new members")
        elif status == "active":
            explanations.append("Active project with open contribution opportunities")
        elif status in ("planning", "draft"):
            explanations.append("Early-stage project with open contribution opportunities")

    return explanations


def explain_journal(user_p: dict, journal: dict, sub_scores: dict) -> list[str]:
    """
    Return a list of human-readable bullet strings explaining the journal match.
    """
    explanations: list[str] = []

    # Subject / area alignment
    user_areas = set(user_p.get("research_areas") or [])
    journal_subjects = set(s.strip().lower() for s in (journal.get("subjects") or []))
    shared = sorted(user_areas & journal_subjects)
    if shared and sub_scores.get("subject_score", 0) > 0:
        explanations.append(f"Covers your primary research area: {_fmt_list([s.title() for s in shared])}")
    elif sub_scores.get("subject_score", 0) > 0:
        explanations.append("Strong subject area alignment with your research profile")

    # Keyword match in journal title/subjects
    if sub_scores.get("kw_score", 0) > 0:
        explanations.append("Keywords from your profile appear in this journal's scope")

    # Quartile
    quartile = (journal.get("quartile") or "").upper()
    quartile_score = sub_scores.get("quartile_score", 0)
    if quartile and quartile_score > 0:
        explanations.append(f"{quartile} journal matching your publication profile")

    # Open access
    if journal.get("open_access") and sub_scores.get("oa_score", 0) > 0:
        explanations.append("Open access — aligns with your publication history")

    return explanations


def explain_conference(user_p: dict, conf: dict, sub_scores: dict) -> list[str]:
    """
    Return a list of human-readable bullet strings explaining the conference match.
    """
    explanations: list[str] = []

    # Area match
    user_areas = set(user_p.get("research_areas") or [])
    conf_areas = set(a.strip().lower() for a in (conf.get("research_areas") or []))
    shared = sorted(user_areas & conf_areas)
    if shared and sub_scores.get("area_score", 0) > 0:
        explanations.append(f"Matches your research area: {_fmt_list([a.title() for a in shared])}")

    # Rank
    rank = (conf.get("rank") or "").upper()
    rank_score = sub_scores.get("rank_score", 0)
    if rank and rank_score >= 20:
        explanations.append(f"Prestigious {rank}-ranked conference")
    elif rank and rank_score > 0:
        explanations.append(f"Ranked conference ({rank})")

    # Deadline urgency
    if sub_scores.get("deadline_urgency", 0) > 0:
        explanations.append("Submission deadline approaching — act soon")

    # Format bonus
    fmt = (conf.get("format") or "").lower()
    if sub_scores.get("format_score", 0) > 0 and fmt in ("virtual", "hybrid"):
        explanations.append(f"Accessible {fmt} format")

    return explanations


def explain_grant(user_p: dict, grant: dict, sub_scores: dict) -> list[str]:
    """
    Return a list of human-readable bullet strings explaining the grant match.
    """
    explanations: list[str] = []

    # Area match
    user_areas = set(user_p.get("research_areas") or [])
    grant_areas = set(a.strip().lower() for a in (grant.get("research_areas") or []))
    shared = sorted(user_areas & grant_areas)
    if shared and sub_scores.get("area_score", 0) > 0:
        explanations.append(f"Matches your research area: {_fmt_list([a.title() for a in shared])}")

    # Career stage
    if sub_scores.get("career_score", 0) > 0:
        role = user_p.get("academic_role", "")
        explanations.append(f"Your career stage ({role.replace('_', ' ').title()}) is eligible")

    # Country eligibility (country_score or universal_score key — both supported)
    country_eligible = sub_scores.get("country_score", 0) > 0 or sub_scores.get("universal_score", 0) > 0
    if country_eligible:
        country_eligibility = grant.get("country_eligibility") or []
        if not country_eligibility:
            explanations.append("Open to applicants from all countries")
        else:
            explanations.append(f"Your country is eligible ({user_p.get('country', '')})")

    # Keyword match
    if sub_scores.get("kw_score", 0) > 0:
        explanations.append("Keywords from your profile match the grant scope")

    return explanations


def explain_reviewer(user_p: dict, reviewer: dict, sub_scores: dict) -> list[str]:
    """
    Return a list of human-readable bullet strings explaining the reviewer recommendation.
    """
    explanations: list[str] = []

    # Expertise overlap
    if sub_scores.get("expertise_score", 0) > 0:
        user_areas = set(user_p.get("research_areas") or [])
        rev_areas = set(reviewer.get("research_areas") or [])
        shared = sorted(user_areas & rev_areas)
        if shared:
            explanations.append(f"Expertise overlap: {_fmt_list([a.title() for a in shared])}")
        else:
            explanations.append("Strong expertise alignment with your manuscript")

    # Publication record
    pub_count = reviewer.get("published_count", 0) or reviewer.get("publication_count", 0)
    if pub_count and sub_scores.get("publication_score", 0) > 0:
        explanations.append(f"Strong publication record ({pub_count} published works)")

    # Review history
    review_count = reviewer.get("review_count", 0)
    if review_count and sub_scores.get("review_history_score", 0) > 0:
        explanations.append(f"Experienced reviewer ({review_count} completed reviews)")

    # Seniority
    if sub_scores.get("seniority_score", 0) >= 15:
        role = reviewer.get("academic_role", "").replace("_", " ").title()
        explanations.append(f"Senior academic ({role})")

    # Country diversity
    if sub_scores.get("country_diversity", 0) > 0:
        explanations.append("No conflict of interest — different institution and country")
    else:
        explanations.append("No conflict of interest detected")

    return explanations


def explain_mentor(user_p: dict, mentor: dict, sub_scores: dict) -> list[str]:
    """
    Return a list of human-readable bullet strings explaining the mentor recommendation.
    """
    explanations: list[str] = []

    # Expertise alignment
    user_areas = set(user_p.get("research_areas") or [])
    mentor_areas = set(mentor.get("research_areas") or [])
    shared = sorted(user_areas & mentor_areas)
    if shared and sub_scores.get("area_score", 0) > 0:
        explanations.append(f"Expertise alignment: {_fmt_list([a.title() for a in shared])}")

    # Keyword overlap
    if sub_scores.get("kw_score", 0) > 0:
        explanations.append("Shared research keywords — strong topical fit")

    # Reputation
    rep = mentor.get("reputation_score", 0)
    if rep and sub_scores.get("rep_score", 0) > 0:
        explanations.append(f"Highly regarded researcher (reputation score: {rep})")

    # Publication record
    pub_count = mentor.get("published_count", 0) or mentor.get("publication_count", 0)
    if pub_count and sub_scores.get("publication_score", 0) > 0:
        explanations.append(f"Strong publication record ({pub_count} published works)")

    # Teaching activity
    if sub_scores.get("teaching_score", 0) > 0:
        explanations.append("Active in teaching and mentorship activities")

    return explanations
