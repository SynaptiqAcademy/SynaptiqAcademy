"""Semantic Scholar ingestion via S2 API."""
from __future__ import annotations

import logging
import urllib.parse

import httpx

from services.literature.ingestion.base import IngestionResult, _clean
from services.literature.models import Paper, PaperSource

log = logging.getLogger("synaptiq.literature.s2")

_BASE = "https://api.semanticscholar.org/graph/v1/paper"
_FIELDS = (
    "title,authors,year,abstract,journal,externalIds,"
    "citationCount,referenceCount,fieldsOfStudy,"
    "isOpenAccess,publicationVenue,url,tldr"
)


async def fetch_by_paper_id(paper_id: str) -> IngestionResult:
    """Fetch by S2 paper ID, DOI, PMID, or arXiv ID.

    Supports formats: {s2_id}, DOI:{doi}, PMID:{pmid}, ARXIV:{arxiv_id}
    """
    paper_id = paper_id.strip()
    # Detect and normalise prefix
    if paper_id.startswith("10.") or "/" in paper_id[:8]:
        paper_id = f"DOI:{urllib.parse.quote(paper_id, safe='/')}"

    url = f"{_BASE}/{urllib.parse.quote(paper_id, safe='.:/')}"

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params={"fields": _FIELDS})
            if resp.status_code == 404:
                return IngestionResult(success=False,
                                       error=f"Semantic Scholar: not found ({paper_id})",
                                       source=PaperSource.SEMANTIC_SCHOLAR, source_id=paper_id)
            if resp.status_code == 429:
                return IngestionResult(success=False, error="Semantic Scholar rate limit reached",
                                       source=PaperSource.SEMANTIC_SCHOLAR, source_id=paper_id)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        return IngestionResult(success=False, error=f"S2 request failed: {exc}",
                               source=PaperSource.SEMANTIC_SCHOLAR, source_id=paper_id)

    paper = _parse(data, paper_id)
    if not paper:
        return IngestionResult(success=False, error="S2: could not parse response",
                               source=PaperSource.SEMANTIC_SCHOLAR, source_id=paper_id)
    return IngestionResult(success=True, paper=paper,
                           source=PaperSource.SEMANTIC_SCHOLAR, source_id=paper_id)


async def search_s2(query: str, limit: int = 20) -> list[Paper]:
    """Full-text search via Semantic Scholar."""
    params = {
        "query": query,
        "limit": min(limit, 100),
        "fields": _FIELDS,
    }
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(f"{_BASE}/search", params=params)
            resp.raise_for_status()
            results = resp.json().get("data", [])
    except Exception as exc:
        log.warning("S2 search failed: %s", exc)
        return []

    papers = []
    for item in results:
        p = _parse(item, item.get("paperId", ""))
        if p:
            papers.append(p)
    return papers


def _parse(data: dict, source_id: str) -> Paper | None:
    try:
        title = _clean(data.get("title", ""))
        if not title:
            return None

        authors = [a.get("name", "") for a in data.get("authors", []) if a.get("name")]
        year = data.get("year") or 0

        abstract = _clean(data.get("abstract", ""))
        # Use TLDR if no abstract
        if not abstract:
            tldr = data.get("tldr", {})
            if isinstance(tldr, dict):
                abstract = _clean(tldr.get("text", ""))

        ext_ids = data.get("externalIds", {}) or {}
        doi = ext_ids.get("DOI", "")
        pmid = str(ext_ids.get("PubMed", ""))
        arxiv_id = ext_ids.get("ArXiv", "")

        venue = data.get("publicationVenue", {}) or {}
        journal = _clean(venue.get("name", "") or data.get("journal", {}).get("name", ""))

        keywords = data.get("fieldsOfStudy", []) or []

        return Paper(
            source=PaperSource.SEMANTIC_SCHOLAR,
            source_id=source_id,
            title=title,
            authors=authors,
            year=year,
            abstract=abstract,
            journal=journal,
            doi=doi,
            pmid=pmid,
            arxiv_id=arxiv_id,
            url=data.get("url", ""),
            keywords=keywords,
            citation_count=data.get("citationCount", 0),
            reference_count=data.get("referenceCount", 0),
            open_access=data.get("isOpenAccess", False),
            raw_metadata={"s2_id": data.get("paperId", ""), "doi": doi},
        )
    except Exception as exc:
        log.debug("S2 parse error: %s", exc)
        return None
