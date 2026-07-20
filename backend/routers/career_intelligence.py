"""Academic Career Intelligence Engine — API Router (Phase XVI)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from db import get_db
from repo.shim import make_db_proxy
from plans_catalogue import get_credit_cost
from services.career_intelligence import get_career_engine
from services.credits_service import consume_credits

router = APIRouter(
    prefix="/api/career-intelligence",
    tags=["career-intelligence"],
)

admin_router = APIRouter(
    prefix="/api/admin/career-intelligence",
    tags=["admin-career-intelligence"],
)


# ── Request models ────────────────────────────────────────────────────────────

class UserDataBody(BaseModel):
    user_data: dict = Field(default_factory=dict)


class RoadmapBody(BaseModel):
    user_data: dict = Field(default_factory=dict)
    horizon: str = "3_year"


class GoalBody(BaseModel):
    user_data: dict = Field(default_factory=dict)
    goals: list[dict] = Field(default_factory=list)


class PromotionBody(BaseModel):
    user_data: dict = Field(default_factory=dict)
    target: str = "associate_professor"


class VizBody(BaseModel):
    user_data: dict = Field(default_factory=dict)
    viz_type: str


class ExportBody(BaseModel):
    user_data: dict = Field(default_factory=dict)
    report_type: str = "career_report"
    export_format: str = "pdf"


# ── Helper ────────────────────────────────────────────────────────────────────

async def _user_data(current_user: dict) -> dict:
    """Load the requester's Mongo profile and merge with current_user."""
    uid  = str(current_user.get("_id") or current_user.get("id") or "")
    _db  = make_db_proxy(get_db(), current_user)
    doc  = await _db.users.find_one({"_id": current_user.get("_id")}) or {}
    merged = {**doc, **current_user}
    return merged


# ── User endpoints (12) ───────────────────────────────────────────────────────

@router.get("/profile")
async def career_profile(current_user: dict = Depends(get_current_user)):
    """Build and return the caller's career profile."""
    cost = get_credit_cost("career_profile", 5)
    await consume_credits(str(current_user.get("_id", "")), "career_profile")
    engine = await get_career_engine()
    data   = await _user_data(current_user)
    return engine.build_profile(data)


@router.post("/roadmap")
async def career_roadmap(body: RoadmapBody, current_user: dict = Depends(get_current_user)):
    """Generate a 1/3/5/10-year career roadmap."""
    await consume_credits(str(current_user.get("_id", "")), "career_roadmap")
    engine = await get_career_engine()
    data   = {**await _user_data(current_user), **body.user_data}
    return engine.build_roadmap(data, horizon=body.horizon)


@router.post("/goals")
async def career_goals(body: GoalBody, current_user: dict = Depends(get_current_user)):
    """Evaluate user goals or infer smart default goals."""
    await consume_credits(str(current_user.get("_id", "")), "career_goals")
    engine = await get_career_engine()
    data   = {**await _user_data(current_user), **body.user_data}
    return engine.evaluate_goals(data, goals=body.goals or None)


@router.get("/skill-gaps")
async def skill_gaps(current_user: dict = Depends(get_current_user)):
    """Assess 15 skill domains and identify gaps."""
    await consume_credits(str(current_user.get("_id", "")), "career_skill_gaps")
    engine = await get_career_engine()
    data   = await _user_data(current_user)
    return engine.analyse_skill_gaps(data)


@router.post("/promotion-readiness")
async def promotion_readiness(body: PromotionBody, current_user: dict = Depends(get_current_user)):
    """Assess promotion readiness for a target level."""
    await consume_credits(str(current_user.get("_id", "")), "career_promotion")
    engine = await get_career_engine()
    data   = {**await _user_data(current_user), **body.user_data}
    return engine.assess_promotion(data, target=body.target)


@router.get("/productivity")
async def productivity(current_user: dict = Depends(get_current_user)):
    """Detailed research productivity metrics."""
    await consume_credits(str(current_user.get("_id", "")), "career_productivity")
    engine = await get_career_engine()
    data   = await _user_data(current_user)
    return engine.analyse_productivity(data)


@router.get("/risks")
async def career_risks(current_user: dict = Depends(get_current_user)):
    """Detect career risk signals from the profile."""
    await consume_credits(str(current_user.get("_id", "")), "career_risks")
    engine = await get_career_engine()
    data   = await _user_data(current_user)
    return engine.detect_risks(data)


@router.get("/recommendations")
async def recommendations(current_user: dict = Depends(get_current_user)):
    """Personalized recommendations across 7 categories."""
    await consume_credits(str(current_user.get("_id", "")), "career_recommendations")
    engine = await get_career_engine()
    data   = await _user_data(current_user)
    return engine.generate_recommendations(data)


@router.get("/copilot-suggestions")
async def copilot_suggestions(current_user: dict = Depends(get_current_user)):
    """Academic Copilot integration suggestions."""
    await consume_credits(str(current_user.get("_id", "")), "career_copilot")
    engine = await get_career_engine()
    data   = await _user_data(current_user)
    return engine.copilot_suggestions(data)


@router.post("/visualization")
async def visualization(body: VizBody, current_user: dict = Depends(get_current_user)):
    """Generate a visualization data payload (one of 10 types)."""
    await consume_credits(str(current_user.get("_id", "")), "career_visualization")
    engine = await get_career_engine()
    data   = {**await _user_data(current_user), **body.user_data}
    return engine.visualization(data, viz_type=body.viz_type)


@router.post("/export")
async def export_report(body: ExportBody, current_user: dict = Depends(get_current_user)):
    """Export a career intelligence report (6 types × 3 formats)."""
    await consume_credits(str(current_user.get("_id", "")), "career_export")
    engine = await get_career_engine()
    data   = {**await _user_data(current_user), **body.user_data}
    return engine.export_report(data, report_type=body.report_type,
                                export_format=body.export_format)


@router.get("/full-analysis")
async def full_analysis(current_user: dict = Depends(get_current_user)):
    """Run all engines and return a comprehensive career intelligence report."""
    await consume_credits(str(current_user.get("_id", "")), "career_full_analysis")
    engine = await get_career_engine()
    data   = await _user_data(current_user)
    return engine.full_analysis(data)


# ── Admin endpoints (3) ────────────────────────────────────────────────────────

@router.get("/available-types")
async def available_types():
    """Public endpoint listing visualization and export options — no auth required."""
    return {
        "viz_types":      [v.value for v in __import__(
            "services.career_intelligence.models", fromlist=["VizType"]).VizType],
        "export_types":   [v.value for v in __import__(
            "services.career_intelligence.models", fromlist=["ExportReportType"]).ExportReportType],
        "export_formats": ["pdf", "docx", "markdown"],
        "horizons":       ["1_year", "3_year", "5_year", "10_year"],
        "promotion_targets": [v.value for v in __import__(
            "services.career_intelligence.models", fromlist=["PromotionTarget"]).PromotionTarget],
    }


@admin_router.get("/telemetry")
async def admin_telemetry(current_user: dict = Depends(get_current_user)):
    """Admin: engine telemetry and usage stats."""
    from services.career_intelligence.telemetry import get_telemetry
    return get_telemetry().to_dict()


@admin_router.post("/analytics")
async def admin_analytics(body: dict, current_user: dict = Depends(get_current_user)):
    """Admin: aggregate career intelligence across a list of user dicts."""
    engine = await get_career_engine()
    users  = body.get("users", [])
    if not isinstance(users, list):
        raise HTTPException(status_code=400, detail="'users' must be a list")
    return engine.admin_analytics(users)


@admin_router.post("/reset")
async def admin_reset(current_user: dict = Depends(get_current_user)):
    """Admin: reset the engine singleton (useful for hot-reload in dev)."""
    from services.career_intelligence.engine import reset_career_engine
    reset_career_engine()
    return {"status": "reset", "message": "Career engine singleton cleared."}
