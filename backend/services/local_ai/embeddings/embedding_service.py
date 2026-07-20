"""Local embedding service — uses Ollama or compatible providers."""
from __future__ import annotations

import logging
import math

import httpx

logger = logging.getLogger("synaptiq.local_ai.embeddings")

_DEFAULT_EMBED_MODEL = "nomic-embed-text"


class LocalEmbeddingService:
    """Generate dense text embeddings using locally-running models.

    Requires Ollama with an embedding model pulled, e.g.:
        ollama pull nomic-embed-text
    """

    def __init__(self, base_url: str = "http://localhost:11434", model: str = _DEFAULT_EMBED_MODEL) -> None:
        self._base_url = base_url.rstrip("/")
        self._default_model = model

    async def embed(
        self,
        texts: list[str],
        model: str | None = None,
        timeout: float = 30.0,
    ) -> list[list[float]]:
        """Return embedding vectors for each text."""
        use_model = model or self._default_model
        embeddings: list[list[float]] = []

        async with httpx.AsyncClient(base_url=self._base_url, timeout=timeout) as c:
            for text in texts:
                try:
                    r = await c.post("/api/embeddings", json={"model": use_model, "prompt": text})
                    r.raise_for_status()
                    vec = r.json().get("embedding", [])
                    embeddings.append(vec)
                except Exception as exc:
                    logger.warning("embed error for text=%r: %s", text[:40], exc)
                    embeddings.append([])

        return embeddings

    async def embed_single(self, text: str, model: str | None = None) -> list[float]:
        results = await self.embed([text], model=model)
        return results[0] if results else []

    async def similarity(self, text_a: str, text_b: str) -> float:
        """Cosine similarity between two texts (0.0–1.0)."""
        vecs = await self.embed([text_a, text_b])
        if len(vecs) < 2 or not vecs[0] or not vecs[1]:
            return 0.0
        return _cosine(vecs[0], vecs[1])

    async def rank_by_similarity(
        self,
        query: str,
        candidates: list[str],
    ) -> list[tuple[int, float]]:
        """Return (index, similarity) sorted by similarity descending."""
        all_texts = [query] + candidates
        vecs = await self.embed(all_texts)
        if not vecs or not vecs[0]:
            return list(enumerate([0.0] * len(candidates)))
        q_vec = vecs[0]
        scored = [
            (i, _cosine(q_vec, vecs[i + 1]) if vecs[i + 1] else 0.0)
            for i in range(len(candidates))
        ]
        return sorted(scored, key=lambda x: x[1], reverse=True)


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x * x for x in a))
    mag_b = math.sqrt(sum(x * x for x in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)
