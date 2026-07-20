"""KnowledgeEngine — singleton that wires all subsystems together.

Provides the external API used by AI feature integrations and HTTP routers.
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from services.knowledge.config import KnowledgeConfig, load_knowledge_config
from services.knowledge.context.context_builder import ContextBuilder
from services.knowledge.embeddings.service import EmbeddingService
from services.knowledge.indexing.background_indexer import BackgroundIndexer
from services.knowledge.ingestion.pipeline import IngestionPipeline
from services.knowledge.models import (
    Citation,
    DocumentMetadata,
    IndexingJob,
    KnowledgeDocument,
    SearchResult,
)
from services.knowledge.retrieval.filters import RetrievalFilter
from services.knowledge.retrieval.hybrid_retriever import HybridRetriever
from services.knowledge.retrieval.retrieval_cache import RetrievalCache
from services.knowledge.telemetry import get_knowledge_telemetry
from services.knowledge.vector_store.base import VectorStore
from repo.shim import DBProxy
from repo.security_context import SecurityContext

logger = logging.getLogger(__name__)

# RAG-eligible AI features
_RAG_FEATURES = frozenset({
    "research_gap_finder",
    "literature_review",
    "manuscript_review",
    "statistical_review",
    "research_design_advisor",
    "ai_assistant",
    "ai_chat",
    "teaching_lesson_generation",
    "teaching_assessment_generation",
    "research_brainstorming",
    "writing_improvement",
    "academic_proofreading",
})


def _build_vector_store(config: KnowledgeConfig, db) -> VectorStore:
    if config.vector_backend == "mongodb":
        from services.knowledge.vector_store.mongodb_store import MongoDBVectorStore
        return MongoDBVectorStore(db, config.mongo_vector_index)
    from services.knowledge.vector_store.numpy_store import NumpyVectorStore
    return NumpyVectorStore(db)


class KnowledgeEngine:
    """Central orchestrator for the RAG & Knowledge subsystem."""

    def __init__(self, config: KnowledgeConfig, db) -> None:
        self._config = config
        self._db = db
        self._emb = EmbeddingService(config)
        self._vs = _build_vector_store(config, db)
        self._pipeline = IngestionPipeline(config, self._emb, self._vs)
        self._retriever = HybridRetriever(
            self._vs, self._emb, config.semantic_weight, config.keyword_weight
        )
        self._ctx_builder = ContextBuilder(
            config.context_max_tokens,
            config.context_max_chunks,
        )
        self._cache = RetrievalCache(ttl=config.retrieval_cache_ttl_seconds)
        self._indexer = BackgroundIndexer(self._pipeline, db)
        self._indexer.start()

    # ── Document management ────────────────────────────────────────────────────

    async def submit_document(
        self,
        content_bytes: bytes,
        filename: str,
        user_id: str,
        file_type: str | None = None,
        metadata: DocumentMetadata | None = None,
        workspace_id: str | None = None,
        source_kind: str = "upload",
        source_id: str = "",
        visibility: str = "private",
        priority: int = 5,
    ) -> str:
        """Queue a document for background indexing. Returns document_id."""
        if file_type is None:
            file_type = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"

        document_id = str(uuid.uuid4())
        job = IndexingJob(
            job_id=str(uuid.uuid4()),
            document_id=document_id,
            user_id=user_id,
            filename=filename,
            file_type=file_type,
            content_bytes=content_bytes,
            metadata=metadata or DocumentMetadata(),
            workspace_id=workspace_id,
            source_kind=source_kind,
            source_id=source_id,
            visibility=visibility,
            priority=priority,
        )
        await self._indexer.enqueue(job)
        return document_id

    async def delete_document(self, document_id: str, user_id: str) -> int:
        """Delete a document and all its chunks. Returns chunks deleted."""
        doc = await self._db["knowledge_documents"].find_one(
            {"_id": document_id, "user_id": user_id}
        )
        if doc is None:
            raise PermissionError(f"Document {document_id} not found or not owned by user")
        deleted = await self._vs.delete_document(document_id)
        await self._db["knowledge_documents"].delete_one({"_id": document_id})
        return deleted

    async def get_document_status(self, document_id: str, user_id: str) -> dict:
        doc = await self._db["knowledge_documents"].find_one(
            {"_id": document_id, "user_id": user_id},
            {"embedding": 0},
        )
        if doc is None:
            return {}
        doc["_id"] = str(doc["_id"])
        return doc

    async def list_documents(
        self, user_id: str, workspace_id: str | None = None, limit: int = 50
    ) -> list[dict]:
        query: dict = {"user_id": user_id}
        if workspace_id:
            query["workspace_id"] = workspace_id
        docs = await self._db["knowledge_documents"].find(
            query, {"embedding": 0}
        ).sort("indexed_at", -1).limit(limit).to_list(length=limit)
        for d in docs:
            d["_id"] = str(d["_id"])
        return docs

    # ── Retrieval ─────────────────────────────────────────────────────────────

    async def retrieve(
        self,
        query: str,
        user_id: str,
        workspace_id: str | None = None,
        top_k: int | None = None,
        min_score: float | None = None,
    ) -> list[SearchResult]:
        """Run hybrid retrieval, with caching."""
        if not self._config.enabled:
            return []

        top_k = top_k or self._config.retrieval_top_k
        min_score = min_score if min_score is not None else self._config.retrieval_min_score

        cache_key = self._cache.make_key(query, user_id, top_k, workspace_id)
        cached = self._cache.get(cache_key)
        if cached is not None:
            get_knowledge_telemetry().record_retrieval(
                results=len(cached), latency_ms=0, from_cache=True
            )
            return cached

        t0 = time.monotonic()
        rf = RetrievalFilter(user_id=user_id, workspace_id=workspace_id)
        results = await self._retriever.retrieve(query, top_k, rf, min_score)
        latency_ms = int((time.monotonic() - t0) * 1000)

        top_score = results[0].semantic_score if results else 0.0
        get_knowledge_telemetry().record_retrieval(
            results=len(results),
            latency_ms=latency_ms,
            query_length=len(query),
            top_score=top_score,
            from_cache=False,
        )
        self._cache.set(cache_key, results)
        return results

    async def build_context(
        self,
        query: str,
        user_id: str,
        workspace_id: str | None = None,
        top_k: int | None = None,
    ) -> tuple[str, list[Citation]]:
        """Retrieve + build formatted context string + citations."""
        results = await self.retrieve(query, user_id, workspace_id, top_k)
        return self._ctx_builder.build(results)

    async def is_rag_eligible(self, feature: str) -> bool:
        return feature in _RAG_FEATURES and self._config.rag_enabled

    # ── Admin / stats ─────────────────────────────────────────────────────────

    async def get_stats(self) -> dict:
        chunk_count = await self._vs.chunk_count()
        doc_count = await self._db["knowledge_documents"].count_documents({})
        tel = get_knowledge_telemetry().get_stats()
        return {
            "enabled": self._config.enabled,
            "rag_enabled": self._config.rag_enabled,
            "embedding_provider": self._config.embedding_provider,
            "vector_backend": self._config.vector_backend,
            "chunk_strategy": self._config.chunk_strategy,
            "total_documents": doc_count,
            "total_chunks": chunk_count,
            "embedding_cache_size": self._emb.cache_size(),
            "retrieval_cache_size": self._cache.size(),
            "indexing_queue_size": self._indexer.queue_size(),
            **tel,
        }

    async def reindex_document(self, document_id: str, user_id: str) -> None:
        """Re-queue an existing document for reindexing (e.g. after model change)."""
        doc = await self._db["knowledge_documents"].find_one(
            {"_id": document_id, "user_id": user_id}
        )
        if not doc:
            raise PermissionError(f"Document {document_id} not found")
        # Delete existing chunks
        await self._vs.delete_document(document_id)
        # Re-enqueue (content must be re-fetched from storage by caller)
        raise NotImplementedError("Reindexing requires re-fetching document bytes from storage")

    def clear_caches(self) -> None:
        self._cache.clear()
        self._emb.clear_cache()

    async def shutdown(self) -> None:
        self._indexer.stop()


# ── Singleton ─────────────────────────────────────────────────────────────────

_engine: KnowledgeEngine | None = None
_lock = asyncio.Lock()


async def get_knowledge_engine() -> KnowledgeEngine:
    global _engine
    if _engine is None:
        async with _lock:
            if _engine is None:
                from db import get_db
                config = load_knowledge_config()
                db = get_db()
                db = DBProxy(db, SecurityContext.system())

                _engine = KnowledgeEngine(config, db)
                logger.info("KnowledgeEngine initialized (backend=%s)", config.vector_backend)
    return _engine


async def reset_knowledge_engine() -> None:
    global _engine
    if _engine is not None:
        await _engine.shutdown()
    _engine = None
