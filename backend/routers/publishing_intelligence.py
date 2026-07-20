"""Academic Publishing Intelligence — Router (Phase XII).

User routes:   /api/publishing/*
Admin routes:  /api/admin/publishing/*
"""
from __future__ import annotations

import time
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from db import get_db
from plans_catalogue import get_credit_cost
from services.credits_service import consume_credits
from services.publishing import get_publishing_engine
from services.publishing.telemetry import get_telemetry
from repo.shim import make_db_proxy

router       = APIRouter(prefix="/api/publishing", tags=["publishing"])
admin_router = APIRouter(prefix="/api/admin/publishing", tags=["admin-publishing"])


# ── Pydantic request schemas ──────────────────────────────────────────────────

class JournalAnalyseRequest(BaseModel):
    text: str = Field(..., min_length=10)
    discipline: str = "general"
    manuscript_quality: float = Field(70.0, ge=0, le=100)


class JournalMatchRequest(BaseModel):
    text: str = Field(..., min_length=10)
    discipline: str = "general"
    manuscript_quality: float = Field(70.0, ge=0, le=100)
    match_types: Optional[list[str]] = None


class ConferenceMatchRequest(BaseModel):
    text: str = Field(..., min_length=10)
    discipline: str = "general"
    manuscript_quality: float = Field(70.0, ge=0, le=100)


class GrantMatchRequest(BaseModel):
    text: str = Field(..., min_length=10)
    discipline: str = "general"
    manuscript_quality: float = Field(70.0, ge=0, le=100)
    user_profile: Optional[dict] = None


class ReadinessRequest(BaseModel):
    text: str = Field(..., min_length=20)
    metadata: Optional[dict] = None


class CoverLetterRequest(BaseModel):
    manuscript_title: str = Field(..., min_length=3)
    journal: str = Field(..., min_length=3)
    metadata: Optional[dict] = None


class ReviewerResponseRequest(BaseModel):
    revision_type: str = "major_revision"
    manuscript_title: str = Field(..., min_length=3)
    journal: str = Field(..., min_length=3)
    reviewer_comments: list[dict] = Field(default_factory=list)
    metadata: Optional[dict] = None


class StrategyRequest(BaseModel):
    manuscript_title: str = Field(..., min_length=3)
    text: str = Field(..., min_length=20)
    discipline: str = "general"
    manuscript_quality: float = Field(70.0, ge=0, le=100)


class RiskRequest(BaseModel):
    text: str = Field(..., min_length=20)
    manuscript_quality: float = Field(70.0, ge=0, le=100)
    scope_match: float = Field(0.5, ge=0, le=1)
    journal_acceptance_rate: float = Field(0.25, ge=0, le=1)
    journal_review_weeks: int = Field(12, ge=1, le=104)
    journal_predatory_risk: float = Field(0.0, ge=0, le=1)
    metadata: Optional[dict] = None


class ExportRequest(BaseModel):
    export_type: str
    fmt: str = "markdown"
    payload: dict = Field(default_factory=dict)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _deduct(user: dict, key: str, db) -> None:
    await consume_credits(str(user.get("_id") or user.get("id", "")), key)


def _ok(data: Any) -> dict:
    return {"status": "success", "data": data}


# ── User endpoints ────────────────────────────────────────────────────────────

@router.post("/journal/analyse")
async def analyse_journal(
    body: JournalAnalyseRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Analyse journal fit for a manuscript (30+ factors)."""
    db = make_db_proxy(db, user)
    try:
        await _deduct(user, "publishing_journal_analyse", db)
        engine = await get_publishing_engine()
        result = await engine.analyse_journal(body.text, body.discipline, body.manuscript_quality)
        return _ok(result)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.post("/journal/match")
async def match_journals(
    body: JournalMatchRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Smart journal matching — 6 match strategies."""
    db = make_db_proxy(db, user)
    try:
        await _deduct(user, "publishing_journal_match", db)
        engine = await get_publishing_engine()
        result = await engine.match_journal(
            body.text, body.discipline, body.manuscript_quality, body.match_types
        )
        return _ok(result)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.get("/journal/{journal_id}/profile")
async def get_journal_profile(
    journal_id: str,
    user: dict = Depends(get_current_user),
):
    """Get a journal profile by name (URL-encoded)."""
    from services.publishing.journal_analyzer import get_all_profiles
    profiles = get_all_profiles()
    name_lower = journal_id.replace("-", " ").replace("%20", " ").lower()
    match = next((p for p in profiles if p.name.lower() == name_lower), None)
    if not match:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Journal '{journal_id}' not found.")
    return _ok(match.to_dict())


@router.post("/conference/match")
async def match_conferences(
    body: ConferenceMatchRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Match conferences by research area and manuscript quality."""
    db = make_db_proxy(db, user)
    try:
        await _deduct(user, "publishing_conference_match", db)
        engine = await get_publishing_engine()
        result = await engine.match_conference(body.text, body.discipline, body.manuscript_quality)
        return _ok(result)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.post("/grant/match")
async def match_grants(
    body: GrantMatchRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Match grants by topic and eligibility."""
    db = make_db_proxy(db, user)
    try:
        await _deduct(user, "publishing_grant_match", db)
        engine = await get_publishing_engine()
        result = await engine.match_grant(
            body.text, body.discipline, body.manuscript_quality, body.user_profile
        )
        return _ok(result)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.post("/submission/readiness")
async def check_submission_readiness(
    body: ReadinessRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Check submission readiness (15+ criteria)."""
    db = make_db_proxy(db, user)
    try:
        await _deduct(user, "publishing_readiness_check", db)
        engine = await get_publishing_engine()
        result = await engine.check_readiness(body.text, body.metadata)
        return _ok(result)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.post("/cover-letter")
async def generate_cover_letter(
    body: CoverLetterRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Generate a publication-ready cover letter."""
    db = make_db_proxy(db, user)
    try:
        await _deduct(user, "publishing_cover_letter", db)
        engine = await get_publishing_engine()
        result = await engine.generate_cover_letter(
            body.manuscript_title, body.journal, body.metadata
        )
        return _ok(result)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.post("/reviewer-response")
async def generate_reviewer_response(
    body: ReviewerResponseRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Generate a point-by-point reviewer response document."""
    db = make_db_proxy(db, user)
    try:
        await _deduct(user, "publishing_reviewer_response", db)
        engine = await get_publishing_engine()
        result = await engine.generate_reviewer_response(
            body.revision_type,
            body.manuscript_title,
            body.journal,
            body.reviewer_comments,
            body.metadata,
        )
        return _ok(result)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.post("/strategy")
async def build_strategy(
    body: StrategyRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Build a multi-option publication strategy."""
    db = make_db_proxy(db, user)
    try:
        await _deduct(user, "publishing_strategy", db)
        engine = await get_publishing_engine()
        result = await engine.build_strategy(
            body.manuscript_title, body.text, body.discipline, body.manuscript_quality
        )
        return _ok(result)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.post("/risk")
async def analyse_risk(
    body: RiskRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Analyse publication risk across 8 dimensions."""
    db = make_db_proxy(db, user)
    try:
        await _deduct(user, "publishing_risk_analysis", db)
        engine = await get_publishing_engine()
        result = await engine.analyse_risk(
            body.text,
            body.manuscript_quality,
            body.scope_match,
            body.journal_acceptance_rate,
            body.journal_review_weeks,
            body.journal_predatory_risk,
            body.metadata,
        )
        return _ok(result)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.get("/dashboard")
async def get_publishing_dashboard(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Get the personalised publishing intelligence dashboard."""
    db = make_db_proxy(db, user)
    try:
        await _deduct(user, "publishing_dashboard", db)
        engine = await get_publishing_engine()
        result = await engine.get_dashboard(str(user["_id"]), db)
        return _ok(result)
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.post("/export")
async def export_document(
    body: ExportRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Export a publishing document (cover letter, roadmap, comparison, etc.)."""
    db = make_db_proxy(db, user)
    try:
        await _deduct(user, "publishing_export", db)
        engine = await get_publishing_engine()
        result = await engine.export(body.export_type, body.fmt, body.payload)
        return _ok({"text": result, "export_type": body.export_type, "fmt": body.fmt})
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.get("/meta/match-types")
async def get_match_types():
    """List all available journal match types (no auth required)."""
    from services.publishing.models import MatchType
    return _ok([{"value": m.value, "label": m.value.replace("_", " ").title()} for m in MatchType])


@router.get("/meta/export-formats")
async def get_export_formats():
    """List all available export formats (no auth required)."""
    from services.publishing.models import ExportFormat
    return _ok([f.value for f in ExportFormat])


# ── Admin endpoints ───────────────────────────────────────────────────────────

@admin_router.get("/overview")
async def admin_overview(
    user: dict = Depends(get_current_user),
):
    snap = get_telemetry().snapshot()
    return {
        "status": "success",
        "total_operations": sum(v for k, v in snap.items() if isinstance(v, int) and k != "errors"),
        "errors": snap["errors"],
        "latency_avg_s": snap["latency_avg_s"],
        "breakdown": snap,
    }


@admin_router.get("/telemetry")
async def admin_telemetry(
    user: dict = Depends(get_current_user),
):
    return {"status": "success", "telemetry": get_telemetry().snapshot()}


@admin_router.post("/telemetry/reset")
async def reset_telemetry(
    user: dict = Depends(get_current_user),
):
    get_telemetry().reset()
    return {"status": "success", "message": "Publishing intelligence telemetry reset."}
