"""Academic Prediction & Forecasting Intelligence Engine — Router (Phase XVIII).

User endpoints:  /api/prediction-intelligence/*
Admin endpoints: /api/admin/prediction-intelligence/*
Public:          /api/prediction-intelligence/available-types
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from auth_utils import get_current_user
from services.credits_service import consume_credits
from plans_catalogue import get_credit_cost
from services.prediction_intelligence import get_prediction_engine
from services.prediction_intelligence.models import (
    ForecastHorizon, PredictionType, ScenarioType, VizType, WhatIfFactor,
)

router       = APIRouter(prefix="/api/prediction-intelligence",       tags=["Prediction Intelligence"])
admin_router = APIRouter(prefix="/api/admin/prediction-intelligence", tags=["Admin: Prediction Intelligence"])


# ── Request models ────────────────────────────────────────────────────────────

class ManuscriptRequest(BaseModel):
    manuscript: dict


class JournalRankingRequest(BaseModel):
    manuscript:  dict
    max_results: int = 8


class ConferenceRequest(BaseModel):
    profile: dict


class GrantRequest(BaseModel):
    grant: dict


class CareerForecastRequest(BaseModel):
    profile: dict
    horizon: str = "3y"


class CollaborationRequest(BaseModel):
    profile: dict


class InstitutionRequest(BaseModel):
    profile: dict
    horizon: str = "3y"


class TrendRequest(BaseModel):
    profile: dict | None = None
    top_k:   int = 8


class StrategicRequest(BaseModel):
    question: str
    profile:  dict


class ScenarioRequest(BaseModel):
    manuscript:     dict
    scenario_types: list[str] | None = None


class WhatIfRequest(BaseModel):
    manuscript: dict
    factor:     str


class VizRequest(BaseModel):
    viz_type: str
    data:     dict


class CopilotForecastRequest(BaseModel):
    workflow: str
    profile:  dict


class CopilotEnrichRequest(BaseModel):
    prompt:  str
    profile: dict


# ── Public ────────────────────────────────────────────────────────────────────

@router.get("/available-types")
async def available_types():
    return {
        "prediction_types":  [e.value for e in PredictionType],
        "forecast_horizons": [e.value for e in ForecastHorizon],
        "scenario_types":    [e.value for e in ScenarioType],
        "what_if_factors":   [e.value for e in WhatIfFactor],
        "viz_types":         [e.value for e in VizType],
    }


# ── Publication ───────────────────────────────────────────────────────────────

@router.post("/publication")
async def predict_publication(
    body: ManuscriptRequest,
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "prediction_publication")
    engine = await get_prediction_engine()
    return engine.predict_publication(body.manuscript)


# ── Journal ───────────────────────────────────────────────────────────────────

@router.post("/journal-ranking")
async def journal_ranking(
    body: JournalRankingRequest,
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "prediction_journal_ranking")
    engine = await get_prediction_engine()
    return engine.predict_journals(body.manuscript, body.max_results)


# ── Conference ────────────────────────────────────────────────────────────────

@router.post("/conference")
async def conference_prediction(
    body: ConferenceRequest,
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "prediction_conference")
    engine = await get_prediction_engine()
    return {"conferences": engine.predict_conference(body.profile)}


# ── Grant ─────────────────────────────────────────────────────────────────────

@router.post("/grant")
async def grant_prediction(
    body: GrantRequest,
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "prediction_grant")
    engine = await get_prediction_engine()
    return engine.predict_grant(body.grant)


# ── Career ────────────────────────────────────────────────────────────────────

@router.post("/career-forecast")
async def career_forecast(
    body: CareerForecastRequest,
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "prediction_career_forecast")
    engine = await get_prediction_engine()
    return engine.forecast_career(body.profile, body.horizon)


# ── Collaboration ─────────────────────────────────────────────────────────────

@router.post("/collaboration-forecast")
async def collaboration_forecast(
    body: CollaborationRequest,
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "prediction_collaboration")
    engine = await get_prediction_engine()
    return engine.forecast_collaboration(body.profile)


# ── Institution ───────────────────────────────────────────────────────────────

@router.post("/institution-forecast")
async def institution_forecast(
    body: InstitutionRequest,
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "prediction_institution")
    engine = await get_prediction_engine()
    return engine.forecast_institution(body.profile, body.horizon)


# ── Trend ─────────────────────────────────────────────────────────────────────

@router.post("/trend-forecast")
async def trend_forecast(
    body: TrendRequest,
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "prediction_trend")
    engine = await get_prediction_engine()
    return engine.forecast_trends(body.profile, body.top_k)


# ── Strategic decision ────────────────────────────────────────────────────────

@router.post("/strategic-decision")
async def strategic_decision(
    body: StrategicRequest,
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "prediction_strategic")
    engine = await get_prediction_engine()
    return engine.strategic_decision(body.question, body.profile)


# ── Scenario simulation ───────────────────────────────────────────────────────

@router.post("/scenario-simulation")
async def scenario_simulation(
    body: ScenarioRequest,
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "prediction_scenario")
    engine = await get_prediction_engine()
    return engine.simulate_scenarios(body.manuscript, body.scenario_types)


# ── What-if ───────────────────────────────────────────────────────────────────

@router.post("/what-if")
async def what_if(
    body: WhatIfRequest,
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "prediction_what_if")
    engine = await get_prediction_engine()
    return engine.what_if(body.manuscript, body.factor)


# ── Visualization ─────────────────────────────────────────────────────────────

@router.post("/visualization")
async def visualization(
    body: VizRequest,
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "prediction_visualization")
    engine = await get_prediction_engine()
    return engine.visualize(body.viz_type, body.data)


# ── Copilot ───────────────────────────────────────────────────────────────────

@router.post("/copilot-forecast")
async def copilot_forecast(
    body: CopilotForecastRequest,
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "prediction_copilot")
    engine = await get_prediction_engine()
    return {"suggestions": engine.copilot_forecasts(body.workflow, body.profile)}


@router.post("/copilot-enrich")
async def copilot_enrich(
    body: CopilotEnrichRequest,
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "prediction_copilot")
    engine = await get_prediction_engine()
    return {"enriched_prompt": engine.copilot_enrich_prompt(body.prompt, body.profile)}


# ── Admin ─────────────────────────────────────────────────────────────────────

@admin_router.get("/telemetry")
async def admin_telemetry(current_user: dict = Depends(get_current_user)):
    from services.prediction_intelligence.telemetry import get_telemetry
    return get_telemetry().to_dict()


@admin_router.get("/analytics")
async def admin_analytics(current_user: dict = Depends(get_current_user)):
    engine = await get_prediction_engine()
    return engine.admin_analytics()


@admin_router.post("/reset")
async def admin_reset(current_user: dict = Depends(get_current_user)):
    from services.prediction_intelligence.engine import reset_prediction_engine
    reset_prediction_engine()
    return {"status": "reset", "message": "Prediction engine singleton reset."}
