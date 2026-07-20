"""Manuscripts — production lifecycle router.

Endpoints:
  GET    /api/manuscripts                          — list (author/coauthor)
  POST   /api/manuscripts                          — create
  GET    /api/manuscripts/{id}                     — detail + enrichment
  PATCH  /api/manuscripts/{id}                     — update (any author)
  DELETE /api/manuscripts/{id}                     — delete (lead author)
  GET    /api/manuscripts/{id}/dashboard           — progress, readiness, contributions
  POST   /api/manuscripts/{id}/authors             — add author (lead only)
  PATCH  /api/manuscripts/{id}/authors             — reorder + set corresponding author
  POST   /api/manuscripts/{id}/versions            — snapshot current state
  GET    /api/manuscripts/{id}/versions            — version history
  POST   /api/manuscripts/{id}/versions/{v}/restore— restore a version
  GET    /api/manuscripts/{id}/comments            — comments (filtered by section)
  POST   /api/manuscripts/{id}/comments            — add comment
  POST   /api/manuscripts/comments/{cid}/resolve   — resolve a comment
  GET    /api/manuscripts/{id}/review-requests     — list review assignments
  POST   /api/manuscripts/{id}/review-requests     — assign a peer reviewer
  PATCH  /api/manuscripts/review-requests/{rid}    — update (accept/decline/complete + verdict)
  POST   /api/manuscripts/{id}/contributions       — log a writing contribution
  GET    /api/manuscripts/{id}/references          — citation list
  POST   /api/manuscripts/{id}/references          — add citation
  DELETE /api/manuscripts/{id}/references/{ref_id} — remove citation
  GET    /api/manuscripts/{id}/journal-matches     — AI journal recommendations
  GET    /api/manuscripts/{id}/analytics           — submission timeline + review cycles
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from db import get_db
from models import ManuscriptCreate, ManuscriptUpdate
from services.permissions import assert_quota
from repo.shim import DBProxy
from repo.security_context import SecurityContext

log = logging.getLogger("synaptiq.manuscripts")

def _emit_rep(user_id, event_type, entity_id, description=None):
    async def _task():
        try:
            from services.reputation.events import emit_reputation_event
            await emit_reputation_event(user_id, event_type, "manuscript", entity_id, description)
        except Exception:
            pass
    try:
        asyncio.ensure_future(_task())
    except RuntimeError:
        pass
router = APIRouter(prefix="/api/manuscripts", tags=["manuscripts"])

# ── constants ──────────────────────────────────────────────────────────────────

MANUSCRIPT_TYPES = [
    "Journal Article", "Conference Paper", "Review Paper", "Systematic Review",
    "Meta-Analysis", "Book Chapter", "Research Proposal", "Grant Proposal",
    "Doctoral Thesis Chapter", "White Paper",
]

MANUSCRIPT_STATUSES = [
    "draft", "internal_review", "ready_for_submission", "submitted",
    "under_review", "major_revision", "minor_revision", "accepted",
    "rejected", "published", "withdrawn",
]

DEFAULT_SECTIONS = {
    "title": "", "abstract": "", "introduction": "", "literature_review": "",
    "methodology": "", "results": "", "discussion": "", "conclusion": "",
    "references": "", "appendices": "",
}

SECTION_KEYS = list(DEFAULT_SECTIONS.keys())

AUTHOR_ROLES = ["Lead Author", "Co-Author", "Corresponding Author", "Reviewer", "Advisor", "Editor"]

# ── helpers ────────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ser(d):
    if not d:
        return None
    x = dict(d)
    x["id"] = str(x.pop("_id"))
    return x


def _assert_author(doc: dict, user_id: str) -> None:
    if user_id not in (doc.get("authors") or []):
        raise HTTPException(403, "Only manuscript authors can perform this action")


def _assert_lead(doc: dict, user_id: str) -> None:
    if doc.get("lead_author_id") != user_id:
        raise HTTPException(403, "Only the lead author can perform this action")


def _progress_pct(sections: dict) -> int:
    filled = sum(1 for k in SECTION_KEYS if (sections or {}).get(k, "").strip())
    return int(filled / len(SECTION_KEYS) * 100)


async def _notify(user_id: str, kind: str, title: str, body: str,
                  link: str, actor_id: str, payload: dict = None) -> None:
    try:
        from services.notifications_service import dispatch as _d, NotificationEvent as _NE
        await _d(_NE(user_id=user_id, kind=kind, title=title, body=body,
                     link=link, actor_id=actor_id, payload=payload or {}))
    except Exception:
        pass


async def _enrich(doc: dict, db) -> dict:
    m = _ser(doc)
    mid = m["id"]

    author_ids = m.get("authors") or []
    a_oids = [ObjectId(a) for a in author_ids if ObjectId.is_valid(a)]

    authors_raw, journal, project, workspace = await asyncio.gather(
        db.users.find({"_id": {"$in": a_oids}},
                      {"full_name": 1, "institution": 1, "avatar_url": 1,
                       "orcid": 1, "department": 1}).to_list(30),
        db.journals.find_one({"_id": ObjectId(m["target_journal_id"])}) if ObjectId.is_valid(m.get("target_journal_id", "")) else asyncio.sleep(0),
        db.projects.find_one({"_id": ObjectId(m["project_id"])}) if ObjectId.is_valid(m.get("project_id", "")) else asyncio.sleep(0),
        db.workspaces.find_one({"_id": ObjectId(m["workspace_id"])}, {"name": 1}) if ObjectId.is_valid(m.get("workspace_id", "")) else asyncio.sleep(0),
    )

    author_map = {str(u["_id"]): u for u in authors_raw}
    roles = m.get("author_roles") or {}
    m["authors_info"] = [
        {
            "id":           str(u["_id"]),
            "full_name":    u.get("full_name", ""),
            "institution":  u.get("institution", ""),
            "department":   u.get("department", ""),
            "avatar_url":   u.get("avatar_url"),
            "orcid_id":     (u.get("orcid") or {}).get("orcid_id"),
            "role":         roles.get(str(u["_id"]), "Co-Author"),
        }
        for uid in author_ids
        for u in [author_map.get(uid)]
        if u
    ]

    if journal and not isinstance(journal, type(None)):
        m["target_journal"] = {
            "id": str(journal["_id"]), "title": journal.get("title", ""),
            "publisher": journal.get("publisher", ""), "quartile": journal.get("quartile", ""),
            "impact_factor": journal.get("impact_factor"),
            "review_time_weeks": journal.get("review_time_weeks"),
            "acceptance_rate": journal.get("acceptance_rate"),
            "apc_usd": journal.get("apc_usd"),
        }

    if project and not isinstance(project, type(None)):
        m["project"] = {"id": str(project["_id"]), "title": project.get("title", "")}

    if workspace and not isinstance(workspace, type(None)):
        m["workspace"] = {"id": str(workspace["_id"]), "name": workspace.get("name", "")}

    return m


# ══════════════════════════════════════════════════════════════════════════════
# COMMENT RESOLVE — must be before /{manuscript_id} to avoid clash
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/comments/{comment_id}/resolve")
async def resolve_comment(comment_id: str, user: dict = Depends(get_current_user)):
    """Resolve a manuscript comment. Authors only."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(comment_id)
    except Exception:
        raise HTTPException(404, "Comment not found")
    comment = await db.manuscript_comments.find_one({"_id": oid})
    if not comment:
        raise HTTPException(404, "Comment not found")
    m = await db.manuscripts.find_one({"_id": ObjectId(comment["manuscript_id"])})
    if not m or user["id"] not in (m.get("authors") or []):
        raise HTTPException(403, "Forbidden")
    await db.manuscript_comments.update_one(
        {"_id": oid},
        {"$set": {"resolved": True, "resolved_by": user["id"], "resolved_at": _now()}},
    )
    return {"ok": True}


@router.patch("/review-requests/{rid}")
async def update_review_request(rid: str, body: dict, user: dict = Depends(get_current_user)):
    """Reviewer accepts/declines/completes a review request."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(rid)
    except Exception:
        raise HTTPException(404, "Not found")
    rr = await db.review_requests.find_one({"_id": oid})
    if not rr:
        raise HTTPException(404, "Not found")

    # Reviewer can accept/decline/complete; lead author can cancel
    is_reviewer = rr.get("reviewer_id") == user["id"]
    m = await db.manuscripts.find_one({"_id": ObjectId(rr["manuscript_id"])})
    is_author = m and user["id"] in (m.get("authors") or [])

    if not is_reviewer and not is_author:
        raise HTTPException(403, "Forbidden")

    update: dict = {"updated_at": _now()}
    if "status" in body:
        update["status"] = body["status"]
    if "verdict" in body:
        update["verdict"] = body["verdict"]
        update["verdict_comment"] = body.get("verdict_comment", "")
        update["completed_at"] = _now()

    await db.review_requests.update_one({"_id": oid}, {"$set": update})
    # Emit peer_review_completed when reviewer submits verdict
    if is_reviewer and update.get("verdict"):
        _emit_rep(user["id"], "peer_review_completed", rid)
    return _ser(await db.review_requests.find_one({"_id": oid}))


# ══════════════════════════════════════════════════════════════════════════════
# MANUSCRIPT CRUD
# ══════════════════════════════════════════════════════════════════════════════

@router.get("")
async def list_manuscripts(
    project_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    status: Optional[str] = None,
    manuscript_type: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    query: dict = {"authors": user["id"]}
    if project_id:
        query["project_id"] = project_id
    if workspace_id:
        query["workspace_id"] = workspace_id
    if status:
        query["status"] = status
    if manuscript_type:
        query["manuscript_type"] = manuscript_type

    docs = await db.manuscripts.find(query).sort("updated_at", -1).to_list(200)
    out = []
    journal_ids = list({d["target_journal_id"] for d in docs if d.get("target_journal_id") and ObjectId.is_valid(d["target_journal_id"])})
    j_oids = [ObjectId(j) for j in journal_ids]
    journals_raw = await db.journals.find({"_id": {"$in": j_oids}}, {"title": 1, "quartile": 1}).to_list(len(j_oids)) if j_oids else []
    j_map = {str(j["_id"]): j for j in journals_raw}

    for d in docs:
        x = _ser(d)
        jid = x.get("target_journal_id", "")
        if jid in j_map:
            j = j_map[jid]
            x["target_journal"] = {"id": str(j["_id"]), "title": j.get("title"), "quartile": j.get("quartile")}
        out.append(x)
    return out


@router.post("", status_code=201)
async def create_manuscript(payload: ManuscriptCreate, user: dict = Depends(get_current_user)):
    await assert_quota(user, "manuscripts")
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    now = _now()
    sections = dict(DEFAULT_SECTIONS)
    sections["title"]    = payload.title
    sections["abstract"] = payload.abstract or ""

    authors = [user["id"]]
    if payload.coauthors:
        for cid in payload.coauthors:
            if cid != user["id"] and cid not in authors:
                authors.append(cid)

    doc = {
        "title":                   payload.title.strip(),
        "abstract":                payload.abstract or "",
        "keywords":                payload.keywords or [],
        "manuscript_type":         payload.manuscript_type or "Journal Article",
        "project_id":              payload.project_id or "",
        "workspace_id":            payload.workspace_id or "",
        "target_journal_id":       payload.target_journal_id or "",
        "authors":                 authors,
        "lead_author_id":          user["id"],
        "corresponding_author_id": user["id"],
        "author_roles":            {user["id"]: "Lead Author"},
        "status":                  "draft",
        "sections":                sections,
        "current_version":         0,
        "doi":                     None,
        "submission_notes":        "",
        "acknowledgements":        "",
        "funding_statement":       "",
        "conflict_of_interest":    "",
        "status_history":          [{"status": "draft", "at": now, "by": user["id"]}],
        "created_at":              now,
        "updated_at":              now,
        "last_activity":           now,
    }
    res = await db.manuscripts.insert_one(doc)
    doc["_id"] = res.inserted_id
    mid = str(res.inserted_id)
    _emit_rep(user["id"], "manuscript_created", mid)
    return _ser(doc)


@router.get("/{manuscript_id}")
async def get_manuscript(manuscript_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(manuscript_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.manuscripts.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_author(doc, user["id"])
    return await _enrich(doc, db)


@router.patch("/{manuscript_id}")
async def update_manuscript(manuscript_id: str, payload: ManuscriptUpdate, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(manuscript_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.manuscripts.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_author(doc, user["id"])

    dump = payload.model_dump(exclude_unset=True)
    update: dict = {k: v for k, v in dump.items() if v is not None}

    # Status change — track history
    if "status" in update and update["status"] != doc.get("status"):
        new_status = update["status"]
        if new_status not in MANUSCRIPT_STATUSES:
            raise HTTPException(400, f"Invalid status: {new_status}")
        await db.manuscripts.update_one(
            {"_id": oid},
            {"$push": {"status_history": {"status": new_status, "at": _now(), "by": user["id"]}}},
        )
        if new_status == "submitted":
            _emit_rep(user["id"], "manuscript_submitted", manuscript_id)
        elif new_status == "published":
            _emit_rep(user["id"], "manuscript_published", manuscript_id)

    # Sync abstract to sections
    if "abstract" in update:
        update["sections.abstract"] = update.pop("abstract")

    if update:
        update["updated_at"] = _now()
        update["last_activity"] = _now()
        await db.manuscripts.update_one({"_id": oid}, {"$set": update})

    return _ser(await db.manuscripts.find_one({"_id": oid}))


@router.delete("/{manuscript_id}", status_code=204)
async def delete_manuscript(manuscript_id: str, user: dict = Depends(get_current_user)):
    """Hard-delete. Lead author only."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(manuscript_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.manuscripts.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_lead(doc, user["id"])

    await asyncio.gather(
        db.manuscript_versions.delete_many({"manuscript_id": manuscript_id}),
        db.manuscript_comments.delete_many({"manuscript_id": manuscript_id}),
        db.manuscript_contributions.delete_many({"manuscript_id": manuscript_id}),
        db.review_requests.delete_many({"manuscript_id": manuscript_id}),
        db.manuscript_references.delete_many({"manuscript_id": manuscript_id}),
        db.manuscripts.delete_one({"_id": oid}),
    )


# ══════════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/{manuscript_id}/dashboard")
async def manuscript_dashboard(manuscript_id: str, user: dict = Depends(get_current_user)):
    """Progress, readiness checklist, contributions, recent comments."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(manuscript_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.manuscripts.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_author(doc, user["id"])

    sections = doc.get("sections") or {}
    prog = _progress_pct(sections)

    version_count, open_comments, review_requests, contributions, refs_count = await asyncio.gather(
        db.manuscript_versions.count_documents({"manuscript_id": manuscript_id}),
        db.manuscript_comments.count_documents({"manuscript_id": manuscript_id, "resolved": {"$ne": True}}),
        db.review_requests.find({"manuscript_id": manuscript_id}).sort("created_at", -1).limit(10).to_list(10),
        db.manuscript_contributions.find({"manuscript_id": manuscript_id}).sort("edits", -1).limit(10).to_list(10),
        db.manuscript_references.count_documents({"manuscript_id": manuscript_id}),
    )

    # Readiness
    ready_for_submission = (
        bool((sections.get("title") or "").strip())
        and bool((sections.get("abstract") or "").strip())
        and len(doc.get("authors") or []) >= 1
        and bool(doc.get("target_journal_id"))
        and prog >= 80
        and bool(doc.get("corresponding_author_id"))
    )

    return {
        "progress_pct":          prog,
        "sections_filled":       sum(1 for k in SECTION_KEYS if sections.get(k, "").strip()),
        "sections_total":        len(SECTION_KEYS),
        "ready_for_submission":  ready_for_submission,
        "version_count":         version_count,
        "open_comments":         open_comments,
        "refs_count":            refs_count,
        "review_requests":       [_ser(r) for r in review_requests],
        "contributions":         [_ser(c) for c in contributions],
    }


# ══════════════════════════════════════════════════════════════════════════════
# AUTHORS
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/{manuscript_id}/authors")
async def add_author(manuscript_id: str, body: dict, user: dict = Depends(get_current_user)):
    """Add an author. Lead author only."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    new_id = body.get("user_id")
    if not new_id:
        raise HTTPException(400, "user_id required")
    try:
        oid = ObjectId(manuscript_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.manuscripts.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_lead(doc, user["id"])

    if new_id in (doc.get("authors") or []):
        raise HTTPException(409, "Already an author")
    try:
        target = await db.users.find_one({"_id": ObjectId(new_id)}, {"full_name": 1})
    except Exception:
        raise HTTPException(404, "User not found")
    if not target:
        raise HTTPException(404, "User not found")

    role = body.get("role", "Co-Author")
    if role not in AUTHOR_ROLES:
        role = "Co-Author"

    await db.manuscripts.update_one(
        {"_id": oid},
        {
            "$addToSet": {"authors": new_id},
            "$set": {f"author_roles.{new_id}": role, "updated_at": _now()},
        },
    )
    await _notify(
        user_id=new_id, kind="manuscript_author_added",
        title=f"You were added to a manuscript",
        body=f"{user.get('full_name','Someone')} added you to '{doc.get('title','')}' as {role}",
        link=f"/manuscripts/{manuscript_id}", actor_id=user["id"],
        payload={"manuscript_id": manuscript_id},
    )
    return {"ok": True, "user_id": new_id, "role": role}


@router.patch("/{manuscript_id}/authors")
async def update_authors(manuscript_id: str, body: dict, user: dict = Depends(get_current_user)):
    """Update author order and/or corresponding author. Lead author only."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(manuscript_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.manuscripts.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_lead(doc, user["id"])

    update: dict = {"updated_at": _now()}
    if "order" in body:
        new_order = body["order"]
        # Validate all IDs are existing authors
        existing = set(doc.get("authors") or [])
        if not all(uid in existing for uid in new_order):
            raise HTTPException(400, "Order contains unknown author IDs")
        update["authors"] = new_order
    if "corresponding_author_id" in body:
        cid = body["corresponding_author_id"]
        if cid not in (doc.get("authors") or []):
            raise HTTPException(400, "Corresponding author must be an existing author")
        update["corresponding_author_id"] = cid
        update[f"author_roles.{cid}"] = "Corresponding Author"

    await db.manuscripts.update_one({"_id": oid}, {"$set": update})
    return {"ok": True}


# ══════════════════════════════════════════════════════════════════════════════
# VERSION CONTROL
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/{manuscript_id}/versions")
async def list_versions(manuscript_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(manuscript_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.manuscripts.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_author(doc, user["id"])

    versions = await db.manuscript_versions.find(
        {"manuscript_id": manuscript_id}
    ).sort("version", -1).to_list(100)
    return [_ser(v) for v in versions]


@router.post("/{manuscript_id}/versions")
async def create_version(manuscript_id: str, body: dict, user: dict = Depends(get_current_user)):
    """Snapshot the current manuscript state as a new version."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(manuscript_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.manuscripts.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_author(doc, user["id"])

    current_version = doc.get("current_version", 0) + 1
    now = _now()
    version_doc = {
        "manuscript_id": manuscript_id,
        "version":       current_version,
        "summary":       (body.get("summary") or "").strip()[:500],
        "author_id":     user["id"],
        "author_name":   user.get("full_name", "Someone"),
        "sections":      doc.get("sections") or {},
        "status":        doc.get("status", "draft"),
        "created_at":    now,
    }
    res = await db.manuscript_versions.insert_one(version_doc)
    await db.manuscripts.update_one(
        {"_id": oid},
        {"$set": {"current_version": current_version, "updated_at": now}},
    )
    version_doc["_id"] = res.inserted_id
    return _ser(version_doc)


@router.post("/{manuscript_id}/versions/{version_number}/restore")
async def restore_version(manuscript_id: str, version_number: int, user: dict = Depends(get_current_user)):
    """Restore a prior version. Auto-snapshots current state first."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(manuscript_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.manuscripts.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_author(doc, user["id"])

    target = await db.manuscript_versions.find_one({
        "manuscript_id": manuscript_id, "version": version_number,
    })
    if not target:
        raise HTTPException(404, f"Version {version_number} not found")

    now = _now()
    current_version = doc.get("current_version", 0) + 1

    # Snapshot current state before overwriting
    await db.manuscript_versions.insert_one({
        "manuscript_id": manuscript_id,
        "version":       current_version,
        "summary":       f"Auto-snapshot before restore to v{version_number}",
        "author_id":     user["id"],
        "author_name":   user.get("full_name", "Someone"),
        "sections":      doc.get("sections") or {},
        "status":        doc.get("status", "draft"),
        "created_at":    now,
    })

    # Restore the target sections
    await db.manuscripts.update_one(
        {"_id": oid},
        {"$set": {
            "sections":        target.get("sections") or {},
            "current_version": current_version,
            "updated_at":      now,
            "last_activity":   now,
        }},
    )
    return {"ok": True, "restored_to": version_number, "new_version": current_version}


# ══════════════════════════════════════════════════════════════════════════════
# COMMENTS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/{manuscript_id}/comments")
async def list_comments(
    manuscript_id: str,
    section: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(manuscript_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.manuscripts.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_author(doc, user["id"])

    q: dict = {"manuscript_id": manuscript_id}
    if section:
        q["section"] = section
    comments = await db.manuscript_comments.find(q).sort("created_at", -1).to_list(200)
    return [_ser(c) for c in comments]


@router.post("/{manuscript_id}/comments")
async def add_comment(manuscript_id: str, body: dict, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(manuscript_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.manuscripts.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_author(doc, user["id"])

    text = (body.get("body") or "").strip()
    if not text:
        raise HTTPException(400, "body is required")

    now = _now()
    comment_doc = {
        "manuscript_id": manuscript_id,
        "section":       body.get("section", ""),
        "anchor":        body.get("anchor", ""),
        "body":          text,
        "author_id":     user["id"],
        "author_name":   user.get("full_name", "Someone"),
        "resolved":      False,
        "created_at":    now,
    }
    res = await db.manuscript_comments.insert_one(comment_doc)
    await db.manuscripts.update_one({"_id": oid}, {"$set": {"last_activity": now}})
    comment_doc["_id"] = res.inserted_id
    return _ser(comment_doc)


# ══════════════════════════════════════════════════════════════════════════════
# PEER REVIEW REQUESTS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/{manuscript_id}/review-requests")
async def list_review_requests(manuscript_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(manuscript_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.manuscripts.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_author(doc, user["id"])

    rrs = await db.review_requests.find(
        {"manuscript_id": manuscript_id}
    ).sort("created_at", -1).to_list(50)

    # Enrich with reviewer profiles
    reviewer_ids = [ObjectId(r["reviewer_id"]) for r in rrs if ObjectId.is_valid(r.get("reviewer_id", ""))]
    reviewers_raw = await db.users.find({"_id": {"$in": reviewer_ids}},
                                        {"full_name": 1, "institution": 1, "avatar_url": 1}).to_list(50)
    rev_map = {str(u["_id"]): u for u in reviewers_raw}

    out = []
    for rr in rrs:
        item = _ser(rr)
        rv = rev_map.get(rr.get("reviewer_id", ""))
        if rv:
            item["reviewer"] = {
                "id": str(rv["_id"]), "full_name": rv.get("full_name", ""),
                "institution": rv.get("institution", ""), "avatar_url": rv.get("avatar_url"),
            }
        out.append(item)
    return out


@router.post("/{manuscript_id}/review-requests")
async def create_review_request(manuscript_id: str, body: dict, user: dict = Depends(get_current_user)):
    """Assign a peer reviewer. Any author can invite."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(manuscript_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.manuscripts.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_author(doc, user["id"])

    reviewer_id = body.get("reviewer_id")
    if not reviewer_id:
        raise HTTPException(400, "reviewer_id required")
    if reviewer_id in (doc.get("authors") or []):
        raise HTTPException(400, "Authors cannot be assigned as reviewers")

    # Check target user exists
    try:
        target = await db.users.find_one({"_id": ObjectId(reviewer_id)}, {"full_name": 1})
    except Exception:
        raise HTTPException(404, "User not found")
    if not target:
        raise HTTPException(404, "Reviewer not found")

    # Prevent duplicate pending
    existing = await db.review_requests.find_one({
        "manuscript_id": manuscript_id, "reviewer_id": reviewer_id, "status": "pending",
    })
    if existing:
        raise HTTPException(409, "A pending review request already exists for this reviewer")

    now = _now()
    rr_doc = {
        "manuscript_id": manuscript_id,
        "reviewer_id":   reviewer_id,
        "assigned_by":   user["id"],
        "section":       body.get("section", ""),
        "note":          body.get("note", ""),
        "status":        "pending",
        "verdict":       None,
        "verdict_comment": "",
        "created_at":    now,
        "updated_at":    now,
    }
    res = await db.review_requests.insert_one(rr_doc)

    await _notify(
        user_id=reviewer_id, kind="manuscript_review_request",
        title=f"Review request for '{doc.get('title','a manuscript')}'",
        body=f"{user.get('full_name','Someone')} invited you to review a manuscript",
        link=f"/manuscripts/{manuscript_id}", actor_id=user["id"],
        payload={"manuscript_id": manuscript_id, "request_id": str(res.inserted_id)},
    )

    rr_doc["_id"] = res.inserted_id
    return _ser(rr_doc)


# ══════════════════════════════════════════════════════════════════════════════
# CONTRIBUTIONS
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/{manuscript_id}/contributions")
async def log_contribution(manuscript_id: str, body: dict, user: dict = Depends(get_current_user)):
    """Upsert-increment a contribution record for the calling author."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(manuscript_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.manuscripts.find_one({"_id": oid}, {"authors": 1})
    if not doc or user["id"] not in (doc.get("authors") or []):
        raise HTTPException(403, "Forbidden")

    section    = body.get("section", "general")
    char_delta = int(body.get("char_delta", 0))
    now = _now()

    await db.manuscript_contributions.update_one(
        {"manuscript_id": manuscript_id, "user_id": user["id"], "section": section},
        {
            "$inc":  {"char_delta": char_delta, "edits": 1},
            "$set":  {"user_name": user.get("full_name", ""), "last_edit_at": now},
            "$setOnInsert": {"manuscript_id": manuscript_id, "user_id": user["id"],
                             "section": section, "created_at": now},
        },
        upsert=True,
    )
    return {"ok": True}


# ══════════════════════════════════════════════════════════════════════════════
# REFERENCES (citation manager)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/{manuscript_id}/references")
async def list_references(manuscript_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(manuscript_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.manuscripts.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_author(doc, user["id"])
    refs = await db.manuscript_references.find(
        {"manuscript_id": manuscript_id}
    ).sort("created_at", 1).to_list(500)
    return [_ser(r) for r in refs]


@router.post("/{manuscript_id}/references", status_code=201)
async def add_reference(manuscript_id: str, body: dict, user: dict = Depends(get_current_user)):
    """Add a citation. Deduplicates by DOI."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(manuscript_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.manuscripts.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_author(doc, user["id"])

    doi = (body.get("doi") or "").strip().lower()
    if doi:
        existing = await db.manuscript_references.find_one({
            "manuscript_id": manuscript_id, "doi": doi,
        })
        if existing:
            raise HTTPException(409, "Reference with this DOI already added")

    now = _now()
    ref_doc = {
        "manuscript_id": manuscript_id,
        "doi":           doi or None,
        "title":         body.get("title", ""),
        "authors":       body.get("authors", ""),
        "journal":       body.get("journal", ""),
        "year":          body.get("year"),
        "volume":        body.get("volume"),
        "issue":         body.get("issue"),
        "pages":         body.get("pages"),
        "url":           body.get("url", ""),
        "openalex_id":   body.get("openalex_id"),
        "added_by":      user["id"],
        "created_at":    now,
    }
    res = await db.manuscript_references.insert_one(ref_doc)
    ref_doc["_id"] = res.inserted_id
    return _ser(ref_doc)


@router.delete("/{manuscript_id}/references/{ref_id}", status_code=204)
async def delete_reference(manuscript_id: str, ref_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        m_oid = ObjectId(manuscript_id)
        r_oid = ObjectId(ref_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.manuscripts.find_one({"_id": m_oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_author(doc, user["id"])
    await db.manuscript_references.delete_one({"_id": r_oid, "manuscript_id": manuscript_id})


# ══════════════════════════════════════════════════════════════════════════════
# JOURNAL AI RECOMMENDATIONS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/{manuscript_id}/journal-matches")
async def journal_matches(
    manuscript_id: str,
    limit: int = Query(default=10, ge=1, le=20),
    user: dict = Depends(get_current_user),
):
    """Score all journals against this manuscript's keywords/abstract/type."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(manuscript_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.manuscripts.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_author(doc, user["id"])

    keywords = {k.lower() for k in (doc.get("keywords") or [])}
    abstract  = (doc.get("abstract") or doc.get("sections", {}).get("abstract", "")).lower()
    ms_type   = doc.get("manuscript_type", "").lower()
    area_words = set(abstract.split()) if abstract else set()

    journals_raw = await db.journals.find({}).limit(200).to_list(200)

    def _score(j: dict) -> int:
        score = 0
        # Keyword overlap with journal subject areas
        j_areas = {a.lower() for a in (j.get("research_areas") or j.get("subject_areas") or [])}
        j_kw    = {k.lower() for k in (j.get("keywords") or [])}
        score  += len(keywords & j_areas) * 10
        score  += len(keywords & j_kw) * 8
        # Title word match
        j_title = j.get("title", "").lower()
        score  += sum(2 for w in keywords if w in j_title)
        # Abstract word match (rough)
        score  += min(20, sum(1 for w in area_words if len(w) > 4 and w in j_title))
        # Quartile bonus
        q = (j.get("quartile") or "").upper()
        score += {"Q1": 15, "Q2": 10, "Q3": 5, "Q4": 2}.get(q, 0)
        # h-index / impact factor
        if j.get("impact_factor"):
            score += min(10, int(j["impact_factor"]))
        return score

    scored = sorted(journals_raw, key=_score, reverse=True)[:limit]
    out = []
    for j in scored:
        item = {
            "id":               str(j["_id"]),
            "title":            j.get("title", ""),
            "publisher":        j.get("publisher", ""),
            "quartile":         j.get("quartile"),
            "impact_factor":    j.get("impact_factor"),
            "review_time_weeks": j.get("review_time_weeks"),
            "acceptance_rate":  j.get("acceptance_rate"),
            "apc_usd":          j.get("apc_usd"),
            "match_score":      _score(j),
            "match_reason":     _match_reason(j, keywords, q=(j.get("quartile") or "").upper()),
        }
        out.append(item)
    return out


def _match_reason(j: dict, keywords: set, q: str) -> str:
    j_areas = {a.lower() for a in (j.get("research_areas") or [])}
    overlap = list(keywords & j_areas)[:3]
    if overlap:
        return f"Shared areas: {', '.join(overlap)}"
    if q in ("Q1", "Q2"):
        return f"{q} journal — high impact"
    return "Ranked by journal scope alignment"


# ══════════════════════════════════════════════════════════════════════════════
# ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/{manuscript_id}/analytics")
async def manuscript_analytics(manuscript_id: str, user: dict = Depends(get_current_user)):
    """Submission timeline, review cycles, revision history."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(manuscript_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.manuscripts.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_author(doc, user["id"])

    submissions, reviews, versions, contributions = await asyncio.gather(
        db.submissions.find({"manuscript_id": manuscript_id}).sort("created_at", 1).to_list(50),
        db.review_requests.find({"manuscript_id": manuscript_id}).to_list(50),
        db.manuscript_versions.count_documents({"manuscript_id": manuscript_id}),
        db.manuscript_contributions.find({"manuscript_id": manuscript_id}).to_list(20),
    )

    # Status timeline from status_history
    status_history = doc.get("status_history") or []

    return {
        "manuscript_id":    manuscript_id,
        "status_history":   status_history,
        "submission_count": len(submissions),
        "submissions":      [_ser(s) for s in submissions],
        "review_count":     len(reviews),
        "reviews":          [_ser(r) for r in reviews],
        "version_count":    versions,
        "contributions":    [_ser(c) for c in contributions],
        "days_in_draft":    _days_in_status(status_history, "draft"),
        "days_in_review":   _days_in_status(status_history, "under_review"),
    }


def _days_in_status(history: list, status: str) -> Optional[int]:
    entered = exited = None
    for h in history:
        if h.get("status") == status and not entered:
            entered = h.get("at")
        elif entered and h.get("status") != status:
            exited = h.get("at")
    if not entered:
        return None
    end = exited or _now()
    try:
        dt_in  = datetime.fromisoformat(entered.replace("Z", "+00:00"))
        dt_out = datetime.fromisoformat(end.replace("Z", "+00:00"))
        return max(0, (dt_out - dt_in).days)
    except Exception:
        return None
