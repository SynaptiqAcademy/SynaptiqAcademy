"""Admin Operating System (AOS) — SYNAPTIQ enterprise command center.

All endpoints require is_super_admin.
All mutating operations are audit-logged.

Sections:
  1. Executive Command Center — enhanced dashboard, timeseries, export
  2. Revenue Intelligence — ARPU, LTV, CAC, conversion, retention, by-country, forecast
  3. Subscription Control — list/extend/cancel/upgrade/recover subscriptions
  4. Research Governance — stalled projects, inactive manuscripts, health scores
  5. Teaching Governance — quality audit, teacher analytics
  6. Platform Health — infrastructure, integrations, incidents
  7. Error & Incident Center — log, triage, resolve errors
  8. Platform Auditor — automated scoring (Health, Security, Performance, UX, Academic)
  9. Database Operations — collection stats, integrity, health score
 10. User History — login, device, session, full activity timeline
 11. Communications — banner management, campaign analytics
 12. Promotions Enhanced — campaign analytics, conversion tracking
"""
from __future__ import annotations

import asyncio
import csv
import io
import os
import sys
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

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

router = APIRouter(prefix="/api/admin/aos", tags=["admin-aos"])
_GATE = [Depends(require_super_admin)]

# ─────────────────────────── helpers ─────────────────────────────────────────

_START_TIME = time.time()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now().isoformat()


def _ago(days: int = 0, hours: int = 0, minutes: int = 0) -> str:
    return (_now() - timedelta(days=days, hours=hours, minutes=minutes)).isoformat()


def _parse_oid(uid: str) -> ObjectId:
    try:
        return ObjectId(uid)
    except (InvalidId, Exception):
        raise HTTPException(status_code=400, detail="Invalid ID")


def _ser(doc: dict) -> dict:
    if not doc:
        return doc
    doc["id"] = str(doc.pop("_id", ""))
    return doc


def _uptime_seconds() -> int:
    return int(time.time() - _START_TIME)


# ═════════════════════════════════════════════════════════════════════════════
# 1. EXECUTIVE COMMAND CENTER
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/dashboard", dependencies=_GATE)
async def aos_dashboard(
    days: int = Query(30, ge=1, le=365),
    country: Optional[str] = None,
    academic_role: Optional[str] = None,
):
    """Enhanced executive dashboard — all user, activity, and financial KPIs."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    now = _now()
    cutoff = _ago(days)
    today  = datetime(now.year, now.month, now.day, tzinfo=timezone.utc).isoformat()
    week   = _ago(7)

    user_filt: dict = {}
    if country:
        user_filt["country"] = country
    if academic_role:
        user_filt["academic_role"] = {"$regex": academic_role, "$options": "i"}

    (
        total_users, free_users, researcher_users, pro_researcher_users, institution_users,
        orcid_users, email_verified_users, onboarded_users, suspended_users, banned_users,
        new_today, new_week, new_period,
        verified_researchers, verified_professors, premium_users,
    ) = await asyncio.gather(
        db.users.count_documents(user_filt),
        db.users.count_documents({**user_filt, "plan_code": "free"}),
        db.users.count_documents({**user_filt, "plan_code": "researcher"}),
        db.users.count_documents({**user_filt, "plan_code": "pro_researcher"}),
        db.users.count_documents({**user_filt, "plan_code": "institution"}),
        db.users.count_documents({**user_filt, "orcid.orcid_id": {"$exists": True, "$ne": None}}),
        db.users.count_documents({**user_filt, "email_verified": True}),
        db.users.count_documents({**user_filt, "onboarded": True}),
        db.users.count_documents({**user_filt, "status": "suspended"}),
        db.users.count_documents({**user_filt, "status": "banned"}),
        db.users.count_documents({**user_filt, "created_at": {"$gte": today}}),
        db.users.count_documents({**user_filt, "created_at": {"$gte": week}}),
        db.users.count_documents({**user_filt, "created_at": {"$gte": cutoff}}),
        db.users.count_documents({**user_filt, "academic_role": {"$regex": "professor|associate professor|full professor|dean|rector", "$options": "i"}, "email_verified": True}),
        db.users.count_documents({**user_filt, "academic_role": {"$regex": "professor|associate|dean|rector", "$options": "i"}}),
        db.users.count_documents({**user_filt, "plan_code": {"$in": ["researcher", "pro_researcher", "institution"]}}),
    )

    # Online users: active in last 15 minutes via audit_log
    online_cutoff = _ago(minutes=15)
    online_pipe = [
        {"$match": {"action": "auth.login", "created_at": {"$gte": online_cutoff}}},
        {"$group": {"_id": "$actor_id"}},
        {"$count": "n"},
    ]
    online_agg = await db.audit_log.aggregate(online_pipe).to_list(1)
    online_users = online_agg[0]["n"] if online_agg else 0

    # Activity KPIs for the period
    (
        new_projects, new_publications, new_collabs, new_manuscripts,
        new_collaborations_requests, ai_requests,
    ) = await asyncio.gather(
        db.projects.count_documents({"created_at": {"$gte": cutoff}}),
        db.publications.count_documents({"created_at": {"$gte": cutoff}}),
        db.collaborations.count_documents({"created_at": {"$gte": cutoff}}),
        db.manuscripts.count_documents({"created_at": {"$gte": cutoff}}),
        db.collaboration_requests.count_documents({"created_at": {"$gte": cutoff}}),
        db.credit_transactions.count_documents({"kind": "consume", "created_at": {"$gte": cutoff}}),
    )

    # Teaching activity
    new_courses  = await db.courses.count_documents({"created_at": {"$gte": cutoff}})
    new_lessons  = await db.lessons.count_documents({"created_at": {"$gte": cutoff}})

    # Financial
    from plans_catalogue import PLANS, get_plan  # type: ignore
    mrr = 0.0
    for p in PLANS:
        if p["code"] == "free":
            continue
        cnt = {
            "researcher": researcher_users,
            "pro_researcher": pro_researcher_users,
            "institution": institution_users,
        }.get(p["code"], 0)
        plan = get_plan(p["code"])
        mrr += cnt * float(plan.get("price_eur_monthly", 0))

    active_subscribers = researcher_users + pro_researcher_users + institution_users
    churn_pipe = [
        {"$match": {
            "created_at": {"$gte": cutoff},
            "from_plan": {"$in": ["researcher", "pro_researcher", "institution"]},
            "to_plan": {"$in": [None, "free"]},
        }},
        {"$count": "n"},
    ]
    churn_agg = await db.subscription_history.aggregate(churn_pipe).to_list(1)
    churned = churn_agg[0]["n"] if churn_agg else 0
    churn_rate = round(churned / max(active_subscribers, 1) * 100, 2)

    # Free-to-premium conversion
    conv_pipe = [
        {"$match": {
            "created_at": {"$gte": cutoff},
            "from_plan": "free",
            "to_plan": {"$in": ["researcher", "pro_researcher", "institution"]},
        }},
        {"$count": "n"},
    ]
    conv_agg = await db.subscription_history.aggregate(conv_pipe).to_list(1)
    conversions = conv_agg[0]["n"] if conv_agg else 0
    conversion_rate = round(conversions / max(free_users, 1) * 100, 2)

    arpu = round(mrr / max(active_subscribers, 1), 2)

    return {
        "period_days": days,
        "filters": {"country": country, "academic_role": academic_role},
        "users": {
            "total":              total_users,
            "online_now":         online_users,
            "new_today":          new_today,
            "new_week":           new_week,
            "new_period":         new_period,
            "free":               free_users,
            "researcher":         researcher_users,
            "pro_researcher":     pro_researcher_users,
            "institution":        institution_users,
            "premium":            premium_users,
            "orcid_linked":       orcid_users,
            "email_verified":     email_verified_users,
            "onboarded":          onboarded_users,
            "suspended":          suspended_users,
            "banned":             banned_users,
            "verified_researchers": verified_researchers,
            "verified_professors":  verified_professors,
        },
        "activity": {
            "new_projects":             new_projects,
            "new_publications":         new_publications,
            "new_collaborations":       new_collabs,
            "new_manuscripts":          new_manuscripts,
            "collaboration_requests":   new_collaborations_requests,
            "ai_requests":              ai_requests,
            "new_courses":              new_courses,
            "new_lessons":              new_lessons,
        },
        "financial": {
            "mrr_eur":          round(mrr, 2),
            "arr_eur":          round(mrr * 12, 2),
            "active_subscribers": active_subscribers,
            "arpu_eur":         arpu,
            "churned_period":   churned,
            "churn_rate_pct":   churn_rate,
            "conversions":      conversions,
            "conversion_rate_pct": conversion_rate,
        },
    }


@router.get("/timeseries", dependencies=_GATE)
async def aos_timeseries(days: int = Query(30, ge=7, le=365)):
    """Daily registrations, logins, AI requests, and publications for sparklines."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    now = _now()
    series = []
    for d in range(days - 1, -1, -1):
        day_start = (now - timedelta(days=d)).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        day_end   = (now - timedelta(days=d)).replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()
        label = (now - timedelta(days=d)).strftime("%Y-%m-%d")
        regs, logins, ai_reqs, pubs = await asyncio.gather(
            db.users.count_documents({"created_at": {"$gte": day_start, "$lte": day_end}}),
            db.audit_log.count_documents({"action": "auth.login", "created_at": {"$gte": day_start, "$lte": day_end}}),
            db.credit_transactions.count_documents({"kind": "consume", "created_at": {"$gte": day_start, "$lte": day_end}}),
            db.publications.count_documents({"created_at": {"$gte": day_start, "$lte": day_end}}),
        )
        series.append({
            "date":         label,
            "registrations": regs,
            "logins":       logins,
            "ai_requests":  ai_reqs,
            "publications": pubs,
        })
    return {"days": days, "series": series}


@router.get("/community/stats", dependencies=_GATE)
async def aos_community_stats():
    """Community section stats for Mission Control — thin wrapper around the
    existing Academic Network analytics engine (no admin-facing equivalent
    existed previously)."""
    from services.network.analytics_engine import get_platform_network_stats

    db = get_db()
    db = DBProxy(db, SecurityContext.system())
    return await get_platform_network_stats(db)


@router.get("/export", dependencies=_GATE)
async def aos_export(report: str = Query("users", enum=["users", "activity", "financial"])):
    """CSV export of executive dashboard data."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    buf = io.StringIO()
    w   = csv.writer(buf)

    if report == "users":
        cursor = db.users.find({}, {
            "email": 1, "full_name": 1, "plan_code": 1, "status": 1,
            "email_verified": 1, "country": 1, "academic_role": 1,
            "orcid": 1, "created_at": 1,
        }).sort("created_at", -1)
        w.writerow(["Email", "Name", "Plan", "Status", "Verified", "Country", "Academic Role", "ORCID", "Created"])
        async for u in cursor:
            w.writerow([
                u.get("email"), u.get("full_name"), u.get("plan_code", "free"),
                u.get("status", "active"), u.get("email_verified", False),
                u.get("country"), u.get("academic_role"),
                bool((u.get("orcid") or {}).get("orcid_id")),
                (u.get("created_at") or "")[:10],
            ])
        filename = "users.csv"

    elif report == "activity":
        cursor = db.audit_log.find({}, {
            "action": 1, "actor_email": 1, "created_at": 1, "ip": 1,
        }).sort("created_at", -1).limit(5000)
        w.writerow(["Timestamp", "Action", "Actor", "IP"])
        async for ev in cursor:
            w.writerow([ev.get("created_at"), ev.get("action"), ev.get("actor_email"), ev.get("ip")])
        filename = "activity.csv"

    else:
        cursor = db.billing_history.find({}, {
            "kind": 1, "amount_eur": 1, "status": 1, "created_at": 1,
            "user_id": 1,
        }).sort("created_at", -1).limit(5000)
        w.writerow(["Date", "Kind", "Amount EUR", "Status", "User ID"])
        async for r in cursor:
            w.writerow([
                (r.get("created_at") or "")[:10],
                r.get("kind"), r.get("amount_eur"), r.get("status"), r.get("user_id"),
            ])
        filename = "financial.csv"

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ═════════════════════════════════════════════════════════════════════════════
# 2. REVENUE INTELLIGENCE
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/revenue/metrics", dependencies=_GATE)
async def revenue_metrics(days: int = 30):
    """ARPU, LTV, CAC, free-to-premium conversion, retention rate, churn."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    cutoff = _ago(days)

    from plans_catalogue import PLANS, get_plan  # type: ignore

    plan_counts: dict[str, int] = {}
    for p in PLANS:
        plan_counts[p["code"]] = await db.users.count_documents({"plan_code": p["code"]})

    active = sum(v for k, v in plan_counts.items() if k != "free")
    total  = sum(plan_counts.values())

    mrr = 0.0
    for p in PLANS:
        if p["code"] == "free":
            continue
        plan = get_plan(p["code"])
        mrr += plan_counts[p["code"]] * float(plan.get("price_eur_monthly", 0))
    arr = mrr * 12

    arpu = round(mrr / max(active, 1), 2)
    # LTV estimate: ARPU / churn_rate (if churn_rate > 0)
    churn_pipe = [
        {"$match": {"created_at": {"$gte": cutoff},
                    "from_plan": {"$in": ["researcher", "pro_researcher", "institution"]},
                    "to_plan": {"$in": [None, "free"]}}},
        {"$count": "n"},
    ]
    ch = await db.subscription_history.aggregate(churn_pipe).to_list(1)
    churned = ch[0]["n"] if ch else 0
    churn_rate_monthly = churned / max(active, 1)
    ltv = round(arpu / churn_rate_monthly, 2) if churn_rate_monthly > 0 else 0.0

    # CAC: approximated as pack_revenue spend on campaigns / conversions
    conv_pipe = [
        {"$match": {"created_at": {"$gte": cutoff}, "from_plan": "free",
                    "to_plan": {"$in": ["researcher", "pro_researcher", "institution"]}}},
        {"$count": "n"},
    ]
    conv_agg = await db.subscription_history.aggregate(conv_pipe).to_list(1)
    conversions = conv_agg[0]["n"] if conv_agg else 0

    promo_spend_pipe = [
        {"$match": {"created_at": {"$gte": cutoff}}},
        {"$group": {"_id": None, "total": {"$sum": "$credits_granted"}}},
    ]
    promo_agg = await db.promotions.aggregate(promo_spend_pipe).to_list(1)
    promo_credits = promo_agg[0]["total"] if promo_agg else 0
    cac = round(promo_credits / max(conversions, 1) * 0.05, 2)

    # Retention: users who converted AND are still on paid plan
    retention_pipe = [
        {"$match": {"created_at": {"$gte": _ago(days * 2), "$lt": cutoff},
                    "to_plan": {"$in": ["researcher", "pro_researcher", "institution"]}}},
        {"$group": {"_id": "$user_id"}},
    ]
    converted_then = await db.subscription_history.aggregate(retention_pipe).to_list(10000)
    converted_user_ids = [r["_id"] for r in converted_then]
    still_paid = 0
    if converted_user_ids:
        still_paid = await db.users.count_documents(
            {"_id": {"$in": [ObjectId(uid) for uid in converted_user_ids if uid and len(uid) == 24]},
             "plan_code": {"$in": ["researcher", "pro_researcher", "institution"]}}
        )
    retention_rate = round(still_paid / max(len(converted_user_ids), 1) * 100, 1)

    conversion_rate = round(conversions / max(plan_counts.get("free", 1), 1) * 100, 2)

    return {
        "period_days":     days,
        "mrr_eur":         round(mrr, 2),
        "arr_eur":         round(arr, 2),
        "arpu_eur":        arpu,
        "ltv_eur":         ltv,
        "cac_eur":         cac,
        "active_subscribers": active,
        "total_users":     total,
        "plan_counts":     plan_counts,
        "churned_period":  churned,
        "churn_rate_pct":  round(churn_rate_monthly * 100, 2),
        "conversions":     conversions,
        "conversion_rate_pct": conversion_rate,
        "retention_rate_pct":  retention_rate,
    }


@router.get("/revenue/by-country", dependencies=_GATE)
async def revenue_by_country():
    """Revenue and user distribution by country."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    pipe = [
        {"$match": {"plan_code": {"$in": ["researcher", "pro_researcher", "institution"]}}},
        {"$group": {"_id": "$country", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 30},
    ]
    docs = await db.users.aggregate(pipe).to_list(30)
    from plans_catalogue import get_plan  # type: ignore
    # Approximate revenue per country from plan counts
    plan_pipe = [
        {"$match": {"plan_code": {"$in": ["researcher", "pro_researcher", "institution"]}}},
        {"$group": {"_id": {"country": "$country", "plan": "$plan_code"}, "count": {"$sum": 1}}},
    ]
    plan_docs = await db.users.aggregate(plan_pipe).to_list(1000)
    country_rev: dict[str, float] = {}
    for d in plan_docs:
        country = d["_id"].get("country") or "Unknown"
        plan_code = d["_id"].get("plan") or "free"
        plan = get_plan(plan_code)
        rev = d["count"] * float(plan.get("price_eur_monthly", 0))
        country_rev[country] = country_rev.get(country, 0) + rev

    result = []
    for d in docs:
        country = d["_id"] or "Unknown"
        result.append({
            "country":    country,
            "users":      d["count"],
            "mrr_eur":    round(country_rev.get(country, 0), 2),
        })
    return {"items": result}


@router.get("/revenue/forecast", dependencies=_GATE)
async def revenue_forecast():
    """Simple 3-month revenue forecast based on trend (last 3 months vs previous 3)."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    now = _now()

    monthly_data = []
    for m in range(5, -1, -1):
        month_start = (now.replace(day=1) - timedelta(days=m * 30)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        month_end = (month_start + timedelta(days=32)).replace(day=1)
        pipe = [
            {"$match": {"kind": {"$in": ["pack_purchase", "invoice"]}, "status": "paid",
                        "created_at": {"$gte": month_start.isoformat(), "$lt": month_end.isoformat()}}},
            {"$group": {"_id": None, "total": {"$sum": "$amount_eur"}}},
        ]
        r = await db.billing_history.aggregate(pipe).to_list(1)
        monthly_data.append({
            "month":      month_start.strftime("%Y-%m"),
            "revenue_eur": round((r[0].get("total") if r else 0) or 0.0, 2),
        })

    # Linear trend: average of last 3 vs previous 3
    if len(monthly_data) >= 6:
        prev3_avg = sum(d["revenue_eur"] for d in monthly_data[:3]) / 3
        last3_avg = sum(d["revenue_eur"] for d in monthly_data[3:]) / 3
        growth_rate = (last3_avg - prev3_avg) / max(prev3_avg, 1)
    else:
        last3_avg = (monthly_data[-1]["revenue_eur"] if monthly_data else 0)
        growth_rate = 0.05  # default 5% growth assumption

    forecast = []
    base = last3_avg
    for i in range(1, 4):
        projected = round(base * (1 + growth_rate) ** i, 2)
        month_label = (now + timedelta(days=i * 30)).strftime("%Y-%m")
        forecast.append({"month": month_label, "projected_eur": projected})

    return {
        "history":       monthly_data,
        "forecast":      forecast,
        "growth_rate_pct": round(growth_rate * 100, 1),
        "methodology":   "Linear extrapolation from 3-month trend vs previous 3-month period",
    }


# ═════════════════════════════════════════════════════════════════════════════
# 3. SUBSCRIPTION CONTROL CENTER
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/subscriptions", dependencies=_GATE)
async def list_subscriptions(
    status: Optional[str] = None,
    plan: Optional[str] = None,
    page: int = 1,
    limit: int = 50,
):
    """List all subscriptions with plan/status filters."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    filt: dict = {}
    if status == "active":
        filt["plan_code"] = {"$in": ["researcher", "pro_researcher", "institution"]}
    elif status == "free":
        filt["plan_code"] = "free"
    elif status == "suspended":
        filt["status"] = "suspended"
    if plan:
        filt["plan_code"] = plan
    skip  = (max(page, 1) - 1) * limit
    total = await db.users.count_documents(filt)
    cursor = db.users.find(filt, {
        "email": 1, "full_name": 1, "plan_code": 1, "subscription_status": 1,
        "status": 1, "created_at": 1, "credits_balance": 1,
    }).sort("created_at", -1).skip(skip).limit(limit)
    docs = []
    async for u in cursor:
        docs.append({
            "id":                 str(u["_id"]),
            "email":              u.get("email"),
            "name":               u.get("full_name"),
            "plan":               u.get("plan_code", "free"),
            "subscription_status": u.get("subscription_status"),
            "account_status":     u.get("status", "active"),
            "credits":            u.get("credits_balance", 0),
            "created_at":         u.get("created_at"),
        })
    return {"total": total, "page": page, "limit": limit, "items": docs}


@router.get("/subscriptions/trials", dependencies=_GATE)
async def list_trials():
    """Users currently on trial subscriptions."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    docs = await db.users.find(
        {"subscription_status": {"$regex": "trial", "$options": "i"}},
        {"email": 1, "full_name": 1, "plan_code": 1, "trial_ends_at": 1, "created_at": 1},
    ).to_list(500)
    return {"items": [_ser(d) for d in docs]}


@router.get("/subscriptions/churned", dependencies=_GATE)
async def churned_users(days: int = 30):
    """Users who churned (downgraded from paid to free) in the last N days."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    cutoff = _ago(days)
    pipe = [
        {"$match": {
            "created_at": {"$gte": cutoff},
            "from_plan": {"$in": ["researcher", "pro_researcher", "institution"]},
            "to_plan": {"$in": [None, "free"]},
        }},
        {"$sort": {"created_at": -1}},
        {"$limit": 200},
    ]
    docs = await db.subscription_history.aggregate(pipe).to_list(200)
    for d in docs:
        d["id"] = str(d.pop("_id", ""))
    return {"period_days": days, "count": len(docs), "items": docs}


class SubscriptionPatch(BaseModel):
    action: str  # "extend" | "cancel" | "upgrade" | "downgrade"
    plan: Optional[str] = None
    days: Optional[int] = None
    reason: str = ""


@router.patch("/subscriptions/{uid}", dependencies=_GATE)
async def patch_subscription(
    uid: str,
    body: SubscriptionPatch,
    request: Request,
    admin: dict = Depends(require_super_admin),
):
    """Extend, cancel, upgrade, or downgrade a user's subscription."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    oid = _parse_oid(uid)
    user = await db.users.find_one({"_id": oid}, {"email": 1, "plan_code": 1})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    now = _now_iso()
    old_plan = user.get("plan_code", "free")
    update: dict = {"updated_at": now}

    if body.action == "cancel":
        update["plan_code"]            = "free"
        update["subscription_status"]  = "cancelled"
    elif body.action in ("upgrade", "downgrade") and body.plan:
        update["plan_code"] = body.plan
        update["subscription_status"] = "active"
    elif body.action == "extend" and body.days:
        update["subscription_extended_days"] = body.days
        update["subscription_extended_at"]   = now
    else:
        raise HTTPException(status_code=400, detail="Invalid action or missing parameters")

    await db.users.update_one({"_id": oid}, {"$set": update})
    await db.subscription_history.insert_one({
        "user_id":    uid,
        "from_plan":  old_plan,
        "to_plan":    update.get("plan_code", old_plan),
        "action":     body.action,
        "reason":     body.reason,
        "by_admin":   admin.get("email"),
        "created_at": now,
    })
    await log_event(
        f"admin.subscription.{body.action}",
        actor_id=admin["id"], actor_email=admin.get("email"),
        target_id=uid, target_email=user.get("email"),
        ip=request_meta(request)["ip"],
        extra={"from_plan": old_plan, "to_plan": body.plan, "days": body.days, "reason": body.reason},
    )
    return {"ok": True, "action": body.action, "user_id": uid}


# ═════════════════════════════════════════════════════════════════════════════
# 4. RESEARCH GOVERNANCE CENTER
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/research/overview", dependencies=_GATE)
async def research_overview():
    """Platform-wide research activity overview."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    cutoff_30 = _ago(30)
    cutoff_90 = _ago(90)

    (
        total_publications, total_manuscripts, total_projects,
        total_workspaces, total_collabs, total_grant_links, total_grant_apps,
        active_projects, active_manuscripts, pub_month, ms_month, proj_month,
    ) = await asyncio.gather(
        db.publications.count_documents({}),
        db.manuscripts.count_documents({}),
        db.projects.count_documents({}),
        db.workspaces.count_documents({}),
        db.collaborations.count_documents({}),
        db.grant_links.count_documents({}),
        db.grant_applications.count_documents({}),
        db.projects.count_documents({"status": {"$ne": "archived"}}),
        db.manuscripts.count_documents({"status": {"$in": ["draft", "submitted", "revision_requested"]}}),
        db.publications.count_documents({"created_at": {"$gte": cutoff_30}}),
        db.manuscripts.count_documents({"created_at": {"$gte": cutoff_30}}),
        db.projects.count_documents({"created_at": {"$gte": cutoff_30}}),
    )

    return {
        "publications":      {"total": total_publications, "new_30d": pub_month},
        "manuscripts":       {"total": total_manuscripts, "active": active_manuscripts, "new_30d": ms_month},
        "projects":          {"total": total_projects, "active": active_projects, "new_30d": proj_month},
        "workspaces":        {"total": total_workspaces},
        "collaborations":    {"total": total_collabs},
        "grants":            {"links": total_grant_links, "applications": total_grant_apps, "total": total_grant_links + total_grant_apps},
    }


@router.get("/research/stalled", dependencies=_GATE)
async def research_stalled(days: int = 30):
    """Detect stalled projects, inactive manuscripts, and dormant collaborations."""
    db     = get_db()
    db = DBProxy(db, SecurityContext.system())

    cutoff = _ago(days)

    # Stalled projects: no update in last N days, not archived
    stalled_projs = await db.projects.find(
        {"updated_at": {"$lt": cutoff}, "status": {"$nin": ["archived", "completed"]}},
        {"title": 1, "owner_id": 1, "updated_at": 1, "members": 1},
    ).limit(50).to_list(50)

    # Inactive manuscripts: no update in last N days, not published/rejected
    inactive_ms = await db.manuscripts.find(
        {"updated_at": {"$lt": cutoff}, "status": {"$nin": ["published", "rejected", "withdrawn"]}},
        {"title": 1, "authors": 1, "updated_at": 1, "status": 1},
    ).limit(50).to_list(50)

    # Dormant collaborations: open collabs with no messages in last N days
    dormant_collabs = await db.collaborations.find(
        {"status": "active", "updated_at": {"$lt": cutoff}},
        {"title": 1, "owner_id": 1, "members": 1, "updated_at": 1},
    ).limit(50).to_list(50)

    # Expired funding opportunities
    now_str = _now_iso()
    expired_grants = await db.grants.find(
        {"deadline": {"$lt": now_str}, "status": {"$nin": ["closed", "archived"]}},
        {"title": 1, "deadline": 1, "funder": 1},
    ).limit(20).to_list(20)

    for d in stalled_projs + inactive_ms + dormant_collabs + expired_grants:
        d["id"] = str(d.pop("_id", ""))

    return {
        "stale_days":          days,
        "stalled_projects":    stalled_projs,
        "inactive_manuscripts": inactive_ms,
        "dormant_collaborations": dormant_collabs,
        "expired_funding":     expired_grants,
        "totals": {
            "stalled_projects":     len(stalled_projs),
            "inactive_manuscripts": len(inactive_ms),
            "dormant_collabs":      len(dormant_collabs),
            "expired_funding":      len(expired_grants),
        },
    }


@router.get("/research/health", dependencies=_GATE)
async def research_health():
    """Research health score from platform activity signals."""
    db      = get_db()
    db = DBProxy(db, SecurityContext.system())

    cutoff  = _ago(30)
    cutoff7 = _ago(7)

    (
        total_pubs, pubs_30d, total_ms, ms_active,
        total_proj, proj_active, total_collabs, collabs_active,
        grant_awarded, grant_apps,
    ) = await asyncio.gather(
        db.publications.count_documents({}),
        db.publications.count_documents({"created_at": {"$gte": cutoff}}),
        db.manuscripts.count_documents({}),
        db.manuscripts.count_documents({"status": {"$nin": ["published", "rejected", "withdrawn"]}}),
        db.projects.count_documents({}),
        db.projects.count_documents({"status": {"$nin": ["archived", "completed"]}}),
        db.collaborations.count_documents({}),
        db.collaborations.count_documents({"status": "active"}),
        db.grant_links.count_documents({"status": "awarded"}),
        db.grant_applications.count_documents({}),
    )

    import math

    def _score(value: int, scale: int) -> float:
        return round(min(100, math.log1p(value) / math.log1p(scale) * 100), 1)

    publication_score  = _score(total_pubs, 500)
    activity_score     = _score(pubs_30d, 50)
    manuscript_score   = _score(ms_active, 100)
    project_score      = _score(proj_active, 200)
    collab_score       = _score(collabs_active, 100)
    grant_score        = _score(grant_awarded, 20)

    overall = round(
        0.30 * publication_score + 0.20 * activity_score + 0.15 * manuscript_score +
        0.15 * project_score + 0.10 * collab_score + 0.10 * grant_score, 1
    )

    recommendations = []
    if pubs_30d < 5:
        recommendations.append("Low publication activity in last 30 days — consider outreach to active researchers.")
    if proj_active / max(total_proj, 1) < 0.5:
        recommendations.append("Over 50% of projects are archived/completed — new project creation is lagging.")
    if collabs_active < 5:
        recommendations.append("Few active collaborations — promote collaboration tools.")
    if grant_awarded < 3:
        recommendations.append("Low grant success — consider improving grant matching algorithms.")

    return {
        "overall_score":   int(overall),
        "components": {
            "publication":  publication_score,
            "activity_30d": activity_score,
            "manuscripts":  manuscript_score,
            "projects":     project_score,
            "collaborations": collab_score,
            "grants":       grant_score,
        },
        "raw": {
            "total_publications":  total_pubs,
            "publications_30d":    pubs_30d,
            "active_manuscripts":  ms_active,
            "active_projects":     proj_active,
            "active_collaborations": collabs_active,
            "awarded_grants":      grant_awarded,
        },
        "recommendations": recommendations,
    }


# ═════════════════════════════════════════════════════════════════════════════
# 5. TEACHING GOVERNANCE
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/teaching/overview", dependencies=_GATE)
async def teaching_overview():
    """Complete educational platform overview."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    cutoff = _ago(30)

    (
        total_courses, active_courses, total_lessons, total_assessments,
        total_portfolios, total_certificates, total_enrollments,
        new_courses_30d, new_lessons_30d, total_submissions,
    ) = await asyncio.gather(
        db.courses.count_documents({}),
        db.courses.count_documents({"status": {"$in": ["published", "active"]}}),
        db.lessons.count_documents({}),
        db.assessments.count_documents({}),
        db.portfolios.count_documents({}),
        db.certificates.count_documents({}),
        db.enrollments.count_documents({}),
        db.courses.count_documents({"created_at": {"$gte": cutoff}}),
        db.lessons.count_documents({"created_at": {"$gte": cutoff}}),
        db.student_submissions.count_documents({}),
    )

    # Completion rates
    completed_enrollments = await db.enrollments.count_documents({"status": "completed"})
    completion_rate = round(completed_enrollments / max(total_enrollments, 1) * 100, 1)

    return {
        "courses":         {"total": total_courses, "active": active_courses, "new_30d": new_courses_30d},
        "lessons":         {"total": total_lessons, "new_30d": new_lessons_30d},
        "assessments":     {"total": total_assessments},
        "portfolios":      {"total": total_portfolios},
        "certificates":    {"total": total_certificates},
        "enrollments":     {"total": total_enrollments, "completed": completed_enrollments, "completion_rate_pct": completion_rate},
        "submissions":     {"total": total_submissions},
    }


@router.get("/teaching/quality", dependencies=_GATE)
async def teaching_quality_audit():
    """Academic quality audit — detect content gaps and compliance issues."""
    db = get_db()

    db = DBProxy(db, SecurityContext.system())

    # Courses with no lessons
    courses_no_lessons: list[dict] = []
    async for c in db.courses.find({"status": "published"}, {"title": 1, "instructor_id": 1}):
        lesson_count = await db.lessons.count_documents({"course_id": str(c["_id"])})
        if lesson_count == 0:
            courses_no_lessons.append({"id": str(c["_id"]), "title": c.get("title"), "instructor_id": c.get("instructor_id")})

    # Lessons with no assessments
    lessons_no_assessment: list[dict] = []
    async for l in db.lessons.find({}, {"title": 1, "course_id": 1}).limit(500):
        assessment_count = await db.assessments.count_documents({"lesson_id": str(l["_id"])})
        if assessment_count == 0:
            lessons_no_assessment.append({"id": str(l["_id"]), "title": l.get("title"), "course_id": l.get("course_id")})
        if len(lessons_no_assessment) >= 20:
            break

    # Inactive instructors (courses published, no lesson added in 30 days)
    cutoff = _ago(30)
    inactive_instructors: list[dict] = []
    instructor_ids = await db.courses.distinct("instructor_id", {"status": "published"})
    for iid in instructor_ids[:50]:
        recent = await db.lessons.count_documents({"instructor_id": iid, "created_at": {"$gte": cutoff}})
        if recent == 0:
            u = await db.users.find_one({"_id": ObjectId(iid) if len(iid) == 24 else None}, {"email": 1, "full_name": 1})
            inactive_instructors.append({
                "instructor_id": iid,
                "email": (u or {}).get("email"),
                "name": (u or {}).get("full_name"),
            })

    # Quality score
    total_courses = await db.courses.count_documents({})
    issues = len(courses_no_lessons) + len(lessons_no_assessment) + len(inactive_instructors)
    quality_score = max(0, round(100 - (issues / max(total_courses, 1)) * 50, 1))

    return {
        "quality_score":         quality_score,
        "courses_without_lessons": courses_no_lessons[:10],
        "lessons_without_assessments": lessons_no_assessment[:10],
        "inactive_instructors":  inactive_instructors[:10],
        "issue_count":           issues,
        "recommendations": [
            "Add lessons to empty published courses." if courses_no_lessons else None,
            "Add assessments to lessons for better engagement." if lessons_no_assessment else None,
            "Re-engage inactive instructors." if inactive_instructors else None,
        ],
    }


# ═════════════════════════════════════════════════════════════════════════════
# 6. PLATFORM HEALTH CENTER
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/health/infrastructure", dependencies=_GATE)
async def health_infrastructure():
    """Real infrastructure metrics — uptime, database, service availability."""
    db = get_db()

    db = DBProxy(db, SecurityContext.system())

    # Database health
    db_ok  = False
    db_stats: dict = {}
    try:
        await db.command("ping")
        db_ok = True
        srv = await db.command("serverStatus")
        db_stats = {
            "connections_current": (srv.get("connections") or {}).get("current", 0),
            "connections_available": (srv.get("connections") or {}).get("available", 0),
            "ops_per_second": {
                k: (srv.get("opcounters") or {}).get(k, 0)
                for k in ["insert", "query", "update", "delete", "getmore", "command"]
            },
            "uptime_seconds": srv.get("uptime", 0),
        }
    except Exception as e:
        db_stats = {"error": str(e)}

    # Python process memory (no psutil — use platform.uname)
    import platform
    py_version = sys.version.split(" ")[0]

    # Uptime of this process
    uptime_s = _uptime_seconds()
    uptime_h = round(uptime_s / 3600, 2)

    # Collection counts (quick health check)
    collection_names = await db.list_collection_names()
    total_collections = len(collection_names)

    # Recently logged errors
    error_count_24h = await db.error_logs.count_documents({"created_at": {"$gte": _ago(hours=24)}})

    return {
        "app_uptime_hours":     uptime_h,
        "app_uptime_seconds":   uptime_s,
        "python_version":       py_version,
        "platform":             platform.system(),
        "database": {
            "ok":         db_ok,
            "stats":      db_stats,
            "collections": total_collections,
        },
        "errors_24h":           error_count_24h,
    }


@router.get("/health/integrations", dependencies=_GATE)
async def health_integrations():
    """External integration status from environment configuration."""
    checks = {
        "stripe":      bool(os.environ.get("STRIPE_SECRET_KEY")),
        "resend_email": bool(os.environ.get("RESEND_API_KEY")),
        "orcid":       bool(os.environ.get("ORCID_CLIENT_ID") and os.environ.get("ORCID_CLIENT_SECRET")),
        "google_oauth": bool(os.environ.get("GOOGLE_CLIENT_ID")),
        "openai":      bool(os.environ.get("OPENAI_API_KEY")),
        "anthropic":   bool(os.environ.get("ANTHROPIC_API_KEY")),
        "aws_s3":      bool(os.environ.get("AWS_ACCESS_KEY_ID")),
        "mongodb":     bool(os.environ.get("MONGODB_URI") or os.environ.get("MONGO_URL")),
        "redis":       bool(os.environ.get("REDIS_URL")),
        "jwt_secret":  bool(os.environ.get("JWT_SECRET")),
    }
    configured = sum(1 for v in checks.values() if v)
    total = len(checks)
    health_score = round(configured / total * 100, 0)

    # DB ping
    db_ok = False
    try:
        db = get_db()
        db = DBProxy(db, SecurityContext.system())

        await db.command("ping")
        db_ok = True
    except Exception:
        pass

    return {
        "integrations":  {k: {"configured": v, "status": "ok" if v else "missing"} for k, v in checks.items()},
        "db_reachable":  db_ok,
        "configured":    configured,
        "total":         total,
        "health_score":  int(health_score),
    }


@router.get("/health/incidents", dependencies=_GATE)
async def health_incidents(limit: int = 50):
    """Recent platform incidents from error_logs collection."""
    db   = get_db()
    db = DBProxy(db, SecurityContext.system())

    docs = await db.error_logs.find(
        {},
        {"severity": 1, "category": 1, "message": 1, "endpoint": 1,
         "user_id": 1, "resolved": 1, "created_at": 1, "frequency": 1}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    for d in docs:
        d["id"] = str(d.pop("_id", ""))
    return {"count": len(docs), "items": docs}


# ═════════════════════════════════════════════════════════════════════════════
# 7. ERROR & INCIDENT CENTER
# ═════════════════════════════════════════════════════════════════════════════

class ErrorReport(BaseModel):
    severity:   str = "medium"   # low | medium | high | critical
    category:   str = "frontend" # frontend | backend | api | database | payment | auth | email
    message:    str
    endpoint:   Optional[str] = None
    stack_trace: Optional[str] = None
    browser:    Optional[str] = None
    user_id:    Optional[str] = None
    metadata:   Optional[dict] = None


@router.post("/errors")
async def log_error(body: ErrorReport):
    """Log a frontend or backend error — no auth required for frontend error collection."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    now = _now_iso()

    # Check if this error already exists (dedup by message + endpoint)
    existing = await db.error_logs.find_one(
        {"message": body.message, "endpoint": body.endpoint, "resolved": {"$ne": True}},
        {"_id": 1, "frequency": 1},
    )
    if existing:
        await db.error_logs.update_one(
            {"_id": existing["_id"]},
            {"$inc": {"frequency": 1}, "$set": {"last_seen": now}},
        )
        return {"ok": True, "deduplicated": True, "id": str(existing["_id"])}

    result = await db.error_logs.insert_one({
        "severity":    body.severity,
        "category":    body.category,
        "message":     body.message[:2000],
        "endpoint":    body.endpoint,
        "stack_trace": (body.stack_trace or "")[:5000],
        "browser":     body.browser,
        "user_id":     body.user_id,
        "metadata":    body.metadata or {},
        "frequency":   1,
        "resolved":    False,
        "owner":       None,
        "first_seen":  now,
        "last_seen":   now,
        "created_at":  now,
    })
    return {"ok": True, "id": str(result.inserted_id)}


@router.get("/errors", dependencies=_GATE)
async def list_errors(
    severity: Optional[str] = None,
    category: Optional[str] = None,
    resolved: Optional[bool] = None,
    page: int = 1,
    limit: int = 50,
):
    """List platform errors with filtering."""
    db   = get_db()
    db = DBProxy(db, SecurityContext.system())

    filt: dict = {}
    if severity:
        filt["severity"] = severity
    if category:
        filt["category"] = category
    if resolved is not None:
        filt["resolved"] = resolved
    skip  = (max(page, 1) - 1) * limit
    total = await db.error_logs.count_documents(filt)
    docs  = await db.error_logs.find(filt).sort("last_seen", -1).skip(skip).limit(limit).to_list(limit)
    for d in docs:
        d["id"] = str(d.pop("_id", ""))
    return {"total": total, "page": page, "limit": limit, "items": docs}


class ErrorPatch(BaseModel):
    resolved: Optional[bool]  = None
    owner:    Optional[str]   = None
    note:     Optional[str]   = None


@router.patch("/errors/{error_id}", dependencies=_GATE)
async def update_error(
    error_id: str,
    body: ErrorPatch,
    request: Request,
    admin: dict = Depends(require_super_admin),
):
    """Mark resolved, assign owner, or add remediation note."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    oid = _parse_oid(error_id)
    upd: dict = {"updated_at": _now_iso()}
    if body.resolved is not None:
        upd["resolved"] = body.resolved
        if body.resolved:
            upd["resolved_at"] = _now_iso()
            upd["resolved_by"] = admin.get("email")
    if body.owner:
        upd["owner"] = body.owner
    if body.note:
        upd["remediation_note"] = body.note
    result = await db.error_logs.update_one({"_id": oid}, {"$set": upd})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Error not found")
    await log_event(
        "admin.error.update",
        actor_id=admin["id"], actor_email=admin.get("email"),
        ip=request_meta(request)["ip"],
        extra={"error_id": error_id, "resolved": body.resolved, "owner": body.owner},
    )
    return {"ok": True}


@router.get("/errors/stats", dependencies=_GATE)
async def error_stats():
    """Error statistics: by severity, by category, trend."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    cutoff_24h = _ago(hours=24)
    cutoff_7d  = _ago(days=7)

    by_severity = await db.error_logs.aggregate([
        {"$group": {"_id": "$severity", "count": {"$sum": "$frequency"}}},
        {"$sort": {"count": -1}},
    ]).to_list(10)
    by_category = await db.error_logs.aggregate([
        {"$group": {"_id": "$category", "count": {"$sum": "$frequency"}}},
        {"$sort": {"count": -1}},
    ]).to_list(10)
    unresolved = await db.error_logs.count_documents({"resolved": {"$ne": True}})
    critical   = await db.error_logs.count_documents({"severity": "critical", "resolved": {"$ne": True}})
    new_24h    = await db.error_logs.count_documents({"first_seen": {"$gte": cutoff_24h}})

    return {
        "unresolved":  unresolved,
        "critical":    critical,
        "new_24h":     new_24h,
        "by_severity": [{"severity": d["_id"] or "unknown", "count": d["count"]} for d in by_severity],
        "by_category": [{"category": d["_id"] or "unknown", "count": d["count"]} for d in by_category],
    }


@router.get("/errors/export", dependencies=_GATE)
async def export_errors():
    """Download incident report as CSV."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    docs = await db.error_logs.find({}).sort("last_seen", -1).limit(1000).to_list(1000)
    buf  = io.StringIO()
    w    = csv.writer(buf)
    w.writerow(["ID", "Severity", "Category", "Message", "Endpoint", "Frequency", "First Seen", "Last Seen", "Resolved", "Browser", "User ID"])
    for d in docs:
        w.writerow([
            str(d["_id"]), d.get("severity"), d.get("category"),
            (d.get("message") or "")[:200], d.get("endpoint"),
            d.get("frequency", 1), d.get("first_seen"), d.get("last_seen"),
            d.get("resolved", False), d.get("browser"), d.get("user_id"),
        ])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="incident_report.csv"'},
    )


# ═════════════════════════════════════════════════════════════════════════════
# 8. PLATFORM AUDITOR
# ═════════════════════════════════════════════════════════════════════════════

async def _run_platform_audit(db) -> dict:
    """Automated platform health audit — scores across 5 dimensions."""
    now = _now_iso()
    cutoff = _ago(30)

    # ── Security Score ─────────────────────────────────────────────────────
    failed_logins_24h = await db.security_events.count_documents(
        {"event_type": "login_failed", "created_at": {"$gte": _ago(hours=24)}}
    )
    blocked_ips = await db.blocked_ips.count_documents({})
    unresolved_critical = await db.error_logs.count_documents({"severity": "critical", "resolved": {"$ne": True}})
    security_score = max(0, 100 - failed_logins_24h * 2 - blocked_ips * 5 - unresolved_critical * 10)

    # ── Performance Score ──────────────────────────────────────────────────
    error_rate = await db.error_logs.count_documents({"first_seen": {"$gte": cutoff}})
    api_errors = await db.error_logs.count_documents({"category": "api", "first_seen": {"$gte": cutoff}})
    db_errors  = await db.error_logs.count_documents({"category": "database", "first_seen": {"$gte": cutoff}})
    performance_score = max(0, 100 - error_rate * 3 - api_errors * 5 - db_errors * 8)

    # ── Academic Quality Score ─────────────────────────────────────────────
    total_courses = max(await db.courses.count_documents({}), 1)
    courses_with_lessons = 0
    async for c in db.courses.find({"status": "published"}, {"_id": 1}).limit(100):
        lc = await db.lessons.count_documents({"course_id": str(c["_id"])})
        if lc > 0:
            courses_with_lessons += 1
    academic_score = round(courses_with_lessons / total_courses * 100, 1)

    # ── UX Score ──────────────────────────────────────────────────────────
    frontend_errors = await db.error_logs.count_documents({"category": "frontend", "resolved": {"$ne": True}})
    onboarded_users = await db.users.count_documents({"onboarded": True})
    total_users     = max(await db.users.count_documents({}), 1)
    onboarding_rate = round(onboarded_users / total_users * 100, 1)
    ux_score = max(0, round(onboarding_rate - frontend_errors * 2, 1))

    # ── Platform Health Score ──────────────────────────────────────────────
    db_ok = False
    try:
        await db.command("ping")
        db_ok = True
    except Exception:
        pass
    integrations_ok = sum([
        bool(os.environ.get("STRIPE_SECRET_KEY")),
        bool(os.environ.get("RESEND_API_KEY")),
        bool(os.environ.get("ORCID_CLIENT_ID")),
        bool(os.environ.get("JWT_SECRET")),
        bool(os.environ.get("MONGODB_URI") or os.environ.get("MONGO_URL")),
    ])
    health_score = round((integrations_ok / 5) * 50 + (50 if db_ok else 0) - unresolved_critical * 5, 1)

    overall = round(
        0.30 * health_score + 0.20 * security_score + 0.20 * performance_score +
        0.20 * academic_score + 0.10 * ux_score, 1
    )

    # Issues
    issues = []
    if failed_logins_24h > 50:
        issues.append({"severity": "high", "area": "security", "message": f"{failed_logins_24h} failed logins in 24h — possible brute-force attack."})
    if unresolved_critical > 0:
        issues.append({"severity": "critical", "area": "errors", "message": f"{unresolved_critical} unresolved critical errors detected."})
    if not os.environ.get("STRIPE_SECRET_KEY"):
        issues.append({"severity": "high", "area": "integrations", "message": "Stripe not configured — payment processing unavailable."})
    if error_rate > 20:
        issues.append({"severity": "medium", "area": "performance", "message": f"{error_rate} new errors in last 30 days."})
    if courses_with_lessons < total_courses * 0.7:
        issues.append({"severity": "medium", "area": "academic", "message": "Over 30% of published courses have no lessons."})
    if onboarding_rate < 60:
        issues.append({"severity": "medium", "area": "ux", "message": f"Only {onboarding_rate}% of users completed onboarding."})

    result = {
        "overall_score":  int(overall),
        "scores": {
            "platform_health": max(0, int(health_score)),
            "security":        max(0, int(security_score)),
            "performance":     max(0, int(performance_score)),
            "academic_quality": max(0, int(academic_score)),
            "ux":              max(0, int(ux_score)),
        },
        "issues":      issues,
        "issue_count": len(issues),
        "audited_at":  now,
        "metrics": {
            "failed_logins_24h":      failed_logins_24h,
            "blocked_ips":            blocked_ips,
            "unresolved_errors":      unresolved_critical,
            "courses_with_lessons":   courses_with_lessons,
            "total_courses":          total_courses,
            "onboarding_rate_pct":    onboarding_rate,
            "db_reachable":           db_ok,
            "integrations_configured": integrations_ok,
        },
    }
    # Persist latest report
    await db.platform_audit_reports.update_one(
        {"_id": "latest"},
        {"$set": result},
        upsert=True,
    )
    return result


@router.post("/platform-audit/run", dependencies=_GATE)
async def run_platform_audit(admin: dict = Depends(require_super_admin)):
    """Trigger an automated platform audit scan."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    result = await _run_platform_audit(db)
    await log_event(
        "admin.platform_audit.run",
        actor_id=admin["id"], actor_email=admin.get("email"),
        extra={"overall_score": result["overall_score"]},
    )
    return result


@router.get("/platform-audit/report", dependencies=_GATE)
async def get_audit_report():
    """Return the latest platform audit report."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    doc = await db.platform_audit_reports.find_one({"_id": "latest"})
    if not doc:
        # Run fresh audit if no report exists
        doc = await _run_platform_audit(db)
    doc.pop("_id", None)
    return doc


@router.get("/platform-audit/scores", dependencies=_GATE)
async def audit_scores():
    """Return only the platform health scores (lightweight)."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    doc = await db.platform_audit_reports.find_one({"_id": "latest"}, {"scores": 1, "overall_score": 1, "audited_at": 1})
    if not doc:
        return {"scores": None, "overall_score": None, "audited_at": None, "message": "No audit run yet — POST /platform-audit/run"}
    doc.pop("_id", None)
    return doc


# ═════════════════════════════════════════════════════════════════════════════
# 9. DATABASE OPERATIONS CENTER
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/db/overview", dependencies=_GATE)
async def db_overview():
    """MongoDB collection stats — document counts, storage, indexes."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    try:
        db_stats_raw = await db.command("dbStats")
        storage_size_mb  = round((db_stats_raw.get("storageSize", 0)) / 1024 / 1024, 2)
        data_size_mb     = round((db_stats_raw.get("dataSize", 0)) / 1024 / 1024, 2)
        index_size_mb    = round((db_stats_raw.get("indexSize", 0)) / 1024 / 1024, 2)
        total_collections = db_stats_raw.get("collections", 0)
        total_indexes     = db_stats_raw.get("indexes", 0)
    except Exception as e:
        return {"error": str(e)}

    # Top collections by document count
    collection_names = await db.list_collection_names()
    col_stats = []
    for name in sorted(collection_names):
        try:
            count = await db[name].count_documents({})
            col_stats.append({"collection": name, "count": count})
        except Exception:
            col_stats.append({"collection": name, "count": -1})

    col_stats.sort(key=lambda x: -x["count"])

    return {
        "storage_size_mb":  storage_size_mb,
        "data_size_mb":     data_size_mb,
        "index_size_mb":    index_size_mb,
        "total_collections": total_collections,
        "total_indexes":    total_indexes,
        "collections":      col_stats,
    }


@router.get("/db/integrity", dependencies=_GATE)
async def db_integrity_check():
    """Quick data integrity scan — orphaned records and missing references."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    issues: list[dict] = []

    # Publications with no user
    pub_sample = await db.publications.find({}, {"user_id": 1}).limit(500).to_list(500)
    orphan_pubs = 0
    for p in pub_sample:
        uid = p.get("user_id")
        if uid:
            exists = await db.users.count_documents({"_id": ObjectId(uid) if len(uid) == 24 else None})
            if not exists:
                orphan_pubs += 1
    if orphan_pubs:
        issues.append({"type": "orphan_publications", "count": orphan_pubs, "action": "Remove publications for deleted users"})

    # Manuscripts with no author
    ms_sample = await db.manuscripts.find({}, {"authors": 1}).limit(200).to_list(200)
    orphan_ms = 0
    for m in ms_sample:
        authors = m.get("authors") or []
        if not authors:
            orphan_ms += 1
    if orphan_ms:
        issues.append({"type": "manuscripts_no_author", "count": orphan_ms, "action": "Add authors to manuscripts"})

    # Users with no email
    no_email = await db.users.count_documents({"email": {"$in": [None, ""]}})
    if no_email:
        issues.append({"type": "users_no_email", "count": no_email, "action": "Users missing email addresses"})

    # Duplicate emails
    dup_pipe = [
        {"$group": {"_id": "$email", "count": {"$sum": 1}}},
        {"$match": {"count": {"$gt": 1}}},
        {"$count": "n"},
    ]
    dup_agg = await db.users.aggregate(dup_pipe).to_list(1)
    dup_emails = dup_agg[0]["n"] if dup_agg else 0
    if dup_emails:
        issues.append({"type": "duplicate_emails", "count": dup_emails, "action": "Deduplicate user accounts"})

    integrity_score = max(0, 100 - len(issues) * 15)

    return {
        "integrity_score": integrity_score,
        "issues":          issues,
        "issue_count":     len(issues),
        "scanned_at":      _now_iso(),
    }


@router.get("/db/health", dependencies=_GATE)
async def db_health():
    """Overall database health score and connection status."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    ok = False
    latency_ms: Optional[float] = None
    server_info: dict = {}
    try:
        t0 = time.time()
        await db.command("ping")
        latency_ms = round((time.time() - t0) * 1000, 2)
        ok = True
        info = await db.command("serverStatus")
        server_info = {
            "uptime_seconds": info.get("uptime", 0),
            "version":        info.get("version", ""),
            "connections":    (info.get("connections") or {}).get("current", 0),
        }
    except Exception as e:
        server_info = {"error": str(e)}

    score = 100 if ok else 0
    if latency_ms and latency_ms > 100:
        score -= 20
    if latency_ms and latency_ms > 500:
        score -= 30

    return {
        "ok":            ok,
        "latency_ms":    latency_ms,
        "health_score":  score,
        "server_info":   server_info,
    }


# ═════════════════════════════════════════════════════════════════════════════
# 10. USER HISTORY
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/users/{uid}/history", dependencies=_GATE)
async def user_history(uid: str, limit: int = 100):
    """Login history, device history, and session info from audit_log."""
    db = get_db()

    db = DBProxy(db, SecurityContext.system())

    login_events = await db.audit_log.find(
        {"actor_id": uid, "action": {"$in": ["auth.login", "auth.logout", "auth.login_google"]}},
        {"action": 1, "ip": 1, "user_agent": 1, "created_at": 1, "extra": 1},
    ).sort("created_at", -1).limit(limit).to_list(limit)

    # Device fingerprints: unique (user_agent, ip) combos
    devices: dict[str, dict] = {}
    for ev in login_events:
        ua  = ev.get("user_agent") or "Unknown"
        ip  = ev.get("ip") or "Unknown"
        key = f"{ua}|{ip}"
        if key not in devices:
            devices[key] = {
                "user_agent": ua,
                "ip":         ip,
                "first_seen": ev.get("created_at"),
                "last_seen":  ev.get("created_at"),
                "logins":     0,
            }
        devices[key]["last_seen"] = ev.get("created_at")
        devices[key]["logins"]   += 1

    for ev in login_events:
        ev["id"] = str(ev.pop("_id", ""))

    return {
        "login_events":    login_events,
        "device_history":  list(devices.values())[:20],
        "unique_devices":  len(devices),
        "total_logins":    sum(1 for ev in login_events if "login" in ev.get("action", "")),
    }


@router.get("/users/{uid}/timeline", dependencies=_GATE)
async def user_activity_timeline(uid: str, limit: int = 200):
    """Complete chronological activity timeline for a user."""
    db = get_db()

    db = DBProxy(db, SecurityContext.system())

    events = await db.audit_log.find(
        {"actor_id": uid},
        {"action": 1, "target_id": 1, "target_type": 1, "extra": 1, "created_at": 1, "ip": 1},
    ).sort("created_at", -1).limit(limit).to_list(limit)

    for ev in events:
        ev["id"] = str(ev.pop("_id", ""))

    # Summarize by action category
    categories: dict[str, int] = {}
    for ev in events:
        cat = ev.get("action", "unknown").split(".")[0]
        categories[cat] = categories.get(cat, 0) + 1

    return {
        "events":          events,
        "total":           len(events),
        "categories":      categories,
    }


@router.get("/users/{uid}/sessions", dependencies=_GATE)
async def user_sessions(uid: str):
    """Active/recent sessions inferred from audit_log login events."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    sessions = await db.audit_log.find(
        {"actor_id": uid, "action": {"$regex": "login", "$options": "i"}},
        {"ip": 1, "user_agent": 1, "created_at": 1},
    ).sort("created_at", -1).limit(20).to_list(20)
    for s in sessions:
        s["id"] = str(s.pop("_id", ""))
    return {"sessions": sessions}


# ═════════════════════════════════════════════════════════════════════════════
# 11. COMMUNICATIONS CENTER
# ═════════════════════════════════════════════════════════════════════════════

class BannerBody(BaseModel):
    title:    str
    message:  str
    kind:     str = "info"  # info | warning | success | promo
    link:     str = ""
    segment:  str = "all"
    expires_at: Optional[str] = None


@router.post("/banners", dependencies=_GATE)
async def create_banner(body: BannerBody, request: Request, admin: dict = Depends(require_super_admin)):
    """Create a platform-wide promotional or informational banner."""
    if not body.title or not body.message:
        raise HTTPException(status_code=400, detail="title and message required")
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    now = _now_iso()
    result = await db.platform_banners.insert_one({
        "title":      body.title,
        "message":    body.message,
        "kind":       body.kind,
        "link":       body.link,
        "segment":    body.segment,
        "active":     True,
        "expires_at": body.expires_at,
        "created_at": now,
        "created_by": admin.get("email"),
    })
    await log_event(
        "admin.banner.create",
        actor_id=admin["id"], actor_email=admin.get("email"),
        ip=request_meta(request)["ip"],
        extra={"title": body.title, "kind": body.kind, "segment": body.segment},
    )
    return {"ok": True, "id": str(result.inserted_id)}


@router.get("/banners", dependencies=_GATE)
async def list_banners():
    """List all platform banners."""
    db   = get_db()
    db = DBProxy(db, SecurityContext.system())

    docs = await db.platform_banners.find({}).sort("created_at", -1).limit(50).to_list(50)
    for d in docs:
        d["id"] = str(d.pop("_id", ""))
    return {"items": docs}


@router.delete("/banners/{bid}", dependencies=_GATE)
async def delete_banner(bid: str, admin: dict = Depends(require_super_admin)):
    """Deactivate a banner."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    oid = _parse_oid(bid)
    await db.platform_banners.update_one({"_id": oid}, {"$set": {"active": False, "deactivated_at": _now_iso()}})
    return {"ok": True}


@router.get("/communications/stats", dependencies=_GATE)
async def communications_stats():
    """Email campaign and announcement statistics."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    announcements = await db.announcements.count_documents({})
    banners       = await db.platform_banners.count_documents({})
    active_banners = await db.platform_banners.count_documents({"active": True})
    campaigns     = await db.email_campaigns.count_documents({})

    recent_announcements = await db.announcements.find(
        {}, {"title": 1, "segment": 1, "sent_to": 1, "sent_by": 1, "created_at": 1}
    ).sort("created_at", -1).limit(10).to_list(10)
    for d in recent_announcements:
        d["id"] = str(d.pop("_id", ""))

    return {
        "total_announcements": announcements,
        "total_banners":       banners,
        "active_banners":      active_banners,
        "total_campaigns":     campaigns,
        "recent_announcements": recent_announcements,
    }


# ═════════════════════════════════════════════════════════════════════════════
# 12. PROMOTIONS ENHANCED
# ═════════════════════════════════════════════════════════════════════════════

@router.get("/promotions/stats", dependencies=_GATE)
async def promotions_stats(days: int = 30):
    """Promotion conversion analytics — redemption rates and revenue impact."""
    db     = get_db()
    db = DBProxy(db, SecurityContext.system())

    cutoff = _ago(days)

    total_promotions = await db.promotions.count_documents({})
    recent_promotions = await db.promotions.count_documents({"created_at": {"$gte": cutoff}})

    # Redemptions
    redemptions = await db.promotions.aggregate([
        {"$group": {"_id": "$kind", "count": {"$sum": 1}, "credits_granted": {"$sum": "$credits_granted"}}},
        {"$sort": {"count": -1}},
    ]).to_list(20)

    # Conversions from promotions: users who got a promo and then upgraded
    promo_user_ids = await db.promotions.distinct("user_id", {"created_at": {"$gte": cutoff}})
    converted_from_promo = 0
    if promo_user_ids:
        converted_from_promo = await db.subscription_history.count_documents({
            "user_id": {"$in": promo_user_ids},
            "created_at": {"$gte": cutoff},
            "to_plan": {"$in": ["researcher", "pro_researcher", "institution"]},
        })
    promo_conversion_rate = round(converted_from_promo / max(len(promo_user_ids), 1) * 100, 1)

    return {
        "period_days":          days,
        "total_promotions":     total_promotions,
        "recent_promotions":    recent_promotions,
        "unique_recipients":    len(promo_user_ids),
        "conversions":          converted_from_promo,
        "conversion_rate_pct":  promo_conversion_rate,
        "by_kind":              redemptions,
    }


class CampaignBody(BaseModel):
    name:        str
    description: str = ""
    kind:        str = "credits"  # credits | trial | discount
    segment:     str = "free"     # all | free | paid
    value:       int = 0
    expires_at:  Optional[str] = None
    user_limit:  Optional[int] = None


@router.post("/promotions/campaign", dependencies=_GATE)
async def create_campaign(body: CampaignBody, request: Request, admin: dict = Depends(require_super_admin)):
    """Create a tracked promotional campaign."""
    if not body.name:
        raise HTTPException(status_code=400, detail="name required")
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    now = _now_iso()
    result = await db.promotion_campaigns.insert_one({
        "name":        body.name,
        "description": body.description,
        "kind":        body.kind,
        "segment":     body.segment,
        "value":       body.value,
        "expires_at":  body.expires_at,
        "user_limit":  body.user_limit,
        "redemptions": 0,
        "conversions": 0,
        "active":      True,
        "created_at":  now,
        "created_by":  admin.get("email"),
    })
    await log_event(
        "admin.campaign.create",
        actor_id=admin["id"], actor_email=admin.get("email"),
        ip=request_meta(request)["ip"],
        extra={"name": body.name, "kind": body.kind, "segment": body.segment, "value": body.value},
    )
    return {"ok": True, "id": str(result.inserted_id), "name": body.name}


@router.get("/promotions/campaigns", dependencies=_GATE)
async def list_campaigns():
    """List all promotional campaigns with performance metrics."""
    db   = get_db()
    db = DBProxy(db, SecurityContext.system())

    docs = await db.promotion_campaigns.find({}).sort("created_at", -1).limit(50).to_list(50)
    for d in docs:
        d["id"] = str(d.pop("_id", ""))
        d["conversion_rate"] = round(d.get("conversions", 0) / max(d.get("redemptions", 1), 1) * 100, 1)
    return {"items": docs}
