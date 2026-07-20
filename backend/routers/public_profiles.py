from __future__ import annotations
import asyncio
import logging
from typing import Optional, List
from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi import Security
from pydantic import BaseModel
from auth_utils import get_current_user
from db import get_db
from zt.deps import zt_check, zt_is_admin, zt_is_super_admin
from repo.shim import make_db_proxy

logger = logging.getLogger("synaptiq")
router = APIRouter(prefix="/api/profiles", tags=["public-profiles"])
_bearer = HTTPBearer(auto_error=False)

def _s(v):
    return str(v) if v is not None else None

# ── Pydantic models ──────────────────────────────────────────────────────────

class ClaimSlugBody(BaseModel):
    slug: str

class ShowcaseItemBody(BaseModel):
    item_type: str
    item_id: str
    custom_label: str = ""

class ShowcaseOrderBody(BaseModel):
    ordered_ids: List[str]

class VisibilityBody(BaseModel):
    publications: str = "public"
    impact: str = "public"
    projects: str = "public"
    grants: str = "public"
    collaborations: str = "public"
    teaching: str = "public"
    reputation: str = "public"
    timeline: str = "public"
    contact: str = "public"

# ── Helpers ──────────────────────────────────────────────────────────────────

async def _get_optional_viewer(credentials: Optional[HTTPAuthorizationCredentials]) -> Optional[str]:
    if not credentials:
        return None
    try:
        import jwt as pyjwt
        import os
        secret = os.environ.get("JWT_SECRET", "")
        payload = pyjwt.decode(credentials.credentials, secret, algorithms=["HS256"])
        return str(payload.get("sub") or payload.get("user_id") or payload.get("id") or "")
    except Exception:
        return None

async def _slug_to_user_id(slug: str, db) -> str:
    try:
        from services.public_profiles.slug_service import get_user_id_by_slug
    except ImportError:
        raise HTTPException(status_code=503, detail="Profile services unavailable")
    user_id = await get_user_id_by_slug(slug, db)
    if not user_id:
        raise HTTPException(status_code=404, detail="Researcher profile not found")
    return user_id

async def _check_visibility(slug: str, section: str, db) -> str:
    """Return user_id if section is public, raise 404 otherwise."""
    doc = await db.public_profiles.find_one({"slug": slug}, {"user_id": 1, "visibility_settings": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Profile not found")
    vs = doc.get("visibility_settings") or {}
    if vs.get(section, "public") != "public":
        raise HTTPException(status_code=403, detail=f"Section '{section}' is not public")
    return doc["user_id"]

# ══════════════════════════════════════════════════════════════════════════════
# MY PROFILE ENDPOINTS (authenticated) — registered BEFORE /{slug} routes
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/me")
async def get_my_profile(user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    try:
        from services.public_profiles.slug_service import get_or_create_profile
        from services.public_profiles.profile_service import get_full_profile
    except ImportError:
        raise HTTPException(status_code=503, detail="Profile services unavailable")
    await get_or_create_profile(user["id"], db)
    return await get_full_profile(user["id"], db, viewer_id=user["id"])

@router.post("/me/slug")
async def claim_slug(body: ClaimSlugBody, user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    try:
        from services.public_profiles.slug_service import claim_custom_slug
    except ImportError:
        raise HTTPException(status_code=503, detail="Profile services unavailable")
    try:
        return await claim_custom_slug(user["id"], body.slug, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/me/analytics")
async def my_analytics(user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    try:
        from services.public_profiles.analytics_service import get_profile_analytics
    except ImportError:
        raise HTTPException(status_code=503, detail="Profile services unavailable")
    return await get_profile_analytics(user["id"], db)

@router.get("/me/showcase")
async def get_my_showcase(user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    try:
        from services.public_profiles.showcase_service import get_showcase
    except ImportError:
        raise HTTPException(status_code=503, detail="Profile services unavailable")
    return await get_showcase(user["id"], db)

@router.post("/me/showcase")
async def add_to_showcase(body: ShowcaseItemBody, user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    try:
        from services.public_profiles.showcase_service import add_showcase_item
    except ImportError:
        raise HTTPException(status_code=503, detail="Profile services unavailable")
    try:
        return await add_showcase_item(user["id"], body.item_type, body.item_id, body.custom_label, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/me/showcase/order")
async def reorder_showcase(body: ShowcaseOrderBody, user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    try:
        from services.public_profiles.showcase_service import update_showcase_order
    except ImportError:
        raise HTTPException(status_code=503, detail="Profile services unavailable")
    return await update_showcase_order(user["id"], body.ordered_ids, db)

@router.delete("/me/showcase/{showcase_id}")
async def remove_from_showcase(showcase_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    try:
        from services.public_profiles.showcase_service import remove_showcase_item
    except ImportError:
        raise HTTPException(status_code=503, detail="Profile services unavailable")
    ok = await remove_showcase_item(user["id"], showcase_id, db)
    if not ok:
        raise HTTPException(status_code=404, detail="Showcase item not found")
    return {"deleted": True}

@router.get("/me/visibility")
async def get_visibility(user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    doc = await db.public_profiles.find_one({"user_id": user["id"]}, {"visibility_settings": 1})
    default = {"publications": "public", "impact": "public", "projects": "public", "grants": "public",
               "collaborations": "public", "teaching": "public", "reputation": "public", "timeline": "public", "contact": "public"}
    return (doc or {}).get("visibility_settings", default)

@router.put("/me/visibility")
async def update_visibility(body: VisibilityBody, user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    allowed = {"public", "connections", "private"}
    settings = body.dict()
    for k, v in settings.items():
        if v not in allowed:
            raise HTTPException(status_code=400, detail=f"Invalid visibility value '{v}' for '{k}'")
    now = datetime.now(timezone.utc).isoformat()
    await db.public_profiles.update_one(
        {"user_id": user["id"]},
        {"$set": {"visibility_settings": settings, "updated_at": now}},
        upsert=True,
    )
    return settings

@router.get("/me/followers")
async def get_my_followers(user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    try:
        from services.public_profiles.follow_service import get_followers
    except ImportError:
        raise HTTPException(status_code=503, detail="Profile services unavailable")
    return await get_followers(user["id"], db)

@router.get("/me/following")
async def get_my_following(user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    try:
        from services.public_profiles.follow_service import get_following
    except ImportError:
        raise HTTPException(status_code=503, detail="Profile services unavailable")
    return await get_following(user["id"], db)

# ══════════════════════════════════════════════════════════════════════════════
# FOLLOW ENDPOINTS
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/follow/{target_user_id}")
async def follow_researcher(target_user_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    try:
        from services.public_profiles.follow_service import follow_researcher as _follow
    except ImportError:
        raise HTTPException(status_code=503, detail="Profile services unavailable")
    try:
        return await _follow(user["id"], target_user_id, db)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/follow/{target_user_id}")
async def unfollow(target_user_id: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    try:
        from services.public_profiles.follow_service import unfollow_researcher
    except ImportError:
        raise HTTPException(status_code=503, detail="Profile services unavailable")
    await unfollow_researcher(user["id"], target_user_id, db)
    return {"following": False}

# ══════════════════════════════════════════════════════════════════════════════
# DIRECTORY (public, no auth)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/directory")
async def researcher_directory(
    search: Optional[str] = Query(None),
    research_area: Optional[str] = Query(None),
    institution: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    career_stage: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    db=Depends(get_db),
):
    db = make_db_proxy(db, system=True)
    query: dict = {}
    if search:
        query["full_name"] = {"$regex": search, "$options": "i"}
    if research_area:
        query["research_interests"] = {"$elemMatch": {"$regex": research_area, "$options": "i"}}
    if institution:
        query["institution"] = {"$regex": institution, "$options": "i"}
    if country:
        query["country"] = country
    if career_stage:
        query["career_stage"] = career_stage

    total = await db.users.count_documents(query)
    skip = (page - 1) * limit
    projection = {"full_name": 1, "avatar_url": 1, "institution": 1, "country": 1, "career_stage": 1, "research_interests": 1, "department": 1}
    items = []
    async for u in db.users.find(query, projection).skip(skip).limit(limit):
        uid = str(u["_id"])
        slug_doc = await db.public_profiles.find_one({"user_id": uid}, {"slug": 1})
        items.append({
            "user_id": uid,
            "full_name": u.get("full_name",""),
            "avatar_url": u.get("avatar_url"),
            "institution": u.get("institution",""),
            "country": u.get("country",""),
            "career_stage": u.get("career_stage",""),
            "research_interests": u.get("research_interests") or [],
            "department": u.get("department",""),
            "slug": (slug_doc or {}).get("slug"),
        })
    return {"items": items, "total": total, "page": page, "pages": max(1, -(-total // limit))}

# ══════════════════════════════════════════════════════════════════════════════
# ADMIN STATS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/admin/stats")
async def admin_stats(user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    zt_check(user, "admin", "admin")
    total_profiles = await db.public_profiles.count_documents({})
    total_followers = await db.profile_followers.count_documents({})
    total_showcase = await db.profile_showcases.count_documents({})
    view_pipeline = [{"$group": {"_id": None, "total": {"$sum": "$view_count"}}}]
    view_result = [r async for r in db.public_profiles.aggregate(view_pipeline)]
    total_views = view_result[0]["total"] if view_result else 0
    top_viewed = []
    async for p in db.public_profiles.find({}, {"user_id": 1, "slug": 1, "view_count": 1}).sort("view_count", -1).limit(10):
        u = await db.users.find_one({"_id": ObjectId(p["user_id"])}, {"full_name": 1}) if p.get("user_id") else None
        top_viewed.append({"user_id": p.get("user_id"), "slug": p.get("slug"), "full_name": (u or {}).get("full_name",""), "view_count": p.get("view_count",0)})
    return {"total_profiles": total_profiles, "total_views": total_views, "total_followers": total_followers, "total_showcase_items": total_showcase, "top_viewed_profiles": top_viewed}

# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC RESEARCHER PROFILE ENDPOINTS (by slug) — MUST BE LAST
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/researcher/{slug}")
async def get_public_profile(
    slug: str,
    request: Request,
    db=Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_bearer),
):
    db = make_db_proxy(db, system=True)
    try:
        from services.public_profiles.slug_service import get_user_id_by_slug
        from services.public_profiles.profile_service import get_full_profile
        from services.public_profiles.analytics_service import record_view
    except ImportError:
        raise HTTPException(status_code=503, detail="Profile services unavailable")
    user_id = await get_user_id_by_slug(slug, db)
    if not user_id:
        raise HTTPException(status_code=404, detail="Researcher profile not found")
    viewer_id = await _get_optional_viewer(credentials)
    profile = await get_full_profile(user_id, db, viewer_id=viewer_id)
    # Apply visibility for non-owners
    if viewer_id != user_id:
        vs = profile.get("visibility_settings") or {}
        for section in ["impact", "projects", "grants", "collaborations", "teaching", "reputation", "timeline"]:
            if vs.get(section, "public") != "public":
                profile[section] = None
        if vs.get("contact", "public") != "public":
            profile["email"] = None
    # Fire-and-forget view tracking
    client_ip = request.client.host if request.client else ""
    referrer = request.headers.get("referer", "")
    asyncio.create_task(record_view(user_id, client_ip, referrer, db))
    return profile

@router.get("/researcher/{slug}/publications")
async def get_profile_publications(slug: str, db=Depends(get_db)):
    db = make_db_proxy(db, system=True)
    user_id = await _check_visibility(slug, "publications", db)
    try:
        from services.public_profiles.profile_service import get_publications_for_profile
    except ImportError:
        raise HTTPException(status_code=503, detail="Profile services unavailable")
    return await get_publications_for_profile(user_id, db)

@router.get("/researcher/{slug}/impact")
async def get_profile_impact(slug: str, db=Depends(get_db)):
    db = make_db_proxy(db, system=True)
    user_id = await _check_visibility(slug, "impact", db)
    try:
        from services.public_profiles.profile_service import get_impact_for_profile
    except ImportError:
        raise HTTPException(status_code=503, detail="Profile services unavailable")
    return await get_impact_for_profile(user_id, db)

@router.get("/researcher/{slug}/projects")
async def get_profile_projects(slug: str, db=Depends(get_db)):
    db = make_db_proxy(db, system=True)
    user_id = await _check_visibility(slug, "projects", db)
    try:
        from services.public_profiles.profile_service import get_projects_for_profile
    except ImportError:
        raise HTTPException(status_code=503, detail="Profile services unavailable")
    return await get_projects_for_profile(user_id, db)

@router.get("/researcher/{slug}/grants")
async def get_profile_grants(slug: str, db=Depends(get_db)):
    db = make_db_proxy(db, system=True)
    user_id = await _check_visibility(slug, "grants", db)
    try:
        from services.public_profiles.profile_service import get_grants_for_profile
    except ImportError:
        raise HTTPException(status_code=503, detail="Profile services unavailable")
    return await get_grants_for_profile(user_id, db)

@router.get("/researcher/{slug}/collaborations")
async def get_profile_collaborations(slug: str, db=Depends(get_db)):
    db = make_db_proxy(db, system=True)
    user_id = await _check_visibility(slug, "collaborations", db)
    try:
        from services.public_profiles.profile_service import get_collaborations_for_profile
    except ImportError:
        raise HTTPException(status_code=503, detail="Profile services unavailable")
    return await get_collaborations_for_profile(user_id, db)

@router.get("/researcher/{slug}/teaching")
async def get_profile_teaching(slug: str, db=Depends(get_db)):
    db = make_db_proxy(db, system=True)
    user_id = await _check_visibility(slug, "teaching", db)
    try:
        from services.public_profiles.profile_service import get_teaching_for_profile
    except ImportError:
        raise HTTPException(status_code=503, detail="Profile services unavailable")
    return await get_teaching_for_profile(user_id, db)

@router.get("/researcher/{slug}/reputation")
async def get_profile_reputation(slug: str, db=Depends(get_db)):
    db = make_db_proxy(db, system=True)
    user_id = await _check_visibility(slug, "reputation", db)
    try:
        from services.public_profiles.profile_service import get_reputation_for_profile
    except ImportError:
        raise HTTPException(status_code=503, detail="Profile services unavailable")
    return await get_reputation_for_profile(user_id, db)

@router.get("/researcher/{slug}/timeline")
async def get_profile_timeline(slug: str, db=Depends(get_db)):
    db = make_db_proxy(db, system=True)
    user_id = await _check_visibility(slug, "timeline", db)
    try:
        from services.public_profiles.profile_service import get_timeline_for_profile
    except ImportError:
        raise HTTPException(status_code=503, detail="Profile services unavailable")
    return await get_timeline_for_profile(user_id, db)

@router.get("/researcher/{slug}/follow-status")
async def get_follow_status(slug: str, user: dict = Depends(get_current_user), db=Depends(get_db)):
    db = make_db_proxy(db, user)
    try:
        from services.public_profiles.slug_service import get_user_id_by_slug
        from services.public_profiles.follow_service import is_following
    except ImportError:
        raise HTTPException(status_code=503, detail="Profile services unavailable")
    target_user_id = await get_user_id_by_slug(slug, db)
    if not target_user_id:
        raise HTTPException(status_code=404, detail="Profile not found")
    return {"following": await is_following(user["id"], target_user_id, db)}
