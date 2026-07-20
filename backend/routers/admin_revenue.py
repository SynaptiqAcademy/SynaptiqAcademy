"""Admin Revenue Dashboard endpoints — SUPER_ADMIN only.

Returns aggregate KPIs: MRR/ARR, plan breakdown, churn approximation, credit
volume. All numbers computed from MongoDB aggregations (no mocks).
"""
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends

from db import get_db
from plans_catalogue import PLANS, get_plan
from services.permissions import require_super_admin
from repo.shim import DBProxy
from repo.security_context import SecurityContext

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _ago_iso(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


@router.get("/revenue", dependencies=[Depends(require_super_admin)])
async def revenue_dashboard():
    db = get_db()

    db = DBProxy(db, SecurityContext.system())

    # ---- User counts by plan ----
    plan_codes = [p["code"] for p in PLANS]
    plan_counts = {}
    for code in plan_codes:
        plan_counts[code] = await db.users.count_documents({"plan_code": code})
    total_users = await db.users.count_documents({})
    active_subscribers = sum(plan_counts[c] for c in plan_codes if c != "free")

    # ---- MRR / ARR ----
    mrr = 0.0
    for code in plan_codes:
        plan = get_plan(code)
        if code == "free":
            continue
        # Approximation: assume monthly billing for everyone; annual subs would
        # still amortise to the same monthly run-rate.
        mrr += plan_counts[code] * float(plan["price_eur_monthly"])
    arr = mrr * 12.0

    # ---- Credits volume (last 30 days) ----
    cutoff = _ago_iso(30)
    consumed_pipeline = [
        {"$match": {"kind": "consume", "created_at": {"$gte": cutoff}}},
        {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
    ]
    consumed = await db.credit_transactions.aggregate(consumed_pipeline).to_list(1)
    credits_consumed_30d = (consumed[0]["total"] if consumed else 0)

    purchased_pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}, "status": "paid"}},
        {"$group": {"_id": None, "credits": {"$sum": "$credits"}, "count": {"$sum": 1}}},
    ]
    purch = await db.credit_purchases.aggregate(purchased_pipeline).to_list(1)
    credits_purchased_30d = (purch[0]["credits"] if purch else 0)
    pack_purchases_30d = (purch[0]["count"] if purch else 0)

    # ---- Pack purchase revenue (30d) ----
    pack_revenue_pipeline = [
        {"$match": {"kind": "pack_purchase", "created_at": {"$gte": cutoff}, "status": "paid"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount_eur"}}},
    ]
    pr = await db.billing_history.aggregate(pack_revenue_pipeline).to_list(1)
    pack_revenue_30d = round((pr[0]["total"] or 0) if pr else 0.0, 2)

    # ---- Churn approximation (last 30 days) ----
    # Subscriptions transitioned away from a paid plan in last 30 days
    churn_pipeline = [
        {"$match": {"created_at": {"$gte": cutoff},
                    "from_plan": {"$in": ["researcher", "pro_researcher", "institution"]},
                    "to_plan":   {"$in": [None, "free"]}}},
        {"$count": "n"},
    ]
    ch = await db.subscription_history.aggregate(churn_pipeline).to_list(1)
    churned_30d = (ch[0]["n"] if ch else 0)
    churn_rate = round((churned_30d / max(active_subscribers, 1)) * 100, 2)

    # ---- Revenue trend (last 12 weeks, weekly buckets) ----
    weeks = []
    for w in range(11, -1, -1):
        start = _ago_iso((w + 1) * 7)
        end = _ago_iso(w * 7)
        wpipe = [
            {"$match": {"created_at": {"$gte": start, "$lt": end},
                        "kind": {"$in": ["pack_purchase", "invoice"]},
                        "status": "paid"}},
            {"$group": {"_id": None, "total": {"$sum": "$amount_eur"}}},
        ]
        wr = await db.billing_history.aggregate(wpipe).to_list(1)
        weeks.append({"week_start": start[:10], "amount_eur": round((wr[0]["total"] or 0) if wr else 0.0, 2)})

    return {
        "users": {
            "total": total_users,
            "free": plan_counts.get("free", 0),
            "researcher": plan_counts.get("researcher", 0),
            "pro_researcher": plan_counts.get("pro_researcher", 0),
            "institution": plan_counts.get("institution", 0),
            "active_subscribers": active_subscribers,
        },
        "revenue": {
            "mrr_eur": round(mrr, 2),
            "arr_eur": round(arr, 2),
            "pack_revenue_30d_eur": pack_revenue_30d,
        },
        "credits": {
            "consumed_30d": credits_consumed_30d,
            "purchased_30d": credits_purchased_30d,
            "pack_purchases_30d": pack_purchases_30d,
        },
        "churn": {
            "churned_30d": churned_30d,
            "churn_rate_pct": churn_rate,
        },
        "revenue_trend_weekly": weeks,
    }


@router.get("/users-overview", dependencies=[Depends(require_super_admin)])
async def users_overview(limit: int = 50):
    """Recent users with plan + status snapshot for an admin table."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    cursor = db.users.find({}, {
        "email": 1, "full_name": 1, "plan_code": 1, "subscription_status": 1,
        "credits_balance": 1, "credits_pack_balance": 1, "created_at": 1,
        "email_verified": 1, "onboarded": 1, "role": 1,
    }).sort("created_at", -1).limit(limit)
    out = []
    async for u in cursor:
        out.append({
            "id": str(u["_id"]),
            "email": u.get("email"),
            "name": u.get("full_name"),
            "plan": u.get("plan_code", "free"),
            "subscription_status": u.get("subscription_status"),
            "credits_monthly": u.get("credits_balance", 0),
            "credits_pack": u.get("credits_pack_balance", 0),
            "email_verified": u.get("email_verified", False),
            "onboarded": u.get("onboarded", False),
            "role": u.get("role", "user"),
            "created_at": u.get("created_at"),
        })
    return out
