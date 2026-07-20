"""Admin Growth Engine — SUPER_ADMIN endpoints for promotions, engagement, analytics, audit."""
import asyncio
from fastapi import APIRouter, Depends, Request, HTTPException

from services.permissions import require_super_admin
from services.promotions import issue_promotion, list_promotions
from services.engagement import compute_engagement, platform_analytics
from db import get_db
from repo.shim import DBProxy
from repo.security_context import SecurityContext

router = APIRouter(prefix="/api/admin", tags=["admin-growth"])


# ---------------- Promotions ----------------

@router.post("/promotions", dependencies=[Depends(require_super_admin)])
async def admin_issue_promotion(payload: dict, request: Request,
                                 user: dict = Depends(require_super_admin)):
    rec = await issue_promotion(
        actor=user,
        target_user_id=payload.get("target_user_id"),
        target_email=payload.get("target_email"),
        kind=payload.get("kind"),
        payload=payload.get("payload", {}),
    )
    return rec


@router.get("/promotions", dependencies=[Depends(require_super_admin)])
async def admin_list_promotions(target_user_id: str | None = None, limit: int = 100):
    return await list_promotions(target_user_id=target_user_id, limit=limit)


# ---------------- Engagement ----------------

@router.get("/engagement/{uid}", dependencies=[Depends(require_super_admin)])
async def admin_engagement(uid: str):
    return await compute_engagement(uid)


@router.get("/engagement", dependencies=[Depends(require_super_admin)])
async def admin_engagement_overview(limit: int = 200):
    """Returns precomputed engagement scores stored on user documents.

    Scores are written by compute_engagement() (called per-user via
    GET /api/admin/engagement/{uid}) or via the refresh-all endpoint below.
    This avoids the N+1 query pattern at scale.
    """
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    cursor = db.users.find(
        {},
        {"_id": 1, "email": 1, "engagement_tier": 1, "engagement_score": 1, "engagement_computed_at": 1},
    ).sort("engagement_score", -1).limit(limit)
    users_data = await cursor.to_list(limit)
    out = [
        {
            "user_id": str(u["_id"]),
            "email": u.get("email", ""),
            "tier": u.get("engagement_tier", "unknown"),
            "score": u.get("engagement_score", 0),
            "computed_at": u.get("engagement_computed_at"),
        }
        for u in users_data
    ]
    buckets: dict = {}
    for r in out:
        buckets[r["tier"]] = buckets.get(r["tier"], 0) + 1
    return {"users": out, "tier_counts": buckets}


@router.post("/engagement/refresh-all", dependencies=[Depends(require_super_admin)])
async def refresh_all_engagement():
    """Batch-recompute engagement scores for all users (runs synchronously, may be slow).

    Call this once after deploy to warm the precomputed scores. Subsequent
    individual calls to GET /api/admin/engagement/{uid} keep them fresh.
    """
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    user_ids = await db.users.distinct("_id")
    refreshed = 0
    failed = 0
    for uid in user_ids:
        try:
            await compute_engagement(str(uid))
            refreshed += 1
        except Exception:
            failed += 1
    return {"ok": True, "refreshed": refreshed, "failed": failed}


# ---------------- Analytics ----------------

@router.get("/analytics", dependencies=[Depends(require_super_admin)])
async def admin_analytics():
    return await platform_analytics()


# ---------------- Audit log ----------------

@router.get("/audit", dependencies=[Depends(require_super_admin)])
async def admin_audit(
    page: int = 1,
    limit: int = 50,
    action: str | None = None,
    actor_id: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    q: dict = {}
    if action:
        q["action"] = action
    if actor_id:
        q["actor_id"] = actor_id
    date_filter: dict = {}
    if from_date:
        date_filter["$gte"] = from_date
    if to_date:
        date_filter["$lte"] = to_date + "T23:59:59Z"
    if date_filter:
        q["created_at"] = date_filter
    skip = (max(page, 1) - 1) * limit
    total = await db.audit_log.count_documents(q)
    docs = await db.audit_log.find(q).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    out = []
    for d in docs:
        d["id"] = str(d.pop("_id"))
        out.append(d)
    return {"total": total, "items": out}
