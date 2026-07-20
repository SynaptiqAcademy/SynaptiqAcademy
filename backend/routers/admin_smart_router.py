"""Admin Smart Router Dashboard — 14 endpoints for full visibility and control."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from db import get_db
from zt.deps import zt_check, zt_is_admin, zt_is_super_admin

router = APIRouter(prefix="/api/admin/smart-router", tags=["admin-smart-router"])


async def _require_admin(current_user=Depends(get_current_user)):
    zt_check(current_user, "admin", "admin")
    return current_user


async def _get_router():
    from services.smart_router.engine import get_smart_router_async
    return await get_smart_router_async()


# ── 1. Dashboard overview ──────────────────────────────────────────────────────

@router.get("/overview")
async def get_overview(_=Depends(_require_admin)):
    """Complete smart router status: telemetry, cache, load, budget."""
    sr = await _get_router()
    telem = sr.get_telemetry()
    cache = sr.get_cache_stats()
    load = sr.get_load_summary()
    budget = await sr.get_budget_summary()
    return {
        "telemetry": telem,
        "cache": cache,
        "load": load,
        "budget": budget,
    }


# ── 2. Routing telemetry ───────────────────────────────────────────────────────

@router.get("/telemetry")
async def get_telemetry(_=Depends(_require_admin)):
    sr = await _get_router()
    return sr.get_telemetry()


# ── 3. Cache stats and control ─────────────────────────────────────────────────

@router.get("/cache")
async def get_cache_stats(_=Depends(_require_admin)):
    sr = await _get_router()
    return sr.get_cache_stats()


class CacheClearRequest(BaseModel):
    level: str = Field(default="all", pattern="^(all|decisions|outputs|templates)$")


@router.post("/cache/clear")
async def clear_cache(body: CacheClearRequest, _=Depends(_require_admin)):
    sr = await _get_router()
    sr.clear_cache(body.level)
    return {"ok": True, "cleared": body.level}


# ── 4. Provider load ───────────────────────────────────────────────────────────

@router.get("/load")
async def get_provider_load(_=Depends(_require_admin)):
    sr = await _get_router()
    return sr.get_load_summary()


# ── 5. Budget ─────────────────────────────────────────────────────────────────

@router.get("/budget")
async def get_budget(_=Depends(_require_admin)):
    sr = await _get_router()
    return await sr.get_budget_summary()


@router.get("/budget/history")
async def get_budget_history(
    days: int = Query(default=7, ge=1, le=90),
    _=Depends(_require_admin),
):
    sr = await _get_router()
    return await sr.get_budget_history(days=days)


# ── 6. Audit log ──────────────────────────────────────────────────────────────

@router.get("/audit")
async def get_audit_log(
    limit: int = Query(default=100, ge=1, le=500),
    feature: Optional[str] = Query(default=None),
    _=Depends(_require_admin),
):
    sr = await _get_router()
    return await sr.get_audit_log(limit=limit, feature=feature)


# ── 7. Complexity explainer ────────────────────────────────────────────────────

class ComplexityRequest(BaseModel):
    feature: str
    messages: list[dict]
    system_prompt: str = ""


@router.post("/explain-complexity")
async def explain_complexity(body: ComplexityRequest, _=Depends(_require_admin)):
    sr = await _get_router()
    return sr.explain_complexity(body.feature, body.messages, body.system_prompt)


# ── 8. Load simulation ────────────────────────────────────────────────────────

class SimulationRequest(BaseModel):
    concurrent_users: int = Field(ge=1, le=1_000_000)
    duration_minutes: int = Field(default=60, ge=1, le=1440)


@router.post("/simulate")
async def simulate_load(body: SimulationRequest, _=Depends(_require_admin)):
    sr = await _get_router()
    result = sr.simulate(body.concurrent_users, body.duration_minutes)
    return {
        "n_users": result.n_users,
        "duration_minutes": result.duration_minutes,
        "estimated_requests": result.estimated_requests,
        "layer_distribution": result.layer_distribution,
        "estimated_cloud_cost_usd": result.estimated_cloud_cost_usd,
        "estimated_savings_vs_cloud_usd": result.estimated_savings_vs_cloud_usd,
        "estimated_gpu_hours": result.estimated_gpu_hours,
        "estimated_local_requests": result.estimated_local_requests,
        "estimated_rule_requests": result.estimated_rule_requests,
        "p50_latency_ms": result.p50_latency_ms,
        "p95_latency_ms": result.p95_latency_ms,
        "p99_latency_ms": result.p99_latency_ms,
        "recommended_gpu_count": result.recommended_gpu_count,
        "recommended_local_model_replicas": result.recommended_local_model_replicas,
        "cost_breakdown": result.cost_breakdown,
        "warnings": result.warnings,
    }


@router.get("/simulate/compare")
async def simulate_compare(
    users: str = Query(description="Comma-separated user counts e.g. 100,1000,10000"),
    _=Depends(_require_admin),
):
    try:
        counts = [int(x.strip()) for x in users.split(",") if x.strip()]
        counts = [max(1, min(1_000_000, c)) for c in counts[:10]]  # cap at 10
    except ValueError:
        raise HTTPException(status_code=400, detail="users must be comma-separated integers")
    sr = await _get_router()
    return sr.compare_scales(counts)


# ── 9. Feature profiles ────────────────────────────────────────────────────────

@router.get("/profiles")
async def list_profiles(_=Depends(_require_admin)):
    from services.smart_router.profiles import list_profiles
    profiles = list_profiles()
    return [
        {
            "feature_id": p.feature_id,
            "base_complexity": p.base_complexity.name,
            "priority_score": p.priority_score,
            "cacheable": p.cacheable,
            "min_subscription_tier": p.min_subscription_tier,
            "allow_local_downgrade": p.allow_local_downgrade,
            "allow_rule_downgrade": p.allow_rule_downgrade,
            "typical_context_tokens": p.typical_context_tokens,
            "expected_output_tokens": p.expected_output_tokens,
        }
        for p in profiles
    ]


@router.get("/profiles/{feature_id}")
async def get_feature_profile(feature_id: str, _=Depends(_require_admin)):
    from services.smart_router.profiles import get_profile
    p = get_profile(feature_id)
    return {
        "feature_id": p.feature_id,
        "base_complexity": p.base_complexity.name,
        "priority_score": p.priority_score,
        "cacheable": p.cacheable,
        "min_subscription_tier": p.min_subscription_tier,
        "allow_local_downgrade": p.allow_local_downgrade,
        "allow_rule_downgrade": p.allow_rule_downgrade,
        "typical_context_tokens": p.typical_context_tokens,
        "expected_output_tokens": p.expected_output_tokens,
    }


# ── 10. Telemetry reset ────────────────────────────────────────────────────────

@router.post("/telemetry/reset")
async def reset_telemetry(_=Depends(_require_admin)):
    sr = await _get_router()
    sr.reset_telemetry()
    return {"ok": True}


# ── 11. Config inspection ──────────────────────────────────────────────────────

@router.get("/config")
async def get_config(_=Depends(_require_admin)):
    from services.smart_router.config import load_router_config
    cfg = load_router_config()
    return {
        "enabled": cfg.enabled,
        "preferred_cloud_provider": cfg.preferred_cloud_provider,
        "cloud_provider_fallbacks": cfg.cloud_provider_fallbacks,
        "daily_budget_usd": cfg.daily_budget_usd,
        "weekly_budget_usd": cfg.weekly_budget_usd,
        "monthly_budget_usd": cfg.monthly_budget_usd,
        "budget_alert_pct": cfg.budget_alert_pct,
        "budget_throttle_pct": cfg.budget_throttle_pct,
        "budget_reject_pct": cfg.budget_reject_pct,
        "large_context_threshold": cfg.large_context_threshold,
        "very_large_context_threshold": cfg.very_large_context_threshold,
        "max_concurrent_per_provider": cfg.max_concurrent_per_provider,
        "audit_enabled": cfg.audit_enabled,
    }


# ── 12. Routing accuracy ───────────────────────────────────────────────────────

@router.get("/routing-accuracy")
async def get_routing_accuracy(_=Depends(_require_admin)):
    from services.smart_router.telemetry import get_router_telemetry
    return get_router_telemetry().get_routing_accuracy()
