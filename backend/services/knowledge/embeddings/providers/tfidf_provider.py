"""TF-IDF embedding provider — pure Python, always available.

Produces sparse bag-of-words vectors in a fixed vocabulary space.
Suitable as a fallback when no neural embedding server is available.
Vocabulary is built lazily from the first batch of texts and frozen thereafter.
"""
from __future__ import annotations

import hashlib
import math
import re
import threading
from collections import Counter

from services.knowledge.embeddings.providers.base import EmbeddingProvider

_STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
    "for", "of", "with", "by", "is", "was", "are", "were", "be",
    "been", "have", "has", "had", "do", "does", "did", "will",
    "that", "this", "it", "its", "as", "not", "from", "their",
}
_MAX_VOCAB = 4096
_TOKEN_RE = re.compile(r"[a-zA-Z]{3,}")


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text) if t.lower() not in _STOP_WORDS]


class TFIDFEmbeddingProvider(EmbeddingProvider):
    """Sparse TF-IDF vectors, dimension=_MAX_VOCAB.

    The vocabulary is fixed on first call to embed_batch or can be preloaded.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._vocab: dict[str, int] = {}   # token → col index
        self._idf: dict[str, float] = {}   # token → IDF weight
        self._n_docs = 0
        self._frozen = False
        self._dim = _MAX_VOCAB

    @property
    def name(self) -> str:
        return "tfidf"

    @property
    def dimension(self) -> int:
        return self._dim

    def is_available(self) -> bool:
        return True

    def train(self, corpus: list[str]) -> None:
        """Build vocabulary and IDF weights from a corpus of strings."""
        with self._lock:
            df: Counter[str] = Counter()
            tokenized = []
            for doc in corpus:
                tokens = set(_tokenize(doc))
                tokenized.append(tokens)
                df.update(tokens)

            n = len(corpus)
            # Select top _MAX_VOCAB terms by df
            top = sorted(df.items(), key=lambda x: -x[1])[:_MAX_VOCAB]
            self._vocab = {term: idx for idx, (term, _) in enumerate(top)}
            self._idf = {
                term: math.log((n + 1) / (count + 1)) + 1.0
                for term, count in top
            }
            self._n_docs = n
            self._frozen = True

    def _vectorize(self, text: str) -> list[float]:
        tokens = _tokenize(text)
        if not tokens:
            return [0.0] * self._dim
        tf: Counter[str] = Counter(tokens)
        vec = [0.0] * self._dim
        for term, count in tf.items():
            idx = self._vocab.get(term)
            if idx is None:
                continue
            tfidf = (count / len(tokens)) * self._idf.get(term, 1.0)
            vec[idx] = tfidf
        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    async def embed(self, text: str) -> list[float]:
        if not self._frozen:
            # Auto-train on single text (degenerate but safe)
            self.train([text])
        return self._vectorize(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not self._frozen:
            self.train(texts)
        return [self._vectorize(t) for t in texts]
