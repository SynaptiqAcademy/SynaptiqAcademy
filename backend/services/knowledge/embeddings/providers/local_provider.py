"""Ollama embedding provider — calls /api/embeddings."""
from __future__ import annotations

import asyncio
import logging

from services.knowledge.embeddings.providers.base import EmbeddingProvider

logger = logging.getLogger(__name__)

_TIMEOUT = 15.0
_BATCH_PARALLEL = 4


class LocalEmbeddingProvider(EmbeddingProvider):
    """Uses Ollama's /api/embeddings endpoint."""

    def __init__(self, base_url: str, model: str, dimension: int = 768) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._dim = dimension
        self._available: bool | None = None

    @property
    def name(self) -> str:
        return f"ollama:{self._model}"

    @property
    def dimension(self) -> int:
        return self._dim

    def is_available(self) -> bool:
        if self._available is None:
            self._available = True  # optimistic; real check is async
        return self._available

    async def embed(self, text: str) -> list[float]:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
                r = await client.post(
                    f"{self._base_url}/api/embeddings",
                    json={"model": self._model, "prompt": text},
                )
                r.raise_for_status()
                data = r.json()
                emb = data.get("embedding", [])
                self._available = True
                return emb
        except Exception as exc:
            self._available = False
            raise RuntimeError(f"Ollama embed failed: {exc}") from exc

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        sem = asyncio.Semaphore(_BATCH_PARALLEL)

        async def _one(text: str) -> list[float]:
            async with sem:
                return await self.embed(text)

        return await asyncio.gather(*[_one(t) for t in texts])

    async def check_available(self) -> bool:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=3.0) as client:
                r = await client.get(f"{self._base_url}/api/tags")
                self._available = r.status_code == 200
                return self._available
        except Exception:
            self._available = False
            return False
