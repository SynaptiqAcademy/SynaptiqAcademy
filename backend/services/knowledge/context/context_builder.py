"""Context builder — assembles retrieved chunks into a formatted AI context string.

Handles deduplication, token budget enforcement, and citation formatting.
"""
from __future__ import annotations

import re

from services.knowledge.models import Citation, SearchResult


def _count_tokens(text: str) -> int:
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text, disallowed_special=()))
    except Exception:
        return max(1, len(text) // 4)


def _word_set(text: str) -> set[str]:
    return set(re.findall(r"\b\w{4,}\b", text.lower()))


def _jaccard(a: str, b: str) -> float:
    sa, sb = _word_set(a), _word_set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


class ContextBuilder:
    """Builds the AI context string from a ranked list of SearchResults."""

    def __init__(
        self,
        max_tokens: int = 3000,
        max_chunks: int = 6,
        dedup_threshold: float = 0.85,
    ) -> None:
        self._max_tokens = max_tokens
        self._max_chunks = max_chunks
        self._dedup_threshold = dedup_threshold

    def _deduplicate(self, results: list[SearchResult]) -> list[SearchResult]:
        """Remove results that are highly similar to an already-kept result."""
        kept: list[SearchResult] = []
        for r in results:
            is_dup = any(_jaccard(r.text, k.text) >= self._dedup_threshold for k in kept)
            if not is_dup:
                kept.append(r)
        return kept

    def build(self, results: list[SearchResult]) -> tuple[str, list[Citation]]:
        """Return (context_string, list_of_citations).

        context_string is formatted for injection into the AI system prompt.
        citations preserve full provenance for each included chunk.
        """
        if not results:
            return "", []

        unique = self._deduplicate(results)

        selected: list[SearchResult] = []
        tokens_used = 0
        for result in unique[:self._max_chunks]:
            chunk_tokens = _count_tokens(result.text)
            if tokens_used + chunk_tokens > self._max_tokens:
                break
            selected.append(result)
            tokens_used += chunk_tokens

        if not selected:
            return "", []

        citations: list[Citation] = []
        blocks: list[str] = []
        for i, r in enumerate(selected, 1):
            citation = r.to_citation()
            citations.append(citation)
            ref = citation.format_short()
            blocks.append(f"[Source {i}: {ref}]\n{r.text}")

        context = (
            "The following excerpts from your indexed documents are relevant to this query. "
            "Use them to inform your response and cite sources where appropriate.\n\n"
            + "\n\n---\n\n".join(blocks)
        )
        return context, citations
