"""Grant Collaboration Hub — Partner Matching Engine.

Pure algorithmic partner compatibility scoring (no LLM calls).

Collections:
  grant_partner_matches  — cached match results (1hr TTL)
  grant_collaborations   — for research_areas
  grant_team_members     — to exclude existing members
  grant_positions        — for expertise requirements
  grant_consortia        — for institution coverage scoring
  users                  — candidate pool
  publications           — for publication scoring
  research_reputation    — for reputation scoring
"""
from __future__ import annotations

import ast
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional

from bson import ObjectId


def _ser(d: dict) -> dict:
    if not d:
        return {}
    out = dict(d)
    if "_id" in out:
        out["id"] = str(out.pop("_id"))
    for k, v in out.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
    return out


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_list(value) -> list:
    """Parse a field that might be a list or a string-encoded list."""
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = ast.literal_eval(value)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            pass
        # Single string item
        if value.strip():
            return [value.strip()]
    return []


def _jaccard(set_a: set, set_b: set) -> float:
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def _compute_score(user: dict, collab_research_areas: list, partner_inst_ids: set, open_positions: list) -> dict:
    """Compute a 5-component compatibility score for a candidate user."""
    # 1. Research area score (0-35)
    user_interests = _safe_list(
        user.get("research_interests") or user.get("research_areas") or []
    )
    collab_set = {a.lower().strip() for a in collab_research_areas if a}
    user_set = {a.lower().strip() for a in user_interests if a}
    research_area_score = round(_jaccard(collab_set, user_set) * 35, 2)

    # 2. Publication score (0-25) — computed externally; default from stored count
    pub_count = int(user.get("_pub_count", 0))
    publication_score = min(25.0, pub_count * 2.0)

    # 3. Reputation score (0-20)
    rep_overall = float(user.get("_rep_score", 0))
    reputation_score = min(20.0, rep_overall / 5.0)

    # 4. Institution coverage score (0-10)
    user_inst_id = str(user.get("institution_id", ""))
    if user_inst_id and user_inst_id not in partner_inst_ids:
        institution_coverage_score = 10.0
    else:
        institution_coverage_score = 5.0

    # 5. Expertise match score (0-10)
    user_keywords = {
        kw.lower().strip()
        for kw in _safe_list(user.get("keywords") or user.get("expertise") or [])
        if kw
    }
    matched_positions = 0
    for pos in open_positions:
        req_expertise = {e.lower().strip() for e in _safe_list(pos.get("required_expertise", [])) if e}
        if req_expertise and user_keywords & req_expertise:
            matched_positions += 1
    if open_positions:
        expertise_match_score = min(10.0, (matched_positions / len(open_positions)) * 10.0)
    else:
        expertise_match_score = 0.0

    total = round(
        research_area_score + publication_score + reputation_score
        + institution_coverage_score + expertise_match_score,
        2,
    )

    return {
        "total_score": total,
        "components": {
            "research_area_score": research_area_score,
            "publication_score": publication_score,
            "reputation_score": reputation_score,
            "institution_coverage_score": institution_coverage_score,
            "expertise_match_score": expertise_match_score,
        },
    }


# ── cache helpers ─────────────────────────────────────────────────────────────

async def _get_cached_matches(collab_id: str, db) -> Optional[list]:
    """Return cached matches if still fresh (within 1 hour)."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
    cutoff_str = cutoff.isoformat()

    docs = await db["grant_partner_matches"].find(
        {"collaboration_id": collab_id, "computed_at": {"$gte": cutoff_str}}
    ).sort("total_score", -1).to_list(20)

    if docs:
        return [_ser(d) for d in docs]
    return None


# ── public API ────────────────────────────────────────────────────────────────

async def compute_partner_matches(collab_id: str, db, force_refresh: bool = False) -> list:
    """Compute partner compatibility scores. Uses cache unless force_refresh=True."""
    # Check cache
    if not force_refresh:
        cached = await _get_cached_matches(collab_id, db)
        if cached:
            return cached

    # Fetch collab, existing members, open positions, and consortium in parallel
    try:
        oid = ObjectId(collab_id)
    except Exception:
        return []

    collab, member_docs, open_position_docs, consortium = await asyncio.gather(
        db["grant_collaborations"].find_one({"_id": oid}),
        db["grant_team_members"].find({"collaboration_id": collab_id}, {"user_id": 1}).to_list(500),
        db["grant_positions"].find({"collaboration_id": collab_id, "status": "open"}).to_list(100),
        db["grant_consortia"].find_one({"collaboration_id": collab_id}),
    )

    if not collab:
        return []

    collab_research_areas = _safe_list(collab.get("research_areas", []))
    existing_user_ids = {m.get("user_id") for m in member_docs if m.get("user_id")}

    # Build set of institution IDs already in consortium
    partner_inst_ids: set = set()
    if consortium:
        lead_inst = consortium.get("lead_institution_id", "")
        if lead_inst:
            partner_inst_ids.add(lead_inst)
        for p in consortium.get("partner_institutions", []):
            inst_id = p.get("institution_id", "")
            if inst_id:
                partner_inst_ids.add(inst_id)

    # Fetch candidate users (limit 200, sorted by reputation)
    candidate_users = await db["users"].find(
        {},
        {
            "first_name": 1, "last_name": 1, "name": 1, "email": 1,
            "institution_id": 1, "institution": 1, "career_stage": 1,
            "research_interests": 1, "research_areas": 1, "keywords": 1, "expertise": 1,
        },
    ).limit(200).to_list(200)

    # Filter out existing members
    candidates = [
        u for u in candidate_users
        if str(u.get("_id", "")) not in existing_user_ids
    ]

    if not candidates:
        return []

    # Batch-fetch publication counts and reputation scores
    user_oids = [u["_id"] for u in candidates]
    user_id_strs = [str(u["_id"]) for u in candidates]

    pub_agg, rep_docs = await asyncio.gather(
        db["publications"].aggregate([
            {"$match": {"user_id": {"$in": user_id_strs}}},
            {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
        ]).to_list(200),
        db["research_reputation"].find(
            {"user_id": {"$in": user_id_strs}},
            {"user_id": 1, "overall_score": 1},
        ).to_list(200),
    )

    pub_counts = {p["_id"]: p["count"] for p in pub_agg}
    rep_scores = {r["user_id"]: float(r.get("overall_score", 0)) for r in rep_docs}

    # Augment candidates with fetched data
    for u in candidates:
        uid_str = str(u["_id"])
        u["_pub_count"] = pub_counts.get(uid_str, 0)
        u["_rep_score"] = rep_scores.get(uid_str, 0.0)

    # Score all candidates
    now = _now()
    results = []
    for u in candidates:
        score_data = _compute_score(u, collab_research_areas, partner_inst_ids, open_position_docs)
        if score_data["total_score"] < 30.0:
            continue

        uid_str = str(u["_id"])
        user_name = (
            u.get("name")
            or f"{u.get('first_name', '')} {u.get('last_name', '')}".strip()
        )

        match_doc = {
            "collaboration_id": collab_id,
            "user_id": uid_str,
            "user_name": user_name,
            "email": u.get("email", ""),
            "institution": u.get("institution", ""),
            "institution_id": str(u.get("institution_id", "")),
            "career_stage": u.get("career_stage", ""),
            "total_score": score_data["total_score"],
            "components": score_data["components"],
            "computed_at": now,
        }

        # Upsert into cache
        await db["grant_partner_matches"].update_one(
            {"collaboration_id": collab_id, "user_id": uid_str},
            {"$set": match_doc},
            upsert=True,
        )
        results.append(match_doc)

    # Sort descending and return top 20
    results.sort(key=lambda x: x["total_score"], reverse=True)
    return results[:20]


async def get_partner_matches(collab_id: str, db) -> list:
    """Return partner matches (from cache or compute if stale)."""
    cached = await _get_cached_matches(collab_id, db)
    if cached:
        return cached
    return await compute_partner_matches(collab_id, db)


async def compute_single_match(collab_id: str, user_id: str, db) -> dict:
    """Compute compatibility score for a single user against a collaboration."""
    try:
        collab_oid = ObjectId(collab_id)
    except Exception:
        return {}

    try:
        user_oid = ObjectId(user_id)
    except Exception:
        return {}

    collab, user, open_position_docs, consortium = await asyncio.gather(
        db["grant_collaborations"].find_one({"_id": collab_oid}),
        db["users"].find_one({"_id": user_oid}),
        db["grant_positions"].find({"collaboration_id": collab_id, "status": "open"}).to_list(100),
        db["grant_consortia"].find_one({"collaboration_id": collab_id}),
    )

    if not collab or not user:
        return {}

    collab_research_areas = _safe_list(collab.get("research_areas", []))

    partner_inst_ids: set = set()
    if consortium:
        lead_inst = consortium.get("lead_institution_id", "")
        if lead_inst:
            partner_inst_ids.add(lead_inst)
        for p in consortium.get("partner_institutions", []):
            inst_id = p.get("institution_id", "")
            if inst_id:
                partner_inst_ids.add(inst_id)

    # Fetch pub count and rep score
    pub_count_agg, rep_doc = await asyncio.gather(
        db["publications"].count_documents({"user_id": user_id}),
        db["research_reputation"].find_one({"user_id": user_id}, {"overall_score": 1}),
    )

    user["_pub_count"] = pub_count_agg
    user["_rep_score"] = float(rep_doc.get("overall_score", 0)) if rep_doc else 0.0

    score_data = _compute_score(user, collab_research_areas, partner_inst_ids, open_position_docs)

    return {
        "collaboration_id": collab_id,
        "user_id": user_id,
        "total_score": score_data["total_score"],
        "components": score_data["components"],
        "computed_at": _now(),
    }
