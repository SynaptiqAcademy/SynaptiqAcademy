"""Research Collaboration Intelligence Engine — Router (Phase XIV).

Separate from existing /api/collaboration-intelligence/ (Phase XI LLM matchmaking).
New prefix: /api/collab-intelligence/

User routes:   /api/collab-intelligence/*
Admin routes:  /api/admin/collab-intelligence/*
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from db import get_db
from services.credits_service import consume_credits
from services.collab_intelligence import get_collab_engine
from services.collab_intelligence.telemetry import get_telemetry
from repo.shim import make_db_proxy

router       = APIRouter(prefix="/api/collab-intelligence", tags=["collab-intelligence"])
admin_router = APIRouter(prefix="/api/admin/collab-intelligence", tags=["admin-collab-intelligence"])


# ── Request schemas ───────────────────────────────────────────────────────────

class ProfileBuildRequest(BaseModel):
    user_doc: dict = Field(..., description="MongoDB user document")


class MatchRequest(BaseModel):
    user_a: dict
    user_b: dict


class RankCandidatesRequest(BaseModel):
    source_user: dict
    candidate_users: list[dict] = Field(..., min_items=1)
    top_n: int = Field(default=10, ge=1, le=50)


class OpportunitiesRequest(BaseModel):
    source_user: dict
    candidate_users: list[dict] = Field(..., min_items=1)
    top_n: int = Field(default=10, ge=1, le=50)


class TeamBuildRequest(BaseModel):
    candidate_users: list[dict] = Field(..., min_items=2)
    objective: str = Field(..., min_length=5)
    team_type: str = "interdisciplinary"
    required_concepts: Optional[list[str]] = None
    max_size: Optional[int] = Field(None, ge=2, le=15)


class TeamSimulateRequest(BaseModel):
    team_users: list[dict] = Field(..., min_items=2)
    objective: str = Field(..., min_length=5)


class IntroduceRequest(BaseModel):
    user_a: dict
    user_b: dict


class NetworkAnalysisRequest(BaseModel):
    user_docs: list[dict] = Field(..., min_items=2)
    similarity_threshold: float = Field(default=0.35, ge=0.1, le=0.9)


class PredictRequest(BaseModel):
    user_a: dict
    user_b: dict


class RecommendationsRequest(BaseModel):
    source_user: dict
    candidate_users: list[dict] = Field(..., min_items=1)
    include_types: Optional[list[str]] = None
    top_n: int = Field(default=10, ge=1, le=50)


class InsightsRequest(BaseModel):
    source_user: dict
    all_users: Optional[list[dict]] = None


class SocialGraphRequest(BaseModel):
    user_docs: list[dict] = Field(..., min_items=1)
    include_topics: bool = True
    include_methods: bool = True
    include_institutions: bool = True


class VizRequest(BaseModel):
    viz_type: str
    user_docs: list[dict] = Field(..., min_items=1)
    source_user: Optional[dict] = None


class AdminAnalyticsRequest(BaseModel):
    user_docs: list[dict] = Field(..., min_items=1)


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _deduct(user: dict, action: str) -> None:
    await consume_credits(str(user.get("_id") or user.get("id", "")), action)


def _ok(data) -> dict:
    return {"status": "success", "data": data}


# ── User endpoints ────────────────────────────────────────────────────────────

@router.post("/profile/build")
async def build_profile(
    body: ProfileBuildRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Build a comprehensive researcher profile from a user document."""
    db = make_db_proxy(db, user)
    try:
        engine = await get_collab_engine()
        return _ok(engine.profile_to_dict(body.user_doc))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.post("/match")
async def match_researchers(
    body: MatchRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Calculate multi-dimensional compatibility between two researchers."""
    db = make_db_proxy(db, user)
    try:
        await _deduct(user, "collab_match")
        engine = await get_collab_engine()
        return _ok(engine.match(body.user_a, body.user_b))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.post("/match/rank")
async def rank_candidates(
    body: RankCandidatesRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Rank a pool of candidates by compatibility with a source researcher."""
    db = make_db_proxy(db, user)
    try:
        await _deduct(user, "collab_rank")
        engine = await get_collab_engine()
        return _ok(engine.rank_candidates(body.source_user, body.candidate_users, body.top_n))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.post("/opportunities")
async def find_opportunities(
    body: OpportunitiesRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Detect collaboration opportunities for a researcher across a candidate pool."""
    db = make_db_proxy(db, user)
    try:
        await _deduct(user, "collab_opportunities")
        engine = await get_collab_engine()
        return _ok(engine.find_opportunities(body.source_user, body.candidate_users, body.top_n))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.post("/team/build")
async def build_team(
    body: TeamBuildRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Build an optimal research team for a given objective."""
    db = make_db_proxy(db, user)
    try:
        await _deduct(user, "collab_team_build")
        engine = await get_collab_engine()
        return _ok(engine.build_team(
            body.candidate_users, body.objective,
            body.team_type, body.required_concepts, body.max_size,
        ))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.post("/team/simulate")
async def simulate_team(
    body: TeamSimulateRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Simulate expected outputs for a given team composition."""
    db = make_db_proxy(db, user)
    try:
        await _deduct(user, "collab_team_simulate")
        engine = await get_collab_engine()
        return _ok(engine.simulate_team(body.team_users, body.objective))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.post("/introduce")
async def generate_introduction(
    body: IntroduceRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Generate a smart introduction narrative for two researchers."""
    db = make_db_proxy(db, user)
    try:
        await _deduct(user, "collab_introduction")
        engine = await get_collab_engine()
        return _ok(engine.introduce(body.user_a, body.user_b))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.post("/network/analyze")
async def analyze_network(
    body: NetworkAnalysisRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Analyze the collaboration network for a set of researchers."""
    db = make_db_proxy(db, user)
    try:
        await _deduct(user, "collab_network")
        engine = await get_collab_engine()
        return _ok(engine.analyze_network(body.user_docs, body.similarity_threshold))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.post("/predict")
async def predict_collaboration(
    body: PredictRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Predict collaboration success, publication, and grant probabilities."""
    db = make_db_proxy(db, user)
    try:
        await _deduct(user, "collab_prediction")
        engine = await get_collab_engine()
        return _ok(engine.predict(body.user_a, body.user_b))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.post("/recommendations")
async def get_recommendations(
    body: RecommendationsRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Get ranked researcher, institution, and country recommendations."""
    db = make_db_proxy(db, user)
    try:
        await _deduct(user, "collab_recommendations")
        engine = await get_collab_engine()
        return _ok(engine.recommendations(
            body.source_user, body.candidate_users, body.include_types, body.top_n
        ))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.post("/insights")
async def get_insights(
    body: InsightsRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Generate personalized collaboration insights for a researcher."""
    db = make_db_proxy(db, user)
    try:
        engine = await get_collab_engine()
        return _ok(engine.insights(body.source_user, body.all_users))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.post("/social-graph")
async def build_social_graph(
    body: SocialGraphRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Build an academic social graph connecting researchers, institutions, and topics."""
    db = make_db_proxy(db, user)
    try:
        await _deduct(user, "collab_social_graph")
        engine = await get_collab_engine()
        return _ok(engine.social_graph(
            body.user_docs, body.include_topics, body.include_methods, body.include_institutions
        ))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.post("/visualizations")
async def get_visualization(
    body: VizRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Get structured visualization data for charts and graphs."""
    db = make_db_proxy(db, user)
    try:
        engine = await get_collab_engine()
        return _ok(engine.visualization(body.viz_type, body.user_docs, body.source_user))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


# ── Admin endpoints ───────────────────────────────────────────────────────────

@admin_router.post("/analytics")
async def admin_analytics(
    body: AdminAnalyticsRequest,
    user: dict = Depends(get_current_user),
):
    """Full platform analytics: top collaborators, communities, international stats."""
    try:
        engine = await get_collab_engine()
        return _ok(engine.admin_analytics(body.user_docs))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@admin_router.get("/telemetry")
async def admin_telemetry(user: dict = Depends(get_current_user)):
    return {"status": "success", "telemetry": get_telemetry().snapshot()}


@admin_router.post("/telemetry/reset")
async def reset_telemetry(user: dict = Depends(get_current_user)):
    get_telemetry().reset()
    return {"status": "success", "message": "Collaboration Intelligence telemetry reset."}
