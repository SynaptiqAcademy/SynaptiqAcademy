from __future__ import annotations
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from auth_utils import get_current_user
from db import get_db
from zt.deps import zt_check, zt_is_admin, zt_is_super_admin
from repo.shim import make_db_proxy

logger = logging.getLogger("synaptiq")
router = APIRouter(prefix="/api/institution-analytics", tags=["institution-analytics-center"])


def _s(v):
    return str(v) if v is not None else None


async def _require_member_or_admin(institution_id: str, user: dict, db) -> bool:
    if zt_is_admin(user):
        return True
    mem = await db.institution_memberships.find_one({
        "institution_id": institution_id, "user_id": user["id"], "status": "active"
    })
    if not mem:
        raise HTTPException(status_code=403, detail="Must be an active member of this institution")
    return True


async def _require_inst_admin(institution_id: str, user: dict, db):
    if zt_is_admin(user):
        return
    mem = await db.institution_memberships.find_one({
        "institution_id": institution_id, "user_id": user["id"],
        "role": {"$in": ["owner", "admin"]}, "status": "active"
    })
    if not mem:
        raise HTTPException(status_code=403, detail="Institution admin access required")


# ---------------------------------------------------------------------------
# Static routes MUST be registered before /{institution_id}/... routes
# ---------------------------------------------------------------------------

# --- Platform Benchmarks (public) ---
@router.get("/platform/benchmarks")
async def get_platform_benchmarks(db=Depends(get_db)):
    """Public global benchmark statistics."""
    db = make_db_proxy(db, system=True)
    try:
        from services.institution_analytics import benchmarking_engine
    except ImportError:
        raise HTTPException(status_code=503, detail="Benchmarking engine unavailable")
    result = await benchmarking_engine.get_global_benchmarks(db)
    return result


# --- Leaderboards (public) ---
@router.get("/leaderboards")
async def get_institution_leaderboards(db=Depends(get_db)):
    """Public institution leaderboard ranked by IIS score."""
    db = make_db_proxy(db, system=True)
    cursor = db.institution_impact.find({}).sort("iis_total", -1).limit(50)
    docs = await cursor.to_list(length=50)
    results = []
    for doc in docs:
        inst_id = doc.get("institution_id")
        inst = None
        if inst_id:
            inst = await db.institutions.find_one({"_id": ObjectId(inst_id)} if ObjectId.is_valid(inst_id) else {"id": inst_id})
        results.append({
            "institution_id": inst_id,
            "name": inst.get("name") if inst else None,
            "country": inst.get("country") if inst else None,
            "type": inst.get("type") if inst else None,
            "iis_total": doc.get("iis_total"),
            "iis_breakdown": doc.get("iis_breakdown"),
            "_id": _s(doc.get("_id")),
        })
    return results


# --- Admin Overview (platform admin) ---
@router.get("/admin/overview")
async def get_admin_overview(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    """Platform admin overview of institution analytics."""
    db = make_db_proxy(db, user)
    zt_check(user, "admin", "admin")

    total_institutions = await db.institutions.count_documents({})
    total_with_analytics = await db.institution_impact.count_documents({})

    # Compute avg KPIs from kpi snapshots
    pipeline = [
        {"$group": {
            "_id": None,
            "avg_publications": {"$avg": "$kpis.total_publications"},
            "avg_citations": {"$avg": "$kpis.total_citations"},
            "avg_grants": {"$avg": "$kpis.total_grants"},
            "avg_h_index": {"$avg": "$kpis.avg_h_index"},
        }}
    ]
    agg = await db.institution_kpi_snapshots.aggregate(pipeline).to_list(length=1)
    avg_kpis = agg[0] if agg else {}
    avg_kpis.pop("_id", None)

    # Top 5 performers by IIS
    top_cursor = db.institution_impact.find({}).sort("iis_total", -1).limit(5)
    top_docs = await top_cursor.to_list(length=5)
    top_performers = []
    for doc in top_docs:
        inst_id = doc.get("institution_id")
        inst = None
        if inst_id:
            inst = await db.institutions.find_one({"_id": ObjectId(inst_id)} if ObjectId.is_valid(inst_id) else {"id": inst_id})
        top_performers.append({
            "institution_id": inst_id,
            "name": inst.get("name") if inst else None,
            "iis_total": doc.get("iis_total"),
        })

    return {
        "total_institutions": total_institutions,
        "total_with_analytics": total_with_analytics,
        "avg_kpis": avg_kpis,
        "top_performers": top_performers,
    }


# ---------------------------------------------------------------------------
# KPI Endpoints
# ---------------------------------------------------------------------------

@router.get("/{institution_id}/kpis")
async def get_institution_kpis(
    institution_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    await _require_member_or_admin(institution_id, user, db)
    try:
        from services.institution_analytics import kpi_engine
    except ImportError:
        raise HTTPException(status_code=503, detail="KPI engine unavailable")
    result = await kpi_engine.get_institution_kpis(institution_id, db)
    return result


@router.post("/{institution_id}/kpis/refresh")
async def refresh_institution_kpis(
    institution_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    await _require_inst_admin(institution_id, user, db)
    try:
        from services.institution_analytics import kpi_engine
    except ImportError:
        raise HTTPException(status_code=503, detail="KPI engine unavailable")
    result = await kpi_engine.compute_institution_kpis(institution_id, db)
    return result


@router.get("/{institution_id}/kpis/history")
async def get_kpi_history(
    institution_id: str,
    months: int = Query(12, ge=1, le=120),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    await _require_member_or_admin(institution_id, user, db)
    try:
        from services.institution_analytics import kpi_engine
    except ImportError:
        raise HTTPException(status_code=503, detail="KPI engine unavailable")
    result = await kpi_engine.get_kpi_history(institution_id, months, db)
    return result


# ---------------------------------------------------------------------------
# Performance Endpoints
# ---------------------------------------------------------------------------

@router.get("/{institution_id}/performance")
async def get_research_performance(
    institution_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    await _require_member_or_admin(institution_id, user, db)
    try:
        from services.institution_analytics import performance_engine
    except ImportError:
        raise HTTPException(status_code=503, detail="Performance engine unavailable")
    result = await performance_engine.get_research_performance(institution_id, db)
    return result


@router.get("/{institution_id}/performance/trends")
async def get_publication_trends(
    institution_id: str,
    years: int = Query(5, ge=1, le=20),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    await _require_member_or_admin(institution_id, user, db)
    try:
        from services.institution_analytics import performance_engine
    except ImportError:
        raise HTTPException(status_code=503, detail="Performance engine unavailable")
    result = await performance_engine.get_publication_trends(institution_id, years, db)
    return result


# ---------------------------------------------------------------------------
# Researcher Endpoints
# ---------------------------------------------------------------------------

@router.get("/{institution_id}/researchers/top")
async def get_top_researchers(
    institution_id: str,
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    await _require_member_or_admin(institution_id, user, db)
    try:
        from services.institution_analytics import researcher_engine
    except ImportError:
        raise HTTPException(status_code=503, detail="Researcher engine unavailable")
    result = await researcher_engine.get_top_researchers(institution_id, limit, db)
    return result


@router.get("/{institution_id}/researchers/fastest-growing")
async def get_fastest_growing_researchers(
    institution_id: str,
    limit: int = Query(10, ge=1, le=50),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    await _require_member_or_admin(institution_id, user, db)
    try:
        from services.institution_analytics import researcher_engine
    except ImportError:
        raise HTTPException(status_code=503, detail="Researcher engine unavailable")
    result = await researcher_engine.get_fastest_growing_researchers(institution_id, limit, db)
    return result


@router.get("/{institution_id}/researchers/collaborative")
async def get_most_collaborative_researchers(
    institution_id: str,
    limit: int = Query(10, ge=1, le=50),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    await _require_member_or_admin(institution_id, user, db)
    try:
        from services.institution_analytics import researcher_engine
    except ImportError:
        raise HTTPException(status_code=503, detail="Researcher engine unavailable")
    result = await researcher_engine.get_most_collaborative_researchers(institution_id, limit, db)
    return result


@router.get("/{institution_id}/researchers/trajectories")
async def get_researcher_trajectories(
    institution_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    await _require_member_or_admin(institution_id, user, db)
    try:
        from services.institution_analytics import researcher_engine
    except ImportError:
        raise HTTPException(status_code=503, detail="Researcher engine unavailable")
    result = await researcher_engine.get_researcher_trajectories(institution_id, db)
    return result


# ---------------------------------------------------------------------------
# Department Endpoints
# ---------------------------------------------------------------------------

@router.get("/{institution_id}/departments")
async def get_department_analytics(
    institution_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    await _require_member_or_admin(institution_id, user, db)
    try:
        from services.institution_analytics import department_engine
    except ImportError:
        raise HTTPException(status_code=503, detail="Department engine unavailable")
    result = await department_engine.get_department_analytics(institution_id, db)
    return result


@router.get("/{institution_id}/departments/compare")
async def compare_departments(
    institution_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    await _require_member_or_admin(institution_id, user, db)
    try:
        from services.institution_analytics import department_engine
    except ImportError:
        raise HTTPException(status_code=503, detail="Department engine unavailable")
    result = await department_engine.compare_departments(institution_id, db)
    return result


# ---------------------------------------------------------------------------
# Grant Endpoints
# ---------------------------------------------------------------------------

@router.get("/{institution_id}/grants/performance")
async def get_grant_performance(
    institution_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    await _require_member_or_admin(institution_id, user, db)
    try:
        from services.institution_analytics import grant_engine
    except ImportError:
        raise HTTPException(status_code=503, detail="Grant engine unavailable")
    result = await grant_engine.get_grant_performance(institution_id, db)
    return result


@router.get("/{institution_id}/grants/trends")
async def get_funding_trends(
    institution_id: str,
    years: int = Query(5, ge=1, le=20),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    await _require_member_or_admin(institution_id, user, db)
    try:
        from services.institution_analytics import grant_engine
    except ImportError:
        raise HTTPException(status_code=503, detail="Grant engine unavailable")
    result = await grant_engine.get_funding_trends(institution_id, years, db)
    return result


# ---------------------------------------------------------------------------
# Benchmarking Endpoints
# ---------------------------------------------------------------------------

@router.get("/{institution_id}/benchmarks")
async def benchmark_institution(
    institution_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    await _require_member_or_admin(institution_id, user, db)
    try:
        from services.institution_analytics import benchmarking_engine
    except ImportError:
        raise HTTPException(status_code=503, detail="Benchmarking engine unavailable")
    result = await benchmarking_engine.benchmark_institution(institution_id, db)
    return result


# ---------------------------------------------------------------------------
# Forecasting Endpoints
# ---------------------------------------------------------------------------

@router.get("/{institution_id}/forecasts")
async def get_institution_forecasts(
    institution_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    await _require_member_or_admin(institution_id, user, db)
    try:
        from services.institution_analytics import forecasting_engine
    except ImportError:
        raise HTTPException(status_code=503, detail="Forecasting engine unavailable")
    result = await forecasting_engine.get_latest_forecasts(institution_id, db)
    if result is None:
        result = await forecasting_engine.generate_forecasts(institution_id, db)
    return result


@router.post("/{institution_id}/forecasts/generate")
async def generate_institution_forecasts(
    institution_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    await _require_inst_admin(institution_id, user, db)
    try:
        from services.institution_analytics import forecasting_engine
    except ImportError:
        raise HTTPException(status_code=503, detail="Forecasting engine unavailable")
    result = await forecasting_engine.generate_forecasts(institution_id, db)
    return result


# ---------------------------------------------------------------------------
# Report Endpoints
# ---------------------------------------------------------------------------

class ReportGenerateRequest(BaseModel):
    report_type: str  # executive / research / funding / accreditation
    title: str = ""


@router.get("/{institution_id}/reports")
async def list_institution_reports(
    institution_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    await _require_member_or_admin(institution_id, user, db)
    cursor = db.institution_reports.find(
        {"institution_id": institution_id}
    ).sort("created_at", -1).limit(20)
    docs = await cursor.to_list(length=20)
    for doc in docs:
        doc["_id"] = _s(doc.get("_id"))
    return docs


@router.post("/{institution_id}/reports/generate")
async def generate_institution_report(
    institution_id: str,
    body: ReportGenerateRequest,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    await _require_inst_admin(institution_id, user, db)

    # Gather KPIs, performance, grants data in parallel
    try:
        from services.institution_analytics import kpi_engine, performance_engine, grant_engine
        kpis, performance_summary, grant_summary = await asyncio.gather(
            kpi_engine.get_institution_kpis(institution_id, db),
            performance_engine.get_research_performance(institution_id, db),
            grant_engine.get_grant_performance(institution_id, db),
            return_exceptions=True,
        )
        # Replace exceptions with None so the report still saves
        if isinstance(kpis, Exception):
            kpis = None
        if isinstance(performance_summary, Exception):
            performance_summary = None
        if isinstance(grant_summary, Exception):
            grant_summary = None
    except ImportError:
        kpis = performance_summary = grant_summary = None

    now = datetime.now(timezone.utc)
    report_doc = {
        "institution_id": institution_id,
        "report_type": body.report_type,
        "title": body.title or f"{body.report_type.capitalize()} Report",
        "status": "ready",
        "data": {
            "kpis": kpis,
            "performance_summary": performance_summary,
            "grant_summary": grant_summary,
        },
        "created_by": user["id"],
        "created_at": now,
    }
    result = await db.institution_reports.insert_one(report_doc)
    report_doc["_id"] = _s(result.inserted_id)
    return report_doc


# ---------------------------------------------------------------------------
# Collaboration Analytics Endpoint
# ---------------------------------------------------------------------------

@router.get("/{institution_id}/collaborations/analytics")
async def get_collaboration_analytics(
    institution_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    await _require_member_or_admin(institution_id, user, db)

    # Fetch member IDs
    member_cursor = db.institution_memberships.find(
        {"institution_id": institution_id, "status": "active"},
        {"user_id": 1}
    )
    members = await member_cursor.to_list(length=10000)
    member_ids = [m["user_id"] for m in members]

    # Query collaborations where created_by or participants contains any member_id
    collab_cursor = db.collaborations.find({
        "$or": [
            {"created_by": {"$in": member_ids}},
            {"participants": {"$in": member_ids}},
        ]
    })
    collabs = await collab_cursor.to_list(length=10000)

    total = len(collabs)
    by_status: dict = {}
    international_count = 0
    internal_count = 0
    partner_institutions: set = set()

    for collab in collabs:
        status = collab.get("status", "unknown")
        by_status[status] = by_status.get(status, 0) + 1

        participants = collab.get("participants", [])
        # Determine if any participant is outside the institution
        outside = [p for p in participants if p not in member_ids]
        if outside:
            international_count += 1
            # Try to find partner institution memberships
            partner_cursor = db.institution_memberships.find(
                {"user_id": {"$in": outside}, "status": "active"},
                {"institution_id": 1}
            )
            partner_mems = await partner_cursor.to_list(length=1000)
            for pm in partner_mems:
                pid = pm.get("institution_id")
                if pid and pid != institution_id:
                    partner_institutions.add(pid)
        else:
            internal_count += 1

    return {
        "total": total,
        "by_status": by_status,
        "international_count": international_count,
        "internal_count": internal_count,
        "unique_partners": len(partner_institutions),
    }


# ---------------------------------------------------------------------------
# Snapshot Endpoint
# ---------------------------------------------------------------------------

@router.get("/{institution_id}/snapshot")
async def get_institution_snapshot(
    institution_id: str,
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    await _require_member_or_admin(institution_id, user, db)

    try:
        from services.institution_analytics import (
            kpi_engine,
            performance_engine,
            benchmarking_engine,
            forecasting_engine,
        )
        kpis, performance, benchmarks, forecasts = await asyncio.gather(
            kpi_engine.get_institution_kpis(institution_id, db),
            performance_engine.get_research_performance(institution_id, db),
            benchmarking_engine.benchmark_institution(institution_id, db),
            forecasting_engine.get_latest_forecasts(institution_id, db),
            return_exceptions=True,
        )
        if isinstance(kpis, Exception):
            kpis = None
        if isinstance(performance, Exception):
            performance = None
        if isinstance(benchmarks, Exception):
            benchmarks = None
        if isinstance(forecasts, Exception):
            forecasts = None
    except ImportError:
        kpis = performance = benchmarks = forecasts = None

    return {
        "institution_id": institution_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "kpis": kpis,
        "performance": performance,
        "benchmarks": benchmarks,
        "forecasts": forecasts,
    }
