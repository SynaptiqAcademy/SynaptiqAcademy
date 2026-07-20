"""Async metadata enrichment: DOI → Crossref, ORCID lookup."""
from __future__ import annotations

import asyncio
import logging

from services.knowledge.models import DocumentMetadata

logger = logging.getLogger(__name__)

_CROSSREF_BASE = "https://api.crossref.org/works/"
_TIMEOUT = 5.0


async def enrich_from_doi(metadata: DocumentMetadata) -> DocumentMetadata:
    """Fill in missing metadata fields from Crossref using DOI."""
    if not metadata.doi:
        return metadata
    try:
        import httpx
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            r = await client.get(f"{_CROSSREF_BASE}{metadata.doi}")
            if r.status_code != 200:
                return metadata
            data = r.json().get("message", {})
    except Exception as exc:
        logger.debug("Crossref lookup failed for %s: %s", metadata.doi, exc)
        return metadata

    if not metadata.title:
        titles = data.get("title", [])
        metadata.title = titles[0] if titles else ""

    if not metadata.authors:
        authors_raw = data.get("author", [])
        metadata.authors = [
            f"{a.get('family', '')}, {a.get('given', '')}".strip(", ")
            for a in authors_raw
        ]

    if not metadata.journal:
        container = data.get("container-title", [])
        metadata.journal = container[0] if container else ""

    if not metadata.publication_year:
        dp = data.get("published", {}).get("date-parts", [[None]])[0]
        metadata.publication_year = dp[0] if dp else None

    if not metadata.abstract:
        metadata.abstract = data.get("abstract", "")[:1000]

    if not metadata.keywords:
        metadata.keywords = data.get("subject", [])[:10]

    return metadata
