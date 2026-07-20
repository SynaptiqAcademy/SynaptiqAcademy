"""Research Collaboration Intelligence — Recommendation Engine (Phase XIV).

Ranks and returns multi-type recommendations: researchers, institutions,
labs, research groups, and international partners.
"""
from __future__ import annotations

from .models import Recommendation, ResearcherProfile
from .matching_engine import match_researchers


def _researcher_recommendations(
    source: ResearcherProfile,
    candidates: list[ResearcherProfile],
    top_n: int = 10,
) -> list[Recommendation]:
    recs: list[Recommendation] = []
    for c in candidates:
        if c.user_id == source.user_id:
            continue
        m = match_researchers(source, c)
        shared = sorted(source.all_interests() & c.all_interests())[:3]
        reason = (
            f"{m.collab_type.value.replace('_', ' ').title()} match: "
            f"{', '.join(shared) or 'compatible research profiles'}. "
            f"Score: {m.overall_score:.2f}."
        )
        tags: list[str] = []
        if source.country != c.country and c.country:
            tags.append("international")
        if not (set(source.domains) & set(c.domains)):
            tags.append("interdisciplinary")
        if m.grant_compatibility > 0.7:
            tags.append("grant-ready")
        recs.append(Recommendation(
            target_id=c.user_id,
            target_type="researcher",
            target_name=c.name,
            score=m.overall_score,
            reason=reason,
            tags=tags,
        ))
    return sorted(recs, key=lambda r: -r.score)[:top_n]


def _institution_recommendations(
    source: ResearcherProfile,
    candidates: list[ResearcherProfile],
    top_n: int = 5,
) -> list[Recommendation]:
    """Recommend institutions via their researchers."""
    inst_scores: dict[str, list[float]] = {}
    inst_names: dict[str, str] = {}

    for c in candidates:
        if not c.institution or c.user_id == source.user_id:
            continue
        if c.institution.lower() == source.institution.lower():
            continue
        m = match_researchers(source, c)
        inst_key = c.institution.lower()
        inst_scores.setdefault(inst_key, []).append(m.overall_score)
        inst_names[inst_key] = c.institution

    recs: list[Recommendation] = []
    for key, scores in inst_scores.items():
        avg_score = sum(scores) / len(scores)
        boost = min(len(scores) / 5.0, 1.0) * 0.1
        recs.append(Recommendation(
            target_id=key,
            target_type="institution",
            target_name=inst_names[key],
            score=round(min(avg_score + boost, 1.0), 3),
            reason=f"{len(scores)} compatible researcher(s) at this institution.",
            tags=["institution"],
        ))
    return sorted(recs, key=lambda r: -r.score)[:top_n]


def _country_recommendations(
    source: ResearcherProfile,
    candidates: list[ResearcherProfile],
    top_n: int = 5,
) -> list[Recommendation]:
    country_scores: dict[str, list[float]] = {}

    for c in candidates:
        if not c.country or c.user_id == source.user_id:
            continue
        if c.country.lower() == source.country.lower():
            continue
        m = match_researchers(source, c)
        country_scores.setdefault(c.country, []).append(m.overall_score)

    recs: list[Recommendation] = []
    for country, scores in country_scores.items():
        avg = sum(scores) / len(scores)
        recs.append(Recommendation(
            target_id=country.lower().replace(" ", "_"),
            target_type="country",
            target_name=country,
            score=round(avg, 3),
            reason=f"{len(scores)} compatible researcher(s) in {country}.",
            tags=["international", "country"],
        ))
    return sorted(recs, key=lambda r: -r.score)[:top_n]


def generate_recommendations(
    source: ResearcherProfile,
    candidates: list[ResearcherProfile],
    include_types: list[str] | None = None,
    top_n: int = 10,
) -> dict[str, list[Recommendation]]:
    """Generate ranked recommendations across all types."""
    types = set(include_types or ["researcher", "institution", "country"])
    result: dict[str, list[Recommendation]] = {}

    if "researcher" in types:
        result["researchers"] = _researcher_recommendations(source, candidates, top_n)
    if "institution" in types:
        result["institutions"] = _institution_recommendations(source, candidates)
    if "country" in types:
        result["countries"] = _country_recommendations(source, candidates)

    return result


def serialize_recommendations(recs: dict[str, list[Recommendation]]) -> dict:
    return {k: [r.to_dict() for r in v] for k, v in recs.items()}
