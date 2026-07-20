"""Academic Intelligence Router — admin dashboard + user-facing academic API."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from zt.deps import zt_check, zt_is_admin, zt_is_super_admin

router = APIRouter(prefix="/api/academic", tags=["academic-intelligence"])
admin_router = APIRouter(prefix="/api/admin/academic-intelligence", tags=["admin-academic"])


# ── Auth helpers ───────────────────────────────────────────────────────────────

async def _require_admin(current_user=Depends(get_current_user)):
    zt_check(user, "admin", "admin")
    return current_user


async def _get_engine():
    from services.academic.engine import get_academic_engine
    return await get_academic_engine()


# ═════════════════════════════════════════════════════════════════════════════
# USER-FACING ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════

# ── 1. Get academic profile ────────────────────────────────────────────────────

@router.get("/profile")
async def get_academic_profile(current_user=Depends(get_current_user)):
    """Return the user's academic intelligence profile."""
    engine = await _get_engine()
    user_id = str(current_user.get("_id", current_user.get("id", "")))
    profile = await engine._memory.get_user_profile(user_id)
    return profile.to_dict()


# ── 2. Get academic memory ─────────────────────────────────────────────────────

@router.get("/memory")
async def get_academic_memory(current_user=Depends(get_current_user)):
    """Return the user's academic memory (recent interactions + profile)."""
    engine = await _get_engine()
    user_id = str(current_user.get("_id", current_user.get("id", "")))
    return await engine.get_user_memory(user_id)


# ── 3. Clear academic memory ───────────────────────────────────────────────────

@router.delete("/memory")
async def clear_academic_memory(current_user=Depends(get_current_user)):
    """Clear the user's academic memory."""
    engine = await _get_engine()
    user_id = str(current_user.get("_id", current_user.get("id", "")))
    deleted = await engine.clear_user_memory(user_id)
    return {"ok": True, "deleted_records": deleted}


# ── 4. Strategic recommendations ──────────────────────────────────────────────

@router.get("/strategy")
async def get_strategy(current_user=Depends(get_current_user)):
    """Return personalized academic strategic recommendations."""
    engine = await _get_engine()
    user_id = str(current_user.get("_id", current_user.get("id", "")))
    return await engine.get_strategy(user_id)


# ── 5. Analyze a text ─────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=10, max_length=50_000)
    feature: str = Field(default="manuscript_review")


@router.post("/analyze")
async def analyze_text(body: AnalyzeRequest, current_user=Depends(get_current_user)):
    """Run a full academic intelligence analysis on provided text."""
    engine = await _get_engine()
    user_id = str(current_user.get("_id", current_user.get("id", "")))
    analysis = await engine.analyze(
        text=body.text,
        feature=body.feature,
        user_id=user_id,
    )
    return analysis.to_dict()


# ═════════════════════════════════════════════════════════════════════════════
# ADMIN ENDPOINTS
# ═════════════════════════════════════════════════════════════════════════════

# ── 1. Overview ───────────────────────────────────────────────────────────────

@admin_router.get("/overview")
async def get_overview(_=Depends(_require_admin)):
    """Complete Academic Intelligence Engine stats."""
    engine = await _get_engine()
    telemetry = engine.get_telemetry_stats()
    memory = await engine.get_memory_stats()
    graph = await engine.get_graph_stats()
    return {
        "telemetry": telemetry,
        "memory": memory,
        "knowledge_graph": graph,
    }


# ── 2. Telemetry ─────────────────────────────────────────────────────────────

@admin_router.get("/telemetry")
async def get_telemetry(_=Depends(_require_admin)):
    engine = await _get_engine()
    return engine.get_telemetry_stats()


# ── 3. Quality scores ─────────────────────────────────────────────────────────

@admin_router.get("/quality-scores")
async def get_quality_scores(_=Depends(_require_admin)):
    """Quality score distribution across all academic features."""
    engine = await _get_engine()
    stats = engine.get_telemetry_stats()
    return {
        "avg_quality_score": stats.get("avg_quality_score", 0.0),
        "quality_improvement_rate_pct": stats.get("quality_improvement_rate_pct", 0.0),
        "quality_checks": stats.get("quality_checks", 0),
    }


# ── 4. Reasoning / weakness stats ────────────────────────────────────────────

@admin_router.get("/reasoning")
async def get_reasoning_stats(_=Depends(_require_admin)):
    engine = await _get_engine()
    stats = engine.get_telemetry_stats()
    return {
        "total_weaknesses_detected": stats.get("total_weaknesses_detected", 0),
        "avg_weaknesses_per_request": stats.get("avg_weaknesses_per_request", 0),
        "most_common_weaknesses": stats.get("most_common_weaknesses", {}),
    }


# ── 5. Memory stats ───────────────────────────────────────────────────────────

@admin_router.get("/memory/stats")
async def get_memory_stats(_=Depends(_require_admin)):
    engine = await _get_engine()
    return await engine.get_memory_stats()


# ── 6. Knowledge graph stats ──────────────────────────────────────────────────

@admin_router.get("/graph/stats")
async def get_graph_stats(_=Depends(_require_admin)):
    engine = await _get_engine()
    return await engine.get_graph_stats()


# ── 7. Domain distribution ────────────────────────────────────────────────────

@admin_router.get("/domains")
async def get_domain_distribution(_=Depends(_require_admin)):
    engine = await _get_engine()
    stats = engine.get_telemetry_stats()
    return {
        "domain_distribution": stats.get("top_domains", {}),
        "top_features": stats.get("top_features", []),
    }


# ── 8. Most common weaknesses ────────────────────────────────────────────────

@admin_router.get("/weaknesses")
async def get_weakness_stats(_=Depends(_require_admin)):
    engine = await _get_engine()
    stats = engine.get_telemetry_stats()
    return {
        "most_common_weaknesses": stats.get("most_common_weaknesses", {}),
        "total_weaknesses_detected": stats.get("total_weaknesses_detected", 0),
    }


# ── 9. Confidence distribution ───────────────────────────────────────────────

@admin_router.get("/confidence")
async def get_confidence_stats(_=Depends(_require_admin)):
    engine = await _get_engine()
    stats = engine.get_telemetry_stats()
    return {
        "avg_confidence_score": stats.get("avg_confidence_score", 0.0),
        "total_enriched_requests": stats.get("enriched_requests", 0),
    }


# ── 10. Validation stats ─────────────────────────────────────────────────────

@admin_router.get("/validation")
async def get_validation_stats(_=Depends(_require_admin)):
    engine = await _get_engine()
    stats = engine.get_telemetry_stats()
    return {
        "validation_passes": stats.get("validation_passes", 0),
        "validation_failures": stats.get("validation_failures", 0),
        "validation_pass_rate_pct": stats.get("validation_pass_rate_pct", 0.0),
    }


# ── 11. Admin analyze ────────────────────────────────────────────────────────

class AdminAnalyzeRequest(BaseModel):
    text: str = Field(min_length=10, max_length=50_000)
    feature: str = Field(default="manuscript_review")
    user_id: str = Field(default="")


@admin_router.post("/analyze")
async def admin_analyze(body: AdminAnalyzeRequest, _=Depends(_require_admin)):
    """Admin: run full academic analysis on any text."""
    engine = await _get_engine()
    analysis = await engine.analyze(
        text=body.text,
        feature=body.feature,
        user_id=body.user_id,
    )
    return analysis.to_dict()


# ── 12. Reset telemetry ──────────────────────────────────────────────────────

@admin_router.post("/telemetry/reset")
async def reset_telemetry(_=Depends(_require_admin)):
    engine = await _get_engine()
    engine.reset_telemetry()
    return {"ok": True}


# ── 13. Ontology / feature list ──────────────────────────────────────────────

@admin_router.get("/features")
async def get_academic_features(_=Depends(_require_admin)):
    """Return all features managed by the Academic Intelligence Engine."""
    from services.academic.ontology import ACADEMIC_FEATURES, FEATURE_QUALITY_THRESHOLDS, FEATURE_REASONING_FRAMEWORKS
    return {
        "academic_features": sorted(list(ACADEMIC_FEATURES)),
        "quality_thresholds": FEATURE_QUALITY_THRESHOLDS,
        "reasoning_frameworks": {k: v[:120] + "..." for k, v in FEATURE_REASONING_FRAMEWORKS.items()},
    }
