"""Synaptiq Impact Score (SIS) — 0-10 000 point composite.

Eight components, each with an explicit ceiling, are summed to produce the SIS.
Every component returns a score, max, and a details dict so the UI can render
a fully auditable breakdown.

No FastAPI dependencies — safe to call from HTTP endpoints, schedulers, and
background tasks.
"""
from __future__ import annotations

import math
import logging
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId

log = logging.getLogger("synaptiq.impact.sis")


# ─────────────────────────── helpers ─────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cap(value: float, ceiling: int) -> int:
    """Clamp a float to [0, ceiling] and return as int."""
    return min(ceiling, max(0, int(value)))


def _sis_label(total: int) -> str:
    if total >= 9000:
        return "Eminent Scholar"
    if total >= 7000:
        return "Distinguished Researcher"
    if total >= 5000:
        return "Senior Scholar"
    if total >= 3000:
        return "Established Researcher"
    if total >= 1500:
        return "Rising Scholar"
    if total >= 500:
        return "Emerging Scholar"
    return "New Researcher"


# ─────────────────────────── component builders ───────────────────────────────

async def _component_research_output(uid: str, db) -> dict:
    """Component 1: Research Output — max 2500 pts."""
    MAX = 2500
    CAP_PUBLISHED  = 1500
    CAP_SUBMITTED  = 500
    CAP_DRAFTED    = 500

    agg = await db.manuscripts.aggregate([
        {
            "$match": {
                "$or": [
                    {"lead_author_id": uid},
                    {"authors": uid},
                ]
            }
        },
        {
            "$group": {
                "_id": None,
                "published": {"$sum": {"$cond": [{"$eq": ["$status", "published"]}, 1, 0]}},
                "submitted": {"$sum": {"$cond": [{"$eq": ["$status", "submitted"]}, 1, 0]}},
                "draft":     {"$sum": {"$cond": [{"$eq": ["$status", "draft"]},     1, 0]}},
            }
        },
    ]).to_list(1)

    row = agg[0] if agg else {}
    n_published = int(row.get("published") or 0)
    n_submitted = int(row.get("submitted") or 0)
    n_drafted   = int(row.get("draft")     or 0)

    # Also count from publications collection (OpenAlex synced, already published)
    pub_count = await db.publications.count_documents({"owner_id": uid})
    # Merge: use the higher of manuscripts-published vs openalex-publications
    n_published = max(n_published, pub_count)

    pts_published = _cap(n_published * 200, CAP_PUBLISHED)
    pts_submitted = _cap(n_submitted * 100, CAP_SUBMITTED)
    pts_drafted   = _cap(n_drafted   *  25, CAP_DRAFTED)
    score         = pts_published + pts_submitted + pts_drafted

    return {
        "score": score,
        "max":   MAX,
        "details": {
            "manuscripts_published": n_published,
            "manuscripts_submitted": n_submitted,
            "manuscripts_drafted":   n_drafted,
            "pts_published": pts_published,
            "pts_submitted": pts_submitted,
            "pts_drafted":   pts_drafted,
        },
    }


async def _component_citation_impact(uid: str, db) -> dict:
    """Component 2: Citation Impact — max 2000 pts."""
    MAX = 2000

    # Check openalex_metrics on user doc
    u_doc = await db.users.find_one(
        {"_id": ObjectId(uid)},
        {"openalex_metrics": 1, "h_index": 1},
    )
    oam = (u_doc or {}).get("openalex_metrics") or {}
    oa_h_index      = int(oam.get("h_index")    or (u_doc or {}).get("h_index") or 0)
    oa_citations    = int(oam.get("citations")   or 0)

    # Also aggregate from publications collection
    pub_agg = await db.publications.aggregate([
        {"$match": {"owner_id": uid}},
        {"$group": {"_id": None, "total": {"$sum": {"$ifNull": ["$citations", 0]}}}},
    ]).to_list(1)
    pub_cits = int((pub_agg[0].get("total") or 0) if pub_agg else 0)

    total_citations = max(oa_citations, pub_cits)
    h_index         = oa_h_index

    if h_index > 0 or total_citations > 0:
        raw = h_index * 80 + math.log1p(total_citations) * 100
        score = _cap(raw, MAX)
        source = "openalex"
        details = {
            "h_index":        h_index,
            "total_citations": total_citations,
            "formula": "h_index * 80 + log(total_citations+1) * 100",
            "data_source": source,
        }
    else:
        # Fallback: publication_score from research_reputation (0-100 → 0-500)
        rep = await db.research_reputation.find_one(
            {"user_id": uid},
            {"publication_score": 1},
        )
        pub_score = int((rep or {}).get("publication_score") or 0)
        score = _cap(pub_score * 5, MAX)
        details = {
            "h_index":        0,
            "total_citations": 0,
            "formula": "publication_score_from_reputation * 5",
            "reputation_publication_score": pub_score,
            "data_source": "reputation_fallback",
        }

    return {"score": score, "max": MAX, "details": details}


async def _component_collaboration(uid: str, db) -> dict:
    """Component 3: Collaboration — max 1500 pts."""
    MAX = 1500
    CAP_ACTIVE   = 750
    CAP_PROJECTS = 500
    CAP_INTL     = 250

    # Active collaborations (from collaborations collection where user is member/creator)
    active_collabs = await db.collaborations.count_documents({
        "$or": [{"creator_id": uid}, {"members": uid}],
        "status": "active",
    })

    # Also count accepted collaboration_requests
    accepted_requests = await db.collaboration_requests.count_documents({
        "$or": [{"sender_id": uid}, {"receiver_id": uid}],
        "status": "accepted",
    })

    # Use the higher of the two counts as a proxy for active collaborations
    effective_active = max(active_collabs, accepted_requests)

    # Project memberships
    project_memberships = await db.projects.count_documents({
        "$or": [{"owner_id": uid}, {"members": uid}],
    })

    # International collaborations: collaborators from a different country
    # Pull user's country
    u_doc = await db.users.find_one(
        {"_id": ObjectId(uid)},
        {"country": 1},
    )
    user_country = (u_doc or {}).get("country") or ""

    international_count = 0
    if user_country:
        # Find partner IDs from accepted requests
        req_docs = await db.collaboration_requests.find(
            {
                "$or": [{"sender_id": uid}, {"receiver_id": uid}],
                "status": "accepted",
            },
            {"sender_id": 1, "receiver_id": 1},
        ).to_list(200)

        partner_ids: set[str] = set()
        for r in req_docs:
            pid = r["receiver_id"] if r.get("sender_id") == uid else r.get("sender_id")
            if pid and pid != uid:
                partner_ids.add(pid)

        if partner_ids:
            valid_ids = [ObjectId(p) for p in partner_ids if len(p) == 24]
            intl_count_agg = await db.users.count_documents({
                "_id": {"$in": valid_ids},
                "country": {"$exists": True, "$ne": user_country, "$ne": "", "$ne": None},
            })
            international_count = intl_count_agg

    pts_active   = _cap(effective_active   * 150, CAP_ACTIVE)
    pts_projects = _cap(project_memberships * 100, CAP_PROJECTS)
    pts_intl     = _cap(international_count *  50, CAP_INTL)
    score        = pts_active + pts_projects + pts_intl

    return {
        "score": score,
        "max":   MAX,
        "details": {
            "active_collaborations":  effective_active,
            "project_memberships":    project_memberships,
            "international_collabs":  international_count,
            "pts_active":   pts_active,
            "pts_projects": pts_projects,
            "pts_intl":     pts_intl,
        },
    }


async def _component_grant_activity(uid: str, db) -> dict:
    """Component 4: Grant Activity — max 1000 pts."""
    MAX = 1000
    CAP_SUBMITTED = 600
    CAP_FUNDED    = 400

    # grant_applications: pi_id is the primary investigator
    submitted_agg = await db.grant_applications.aggregate([
        {"$match": {"pi_id": uid}},
        {
            "$group": {
                "_id": None,
                "submitted": {
                    "$sum": {
                        "$cond": [
                            {"$in": ["$status", ["submitted", "under_review", "approved", "funded", "rejected"]]},
                            1,
                            0,
                        ]
                    }
                },
                "funded": {
                    "$sum": {
                        "$cond": [{"$in": ["$status", ["approved", "funded"]]}, 1, 0]
                    }
                },
            }
        },
    ]).to_list(1)

    row = submitted_agg[0] if submitted_agg else {}
    n_submitted = int(row.get("submitted") or 0)
    n_funded    = int(row.get("funded")    or 0)

    pts_submitted = _cap(n_submitted * 200, CAP_SUBMITTED)
    pts_funded    = _cap(n_funded    * 400, CAP_FUNDED)
    score         = pts_submitted + pts_funded

    return {
        "score": score,
        "max":   MAX,
        "details": {
            "grant_applications_submitted": n_submitted,
            "grant_applications_funded":    n_funded,
            "pts_submitted": pts_submitted,
            "pts_funded":    pts_funded,
        },
    }


async def _component_teaching(uid: str, db) -> dict:
    """Component 5: Teaching — max 1000 pts."""
    MAX = 1000
    CAP = 1000

    published_lessons = await db.teaching_lessons.count_documents({
        "owner_id": uid,
        "status": "published",
    })

    score = _cap(published_lessons * 100, CAP)

    return {
        "score": score,
        "max":   MAX,
        "details": {
            "teaching_lessons_published": published_lessons,
            "pts_lessons": score,
        },
    }


async def _component_review_activity(uid: str, db) -> dict:
    """Component 6: Review Activity — max 500 pts."""
    MAX = 500
    CAP = 500

    reviews_completed = await db.review_requests.count_documents({
        "reviewer_id": uid,
        "status": "completed",
    })

    if reviews_completed > 0:
        score = _cap(reviews_completed * 100, CAP)
        reviewer_score_used = None
    else:
        # Fallback: reviewer_score from research_reputation
        rep = await db.research_reputation.find_one(
            {"user_id": uid},
            {"reviewer_score": 1},
        )
        reviewer_score = int((rep or {}).get("reviewer_score") or 0)
        score = _cap(reviewer_score // 2, CAP)
        reviewer_score_used = reviewer_score

    return {
        "score": score,
        "max":   MAX,
        "details": {
            "reviews_completed": reviews_completed,
            "reviewer_score_fallback": reviewer_score_used,
            "pts_reviews": score,
        },
    }


async def _component_platform_reputation(uid: str, db) -> dict:
    """Component 7: Platform Reputation — max 300 pts.

    research_reputation.overall_score max is ~5000 (based on system design).
    5000 / 17 ≈ 294, rounded ceiling to 300.
    """
    MAX = 300

    rep = await db.research_reputation.find_one(
        {"user_id": uid},
        {"overall_score": 1},
    )
    overall_score = int((rep or {}).get("overall_score") or 0)
    raw = overall_score / 17.0
    score = _cap(raw, MAX)

    return {
        "score": score,
        "max":   MAX,
        "details": {
            "overall_score":   overall_score,
            "formula":         "overall_score / 17",
        },
    }


async def _component_profile_completeness(uid: str, db) -> dict:
    """Component 8: Profile Completeness — max 200 pts."""
    MAX = 200

    u_doc = await db.users.find_one(
        {"_id": ObjectId(uid)},
        {
            "orcid":           1,
            "orcid_verified":  1,
            "avatar_url":      1,
            "bio":             1,
            "institution":     1,
            "research_areas":  1,
            "research_keywords": 1,
            "research_methods":  1,
        },
    )
    u = u_doc or {}

    orcid_verified  = bool(u.get("orcid_verified") or u.get("orcid"))
    has_avatar      = bool(u.get("avatar_url"))
    has_bio         = bool((u.get("bio") or "").strip())
    has_institution = bool((u.get("institution") or "").strip())
    has_areas       = bool(u.get("research_areas"))
    has_keywords    = bool(u.get("research_keywords"))
    has_methods     = bool(u.get("research_methods"))

    pts_orcid       = 50 if orcid_verified  else 0
    pts_avatar      = 25 if has_avatar      else 0
    pts_bio         = 25 if has_bio         else 0
    pts_institution = 25 if has_institution else 0
    pts_areas       = 25 if has_areas       else 0
    pts_keywords    = 25 if has_keywords    else 0
    pts_methods     = 25 if has_methods     else 0

    score = sum([
        pts_orcid, pts_avatar, pts_bio,
        pts_institution, pts_areas, pts_keywords, pts_methods,
    ])

    return {
        "score": score,
        "max":   MAX,
        "details": {
            "orcid_verified":  orcid_verified,
            "avatar":          has_avatar,
            "bio":             has_bio,
            "institution":     has_institution,
            "research_areas":  has_areas,
            "keywords":        has_keywords,
            "methods":         has_methods,
            "pts_orcid":       pts_orcid,
            "pts_avatar":      pts_avatar,
            "pts_bio":         pts_bio,
            "pts_institution": pts_institution,
            "pts_areas":       pts_areas,
            "pts_keywords":    pts_keywords,
            "pts_methods":     pts_methods,
        },
    }


# ─────────────────────────── main entry point ─────────────────────────────────

async def compute_synaptiq_impact_score(user_id: str, db) -> dict:
    """Compute the Synaptiq Impact Score (SIS) for a user.

    Aggregates 8 components into a 0–10 000 composite score.
    All component queries are independent and run concurrently via asyncio.gather.

    Args:
        user_id: str — MongoDB ObjectId string of the user.
        db: Motor database instance.

    Returns:
        {
          "total": int,                  # 0-10000
          "components": {
            "research_output":     {"score": int, "max": 2500, "details": {...}},
            "citation_impact":     {"score": int, "max": 2000, "details": {...}},
            "collaboration":       {"score": int, "max": 1500, "details": {...}},
            "grant_activity":      {"score": int, "max": 1000, "details": {...}},
            "teaching":            {"score": int, "max": 1000, "details": {...}},
            "review_activity":     {"score": int, "max":  500, "details": {...}},
            "platform_reputation": {"score": int, "max":  300, "details": {...}},
            "profile_completeness":{"score": int, "max":  200, "details": {...}},
          },
          "label": str,
          "computed_at": str,           # ISO 8601
        }
    """
    import asyncio

    uid = user_id

    (
        c1, c2, c3, c4, c5, c6, c7, c8
    ) = await asyncio.gather(
        _component_research_output(uid, db),
        _component_citation_impact(uid, db),
        _component_collaboration(uid, db),
        _component_grant_activity(uid, db),
        _component_teaching(uid, db),
        _component_review_activity(uid, db),
        _component_platform_reputation(uid, db),
        _component_profile_completeness(uid, db),
    )

    total = (
        c1["score"] + c2["score"] + c3["score"] + c4["score"]
        + c5["score"] + c6["score"] + c7["score"] + c8["score"]
    )
    # Hard cap at 10000
    total = min(10000, total)

    return {
        "total": total,
        "components": {
            "research_output":      c1,
            "citation_impact":      c2,
            "collaboration":        c3,
            "grant_activity":       c4,
            "teaching":             c5,
            "review_activity":      c6,
            "platform_reputation":  c7,
            "profile_completeness": c8,
        },
        "label":       _sis_label(total),
        "computed_at": _now_iso(),
    }
