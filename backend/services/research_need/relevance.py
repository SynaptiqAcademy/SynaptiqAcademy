"""Research-Need <-> profile RELEVANCE layer.

This is deliberately NOT services/collab_intelligence/matching_engine.py.
That engine answers "how compatible are these two researchers with each
other" (career-stage fit, availability, diversity, etc. — dimensions that
only make sense between two people). This module answers a different
question: "how well does this one profile's real, already-safe-serialized
fields cover the expertise a research question needs" — there is no second
person on the other side of this comparison, so the canonical engine's
weighted person-to-person formula does not apply and is intentionally left
untouched. If a future phase wants to blend the two (e.g. "people compatible
with me AND relevant to this need"), that blend belongs in a caller, not
inside either engine.

Candidate retrieval reuses services/network/discovery_engine.search_people()
directly — one call, so every Phase 8B eligibility/privacy rule (self
exclusion, blocking, demo/staff exclusion, show_in_discovery, private
profiles) applies for free, and evidence is computed only from the fields
that function already serializes as public-safe.
"""
from __future__ import annotations

import re

from services.network import discovery_engine as discovery
from .models import ResearchNeed

# Result-card fields worth scanning for evidence, and which "kind" of match
# each counts as. Order matters only for readability of the evidence list.
_SIMILAR_FIELDS = ("research_areas", "research_interests", "research_keywords")
_COMPLEMENTARY_FIELDS = ("professional_expertise", "professional_role")
_METHOD_FIELDS = ("methods", "software_skills")
_ROLE_FIELDS = ("academic_role", "professional_role", "user_type")

_MAX_QUERY_TERMS = 20
_DEFAULT_POOL_SIZE = 50


def _regex_or(terms: list[str]) -> str:
    escaped = [re.escape(t) for t in terms[:_MAX_QUERY_TERMS] if t]
    return "|".join(escaped)


def _field_values(person: dict, field: str) -> list[str]:
    v = person.get(field)
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def _term_matches(term: str, value: str) -> bool:
    t = term.strip().lower()
    v = (value or "").strip().lower()
    return bool(t) and bool(v) and (t in v or v in t)


def _evidence_for(person: dict, terms: list[str], fields: tuple[str, ...]) -> list[dict]:
    hits: list[dict] = []
    for field in fields:
        for value in _field_values(person, field):
            for term in terms:
                if _term_matches(term, value):
                    hits.append({"field": field, "value": value, "matched_term": term})
                    break
    return hits


def _explanation(person: dict, similar_ev: list[dict], complementary_ev: list[dict], method_ev: list[dict]) -> str:
    parts = []
    if similar_ev:
        vals = ", ".join(sorted({e["value"] for e in similar_ev})[:3])
        parts.append(f"lists {vals}")
    if complementary_ev:
        vals = ", ".join(sorted({e["value"] for e in complementary_ev})[:2])
        parts.append(f"brings complementary expertise in {vals}")
    if method_ev:
        vals = ", ".join(sorted({e["value"] for e in method_ev})[:2])
        parts.append(f"uses {vals}")
    if not parts:
        return "Limited profile information available to explain this match."
    name = person.get("name") or "This researcher"
    return f"{name} " + "; ".join(parts) + "."


async def find_relevant_people(db, need: ResearchNeed, *, viewer_id: str | None, limit: int = _DEFAULT_POOL_SIZE) -> dict:
    """Retrieve real, eligible candidates and group/explain them against the
    Research Need. Never invents a candidate — an empty pool returns an
    honest empty result, not a fabricated one (§20)."""
    terms = need.all_terms()
    filters: dict = {}
    if terms:
        filters["q"] = _regex_or(terms)

    pool = await discovery.search_people(db, filters, page=1, limit=limit, viewer_id=viewer_id)

    similar_terms = need.required_expertise + need.topics + need.research_domains + need.disciplines
    complementary_terms = need.complementary_expertise + need.interdisciplinary_connections + need.relevant_professional_roles
    method_terms = need.useful_methods + need.useful_software_or_tools

    similar_group: list[dict] = []
    complementary_group: list[dict] = []
    methods_group: list[dict] = []
    covered_terms: set[str] = set()

    for person in pool["results"]:
        similar_ev = _evidence_for(person, similar_terms, _SIMILAR_FIELDS) if similar_terms else []
        complementary_ev = _evidence_for(person, complementary_terms, _COMPLEMENTARY_FIELDS + _ROLE_FIELDS) if complementary_terms else []
        method_ev = _evidence_for(person, method_terms, _METHOD_FIELDS) if method_terms else []

        # Also allow the raw research_keywords to surface similar-expertise
        # evidence even when the AI (or fallback) didn't separately name
        # required_expertise — keeps the fallback path useful (§4).
        if not similar_ev and need.research_keywords:
            similar_ev = _evidence_for(person, need.research_keywords, _SIMILAR_FIELDS)

        if not (similar_ev or complementary_ev or method_ev):
            continue  # no evidence to honestly explain this candidate — drop, don't guess

        for ev in (similar_ev, complementary_ev, method_ev):
            covered_terms.update(e["matched_term"].lower() for e in ev)

        card = dict(person)
        card["evidence"] = similar_ev + complementary_ev + method_ev
        card["explanation"] = _explanation(person, similar_ev, complementary_ev, method_ev)

        if similar_ev:
            similar_group.append(card)
        elif complementary_ev:
            complementary_group.append(card)
        else:
            methods_group.append(card)

    named_expertise = [t for t in (need.required_expertise + need.complementary_expertise) if t]
    missing_expertise = [
        t for t in named_expertise
        if t.strip().lower() not in covered_terms
        and not any(_term_matches(t, c) for c in covered_terms)
    ]

    return {
        "similar": similar_group,
        "complementary": complementary_group,
        "methods_specialists": methods_group,
        "missing_expertise": missing_expertise,
        "pool_total": pool["total"],
    }
