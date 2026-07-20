"""Knowledge Engine configuration — fully driven by environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class KnowledgeConfig:
    # ── Enable/disable ─────────────────────────────────────────────────────────
    enabled: bool = True
    rag_enabled: bool = True           # inject context into AI requests

    # ── Embedding ─────────────────────────────────────────────────────────────
    embedding_provider: str = "local"  # local | openai | tfidf
    embedding_model: str = "nomic-embed-text"
    embedding_dim: int = 768           # nomic-embed-text=768, openai=1536
    ollama_base_url: str = "http://localhost:11434"
    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"

    # ── Vector store ──────────────────────────────────────────────────────────
    vector_backend: str = "mongodb"    # mongodb | numpy; mongodb uses Atlas $vectorSearch with numpy fallback
    mongo_collection_chunks: str = "knowledge_chunks"
    mongo_collection_documents: str = "knowledge_documents"
    mongo_vector_index: str = "vector_index"

    # ── Chunking ──────────────────────────────────────────────────────────────
    chunk_strategy: str = "section"    # section | paragraph
    chunk_max_tokens: int = 500
    chunk_overlap_tokens: int = 50
    chunk_min_tokens: int = 50

    # ── Retrieval ────────────────────────────────────────────────────────────
    retrieval_top_k: int = 8
    retrieval_min_score: float = 0.30
    keyword_weight: float = 0.35       # weight for BM25 vs semantic
    semantic_weight: float = 0.65

    # ── Context builder ──────────────────────────────────────────────────────
    context_max_tokens: int = 3000
    context_max_chunks: int = 6
    context_deduplicate_threshold: float = 0.85  # cosine similarity

    # ── Caching ──────────────────────────────────────────────────────────────
    embedding_cache_ttl_seconds: float = 3600.0
    retrieval_cache_ttl_seconds: float = 120.0

    # ── Indexing ─────────────────────────────────────────────────────────────
    indexing_batch_size: int = 10
    indexing_queue_max_size: int = 500
    auto_index_uploads: bool = True

    @classmethod
    def from_env(cls) -> "KnowledgeConfig":
        return cls(
            enabled=os.environ.get("KNOWLEDGE_ENABLED", "1") == "1",
            rag_enabled=os.environ.get("KNOWLEDGE_RAG_ENABLED", "1") == "1",
            embedding_provider=os.environ.get("KNOWLEDGE_EMBEDDING_PROVIDER", "local"),
            embedding_model=os.environ.get("KNOWLEDGE_EMBEDDING_MODEL", "nomic-embed-text"),
            embedding_dim=int(os.environ.get("KNOWLEDGE_EMBEDDING_DIM", "768") or "768"),
            ollama_base_url=os.environ.get("LOCAL_AI_OLLAMA_URL", "http://localhost:11434"),
            openai_api_key=os.environ.get("OPENAI_API_KEY", ""),
            openai_embedding_model=os.environ.get(
                "KNOWLEDGE_OPENAI_EMBED_MODEL", "text-embedding-3-small"
            ),
            vector_backend=os.environ.get("KNOWLEDGE_VECTOR_BACKEND", "mongodb"),
            mongo_collection_chunks=os.environ.get(
                "KNOWLEDGE_CHUNKS_COLLECTION", "knowledge_chunks"
            ),
            mongo_collection_documents=os.environ.get(
                "KNOWLEDGE_DOCS_COLLECTION", "knowledge_documents"
            ),
            chunk_strategy=os.environ.get("KNOWLEDGE_CHUNK_STRATEGY", "section"),
            chunk_max_tokens=int(os.environ.get("KNOWLEDGE_CHUNK_MAX_TOKENS", "500") or "500"),
            chunk_overlap_tokens=int(
                os.environ.get("KNOWLEDGE_CHUNK_OVERLAP", "50") or "50"
            ),
            chunk_min_tokens=int(os.environ.get("KNOWLEDGE_CHUNK_MIN_TOKENS", "50") or "50"),
            retrieval_top_k=int(os.environ.get("KNOWLEDGE_TOP_K", "8") or "8"),
            retrieval_min_score=float(
                os.environ.get("KNOWLEDGE_MIN_SCORE", "0.30") or "0.30"
            ),
            keyword_weight=float(os.environ.get("KNOWLEDGE_KW_WEIGHT", "0.35") or "0.35"),
            semantic_weight=float(os.environ.get("KNOWLEDGE_SEM_WEIGHT", "0.65") or "0.65"),
            context_max_tokens=int(
                os.environ.get("KNOWLEDGE_CTX_MAX_TOKENS", "3000") or "3000"
            ),
            context_max_chunks=int(
                os.environ.get("KNOWLEDGE_CTX_MAX_CHUNKS", "6") or "6"
            ),
            auto_index_uploads=os.environ.get("KNOWLEDGE_AUTO_INDEX", "1") == "1",
        )


_config: KnowledgeConfig | None = None


def load_knowledge_config() -> KnowledgeConfig:
    global _config
    if _config is None:
        _config = KnowledgeConfig.from_env()
    return _config


def reload_knowledge_config() -> KnowledgeConfig:
    global _config
    _config = KnowledgeConfig.from_env()
    return _config
