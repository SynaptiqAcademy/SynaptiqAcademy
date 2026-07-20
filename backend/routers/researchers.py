"""Researcher discovery endpoints: saved researchers, recent views, match scoring."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query

from auth_utils import get_current_user, serialize_public_user
from db import get_db
from repo.shim import DBProxy
from repo.security_context import SecurityContext

log = logging.getLogger("synaptiq.researchers")
router = APIRouter(prefix="/api/researchers", tags=["researchers"])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─────────────────────── saved researchers ───────────────────────────────────

@router.post("/saved/{target_user_id}", status_code=201)
async def save_researcher(target_user_id: str, user: dict = Depends(get_current_user)):
    """Save (bookmark) a researcher profile."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    if target_user_id == user["id"]:
        raise HTTPException(400, "Cannot save yourself")
    try:
        target_oid = ObjectId(target_user_id)
    except Exception:
        raise HTTPException(404, "User not found")
    target = await db.users.find_one({"_id": target_oid}, {"_id": 1, "full_name": 1})
    if not target:
        raise HTTPException(404, "User not found")

    existing = await db.saved_researchers.find_one({
        "user_id": user["id"], "saved_user_id": target_user_id,
    })
    if existing:
        return {"id": str(existing["_id"]), "already_saved": True}

    result = await db.saved_researchers.insert_one({
        "user_id":       user["id"],
        "saved_user_id": target_user_id,
        "created_at":    _now(),
    })
    return {"id": str(result.inserted_id), "saved": True}


@router.delete("/saved/{target_user_id}", status_code=204)
async def unsave_researcher(target_user_id: str, user: dict = Depends(get_current_user)):
    """Remove a saved researcher."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    await db.saved_researchers.delete_one({
        "user_id": user["id"], "saved_user_id": target_user_id,
    })


@router.get("/saved")
async def list_saved_researchers(
    limit: int = Query(default=50, ge=1, le=100),
    cursor: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """List all researchers the current user has saved, with full profiles."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    q: dict = {"user_id": user["id"]}
    if cursor:
        try:
            q["_id"] = {"$lt": ObjectId(cursor)}
        except Exception:
            pass

    saves = await db.saved_researchers.find(q).sort("_id", -1).limit(limit).to_list(limit)
    if not saves:
        return {"items": [], "next_cursor": None}

    saved_ids = [ObjectId(s["saved_user_id"]) for s in saves]
    users_raw = await db.users.find({"_id": {"$in": saved_ids}}).to_list(len(saved_ids))
    users_map = {str(u["_id"]): u for u in users_raw}

    items = []
    for s in saves:
        u = users_map.get(s["saved_user_id"])
        if u:
            pub = serialize_public_user(u)
            pub["saved_at"] = s.get("created_at")
            items.append(pub)

    next_cursor = str(saves[-1]["_id"]) if len(saves) == limit else None
    return {"items": items, "next_cursor": next_cursor}


@router.get("/saved/ids")
async def saved_researcher_ids(user: dict = Depends(get_current_user)):
    """Return just the set of saved user IDs for the current user (fast badge check)."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    saves = await db.saved_researchers.find(
        {"user_id": user["id"]}, {"saved_user_id": 1},
    ).to_list(1000)
    return {"ids": [s["saved_user_id"] for s in saves]}


# ─────────────────────── recently viewed ─────────────────────────────────────

@router.get("/recently-viewed")
async def recently_viewed(limit: int = Query(default=10, ge=1, le=50),
                          user: dict = Depends(get_current_user)):
    """Profiles this user has recently viewed."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    views = await db.profile_views.find(
        {"viewer_id": user["id"]},
    ).sort("created_at", -1).limit(limit * 3).to_list(limit * 3)

    seen: set[str] = set()
    deduped = []
    for v in views:
        vid = v.get("viewed_id")
        if vid and vid not in seen and vid != user["id"]:
            seen.add(vid)
            deduped.append(vid)
            if len(deduped) >= limit:
                break

    if not deduped:
        return []

    users_raw = await db.users.find({"_id": {"$in": [ObjectId(i) for i in deduped]}}).to_list(len(deduped))
    users_map = {str(u["_id"]): u for u in users_raw}
    return [serialize_public_user(users_map[uid]) for uid in deduped if uid in users_map]


# ─────────────────────── match score (on-demand) ─────────────────────────────

@router.get("/match-score/{target_user_id}")
async def get_match_score(target_user_id: str, user: dict = Depends(get_current_user)):
    """Return a fast local pre-score (0-100) between current user and target."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    if target_user_id == user["id"]:
        return {"score": 100, "reason": "This is you."}
    try:
        oid = ObjectId(target_user_id)
    except Exception:
        raise HTTPException(404, "User not found")
    target = await db.users.find_one({"_id": oid})
    if not target:
        raise HTTPException(404, "User not found")

    def _safe_set(v) -> set:
        return {str(x).lower().strip() for x in (v or []) if x}

    u_areas  = _safe_set(user.get("research_areas"))
    c_areas  = _safe_set(target.get("research_areas"))
    u_kw     = _safe_set(user.get("research_keywords"))
    c_kw     = _safe_set(target.get("research_keywords"))
    u_skills = _safe_set(user.get("skills") or [] + user.get("software_skills") or [] + user.get("methods") or [])
    c_skills = _safe_set(target.get("skills") or [] + target.get("software_skills") or [] + target.get("methods") or [])

    def _jaccard(a, b):
        if not a or not b: return 0.0
        return len(a & b) / len(a | b)

    area_j  = _jaccard(u_areas, c_areas)
    kw_j    = _jaccard(u_kw, c_kw)
    skill_j = _jaccard(u_skills, c_skills)
    # Institution proximity bonus
    inst_bonus = 5 if (user.get("institution") and user.get("institution") == target.get("institution")) else 0
    # Country bonus
    ctry_bonus = 3 if (user.get("country") and user.get("country") == target.get("country")) else 0

    raw = int(area_j * 40 + kw_j * 25 + skill_j * 20) + inst_bonus + ctry_bonus
    score = min(98, max(0, raw))

    overlaps = list(u_areas & c_areas)[:4]
    if overlaps:
        reason = f"{score}% match — shared areas: {', '.join(overlaps)}"
    elif list(u_kw & c_kw):
        reason = f"{score}% match — shared keywords: {', '.join(list(u_kw & c_kw)[:3])}"
    else:
        reason = f"{score}% compatibility based on profile analysis"

    return {"score": score, "reason": reason, "overlaps": {"areas": overlaps}}


# ─────────────────────── discover sections ────────────────────────────────────

@router.get("/discover/sections")
async def discover_sections(user: dict = Depends(get_current_user)):
    """Return structured discovery sections: recommendations, trending, recent, experts, etc."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    user_areas = {a.lower() for a in (user.get("research_areas") or [])}
    user_kw    = {k.lower() for k in (user.get("research_keywords") or [])}
    user_methods = {m.lower() for m in (user.get("methods") or [])}
    user_inst  = (user.get("institution") or "").lower()
    user_country = (user.get("country") or "").lower()

    # Already saved/viewed IDs — exclude from some sections
    saved_raw = await db.saved_researchers.find({"user_id": uid}, {"saved_user_id": 1}).to_list(500)
    saved_ids = {s["saved_user_id"] for s in saved_raw}

    base_filter = {
        "_id": {"$ne": ObjectId(uid)},
        "is_demo": {"$ne": True},
        "profile_visibility": {"$ne": "private"},
    }

    def _score(r):
        r_areas   = {a.lower() for a in (r.get("research_areas") or [])}
        r_kw      = {k.lower() for k in (r.get("research_keywords") or [])}
        r_methods = {m.lower() for m in (r.get("methods") or [])}
        area_overlap = len(user_areas & r_areas)
        kw_overlap   = len(user_kw & r_kw)
        meth_overlap = len(user_methods & r_methods)
        h = int((r.get("openalex_metrics") or {}).get("h_index") or r.get("h_index") or 0)
        pubs = int(r.get("publications_count") or 0)
        inst_bonus = 3 if user_inst and (r.get("institution") or "").lower() == user_inst else 0
        ctry_bonus = 2 if user_country and (r.get("country") or "").lower() == user_country else 0
        return area_overlap * 5 + kw_overlap * 3 + meth_overlap * 4 + (1 if h > 0 else 0) + (1 if pubs > 0 else 0) + inst_bonus + ctry_bonus

    # ── Section 1: Recommended (area + keyword overlap) ──────────────────────
    rec_filter = {**base_filter}
    if user_areas:
        rec_filter["research_areas"] = {"$in": [a for a in user.get("research_areas", [])]}
    rec_raw = await db.users.find(rec_filter).limit(30).to_list(30)
    rec_raw.sort(key=_score, reverse=True)
    recommended = rec_raw[:8]

    # Fallback if no area matches
    if len(recommended) < 4:
        fallback = await db.users.find(base_filter).sort("_id", -1).limit(12).to_list(12)
        seen = {str(r["_id"]) for r in recommended}
        for r in fallback:
            if str(r["_id"]) not in seen and len(recommended) < 8:
                recommended.append(r)

    # ── Section 2: Methodology experts (share methods) ───────────────────────
    experts_filter = {**base_filter}
    if user_methods:
        experts_filter["methods"] = {"$in": list(user.get("methods", []))}
    experts_raw = await db.users.find(experts_filter).limit(20).to_list(20)
    experts_raw.sort(key=_score, reverse=True)
    methodology_experts = experts_raw[:6]

    # ── Section 3: Institutional matches ─────────────────────────────────────
    institutional = []
    if user_inst:
        inst_filter = {**base_filter, "institution": {"$regex": user.get("institution",""), "$options": "i"}}
        institutional = await db.users.find(inst_filter).limit(6).to_list(6)

    # ── Section 4: International matches (different country, strong area overlap) ──
    intl_filter = {**base_filter}
    if user_country:
        intl_filter["country"] = {"$ne": user.get("country")}
    if user_areas:
        intl_filter["research_areas"] = {"$in": list(user.get("research_areas", []))}
    intl_raw = await db.users.find(intl_filter).limit(20).to_list(20)
    intl_raw.sort(key=_score, reverse=True)
    international = intl_raw[:6]

    # ── Section 5: Recently active ───────────────────────────────────────────
    recent_raw = await db.users.find(base_filter).sort("last_updated", -1).limit(8).to_list(8)

    # ── Section 6: Top by h-index ─────────────────────────────────────────────
    top_scholars = await db.users.find(
        {**base_filter, "h_index": {"$gt": 0}},
        sort=[("h_index", -1)],
    ).limit(8).to_list(8)

    # ── Section 7: Available for collaboration ────────────────────────────────
    avail_raw = await db.users.find(
        {**base_filter, "available_for_collaboration": True},
    ).limit(20).to_list(20)
    avail_raw.sort(key=_score, reverse=True)
    available_collaborators = avail_raw[:8]

    # ── Section 8: Available for reviewing ────────────────────────────────────
    reviewers_raw = await db.users.find(
        {**base_filter, "available_for_reviewing": True},
    ).limit(12).to_list(12)
    reviewers_raw.sort(key=_score, reverse=True)
    reviewers = reviewers_raw[:6]

    def _ser(researchers_list):
        result = []
        for r in researchers_list:
            pub = serialize_public_user(r)
            pub["match_score"] = _score(r)
            pub["is_saved"] = str(r["_id"]) in saved_ids
            result.append(pub)
        return result

    return {
        "recommended":            _ser(recommended),
        "methodology_experts":    _ser(methodology_experts),
        "institutional_matches":  _ser(institutional),
        "international_matches":  _ser(international),
        "recently_active":        _ser(recent_raw),
        "top_scholars":           _ser(top_scholars),
        "available_collaborators": _ser(available_collaborators),
        "available_reviewers":    _ser(reviewers),
    }
