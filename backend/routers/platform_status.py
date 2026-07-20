"""Public Platform Status — enterprise-grade health and status reporting.

GET /api/status          — machine-readable platform status (for status pages, uptime robots)
GET /api/status/history  — recent incidents / degradation events (last 30 days)

Enterprise customers and monitoring systems poll this endpoint to determine:
  - Overall platform health (operational / degraded / outage)
  - Per-component status (API, AI, billing, database, storage, email)
  - Scheduled maintenance windows
  - Recent incident history

No authentication required — status pages must be publicly accessible.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from db import get_db
from repo.shim import DBProxy
from repo.security_context import SecurityContext
from services.permissions import require_super_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/status", tags=["platform-status"])

_VERSION = os.environ.get("APP_VERSION", "1.0.0")
_PLATFORM_NAME = "Synaptiq"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ago(days: int = 0, hours: int = 0, minutes: int = 0) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days, hours=hours, minutes=minutes)


async def _check_mongodb() -> dict:
    try:
        db = get_db()
        await db.users.find_one({}, {"_id": 1})
        return {"status": "operational", "latency_ms": None}
    except Exception as e:
        return {"status": "outage", "error": str(e)[:100]}


async def _check_redis() -> dict:
    try:
        from services.redis_client import get_redis
        r = await get_redis()
        if r:
            await r.ping()
            return {"status": "operational"}
        return {"status": "degraded", "note": "Redis not configured"}
    except Exception as e:
        return {"status": "degraded", "error": str(e)[:100]}


def _check_ai() -> dict:
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
    has_openai = bool(os.environ.get("OPENAI_API_KEY"))
    if has_anthropic or has_openai:
        return {"status": "operational", "providers": {
            "anthropic": "configured" if has_anthropic else "not_configured",
            "openai": "configured" if has_openai else "not_configured",
        }}
    return {"status": "degraded", "note": "No AI provider API keys configured"}


def _check_email() -> dict:
    if os.environ.get("RESEND_API_KEY"):
        return {"status": "operational"}
    return {"status": "degraded", "note": "Email service (Resend) not configured"}


def _check_billing() -> dict:
    from services import stripe_service
    if stripe_service.is_configured():
        return {"status": "operational"}
    return {"status": "degraded", "note": "Stripe not configured — billing unavailable"}


async def _get_maintenance_window(db) -> dict | None:
    try:
        doc = await db.platform_settings.find_one({"key": "maintenance_mode"})
        if doc and doc.get("enabled"):
            return {
                "active": True,
                "message": doc.get("message", "Scheduled maintenance in progress"),
                "started_at": doc.get("updated_at"),
            }
    except Exception:
        pass
    return None


@router.get("")
async def get_status():
    """Public platform status — machine-readable for monitoring systems."""
    db_raw = get_db()
    db = DBProxy(db_raw, SecurityContext.system())

    # Run component checks
    mongo = await _check_mongodb()
    redis = await _check_redis()
    ai = _check_ai()
    email = _check_email()
    billing = _check_billing()
    maintenance = await _get_maintenance_window(db)

    components = {
        "api":      {"status": "operational"},
        "database": mongo,
        "cache":    redis,
        "ai":       ai,
        "email":    email,
        "billing":  billing,
    }

    # Derive overall status
    statuses = [c["status"] for c in components.values()]
    if "outage" in statuses or maintenance:
        overall = "outage" if "outage" in statuses else "maintenance"
    elif "degraded" in statuses:
        overall = "degraded"
    else:
        overall = "operational"

    response = {
        "platform": _PLATFORM_NAME,
        "version": _VERSION,
        "status": overall,
        "timestamp": _now(),
        "components": components,
    }
    if maintenance:
        response["maintenance"] = maintenance

    # Fetch active incidents from DB (non-blocking; degrade gracefully)
    try:
        recent_threshold = _ago(days=7).isoformat()
        incidents = await db.platform_incidents.find(
            {"status": {"$in": ["investigating", "identified", "monitoring"]},
             "created_at": {"$gte": recent_threshold}}
        ).sort("created_at", -1).limit(5).to_list(5)
        if incidents:
            response["active_incidents"] = [
                {"id": str(i["_id"]), "title": i.get("title", ""),
                 "status": i.get("status"), "severity": i.get("severity", "minor"),
                 "created_at": i.get("created_at")}
                for i in incidents
            ]
    except Exception:
        pass

    return response


@router.get("/history")
async def get_status_history(days: int = 30):
    """Recent incidents and degradation events (last N days, default 30)."""
    if days > 90:
        days = 90
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    threshold = _ago(days=days).isoformat()
    try:
        incidents = await db.platform_incidents.find(
            {"created_at": {"$gte": threshold}}
        ).sort("created_at", -1).limit(100).to_list(100)
        return {
            "period_days": days,
            "incidents": [
                {
                    "id": str(i["_id"]),
                    "title": i.get("title", ""),
                    "status": i.get("status", "resolved"),
                    "severity": i.get("severity", "minor"),
                    "affected_components": i.get("affected_components", []),
                    "created_at": i.get("created_at"),
                    "resolved_at": i.get("resolved_at"),
                    "updates": i.get("updates", []),
                }
                for i in incidents
            ],
        }
    except Exception:
        return {"period_days": days, "incidents": []}


# ── Admin-only incident management ────────────────────────────────────────────

@router.post("/incidents", dependencies=[Depends(require_super_admin)])
async def create_incident(body: dict, admin: dict = Depends(require_super_admin)):
    """Create a new platform incident (visible on status page)."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    doc = {
        "title": body.get("title", "Incident"),
        "severity": body.get("severity", "minor"),   # minor / major / critical
        "status": body.get("status", "investigating"),  # investigating / identified / monitoring / resolved
        "affected_components": body.get("affected_components", []),
        "message": body.get("message", ""),
        "created_by": admin.get("email"),
        "created_at": _now(),
        "resolved_at": None,
        "updates": [],
    }
    result = await db.platform_incidents.insert_one(doc)
    return {"ok": True, "incident_id": str(result.inserted_id)}


@router.patch("/incidents/{incident_id}", dependencies=[Depends(require_super_admin)])
async def update_incident(incident_id: str, body: dict, admin: dict = Depends(require_super_admin)):
    """Update an incident (add update message, change status, resolve)."""
    from bson import ObjectId
    from bson.errors import InvalidId
    from fastapi import HTTPException

    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    try:
        oid = ObjectId(incident_id)
    except (InvalidId, Exception):
        raise HTTPException(status_code=400, detail="Invalid incident ID")

    update: dict = {"updated_at": _now()}
    if "status" in body:
        update["status"] = body["status"]
        if body["status"] == "resolved":
            update["resolved_at"] = _now()
    if "severity" in body:
        update["severity"] = body["severity"]
    if "message" in body and body["message"]:
        push = {"updates": {
            "message": body["message"],
            "status": body.get("status", ""),
            "updated_by": admin.get("email"),
            "updated_at": _now(),
        }}
    else:
        push = {}

    ops: dict = {"$set": update}
    if push:
        ops["$push"] = push

    result = await db.platform_incidents.update_one({"_id": oid}, ops)
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"ok": True}
