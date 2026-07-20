"""
Institution Intelligence Platform — REST API
36 endpoints at /api/iip (user/institution) and /api/admin/iip (super_admin)

Security model:
  - admin/super_admin: full access
  - super_admin: can query any institution via ?institution= param
  - admin: scoped to their own institution field
"""
from typing import Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from db import get_db
from repo.shim import make_db_proxy

from services.iip.health_engine       import compute_health_score, get_health_history
from services.iip.faculty_engine       import (
    get_faculty_overview, get_faculty_list,
    get_top_performers, get_at_risk_researchers, get_promotion_candidates,
)
from services.iip.department_engine    import get_department_overview, get_department_detail
from services.iip.publication_engine   import get_publication_overview, get_publication_trends
from services.iip.grant_engine         import get_grant_overview, get_grant_pipeline
from services.iip.collaboration_engine import get_collaboration_overview, get_collaboration_network
from services.iip.financial_engine     import get_financial_overview, get_financial_by_department
from services.iip.risk_engine          import detect_institutional_risks
from services.iip.forecast_engine      import (
    get_publication_forecast, get_grant_forecast,
    get_faculty_growth_forecast, get_citation_forecast,
)
from services.iip.benchmark_engine     import (
    get_benchmark_overview, get_historical_benchmark, get_department_benchmark,
)
from services.iip.executive_assistant  import ask_assistant, get_conversation_history
from services.iip.report_engine        import generate_report, export_to_csv, export_to_json, list_reports
from zt.deps import zt_check, zt_is_admin, zt_is_super_admin

router       = APIRouter(prefix="/api/iip", tags=["institution-platform"])
admin_router = APIRouter(prefix="/api/admin/iip", tags=["institution-platform-admin"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _uid(user: dict) -> str:
    return str(user.get("_id") or user.get("id", ""))


def _require_admin(user: dict):
    zt_check(user, "admin", "admin")


def _get_institution(user: dict, institution: Optional[str]) -> str:
    if zt_is_super_admin(user) and institution:
        return institution
    return user.get("institution") or institution or ""


def _require_institution(institution: str):
    if not institution:
        raise HTTPException(400, "Institution not specified. Add your institution to your profile or pass ?institution= param.")


# ── Pydantic ──────────────────────────────────────────────────────────────────

class AssistantQuery(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000)

class ReportRequest(BaseModel):
    report_type: str = "executive_summary"

class IIPSettings(BaseModel):
    benchmark_mode: str = "anonymous"
    report_schedule: str = "monthly"
    alert_threshold: float = 50.0
    enabled_modules: list[str] = Field(default_factory=list)


# ── Executive Dashboard ───────────────────────────────────────────────────────

@router.get("/executive/overview")
async def executive_overview(
    institution: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    inst = _get_institution(user, institution)
    _require_institution(inst)
    import asyncio
    health, pubs, grants, faculty, risks, collab, financial = await asyncio.gather(
        compute_health_score(inst, db),
        get_publication_overview(inst, db),
        get_grant_overview(inst, db),
        get_faculty_overview(inst, db),
        detect_institutional_risks(inst, db),
        get_collaboration_overview(inst, db),
        get_financial_overview(inst, db),
    )
    return {
        "institution": inst,
        "health": {"score": health["score"], "grade": health["grade"], "faculty_count": health["faculty_count"]},
        "publications": {
            "total": pubs["total"],
            "q1q2_pct": pubs["q1q2_pct"],
            "growth_rate_pct": pubs["growth_rate_pct"],
            "avg_citations": pubs["avg_citations"],
        },
        "grants": {
            "total": grants["total"],
            "approved": grants["approved"],
            "success_rate": grants["success_rate"],
            "total_funding": grants["total_funding"],
        },
        "faculty": {
            "total": faculty["total"],
            "active": faculty["active"],
            "engagement_rate": faculty["engagement_rate"],
        },
        "collaboration": {
            "total": collab["total"],
            "international_pct": collab["international_pct"],
        },
        "financial": {
            "total_research_income": financial["total_research_income"],
            "income_growth_pct": financial["income_growth_pct"],
        },
        "risks": {
            "total": len(risks),
            "critical": sum(1 for r in risks if r["level"] == "critical"),
            "high": sum(1 for r in risks if r["level"] == "high"),
            "top_risk": risks[0]["title"] if risks else None,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health/score")
async def health_score(
    institution: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    inst = _get_institution(user, institution)
    _require_institution(inst)
    return await compute_health_score(inst, db)


@router.get("/health/history")
async def health_history(
    institution: Optional[str] = Query(None),
    days: int = Query(180, ge=7, le=730),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    inst = _get_institution(user, institution)
    _require_institution(inst)
    return await get_health_history(inst, days, db)


# ── Faculty ───────────────────────────────────────────────────────────────────

@router.get("/faculty/overview")
async def faculty_overview(
    institution: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    inst = _get_institution(user, institution)
    _require_institution(inst)
    return await get_faculty_overview(inst, db)


@router.get("/faculty/list")
async def faculty_list(
    institution: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    inst = _get_institution(user, institution)
    _require_institution(inst)
    return await get_faculty_list(inst, db, limit=limit, skip=skip)


@router.get("/faculty/top-performers")
async def top_performers(
    institution: Optional[str] = Query(None),
    limit: int = Query(10, le=50),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    inst = _get_institution(user, institution)
    _require_institution(inst)
    return await get_top_performers(inst, db, limit=limit)


@router.get("/faculty/at-risk")
async def at_risk_researchers(
    institution: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    inst = _get_institution(user, institution)
    _require_institution(inst)
    return await get_at_risk_researchers(inst, db)


@router.get("/faculty/promotion-candidates")
async def promotion_candidates(
    institution: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    inst = _get_institution(user, institution)
    _require_institution(inst)
    return await get_promotion_candidates(inst, db)


# ── Departments ───────────────────────────────────────────────────────────────

@router.get("/departments/overview")
async def departments_overview(
    institution: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    inst = _get_institution(user, institution)
    _require_institution(inst)
    return await get_department_overview(inst, db)


@router.get("/departments/{department}")
async def department_detail(
    department: str,
    institution: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    inst = _get_institution(user, institution)
    _require_institution(inst)
    return await get_department_detail(inst, department, db)


# ── Publications ──────────────────────────────────────────────────────────────

@router.get("/publications/overview")
async def publications_overview(
    institution: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    inst = _get_institution(user, institution)
    _require_institution(inst)
    return await get_publication_overview(inst, db)


@router.get("/publications/trends")
async def publication_trends(
    institution: Optional[str] = Query(None),
    years: int = Query(5, ge=2, le=10),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    inst = _get_institution(user, institution)
    _require_institution(inst)
    return await get_publication_trends(inst, db, years=years)


# ── Grants ────────────────────────────────────────────────────────────────────

@router.get("/grants/overview")
async def grants_overview(
    institution: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    inst = _get_institution(user, institution)
    _require_institution(inst)
    return await get_grant_overview(inst, db)


@router.get("/grants/pipeline")
async def grant_pipeline(
    institution: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    inst = _get_institution(user, institution)
    _require_institution(inst)
    return await get_grant_pipeline(inst, db)


# ── Collaborations ────────────────────────────────────────────────────────────

@router.get("/collaborations/overview")
async def collaborations_overview(
    institution: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    inst = _get_institution(user, institution)
    _require_institution(inst)
    return await get_collaboration_overview(inst, db)


@router.get("/collaborations/network")
async def collaboration_network(
    institution: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    inst = _get_institution(user, institution)
    _require_institution(inst)
    return await get_collaboration_network(inst, db)


# ── Financial ─────────────────────────────────────────────────────────────────

@router.get("/financial/overview")
async def financial_overview(
    institution: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    inst = _get_institution(user, institution)
    _require_institution(inst)
    return await get_financial_overview(inst, db)


@router.get("/financial/by-department")
async def financial_by_department(
    institution: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    inst = _get_institution(user, institution)
    _require_institution(inst)
    return await get_financial_by_department(inst, db)


# ── Risks ─────────────────────────────────────────────────────────────────────

@router.get("/risks")
async def institutional_risks(
    institution: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    inst = _get_institution(user, institution)
    _require_institution(inst)
    risks = await detect_institutional_risks(inst, db)
    return {
        "institution": inst,
        "total": len(risks),
        "critical": sum(1 for r in risks if r["level"] == "critical"),
        "high": sum(1 for r in risks if r["level"] == "high"),
        "medium": sum(1 for r in risks if r["level"] == "medium"),
        "low": sum(1 for r in risks if r["level"] == "low"),
        "flags": risks,
    }


# ── Forecasts ─────────────────────────────────────────────────────────────────

@router.get("/forecasts/publications")
async def forecast_publications(
    institution: Optional[str] = Query(None),
    horizon: int = Query(3, ge=1, le=5),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    inst = _get_institution(user, institution)
    _require_institution(inst)
    return await get_publication_forecast(inst, db, horizon_years=horizon)


@router.get("/forecasts/grants")
async def forecast_grants(
    institution: Optional[str] = Query(None),
    horizon: int = Query(3, ge=1, le=5),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    inst = _get_institution(user, institution)
    _require_institution(inst)
    return await get_grant_forecast(inst, db, horizon_years=horizon)


@router.get("/forecasts/faculty")
async def forecast_faculty(
    institution: Optional[str] = Query(None),
    horizon: int = Query(3, ge=1, le=5),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    inst = _get_institution(user, institution)
    _require_institution(inst)
    return await get_faculty_growth_forecast(inst, db, horizon_years=horizon)


@router.get("/forecasts/citations")
async def forecast_citations(
    institution: Optional[str] = Query(None),
    horizon: int = Query(3, ge=1, le=5),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    inst = _get_institution(user, institution)
    _require_institution(inst)
    return await get_citation_forecast(inst, db, horizon_years=horizon)


# ── Benchmarks ────────────────────────────────────────────────────────────────

@router.get("/benchmarks/overview")
async def benchmarks_overview(
    institution: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    inst = _get_institution(user, institution)
    _require_institution(inst)
    return await get_benchmark_overview(inst, db)


@router.get("/benchmarks/history")
async def benchmarks_history(
    institution: Optional[str] = Query(None),
    days: int = Query(180, ge=7, le=730),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    inst = _get_institution(user, institution)
    _require_institution(inst)
    return await get_historical_benchmark(inst, db, days=days)


@router.get("/benchmarks/departments")
async def benchmark_departments(
    institution: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    inst = _get_institution(user, institution)
    _require_institution(inst)
    return await get_department_benchmark(inst, db)


# ── AI Executive Assistant ────────────────────────────────────────────────────

@router.post("/assistant/query")
async def assistant_query(
    body: AssistantQuery,
    institution: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    inst = _get_institution(user, institution)
    _require_institution(inst)
    return await ask_assistant(inst, body.query, db)


@router.get("/assistant/history")
async def assistant_history(
    institution: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    inst = _get_institution(user, institution)
    _require_institution(inst)
    return await get_conversation_history(inst, db, limit=limit)


# ── Reports ───────────────────────────────────────────────────────────────────

@router.post("/reports/generate")
async def generate_executive_report(
    body: ReportRequest,
    institution: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    inst = _get_institution(user, institution)
    _require_institution(inst)
    return await generate_report(inst, body.report_type, db)


@router.get("/reports/list")
async def list_executive_reports(
    institution: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    inst = _get_institution(user, institution)
    _require_institution(inst)
    return await list_reports(inst, db, limit=limit)


@router.get("/reports/download/{fmt}")
async def download_report(
    fmt: str,
    institution: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    inst = _get_institution(user, institution)
    _require_institution(inst)
    if fmt not in ("csv", "json"):
        raise HTTPException(400, "Supported formats: csv, json")
    report = await generate_report(inst, "executive_summary", db)
    if fmt == "csv":
        content = export_to_csv(report)
        return Response(content=content, media_type="text/csv",
                        headers={"Content-Disposition": f"attachment; filename=iip_report_{inst}.csv"})
    return Response(content=export_to_json(report), media_type="application/json",
                    headers={"Content-Disposition": f"attachment; filename=iip_report_{inst}.json"})


# ── Settings ──────────────────────────────────────────────────────────────────

@router.get("/settings")
async def get_settings(
    institution: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    inst = _get_institution(user, institution)
    doc = await db.iip_settings.find_one({"institution": inst})
    if not doc:
        return {"institution": inst, "benchmark_mode": "anonymous", "report_schedule": "monthly",
                "alert_threshold": 50.0, "enabled_modules": []}
    doc.pop("_id", None)
    return doc


@router.put("/settings")
async def update_settings(
    body: IIPSettings,
    institution: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    _require_admin(user)
    inst = _get_institution(user, institution)
    _require_institution(inst)
    await db.iip_settings.update_one(
        {"institution": inst},
        {"$set": {**body.model_dump(), "institution": inst,
                  "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
    return {"institution": inst, "status": "updated", **body.model_dump()}


# ── Admin endpoints ───────────────────────────────────────────────────────────

@admin_router.get("/institutions")
async def list_institutions(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    zt_check(user, "admin", "security")
    # Get all unique institutions from users
    institutions = await db.users.distinct("institution", {"institution": {"$exists": True, "$ne": ""}})
    inst_stats = []
    for inst in institutions[:50]:
        count = await db.users.count_documents({"institution": inst})
        inst_stats.append({"institution": inst, "user_count": count})
    return sorted(inst_stats, key=lambda x: -x["user_count"])


@admin_router.get("/platform-stats")
async def platform_stats(
    user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, user)
    zt_check(user, "admin", "security")
    import asyncio
    total_institutions = len(await db.users.distinct("institution", {"institution": {"$ne": ""}}))
    total_reports = await db.iip_reports.count_documents({})
    total_conversations = await db.iip_ai_conversations.count_documents({})
    total_snapshots = await db.iip_health_snapshots.count_documents({})
    return {
        "total_institutions": total_institutions,
        "total_reports_generated": total_reports,
        "total_assistant_conversations": total_conversations,
        "total_health_snapshots": total_snapshots,
    }
