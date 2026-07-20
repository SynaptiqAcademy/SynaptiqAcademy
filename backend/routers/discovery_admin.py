"""Discovery admin endpoints — manual sync triggers + introspection.

All write endpoints require admin. Read endpoints are open to authenticated
users so the in-app status panels work.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth_utils import get_current_user
from db import get_db
from services.discovery import (
    provider_summary, run_kind, ensure_indexes, scheduler_enabled,
)
from services.discovery.registry import providers_for
from repo.shim import DBProxy
from repo.security_context import SecurityContext
from zt.deps import zt_check, zt_is_admin, zt_is_super_admin

logger = logging.getLogger("synaptiq.discovery.admin")

router = APIRouter(prefix="/api/discovery", tags=["discovery"])

KINDS = {"journal", "conference", "grant"}

# Strong references so fire-and-forget tasks aren't GC'd by Python.
_BACKGROUND_TASKS: set[asyncio.Task] = set()


def _spawn(coro):
    t = asyncio.create_task(coro)
    _BACKGROUND_TASKS.add(t)
    t.add_done_callback(_BACKGROUND_TASKS.discard)
    return t


def _require_admin(user: dict) -> None:
    zt_check(user, "admin", "admin")


@router.get("/sources")
async def sources(_user: dict = Depends(get_current_user)):
    return {
        "scheduler_enabled": scheduler_enabled(),
        "providers": provider_summary(),
    }


@router.get("/stats")
async def stats(_user: dict = Depends(get_current_user)):
    """Counts + latest sync info per kind/source. Cheap aggregation."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    out: dict = {}
    for kind, coll in (("journal", "journals"), ("conference", "conferences"), ("grant", "grants")):
        total = await db[coll].count_documents({})
        per_source = []
        agg = db[coll].aggregate([{"$group": {"_id": "$source", "count": {"$sum": 1}}},
                                  {"$sort": {"count": -1}}])
        async for row in agg:
            per_source.append({"source": row["_id"] or "unknown", "count": row["count"]})
        last_runs = await db.ingest_runs.find({"kind": kind}).sort("started_at", -1).limit(3).to_list(3)
        for lr in last_runs: lr["_id"] = str(lr["_id"])
        out[kind] = {"total": total, "per_source": per_source, "recent_runs": last_runs}
    return out


class SyncIn(BaseModel):
    providers: Optional[list[str]] = None
    max_records_per_source: int = 2000
    max_wall_seconds_per_source: int = 90
    reset_cursor: bool = False


@router.post("/sync/{kind}")
async def sync_kind(kind: str, body: SyncIn | None = None,
                    user: dict = Depends(get_current_user)):
    _require_admin(user)
    if kind not in KINDS: raise HTTPException(400, "Invalid kind")
    body = body or SyncIn()
    # Validate provider names
    if body.providers:
        valid = {p.name for p in providers_for(kind)}
        unknown = set(body.providers) - valid
        if unknown: raise HTTPException(400, f"Unknown providers: {sorted(unknown)}")
    # Fire-and-forget; the runner already has its own wall-seconds bound.
    _spawn(run_kind(
        kind, providers=body.providers,
        max_records_per_source=body.max_records_per_source,
        reset_cursor=body.reset_cursor,
        max_wall_seconds_per_source=body.max_wall_seconds_per_source,
    ))
    return {"ok": True, "queued": True, "kind": kind, "providers": body.providers}


@router.post("/indexes/ensure")
async def indexes_ensure(user: dict = Depends(get_current_user)):
    _require_admin(user)
    await ensure_indexes()
    return {"ok": True}


@router.get("/runs")
async def runs(kind: Optional[str] = None, limit: int = 20,
               _user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    q = {"kind": kind} if kind else {}
    docs = await db.ingest_runs.find(q).sort("started_at", -1).limit(limit).to_list(limit)
    for d in docs: d["_id"] = str(d["_id"])
    return docs
