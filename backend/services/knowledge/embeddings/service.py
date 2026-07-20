"""EmbeddingService — provider selection, caching, batch embedding."""
from __future__ import annotations

import asyncio
import logging

from services.knowledge.config import KnowledgeConfig
from services.knowledge.embeddings.cache import EmbeddingCache
from services.knowledge.embeddings.providers.base import EmbeddingProvider
from services.knowledge.embeddings.providers.local_provider import LocalEmbeddingProvider
from services.knowledge.embeddings.providers.openai_provider import OpenAIEmbeddingProvider
from services.knowledge.embeddings.providers.tfidf_provider import TFIDFEmbeddingProvider
from services.knowledge.telemetry import get_knowledge_telemetry

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Selects the best available embedding provider and handles caching."""

    def __init__(self, config: KnowledgeConfig) -> None:
        self._config = config
        self._cache = EmbeddingCache(ttl=config.embedding_cache_ttl_seconds)
        self._provider: EmbeddingProvider | None = None
        self._tfidf = TFIDFEmbeddingProvider()

    async def _get_provider(self) -> EmbeddingProvider:
        if self._provider is not None:
            return self._provider

        cfg = self._config
        preferred = cfg.embedding_provider.lower()

        if preferred in ("local", "ollama"):
            p = LocalEmbeddingProvider(cfg.ollama_base_url, cfg.embedding_model, cfg.embedding_dim)
            if await p.check_available():
                self._provider = p
                logger.info("Embedding: using Ollama %s", cfg.embedding_model)
                return self._provider

        if preferred == "openai" or cfg.openai_api_key:
            if cfg.openai_api_key:
                p = OpenAIEmbeddingProvider(cfg.openai_api_key, cfg.openai_embedding_model)
                self._provider = p
                logger.info("Embedding: using OpenAI %s", cfg.openai_embedding_model)
                return self._provider

        # Always-available fallback
        logger.warning("Embedding: no neural provider available, using TF-IDF fallback")
        self._provider = self._tfidf
        return self._provider

    async def embed(self, text: str) -> list[float]:
        provider = await self._get_provider()
        key = self._cache.make_key(provider.name, text)
        cached = self._cache.get(key)
        if cached is not None:
            get_knowledge_telemetry().record_embedding(from_cache=True)
            return cached
        emb = await provider.embed(text)
        self._cache.set(key, emb)
        get_knowledge_telemetry().record_embedding(from_cache=False)
        return emb

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        provider = await self._get_provider()
        results: list[list[float] | None] = [None] * len(texts)
        uncached_indices: list[int] = []
        uncached_texts: list[str] = []

        for i, text in enumerate(texts):
            key = self._cache.make_key(provider.name, text)
            cached = self._cache.get(key)
            if cached is not None:
                results[i] = cached
                get_knowledge_telemetry().record_embedding(from_cache=True)
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)

        if uncached_texts:
            embeddings = await provider.embed_batch(uncached_texts)
            for i, emb in zip(uncached_indices, embeddings):
                results[i] = emb
                key = self._cache.make_key(provider.name, texts[i])
                self._cache.set(key, emb)
                get_knowledge_telemetry().record_embedding(from_cache=False)

        return [r for r in results if r is not None]

    @property
    def dimension(self) -> int:
        if self._provider:
            return self._provider.dimension
        return self._config.embedding_dim

    def cache_size(self) -> int:
        return self._cache.size()

    def clear_cache(self) -> None:
        self._cache.clear()
