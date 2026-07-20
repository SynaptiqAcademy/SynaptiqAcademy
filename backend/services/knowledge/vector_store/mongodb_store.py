"""MongoDB Atlas Vector Search store (requires Atlas M10+ with vector index).

Falls back to NumpyVectorStore if $vectorSearch aggregation is unsupported.
"""
from __future__ import annotations

import logging

from services.knowledge.models import Chunk, SearchResult
from services.knowledge.vector_store.base import VectorStore
from services.knowledge.vector_store.numpy_store import NumpyVectorStore

logger = logging.getLogger(__name__)


class MongoDBVectorStore(VectorStore):
    """Uses Atlas $vectorSearch if available, otherwise delegates to NumpyVectorStore."""

    def __init__(self, db, index_name: str = "vector_index") -> None:
        self._db = db
        self._index_name = index_name
        self._coll = db["knowledge_chunks"]
        self._fallback = NumpyVectorStore(db)
        self._atlas_available: bool | None = None

    async def _check_atlas(self) -> bool:
        if self._atlas_available is not None:
            return self._atlas_available
        try:
            await self._db.command("ping")
            # Probe whether $vectorSearch is available
            pipeline = [
                {
                    "$vectorSearch": {
                        "index": self._index_name,
                        "path": "embedding",
                        "queryVector": [0.0] * 768,
                        "numCandidates": 1,
                        "limit": 1,
                    }
                }
            ]
            await self._coll.aggregate(pipeline).to_list(length=1)
            self._atlas_available = True
            logger.info("MongoDB Atlas Vector Search is available")
        except Exception:
            self._atlas_available = False
            logger.warning("MongoDB Atlas Vector Search unavailable; using numpy fallback")
        return self._atlas_available

    async def add_chunks(self, chunks: list[Chunk]) -> None:
        await self._fallback.add_chunks(chunks)

    async def search(
        self,
        query_embedding: list[float],
        top_k: int,
        filter_user_id: str | None = None,
        filter_workspace_id: str | None = None,
        filter_visibility: list[str] | None = None,
    ) -> list[SearchResult]:
        if await self._check_atlas():
            return await self._atlas_search(
                query_embedding, top_k, filter_user_id, filter_workspace_id, filter_visibility
            )
        return await self._fallback.search(
            query_embedding, top_k, filter_user_id, filter_workspace_id, filter_visibility
        )

    async def _atlas_search(
        self,
        query_embedding: list[float],
        top_k: int,
        filter_user_id: str | None,
        filter_workspace_id: str | None,
        filter_visibility: list[str] | None,
    ) -> list[SearchResult]:
        pre_filter: dict = {}
        if filter_user_id:
            pre_filter["user_id"] = filter_user_id
        if filter_workspace_id:
            pre_filter["workspace_id"] = filter_workspace_id
        if filter_visibility:
            pre_filter["visibility"] = {"$in": filter_visibility}

        pipeline = [
            {
                "$vectorSearch": {
                    "index": self._index_name,
                    "path": "embedding",
                    "queryVector": query_embedding,
                    "numCandidates": top_k * 10,
                    "limit": top_k,
                    **({"filter": pre_filter} if pre_filter else {}),
                }
            },
            {
                "$project": {
                    "text": 1, "document_id": 1, "chunk_index": 1,
                    "heading": 1, "section": 1, "page_number": 1,
                    "doi": 1, "authors": 1, "title": 1, "publication_year": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]
        try:
            docs = await self._coll.aggregate(pipeline).to_list(length=top_k)
        except Exception as exc:
            logger.error("Atlas $vectorSearch failed: %s; falling back to numpy", exc)
            self._atlas_available = False
            return await self._fallback.search(
                query_embedding, top_k, filter_user_id, filter_workspace_id, filter_visibility
            )

        return [
            SearchResult(
                chunk_id=str(d.get("_id", "")),
                document_id=d.get("document_id", ""),
                text=d.get("text", ""),
                score=float(d.get("score", 0.0)),
                semantic_score=float(d.get("score", 0.0)),
                heading=d.get("heading", ""),
                section=d.get("section", ""),
                page_number=d.get("page_number"),
                doi=d.get("doi", ""),
                authors=d.get("authors", []),
                title=d.get("title", ""),
                publication_year=d.get("publication_year"),
            )
            for d in docs
        ]

    async def delete_document(self, document_id: str) -> int:
        return await self._fallback.delete_document(document_id)

    async def chunk_count(self) -> int:
        return await self._fallback.chunk_count()

    async def get_chunks_by_document(self, document_id: str) -> list[Chunk]:
        return await self._fallback.get_chunks_by_document(document_id)
