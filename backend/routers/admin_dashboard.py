"""Admin Control Center — dashboard aggregations."""
from __future__ import annotations
import asyncio
import os
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends
from db import get_db
from services.permissions import require_super_admin
from repo.shim import DBProxy
from repo.security_context import SecurityContext

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _ago_iso(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def _today_iso() -> str:
    t = datetime.now(timezone.utc)
    return datetime(t.year, t.month, t.day, tzinfo=timezone.utc).isoformat()


@router.get("/dashboard", dependencies=[Depends(require_super_admin)])
async def admin_dashboard():
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    today = _today_iso()
    week_ago = _ago_iso(7)
    month_ago = _ago_iso(30)

    # Run all aggregations in parallel
    (
        total_users, free_users, researcher_users, pro_researcher_users, institution_users,
        orcid_users, verified_users, onboarded_users, suspended_users, banned_users,
        new_today, new_week, new_month,
        total_projects, projects_month,
        total_workspaces, workspaces_month,
        total_collabs, active_collabs,
        total_manuscripts,
        total_publications,
        lit_reviews_month, gap_reviews_month, manuscript_reviews_month, stat_reviews_month, design_reviews_month,
    ) = await asyncio.gather(
        db.users.count_documents({}),
        db.users.count_documents({"plan_code": "free"}),
        db.users.count_documents({"plan_code": "researcher"}),
        db.users.count_documents({"plan_code": "pro_researcher"}),
        db.users.count_documents({"plan_code": "institution"}),
        db.users.count_documents({"orcid.orcid_id": {"$exists": True, "$ne": None}}),
        db.users.count_documents({"email_verified": True}),
        db.users.count_documents({"onboarded": True}),
        db.users.count_documents({"status": "suspended"}),
        db.users.count_documents({"status": "banned"}),
        db.users.count_documents({"created_at": {"$gte": today}}),
        db.users.count_documents({"created_at": {"$gte": week_ago}}),
        db.users.count_documents({"created_at": {"$gte": month_ago}}),
        db.projects.count_documents({}),
        db.projects.count_documents({"created_at": {"$gte": month_ago}}),
        db.workspaces.count_documents({}),
        db.workspaces.count_documents({"created_at": {"$gte": month_ago}}),
        db.collaborations.count_documents({}),
        db.collaborations.count_documents({"status": "active"}),
        db.manuscripts.count_documents({}),
        db.publications.count_documents({}),
        db.literature_reviews.count_documents({"created_at": {"$gte": month_ago}}),
        db.research_gap_reviews.count_documents({"created_at": {"$gte": month_ago}}),
        db.manuscript_reviews.count_documents({"created_at": {"$gte": month_ago}}),
        db.statistical_reviews.count_documents({"created_at": {"$gte": month_ago}}),
        db.research_design_reviews.count_documents({"created_at": {"$gte": month_ago}}),
    )

    # Financial aggregations (sequential — depend on same collections)
    active_subscribers = researcher_users + pro_researcher_users + institution_users

    credits_pipe = [
        {"$match": {"kind": "consume", "created_at": {"$gte": month_ago}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]
    credits_agg = await db.credit_transactions.aggregate(credits_pipe).to_list(1)
    credits_consumed_30d = credits_agg[0]["total"] if credits_agg else 0

    purchased_pipe = [
        {"$match": {"created_at": {"$gte": month_ago}, "status": "paid"}},
        {"$group": {"_id": None, "credits": {"$sum": "$credits"}}},
    ]
    purchased_agg = await db.credit_purchases.aggregate(purchased_pipe).to_list(1)
    credits_purchased_30d = purchased_agg[0]["credits"] if purchased_agg else 0

    pack_rev_pipe = [
        {"$match": {"kind": "pack_purchase", "created_at": {"$gte": month_ago}, "status": "paid"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount_eur"}}},
    ]
    pack_rev_agg = await db.billing_history.aggregate(pack_rev_pipe).to_list(1)
    pack_revenue_30d = round((pack_rev_agg[0]["total"] or 0) if pack_rev_agg else 0.0, 2)

    churn_pipe = [
        {"$match": {"created_at": {"$gte": month_ago}, "from_plan": {"$in": ["researcher", "pro_researcher", "institution"]}, "to_plan": {"$in": [None, "free"]}}},
        {"$count": "n"},
    ]
    churn_agg = await db.subscription_history.aggregate(churn_pipe).to_list(1)
    churned_30d = churn_agg[0]["n"] if churn_agg else 0
    churn_rate = round((churned_30d / max(active_subscribers, 1)) * 100, 2)

    # MRR — import PLANS dynamically to avoid circular deps
    from plans_catalogue import PLANS, get_plan
    mrr = 0.0
    for p in PLANS:
        if p["code"] == "free":
            continue
        cnt = {"researcher": researcher_users, "pro_researcher": pro_researcher_users, "institution": institution_users}.get(p["code"], 0)
        plan = get_plan(p["code"])
        mrr += cnt * float(plan.get("price_eur_monthly", 0))

    # AI requests (credit_transactions consume events in last 30d as proxy)
    ai_pipe = [
        {"$match": {"created_at": {"$gte": month_ago}, "kind": "consume"}},
        {"$count": "n"},
    ]
    ai_agg = await db.credit_transactions.aggregate(ai_pipe).to_list(1)
    ai_requests_month = ai_agg[0]["n"] if ai_agg else 0

    # Messages in last 30 days
    messages_month = await db.messages.count_documents({"created_at": {"$gte": month_ago}})

    # Active today (users who logged in today per audit_log)
    active_today_pipe = [
        {"$match": {"action": "auth.login", "created_at": {"$gte": today}}},
        {"$group": {"_id": "$actor_id"}},
        {"$count": "n"},
    ]
    active_today_agg = await db.audit_log.aggregate(active_today_pipe).to_list(1)
    active_today = active_today_agg[0]["n"] if active_today_agg else 0

    # System health
    db_ok = False
    try:
        await db.command("ping")
        db_ok = True
    except Exception:
        pass

    return {
        "users": {
            "total": total_users,
            "new_today": new_today,
            "new_week": new_week,
            "new_month": new_month,
            "free": free_users,
            "researcher": researcher_users,
            "pro_researcher": pro_researcher_users,
            "institution": institution_users,
            "orcid_connected": orcid_users,
            "email_verified": verified_users,
            "onboarded": onboarded_users,
            "suspended": suspended_users,
            "banned": banned_users,
            "active_today": active_today,
        },
        "engagement": {
            "projects_total": total_projects,
            "projects_month": projects_month,
            "workspaces_total": total_workspaces,
            "workspaces_month": workspaces_month,
            "collaborations_total": total_collabs,
            "collaborations_active": active_collabs,
            "manuscripts_total": total_manuscripts,
            "messages_month": messages_month,
            "ai_requests_month": ai_requests_month,
        },
        "research": {
            "publications_total": total_publications,
            "literature_reviews_month": lit_reviews_month,
            "gap_reviews_month": gap_reviews_month,
            "manuscript_reviews_month": manuscript_reviews_month,
            "stat_reviews_month": stat_reviews_month,
            "design_reviews_month": design_reviews_month,
        },
        "financial": {
            "mrr_eur": round(mrr, 2),
            "arr_eur": round(mrr * 12, 2),
            "active_subscribers": active_subscribers,
            "credits_consumed_30d": credits_consumed_30d,
            "credits_purchased_30d": credits_purchased_30d,
            "pack_revenue_30d_eur": pack_revenue_30d,
            "churned_30d": churned_30d,
            "churn_rate_pct": churn_rate,
        },
        "system": {
            "db_ok": db_ok,
            "email_configured": bool(os.environ.get("RESEND_API_KEY") and os.environ.get("EMAIL_FROM")),
            "orcid_configured": bool(os.environ.get("ORCID_CLIENT_ID")),
            "stripe_configured": bool(os.environ.get("STRIPE_SECRET_KEY")),
        },
    }
