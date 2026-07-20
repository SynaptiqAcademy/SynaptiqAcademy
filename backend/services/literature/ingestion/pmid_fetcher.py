"""PMID ingestion via NCBI PubMed API."""
from __future__ import annotations

import json
import logging

import httpx

from services.literature.ingestion.base import IngestionResult, _clean
from services.literature.models import Paper, PaperSource

log = logging.getLogger("synaptiq.literature.pmid")

_ESUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
_EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
_ELINK = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"


async def fetch_by_pmid(pmid: str) -> IngestionResult:
    """Fetch paper metadata from PubMed by PMID."""
    pmid = pmid.strip()

    params = {
        "db": "pubmed",
        "id": pmid,
        "retmode": "json",
        "rettype": "abstract",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # ESummary gives structured JSON metadata
            resp = await client.get(_ESUMMARY, params=params)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        return IngestionResult(success=False, error=f"PubMed request failed: {exc}",
                               source=PaperSource.PMID, source_id=pmid)

    try:
        result = data.get("result", {})
        uids = result.get("uids", [])
        if not uids:
            return IngestionResult(success=False, error=f"PMID not found: {pmid}",
                                   source=PaperSource.PMID, source_id=pmid)

        doc = result.get(pmid) or result.get(uids[0], {})

        # Parse authors
        authors = []
        for a in doc.get("authors", []):
            name = a.get("name", "")
            if name:
                authors.append(name)

        # Year
        pubdate = doc.get("pubdate", "")
        year = int(pubdate[:4]) if pubdate and pubdate[:4].isdigit() else 0

        # Abstract — esummary doesn't always include it; we add it via efetch
        abstract = await _fetch_abstract(pmid)

        # Journal
        journal = _clean(doc.get("fulljournalname", "") or doc.get("source", ""))

        paper = Paper(
            source=PaperSource.PMID,
            source_id=pmid,
            title=_clean(doc.get("title", "")),
            authors=authors,
            year=year,
            abstract=abstract,
            journal=journal,
            volume=_clean(doc.get("volume", "")),
            issue=_clean(doc.get("issue", "")),
            pages=_clean(doc.get("pages", "")),
            pmid=pmid,
            url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
            keywords=[k.get("value", "") for k in doc.get("attributes", [])
                      if k.get("value")],
            raw_metadata=doc,
        )
        return IngestionResult(success=True, paper=paper, source=PaperSource.PMID, source_id=pmid)

    except Exception as exc:
        return IngestionResult(success=False, error=f"PMID parse error: {exc}",
                               source=PaperSource.PMID, source_id=pmid)


async def _fetch_abstract(pmid: str) -> str:
    """Fetch abstract text via efetch (text mode)."""
    try:
        params = {"db": "pubmed", "id": pmid, "retmode": "text", "rettype": "abstract"}
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(_EFETCH, params=params)
            if resp.status_code == 200:
                text = resp.text
                if "Abstract" in text:
                    idx = text.find("Abstract")
                    snippet = text[idx + 8:idx + 3000].strip()
                    # Remove the next author block (starts with next section)
                    for marker in ["\n\n", "PMID:"]:
                        pos = snippet.find(marker)
                        if pos > 100:
                            snippet = snippet[:pos]
                    return _clean(snippet)
    except Exception:
        pass
    return ""
