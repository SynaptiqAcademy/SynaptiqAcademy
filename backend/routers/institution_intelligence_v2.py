"""Institution Intelligence Engine — API router (Phase XV).

User endpoints: /api/institution-intelligence/*
Admin endpoints: /api/admin/institution-intelligence/*

Does NOT touch:
  /api/institution-analytics  (Phase XXVIII)
  /api/institution-hub        (Phase XXIV)
  /api/institutional/analytics (Phase XI)
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from services.credits_service import consume_credits
from services.institution_intelligence import (
    ExportFormat, ExportReportType, ForecastType, VizType,
    get_institution_engine, reset_institution_engine,
)
from services.institution_intelligence.telemetry import (
    InstitutionTelemetry, get_telemetry,
)

router = APIRouter(
    prefix="/api/institution-intelligence",
    tags=["institution-intelligence"],
)
admin_router = APIRouter(
    prefix="/api/admin/institution-intelligence",
    tags=["institution-intelligence-admin"],
)


# ── Pydantic models ───────────────────────────────────────────────────────────

class InstitutionDataBody(BaseModel):
    name: str                              = ""
    institution_type: str                  = "university"
    country: str                           = ""
    founding_year: int                     = 0
    researchers: list[dict[str, Any]]      = Field(default_factory=list)
    grants: list[dict[str, Any]]           = Field(default_factory=list)
    publications: list[dict[str, Any]]     = Field(default_factory=list)
    projects: list[dict[str, Any]]         = Field(default_factory=list)
    departments: list[str]                 = Field(default_factory=list)
    total_budget: float                    = 0.0
    total_students: int                    = 0
    metadata: dict[str, Any]              = Field(default_factory=dict)

    def to_dict(self) -> dict:
        return self.model_dump()


class PredictBody(InstitutionDataBody):
    horizon: int = 3


class RecommendationsBody(InstitutionDataBody):
    audiences: list[str] = Field(default_factory=list)


class VizBody(InstitutionDataBody):
    viz_type: str = "institution_knowledge_graph"


class ExportBody(InstitutionDataBody):
    report_type: str  = "executive"
    export_format: str = "pdf"


class KnowledgeGraphBody(InstitutionDataBody):
    max_nodes: int = 200


# ── Credit helper ──────────────────────────────────────────────────────────────

async def _deduct(user: dict, key: str) -> None:
    uid = str(user.get("_id") or user.get("id", ""))
    await consume_credits(uid, key)


# ── User endpoints ────────────────────────────────────────────────────────────

@router.post("/profile")
async def build_profile(
    body: InstitutionDataBody,
    user: dict = Depends(get_current_user),
):
    """Build a comprehensive institution profile from researcher and grant data."""
    await _deduct(user, "institution_profile")
    engine = await get_institution_engine()
    try:
        return {"status": "ok", "profile": engine.build_profile(body.to_dict())}
    except Exception as exc:
        get_telemetry().record_error()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc)) from exc


@router.post("/kpis")
async def compute_kpis(
    body: InstitutionDataBody,
    user: dict = Depends(get_current_user),
):
    """Compute all 20 institutional KPIs."""
    await _deduct(user, "institution_kpis")
    engine = await get_institution_engine()
    try:
        return {"status": "ok", "kpis": engine.compute_kpis(body.to_dict())}
    except Exception as exc:
        get_telemetry().record_error()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc)) from exc


@router.post("/organizational")
async def organizational_intelligence(
    body: InstitutionDataBody,
    user: dict = Depends(get_current_user),
):
    """Detect organizational insights: underperforming departments, emerging groups, bottlenecks."""
    await _deduct(user, "institution_organizational")
    engine = await get_institution_engine()
    try:
        return {"status": "ok", **engine.organizational_intelligence(body.to_dict())}
    except Exception as exc:
        get_telemetry().record_error()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc)) from exc


@router.post("/predict")
async def predict(
    body: PredictBody,
    user: dict = Depends(get_current_user),
):
    """Generate multi-year institutional forecasts (publications, citations, grants, etc.)."""
    await _deduct(user, "institution_predict")
    engine = await get_institution_engine()
    try:
        return {"status": "ok", **engine.predict(body.to_dict(), horizon=body.horizon)}
    except Exception as exc:
        get_telemetry().record_error()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc)) from exc


@router.post("/resources")
async def optimise_resources(
    body: InstitutionDataBody,
    user: dict = Depends(get_current_user),
):
    """Generate resource allocation recommendations (grants, labs, staffing, partnerships)."""
    await _deduct(user, "institution_resources")
    engine = await get_institution_engine()
    try:
        return {"status": "ok", **engine.optimise_resources(body.to_dict())}
    except Exception as exc:
        get_telemetry().record_error()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc)) from exc


@router.post("/talent")
async def talent_intelligence(
    body: InstitutionDataBody,
    user: dict = Depends(get_current_user),
):
    """Identify future leaders, high-potential researchers, retention risks, succession candidates."""
    await _deduct(user, "institution_talent")
    engine = await get_institution_engine()
    try:
        return {"status": "ok", "talent": engine.talent_intelligence(body.to_dict())}
    except Exception as exc:
        get_telemetry().record_error()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc)) from exc


@router.post("/portfolio")
async def analyse_portfolio(
    body: InstitutionDataBody,
    user: dict = Depends(get_current_user),
):
    """Evaluate research portfolio: balance, maturity, diversity, strategic alignment."""
    await _deduct(user, "institution_portfolio")
    engine = await get_institution_engine()
    try:
        return {"status": "ok", **engine.analyse_portfolio(body.to_dict())}
    except Exception as exc:
        get_telemetry().record_error()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc)) from exc


@router.post("/benchmark")
async def benchmark_institution(
    body: InstitutionDataBody,
    user: dict = Depends(get_current_user),
):
    """Benchmark institution KPIs against synthetic peer institutions."""
    await _deduct(user, "institution_benchmark")
    engine = await get_institution_engine()
    try:
        return {"status": "ok", **engine.benchmark_institution(body.to_dict())}
    except Exception as exc:
        get_telemetry().record_error()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc)) from exc


@router.post("/risks")
async def detect_risks(
    body: InstitutionDataBody,
    user: dict = Depends(get_current_user),
):
    """Identify strategic risks (grant dependency, isolation, funding instability, etc.)."""
    await _deduct(user, "institution_risks")
    engine = await get_institution_engine()
    try:
        return {"status": "ok", **engine.detect_risks(body.to_dict())}
    except Exception as exc:
        get_telemetry().record_error()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc)) from exc


@router.post("/recommendations")
async def recommendations(
    body: RecommendationsBody,
    user: dict = Depends(get_current_user),
):
    """Generate evidence-based executive recommendations for rectors, deans, grant offices, etc."""
    await _deduct(user, "institution_recommendations")
    engine = await get_institution_engine()
    try:
        return {
            "status": "ok",
            **engine.recommendations(body.to_dict(), audiences=body.audiences or None),
        }
    except Exception as exc:
        get_telemetry().record_error()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc)) from exc


@router.post("/monitor")
async def monitor(
    body: InstitutionDataBody,
    user: dict = Depends(get_current_user),
):
    """Run autonomous monitoring — generate threshold-based alerts for KPI deviations."""
    await _deduct(user, "institution_monitor")
    engine = await get_institution_engine()
    try:
        return {"status": "ok", **engine.monitor(body.to_dict())}
    except Exception as exc:
        get_telemetry().record_error()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc)) from exc


@router.post("/knowledge-graph")
async def knowledge_graph(
    body: KnowledgeGraphBody,
    user: dict = Depends(get_current_user),
):
    """Build institution knowledge graph (researchers, departments, grants, topics, funders)."""
    await _deduct(user, "institution_knowledge_graph")
    engine = await get_institution_engine()
    try:
        return {
            "status": "ok",
            "graph": engine.knowledge_graph(body.to_dict(), max_nodes=body.max_nodes),
        }
    except Exception as exc:
        get_telemetry().record_error()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc)) from exc


@router.post("/visualizations")
async def visualizations(
    body: VizBody,
    user: dict = Depends(get_current_user),
):
    """Generate executive dashboard visualization data (12 viz types)."""
    await _deduct(user, "institution_visualization")
    engine = await get_institution_engine()
    try:
        return {
            "status": "ok",
            "visualization": engine.visualization(body.viz_type, body.to_dict()),
        }
    except Exception as exc:
        get_telemetry().record_error()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc)) from exc


@router.post("/export")
async def export_report(
    body: ExportBody,
    user: dict = Depends(get_current_user),
):
    """Generate an institutional report (executive/accreditation/strategy/grant/dept/benchmark) in PDF/DOCX/EXCEL/PPTX."""
    await _deduct(user, "institution_export")
    engine = await get_institution_engine()
    try:
        return {
            "status": "ok",
            "export": engine.export_report(
                body.to_dict(),
                report_type=body.report_type,
                export_format=body.export_format,
            ),
        }
    except Exception as exc:
        get_telemetry().record_error()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc)) from exc


@router.post("/full-analysis")
async def full_analysis(
    body: InstitutionDataBody,
    user: dict = Depends(get_current_user),
):
    """Run all engines in one call — comprehensive institutional intelligence report."""
    await _deduct(user, "institution_full_analysis")
    engine = await get_institution_engine()
    try:
        return {"status": "ok", **engine.full_analysis(body.to_dict())}
    except Exception as exc:
        get_telemetry().record_error()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc)) from exc


# ── Admin endpoints ────────────────────────────────────────────────────────────

@admin_router.post("/analytics")
async def admin_analytics(
    body: dict,
    user: dict = Depends(get_current_user),
):
    """Platform-level analytics across multiple institutions."""
    engine = await get_institution_engine()
    institutions = body.get("institutions") or []
    try:
        return {"status": "ok", "analytics": engine.admin_analytics(institutions)}
    except Exception as exc:
        get_telemetry().record_error()
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(exc)) from exc


@admin_router.get("/telemetry")
async def telemetry(user: dict = Depends(get_current_user)):
    """Get engine telemetry metrics."""
    return {"status": "ok", "telemetry": get_telemetry().snapshot()}


@admin_router.post("/telemetry/reset")
async def reset_telemetry(user: dict = Depends(get_current_user)):
    """Reset engine telemetry counters."""
    get_telemetry().reset()
    reset_institution_engine()
    return {"status": "ok", "message": "Telemetry reset"}
