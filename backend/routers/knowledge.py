"""User-facing Knowledge Engine API — document management & retrieval."""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from auth_utils import get_current_user
from repo.shim import DBProxy
from repo.security_context import SecurityContext

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

_ALLOWED_TYPES = {"pdf", "docx", "doc", "txt", "md", "markdown", "html", "htm", "csv", "pptx"}
_MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


async def _engine():
    from services.knowledge.engine import get_knowledge_engine
    return await get_knowledge_engine()


@router.post("/documents")
async def upload_document(
    file: UploadFile = File(...),
    workspace_id: str | None = Form(None),
    visibility: str = Form("private"),
    source_kind: str = Form("upload"),
    source_id: str = Form(""),
    user=Depends(get_current_user),
):
    """Upload a document and queue it for indexing."""
    filename = file.filename or "untitled"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in _ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(_ALLOWED_TYPES))}",
        )
    content = await file.read()
    if len(content) > _MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large (max 50 MB)")
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")

    if visibility not in ("private", "workspace", "public"):
        visibility = "private"

    user_id = str(user.get("_id", ""))
    engine = await _engine()
    document_id = await engine.submit_document(
        content_bytes=content,
        filename=filename,
        user_id=user_id,
        file_type=ext,
        workspace_id=workspace_id,
        source_kind=source_kind,
        source_id=source_id,
        visibility=visibility,
    )
    return {
        "document_id": document_id,
        "filename": filename,
        "status": "queued",
        "message": "Document queued for indexing",
    }


@router.get("/documents")
async def list_documents(
    workspace_id: str | None = Query(None),
    limit: int = Query(50, le=200),
    user=Depends(get_current_user),
):
    """List the current user's indexed documents."""
    user_id = str(user.get("_id", ""))
    engine = await _engine()
    docs = await engine.list_documents(user_id, workspace_id, limit)
    return {"documents": docs, "count": len(docs)}


@router.get("/documents/{document_id}")
async def get_document(document_id: str, user=Depends(get_current_user)):
    """Get status and metadata for a specific document."""
    user_id = str(user.get("_id", ""))
    engine = await _engine()
    doc = await engine.get_document_status(document_id, user_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str, user=Depends(get_current_user)):
    """Delete a document and all its chunks from the knowledge base."""
    user_id = str(user.get("_id", ""))
    engine = await _engine()
    try:
        deleted = await engine.delete_document(document_id, user_id)
    except PermissionError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"deleted_chunks": deleted, "document_id": document_id}


@router.post("/search")
async def search_knowledge(body: dict, user=Depends(get_current_user)):
    """Semantic + keyword search across the user's knowledge base."""
    query = body.get("query", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
    top_k = min(int(body.get("top_k", 8)), 20)
    workspace_id = body.get("workspace_id")
    min_score = float(body.get("min_score", 0.0))

    user_id = str(user.get("_id", ""))
    engine = await _engine()
    results = await engine.retrieve(
        query=query,
        user_id=user_id,
        workspace_id=workspace_id,
        top_k=top_k,
        min_score=min_score,
    )
    return {
        "query": query,
        "results": [r.to_dict() for r in results],
        "count": len(results),
    }


@router.post("/context")
async def build_context(body: dict, user=Depends(get_current_user)):
    """Retrieve context + citations for use in AI prompts."""
    query = body.get("query", "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
    workspace_id = body.get("workspace_id")
    top_k = min(int(body.get("top_k", 6)), 15)

    user_id = str(user.get("_id", ""))
    engine = await _engine()
    context, citations = await engine.build_context(query, user_id, workspace_id, top_k)
    return {
        "query": query,
        "context": context,
        "citations": [c.to_dict() for c in citations],
        "citation_count": len(citations),
    }


@router.get("/stats")
async def knowledge_stats(user=Depends(get_current_user)):
    """User-facing stats: how many documents indexed, chunk count."""
    user_id = str(user.get("_id", ""))
    from db import get_db
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    doc_count = await db["knowledge_documents"].count_documents({"user_id": user_id})
    chunk_count = await db["knowledge_chunks"].count_documents({"user_id": user_id})
    return {
        "documents": doc_count,
        "chunks": chunk_count,
    }
