"""Deduplication for the Academic Research Record.

CRITICAL architectural rule (per the approved design): a publication is a
GLOBAL academic work, not something scoped to a single Synaptiq user. DOI
lookup therefore searches `publications` by `doi` alone — never scoped by
`owner_id` — so that two Synaptiq co-authors (or an ORCID import + a manual
entry + a Crossref-discovered enrichment) converge onto the SAME document
instead of each user's action creating their own private copy.

Non-DOI records are deliberately NOT merged on a title-only match (the
existing ORCID pipeline's `title_norm`-only fallback is a known, confirmed
risk — see the Phase 1 design audit). A low-confidence match is returned for
review rather than silently merged or silently overwritten.
"""
from __future__ import annotations

import re


def _norm_title(title: str) -> str:
    return re.sub(r"\s+", " ", (title or "").lower().strip())


async def find_by_doi(db, doi: str) -> dict | None:
    """Global lookup — the normalized DOI is the sole match key. No owner_id
    scoping: this is what makes multiple Synaptiq users, and multiple import
    sources, converge onto one canonical record."""
    if not doi:
        return None
    return await db.publications.find_one({"doi": doi})


async def find_candidate_by_title(
    db, title: str, authors: list[dict] | None = None, year: int | None = None,
) -> dict | None:
    """Best-effort candidate for a DOI-less record. Returns the candidate
    together with a confidence score; NEVER auto-merges here — the caller
    decides what to do with a low-confidence match (route to user review,
    per Step 8 of the design)."""
    title_norm = _norm_title(title)
    if not title_norm:
        return None
    candidates = await db.publications.find({"title_norm": title_norm}).to_list(10)
    if not candidates:
        return None

    author_names = {
        (a.get("display_name") or "").strip().lower()
        for a in (authors or []) if a.get("display_name")
    }

    best = None
    best_confidence = 0.0
    for cand in candidates:
        confidence = 0.5  # title_norm exact match alone is only a starting point
        cand_year = cand.get("year")
        if year and cand_year:
            if year == cand_year:
                confidence += 0.3
            elif abs(year - cand_year) <= 1:
                confidence += 0.1
            else:
                confidence -= 0.2
        cand_author_names = {
            (a.get("display_name") or "").strip().lower()
            for a in (cand.get("authors") or []) if isinstance(a, dict) and a.get("display_name")
        }
        if author_names and cand_author_names:
            overlap = len(author_names & cand_author_names) / max(len(author_names | cand_author_names), 1)
            confidence += overlap * 0.3
        confidence = max(0.0, min(confidence, 1.0))
        if confidence > best_confidence:
            best, best_confidence = cand, confidence

    if best is None:
        return None
    return {"candidate": best, "confidence": round(best_confidence, 3)}


# A match below this bar is never auto-merged — routed to review instead.
NON_DOI_AUTO_MERGE_THRESHOLD = 0.8
