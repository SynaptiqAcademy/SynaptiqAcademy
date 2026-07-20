"""Institutional Analytics — executive-level research analytics for institution members.

Eight dashboard endpoints:
  executive / research / funding / collaboration (original four)
  doctoral / research-office / benchmark / export (Phase 11 additions)

All endpoints resolve the caller's institution automatically and gate access
behind a paid institution plan.
"""
from __future__ import annotations
import asyncio
import csv
import io
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from bson import ObjectId

from auth_utils import get_current_user
from db import get_db
from services.institutions.analytics import (
    institution_overview,
    publications_breakdown,
    collaboration_breakdown,
    funding_breakdown,
    reputation_top,
    research_health,
    _scoped_user_ids,
    _budget_to_usd,
    _APP_STATUS_MAP,
)
from services.institutions.department_service import (
    assert_institution_plan,
    rank_departments,
)
from repo.shim import DBProxy
from repo.security_context import SecurityContext

router = APIRouter(prefix="/api/institutional/analytics", tags=["institutional-analytics"])


async def _resolve_institution(user: dict) -> str:
    institution_id = user.get("institution_id")
    if not institution_id:
        db = get_db()
        db = DBProxy(db, SecurityContext.from_user(user))

        mem = await db.institution_memberships.find_one(
            {"user_id": user["id"], "status": "approved"}
        )
        if not mem:
            raise HTTPException(
                status_code=403,
                detail="No institutional affiliation found. Join an institution to access analytics.",
            )
        institution_id = mem["institution_id"]
    return institution_id


async def _faculty_productivity(user_ids: list[str]) -> list[dict]:
    if not user_ids:
        return []
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    pub_pipe = [
        {"$match": {"author_ids": {"$in": user_ids}, "status": "published"}},
        {"$unwind": "$author_ids"},
        {"$match": {"author_ids": {"$in": user_ids}}},
        {"$group": {"_id": "$author_ids", "pubs": {"$sum": 1}}},
    ]
    pub_rows, u_docs = await asyncio.gather(
        db.manuscripts.aggregate(pub_pipe).to_list(len(user_ids)),
        db.users.find(
            {"_id": {"$in": [ObjectId(u) for u in user_ids]}},
            {"full_name": 1, "academic_role": 1, "openalex_metrics": 1, "h_index": 1},
        ).to_list(len(user_ids)),
    )
    pub_by_user = {r["_id"]: r["pubs"] for r in pub_rows}
    rows = []
    for u in u_docs:
        uid = str(u["_id"])
        oa = u.get("openalex_metrics") or {}
        rows.append({
            "user_id": uid,
            "name": u.get("full_name"),
            "role": u.get("academic_role"),
            "publications": pub_by_user.get(uid, 0),
            "citations": int(oa.get("citations") or 0),
            "h_index": int(oa.get("h_index") or u.get("h_index") or 0),
        })
    rows.sort(key=lambda x: x["publications"], reverse=True)
    return rows[:20]


async def _research_area_distribution(user_ids: list[str]) -> list[dict]:
    if not user_ids:
        return []
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    users = await db.users.find(
        {"_id": {"$in": [ObjectId(u) for u in user_ids]}},
        {"research_areas": 1},
    ).to_list(len(user_ids))
    counts: dict[str, int] = {}
    for u in users:
        for area in u.get("research_areas") or []:
            if isinstance(area, str) and area.strip():
                key = area.strip()
                counts[key] = counts.get(key, 0) + 1
    return [{"area": a, "n": n} for a, n in sorted(counts.items(), key=lambda x: x[1], reverse=True)[:20]]


async def _citation_trend(user_ids: list[str]) -> list[dict]:
    if not user_ids:
        return []
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    pipe = [
        {"$match": {"author_ids": {"$in": user_ids}, "status": "published", "citations": {"$gt": 0}}},
        {"$project": {
            "year": {"$substr": [{"$ifNull": ["$published_at", "$created_at"]}, 0, 4]},
            "citations": 1,
        }},
        {"$group": {"_id": "$year", "citations": {"$sum": "$citations"}, "papers": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    rows = await db.manuscripts.aggregate(pipe).to_list(50)
    return [{"year": r["_id"], "citations": r["citations"], "papers": r["papers"]} for r in rows if r.get("_id")]


async def _collaboration_trend(user_ids: list[str]) -> list[dict]:
    if not user_ids:
        return []
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    pipe = [
        {"$match": {"author_ids": {"$in": user_ids}}},
        {"$project": {"year": {"$substr": [{"$ifNull": ["$published_at", "$created_at"]}, 0, 4]}}},
        {"$group": {"_id": "$year", "n": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
    ]
    rows = await db.manuscripts.aggregate(pipe).to_list(20)
    return [{"year": r["_id"], "n": r["n"]} for r in rows if r.get("_id")]


async def _institutional_h_index(user_ids: list[str]) -> int:
    if not user_ids:
        return 0
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    u_docs = await db.users.find(
        {"_id": {"$in": [ObjectId(u) for u in user_ids]}},
        {"openalex_metrics": 1, "h_index": 1},
    ).to_list(len(user_ids))
    h_values = [int((u.get("openalex_metrics") or {}).get("h_index") or u.get("h_index") or 0) for u in u_docs]
    return max(h_values) if h_values else 0


# ─── Executive Dashboard ──────────────────────────────────────────────────────

@router.get("/executive")
async def executive_dashboard(user: dict = Depends(get_current_user)):
    institution_id = await _resolve_institution(user)
    await assert_institution_plan(institution_id)

    user_ids = await _scoped_user_ids(institution_id)

    overview, pubs, funding, rep, health, area_dist, inst_h = await asyncio.gather(
        institution_overview(institution_id),
        publications_breakdown(institution_id),
        funding_breakdown(institution_id),
        reputation_top(institution_id, limit=5),
        research_health(institution_id),
        _research_area_distribution(user_ids),
        _institutional_h_index(user_ids),
    )

    by_status = {r["status"]: r for r in funding.get("by_status", [])}
    awarded_n = by_status.get("awarded", {}).get("n", 0)
    total_n = sum(r["n"] for r in funding.get("by_status", []))
    grant_success_rate = round((awarded_n / total_n * 100) if total_n else 0.0, 1)

    return {
        "overview": overview,
        "publication_trend": pubs["by_year"],
        "research_areas": area_dist[:10],
        "department_comparison": pubs["by_unit"][:10],
        "funding_by_department": funding["by_unit"][:10],
        "top_researchers": rep["top_researchers"],
        "impact_score": health,
        "institutional_h_index": inst_h,
        "grant_success_rate": grant_success_rate,
    }


# ─── Research Dashboard ───────────────────────────────────────────────────────

@router.get("/research")
async def research_dashboard(user: dict = Depends(get_current_user)):
    institution_id = await _resolve_institution(user)
    await assert_institution_plan(institution_id)

    user_ids = await _scoped_user_ids(institution_id)

    pubs, area_dist, cit_trend, faculty = await asyncio.gather(
        publications_breakdown(institution_id),
        _research_area_distribution(user_ids),
        _citation_trend(user_ids),
        _faculty_productivity(user_ids),
    )

    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    top_pubs = await db.manuscripts.find(
        {"author_ids": {"$in": user_ids}, "status": "published"},
        {"title": 1, "published_at": 1, "citations": 1, "journal": 1},
    ).sort("citations", -1).limit(10).to_list(10)
    for p in top_pubs:
        p["id"] = str(p.pop("_id"))
        p.setdefault("citations", 0)

    return {
        "publication_trend": pubs["by_year"],
        "by_unit": pubs["by_unit"],
        "research_areas": area_dist,
        "citation_trend": cit_trend,
        "faculty_productivity": faculty,
        "top_publications": top_pubs,
    }


# ─── Funding Dashboard ────────────────────────────────────────────────────────

@router.get("/funding")
async def funding_dashboard(user: dict = Depends(get_current_user)):
    institution_id = await _resolve_institution(user)
    await assert_institution_plan(institution_id)

    user_ids = await _scoped_user_ids(institution_id)

    funding, overview = await asyncio.gather(
        funding_breakdown(institution_id),
        institution_overview(institution_id),
    )

    by_status = {r["status"]: r for r in funding.get("by_status", [])}
    awarded_n = by_status.get("awarded", {}).get("n", 0)
    total_n = sum(r["n"] for r in funding.get("by_status", []))
    success_rate = round((awarded_n / total_n * 100) if total_n else 0.0, 1)

    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    gl_trend, app_trend = await asyncio.gather(
        db.grant_links.aggregate([
            {"$match": {"user_id": {"$in": user_ids}, "status": "awarded"}},
            {"$project": {"year": {"$substr": ["$created_at", 0, 4]}, "amount_usd": 1}},
            {"$group": {"_id": "$year", "total_usd": {"$sum": "$amount_usd"}, "n": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ]).to_list(20),
        db.grant_applications.aggregate([
            {"$match": {"pi_id": {"$in": user_ids}, "status": "funded"}},
            {"$project": {"year": {"$substr": ["$updated_at", 0, 4]},
                          "requested_budget": 1, "currency": 1}},
            {"$group": {"_id": "$year", "n": {"$sum": 1},
                        "budget_eur": {"$sum": "$requested_budget"}}},
            {"$sort": {"_id": 1}},
        ]).to_list(20),
    )

    # Merge both trend sources by year
    trend_by_year: dict[str, dict] = {}
    for r in gl_trend:
        y = r.get("_id") or ""
        if y:
            trend_by_year[y] = {"year": y, "total_usd": int(r.get("total_usd") or 0), "n": r.get("n", 0)}
    for r in app_trend:
        y = r.get("_id") or ""
        if y:
            app_usd = int(_budget_to_usd(r.get("budget_eur") or 0, "EUR"))
            if y in trend_by_year:
                trend_by_year[y]["total_usd"] += app_usd
                trend_by_year[y]["n"] += r.get("n", 0)
            else:
                trend_by_year[y] = {"year": y, "total_usd": app_usd, "n": r.get("n", 0)}
    trend = sorted(trend_by_year.values(), key=lambda x: x["year"])

    return {
        "summary": {
            "total_usd": funding["total_usd"],
            "awarded_grants": overview["grants"]["awarded"],
            "total_grants": overview["grants"]["total"],
            "grant_success_rate": success_rate,
        },
        "by_status": funding["by_status"],
        "by_department": funding["by_unit"],
        "trend": trend,
    }


# ─── Collaboration Dashboard ──────────────────────────────────────────────────

@router.get("/collaboration")
async def collaboration_dashboard(user: dict = Depends(get_current_user)):
    institution_id = await _resolve_institution(user)
    await assert_institution_plan(institution_id)

    user_ids = await _scoped_user_ids(institution_id)

    collab, trend, faculty = await asyncio.gather(
        collaboration_breakdown(institution_id),
        _collaboration_trend(user_ids),
        _faculty_productivity(user_ids),
    )

    faculty_collab = [
        {"name": f["name"], "publications": f["publications"], "user_id": f["user_id"]}
        for f in faculty
        if f["publications"] > 0
    ][:10]

    return {
        "summary": {
            "internal_collaborations": collab["internal"],
            "external_collaborations": collab["external"],
            "total": collab["internal"] + collab["external"],
        },
        "network": collab["network"][:30],
        "trend": trend,
        "top_collaborators": faculty_collab,
    }


# ─── Doctoral School Dashboard ────────────────────────────────────────────────

_PHD_ROLES = {"phd student", "phd candidate", "doctoral student", "doctoral researcher",
              "doctoral candidate", "graduate student", "grad student", "postgraduate student"}


@router.get("/doctoral")
async def doctoral_dashboard(user: dict = Depends(get_current_user)):
    """PhD student tracking: cohort size, thesis progress, completion rate, supervisors."""
    institution_id = await _resolve_institution(user)
    await assert_institution_plan(institution_id)

    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    user_ids = await _scoped_user_ids(institution_id)
    if not user_ids:
        return _empty_doctoral()

    # Identify PhD students by academic_role (case-insensitive)
    all_users = await db.users.find(
        {"_id": {"$in": [ObjectId(u) for u in user_ids]}},
        {"full_name": 1, "academic_role": 1, "avatar_url": 1, "research_areas": 1,
         "openalex_metrics": 1, "h_index": 1},
    ).to_list(len(user_ids))

    phd_users = [u for u in all_users
                 if (u.get("academic_role") or "").lower() in _PHD_ROLES
                 or "phd" in (u.get("academic_role") or "").lower()
                 or "doctoral" in (u.get("academic_role") or "").lower()]

    phd_ids = [str(u["_id"]) for u in phd_users]

    if not phd_ids:
        return {**_empty_doctoral(), "total_phd_students": 0}

    # Manuscript tracking (thesis proxies — in-progress = active, published = completed)
    ms_active, ms_completed = await asyncio.gather(
        db.manuscripts.count_documents({"author_ids": {"$in": phd_ids}, "status": {"$ne": "published"}}),
        db.manuscripts.count_documents({"author_ids": {"$in": phd_ids}, "status": "published"}),
    )

    # Supervisors: institution members who are NOT PhD students (senior roles)
    _senior_roles = {"professor", "associate professor", "assistant professor",
                     "senior lecturer", "lecturer", "postdoc", "researcher", "senior researcher",
                     "research director", "group leader", "principal investigator"}
    supervisors = [u for u in all_users
                   if str(u["_id"]) not in set(phd_ids)
                   and any(kw in (u.get("academic_role") or "").lower()
                           for kw in ["professor", "lecturer", "postdoc", "researcher", "director", "pi", "principal"])]

    # Co-authorship-based supervisor matching
    supervision_pairs = await db.manuscripts.aggregate([
        {"$match": {"author_ids": {"$in": phd_ids}}},
        {"$project": {"author_ids": 1}},
        {"$unwind": "$author_ids"},
        {"$group": {"_id": {"phd": {"$first": "$author_ids"}, "ms_id": "$_id"},
                    "all_authors": {"$push": "$author_ids"}}},
    ]).to_list(500)

    sup_ids_set = {str(u["_id"]) for u in supervisors}
    pair_counts: dict[str, set] = {}
    for ms in await db.manuscripts.find(
        {"author_ids": {"$in": phd_ids}}, {"author_ids": 1}
    ).to_list(500):
        for pid in ms.get("author_ids", []):
            if pid in set(phd_ids):
                for co in ms.get("author_ids", []):
                    if co in sup_ids_set and co != pid:
                        pair_counts.setdefault(pid, set()).add(co)

    # PhD by department
    mem_rows = await db.institution_memberships.find(
        {"institution_id": institution_id, "status": "approved", "user_id": {"$in": phd_ids}},
        {"user_id": 1, "unit_ids": 1},
    ).to_list(len(phd_ids))
    unit_counts: dict[str, int] = {}
    for m in mem_rows:
        for uid in (m.get("unit_ids") or []):
            unit_counts[uid] = unit_counts.get(uid, 0) + 1
    unit_docs = await db.units.find(
        {"_id": {"$in": [ObjectId(u) for u in unit_counts.keys()]}},
        {"name": 1, "type": 1}
    ).to_list(50) if unit_counts else []
    by_department = sorted(
        [{"department": doc.get("name"), "unit_id": str(doc["_id"]),
          "phd_students": unit_counts.get(str(doc["_id"]), 0)}
         for doc in unit_docs],
        key=lambda x: x["phd_students"], reverse=True
    )

    # Student profiles (top 20)
    name_map = {str(u["_id"]): u.get("full_name") for u in all_users}
    student_profiles = []
    for u in phd_users[:20]:
        uid = str(u["_id"])
        ms_count = await db.manuscripts.count_documents({"author_ids": uid})
        pub_count = await db.manuscripts.count_documents({"author_ids": uid, "status": "published"})
        sups = list(pair_counts.get(uid, set()))
        student_profiles.append({
            "id": uid,
            "name": u.get("full_name"),
            "research_areas": (u.get("research_areas") or [])[:3],
            "manuscripts_active": ms_count - pub_count,
            "manuscripts_published": pub_count,
            "supervisor_names": [name_map.get(s) for s in sups[:3] if name_map.get(s)],
        })

    completion_rate = round(ms_completed / max(1, ms_completed + ms_active) * 100, 1)

    return {
        "total_phd_students": len(phd_ids),
        "total_supervisors": len(supervisors),
        "manuscripts_active": ms_active,
        "manuscripts_completed": ms_completed,
        "completion_rate": completion_rate,
        "by_department": by_department,
        "student_profiles": student_profiles,
        "supervision_coverage": round(
            len([p for p in phd_ids if pair_counts.get(p)]) / max(1, len(phd_ids)) * 100, 1
        ),
    }


def _empty_doctoral() -> dict:
    return {
        "total_phd_students": 0, "total_supervisors": 0,
        "manuscripts_active": 0, "manuscripts_completed": 0,
        "completion_rate": 0.0, "by_department": [],
        "student_profiles": [], "supervision_coverage": 0.0,
    }


# ─── Research Office Dashboard ────────────────────────────────────────────────

@router.get("/research-office")
async def research_office_dashboard(user: dict = Depends(get_current_user)):
    """Grant pipeline view for the Research Office: status breakdown, upcoming deadlines, PI capacity."""
    institution_id = await _resolve_institution(user)
    await assert_institution_plan(institution_id)

    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    user_ids = await _scoped_user_ids(institution_id)
    if not user_ids:
        return _empty_research_office()

    # All grant applications for institution researchers
    apps = await db.grant_applications.find(
        {"pi_id": {"$in": user_ids}},
        {"pi_id": 1, "grant_id": 1, "status": 1, "requested_budget": 1,
         "currency": 1, "created_at": 1, "updated_at": 1, "consortium_name": 1},
    ).to_list(2000)

    # Status pipeline
    status_counts: dict[str, dict] = {}
    for a in apps:
        s = a.get("status") or "draft"
        if s not in status_counts:
            status_counts[s] = {"status": s, "n": 0, "budget_usd": 0}
        status_counts[s]["n"] += 1
        status_counts[s]["budget_usd"] += int(
            _budget_to_usd(a.get("requested_budget") or 0, a.get("currency") or "USD")
        )
    pipeline = sorted(status_counts.values(), key=lambda x: x["n"], reverse=True)

    # Total committed budget (submitted + under_evaluation + funded)
    active_statuses = {"submitted", "eligible", "under_evaluation", "funded"}
    committed_usd = sum(
        int(_budget_to_usd(a.get("requested_budget") or 0, a.get("currency") or "USD"))
        for a in apps if a.get("status") in active_statuses
    )
    funded_usd = sum(
        int(_budget_to_usd(a.get("requested_budget") or 0, a.get("currency") or "USD"))
        for a in apps if a.get("status") == "funded"
    )

    # Upcoming deadlines — look up grant deadlines for active applications
    active_grant_ids = list({a["grant_id"] for a in apps
                              if a.get("status") in {"draft", "in_preparation", "internal_review",
                                                      "ready_for_submission", "submitted"}
                              and a.get("grant_id")})
    from datetime import date
    today_str = date.today().isoformat()
    deadline_grants = await db.grants.find(
        {"_id": {"$in": [ObjectId(gid) for gid in active_grant_ids if len(gid) == 24]},
         "deadline": {"$gte": today_str}},
        {"title": 1, "deadline": 1, "sponsor": 1, "funding_amount": 1},
    ).sort("deadline", 1).limit(10).to_list(10)

    upcoming_deadlines = []
    grant_id_map = {str(g["_id"]): g for g in deadline_grants}
    app_by_grant = {a["grant_id"]: a for a in apps if a.get("grant_id") in grant_id_map}
    for gid, g in grant_id_map.items():
        a = app_by_grant.get(gid)
        upcoming_deadlines.append({
            "grant_id": gid,
            "title": g.get("title"),
            "sponsor": g.get("sponsor"),
            "deadline": g.get("deadline"),
            "application_status": a.get("status") if a else None,
        })

    # PI capacity: count active applications per PI
    pi_load: dict[str, int] = {}
    for a in apps:
        if a.get("status") not in {"closed", "withdrawn", "rejected"}:
            pi_load[a["pi_id"]] = pi_load.get(a["pi_id"], 0) + 1
    active_pi_count = len(pi_load)
    overloaded_pis = [{"pi_id": pid, "active_apps": n}
                      for pid, n in pi_load.items() if n >= 3]

    # Top PIs by total funded
    funded_by_pi: dict[str, float] = {}
    for a in apps:
        if a.get("status") == "funded":
            funded_by_pi[a["pi_id"]] = funded_by_pi.get(a["pi_id"], 0) + _budget_to_usd(
                a.get("requested_budget") or 0, a.get("currency") or "USD"
            )
    top_pi_ids = sorted(funded_by_pi, key=lambda x: funded_by_pi[x], reverse=True)[:5]
    pi_docs = await db.users.find(
        {"_id": {"$in": [ObjectId(p) for p in top_pi_ids if len(p) == 24]}},
        {"full_name": 1}
    ).to_list(5)
    pi_name_map = {str(u["_id"]): u.get("full_name") for u in pi_docs}
    top_pis = [{"pi_id": pid, "name": pi_name_map.get(pid), "funded_usd": int(funded_by_pi[pid])}
               for pid in top_pi_ids]

    return {
        "summary": {
            "total_applications": len(apps),
            "active_pis": active_pi_count,
            "committed_budget_usd": committed_usd,
            "funded_budget_usd": funded_usd,
            "success_rate": round(
                sum(1 for a in apps if a.get("status") == "funded") /
                max(1, sum(1 for a in apps if a.get("status") in
                           {"funded", "rejected", "closed"})) * 100, 1
            ),
        },
        "pipeline": pipeline,
        "upcoming_deadlines": upcoming_deadlines,
        "top_pis": top_pis,
        "overloaded_pis": overloaded_pis[:5],
    }


def _empty_research_office() -> dict:
    return {
        "summary": {"total_applications": 0, "active_pis": 0,
                    "committed_budget_usd": 0, "funded_budget_usd": 0, "success_rate": 0.0},
        "pipeline": [], "upcoming_deadlines": [], "top_pis": [], "overloaded_pis": [],
    }


# ─── Department Benchmarking ──────────────────────────────────────────────────

@router.get("/benchmark")
async def benchmark_dashboard(user: dict = Depends(get_current_user)):
    """Department vs department ranking by composite research score."""
    institution_id = await _resolve_institution(user)
    await assert_institution_plan(institution_id)

    rankings = await rank_departments(institution_id)

    # Build comparison matrix for top metrics
    metrics_keys = ["publications", "total_citations", "grants_awarded", "funding_usd", "avg_reputation"]
    comparison = [
        {
            "department_id": r["department_id"],
            "name": r["name"],
            "rank": r["rank"],
            "score": r["score"],
            "research_areas": r.get("research_areas") or [],
            **{k: r["metrics"].get(k, 0) for k in metrics_keys},
        }
        for r in rankings
    ]

    return {
        "rankings": comparison,
        "total_departments": len(rankings),
        "metrics_used": ["Citations (30%)", "Publications (25%)", "Reputation (20%)",
                          "Funding (15%)", "Projects (10%)"],
    }


# ─── Analytics Export ─────────────────────────────────────────────────────────

@router.get("/export")
async def export_analytics(
    report_type: str = Query("researchers", pattern="^(researchers|publications|funding|departments)$"),
    user: dict = Depends(get_current_user),
):
    """Export institution analytics as CSV. report_type: researchers|publications|funding|departments."""
    institution_id = await _resolve_institution(user)
    await assert_institution_plan(institution_id)

    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    user_ids = await _scoped_user_ids(institution_id)

    output = io.StringIO()
    writer = csv.writer(output)

    if report_type == "researchers":
        writer.writerow(["Name", "Role", "Publications", "Citations", "h-index", "Reputation"])
        if user_ids:
            u_docs, rep_rows, ms_agg = await asyncio.gather(
                db.users.find(
                    {"_id": {"$in": [ObjectId(u) for u in user_ids]}},
                    {"full_name": 1, "academic_role": 1, "openalex_metrics": 1, "h_index": 1},
                ).to_list(len(user_ids)),
                db.reputation_scores.find({"user_id": {"$in": user_ids}}).to_list(len(user_ids)),
                db.manuscripts.aggregate([
                    {"$match": {"author_ids": {"$in": user_ids}, "status": "published"}},
                    {"$unwind": "$author_ids"},
                    {"$match": {"author_ids": {"$in": user_ids}}},
                    {"$group": {"_id": "$author_ids", "n": {"$sum": 1}}},
                ]).to_list(len(user_ids)),
            )
            rep_map = {r["user_id"]: r.get("overall", 0) for r in rep_rows}
            ms_map = {r["_id"]: r["n"] for r in ms_agg}
            for u in u_docs:
                uid = str(u["_id"])
                oa = u.get("openalex_metrics") or {}
                writer.writerow([
                    u.get("full_name") or "", u.get("academic_role") or "",
                    ms_map.get(uid, 0), int(oa.get("citations") or 0),
                    int(oa.get("h_index") or u.get("h_index") or 0),
                    round(rep_map.get(uid, 0), 2),
                ])

    elif report_type == "publications":
        writer.writerow(["Title", "Author", "Journal", "Year", "Citations", "Status"])
        if user_ids:
            pubs = await db.manuscripts.find(
                {"author_ids": {"$in": user_ids}},
                {"title": 1, "author_ids": 1, "journal": 1, "published_at": 1,
                 "citations": 1, "status": 1},
            ).sort("citations", -1).limit(1000).to_list(1000)
            name_map = {str(u["_id"]): u.get("full_name") for u in
                        await db.users.find({"_id": {"$in": [ObjectId(u) for u in user_ids]}},
                                            {"full_name": 1}).to_list(len(user_ids))}
            for p in pubs:
                first_auth = (p.get("author_ids") or [""])[0]
                writer.writerow([
                    p.get("title") or "", name_map.get(first_auth, ""),
                    p.get("journal") or "", (p.get("published_at") or "")[:4],
                    int(p.get("citations") or 0), p.get("status") or "",
                ])

    elif report_type == "funding":
        writer.writerow(["Source", "PI", "Status", "Amount USD", "Currency", "Date"])
        if user_ids:
            gl_rows = await db.grant_links.find(
                {"user_id": {"$in": user_ids}},
                {"user_id": 1, "title": 1, "status": 1, "amount_usd": 1, "created_at": 1},
            ).to_list(2000)
            app_rows = await db.grant_applications.find(
                {"pi_id": {"$in": user_ids}},
                {"pi_id": 1, "status": 1, "requested_budget": 1, "currency": 1, "created_at": 1},
            ).to_list(2000)
            name_map = {str(u["_id"]): u.get("full_name") for u in
                        await db.users.find({"_id": {"$in": [ObjectId(u) for u in user_ids]}},
                                            {"full_name": 1}).to_list(len(user_ids))}
            for r in gl_rows:
                writer.writerow([
                    r.get("title") or "ORCID Grant", name_map.get(r.get("user_id"), ""),
                    r.get("status") or "", int(r.get("amount_usd") or 0), "USD",
                    (r.get("created_at") or "")[:10],
                ])
            for a in app_rows:
                writer.writerow([
                    "Platform Application", name_map.get(a.get("pi_id"), ""),
                    a.get("status") or "",
                    int(_budget_to_usd(a.get("requested_budget") or 0, a.get("currency") or "USD")),
                    a.get("currency") or "USD",
                    (a.get("created_at") or "")[:10],
                ])

    elif report_type == "departments":
        writer.writerow(["Department", "Rank", "Score", "Members", "Publications",
                          "Citations", "Grants Awarded", "Funding USD", "Avg Reputation"])
        rankings = await rank_departments(institution_id)
        for r in rankings:
            m = r.get("metrics") or {}
            writer.writerow([
                r.get("name") or "", r.get("rank") or "", round(r.get("score") or 0, 4),
                m.get("members", 0), m.get("publications", 0), m.get("total_citations", 0),
                m.get("grants_awarded", 0), m.get("funding_usd", 0),
                round(m.get("avg_reputation", 0), 2),
            ])

    output.seek(0)
    filename = f"synaptiq_{report_type}_report.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
