"""SYNAPTIQ Phase 6 — AI matching + deadline intelligence endpoints."""
from __future__ import annotations

from datetime import datetime, timezone, date, timedelta
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from auth_utils import get_current_user
from db import get_db
from services.ai.matching import (
    match_journals, match_conferences, match_grants, match_reviewers,
)
from services.permissions import require_feature, is_super_admin
from repo.shim import DBProxy
from repo.security_context import SecurityContext

router = APIRouter(prefix="/api", tags=["ai-matching"])


# -------------------------------- MATCHING ----------------------------------
class JournalMatchIn(BaseModel):
    manuscript_id: str
    top_n: int = 6


@router.post("/matching/journal", dependencies=[Depends(require_feature("ai_journal_matching"))])
async def journal_matching(body: JournalMatchIn, user: dict = Depends(get_current_user)):
    return await match_journals(user_id=user["id"], manuscript_id=body.manuscript_id, top_n=body.top_n)


class ConferenceMatchIn(BaseModel):
    manuscript_id: str
    top_n: int = 6


@router.post("/matching/conference", dependencies=[Depends(require_feature("ai_conference_matching"))])
async def conference_matching(body: ConferenceMatchIn, user: dict = Depends(get_current_user)):
    return await match_conferences(user_id=user["id"], manuscript_id=body.manuscript_id, top_n=body.top_n)


class GrantMatchIn(BaseModel):
    manuscript_id: Optional[str] = None
    project_id: Optional[str] = None
    query: Optional[str] = None
    top_n: int = 6


@router.post("/matching/grant", dependencies=[Depends(require_feature("ai_grant_matching"))])
async def grant_matching(body: GrantMatchIn, user: dict = Depends(get_current_user)):
    return await match_grants(user_id=user["id"], manuscript_id=body.manuscript_id,
                              project_id=body.project_id, query=body.query, top_n=body.top_n)


class ReviewerMatchIn(BaseModel):
    manuscript_id: str
    top_n: int = 6


@router.post("/matching/reviewer", dependencies=[Depends(require_feature("ai_assistant"))])
async def reviewer_matching(body: ReviewerMatchIn, user: dict = Depends(get_current_user)):
    return await match_reviewers(user_id=user["id"], manuscript_id=body.manuscript_id, top_n=body.top_n)


@router.get("/matching/history")
async def matching_history(limit: int = 30, kind: Optional[str] = None,
                           user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    q = {"user_id": user["id"]}
    if kind: q["kind"] = kind
    docs = await db.ai_requests.find(q).sort("created_at", -1).limit(limit).to_list(limit)
    for d in docs: d["_id"] = str(d["_id"])
    return docs


@router.get("/matching/analytics")
async def matching_analytics(user: dict = Depends(get_current_user)):
    """User-level + (when admin) global analytics. Counts and most-matched venues."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    is_admin = is_super_admin(user)
    base_q = {} if is_admin else {"user_id": user["id"]}
    pipeline = [
        {"$match": base_q},
        # Normalize legacy records where credits_consumed was stored as a dict
        # `{consumed, balance, action}` from consume_credits() instead of int.
        {"$set": {"credits_consumed": {
            "$cond": [
                {"$eq": [{"$type": "$credits_consumed"}, "object"]},
                {"$ifNull": ["$credits_consumed.consumed", 0]},
                {"$ifNull": ["$credits_consumed", 0]},
            ]
        }}},
        {"$facet": {
            "by_kind": [{"$group": {"_id": "$kind", "n": {"$sum": 1},
                                     "credits": {"$sum": "$credits_consumed"}}},
                        {"$sort": {"n": -1}}],
            "top_journals": [
                {"$match": {"kind": "journal_matching"}},
                {"$unwind": "$output_excerpt"},
                {"$group": {"_id": "$output_excerpt.journal_id", "n": {"$sum": 1}}},
                {"$sort": {"n": -1}}, {"$limit": 10},
            ],
            "top_conferences": [
                {"$match": {"kind": "conference_matching"}},
                {"$unwind": "$output_excerpt"},
                {"$group": {"_id": "$output_excerpt.conference_id", "n": {"$sum": 1}}},
                {"$sort": {"n": -1}}, {"$limit": 10},
            ],
            "top_grants": [
                {"$match": {"kind": "grant_matching"}},
                {"$unwind": "$output_excerpt"},
                {"$group": {"_id": "$output_excerpt.grant_id", "n": {"$sum": 1}}},
                {"$sort": {"n": -1}}, {"$limit": 10},
            ],
            "recent": [
                {"$sort": {"created_at": -1}}, {"$limit": 20},
                {"$project": {"_id": {"$toString": "$_id"}, "kind": 1,
                              "credits_consumed": 1, "created_at": 1, "user_id": 1}},
            ],
        }},
    ]
    out = await db.ai_requests.aggregate(pipeline).to_list(1)
    data = (out[0] if out else {}) or {}

    # Resolve venue titles for the popularity lists (client wants names, not ObjectIds).
    async def _resolve(coll: str, items: list[dict], id_key: str) -> list[dict]:
        if not items: return items
        ids = []
        for it in items:
            if not it.get("_id"): continue
            try: ids.append(ObjectId(it["_id"]))
            except Exception: pass
        if not ids: return items
        docs = await db[coll].find({"_id": {"$in": ids}},
                                   {"title": 1, "name": 1}).to_list(len(ids))
        name_by_id = {str(d["_id"]): (d.get("title") or d.get("name") or "") for d in docs}
        return [{**it, id_key: name_by_id.get(str(it.get("_id"))) or it.get("_id")} for it in items]

    data["top_journals"]    = await _resolve("journals", data.get("top_journals") or [], "title")
    data["top_conferences"] = await _resolve("conferences", data.get("top_conferences") or [], "name")
    data["top_grants"]      = await _resolve("grants", data.get("top_grants") or [], "title")

    # Admin-only: top users by credits
    top_users: list[dict] = []
    assistant_sessions = await db.chat_sessions.count_documents({} if is_admin else {"user_id": user["id"]})
    if is_admin:
        users_pipe = [
            {"$group": {"_id": "$user_id", "n": {"$sum": 1}, "credits": {"$sum": "$credits_consumed"}}},
            {"$sort": {"credits": -1}}, {"$limit": 10},
        ]
        tu = await db.ai_requests.aggregate(users_pipe).to_list(10)
        # resolve names
        u_ids = []
        for r in tu:
            try: u_ids.append(ObjectId(r["_id"]))
            except Exception: pass
        u_docs = await db.users.find({"_id": {"$in": u_ids}}, {"full_name": 1, "email": 1}).to_list(len(u_ids)) if u_ids else []
        u_by_id = {str(d["_id"]): d for d in u_docs}
        for r in tu:
            u = u_by_id.get(str(r["_id"])) or {}
            top_users.append({"_id": r["_id"], "full_name": u.get("full_name") or u.get("email") or r["_id"],
                              "calls": r["n"], "credits": r["credits"]})
    data["top_users"] = top_users
    data["assistant_sessions"] = assistant_sessions

    return {"scope": "global" if is_admin else "user", "data": data, **data}


# -------------------------- DEADLINE INTELLIGENCE ----------------------------
def _today() -> date: return datetime.now(timezone.utc).date()


def _urgency(deadline_iso: Optional[str]) -> str:
    if not deadline_iso: return "upcoming"
    try: d = date.fromisoformat(deadline_iso[:10])
    except Exception: return "upcoming"
    today = _today(); diff = (d - today).days
    if diff < 0: return "missed"
    if diff <= 3: return "critical"
    if diff <= 14: return "due_soon"
    return "upcoming"


async def _user_deadlines(user_id: str, *, workspace_id: Optional[str] = None,
                          project_id: Optional[str] = None) -> list[dict]:
    """Aggregate every relevant deadline for the user (or scoped to a workspace/project)."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    items: list[dict] = []
    today_iso = _today().isoformat()

    # Manuscripts the user authors (or scoped to workspace/project)
    m_query: dict = {"authors": user_id}
    if workspace_id: m_query["workspace_id"] = workspace_id
    if project_id: m_query["project_id"] = project_id
    manuscripts = await db.manuscripts.find(m_query).to_list(200)
    ms_ids = [str(m["_id"]) for m in manuscripts]

    # Submissions for these manuscripts
    if ms_ids:
        subs = await db.submissions.find({"manuscript_id": {"$in": ms_ids}}).to_list(400)
        for s in subs:
            venue_kind = s.get("venue_kind")
            venue = (s.get("venue_snapshot") or {})
            venue_name = venue.get("name") or "Unknown venue"
            stage = s.get("stage")
            # Hydrate live deadlines from venue (best-effort)
            sub_dl = None; cam_dl = None
            if venue_kind == "conference" and s.get("venue_id"):
                try: vc = await db.conferences.find_one({"_id": ObjectId(s["venue_id"])})
                except Exception: vc = None
                if vc:
                    sub_dl = vc.get("submission_deadline")
                    cam_dl = vc.get("camera_ready_date")
            label_kind = "conference_submission" if venue_kind == "conference" else "journal_submission"
            # Submission deadline for not-yet-submitted
            if stage in ("selected", "ready") and sub_dl:
                items.append({"kind": label_kind, "date": sub_dl, "urgency": _urgency(sub_dl),
                              "label": f"Submit to {venue_name}",
                              "manuscript_id": s["manuscript_id"], "submission_id": str(s["_id"]),
                              "venue_kind": venue_kind, "link": f"/manuscripts/{s['manuscript_id']}"})
            # Revision deadline (if recorded in revision_notes with submitted_at + 14d default)
            if stage == "revision_requested":
                last_rev = (s.get("revision_notes") or [])[-1] if s.get("revision_notes") else None
                dueby = None
                if last_rev:
                    try:
                        base = datetime.fromisoformat(last_rev.get("submitted_at"))
                        dueby = (base + timedelta(days=21)).date().isoformat()
                    except Exception: pass
                if dueby:
                    items.append({"kind": "revision_due", "date": dueby, "urgency": _urgency(dueby),
                                  "label": f"Revision due — {venue_name}",
                                  "manuscript_id": s["manuscript_id"], "submission_id": str(s["_id"]),
                                  "link": f"/manuscripts/{s['manuscript_id']}"})
            # Camera-ready
            if cam_dl and stage in ("accepted",):
                items.append({"kind": "camera_ready", "date": cam_dl, "urgency": _urgency(cam_dl),
                              "label": f"Camera-ready — {venue_name}",
                              "manuscript_id": s["manuscript_id"], "submission_id": str(s["_id"]),
                              "link": f"/manuscripts/{s['manuscript_id']}"})

    # Grant deadlines for saved/tracked grants on the user
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    saved_grants = user.get("saved_funding_ids") or []
    if saved_grants:
        from bson.errors import InvalidId
        oids = []
        for s in saved_grants:
            try: oids.append(ObjectId(s))
            except (InvalidId, Exception): continue
        if oids:
            grants = await db.grants.find({"_id": {"$in": oids}}).to_list(200)
            for g in grants:
                dl = g.get("deadline")
                if not dl: continue
                items.append({"kind": "grant_deadline", "date": dl, "urgency": _urgency(dl),
                              "label": f"Grant: {g.get('title','')[:60]}",
                              "grant_id": str(g["_id"]), "sponsor": g.get("sponsor"),
                              "link": f"/grants/{str(g['_id'])}"})

    # Workspace milestones (only when in scope or aggregating to user)
    if workspace_id:
        ms = await db.milestones.find({"workspace_id": workspace_id, "completed": {"$ne": True}}).to_list(200)
        for x in ms:
            d = x.get("target_date")
            if d:
                items.append({"kind": "milestone", "date": d, "urgency": _urgency(d),
                              "label": x.get("title") or "Milestone",
                              "milestone_id": str(x["_id"]), "workspace_id": workspace_id,
                              "link": f"/workspaces/{workspace_id}"})

    # Sort: missed first (highest urgency), then critical → due_soon → upcoming.
    URG_RANK = {"missed": 0, "critical": 1, "due_soon": 2, "upcoming": 3}
    items.sort(key=lambda x: (URG_RANK.get(x["urgency"], 9), x.get("date") or "9999-12-31"))
    return items


@router.get("/deadlines/mine")
async def deadlines_mine(workspace_id: Optional[str] = None,
                         project_id: Optional[str] = None,
                         limit: int = 12,
                         user: dict = Depends(get_current_user)):
    items = await _user_deadlines(user["id"], workspace_id=workspace_id, project_id=project_id)
    # bucket counts
    counts = {"missed": 0, "critical": 0, "due_soon": 0, "upcoming": 0}
    for it in items: counts[it["urgency"]] = counts.get(it["urgency"], 0) + 1
    return {"items": items[:limit], "total": len(items), "counts": counts}
