"""In-process numpy vector store backed by MongoDB for persistence.

Embeddings are stored in MongoDB (`knowledge_chunks`) and loaded into a numpy
matrix on first search. New chunks are appended in-memory and persisted to
MongoDB. Index is rebuilt from MongoDB on startup if chunks exist.
"""
from __future__ import annotations

import asyncio
import logging
import time

import numpy as np

from services.knowledge.models import Chunk, SearchResult
from services.knowledge.vector_store.base import VectorStore

logger = logging.getLogger(__name__)

_CHUNK_COLL = "knowledge_chunks"


def _cosine_matrix(query: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Return cosine similarity scores: (N,) for query (D,) and matrix (N, D)."""
    q_norm = np.linalg.norm(query)
    if q_norm == 0:
        return np.zeros(matrix.shape[0])
    m_norms = np.linalg.norm(matrix, axis=1)
    m_norms[m_norms == 0] = 1.0
    return (matrix @ query) / (m_norms * q_norm)


class NumpyVectorStore(VectorStore):
    def __init__(self, db) -> None:
        self._db = db
        self._matrix: np.ndarray | None = None    # (N, dim)
        self._meta: list[dict] = []               # parallel list of chunk metadata
        self._loaded = False
        self._rebuild_lock: asyncio.Lock | None = None

    def _get_lock(self) -> asyncio.Lock:
        if self._rebuild_lock is None:
            self._rebuild_lock = asyncio.Lock()
        return self._rebuild_lock

    async def _ensure_index(self) -> None:
        """Load embeddings from MongoDB into memory on first use."""
        if self._loaded:
            return
        async with self._get_lock():
            if self._loaded:
                return
            t0 = time.monotonic()
            chunks = await self._db[_CHUNK_COLL].find(
                {}, {"embedding": 1, "text": 1, "document_id": 1, "chunk_index": 1,
                     "heading": 1, "section": 1, "page_number": 1, "user_id": 1,
                     "workspace_id": 1, "visibility": 1, "doi": 1, "authors": 1,
                     "title": 1, "publication_year": 1}
            ).to_list(length=None)

            if chunks:
                valid = [c for c in chunks if c.get("embedding")]
                if valid:
                    self._matrix = np.array(
                        [c["embedding"] for c in valid], dtype=np.float32
                    )
                    self._meta = valid
            self._loaded = True
            logger.info(
                "NumpyVectorStore: loaded %d chunks in %.1fs",
                len(self._meta), time.monotonic() - t0,
            )

    async def add_chunks(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        docs = [c.to_mongo_dict() for c in chunks]
        result = await self._db[_CHUNK_COLL].insert_many(docs)

        # Append to in-memory index
        new_embeddings = [c.embedding for c in chunks if c.embedding]
        if new_embeddings and self._loaded:
            new_matrix = np.array(new_embeddings, dtype=np.float32)
            if self._matrix is None:
                self._matrix = new_matrix
            else:
                self._matrix = np.vstack([self._matrix, new_matrix])
            # Add metadata, injecting the new _id from insertion
            for chunk, inserted_id in zip(chunks, result.inserted_ids):
                d = chunk.to_mongo_dict()
                d["_id"] = inserted_id
                self._meta.append(d)

    async def search(
        self,
        query_embedding: list[float],
        top_k: int,
        filter_user_id: str | None = None,
        filter_workspace_id: str | None = None,
        filter_visibility: list[str] | None = None,
    ) -> list[SearchResult]:
        await self._ensure_index()

        if self._matrix is None or len(self._meta) == 0:
            return []

        q = np.array(query_embedding, dtype=np.float32)
        scores = _cosine_matrix(q, self._matrix)

        # Sort by score descending
        top_indices = np.argsort(-scores)

        results: list[SearchResult] = []
        for idx in top_indices:
            if len(results) >= top_k:
                break
            m = self._meta[idx]
            score = float(scores[idx])
            if score < 0:
                continue
            # Permission filter
            if filter_user_id and m.get("user_id") != filter_user_id:
                vis = m.get("visibility", "private")
                if vis == "private":
                    continue
                if vis == "workspace":
                    if not filter_workspace_id or m.get("workspace_id") != filter_workspace_id:
                        continue
            if filter_visibility and m.get("visibility") not in filter_visibility:
                continue
            chunk_id = str(m.get("_id", ""))
            results.append(SearchResult(
                chunk_id=chunk_id,
                document_id=m.get("document_id", ""),
                text=m.get("text", ""),
                score=score,
                semantic_score=score,
                heading=m.get("heading", ""),
                section=m.get("section", ""),
                page_number=m.get("page_number"),
                doi=m.get("doi", ""),
                authors=m.get("authors", []),
                title=m.get("title", ""),
                publication_year=m.get("publication_year"),
            ))
        return results

    async def delete_document(self, document_id: str) -> int:
        result = await self._db[_CHUNK_COLL].delete_many({"document_id": document_id})
        # Remove from in-memory index
        if self._loaded and self._meta:
            keep = [
                i for i, m in enumerate(self._meta) if m.get("document_id") != document_id
            ]
            if keep and self._matrix is not None:
                self._matrix = self._matrix[keep]
                self._meta = [self._meta[i] for i in keep]
            else:
                self._matrix = None
                self._meta = []
        return result.deleted_count

    async def chunk_count(self) -> int:
        return await self._db[_CHUNK_COLL].count_documents({})

    async def get_chunks_by_document(self, document_id: str) -> list[Chunk]:
        docs = await self._db[_CHUNK_COLL].find({"document_id": document_id}).to_list(length=None)
        chunks = []
        for d in docs:
            chunks.append(Chunk(
                document_id=d.get("document_id", ""),
                chunk_index=d.get("chunk_index", 0),
                text=d.get("text", ""),
                heading=d.get("heading", ""),
                section=d.get("section", ""),
                page_number=d.get("page_number"),
                token_count=d.get("token_count", 0),
                embedding=d.get("embedding", []),
                user_id=d.get("user_id", ""),
                workspace_id=d.get("workspace_id"),
                visibility=d.get("visibility", "private"),
                doi=d.get("doi", ""),
                authors=d.get("authors", []),
                title=d.get("title", ""),
                publication_year=d.get("publication_year"),
            ))
        return chunks
