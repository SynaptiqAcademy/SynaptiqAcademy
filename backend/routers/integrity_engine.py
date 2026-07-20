"""
Academic Integrity & Research Verification Engine — REST API
18 endpoints at /api/integrity
"""
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from worker import enqueue_job
from worker.models import Job, Priority
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from db import get_db
from services.integrity.engine import (
    run_integrity_analysis, get_report, get_job_status,
)
from services.integrity.providers import (
    get_all_provider_status, get_provider, PROVIDER_REGISTRY,
)
from zt.deps import zt_check, zt_is_admin, zt_is_super_admin
from repo.shim import make_db_proxy

router       = APIRouter(prefix="/api/integrity", tags=["integrity"])
admin_router = APIRouter(prefix="/api/admin/integrity", tags=["integrity-admin"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _uid(user: dict) -> str:
    return str(user.get("_id") or user.get("id", ""))


def _require_admin(user: dict):
    zt_check(user, "admin", "admin")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Pydantic ──────────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    force_refresh: bool = False


class ProviderVerifyRequest(BaseModel):
    provider: str
    entity_type: str = "publication"
    payload: dict = Field(default_factory=dict)


# ── User endpoints ────────────────────────────────────────────────────────────

@router.post("/analyze")
async def trigger_analysis(
    body: AnalyzeRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Trigger background integrity analysis. Returns immediately with job status."""
    db = make_db_proxy(db, user)
    uid = _uid(user)

    # Check if already running
    job_status = await get_job_status(uid, db)
    if job_status.get("status") == "running" and not body.force_refresh:
        return {"status": "running", "message": "Analysis already in progress", "job": job_status}

    # Mark as pending immediately
    await db.integrity_jobs.update_one(
        {"user_id": uid},
        {"$set": {"user_id": uid, "status": "pending", "queued_at": _now()}},
        upsert=True,
    )

    worker_job = Job(
        job_type="integrity.analysis",
        payload={"user_id": uid},
        user_id=uid,
        priority=Priority.NORMAL,
    )
    await enqueue_job(worker_job, db)
    return {
        "status": "pending",
        "message": "Integrity analysis queued. Check /api/integrity/status for progress.",
        "user_id": uid,
    }


@router.post("/analyze/sync")
async def trigger_analysis_sync(
    body: AnalyzeRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Run integrity analysis synchronously and return full report. Slower but immediate."""
    db = make_db_proxy(db, user)
    uid = _uid(user)
    try:
        report = await run_integrity_analysis(uid, db)
        return report
    except Exception as exc:
        raise HTTPException(500, f"Analysis failed: {exc}")


@router.get("/status")
async def get_analysis_status(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    uid = _uid(user)
    return await get_job_status(uid, db)


@router.get("/report")
async def get_integrity_report(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    uid = _uid(user)
    report = await get_report(uid, db)
    if not report:
        job = await get_job_status(uid, db)
        if job.get("status") in ("pending", "running"):
            return {"status": job["status"], "message": "Analysis in progress"}
        return {"status": "not_started", "message": "No integrity report found. Trigger /api/integrity/analyze first."}
    return report


@router.get("/score")
async def get_integrity_score(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    uid = _uid(user)
    report = await get_report(uid, db)
    if not report:
        raise HTTPException(404, "No integrity report. Run /api/integrity/analyze first.")
    return {
        "integrity_score": report.get("integrity_score"),
        "grade": report.get("grade"),
        "score_factors": report.get("score_factors"),
        "score_contributions": report.get("score_contributions"),
        "generated_at": report.get("generated_at"),
    }


@router.get("/risks")
async def get_risk_flags(
    level: Optional[str] = Query(None, description="Filter by level: low, medium, high, critical"),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    uid = _uid(user)
    report = await get_report(uid, db)
    if not report:
        raise HTTPException(404, "No integrity report.")
    flags = report.get("risk_flags", [])
    if level:
        flags = [f for f in flags if f.get("level") == level]
    return {"total": len(flags), "flags": flags}


@router.get("/identity")
async def get_identity_analysis(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    uid = _uid(user)
    report = await get_report(uid, db)
    if not report:
        raise HTTPException(404, "No integrity report.")
    return report.get("identity", {})


@router.get("/publications")
async def get_publication_analysis(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    uid = _uid(user)
    report = await get_report(uid, db)
    if not report:
        raise HTTPException(404, "No integrity report.")
    return report.get("publications", {})


@router.get("/citations")
async def get_citation_analysis(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    uid = _uid(user)
    report = await get_report(uid, db)
    if not report:
        raise HTTPException(404, "No integrity report.")
    return report.get("citations", {})


@router.get("/grants")
async def get_grant_analysis(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    uid = _uid(user)
    report = await get_report(uid, db)
    if not report:
        raise HTTPException(404, "No integrity report.")
    return report.get("grants", {})


@router.post("/providers/verify")
async def verify_with_provider(
    body: ProviderVerifyRequest,
    user: dict = Depends(get_current_user),
):
    """Direct provider verification — useful for testing a specific DOI or ORCID."""
    prov = get_provider(body.provider)
    if not prov:
        raise HTTPException(404, f"Unknown provider: {body.provider}. "
                            f"Available: {list(PROVIDER_REGISTRY.keys())}")
    result = await prov.verify(body.entity_type, body.payload)
    return result


@router.get("/providers")
async def list_providers(user: dict = Depends(get_current_user)):
    """List all registered external providers and their availability."""
    statuses = await get_all_provider_status()
    return {"providers": statuses, "total": len(statuses)}


# ── Admin endpoints ───────────────────────────────────────────────────────────

@admin_router.get("/stats")
async def admin_integrity_stats(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    total_reports    = await db.integrity_reports.count_documents({})
    pending_jobs     = await db.integrity_jobs.count_documents({"status": {"$in": ["pending", "running"]}})
    complete_jobs    = await db.integrity_jobs.count_documents({"status": "complete"})
    error_jobs       = await db.integrity_jobs.count_documents({"status": "error"})
    critical_reports = await db.integrity_reports.count_documents({"critical_risks": {"$gt": 0}})
    high_reports     = await db.integrity_reports.count_documents({"high_risks": {"$gt": 0}})

    # Score distribution
    pipeline = [
        {"$match": {"status": "complete", "integrity_score": {"$exists": True}}},
        {"$group": {"_id": None,
                    "avg_score": {"$avg": "$integrity_score"},
                    "min_score": {"$min": "$integrity_score"},
                    "max_score": {"$max": "$integrity_score"}}},
    ]
    agg = await db.integrity_reports.aggregate(pipeline).to_list(length=1)
    score_stats = agg[0] if agg else {"avg_score": 0, "min_score": 0, "max_score": 0}
    score_stats.pop("_id", None)

    providers = await get_all_provider_status()

    return {
        "total_reports":    total_reports,
        "pending_jobs":     pending_jobs,
        "complete_jobs":    complete_jobs,
        "error_jobs":       error_jobs,
        "critical_reports": critical_reports,
        "high_risk_reports": high_reports,
        "score_stats":      score_stats,
        "providers":        providers,
    }


@admin_router.get("/reports")
async def admin_list_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, le=100),
    grade: Optional[str] = Query(None),
    has_critical: Optional[bool] = Query(None),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    filt: dict = {"status": "complete"}
    if grade:
        filt["grade"] = grade
    if has_critical is not None:
        filt["critical_risks"] = {"$gt": 0} if has_critical else 0

    total = await db.integrity_reports.count_documents(filt)
    cursor = (db.integrity_reports.find(filt, {
        "user_id": 1, "integrity_score": 1, "grade": 1,
        "risk_count": 1, "critical_risks": 1, "high_risks": 1,
        "generated_at": 1,
    }).skip(skip).limit(limit).sort("integrity_score", 1))
    docs = await cursor.to_list(length=limit)
    for d in docs:
        d.pop("_id", None)
    return {"total": total, "reports": docs, "skip": skip, "limit": limit}


@admin_router.get("/reports/{target_user_id}")
async def admin_get_user_report(
    target_user_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    report = await get_report(target_user_id, db)
    if not report:
        raise HTTPException(404, "No integrity report for this user.")
    return report


@admin_router.post("/analyze/{target_user_id}")
async def admin_trigger_user_analysis(
    target_user_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    await db.integrity_jobs.update_one(
        {"user_id": target_user_id},
        {"$set": {"user_id": target_user_id, "status": "pending",
                  "queued_at": _now(), "triggered_by_admin": _uid(user)}},
        upsert=True,
    )
    worker_job = Job(
        job_type="integrity.analysis",
        payload={"user_id": target_user_id},
        user_id=target_user_id,
        priority=Priority.HIGH,
    )
    await enqueue_job(worker_job, db)
    return {"status": "pending", "target_user_id": target_user_id}


@admin_router.get("/jobs")
async def admin_list_jobs(
    status: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    filt: dict = {}
    if status:
        filt["status"] = status
    total = await db.integrity_jobs.count_documents(filt)
    docs = await db.integrity_jobs.find(filt).skip(skip).limit(limit).sort("queued_at", -1).to_list(length=limit)
    for d in docs:
        d.pop("_id", None)
    return {"total": total, "jobs": docs}


@admin_router.get("/providers")
async def admin_provider_status(user: dict = Depends(get_current_user)):
    _require_admin(user)
    return {"providers": await get_all_provider_status()}
