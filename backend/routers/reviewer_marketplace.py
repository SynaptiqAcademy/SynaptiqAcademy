from __future__ import annotations
import asyncio
import logging
from typing import Optional, List
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from auth_utils import get_current_user
from db import get_db
from repo.shim import make_db_proxy
from zt.deps import zt_check, zt_is_admin, zt_is_super_admin

logger = logging.getLogger("synaptiq")
router = APIRouter(prefix="/api/reviewer-marketplace", tags=["reviewer-marketplace"])

def _s(v): return str(v) if v is not None else None

# ── Pydantic models ──────────────────────────────────────────────────────────

class UpdateReviewerProfileBody(BaseModel):
    research_areas: Optional[List[str]] = None
    methods_expertise: Optional[List[str]] = None
    languages: Optional[List[str]] = None
    availability_status: Optional[str] = None
    country: Optional[str] = None

class CreateReviewRequestBody(BaseModel):
    title: str
    description: str = ""
    review_type: str  # manuscript/grant/thesis/conference/methodology/statistical/data/dissertation/custom
    research_area: str = ""
    keywords: List[str] = []
    required_expertise: List[str] = []
    methodology: str = ""
    deadline: Optional[str] = None
    confidentiality: str = "anonymous"  # public/anonymous/double-blind/single-blind
    visibility: str = "public"

class UpdateReviewRequestBody(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    required_expertise: Optional[List[str]] = None
    deadline: Optional[str] = None
    status: Optional[str] = None
    visibility: Optional[str] = None

class InviteReviewerBody(BaseModel):
    reviewer_user_id: str
    message: str = ""
    due_date: Optional[str] = None

class AssignmentResponseBody(BaseModel):
    response: str  # "accepted" or "declined"
    message: str = ""

class SubmitReportBody(BaseModel):
    overall_recommendation: str  # accept/minor_revisions/major_revisions/reject/resubmit
    overall_score: float = 5.0  # 0-10
    summary_comments: str = ""
    confidential_comments: str = ""
    review_sections: List[dict] = []  # [{section_title, score, comments}]

class RateReviewBody(BaseModel):
    rating: int  # 1-5
    timeliness_rating: int = 3
    quality_rating: int = 3
    helpfulness_rating: int = 3
    comment: str = ""


# ══════════════════════════════════════════════════════════════════════════════
# REVIEWER PROFILE ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/profile/me")
async def get_my_reviewer_profile(user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    try:
        from services.reviewer_marketplace.reviewer_service import get_or_create_reviewer_profile
    except ImportError:
        raise HTTPException(status_code=503, detail="Reviewer Marketplace services unavailable")
    return await get_or_create_reviewer_profile(user["id"], db)

@router.patch("/profile/me")
async def update_my_reviewer_profile(body: UpdateReviewerProfileBody, user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    try:
        from services.reviewer_marketplace.reviewer_service import update_reviewer_profile
    except ImportError:
        raise HTTPException(status_code=503, detail="Reviewer Marketplace services unavailable")
    updates = {k: v for k, v in body.dict().items() if v is not None}
    return await update_reviewer_profile(user["id"], updates, db)

@router.post("/profile/me/refresh-score")
async def refresh_my_reviewer_score(user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    try:
        from services.reviewer_marketplace.reviewer_service import compute_reviewer_score
    except ImportError:
        raise HTTPException(status_code=503, detail="Reviewer Marketplace services unavailable")
    score = await compute_reviewer_score(user["id"], db)
    return {"reviewer_score": score}

@router.get("/profile/{user_id}")
async def get_reviewer_profile(user_id: str, db=Depends(get_db)):
    db = make_db_proxy(db, system=True)
    try:
        from services.reviewer_marketplace.reviewer_service import get_reviewer_public_profile
    except ImportError:
        raise HTTPException(status_code=503, detail="Reviewer Marketplace services unavailable")
    return await get_reviewer_public_profile(user_id, db)

@router.get("/reviewers")
async def list_reviewers(
    research_area: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    methods_expertise: Optional[str] = Query(None),
    availability_status: Optional[str] = Query(None),
    reviewer_level: Optional[int] = Query(None),
    min_rating: Optional[float] = Query(None),
    verified_reviewer: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    db=Depends(get_db),
):
    db = make_db_proxy(db, system=True)
    try:
        from services.reviewer_marketplace.reviewer_service import list_reviewers as _list_reviewers
    except ImportError:
        raise HTTPException(status_code=503, detail="Reviewer Marketplace services unavailable")
    filters = {}
    if research_area: filters["research_area"] = research_area
    if country: filters["country"] = country
    if methods_expertise: filters["methods_expertise"] = methods_expertise
    if availability_status: filters["availability_status"] = availability_status
    if reviewer_level: filters["reviewer_level"] = reviewer_level
    if min_rating: filters["min_rating"] = min_rating
    if verified_reviewer is not None: filters["verified_reviewer"] = verified_reviewer
    return await _list_reviewers(db, filters, page, limit)


# ══════════════════════════════════════════════════════════════════════════════
# REVIEW REQUEST ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/requests")
async def create_review_request(body: CreateReviewRequestBody, user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "requester_user_id": user["id"],
        "title": body.title,
        "description": body.description,
        "review_type": body.review_type,
        "research_area": body.research_area,
        "keywords": body.keywords,
        "required_expertise": body.required_expertise,
        "methodology": body.methodology,
        "deadline": body.deadline,
        "confidentiality": body.confidentiality,
        "status": "open",
        "visibility": body.visibility,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.review_requests.insert_one(doc)
    doc["_id"] = _s(result.inserted_id)
    return doc

@router.get("/requests")
async def list_review_requests(
    status: Optional[str] = Query(None),
    review_type: Optional[str] = Query(None),
    research_area: Optional[str] = Query(None),
    visibility: str = Query("public"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    db=Depends(get_db),
):
    db = make_db_proxy(db, system=True)
    query: dict = {"visibility": visibility}
    if status: query["status"] = status
    if review_type: query["review_type"] = review_type
    if research_area: query["research_area"] = {"$regex": research_area, "$options": "i"}
    total = await db.review_requests.count_documents(query)
    skip = (page - 1) * limit
    items = []
    async for r in db.review_requests.find(query).sort("created_at", -1).skip(skip).limit(limit):
        r["_id"] = _s(r["_id"])
        # Join requester name
        try:
            u = await db.users.find_one({"_id": ObjectId(r["requester_user_id"])}, {"full_name": 1})
            r["requester_name"] = (u or {}).get("full_name", "")
        except Exception:
            r["requester_name"] = ""
        items.append(r)
    return {"items": items, "total": total, "page": page, "pages": max(1, -(-total // limit))}

@router.get("/requests/my")
async def my_review_requests(user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    items = []
    async for r in db.review_requests.find({"requester_user_id": user["id"]}).sort("created_at", -1):
        r["_id"] = _s(r["_id"])
        # count assignments
        r["assignment_count"] = await db.review_assignments.count_documents({"request_id": _s(r["_id"])})
        items.append(r)
    return items

@router.get("/requests/assigned-to-me")
async def my_assignments(user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    items = []
    async for a in db.review_assignments.find({"reviewer_user_id": user["id"]}).sort("invited_at", -1):
        a["_id"] = _s(a["_id"])
        # join request
        try:
            req = await db.review_requests.find_one({"_id": ObjectId(a["request_id"])})
            if req: req["_id"] = _s(req["_id"])
            a["request"] = req
        except Exception:
            a["request"] = None
        items.append(a)
    return items

@router.get("/requests/{rid}")
async def get_review_request(rid: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    try:
        req = await db.review_requests.find_one({"_id": ObjectId(rid)})
    except Exception:
        raise HTTPException(status_code=404, detail="Review request not found")
    if not req:
        raise HTTPException(status_code=404, detail="Review request not found")
    req["_id"] = _s(req["_id"])
    # Get assignments
    assignments = []
    async for a in db.review_assignments.find({"request_id": rid}):
        a["_id"] = _s(a["_id"])
        # join reviewer info (only for requester)
        if req["requester_user_id"] == user["id"] or zt_is_super_admin(user):
            try:
                rv = await db.users.find_one({"_id": ObjectId(a["reviewer_user_id"])}, {"full_name": 1, "avatar_url": 1})
                a["reviewer_name"] = (rv or {}).get("full_name", "")
            except Exception:
                a["reviewer_name"] = ""
        assignments.append(a)
    req["assignments"] = assignments
    # Get conflicts count
    req["conflict_count"] = await db.review_conflicts.count_documents({"request_id": rid})
    return req

@router.patch("/requests/{rid}")
async def update_review_request(rid: str, body: UpdateReviewRequestBody, user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    req = await db.review_requests.find_one({"_id": ObjectId(rid)}, {"requester_user_id": 1})
    if not req or req["requester_user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to update this request")
    updates = {k: v for k, v in body.dict().items() if v is not None}
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.review_requests.update_one({"_id": ObjectId(rid)}, {"$set": updates})
    updated = await db.review_requests.find_one({"_id": ObjectId(rid)})
    updated["_id"] = _s(updated["_id"])
    return updated

@router.delete("/requests/{rid}")
async def delete_review_request(rid: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    req = await db.review_requests.find_one({"_id": ObjectId(rid)}, {"requester_user_id": 1})
    if not req or req["requester_user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    await db.review_requests.update_one({"_id": ObjectId(rid)}, {"$set": {"status": "archived", "updated_at": datetime.now(timezone.utc).isoformat()}})
    return {"archived": True}


# ══════════════════════════════════════════════════════════════════════════════
# MATCHING & CONFLICT ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/requests/{rid}/matches")
async def get_reviewer_matches(rid: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    try:
        from services.reviewer_marketplace.matching_engine import match_reviewers_for_request
    except ImportError:
        raise HTTPException(status_code=503, detail="Reviewer Marketplace services unavailable")
    return await match_reviewers_for_request(rid, db)

@router.post("/requests/{rid}/matches/refresh")
async def refresh_matches(rid: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    try:
        from services.reviewer_marketplace.matching_engine import match_reviewers_for_request
    except ImportError:
        raise HTTPException(status_code=503, detail="Reviewer Marketplace services unavailable")
    return await match_reviewers_for_request(rid, db, limit=10)

@router.get("/requests/{rid}/conflicts")
async def get_conflicts(rid: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    try:
        from services.reviewer_marketplace.conflict_detection import get_conflicts_for_request
    except ImportError:
        raise HTTPException(status_code=503, detail="Reviewer Marketplace services unavailable")
    return await get_conflicts_for_request(rid, db)

@router.post("/requests/{rid}/check-conflict/{reviewer_user_id}")
async def check_conflict(rid: str, reviewer_user_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    try:
        from services.reviewer_marketplace.conflict_detection import detect_conflicts
    except ImportError:
        raise HTTPException(status_code=503, detail="Reviewer Marketplace services unavailable")
    conflicts = await detect_conflicts(rid, reviewer_user_id, db)
    return {"has_conflict": len(conflicts) > 0, "conflicts": conflicts}


# ══════════════════════════════════════════════════════════════════════════════
# ASSIGNMENT ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/requests/{rid}/invite")
async def invite_reviewer(rid: str, body: InviteReviewerBody, user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    # Verify requester owns this request
    req = await db.review_requests.find_one({"_id": ObjectId(rid)}, {"requester_user_id": 1, "status": 1, "title": 1})
    if not req or req["requester_user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized")
    # Check not already invited
    existing = await db.review_assignments.find_one({"request_id": rid, "reviewer_user_id": body.reviewer_user_id, "status": {"$nin": ["declined", "withdrawn"]}})
    if existing:
        raise HTTPException(status_code=400, detail="Reviewer already invited")
    # Check conflicts
    try:
        from services.reviewer_marketplace.conflict_detection import detect_conflicts
        conflicts = await detect_conflicts(rid, body.reviewer_user_id, db)
        if conflicts:
            raise HTTPException(status_code=400, detail=f"Conflict of interest detected: {conflicts[0]['conflict_type']}")
    except ImportError:
        pass
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "request_id": rid,
        "reviewer_user_id": body.reviewer_user_id,
        "status": "invited",
        "message": body.message,
        "due_date": body.due_date,
        "invited_at": now,
        "accepted_at": None,
        "completed_at": None,
    }
    result = await db.review_assignments.insert_one(doc)
    doc["_id"] = _s(result.inserted_id)
    # Create notification
    try:
        await db.notifications.insert_one({"user_id": body.reviewer_user_id, "type": "review_invitation", "message": f"You have been invited to review: {req.get('title','a submission')}", "read": False, "created_at": now})
    except Exception:
        pass
    # Update request status to "matching" if open
    if req.get("status") == "open":
        await db.review_requests.update_one({"_id": ObjectId(rid)}, {"$set": {"status": "matching", "updated_at": now}})
    return doc

@router.post("/assignments/{aid}/respond")
async def respond_to_assignment(aid: str, body: AssignmentResponseBody, user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    try:
        assignment = await db.review_assignments.find_one({"_id": ObjectId(aid)})
    except Exception:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if assignment["reviewer_user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not your assignment")
    if assignment["status"] not in ("invited",):
        raise HTTPException(status_code=400, detail=f"Cannot respond to assignment in status: {assignment['status']}")
    now = datetime.now(timezone.utc).isoformat()
    new_status = "accepted" if body.response == "accepted" else "declined"
    updates: dict = {"status": new_status}
    if new_status == "accepted":
        updates["accepted_at"] = now
        # Move request to "in_review"
        await db.review_requests.update_one({"_id": ObjectId(assignment["request_id"])}, {"$set": {"status": "in_review", "updated_at": now}})
    await db.review_assignments.update_one({"_id": ObjectId(aid)}, {"$set": updates})
    return {"assignment_id": aid, "status": new_status}

@router.post("/assignments/{aid}/withdraw")
async def withdraw_assignment(aid: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    try:
        assignment = await db.review_assignments.find_one({"_id": ObjectId(aid)})
    except Exception:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if not assignment or assignment["reviewer_user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not your assignment")
    await db.review_assignments.update_one({"_id": ObjectId(aid)}, {"$set": {"status": "withdrawn"}})
    return {"withdrawn": True}


# ══════════════════════════════════════════════════════════════════════════════
# REVIEW REPORT ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/assignments/{aid}/report")
async def submit_review_report(aid: str, body: SubmitReportBody, user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    try:
        assignment = await db.review_assignments.find_one({"_id": ObjectId(aid)})
    except Exception:
        raise HTTPException(status_code=404, detail="Assignment not found")
    if not assignment or assignment["reviewer_user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Not your assignment")
    if assignment["status"] not in ("accepted",):
        raise HTTPException(status_code=400, detail="Assignment must be accepted before submitting report")
    now = datetime.now(timezone.utc).isoformat()
    # Check for existing report (versioning)
    existing = await db.review_reports.find_one({"assignment_id": aid})
    version = (existing.get("version", 0) + 1) if existing else 1
    doc = {
        "request_id": assignment["request_id"],
        "reviewer_user_id": user["id"],
        "assignment_id": aid,
        "overall_recommendation": body.overall_recommendation,
        "overall_score": max(0.0, min(10.0, body.overall_score)),
        "summary_comments": body.summary_comments,
        "confidential_comments": body.confidential_comments,
        "review_sections": body.review_sections,
        "version": version,
        "submitted_at": now,
        "created_at": now,
    }
    if existing:
        await db.review_reports.update_one({"_id": existing["_id"]}, {"$set": doc})
        doc["_id"] = _s(existing["_id"])
    else:
        result = await db.review_reports.insert_one(doc)
        doc["_id"] = _s(result.inserted_id)
    # Mark assignment completed
    await db.review_assignments.update_one({"_id": ObjectId(aid)}, {"$set": {"status": "completed", "completed_at": now}})
    # Compute quality
    try:
        from services.reviewer_marketplace.quality_engine import compute_review_quality, update_reviewer_stats
        report_id = doc["_id"] if isinstance(doc["_id"], str) else str(doc["_id"])
        await compute_review_quality(report_id, db)
        await update_reviewer_stats(user["id"], db)
    except ImportError:
        pass
    return doc

@router.get("/requests/{rid}/report")
async def get_review_report(rid: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    # Check user is requester or reviewer
    req = await db.review_requests.find_one({"_id": ObjectId(rid)}, {"requester_user_id": 1, "confidentiality": 1})
    if not req:
        raise HTTPException(status_code=404, detail="Request not found")
    report = await db.review_reports.find_one({"request_id": rid})
    if not report:
        raise HTTPException(status_code=404, detail="No report submitted yet")
    report["_id"] = _s(report["_id"])
    # Hide confidential comments from non-requesters
    if req["requester_user_id"] != user["id"] and report.get("reviewer_user_id") != user["id"]:
        report.pop("confidential_comments", None)
    return report


# ══════════════════════════════════════════════════════════════════════════════
# RATING ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/requests/{rid}/rate-reviewer")
async def rate_reviewer(rid: str, body: RateReviewBody, user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    req = await db.review_requests.find_one({"_id": ObjectId(rid)}, {"requester_user_id": 1, "status": 1})
    if not req or req["requester_user_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Only the requester can rate reviewers")
    if req.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Can only rate after review is completed")
    # Get the reviewer
    assignment = await db.review_assignments.find_one({"request_id": rid, "status": "completed"})
    if not assignment:
        raise HTTPException(status_code=404, detail="No completed assignment found")
    reviewer_user_id = assignment["reviewer_user_id"]
    # Check not already rated
    existing = await db.review_ratings.find_one({"request_id": rid, "rater_user_id": user["id"]})
    if existing:
        raise HTTPException(status_code=400, detail="Already rated this review")
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "request_id": rid,
        "reviewer_user_id": reviewer_user_id,
        "rater_user_id": user["id"],
        "rating": max(1, min(5, body.rating)),
        "timeliness_rating": max(1, min(5, body.timeliness_rating)),
        "quality_rating": max(1, min(5, body.quality_rating)),
        "helpfulness_rating": max(1, min(5, body.helpfulness_rating)),
        "comment": body.comment,
        "created_at": now,
    }
    result = await db.review_ratings.insert_one(doc)
    doc["_id"] = _s(result.inserted_id)
    # Update reviewer stats
    try:
        from services.reviewer_marketplace.quality_engine import update_reviewer_stats
        await update_reviewer_stats(reviewer_user_id, db)
    except ImportError:
        pass
    # Mark request as completed
    await db.review_requests.update_one({"_id": ObjectId(rid)}, {"$set": {"status": "completed", "updated_at": now}})
    return doc

@router.get("/reviewers/{uid}/ratings")
async def get_reviewer_ratings(uid: str, db=Depends(get_db)):
    db = make_db_proxy(db, system=True)
    items = []
    async for r in db.review_ratings.find({"reviewer_user_id": uid}).sort("created_at", -1).limit(20):
        r["_id"] = _s(r["_id"])
        items.append(r)
    return items


# ══════════════════════════════════════════════════════════════════════════════
# ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/analytics/reviewer")
async def my_reviewer_analytics(user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    try:
        from services.reviewer_marketplace.analytics_service import get_reviewer_analytics
    except ImportError:
        raise HTTPException(status_code=503, detail="Reviewer Marketplace services unavailable")
    return await get_reviewer_analytics(user["id"], db)

@router.get("/analytics/requester")
async def my_requester_analytics(user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    try:
        from services.reviewer_marketplace.analytics_service import get_requester_analytics
    except ImportError:
        raise HTTPException(status_code=503, detail="Reviewer Marketplace services unavailable")
    return await get_requester_analytics(user["id"], db)


# ══════════════════════════════════════════════════════════════════════════════
# ADMIN ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/admin/stats")
async def admin_marketplace_stats(user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    zt_check(user, "admin", "admin")
    try:
        from services.reviewer_marketplace.analytics_service import get_platform_review_analytics
    except ImportError:
        raise HTTPException(status_code=503, detail="Reviewer Marketplace services unavailable")
    return await get_platform_review_analytics(db)

@router.post("/admin/certify/{uid}")
async def certify_reviewer(uid: str, cert_type: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    zt_check(user, "admin", "admin")
    try:
        from services.reviewer_marketplace.reviewer_service import award_certification
    except ImportError:
        raise HTTPException(status_code=503, detail="Reviewer Marketplace services unavailable")
    try:
        return await award_certification(uid, cert_type, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
