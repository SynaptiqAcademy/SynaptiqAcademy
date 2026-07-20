"""OpenAlex citation provider.

Implements CitationProvider against the OpenAlex REST API v1.
Doc: https://docs.openalex.org/

Polite pool: sends mailto= in User-Agent per OpenAlex guidelines.
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import httpx

from .base import (
    CitationProvider, CitationSyncResult, CitingWork, PublicationMatch,
)

log = logging.getLogger("synaptiq.citations.openalex")

BASE       = "https://api.openalex.org"
MAILTO     = os.environ.get("OPENALEX_MAILTO", "admin@synaptiq.academy")
HEADERS    = {"User-Agent": f"SYNAPTIQ/1.0 (mailto:{MAILTO})"}
TIMEOUT    = 12


def _work_to_match(w: dict) -> PublicationMatch:
    ids = w.get("ids") or {}
    doi_raw = ids.get("doi") or w.get("doi") or ""
    doi = doi_raw.replace("https://doi.org/", "").replace("http://doi.org/", "").lower().strip() or None

    concepts = [c["display_name"] for c in (w.get("concepts") or [])[:8] if c.get("display_name")]
    topics   = [t["display_name"] for t in (w.get("topics")   or [])[:8] if t.get("display_name")]

    coauthors = []
    for a in (w.get("authorships") or [])[:20]:
        author = a.get("author") or {}
        insts  = a.get("institutions") or [{}]
        coauthors.append({
            "name":        author.get("display_name"),
            "orcid":       author.get("orcid"),
            "institution": insts[0].get("display_name") if insts else None,
        })

    counts_by_year = sorted(
        [{"year": r["year"], "count": r.get("cited_by_count", 0)}
         for r in (w.get("counts_by_year") or []) if r.get("year")],
        key=lambda x: x["year"],
    )

    primary_loc = w.get("primary_location") or {}
    source      = primary_loc.get("source") or {}
    journal     = source.get("display_name")

    oa = (w.get("best_oa_location") or {})
    oa_url = oa.get("pdf_url") or oa.get("landing_page_url")

    return PublicationMatch(
        provider_id    = w.get("id", ""),
        doi            = doi,
        title          = w.get("title"),
        year           = w.get("publication_year"),
        journal        = journal,
        citation_count = int(w.get("cited_by_count") or 0),
        concepts       = concepts,
        topics         = topics,
        coauthors      = coauthors,
        counts_by_year = counts_by_year,
        open_access_url = oa_url,
    )


def _citing_work_from(w: dict) -> CitingWork:
    ids = w.get("ids") or {}
    doi_raw = ids.get("doi") or w.get("doi") or ""
    doi = doi_raw.replace("https://doi.org/", "").lower().strip() or None
    primary = w.get("primary_location") or {}
    source  = primary.get("source") or {}
    return CitingWork(
        provider_id    = w.get("id", ""),
        doi            = doi,
        title          = w.get("title"),
        year           = w.get("publication_year"),
        journal        = source.get("display_name"),
        citation_count = int(w.get("cited_by_count") or 0),
    )


class OpenAlexProvider(CitationProvider):
    """Full implementation of CitationProvider against OpenAlex."""

    @property
    def name(self) -> str:
        return "openalex"

    # ── search ───────────────────────────────────────────────────────────────

    async def search_publication(
        self,
        *,
        doi: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Optional[PublicationMatch]:
        async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as cli:
            if doi:
                clean = doi.strip().lower()
                if clean.startswith("http"):
                    clean = clean.split("doi.org/", 1)[-1]
                try:
                    r = await cli.get(f"{BASE}/works/doi:{clean}")
                    if r.status_code == 200:
                        return _work_to_match(r.json())
                except Exception as e:
                    log.warning("OpenAlex DOI lookup failed (%s): %s", doi, e)

            if title:
                try:
                    r = await cli.get(f"{BASE}/works", params={
                        "search": title[:200],
                        "per_page": 1,
                        "select": "id,doi,title,publication_year,cited_by_count,"
                                  "primary_location,concepts,topics,authorships,"
                                  "counts_by_year,best_oa_location,ids",
                    })
                    if r.status_code == 200:
                        results = r.json().get("results") or []
                        if results:
                            return _work_to_match(results[0])
                except Exception as e:
                    log.warning("OpenAlex title search failed (%s): %s", title[:60], e)

        return None

    # ── count ────────────────────────────────────────────────────────────────

    async def get_citation_count(self, provider_id: str) -> int:
        async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as cli:
            try:
                r = await cli.get(provider_id, params={"select": "cited_by_count"})
                if r.status_code == 200:
                    return int(r.json().get("cited_by_count") or 0)
            except Exception as e:
                log.warning("get_citation_count failed (%s): %s", provider_id, e)
        return 0

    # ── history ──────────────────────────────────────────────────────────────

    async def get_citation_history(self, provider_id: str) -> list[dict]:
        async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as cli:
            try:
                r = await cli.get(provider_id, params={"select": "counts_by_year"})
                if r.status_code == 200:
                    rows = r.json().get("counts_by_year") or []
                    return sorted(
                        [{"year": row["year"], "count": int(row.get("cited_by_count") or 0)}
                         for row in rows if row.get("year")],
                        key=lambda x: x["year"],
                    )
            except Exception as e:
                log.warning("get_citation_history failed (%s): %s", provider_id, e)
        return []

    # ── citing works ─────────────────────────────────────────────────────────

    async def get_citing_works(
        self, provider_id: str, *, limit: int = 20
    ) -> list[CitingWork]:
        # OpenAlex work IDs are URLs like https://openalex.org/W123...
        # strip to short form for filter
        short_id = provider_id.split("/")[-1] if "/" in provider_id else provider_id
        async with httpx.AsyncClient(timeout=TIMEOUT, headers=HEADERS) as cli:
            try:
                r = await cli.get(f"{BASE}/works", params={
                    "filter": f"cites:{short_id}",
                    "sort":   "publication_year:desc",
                    "per_page": min(limit, 25),
                    "select": "id,doi,title,publication_year,cited_by_count,"
                              "primary_location,ids",
                })
                if r.status_code == 200:
                    return [_citing_work_from(w) for w in (r.json().get("results") or [])]
            except Exception as e:
                log.warning("get_citing_works failed (%s): %s", provider_id, e)
        return []

    # ── full sync ────────────────────────────────────────────────────────────

    async def sync_publication(
        self,
        *,
        doi: Optional[str] = None,
        title: Optional[str] = None,
    ) -> CitationSyncResult:
        match = await self.search_publication(doi=doi, title=title)
        if not match:
            return CitationSyncResult(found=False, provider=self.name, publication=None,
                                      error="No OpenAlex match found")

        citing = await self.get_citing_works(match.provider_id, limit=20)
        return CitationSyncResult(
            found=True,
            provider=self.name,
            publication=match,
            citing_works=citing,
        )
