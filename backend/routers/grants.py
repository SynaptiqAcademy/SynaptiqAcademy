"""Grants — Discovery + Matching.

Discovery:
  GET  /api/grants             — list / overview / search with full filtering
  GET  /api/grants/facets      — aggregated facets (areas, country, type, sponsor)
  GET  /api/grants/matches     — personalised matching (profile-based, no AI credits)
  GET  /api/grants/{id}        — grant detail + user application status
  POST /api/grants/{id}/save   — bookmark
  POST /api/grants/{id}/unsave — remove bookmark
  GET  /api/grants/{id}/applications — applications for this grant (PI-visible)

Matching logic:
  - Scores every open grant against user profile (research_areas, keywords,
    career_stage, country, institution, ORCID fundings).
  - No Claude call — deterministic scoring for instant results.
  - AI-powered matching (with Claude) is in services/ai/matching.py
    and exposed through the existing /api/ai/match/grants endpoint.
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from auth_utils import get_current_user
from db import get_db
from services.permissions import check_discovery_quota
from repo.shim import DBProxy
from repo.security_context import SecurityContext
from zt.deps import zt_check, zt_is_admin, zt_is_super_admin

router = APIRouter(prefix="/api/grants", tags=["grants"])


def _ser(d):
    if not d:
        return None
    x = dict(d)
    x["id"] = str(x.pop("_id"))
    return x


def _open(d: dict) -> bool:
    today = date.today().isoformat()
    dl = d.get("deadline")
    return (not dl) or dl > today


# Career stage → eligible grant types / keywords mapping
_CAREER_KEYWORDS = {
    "early_career": {"starting grant", "fellowship", "early career", "junior", "phd", "postdoc",
                     "marie curie", "msca", "young researcher"},
    "mid_career":   {"consolidator", "career development", "mid-career", "associate", "investigator"},
    "senior":       {"advanced grant", "synergy", "collaborative", "frontier", "excellence", "principal"},
    "industry":     {"innovation", "sme", "industry", "enterprise", "technology transfer", "startup"},
}

FUNDING_SOURCES = {
    "Horizon Europe", "ERC", "Marie Curie / MSCA", "Erasmus+",
    "NIH", "NSF", "Wellcome Trust", "UKRI", "DFG",
    "ANR", "FWF", "NWO", "Swiss National Science Foundation",
    "European Social Fund", "InvestEU", "EIT", "Private Foundation",
    "Institutional Call", "Regional Fund", "Custom",
}


@router.get("")
async def list_grants(
    q: Optional[str] = None,
    research_area: Optional[str] = None,
    country: Optional[str] = None,
    funding_type: Optional[str] = None,
    sponsor: Optional[str] = None,
    career_stage: Optional[str] = None,
    discipline: Optional[str] = None,
    open_only: bool = False,
    min_amount: Optional[float] = Query(None, ge=0),
    max_amount: Optional[float] = Query(None, ge=0),
    deadline_before: Optional[str] = None,
    deadline_after: Optional[str] = None,
    sort: str = Query("deadline_asc", pattern="^(deadline_asc|deadline_desc|amount|recent|relevance)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(24, ge=1, le=100),
    overview: bool = False,
    user: dict = Depends(get_current_user),
):
    await check_discovery_quota(user, "grant")
    db = get_db()

    db = DBProxy(db, SecurityContext.from_user(user))

    # Legacy overview mode (used by old Discover page + dashboard widget)
    if overview:
        user_areas = user.get("research_areas") or []
        saved_ids = user.get("saved_funding_ids") or []
        all_grants = await db.grants.find({}).sort("deadline", 1).limit(100).to_list(100)
        saved_oids = set()
        for sid in saved_ids:
            try:
                saved_oids.add(ObjectId(sid))
            except Exception:
                pass
        saved = [g for g in all_grants if g["_id"] in saved_oids]
        recommended = [g for g in all_grants
                       if set(g.get("research_areas") or []) & set(user_areas)
                       and g["_id"] not in saved_oids]
        return {
            "discover":    [_ser(g) for g in all_grants],
            "saved":       [_ser(g) for g in saved],
            "recommended": [_ser(g) for g in recommended[:8]],
            "tracking":    [_ser(g) for g in saved],
        }

    query: dict = {}
    if q:
        query["$text"] = {"$search": q}
    if research_area or discipline:
        query["research_areas"] = research_area or discipline
    if country:
        query["$or"] = [{"country": country.upper()}, {"country": {"$exists": False}}, {"country": None}]
    if funding_type:
        query["funding_type"] = funding_type
    if sponsor:
        query["sponsor"] = {"$regex": sponsor, "$options": "i"}
    if open_only:
        query["deadline"] = {"$gt": date.today().isoformat()}
    if min_amount is not None:
        query.setdefault("funding_amount.amount", {})["$gte"] = min_amount
    if max_amount is not None:
        query.setdefault("funding_amount.amount", {})["$lte"] = max_amount
    if deadline_before:
        query.setdefault("deadline", {})["$lte"] = deadline_before
    if deadline_after:
        query.setdefault("deadline", {})["$gte"] = deadline_after

    # Career stage filter — keyword-based
    if career_stage and career_stage in _CAREER_KEYWORDS:
        kws = list(_CAREER_KEYWORDS[career_stage])
        query["$or"] = [{"title": {"$regex": kw, "$options": "i"}} for kw in kws]

    if sort == "relevance" and q:
        cursor = db.grants.find(query, {"score": {"$meta": "textScore"}}).sort([("score", {"$meta": "textScore"})])
    elif sort == "deadline_desc":
        cursor = db.grants.find(query).sort([("deadline", -1)])
    elif sort == "amount":
        cursor = db.grants.find(query).sort([("funding_amount.amount", -1)])
    elif sort == "recent":
        cursor = db.grants.find(query).sort([("updated_at", -1)])
    else:
        cursor = db.grants.find(query).sort([("deadline", 1)])

    total = await db.grants.count_documents(query)
    skip = (page - 1) * page_size
    docs = await cursor.skip(skip).limit(page_size).to_list(page_size)

    # Annotate with saved status
    saved_ids = set(user.get("saved_funding_ids") or [])
    out = []
    for d in docs:
        item = _ser(d)
        item["is_saved"] = item["id"] in saved_ids
        out.append(item)

    return {
        "items":     out,
        "total":     total,
        "page":      page,
        "page_size": page_size,
        "has_more":  skip + len(docs) < total,
    }


@router.get("/facets")
async def grant_facets(
    q: Optional[str] = None,
    _user: dict = Depends(get_current_user),
):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    match: dict = {}
    if q:
        match["$text"] = {"$search": q}
    pipeline = [
        {"$match": match},
        {"$facet": {
            "research_areas": [
                {"$unwind": "$research_areas"},
                {"$group": {"_id": "$research_areas", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}, {"$limit": 30},
            ],
            "countries": [
                {"$group": {"_id": "$country", "count": {"$sum": 1}}},
                {"$match": {"_id": {"$ne": None}}}, {"$sort": {"count": -1}}, {"$limit": 30},
            ],
            "funding_types": [
                {"$group": {"_id": "$funding_type", "count": {"$sum": 1}}},
                {"$match": {"_id": {"$ne": None}}}, {"$sort": {"count": -1}},
            ],
            "sponsors": [
                {"$group": {"_id": "$sponsor", "count": {"$sum": 1}}},
                {"$match": {"_id": {"$ne": None}}}, {"$sort": {"count": -1}}, {"$limit": 30},
            ],
            "career_stages": [
                {"$group": {"_id": "$career_stage", "count": {"$sum": 1}}},
                {"$match": {"_id": {"$ne": None}}}, {"$sort": {"count": -1}},
            ],
        }},
    ]
    out = await db.grants.aggregate(pipeline).to_list(1)
    return out[0] if out else {}


@router.get("/matches")
async def grant_matches(
    limit: int = Query(default=15, ge=1, le=30),
    user: dict = Depends(get_current_user),
):
    """
    Profile-based grant matching. Scores open grants deterministically
    against the user's research areas, keywords, career stage, country,
    institution and ORCID funding history. Returns ranked matches with
    match_score and eligibility_note. No credits consumed.
    """
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    today = date.today().isoformat()

    # Pull open grants
    all_grants = await db.grants.find({
        "$or": [{"deadline": None}, {"deadline": {"$gt": today}}],
    }).sort("deadline", 1).limit(500).to_list(500)

    user_areas = {a.lower() for a in (user.get("research_areas") or [])}
    user_kw    = {k.lower() for k in (user.get("research_keywords") or [])}
    user_interests = {k.lower() for k in (user.get("research_interests") or [])}
    user_country = (user.get("country") or "").upper()
    career_stage = (user.get("career_stage") or "").lower().replace(" ", "_")
    stage_kws  = _CAREER_KEYWORDS.get(career_stage, set())

    # Build set of already-funded agency names from ORCID
    orcid_funders = {
        (f.get("organization") or {}).get("name", "").lower()
        for f in (user.get("orcid_fundings") or [])
    }
    # Build set of saved ids
    saved_ids = set(user.get("saved_funding_ids") or [])

    def _score(g: dict) -> tuple[int, str]:
        score = 0
        notes = []

        g_areas = {a.lower() for a in (g.get("research_areas") or [])}
        g_title = g.get("title", "").lower()
        g_text  = (g.get("abstract_text") or g.get("summary") or "").lower()
        g_sponsor = (g.get("sponsor") or "").lower()
        g_country = (g.get("country") or "").upper()

        # Research area overlap
        area_overlap = user_areas & g_areas
        score += len(area_overlap) * 15
        if area_overlap:
            notes.append(f"Matches {', '.join(list(area_overlap)[:2])}")

        # Keyword overlap in title/text
        for kw in user_kw | user_interests:
            if kw in g_title:
                score += 6
            elif kw in g_text:
                score += 3

        # Career stage
        for skw in stage_kws:
            if skw in g_title or skw in g_text:
                score += 8
                notes.append("Matches career stage")
                break

        # Country match
        if g_country and g_country == user_country:
            score += 10
            notes.append("National funder")
        elif not g_country:
            score += 3  # international

        # Prior relationship with funder
        if g_sponsor in orcid_funders:
            score += 20
            notes.append("Previous funding from this agency")

        # Saved bonus
        if str(g["_id"]) in saved_ids:
            score += 5

        # Deadline urgency (within 3 months = bonus)
        dl = g.get("deadline")
        if dl:
            try:
                days = (datetime.strptime(dl, "%Y-%m-%d").date() - date.today()).days
                if 0 < days <= 90:
                    score += 5
                    notes.append(f"{days}d to deadline")
            except Exception:
                pass

        return score, "; ".join(notes) if notes else "Matched by research profile"

    scored = sorted(all_grants, key=lambda g: _score(g)[0], reverse=True)[:limit]
    out = []
    for g in scored:
        s, note = _score(g)
        item = _ser(g)
        item["match_score"] = s
        item["match_reason"] = note
        item["is_saved"] = item["id"] in saved_ids
        # Eligibility estimate
        career_match = any(ck in (g.get("title", "") + " " + (g.get("abstract_text") or "")).lower()
                           for ck in stage_kws) if stage_kws else True
        item["eligibility_estimate"] = "high" if career_match else "medium"
        out.append(item)
    return out


@router.get("/{grant_id}")
async def get_grant(grant_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(grant_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Not found")
    doc = await db.grants.find_one({"_id": oid})
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    item = _ser(doc)
    saved_ids = set(user.get("saved_funding_ids") or [])
    item["is_saved"] = item["id"] in saved_ids

    # Check if user already has an application
    existing = await db.grant_applications.find_one(
        {"grant_id": grant_id, "pi_id": user["id"],
         "status": {"$nin": ["withdrawn", "closed"]}},
        {"_id": 1, "status": 1},
    )
    if existing:
        item["user_application"] = {"id": str(existing["_id"]), "status": existing.get("status")}
    return item


@router.post("/{grant_id}/save")
async def save_grant(grant_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        ObjectId(grant_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Not found")
    await db.users.update_one({"_id": ObjectId(user["id"])}, {"$addToSet": {"saved_funding_ids": grant_id}})
    return {"ok": True}


@router.post("/{grant_id}/unsave")
async def unsave_grant(grant_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    await db.users.update_one({"_id": ObjectId(user["id"])}, {"$pull": {"saved_funding_ids": grant_id}})
    return {"ok": True}


@router.get("/{grant_id}/applications")
async def grant_applications_list(
    grant_id: str,
    user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
):
    """List applications for a grant. Visible to: admins and the user's own application."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    is_admin = zt_is_admin(user)
    if is_admin:
        q: dict = {"grant_id": grant_id}
    else:
        q = {"grant_id": grant_id, "pi_id": user["id"]}

    total = await db.grant_applications.count_documents(q)
    skip = (page - 1) * page_size
    apps = await db.grant_applications.find(q).sort("created_at", -1).skip(skip).limit(page_size).to_list(page_size)
    return {
        "items": [_ser(a) for a in apps],
        "total": total,
        "page":  page,
    }
