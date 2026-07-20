"""Admin Account Security — audit, lockdown, and super-admin verification.

Provides endpoints to:
  - Audit all elevated-privilege accounts on the platform
  - Run a one-click lockdown that strips super_admin from all but the protected account
  - Verify the protected account exists and is healthy
  - View the role hierarchy
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Request

from db import get_db
from services.admin_audit import log_event, request_meta
from services.permissions import (
    require_super_admin,
    PROTECTED_SUPER_ADMIN_EMAIL,
    ROLE_HIERARCHY,
    SUPER_ADMIN_EMAILS,
    is_protected_account,
)
from repo.shim import DBProxy
from repo.security_context import SecurityContext

router = APIRouter(prefix="/api/admin/account-security", tags=["admin-account-security"])
_GATE = [Depends(require_super_admin)]

_ELEVATED_ROLES = {"super_admin", "admin", "institution_admin", "moderator",
                   "verified_professor", "verified_researcher"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/admin/account-security/audit
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/audit", dependencies=_GATE)
async def audit_privileged_accounts():
    """Full audit of all users with elevated roles or super-admin emails."""
    db = get_db()

    db = DBProxy(db, SecurityContext.system())

    # All users who have an elevated role
    elevated = await db.users.find(
        {"role": {"$in": list(_ELEVATED_ROLES)}},
        {
            "_id": 1, "email": 1, "full_name": 1, "role": 1,
            "status": 1, "created_at": 1, "email_verified": 1,
            "last_login_at": 1, "plan_code": 1, "protected": 1,
        }
    ).sort("role", 1).to_list(500)

    # Users in SUPER_ADMIN_EMAILS env var but without role=super_admin
    env_admins_no_role = await db.users.find(
        {"email": {"$in": list(SUPER_ADMIN_EMAILS)}, "role": {"$ne": "super_admin"}},
        {"_id": 1, "email": 1, "full_name": 1, "role": 1, "status": 1, "created_at": 1},
    ).to_list(100)

    results = []
    for u in elevated:
        email = (u.get("email") or "").lower()
        results.append({
            "id":             str(u["_id"]),
            "email":          u.get("email"),
            "full_name":      u.get("full_name"),
            "role":           u.get("role"),
            "status":         u.get("status") or "active",
            "email_verified": u.get("email_verified", False),
            "created_at":     (u.get("created_at") or "")[:10],
            "plan_code":      u.get("plan_code"),
            "is_protected":   email == PROTECTED_SUPER_ADMIN_EMAIL,
            "in_env_list":    email in SUPER_ADMIN_EMAILS,
            "source":         "role",
        })

    for u in env_admins_no_role:
        email = (u.get("email") or "").lower()
        if not any(r["id"] == str(u["_id"]) for r in results):
            results.append({
                "id":           str(u["_id"]),
                "email":        u.get("email"),
                "full_name":    u.get("full_name"),
                "role":         u.get("role"),
                "status":       u.get("status") or "active",
                "email_verified": u.get("email_verified", False),
                "created_at":   (u.get("created_at") or "")[:10],
                "plan_code":    u.get("plan_code"),
                "is_protected": email == PROTECTED_SUPER_ADMIN_EMAIL,
                "in_env_list":  True,
                "source":       "env_list",
            })

    # Risks / anomalies
    risks = []
    for r in results:
        if r["role"] == "super_admin" and not r["is_protected"]:
            risks.append({
                "severity": "critical",
                "email":    r["email"],
                "message":  f"{r['email']} has role=super_admin but is NOT the protected account.",
            })
        if r["is_protected"] and r["role"] != "super_admin":
            risks.append({
                "severity": "critical",
                "email":    r["email"],
                "message":  "Protected account exists but role is not super_admin.",
            })
        if r["is_protected"] and r["status"] != "active":
            risks.append({
                "severity": "critical",
                "email":    r["email"],
                "message":  f"Protected account is {r['status']}.",
            })

    protected_exists = any(r["is_protected"] for r in results)
    rogue_super_admins = [r for r in results if r["role"] == "super_admin" and not r["is_protected"]]

    return {
        "accounts":               results,
        "total_elevated":         len(results),
        "rogue_super_admins":     rogue_super_admins,
        "rogue_count":            len(rogue_super_admins),
        "protected_account_exists": protected_exists,
        "risks":                  risks,
        "risk_count":             len(risks),
        "protected_email":        PROTECTED_SUPER_ADMIN_EMAIL,
        "audited_at":             _now_iso(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/admin/account-security/lockdown
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/lockdown", dependencies=_GATE)
async def run_lockdown(dry_run: bool = True, admin: dict = Depends(require_super_admin), request: Request = None):
    """Strip super_admin from all accounts except the protected one.

    Pass dry_run=false to actually apply. Returns a report of affected accounts.
    """
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    now = _now_iso()

    # Find rogue super_admins
    rogue_docs = await db.users.find(
        {"role": "super_admin", "email": {"$ne": PROTECTED_SUPER_ADMIN_EMAIL}},
        {"_id": 1, "email": 1, "full_name": 1, "role": 1},
    ).to_list(500)

    affected = []
    for u in rogue_docs:
        uid  = str(u["_id"])
        email = u.get("email")
        if not dry_run:
            await db.users.update_one(
                {"_id": u["_id"]},
                {"$set": {"role": "user", "updated_at": now}},
            )
            await log_event(
                "admin.lockdown.demote_super_admin",
                actor_id=admin["id"], actor_email=admin.get("email"),
                target_id=uid, target_type="user", target_email=email,
                ip=request_meta(request)["ip"] if request else None,
                extra={"from_role": "super_admin", "to_role": "user", "reason": "lockdown"},
            )
        affected.append({"id": uid, "email": email, "action": "demoted to user"})

    # Ensure protected account has correct state
    protected_doc = await db.users.find_one({"email": PROTECTED_SUPER_ADMIN_EMAIL})
    protected_fix: dict = {}
    if protected_doc:
        if protected_doc.get("role") != "super_admin":
            protected_fix["role"] = "super_admin"
        if protected_doc.get("status") in ("suspended", "banned"):
            protected_fix["status"] = None
        if not protected_doc.get("email_verified"):
            protected_fix["email_verified"] = True
        if not protected_doc.get("protected"):
            protected_fix["protected"] = True
        if protected_fix and not dry_run:
            await db.users.update_one(
                {"email": PROTECTED_SUPER_ADMIN_EMAIL},
                {"$set": {**protected_fix, "updated_at": now},
                 "$unset": {"suspended_at": "", "ban_reason": ""}},
            )
    protected_status = "verified" if (protected_doc and protected_doc.get("role") == "super_admin") else "missing"

    return {
        "dry_run":           dry_run,
        "demoted_accounts":  affected,
        "demoted_count":     len(affected),
        "protected_status":  protected_status,
        "protected_fixes":   protected_fix,
        "protected_email":   PROTECTED_SUPER_ADMIN_EMAIL,
        "applied_at":        now if not dry_run else None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/admin/account-security/protected-status
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/protected-status", dependencies=_GATE)
async def protected_account_status():
    """Verify that admin@synaptiq.academy exists with correct super-admin permissions."""
    db  = get_db()
    db = DBProxy(db, SecurityContext.system())

    doc = await db.users.find_one(
        {"email": PROTECTED_SUPER_ADMIN_EMAIL},
        {"_id": 1, "email": 1, "full_name": 1, "role": 1, "status": 1,
         "email_verified": 1, "plan_code": 1, "protected": 1, "created_at": 1},
    )
    if not doc:
        return {
            "exists":         False,
            "healthy":        False,
            "issues":         ["Account does not exist — restart the server to re-seed it."],
            "protected_email": PROTECTED_SUPER_ADMIN_EMAIL,
        }

    issues = []
    if doc.get("role") != "super_admin":
        issues.append(f"Role is '{doc.get('role')}' instead of 'super_admin'")
    if doc.get("status") in ("suspended", "banned"):
        issues.append(f"Account is {doc['status']}")
    if not doc.get("email_verified"):
        issues.append("Email is not verified")
    if not doc.get("protected"):
        issues.append("Protected flag is missing")

    return {
        "exists":          True,
        "healthy":         len(issues) == 0,
        "id":              str(doc["_id"]),
        "email":           doc.get("email"),
        "full_name":       doc.get("full_name"),
        "role":            doc.get("role"),
        "status":          doc.get("status") or "active",
        "email_verified":  doc.get("email_verified", False),
        "plan_code":       doc.get("plan_code"),
        "protected":       doc.get("protected", False),
        "created_at":      (doc.get("created_at") or "")[:10],
        "issues":          issues,
        "protected_email": PROTECTED_SUPER_ADMIN_EMAIL,
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/admin/account-security/role-hierarchy
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/role-hierarchy", dependencies=_GATE)
async def get_role_hierarchy():
    """Return the platform role hierarchy with counts per role."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    counts_agg = await db.users.aggregate([
        {"$group": {"_id": "$role", "count": {"$sum": 1}}},
    ]).to_list(20)
    counts = {d["_id"]: d["count"] for d in counts_agg}

    hierarchy = [
        {
            "level":  level,
            "role":   role,
            "count":  counts.get(role, 0),
            "api_grantable": role not in ("super_admin",),
            "protected": role == "super_admin",
        }
        for role, level in sorted(ROLE_HIERARCHY.items(), key=lambda x: -x[1])
    ]

    return {
        "hierarchy": hierarchy,
        "protected_email": PROTECTED_SUPER_ADMIN_EMAIL,
        "total_users": sum(counts.values()),
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/admin/account-security/verify-access
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/verify-access", dependencies=_GATE)
async def verify_admin_access(admin: dict = Depends(require_super_admin)):
    """Confirms that the calling account can access all admin routes."""
    return {
        "ok":           True,
        "email":        admin.get("email"),
        "role":         admin.get("role"),
        "is_protected": (admin.get("email") or "").lower() == PROTECTED_SUPER_ADMIN_EMAIL,
        "routes_accessible": [
            "/admin", "/admin/dashboard", "/admin/analytics", "/admin/revenue",
            "/admin/users", "/admin/subscriptions", "/admin/health",
            "/admin/errors", "/admin/research", "/admin/database",
            "/admin/platform-auditor", "/admin/security", "/admin/audit",
            "/admin/email", "/admin/communications", "/admin/promotions",
            "/admin/feature-flags-center", "/admin/jobs", "/admin/api-monitor",
            "/admin/storage", "/admin/institution-center", "/admin/search",
            "/admin/data-quality", "/admin/releases", "/admin/support",
            "/admin/research-integrity", "/admin/command-map", "/admin/copilot",
            "/admin/account-security",
        ],
        "verified_at": _now_iso(),
    }
