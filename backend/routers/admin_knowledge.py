"""Admin Knowledge Engine dashboard — stats, documents, cache management."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from auth_utils import get_current_user
from repo.shim import DBProxy
from repo.security_context import SecurityContext
from zt.deps import zt_check, zt_is_admin, zt_is_super_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/knowledge", tags=["admin-knowledge"])


def _require_admin(user: dict = Depends(get_current_user)) -> dict:
    zt_check(user, "admin", "admin")
    return user


async def _engine():
    from services.knowledge.engine import get_knowledge_engine
    return await get_knowledge_engine()


@router.get("/status")
async def knowledge_status(admin=Depends(_require_admin)):
    """Overview: enabled state, chunk count, document count, embedding provider."""
    engine = await _engine()
    return await engine.get_stats()


@router.get("/documents")
async def list_all_documents(
    limit: int = Query(100, le=500),
    status: str | None = Query(None),
    admin=Depends(_require_admin),
):
    """List all indexed documents (admin view, all users)."""
    from db import get_db
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    query: dict = {}
    if status:
        query["status"] = status
    docs = await db["knowledge_documents"].find(query).sort("indexed_at", -1).limit(limit).to_list(length=limit)
    for d in docs:
        d["_id"] = str(d["_id"])
    return {"documents": docs, "count": len(docs)}


@router.delete("/documents/{document_id}")
async def admin_delete_document(document_id: str, admin=Depends(_require_admin)):
    """Delete any document regardless of owner."""
    from db import get_db
    engine = await _engine()
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    deleted = await engine._vs.delete_document(document_id)
    await db["knowledge_documents"].delete_one({"_id": document_id})
    return {"deleted_chunks": deleted, "document_id": document_id}


@router.get("/telemetry")
async def knowledge_telemetry(admin=Depends(_require_admin)):
    from services.knowledge.telemetry import get_knowledge_telemetry
    return get_knowledge_telemetry().get_stats()


@router.post("/telemetry/reset")
async def reset_telemetry(admin=Depends(_require_admin)):
    from services.knowledge.telemetry import get_knowledge_telemetry
    get_knowledge_telemetry().reset()
    return {"reset": True}


@router.delete("/cache")
async def clear_cache(admin=Depends(_require_admin)):
    engine = await _engine()
    engine.clear_caches()
    return {"cleared": True}


@router.get("/config")
async def get_config(admin=Depends(_require_admin)):
    engine = await _engine()
    c = engine._config
    return {
        "enabled": c.enabled,
        "rag_enabled": c.rag_enabled,
        "embedding_provider": c.embedding_provider,
        "embedding_model": c.embedding_model,
        "embedding_dim": c.embedding_dim,
        "vector_backend": c.vector_backend,
        "chunk_strategy": c.chunk_strategy,
        "chunk_max_tokens": c.chunk_max_tokens,
        "retrieval_top_k": c.retrieval_top_k,
        "retrieval_min_score": c.retrieval_min_score,
        "context_max_tokens": c.context_max_tokens,
        "context_max_chunks": c.context_max_chunks,
    }


@router.get("/queue")
async def indexing_queue_status(admin=Depends(_require_admin)):
    engine = await _engine()
    return {"queue_size": engine._indexer.queue_size()}


@router.get("/failed-documents")
async def list_failed_documents(
    limit: int = Query(50, le=200),
    admin=Depends(_require_admin),
):
    from db import get_db
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    docs = await db["knowledge_documents"].find(
        {"status": "failed"}, {"embedding": 0}
    ).sort("indexed_at", -1).limit(limit).to_list(length=limit)
    for d in docs:
        d["_id"] = str(d["_id"])
    return {"failed_documents": docs, "count": len(docs)}


@router.post("/test-retrieval")
async def test_retrieval(
    body: dict,
    admin=Depends(_require_admin),
):
    """Test retrieval for a given query (uses admin user_id)."""
    engine = await _engine()
    query = body.get("query", "")
    top_k = int(body.get("top_k", 5))
    user_id = body.get("user_id", str(admin.get("_id", "")))
    if not query:
        raise HTTPException(status_code=400, detail="query required")
    results = await engine.retrieve(query, user_id=user_id, top_k=top_k)
    return {
        "query": query,
        "results": [r.to_dict() for r in results],
        "count": len(results),
    }
