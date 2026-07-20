"""Paragraph chunker — splits by blank lines, groups until max_tokens."""
from __future__ import annotations

import re

from services.knowledge.ingestion.chunkers.base import ChunkerBase, _count_tokens
from services.knowledge.models import Chunk, DocumentMetadata


def _split_paragraphs(text: str) -> list[str]:
    return [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]


class ParagraphChunker(ChunkerBase):
    """Paragraph-based chunker used when no heading structure is detected.

    Groups consecutive paragraphs until max_tokens, then starts a new chunk
    with overlap from the last paragraph(s).
    """

    def chunk(
        self,
        sections: list[dict],
        metadata: DocumentMetadata,
        document_id: str,
        user_id: str = "",
        workspace_id: str | None = None,
        visibility: str = "private",
    ) -> list[Chunk]:
        # Flatten all section text
        full_text = "\n\n".join(s.get("text", "") for s in sections if s.get("text"))
        paragraphs = _split_paragraphs(full_text)

        chunks: list[Chunk] = []
        idx = 0
        current_paras: list[str] = []
        current_tokens = 0

        for i, para in enumerate(paragraphs):
            pt = _count_tokens(para)
            if current_tokens + pt > self.max_tokens and current_paras:
                text = "\n\n".join(current_paras)
                if current_tokens >= self.min_tokens:
                    chunks.append(self._make_chunk(
                        text=text,
                        document_id=document_id,
                        chunk_index=idx,
                        heading="",
                        section="",
                        page=None,
                        paragraph_index=i - len(current_paras),
                        metadata=metadata,
                        user_id=user_id,
                        workspace_id=workspace_id,
                        visibility=visibility,
                    ))
                    idx += 1
                # Overlap: keep last few paragraphs
                overlap: list[str] = []
                overlap_t = 0
                for p in reversed(current_paras):
                    ot = _count_tokens(p)
                    if overlap_t + ot > self.overlap_tokens:
                        break
                    overlap.insert(0, p)
                    overlap_t += ot
                current_paras = overlap
                current_tokens = overlap_t

            current_paras.append(para)
            current_tokens += pt

        if current_paras and current_tokens >= self.min_tokens:
            chunks.append(self._make_chunk(
                text="\n\n".join(current_paras),
                document_id=document_id,
                chunk_index=idx,
                heading="",
                section="",
                page=None,
                paragraph_index=len(paragraphs) - len(current_paras),
                metadata=metadata,
                user_id=user_id,
                workspace_id=workspace_id,
                visibility=visibility,
            ))

        return chunks
