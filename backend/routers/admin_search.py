"""Admin Global Search — cross-collection search backing the Admin OS command
palette. Read-only, super_admin only. Fans out across the highest-value
existing collections using the same DBProxy/regex-$or idiom already used in
admin_content.py and admin_users_mgmt.py — no new data-access architecture.
"""
from __future__ import annotations
import re
from typing import Optional

from fastapi import APIRouter, Depends

from db import get_db
from services.permissions import require_super_admin
from repo.shim import DBProxy
from repo.security_context import SecurityContext

router = APIRouter(prefix="/api/admin/search", tags=["admin-search"])

# (collection, fields to match, projection)
_COLLECTIONS = [
    ("users",        ["email", "full_name"],   {"email": 1, "full_name": 1, "role": 1, "plan_code": 1}),
    ("projects",      ["title", "description"], {"title": 1, "owner_id": 1, "status": 1}),
    ("workspaces",    ["name"],                  {"name": 1, "owner_id": 1, "status": 1}),
    ("institutions",  ["name", "domain"],        {"name": 1, "domain": 1, "country": 1}),
    ("publications",  ["title"],                 {"title": 1, "owner_id": 1, "year": 1}),
    ("support_tickets", ["subject", "message"],  {"subject": 1, "status": 1, "priority": 1, "user_id": 1}),
]


def _serialize(docs: list) -> list:
    out = []
    for d in docs:
        d = dict(d)
        d["id"] = str(d.pop("_id", ""))
        out.append(d)
    return out


@router.get("", dependencies=[Depends(require_super_admin)])
async def global_search(q: str, limit_per_collection: int = 5):
    """Search across users, projects, workspaces, institutions, publications,
    and support tickets. Returns up to `limit_per_collection` matches per
    collection. Used by the Admin OS command palette's live-search section."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    q = (q or "").strip()
    if not q:
        return {"query": q, "results": {}}

    limit_per_collection = max(1, min(limit_per_collection, 20))
    escaped = re.escape(q)

    results: dict = {}
    for coll, fields, projection in _COLLECTIONS:
        filt = {"$or": [{f: {"$regex": escaped, "$options": "i"}} for f in fields]}
        docs = await db[coll].find(filt, projection).limit(limit_per_collection).to_list(limit_per_collection)
        results[coll] = _serialize(docs)

    return {"query": q, "results": results}
