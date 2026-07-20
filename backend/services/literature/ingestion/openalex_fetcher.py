"""OpenAlex ingestion — rich scholarly metadata (no auth required)."""
from __future__ import annotations

import logging
import re
import urllib.parse

import httpx

from services.literature.ingestion.base import IngestionResult, _clean
from services.literature.models import Paper, PaperSource

log = logging.getLogger("synaptiq.literature.openalex")

_BASE = "https://api.openalex.org"
_HEADERS = {
    "User-Agent": "Synaptiq/1.0 (mailto:admin@synaptiq.academy)",
}


async def fetch_by_doi(doi: str) -> IngestionResult:
    return await _fetch(f"{_BASE}/works/doi:{doi}", source_id=doi)


async def fetch_by_pmid(pmid: str) -> IngestionResult:
    return await _fetch(f"{_BASE}/works/pmid:{pmid}", source_id=pmid)


async def fetch_by_openalex_id(openalex_id: str) -> IngestionResult:
    oid = openalex_id.strip()
    if not oid.startswith("https://"):
        oid = f"https://openalex.org/{oid}"
    return await _fetch(f"{_BASE}/works/{urllib.parse.quote(oid, safe=':/.')}", source_id=openalex_id)


async def search_openalex(query: str, limit: int = 20) -> list[Paper]:
    """Full-text search across OpenAlex works."""
    params = {
        "search": query,
        "per-page": min(limit, 200),
        "select": "id,title,authorships,publication_year,primary_location,doi,cited_by_count,"
                  "keywords,abstract_inverted_index,open_access,referenced_works_count",
    }
    try:
        async with httpx.AsyncClient(timeout=20.0, headers=_HEADERS) as client:
            resp = await client.get(f"{_BASE}/works", params=params)
            resp.raise_for_status()
            results = resp.json().get("results", [])
    except Exception as exc:
        log.warning("OpenAlex search failed: %s", exc)
        return []

    papers = []
    for item in results:
        p = _parse_work(item)
        if p:
            papers.append(p)
    return papers


# ── Internal helpers ───────────────────────────────────────────────────────────

async def _fetch(url: str, source_id: str = "") -> IngestionResult:
    try:
        async with httpx.AsyncClient(timeout=15.0, headers=_HEADERS) as client:
            resp = await client.get(url)
            if resp.status_code == 404:
                return IngestionResult(success=False, error=f"OpenAlex: not found ({source_id})",
                                       source=PaperSource.OPENALEX, source_id=source_id)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        return IngestionResult(success=False, error=f"OpenAlex request failed: {exc}",
                               source=PaperSource.OPENALEX, source_id=source_id)

    paper = _parse_work(data)
    if not paper:
        return IngestionResult(success=False, error="OpenAlex: could not parse response",
                               source=PaperSource.OPENALEX, source_id=source_id)
    return IngestionResult(success=True, paper=paper, source=PaperSource.OPENALEX, source_id=source_id)


def _parse_work(data: dict) -> Paper | None:
    try:
        title = _clean(data.get("title", ""))
        if not title:
            return None

        authors = []
        for auth in data.get("authorships", []):
            a = auth.get("author", {})
            name = a.get("display_name", "")
            if name:
                authors.append(name)

        year = data.get("publication_year", 0) or 0

        doi = (data.get("doi") or "").replace("https://doi.org/", "")

        # Abstract from inverted index (OpenAlex encodes it this way)
        abstract = _decode_inverted_index(data.get("abstract_inverted_index"))

        # Source / journal
        loc = data.get("primary_location", {}) or {}
        source = loc.get("source", {}) or {}
        journal = _clean(source.get("display_name", ""))

        # Keywords
        kws = [k.get("display_name", "") for k in data.get("keywords", []) if k.get("display_name")]

        # Institutions
        institutions = []
        for auth in data.get("authorships", [])[:3]:
            for inst in auth.get("institutions", []):
                name = inst.get("display_name", "")
                if name and name not in institutions:
                    institutions.append(name)

        openalex_id = data.get("id", "")
        pmid = ""
        ids = data.get("ids", {})
        if ids:
            pmid = (ids.get("pmid") or "").replace("https://pubmed.ncbi.nlm.nih.gov/", "").strip("/")

        return Paper(
            source=PaperSource.OPENALEX,
            source_id=openalex_id,
            title=title,
            authors=authors,
            year=year,
            abstract=abstract,
            doi=doi,
            pmid=pmid,
            openalex_id=openalex_id,
            journal=journal,
            keywords=kws,
            citation_count=data.get("cited_by_count", 0),
            reference_count=data.get("referenced_works_count", 0),
            institution=institutions[0] if institutions else "",
            open_access=(data.get("open_access", {}) or {}).get("is_oa", False),
            url=f"https://doi.org/{doi}" if doi else openalex_id,
            raw_metadata={"openalex_id": openalex_id, "doi": doi},
        )
    except Exception as exc:
        log.debug("OpenAlex parse error: %s", exc)
        return None


def _decode_inverted_index(inv: dict | None) -> str:
    """Reconstruct abstract from OpenAlex inverted index format."""
    if not inv:
        return ""
    try:
        max_pos = max(pos for positions in inv.values() for pos in positions)
        words = [""] * (max_pos + 1)
        for word, positions in inv.items():
            for pos in positions:
                if 0 <= pos <= max_pos:
                    words[pos] = word
        return " ".join(w for w in words if w)
    except Exception:
        return ""
