"""Research Collaboration Intelligence — Multi-dimensional Matching Engine (Phase XIV).

Calculates 9-dimension compatibility between researcher profiles. All scoring is
deterministic rule-based, requiring no LLM calls. Each dimension returns 0-1.
"""
from __future__ import annotations

from .models import CareerStage, CollabMatch, CollabType, ResearcherProfile

# ── Dimension weights (sum to 1.0) ────────────────────────────────────────────
_WEIGHTS = {
    "research_similarity":         0.25,
    "complementarity":             0.20,
    "methodological_compatibility":0.15,
    "publication_synergy":         0.10,
    "citation_overlap":            0.08,
    "grant_compatibility":         0.07,
    "diversity_score":             0.07,
    "availability_compatibility":  0.05,
    "career_stage_compatibility":  0.03,
}

_CAREER_COMPAT: dict[tuple[CareerStage, CareerStage], float] = {
    (CareerStage.STUDENT,      CareerStage.EARLY_CAREER):  0.7,
    (CareerStage.STUDENT,      CareerStage.MID_CAREER):    0.5,
    (CareerStage.STUDENT,      CareerStage.SENIOR):        0.4,
    (CareerStage.POSTDOC,      CareerStage.EARLY_CAREER):  0.85,
    (CareerStage.POSTDOC,      CareerStage.MID_CAREER):    0.75,
    (CareerStage.POSTDOC,      CareerStage.SENIOR):        0.6,
    (CareerStage.EARLY_CAREER, CareerStage.EARLY_CAREER):  0.90,
    (CareerStage.EARLY_CAREER, CareerStage.MID_CAREER):    0.85,
    (CareerStage.MID_CAREER,   CareerStage.MID_CAREER):    0.95,
    (CareerStage.MID_CAREER,   CareerStage.SENIOR):        0.85,
    (CareerStage.SENIOR,       CareerStage.SENIOR):        0.90,
}


def _jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def _complementarity(a: set, b: set) -> float:
    """How much does A offer B and vice versa? Measures mutual value."""
    if not a or not b:
        return 0.0
    a_offers_b = len(b - a) / len(b)      # fraction of B's interests A can complement
    b_offers_a = len(a - b) / len(a)      # fraction of A's interests B can complement
    # High complementarity = both offer each other something without total overlap
    return (a_offers_b + b_offers_a) / 2.0 * min(len(a & b) / max(len(a | b) * 0.2, 1), 1.0) + 0.3


def _research_similarity(a: ResearcherProfile, b: ResearcherProfile) -> float:
    domain_j = _jaccard(set(a.domains), set(b.domains))
    keyword_j = _jaccard(a.all_interests(), b.all_interests())
    return round(domain_j * 0.5 + keyword_j * 0.5, 3)


def _complementarity_score(a: ResearcherProfile, b: ResearcherProfile) -> float:
    a_int = a.all_interests()
    b_int = b.all_interests()
    if not a_int or not b_int:
        return 0.3
    # Optimal complementarity: ~30-60% overlap
    overlap = len(a_int & b_int) / len(a_int | b_int) if a_int | b_int else 0
    if 0.25 <= overlap <= 0.65:
        score = 0.8 + (overlap - 0.25) / 0.4 * 0.2
    elif overlap < 0.25:
        score = max(0.2, overlap * 3.0)
    else:
        score = max(0.3, 1.0 - (overlap - 0.65) * 2.0)
    # Bonus for complementary skills
    a_skills = a.all_skills() | a.all_methods()
    b_skills = b.all_skills() | b.all_methods()
    skill_comp = len((a_skills - b_skills) | (b_skills - a_skills)) / max(len(a_skills | b_skills), 1)
    return round(min(score + skill_comp * 0.2, 1.0), 3)


def _method_compatibility(a: ResearcherProfile, b: ResearcherProfile) -> float:
    a_m = a.all_methods()
    b_m = b.all_methods()
    if not a_m and not b_m:
        return 0.5
    j = _jaccard(a_m, b_m)
    # Some shared + some different = best compatibility
    if 0.2 <= j <= 0.7:
        return round(0.75 + j * 0.2, 3)
    return round(max(0.4, j), 3)


def _publication_synergy(a: ResearcherProfile, b: ResearcherProfile) -> float:
    a_active = a.publication_count > 0
    b_active = b.publication_count > 0
    if not a_active or not b_active:
        return 0.3
    a_q = a.quality_score
    b_q = b.quality_score
    # Combined quality potential
    synergy = (a_q + b_q) / 2.0 * 0.7 + min(a.h_index, b.h_index) / 20.0 * 0.3
    return round(min(synergy, 1.0), 3)


def _citation_overlap(a: ResearcherProfile, b: ResearcherProfile) -> float:
    # Proxy: same domains → likely shared citation networks
    if not a.domains or not b.domains:
        return 0.2
    j = _jaccard(set(a.domains), set(b.domains))
    return round(j * 0.8 + 0.1, 3)


def _grant_compatibility(a: ResearcherProfile, b: ResearcherProfile) -> float:
    a_g = a.competency_graph.grant_success_rate if a.competency_graph else 0.0
    b_g = b.competency_graph.grant_success_rate if b.competency_graph else 0.0
    # If one has strong grant history, makes team more competitive
    combined = min(a_g + b_g, 1.0)
    return round(max(combined, 0.3), 3)


def _diversity_score(a: ResearcherProfile, b: ResearcherProfile) -> float:
    score = 0.5
    if a.institution and b.institution and a.institution.lower() != b.institution.lower():
        score += 0.2   # different institution
    if a.country and b.country and a.country.lower() != b.country.lower():
        score += 0.2   # different country = international
    if a.languages and b.languages:
        shared_langs = set(l.lower() for l in a.languages) & set(l.lower() for l in b.languages)
        if shared_langs:
            score += 0.1
    return round(min(score, 1.0), 3)


def _availability_compat(a: ResearcherProfile, b: ResearcherProfile) -> float:
    # Compatibility is higher when both are available
    return round((a.availability * b.availability) ** 0.5, 3)


def _career_stage_compat(a: ResearcherProfile, b: ResearcherProfile) -> float:
    pair = (a.career_stage, b.career_stage)
    if pair in _CAREER_COMPAT:
        return _CAREER_COMPAT[pair]
    rev_pair = (b.career_stage, a.career_stage)
    if rev_pair in _CAREER_COMPAT:
        return _CAREER_COMPAT[rev_pair]
    return 0.7  # same stage by default


def _infer_collab_type(a: ResearcherProfile, b: ResearcherProfile, similarity: float) -> CollabType:
    # Mentorship signals
    stage_pair = {a.career_stage, b.career_stage}
    if CareerStage.SENIOR in stage_pair and CareerStage.STUDENT in stage_pair:
        return CollabType.SUPERVISOR
    if CareerStage.SENIOR in stage_pair and CareerStage.EARLY_CAREER in stage_pair:
        return CollabType.MENTOR

    # International
    if a.country and b.country and a.country.lower() != b.country.lower():
        return CollabType.INTERNATIONAL

    # Interdisciplinary
    if a.domains and b.domains:
        if len(set(a.domains) & set(b.domains)) == 0:
            return CollabType.INTERDISCIPLINARY

    return CollabType.CO_AUTHOR


def _build_explanation(
    a: ResearcherProfile,
    b: ResearcherProfile,
    similarity: float,
    complementarity: float,
    collab_type: CollabType,
) -> str:
    shared = list(a.all_interests() & b.all_interests())[:3]
    comp_a = list(a.all_interests() - b.all_interests())[:2]
    comp_b = list(b.all_interests() - a.all_interests())[:2]

    parts: list[str] = []
    if shared:
        parts.append(f"Shared research interests: {', '.join(shared)}")
    if comp_a:
        parts.append(f"{a.name or 'Researcher A'} brings: {', '.join(comp_a)}")
    if comp_b:
        parts.append(f"{b.name or 'Researcher B'} brings: {', '.join(comp_b)}")
    if a.country != b.country and a.country and b.country:
        parts.append(f"International collaboration opportunity ({a.country} ↔ {b.country})")
    if a.institution != b.institution and a.institution and b.institution:
        parts.append(f"Cross-institutional collaboration ({a.institution} ↔ {b.institution})")

    if collab_type == CollabType.MENTOR:
        parts.append("Mentorship opportunity based on career stage difference")
    elif collab_type == CollabType.INTERDISCIPLINARY:
        parts.append("High interdisciplinary potential — distinct domain expertise")

    return ". ".join(parts) or "Compatible research profiles with strong collaboration potential."


def match_researchers(a: ResearcherProfile, b: ResearcherProfile) -> CollabMatch:
    """Calculate multi-dimensional compatibility between two researcher profiles."""
    sim   = _research_similarity(a, b)
    comp  = _complementarity_score(a, b)
    meth  = _method_compatibility(a, b)
    pub   = _publication_synergy(a, b)
    cit   = _citation_overlap(a, b)
    grant = _grant_compatibility(a, b)
    div   = _diversity_score(a, b)
    avail = _availability_compat(a, b)
    stage = _career_stage_compat(a, b)

    overall = (
        sim   * _WEIGHTS["research_similarity"] +
        comp  * _WEIGHTS["complementarity"] +
        meth  * _WEIGHTS["methodological_compatibility"] +
        pub   * _WEIGHTS["publication_synergy"] +
        cit   * _WEIGHTS["citation_overlap"] +
        grant * _WEIGHTS["grant_compatibility"] +
        div   * _WEIGHTS["diversity_score"] +
        avail * _WEIGHTS["availability_compatibility"] +
        stage * _WEIGHTS["career_stage_compatibility"]
    )

    collab_type = _infer_collab_type(a, b, sim)
    shared_kws  = sorted(a.all_interests() & b.all_interests())[:8]
    comp_skills = sorted((a.all_skills() | a.all_methods()) ^ (b.all_skills() | b.all_methods()))[:8]
    explanation = _build_explanation(a, b, sim, comp, collab_type)

    return CollabMatch(
        researcher_a_id=a.user_id,
        researcher_b_id=b.user_id,
        overall_score=round(overall, 3),
        research_similarity=sim,
        complementarity=comp,
        methodological_compatibility=meth,
        publication_synergy=pub,
        citation_overlap=cit,
        grant_compatibility=grant,
        diversity_score=div,
        availability_compatibility=avail,
        career_stage_compatibility=stage,
        shared_keywords=list(shared_kws),
        complementary_skills=list(comp_skills),
        explanation=explanation,
        collab_type=collab_type,
    )


def rank_matches(
    source: ResearcherProfile,
    candidates: list[ResearcherProfile],
    top_n: int = 10,
) -> list[CollabMatch]:
    """Rank all candidates by compatibility with source, return top_n."""
    matches = [match_researchers(source, c) for c in candidates if c.user_id != source.user_id]
    matches.sort(key=lambda m: -m.overall_score)
    return matches[:top_n]
