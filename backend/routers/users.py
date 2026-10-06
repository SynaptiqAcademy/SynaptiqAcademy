import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel

from auth_utils import get_current_user, serialize_user, serialize_public_user, invalidate_user_cache
from db import get_db
from models import ProfileUpdate, OnboardingComplete
from repo.shim import DBProxy
from repo.security_context import SecurityContext
from services.permissions import REAL_CUSTOMER_FILTER
from services.safe_search import contains as safe_contains

router = APIRouter(prefix="/api/users", tags=["users"])

async def _maybe_emit_profile_completed(user_id: str, db):
    """Emit profile_completed reputation event if user now has a complete profile."""
    try:
        from services.reputation.events import emit_reputation_event
        u = await db.users.find_one({"_id": ObjectId(user_id)}, {
            "biography": 1, "institution": 1, "keywords": 1, "avatar_url": 1, "orcid": 1
        })
        if not u:
            return
        has_bio = bool((u.get("biography") or "").strip())
        has_institution = bool((u.get("institution") or "").strip())
        has_keywords = bool(u.get("keywords"))
        has_avatar = bool(u.get("avatar_url"))
        orcid = u.get("orcid") or {}
        has_orcid = bool(orcid.get("orcid_id") if isinstance(orcid, dict) else orcid)
        if has_bio and has_institution and has_keywords and (has_avatar or has_orcid):
            await emit_reputation_event(user_id, "profile_completed", "user", user_id)
    except Exception:
        pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    return user


@router.post("/me/onboarding")
async def complete_onboarding(payload: OnboardingComplete, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    update = payload.model_dump()
    # orcid is OAuth-only (see ProfileUpdate's own field exclusion, models.py) —
    # users.orcid is a dict {orcid_id, access_token, ...} once connected via
    # OAuth; OnboardingComplete.orcid is a legacy plain-string field. Writing
    # it here would silently clobber an already-connected OAuth dict back to
    # a bare string if a user connects ORCID before finishing onboarding.
    update.pop("orcid", None)
    update["full_name"] = f"{payload.first_name} {payload.last_name}".strip()
    update["onboarded"] = True
    await db.users.update_one({"_id": ObjectId(user["id"])}, {"$set": update})
    invalidate_user_cache(user["id"])
    updated = await db.users.find_one({"_id": ObjectId(user["id"])})
    return serialize_user(updated)


@router.patch("/me")
async def update_me(payload: ProfileUpdate, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    # Include lists (even empty — allows clearing) and booleans (False is valid),
    # but skip None which means "not provided / no change".
    dump = payload.model_dump(exclude_unset=True)
    update = {
        k: v for k, v in dump.items()
        if v is not None or isinstance(v, (list, bool))
    }
    if not update:
        return user
    # Auto-derive full_name if first/last name changed
    if "first_name" in update or "last_name" in update:
        fn = update.get("first_name") or user.get("first_name", "")
        ln = update.get("last_name") or user.get("last_name", "")
        update["full_name"] = f"{fn} {ln}".strip()
    # Invalidate last_updated timestamp
    from datetime import datetime, timezone as _tz
    update["last_updated"] = datetime.now(_tz.utc).isoformat()
    await db.users.update_one({"_id": ObjectId(user["id"])}, {"$set": update})
    invalidate_user_cache(user["id"])
    updated = await db.users.find_one({"_id": ObjectId(user["id"])})
    asyncio.ensure_future(_maybe_emit_profile_completed(user["id"], DBProxy(get_db(), SecurityContext.system())))
    return serialize_user(updated)


@router.get("/me/profile-completion")
async def profile_completion(user: dict = Depends(get_current_user)):
    """Return a real-data profile completion score with per-item breakdown.

    Scoring breakdown (max 100):
      avatar             +10  — profile photo present
      biography          +10  — biography written
      institution        +10  — institution field filled
      keywords           +10  — research keywords present
      methods            +5   — research methods filled
      social             +5   — at least one academic link (ORCID/Scholar/ResearchGate/LinkedIn)
      availability       +5   — availability status set
      orcid_connected    +15  — ORCID OAuth connected
      publications       +15  — at least one publication imported
      employment         +10  — employment record present (ORCID or manual)
      education          +5   — education record present (ORCID or manual)
    Total: 100
    """
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    from services.profile_completion import compute_profile_completion
    result = await compute_profile_completion(db, user["id"])
    if result is None:
        raise HTTPException(404, "User not found")
    return result


@router.get("/me/cv")
async def download_cv(user: dict = Depends(get_current_user)):
    """Structured CV data — used by the frontend to generate a printable CV."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    u = await db.users.find_one({"_id": ObjectId(user["id"])})
    if not u:
        raise HTTPException(404, "User not found")
    orcid = (u.get("orcid") or {}) if isinstance(u.get("orcid"), dict) else {}
    pubs = await db.publications.find(
        {"owner_id": user["id"]}
    ).sort([("year", -1)]).limit(100).to_list(100)
    oam = (u.get("openalex_metrics") or {})
    return {
        "generated_at": _now(),
        "identity": {
            "full_name":    u.get("full_name") or "",
            "academic_role": u.get("academic_role") or "",
            "institution":  u.get("institution") or "",
            "department":   u.get("department") or "",
            "city":         u.get("city") or "",
            "country":      u.get("country") or "",
            "biography":    u.get("biography") or "",
            "orcid_id":     orcid.get("orcid_id") or "",
            "google_scholar": u.get("google_scholar") or "",
            "researchgate": u.get("researchgate") or "",
            "linkedin":     u.get("linkedin") or "",
            "website":      u.get("website") or "",
            "scopus_id":    u.get("scopus_id") or "",
            "email":        u.get("email") or "",
        },
        "metrics": {
            "h_index":           int(oam.get("h_index") or u.get("h_index") or 0),
            "i10_index":         int(oam.get("i10_index") or 0),
            "total_citations":   int(oam.get("citations") or 0),
            "publications_count": len(pubs),
        },
        "research": {
            "research_areas":       u.get("research_areas") or [],
            "research_keywords":    u.get("research_keywords") or [],
            "research_interests":   u.get("research_interests") or [],
            "methods":              u.get("methods") or [],
            "skills":               u.get("skills") or [],
            "software_skills":      u.get("software_skills") or [],
            "languages":            u.get("languages") or [],
        },
        "employment": u.get("orcid_employments") or [],
        "education":  u.get("orcid_educations") or [],
        "funding":    u.get("orcid_fundings") or [],
        "awards":     u.get("awards") or [],
        "certifications": u.get("certifications") or [],
        "memberships": u.get("memberships") or [],
        "publications": [
            {
                "title":    p.get("title") or "",
                "year":     p.get("year"),
                "journal":  p.get("journal") or "",
                "type":     p.get("type") or "journal-article",
                "doi":      p.get("doi") or "",
                "citations": int(p.get("citations") or 0),
            }
            for p in pubs
        ],
    }


@router.get("/{user_id}/publications")
async def user_publications(
    user_id: str,
    q: Optional[str] = None,
    type: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=100),
    skip: int = 0,
    _user: dict = Depends(get_current_user),
):
    """List publications for any user (authenticated callers only)."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    try:
        ObjectId(user_id)
    except Exception:
        raise HTTPException(404, "User not found")
    qf: dict = {"owner_id": user_id}
    if type:
        qf["type"] = type
    if q:
        qf["$or"] = [
            {"title": safe_contains(q)},
            {"journal": safe_contains(q)},
        ]
    total = await db.publications.count_documents(qf)
    docs = await db.publications.find(qf).sort([("year", -1), ("title", 1)]).skip(skip).limit(limit).to_list(limit)
    for d in docs:
        d["id"] = str(d.pop("_id"))
    return {"results": docs, "total": total}


@router.get("")
async def list_users(
    # Full-text / keyword search
    q: Optional[str] = None,
    # Field filters
    research_area: Optional[str] = None,
    keyword: Optional[str] = None,
    method: Optional[str] = None,
    software_skill: Optional[str] = None,
    department: Optional[str] = None,
    institution: Optional[str] = None,
    country: Optional[str] = None,
    availability: Optional[str] = None,
    user_type: Optional[str] = None,
    primary_domain: Optional[str] = None,
    teaching_area: Optional[str] = None,
    professional_expertise: Optional[str] = None,
    orcid_id: Optional[str] = None,
    openalex_id: Optional[str] = None,
    # Boolean availability flags
    available_for_collaboration: Optional[bool] = None,
    available_for_reviewing: Optional[bool] = None,
    available_for_consulting: Optional[bool] = None,
    available_for_supervision: Optional[bool] = None,
    # Metric filters
    has_orcid: Optional[bool] = None,
    has_openalex: Optional[bool] = None,
    min_h_index: int = Query(default=0, ge=0),
    min_publications: int = Query(default=0, ge=0),
    # Pagination
    limit: int = Query(default=30, ge=1, le=100),
    cursor: Optional[str] = Query(default=None),
    _user: dict = Depends(get_current_user),
):
    from services.network.discovery_engine import _discovery_exclusions, _to_object_id

    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    query: dict = {
        "is_demo": {"$ne": True},
        # Visibility: exclude users who have explicitly set profile to private
        "profile_visibility": {"$ne": "private"},
        # Internal/staff accounts (the protected super-admin, moderators) are
        # never real researchers to discover or connect with.
        **REAL_CUSTOMER_FILTER,
    }

    # Self-exclusion + the same block/opt-out exclusion already enforced on
    # /api/network/people and /api/profiles/directory — this endpoint was
    # missing both (Phase 3 People Discovery audit). Held separately from
    # `query["_id"]` here and merged in below, alongside cursor pagination,
    # so the two don't clobber each other (both target `_id`).
    excluded = await _discovery_exclusions(db, _user["id"])
    id_nin = [ObjectId(_user["id"])] + [_to_object_id(x) for x in excluded]

    # ── Full-text search ──────────────────────────────────────────────────────
    if q:
        query["$or"] = [
            {"full_name":         safe_contains(q)},
            {"institution":       safe_contains(q)},
            {"department":        safe_contains(q)},
            {"research_areas":    safe_contains(q)},
            {"research_keywords": safe_contains(q)},
            {"skills":            safe_contains(q)},
            {"methods":           safe_contains(q)},
            {"software_skills":   safe_contains(q)},
            {"biography":         safe_contains(q)},
            {"orcid.orcid_id":    safe_contains(q)},
            {"openalex_author_id":safe_contains(q)},
        ]

    # ── Specific field filters ────────────────────────────────────────────────
    if research_area:
        query["research_areas"] = {"$in": [research_area]}
    if keyword:
        query["research_keywords"] = safe_contains(keyword)
    if method:
        query["methods"] = safe_contains(method)
    if software_skill:
        query["software_skills"] = safe_contains(software_skill)
    if department:
        query["department"] = safe_contains(department)
    if institution:
        query["institution"] = safe_contains(institution)
    if country:
        query["country"] = country
    if availability:
        query["availability"] = availability
    if user_type:
        query["user_type"] = user_type
    if primary_domain:
        query["primary_domain"] = primary_domain
    if teaching_area:
        query["teaching_areas"] = teaching_area
    if professional_expertise:
        query["professional_expertise"] = professional_expertise
    if orcid_id:
        query["orcid.orcid_id"] = safe_contains(orcid_id)
    if openalex_id:
        query["openalex_author_id"] = safe_contains(openalex_id)

    # ── Boolean availability ──────────────────────────────────────────────────
    if available_for_collaboration is True:
        query["available_for_collaboration"] = True
    if available_for_reviewing is True:
        query["available_for_reviewing"] = True
    if available_for_consulting is True:
        query["available_for_consulting"] = True
    if available_for_supervision is True:
        query["available_for_supervision"] = True

    # ── Verification filters ──────────────────────────────────────────────────
    if has_orcid is True:
        query["orcid.orcid_id"] = {"$exists": True, "$ne": ""}
    if has_openalex is True:
        query["openalex_author_id"] = {"$exists": True, "$ne": ""}

    # ── Metric floors ─────────────────────────────────────────────────────────
    if min_h_index > 0:
        query["h_index"] = {"$gte": min_h_index}
    if min_publications > 0:
        query["publications_count"] = {"$gte": min_publications}

    # ── Cursor pagination ─────────────────────────────────────────────────────
    id_filter: dict = {"$nin": id_nin}
    if cursor:
        try:
            id_filter["$gt"] = ObjectId(cursor)
        except Exception:
            pass
    query["_id"] = id_filter

    docs = await db.users.find(query).sort("_id", 1).limit(limit).to_list(limit)
    items = [serialize_public_user(u) for u in docs]
    next_cursor = str(docs[-1]["_id"]) if len(docs) == limit else None

    if cursor is not None or next_cursor is not None:
        return {"items": items, "next_cursor": next_cursor}
    return items


@router.get("/{user_id}")
async def get_user(user_id: str, viewer: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    try:
        oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=404, detail="User not found")
    user = await db.users.find_one({"_id": oid})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Visibility enforcement
    visibility = user.get("profile_visibility") or "public"
    if visibility == "private" and str(user["_id"]) != viewer["id"]:
        # A member who chose Network visibility stays visible to people who
        # share a group or community with them, and to no one else.
        from services.discovery_preferences import network_visible_to
        if str(user["_id"]) not in await network_visible_to(db, viewer["id"]):
            raise HTTPException(status_code=404, detail="User not found")

    # Track profile view (async fire-and-forget, never blocks the response)
    if str(user["_id"]) != viewer["id"]:
        try:
            from datetime import datetime as _dt, timezone as _tz
            await db.profile_views.insert_one({
                "viewed_id":  str(user["_id"]),
                "viewer_id":  viewer["id"],
                "created_at": _dt.now(_tz.utc).isoformat(),
            })
        except Exception:
            pass

    return serialize_public_user(user)


@router.get("/{user_id}/stats")
async def get_user_stats(user_id: str, owner: dict = Depends(get_current_user)):
    """Owner-only: profile view count + recent viewers."""
    if user_id != owner["id"]:
        raise HTTPException(403, "Forbidden")
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    total_views = await db.profile_views.count_documents({"viewed_id": user_id})
    recent_raw = await db.profile_views.find(
        {"viewed_id": user_id},
        {"viewer_id": 1, "created_at": 1},
    ).sort("created_at", -1).limit(20).to_list(20)
    viewer_ids = list({ObjectId(r["viewer_id"]) for r in recent_raw if r.get("viewer_id")})
    viewers_map: dict = {}
    if viewer_ids:
        vdocs = await db.users.find(
            {"_id": {"$in": viewer_ids}},
            {"full_name": 1, "institution": 1, "avatar_url": 1},
        ).to_list(len(viewer_ids))
        viewers_map = {str(d["_id"]): {"id": str(d["_id"]), "full_name": d.get("full_name",""), "institution": d.get("institution",""), "avatar_url": d.get("avatar_url")} for d in vdocs}
    recent_views = [
        {**viewers_map.get(r["viewer_id"], {"id": r["viewer_id"]}), "viewed_at": r.get("created_at")}
        for r in recent_raw if r.get("viewer_id")
    ]
    return {"total_views": total_views, "recent_viewers": recent_views[:10]}


@router.post("/{user_id}/connect")
async def connect(user_id: str, user: dict = Depends(get_current_user)):
    """Send a connection request. One-directional until the target accepts."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    if user_id == user["id"]:
        raise HTTPException(status_code=400, detail="Cannot connect to yourself")
    try:
        target_oid = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=404, detail="User not found")
    target = await db.users.find_one({"_id": target_oid}, {"_id": 1})
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    # Prevent duplicate pending requests
    existing = await db.connection_requests.find_one({
        "sender_id": user["id"], "receiver_id": user_id, "status": "pending",
    })
    if existing:
        raise HTTPException(status_code=409, detail="Connection request already pending")
    # Already connected check
    me_doc = await db.users.find_one({"_id": ObjectId(user["id"])}, {"connections": 1})
    if user_id in (me_doc or {}).get("connections", []):
        raise HTTPException(status_code=409, detail="Already connected")
    doc = {
        "sender_id":   user["id"],
        "receiver_id": user_id,
        "status":      "pending",
        "created_at":  _now(),
    }
    try:
        result = await db.connection_requests.insert_one(doc)
    except Exception as dup_err:
        if "duplicate key" in str(dup_err).lower() or "E11000" in str(dup_err):
            raise HTTPException(status_code=409, detail="Connection request already pending")
        raise dup_err
    from services.notifications_service import dispatch, NotificationEvent
    await dispatch(NotificationEvent(
        user_id=user_id,
        kind="connection_request",
        title=f"{user.get('full_name', 'Someone')} wants to connect",
        body="You have a new connection request.",
        link=f"/profile/{user['id']}",
        actor_id=user["id"],
        payload={"request_id": str(result.inserted_id)},
    ))
    return {"ok": True, "status": "pending", "request_id": str(result.inserted_id)}


@router.post("/{user_id}/connect/accept")
async def accept_connect(user_id: str, user: dict = Depends(get_current_user)):
    """Accept a pending connection request from user_id."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    result = await db.connection_requests.update_one(
        {"sender_id": user_id, "receiver_id": user["id"], "status": "pending"},
        {"$set": {"status": "accepted", "responded_at": _now()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="No pending connection request found")
    # Parallel $addToSet — both run concurrently to minimize asymmetry window.
    await asyncio.gather(
        db.users.update_one({"_id": ObjectId(user["id"])}, {"$addToSet": {"connections": user_id}}),
        db.users.update_one({"_id": ObjectId(user_id)}, {"$addToSet": {"connections": user["id"]}}),
    )
    return {"ok": True, "status": "accepted"}


@router.post("/{user_id}/connect/decline")
async def decline_connect(user_id: str, user: dict = Depends(get_current_user)):
    """Decline a pending connection request from user_id."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    result = await db.connection_requests.update_one(
        {"sender_id": user_id, "receiver_id": user["id"], "status": "pending"},
        {"$set": {"status": "declined", "responded_at": _now()}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="No pending request to decline")
    return {"ok": True, "status": "declined"}


@router.delete("/{user_id}/connect")
async def disconnect(user_id: str, user: dict = Depends(get_current_user)):
    """Remove an existing connection or withdraw a pending request."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    # Parallel $pull for both sides + pending request withdrawal — all three are independent.
    await asyncio.gather(
        db.users.update_one({"_id": ObjectId(user["id"])}, {"$pull": {"connections": user_id}}),
        db.users.update_one({"_id": ObjectId(user_id)}, {"$pull": {"connections": user["id"]}}),
        db.connection_requests.update_many(
            {"$or": [
                {"sender_id": user["id"], "receiver_id": user_id},
                {"sender_id": user_id, "receiver_id": user["id"]},
            ], "status": "pending"},
            {"$set": {"status": "withdrawn", "responded_at": _now()}},
        ),
    )
    return {"ok": True}


@router.get("/me/export")
async def export_my_data(user: dict = Depends(get_current_user)):
    """GDPR Articles 15 and 20 — a structured copy of the member's data.
    Built by services/account_lifecycle.build_export: no passwords, tokens,
    secrets, internal storage paths or embeddings."""
    from services.account_lifecycle import build_export
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))
    data = await build_export(db, user["id"])
    try:
        from services.admin_audit import log_event
        await log_event("user.data_export", actor_id=user["id"], target_id=user["id"], target_type="user")
    except Exception:
        pass
    return data


class DeleteAccountIn(BaseModel):
    confirm: str = ""
    password: Optional[str] = None


REAUTH_WINDOW_MINUTES = 10


@router.delete("/me")
async def delete_my_account(payload: DeleteAccountIn, user: dict = Depends(get_current_user)):
    """GDPR Article 17 — self-service account deletion.

    Requires typing DELETE and proving it's really the member: their password,
    or for accounts without one (ORCID/Google sign-in) a sign-in within the
    last few minutes. What is deleted, anonymised, handed over or retained is
    defined in services/account_lifecycle.py.
    """
    from auth_utils import verify_password
    from services.account_lifecycle import DeletionBlocked, delete_account, preflight

    if (payload.confirm or "").strip() != "DELETE":
        raise HTTPException(status_code=400, detail="Type DELETE to confirm.")

    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))
    full = await db.users.find_one({"_id": ObjectId(user["id"])}, {"password_hash": 1, "last_successful_login": 1}) or {}
    if full.get("password_hash"):
        if not payload.password or not verify_password(payload.password, full["password_hash"]):
            raise HTTPException(status_code=403, detail="That password isn't right.")
    else:
        last = full.get("last_successful_login")
        try:
            last_dt = datetime.fromisoformat(last) if isinstance(last, str) else last
            if last_dt and last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)
        except Exception:
            last_dt = None
        if not last_dt or datetime.now(timezone.utc) - last_dt > timedelta(minutes=REAUTH_WINDOW_MINUTES):
            raise HTTPException(status_code=401, detail={
                "code": "reauth_required",
                "message": "For your security, sign out and sign in again, then delete your account within 10 minutes.",
            })

    try:
        await preflight(db, user)
        summary = await delete_account(db, user, actor="self")
    except DeletionBlocked as e:
        raise HTTPException(status_code=409, detail=str(e))
    try:
        invalidate_user_cache(user["id"])
    except Exception:
        pass

    try:
        from services.admin_audit import log_event
        # The record of the deletion keeps the account id only — never the
        # email or name of the person who asked to be forgotten.
        await log_event("user.self_delete", actor_id=user["id"], target_id=user["id"], target_type="user",
                        extra={"summary": summary})
    except Exception:
        pass

    return {"ok": True, "message": "Your account has been deleted."}


@router.get("/me/connection-requests")
async def my_connection_requests(user: dict = Depends(get_current_user)):
    """List pending connection requests received by the current user."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    docs = await db.connection_requests.find(
        {"receiver_id": user["id"], "status": "pending"}
    ).sort("created_at", -1).to_list(100)
    sender_ids = [ObjectId(d["sender_id"]) for d in docs if d.get("sender_id")]
    senders = {}
    if sender_ids:
        for s in await db.users.find({"_id": {"$in": sender_ids}}).to_list(100):
            senders[str(s["_id"])] = serialize_public_user(s)
    out = []
    for d in docs:
        item = {"id": str(d["_id"]), "sender_id": d["sender_id"],
                "status": d["status"], "created_at": d.get("created_at")}
        item["sender"] = senders.get(d["sender_id"])
        out.append(item)
    return out
