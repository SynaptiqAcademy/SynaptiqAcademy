"""Section-aware chunker — one chunk per section, splitting long sections."""
from __future__ import annotations

from services.knowledge.ingestion.chunkers.base import ChunkerBase, _count_tokens
from services.knowledge.models import Chunk, DocumentMetadata


class SectionChunker(ChunkerBase):
    """Produces chunks aligned to document sections.

    If a section fits in max_tokens → single chunk.
    If it exceeds → sentence-split into overlapping sub-chunks.
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
        chunks: list[Chunk] = []
        idx = 0

        for section in sections:
            heading = section.get("heading", "")
            text = section.get("text", "").strip()
            page = section.get("page")
            if not text:
                continue

            token_count = _count_tokens(text)

            if token_count <= self.max_tokens:
                if token_count >= self.min_tokens:
                    chunks.append(self._make_chunk(
                        text=text,
                        document_id=document_id,
                        chunk_index=idx,
                        heading=heading,
                        section=heading,
                        page=page,
                        paragraph_index=None,
                        metadata=metadata,
                        user_id=user_id,
                        workspace_id=workspace_id,
                        visibility=visibility,
                    ))
                    idx += 1
            else:
                sub_texts = self._split_long_text(text, heading, page)
                for sub in sub_texts:
                    if _count_tokens(sub) >= self.min_tokens:
                        chunks.append(self._make_chunk(
                            text=sub,
                            document_id=document_id,
                            chunk_index=idx,
                            heading=heading,
                            section=heading,
                            page=page,
                            paragraph_index=None,
                            metadata=metadata,
                            user_id=user_id,
                            workspace_id=workspace_id,
                            visibility=visibility,
                        ))
                        idx += 1

        return chunks
