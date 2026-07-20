"""Input source resolution for Research Gap Intelligence.

Extracts structured content (text, papers, analyses) from all supported sources.
Delegates to Literature Intelligence ingestion where available.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from .models import GapIntelligenceRequest, InputSource

log = logging.getLogger("synaptiq.research_gap.resolver")


@dataclass
class ResolvedContent:
    text: str = ""                        # combined raw text for AI analysis
    papers: list = field(default_factory=list)    # List[Paper] from lit engine
    analyses: list = field(default_factory=list)  # List[PaperAnalysis]
    source_descriptions: list[str] = field(default_factory=list)
    corpus_size: int = 0


async def resolve_inputs(
    request: GapIntelligenceRequest,
    db=None,
) -> ResolvedContent:
    """Resolve all input sources into a unified content object."""
    result = ResolvedContent()
    parts: list[str] = []

    # Start with inline content
    if request.content:
        parts.append(request.content)
        result.source_descriptions.append("inline text")

    # Pull from Literature Intelligence session if provided
    if request.lit_session_id:
        lit_content = await _resolve_lit_session(request.lit_session_id, db)
        if lit_content:
            parts.append(lit_content.text)
            result.papers.extend(lit_content.papers)
            result.analyses.extend(lit_content.analyses)
            result.source_descriptions.append(
                f"literature session ({len(lit_content.papers)} papers)"
            )

    # Fetch additional papers from API sources
    for src in request.input_sources:
        if src == InputSource.TEXT:
            continue   # already handled via request.content
        if src == InputSource.LIT_SESSION:
            continue   # already handled above
        try:
            fetched = await _fetch_from_source(src, request)
            if fetched:
                parts.append(fetched)
                result.source_descriptions.append(src.value)
        except Exception as exc:
            log.warning("Source %s fetch failed: %s", src.value, exc)

    result.text = "\n\n".join(p for p in parts if p)
    result.corpus_size = len(result.papers)
    return result


async def _resolve_lit_session(session_id: str, db) -> Optional[ResolvedContent]:
    """Pull papers and analyses from a Literature Intelligence session."""
    if db is None:
        return None
    try:
        from services.literature.engine import get_literature_engine
        engine = await get_literature_engine()
        session = await engine.get_session(session_id, "")   # admin-level, no user check
        if not session:
            return None

        papers_raw = await db.lit_papers.find(
            {"session_id": session_id}
        ).to_list(500)
        analyses_raw = await db.lit_paper_analyses.find(
            {"session_id": session_id}
        ).to_list(500)

        result = ResolvedContent()
        result.papers = [engine._doc_to_paper(p) for p in papers_raw]
        result.analyses = [engine._doc_to_analysis(a) for a in analyses_raw]

        # Build text block from abstracts and analyses
        text_parts = []
        for p in result.papers[:30]:
            if p.abstract:
                text_parts.append(f"Paper: {p.title} ({p.year})\nAbstract: {p.abstract}")
        result.text = "\n\n".join(text_parts)
        return result
    except Exception as exc:
        log.warning("Literature session resolution failed: %s", exc)
        return None


async def _fetch_from_source(source: InputSource, request: GapIntelligenceRequest) -> str:
    """Fetch additional content from external API sources."""
    if source in (InputSource.PDF, InputSource.DOCX, InputSource.MARKDOWN_FILE):
        return ""  # File sources are provided via request.content

    if source == InputSource.OPENALEX:
        return await _search_openalex(request.topic, limit=5)
    if source == InputSource.SEMANTIC_SCHOLAR:
        return await _search_s2(request.topic, limit=5)
    if source == InputSource.DOI:
        return ""  # DOI resolution happens via Literature Intelligence
    return ""


async def _search_openalex(topic: str, limit: int = 5) -> str:
    """Quick OpenAlex search for recent papers on the topic."""
    try:
        import httpx
        url = "https://api.openalex.org/works"
        params = {
            "search": topic,
            "per-page": limit,
            "select": "title,abstract_inverted_index,publication_year,primary_location",
            "mailto": "research@synaptiq.academy",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                return ""
            data = resp.json()
            parts = []
            for work in data.get("results", []):
                title = work.get("title", "")
                year = work.get("publication_year", "")
                abstract = _decode_inverted_index(work.get("abstract_inverted_index") or {})
                if title:
                    parts.append(f"Paper: {title} ({year})\nAbstract: {abstract}")
            return "\n\n".join(parts)
    except Exception:
        return ""


async def _search_s2(topic: str, limit: int = 5) -> str:
    """Quick Semantic Scholar search for recent papers."""
    try:
        import httpx
        url = "https://api.semanticscholar.org/graph/v1/paper/search"
        params = {
            "query": topic,
            "limit": limit,
            "fields": "title,abstract,year",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code != 200:
                return ""
            data = resp.json()
            parts = []
            for paper in data.get("data", []):
                title = paper.get("title", "")
                year = paper.get("year", "")
                abstract = paper.get("abstract", "") or paper.get("tldr", {}).get("text", "")
                if title:
                    parts.append(f"Paper: {title} ({year})\nAbstract: {abstract}")
            return "\n\n".join(parts)
    except Exception:
        return ""


def _decode_inverted_index(ii: dict) -> str:
    if not ii:
        return ""
    positions: dict[int, str] = {}
    for word, pos_list in ii.items():
        for pos in pos_list:
            positions[pos] = word
    return " ".join(positions[i] for i in sorted(positions))
