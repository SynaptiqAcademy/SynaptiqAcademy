"""Grant Collaboration Hub — Consortium Service.

Manages consortia and work packages for collaboration workspaces.

Collections:
  grant_consortia      — consortium builder (lead + partner institutions)
  grant_work_packages  — work packages with tasks and deliverables
  institutions         — for name/country/type lookups
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId


def _ser(d: dict) -> dict:
    if not d:
        return {}
    out = dict(d)
    if "_id" in out:
        out["id"] = str(out.pop("_id"))
    for k, v in out.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
    return out


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── consortium ────────────────────────────────────────────────────────────────

async def get_or_create_consortium(
    collab_id: str,
    lead_user_id: str,
    lead_institution_id: str,
    db,
) -> dict:
    """Fetch existing consortium or create one with lead info."""
    existing = await db["grant_consortia"].find_one({"collaboration_id": collab_id})
    if existing:
        return _ser(existing)

    # Look up lead institution name
    lead_institution_name = ""
    if lead_institution_id:
        try:
            inst = await db["institutions"].find_one(
                {"_id": ObjectId(lead_institution_id)},
                {"name": 1},
            )
            if inst:
                lead_institution_name = inst.get("name", "")
        except Exception:
            pass

    now = _now()
    doc = {
        "collaboration_id": collab_id,
        "lead_institution_id": lead_institution_id or "",
        "lead_institution_name": lead_institution_name,
        "partner_institutions": [],
        "total_budget": 0.0,
        "created_at": now,
        "updated_at": now,
    }
    result = await db["grant_consortia"].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _ser(doc)


async def add_partner_institution(
    collab_id: str,
    user_id: str,
    institution_id: str,
    role: str,
    budget_share: float,
    db,
) -> dict:
    """Add a partner institution to the consortium."""
    consortium = await db["grant_consortia"].find_one({"collaboration_id": collab_id})
    if not consortium:
        raise KeyError(f"Consortium for collaboration {collab_id} not found. Create it first.")

    # Check duplicate
    partners = consortium.get("partner_institutions", [])
    existing_ids = [p.get("institution_id") for p in partners]
    if institution_id in existing_ids:
        raise ValueError(f"Institution {institution_id} is already a partner")

    # Look up institution details
    institution_name = ""
    institution_countries: list = []
    try:
        inst = await db["institutions"].find_one(
            {"_id": ObjectId(institution_id)},
            {"name": 1, "country": 1, "countries": 1},
        )
        if inst:
            institution_name = inst.get("name", "")
            country = inst.get("country", "")
            if country:
                institution_countries = [country]
            else:
                institution_countries = inst.get("countries", [])
    except Exception:
        pass

    partner_entry = {
        "institution_id": institution_id,
        "institution_name": institution_name,
        "role": role,
        "budget_share": float(budget_share),
        "deliverables": [],
        "countries": institution_countries,
        "status": "active",
        "joined_at": _now(),
    }

    await db["grant_consortia"].update_one(
        {"collaboration_id": collab_id},
        {
            "$push": {"partner_institutions": partner_entry},
            "$set": {"updated_at": _now()},
        },
    )

    updated = await db["grant_consortia"].find_one({"collaboration_id": collab_id})
    return _ser(updated)


async def update_partner(
    collab_id: str,
    institution_id: str,
    updates: dict,
    db,
) -> dict:
    """Update a partner institution's fields within the consortium."""
    allowed = {"role", "budget_share", "deliverables", "status"}
    set_fields: dict = {}
    for k, v in updates.items():
        if k in allowed:
            set_fields[f"partner_institutions.$.{k}"] = v
    set_fields["updated_at"] = _now()

    await db["grant_consortia"].update_one(
        {"collaboration_id": collab_id, "partner_institutions.institution_id": institution_id},
        {"$set": set_fields},
    )

    updated = await db["grant_consortia"].find_one({"collaboration_id": collab_id})
    return _ser(updated)


async def remove_partner(
    collab_id: str,
    institution_id: str,
    user_id: str,
    db,
) -> bool:
    """Remove a partner institution from the consortium."""
    result = await db["grant_consortia"].update_one(
        {"collaboration_id": collab_id},
        {
            "$pull": {"partner_institutions": {"institution_id": institution_id}},
            "$set": {"updated_at": _now()},
        },
    )
    return result.modified_count > 0


# ── work packages ─────────────────────────────────────────────────────────────

async def create_work_package(collab_id: str, user_id: str, data: dict, db) -> dict:
    """Create a work package within a collaboration."""
    # Get lead user name
    lead_user_name = ""
    lead_user_id = data.get("lead_user_id", user_id)
    try:
        user = await db["users"].find_one(
            {"_id": ObjectId(lead_user_id)},
            {"first_name": 1, "last_name": 1, "name": 1},
        )
        if user:
            lead_user_name = (
                user.get("name")
                or f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
            )
    except Exception:
        pass

    now = _now()
    doc = {
        "collaboration_id": collab_id,
        "title": data.get("title", ""),
        "description": data.get("description", ""),
        "lead_user_id": lead_user_id,
        "lead_user_name": lead_user_name,
        "tasks": [],
        "deliverables": data.get("deliverables", []),
        "budget": float(data.get("budget", 0.0)),
        "start_date": data.get("start_date", ""),
        "end_date": data.get("end_date", ""),
        "status": "not_started",
        "created_at": now,
        "updated_at": now,
    }
    result = await db["grant_work_packages"].insert_one(doc)
    doc["_id"] = result.inserted_id
    return _ser(doc)


async def list_work_packages(collab_id: str, db) -> list:
    """List all work packages for a collaboration."""
    docs = await db["grant_work_packages"].find(
        {"collaboration_id": collab_id}
    ).sort("created_at", 1).to_list(200)
    return [_ser(d) for d in docs]


async def update_work_package(wp_id: str, user_id: str, updates: dict, db) -> dict:
    """Update a work package."""
    try:
        oid = ObjectId(wp_id)
    except Exception:
        raise KeyError(f"Invalid work package id: {wp_id}")

    allowed = {
        "title", "description", "lead_user_id", "deliverables",
        "budget", "start_date", "end_date", "status",
    }
    safe = {k: v for k, v in updates.items() if k in allowed}
    if "budget" in safe:
        safe["budget"] = float(safe["budget"])
    safe["updated_at"] = _now()

    await db["grant_work_packages"].update_one({"_id": oid}, {"$set": safe})
    doc = await db["grant_work_packages"].find_one({"_id": oid})
    if not doc:
        raise KeyError(f"Work package {wp_id} not found")
    return _ser(doc)


async def add_task_to_wp(wp_id: str, user_id: str, task_data: dict, db) -> dict:
    """Add a task to a work package."""
    try:
        oid = ObjectId(wp_id)
    except Exception:
        raise KeyError(f"Invalid work package id: {wp_id}")

    # Resolve assignee name
    assignee_name = ""
    assignee_uid = task_data.get("assignee_user_id", "")
    if assignee_uid:
        try:
            user = await db["users"].find_one(
                {"_id": ObjectId(assignee_uid)},
                {"first_name": 1, "last_name": 1, "name": 1},
            )
            if user:
                assignee_name = (
                    user.get("name")
                    or f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                )
        except Exception:
            pass

    task = {
        "task_id": str(uuid.uuid4()),
        "title": task_data.get("title", ""),
        "assignee_user_id": assignee_uid,
        "assignee_name": assignee_name,
        "due_date": task_data.get("due_date", ""),
        "status": task_data.get("status", "todo"),
    }

    now = _now()
    await db["grant_work_packages"].update_one(
        {"_id": oid},
        {"$push": {"tasks": task}, "$set": {"updated_at": now}},
    )

    doc = await db["grant_work_packages"].find_one({"_id": oid})
    if not doc:
        raise KeyError(f"Work package {wp_id} not found")
    return _ser(doc)


# ── eligibility validation ────────────────────────────────────────────────────

async def validate_consortium_eligibility(collab_id: str, db) -> dict:
    """Validate consortium eligibility based on structural requirements."""
    consortium = await db["grant_consortia"].find_one({"collaboration_id": collab_id})

    issues: list[str] = []
    checks: dict = {}

    # 1. Lead institution set?
    has_lead = bool(consortium and consortium.get("lead_institution_id"))
    checks["has_lead_institution"] = has_lead
    if not has_lead:
        issues.append("Lead institution is not set")

    partners = consortium.get("partner_institutions", []) if consortium else []
    active_partners = [p for p in partners if p.get("status") != "removed"]

    # 2. At least 1 partner?
    has_partners = len(active_partners) >= 1
    checks["has_at_least_one_partner"] = has_partners
    if not has_partners:
        issues.append("At least one partner institution is required")

    # 3. Budget shares sum ≤ 100?
    total_share = sum(float(p.get("budget_share", 0)) for p in active_partners)
    budget_ok = total_share <= 100.0
    checks["budget_shares_valid"] = budget_ok
    checks["total_budget_share"] = round(total_share, 2)
    if not budget_ok:
        issues.append(f"Partner budget shares sum to {total_share:.1f}% (exceeds 100%)")

    # 4. No duplicate institutions?
    partner_ids = [p.get("institution_id") for p in active_partners]
    lead_id = consortium.get("lead_institution_id", "") if consortium else ""
    all_inst_ids = ([lead_id] if lead_id else []) + partner_ids
    no_duplicates = len(all_inst_ids) == len(set(all_inst_ids))
    checks["no_duplicate_institutions"] = no_duplicates
    if not no_duplicates:
        issues.append("Duplicate institution detected in consortium")

    # 5. At least 2 countries represented?
    # Collect countries from partner entries
    all_countries: set = set()
    if lead_id:
        try:
            inst = await db["institutions"].find_one(
                {"_id": ObjectId(lead_id)},
                {"country": 1},
            )
            if inst and inst.get("country"):
                all_countries.add(inst["country"])
        except Exception:
            pass

    for p in active_partners:
        for c in p.get("countries", []):
            if c:
                all_countries.add(c)

    multi_country = len(all_countries) >= 2
    checks["multi_country"] = multi_country
    checks["countries_represented"] = list(all_countries)
    if not multi_country:
        issues.append("At least 2 countries must be represented in the consortium")

    is_eligible = len(issues) == 0
    return {
        "is_eligible": is_eligible,
        "issues": issues,
        "checks": checks,
    }
