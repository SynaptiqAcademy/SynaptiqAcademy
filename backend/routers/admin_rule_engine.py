"""Admin analytics endpoint for the Rule Engine subsystem.

Exposes execution telemetry: requests served, AI calls saved, cost savings,
execution times, cache performance, top rules, and recent execution history.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from auth_utils import get_current_user
from db import get_db
from repo.shim import DBProxy
from repo.security_context import SecurityContext
from zt.deps import zt_check, zt_is_admin, zt_is_super_admin

router = APIRouter(prefix="/api/admin/rule-engine", tags=["admin", "rule-engine"])


def _require_admin(user: dict = Depends(get_current_user)) -> dict:
    zt_check(user, "admin", "admin")
    return user


@router.get("/stats")
async def get_rule_engine_stats(_: dict = Depends(_require_admin)) -> dict:
    """Return in-process rule engine execution statistics."""
    from services.rule_engine.telemetry import get_stats
    stats = get_stats()
    return {
        "status": "ok",
        "stats": stats,
    }


@router.get("/features")
async def list_rule_features(_: dict = Depends(_require_admin)) -> dict:
    """List all features handled by the rule engine with descriptions."""
    from services.rule_engine.engine import get_rule_engine
    from services.ai.engine.registry import get_feature_meta
    engine = get_rule_engine()
    features = []
    for fid in engine.supported_features():
        meta = get_feature_meta(fid)
        features.append({
            "feature_id": fid,
            "display_name": meta.display_name,
            "description": meta.description,
            "layer": meta.preferred_layer.value,
            "cost_per_request_usd": 0.0,
        })
    return {"count": len(features), "features": features}


@router.get("/analytics")
async def get_rule_engine_analytics(
    days: int = 30,
    _: dict = Depends(_require_admin),
) -> dict:
    """Return persisted execution analytics from MongoDB (last N days)."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    from services.rule_engine.telemetry import get_stats
    from services.rule_engine.statistics.stats_engine import StatsEngine
    from services.rule_engine.utils.date_utils import days_ago

    cutoff = days_ago(days)

    # Fetch rule engine executions from ai_requests collection (rule_engine provider)
    records = await db.ai_requests.find(
        {"provider": "rule_engine", "created_at": {"$gte": cutoff.isoformat()}}
    ).sort("created_at", -1).limit(1000).to_list(1000)

    total_rule_requests = len(records)
    total_ai_requests = await db.ai_requests.count_documents(
        {"created_at": {"$gte": cutoff.isoformat()}}
    )
    cloud_requests = await db.ai_requests.count_documents({
        "created_at": {"$gte": cutoff.isoformat()},
        "layer": "cloud",
    })

    latencies = [r.get("duration_ms") or r.get("latency_ms") or 0 for r in records]
    features_used: dict[str, int] = {}
    for r in records:
        f = r.get("feature") or "unknown"
        features_used[f] = features_used.get(f, 0) + 1

    # Savings estimation
    avg_cloud_cost_usd = 0.0225  # per request
    estimated_savings = total_rule_requests * avg_cloud_cost_usd

    return {
        "period_days": days,
        "summary": {
            "total_requests": total_ai_requests,
            "rule_engine_requests": total_rule_requests,
            "cloud_ai_requests": cloud_requests,
            "rule_engine_pct": round(
                total_rule_requests / max(total_ai_requests, 1) * 100, 1
            ),
            "estimated_cost_saved_usd": round(estimated_savings, 4),
            "avg_execution_time_ms": round(
                StatsEngine.mean(latencies), 2
            ) if latencies else 0.0,
        },
        "top_features": sorted(
            [{"feature": k, "count": v} for k, v in features_used.items()],
            key=lambda x: -x["count"],
        )[:10],
        "in_process_stats": get_stats(),
    }


@router.post("/execute")
async def execute_rule(
    payload: dict,
    _: dict = Depends(_require_admin),
) -> dict:
    """Execute a rule engine feature directly (admin testing tool).

    Body: {"feature": "...", "data": {...}}
    """
    from services.rule_engine.engine import get_rule_engine
    feature = payload.get("feature")
    data = payload.get("data") or {}

    if not feature:
        raise HTTPException(status_code=422, detail="'feature' is required")

    engine = get_rule_engine()
    if not engine.can_handle(feature):
        raise HTTPException(
            status_code=404,
            detail=f"Unknown feature '{feature}'. Available: {engine.supported_features()}",
        )

    result = engine.execute(feature, data)
    return {"feature": feature, "result": result}


@router.get("/health")
async def rule_engine_health(_: dict = Depends(_require_admin)) -> dict:
    """Verify rule engine is importable and operational."""
    try:
        from services.rule_engine.engine import get_rule_engine
        engine = get_rule_engine()
        supported = engine.supported_features()
        # Quick smoke test
        test = engine.execute("statistics", {"values": [1, 2, 3], "operation": "mean"})
        return {
            "status": "ok",
            "features_count": len(supported),
            "smoke_test": test,
        }
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


@router.delete("/stats/reset")
async def reset_stats(_: dict = Depends(_require_admin)) -> dict:
    """Reset in-process telemetry counters."""
    from services.rule_engine.telemetry import reset_stats
    reset_stats()
    return {"status": "ok", "message": "Rule engine telemetry reset."}
