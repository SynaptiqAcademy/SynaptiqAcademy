"""Research Gap Intelligence Router — Phase VIII.

User endpoints:   /api/research-gap-intelligence/
Admin endpoints:  /api/admin/research-gap-intelligence/

The original /api/research-gap-finder endpoints are UNCHANGED (backward compatible).
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from services.credits_service import consume_credits, refund_credits
from services.permissions import require_feature
from services.research_gap.models import (
    AnalysisDepth, ExportFormat, GapType, GapIntelligenceRequest, InputSource,
)
from repo.shim import DBProxy
from repo.security_context import SecurityContext
from zt.deps import zt_check, zt_is_admin, zt_is_super_admin

log = logging.getLogger("synaptiq.research_gap_intelligence")

router = APIRouter(
    prefix="/api/research-gap-intelligence",
    tags=["research-gap-intelligence"],
)
admin_router = APIRouter(
    prefix="/api/admin/research-gap-intelligence",
    tags=["admin-research-gap"],
)

_CREDIT_COSTS = {
    AnalysisDepth.QUICK: 5,
    AnalysisDepth.STANDARD: 10,
    AnalysisDepth.DEEP: 20,
}


# ── Auth helpers ───────────────────────────────────────────────────────────────

async def _require_admin(user=Depends(get_current_user)):
    zt_check(user, "admin", "admin")
    return user


async def _get_engine():
    from services.research_gap.engine import get_gap_engine
    return await get_gap_engine()


def _uid(user: dict) -> str:
    return str(user.get("_id", user.get("id", "")))


# ══════════════════════════════════════════════════════════════════════════════
# REQUEST MODELS
# ══════════════════════════════════════════════════════════════════════════════

class AnalyzeRequest(BaseModel):
    topic: str = Field(..., min_length=3, max_length=300)
    content: str = Field(default="", max_length=20000,
                         description="Raw text: abstract, notes, literature extract")
    lit_session_id: str = Field(default="",
                                description="Link to a Literature Intelligence session")
    analysis_depth: str = Field(default="standard",
                                description="quick | standard | deep")
    focus_gap_types: list[str] = Field(default=[], max_length=18,
                                       description="Restrict to specific gap types; empty = all")
    discipline: str = Field(default="", max_length=100)
    methodology_preference: str = Field(default="", max_length=200)
    year_from: Optional[int] = Field(default=None, ge=1900, le=2100)
    year_to: Optional[int] = Field(default=None, ge=1900, le=2100)
    target_journal_type: str = Field(default="", max_length=200)
    additional_context: str = Field(default="", max_length=2000)


class QuickAnalyzeRequest(BaseModel):
    """Simplified request for quick text-only analysis (5 credits)."""
    topic: str = Field(..., min_length=3, max_length=300)
    content: str = Field(default="", max_length=10000)
    discipline: str = Field(default="", max_length=100)


# ══════════════════════════════════════════════════════════════════════════════
# USER ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/analyze")
async def analyze(
    body: AnalyzeRequest,
    user=Depends(require_feature("ai_research_gap_finder")),
):
    """Run a full research gap intelligence analysis. Costs 5–20 credits by depth."""
    try:
        depth = AnalysisDepth(body.analysis_depth)
    except ValueError:
        raise HTTPException(422, f"Invalid analysis_depth: {body.analysis_depth}")

    focus_types: list[GapType] = []
    for gt_str in body.focus_gap_types:
        try:
            focus_types.append(GapType(gt_str))
        except ValueError:
            raise HTTPException(422, f"Unknown gap type: {gt_str}")

    credit_cost = _CREDIT_COSTS[depth]
    charged = await consume_credits(
        _uid(user),
        "ai_research_gap_finder",
        metadata={"topic": body.topic[:80], "depth": depth.value},
    )
    credits_used = charged.get("consumed", credit_cost)

    try:
        engine = await _get_engine()
        request = GapIntelligenceRequest(
            topic=body.topic,
            content=body.content,
            lit_session_id=body.lit_session_id,
            input_sources=[InputSource.TEXT] + (
                [InputSource.LIT_SESSION] if body.lit_session_id else []
            ),
            analysis_depth=depth,
            focus_gap_types=focus_types,
            discipline=body.discipline,
            methodology_preference=body.methodology_preference,
            year_from=body.year_from,
            year_to=body.year_to,
            target_journal_type=body.target_journal_type,
            additional_context=body.additional_context,
            user_id=_uid(user),
        )
        result = await engine.analyze(request)
        result.credits_used = credits_used
    except Exception as exc:
        await refund_credits(_uid(user), "ai_research_gap_finder", reason=str(exc)[:200])
        log.error("Gap intelligence analysis failed: %s", exc)
        raise HTTPException(503, "Analysis failed. Credits have been refunded.")

    return result.to_dict()


@router.post("/analyze/quick")
async def analyze_quick(
    body: QuickAnalyzeRequest,
    user=Depends(require_feature("ai_research_gap_finder")),
):
    """Quick text-only analysis — 5 credits, returns in ~30 seconds."""
    charged = await consume_credits(
        _uid(user), "ai_research_gap_finder",
        metadata={"topic": body.topic[:80], "depth": "quick"},
    )
    credits_used = charged.get("consumed", 5)

    try:
        engine = await _get_engine()
        request = GapIntelligenceRequest(
            topic=body.topic,
            content=body.content,
            input_sources=[InputSource.TEXT],
            analysis_depth=AnalysisDepth.QUICK,
            discipline=body.discipline,
            user_id=_uid(user),
        )
        result = await engine.analyze(request)
        result.credits_used = credits_used
    except Exception as exc:
        await refund_credits(_uid(user), "ai_research_gap_finder", reason=str(exc)[:200])
        log.error("Quick gap analysis failed: %s", exc)
        raise HTTPException(503, "Analysis failed. Credits refunded.")

    return result.to_dict()


@router.get("/history")
async def list_analyses(
    limit: int = Query(default=20, ge=1, le=100),
    user=Depends(get_current_user),
):
    """List the user's past gap intelligence analyses."""
    engine = await _get_engine()
    return await engine.list_results(_uid(user), limit=limit)


@router.get("/{result_id}")
async def get_analysis(result_id: str, user=Depends(get_current_user)):
    """Fetch a full gap intelligence result by ID."""
    engine = await _get_engine()
    result = await engine.get_result(result_id, _uid(user))
    if not result:
        raise HTTPException(404, "Analysis not found")
    return result.to_dict()


@router.get("/{result_id}/export/{fmt}")
async def export_analysis(result_id: str, fmt: str, user=Depends(get_current_user)):
    """Export a gap analysis in the requested format."""
    try:
        export_fmt = ExportFormat(fmt.lower())
    except ValueError:
        raise HTTPException(
            422,
            f"Unknown format: {fmt}. Supported: {[f.value for f in ExportFormat]}",
        )
    engine = await _get_engine()
    content, filename, content_type = await engine.export(result_id, _uid(user), export_fmt)
    if not content:
        raise HTTPException(404, "Result not found")
    return Response(
        content=content.encode("utf-8"),
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{result_id}/visualizations")
async def get_visualizations(result_id: str, user=Depends(get_current_user)):
    """Fetch visualization data structures for a gap analysis."""
    engine = await _get_engine()
    result = await engine.get_result(result_id, _uid(user))
    if not result:
        raise HTTPException(404, "Analysis not found")
    return result.visualizations


@router.get("/{result_id}/gaps")
async def get_gaps_only(result_id: str, user=Depends(get_current_user)):
    """Fetch just the detected gaps from an analysis."""
    engine = await _get_engine()
    result = await engine.get_result(result_id, _uid(user))
    if not result:
        raise HTTPException(404, "Analysis not found")
    from db import get_db
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    doc = await db.gap_intelligence_results.find_one(
        {"result_id": result_id}, {"detected_gaps": 1}
    )
    return {"gaps": doc.get("detected_gaps", []) if doc else []}


@router.get("/meta/gap-types")
async def list_gap_types(_=Depends(get_current_user)):
    """List all 18 supported gap types with metadata."""
    from services.research_gap.taxonomy import GAP_METADATA
    return {
        gt.value: {
            "label": meta["label"],
            "description": meta["description"],
            "typical_design": meta["typical_design"],
        }
        for gt, meta in GAP_METADATA.items()
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


@admin_router.get("/gap-taxonomy")
async def admin_gap_taxonomy(_=Depends(_require_admin)):
    from services.research_gap.taxonomy import GAP_METADATA, SCORE_WEIGHTS
    return {
        "gap_types": {
            gt.value: meta for gt, meta in GAP_METADATA.items()
        },
        "score_weights": SCORE_WEIGHTS,
        "supported_export_formats": [f.value for f in ExportFormat],
        "supported_analysis_depths": [d.value for d in AnalysisDepth],
    }


@admin_router.post("/telemetry/reset")
async def admin_reset_telemetry(_=Depends(_require_admin)):
    engine = await _get_engine()
    engine._telemetry.reset()
    return {"ok": True}
