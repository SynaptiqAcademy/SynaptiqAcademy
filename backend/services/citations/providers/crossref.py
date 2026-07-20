"""Crossref citation provider — stub implementation.

Crossref does not surface citation counts directly (that's via Cited-by API,
which requires publisher membership). This stub satisfies the interface so the
provider registry can include Crossref without breaking.

Activate by implementing `search_publication()` using:
  https://api.crossref.org/works/{doi}
and citation counts via the Crossref Metadata Plus programme.
"""
from __future__ import annotations

from typing import Optional

from .base import CitationProvider, CitationSyncResult, CitingWork, PublicationMatch


class CrossrefProvider(CitationProvider):
    """Stub Crossref provider. Not yet activated."""

    @property
    def name(self) -> str:
        return "crossref"

    async def search_publication(
        self,
        *,
        doi: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Optional[PublicationMatch]:
        raise NotImplementedError("Crossref provider not yet implemented")

    async def get_citation_count(self, provider_id: str) -> int:
        raise NotImplementedError

    async def get_citation_history(self, provider_id: str) -> list[dict]:
        raise NotImplementedError

    async def get_citing_works(
        self, provider_id: str, *, limit: int = 20
    ) -> list[CitingWork]:
        raise NotImplementedError

    async def sync_publication(
        self,
        *,
        doi: Optional[str] = None,
        title: Optional[str] = None,
    ) -> CitationSyncResult:
        raise NotImplementedError
