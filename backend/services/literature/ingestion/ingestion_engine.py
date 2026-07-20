"""Ingestion Engine — routes paper ingest requests to the appropriate fetcher."""
from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator

from services.literature.ingestion.base import IngestionResult
from services.literature.ingestion.doi_fetcher import fetch_by_doi as doi_fetch
from services.literature.ingestion.pmid_fetcher import fetch_by_pmid as pmid_fetch
from services.literature.ingestion.arxiv_fetcher import fetch_by_arxiv_id as arxiv_fetch
from services.literature.ingestion.openalex_fetcher import (
    fetch_by_doi as oa_doi_fetch,
    fetch_by_openalex_id as oa_id_fetch,
    search_openalex,
)
from services.literature.ingestion.semantic_scholar import (
    fetch_by_paper_id as s2_fetch,
    search_s2,
)
from services.literature.ingestion.file_parser import parse_file
from services.literature.models import Paper, PaperSource

log = logging.getLogger("synaptiq.literature.ingestion")

# Max concurrent ingest operations
_SEMAPHORE_SIZE = 5


class IngestionEngine:
    """Routes paper requests to the correct source and normalises results."""

    async def ingest_one(
        self,
        source: PaperSource,
        source_id: str,
        session_id: str = "",
    ) -> IngestionResult:
        """Ingest a single paper from an external API source."""
        result = await self._fetch(source, source_id)
        if result.success and result.paper:
            result.paper.session_id = session_id
        return result

    async def ingest_batch(
        self,
        items: list[tuple[PaperSource, str]],
        session_id: str = "",
    ) -> list[IngestionResult]:
        """Ingest multiple papers with bounded concurrency."""
        sem = asyncio.Semaphore(_SEMAPHORE_SIZE)

        async def _bounded(source: PaperSource, sid: str) -> IngestionResult:
            async with sem:
                return await self.ingest_one(source, sid, session_id)

        tasks = [_bounded(src, sid) for src, sid in items]
        return await asyncio.gather(*tasks)

    async def ingest_file(
        self,
        content: bytes,
        filename: str,
        session_id: str = "",
    ) -> IngestionResult:
        result = parse_file(content, filename, session_id)
        return result

    async def search(
        self,
        query: str,
        sources: list[str] | None = None,
        limit: int = 20,
    ) -> list[Paper]:
        """Search across enabled sources and merge deduplicated results."""
        sources = sources or ["openalex", "semantic_scholar"]
        tasks = []
        if "openalex" in sources:
            tasks.append(search_openalex(query, limit))
        if "semantic_scholar" in sources:
            tasks.append(search_s2(query, limit))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        papers: list[Paper] = []
        seen_dois: set[str] = set()
        seen_titles: set[str] = set()

        for batch in results:
            if isinstance(batch, Exception):
                continue
            for p in batch:
                # Deduplicate by DOI or normalised title
                key = p.doi.lower() if p.doi else ""
                title_key = _normalise_title(p.title)
                if key and key in seen_dois:
                    continue
                if title_key in seen_titles:
                    continue
                if key:
                    seen_dois.add(key)
                seen_titles.add(title_key)
                papers.append(p)

        return papers[:limit]

    async def enrich_with_openalex(self, paper: Paper) -> Paper:
        """Try to fetch richer metadata (citation count, institution) from OpenAlex."""
        if not paper.doi:
            return paper
        try:
            result = await oa_doi_fetch(paper.doi)
            if result.success and result.paper:
                oa = result.paper
                if oa.citation_count > paper.citation_count:
                    paper.citation_count = oa.citation_count
                if not paper.institution and oa.institution:
                    paper.institution = oa.institution
                if not paper.abstract and oa.abstract:
                    paper.abstract = oa.abstract
                if not paper.openalex_id and oa.openalex_id:
                    paper.openalex_id = oa.openalex_id
        except Exception:
            pass
        return paper

    # ── Private ───────────────────────────────────────────────────────────────

    async def _fetch(self, source: PaperSource, source_id: str) -> IngestionResult:
        if source == PaperSource.DOI:
            # Try CrossRef first, enrich with OpenAlex
            result = await doi_fetch(source_id)
            if result.success and result.paper:
                result.paper = await self.enrich_with_openalex(result.paper)
            return result
        if source == PaperSource.PMID:
            return await pmid_fetch(source_id)
        if source == PaperSource.ARXIV:
            return await arxiv_fetch(source_id)
        if source == PaperSource.OPENALEX:
            return await oa_id_fetch(source_id)
        if source == PaperSource.SEMANTIC_SCHOLAR:
            return await s2_fetch(source_id)
        return IngestionResult(success=False,
                               error=f"Source not supported for API ingest: {source.value}",
                               source=source, source_id=source_id)


def _normalise_title(title: str) -> str:
    import re
    return re.sub(r"\W+", "", title.lower())[:60]
