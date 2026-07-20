#!/usr/bin/env python3
"""Admin Account Consolidation & Super-Admin Lockdown Script.

Usage:
    # Audit only (no changes):
    python scripts/admin_lockdown.py --audit

    # Dry-run the lockdown:
    python scripts/admin_lockdown.py --dry-run

    # Apply lockdown (strips super_admin from all accounts except protected):
    python scripts/admin_lockdown.py --apply

    # Create / verify the protected account:
    python scripts/admin_lockdown.py --verify
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── ensure backend package is on path ───────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from auth_utils import hash_password
from db import get_db

PROTECTED_EMAIL = "admin@synaptiq.academy"
ELEVATED_ROLES  = {"super_admin", "admin", "institution_admin", "moderator",
                   "verified_professor", "verified_researcher"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─────────────────────────────────────────────────────────────────────────────
# Report helpers
# ─────────────────────────────────────────────────────────────────────────────

def _header(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def _row(label: str, value) -> None:
    print(f"  {label:<30} {value}")


# ─────────────────────────────────────────────────────────────────────────────
# Audit
# ─────────────────────────────────────────────────────────────────────────────

async def audit(db) -> dict:
    _header("PRIVILEGE AUDIT")

    elevated = await db.users.find(
        {"role": {"$in": list(ELEVATED_ROLES)}},
        {"_id": 1, "email": 1, "full_name": 1, "role": 1, "status": 1,
         "created_at": 1, "email_verified": 1, "plan_code": 1, "protected": 1},
    ).sort("role", 1).to_list(1000)

    print(f"\n  {'ID':>26}  {'Email':<40}  {'Role':<20}  {'Status':<12}  {'Verified':<8}  {'Created'}")
    print("  " + "-" * 120)

    rogue_super_admins = []
    for u in elevated:
        uid    = str(u["_id"])
        email  = u.get("email", "")
        role   = u.get("role", "")
        status = u.get("status") or "active"
        verified = "✓" if u.get("email_verified") else "✗"
        created  = (u.get("created_at") or "")[:10]
        marker   = " ← PROTECTED" if email.lower() == PROTECTED_EMAIL else ""
        if role == "super_admin" and email.lower() != PROTECTED_EMAIL:
            marker = " ← ROGUE SUPER-ADMIN"
            rogue_super_admins.append(u)
        print(f"  {uid:>26}  {email:<40}  {role:<20}  {status:<12}  {verified:<8}  {created}{marker}")

    _header("AUDIT SUMMARY")
    _row("Total elevated accounts:", len(elevated))
    _row("Rogue super-admins:", len(rogue_super_admins))
    protected_doc = next((u for u in elevated if u.get("email", "").lower() == PROTECTED_EMAIL), None)
    if protected_doc:
        _row("Protected account:", f"✓ EXISTS  role={protected_doc.get('role')}  status={protected_doc.get('status') or 'active'}")
    else:
        _row("Protected account:", "✗ MISSING — run --verify to create")

    return {"elevated": elevated, "rogue": rogue_super_admins, "protected": protected_doc}


# ─────────────────────────────────────────────────────────────────────────────
# Verify / create protected account
# ─────────────────────────────────────────────────────────────────────────────

async def verify_protected(db) -> None:
    _header("PROTECTED ACCOUNT VERIFICATION")

    password = os.environ.get("SUPER_ADMIN_PASSWORD", "")
    if not password:
        print("  ⚠  SUPER_ADMIN_PASSWORD env var not set — cannot create/re-key account.")
        password = None

    doc = await db.users.find_one({"email": PROTECTED_EMAIL})
    now = _now()

    if not doc:
        if not password:
            print(f"  ✗  Account {PROTECTED_EMAIL} does not exist. Set SUPER_ADMIN_PASSWORD and re-run.")
            return
        await db.users.insert_one({
            "email": PROTECTED_EMAIL,
            "password_hash": hash_password(password),
            "full_name": "SYNAPTIQ Super Admin",
            "role": "super_admin",
            "institution": "SYNAPTIQ HQ",
            "department": "Operations",
            "country": "Global",
            "academic_role": "Super Administrator",
            "biography": "Sole platform super administrator.",
            "research_areas": [], "skills": [], "can_contribute": [], "looking_for": [],
            "availability": "Available", "h_index": 0, "avatar_url": "",
            "collaboration_score": 100, "publication_score": 0,
            "expertise_score": 100, "community_score": 100,
            "connections": [], "onboarded": True,
            "email_verified": True,
            "email_verified_at": now,
            "plan_code": "institution",
            "subscription_status": "active",
            "credits_balance": 1000000,
            "credits_pack_balance": 0,
            "credits_monthly_allowance": 1000000,
            "credits_reset_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "failed_login_count": 0, "locked_until": None,
            "protected": True,
            "created_at": now,
        })
        print(f"  ✓  Created {PROTECTED_EMAIL} with role=super_admin")
    else:
        updates: dict = {}
        if doc.get("role") != "super_admin":
            updates["role"] = "super_admin"
        if not doc.get("email_verified"):
            updates["email_verified"] = True
        if doc.get("status") in ("suspended", "banned"):
            updates["status"] = None
        if not doc.get("protected"):
            updates["protected"] = True
        if updates:
            await db.users.update_one(
                {"email": PROTECTED_EMAIL},
                {"$set": {**updates, "updated_at": now},
                 "$unset": {"suspended_at": "", "ban_reason": ""}},
            )
            print(f"  ✓  Updated {PROTECTED_EMAIL}: {updates}")
        else:
            print(f"  ✓  {PROTECTED_EMAIL} is healthy — no changes needed")


# ─────────────────────────────────────────────────────────────────────────────
# Lockdown
# ─────────────────────────────────────────────────────────────────────────────

async def lockdown(db, dry_run: bool = True) -> None:
    label = "DRY-RUN" if dry_run else "APPLY"
    _header(f"PRIVILEGE LOCKDOWN [{label}]")

    rogue = await db.users.find(
        {"role": "super_admin", "email": {"$ne": PROTECTED_EMAIL}},
        {"_id": 1, "email": 1, "full_name": 1, "role": 1},
    ).to_list(500)

    if not rogue:
        print(f"  ✓  No rogue super-admins found. Platform is already locked down.")
    else:
        for u in rogue:
            uid   = str(u["_id"])
            email = u.get("email", "")
            if not dry_run:
                await db.users.update_one(
                    {"_id": u["_id"]},
                    {"$set": {"role": "user", "updated_at": _now()}},
                )
                print(f"  {'DEMOTED':<10}  {email}  ({uid})")
            else:
                print(f"  {'WOULD DEMOTE':<14}  {email}  ({uid})")

    if not dry_run:
        # Also ensure protected account is correct
        await verify_protected(db)
        print(f"\n  ✓  Lockdown complete. Only {PROTECTED_EMAIL} retains super_admin.")
    else:
        print(f"\n  (dry-run) No changes applied. Run with --apply to execute.")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

async def main() -> None:
    parser = argparse.ArgumentParser(description="Synaptiq Admin Account Consolidation")
    parser.add_argument("--audit",   action="store_true", help="Audit elevated accounts (read-only)")
    parser.add_argument("--dry-run", action="store_true", help="Show what lockdown would do without applying")
    parser.add_argument("--apply",   action="store_true", help="Apply the lockdown (strips rogue super-admins)")
    parser.add_argument("--verify",  action="store_true", help="Create/verify the protected account")
    args = parser.parse_args()

    if not any([args.audit, args.dry_run, args.apply, args.verify]):
        parser.print_help()
        sys.exit(1)

    from motor.motor_asyncio import AsyncIOMotorClient
    mongo_url = os.environ.get("MONGODB_URL", "mongodb://localhost:27017")
    db_name   = os.environ.get("DB_NAME", "synaptiq")
    client    = AsyncIOMotorClient(mongo_url)
    db        = client[db_name]

    print(f"\n  Connected to MongoDB: {mongo_url}/{db_name}")
    print(f"  Protected account: {PROTECTED_EMAIL}")
    print(f"  Timestamp: {_now()}")

    if args.audit or args.dry_run or args.apply:
        await audit(db)

    if args.verify:
        await verify_protected(db)

    if args.dry_run:
        await lockdown(db, dry_run=True)

    if args.apply:
        confirm = input(f"\n  Apply lockdown? This will demote all super-admins except {PROTECTED_EMAIL}. Type YES: ")
        if confirm.strip() == "YES":
            await lockdown(db, dry_run=False)
        else:
            print("  Cancelled.")

    client.close()
    print("\n  Done.\n")


if __name__ == "__main__":
    asyncio.run(main())
