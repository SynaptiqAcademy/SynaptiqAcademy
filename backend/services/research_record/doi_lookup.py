"""DOI metadata lookup — Crossref + OpenAlex, merged into one preview shape.

Reuses the existing, already-correct provider implementations rather than
writing a third DOI parser:
  - services/integrity/providers.py::CrossrefProvider (only existing
    Crossref caller that extracts `publisher`)
  - services/integrity/providers.py::OpenAlexProvider (DOI-filtered
    single-work lookup)

Stateless: never touches the database, never persists anything. Used by the
preview endpoint; the confirm endpoint is a separate, explicit step (see
routers/research_record.py).
"""
from __future__ import annotations

import asyncio
import logging

from services.integrity.providers import CrossrefProvider, OpenAlexProvider
from services.research_record.doi_normalize import normalize_doi

log = logging.getLogger("synaptiq.research_record")

_CROSSREF_TYPE_MAP = {
    "journal-article":    "journal_article",
    "proceedings-article": "conference_paper",
    "book":                "book",
    "book-chapter":        "book_chapter",
    "monograph":           "book",
    "posted-content":      "preprint",
    "dataset":              "dataset",
    "report":               "other",
}


def _year_from_pub_date(pub_date: str | None) -> int | None:
    if not pub_date:
        return None
    try:
        return int(str(pub_date).split("-")[0])
    except (ValueError, IndexError):
        return None


def _merge_authors(crossref_authors: list[dict], openalex_authorships: list[dict]) -> list[dict]:
    """Crossref authors have given/family/orcid (structured, reliable for
    matching); OpenAlex authorships have a display name + an OpenAlex author
    id (not an ORCID id). Prefer Crossref's structured names; fall back to
    OpenAlex only when Crossref returned none."""
    if crossref_authors:
        out = []
        for a in crossref_authors:
            name = f"{a.get('given', '')} {a.get('family', '')}".strip() or a.get("family", "")
            if not name:
                continue
            orcid = (a.get("orcid") or "").rstrip("/").rsplit("/", 1)[-1] or None
            out.append({"display_name": name, "orcid_id": orcid, "is_external": True})
        return out
    return [
        {"display_name": a.get("name", ""), "orcid_id": None, "is_external": True}
        for a in openalex_authorships if a.get("name")
    ]


async def lookup_doi(doi: str) -> dict:
    """Validate + normalize a DOI, fetch Crossref + OpenAlex in parallel, and
    return a single merged preview. Never persists anything.

    Returns:
        {
          "doi": "<bare normalized doi>",
          "found": bool,               # true if at least one source had it
          "title": str, "journal": str, "publisher": str, "year": int|None,
          "url": str, "record_type": str, "authors": [...],
          "sources_used": ["crossref"|"openalex", ...],
          "citations_count": int,
          "is_retracted": bool,
        }

    Raises ValueError if `doi` doesn't pass format validation — never
    fabricates metadata for an invalid or unresolvable DOI.
    """
    bare_doi = normalize_doi(doi)
    if not bare_doi:
        raise ValueError(f"Invalid DOI format: {doi!r}")

    crossref_result, openalex_result = await asyncio.gather(
        CrossrefProvider().verify("publication", {"doi": bare_doi}),
        OpenAlexProvider().verify("publication", {"doi": bare_doi}),
        return_exceptions=True,
    )
    if isinstance(crossref_result, Exception):
        log.warning("Crossref lookup failed for %s: %s", bare_doi, crossref_result)
        crossref_result = {"found": False, "data": {}}
    if isinstance(openalex_result, Exception):
        log.warning("OpenAlex lookup failed for %s: %s", bare_doi, openalex_result)
        openalex_result = {"found": False, "data": {}}

    cr = crossref_result.get("data") or {} if crossref_result.get("found") else {}
    oa = openalex_result.get("data") or {} if openalex_result.get("found") else {}
    sources_used = [n for n, d in (("crossref", cr), ("openalex", oa)) if d]

    if not sources_used:
        return {
            "doi": bare_doi, "found": False,
            "title": "", "journal": "", "publisher": "", "year": None,
            "url": f"https://doi.org/{bare_doi}", "record_type": "other",
            "authors": [], "sources_used": [], "citations_count": 0,
            "is_retracted": False,
        }

    title   = cr.get("title") or oa.get("title") or ""
    journal = cr.get("journal") or oa.get("source") or ""
    year    = _year_from_pub_date(cr.get("pub_date")) or _year_from_pub_date(oa.get("publication_date"))
    record_type = _CROSSREF_TYPE_MAP.get(cr.get("type", ""), "other")

    return {
        "doi": bare_doi,
        "found": True,
        "title": title,
        "journal": journal,
        "publisher": cr.get("publisher") or "",
        "year": year,
        "url": f"https://doi.org/{bare_doi}",
        "record_type": record_type,
        "authors": _merge_authors(cr.get("authors") or [], oa.get("authorships") or []),
        "sources_used": sources_used,
        "citations_count": max(cr.get("citations_count") or 0, oa.get("cited_by_count") or 0),
        "is_retracted": bool(oa.get("is_retracted")),
    }
