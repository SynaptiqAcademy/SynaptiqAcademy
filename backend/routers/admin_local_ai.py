"""Admin Local AI Dashboard — provider management, model control, telemetry, health."""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth_utils import get_current_user

logger = logging.getLogger("synaptiq.routers.admin_local_ai")

router = APIRouter(prefix="/api/admin/local-ai", tags=["admin", "local-ai"])


def _require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    role = current_user.get("role", "")
    if role not in ("admin", "super_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def _get_engine():
    from services.local_ai.engine import get_local_engine
    return get_local_engine()


# ── Status overview ──────────────────────────────────────────────────────────

@router.get("/status")
async def get_status(_: dict = Depends(_require_admin)):
    """Provider availability, model count, telemetry summary."""
    try:
        engine = _get_engine()
        health = await engine.health()
        telemetry = engine.telemetry()
        return {
            "status": "operational",
            "providers": health["providers"],
            "models": health["models"],
            "cache": health["cache"],
            "telemetry": {
                "total_requests": telemetry["total_requests"],
                "requests_served_locally": telemetry["requests_served_locally"],
                "fallback_to_cloud_count": telemetry["fallback_to_cloud_count"],
                "cache_hit_rate_pct": telemetry["cache_hit_rate_pct"],
                "avg_latency_ms": telemetry["avg_latency_ms"],
                "estimated_cost_saved_usd": telemetry["estimated_cost_saved_usd"],
            },
        }
    except Exception as exc:
        logger.error("admin_local_ai status error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


# ── Models ──────────────────────────────────────────────────────────────────

@router.get("/models")
async def list_models(_: dict = Depends(_require_admin)):
    """All discovered models with metadata and admin enable/disable state."""
    try:
        engine = _get_engine()
        models = await engine.list_models()
        return {
            "total": len(models),
            "models": [m.to_dict() for m in models],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/models/{model_key:path}/enable")
async def enable_model(model_key: str, _: dict = Depends(_require_admin)):
    """Enable a model by its registry key (provider::model_id)."""
    engine = _get_engine()
    ok = engine.enable_model(model_key)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Model '{model_key}' not found in registry")
    return {"model_key": model_key, "enabled": True}


@router.put("/models/{model_key:path}/disable")
async def disable_model(model_key: str, _: dict = Depends(_require_admin)):
    """Disable a model — it will be skipped by the router until re-enabled."""
    engine = _get_engine()
    ok = engine.disable_model(model_key)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Model '{model_key}' not found in registry")
    return {"model_key": model_key, "enabled": False}


@router.post("/models/refresh")
async def refresh_models(_: dict = Depends(_require_admin)):
    """Re-discover models from all reachable providers."""
    engine = _get_engine()
    count = await engine.refresh_models()
    return {"discovered": count, "message": f"Found {count} models across all providers"}


# ── Health ──────────────────────────────────────────────────────────────────

@router.get("/health")
async def get_health(_: dict = Depends(_require_admin)):
    """Full system health: provider status + RAM/GPU/CPU."""
    try:
        engine = _get_engine()
        health = await engine.health()
        return health
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── Telemetry ────────────────────────────────────────────────────────────────

@router.get("/telemetry")
async def get_telemetry(_: dict = Depends(_require_admin)):
    """Full telemetry: requests, latency, cache, fallbacks, cost saved, history."""
    engine = _get_engine()
    return engine.telemetry()


@router.delete("/telemetry/reset")
async def reset_telemetry(_: dict = Depends(_require_admin)):
    """Reset all in-process telemetry counters."""
    from services.local_ai.telemetry import reset_telemetry as _reset
    _reset()
    return {"reset": True, "message": "Local AI telemetry counters cleared"}


# ── Cache ────────────────────────────────────────────────────────────────────

@router.get("/cache")
async def get_cache_stats(_: dict = Depends(_require_admin)):
    """Response cache statistics."""
    engine = _get_engine()
    return engine.cache_stats()


@router.delete("/cache")
async def clear_cache(_: dict = Depends(_require_admin)):
    """Clear all cached responses."""
    engine = _get_engine()
    cleared = engine.clear_cache()
    return {"cleared": cleared, "message": f"Cleared {cleared} cached responses"}


# ── Configuration ────────────────────────────────────────────────────────────

@router.get("/config")
async def get_config(_: dict = Depends(_require_admin)):
    """Current Local AI configuration (no secrets)."""
    from services.local_ai.config import load_local_config
    cfg = load_local_config()
    return {
        "default_provider": cfg.default_provider,
        "preferred_model": cfg.preferred_model,
        "ollama_url": cfg.ollama_base_url,
        "vllm_url": cfg.vllm_base_url,
        "lm_studio_url": cfg.lm_studio_base_url,
        "openai_compatible_url": cfg.openai_compatible_base_url,
        "max_context_tokens": cfg.max_context_tokens,
        "max_output_tokens": cfg.max_output_tokens,
        "timeout_seconds": cfg.timeout_seconds,
        "temperature": cfg.temperature,
        "max_parallel_requests": cfg.max_parallel_requests,
        "max_retries": cfg.max_retries,
        "cache_ttl_seconds": cfg.cache_ttl_seconds,
        "cache_max_size": cfg.cache_max_size,
        "enable_streaming": cfg.enable_streaming,
        "auto_discover": cfg.auto_discover,
    }


# ── Test endpoint ────────────────────────────────────────────────────────────

class TestRequest(BaseModel):
    feature: str = "summarization"
    text: str = "Test the local AI engine."
    model: str | None = None
    max_tokens: int = 256


@router.post("/test")
async def test_generation(
    body: TestRequest,
    _: dict = Depends(_require_admin),
):
    """Directly invoke local AI for a test prompt and return the result."""
    from services.local_ai.engine import LocalGenerateRequest, get_local_engine
    from services.local_ai.utils.prompt_optimizer import build_academic_system_prompt

    engine = get_local_engine()
    req = LocalGenerateRequest(
        system=build_academic_system_prompt(body.feature),
        messages=[{"role": "user", "content": body.text}],
        feature=body.feature,
        max_tokens=body.max_tokens,
        model=body.model,
    )
    result = await engine.generate(req)
    return {
        "text": result.text,
        "provider": result.provider,
        "model": result.model,
        "feature": result.feature,
        "latency_ms": result.latency_ms,
        "from_cache": result.from_cache,
        "input_tokens": result.input_tokens,
        "output_tokens": result.output_tokens,
        "error": result.error,
    }


# ── Feature registry ─────────────────────────────────────────────────────────

@router.get("/features")
async def list_local_features(_: dict = Depends(_require_admin)):
    """List all features registered as LOCAL-layer in the AI engine registry."""
    from services.ai.engine.registry import list_features
    from services.ai.engine.types import ExecutionLayer
    local_features = [
        {
            "feature_id": f.feature_id,
            "display_name": f.display_name,
            "description": f.description,
            "max_tokens": f.max_tokens,
            "priority": f.priority,
            "cost_sensitivity": f.cost_sensitivity,
        }
        for f in list_features()
        if f.preferred_layer == ExecutionLayer.LOCAL
    ]
    return {"count": len(local_features), "features": local_features}
