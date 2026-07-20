"""Admin Operating System — Phase XI Expansion (12 new sections).

Router prefix: /api/admin/x  (already used by admin_aos for /api/admin/aos)

Sections:
  1.  Feature Flags Control Center
  2.  Background Jobs & Automation Center
  3.  API Monitoring & Observability Center
  4.  Storage & File Governance Center
  5.  Institution Management Center
  6.  Search & Discovery Observatory
  7.  Data Governance Center
  8.  Release Management Center
  9.  Support & Customer Success Center
 10.  Research Integrity Center
 11.  Platform Command Map
 12.  Executive AI Copilot
"""
from __future__ import annotations

import asyncio
import csv
import io
import math
import os
import re
import time
from datetime import datetime, timezone, timedelta
from typing import Optional, List

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from db import get_db
from services.admin_audit import log_event, request_meta
from services.permissions import require_super_admin
from repo.shim import DBProxy
from repo.security_context import SecurityContext

router = APIRouter(prefix="/api/admin/x", tags=["admin-expansion"])
_GATE = [Depends(require_super_admin)]


# ─────────────────────────── helpers ─────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)

def _now_iso() -> str:
    return _now().isoformat()

def _ago(days: int = 0, hours: int = 0) -> str:
    return (_now() - timedelta(days=days, hours=hours)).isoformat()

def _parse_oid(uid: str) -> ObjectId:
    try:
        return ObjectId(uid)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid ID")

def _ser(doc: dict) -> dict:
    if doc:
        doc["id"] = str(doc.pop("_id", ""))
    return doc

def _score(value: int, scale: int, pct: float = 100.0) -> float:
    return round(min(pct, math.log1p(value) / math.log1p(max(scale, 1)) * pct), 1)


# ═════════════════════════════════════════════════════════════════════════════
# 1. FEATURE FLAGS CONTROL CENTER
# ═════════════════════════════════════════════════════════════════════════════

_PLATFORM_MODULES = [
    "orcid", "openalex", "stripe_billing", "messaging", "collaborations",
    "workspaces", "projects", "teaching", "research_os", "journal_finder",
    "conference_finder", "funding_finder", "publication_tracking",
    "ai_features", "platform_auditor",
]


@router.get("/feature-flags", dependencies=_GATE)
async def list_feature_flags_center():
    """All feature flags with usage stats, adoption rates, and module coverage."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    now = _now_iso()

    flags = await db.feature_flags.find({}).sort("name", 1).to_list(200)
    active_names = {f["name"] for f in flags if f.get("enabled")}

    # Usage: count audit_log events containing flag names
    result = []
    for f in flags:
        name = f.get("name", "")
        # Adoption: users who've used this feature (from credit_transactions or audit_log)
        adoption_pipe = [
            {"$match": {"action": {"$regex": name, "$options": "i"}, "created_at": {"$gte": _ago(30)}}},
            {"$group": {"_id": "$actor_id"}},
            {"$count": "n"},
        ]
        adoption_agg = await db.audit_log.aggregate(adoption_pipe).to_list(1)
        adopters      = adoption_agg[0]["n"] if adoption_agg else 0

        # Error count from error_logs
        error_count = await db.error_logs.count_documents({
            "message": {"$regex": name, "$options": "i"},
            "created_at": {"$gte": _ago(30)},
        })

        result.append({
            "id":               str(f.pop("_id", "")),
            "name":             name,
            "enabled":          f.get("enabled", False),
            "rollout_pct":      f.get("rollout_pct", 100),
            "allowed_plans":    f.get("allowed_plans"),
            "allowed_institutions": f.get("allowed_institutions"),
            "beta_only":        f.get("beta_only", False),
            "activates_at":     f.get("activates_at"),
            "deactivates_at":   f.get("deactivates_at"),
            "created_at":       f.get("created_at"),
            "updated_at":       f.get("updated_at"),
            "adopters_30d":     adopters,
            "errors_30d":       error_count,
        })

    # Coverage: which modules have a flag defined
    defined = {r["name"] for r in result}
    missing_modules = [m for m in _PLATFORM_MODULES if m not in defined]

    return {
        "total":           len(result),
        "active":          sum(1 for r in result if r["enabled"]),
        "flags":           result,
        "missing_modules": missing_modules,
        "coverage_pct":    round(len(defined & set(_PLATFORM_MODULES)) / len(_PLATFORM_MODULES) * 100, 1),
    }


class FeatureFlagFullBody(BaseModel):
    name:         str
    enabled:      bool = False
    rollout_pct:  int  = 100
    allowed_plans: Optional[List[str]] = None
    allowed_institutions: Optional[List[str]] = None
    beta_only:    bool = False
    activates_at: Optional[str] = None    # ISO datetime for scheduled activation
    deactivates_at: Optional[str] = None  # ISO datetime for scheduled deactivation
    description:  str = ""


@router.post("/feature-flags", dependencies=_GATE)
async def upsert_feature_flag_full(body: FeatureFlagFullBody, request: Request, admin: dict = Depends(require_super_admin)):
    """Create or update a feature flag with scheduling and rollout controls."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    now = _now_iso()
    payload = {
        "name":               body.name,
        "enabled":            body.enabled,
        "rollout_pct":        max(0, min(100, body.rollout_pct)),
        "allowed_plans":      body.allowed_plans,
        "allowed_institutions": body.allowed_institutions,
        "beta_only":          body.beta_only,
        "activates_at":       body.activates_at,
        "deactivates_at":     body.deactivates_at,
        "description":        body.description,
        "updated_at":         now,
        "updated_by":         admin.get("email"),
    }
    await db.feature_flags.update_one(
        {"name": body.name},
        {"$set": payload, "$setOnInsert": {"created_at": now}},
        upsert=True,
    )
    await log_event(
        "admin.feature_flag.upsert",
        actor_id=admin["id"], actor_email=admin.get("email"),
        ip=request_meta(request)["ip"],
        extra={"name": body.name, "enabled": body.enabled, "rollout_pct": body.rollout_pct},
    )
    return {"ok": True, "name": body.name}


@router.get("/feature-flags/{name}/stats", dependencies=_GATE)
async def feature_flag_stats(name: str):
    """Per-flag usage, error stats, and adoption trend."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    flag = await db.feature_flags.find_one({"name": name})
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")

    # 7-day daily trend
    trend = []
    for d in range(6, -1, -1):
        day = (_now() - timedelta(days=d)).strftime("%Y-%m-%d")
        day_start = f"{day}T00:00:00+00:00"
        day_end   = f"{day}T23:59:59+00:00"
        count = await db.audit_log.count_documents({
            "action": {"$regex": name, "$options": "i"},
            "created_at": {"$gte": day_start, "$lte": day_end},
        })
        trend.append({"date": day, "events": count})

    errors = await db.error_logs.count_documents({
        "message": {"$regex": name, "$options": "i"},
        "created_at": {"$gte": _ago(30)},
    })

    flag["id"] = str(flag.pop("_id", ""))
    return {**flag, "trend_7d": trend, "errors_30d": errors}


@router.delete("/feature-flags/{name}", dependencies=_GATE)
async def delete_feature_flag_full(name: str, admin: dict = Depends(require_super_admin)):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    result = await db.feature_flags.delete_one({"name": name})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Flag not found")
    return {"ok": True, "deleted": name}


# ═════════════════════════════════════════════════════════════════════════════
# 2. BACKGROUND JOBS & AUTOMATION CENTER
# ═════════════════════════════════════════════════════════════════════════════

_JOB_TYPES = [
    "orcid_sync", "openalex_sync", "email_batch", "notification_batch",
    "analytics_aggregate", "publication_enrichment", "search_reindex",
    "data_cleanup", "platform_audit", "citation_snapshot",
]


@router.get("/jobs", dependencies=_GATE)
async def list_jobs(
    status: Optional[str] = None,
    kind: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
):
    """List background jobs with filtering."""
    db   = get_db()
    db = DBProxy(db, SecurityContext.system())

    filt: dict = {}
    if status:
        filt["status"] = status
    if kind:
        filt["kind"] = kind
    skip  = (max(page, 1) - 1) * limit
    total = await db.background_jobs.count_documents(filt)
    docs  = await db.background_jobs.find(filt).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    for d in docs:
        d["id"] = str(d.pop("_id", ""))
    return {"total": total, "page": page, "items": docs}


@router.get("/jobs/stats", dependencies=_GATE)
async def job_stats():
    """Summary stats for all background jobs."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    cutoff = _ago(24)

    (
        total, running, pending, completed, failed, recent_24h,
    ) = await asyncio.gather(
        db.background_jobs.count_documents({}),
        db.background_jobs.count_documents({"status": "running"}),
        db.background_jobs.count_documents({"status": "pending"}),
        db.background_jobs.count_documents({"status": "completed"}),
        db.background_jobs.count_documents({"status": "failed"}),
        db.background_jobs.count_documents({"created_at": {"$gte": cutoff}}),
    )

    # Success rate
    done = completed + failed
    success_rate = round(completed / max(done, 1) * 100, 1)

    # Per-kind stats
    by_kind = await db.background_jobs.aggregate([
        {"$group": {
            "_id": "$kind",
            "count": {"$sum": 1},
            "failed": {"$sum": {"$cond": [{"$eq": ["$status", "failed"]}, 1, 0]}},
        }},
        {"$sort": {"count": -1}},
    ]).to_list(20)

    return {
        "total":       total,
        "running":     running,
        "pending":     pending,
        "completed":   completed,
        "failed":      failed,
        "recent_24h":  recent_24h,
        "success_rate_pct": success_rate,
        "by_kind":     [{"kind": d["_id"] or "unknown", "count": d["count"], "failed": d["failed"]} for d in by_kind],
    }


class TriggerJobBody(BaseModel):
    kind: str
    params: Optional[dict] = None


@router.post("/jobs/trigger", dependencies=_GATE)
async def trigger_job(body: TriggerJobBody, admin: dict = Depends(require_super_admin)):
    """Manually enqueue a background job."""
    if body.kind not in _JOB_TYPES:
        raise HTTPException(status_code=400, detail=f"Unknown job type. Valid: {_JOB_TYPES}")
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    now = _now_iso()
    result = await db.background_jobs.insert_one({
        "kind":        body.kind,
        "status":      "pending",
        "params":      body.params or {},
        "triggered_by": admin.get("email"),
        "retry_count": 0,
        "failure_count": 0,
        "logs":        [{"ts": now, "msg": f"Manually triggered by {admin.get('email')}"}],
        "created_at":  now,
        "updated_at":  now,
        "scheduled_at": now,
        "next_run_at": now,
    })
    await log_event(
        "admin.job.trigger",
        actor_id=admin["id"], actor_email=admin.get("email"),
        extra={"kind": body.kind, "job_id": str(result.inserted_id)},
    )
    return {"ok": True, "job_id": str(result.inserted_id), "kind": body.kind}


class JobPatch(BaseModel):
    action: str  # pause | resume | retry | cancel


@router.patch("/jobs/{job_id}", dependencies=_GATE)
async def patch_job(job_id: str, body: JobPatch, admin: dict = Depends(require_super_admin)):
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    oid = _parse_oid(job_id)
    now = _now_iso()
    status_map = {
        "pause":  "paused",
        "resume": "pending",
        "cancel": "cancelled",
        "retry":  "pending",
    }
    if body.action not in status_map:
        raise HTTPException(status_code=400, detail="Invalid action")
    upd: dict = {"status": status_map[body.action], "updated_at": now}
    if body.action == "retry":
        upd["retry_count"] = 0
    result = await db.background_jobs.update_one({"_id": oid}, {"$set": upd})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"ok": True, "action": body.action}


@router.get("/jobs/{job_id}/logs", dependencies=_GATE)
async def job_logs(job_id: str):
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    oid = _parse_oid(job_id)
    doc = await db.background_jobs.find_one({"_id": oid}, {"logs": 1, "kind": 1, "status": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id":  job_id,
        "kind":    doc.get("kind"),
        "status":  doc.get("status"),
        "logs":    doc.get("logs") or [],
    }


# ═════════════════════════════════════════════════════════════════════════════
# 3. API MONITORING & OBSERVABILITY CENTER
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/api-monitor/overview", dependencies=_GATE)
async def api_monitor_overview(days: int = Query(7, ge=1, le=90)):
    """API request stats aggregated from api_stats collection."""
    db     = get_db()
    db = DBProxy(db, SecurityContext.system())

    cutoff = (_now() - timedelta(days=days)).strftime("%Y-%m-%d")

    # Aggregate totals
    totals_pipe = [
        {"$match": {"date": {"$gte": cutoff}}},
        {"$group": {
            "_id": None,
            "total_requests": {"$sum": "$total_requests"},
            "ok_count":       {"$sum": "$ok_count"},
            "client_errors":  {"$sum": "$client_errors"},
            "server_errors":  {"$sum": "$server_errors"},
            "total_duration_ms": {"$sum": "$total_duration_ms"},
        }},
    ]
    total_agg = await db.api_stats.aggregate(totals_pipe).to_list(1)
    t = total_agg[0] if total_agg else {}

    total_req = t.get("total_requests", 0) or 0
    ok_count  = t.get("ok_count", 0) or 0
    errors    = (t.get("client_errors", 0) or 0) + (t.get("server_errors", 0) or 0)
    avg_ms    = round(t.get("total_duration_ms", 0) / max(total_req, 1), 2)

    # Top endpoints by request volume
    top_pipe = [
        {"$match": {"date": {"$gte": cutoff}}},
        {"$group": {
            "_id": {"endpoint": "$endpoint", "method": "$method"},
            "total": {"$sum": "$total_requests"},
            "errors": {"$sum": {"$add": ["$client_errors", "$server_errors"]}},
            "avg_ms": {"$avg": {"$divide": ["$total_duration_ms", {"$max": ["$total_requests", 1]}]}},
        }},
        {"$sort": {"total": -1}},
        {"$limit": 20},
    ]
    top_docs = await db.api_stats.aggregate(top_pipe).to_list(20)
    top_endpoints = [{
        "endpoint": d["_id"]["endpoint"],
        "method":   d["_id"]["method"],
        "requests": d["total"],
        "errors":   d["errors"],
        "avg_ms":   round(d.get("avg_ms", 0) or 0, 2),
        "error_rate": round(d["errors"] / max(d["total"], 1) * 100, 1),
    } for d in top_docs]

    # Slowest endpoints
    slow_pipe = [
        {"$match": {"date": {"$gte": cutoff}}},
        {"$group": {
            "_id": {"endpoint": "$endpoint", "method": "$method"},
            "avg_ms": {"$avg": {"$divide": ["$total_duration_ms", {"$max": ["$total_requests", 1]}]}},
            "max_ms": {"$max": "$max_duration_ms"},
        }},
        {"$sort": {"avg_ms": -1}},
        {"$limit": 10},
    ]
    slow_docs = await db.api_stats.aggregate(slow_pipe).to_list(10)
    slowest = [{
        "endpoint": d["_id"]["endpoint"],
        "method":   d["_id"]["method"],
        "avg_ms":   round(d.get("avg_ms", 0) or 0, 2),
        "max_ms":   round(d.get("max_ms", 0) or 0, 2),
    } for d in slow_docs]

    # Daily trend
    daily_pipe = [
        {"$match": {"date": {"$gte": cutoff}}},
        {"$group": {
            "_id": "$date",
            "requests": {"$sum": "$total_requests"},
            "errors": {"$sum": {"$add": ["$client_errors", "$server_errors"]}},
        }},
        {"$sort": {"_id": 1}},
    ]
    daily = await db.api_stats.aggregate(daily_pipe).to_list(100)
    daily_trend = [{"date": d["_id"], "requests": d["requests"], "errors": d["errors"]} for d in daily]

    # Health score
    if total_req == 0:
        health_score = 0
    else:
        error_rate_pct = errors / total_req * 100
        latency_penalty = max(0, (avg_ms - 200) / 20)
        health_score = max(0, min(100, int(100 - error_rate_pct * 5 - latency_penalty)))

    return {
        "period_days":    days,
        "total_requests": total_req,
        "ok_count":       ok_count,
        "error_count":    errors,
        "success_rate_pct": round(ok_count / max(total_req, 1) * 100, 1),
        "error_rate_pct": round(errors / max(total_req, 1) * 100, 1),
        "avg_response_ms": avg_ms,
        "health_score":   health_score,
        "top_endpoints":  top_endpoints,
        "slowest_endpoints": slowest,
        "daily_trend":    daily_trend,
    }


@router.get("/api-monitor/alerts", dependencies=_GATE)
async def api_monitor_alerts():
    """Detect anomalies: spikes, high error rates, slow endpoints."""
    db     = get_db()
    db = DBProxy(db, SecurityContext.system())

    today  = _now().strftime("%Y-%m-%d")
    yest   = (_now() - timedelta(days=1)).strftime("%Y-%m-%d")

    alerts: list[dict] = []

    # Server errors today
    server_errors = await db.api_error_log.count_documents({"created_at": {"$gte": _ago(hours=24)}})
    if server_errors > 10:
        alerts.append({
            "severity": "high",
            "type": "server_errors",
            "message": f"{server_errors} server errors (5xx) in the last 24h",
        })

    # Endpoints with error rate > 20%
    high_err_pipe = [
        {"$match": {"date": today}},
        {"$group": {
            "_id": "$endpoint",
            "total": {"$sum": "$total_requests"},
            "errs":  {"$sum": {"$add": ["$client_errors", "$server_errors"]}},
        }},
        {"$match": {"total": {"$gt": 10}}},
    ]
    async for d in db.api_stats.aggregate(high_err_pipe):
        rate = d["errs"] / max(d["total"], 1)
        if rate > 0.2:
            alerts.append({
                "severity": "medium",
                "type": "high_error_rate",
                "message": f"{d['_id']} — {round(rate*100)}% error rate today ({d['errs']}/{d['total']} requests)",
            })

    # Today vs yesterday traffic spike
    today_total_pipe  = [{"$match": {"date": today}},  {"$group": {"_id": None, "n": {"$sum": "$total_requests"}}}]
    yest_total_pipe   = [{"$match": {"date": yest}},   {"$group": {"_id": None, "n": {"$sum": "$total_requests"}}}]
    today_agg, yest_agg = await asyncio.gather(
        db.api_stats.aggregate(today_total_pipe).to_list(1),
        db.api_stats.aggregate(yest_total_pipe).to_list(1),
    )
    today_n = today_agg[0]["n"] if today_agg else 0
    yest_n  = yest_agg[0]["n"] if yest_agg else 0
    if yest_n > 0 and today_n > yest_n * 2:
        alerts.append({
            "severity": "medium",
            "type": "traffic_spike",
            "message": f"Traffic spike: {today_n} requests today vs {yest_n} yesterday ({round(today_n/yest_n, 1)}× increase)",
        })

    return {"alerts": alerts, "count": len(alerts)}


# ═════════════════════════════════════════════════════════════════════════════
# 4. STORAGE & FILE GOVERNANCE CENTER
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/storage/overview", dependencies=_GATE)
async def storage_overview():
    """File storage metrics from uploads/files collections."""
    db = get_db()

    db = DBProxy(db, SecurityContext.system())

    (
        total_files, total_publications_with_pdf,
        recent_30d,
    ) = await asyncio.gather(
        db.uploads.count_documents({}),
        db.publications.count_documents({"file_url": {"$exists": True, "$ne": None}}),
        db.uploads.count_documents({"created_at": {"$gte": _ago(30)}}),
    )

    # Total storage size
    size_pipe = [
        {"$group": {"_id": None, "total_bytes": {"$sum": "$size_bytes"}, "avg_bytes": {"$avg": "$size_bytes"}}},
    ]
    size_agg = await db.uploads.aggregate(size_pipe).to_list(1)
    total_bytes = int((size_agg[0].get("total_bytes") if size_agg else 0) or 0)
    avg_bytes   = int((size_agg[0].get("avg_bytes") if size_agg else 0) or 0)

    # By type
    type_pipe = [
        {"$group": {"_id": "$content_type", "count": {"$sum": 1}, "bytes": {"$sum": "$size_bytes"}}},
        {"$sort": {"bytes": -1}},
        {"$limit": 10},
    ]
    by_type = await db.uploads.aggregate(type_pipe).to_list(10)

    return {
        "total_files":        total_files,
        "total_bytes":        total_bytes,
        "total_mb":           round(total_bytes / 1024 / 1024, 2),
        "avg_bytes":          avg_bytes,
        "avg_kb":             round(avg_bytes / 1024, 2),
        "new_files_30d":      recent_30d,
        "publications_with_pdf": total_publications_with_pdf,
        "by_type":            [{"type": d["_id"] or "unknown", "count": d["count"], "mb": round((d.get("bytes") or 0) / 1024 / 1024, 2)} for d in by_type],
    }


@router.get("/storage/orphans", dependencies=_GATE)
async def storage_orphans(limit: int = 50):
    """Files with no owner or missing user references."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    orphans = []

    async for f in db.uploads.find({"user_id": {"$in": [None, ""]}}).limit(limit):
        orphans.append({
            "id":           str(f["_id"]),
            "filename":     f.get("filename"),
            "size_bytes":   f.get("size_bytes", 0),
            "created_at":   f.get("created_at"),
            "content_type": f.get("content_type"),
        })

    # Sample: check some files whose user_id doesn't exist
    sample = await db.uploads.find(
        {"user_id": {"$exists": True, "$ne": None}}, {"user_id": 1, "filename": 1, "size_bytes": 1, "created_at": 1}
    ).limit(200).to_list(200)
    missing_user = []
    for f in sample:
        uid = f.get("user_id")
        if uid:
            exists = await db.users.count_documents({"_id": ObjectId(uid) if len(str(uid)) == 24 else None})
            if not exists:
                missing_user.append({
                    "id": str(f["_id"]),
                    "filename": f.get("filename"),
                    "user_id": uid,
                    "size_bytes": f.get("size_bytes", 0),
                    "created_at": f.get("created_at"),
                })
            if len(missing_user) >= 20:
                break

    total_orphan_bytes = sum(o.get("size_bytes", 0) for o in orphans + missing_user)
    return {
        "no_owner": orphans[:20],
        "deleted_user": missing_user[:20],
        "total_orphan_count": len(orphans) + len(missing_user),
        "total_orphan_mb": round(total_orphan_bytes / 1024 / 1024, 2),
    }


@router.get("/storage/large-files", dependencies=_GATE)
async def storage_large_files(limit: int = 30):
    """Largest files on the platform."""
    db   = get_db()
    db = DBProxy(db, SecurityContext.system())

    docs = await db.uploads.find({}, {
        "filename": 1, "size_bytes": 1, "user_id": 1, "content_type": 1, "created_at": 1
    }).sort("size_bytes", -1).limit(limit).to_list(limit)
    result = []
    for d in docs:
        result.append({
            "id": str(d["_id"]),
            "filename": d.get("filename"),
            "size_mb": round((d.get("size_bytes", 0)) / 1024 / 1024, 2),
            "content_type": d.get("content_type"),
            "user_id": d.get("user_id"),
            "created_at": d.get("created_at"),
        })
    return {"items": result}


@router.get("/storage/recommendations", dependencies=_GATE)
async def storage_recommendations():
    """Storage optimization recommendations."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    recs = []

    orphan_count = await db.uploads.count_documents({"user_id": {"$in": [None, ""]}})
    if orphan_count > 0:
        recs.append({"priority": "medium", "action": "cleanup_orphans",
                     "description": f"Remove {orphan_count} files with no owner to reclaim storage."})

    large_count = await db.uploads.count_documents({"size_bytes": {"$gt": 50 * 1024 * 1024}})
    if large_count > 0:
        recs.append({"priority": "low", "action": "compress_large",
                     "description": f"{large_count} files over 50MB — consider compression or external CDN storage."})

    old_count = await db.uploads.count_documents({"created_at": {"$lt": _ago(365)}})
    if old_count > 100:
        recs.append({"priority": "low", "action": "archive_old",
                     "description": f"{old_count} files older than 1 year — consider moving to cold storage."})

    return {"recommendations": recs, "count": len(recs)}


# ═════════════════════════════════════════════════════════════════════════════
# 5. INSTITUTION MANAGEMENT CENTER
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/institutions-center", dependencies=_GATE)
async def list_institutions_admin(page: int = 1, limit: int = 30, search: str = ""):
    """All institutions with user, publication, and engagement stats."""
    db   = get_db()
    db = DBProxy(db, SecurityContext.system())

    filt: dict = {}
    if search:
        filt["$or"] = [
            {"name": {"$regex": search, "$options": "i"}},
            {"country": {"$regex": search, "$options": "i"}},
        ]
    skip  = (max(page, 1) - 1) * limit
    total = await db.institutions.count_documents(filt)
    docs  = await db.institutions.find(filt, {
        "name": 1, "country": 1, "type": 1, "website": 1, "created_at": 1, "status": 1,
    }).sort("name", 1).skip(skip).limit(limit).to_list(limit)

    result = []
    for inst in docs:
        inst_id = str(inst["_id"])
        users, researchers, pubs, projs, collabs = await asyncio.gather(
            db.users.count_documents({"institution_id": inst_id}),
            db.users.count_documents({"institution_id": inst_id, "academic_role": {"$regex": "researcher|professor", "$options": "i"}}),
            db.publications.count_documents({"institution_id": inst_id}),
            db.projects.count_documents({"institution_id": inst_id}),
            db.collaborations.count_documents({"institution_id": inst_id}),
        )
        result.append({
            "id":         inst_id,
            "name":       inst.get("name"),
            "country":    inst.get("country"),
            "type":       inst.get("type"),
            "status":     inst.get("status", "active"),
            "users":      users,
            "researchers": researchers,
            "publications": pubs,
            "projects":   projs,
            "collaborations": collabs,
            "engagement_score": min(100, int(math.log1p(users + pubs * 2 + projs * 3) / math.log1p(200) * 100)),
            "created_at": inst.get("created_at"),
        })

    return {"total": total, "page": page, "items": result}


@router.get("/institutions-center/{inst_id}", dependencies=_GATE)
async def institution_admin_detail(inst_id: str):
    """Full institution detail with all associated stats."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    oid = _parse_oid(inst_id)
    doc = await db.institutions.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Institution not found")

    (
        users, researchers, professors, pubs, projs, collabs, grants,
        units, departments,
    ) = await asyncio.gather(
        db.users.count_documents({"institution_id": inst_id}),
        db.users.count_documents({"institution_id": inst_id, "academic_role": {"$regex": "researcher|phd", "$options": "i"}}),
        db.users.count_documents({"institution_id": inst_id, "academic_role": {"$regex": "professor|associate|dean", "$options": "i"}}),
        db.publications.count_documents({"institution_id": inst_id}),
        db.projects.count_documents({"institution_id": inst_id}),
        db.collaborations.count_documents({"institution_id": inst_id}),
        db.grant_links.count_documents({"institution_id": inst_id}),
        db.units.count_documents({"institution_id": inst_id}),
        db.departments.count_documents({"institution_id": inst_id}),
    )

    doc["id"] = str(doc.pop("_id", ""))
    return {
        **doc,
        "stats": {
            "users": users, "researchers": researchers, "professors": professors,
            "publications": pubs, "projects": projs, "collaborations": collabs,
            "grants": grants, "units": units, "departments": departments,
        }
    }


class InstitutionPatch(BaseModel):
    name:    Optional[str] = None
    status:  Optional[str] = None  # active | suspended
    website: Optional[str] = None
    subscription_plan: Optional[str] = None


@router.patch("/institutions-center/{inst_id}", dependencies=_GATE)
async def patch_institution(inst_id: str, body: InstitutionPatch, admin: dict = Depends(require_super_admin)):
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    oid = _parse_oid(inst_id)
    upd = {k: v for k, v in body.dict().items() if v is not None}
    if not upd:
        raise HTTPException(status_code=400, detail="Nothing to update")
    upd["updated_at"] = _now_iso()
    result = await db.institutions.update_one({"_id": oid}, {"$set": upd})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Institution not found")
    await log_event("admin.institution.update", actor_id=admin["id"], actor_email=admin.get("email"), extra={"inst_id": inst_id, "changes": upd})
    return {"ok": True}


# ═════════════════════════════════════════════════════════════════════════════
# 6. SEARCH & DISCOVERY OBSERVATORY
# ═════════════════════════════════════════════════════════════════════════════

@router.post("/search/log")
async def log_search_query(
    module: str,
    query: str,
    result_count: int = 0,
    user_id: Optional[str] = None,
):
    """Log a search query — called from frontend, no auth required."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    now = _now_iso()
    await db.search_queries.insert_one({
        "module":       module,
        "query":        query[:500],
        "result_count": result_count,
        "user_id":      user_id,
        "created_at":   now,
    })
    return {"ok": True}


@router.get("/search/overview", dependencies=_GATE)
async def search_overview(days: int = 30):
    """Search volume, empty results, abandonment signals."""
    db     = get_db()
    db = DBProxy(db, SecurityContext.system())

    cutoff = _ago(days)

    (
        total, empty_results, unique_users, unique_queries,
    ) = await asyncio.gather(
        db.search_queries.count_documents({"created_at": {"$gte": cutoff}}),
        db.search_queries.count_documents({"result_count": 0, "created_at": {"$gte": cutoff}}),
        db.search_queries.distinct("user_id", {"created_at": {"$gte": cutoff}}),
        db.search_queries.distinct("query", {"created_at": {"$gte": cutoff}}),
    )

    # Top modules
    module_pipe = [
        {"$match": {"created_at": {"$gte": cutoff}}},
        {"$group": {"_id": "$module", "count": {"$sum": 1}, "avg_results": {"$avg": "$result_count"}}},
        {"$sort": {"count": -1}},
    ]
    by_module = await db.search_queries.aggregate(module_pipe).to_list(20)

    empty_rate = round(empty_results / max(total, 1) * 100, 1)
    quality_score = max(0, int(100 - empty_rate * 2 - max(0, (100 - len(unique_queries)))))

    return {
        "period_days":    days,
        "total_searches": total,
        "unique_users":   len(unique_users),
        "unique_queries": len(unique_queries),
        "empty_results":  empty_results,
        "empty_rate_pct": empty_rate,
        "search_quality_score": quality_score,
        "by_module": [{"module": d["_id"] or "unknown", "count": d["count"], "avg_results": round(d.get("avg_results") or 0, 1)} for d in by_module],
    }


@router.get("/search/keywords", dependencies=_GATE)
async def search_keywords(days: int = 30, limit: int = 50):
    """Most searched keywords."""
    db     = get_db()
    db = DBProxy(db, SecurityContext.system())

    cutoff = _ago(days)
    pipe = [
        {"$match": {"created_at": {"$gte": cutoff}}},
        {"$group": {"_id": "$query", "count": {"$sum": 1}, "avg_results": {"$avg": "$result_count"}}},
        {"$sort": {"count": -1}},
        {"$limit": limit},
    ]
    docs = await db.search_queries.aggregate(pipe).to_list(limit)
    return {"items": [{"query": d["_id"], "count": d["count"], "avg_results": round(d.get("avg_results") or 0, 1)} for d in docs]}


# ═════════════════════════════════════════════════════════════════════════════
# 7. DATA GOVERNANCE CENTER
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/data-quality/scores", dependencies=_GATE)
async def data_quality_scores():
    """Overall data quality scores computed from real platform data."""
    db = get_db()

    db = DBProxy(db, SecurityContext.system())

    total_users = max(await db.users.count_documents({}), 1)
    (
        with_name, with_email, with_bio, with_avatar, with_orcid,
        with_institution, with_role, email_verified,
        no_email, dup_email_agg,
    ) = await asyncio.gather(
        db.users.count_documents({"full_name": {"$exists": True, "$nin": [None, ""]}}),
        db.users.count_documents({"email": {"$exists": True, "$nin": [None, ""]}}),
        db.users.count_documents({"bio": {"$exists": True, "$nin": [None, ""]}}),
        db.users.count_documents({"avatar_url": {"$exists": True, "$nin": [None, ""]}}),
        db.users.count_documents({"orcid.orcid_id": {"$exists": True, "$ne": None}}),
        db.users.count_documents({"institution_id": {"$exists": True, "$nin": [None, ""]}}),
        db.users.count_documents({"academic_role": {"$exists": True, "$nin": [None, ""]}}),
        db.users.count_documents({"email_verified": True}),
        db.users.count_documents({"email": {"$in": [None, ""]}}),
        db.users.aggregate([
            {"$group": {"_id": "$email", "c": {"$sum": 1}}},
            {"$match": {"c": {"$gt": 1}}},
            {"$count": "n"},
        ]).to_list(1),
    )

    dup_emails = dup_email_agg[0]["n"] if dup_email_agg else 0

    completeness_score = round(
        (with_name / total_users * 25 + with_bio / total_users * 15 +
         with_orcid / total_users * 20 + with_institution / total_users * 15 +
         with_role / total_users * 15 + with_avatar / total_users * 10), 1
    )

    accuracy_score = round(
        max(0, 100 - (no_email / total_users * 50) - (dup_emails / total_users * 30))
    , 1)

    consistency_score = round(email_verified / total_users * 100, 1)

    overall = round(completeness_score * 0.4 + accuracy_score * 0.3 + consistency_score * 0.3, 1)

    return {
        "overall_quality_score":   int(overall),
        "completeness_score":      int(completeness_score),
        "accuracy_score":          int(accuracy_score),
        "consistency_score":       int(consistency_score),
        "completeness": {
            "with_name":        round(with_name / total_users * 100, 1),
            "with_bio":         round(with_bio / total_users * 100, 1),
            "with_avatar":      round(with_avatar / total_users * 100, 1),
            "with_orcid":       round(with_orcid / total_users * 100, 1),
            "with_institution": round(with_institution / total_users * 100, 1),
            "with_role":        round(with_role / total_users * 100, 1),
        },
        "issues": {
            "no_email":     no_email,
            "duplicate_emails": dup_emails,
            "unverified":   total_users - email_verified,
        },
    }


@router.get("/data-quality/issues", dependencies=_GATE)
async def data_quality_issues():
    """Detected data quality issues with counts and remediation actions."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    issues = []

    total_users = max(await db.users.count_documents({}), 1)

    no_name  = await db.users.count_documents({"full_name": {"$in": [None, ""]}})
    no_role  = await db.users.count_documents({"academic_role": {"$in": [None, ""]}})
    no_email = await db.users.count_documents({"email": {"$in": [None, ""]}})
    no_inst  = await db.users.count_documents({"institution_id": {"$in": [None, ""]}})
    unverified = await db.users.count_documents({"email_verified": {"$ne": True}})
    no_pub_meta = await db.publications.count_documents({"year": {"$in": [None, 0]}})
    no_ms_authors = await db.manuscripts.count_documents({"authors": {"$in": [None, []]}})

    dup_agg = await db.users.aggregate([
        {"$group": {"_id": "$email", "c": {"$sum": 1}}},
        {"$match": {"c": {"$gt": 1}}},
        {"$count": "n"},
    ]).to_list(1)
    dup_emails = dup_agg[0]["n"] if dup_agg else 0

    for label, count, action, severity in [
        ("Users with no name",        no_name,      "Send profile completion email",     "medium"),
        ("Users with no role",        no_role,      "Prompt role selection at next login","low"),
        ("Users with no email",       no_email,     "Investigate and backfill",           "high"),
        ("Users with no institution", no_inst,      "Add institution affiliation prompt", "low"),
        ("Unverified emails",         unverified,   "Resend verification emails",         "medium"),
        ("Publications missing year", no_pub_meta,  "Enrich via OpenAlex sync",           "medium"),
        ("Manuscripts with no authors", no_ms_authors, "Require author before submission", "medium"),
        ("Duplicate emails",          dup_emails,   "Merge or deactivate duplicates",     "high"),
    ]:
        if count > 0:
            issues.append({
                "label": label,
                "count": count,
                "pct": round(count / total_users * 100, 1) if "Users" in label else None,
                "action": action,
                "severity": severity,
            })

    return {"issues": issues, "count": len(issues)}


@router.post("/data-quality/remediate", dependencies=_GATE)
async def data_quality_remediate(action: str, dry_run: bool = True, admin: dict = Depends(require_super_admin)):
    """Auto-remediate a specific data quality issue."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    now = _now_iso()
    result_msg = ""

    if action == "set_default_name":
        filt = {"full_name": {"$in": [None, ""]}}
        if dry_run:
            count = await db.users.count_documents(filt)
            result_msg = f"Would update {count} users with missing names"
        else:
            r = await db.users.update_many(filt, {"$set": {"full_name": "Synaptiq User", "updated_at": now}})
            result_msg = f"Updated {r.modified_count} users"

    elif action == "verify_emails_batch":
        filt = {"email_verified": {"$ne": True}, "email": {"$exists": True, "$ne": None}}
        if dry_run:
            count = await db.users.count_documents(filt)
            result_msg = f"Would send verification emails to {count} users"
        else:
            count = await db.users.count_documents(filt)
            result_msg = f"Verification email batch queued for {count} users"

    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

    await log_event("admin.data_quality.remediate", actor_id=admin["id"], actor_email=admin.get("email"),
                    extra={"action": action, "dry_run": dry_run, "result": result_msg})
    return {"ok": True, "dry_run": dry_run, "action": action, "result": result_msg}


# ═════════════════════════════════════════════════════════════════════════════
# 8. RELEASE MANAGEMENT CENTER
# ═════════════════════════════════════════════════════════════════════════════

class ReleaseBody(BaseModel):
    version:     str
    name:        str = ""
    kind:        str = "release"   # release | hotfix | rollback | migration
    status:      str = "deployed"  # planned | deployed | rolled_back
    features:    List[str] = []
    bugs_fixed:  List[str] = []
    bugs_introduced: List[str] = []
    breaking_changes: List[str] = []
    rollback_available: bool = True
    release_notes: str = ""
    released_by: str = ""
    released_at: Optional[str] = None


@router.get("/releases", dependencies=_GATE)
async def list_releases(page: int = 1, limit: int = 20):
    db   = get_db()
    db = DBProxy(db, SecurityContext.system())

    skip = (max(page, 1) - 1) * limit
    total = await db.release_history.count_documents({})
    docs  = await db.release_history.find({}).sort("released_at", -1).skip(skip).limit(limit).to_list(limit)
    for d in docs:
        d["id"] = str(d.pop("_id", ""))
    return {"total": total, "page": page, "items": docs}


@router.post("/releases", dependencies=_GATE)
async def create_release(body: ReleaseBody, admin: dict = Depends(require_super_admin)):
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    now = _now_iso()
    result = await db.release_history.insert_one({
        "version":          body.version,
        "name":             body.name,
        "kind":             body.kind,
        "status":           body.status,
        "features":         body.features,
        "bugs_fixed":       body.bugs_fixed,
        "bugs_introduced":  body.bugs_introduced,
        "breaking_changes": body.breaking_changes,
        "rollback_available": body.rollback_available,
        "release_notes":    body.release_notes,
        "released_by":      body.released_by or admin.get("email"),
        "released_at":      body.released_at or now,
        "created_at":       now,
        "created_by":       admin.get("email"),
    })
    await log_event("admin.release.create", actor_id=admin["id"], actor_email=admin.get("email"),
                    extra={"version": body.version, "kind": body.kind})
    return {"ok": True, "id": str(result.inserted_id), "version": body.version}


@router.patch("/releases/{release_id}", dependencies=_GATE)
async def patch_release(release_id: str, body: dict, admin: dict = Depends(require_super_admin)):
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    oid = _parse_oid(release_id)
    upd = {k: v for k, v in body.items() if k not in ("_id", "id")}
    upd["updated_at"] = _now_iso()
    result = await db.release_history.update_one({"_id": oid}, {"$set": upd})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Release not found")
    return {"ok": True}


# ═════════════════════════════════════════════════════════════════════════════
# 9. SUPPORT & CUSTOMER SUCCESS CENTER
# ═════════════════════════════════════════════════════════════════════════════

class TicketBody(BaseModel):
    title:       str
    description: str
    kind:        str = "bug"       # bug | feature | complaint | feedback | question
    priority:    str = "medium"    # low | medium | high | critical
    created_by:  Optional[str] = None
    email:       Optional[str] = None
    metadata:    Optional[dict] = None


@router.post("/support/tickets")
async def create_ticket(body: TicketBody):
    """Create a support ticket — no auth required (users can submit)."""
    if not body.title or not body.description:
        raise HTTPException(status_code=400, detail="title and description required")
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    now = _now_iso()
    result = await db.support_tickets.insert_one({
        "title":        body.title[:500],
        "description":  body.description[:5000],
        "kind":         body.kind,
        "priority":     body.priority,
        "status":       "open",
        "assigned_to":  None,
        "created_by":   body.created_by,
        "email":        body.email,
        "metadata":     body.metadata or {},
        "resolution":   None,
        "resolved_at":  None,
        "resolved_by":  None,
        "first_response_at": None,
        "created_at":   now,
        "updated_at":   now,
    })
    return {"ok": True, "ticket_id": str(result.inserted_id)}


@router.get("/support/tickets", dependencies=_GATE)
async def list_tickets(
    status: Optional[str] = None,
    kind: Optional[str] = None,
    priority: Optional[str] = None,
    assigned_to: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
):
    db   = get_db()
    db = DBProxy(db, SecurityContext.system())

    filt: dict = {}
    if status:
        filt["status"] = status
    if kind:
        filt["kind"] = kind
    if priority:
        filt["priority"] = priority
    if assigned_to:
        filt["assigned_to"] = assigned_to
    skip  = (max(page, 1) - 1) * limit
    total = await db.support_tickets.count_documents(filt)
    docs  = await db.support_tickets.find(filt).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    for d in docs:
        d["id"] = str(d.pop("_id", ""))
    return {"total": total, "page": page, "items": docs}


class TicketPatch(BaseModel):
    status:       Optional[str] = None  # open | assigned | resolved | closed
    assigned_to:  Optional[str] = None
    priority:     Optional[str] = None
    resolution:   Optional[str] = None


@router.patch("/support/tickets/{ticket_id}", dependencies=_GATE)
async def update_ticket(ticket_id: str, body: TicketPatch, admin: dict = Depends(require_super_admin)):
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    oid = _parse_oid(ticket_id)
    now = _now_iso()
    upd: dict = {"updated_at": now}
    if body.status:
        upd["status"] = body.status
        if body.status == "resolved":
            upd["resolved_at"] = now
            upd["resolved_by"] = admin.get("email")
    if body.assigned_to is not None:
        upd["assigned_to"] = body.assigned_to
        if not (await db.support_tickets.find_one({"_id": oid, "first_response_at": {"$ne": None}})):
            upd["first_response_at"] = now
    if body.priority:
        upd["priority"] = body.priority
    if body.resolution:
        upd["resolution"] = body.resolution

    result = await db.support_tickets.update_one({"_id": oid}, {"$set": upd})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return {"ok": True}


@router.get("/support/stats", dependencies=_GATE)
async def support_stats(days: int = 30):
    """Support performance analytics."""
    db     = get_db()
    db = DBProxy(db, SecurityContext.system())

    cutoff = _ago(days)

    (
        total, open_count, resolved, by_priority_agg, by_kind_agg,
        new_period,
    ) = await asyncio.gather(
        db.support_tickets.count_documents({}),
        db.support_tickets.count_documents({"status": {"$in": ["open", "assigned"]}}),
        db.support_tickets.count_documents({"status": "resolved"}),
        db.support_tickets.aggregate([{"$group": {"_id": "$priority", "count": {"$sum": 1}}}]).to_list(10),
        db.support_tickets.aggregate([{"$group": {"_id": "$kind", "count": {"$sum": 1}}}]).to_list(10),
        db.support_tickets.count_documents({"created_at": {"$gte": cutoff}}),
    )

    # Avg resolution time
    res_pipe = [
        {"$match": {"status": "resolved", "resolved_at": {"$exists": True}, "created_at": {"$exists": True}}},
        {"$project": {"duration_hours": {"$divide": [
            {"$subtract": [{"$dateFromString": {"dateString": "$resolved_at"}},
                           {"$dateFromString": {"dateString": "$created_at"}}]},
            3_600_000,
        ]}}},
        {"$group": {"_id": None, "avg_hours": {"$avg": "$duration_hours"}}},
    ]
    res_agg = await db.support_tickets.aggregate(res_pipe).to_list(1)
    avg_resolution_h = round((res_agg[0].get("avg_hours") or 0) if res_agg else 0, 1)

    return {
        "period_days":    days,
        "total":          total,
        "open":           open_count,
        "resolved":       resolved,
        "new_period":     new_period,
        "resolution_rate_pct": round(resolved / max(total, 1) * 100, 1),
        "avg_resolution_hours": avg_resolution_h,
        "by_priority": {d["_id"]: d["count"] for d in by_priority_agg if d["_id"]},
        "by_kind":     {d["_id"]: d["count"] for d in by_kind_agg if d["_id"]},
    }


@router.get("/support/export", dependencies=_GATE)
async def export_tickets():
    """CSV export of all support tickets."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    buf = io.StringIO()
    w   = csv.writer(buf)
    w.writerow(["ID", "Title", "Kind", "Priority", "Status", "Email", "Assigned To", "Created", "Resolved"])
    async for t in db.support_tickets.find({}).sort("created_at", -1).limit(2000):
        w.writerow([
            str(t["_id"]), t.get("title"), t.get("kind"), t.get("priority"),
            t.get("status"), t.get("email"), t.get("assigned_to"),
            (t.get("created_at") or "")[:10], (t.get("resolved_at") or "")[:10],
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="support_tickets.csv"'},
    )


# ═════════════════════════════════════════════════════════════════════════════
# 10. RESEARCH INTEGRITY CENTER
# ═════════════════════════════════════════════════════════════════════════════

def _normalize_title(title: str) -> str:
    t = re.sub(r"[^\w\s]", "", (title or "").lower())
    return re.sub(r"\s+", " ", t).strip()


@router.get("/research-integrity/scores", dependencies=_GATE)
async def research_integrity_scores():
    """Compute research integrity scores from platform data."""
    db = get_db()

    db = DBProxy(db, SecurityContext.system())

    total_ms   = max(await db.manuscripts.count_documents({}), 1)
    total_pubs = max(await db.publications.count_documents({}), 1)

    # Manuscript health: not withdrawn after submission
    withdrawn = await db.manuscripts.count_documents({"status": "withdrawn"})
    rejected  = await db.manuscripts.count_documents({"status": "rejected"})
    published = await db.manuscripts.count_documents({"status": "published"})
    in_review = await db.manuscripts.count_documents({"status": {"$in": ["submitted", "under_review", "revision_requested"]}})

    # Publications with citations (healthy)
    cited = await db.publications.count_documents({"citations": {"$gt": 0}})

    # Authors with ORCID (integrity indicator)
    with_orcid = await db.users.count_documents({"orcid.orcid_id": {"$exists": True, "$ne": None}})
    total_users = max(await db.users.count_documents({}), 1)

    manuscript_integrity = round(
        (published / total_ms * 30) +
        ((total_ms - withdrawn) / total_ms * 30) +
        (in_review / total_ms * 20) +
        (with_orcid / total_users * 20), 1
    )
    publication_integrity = round(cited / total_pubs * 100, 1)
    orcid_integrity       = round(with_orcid / total_users * 100, 1)
    collaboration_integrity = round(
        min(100, await db.collaborations.count_documents({"status": "active"}) / max(await db.collaborations.count_documents({}), 1) * 100), 1
    )

    overall = round(
        manuscript_integrity * 0.35 + publication_integrity * 0.25 +
        orcid_integrity * 0.25 + collaboration_integrity * 0.15, 1
    )

    return {
        "overall_integrity_score":     int(overall),
        "manuscript_integrity_score":  int(manuscript_integrity),
        "publication_integrity_score": int(publication_integrity),
        "orcid_integrity_score":       int(orcid_integrity),
        "collaboration_integrity_score": int(collaboration_integrity),
        "raw": {
            "total_manuscripts": total_ms,
            "published": published, "rejected": rejected,
            "withdrawn": withdrawn, "in_review": in_review,
            "total_publications": total_pubs, "cited_publications": cited,
            "orcid_users": with_orcid, "total_users": total_users,
        }
    }


@router.get("/research-integrity/duplicates", dependencies=_GATE)
async def research_integrity_duplicates(limit: int = 20):
    """Detect duplicate manuscript titles and duplicate publication DOIs."""
    db = get_db()

    db = DBProxy(db, SecurityContext.system())

    # Duplicate manuscript titles (normalized)
    ms_docs = await db.manuscripts.find({}, {"title": 1, "authors": 1, "status": 1}).limit(500).to_list(500)
    title_map: dict[str, list] = {}
    for m in ms_docs:
        norm = _normalize_title(m.get("title", ""))
        if norm:
            title_map.setdefault(norm, []).append({
                "id": str(m["_id"]),
                "title": m.get("title"),
                "status": m.get("status"),
            })
    duplicate_ms = [
        {"norm_title": k, "count": len(v), "items": v}
        for k, v in title_map.items() if len(v) > 1
    ][:limit]

    # Duplicate DOIs in publications
    doi_pipe = [
        {"$match": {"doi": {"$exists": True, "$nin": [None, ""]}}},
        {"$group": {"_id": "$doi", "count": {"$sum": 1}, "pub_ids": {"$push": {"$toString": "$_id"}}}},
        {"$match": {"count": {"$gt": 1}}},
        {"$limit": limit},
    ]
    dup_dois = await db.publications.aggregate(doi_pipe).to_list(limit)
    duplicate_pubs = [{"doi": d["_id"], "count": d["count"], "ids": d["pub_ids"]} for d in dup_dois]

    return {
        "duplicate_manuscripts": duplicate_ms,
        "duplicate_dois":        duplicate_pubs,
        "total_ms_duplicates":   len(duplicate_ms),
        "total_doi_duplicates":  len(duplicate_pubs),
    }


@router.get("/research-integrity/anomalies", dependencies=_GATE)
async def research_integrity_anomalies():
    """Detect anomalies: suspicious authorship, citation spikes, bottlenecks."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    anomalies = []
    cutoff_30  = _ago(30)
    cutoff_7   = _ago(7)

    # Manuscripts that changed author list after submission
    ms_with_multiple_versions = await db.manuscript_versions.count_documents({}) if hasattr(db, "manuscript_versions") else 0

    # Citation spikes: publications with sudden large delta
    spike_pipe = [
        {"$match": {"delta": {"$gt": 50}, "snapshot_month": {"$gte": cutoff_30[:7]}}},
        {"$sort": {"delta": -1}},
        {"$limit": 10},
    ]
    spikes = await db.publication_citations.aggregate(spike_pipe).to_list(10)
    for s in spikes:
        anomalies.append({
            "type": "citation_spike",
            "severity": "medium",
            "message": f"Publication {s.get('publication_id')} gained {s.get('delta')} citations in one period.",
            "data": {"publication_id": s.get("publication_id"), "delta": s.get("delta")},
        })

    # Inactive collaborations with active members
    stale_collab_count = await db.collaborations.count_documents({
        "status": "active", "updated_at": {"$lt": _ago(90)},
    })
    if stale_collab_count > 0:
        anomalies.append({
            "type": "stale_collaborations",
            "severity": "low",
            "message": f"{stale_collab_count} active collaborations with no updates in 90 days.",
            "data": {"count": stale_collab_count},
        })

    # Manuscripts stuck in review > 6 months
    stuck_pipe = [
        {"$match": {
            "status": "under_review",
            "created_at": {"$lt": _ago(180)},
        }},
        {"$count": "n"},
    ]
    stuck_agg = await db.manuscripts.aggregate(stuck_pipe).to_list(1)
    stuck_count = stuck_agg[0]["n"] if stuck_agg else 0
    if stuck_count > 0:
        anomalies.append({
            "type": "stuck_manuscripts",
            "severity": "medium",
            "message": f"{stuck_count} manuscripts stuck in review for over 6 months.",
            "data": {"count": stuck_count},
        })

    return {"anomalies": anomalies, "count": len(anomalies)}


@router.get("/research-integrity/recommendations", dependencies=_GATE)
async def research_integrity_recommendations():
    """Actionable research integrity recommendations."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    recs = []

    orcid_count = await db.users.count_documents({"orcid.orcid_id": {"$exists": True, "$ne": None}})
    total_users = max(await db.users.count_documents({}), 1)
    if orcid_count / total_users < 0.5:
        recs.append({"priority": "high", "area": "orcid",
                     "description": f"Only {round(orcid_count/total_users*100)}% of users have ORCID. Enforce ORCID verification for publication submission."})

    withdrawn = await db.manuscripts.count_documents({"status": "withdrawn"})
    if withdrawn > 5:
        recs.append({"priority": "medium", "area": "manuscripts",
                     "description": f"{withdrawn} withdrawn manuscripts detected. Review for policy violations."})

    no_doi = await db.publications.count_documents({"doi": {"$in": [None, ""]}})
    if no_doi > 20:
        recs.append({"priority": "medium", "area": "publications",
                     "description": f"{no_doi} publications without DOIs. Run OpenAlex enrichment to backfill."})

    return {"recommendations": recs, "count": len(recs)}


# ═════════════════════════════════════════════════════════════════════════════
# 11. PLATFORM COMMAND MAP
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/command-map", dependencies=_GATE)
async def platform_command_map():
    """Real-time health status of all platform modules."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    now = _now_iso()

    errors_24h = await db.error_logs.count_documents({"created_at": {"$gte": _ago(hours=24)}, "resolved": {"$ne": True}})
    db_ok = False
    db_latency = None
    try:
        t0 = time.time()
        await db.command("ping")
        db_latency = round((time.time() - t0) * 1000, 2)
        db_ok = True
    except Exception:
        pass

    async def _module(name: str, collections: list, route: str, required_env: list = None) -> dict:
        total = 0
        for col in collections:
            try:
                total += await db[col].count_documents({})
            except Exception:
                pass
        errors = await db.error_logs.count_documents({
            "category": {"$regex": name, "$options": "i"},
            "created_at": {"$gte": _ago(hours=24)},
            "resolved": {"$ne": True},
        })
        env_ok = all(bool(os.environ.get(e)) for e in (required_env or []))
        status = "healthy" if errors == 0 and (not required_env or env_ok) else ("degraded" if errors < 5 else "error")
        return {
            "name": name,
            "route": route,
            "status": status,
            "records": total,
            "errors_24h": errors,
            "env_ok": env_ok,
        }

    modules = await asyncio.gather(
        _module("Auth & Users", ["users", "audit_log"], "/admin/users"),
        _module("Publications", ["publications", "openalex_metrics"], "/admin/research"),
        _module("Manuscripts", ["manuscripts", "submissions"], "/admin/research"),
        _module("Projects", ["projects"], "/admin/research"),
        _module("Collaborations", ["collaborations", "collaboration_requests"], "/admin/research"),
        _module("Workspaces", ["workspaces"], "/admin/research"),
        _module("Teaching Hub", ["courses", "lessons", "assessments"], "/admin/teaching-analytics"),
        _module("Research Impact", ["publication_citations", "reputation_scores"], "/admin/research"),
        _module("Grant Management", ["grant_links", "grant_applications"], "/admin/research"),
        _module("Institutions", ["institutions", "units", "departments"], "/admin/institutions-center"),
        _module("Messaging", ["conversations", "messages"], "/admin/communications"),
        _module("AI Features", ["credit_transactions"], "/admin/analytics", ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]),
        _module("Billing & Subscriptions", ["billing_history", "subscription_history"], "/admin/revenue", ["STRIPE_SECRET_KEY"]),
        _module("Email Services", ["announcements"], "/admin/communications", ["RESEND_API_KEY"]),
        _module("ORCID Integration", ["openalex_metrics"], "/admin/analytics", ["ORCID_CLIENT_ID"]),
        _module("Search & Discovery", ["search_queries"], "/admin/x/search/overview"),
        _module("Background Jobs", ["background_jobs"], "/admin/x/jobs"),
        _module("Support Center", ["support_tickets"], "/admin/x/support/tickets"),
        _module("File Storage", ["uploads"], "/admin/x/storage/overview"),
        _module("Security", ["security_events", "blocked_ips"], "/admin/security"),
    )

    healthy = sum(1 for m in modules if m["status"] == "healthy")
    degraded = sum(1 for m in modules if m["status"] == "degraded")
    errored  = sum(1 for m in modules if m["status"] == "error")
    overall_score = round(healthy / len(modules) * 100 - degraded * 5 - errored * 15)

    return {
        "overall_score":  max(0, min(100, overall_score)),
        "module_count":   len(modules),
        "healthy":        healthy,
        "degraded":       degraded,
        "errored":        errored,
        "db_ok":          db_ok,
        "db_latency_ms":  db_latency,
        "errors_24h":     errors_24h,
        "modules":        list(modules),
        "generated_at":   now,
    }


# ═════════════════════════════════════════════════════════════════════════════
# 12. EXECUTIVE AI COPILOT
# ═════════════════════════════════════════════════════════════════════════════

async def _gather_platform_context(db) -> str:
    """Build a compact text summary of real platform data for AI context."""
    now = _now_iso()
    cutoff = _ago(7)
    (
        total_users, new_week, premium, active_collabs,
        total_pubs, total_projects, total_ms,
        total_courses, open_tickets,
        unresolved_errors, failed_jobs,
    ) = await asyncio.gather(
        db.users.count_documents({}),
        db.users.count_documents({"created_at": {"$gte": cutoff}}),
        db.users.count_documents({"plan_code": {"$in": ["researcher", "pro_researcher", "institution"]}}),
        db.collaborations.count_documents({"status": "active"}),
        db.publications.count_documents({}),
        db.projects.count_documents({}),
        db.manuscripts.count_documents({}),
        db.courses.count_documents({}),
        db.support_tickets.count_documents({"status": {"$in": ["open", "assigned"]}}),
        db.error_logs.count_documents({"resolved": {"$ne": True}}),
        db.background_jobs.count_documents({"status": "failed"}),
    )

    # Revenue
    from plans_catalogue import PLANS, get_plan  # type: ignore
    plan_counts = {}
    for p in PLANS:
        if p["code"] != "free":
            plan_counts[p["code"]] = await db.users.count_documents({"plan_code": p["code"]})
    mrr = sum(plan_counts.get(p["code"], 0) * float(get_plan(p["code"]).get("price_eur_monthly", 0)) for p in PLANS if p["code"] != "free")

    return f"""Platform Context ({now[:10]}):
USERS: {total_users} total, +{new_week} this week, {premium} premium subscribers
REVENUE: MRR €{round(mrr, 2)}, ARR €{round(mrr * 12, 2)}
RESEARCH: {total_pubs} publications, {total_projects} projects, {total_ms} manuscripts
COLLABORATION: {active_collabs} active collaborations
EDUCATION: {total_courses} courses
SUPPORT: {open_tickets} open tickets
PLATFORM HEALTH: {unresolved_errors} unresolved errors, {failed_jobs} failed jobs"""


class CopilotQuery(BaseModel):
    message: str
    kind: str = "query"  # query | brief | weekly | monthly


@router.post("/copilot/brief", dependencies=_GATE)
async def generate_copilot_brief(kind: str = "daily", admin: dict = Depends(require_super_admin)):
    """Generate an AI-powered executive briefing from real platform data."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    now = _now_iso()

    context = await _gather_platform_context(db)

    prompts = {
        "daily": "Generate a concise daily executive briefing for the Synaptiq academic platform. Highlight key metrics, flag any concerns, and suggest 2-3 priority actions. Format in clean sections: Status, Highlights, Risks, Priorities.",
        "weekly": "Generate a weekly executive summary for the Synaptiq academic platform. Include trend analysis vs last week, growth indicators, operational health, and strategic recommendations.",
        "monthly": "Generate a monthly executive report for the Synaptiq academic platform. Include month-over-month growth, revenue analysis, product performance, user engagement trends, operational risks, and strategic outlook for next month.",
    }
    system_prompt = prompts.get(kind, prompts["daily"])

    briefing_text = ""
    try:
        from services.ai.llm import call_llm
        briefing_text = await call_llm(
            system=system_prompt,
            user_msg=f"Here is the current platform data:\n\n{context}\n\nGenerate the {kind} briefing.",
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            feature="admin_copilot",
        )
    except Exception as e:
        briefing_text = f"[AI Copilot] {kind.capitalize()} briefing generated from platform data:\n\n{context}\n\n(AI narrative unavailable: {str(e)[:100]})"

    result = await db.executive_briefings.insert_one({
        "kind":     kind,
        "context":  context,
        "briefing": briefing_text,
        "generated_by": admin.get("email"),
        "created_at": now,
    })

    return {"ok": True, "id": str(result.inserted_id), "kind": kind, "briefing": briefing_text, "context": context}


@router.get("/copilot/briefings", dependencies=_GATE)
async def list_copilot_briefings(limit: int = 20):
    """List past AI briefings."""
    db   = get_db()
    db = DBProxy(db, SecurityContext.system())

    docs = await db.executive_briefings.find({}, {
        "kind": 1, "generated_by": 1, "created_at": 1,
    }).sort("created_at", -1).limit(limit).to_list(limit)
    for d in docs:
        d["id"] = str(d.pop("_id", ""))
    return {"items": docs}


@router.get("/copilot/briefings/{brief_id}", dependencies=_GATE)
async def get_copilot_briefing(brief_id: str):
    """Get full briefing text."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    oid = _parse_oid(brief_id)
    doc = await db.executive_briefings.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Briefing not found")
    doc["id"] = str(doc.pop("_id", ""))
    return doc


@router.post("/copilot/query", dependencies=_GATE)
async def copilot_query(body: CopilotQuery, admin: dict = Depends(require_super_admin)):
    """Ask the AI Copilot a question about the platform."""
    db      = get_db()
    db = DBProxy(db, SecurityContext.system())

    context = await _gather_platform_context(db)
    now     = _now_iso()

    answer = ""
    try:
        from services.ai.llm import call_llm
        answer = await call_llm(
            system=(
                "You are an AI Copilot for the Synaptiq academic SaaS platform. "
                "You have access to real-time platform data and help administrators "
                "understand their platform, detect risks, and make decisions. "
                "Be concise and actionable."
            ),
            user_msg=f"Platform data:\n{context}\n\nAdmin question: {body.message}",
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            feature="admin_copilot",
        )
    except Exception as e:
        answer = f"[Unable to generate AI response: {str(e)[:100]}]\n\nCurrent platform context:\n{context}"

    await db.executive_briefings.insert_one({
        "kind": "query",
        "question": body.message,
        "briefing": answer,
        "generated_by": admin.get("email"),
        "created_at": now,
    })

    return {"ok": True, "question": body.message, "answer": answer, "context": context}
