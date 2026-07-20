"""Thread-safe telemetry for the Knowledge Engine."""
from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass, field

_MAX_HISTORY = 200


@dataclass
class _RetrievalRecord:
    query_length: int
    results: int
    latency_ms: int
    semantic_score: float
    from_cache: bool
    timestamp: float = field(default_factory=time.time)


class KnowledgeTelemetry:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reset()

    def _reset(self) -> None:
        self._docs_indexed: int = 0
        self._chunks_indexed: int = 0
        self._docs_failed: int = 0
        self._retrieval_count: int = 0
        self._retrieval_cache_hits: int = 0
        self._total_retrieval_ms: int = 0
        self._total_chunks_retrieved: int = 0
        self._embedding_count: int = 0
        self._embedding_cache_hits: int = 0
        self._indexing_queue_size: int = 0
        self._history: deque[_RetrievalRecord] = deque(maxlen=_MAX_HISTORY)

    def record_indexed(self, chunk_count: int) -> None:
        with self._lock:
            self._docs_indexed += 1
            self._chunks_indexed += chunk_count

    def record_failed(self) -> None:
        with self._lock:
            self._docs_failed += 1

    def record_retrieval(
        self,
        results: int,
        latency_ms: int,
        query_length: int = 0,
        top_score: float = 0.0,
        from_cache: bool = False,
    ) -> None:
        with self._lock:
            self._retrieval_count += 1
            self._total_retrieval_ms += latency_ms
            self._total_chunks_retrieved += results
            if from_cache:
                self._retrieval_cache_hits += 1
            self._history.append(_RetrievalRecord(
                query_length=query_length,
                results=results,
                latency_ms=latency_ms,
                semantic_score=top_score,
                from_cache=from_cache,
            ))

    def record_embedding(self, from_cache: bool = False) -> None:
        with self._lock:
            self._embedding_count += 1
            if from_cache:
                self._embedding_cache_hits += 1

    def set_queue_size(self, size: int) -> None:
        with self._lock:
            self._indexing_queue_size = size

    def get_stats(self) -> dict:
        with self._lock:
            r = self._retrieval_count
            avg_lat = (self._total_retrieval_ms / r) if r > 0 else 0.0
            avg_results = (self._total_chunks_retrieved / r) if r > 0 else 0.0
            cache_rate = (self._retrieval_cache_hits / r * 100) if r > 0 else 0.0
            e = self._embedding_count
            embed_cache = (self._embedding_cache_hits / e * 100) if e > 0 else 0.0
            return {
                "documents_indexed": self._docs_indexed,
                "chunks_indexed": self._chunks_indexed,
                "documents_failed": self._docs_failed,
                "retrieval_requests": r,
                "avg_retrieval_latency_ms": round(avg_lat, 1),
                "avg_chunks_returned": round(avg_results, 1),
                "retrieval_cache_hit_rate_pct": round(cache_rate, 1),
                "embedding_requests": e,
                "embedding_cache_hit_rate_pct": round(embed_cache, 1),
                "indexing_queue_size": self._indexing_queue_size,
                "recent_retrievals": [
                    {
                        "results": rec.results,
                        "latency_ms": rec.latency_ms,
                        "from_cache": rec.from_cache,
                        "score": round(rec.semantic_score, 3),
                        "timestamp": rec.timestamp,
                    }
                    for rec in reversed(self._history)
                ][:20],
            }

    def reset(self) -> None:
        with self._lock:
            self._reset()


_telemetry: KnowledgeTelemetry | None = None
_lock = threading.Lock()


def get_knowledge_telemetry() -> KnowledgeTelemetry:
    global _telemetry
    if _telemetry is None:
        with _lock:
            if _telemetry is None:
                _telemetry = KnowledgeTelemetry()
    return _telemetry
