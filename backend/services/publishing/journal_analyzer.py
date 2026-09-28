"""Academic Publishing Intelligence — Journal analyzer.

Phase 0 rewrite: scores journals against a manuscript using only the live
`journals` collection (populated by services/discovery's OpenAlex/Crossref/
DOAJ ingestion pipeline). No hardcoded journal database, no invented
acceptance/desk-rejection/predatory-risk figures — see AUDIT_PHASE0.md for
the rationale. Seed/demo journal records (`is_seed: true`) are excluded.
"""
from __future__ import annotations

from db import get_db
from repo.security_context import SecurityContext
from repo.shim import DBProxy
from .models import JournalFitScore, JournalProfile

# Only real, currently-populated fields are used for matching.
_MAX_CANDIDATES = 300


def _as_list(v) -> list[str]:
    """Defensive normalization — some legacy/seed records store a
    comma-separated string where the schema expects a list."""
    if not v:
        return []
    if isinstance(v, list):
        return [str(x) for x in v if x]
    if isinstance(v, str):
        return [s.strip() for s in v.split(",") if s.strip()]
    return []


def _to_profile(j: dict) -> JournalProfile:
    return JournalProfile(
        id=str(j.get("_id", "")),
        name=j.get("title") or j.get("name") or "",
        publisher=j.get("publisher", ""),
        issn=j.get("issn") or (j.get("external_ids") or {}).get("issn_l", "") or "",
        quartile=j.get("quartile"),
        quartile_source=j.get("quartile_source"),
        h_index=j.get("h_index"),
        works_count=j.get("works_count"),
        cited_by_count=j.get("cited_by_count"),
        acceptance_rate=j.get("acceptance_rate"),
        open_access=bool(j.get("open_access", False)),
        apc_usd=j.get("apc_usd"),
        tags=_as_list(j.get("subjects")) + _as_list(j.get("research_areas")) + _as_list(j.get("scope_keywords")),
        language=j.get("language"),
        homepage_url=j.get("homepage_url"),
        source=j.get("source", ""),
        last_verified_at=j.get("last_seen_source_at") or j.get("last_synced_at"),
    )


def _scope_match(text_lower: str, discipline_lower: str, journal: JournalProfile) -> float:
    """Keyword/subject overlap between the manuscript and the journal's real
    subject/topic tags. Deterministic, no invented weighting beyond simple
    overlap — this is unchanged in spirit from the pre-Phase-0 heuristic,
    just fed real tags instead of a hardcoded tag list."""
    if not journal.tags:
        return 0.0
    tags_lower = [t.lower() for t in journal.tags if t]
    hits = sum(1 for t in tags_lower if t in text_lower or t in discipline_lower)
    return round(min(1.0, hits / max(len(tags_lower) * 0.4, 1)), 3)


def _overall_fit(scope: float, journal: JournalProfile) -> float:
    """Composite of only-real signals: scope match, a citation-strength
    proxy (h-index, when known), and whether we have enough real data to
    be confident at all. No acceptance/desk-rejection prediction."""
    citation_signal = 0.0
    if journal.h_index:
        citation_signal = min(1.0, journal.h_index / 100.0)
    quartile_bonus = {"Q1": 1.0, "Q2": 0.75, "Q3": 0.55, "Q4": 0.35}.get(journal.quartile or "", 0.5)
    return round(0.6 * scope + 0.25 * citation_signal + 0.15 * quartile_bonus, 3)


def _build_strengths_notes(journal: JournalProfile, scope: float) -> tuple[list[str], list[str]]:
    strengths: list[str] = []
    notes: list[str] = []

    if scope >= 0.6:
        strengths.append(f"Strong subject overlap with {journal.name}'s indexed topics")
    elif scope < 0.2:
        notes.append(f"Weak subject overlap — {journal.name}'s indexed topics may not match closely")

    if journal.open_access:
        strengths.append("Open access")
    if journal.apc_usd is not None:
        strengths.append(f"Article processing charge on record: ${journal.apc_usd:,}")
    else:
        notes.append("No article processing charge on record — confirm on the publisher site")

    if journal.h_index:
        strengths.append(f"h-index {journal.h_index} (OpenAlex)")

    if journal.quartile:
        label = "estimated from citation data" if journal.quartile_source == "openalex_estimate" else "as reported by source"
        notes.append(f"Quartile {journal.quartile} ({label}) — not a substitute for the publisher's official indexing status")
    else:
        notes.append("No quartile data available")

    if journal.acceptance_rate is None:
        notes.append("Acceptance rate not published by any connected source — not shown")

    return strengths[:4], notes[:4]


async def get_all_profiles(db=None, limit: int = _MAX_CANDIDATES) -> list[JournalProfile]:
    if db is None:
        db = DBProxy(get_db(), SecurityContext.system())
    docs = await db.journals.find({"is_seed": {"$ne": True}}).limit(limit).to_list(limit)
    return [_to_profile(j) for j in docs]


async def get_profile_by_id(journal_id: str, db=None) -> JournalProfile | None:
    from bson import ObjectId
    if db is None:
        db = DBProxy(get_db(), SecurityContext.system())
    try:
        oid = ObjectId(journal_id)
    except Exception:
        return None
    doc = await db.journals.find_one({"_id": oid, "is_seed": {"$ne": True}})
    return _to_profile(doc) if doc else None


async def analyze_journal_fit(
    text: str,
    discipline: str,
    manuscript_quality: float,
    db=None,
) -> list[JournalFitScore]:
    """Score real journals in the live collection against the manuscript.
    `manuscript_quality` is accepted for API compatibility with callers but
    no longer perturbs the score — there is no real basis for a
    quality-adjusted acceptance-probability estimate, so none is produced.
    """
    if db is None:
        db = DBProxy(get_db(), SecurityContext.system())

    text_lower = (text or "").lower()
    discipline_lower = (discipline or "").lower()

    journals = await get_all_profiles(db=db)
    scored: list[tuple[float, JournalFitScore]] = []

    for journal in journals:
        scope = _scope_match(text_lower, discipline_lower, journal)
        if scope == 0.0:
            continue

        fit = _overall_fit(scope, journal)
        strengths, notes = _build_strengths_notes(journal, scope)

        rationale = f"{journal.name} shows {scope:.0%} subject overlap with this manuscript"
        if journal.quartile:
            rationale += f" (quartile {journal.quartile}{'*' if journal.quartile_source == 'openalex_estimate' else ''})"
        rationale += "."

        fit_score = JournalFitScore(
            journal=journal,
            scope_match=scope,
            overall_fit=fit,
            strengths=strengths,
            notes=notes,
            rationale=rationale,
        )
        scored.append((fit, fit_score))

    scored.sort(key=lambda x: -x[0])
    return [fs for _, fs in scored]
