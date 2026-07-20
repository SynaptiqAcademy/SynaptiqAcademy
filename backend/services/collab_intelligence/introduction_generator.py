"""Research Collaboration Intelligence — Smart Introduction Generator (Phase XIV).

Generates narrative introductions explaining WHY two researchers should collaborate.
Template-based, no LLM required.
"""
from __future__ import annotations

from .models import CollabType, ResearcherProfile, SmartIntroduction
from .matching_engine import match_researchers

_NARRATIVE_TEMPLATES: dict[CollabType, str] = {
    CollabType.CO_AUTHOR: (
        "{name_a} and {name_b} share research interests in {shared_domains} and have "
        "complementary expertise in {comp_skills}. A co-authored publication would leverage "
        "both researchers' strengths, combining {a_methods} with {b_methods}."
    ),
    CollabType.MENTOR: (
        "{name_b}, with expertise in {shared_domains} and an h-index of {b_h}, "
        "is well positioned to mentor {name_a} in their research career. "
        "Their shared interests in {shared_domains} ensure productive knowledge transfer."
    ),
    CollabType.SUPERVISOR: (
        "{name_b} ({b_institution}) offers doctoral supervision aligned with "
        "{name_a}'s research interests in {shared_domains}. "
        "{name_b}'s research record (h-index: {b_h}, {b_pubs} publications) "
        "reflects strong supervisory capacity."
    ),
    CollabType.INTERNATIONAL: (
        "{name_a} ({a_country}) and {name_b} ({b_country}) represent a valuable "
        "international collaboration. Cross-border partnerships in {shared_domains} "
        "typically generate 40% more citations. Their complementary expertise in "
        "{comp_skills} creates a strong foundation for joint publication."
    ),
    CollabType.INTERDISCIPLINARY: (
        "{name_a}'s background in {a_domains} and {name_b}'s expertise in {b_domains} "
        "create a unique interdisciplinary opportunity. Combining these perspectives "
        "could produce high-impact research that neither could achieve independently."
    ),
    CollabType.GRANT_PARTNER: (
        "{name_a} and {name_b} form a competitive grant team. Their combined expertise "
        "covers {shared_domains} and {comp_skills}, addressing funding agency priorities. "
        "Together they span {a_country} and {b_country}, strengthening international "
        "competitiveness."
    ),
    CollabType.REVIEWER: (
        "{name_b}'s expertise in {shared_domains} makes them an ideal peer reviewer "
        "for {name_a}'s work. With {b_pubs} publications and {b_h} h-index, "
        "{name_b} can provide rigorous, constructive feedback."
    ),
    CollabType.CONFERENCE: (
        "{name_a} and {name_b} both work in {shared_domains}. Connecting at a "
        "joint conference session could initiate a productive academic partnership, "
        "with strong potential for co-authored work in {comp_skills}."
    ),
}


def _fmt(name: str | None, fallback: str) -> str:
    return name.strip() if name and name.strip() else fallback


def generate_introduction(
    a: ResearcherProfile,
    b: ResearcherProfile,
) -> SmartIntroduction:
    m = match_researchers(a, b)

    shared       = sorted(a.all_interests() & b.all_interests())[:4]
    comp_skills  = sorted((a.all_skills() | a.all_methods()) ^ (b.all_skills() | b.all_methods()))[:4]
    a_domains    = list(a.domains)[:3]
    b_domains    = list(b.domains)[:3]
    a_methods    = list(a.all_methods())[:2]
    b_methods    = list(b.all_methods())[:2]

    name_a = _fmt(a.name, "Researcher A")
    name_b = _fmt(b.name, "Researcher B")

    fmt_vars = {
        "name_a": name_a,
        "name_b": name_b,
        "shared_domains": ", ".join(shared) or "overlapping research areas",
        "comp_skills":    ", ".join(comp_skills) or "complementary skills",
        "a_domains":      ", ".join(a_domains) or "research domain",
        "b_domains":      ", ".join(b_domains) or "research domain",
        "a_methods":      ", ".join(a_methods) or "research methods",
        "b_methods":      ", ".join(b_methods) or "research methods",
        "a_country":      a.country or "their country",
        "b_country":      b.country or "their country",
        "a_institution":  a.institution or "their institution",
        "b_institution":  b.institution or "their institution",
        "b_h":            str(int(b.h_index)) if b.h_index else "N/A",
        "b_pubs":         str(b.publication_count),
    }

    tpl = _NARRATIVE_TEMPLATES.get(m.collab_type, _NARRATIVE_TEMPLATES[CollabType.CO_AUTHOR])
    try:
        narrative = tpl.format(**fmt_vars)
    except KeyError:
        narrative = _NARRATIVE_TEMPLATES[CollabType.CO_AUTHOR].format(**fmt_vars)

    # Expected outcomes based on profiles
    expected_outcomes: list[str] = []
    if m.publication_synergy > 0.5:
        expected_outcomes.append("1-3 co-authored publications within 2 years")
    if m.grant_compatibility > 0.6:
        expected_outcomes.append("Joint grant application within 12 months")
    if a.country != b.country and a.country and b.country:
        expected_outcomes.append("International research network expansion")
    if m.citation_overlap > 0.5:
        expected_outcomes.append("Mutual citation network growth")
    if not expected_outcomes:
        expected_outcomes.append("Research collaboration and knowledge exchange")

    # Collaboration hooks
    hooks: list[str] = []
    if shared:
        hooks.append(f"Discuss shared research in {shared[0]}")
    if comp_skills:
        hooks.append(f"Explore how {comp_skills[0]} expertise complements your work")
    if a.institution != b.institution and a.institution and b.institution:
        hooks.append("Propose joint research project across institutions")
    hooks.append("Review each other's recent publications")
    hooks.append("Identify shared funding opportunities")

    return SmartIntroduction(
        researcher_a_id=a.user_id,
        researcher_b_id=b.user_id,
        narrative=narrative,
        shared_interests=list(shared),
        complementary_expertise=list(comp_skills),
        expected_outcomes=expected_outcomes,
        collaboration_hooks=hooks[:4],
        match_score=m.overall_score,
    )
