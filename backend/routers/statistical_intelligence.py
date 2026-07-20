"""Statistical Intelligence 2.0 Router — Phase X.

User endpoints:   /api/statistical-intelligence/
Admin endpoints:  /api/admin/statistical-intelligence/

The original /api/statistical-review endpoints are UNCHANGED (backward compatible).
The original statistical_reviews MongoDB collection is UNCHANGED.
New collection: statistical_intelligence_results.
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
from services.statistical.models import AnalysisDepth, ExportFormat, InputFormat
from services.statistical.data_parser import detect_format, MAX_CONTENT_CHARS
from zt.deps import zt_check, zt_is_admin, zt_is_super_admin

log = logging.getLogger("synaptiq.statistical_intelligence")

router = APIRouter(
    prefix="/api/statistical-intelligence",
    tags=["statistical-intelligence"],
)
admin_router = APIRouter(
    prefix="/api/admin/statistical-intelligence",
    tags=["admin-statistical-intelligence"],
)

_CREDIT_COSTS = {
    AnalysisDepth.QUICK:    10,
    AnalysisDepth.STANDARD: 20,
    AnalysisDepth.DEEP:     35,
}

ALLOWED_MIME = {
    "text/plain", "text/csv", "application/csv", "application/json", "text/json",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.ms-excel", "application/x-spss-sav", "application/x-stata-dta",
}
MAX_FILE_BYTES = 50 * 1024 * 1024


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _require_admin(user=Depends(get_current_user)):
    zt_check(user, "admin", "admin")
    return user


async def _get_engine():
    from services.statistical.engine import get_statistical_engine
    return await get_statistical_engine()


def _uid(user: dict) -> str:
    return str(user.get("_id", user.get("id", "")))


# ── Request models ────────────────────────────────────────────────────────────

class TextAnalysisRequest(BaseModel):
    content: str = Field(
        ..., min_length=20, max_length=80_000,
        description="Statistical results, research output, or study description",
    )
    topic: str = Field(default="", max_length=300)
    research_question: str = Field(default="", max_length=1000)
    methodology: str = Field(default="", max_length=500)
    hypotheses: str = Field(default="", max_length=2000)
    sample_size_text: str = Field(default="", max_length=100)
    discipline: str = Field(default="", max_length=100)
    analysis_depth: str = Field(default="standard", description="quick | standard | deep")
    input_format: str = Field(default="text", description="text | csv | json")
    target_journal: str = Field(default="", max_length=200)


# ══════════════════════════════════════════════════════════════════════════════
# USER ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/analyse/upload")
async def analyse_upload(
    file: UploadFile = File(...),
    topic: str = Form(default=""),
    research_question: str = Form(default=""),
    methodology: str = Form(default=""),
    hypotheses: str = Form(default=""),
    analysis_depth: str = Form(default="standard"),
    discipline: str = Form(default=""),
    target_journal: str = Form(default=""),
    user=Depends(require_feature("ai_statistical_review")),
):
    """Upload CSV, Excel, SPSS, Stata, JSON, or TXT for statistical intelligence analysis."""
    try:
        depth = AnalysisDepth(analysis_depth)
    except ValueError:
        raise HTTPException(422, f"Invalid analysis_depth: {analysis_depth}")

    data = await file.read()
    if len(data) > MAX_FILE_BYTES:
        raise HTTPException(413, f"File exceeds {MAX_FILE_BYTES // 1024 // 1024} MB limit")

    fmt = detect_format(file.filename or "data", file.content_type or "")

    charged = await consume_credits(
        _uid(user), "ai_statistical_review",
        metadata={"filename": file.filename, "depth": depth.value},
    )
    credits_used = charged.get("consumed", _CREDIT_COSTS[depth])

    try:
        engine = await _get_engine()
        from services.statistical.models import StatisticalAnalysisRequest
        request = StatisticalAnalysisRequest(
            content=data,
            topic=topic,
            research_question=research_question,
            methodology=methodology,
            hypotheses=hypotheses,
            discipline=discipline,
            analysis_depth=depth,
            input_format=fmt,
            user_id=_uid(user),
            filename=file.filename or "data",
            target_journal=target_journal,
        )
        result = await engine.analyse(request)
        result.credits_used = credits_used
    except Exception as exc:
        await refund_credits(_uid(user), "ai_statistical_review", reason=str(exc)[:200])
        log.error("Statistical intelligence upload failed: %s", exc)
        raise HTTPException(503, "Analysis failed. Credits refunded.")

    return result.to_dict()


@router.post("/analyse/text")
async def analyse_text(
    body: TextAnalysisRequest,
    user=Depends(require_feature("ai_statistical_review")),
):
    """Analyse statistical results from raw text — the most common input method."""
    try:
        depth = AnalysisDepth(body.analysis_depth)
    except ValueError:
        raise HTTPException(422, f"Invalid analysis_depth: {body.analysis_depth}")

    fmt_map = {
        "text": InputFormat.TEXT, "csv": InputFormat.CSV,
        "json": InputFormat.JSON, "markdown": InputFormat.TEXT,
    }
    fmt = fmt_map.get(body.input_format.lower(), InputFormat.TEXT)

    charged = await consume_credits(
        _uid(user), "ai_statistical_review",
        metadata={"topic": body.topic[:100], "depth": depth.value},
    )
    credits_used = charged.get("consumed", _CREDIT_COSTS[depth])

    try:
        engine = await _get_engine()
        from services.statistical.models import StatisticalAnalysisRequest
        request = StatisticalAnalysisRequest(
            content=body.content,
            topic=body.topic,
            research_question=body.research_question,
            methodology=body.methodology,
            hypotheses=body.hypotheses,
            discipline=body.discipline,
            analysis_depth=depth,
            input_format=fmt,
            user_id=_uid(user),
            target_journal=body.target_journal,
        )
        result = await engine.analyse(request)
        result.credits_used = credits_used
    except Exception as exc:
        await refund_credits(_uid(user), "ai_statistical_review", reason=str(exc)[:200])
        log.error("Statistical intelligence text analysis failed: %s", exc)
        raise HTTPException(503, "Analysis failed. Credits refunded.")

    return result.to_dict()


@router.post("/analyse/quick")
async def analyse_quick(
    body: TextAnalysisRequest,
    user=Depends(require_feature("ai_statistical_review")),
):
    """Quick 10-credit analysis — fast statistical assessment."""
    body.analysis_depth = "quick"
    return await analyse_text(body, user)


@router.get("/history")
async def list_analyses(
    limit: int = Query(default=20, ge=1, le=100),
    user=Depends(get_current_user),
):
    engine = await _get_engine()
    return await engine.list_results(_uid(user), limit=limit)


@router.get("/{result_id}")
async def get_analysis(result_id: str, user=Depends(get_current_user)):
    engine = await _get_engine()
    result = await engine.get_result(result_id, _uid(user))
    if not result:
        raise HTTPException(404, "Analysis not found")
    return result.to_dict()


@router.get("/{result_id}/summary")
async def get_analysis_summary(result_id: str, user=Depends(get_current_user)):
    engine = await _get_engine()
    result = await engine.get_result(result_id, _uid(user))
    if not result:
        raise HTTPException(404, "Analysis not found")
    return result.to_summary()


@router.get("/{result_id}/export/{fmt}")
async def export_analysis(result_id: str, fmt: str, user=Depends(get_current_user)):
    """Export analysis in the specified format (8 formats supported)."""
    try:
        export_fmt = ExportFormat(fmt.lower())
    except ValueError:
        raise HTTPException(
            422, f"Unknown format: {fmt}. Supported: {[f.value for f in ExportFormat]}"
        )
    engine = await _get_engine()
    content, filename, ct = await engine.export(result_id, _uid(user), export_fmt)
    if not content:
        raise HTTPException(404, "Analysis not found")
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
        raise HTTPException(404, "Analysis not found")
    return result.visualizations


@router.get("/{result_id}/issues")
async def get_issues(result_id: str, user=Depends(get_current_user)):
    """Retrieve all detected statistical issues grouped by severity."""
    engine = await _get_engine()
    result = await engine.get_result(result_id, _uid(user))
    if not result:
        raise HTTPException(404, "Analysis not found")
    return {
        "critical":  [i.to_dict() for i in result.critical_issues],
        "major":     [i.to_dict() for i in result.major_issues],
        "moderate":  [i.to_dict() for i in result.moderate_issues],
        "minor":     [i.to_dict() for i in result.minor_issues],
    }


@router.get("/{result_id}/assumptions")
async def get_assumptions(result_id: str, user=Depends(get_current_user)):
    engine = await _get_engine()
    result = await engine.get_result(result_id, _uid(user))
    if not result:
        raise HTTPException(404, "Analysis not found")
    return {
        "assumption_checks": [a.to_dict() for a in result.assumption_checks],
        "method_evaluations": [m.to_dict() for m in result.method_evaluations],
    }


@router.get("/{result_id}/recommendations")
async def get_recommendations(result_id: str, user=Depends(get_current_user)):
    engine = await _get_engine()
    result = await engine.get_result(result_id, _uid(user))
    if not result:
        raise HTTPException(404, "Analysis not found")
    return {
        "recommended_analyses": [r.to_dict() for r in result.recommended_analyses],
        "reviewer_criticisms":  [c.to_dict() for c in result.reviewer_criticisms],
    }


@router.get("/{result_id}/design")
async def get_research_design(result_id: str, user=Depends(get_current_user)):
    engine = await _get_engine()
    result = await engine.get_result(result_id, _uid(user))
    if not result:
        raise HTTPException(404, "Analysis not found")
    return {
        "research_design":   result.research_design.to_dict(),
        "sampling_analysis": result.sampling_analysis.to_dict(),
        "data_quality":      result.data_quality.to_dict(),
        "validity_analysis": result.validity_analysis.to_dict(),
    }


@router.get("/meta/analysis-depths")
async def list_analysis_depths(_=Depends(get_current_user)):
    return {
        "depths": [
            {
                "value": d.value,
                "credits": _CREDIT_COSTS[d],
                "description": {
                    "quick":    "Fast statistical scan — 10 credits",
                    "standard": "Full rule-based + AI advisory — 20 credits (recommended)",
                    "deep":     "Comprehensive pipeline with data analysis — 35 credits",
                }[d.value],
            }
            for d in AnalysisDepth
        ]
    }


@router.get("/meta/export-formats")
async def list_export_formats(_=Depends(get_current_user)):
    return {"formats": [f.value for f in ExportFormat]}


@router.get("/meta/supported-inputs")
async def list_supported_inputs(_=Depends(get_current_user)):
    return {
        "formats": [f.value for f in InputFormat],
        "description": {
            "text":      "Statistical output paste, research description, SPSS/R/Stata output",
            "csv":       "CSV/TSV dataset files",
            "excel":     "Excel workbooks (.xlsx, .xls)",
            "json":      "JSON data arrays or objects",
            "spss":      "SPSS .sav files",
            "stata":     "Stata .dta files",
            "r_dataset": "R .rda/.rds files",
        },
    }


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


@admin_router.get("/capabilities")
async def admin_capabilities(_=Depends(_require_admin)):
    return {
        "version": "2.0",
        "phase": "X",
        "analysis_depths": {d.value: _CREDIT_COSTS[d] for d in AnalysisDepth},
        "export_formats": [f.value for f in ExportFormat],
        "input_formats": [f.value for f in InputFormat],
        "visualization_types": [
            "statistical_quality_dashboard",
            "assumption_status_chart",
            "effect_size_summary",
            "data_quality_heatmap",
            "power_analysis_chart",
            "validity_matrix",
            "issue_breakdown",
            "publication_readiness_gauge",
            "revision_priority_chart",
        ],
        "backward_compatible_endpoints": [
            "/api/statistical-review",
            "/api/statistical-review/history",
            "/api/statistical-review/{id}",
        ],
        "new_collection": "statistical_intelligence_results",
        "legacy_collection": "statistical_reviews",
    }
