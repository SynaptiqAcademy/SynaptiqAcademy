"""Academic Recommendation Engine — Phase XXI.

User-facing endpoints for personalised recommendations across all academic
categories: researchers, projects, journals, conferences, grants, reviewers,
and mentors.

Routes
------
GET  /api/recommendations/all                              — dashboard widget (top 6 per category)
GET  /api/recommendations/researchers                      — researcher suggestions
GET  /api/recommendations/projects                         — project suggestions
GET  /api/recommendations/journals                         — journal suggestions
GET  /api/recommendations/conferences                      — conference suggestions
GET  /api/recommendations/grants                           — grant suggestions
GET  /api/recommendations/reviewers                        — reviewer suggestions (requires manuscript_id or project_id)
GET  /api/recommendations/mentors                          — mentor suggestions
POST /api/recommendations/feedback                         — record an interaction
GET  /api/recommendations/interactions                     — paginated interaction history
DELETE /api/recommendations/interactions/{rec_type}/{target_id} — undo a dismissal
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from auth_utils import get_current_user
from db import get_db
from repo.shim import DBProxy
from repo.security_context import SecurityContext

logger = logging.getLogger("synaptiq.recommendations")

# ── Service layer import (graceful degradation) ───────────────────────────────
try:
    from services.recommendation.engine import (
        get_recommendations,
        record_interaction,
        get_all_recommendations,
    )
    _engine_available = True
except ImportError as _import_err:
    logger.error("Recommendation engine unavailable: %s", _import_err)
    _engine_available = False

_VALID_ACTIONS = {"clicked", "dismissed", "bookmarked", "accepted", "ignored"}
_VALID_TYPES = {
    "researchers", "projects", "journals", "conferences",
    "grants", "reviewers", "mentors",
}
_REFRESH_COOLDOWN_MINUTES = 30

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


def _require_engine() -> None:
    if not _engine_available:
        raise HTTPException(
            status_code=503,
            detail="Recommendation service is temporarily unavailable.",
        )


def _ser_doc(doc: dict) -> dict:
    """Serialize a MongoDB document: convert ObjectId fields to str."""
    if not doc:
        return doc
    out = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, datetime):
            out[k] = v.isoformat()
        elif isinstance(v, dict):
            out[k] = _ser_doc(v)
        elif isinstance(v, list):
            out[k] = [
                _ser_doc(i) if isinstance(i, dict) else
                str(i) if isinstance(i, ObjectId) else i
                for i in v
            ]
        else:
            out[k] = v
    return out


async def _check_refresh_cooldown(user_id: str, category: str, db) -> None:
    """Raise HTTP 429 if the user requested a force-refresh within the last 30 minutes."""
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=_REFRESH_COOLDOWN_MINUTES)
    recent = await db.recommendation_scores.find_one(
        {
            "user_id": user_id,
            "category": category,
            "refreshed_at": {"$gt": cutoff},
        },
        {"refreshed_at": 1},
    )
    if recent:
        refreshed_at: datetime = recent["refreshed_at"]
        if refreshed_at.tzinfo is None:
            refreshed_at = refreshed_at.replace(tzinfo=timezone.utc)
        next_allowed = refreshed_at + timedelta(minutes=_REFRESH_COOLDOWN_MINUTES)
        wait_seconds = int((next_allowed - datetime.now(timezone.utc)).total_seconds())
        raise HTTPException(
            status_code=429,
            detail=(
                f"Refresh cooldown active. Try again in "
                f"{max(wait_seconds, 1)} seconds."
            ),
        )


# ── GET /all ──────────────────────────────────────────────────────────────────

@router.get("/all")
async def all_recommendations(
    force_refresh: bool = Query(False),
    user: dict = Depends(get_current_user),
):
    """Return top 6 recommendations per category for the dashboard widget."""
    _require_engine()
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        result = await get_all_recommendations(user["id"], db, limit_each=6)
        return result
    except Exception as exc:
        logger.exception("Error fetching all recommendations for user %s", user["id"])
        raise HTTPException(status_code=500, detail=str(exc))


# ── GET /researchers ──────────────────────────────────────────────────────────

@router.get("/researchers")
async def researcher_recommendations(
    limit: int = Query(20, ge=1, le=50),
    force_refresh: bool = Query(False),
    country: Optional[str] = Query(None),
    area: Optional[str] = Query(None),
    role: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    _require_engine()
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    if force_refresh:
        await _check_refresh_cooldown(user["id"], "researchers", db)
    filters = {}
    if country:
        filters["country"] = country
    if area:
        filters["area"] = area
    if role:
        filters["role"] = role
    try:
        result = await get_recommendations(
            user["id"], "researchers", db,
            limit=limit, force_refresh=force_refresh,
            filters=filters,
        )
        return result
    except Exception as exc:
        logger.exception("Error fetching researcher recs for user %s", user["id"])
        raise HTTPException(status_code=500, detail=str(exc))


# ── GET /projects ─────────────────────────────────────────────────────────────

@router.get("/projects")
async def project_recommendations(
    limit: int = Query(20, ge=1, le=50),
    force_refresh: bool = Query(False),
    area: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    _require_engine()
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    if force_refresh:
        await _check_refresh_cooldown(user["id"], "projects", db)
    filters = {}
    if area:
        filters["area"] = area
    try:
        result = await get_recommendations(
            user["id"], "projects", db,
            limit=limit, force_refresh=force_refresh,
            filters=filters,
        )
        return result
    except Exception as exc:
        logger.exception("Error fetching project recs for user %s", user["id"])
        raise HTTPException(status_code=500, detail=str(exc))


# ── GET /journals ─────────────────────────────────────────────────────────────

@router.get("/journals")
async def journal_recommendations(
    limit: int = Query(20, ge=1, le=50),
    force_refresh: bool = Query(False),
    open_access: Optional[bool] = Query(None),
    quartile: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    _require_engine()
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    if force_refresh:
        await _check_refresh_cooldown(user["id"], "journals", db)
    filters = {}
    if open_access is not None:
        filters["open_access"] = open_access
    if quartile:
        filters["quartile"] = quartile
    try:
        result = await get_recommendations(
            user["id"], "journals", db,
            limit=limit, force_refresh=force_refresh,
            filters=filters,
        )
        return result
    except Exception as exc:
        logger.exception("Error fetching journal recs for user %s", user["id"])
        raise HTTPException(status_code=500, detail=str(exc))


# ── GET /conferences ──────────────────────────────────────────────────────────

@router.get("/conferences")
async def conference_recommendations(
    limit: int = Query(20, ge=1, le=50),
    force_refresh: bool = Query(False),
    area: Optional[str] = Query(None),
    deadline_state: Optional[str] = Query(None, regex="^(open|any)$"),
    user: dict = Depends(get_current_user),
):
    _require_engine()
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    if force_refresh:
        await _check_refresh_cooldown(user["id"], "conferences", db)
    filters = {}
    if area:
        filters["area"] = area
    if deadline_state:
        filters["deadline_state"] = deadline_state
    try:
        result = await get_recommendations(
            user["id"], "conferences", db,
            limit=limit, force_refresh=force_refresh,
            filters=filters,
        )
        return result
    except Exception as exc:
        logger.exception("Error fetching conference recs for user %s", user["id"])
        raise HTTPException(status_code=500, detail=str(exc))


# ── GET /grants ───────────────────────────────────────────────────────────────

@router.get("/grants")
async def grant_recommendations(
    limit: int = Query(20, ge=1, le=50),
    force_refresh: bool = Query(False),
    area: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    _require_engine()
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    if force_refresh:
        await _check_refresh_cooldown(user["id"], "grants", db)
    filters = {}
    if area:
        filters["area"] = area
    try:
        result = await get_recommendations(
            user["id"], "grants", db,
            limit=limit, force_refresh=force_refresh,
            filters=filters,
        )
        return result
    except Exception as exc:
        logger.exception("Error fetching grant recs for user %s", user["id"])
        raise HTTPException(status_code=500, detail=str(exc))


# ── GET /reviewers ────────────────────────────────────────────────────────────

@router.get("/reviewers")
async def reviewer_recommendations(
    limit: int = Query(20, ge=1, le=50),
    force_refresh: bool = Query(False),
    manuscript_id: Optional[str] = Query(None),
    project_id: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    _require_engine()
    if not manuscript_id and not project_id:
        raise HTTPException(
            status_code=422,
            detail="Either manuscript_id or project_id is required for reviewer recommendations.",
        )
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    if force_refresh:
        await _check_refresh_cooldown(user["id"], "reviewers", db)
    try:
        result = await get_recommendations(
            user["id"], "reviewers", db,
            limit=limit, force_refresh=force_refresh,
            filters={},
            manuscript_id=manuscript_id,
            project_id=project_id,
        )
        return result
    except Exception as exc:
        logger.exception("Error fetching reviewer recs for user %s", user["id"])
        raise HTTPException(status_code=500, detail=str(exc))


# ── GET /mentors ──────────────────────────────────────────────────────────────

@router.get("/mentors")
async def mentor_recommendations(
    limit: int = Query(20, ge=1, le=50),
    force_refresh: bool = Query(False),
    area: Optional[str] = Query(None),
    user: dict = Depends(get_current_user),
):
    _require_engine()
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    if force_refresh:
        await _check_refresh_cooldown(user["id"], "mentors", db)
    filters = {}
    if area:
        filters["area"] = area
    try:
        result = await get_recommendations(
            user["id"], "mentors", db,
            limit=limit, force_refresh=force_refresh,
            filters=filters,
        )
        return result
    except Exception as exc:
        logger.exception("Error fetching mentor recs for user %s", user["id"])
        raise HTTPException(status_code=500, detail=str(exc))


# ── POST /feedback ────────────────────────────────────────────────────────────

class FeedbackBody(BaseModel):
    recommendation_type: str  # researchers|projects|journals|conferences|grants|reviewers|mentors
    target_id: str
    action: str               # clicked|dismissed|bookmarked|accepted|ignored


@router.post("/feedback")
async def record_feedback(
    body: FeedbackBody,
    user: dict = Depends(get_current_user),
):
    """Record a user interaction with a recommendation."""
    _require_engine()
    if body.action not in _VALID_ACTIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid action '{body.action}'. Must be one of: {', '.join(sorted(_VALID_ACTIONS))}.",
        )
    if body.recommendation_type not in _VALID_TYPES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid recommendation_type '{body.recommendation_type}'. "
                f"Must be one of: {', '.join(sorted(_VALID_TYPES))}."
            ),
        )
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        await record_interaction(
            user["id"],
            body.recommendation_type,
            body.target_id,
            body.action,
            db,
        )
        return {"recorded": True}
    except Exception as exc:
        logger.exception(
            "Error recording interaction for user %s type=%s target=%s action=%s",
            user["id"], body.recommendation_type, body.target_id, body.action,
        )
        raise HTTPException(status_code=500, detail=str(exc))


# ── GET /interactions ─────────────────────────────────────────────────────────

@router.get("/interactions")
async def get_interactions(
    rec_type: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: dict = Depends(get_current_user),
):
    """Return the authenticated user's paginated recommendation interaction history."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    query: dict = {"user_id": user["id"]}
    if rec_type:
        query["recommendation_type"] = rec_type
    if action:
        query["action"] = action

    skip = (page - 1) * limit
    try:
        cursor = db.recommendation_interactions.find(query).sort("created_at", -1).skip(skip).limit(limit)
        docs = await cursor.to_list(limit)
        total = await db.recommendation_interactions.count_documents(query)
        return {
            "items": [_ser_doc(d) for d in docs],
            "total": total,
            "page": page,
            "limit": limit,
            "pages": max(1, -(-total // limit)),  # ceiling division
        }
    except Exception as exc:
        logger.exception("Error fetching interactions for user %s", user["id"])
        raise HTTPException(status_code=500, detail=str(exc))


# ── DELETE /interactions/{rec_type}/{target_id} ───────────────────────────────

@router.delete("/interactions/{rec_type}/{target_id}")
async def remove_interaction(
    rec_type: str,
    target_id: str,
    user: dict = Depends(get_current_user),
):
    """Remove a specific interaction (e.g. undo a dismissal so the item reappears)."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    if rec_type not in _VALID_TYPES:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Invalid rec_type '{rec_type}'. "
                f"Must be one of: {', '.join(sorted(_VALID_TYPES))}."
            ),
        )
    try:
        result = await db.recommendation_interactions.delete_one(
            {
                "user_id": user["id"],
                "recommendation_type": rec_type,
                "target_id": target_id,
            }
        )
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=404,
                detail="Interaction not found.",
            )
        # Invalidate cached recommendation scores for this category so the item
        # can reappear on the next request.
        await db.recommendation_scores.delete_many(
            {"user_id": user["id"], "category": rec_type}
        )
        return {"removed": True}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception(
            "Error removing interaction for user %s type=%s target=%s",
            user["id"], rec_type, target_id,
        )
        raise HTTPException(status_code=500, detail=str(exc))
