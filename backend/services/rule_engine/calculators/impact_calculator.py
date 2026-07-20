"""Reusable impact metric calculators (SIS component math, FWCI, etc.)."""
from __future__ import annotations

import math
from typing import Any


def _sat(value: float, scale: float = 10.0, max_pts: float = 100.0) -> float:
    """Logarithmic saturation: maps [0, ∞) → [0, max_pts)."""
    if value <= 0:
        return 0.0
    return round(max_pts * math.log(1 + value / scale) / math.log(1 + 10.0 / scale + 1e-9), 4)


def sis_research_output(
    n_published: int,
    n_submitted: int,
    n_drafted: int,
    max_pts: float = 2500.0,
) -> float:
    raw = min(n_published * 200, 1500) + min(n_submitted * 100, 500) + min(n_drafted * 25, 500)
    return min(raw, max_pts)


def sis_citation_impact(
    h_index: int,
    total_citations: int,
    max_pts: float = 2000.0,
) -> float:
    raw = h_index * 80 + math.log(total_citations + 1) * 100
    return min(raw, max_pts)


def sis_collaboration(
    active_collaborations: int,
    projects: int,
    international_count: int,
    max_pts: float = 1500.0,
) -> float:
    raw = (
        min(active_collaborations * 150, 750)
        + min(projects * 100, 500)
        + min(international_count * 50, 250)
    )
    return min(raw, max_pts)


def sis_grant_activity(
    n_submitted: int,
    n_funded: int,
    max_pts: float = 1000.0,
) -> float:
    raw = min(n_submitted * 200, 600) + min(n_funded * 400, 400)
    return min(raw, max_pts)


def sis_teaching(published_lessons: int, max_pts: float = 1000.0) -> float:
    return float(min(published_lessons * 100, max_pts))


def sis_review_activity(reviews_completed: int, max_pts: float = 500.0) -> float:
    return float(min(reviews_completed * 100, max_pts))


def sis_platform_reputation(overall_score: float, max_pts: float = 300.0) -> float:
    return min(overall_score / 17.0, max_pts)


def sis_profile_completeness(
    orcid_verified: bool,
    has_avatar: bool,
    has_bio: bool,
    has_institution: bool,
    has_research_areas: bool,
    has_keywords: bool,
    has_methods: bool,
    max_pts: float = 200.0,
) -> float:
    pts = 0.0
    if orcid_verified:
        pts += 50
    if has_avatar:
        pts += 25
    if has_bio:
        pts += 25
    if has_institution:
        pts += 25
    if has_research_areas:
        pts += 25
    if has_keywords:
        pts += 25
    if has_methods:
        pts += 25
    return min(pts, max_pts)


def compute_sis(components: dict[str, float]) -> dict[str, Any]:
    """Aggregate SIS from individual components dict."""
    total = sum(components.values())
    label = _sis_label(total)
    return {
        "sis_total": round(total),
        "sis_label": label,
        "components": {k: round(v, 1) for k, v in components.items()},
    }


def _sis_label(score: float) -> str:
    thresholds = [
        (9000, "Eminent Scholar"),
        (7000, "Distinguished Researcher"),
        (5000, "Senior Scholar"),
        (3000, "Established Researcher"),
        (1500, "Rising Scholar"),
        (500, "Emerging Scholar"),
        (0, "New Researcher"),
    ]
    for threshold, label in thresholds:
        if score >= threshold:
            return label
    return "New Researcher"


def field_weighted_citation_impact(
    citation_counts: list[int],
    expected_citations: list[float],
) -> float:
    """FWCI = (actual citations / expected citations for field+year)."""
    n = min(len(citation_counts), len(expected_citations))
    if n == 0:
        return 0.0
    total_actual = sum(citation_counts[:n])
    total_expected = sum(expected_citations[:n])
    if total_expected == 0:
        return 1.0
    return round(total_actual / total_expected, 3)


def research_productivity_score(
    publications_per_year: float,
    citations_per_year: float,
    grants_awarded: int,
    career_years: float,
) -> float:
    """0–100 productivity score."""
    pub_pts = _sat(publications_per_year, scale=2.0, max_pts=40.0)
    cit_pts = _sat(citations_per_year, scale=20.0, max_pts=35.0)
    grant_pts = _sat(grants_awarded, scale=1.0, max_pts=25.0)
    return round(min(pub_pts + cit_pts + grant_pts, 100.0), 1)


def career_progress_score(
    career_years: float,
    h_index: int,
    total_publications: int,
    total_grants: int,
    academic_role: str,
) -> float:
    """0–100 career progress score, benchmarked against expected career stage."""
    expected_h = _expected_h_by_stage(career_years, academic_role)
    expected_pubs = _expected_pubs_by_stage(career_years, academic_role)
    h_ratio = min(h_index / max(expected_h, 1), 1.5)
    pub_ratio = min(total_publications / max(expected_pubs, 1), 1.5)
    grant_bonus = min(total_grants * 5, 15)
    raw = (h_ratio * 40 + pub_ratio * 45 + grant_bonus)
    return round(min(raw, 100.0), 1)


def _expected_h_by_stage(career_years: float, role: str) -> float:
    base = {"phd_candidate": 2, "postdoctoral_researcher": 5, "university_faculty": 10,
            "researcher": 8, "industry_professional": 4}.get(role, 5)
    return max(base * math.sqrt(max(career_years, 1) / 5), 1.0)


def _expected_pubs_by_stage(career_years: float, role: str) -> float:
    rate = {"phd_candidate": 1.5, "postdoctoral_researcher": 3.0, "university_faculty": 4.0,
            "researcher": 3.0, "industry_professional": 1.0}.get(role, 2.0)
    return max(rate * max(career_years, 1), 1.0)
