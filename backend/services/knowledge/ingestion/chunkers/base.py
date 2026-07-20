"""Chunker base — shared token counter + Chunk production."""
from __future__ import annotations

from abc import ABC, abstractmethod

from services.knowledge.models import Chunk, DocumentMetadata


def _count_tokens(text: str) -> int:
    """Fast tiktoken-based count, falls back to char/4 heuristic."""
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text, disallowed_special=()))
    except Exception:
        return max(1, len(text) // 4)


class ChunkerBase(ABC):
    """Abstract chunking strategy."""

    def __init__(self, max_tokens: int = 500, overlap_tokens: int = 50, min_tokens: int = 50) -> None:
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens
        self.min_tokens = min_tokens

    @abstractmethod
    def chunk(
        self,
        sections: list[dict],
        metadata: DocumentMetadata,
        document_id: str,
        user_id: str = "",
        workspace_id: str | None = None,
        visibility: str = "private",
    ) -> list[Chunk]:
        ...

    def _split_long_text(self, text: str, heading: str, page: int | None) -> list[str]:
        """Split text that exceeds max_tokens using sentence-aware splitting."""
        sentences = [s.strip() for s in _RE_SENTENCE.split(text) if s.strip()]
        chunks: list[str] = []
        current: list[str] = []
        current_tokens = 0

        for sent in sentences:
            sent_tokens = _count_tokens(sent)
            if current_tokens + sent_tokens > self.max_tokens and current:
                chunks.append(" ".join(current))
                # Keep overlap sentences
                overlap: list[str] = []
                overlap_t = 0
                for s in reversed(current):
                    st = _count_tokens(s)
                    if overlap_t + st > self.overlap_tokens:
                        break
                    overlap.insert(0, s)
                    overlap_t += st
                current = overlap
                current_tokens = overlap_t
            current.append(sent)
            current_tokens += sent_tokens

        if current:
            chunks.append(" ".join(current))
        return chunks or [text]

    def _make_chunk(
        self,
        text: str,
        document_id: str,
        chunk_index: int,
        heading: str,
        section: str,
        page: int | None,
        paragraph_index: int | None,
        metadata: DocumentMetadata,
        user_id: str,
        workspace_id: str | None,
        visibility: str,
    ) -> Chunk:
        return Chunk(
            document_id=document_id,
            chunk_index=chunk_index,
            text=text,
            heading=heading,
            section=section,
            page_number=page,
            paragraph_index=paragraph_index,
            token_count=_count_tokens(text),
            user_id=user_id,
            workspace_id=workspace_id,
            visibility=visibility,
            doi=metadata.doi,
            authors=metadata.authors,
            title=metadata.title,
            publication_year=metadata.publication_year,
        )


import re
_RE_SENTENCE = re.compile(r"(?<=[.!?])\s+")
