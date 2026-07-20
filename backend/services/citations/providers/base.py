"""Abstract CitationProvider interface.

Any new provider (Crossref, Semantic Scholar, PubMed) must implement this
interface. Callers depend only on the base class, making providers interchangeable.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PublicationMatch:
    """Resolved publication record from a provider."""
    provider_id: str             # provider-specific ID (e.g. OpenAlex W123…)
    doi: Optional[str]
    title: Optional[str]
    year: Optional[int]
    journal: Optional[str]
    citation_count: int = 0
    concepts: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    coauthors: list[dict] = field(default_factory=list)
    counts_by_year: list[dict] = field(default_factory=list)  # [{year, count}]
    open_access_url: Optional[str] = None


@dataclass
class CitingWork:
    """A single work that cites the target publication."""
    provider_id: str
    doi: Optional[str]
    title: Optional[str]
    year: Optional[int]
    journal: Optional[str]
    citation_count: int = 0   # how many citations this citing work itself has


@dataclass
class CitationSyncResult:
    """Result returned by syncPublication()."""
    found: bool
    provider: str
    publication: Optional[PublicationMatch]
    citing_works: list[CitingWork] = field(default_factory=list)
    error: Optional[str] = None


class CitationProvider(ABC):
    """Abstract base for citation data providers.

    Implementations: OpenAlexProvider (available), CrossrefProvider (stub),
    SemanticScholarProvider (stub).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier, e.g. 'openalex'."""

    @abstractmethod
    async def search_publication(
        self,
        *,
        doi: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Optional[PublicationMatch]:
        """Resolve a publication by DOI (preferred) or title.

        Returns None when no match is found.
        """

    @abstractmethod
    async def get_citation_count(self, provider_id: str) -> int:
        """Return the current total citation count for a provider work ID."""

    @abstractmethod
    async def get_citation_history(self, provider_id: str) -> list[dict]:
        """Return [{year: int, count: int}] sorted ascending by year."""

    @abstractmethod
    async def get_citing_works(
        self, provider_id: str, *, limit: int = 20
    ) -> list[CitingWork]:
        """Return papers that cite the given work, newest first."""

    @abstractmethod
    async def sync_publication(
        self,
        *,
        doi: Optional[str] = None,
        title: Optional[str] = None,
    ) -> CitationSyncResult:
        """Full sync: resolve + citation count + history + citing works."""
