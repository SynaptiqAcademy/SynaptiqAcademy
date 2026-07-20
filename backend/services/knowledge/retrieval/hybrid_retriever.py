"""Hybrid retriever: semantic vector search + BM25 keyword search, merged via RRF.

Reciprocal Rank Fusion (RRF) combines semantic and keyword rankings without
needing calibrated scores from both systems — each contributes via rank position.
"""
from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from typing import TYPE_CHECKING

from services.knowledge.models import SearchResult
from services.knowledge.retrieval.filters import RetrievalFilter

if TYPE_CHECKING:
    from services.knowledge.embeddings.service import EmbeddingService
    from services.knowledge.vector_store.base import VectorStore

_STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
    "for", "of", "with", "by", "is", "was", "are", "this", "that",
}
_TOKEN_RE = re.compile(r"[a-zA-Z]{2,}")
_RRF_K = 60  # constant for RRF — typically 60


def _tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text) if t.lower() not in _STOP_WORDS]


def _bm25_score(
    query_terms: list[str],
    doc_terms: list[str],
    avgdl: float,
    df: dict[str, int],
    n_docs: int,
    k1: float = 1.5,
    b: float = 0.75,
) -> float:
    dl = len(doc_terms)
    tf_map = Counter(doc_terms)
    score = 0.0
    for term in query_terms:
        if term not in tf_map:
            continue
        idf = math.log((n_docs - df.get(term, 0) + 0.5) / (df.get(term, 0) + 0.5) + 1)
        tf = tf_map[term] * (k1 + 1) / (tf_map[term] + k1 * (1 - b + b * dl / max(avgdl, 1)))
        score += idf * tf
    return score


def _rrf_merge(
    semantic: list[SearchResult],
    keyword: list[SearchResult],
    sem_weight: float,
    kw_weight: float,
    top_k: int,
) -> list[SearchResult]:
    """Merge two ranked lists using Reciprocal Rank Fusion."""
    scores: dict[str, float] = defaultdict(float)
    result_map: dict[str, SearchResult] = {}

    for rank, r in enumerate(semantic):
        key = r.chunk_id
        scores[key] += sem_weight / (rank + _RRF_K)
        result_map[key] = r

    for rank, r in enumerate(keyword):
        key = r.chunk_id
        scores[key] += kw_weight / (rank + _RRF_K)
        if key not in result_map:
            result_map[key] = r

    merged = sorted(scores.items(), key=lambda x: -x[1])
    out: list[SearchResult] = []
    for chunk_id, fused_score in merged[:top_k]:
        r = result_map[chunk_id]
        out.append(SearchResult(
            chunk_id=chunk_id,
            document_id=r.document_id,
            text=r.text,
            score=fused_score,
            semantic_score=r.semantic_score,
            keyword_score=r.keyword_score,
            heading=r.heading,
            section=r.section,
            page_number=r.page_number,
            doi=r.doi,
            authors=r.authors,
            title=r.title,
            publication_year=r.publication_year,
            filename=r.filename,
        ))
    return out


class HybridRetriever:
    def __init__(
        self,
        vector_store: "VectorStore",
        embedding_service: "EmbeddingService",
        semantic_weight: float = 0.65,
        keyword_weight: float = 0.35,
    ) -> None:
        self._vs = vector_store
        self._emb = embedding_service
        self._sem_w = semantic_weight
        self._kw_w = keyword_weight

    async def retrieve(
        self,
        query: str,
        top_k: int,
        retrieval_filter: RetrievalFilter,
        min_score: float = 0.0,
    ) -> list[SearchResult]:
        # 1. Semantic search
        query_emb = await self._emb.embed(query)
        semantic_results = await self._vs.search(
            query_embedding=query_emb,
            top_k=top_k * 2,
            filter_user_id=retrieval_filter.user_id,
            filter_workspace_id=retrieval_filter.workspace_id,
        )

        # 2. Keyword search over the semantic candidates
        keyword_results = self._keyword_rerank(query, semantic_results)

        # 3. RRF merge
        merged = _rrf_merge(semantic_results, keyword_results, self._sem_w, self._kw_w, top_k)

        # 4. Filter by minimum score
        if min_score > 0:
            merged = [r for r in merged if r.semantic_score >= min_score]

        return merged

    def _keyword_rerank(
        self, query: str, candidates: list[SearchResult]
    ) -> list[SearchResult]:
        """BM25 reranking over the candidate pool."""
        if not candidates:
            return []
        query_terms = _tokenize(query)
        if not query_terms:
            return candidates

        tokenized = [_tokenize(r.text) for r in candidates]
        avgdl = sum(len(t) for t in tokenized) / max(len(tokenized), 1)
        df: dict[str, int] = defaultdict(int)
        for tokens in tokenized:
            for term in set(tokens):
                df[term] += 1

        scored: list[tuple[float, SearchResult]] = []
        for result, tokens in zip(candidates, tokenized):
            bm25 = _bm25_score(query_terms, tokens, avgdl, df, len(candidates))
            scored.append((bm25, result))

        scored.sort(key=lambda x: -x[0])
        results: list[SearchResult] = []
        for bm25, r in scored:
            r.keyword_score = bm25
            results.append(r)
        return results
