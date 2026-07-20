"""arXiv ingestion via arXiv API (Atom XML)."""
from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET

import httpx

from services.literature.ingestion.base import IngestionResult, _clean
from services.literature.models import Paper, PaperSource

log = logging.getLogger("synaptiq.literature.arxiv")

_API_URL = "https://export.arxiv.org/api/query"
_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
    "openSearch": "http://a9.com/-/spec/opensearch/1.1/",
}

# Accept: 1234.5678, 1234.56789, hep-th/9901001, cs.LG/0001001, etc.
_ID_RE = re.compile(r"(\d{4}\.\d{4,5}(?:v\d+)?|[a-z\-]+(?:\.[A-Z]+)?/\d{7})")


def _normalise_id(arxiv_id: str) -> str:
    arxiv_id = arxiv_id.strip()
    # Strip URL prefix if provided
    arxiv_id = re.sub(r"https?://(www\.)?arxiv\.org/(abs/|pdf/)?", "", arxiv_id)
    arxiv_id = arxiv_id.rstrip("/").replace(".pdf", "")
    return arxiv_id


async def fetch_by_arxiv_id(arxiv_id: str) -> IngestionResult:
    """Fetch paper from arXiv by ID."""
    clean_id = _normalise_id(arxiv_id)
    params = {"id_list": clean_id, "max_results": 1}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(_API_URL, params=params)
            resp.raise_for_status()
            root = ET.fromstring(resp.text)
    except httpx.HTTPError as exc:
        return IngestionResult(success=False, error=f"arXiv request failed: {exc}",
                               source=PaperSource.ARXIV, source_id=clean_id)
    except ET.ParseError as exc:
        return IngestionResult(success=False, error=f"arXiv XML parse error: {exc}",
                               source=PaperSource.ARXIV, source_id=clean_id)

    entries = root.findall("atom:entry", _NS)
    if not entries:
        return IngestionResult(success=False, error=f"arXiv ID not found: {clean_id}",
                               source=PaperSource.ARXIV, source_id=clean_id)

    entry = entries[0]

    # Check for error response
    error_el = entry.find("atom:title", _NS)
    if error_el is not None and "Error" in (error_el.text or ""):
        return IngestionResult(success=False, error=f"arXiv error: {error_el.text}",
                               source=PaperSource.ARXIV, source_id=clean_id)

    def _text(tag: str) -> str:
        el = entry.find(tag, _NS)
        return _clean(el.text) if el is not None else ""

    title = _text("atom:title")
    abstract = _text("atom:summary")

    # Authors
    authors = []
    for a in entry.findall("atom:author", _NS):
        name_el = a.find("atom:name", _NS)
        if name_el is not None and name_el.text:
            authors.append(name_el.text.strip())

    # Published year
    pub = _text("atom:published")
    year = int(pub[:4]) if pub and pub[:4].isdigit() else 0

    # DOI link if available
    doi = ""
    doi_el = entry.find("arxiv:doi", _NS)
    if doi_el is not None and doi_el.text:
        doi = doi_el.text.strip()

    # Categories as keywords
    categories = [c.get("term", "") for c in entry.findall("atom:category", _NS)
                  if c.get("term")]

    # arXiv URL
    url = f"https://arxiv.org/abs/{clean_id}"

    paper = Paper(
        source=PaperSource.ARXIV,
        source_id=clean_id,
        title=title,
        authors=authors,
        year=year,
        abstract=abstract,
        doi=doi,
        arxiv_id=clean_id,
        url=url,
        keywords=categories,
        open_access=True,
        journal="arXiv",
        raw_metadata={"id": clean_id, "published": pub, "categories": categories},
    )
    return IngestionResult(success=True, paper=paper, source=PaperSource.ARXIV, source_id=clean_id)
