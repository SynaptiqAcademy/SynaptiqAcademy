"""Abstract vector store interface."""
from __future__ import annotations

from abc import ABC, abstractmethod

from services.knowledge.models import Chunk, SearchResult


class VectorStore(ABC):
    """Persistent chunk storage + similarity search."""

    @abstractmethod
    async def add_chunks(self, chunks: list[Chunk]) -> None:
        """Persist chunks and add their embeddings to the index."""
        ...

    @abstractmethod
    async def search(
        self,
        query_embedding: list[float],
        top_k: int,
        filter_user_id: str | None = None,
        filter_workspace_id: str | None = None,
        filter_visibility: list[str] | None = None,
    ) -> list[SearchResult]:
        """Return top_k most similar chunks, applying permission filters."""
        ...

    @abstractmethod
    async def delete_document(self, document_id: str) -> int:
        """Delete all chunks belonging to a document. Returns count deleted."""
        ...

    @abstractmethod
    async def chunk_count(self) -> int:
        """Total number of indexed chunks."""
        ...

    @abstractmethod
    async def get_chunks_by_document(self, document_id: str) -> list[Chunk]:
        """Retrieve all chunks for a document."""
        ...
