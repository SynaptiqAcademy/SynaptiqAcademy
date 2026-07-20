"""Academic Career Intelligence — Career Profiler (Phase XVI)."""
from __future__ import annotations

from typing import Any

from .models import CareerProfile, CareerStage


def _sf(v: Any, d: float = 0.0) -> float:
    try:
        return float(v) if v is not None else d
    except (TypeError, ValueError):
        return d


def _si(v: Any, d: int = 0) -> int:
    try:
        return int(v) if v is not None else d
    except (TypeError, ValueError):
        return d


def _lst(v: Any) -> list[str]:
    if isinstance(v, list):
        return [str(x).strip() for x in v if x]
    return []


# ── Career stage detection ────────────────────────────────────────────────────

_STAGE_KEYWORDS: dict[str, CareerStage] = {
    "undergraduate": CareerStage.UNDERGRADUATE,
    "bachelor":      CareerStage.UNDERGRADUATE,
    "bsc":           CareerStage.UNDERGRADUATE,
    "master":        CareerStage.MASTER_STUDENT,
    "msc":           CareerStage.MASTER_STUDENT,
    "mres":          CareerStage.MASTER_STUDENT,
    "phd student":   CareerStage.PHD_CANDIDATE,
    "phd candidate": CareerStage.PHD_CANDIDATE,
    "postdoc":       CareerStage.POSTDOC,
    "postdoctoral":  CareerStage.POSTDOC,
    "research fellow": CareerStage.POSTDOC,
    "doctoral":      CareerStage.PHD_CANDIDATE,
    "assistant professor": CareerStage.ASSISTANT_PROF,
    "assistant prof":     CareerStage.ASSISTANT_PROF,
    "associate professor": CareerStage.ASSOCIATE_PROF,
    "associate prof":     CareerStage.ASSOCIATE_PROF,
    "full professor":   CareerStage.PROFESSOR,
    "professor":        CareerStage.PROFESSOR,
    "lecturer":         CareerStage.LECTURER,
    "senior lecturer":  CareerStage.ASSOCIATE_PROF,
    "senior researcher": CareerStage.SENIOR_RESEARCHER,
    "principal investigator": CareerStage.SENIOR_RESEARCHER,
    "pi ":               CareerStage.SENIOR_RESEARCHER,
    "researcher":        CareerStage.RESEARCHER,
    "scientist":         CareerStage.RESEARCHER,
    "director":          CareerStage.ADMINISTRATOR,
    "dean":              CareerStage.ADMINISTRATOR,
    "rector":            CareerStage.ADMINISTRATOR,
    "department head":   CareerStage.ADMINISTRATOR,
    "industry":          CareerStage.INDUSTRY,
    "r&d":               CareerStage.INDUSTRY,
    "engineer":          CareerStage.INDUSTRY,
}


def _detect_stage(user: dict) -> CareerStage:
    pos = (user.get("position") or user.get("user_type") or "").lower()
    for kw, stage in _STAGE_KEYWORDS.items():
        if kw in pos:
            return stage
    # Fallback heuristics
    h     = _sf(user.get("h_index", 0))
    pubs  = _si(user.get("publication_count", 0))
    if pubs == 0 and h == 0:
        return CareerStage.PHD_CANDIDATE
    if h < 3 and pubs < 5:
        return CareerStage.POSTDOC
    if h < 8:
        return CareerStage.ASSISTANT_PROF
    if h < 15:
        return CareerStage.ASSOCIATE_PROF
    return CareerStage.PROFESSOR


def _years_active(user: dict, stage: CareerStage) -> int:
    """Estimate years active in research from career stage and metrics."""
    if stage == CareerStage.UNDERGRADUATE:
        return 0
    if stage == CareerStage.MASTER_STUDENT:
        return 1
    if stage == CareerStage.PHD_CANDIDATE:
        return max(1, _si(user.get("phd_year", 2)))
    if stage == CareerStage.POSTDOC:
        return max(3, _si(user.get("publication_count", 0)) // 2 + 3)
    pubs = _si(user.get("publication_count", 0))
    return max(1, pubs // 4 + 4)


def _productivity_score(user: dict, years: int) -> float:
    pubs = _si(user.get("publication_count", 0))
    per_year = pubs / max(years, 1)
    return min(per_year / 5.0, 1.0)


def _quality_score(user: dict) -> float:
    h      = _sf(user.get("h_index", 0))
    pubs   = _si(user.get("publication_count", 0))
    q1     = _sf(user.get("q1_ratio", 0))
    h_score = min(h / 20.0, 1.0)
    p_score = min(pubs / 50.0, 1.0)
    q_score = q1 if q1 > 0 else h_score * 0.5
    return round((h_score * 0.5 + p_score * 0.2 + q_score * 0.3), 3)


def _impact_score(user: dict) -> float:
    cites = _si(user.get("citation_count", 0))
    pubs  = _si(user.get("publication_count", 0))
    h     = _sf(user.get("h_index", 0))
    cites_per_pub = cites / max(pubs, 1)
    return min((cites_per_pub / 20.0) * 0.4 + (h / 30.0) * 0.6, 1.0)


# ── Public function ───────────────────────────────────────────────────────────

def build_career_profile(user: dict) -> CareerProfile:
    """Build a CareerProfile from any MongoDB user document."""
    uid     = str(user.get("_id") or user.get("id") or "")
    stage   = _detect_stage(user)
    years   = _years_active(user, stage)
    prod    = _productivity_score(user, years)
    qual    = _quality_score(user)
    imp     = _impact_score(user)
    overall = round(prod * 0.3 + qual * 0.3 + imp * 0.3 + min(_sf(user.get("h_index", 0)) / 20, 1.0) * 0.1, 3)

    return CareerProfile(
        user_id=uid,
        name=user.get("full_name") or user.get("name") or "",
        institution=user.get("institution") or "",
        department=user.get("department") or user.get("faculty") or "",
        country=user.get("country") or "",
        position=user.get("position") or user.get("user_type") or "",
        career_stage=stage,
        years_active=years,
        h_index=_sf(user.get("h_index", 0)),
        publication_count=_si(user.get("publication_count", 0)),
        citation_count=_si(user.get("citation_count", 0)),
        grant_count=_si(user.get("grant_count", 0)),
        grant_income=_sf(user.get("grant_income", 0)),
        collaboration_count=_si(user.get("collaboration_count", 0)),
        international_collab_ratio=_sf(user.get("international_collab_ratio", 0)),
        review_count=_si(user.get("peer_review_count", 0)),
        conference_count=_si(user.get("conference_count", 0)),
        research_areas=_lst(user.get("research_areas") or user.get("domains") or []),
        research_methods=_lst(user.get("research_methods") or []),
        statistical_expertise=_lst(user.get("statistical_expertise") or []),
        programming_skills=_lst(user.get("programming_skills") or []),
        languages=_lst(user.get("languages") or []),
        teaching_areas=_lst(user.get("teaching_areas") or []),
        availability=_sf(user.get("availability", 0.7)),
        productivity_score=prod,
        quality_score=qual,
        impact_score=imp,
        overall_score=overall,
    )
