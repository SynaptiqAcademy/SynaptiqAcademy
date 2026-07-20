"""Reputation scoring service — computes 5 platform sub-scores + 4 named
dimensions (research, teaching, community, overall) from real activity.

Sub-scores (each 0..100):
  collaboration  : accepted collaborations, completion rate, workspace memberships
  publication    : platform manuscripts + linked DOIs + OpenAlex external metrics
  reviewer       : peer reviews completed + turnaround time + quality ratings
  funding        : grants linked to workspaces with awarded status
  activity       : workspace/manuscript activity in last 90 days
  teaching       : lesson plans, assessments, portfolio, workspace messages (NEW)

Aggregate dimensions:
  research_score  : publication, reviewer, funding, activity (weighted)
  teaching_score  : teaching sub-score (direct)
  community_score : collaboration + activity (weighted)
  overall_score   : weighted by user_type (researcher-heavy vs teaching-heavy)

All scores cached in `reputation_scores` with TTL 24h.
Anti-gaming: all calculations read aggregate DB counts from source-of-truth
collections. Users cannot submit reputation claims.
"""
from __future__ import annotations
import logging
import math
from datetime import datetime, timedelta, timezone
from typing import Optional

from bson import ObjectId

from db import get_db
from repo.shim import DBProxy
from repo.security_context import SecurityContext

logger = logging.getLogger("synaptiq.reputation")

# ── Sub-score weights for the existing 5-score overall (backward compat) ──────
WEIGHTS = {"collaboration": 0.25, "publication": 0.30, "reviewer": 0.15,
           "funding": 0.15, "activity": 0.15}

# ── Dimension weights per user_type ───────────────────────────────────────────
# research_weight + teaching_weight + community_weight must each be in [0, 1].
# Overall = research*rw + teaching*tw + community*cw (then normalised to 100).
_DW_RESEARCHER   = {"research": 0.55, "teaching": 0.05, "community": 0.40}
_DW_EDUCATOR     = {"research": 0.15, "teaching": 0.60, "community": 0.25}
_DW_FACULTY      = {"research": 0.35, "teaching": 0.30, "community": 0.35}
_DW_INDUSTRY     = {"research": 0.30, "teaching": 0.10, "community": 0.60}
_DW_DEFAULT      = {"research": 0.40, "teaching": 0.10, "community": 0.50}

DIMENSION_WEIGHTS: dict[str, dict] = {
    "undergraduate_student":   _DW_RESEARCHER,
    "masters_student":         _DW_RESEARCHER,
    "phd_candidate":           _DW_RESEARCHER,
    "postdoctoral_researcher":  _DW_RESEARCHER,
    "researcher":              _DW_RESEARCHER,
    "educator":                _DW_EDUCATOR,
    "trainer":                 _DW_EDUCATOR,
    "university_faculty":      _DW_FACULTY,
    "industry_professional":   _DW_INDUSTRY,
}


def _saturate(x: float, scale: float = 12.0) -> float:
    """Smooth 0..100 mapping using log-saturation. ~12 events → ~60; 50+ → ~98."""
    if x <= 0:
        return 0.0
    return round(min(100.0, 100.0 * (1.0 - math.exp(-x / scale))), 1)


# ── Sub-score functions ───────────────────────────────────────────────────────

async def _collab_score(db, uid: str) -> dict:
    owned       = await db.collaborations.count_documents({"owner_id": uid})
    accepted_in = await db.applications.count_documents({"applicant_id": uid, "status": "accepted"})
    closed_in   = await db.applications.count_documents({
        "applicant_id": uid, "status": "accepted", "collaboration_status": "closed"
    })
    completion_rate = (closed_in / accepted_in) if accepted_in else 0.0
    members = await db.workspaces.count_documents({"member_ids": uid})
    raw = owned * 1.0 + accepted_in * 1.5 + members * 0.5
    base = _saturate(raw, scale=10.0)
    score = round(min(100.0, base * (0.85 + 0.30 * completion_rate)), 1)
    return {"score": score, "owned": owned, "accepted": accepted_in,
            "completed": closed_in, "completion_rate": round(completion_rate, 2),
            "workspaces": members}


async def _publication_score(db, uid: str) -> dict:
    pubs        = await db.manuscripts.count_documents({"author_ids": uid, "status": "published"})
    in_progress = await db.manuscripts.count_documents({"author_ids": uid, "status": {"$ne": "published"}})
    user = await db.users.find_one(
        {"_id": ObjectId(uid)},
        {"openalex_metrics": 1, "h_index": 1, "publications_count": 1}
    )
    ext       = (user or {}).get("openalex_metrics") or {}
    ext_works = int(ext.get("works_count") or (user or {}).get("publications_count") or 0)
    ext_cites = int(ext.get("citations") or 0)
    h_index   = int(ext.get("h_index") or (user or {}).get("h_index") or 0)
    raw = pubs * 3 + ext_works * 1 + in_progress * 0.5 + math.log1p(max(0, ext_cites)) * 2 + h_index * 1.5
    score = _saturate(raw, scale=30.0)
    return {"score": score, "platform_published": pubs, "platform_in_progress": in_progress,
            "external_works": ext_works, "external_citations": ext_cites, "h_index": h_index}


async def _reviewer_score(db, uid: str) -> dict:
    completed = await db.reviews.count_documents(
        {"reviewer_id": uid, "status": {"$in": ["submitted", "completed"]}}
    )
    pipeline = [
        {"$match": {"reviewer_id": uid, "status": {"$in": ["submitted", "completed"]},
                    "turnaround_days": {"$exists": True}}},
        {"$group": {"_id": None, "avg_days": {"$avg": "$turnaround_days"},
                    "avg_quality": {"$avg": "$author_quality_rating"}}},
    ]
    out = await db.reviews.aggregate(pipeline).to_list(1)
    avg_days    = (out[0].get("avg_days")    if out else None) or 0
    avg_quality = (out[0].get("avg_quality") if out else None) or 0
    base = _saturate(completed * 2.5, scale=8.0)
    speed_mult   = 1.0 if not avg_days    else max(0.7, min(1.15, 1.15 - (avg_days - 14) / 60))
    quality_mult = 1.0 if not avg_quality else 0.85 + 0.30 * (avg_quality / 5.0)
    score = round(min(100.0, base * speed_mult * quality_mult), 1)
    return {"score": score, "completed": completed,
            "avg_turnaround_days": round(avg_days, 1), "avg_quality": round(avg_quality, 2)}


async def _funding_score(db, uid: str) -> dict:
    awarded   = await db.grant_links.count_documents({"user_id": uid, "status": "awarded"})
    submitted = await db.grant_links.count_documents({"user_id": uid, "status": "submitted"})
    pipeline  = [
        {"$match": {"user_id": uid, "status": "awarded"}},
        {"$group": {"_id": None, "total": {"$sum": "$amount_usd"}}},
    ]
    out = await db.grant_links.aggregate(pipeline).to_list(1)
    total_usd = (out[0].get("total") if out else 0) or 0
    raw = awarded * 6 + submitted * 1 + math.log1p(total_usd / 10000) * 3
    return {"score": _saturate(raw, scale=10.0), "awarded": awarded,
            "submitted": submitted, "total_awarded_usd": int(total_usd)}


async def _activity_score(db, uid: str) -> dict:
    cutoff      = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    msg_count   = await db.chat_messages.count_documents({"user_id": uid, "created_at": {"$gte": cutoff}})
    task_done   = await db.tasks.count_documents({"completed_by": uid, "completed_at": {"$gte": cutoff}})
    manus_edits = await db.manuscript_versions.count_documents({"editor_id": uid, "created_at": {"$gte": cutoff}})
    raw = msg_count * 0.10 + task_done * 1.2 + manus_edits * 1.0
    return {"score": _saturate(raw, scale=10.0), "chat_messages_90d": msg_count,
            "tasks_completed_90d": task_done, "manuscript_edits_90d": manus_edits}


async def _teaching_score(db, uid: str) -> dict:
    """Teaching-specific dimension — lesson plans, assessments, portfolio, workspace engagement."""
    lessons     = await db.teaching_lessons.count_documents({"owner_id": uid})
    assessments = await db.teaching_assessments.count_documents({"owner_id": uid})
    portfolio   = await db.teaching_portfolio_items.count_documents({"owner_id": uid})

    # Teaching workspace messages (AI assistant engagement)
    ws_ids_cursor = db.teaching_workspaces.find({"owner_id": uid}, {"_id": 1})
    ws_ids = [str(doc["_id"]) async for doc in ws_ids_cursor]
    chat_msgs = 0
    if ws_ids:
        chat_msgs = await db.teaching_chat_messages.count_documents(
            {"workspace_id": {"$in": ws_ids}, "role": "user"}
        )

    # Educational collaborations — collaborations with type containing "teaching" or "education"
    edu_collabs = await db.collaborations.count_documents({
        "owner_id": uid,
        "collab_type": {"$in": ["teaching", "education", "mentorship", "curriculum",
                                 "Teaching", "Education", "Mentorship"]},
    })

    raw = (lessons * 3.0 + assessments * 3.0 + portfolio * 2.0
           + chat_msgs * 0.3 + edu_collabs * 4.0)
    score = _saturate(raw, scale=20.0)
    return {
        "score": score,
        "lessons_created": lessons,
        "assessments_created": assessments,
        "portfolio_items": portfolio,
        "workspace_messages": chat_msgs,
        "teaching_collaborations": edu_collabs,
    }


# ── Dimension aggregation ─────────────────────────────────────────────────────

def _compute_dimensions(collab: dict, pub: dict, rev: dict, fund: dict,
                        act: dict, teaching: dict, user_type: Optional[str]) -> dict:
    """Collapse 6 sub-scores into 3 named dimensions + overall."""
    research_score = round(
        0.40 * pub["score"]
        + 0.20 * rev["score"]
        + 0.20 * fund["score"]
        + 0.20 * act["score"],
        1,
    )
    community_score = round(
        0.65 * collab["score"]
        + 0.35 * act["score"],
        1,
    )
    teaching_score = teaching["score"]

    dw = DIMENSION_WEIGHTS.get(user_type or "", _DW_DEFAULT)
    total_w = dw["research"] + dw["teaching"] + dw["community"]
    if total_w == 0:
        total_w = 1.0
    overall = round(
        (dw["research"] * research_score
         + dw["teaching"] * teaching_score
         + dw["community"] * community_score) / total_w,
        1,
    )
    return {
        "research_score": research_score,
        "teaching_score": teaching_score,
        "community_score": community_score,
        "overall": overall,
    }


# ── Main compute ──────────────────────────────────────────────────────────────

async def compute(user_id: str, *, force: bool = False) -> dict:
    """Compute reputation for one user with 24h cache.

    Returns the full score document including sub-scores, 4 dimensions, badges,
    and metadata. Safe to call frequently — returns cached data within 24h.
    """
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    now = datetime.now(timezone.utc)

    if not force:
        cached = await db.reputation_scores.find_one({"user_id": user_id})
        if cached and cached.get("expires_at") and cached["expires_at"] > now.isoformat():
            cached.pop("_id", None)
            return cached

    # Look up user_type for dimension weighting
    user = await db.users.find_one({"_id": ObjectId(user_id)}, {"user_type": 1})
    user_type = (user or {}).get("user_type")

    collab   = await _collab_score(db, user_id)
    pub      = await _publication_score(db, user_id)
    rev      = await _reviewer_score(db, user_id)
    fund     = await _funding_score(db, user_id)
    act      = await _activity_score(db, user_id)
    teaching = await _teaching_score(db, user_id)

    dims = _compute_dimensions(collab, pub, rev, fund, act, teaching, user_type)

    # Legacy overall (5-score weighted) — kept for backward compat
    legacy_overall = round(
        WEIGHTS["collaboration"] * collab["score"]
        + WEIGHTS["publication"]  * pub["score"]
        + WEIGHTS["reviewer"]     * rev["score"]
        + WEIGHTS["funding"]      * fund["score"]
        + WEIGHTS["activity"]     * act["score"],
        1,
    )

    doc: dict = {
        "user_id": user_id,
        "user_type": user_type,
        # Sub-scores
        "collaboration": collab,
        "publication":   pub,
        "reviewer":      rev,
        "funding":       fund,
        "activity":      act,
        "teaching":      teaching,
        # 4 dimensions
        "research_score":  dims["research_score"],
        "teaching_score":  dims["teaching_score"],
        "community_score": dims["community_score"],
        "overall":         dims["overall"],
        # Legacy overall (kept for backward compat with existing ReputationBadge)
        "legacy_overall":  legacy_overall,
        # Weights used (for transparency)
        "dimension_weights": DIMENSION_WEIGHTS.get(user_type or "", _DW_DEFAULT),
        "weights":           WEIGHTS,
        "computed_at":  now.isoformat(),
        "expires_at":   (now + timedelta(hours=24)).isoformat(),
    }

    # Compute and embed badges
    from services.reputation.badges import compute_badges
    try:
        badges = await compute_badges(user_id, doc)
        doc["badges"] = badges
    except Exception as e:
        logger.warning("Badge computation failed for %s: %s", user_id, e)
        doc["badges"] = []

    await db.reputation_scores.update_one(
        {"user_id": user_id}, {"$set": doc}, upsert=True
    )
    doc.pop("_id", None)
    return doc


async def compute_batch(user_ids: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for uid in user_ids:
        try:
            out[uid] = await compute(uid)
        except Exception as e:
            logger.warning("Reputation compute failed for %s: %s", uid, e)
    return out
