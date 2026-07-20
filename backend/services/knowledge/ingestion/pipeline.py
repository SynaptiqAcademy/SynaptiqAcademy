"""Document ingestion pipeline — extract → chunk → embed → store."""
from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from services.knowledge.config import KnowledgeConfig
from services.knowledge.ingestion.extractors.base import DocumentExtractor
from services.knowledge.ingestion.extractors.docx_extractor import DOCXExtractor
from services.knowledge.ingestion.extractors.metadata_enricher import enrich_from_doi
from services.knowledge.ingestion.extractors.pdf_extractor import PDFExtractor
from services.knowledge.ingestion.extractors.text_extractor import (
    CSVExtractor,
    HTMLExtractor,
    MarkdownExtractor,
    PowerPointExtractor,
    TextExtractor,
)
from services.knowledge.ingestion.chunkers.paragraph_chunker import ParagraphChunker
from services.knowledge.ingestion.chunkers.section_chunker import SectionChunker
from services.knowledge.models import Chunk, DocumentMetadata, IndexingJob, KnowledgeDocument
from services.knowledge.telemetry import get_knowledge_telemetry

if TYPE_CHECKING:
    from services.knowledge.embeddings.service import EmbeddingService
    from services.knowledge.vector_store.base import VectorStore

logger = logging.getLogger(__name__)

_EXTRACTORS: list[DocumentExtractor] = [
    PDFExtractor(),
    DOCXExtractor(),
    TextExtractor(),
    MarkdownExtractor(),
    HTMLExtractor(),
    CSVExtractor(),
    PowerPointExtractor(),
]


def _get_extractor(file_type: str) -> DocumentExtractor | None:
    ft = file_type.lower().lstrip(".")
    for ext in _EXTRACTORS:
        if ext.supports(ft):
            return ext
    return None


class IngestionPipeline:
    """End-to-end pipeline: bytes → indexed chunks stored in vector store."""

    def __init__(
        self,
        config: KnowledgeConfig,
        embedding_service: "EmbeddingService",
        vector_store: "VectorStore",
    ) -> None:
        self._config = config
        self._emb = embedding_service
        self._vs = vector_store
        self._chunker_cls = SectionChunker if config.chunk_strategy == "section" else ParagraphChunker

    async def ingest(self, job: IndexingJob) -> KnowledgeDocument:
        """Process one indexing job end-to-end. Returns updated KnowledgeDocument."""
        t0 = time.monotonic()
        tel = get_knowledge_telemetry()

        # 1. Extract text from bytes
        extractor = _get_extractor(job.file_type)
        if extractor is None:
            raise ValueError(f"Unsupported file type: {job.file_type}")

        try:
            extracted = extractor.extract(job.content_bytes, filename=job.filename)
        except Exception as exc:
            logger.error("Extraction failed for %s: %s", job.filename, exc)
            tel.record_failed()
            raise

        # Merge provided metadata with extracted metadata
        meta = job.metadata
        if not meta.title and extracted.metadata.title:
            meta.title = extracted.metadata.title
        if not meta.doi and extracted.metadata.doi:
            meta.doi = extracted.metadata.doi
        if not meta.publication_year and extracted.metadata.publication_year:
            meta.publication_year = extracted.metadata.publication_year
        if not meta.language:
            meta.language = extracted.language

        # 2. Enrich from DOI (async network call, best-effort)
        try:
            meta = await enrich_from_doi(meta)
        except Exception:
            pass

        # 3. Chunk
        chunker = self._chunker_cls(
            max_tokens=self._config.chunk_max_tokens,
            overlap_tokens=self._config.chunk_overlap_tokens,
            min_tokens=self._config.chunk_min_tokens,
        )
        chunks = chunker.chunk(
            sections=extracted.sections,
            metadata=meta,
            document_id=job.document_id,
            user_id=job.user_id,
            workspace_id=job.workspace_id,
            visibility=job.visibility,
        )

        if not chunks:
            raise ValueError(f"No chunks produced for {job.filename}")

        # 4. Embed all chunks (batch)
        texts = [c.text for c in chunks]
        embeddings = await self._emb.embed_batch(texts)
        for chunk, emb in zip(chunks, embeddings):
            chunk.embedding = emb

        # 5. Store in vector store
        await self._vs.add_chunks(chunks)

        elapsed_ms = int((time.monotonic() - t0) * 1000)
        logger.info(
            "Indexed %s: %d chunks in %dms via %s",
            job.filename, len(chunks), elapsed_ms, extracted.extraction_method,
        )
        tel.record_indexed(len(chunks))

        from datetime import datetime, timezone
        doc = KnowledgeDocument(
            document_id=job.document_id,
            user_id=job.user_id,
            filename=job.filename,
            file_type=job.file_type,
            source_kind=job.source_kind,
            source_id=job.source_id,
            workspace_id=job.workspace_id,
            visibility=job.visibility,
            metadata=meta,
            chunk_count=len(chunks),
            indexed_at=datetime.now(timezone.utc),
            status="indexed",
            file_size_bytes=len(job.content_bytes),
        )
        return doc
