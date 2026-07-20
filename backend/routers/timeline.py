import csv
import io
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from repo.shim import make_db_proxy
from db import get_db

from services.timeline.event_service import (
    EVENT_CATALOGUE, CATEGORY_COLORS, CATEGORIES,
    record_event, get_events, get_public_events,
    get_event, update_event, delete_event,
    get_stats, sync_from_existing,
)
from services.timeline.heatmap_service import get_heatmap
from services.timeline.analytics_service import get_analytics
from services.timeline.milestone_service import get_milestones, evaluate_milestones
from services.timeline.insight_service import generate_insights
from zt.deps import zt_check, zt_is_admin, zt_is_super_admin

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/timeline", tags=["timeline"])


# ── Pydantic schemas ─────────────────────────────────────────────────────────

class CreateEventRequest(BaseModel):
    event_type: str
    title: str
    description: str = ""
    metadata: dict = Field(default_factory=dict)
    visibility: str = "public"
    importance: str = "normal"
    occurred_at: Optional[str] = None
    tags: list[str] = Field(default_factory=list)


class UpdateEventRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    visibility: Optional[str] = None
    importance: Optional[str] = None
    tags: Optional[list[str]] = None
    metadata: Optional[dict] = None


class TimelineSettingsUpdate(BaseModel):
    default_visibility: Optional[str] = None
    show_heatmap: Optional[bool] = None
    show_milestones: Optional[bool] = None
    notify_milestones: Optional[bool] = None
    notify_achievements: Optional[bool] = None
    public_categories: Optional[list[str]] = None


# ── Helpers ──────────────────────────────────────────────────────────────────

def _uid(user: dict) -> str:
    return str(user.get("_id", user.get("id", "")))


def _require_admin(user: dict) -> None:
    zt_check(user, "admin", "admin")


def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None


# ── Literal-path routes first (before any /{param} routes) ──────────────────

@router.get("/catalogue")
async def get_catalogue():
    return {
        "event_types": EVENT_CATALOGUE,
        "category_colors": CATEGORY_COLORS,
        "categories": CATEGORIES,
    }


@router.get("/heatmap")
async def heatmap_data(
    days: int = Query(365, ge=30, le=730),
    category: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, current_user)
    return await get_heatmap(_uid(current_user), db, days=days, category=category)


@router.get("/analytics")
async def analytics_data(
    months: int = Query(12, ge=1, le=60),
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, current_user)
    return await get_analytics(_uid(current_user), db, period_months=months)


@router.get("/milestones")
async def milestones_list(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, current_user)
    return await get_milestones(_uid(current_user), db)


@router.get("/insights")
async def insights_list(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, current_user)
    return await generate_insights(_uid(current_user), db)


@router.get("/stats")
async def timeline_stats(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, current_user)
    return await get_stats(_uid(current_user), db)


@router.get("/search")
async def search_events(
    q: str = Query(..., min_length=1),
    category: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, current_user)
    return await get_events(_uid(current_user), db, category=category, search=q, limit=limit)


@router.get("/settings")
async def get_settings(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, current_user)
    uid = _uid(current_user)
    doc = await db.timeline_settings.find_one({"user_id": uid})
    if not doc:
        return {
            "user_id": uid,
            "default_visibility": "public",
            "show_heatmap": True,
            "show_milestones": True,
            "notify_milestones": True,
            "notify_achievements": True,
            "public_categories": CATEGORIES,
        }
    doc.pop("_id", None)
    return doc


@router.patch("/settings")
async def update_settings(
    body: TimelineSettingsUpdate,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, current_user)
    uid = _uid(current_user)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.timeline_settings.update_one(
        {"user_id": uid},
        {"$set": {"user_id": uid, **updates}},
        upsert=True,
    )
    return {"status": "updated"}


@router.post("/sync")
async def sync_timeline(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, current_user)
    result = await sync_from_existing(_uid(current_user), db)
    # Re-evaluate milestones after sync
    awarded = await evaluate_milestones(_uid(current_user), db)
    return {**result, "milestones_awarded": len(awarded)}


@router.get("/admin/stats")
async def admin_stats(
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, current_user)
    _require_admin(current_user)
    total_events = await db.timeline_events.count_documents({})
    total_milestones = await db.timeline_milestones.count_documents({})
    total_users = len(await db.timeline_events.distinct("user_id"))
    breakdown = {}
    for cat in CATEGORIES:
        breakdown[cat] = await db.timeline_events.count_documents({"category": cat})
    return {
        "total_events": total_events,
        "total_milestones": total_milestones,
        "total_users_with_timeline": total_users,
        "category_breakdown": breakdown,
    }


# ── POST /events — create manual event ──────────────────────────────────────

@router.post("/events")
async def create_event(
    body: CreateEventRequest,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, current_user)
    if body.event_type not in EVENT_CATALOGUE:
        raise HTTPException(400, f"Unknown event_type: {body.event_type}")
    occurred = _parse_dt(body.occurred_at)
    event = await record_event(
        user_id=_uid(current_user),
        event_type=body.event_type,
        title=body.title,
        db=db,
        description=body.description,
        metadata=body.metadata,
        visibility=body.visibility,
        importance=body.importance,
        source="manual",
        occurred_at=occurred,
        tags=body.tags,
    )
    await evaluate_milestones(_uid(current_user), db)
    return event


# ── Parameterized event routes — AFTER literal paths ────────────────────────

@router.get("/events/{event_id}")
async def get_single_event(
    event_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, current_user)
    ev = await get_event(event_id, _uid(current_user), db)
    if not ev:
        raise HTTPException(404, "Event not found")
    return ev


@router.patch("/events/{event_id}")
async def patch_event(
    event_id: str,
    body: UpdateEventRequest,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, current_user)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    ev = await update_event(event_id, _uid(current_user), updates, db)
    if not ev:
        raise HTTPException(404, "Event not found or not editable")
    return ev


@router.delete("/events/{event_id}")
async def remove_event(
    event_id: str,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, current_user)
    ok = await delete_event(event_id, _uid(current_user), db)
    if not ok:
        raise HTTPException(404, "Event not found or not deletable (only manual events can be deleted)")
    return {"deleted": True}


@router.get("/public/{target_user_id}")
async def public_timeline(
    target_user_id: str,
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    db=Depends(get_db),
):
    db = make_db_proxy(db, system=True)
    events = await get_public_events(target_user_id, db, limit=limit, skip=skip)
    stats = await get_stats(target_user_id, db)
    return {"events": events, "stats": stats}


@router.get("/export/{fmt}")
async def export_timeline(
    fmt: str,
    category: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, current_user)
    if fmt not in ("json", "csv"):
        raise HTTPException(400, "Supported formats: json, csv")
    events = await get_events(_uid(current_user), db, category=category, limit=10000)
    if fmt == "json":
        return JSONResponse(
            content=events,
            headers={"Content-Disposition": "attachment; filename=timeline.json"},
        )
    # CSV
    fields = ["event_type", "category", "label", "title", "description",
              "occurred_at", "visibility", "importance", "is_milestone", "source"]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for e in events:
        writer.writerow({f: e.get(f, "") for f in fields})
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=timeline.csv"},
    )


# ── Main list endpoint — last to avoid shadowing parameterized paths ─────────

@router.get("")
async def list_events(
    category: Optional[str] = None,
    event_type: Optional[str] = None,
    importance: Optional[str] = None,
    milestones_only: bool = False,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    db = make_db_proxy(db, current_user)
    return await get_events(
        _uid(current_user), db,
        category=category,
        event_type=event_type,
        importance=importance,
        milestones_only=milestones_only,
        start_date=_parse_dt(start_date),
        end_date=_parse_dt(end_date),
        limit=limit,
        skip=skip,
    )
