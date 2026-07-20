import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends, Query

from auth_utils import get_current_user
from db import get_db
from models import CollaborationCreate, ApplicationCreate, ApplicationDecision
from repo.shim import DBProxy
from repo.security_context import SecurityContext

logger = logging.getLogger("synaptiq.collaborations")

def _emit_rep(user_id, event_type, entity_id, description=None):
    async def _task():
        try:
            from services.reputation.events import emit_reputation_event
            await emit_reputation_event(user_id, event_type, "collaboration", entity_id, description)
        except Exception:
            pass
    try:
        asyncio.ensure_future(_task())
    except RuntimeError:
        pass
router = APIRouter(prefix="/api/collaborations", tags=["collaborations"])


def _serialize(doc: dict) -> dict:
    if not doc:
        return None
    d = dict(doc)
    d["id"] = str(d.pop("_id"))
    return d


async def _enrich(doc: dict):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    creator = await db.users.find_one({"_id": ObjectId(doc["creator_id"])})
    if creator:
        doc["creator"] = {
            "id": str(creator["_id"]),
            "full_name": creator.get("full_name", ""),
            "institution": creator.get("institution", ""),
            "avatar_url": creator.get("avatar_url", ""),
        }
    return doc


@router.get("")
async def list_collaborations(
    q: Optional[str] = None,
    collab_type: Optional[str] = None,
    research_area: Optional[str] = None,
    status: str = "open",
    limit: int = 50,
    _user: dict = Depends(get_current_user),
):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    query: dict = {"is_demo": {"$ne": True}}
    if status != "all":
        query["status"] = status
    if q:
        query["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
        ]
    if collab_type:
        query["collab_type"] = collab_type
    if research_area:
        query["research_area"] = research_area
    docs = await db.collaborations.find(query).sort("created_at", -1).limit(limit).to_list(limit)
    serialized = [_serialize(d) for d in docs]

    # Batch-fetch creator profiles to avoid N+1 (one query for all creators)
    creator_ids = list({ObjectId(d["creator_id"]) for d in serialized if d.get("creator_id")})
    creators_by_id: dict = {}
    if creator_ids:
        creator_docs = await db.users.find(
            {"_id": {"$in": creator_ids}},
            {"full_name": 1, "institution": 1, "avatar_url": 1},
        ).to_list(len(creator_ids))
        creators_by_id = {str(d["_id"]): d for d in creator_docs}

    for item in serialized:
        creator = creators_by_id.get(item.get("creator_id"))
        if creator:
            item["creator"] = {
                "id": str(creator["_id"]),
                "full_name": creator.get("full_name", ""),
                "institution": creator.get("institution", ""),
                "avatar_url": creator.get("avatar_url", ""),
            }
    return serialized


@router.post("")
async def create_collaboration(payload: CollaborationCreate, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    doc = payload.model_dump()
    doc.update({
        "creator_id": user["id"],
        "status": "open",
        "members": [user["id"]],
        "applications_count": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    result = await db.collaborations.insert_one(doc)
    # auto-create project
    project_doc = {
        "title": payload.title,
        "description": payload.description,
        "visibility": "team",
        "owner_id": user["id"],
        "members": [user["id"]],
        "collaboration_id": str(result.inserted_id),
        "problem_statement": "",
        "research_gap": "",
        "objectives": [],
        "research_questions": [],
        "hypotheses": [],
        "expected_contributions": "",
        "methodology": "",
        "data_sources": "",
        "sampling": "",
        "analysis_methods": "",
        "ethics": "",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    project = await db.projects.insert_one(project_doc)
    await db.collaborations.update_one(
        {"_id": result.inserted_id}, {"$set": {"project_id": str(project.inserted_id)}}
    )
    doc["_id"] = result.inserted_id
    doc["project_id"] = str(project.inserted_id)
    collab_id = str(result.inserted_id)
    _emit_rep(user["id"], "collaboration_created", collab_id)
    return await _enrich(_serialize(doc))


@router.get("/mine")
async def my_collaborations(user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    # Created by me OR I'm a member — exclude demo records
    docs = await db.collaborations.find(
        {"$or": [{"creator_id": user["id"]}, {"members": user["id"]}], "is_demo": {"$ne": True}}
    ).sort("created_at", -1).to_list(200)
    serialized_docs = [_serialize(d) for d in docs]

    # Pending applications by me — fetch collab ids in one query
    apps = await db.applications.find({"applicant_id": user["id"], "status": "pending"}).to_list(200)
    pending_collab_ids = [ObjectId(a["collaboration_id"]) for a in apps if a.get("collaboration_id")]
    pending_collabs_raw = []
    if pending_collab_ids:
        pending_collabs_raw = await db.collaborations.find(
            {"_id": {"$in": pending_collab_ids}, "is_demo": {"$ne": True}}
        ).to_list(len(pending_collab_ids))

    # Batch-fetch all unique creator profiles for both sets
    all_collab_docs = serialized_docs + [_serialize(d) for d in pending_collabs_raw]
    creator_ids = list({ObjectId(d["creator_id"]) for d in all_collab_docs if d.get("creator_id")})
    creators_by_id: dict = {}
    if creator_ids:
        creator_docs = await db.users.find(
            {"_id": {"$in": creator_ids}},
            {"full_name": 1, "institution": 1, "avatar_url": 1},
        ).to_list(len(creator_ids))
        creators_by_id = {str(d["_id"]): d for d in creator_docs}

    def _attach_creator(item: dict) -> dict:
        creator = creators_by_id.get(item.get("creator_id"))
        if creator:
            item["creator"] = {
                "id": str(creator["_id"]),
                "full_name": creator.get("full_name", ""),
                "institution": creator.get("institution", ""),
                "avatar_url": creator.get("avatar_url", ""),
            }
        return item

    items = [_attach_creator(d) for d in serialized_docs]
    pending = [
        {**_attach_creator(_serialize(c)), "application_status": "pending"}
        for c in pending_collabs_raw
    ]
    return {"active": [i for i in items if i.get("status") in ("open", "active")],
            "completed": [i for i in items if i.get("status") == "completed"],
            "pending": pending}


@router.get("/{collab_id}")
async def get_collaboration(collab_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        doc = await db.collaborations.find_one({"_id": ObjectId(collab_id)})
    except Exception:
        raise HTTPException(status_code=404, detail="Not found")
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    # Open collaborations are publicly discoverable by any authenticated user.
    # Closed, active, or completed collaborations are restricted to the creator and members.
    if doc.get("status") != "open":
        uid = user["id"]
        if uid != doc.get("creator_id") and uid not in doc.get("members", []):
            raise HTTPException(status_code=403, detail="Forbidden")
    return await _enrich(_serialize(doc))


@router.post("/{collab_id}/apply")
async def apply(collab_id: str, payload: ApplicationCreate, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(collab_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Not found")
    collab = await db.collaborations.find_one({"_id": oid})
    if not collab:
        raise HTTPException(status_code=404, detail="Not found")
    if collab["creator_id"] == user["id"]:
        raise HTTPException(status_code=400, detail="Cannot apply to your own collaboration")
    existing = await db.applications.find_one({"collaboration_id": collab_id, "applicant_id": user["id"]})
    if existing:
        raise HTTPException(status_code=400, detail="Already applied")
    app_doc = {
        "collaboration_id": collab_id,
        "applicant_id": user["id"],
        "message": payload.message,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.applications.insert_one(app_doc)
    await db.collaborations.update_one({"_id": oid}, {"$inc": {"applications_count": 1}})
    # Notification
    await db.notifications.insert_one({
        "user_id": collab["creator_id"],
        "type": "application",
        "title": "New application",
        "body": f"{user.get('full_name','Someone')} applied to '{collab['title']}'",
        "link": f"/collaborations/{collab_id}",
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    # Email trigger (dry-run-safe)
    try:
        from services.email_service import send_collaboration_invitation
        await send_collaboration_invitation(
            recipient_user_id=collab["creator_id"], collaboration_id=collab_id,
            collaboration_title=collab["title"], inviter_name=user.get("full_name","Someone"),
            kind="application", message=payload.message or "")
    except Exception as _email_exc:
        logger.warning("collaboration application email failed collab=%s err=%s",
                       collab_id, _email_exc)
    return {"ok": True}


@router.get("/{collab_id}/applications")
async def list_applications(collab_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(collab_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Not found")
    collab = await db.collaborations.find_one({"_id": oid})
    if not collab:
        raise HTTPException(status_code=404, detail="Not found")
    if collab["creator_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    apps = await db.applications.find({"collaboration_id": collab_id}).to_list(100)

    # Batch-fetch applicant profiles to avoid N+1
    applicant_ids = list({ObjectId(a["applicant_id"]) for a in apps if a.get("applicant_id")})
    applicants_by_id: dict = {}
    if applicant_ids:
        applicant_docs = await db.users.find(
            {"_id": {"$in": applicant_ids}},
            {"full_name": 1, "institution": 1, "academic_role": 1, "user_type": 1, "primary_domain": 1, "research_areas": 1, "avatar_url": 1},
        ).to_list(len(applicant_ids))
        applicants_by_id = {str(d["_id"]): d for d in applicant_docs}

    out = []
    for a in apps:
        applicant = applicants_by_id.get(a.get("applicant_id"))
        out.append({
            "id": str(a["_id"]),
            "message": a["message"],
            "status": a["status"],
            "created_at": a["created_at"],
            "applicant": {
                "id":             str(applicant["_id"]),
                "full_name":      applicant.get("full_name", ""),
                "institution":    applicant.get("institution", ""),
                "academic_role":  applicant.get("academic_role", ""),
                "user_type":      applicant.get("user_type"),
                "primary_domain": applicant.get("primary_domain"),
                "research_areas": applicant.get("research_areas", []),
                "avatar_url":     applicant.get("avatar_url", ""),
            } if applicant else None,
        })
    return out


@router.post("/applications/{app_id}/decide")
async def decide_application(app_id: str, payload: ApplicationDecision, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(app_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Not found")
    app = await db.applications.find_one({"_id": oid})
    if not app:
        raise HTTPException(status_code=404, detail="Not found")
    collab = await db.collaborations.find_one({"_id": ObjectId(app["collaboration_id"])})
    if not collab or collab["creator_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    if payload.decision not in ("accepted", "rejected"):
        raise HTTPException(status_code=400, detail="Invalid decision")
    if app.get("status") != "pending":
        raise HTTPException(status_code=409, detail=f"Application already {app['status']}.")
    await db.applications.update_one({"_id": oid}, {"$set": {"status": payload.decision}})
    if payload.decision == "accepted":
        await db.collaborations.update_one(
            {"_id": ObjectId(app["collaboration_id"])},
            {"$addToSet": {"members": app["applicant_id"]}},
        )
        if collab.get("project_id"):
            await db.projects.update_one(
                {"_id": ObjectId(collab["project_id"])},
                {"$addToSet": {"members": app["applicant_id"]}},
            )
        # Award reputation to the applicant who was accepted
        _emit_rep(app["applicant_id"], "collaboration_accepted", app["collaboration_id"])
    # Notify applicant
    await db.notifications.insert_one({
        "user_id": app["applicant_id"],
        "type": "application_decision",
        "title": f"Application {payload.decision}",
        "body": f"Your application to '{collab['title']}' was {payload.decision}",
        "link": f"/collaborations/{app['collaboration_id']}",
        "read": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    # Email trigger (dry-run-safe)
    try:
        from services.email_service import send_collaboration_invitation
        await send_collaboration_invitation(
            recipient_user_id=app["applicant_id"],
            collaboration_id=app["collaboration_id"],
            collaboration_title=collab["title"],
            inviter_name=user.get("full_name",""),
            kind="decision", message=f"Status: {payload.decision}")
    except Exception as _email_exc:
        logger.warning("collaboration decision email failed app=%s err=%s",
                       app_id, _email_exc)
    return {"ok": True}
