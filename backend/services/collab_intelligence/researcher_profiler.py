"""Research Collaboration Intelligence — Researcher Profiler (Phase XIV).

Builds a rich ResearcherProfile from a MongoDB user document.
All scoring is deterministic and requires no external calls.
"""
from __future__ import annotations

import re
from typing import Any

from .models import CareerStage, CompetencyGraph, ResearcherProfile
from .competency_graph import build_competency_graph

# Career stage heuristics (year since PhD or self-reported)
_STAGE_KEYWORDS: dict[CareerStage, list[str]] = {
    CareerStage.STUDENT:      ["phd student", "doctoral", "graduate student", "msc", "undergrad"],
    CareerStage.POSTDOC:      ["postdoc", "post-doctoral", "research fellow", "postdoctoral"],
    CareerStage.EARLY_CAREER: ["assistant professor", "lecturer", "early career", "research associate"],
    CareerStage.MID_CAREER:   ["associate professor", "senior lecturer", "reader"],
    CareerStage.SENIOR:       ["professor", "full professor", "chair", "distinguished"],
    CareerStage.EMERITUS:     ["emeritus", "retired"],
}


def _infer_career_stage(user: dict) -> CareerStage:
    position = (user.get("position") or user.get("academic_position") or "").lower()
    user_type = (user.get("user_type") or "").lower()
    combined = f"{position} {user_type}"

    for stage, keywords in _STAGE_KEYWORDS.items():
        if any(kw in combined for kw in keywords):
            return stage
    return CareerStage.EARLY_CAREER


def _safe_list(val: Any) -> list[str]:
    if isinstance(val, list):
        return [str(v).strip() for v in val if v]
    if isinstance(val, str) and val.strip():
        return [v.strip() for v in re.split(r"[,;|]", val) if v.strip()]
    return []


def _productivity_score(user: dict) -> float:
    """Normalised score 0-1 based on publication + citation volume."""
    pubs    = int(user.get("publication_count", 0) or 0)
    cites   = int(user.get("citation_count", 0) or 0)
    h       = float(user.get("h_index", 0) or 0)

    pub_s  = min(pubs / 50.0, 1.0)
    cite_s = min(cites / 1000.0, 1.0)
    h_s    = min(h / 20.0, 1.0)
    return round((pub_s * 0.4 + cite_s * 0.3 + h_s * 0.3), 3)


def _quality_score(user: dict) -> float:
    """Proxy for publication quality via h-index relative to volume."""
    pubs = int(user.get("publication_count", 0) or 0)
    h    = float(user.get("h_index", 0) or 0)
    if pubs == 0:
        return 0.0
    # h/pubs ratio normalised by 0.5 (good researcher h = half of pubs)
    ratio = (h / pubs) / 0.5 if pubs > 0 else 0.0
    return round(min(ratio, 1.0), 3)


def _impact_score(user: dict) -> float:
    cites = int(user.get("citation_count", 0) or 0)
    h     = float(user.get("h_index", 0) or 0)
    return round(min((cites / 500.0 * 0.5 + h / 20.0 * 0.5), 1.0), 3)


def build_researcher_profile(user: dict) -> ResearcherProfile:
    """Convert a MongoDB user document into a ResearcherProfile."""
    uid   = str(user.get("_id") or user.get("id") or user.get("user_id", ""))
    name  = user.get("full_name") or user.get("name") or f"{user.get('first_name','')} {user.get('last_name','')}".strip()

    domains  = _safe_list(user.get("research_areas") or user.get("domains") or user.get("research_interests"))
    keywords = _safe_list(user.get("keywords") or user.get("research_keywords"))
    methods  = _safe_list(user.get("research_methods") or user.get("methods"))
    stats    = _safe_list(user.get("statistical_expertise") or user.get("statistics"))
    progs    = _safe_list(user.get("programming_skills") or user.get("software_skills"))
    langs    = _safe_list(user.get("languages") or [user.get("language", "English")])

    if not langs:
        langs = ["English"]

    collab_count = int(
        user.get("collaboration_count") or
        user.get("active_collaborations") or
        len(user.get("collaborators", [])) or 0
    )

    intl_ratio = float(user.get("international_collab_ratio", 0) or 0)
    if intl_ratio == 0 and collab_count > 0:
        intl_collab = int(user.get("international_collaborations", 0) or 0)
        if intl_collab:
            intl_ratio = min(intl_collab / collab_count, 1.0)

    availability = float(user.get("availability") or user.get("availability_score") or 0.5)
    response_rate = float(user.get("response_rate") or 0.7)

    productivity = _productivity_score(user)
    quality      = _quality_score(user)
    impact       = _impact_score(user)

    competency = build_competency_graph(
        user_id=uid,
        domains=domains,
        keywords=keywords,
        methods=methods,
        stats=stats,
        progs=progs,
        peer_review_count=int(user.get("peer_review_count", 0) or 0),
        grant_success_rate=float(user.get("grant_success_rate", 0) or 0),
        h_index=float(user.get("h_index", 0) or 0),
    )

    return ResearcherProfile(
        user_id=uid,
        name=name,
        institution=user.get("institution") or user.get("university") or "",
        department=user.get("department") or user.get("faculty") or "",
        country=user.get("country") or "",
        languages=langs,
        career_stage=_infer_career_stage(user),
        domains=domains,
        keywords=keywords,
        methods=methods,
        statistical_expertise=stats,
        programming_skills=progs,
        h_index=float(user.get("h_index", 0) or 0),
        publication_count=int(user.get("publication_count", 0) or 0),
        citation_count=int(user.get("citation_count", 0) or 0),
        collaboration_count=collab_count,
        international_collab_ratio=intl_ratio,
        availability=availability,
        response_rate=response_rate,
        productivity_score=productivity,
        quality_score=quality,
        impact_score=impact,
        competency_graph=competency,
    )
