"""Self-Improving Academic Intelligence Platform — Router (Phase XX).

User:  /api/self-improvement/*
Admin: /api/admin/self-improvement/*
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth_utils import get_current_user
from services.credits_service import consume_credits
from services.self_improvement import get_self_improvement_engine

router       = APIRouter(prefix="/api/self-improvement",       tags=["Self-Improvement"])
admin_router = APIRouter(prefix="/api/admin/self-improvement", tags=["Admin: Self-Improvement"])


# ── Request models ────────────────────────────────────────────────────────────

class FeedbackRequest(BaseModel):
    signal_type:           str
    engine_type:           str
    outcome:               str   = ""
    recommendation_status: str   = "pending"
    quality_delta:         float = 0.0
    confidence:            float = 0.0
    user_cohort:           str   = "general"
    metadata:              dict  = {}


class PersonalizeRequest(BaseModel):
    recommendations: list[dict]
    cohort_id:       str
    category_key:    str = "category"
    score_key:       str = "score"


class CohortFeedbackRequest(BaseModel):
    cohort_id: str
    category:  str
    accepted:  bool


class CopilotRequest(BaseModel):
    workflow:        str
    max_suggestions: int = 5


class CopilotEnrichRequest(BaseModel):
    prompt: str


class IngestTextRequest(BaseModel):
    text:   str
    source: str = "user"


class ExperimentCreateRequest(BaseModel):
    name:          str
    engine_type:   str
    variant_a:     dict
    variant_b:     dict
    description:   str   = ""
    traffic_split: float = 0.5


class ObservationRequest(BaseModel):
    variant: str
    success: bool


class PolicyUpdateRequest(BaseModel):
    updates:    dict
    updated_by: str = "admin"


class OptimizationApplyRequest(BaseModel):
    approved_by: str = "admin"


# ─── User endpoints ───────────────────────────────────────────────────────────

@router.post("/feedback")
async def record_feedback(
    body: FeedbackRequest,
    current_user: dict = Depends(get_current_user),
):
    engine = await get_self_improvement_engine()
    return engine.record_feedback(
        signal_type=body.signal_type,
        engine_type=body.engine_type,
        outcome=body.outcome,
        recommendation_status=body.recommendation_status,
        quality_delta=body.quality_delta,
        confidence=body.confidence,
        user_cohort=body.user_cohort,
        metadata=body.metadata,
    )


@router.get("/feedback-summary")
async def feedback_summary(current_user: dict = Depends(get_current_user)):
    engine = await get_self_improvement_engine()
    return engine.get_feedback_summary()


@router.get("/performance")
async def all_performance(current_user: dict = Depends(get_current_user)):
    await consume_credits(current_user["_id"], "si_query")
    engine = await get_self_improvement_engine()
    return engine.get_all_performance()


@router.get("/performance/{engine_type}")
async def engine_performance(
    engine_type:  str,
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "si_query")
    engine = await get_self_improvement_engine()
    return engine.get_performance(engine_type)


@router.get("/diagnostics")
async def all_diagnostics(current_user: dict = Depends(get_current_user)):
    await consume_credits(current_user["_id"], "si_diagnostics")
    engine = await get_self_improvement_engine()
    return {"diagnostics": engine.run_diagnostics()}


@router.get("/diagnostics/{engine_type}")
async def engine_diagnostic(
    engine_type:  str,
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "si_diagnostics")
    engine = await get_self_improvement_engine()
    return engine.run_engine_diagnostic(engine_type)


@router.get("/platform-quality")
async def platform_quality(current_user: dict = Depends(get_current_user)):
    await consume_credits(current_user["_id"], "si_query")
    engine = await get_self_improvement_engine()
    return engine.get_platform_quality()


@router.get("/knowledge-updates")
async def knowledge_updates(
    min_confidence: float = 0.0,
    current_user:   dict  = Depends(get_current_user),
):
    engine = await get_self_improvement_engine()
    return {"updates": engine.get_pending_knowledge_updates(min_confidence)}


@router.get("/policy")
async def get_policy_endpoint(current_user: dict = Depends(get_current_user)):
    engine = await get_self_improvement_engine()
    return engine.get_policy()


@router.post("/personalize")
async def personalize(
    body:         PersonalizeRequest,
    current_user: dict = Depends(get_current_user),
):
    engine = await get_self_improvement_engine()
    return {"recommendations": engine.personalize(
        body.recommendations, body.cohort_id, body.category_key, body.score_key
    )}


@router.post("/cohort-feedback")
async def cohort_feedback(
    body:         CohortFeedbackRequest,
    current_user: dict = Depends(get_current_user),
):
    engine = await get_self_improvement_engine()
    engine.record_cohort_feedback(body.cohort_id, body.category, body.accepted)
    return {"status": "recorded"}


@router.get("/cohort/{cohort_id}")
async def cohort_profile(
    cohort_id:    str,
    current_user: dict = Depends(get_current_user),
):
    engine = await get_self_improvement_engine()
    return engine.get_cohort_profile(cohort_id)


@router.post("/copilot")
async def copilot(
    body:         CopilotRequest,
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "si_copilot")
    engine = await get_self_improvement_engine()
    return {"suggestions": engine.copilot_suggestions(body.workflow, body.max_suggestions)}


@router.post("/copilot-enrich")
async def copilot_enrich(
    body:         CopilotEnrichRequest,
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "si_copilot")
    engine = await get_self_improvement_engine()
    return {"enriched_prompt": engine.copilot_enrich_prompt(body.prompt)}


# ─── Admin endpoints ──────────────────────────────────────────────────────────

@admin_router.get("/telemetry")
async def admin_telemetry(current_user: dict = Depends(get_current_user)):
    engine = await get_self_improvement_engine()
    return engine.get_telemetry()


@admin_router.get("/audit-log")
async def admin_audit_log(
    limit:        int  = 100,
    current_user: dict = Depends(get_current_user),
):
    engine = await get_self_improvement_engine()
    return {"entries": engine.get_audit_log(limit=limit)}


@admin_router.get("/audit-log/{engine_type}")
async def admin_engine_audit_log(
    engine_type:  str,
    limit:        int  = 50,
    current_user: dict = Depends(get_current_user),
):
    engine = await get_self_improvement_engine()
    return {"entries": engine.get_audit_log(engine_type=engine_type, limit=limit)}


@admin_router.get("/benchmarks")
async def admin_all_benchmarks(current_user: dict = Depends(get_current_user)):
    await consume_credits(current_user["_id"], "si_benchmark")
    engine = await get_self_improvement_engine()
    return engine.run_all_benchmarks()


@admin_router.get("/benchmarks/{engine_type}")
async def admin_engine_benchmark(
    engine_type:  str,
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "si_benchmark")
    engine = await get_self_improvement_engine()
    return engine.run_benchmark(engine_type)


@admin_router.get("/optimizations")
async def admin_optimization_history(
    engine_type:  str  = None,
    limit:        int  = 50,
    current_user: dict = Depends(get_current_user),
):
    engine = await get_self_improvement_engine()
    return {"history": engine.get_optimization_history(engine_type, limit)}


@admin_router.get("/optimizations/pending")
async def admin_pending_optimizations(current_user: dict = Depends(get_current_user)):
    engine = await get_self_improvement_engine()
    return {"pending": engine.get_pending_optimizations()}


@admin_router.post("/optimizations/generate")
async def admin_generate_optimizations(current_user: dict = Depends(get_current_user)):
    await consume_credits(current_user["_id"], "si_optimize")
    engine = await get_self_improvement_engine()
    return {"candidates": engine.generate_optimizations()}


@admin_router.post("/optimizations/{record_id}/apply")
async def admin_apply_optimization(
    record_id:    str,
    body:         OptimizationApplyRequest,
    current_user: dict = Depends(get_current_user),
):
    engine = await get_self_improvement_engine()
    return {"applied": engine.apply_optimization(record_id, body.approved_by)}


@admin_router.post("/optimizations/{record_id}/rollback")
async def admin_rollback_optimization(
    record_id:    str,
    current_user: dict = Depends(get_current_user),
):
    engine = await get_self_improvement_engine()
    return {"rolled_back": engine.rollback_optimization(record_id)}


@admin_router.put("/policy")
async def admin_update_policy(
    body:         PolicyUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    engine = await get_self_improvement_engine()
    return engine.update_policy(body.updates, body.updated_by)


@admin_router.post("/experiments")
async def admin_create_experiment(
    body:         ExperimentCreateRequest,
    current_user: dict = Depends(get_current_user),
):
    await consume_credits(current_user["_id"], "si_experiment")
    engine = await get_self_improvement_engine()
    return engine.create_experiment(
        body.name, body.engine_type, body.variant_a, body.variant_b,
        body.description, body.traffic_split,
    )


@admin_router.get("/experiments")
async def admin_all_experiments(current_user: dict = Depends(get_current_user)):
    engine = await get_self_improvement_engine()
    return {"experiments": engine.get_all_experiments()}


@admin_router.get("/experiments/active")
async def admin_active_experiments(current_user: dict = Depends(get_current_user)):
    engine = await get_self_improvement_engine()
    return {"experiments": engine.get_active_experiments()}


@admin_router.post("/experiments/{experiment_id}/observe")
async def admin_observe_experiment(
    experiment_id: str,
    body:          ObservationRequest,
    current_user:  dict = Depends(get_current_user),
):
    engine = await get_self_improvement_engine()
    return {"recorded": engine.record_experiment_observation(experiment_id, body.variant, body.success)}


@admin_router.get("/experiments/{experiment_id}/evaluate")
async def admin_evaluate_experiment(
    experiment_id: str,
    current_user:  dict = Depends(get_current_user),
):
    engine = await get_self_improvement_engine()
    return engine.evaluate_experiment(experiment_id) or {"error": "experiment_not_found"}


@admin_router.post("/experiments/{experiment_id}/complete")
async def admin_complete_experiment(
    experiment_id: str,
    current_user:  dict = Depends(get_current_user),
):
    engine = await get_self_improvement_engine()
    return {"completed": engine.complete_experiment(experiment_id)}


@admin_router.post("/experiments/{experiment_id}/deploy")
async def admin_deploy_experiment(
    experiment_id: str,
    current_user:  dict = Depends(get_current_user),
):
    engine = await get_self_improvement_engine()
    return engine.deploy_experiment_winner(experiment_id)


@admin_router.post("/experiments/{experiment_id}/rollback")
async def admin_rollback_experiment(
    experiment_id: str,
    current_user:  dict = Depends(get_current_user),
):
    engine = await get_self_improvement_engine()
    return {"rolled_back": engine.rollback_experiment(experiment_id)}


@admin_router.post("/knowledge/ingest")
async def admin_ingest_knowledge(
    body:         IngestTextRequest,
    current_user: dict = Depends(get_current_user),
):
    engine = await get_self_improvement_engine()
    return {"detected": engine.ingest_text(body.text, body.source)}


@admin_router.get("/knowledge/summary")
async def admin_knowledge_summary(current_user: dict = Depends(get_current_user)):
    engine = await get_self_improvement_engine()
    return engine.knowledge_summary()


@admin_router.post("/knowledge-updates/{update_id}/validate")
async def admin_validate_update(
    update_id:    str,
    current_user: dict = Depends(get_current_user),
):
    engine = await get_self_improvement_engine()
    result = engine.validate_knowledge_update(update_id)
    return result or {"error": "update_not_found"}


@admin_router.post("/knowledge-updates/{update_id}/integrate")
async def admin_integrate_update(
    update_id:    str,
    current_user: dict = Depends(get_current_user),
):
    engine = await get_self_improvement_engine()
    return {"integrated": engine.integrate_knowledge_update(update_id)}


@admin_router.post("/knowledge-updates/{update_id}/reject")
async def admin_reject_update(
    update_id:    str,
    current_user: dict = Depends(get_current_user),
):
    engine = await get_self_improvement_engine()
    return {"rejected": engine.reject_knowledge_update(update_id)}
