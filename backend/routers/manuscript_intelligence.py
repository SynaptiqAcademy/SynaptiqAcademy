"""Manuscript Intelligence 2.0 Router — Phase IX.

User endpoints:   /api/manuscript-intelligence/
Admin endpoints:  /api/admin/manuscript-intelligence/

The original /api/manuscript-review endpoints are UNCHANGED (backward compatible).
The original /api/manuscripts endpoints are UNCHANGED (backward compatible).
New collection: manuscript_intelligence_results
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from services.credits_service import consume_credits, refund_credits
from services.permissions import require_feature
from services.manuscript.models import ReviewDepth, ExportFormat, InputFormat
from services.manuscript.doc_parser import detect_format, MAX_CONTENT_CHARS, MIN_CONTENT_CHARS
from zt.deps import zt_check, zt_is_admin, zt_is_super_admin

log = logging.getLogger("synaptiq.manuscript_intelligence")

router = APIRouter(
    prefix="/api/manuscript-intelligence",
    tags=["manuscript-intelligence"],
)
admin_router = APIRouter(
    prefix="/api/admin/manuscript-intelligence",
    tags=["admin-manuscript-intelligence"],
)

_CREDIT_COSTS = {
    ReviewDepth.QUICK: 5,
    ReviewDepth.STANDARD: 15,
    ReviewDepth.DEEP: 25,
}

ALLOWED_MIME = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "text/plain",
    "text/markdown",
    "text/x-latex",
    "application/x-latex",
}
MAX_FILE_BYTES = 50 * 1024 * 1024


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _require_admin(user=Depends(get_current_user)):
    zt_check(user, "admin", "admin")
    return user


async def _get_engine():
    from services.manuscript.engine import get_manuscript_engine
    return await get_manuscript_engine()


def _uid(user: dict) -> str:
    return str(user.get("_id", user.get("id", "")))


# ── Request models ────────────────────────────────────────────────────────────

class TextReviewRequest(BaseModel):
    content: str = Field(..., min_length=200, max_length=80_000,
                         description="Full manuscript text")
    review_depth: str = Field(default="standard", description="quick | standard | deep")
    filename: str = Field(default="manuscript.txt")
    manuscript_id: str = Field(default="")
    target_journal: str = Field(default="", max_length=200)
    discipline: str = Field(default="", max_length=100)
    input_format: str = Field(default="text", description="text | markdown | latex")


# ══════════════════════════════════════════════════════════════════════════════
# USER ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/review/upload")
async def review_upload(
    file: UploadFile = File(...),
    review_depth: str = Form(default="standard"),
    manuscript_id: Optional[str] = Form(default=None),
    target_journal: Optional[str] = Form(default=""),
    discipline: Optional[str] = Form(default=""),
    user=Depends(require_feature("ai_manuscript_review")),
):
    """
    Upload a PDF, DOCX, Markdown, LaTeX, or TXT file for intelligent review.
    Credits: quick=5, standard=15, deep=25.
    """
    if file.content_type and file.content_type not in ALLOWED_MIME:
        raise HTTPException(415, f"Unsupported file type: {file.content_type}")

    try:
        depth = ReviewDepth(review_depth)
    except ValueError:
        raise HTTPException(422, f"Invalid review_depth: {review_depth}")

    data = await file.read()
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(413, f"File exceeds {MAX_FILE_BYTES // 1024 // 1024} MB")

    fmt = detect_format(file.filename or "manuscript", file.content_type or "")

    charged = await consume_credits(
        _uid(user), "ai_manuscript_review",
        metadata={"filename": file.filename, "depth": depth.value},
    )
    credits_used = charged.get("consumed", _CREDIT_COSTS[depth])

    try:
        engine = await _get_engine()
        from services.manuscript.models import ManuscriptReviewRequest
        request = ManuscriptReviewRequest(
            content=data,
            filename=file.filename or "manuscript",
            input_format=fmt,
            review_depth=depth,
            user_id=_uid(user),
            manuscript_id=manuscript_id or "",
            target_journal=target_journal or "",
            discipline=discipline or "",
        )
        result = await engine.review(request)
        result.credits_used = credits_used
    except Exception as exc:
        await refund_credits(_uid(user), "ai_manuscript_review", reason=str(exc)[:200])
        log.error("Manuscript intelligence review failed: %s", exc)
        raise HTTPException(503, "Review failed. Credits refunded.")

    return result.to_dict()


@router.post("/review/text")
async def review_text(
    body: TextReviewRequest,
    user=Depends(require_feature("ai_manuscript_review")),
):
    """
    Review manuscript from raw text (no file upload required).
    Supports text, markdown, or latex format hints.
    Credits: quick=5, standard=15, deep=25.
    """
    try:
        depth = ReviewDepth(body.review_depth)
    except ValueError:
        raise HTTPException(422, f"Invalid review_depth: {body.review_depth}")

    fmt_map = {"text": InputFormat.TXT, "markdown": InputFormat.MARKDOWN, "latex": InputFormat.LATEX}
    fmt = fmt_map.get(body.input_format.lower(), InputFormat.TXT)

    charged = await consume_credits(
        _uid(user), "ai_manuscript_review",
        metadata={"filename": body.filename, "depth": depth.value},
    )
    credits_used = charged.get("consumed", _CREDIT_COSTS[depth])

    try:
        engine = await _get_engine()
        from services.manuscript.models import ManuscriptReviewRequest
        request = ManuscriptReviewRequest(
            content=body.content,
            filename=body.filename,
            input_format=fmt,
            review_depth=depth,
            user_id=_uid(user),
            manuscript_id=body.manuscript_id,
            target_journal=body.target_journal,
            discipline=body.discipline,
        )
        result = await engine.review(request)
        result.credits_used = credits_used
    except Exception as exc:
        await refund_credits(_uid(user), "ai_manuscript_review", reason=str(exc)[:200])
        log.error("Text manuscript review failed: %s", exc)
        raise HTTPException(503, "Review failed. Credits refunded.")

    return result.to_dict()


@router.post("/review/quick")
async def review_quick(
    body: TextReviewRequest,
    user=Depends(require_feature("ai_manuscript_review")),
):
    """Quick 5-credit review — AI only, no deep rule analysis."""
    body.review_depth = "quick"
    return await review_text(body, user)


@router.get("/history")
async def list_reviews(
    limit: int = Query(default=20, ge=1, le=100),
    user=Depends(get_current_user),
):
    engine = await _get_engine()
    return await engine.list_results(_uid(user), limit=limit)


@router.get("/{result_id}")
async def get_review(result_id: str, user=Depends(get_current_user)):
    engine = await _get_engine()
    result = await engine.get_result(result_id, _uid(user))
    if not result:
        raise HTTPException(404, "Review not found")
    return result.to_dict()


@router.get("/{result_id}/summary")
async def get_review_summary(result_id: str, user=Depends(get_current_user)):
    engine = await _get_engine()
    result = await engine.get_result(result_id, _uid(user))
    if not result:
        raise HTTPException(404, "Review not found")
    return result.to_summary()


@router.get("/{result_id}/export/{fmt}")
async def export_review(result_id: str, fmt: str, user=Depends(get_current_user)):
    """Export a review in the specified format."""
    try:
        export_fmt = ExportFormat(fmt.lower())
    except ValueError:
        raise HTTPException(
            422, f"Unknown format: {fmt}. Supported: {[f.value for f in ExportFormat]}"
        )
    engine = await _get_engine()
    content, filename, ct = await engine.export(result_id, _uid(user), export_fmt)
    if not content:
        raise HTTPException(404, "Review not found")
    return Response(
        content=content.encode("utf-8"),
        media_type=ct,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{result_id}/visualizations")
async def get_visualizations(result_id: str, user=Depends(get_current_user)):
    engine = await _get_engine()
    result = await engine.get_result(result_id, _uid(user))
    if not result:
        raise HTTPException(404, "Review not found")
    return result.visualizations


@router.get("/{result_id}/peer-review")
async def get_peer_review_text(result_id: str, user=Depends(get_current_user)):
    """Retrieve the full peer review text."""
    engine = await _get_engine()
    result = await engine.get_result(result_id, _uid(user))
    if not result:
        raise HTTPException(404, "Review not found")
    return {
        "result_id": result_id,
        "peer_review_text": result.peer_review_text,
        "editorial_assessment": result.editorial_assessment,
        "recommendation": result.recommendation.value,
    }


@router.get("/{result_id}/issues")
async def get_issues(result_id: str, user=Depends(get_current_user)):
    """Retrieve all detected issues grouped by severity."""
    engine = await _get_engine()
    result = await engine.get_result(result_id, _uid(user))
    if not result:
        raise HTTPException(404, "Review not found")
    return {
        "critical": [i.to_dict() for i in result.critical_issues],
        "major": [i.to_dict() for i in result.major_issues],
        "minor": [i.to_dict() for i in result.minor_issues],
        "suggestions": [i.to_dict() for i in result.suggestions],
    }


@router.get("/{result_id}/journal-matches")
async def get_journal_matches(result_id: str, user=Depends(get_current_user)):
    engine = await _get_engine()
    result = await engine.get_result(result_id, _uid(user))
    if not result:
        raise HTTPException(404, "Review not found")
    return {"journal_matches": [j.to_dict() for j in result.journal_matches]}


@router.get("/meta/review-depths")
async def list_review_depths(_=Depends(get_current_user)):
    return {
        "depths": [
            {
                "value": d.value,
                "credits": _CREDIT_COSTS[d],
                "description": {
                    "quick": "AI review only — fast, 5 credits",
                    "standard": "Rule-based + AI review — recommended, 15 credits",
                    "deep": "Full pipeline + journal matching — comprehensive, 25 credits",
                }[d.value],
            }
            for d in ReviewDepth
        ]
    }


@router.get("/meta/export-formats")
async def list_export_formats(_=Depends(get_current_user)):
    return {"formats": [f.value for f in ExportFormat]}


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@admin_router.get("/overview")
async def admin_overview(_=Depends(_require_admin)):
    engine = await _get_engine()
    return engine.get_telemetry_stats()


@admin_router.get("/results")
async def admin_list_results(
    limit: int = Query(default=50, ge=1, le=200),
    _=Depends(_require_admin),
):
    engine = await _get_engine()
    return await engine.admin_list_results(limit)


@admin_router.post("/telemetry/reset")
async def admin_reset_telemetry(_=Depends(_require_admin)):
    engine = await _get_engine()
    engine._telemetry.reset()
    return {"ok": True}


@admin_router.get("/supported-formats")
async def admin_supported_formats(_=Depends(_require_admin)):
    return {
        "input_formats": [f.value for f in InputFormat],
        "export_formats": [f.value for f in ExportFormat],
        "review_depths": {d.value: _CREDIT_COSTS[d] for d in ReviewDepth},
        "allowed_mime_types": list(ALLOWED_MIME),
        "max_file_size_mb": MAX_FILE_BYTES // 1024 // 1024,
        "max_text_chars": MAX_CONTENT_CHARS,
    }
