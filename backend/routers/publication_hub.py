"""Publication Hub — manuscript ↔ venue submission tracker.

Pipeline stages (canonical):
    selected → ready → submitted → under_review →
        revision_requested (loop) → accepted → published
        OR rejected / withdrawn

Each submission row links one manuscript to ONE venue (journal OR conference).
A manuscript can be linked to multiple submissions over its lifetime (you can
submit to journal A, get rejected, then submit to journal B). The active
submission is the latest one whose stage is not in {published, rejected, withdrawn}.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth_utils import get_current_user
from db import get_db
from services.permissions import require_feature
from repo.shim import DBProxy
from repo.security_context import SecurityContext

router = APIRouter(prefix="/api/publication-hub", tags=["publication-hub"],
                   dependencies=[Depends(require_feature("publication_tracking"))])


STAGES = ["selected", "ready", "submitted", "under_review",
          "revision_requested", "accepted", "published", "rejected", "withdrawn"]
ACTIVE_STAGES = {"selected", "ready", "submitted", "under_review", "revision_requested", "accepted"}
TERMINAL_STAGES = {"published", "rejected", "withdrawn"}


def _now() -> str: return datetime.now(timezone.utc).isoformat()


def _ser(d):
    if not d: return None
    x = dict(d); x["id"] = str(x.pop("_id"))
    if x.get("manuscript_id") and not isinstance(x["manuscript_id"], str):
        x["manuscript_id"] = str(x["manuscript_id"])
    return x


# ---------------------------- pipeline overview ------------------------------
@router.get("/pipeline")
async def pipeline(user: dict = Depends(get_current_user)):
    """Active overview for the calling researcher.

    Combines:
      - manuscripts they author
      - submissions on those manuscripts (any stage)
    Returns:
      - summary counts
      - stages: each stage → list of {manuscript+submission} rows
    """
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    manuscripts = await db.manuscripts.find({"authors": user["id"]}).sort("updated_at", -1).to_list(300)
    ms_ids = [str(m["_id"]) for m in manuscripts]
    submissions = []
    if ms_ids:
        submissions = await db.submissions.find({"manuscript_id": {"$in": ms_ids}}).sort("updated_at", -1).to_list(500)

    # Latest submission per manuscript (for the kanban)
    latest_by_ms: dict[str, dict] = {}
    for s in submissions:
        m_id = s["manuscript_id"]
        if m_id not in latest_by_ms:
            latest_by_ms[m_id] = s

    # Rows = one per manuscript. Stage = latest submission's stage, or fall back to manuscript.status mapping.
    fallback_stage = {
        "draft": "selected", "internal_review": "ready", "ready_for_submission": "ready",
        "submitted": "submitted", "revision_requested": "revision_requested",
        "accepted": "accepted", "published": "published", "rejected": "rejected",
    }
    by_stage: dict[str, list] = {s: [] for s in STAGES}
    counts = {"total": len(manuscripts), "active": 0,
              "under_review": 0, "revising": 0, "accepted": 0, "published": 0, "rejected": 0}
    for m in manuscripts:
        m_id = str(m["_id"])
        sub = latest_by_ms.get(m_id)
        stage = (sub.get("stage") if sub else fallback_stage.get(m.get("status", "draft"), "selected"))
        row = {
            "manuscript": {"id": m_id, "title": m.get("title", ""),
                            "manuscript_type": m.get("manuscript_type", ""),
                            "status": m.get("status", "draft"),
                            "current_version": m.get("current_version", 0)},
            "submission": _ser(sub) if sub else None,
            "stage": stage,
        }
        by_stage.setdefault(stage, []).append(row)
        if stage in ACTIVE_STAGES: counts["active"] += 1
        if stage == "under_review": counts["under_review"] += 1
        if stage == "revision_requested": counts["revising"] += 1
        if stage == "accepted": counts["accepted"] += 1
        if stage == "published": counts["published"] += 1
        if stage == "rejected": counts["rejected"] += 1
    return {"summary": counts, "stages": by_stage, "stage_order": STAGES}


# ---------------------------- CRUD submissions -------------------------------
class CreateSubmissionIn(BaseModel):
    manuscript_id: str
    venue_kind: str           # "journal" | "conference"
    venue_id: str
    stage: str = "selected"


async def _venue_snapshot(db, kind: str, vid: str) -> dict:
    try: oid = ObjectId(vid)
    except Exception: return {"name": "Unknown"}
    if kind == "journal":
        j = await db.journals.find_one({"_id": oid})
        return {"name": (j or {}).get("title", "Unknown journal"),
                "quartile": (j or {}).get("quartile"),
                "publisher": (j or {}).get("publisher")} if j else {"name": "Unknown"}
    else:
        c = await db.conferences.find_one({"_id": oid})
        return {"name": (c or {}).get("name", "Unknown conference"),
                "acronym": (c or {}).get("acronym"),
                "rank": (c or {}).get("rank")} if c else {"name": "Unknown"}


@router.post("/submissions")
async def create_submission(body: CreateSubmissionIn, user: dict = Depends(get_current_user)):
    if body.venue_kind not in ("journal", "conference"): raise HTTPException(400, "Invalid venue_kind")
    if body.stage not in STAGES: raise HTTPException(400, "Invalid stage")
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try: m_oid = ObjectId(body.manuscript_id)
    except Exception: raise HTTPException(404, "Manuscript not found")
    m = await db.manuscripts.find_one({"_id": m_oid})
    if not m: raise HTTPException(404, "Manuscript not found")
    if user["id"] not in m.get("authors", []): raise HTTPException(403, "Only authors can submit")
    snapshot = await _venue_snapshot(db, body.venue_kind, body.venue_id)
    doc = {
        "manuscript_id": body.manuscript_id,
        "author_id": user["id"],
        "venue_kind": body.venue_kind,
        "venue_id": body.venue_id,
        "venue_snapshot": snapshot,
        "stage": body.stage,
        "history": [{"stage": body.stage, "at": _now(), "by": user["id"]}],
        "reviewer_feedback": [],
        "revision_notes": [],
        "submitted_at": _now() if body.stage in ("submitted", "under_review") else None,
        "decision_at": None,
        "decision": None,
        "final_outcome": None,
        "doi": None,
        "created_at": _now(),
        "updated_at": _now(),
    }
    r = await db.submissions.insert_one(doc); doc["_id"] = r.inserted_id
    # Mirror target_journal_id on the manuscript for convenience
    if body.venue_kind == "journal":
        await db.manuscripts.update_one({"_id": m_oid}, {"$set": {"target_journal_id": body.venue_id, "updated_at": _now()}})
    return _ser(doc)


class UpdateSubmissionIn(BaseModel):
    stage: Optional[str] = None
    decision: Optional[str] = None  # accept | minor_revision | major_revision | reject
    decision_at: Optional[str] = None
    final_outcome: Optional[str] = None
    doi: Optional[str] = None


@router.patch("/submissions/{sid}")
async def update_submission(sid: str, body: UpdateSubmissionIn, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try: oid = ObjectId(sid)
    except Exception: raise HTTPException(404, "Not found")
    s = await db.submissions.find_one({"_id": oid})
    if not s: raise HTTPException(404, "Not found")
    if s.get("author_id") != user["id"]:
        # also allow co-authors
        try: m = await db.manuscripts.find_one({"_id": ObjectId(s["manuscript_id"])})
        except Exception: m = None
        if not m or user["id"] not in (m.get("authors") or []):
            raise HTTPException(403, "Forbidden")
    upd: dict = {"updated_at": _now()}
    push: dict = {}
    if body.stage is not None:
        if body.stage not in STAGES: raise HTTPException(400, "Invalid stage")
        upd["stage"] = body.stage
        push["history"] = {"stage": body.stage, "at": _now(), "by": user["id"]}
        if body.stage in ("submitted", "under_review") and not s.get("submitted_at"):
            upd["submitted_at"] = _now()
        if body.stage in TERMINAL_STAGES:
            upd["decision_at"] = upd.get("decision_at") or _now()
    if body.decision is not None:
        if body.decision not in ("accept", "minor_revision", "major_revision", "reject"):
            raise HTTPException(400, "Invalid decision")
        upd["decision"] = body.decision
        upd["decision_at"] = body.decision_at or _now()
    if body.final_outcome is not None: upd["final_outcome"] = body.final_outcome
    if body.doi is not None: upd["doi"] = body.doi
    op = {"$set": upd}
    if push:
        # Cap history at 50 entries; reviewer_feedback and revision_notes are unbounded arrays
        # pushed separately via dedicated endpoints — only history needs the slice guard.
        op["$push"] = {
            k: {"$each": [v], "$slice": -50} for k, v in push.items()
        }
    await db.submissions.update_one({"_id": oid}, op)
    s = await db.submissions.find_one({"_id": oid})
    return _ser(s)


class FeedbackIn(BaseModel):
    round: int = 1
    reviewer_alias: str = "Reviewer"
    body: str


@router.post("/submissions/{sid}/feedback")
async def add_feedback(sid: str, body: FeedbackIn, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try: oid = ObjectId(sid)
    except Exception: raise HTTPException(404, "Not found")
    s = await db.submissions.find_one({"_id": oid})
    if not s: raise HTTPException(404, "Not found")
    # Allow any manuscript co-author, not just the submission creator
    try: m = await db.manuscripts.find_one({"_id": ObjectId(s["manuscript_id"])})
    except Exception: m = None
    if not m or user["id"] not in (m.get("authors") or []):
        raise HTTPException(403, "Forbidden")
    entry = {"round": body.round, "reviewer_alias": body.reviewer_alias, "body": body.body, "created_at": _now()}
    await db.submissions.update_one({"_id": oid},
        {"$push": {"reviewer_feedback": {"$each": [entry], "$slice": -100}}, "$set": {"updated_at": _now()}})
    return entry


class RevisionIn(BaseModel):
    round: int = 1
    body: str


@router.post("/submissions/{sid}/revision")
async def add_revision_note(sid: str, body: RevisionIn, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try: oid = ObjectId(sid)
    except Exception: raise HTTPException(404, "Not found")
    s = await db.submissions.find_one({"_id": oid})
    if not s: raise HTTPException(404, "Not found")
    # Allow any manuscript co-author, not just the submission creator
    try: m = await db.manuscripts.find_one({"_id": ObjectId(s["manuscript_id"])})
    except Exception: m = None
    if not m or user["id"] not in (m.get("authors") or []):
        raise HTTPException(403, "Forbidden")
    entry = {"round": body.round, "body": body.body, "submitted_at": _now()}
    await db.submissions.update_one({"_id": oid},
        {"$push": {"revision_notes": {"$each": [entry], "$slice": -50}},
         "$set": {"updated_at": _now(), "stage": "revision_requested"}})
    return entry


@router.get("/submissions")
async def list_submissions(manuscript_id: Optional[str] = None,
                            stage: Optional[str] = None,
                            user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    q: dict = {}
    if manuscript_id:
        # Authorization: caller must be an author of the manuscript
        try:
            m_auth = await db.manuscripts.find_one({"_id": ObjectId(manuscript_id)}, {"authors": 1})
        except Exception:
            m_auth = None
        if not m_auth or user["id"] not in (m_auth.get("authors") or []):
            raise HTTPException(403, "Forbidden")
        q["manuscript_id"] = manuscript_id
    else:
        q["author_id"] = user["id"]
    if stage:
        if stage == "active": q["stage"] = {"$in": list(ACTIVE_STAGES)}
        elif stage == "terminal": q["stage"] = {"$in": list(TERMINAL_STAGES)}
        else: q["stage"] = stage
    docs = await db.submissions.find(q).sort("updated_at", -1).to_list(200)
    return [_ser(d) for d in docs]


@router.get("/submissions/{sid}")
async def get_submission(sid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try: oid = ObjectId(sid)
    except Exception: raise HTTPException(404, "Not found")
    s = await db.submissions.find_one({"_id": oid})
    if not s: raise HTTPException(404, "Not found")
    # access: any manuscript author
    try: m = await db.manuscripts.find_one({"_id": ObjectId(s["manuscript_id"])})
    except Exception: m = None
    if not m or user["id"] not in (m.get("authors") or []): raise HTTPException(403, "Forbidden")
    return _ser(s)


# ------------------------ backward-compatible status -------------------------
LEGACY_STAGES = ["draft", "under_review", "revision_requested", "accepted", "published", "rejected"]


@router.post("/manuscripts/{manuscript_id}/status")
async def change_status(manuscript_id: str, body: dict, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    new_status = body.get("status")
    if new_status not in LEGACY_STAGES: raise HTTPException(status_code=400, detail="Invalid status")
    try: oid = ObjectId(manuscript_id)
    except Exception: raise HTTPException(status_code=404, detail="Not found")
    doc = await db.manuscripts.find_one({"_id": oid})
    if not doc: raise HTTPException(status_code=404, detail="Not found")
    if user["id"] not in doc.get("authors", []): raise HTTPException(status_code=403, detail="Forbidden")
    await db.manuscripts.update_one({"_id": oid}, {"$set": {"status": new_status, "updated_at": _now()}})
    return {"ok": True, "status": new_status}
