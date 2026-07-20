"""Impact Dashboard — Phase XXII.

Per-user Research Impact Dashboard: SIS score, publication metrics, benchmarks,
forecasts, history, timeline, snapshots, and exports.

Endpoints:
  GET  /api/impact/me                   — full impact report
  GET  /api/impact/score                — SIS breakdown only
  GET  /api/impact/publication-metrics  — h-index, i10, publication counts
  GET  /api/impact/benchmarks           — peer comparisons
  GET  /api/impact/forecasts            — 6-month trend forecasts
  GET  /api/impact/history              — time-series snapshots
  GET  /api/impact/timeline             — academic event timeline
  POST /api/impact/snapshot             — save named snapshot
  GET  /api/impact/snapshots            — list named snapshots
  GET  /api/impact/export/csv           — CSV export
  GET  /api/impact/export/json          — JSON export
  GET  /api/impact/users/{user_id}      — public view
"""
from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from auth_utils import get_current_user
from db import get_db
from repo.shim import DBProxy
from repo.security_context import SecurityContext

log = logging.getLogger("synaptiq.impact_dashboard")
router = APIRouter(prefix="/api/impact", tags=["impact-dashboard"])

# ─────────────────────────── service imports ─────────────────────────────────
# All wrapped in try/except — service layer created in parallel; 503 if missing.

try:
    from services.impact.snapshot_service import (
        get_research_impact,
        get_history,
        get_platform_impact_summary,
        compute_and_store_research_impact,
    )
    _snapshot_service_available = True
except ImportError:
    _snapshot_service_available = False
    log.warning("services.impact.snapshot_service not available")

try:
    from services.impact.synaptiq_score import compute_synaptiq_impact_score
    _score_service_available = True
except ImportError:
    _score_service_available = False
    log.warning("services.impact.synaptiq_score not available")

try:
    from services.impact.h_index_calculator import compute_publication_metrics
    _hindex_service_available = True
except ImportError:
    _hindex_service_available = False
    log.warning("services.impact.h_index_calculator not available")

try:
    from services.impact.benchmarking import compute_benchmarks
    _benchmarking_service_available = True
except ImportError:
    _benchmarking_service_available = False
    log.warning("services.impact.benchmarking not available")

try:
    from services.impact.forecasting import generate_forecasts
    _forecasting_service_available = True
except ImportError:
    _forecasting_service_available = False
    log.warning("services.impact.forecasting not available")


# ─────────────────────────── helpers ─────────────────────────────────────────

def _require_service(available: bool, name: str) -> None:
    if not available:
        raise HTTPException(
            status_code=503,
            detail=f"Service '{name}' is not available. Please try again later.",
        )


def _oid_to_str(doc: dict) -> dict:
    """Recursively convert ObjectId and datetime values in a dict to JSON-safe types."""
    if not isinstance(doc, dict):
        return doc
    out = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, datetime):
            out[k] = v.isoformat()
        elif isinstance(v, dict):
            out[k] = _oid_to_str(v)
        elif isinstance(v, list):
            out[k] = [_oid_to_str(i) if isinstance(i, (dict, ObjectId)) else (i.isoformat() if isinstance(i, datetime) else i) for i in v]
        else:
            out[k] = v
    return out


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_dt(value) -> Optional[datetime]:
    """Parse ISO string or datetime to timezone-aware datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None
    return None


# ─────────────────────────── models ──────────────────────────────────────────

class SnapshotPayload(BaseModel):
    label: Optional[str] = None


# ─────────────────────────── endpoints ───────────────────────────────────────

@router.get("/me")
async def get_my_impact(
    force_refresh: bool = Query(False),
    user: dict = Depends(get_current_user),
):
    """Full impact report for the requesting user."""
    _require_service(_snapshot_service_available, "snapshot_service")
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    user_id = user["id"]

    if force_refresh:
        # Rate-limit: only allow refresh if last update was > 30 minutes ago.
        existing = await db.research_impact.find_one(
            {"user_id": user_id},
            {"updated_at": 1},
        )
        if existing:
            last_updated = _parse_dt(existing.get("updated_at"))
            if last_updated:
                elapsed = (_now_utc() - last_updated).total_seconds()
                if elapsed < 1800:  # 30 minutes
                    raise HTTPException(
                        status_code=429,
                        detail="Impact data was refreshed recently.",
                    )

    result = await get_research_impact(user_id, db, force_refresh)
    if result is None:
        raise HTTPException(status_code=404, detail="Impact data not found.")
    return _oid_to_str(result)


@router.get("/score")
async def get_impact_score(user: dict = Depends(get_current_user)):
    """Synaptiq Impact Score breakdown."""
    _require_service(_score_service_available, "synaptiq_score")
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    result = await compute_synaptiq_impact_score(user["id"], db)
    return _oid_to_str(result)


@router.get("/publication-metrics")
async def get_publication_metrics(user: dict = Depends(get_current_user)):
    """H-index, i10-index, and publication counts."""
    _require_service(_hindex_service_available, "h_index_calculator")
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    result = await compute_publication_metrics(user["id"], db)
    return _oid_to_str(result)


@router.get("/benchmarks")
async def get_benchmarks(user: dict = Depends(get_current_user)):
    """Peer comparison across role, institution, country, and research area."""
    _require_service(_benchmarking_service_available, "benchmarking")
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    result = await compute_benchmarks(user["id"], db)
    return _oid_to_str(result)


@router.get("/forecasts")
async def get_forecasts(user: dict = Depends(get_current_user)):
    """6-month trend forecasts for key impact metrics."""
    _require_service(_forecasting_service_available, "forecasting")
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    result = await generate_forecasts(user["id"], db)
    return _oid_to_str(result)


@router.get("/history")
async def get_impact_history(
    limit: int = Query(24, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    """Chronological list of historical impact snapshots."""
    _require_service(_snapshot_service_available, "snapshot_service")
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    result = await get_history(user["id"], db, limit)
    return [_oid_to_str(doc) for doc in (result or [])]


@router.get("/timeline")
async def get_academic_timeline(user: dict = Depends(get_current_user)):
    """Academic event timeline: all significant events sorted chronologically."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    user_id = user["id"]
    events: list[dict] = []

    # ── manuscripts ───────────────────────────────────────────────────────────
    try:
        manuscript_docs = await db.manuscripts.find(
            {"owner_id": user_id},
            {"title": 1, "status": 1, "created_at": 1},
        ).to_list(500)
        for m in manuscript_docs:
            title = m.get("title") or "Untitled Manuscript"
            created_at = _parse_dt(m.get("created_at"))
            if created_at:
                events.append({
                    "type": "manuscript_created",
                    "title": f"Started manuscript: {title}",
                    "date": created_at.isoformat(),
                    "icon_type": "manuscript",
                    "metadata": {"manuscript_id": str(m["_id"]), "status": m.get("status")},
                })
            if m.get("status") in ("published", "accepted"):
                events.append({
                    "type": "manuscript_published",
                    "title": f"Manuscript accepted/published: {title}",
                    "date": created_at.isoformat() if created_at else _now_utc().isoformat(),
                    "icon_type": "publication",
                    "metadata": {"manuscript_id": str(m["_id"]), "status": m.get("status")},
                })
    except Exception as exc:
        log.warning("Timeline: manuscripts fetch failed: %s", exc)

    # ── projects (use ObjectId timestamp as proxy for created_at) ─────────────
    try:
        project_docs = await db.projects.find(
            {"members": user_id},
            {"title": 1, "_id": 1},
        ).to_list(500)
        for p in project_docs:
            oid = p.get("_id")
            if isinstance(oid, ObjectId):
                gen_time = oid.generation_time
                if gen_time.tzinfo is None:
                    gen_time = gen_time.replace(tzinfo=timezone.utc)
                events.append({
                    "type": "project_joined",
                    "title": f"Joined project: {p.get('title') or 'Untitled Project'}",
                    "date": gen_time.isoformat(),
                    "icon_type": "project",
                    "metadata": {"project_id": str(oid)},
                })
    except Exception as exc:
        log.warning("Timeline: projects fetch failed: %s", exc)

    # ── collaborations ────────────────────────────────────────────────────────
    try:
        collab_docs = await db.collaborations.find(
            {"$or": [{"owner_id": user_id}, {"members": user_id}]},
            {"title": 1, "created_at": 1},
        ).to_list(500)
        for c in collab_docs:
            created_at = _parse_dt(c.get("created_at"))
            if created_at:
                events.append({
                    "type": "collaboration_created",
                    "title": f"Collaboration: {c.get('title') or 'Untitled'}",
                    "date": created_at.isoformat(),
                    "icon_type": "collaboration",
                    "metadata": {"collaboration_id": str(c["_id"])},
                })
    except Exception as exc:
        log.warning("Timeline: collaborations fetch failed: %s", exc)

    # ── grant applications ────────────────────────────────────────────────────
    try:
        grant_docs = await db.grant_applications.find(
            {"applicant_id": user_id},
            {"title": 1, "status": 1, "created_at": 1},
        ).to_list(500)
        for g in grant_docs:
            created_at = _parse_dt(g.get("created_at"))
            title = g.get("title") or "Grant Application"
            if created_at:
                events.append({
                    "type": "grant_applied",
                    "title": f"Applied for grant: {title}",
                    "date": created_at.isoformat(),
                    "icon_type": "grant",
                    "metadata": {"grant_id": str(g["_id"]), "status": g.get("status")},
                })
            if g.get("status") == "awarded":
                events.append({
                    "type": "grant_awarded",
                    "title": f"Grant awarded: {title}",
                    "date": created_at.isoformat() if created_at else _now_utc().isoformat(),
                    "icon_type": "award",
                    "metadata": {"grant_id": str(g["_id"])},
                })
    except Exception as exc:
        log.warning("Timeline: grant_applications fetch failed: %s", exc)

    # ── research reputation events ────────────────────────────────────────────
    try:
        rep_events = await db.research_reputation_events.find(
            {"user_id": user_id},
            {"event_type": 1, "description": 1, "created_at": 1, "points": 1},
        ).sort("created_at", -1).to_list(200)
        for e in rep_events:
            created_at = _parse_dt(e.get("created_at"))
            if created_at:
                events.append({
                    "type": e.get("event_type") or "reputation_event",
                    "title": e.get("description") or "Reputation event",
                    "date": created_at.isoformat(),
                    "icon_type": "reputation",
                    "metadata": {
                        "points": e.get("points"),
                        "event_id": str(e["_id"]),
                    },
                })
    except Exception as exc:
        log.warning("Timeline: reputation events fetch failed: %s", exc)

    # ── research reputation badges ────────────────────────────────────────────
    try:
        badge_docs = await db.research_reputation_badges.find(
            {"user_id": user_id},
            {"badge_id": 1, "badge_name": 1, "awarded_at": 1},
        ).to_list(200)
        for b in badge_docs:
            awarded_at = _parse_dt(b.get("awarded_at"))
            if awarded_at:
                events.append({
                    "type": "badge_earned",
                    "title": f"Badge earned: {b.get('badge_name') or b.get('badge_id') or 'Badge'}",
                    "date": awarded_at.isoformat(),
                    "icon_type": "badge",
                    "metadata": {
                        "badge_id": b.get("badge_id"),
                        "badge_name": b.get("badge_name"),
                    },
                })
    except Exception as exc:
        log.warning("Timeline: reputation badges fetch failed: %s", exc)

    # Sort descending by date, limit to 100 most recent.
    events.sort(key=lambda e: e.get("date") or "", reverse=True)
    return {"events": events[:100], "total": len(events)}


@router.post("/snapshot")
async def save_snapshot(
    payload: SnapshotPayload,
    user: dict = Depends(get_current_user),
):
    """Save a named snapshot of the user's current impact for comparison."""
    _require_service(_snapshot_service_available, "snapshot_service")
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    user_id = user["id"]

    impact_data = await compute_and_store_research_impact(user_id, db)
    now = _now_utc()

    snapshot_doc = {
        "user_id": user_id,
        "label": payload.label or f"Snapshot {now.strftime('%Y-%m-%d %H:%M')}",
        "computed_at": now.isoformat(),
        "impact_data": impact_data,
        "total_sis": (impact_data or {}).get("total") or (impact_data or {}).get("sis_score") or 0,
        "h_index": (impact_data or {}).get("h_index") or 0,
    }

    result = await db.research_impact_snapshots.insert_one(snapshot_doc)
    return {
        "snapshot_id": str(result.inserted_id),
        "label": snapshot_doc["label"],
        "computed_at": snapshot_doc["computed_at"],
    }


@router.get("/snapshots")
async def list_snapshots(user: dict = Depends(get_current_user)):
    """List user's named snapshots from research_impact_snapshots."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    user_id = user["id"]

    docs = await db.research_impact_snapshots.find(
        {"user_id": user_id},
        {"label": 1, "computed_at": 1, "total_sis": 1, "h_index": 1},
    ).sort("computed_at", -1).to_list(100)

    return [
        {
            "id": str(d["_id"]),
            "label": d.get("label") or "",
            "computed_at": d.get("computed_at") or "",
            "total_sis": d.get("total_sis") or 0,
            "h_index": d.get("h_index") or 0,
        }
        for d in docs
    ]


@router.get("/export/csv")
async def export_csv(user: dict = Depends(get_current_user)):
    """CSV export: SIS breakdown + publication list."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    user_id = user["id"]
    email = user.get("email") or user_id
    today = _now_utc().strftime("%Y%m%d")

    # Fetch impact doc for score components.
    impact_doc = await db.research_impact.find_one({"user_id": user_id})
    impact_doc = _oid_to_str(impact_doc or {})

    # Fetch publications.
    pub_docs = await db.publications.find(
        {"owner_id": user_id},
        {"title": 1, "status": 1, "year": 1, "citations": 1, "journal": 1, "doi": 1, "type": 1},
    ).sort("citations", -1).to_list(2000)

    buf = io.StringIO()
    writer = csv.writer(buf)

    # Row 1: SIS total
    sis_total = impact_doc.get("total") or impact_doc.get("sis_score") or 0
    components = impact_doc.get("components") or {}
    writer.writerow(["# Synaptiq Impact Score (SIS)"])
    writer.writerow(["Total SIS"] + list(components.keys()))
    writer.writerow([sis_total] + list(components.values()))
    writer.writerow([])

    # Publications
    writer.writerow(["# Publications"])
    writer.writerow(["Title", "Status", "Year", "Citations", "Journal", "DOI", "Type"])
    for p in pub_docs:
        writer.writerow([
            p.get("title") or "",
            p.get("status") or "",
            p.get("year") or "",
            int(p.get("citations") or 0),
            p.get("journal") or "",
            p.get("doi") or "",
            p.get("type") or "",
        ])

    safe_email = email.replace("@", "_at_").replace(".", "_")
    filename = f"impact-{safe_email}-{today}.csv"
    buf.seek(0)
    return StreamingResponse(
        iter([buf.read()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/export/json")
async def export_json(user: dict = Depends(get_current_user)):
    """Full JSON export of the user's complete research_impact document."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    user_id = user["id"]
    email = user.get("email") or user_id
    today = _now_utc().strftime("%Y%m%d")

    impact_doc = await db.research_impact.find_one({"user_id": user_id})
    if not impact_doc:
        impact_doc = {"user_id": user_id, "message": "No impact data computed yet."}

    serialized = _oid_to_str(impact_doc)

    safe_email = email.replace("@", "_at_").replace(".", "_")
    filename = f"impact-{safe_email}-{today}.json"

    content = json.dumps(serialized, indent=2, default=str)
    return StreamingResponse(
        iter([content]),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/users/{user_id}")
async def get_public_impact(
    user_id: str,
    _current_user: dict = Depends(get_current_user),
):
    """Public impact view for another researcher (respects profile_visibility)."""
    db = get_db()

    db = DBProxy(db, SecurityContext.system())

    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=404, detail="User not found.")

    target_user = await db.users.find_one(
        {"_id": oid},
        {"profile_visibility": 1, "full_name": 1},
    )
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found.")

    if target_user.get("profile_visibility") == "private":
        raise HTTPException(status_code=403, detail="This researcher's profile is private.")

    impact_doc = await db.research_impact.find_one(
        {"user_id": user_id},
        {"total": 1, "sis_score": 1, "h_index": 1, "publication_count": 1,
         "collaboration_count": 1, "label": 1, "computed_at": 1},
    )
    if not impact_doc:
        raise HTTPException(status_code=404, detail="Impact data not available for this researcher.")

    return {
        "user_id": user_id,
        "full_name": target_user.get("full_name") or "",
        "total_sis": impact_doc.get("total") or impact_doc.get("sis_score") or 0,
        "h_index": impact_doc.get("h_index") or 0,
        "publication_count": impact_doc.get("publication_count") or 0,
        "collaboration_count": impact_doc.get("collaboration_count") or 0,
        "label": impact_doc.get("label") or "",
        "computed_at": impact_doc.get("computed_at") or "",
    }
