"""Discovery quota status — returns current-month usage for journal/conference/grant discovery.

Used by the frontend DiscoveryShell to display a live quota indicator for free-plan users
(e.g. "3 / 5 journal searches used this month"). Paid plans return null limits (unlimited).

GET /api/discovery/quota
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from auth_utils import get_current_user
from db import get_db
from plans_catalogue import get_plan
from repo.shim import DBProxy
from repo.security_context import SecurityContext

router = APIRouter(prefix="/api/discovery", tags=["discovery-quota"])

_LIMIT_KEYS = {
    "journal":    "journal_recs_per_month",
    "conference": "conference_recs_per_month",
    "grant":      "grant_recs_per_month",
}


@router.get("/quota")
async def get_discovery_quota(user: dict = Depends(get_current_user)):
    """Return this user's discovery quota usage for the current calendar month.

    Response shape:
      { month: "YYYY-MM", plan: "free", quota: {
          journal:    { used: 3, limit: 5 },
          conference: { used: 1, limit: 5 },
          grant:      { used: 0, limit: 3 },
      }}

    For paid plans (researcher+), `used` and `limit` are both null (unlimited).
    """
    plan_code = user.get("plan_code") or "free"
    plan = get_plan(plan_code)
    limits = plan.get("limits") or {}
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    quota: dict = {}
    for kind, limit_key in _LIMIT_KEYS.items():
        limit = limits.get(limit_key, -1)
        if limit == -1:
            quota[kind] = {"used": None, "limit": None}
        else:
            doc = await db.discovery_usage.find_one(
                {"user_id": user["id"], "kind": kind, "month": month}
            )
            quota[kind] = {"used": (doc or {}).get("count", 0), "limit": limit}

    return {"month": month, "plan": plan_code, "quota": quota}
