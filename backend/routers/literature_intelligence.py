"""Literature Intelligence Router — Phase VII complete academic literature analysis API.

User endpoints: /api/literature-intelligence/
Admin endpoints: /api/admin/literature-intelligence/

The existing /api/literature-review endpoints are UNCHANGED (backward compatible).
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from services.credits_service import consume_credits, refund_credits
from services.literature.models import ExportFormat, PaperSource, ReviewType
from services.permissions import require_feature
from zt.deps import zt_check, zt_is_admin, zt_is_super_admin

log = logging.getLogger("synaptiq.literature_intelligence")

router = APIRouter(prefix="/api/literature-intelligence", tags=["literature-intelligence"])
admin_router = APIRouter(prefix="/api/admin/literature-intelligence", tags=["admin-literature"])


# ── Auth helpers ───────────────────────────────────────────────────────────────

async def _require_admin(current_user=Depends(get_current_user)):
    zt_check(user, "admin", "admin")
    return current_user


async def _get_engine():
    from services.literature.engine import get_literature_engine
    return await get_literature_engine()


def _user_id(user: dict) -> str:
    return str(user.get("_id", user.get("id", "")))


# ═════════════════════════════════════════════════════════════════════════════
# SESSION MANAGEMENT
# ═════════════════════════════════════════════════════════════════════════════

class CreateSessionRequest(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    review_type: str = Field(default="narrative")
    description: str = Field(default="", max_length=500)


@router.post("/sessions")
async def create_session(
    body: CreateSessionRequest,
    user=Depends(require_feature("ai_literature_review")),
):
    """Create a new literature review session."""
    try:
        rt = ReviewType(body.review_type)
    except ValueError:
        raise HTTPException(422, f"Invalid review_type: {body.review_type}")

    engine = await _get_engine()
    session = await engine.create_session(
        user_id=_user_id(user),
        title=body.title,
        review_type=rt,
        description=body.description,
    )
    return session.to_dict()


@router.get("/sessions")
async def list_sessions(user=Depends(get_current_user)):
    """List the user's literature review sessions."""
    engine = await _get_engine()
    return await engine.list_sessions(_user_id(user))


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, user=Depends(get_current_user)):
    engine = await _get_engine()
    session = await engine.get_session(session_id, _user_id(user))
    if not session:
        raise HTTPException(404, "Session not found")
    return session.to_dict(include_full=True)


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, user=Depends(get_current_user)):
    engine = await _get_engine()
    ok = await engine.delete_session(session_id, _user_id(user))
    if not ok:
        raise HTTPException(404, "Session not found")
    return {"ok": True}


# ═════════════════════════════════════════════════════════════════════════════
# PAPER MANAGEMENT
# ═════════════════════════════════════════════════════════════════════════════

class AddPaperRequest(BaseModel):
    source: str                              # "doi" | "pmid" | "arxiv" | etc.
    source_id: str = Field(min_length=1)


@router.post("/sessions/{session_id}/papers")
async def add_paper(
    session_id: str,
    body: AddPaperRequest,
    user=Depends(get_current_user),
):
    """Add a single paper from an external source (DOI, PMID, arXiv, etc.)."""
    try:
        source = PaperSource(body.source.lower())
    except ValueError:
        raise HTTPException(422, f"Unknown source: {body.source}")

    engine = await _get_engine()
    result = await engine.add_paper_by_source(session_id, _user_id(user), source, body.source_id)
    if not result["ok"]:
        raise HTTPException(422, result.get("error", "Ingestion failed"))
    return result


class BatchAddRequest(BaseModel):
    papers: list[dict] = Field(max_length=500)


@router.post("/sessions/{session_id}/papers/batch")
async def add_papers_batch(
    session_id: str,
    body: BatchAddRequest,
    user=Depends(get_current_user),
):
    """Add up to 500 papers in one request."""
    engine = await _get_engine()
    return await engine.add_papers_batch(session_id, _user_id(user), body.papers)


@router.post("/sessions/{session_id}/papers/upload")
async def upload_paper(
    session_id: str,
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    """Upload a PDF, DOCX, TXT, or Markdown file as a paper."""
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:  # 20 MB
        raise HTTPException(413, "File too large (max 20 MB)")

    engine = await _get_engine()
    result = await engine.add_paper_from_file(session_id, _user_id(user), content, file.filename or "upload.txt")
    if not result["ok"]:
        raise HTTPException(422, result.get("error", "File parsing failed"))
    return result


@router.delete("/sessions/{session_id}/papers/{paper_id}")
async def remove_paper(session_id: str, paper_id: str, user=Depends(get_current_user)):
    engine = await _get_engine()
    ok = await engine.remove_paper(session_id, _user_id(user), paper_id)
    return {"ok": ok}


@router.get("/search")
async def search_papers(
    q: str = Query(min_length=3),
    sources: Optional[str] = Query(default=None, description="comma-separated: openalex,semantic_scholar"),
    limit: int = Query(default=20, ge=1, le=100),
    user=Depends(get_current_user),
):
    """Search OpenAlex and Semantic Scholar for papers."""
    source_list = [s.strip() for s in sources.split(",")] if sources else None
    engine = await _get_engine()
    return await engine.search_papers(q, source_list, limit)


# ═════════════════════════════════════════════════════════════════════════════
# ANALYSIS PIPELINE
# ═════════════════════════════════════════════════════════════════════════════

@router.post("/sessions/{session_id}/analyze")
async def analyze_papers(
    session_id: str,
    user=Depends(require_feature("ai_literature_review")),
):
    """Run 19-field AI analysis on all papers in the session."""
    engine = await _get_engine()
    result = await engine.analyze_papers(session_id, _user_id(user))
    if not result.get("ok"):
        raise HTTPException(422, result.get("error", "Analysis failed"))
    return result


@router.post("/sessions/{session_id}/compare")
async def compare_papers(session_id: str, user=Depends(get_current_user)):
    """Run multi-paper comparative analysis."""
    engine = await _get_engine()
    result = await engine.compare_papers(session_id, _user_id(user))
    if not result.get("ok"):
        raise HTTPException(422, result.get("error", "Comparison failed"))
    return result


@router.post("/sessions/{session_id}/cluster")
async def cluster_papers(session_id: str, user=Depends(get_current_user)):
    """Run thematic clustering on session papers."""
    engine = await _get_engine()
    return await engine.cluster_papers_session(session_id, _user_id(user))


@router.post("/sessions/{session_id}/evolution")
async def detect_evolution(session_id: str, user=Depends(get_current_user)):
    """Build chronological research evolution for the corpus."""
    engine = await _get_engine()
    return await engine.detect_evolution_session(session_id, _user_id(user))


class DetectGapsRequest(BaseModel):
    topic: str = Field(default="", max_length=300)


@router.post("/sessions/{session_id}/gaps")
async def detect_gaps(
    session_id: str,
    body: DetectGapsRequest,
    user=Depends(get_current_user),
):
    """Detect research gaps across the corpus."""
    engine = await _get_engine()
    return await engine.detect_gaps_session(session_id, _user_id(user), body.topic)


class GenerateReviewRequest(BaseModel):
    topic: str = Field(default="", max_length=300)
    additional_instructions: str = Field(default="", max_length=1000)


@router.post("/sessions/{session_id}/generate")
async def generate_review(
    session_id: str,
    body: GenerateReviewRequest,
    user=Depends(require_feature("ai_literature_review")),
):
    """Generate the full AI-written academic review (costs credits)."""
    engine = await _get_engine()
    result = await engine.generate_review_session(
        session_id, _user_id(user), body.topic, body.additional_instructions
    )
    if not result.get("ok"):
        raise HTTPException(422, result.get("error", "Generation failed"))
    return result


# ═════════════════════════════════════════════════════════════════════════════
# VISUALIZATIONS
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/sessions/{session_id}/visualizations")
async def get_visualizations(session_id: str, user=Depends(get_current_user)):
    """Get all visualization data structures for the session."""
    engine = await _get_engine()
    return await engine.get_visualizations(session_id, _user_id(user))


@router.get("/sessions/{session_id}/citation-network")
async def get_citation_network(session_id: str, user=Depends(get_current_user)):
    engine = await _get_engine()
    return await engine.get_citation_network(session_id, _user_id(user))


@router.get("/sessions/{session_id}/author-collaboration")
async def get_author_collaboration(session_id: str, user=Depends(get_current_user)):
    engine = await _get_engine()
    return await engine.get_author_collaboration(session_id, _user_id(user))


# ═════════════════════════════════════════════════════════════════════════════
# EXPORT
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/sessions/{session_id}/export/{fmt}")
async def export_session(
    session_id: str,
    fmt: str,
    user=Depends(get_current_user),
):
    """Export the session in the requested format."""
    try:
        export_fmt = ExportFormat(fmt.lower())
    except ValueError:
        raise HTTPException(422, f"Unknown export format: {fmt}. "
                            f"Supported: {[f.value for f in ExportFormat]}")

    engine = await _get_engine()
    content, filename, content_type = await engine.export_session_data(
        session_id, _user_id(user), export_fmt
    )
    if not content:
        raise HTTPException(404, "Session not found or has no content")

    return Response(
        content=content.encode("utf-8"),
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ═════════════════════════════════════════════════════════════════════════════
# METADATA
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/templates")
async def get_templates(_=Depends(get_current_user)):
    """Return all available review type templates and their structures."""
    engine = await _get_engine()
    return engine.get_supported_templates()


# ═════════════════════════════════════════════════════════════════════════════
# ADMIN ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════

@admin_router.get("/overview")
async def admin_overview(_=Depends(_require_admin)):
    engine = await _get_engine()
    return engine.get_telemetry_stats()


@admin_router.get("/telemetry")
async def admin_telemetry(_=Depends(_require_admin)):
    engine = await _get_engine()
    return engine.get_telemetry_stats()


@admin_router.get("/sessions")
async def admin_list_sessions(limit: int = Query(default=50, ge=1, le=200),
                              _=Depends(_require_admin)):
    engine = await _get_engine()
    return await engine.admin_list_sessions(limit)


@admin_router.post("/telemetry/reset")
async def admin_reset_telemetry(_=Depends(_require_admin)):
    engine = await _get_engine()
    engine._telemetry.reset()
    return {"ok": True}


@admin_router.get("/sources")
async def admin_list_sources(_=Depends(_require_admin)):
    return {
        "api_sources": [s.value for s in PaperSource if s not in (PaperSource.PDF, PaperSource.DOCX, PaperSource.TXT, PaperSource.MARKDOWN)],
        "file_sources": ["pdf", "docx", "txt", "markdown"],
        "review_types": [rt.value for rt in ReviewType],
        "export_formats": [f.value for f in ExportFormat],
    }
