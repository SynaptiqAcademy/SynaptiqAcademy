"""OpenAI embedding provider — text-embedding-3-small default."""
from __future__ import annotations

import asyncio
import logging

from services.knowledge.embeddings.providers.base import EmbeddingProvider

logger = logging.getLogger(__name__)

_BATCH_SIZE = 100
_MODEL_DIMS = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
}


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str, model: str = "text-embedding-3-small") -> None:
        self._api_key = api_key
        self._model = model
        self._dim = _MODEL_DIMS.get(model, 1536)

    @property
    def name(self) -> str:
        return f"openai:{self._model}"

    @property
    def dimension(self) -> int:
        return self._dim

    def is_available(self) -> bool:
        return bool(self._api_key)

    async def embed(self, text: str) -> list[float]:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self._api_key)
            resp = await client.embeddings.create(model=self._model, input=text)
            return resp.data[0].embedding
        except ImportError:
            raise RuntimeError("openai package not installed")
        except Exception as exc:
            raise RuntimeError(f"OpenAI embed failed: {exc}") from exc

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        try:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=self._api_key)
            results: list[list[float]] = []
            for i in range(0, len(texts), _BATCH_SIZE):
                batch = texts[i:i + _BATCH_SIZE]
                resp = await client.embeddings.create(model=self._model, input=batch)
                results.extend([d.embedding for d in sorted(resp.data, key=lambda x: x.index)])
            return results
        except ImportError:
            raise RuntimeError("openai package not installed")
        except Exception as exc:
            raise RuntimeError(f"OpenAI batch embed failed: {exc}") from exc
