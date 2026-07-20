"""Research Meetings — full production router.

Collections:
  meetings                core documents (research/supervision/project/grant/etc.)
  meeting_action_items    action items linked to a meeting (mirrors workspace_tasks)
  meeting_notes           discussion/notes feed per meeting (mirrors workspace_activity)
  meeting_ai_summaries    generated AI summaries + extracted action items/decisions

Reuses existing collections rather than inventing new ones:
  conversations / conversation_members   meeting chat thread (context_key = "meeting:{id}")
  repository_items                       meeting file attachments (filtered by meeting_id)
  notifications (via services.notifications_service.dispatch)   reminders/invites
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from db import get_db
from models import MeetingCreate, MeetingUpdate, ActionItemCreate, ActionItemUpdate, MeetingNoteCreate
from repo.shim import DBProxy
from repo.security_context import SecurityContext
from services.ai.llm import call_llm

log = logging.getLogger("synaptiq.meetings")
router = APIRouter(prefix="/api/meetings", tags=["meetings"])

# ── constants ──────────────────────────────────────────────────────────────────

MEETING_TYPES = [
    "Research Meeting", "PhD Supervision", "Project Meeting", "Grant Meeting",
    "Peer Review Meeting", "Institution Meeting", "Conference Preparation",
    "Journal Submission Meeting",
]

RECURRENCE_RULES = {"none", "daily", "weekly", "biweekly", "monthly"}
MAX_RECURRING_INSTANCES = 12

ACTION_ITEM_PRIORITIES = {"low", "medium", "high"}
ACTION_ITEM_STATUSES = {"open", "in_progress", "done"}

AI_KINDS = {
    "agenda", "summary", "action-items", "decisions",
    "follow-up-email", "next-steps", "manuscript-todo", "grant-follow-up",
}

# ── helpers ────────────────────────────────────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ser(d):
    if not d:
        return None
    x = dict(d)
    x["id"] = str(x.pop("_id"))
    return x


def _oid(id_str: str, what: str = "Not found"):
    try:
        return ObjectId(id_str)
    except Exception:
        raise HTTPException(404, what)


def _is_participant(doc: dict, user_id: str) -> bool:
    return user_id == doc.get("owner_id") or user_id in (doc.get("participant_ids") or [])


def _assert_participant(doc: dict, user_id: str) -> None:
    if not _is_participant(doc, user_id):
        raise HTTPException(403, "Not a participant in this meeting")


def _assert_owner(doc: dict, user_id: str) -> None:
    if doc.get("owner_id") != user_id:
        raise HTTPException(403, "Only the meeting owner can do this")


async def _log_note(db, meeting_id: str, actor_id: str, actor_name: str, message: str, kind: str = "system") -> None:
    try:
        await db.meeting_notes.insert_one({
            "meeting_id": meeting_id,
            "actor_id":   actor_id,
            "actor_name": actor_name,
            "body":       message,
            "kind":       kind,
            "created_at": _now(),
        })
    except Exception as exc:
        log.warning("meeting note insert failed: %s", exc)


async def _notify(user_id: str, kind: str, title: str, body: str, link: str, actor_id: str, payload: dict) -> None:
    try:
        from services.notifications_service import dispatch as _d, NotificationEvent as _NE
        await _d(_NE(user_id=user_id, kind=kind, title=title, body=body,
                     link=link, actor_id=actor_id, payload=payload))
    except Exception:
        pass


async def _enrich(doc: dict, db) -> dict:
    m = _ser(doc)
    m_id = m["id"]
    part_ids = m.get("participant_ids") or []
    part_oids = [ObjectId(p) for p in part_ids if ObjectId.is_valid(p)]

    parts_raw, notes_raw, items_raw, files_raw, summary_raw, ws_raw, proj_raw = await asyncio.gather(
        db.users.find({"_id": {"$in": part_oids}},
                      {"full_name": 1, "academic_role": 1, "institution": 1, "avatar_url": 1}).to_list(50) if part_oids else asyncio.sleep(0),
        db.meeting_notes.find({"meeting_id": m_id}).sort("created_at", -1).limit(50).to_list(50),
        db.meeting_action_items.find({"meeting_id": m_id}).sort("created_at", -1).to_list(100),
        db.repository_items.find({"meeting_id": m_id}).sort("created_at", -1).to_list(50),
        db.meeting_ai_summaries.find({"meeting_id": m_id}).sort("generated_at", -1).limit(1).to_list(1),
        db.workspaces.find_one({"_id": ObjectId(m["workspace_id"])}, {"name": 1}) if m.get("workspace_id") and ObjectId.is_valid(m.get("workspace_id", "")) else asyncio.sleep(0),
        db.projects.find_one({"_id": ObjectId(m["project_id"])}, {"title": 1, "name": 1}) if m.get("project_id") and ObjectId.is_valid(m.get("project_id", "")) else asyncio.sleep(0),
    )

    m["participants"] = [
        {
            "id": str(p["_id"]), "full_name": p.get("full_name", ""),
            "academic_role": p.get("academic_role", ""), "institution": p.get("institution", ""),
            "avatar_url": p.get("avatar_url"),
        }
        for p in (parts_raw or [])
    ]
    m["notes"] = [_ser(n) for n in notes_raw]
    m["action_items"] = [_ser(i) for i in items_raw]
    m["files"] = [_ser(f) for f in files_raw]
    m["ai_summary"] = _ser(summary_raw[0]) if summary_raw else None
    m["workspace_name"] = (ws_raw or {}).get("name") if ws_raw else None
    m["project_title"] = (proj_raw or {}).get("title") or (proj_raw or {}).get("name") if proj_raw else None
    return m


def _recurrence_dates(start_at: str, end_at: str, rule: str, count: int) -> list[tuple[str, str]]:
    try:
        start_dt = datetime.fromisoformat(start_at)
        end_dt = datetime.fromisoformat(end_at)
    except Exception:
        return []
    step = {
        "daily": timedelta(days=1),
        "weekly": timedelta(weeks=1),
        "biweekly": timedelta(weeks=2),
        "monthly": timedelta(days=30),
    }.get(rule)
    if not step:
        return []
    out = []
    for i in range(1, count + 1):
        out.append(((start_dt + step * i).isoformat(), (end_dt + step * i).isoformat()))
    return out


# ── pydantic bodies ────────────────────────────────────────────────────────────

class AIRequestBody(BaseModel):
    instructions: Optional[str] = Field(None, max_length=1000)


# ══════════════════════════════════════════════════════════════════════════════
# STATIC ROUTES — must be registered before /{meeting_id} to avoid path clashes
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/kpis")
async def meeting_kpis(user: dict = Depends(get_current_user)):
    """4 top-line KPI numbers with trend deltas vs the prior 7-day period."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    week_ago = now - timedelta(days=7)
    two_weeks_ago = now - timedelta(days=14)

    base = {"$or": [{"owner_id": uid}, {"participant_ids": uid}]}

    (upcoming, today_count, pending_items, ai_summaries,
     upcoming_prev, ai_summaries_prev) = await asyncio.gather(
        db.meetings.count_documents({**base, "start_at": {"$gte": now.isoformat()}, "status": {"$ne": "cancelled"}}),
        db.meetings.count_documents({**base, "start_at": {"$gte": today_start.isoformat(), "$lt": today_end.isoformat()}, "status": {"$ne": "cancelled"}}),
        db.meeting_action_items.count_documents({"owner_id": uid, "status": {"$ne": "done"}}),
        db.meeting_ai_summaries.count_documents({"generated_by": uid}),
        db.meetings.count_documents({**base, "start_at": {"$gte": week_ago.isoformat(), "$lt": now.isoformat()}}),
        db.meeting_ai_summaries.count_documents({"generated_by": uid, "generated_at": {"$gte": two_weeks_ago.isoformat(), "$lt": week_ago.isoformat()}}),
    )

    def _trend(curr, prev):
        if not prev:
            return None
        return round(((curr - prev) / prev) * 100)

    return {
        "upcoming_meetings":       upcoming,
        "todays_meetings":         today_count,
        "pending_action_items":    pending_items,
        "ai_summaries_generated":  ai_summaries,
        "trends": {
            "upcoming_meetings":      _trend(upcoming, upcoming_prev),
            "ai_summaries_generated": _trend(ai_summaries, ai_summaries_prev),
        },
    }


@router.get("/categories")
async def meeting_categories(user: dict = Depends(get_current_user)):
    """Per-type scheduled count + next occurrence, for the 8 category cards."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    now_iso = datetime.now(timezone.utc).isoformat()
    base = {"$or": [{"owner_id": uid}, {"participant_ids": uid}]}

    async def _one(mtype: str):
        q = {**base, "meeting_type": mtype, "status": {"$ne": "cancelled"}}
        count, next_doc = await asyncio.gather(
            db.meetings.count_documents({**q, "start_at": {"$gte": now_iso}}),
            db.meetings.find_one({**q, "start_at": {"$gte": now_iso}}, sort=[("start_at", 1)]),
        )
        return {
            "meeting_type": mtype,
            "scheduled_count": count,
            "next_occurrence": _ser(next_doc),
        }

    results = await asyncio.gather(*[_one(t) for t in MEETING_TYPES])
    return results


@router.get("/calendar")
async def meeting_calendar(
    month: Optional[str] = Query(None, description="YYYY-MM"),
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    user: dict = Depends(get_current_user),
):
    """Meetings within a month or explicit range, for the month-grid/agenda view."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    if month:
        try:
            year, mon = int(month[:4]), int(month[5:7])
        except Exception:
            raise HTTPException(400, "month must be YYYY-MM")
        start = datetime(year, mon, 1, tzinfo=timezone.utc)
        end = datetime(year + 1, 1, 1, tzinfo=timezone.utc) if mon == 12 else datetime(year, mon + 1, 1, tzinfo=timezone.utc)
        range_start, range_end = start.isoformat(), end.isoformat()
    elif from_date and to_date:
        range_start, range_end = from_date, to_date
    else:
        now = datetime.now(timezone.utc)
        range_start = now.replace(day=1).isoformat()
        range_end = (now.replace(day=1) + timedelta(days=32)).replace(day=1).isoformat()

    uid = user["id"]
    q = {
        "$or": [{"owner_id": uid}, {"participant_ids": uid}],
        "start_at": {"$gte": range_start, "$lt": range_end},
    }
    docs = await db.meetings.find(q).sort("start_at", 1).to_list(500)
    return {"range": {"from": range_start, "to": range_end}, "meetings": [_ser(d) for d in docs]}


@router.get("/action-items")
async def list_action_items(
    status: Optional[str] = None,
    priority: Optional[str] = None,
    project_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """Standalone Action Items panel: every item across the user's meetings."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    q: dict = {"owner_id": user["id"]}
    if status:
        q["status"] = status
    if priority:
        q["priority"] = priority
    if project_id:
        q["project_id"] = project_id

    items = await db.meeting_action_items.find(q).sort("due_date", 1).to_list(200)
    meeting_ids = list({i["meeting_id"] for i in items if i.get("meeting_id")})
    m_oids = [ObjectId(m) for m in meeting_ids if ObjectId.is_valid(m)]
    meetings = await db.meetings.find({"_id": {"$in": m_oids}}, {"title": 1, "start_at": 1}).to_list(200) if m_oids else []
    m_map = {str(m["_id"]): {"id": str(m["_id"]), "title": m.get("title", ""), "start_at": m.get("start_at")} for m in meetings}

    out = []
    for i in items:
        item = _ser(i)
        item["meeting"] = m_map.get(i.get("meeting_id"))
        out.append(item)
    return out


@router.patch("/action-items/{item_id}")
async def update_action_item(item_id: str, payload: ActionItemUpdate, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    oid = _oid(item_id)
    doc = await db.meeting_action_items.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    meeting = await db.meetings.find_one({"_id": ObjectId(doc["meeting_id"])}) if ObjectId.is_valid(doc.get("meeting_id", "")) else None
    if meeting and not _is_participant(meeting, user["id"]) and doc.get("owner_id") != user["id"]:
        raise HTTPException(403, "Not authorized")

    update = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if "priority" in update and update["priority"] not in ACTION_ITEM_PRIORITIES:
        del update["priority"]
    if "status" in update and update["status"] not in ACTION_ITEM_STATUSES:
        del update["status"]
    if update:
        update["updated_at"] = _now()
        await db.meeting_action_items.update_one({"_id": oid}, {"$set": update})
    return _ser(await db.meeting_action_items.find_one({"_id": oid}))


@router.delete("/action-items/{item_id}", status_code=204)
async def delete_action_item(item_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    oid = _oid(item_id)
    doc = await db.meeting_action_items.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    meeting = await db.meetings.find_one({"_id": ObjectId(doc["meeting_id"])}) if ObjectId.is_valid(doc.get("meeting_id", "")) else None
    if meeting:
        _assert_owner(meeting, user["id"])
    await db.meeting_action_items.delete_one({"_id": oid})


# ── ICS import ─────────────────────────────────────────────────────────────────

_ICS_FIELD_RE = re.compile(r"^([A-Z\-]+)(?:;[^:]*)?:(.*)$")


def _parse_ics_datetime(raw: str) -> Optional[str]:
    raw = raw.strip()
    try:
        if raw.endswith("Z"):
            return datetime.strptime(raw, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).isoformat()
        if "T" in raw:
            return datetime.strptime(raw, "%Y%m%dT%H%M%S").isoformat()
        return datetime.strptime(raw, "%Y%m%d").isoformat()
    except Exception:
        return None


def _parse_ics(text: str) -> list[dict]:
    """Minimal VEVENT extractor for SUMMARY/DTSTART/DTEND/LOCATION/DESCRIPTION.

    Hand-rolled rather than a third-party dependency: basic single-value ICS
    fields are simple line-oriented text, and this avoids adding a new pip
    dependency for a narrow, well-understood format subset.
    """
    events = []
    current: Optional[dict] = None
    for raw_line in text.splitlines():
        line = raw_line.rstrip("\r")
        if line == "BEGIN:VEVENT":
            current = {}
        elif line == "END:VEVENT":
            if current is not None:
                events.append(current)
            current = None
        elif current is not None:
            m = _ICS_FIELD_RE.match(line)
            if not m:
                continue
            key, value = m.group(1), m.group(2)
            value = value.replace("\\n", "\n").replace("\\,", ",")
            if key == "SUMMARY":
                current["title"] = value
            elif key == "DESCRIPTION":
                current["description"] = value
            elif key == "LOCATION":
                current["location"] = value
            elif key == "DTSTART":
                current["start_at"] = _parse_ics_datetime(value)
            elif key == "DTEND":
                current["end_at"] = _parse_ics_datetime(value)
    return [e for e in events if e.get("title") and e.get("start_at")]


@router.post("/import-ics", status_code=201)
async def import_ics(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    """Import meetings from an uploaded .ics calendar export."""
    if not file.filename.lower().endswith(".ics"):
        raise HTTPException(400, "File must be a .ics calendar export")
    raw = await file.read()
    try:
        text = raw.decode("utf-8", errors="replace")
    except Exception:
        raise HTTPException(400, "Could not read file as text")

    events = _parse_ics(text)
    if not events:
        return {"imported": 0, "errors": ["No valid VEVENT entries found in file"]}

    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    now = _now()
    imported = 0
    errors = []
    for ev in events:
        try:
            start_at = ev["start_at"]
            end_at = ev.get("end_at") or start_at
            doc = {
                "title": ev["title"][:300],
                "description": ev.get("description", "")[:2000],
                "meeting_type": "Research Meeting",
                "start_at": start_at,
                "end_at": end_at,
                "timezone": "UTC",
                "participant_ids": [],
                "workspace_id": "",
                "project_id": "",
                "location": ev.get("location", ""),
                "video_link": "",
                "agenda": [],
                "tags": ["imported"],
                "is_recurring": False,
                "recurrence_rule": "none",
                "recurrence_parent_id": None,
                "reminder_minutes": 15,
                "ai_summary_enabled": True,
                "owner_id": user["id"],
                "status": "scheduled",
                "pinned": False,
                "created_at": now,
                "updated_at": now,
            }
            await db.meetings.insert_one(doc)
            imported += 1
        except Exception as exc:
            errors.append(str(exc))

    return {"imported": imported, "total_found": len(events), "errors": errors}


# ══════════════════════════════════════════════════════════════════════════════
# MEETING CRUD
# ══════════════════════════════════════════════════════════════════════════════

@router.get("")
async def list_meetings(
    status: Optional[str] = Query(None, description="upcoming|past|today|this_week|this_month|cancelled"),
    project_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    participant_id: Optional[str] = None,
    meeting_type: Optional[str] = None,
    q: Optional[str] = Query(None, max_length=200),
    user: dict = Depends(get_current_user),
):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    uid = user["id"]
    query: dict = {"$or": [{"owner_id": uid}, {"participant_ids": uid}]}
    now = datetime.now(timezone.utc)

    if status == "upcoming":
        query["start_at"] = {"$gte": now.isoformat()}
        query["status"] = {"$ne": "cancelled"}
    elif status == "past":
        query["start_at"] = {"$lt": now.isoformat()}
    elif status == "today":
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        query["start_at"] = {"$gte": day_start.isoformat(), "$lt": (day_start + timedelta(days=1)).isoformat()}
    elif status == "this_week":
        query["start_at"] = {"$gte": now.isoformat(), "$lt": (now + timedelta(days=7)).isoformat()}
    elif status == "this_month":
        query["start_at"] = {"$gte": now.isoformat(), "$lt": (now + timedelta(days=30)).isoformat()}
    elif status == "cancelled":
        query["status"] = "cancelled"

    if project_id:
        query["project_id"] = project_id
    if workspace_id:
        query["workspace_id"] = workspace_id
    if participant_id:
        query["participant_ids"] = participant_id
    if meeting_type:
        query["meeting_type"] = meeting_type
    if q:
        rx = {"$regex": re.escape(q), "$options": "i"}
        query["$and"] = query.get("$and", []) + [{"$or": [{"title": rx}, {"tags": rx}, {"agenda": rx}]}]

    docs = await db.meetings.find(query).sort("start_at", 1).to_list(200)
    return await _attach_light_info(docs, db)


async def _attach_light_info(docs: list[dict], db) -> list[dict]:
    """Batch-resolve participant names + workspace/project titles for list views.

    Lighter than `_enrich` (no notes/action-items/files) — just enough for the
    timeline/calendar cards to show real names instead of raw ObjectId strings.
    """
    part_ids: set[str] = set()
    ws_ids: set[str] = set()
    proj_ids: set[str] = set()
    for d in docs:
        part_ids.update(d.get("participant_ids") or [])
        if d.get("workspace_id"):
            ws_ids.add(d["workspace_id"])
        if d.get("project_id"):
            proj_ids.add(d["project_id"])

    part_oids = [ObjectId(p) for p in part_ids if ObjectId.is_valid(p)]
    ws_oids = [ObjectId(w) for w in ws_ids if ObjectId.is_valid(w)]
    proj_oids = [ObjectId(p) for p in proj_ids if ObjectId.is_valid(p)]

    users_raw, ws_raw, proj_raw = await asyncio.gather(
        db.users.find({"_id": {"$in": part_oids}}, {"full_name": 1, "avatar_url": 1}).to_list(200) if part_oids else asyncio.sleep(0),
        db.workspaces.find({"_id": {"$in": ws_oids}}, {"name": 1}).to_list(100) if ws_oids else asyncio.sleep(0),
        db.projects.find({"_id": {"$in": proj_oids}}, {"title": 1, "name": 1}).to_list(100) if proj_oids else asyncio.sleep(0),
    )
    user_map = {str(u["_id"]): {"id": str(u["_id"]), "full_name": u.get("full_name", ""), "avatar_url": u.get("avatar_url")} for u in (users_raw or [])}
    ws_map = {str(w["_id"]): w.get("name") for w in (ws_raw or [])}
    proj_map = {str(p["_id"]): p.get("title") or p.get("name") for p in (proj_raw or [])}

    out = []
    for d in docs:
        m = _ser(d)
        m["participants"] = [user_map[p] for p in (m.get("participant_ids") or []) if p in user_map]
        m["workspace_name"] = ws_map.get(m.get("workspace_id"))
        m["project_title"] = proj_map.get(m.get("project_id"))
        out.append(m)
    return out


@router.post("", status_code=201)
async def create_meeting(payload: MeetingCreate, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    mtype = payload.meeting_type if payload.meeting_type in MEETING_TYPES else "Research Meeting"
    rule = payload.recurrence_rule if payload.recurrence_rule in RECURRENCE_RULES else "none"
    now = _now()
    participant_ids = list({*(payload.participant_ids or []), user["id"]})

    base_doc = {
        "title":              payload.title.strip(),
        "description":        (payload.description or "").strip(),
        "meeting_type":       mtype,
        "start_at":           payload.start_at,
        "end_at":             payload.end_at,
        "timezone":           payload.timezone or "UTC",
        "participant_ids":    participant_ids,
        "workspace_id":       payload.workspace_id or "",
        "project_id":         payload.project_id or "",
        "location":           payload.location or "",
        "video_link":         payload.video_link or "",
        "agenda":             payload.agenda or [],
        "tags":               payload.tags or [],
        "attachment_links":   payload.attachment_links or [],
        "is_recurring":       bool(payload.is_recurring and rule != "none"),
        "recurrence_rule":    rule,
        "recurrence_parent_id": None,
        "reminder_minutes":   payload.reminder_minutes if payload.reminder_minutes is not None else 15,
        "ai_summary_enabled": payload.ai_summary_enabled if payload.ai_summary_enabled is not None else True,
        "owner_id":           user["id"],
        "status":             "scheduled",
        "pinned":             False,
        "created_at":         now,
        "updated_at":         now,
    }
    res = await db.meetings.insert_one(dict(base_doc))
    base_doc["_id"] = res.inserted_id
    meeting_id = str(res.inserted_id)

    # Auto-create meeting group conversation
    try:
        conv_key = f"meeting:{meeting_id}"
        cr = await db.conversations.insert_one({
            "type": "meeting", "context_id": meeting_id, "context_key": conv_key,
            "title": base_doc["title"], "created_by": user["id"],
            "created_at": now, "last_message_at": now, "last_message_preview": "",
        })
        for pid in participant_ids:
            await db.conversation_members.update_one(
                {"conversation_id": str(cr.inserted_id), "user_id": pid},
                {"$setOnInsert": {"conversation_id": str(cr.inserted_id), "user_id": pid,
                                  "role": "owner" if pid == user["id"] else "member",
                                  "joined_at": now, "last_read_at": now, "muted": False}},
                upsert=True,
            )
    except Exception as exc:
        log.warning("meeting conversation create failed: %s", exc)

    # Notify other participants
    for pid in participant_ids:
        if pid != user["id"]:
            await _notify(
                user_id=pid, kind="meeting_invitation",
                title=f"{user.get('full_name','Someone')} invited you to a meeting",
                body=f"'{base_doc['title']}' — {payload.start_at}",
                link=f"/meetings/{meeting_id}", actor_id=user["id"],
                payload={"meeting_id": meeting_id},
            )

    # Expand recurring instances
    created_ids = [meeting_id]
    if base_doc["is_recurring"]:
        for start_at, end_at in _recurrence_dates(payload.start_at, payload.end_at, rule, MAX_RECURRING_INSTANCES):
            inst = dict(base_doc)
            inst.pop("_id", None)
            inst["start_at"] = start_at
            inst["end_at"] = end_at
            inst["recurrence_parent_id"] = meeting_id
            r = await db.meetings.insert_one(inst)
            created_ids.append(str(r.inserted_id))

    return {**_ser(base_doc), "recurring_instance_ids": created_ids[1:]}


@router.get("/{meeting_id}")
async def get_meeting(meeting_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    doc = await db.meetings.find_one({"_id": _oid(meeting_id)})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_participant(doc, user["id"])
    return await _enrich(doc, db)


@router.patch("/{meeting_id}")
async def update_meeting(meeting_id: str, payload: MeetingUpdate, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    oid = _oid(meeting_id)
    doc = await db.meetings.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_participant(doc, user["id"])

    update = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if "meeting_type" in update and update["meeting_type"] not in MEETING_TYPES:
        del update["meeting_type"]
    if "recurrence_rule" in update and update["recurrence_rule"] not in RECURRENCE_RULES:
        del update["recurrence_rule"]
    if update:
        update["updated_at"] = _now()
        await db.meetings.update_one({"_id": oid}, {"$set": update})
        if any(k in update for k in ("start_at", "end_at", "location", "video_link", "status")):
            await _log_note(db, meeting_id, user["id"], user.get("full_name", "Someone"),
                            f"{user.get('full_name','Someone')} updated the meeting", kind="meeting_updated")
    return _ser(await db.meetings.find_one({"_id": oid}))


@router.delete("/{meeting_id}", status_code=204)
async def delete_meeting(meeting_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    oid = _oid(meeting_id)
    doc = await db.meetings.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_owner(doc, user["id"])

    conv = await db.conversations.find_one({"context_key": f"meeting:{meeting_id}"})
    await asyncio.gather(
        db.meeting_action_items.delete_many({"meeting_id": meeting_id}),
        db.meeting_notes.delete_many({"meeting_id": meeting_id}),
        db.meeting_ai_summaries.delete_many({"meeting_id": meeting_id}),
        db.repository_items.update_many({"meeting_id": meeting_id}, {"$unset": {"meeting_id": ""}}),
    )
    if conv:
        conv_id = str(conv["_id"])
        await asyncio.gather(
            db.conversation_members.delete_many({"conversation_id": conv_id}),
            db.messages.delete_many({"conversation_id": conv_id}),
            db.conversations.delete_one({"_id": conv["_id"]}),
        )
    await db.meetings.delete_one({"_id": oid})


# ══════════════════════════════════════════════════════════════════════════════
# NOTES / DISCUSSION
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/{meeting_id}/notes")
async def list_notes(meeting_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    doc = await db.meetings.find_one({"_id": _oid(meeting_id)})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_participant(doc, user["id"])
    notes = await db.meeting_notes.find({"meeting_id": meeting_id}).sort("created_at", -1).to_list(200)
    return [_ser(n) for n in notes]


@router.post("/{meeting_id}/notes", status_code=201)
async def add_note(meeting_id: str, payload: MeetingNoteCreate, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    doc = await db.meetings.find_one({"_id": _oid(meeting_id)})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_participant(doc, user["id"])

    entry = {
        "meeting_id": meeting_id, "actor_id": user["id"],
        "actor_name": user.get("full_name", "Someone"), "body": payload.body,
        "kind": "note", "created_at": _now(),
    }
    res = await db.meeting_notes.insert_one(entry)
    entry["_id"] = res.inserted_id
    return _ser(entry)


# ══════════════════════════════════════════════════════════════════════════════
# ACTION ITEMS (per meeting)
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/{meeting_id}/action-items")
async def list_meeting_action_items(meeting_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    doc = await db.meetings.find_one({"_id": _oid(meeting_id)})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_participant(doc, user["id"])
    items = await db.meeting_action_items.find({"meeting_id": meeting_id}).sort("created_at", -1).to_list(100)
    return [_ser(i) for i in items]


@router.post("/{meeting_id}/action-items", status_code=201)
async def add_meeting_action_item(meeting_id: str, payload: ActionItemCreate, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    doc = await db.meetings.find_one({"_id": _oid(meeting_id)})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_participant(doc, user["id"])

    priority = payload.priority if payload.priority in ACTION_ITEM_PRIORITIES else "medium"
    now = _now()
    item = {
        "meeting_id": meeting_id,
        "title":      payload.title.strip(),
        "owner_id":   payload.owner_id or user["id"],
        "priority":   priority,
        "due_date":   payload.due_date,
        "project_id": payload.project_id or doc.get("project_id", ""),
        "status":     "open",
        "created_at": now,
        "updated_at": now,
    }
    res = await db.meeting_action_items.insert_one(item)
    item["_id"] = res.inserted_id
    await _log_note(db, meeting_id, user["id"], user.get("full_name", "Someone"),
                    f"Action item added: {item['title']}", kind="action_item_added")
    return _ser(item)


# ══════════════════════════════════════════════════════════════════════════════
# AI FEATURES — all grounded in the meeting's own agenda/notes/context, never
# fabricated. Share one context builder + call_llm invocation.
# ══════════════════════════════════════════════════════════════════════════════

def _meeting_context_block(meeting: dict, notes: list[dict]) -> str:
    lines = [
        f"Title: {meeting.get('title','')}",
        f"Type: {meeting.get('meeting_type','')}",
        f"Description: {meeting.get('description','') or '(none)'}",
        f"Scheduled: {meeting.get('start_at','')} to {meeting.get('end_at','')}",
    ]
    agenda = meeting.get("agenda") or []
    lines.append("Agenda:\n" + ("\n".join(f"- {a}" for a in agenda) if agenda else "(no agenda set)"))
    if notes:
        notes_text = "\n".join(f"[{n.get('actor_name','')}] {n.get('body','')}" for n in reversed(notes) if n.get("body"))
        lines.append("Discussion notes (chronological):\n" + (notes_text or "(no notes)"))
    else:
        lines.append("Discussion notes: (none recorded)")
    return "\n\n".join(lines)


_AI_SYSTEM_PROMPTS = {
    "agenda": "You are an academic meeting assistant. Draft a clear, structured agenda for the described research meeting based only on the given context. Use concise bullet points.",
    "summary": "You are an academic meeting assistant. Summarize the meeting factually based only on the notes and agenda provided. Do not invent details, decisions, or numbers not present in the context.",
    "action-items": "You are an academic meeting assistant. Extract concrete action items mentioned in the discussion notes. Return one action item per line, each with a suggested owner if named in the notes. Only include items actually stated in the context.",
    "decisions": "You are an academic meeting assistant. Extract the decisions actually made during this meeting, based only on the discussion notes. If no decisions are evident, say so plainly.",
    "follow-up-email": "You are an academic meeting assistant. Draft a brief, professional follow-up email summarizing this meeting for its participants, grounded only in the provided context.",
    "next-steps": "You are an academic research assistant. Based only on the meeting context, suggest concrete next research steps that follow logically from what was discussed.",
    "manuscript-todo": "You are an academic writing assistant. Based only on the meeting context, produce a TODO list for manuscript progress discussed in this meeting.",
    "grant-follow-up": "You are a research funding assistant. Based only on the meeting context, produce grant-related follow-up actions discussed in this meeting.",
}


async def _run_meeting_ai(kind: str, meeting: dict, db, user: dict, instructions: Optional[str] = None) -> str:
    meeting_id = str(meeting["_id"]) if "_id" in meeting else meeting["id"]
    notes = await db.meeting_notes.find({"meeting_id": meeting_id}).sort("created_at", 1).limit(100).to_list(100)
    context = _meeting_context_block(meeting, notes)
    if instructions:
        context += f"\n\nAdditional instructions from the requester: {instructions}"

    text = await call_llm(
        system=_AI_SYSTEM_PROMPTS[kind],
        user_msg=context,
        feature=f"meetings.ai.{kind}",
        user_id=user["id"],
        db=db,
        max_tokens=1200,
    )
    return text.strip()


async def _load_meeting_for_ai(meeting_id: str, db, user: dict) -> dict:
    doc = await db.meetings.find_one({"_id": _oid(meeting_id)})
    if not doc:
        raise HTTPException(404, "Not found")
    _assert_participant(doc, user["id"])
    return doc


@router.post("/{meeting_id}/ai/agenda")
async def ai_generate_agenda(meeting_id: str, body: AIRequestBody, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))
    meeting = await _load_meeting_for_ai(meeting_id, db, user)
    text = await _run_meeting_ai("agenda", meeting, db, user, body.instructions)
    return {"kind": "agenda", "text": text}


@router.post("/{meeting_id}/ai/summary")
async def ai_generate_summary(meeting_id: str, body: AIRequestBody, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))
    meeting = await _load_meeting_for_ai(meeting_id, db, user)
    text = await _run_meeting_ai("summary", meeting, db, user, body.instructions)

    now = _now()
    summary_doc = {
        "meeting_id": meeting_id, "summary_text": text,
        "generated_by": user["id"], "generated_at": now, "model_used": "gateway-default",
    }
    res = await db.meeting_ai_summaries.insert_one(summary_doc)
    summary_doc["_id"] = res.inserted_id
    await _log_note(db, meeting_id, user["id"], user.get("full_name", "Someone"),
                    "AI summary generated", kind="ai_summary_generated")
    return {"kind": "summary", "text": text, "summary": _ser(summary_doc)}


@router.post("/{meeting_id}/ai/action-items")
async def ai_extract_action_items(meeting_id: str, body: AIRequestBody, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))
    meeting = await _load_meeting_for_ai(meeting_id, db, user)
    text = await _run_meeting_ai("action-items", meeting, db, user, body.instructions)
    suggestions = [ln.strip("-• ").strip() for ln in text.splitlines() if ln.strip()]
    return {"kind": "action-items", "text": text, "suggestions": suggestions}


@router.post("/{meeting_id}/ai/decisions")
async def ai_extract_decisions(meeting_id: str, body: AIRequestBody, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))
    meeting = await _load_meeting_for_ai(meeting_id, db, user)
    text = await _run_meeting_ai("decisions", meeting, db, user, body.instructions)
    return {"kind": "decisions", "text": text}


@router.post("/{meeting_id}/ai/follow-up-email")
async def ai_follow_up_email(meeting_id: str, body: AIRequestBody, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))
    meeting = await _load_meeting_for_ai(meeting_id, db, user)
    text = await _run_meeting_ai("follow-up-email", meeting, db, user, body.instructions)
    return {"kind": "follow-up-email", "text": text}


@router.post("/{meeting_id}/ai/next-steps")
async def ai_next_steps(meeting_id: str, body: AIRequestBody, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))
    meeting = await _load_meeting_for_ai(meeting_id, db, user)
    text = await _run_meeting_ai("next-steps", meeting, db, user, body.instructions)
    return {"kind": "next-steps", "text": text}


@router.post("/{meeting_id}/ai/manuscript-todo")
async def ai_manuscript_todo(meeting_id: str, body: AIRequestBody, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))
    meeting = await _load_meeting_for_ai(meeting_id, db, user)
    if meeting.get("meeting_type") != "Journal Submission Meeting" and not meeting.get("project_id"):
        raise HTTPException(400, "This action is only available for meetings linked to a manuscript project")
    text = await _run_meeting_ai("manuscript-todo", meeting, db, user, body.instructions)
    return {"kind": "manuscript-todo", "text": text}


@router.post("/{meeting_id}/ai/grant-follow-up")
async def ai_grant_follow_up(meeting_id: str, body: AIRequestBody, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))
    meeting = await _load_meeting_for_ai(meeting_id, db, user)
    if meeting.get("meeting_type") != "Grant Meeting" and not meeting.get("project_id"):
        raise HTTPException(400, "This action is only available for meetings linked to a grant")
    text = await _run_meeting_ai("grant-follow-up", meeting, db, user, body.instructions)
    return {"kind": "grant-follow-up", "text": text}
