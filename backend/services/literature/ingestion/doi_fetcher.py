"""DOI ingestion via CrossRef API (no auth required)."""
from __future__ import annotations

import logging
import urllib.parse

import httpx

from services.literature.ingestion.base import IngestionResult, _clean
from services.literature.models import Paper, PaperSource

log = logging.getLogger("synaptiq.literature.doi")

_CROSSREF_URL = "https://api.crossref.org/works/{doi}"
_HEADERS = {
    "User-Agent": "Synaptiq/1.0 (https://synaptiq.academy; mailto:admin@synaptiq.academy)",
}


async def fetch_by_doi(doi: str) -> IngestionResult:
    """Fetch paper metadata from CrossRef by DOI."""
    doi = doi.strip().lstrip("https://doi.org/").lstrip("http://dx.doi.org/")
    encoded = urllib.parse.quote(doi, safe="/()")
    url = _CROSSREF_URL.format(doi=encoded)

    try:
        async with httpx.AsyncClient(timeout=15.0, headers=_HEADERS) as client:
            resp = await client.get(url)
            if resp.status_code == 404:
                return IngestionResult(success=False, error=f"DOI not found: {doi}",
                                       source=PaperSource.DOI, source_id=doi)
            resp.raise_for_status()
            data = resp.json().get("message", {})
    except httpx.HTTPError as exc:
        return IngestionResult(success=False, error=f"CrossRef request failed: {exc}",
                               source=PaperSource.DOI, source_id=doi)

    # Authors
    authors = []
    for a in data.get("author", []):
        given = a.get("given", "")
        family = a.get("family", "")
        name = f"{family}, {given}".strip(", ") if family else given
        if name:
            authors.append(name)

    # Year
    year = 0
    for date_key in ("published", "published-print", "published-online", "issued"):
        parts = data.get(date_key, {}).get("date-parts", [[]])
        if parts and parts[0]:
            year = int(parts[0][0])
            break

    # Title
    titles = data.get("title", [])
    title = _clean(titles[0]) if titles else ""

    # Abstract — CrossRef sometimes provides it
    abstract = _clean(data.get("abstract", ""))
    # Remove JATS XML tags if present
    if abstract:
        import re
        abstract = re.sub(r"<[^>]+>", " ", abstract).strip()

    # Journal
    journal_titles = data.get("container-title", [])
    journal = journal_titles[0] if journal_titles else ""

    # Keywords
    subjects = data.get("subject", [])

    paper = Paper(
        source=PaperSource.DOI,
        source_id=doi,
        title=title,
        authors=authors,
        year=year,
        abstract=abstract,
        journal=_clean(journal),
        volume=_clean(str(data.get("volume", ""))),
        issue=_clean(str(data.get("issue", ""))),
        pages=_clean(data.get("page", "")),
        doi=doi,
        url=data.get("URL", f"https://doi.org/{doi}"),
        keywords=subjects,
        citation_count=data.get("is-referenced-by-count", 0),
        reference_count=data.get("references-count", 0),
        raw_metadata=data,
    )
    return IngestionResult(success=True, paper=paper, source=PaperSource.DOI, source_id=doi)
