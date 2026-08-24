"""Admin Platform Reset — pre-launch "wipe every account but mine" tool.

Built for the pre-payments testing period: the founder is the only real user
while Stripe billing isn't live yet, and needs a way to clear out any
accounts/data created during testing without touching the protected
super-admin account.

Reuses _purge_user_owned_data() from admin_data_governance.py (the same
cascade the single-account GDPR "purge" endpoint uses) so there's one
definition of "every collection a user owns data in" — then additionally
clears audit_log/security_events rows referencing the deleted accounts,
since this tool's whole purpose is a full wipe, unlike the individual GDPR
purge which intentionally keeps a compliance trail.

Endpoints:
  GET  /api/admin/platform-reset/preview  — list every account that WOULD be deleted
  POST /api/admin/platform-reset/execute  — hard-delete those accounts and their data
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from db import get_db
from routers.admin_data_governance import _purge_user_owned_data
from services.admin_audit import log_event, request_meta
from services.permissions import require_super_admin, PROTECTED_SUPER_ADMIN_EMAIL
from repo.shim import DBProxy
from repo.security_context import SecurityContext

router = APIRouter(prefix="/api/admin/platform-reset", tags=["admin-platform-reset"])
_GATE = [Depends(require_super_admin)]

_CONFIRM_PHRASE = "RESET"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/preview", dependencies=_GATE)
async def preview_reset():
    """List every account that a reset would delete, so the admin can review
    the exact scope before confirming — nothing is deleted here."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    cursor = db.users.find(
        {"email": {"$ne": PROTECTED_SUPER_ADMIN_EMAIL}},
        {"email": 1, "full_name": 1, "role": 1, "plan_code": 1, "created_at": 1, "is_demo": 1},
    ).sort("created_at", 1)
    accounts = await cursor.to_list(2000)
    for a in accounts:
        a["id"] = str(a.pop("_id"))
    return {"count": len(accounts), "accounts": accounts}


class ResetBody(BaseModel):
    confirm: str


@router.post("/execute", dependencies=_GATE)
async def execute_reset(body: ResetBody, request: Request, admin: dict = Depends(require_super_admin)):
    """Hard-deletes every account except the protected super-admin, and every
    piece of data those accounts own. Irreversible — gated on a literal
    confirmation phrase so it can never fire from a stray click."""
    if body.confirm != _CONFIRM_PHRASE:
        raise HTTPException(
            status_code=400,
            detail=f'Type "{_CONFIRM_PHRASE}" exactly to confirm this irreversible action.',
        )

    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    target_docs = await db.users.find(
        {"email": {"$ne": PROTECTED_SUPER_ADMIN_EMAIL}}, {"_id": 1, "email": 1},
    ).to_list(2000)
    target_ids = [d["_id"] for d in target_docs]
    target_id_strs = [str(d["_id"]) for d in target_docs]

    if not target_ids:
        return {"ok": True, "deleted_users": 0}

    for uid in target_id_strs:
        await _purge_user_owned_data(db, uid)

    # This tool's purpose is a full wipe (pre-launch reset), unlike the
    # single-account GDPR purge, which deliberately keeps the audit/security
    # trail for compliance. Clear those references here too.
    await db.audit_log.delete_many(
        {"$or": [{"actor_id": {"$in": target_id_strs}}, {"target_id": {"$in": target_id_strs}}]}
    )
    await db.security_events.delete_many({"actor_id": {"$in": target_id_strs}})

    result = await db.users.delete_many({"_id": {"$in": target_ids}})

    meta = request_meta(request)
    await log_event(
        "admin.platform_reset.execute",
        actor_id=admin["id"], actor_email=admin.get("email"),
        ip=meta["ip"], user_agent=meta["user_agent"],
        extra={"deleted_users": result.deleted_count, "deleted_emails": [d.get("email") for d in target_docs]},
    )
    return {"ok": True, "deleted_users": result.deleted_count}
