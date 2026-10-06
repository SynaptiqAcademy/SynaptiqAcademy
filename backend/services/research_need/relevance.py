"""Research-Need <-> profile RELEVANCE layer.

This is deliberately NOT services/collab_intelligence/matching_engine.py.
That engine answers "how compatible are these two researchers with each
other" (career-stage fit, availability, diversity, etc. — dimensions that
only make sense between two people). This module answers a different
question: "how well does this one profile's real, already-safe-serialized
fields (plus its batched, title-only publication evidence) cover the
expertise a research question needs" — there is no second person on the
other side of this comparison, so the canonical engine's weighted
person-to-person formula does not apply and is intentionally left
untouched. If a future phase wants to blend the two (e.g. "people
compatible with me AND relevant to this need"), that blend belongs in a
caller, not inside either engine.

Candidate retrieval reuses services/network/discovery_engine.search_people()
directly — one call, so every Phase 8B eligibility/privacy rule (self
exclusion, blocking, demo/staff exclusion, show_in_discovery, private
profiles) applies for free, and evidence is computed only from the fields
that function already serializes as public-safe, plus publication titles
(the only field publication_evidence.py exposes).
"""
from __future__ import annotations

import re

from services.network import discovery_engine as discovery
from .models import ResearchNeed
from .publication_evidence import batch_publication_titles
from . import evidence as ev

_SIMILAR_FIELDS = ("research_areas", "research_interests", "research_keywords")
_COMPLEMENTARY_FIELDS = ("professional_expertise", "professional_role")
_METHOD_FIELDS = ("methods", "software_skills")

_MAX_QUERY_TERMS = 20
_DEFAULT_POOL_SIZE = 50


def _field_values(person: dict, field: str) -> list[str]:
    v = person.get(field)
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def _term_matches(term: str, value: str) -> bool:
    t = term.strip().lower()
    v = (value or "").strip().lower()
    return bool(t) and bool(v) and (t in v or v in t)


def _field_evidence(person: dict, terms: list[str], fields: tuple[str, ...], ev_type_by_field: dict[str, str], relationship: str) -> list[dict]:
    hits: list[dict] = []
    for field in fields:
        ev_type = ev_type_by_field[field]
        for value in _field_values(person, field):
            for term in terms:
                if _term_matches(term, value):
                    hits.append({"type": ev_type, "candidate_value": value, "need_value": term, "relationship": relationship})
                    break
    return hits


def _publication_evidence(person: dict, terms: list[str], titles: list[str]) -> list[dict]:
    hits: list[dict] = []
    for title in titles:
        for term in terms:
            if _term_matches(term, title):
                hits.append({"type": "publication", "candidate_value": title, "need_value": term, "relationship": "direct"})
                break
    return hits


def _context_evidence(person: dict, need: ResearchNeed) -> list[dict]:
    hits: list[dict] = []
    if need.geographic_context:
        country = person.get("country") or ""
        institution = person.get("institution") or ""
        if _term_matches(need.geographic_context, country) or _term_matches(need.geographic_context, institution):
            hits.append({
                "type": "geographic_context",
                "candidate_value": country or institution,
                "need_value": need.geographic_context,
                "relationship": "complementary",
            })
    if need.languages:
        for lang in _field_values(person, "languages"):
            for need_lang in need.languages:
                if _term_matches(need_lang, lang):
                    hits.append({"type": "language", "candidate_value": lang, "need_value": need_lang, "relationship": "complementary"})
                    break
    return hits


async def find_relevant_people(
    db,
    need: ResearchNeed,
    *,
    viewer_id: str | None,
    limit: int = _DEFAULT_POOL_SIZE,
    country: str | None = None,
    language: str | None = None,
    available_for_collaboration: bool | None = None,
    include_methods: bool = True,
    prioritize: str | None = None,
) -> dict:
    """Retrieve real, eligible candidates and group/explain them against the
    Research Need. Never invents a candidate — an empty pool returns an
    honest empty result, not a fabricated one (§20 of 8C / §14 of 8D).

    country/language/available_for_collaboration are real backend filters
    (§22 of 8D) — passed straight into discovery_engine's own filter
    handling, not decorative. include_methods drops methods-only matches
    from the pool when the user doesn't want technical-support candidates.
    prioritize swaps which label wins primary placement when a candidate
    qualifies for more than one (§12).

    Known scope limit: retrieval itself (the discovery.search_people call
    below) only ever runs against profile fields (research_areas/keywords/
    methods/etc. via `q`, plus the explicit country/language filters) — a
    candidate whose ONLY overlap with the need is a publication title, or
    is a geographic/language match with no matching profile field at all,
    is not retrieved into the pool in the first place, so publication and
    context evidence only ever enrich a candidate already retrieved via a
    real profile-field match. This keeps retrieval to one call (§26) rather
    than adding a second, publication-driven retrieval path; a future phase
    could lift this by unioning in owner_ids from a title-matching
    publications query, if that proves worth the extra query.
    """
    terms = need.all_terms()
    filters: dict = {}
    if terms:
        filters["q_terms"] = list(terms)
    if country:
        filters["country"] = country
    if language:
        filters["languages"] = language
    if available_for_collaboration is not None:
        filters["available_for_collaboration"] = available_for_collaboration

    pool = await discovery.search_people(db, filters, page=1, limit=limit, viewer_id=viewer_id)
    candidates = pool["results"]

    pub_titles_by_id = await batch_publication_titles(db, [p["id"] for p in candidates])

    similar_terms = need.required_expertise + need.topics + need.research_domains + need.disciplines + need.research_keywords
    complementary_terms = need.complementary_expertise + need.interdisciplinary_connections + need.relevant_professional_roles
    method_terms = need.useful_methods + need.useful_software_or_tools

    groups: dict[str, list[dict]] = {"directly_relevant": [], "complementary_expertise": [], "methods_specialist": [], "context_specialist": []}
    covered_terms: set[str] = set()

    for person in candidates:
        evidence: list[dict] = []
        if similar_terms:
            evidence += _field_evidence(
                person, similar_terms, _SIMILAR_FIELDS,
                {"research_areas": "research_area", "research_interests": "research_area", "research_keywords": "research_keyword"},
                "direct",
            )
        if complementary_terms:
            evidence += _field_evidence(
                person, complementary_terms, _COMPLEMENTARY_FIELDS,
                {"professional_expertise": "professional_expertise", "professional_role": "professional_role"},
                "complementary",
            )
        if method_terms and include_methods:
            evidence += _field_evidence(
                person, method_terms, _METHOD_FIELDS,
                {"methods": "method", "software_skills": "software_tool"},
                "direct",
            )
        titles = pub_titles_by_id.get(person["id"])
        if titles and (similar_terms or method_terms):
            evidence += _publication_evidence(person, similar_terms + method_terms, titles)
        evidence += _context_evidence(person, need)

        if not evidence:
            continue

        covered_terms.update(e["need_value"].strip().lower() for e in evidence)

        labels = ev.labels_for(evidence)
        primary = ev.primary_group(labels, prioritize=prioritize)
        if primary is None:
            continue

        card = dict(person)
        card["evidence"] = evidence
        card["explanation"] = ev.explanation_for(evidence)
        card["contribution"] = ev.contributions_for(evidence)
        card["relevance_labels"] = labels
        groups[primary].append(card)

    named_expertise = [t for t in (need.required_expertise + need.complementary_expertise) if t]
    coverage_map: list[dict] = []
    added: set[str] = set()
    for t in named_expertise:
        tl = t.strip().lower()
        if tl in added:
            continue
        added.add(tl)
        # Exact (case-insensitive) membership only — covered_terms already
        # holds the literal need_value strings that some candidate's
        # evidence actually matched. A fuzzy substring re-check here would
        # compare one need term against ANOTHER need term's text (not a
        # candidate's real field value) and can false-positive purely from
        # shared characters (e.g. "Uncovered X" contains "Covered X").
        coverage_map.append({"term": t, "covered": tl in covered_terms})

    missing_expertise = [c["term"] for c in coverage_map if not c["covered"]]

    return {
        "similar": groups["directly_relevant"],
        "complementary": groups["complementary_expertise"],
        "methods_specialists": groups["methods_specialist"],
        "context_specialists": groups["context_specialist"],
        "coverage_map": coverage_map,
        "missing_expertise": missing_expertise,
        "pool_total": pool["total"],
    }
