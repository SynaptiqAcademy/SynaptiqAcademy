"""One-off migration: link existing users.institution (free text) → institutions._id.

Process:
  1. For each distinct user.institution string, fuzzy-match against existing
     `institutions.name`. If none exists, create the institution.
  2. Set user.institution_id and add an institution_membership with confidence score.

Idempotent: re-running skips already linked users.

Usage: cd /app/backend && python -m scripts.migrate_users_to_institutions
"""
from __future__ import annotations
import asyncio
import os
import re
from datetime import datetime, timezone
from difflib import SequenceMatcher

from bson import ObjectId
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()


def _norm(s: str) -> str:
    return re.sub(r"[\s\-_\.,]+", " ", (s or "").lower()).strip()


def _confidence(a: str, b: str) -> float:
    return round(SequenceMatcher(None, _norm(a), _norm(b)).ratio(), 3)


async def run():
    uri = (
        os.environ.get("MONGODB_URI", "").strip()
        or os.environ.get("MONGO_URL", "").strip()
    )
    if not uri:
        raise RuntimeError("Set MONGODB_URI (Atlas SRV) or MONGO_URL before running this script.")
    db_name = (
        os.environ.get("MONGODB_DB_NAME", "").strip()
        or os.environ.get("DB_NAME", "synaptiq")
    )
    client = AsyncIOMotorClient(uri, retryWrites=True, w="majority", appName="SYNAPTIQ-migrate")
    db = client[db_name]

    users = await db.users.find(
        {"institution": {"$exists": True, "$ne": ""}, "institution_id": {"$exists": False}},
        {"institution": 1, "email": 1, "full_name": 1},
    ).to_list(10_000)
    print(f"[migrate] Users to process: {len(users)}")

    # Cache of normalized name → institution_id
    existing = await db.institutions.find({}, {"name": 1, "email_domains": 1}).to_list(10_000)
    by_norm = {_norm(d["name"]): d for d in existing}

    created = 0
    linked = 0
    flagged = 0

    for u in users:
        raw = (u.get("institution") or "").strip()
        if not raw: continue
        norm = _norm(raw)

        # 1) Exact match
        candidate = by_norm.get(norm)
        confidence = 1.0 if candidate else 0.0

        # 2) Fuzzy match
        if not candidate:
            best_id, best_score = None, 0.0
            for k, v in by_norm.items():
                s = _confidence(raw, v["name"])
                if s > best_score:
                    best_score = s; best_id = v
            if best_id and best_score >= 0.88:
                candidate = best_id
                confidence = best_score

        # 3) Email-domain assist (override match if domain matches)
        domain = None
        if u.get("email") and "@" in u["email"]:
            domain = u["email"].split("@", 1)[1].lower()
            for d in existing:
                if domain in (d.get("email_domains") or []):
                    candidate = d
                    confidence = max(confidence, 0.95)
                    break

        # 4) Create new institution if no match
        if not candidate:
            new_doc = {
                "name": raw, "slug": norm.replace(" ", "-")[:80],
                "country": None, "website": None, "description": None,
                "logo_url": None,
                "email_domains": [domain] if domain else [],
                "research_areas": [],
                "type": "university" if "univ" in norm or "college" in norm else "research_institute",
                "owner_id": None, "admin_ids": [],
                "plan_code": "institution_free",
                "seats": {"total": 0, "assigned": 0, "sponsored": 0},
                "created_via": "migration",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            r = await db.institutions.insert_one(new_doc)
            new_doc["_id"] = r.inserted_id
            existing.append(new_doc)
            by_norm[norm] = new_doc
            candidate = new_doc
            confidence = 1.0
            created += 1

        iid = str(candidate["_id"])
        await db.users.update_one(
            {"_id": u["_id"]},
            {"$set": {"institution_id": iid,
                       "institution_migration_confidence": confidence}}
        )
        # Add membership (status: approved if high confidence, pending if low)
        status = "approved" if confidence >= 0.9 else "pending"
        if status == "pending": flagged += 1
        await db.institution_memberships.update_one(
            {"institution_id": iid, "user_id": str(u["_id"])},
            {"$set": {
                "institution_id": iid, "user_id": str(u["_id"]),
                "role": "researcher", "status": status,
                "unit_ids": [], "seat_type": "personal",
                "verified_via": "migration_high_confidence" if status == "approved" else "migration_low_confidence",
                "migration_confidence": confidence,
                "joined_at": datetime.now(timezone.utc).isoformat(),
            }},
            upsert=True,
        )
        linked += 1

    print(f"[migrate] Created institutions: {created}")
    print(f"[migrate] Linked users: {linked}")
    print(f"[migrate] Flagged low-confidence for review: {flagged}")


if __name__ == "__main__":
    asyncio.run(run())
