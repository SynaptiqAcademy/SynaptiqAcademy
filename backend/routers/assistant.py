"""SYNAPTIQ Phase 7 — Conversational Research Assistant, AI usage dashboard,
saved searches + Resend digests.

All three live in one router because they share infrastructure (LlmChat
sessions, ai_requests audit, credits_service).
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, Literal

from auth_utils import get_current_user
from db import get_db
from plans_catalogue import CREDIT_COSTS
from services.credits_service import consume_credits, refund_credits
from services.ai.matching import DEFAULT_MODEL, DEFAULT_PROVIDER
from services.permissions import require_feature, is_super_admin, require_super_admin
from repo.shim import DBProxy
from repo.security_context import SecurityContext

logger = logging.getLogger("synaptiq.ai.assistant")
router = APIRouter(prefix="/api", tags=["ai-assistant"])

ENTITY_KINDS = {"workspace", "project", "manuscript"}
ASSISTANT_COST = CREDIT_COSTS.get("ai_chat_message", 2)


# ============================== CONTEXT BUILDER ==============================
async def _build_context(kind: str, eid: str, user_id: str) -> dict:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    try: oid = ObjectId(eid)
    except Exception: raise HTTPException(404, "Not found")
    if kind == "workspace":
        ws = await db.workspaces.find_one({"_id": oid})
        if not ws or user_id not in (ws.get("members") or []): raise HTTPException(403, "Forbidden")
        projects = await db.projects.find({"_id": {"$in": [ObjectId(p) for p in (ws.get("project_ids") or []) if _safe_oid(p)]}}).to_list(50) if ws.get("project_ids") else []
        manuscripts = await db.manuscripts.find({"workspace_id": eid}).to_list(50)
        milestones = await db.milestones.find({"workspace_id": eid}).limit(20).to_list(20)
        return {
            "entity": "workspace", "id": eid,
            "name": ws.get("name"), "description": ws.get("description"),
            "members_count": len(ws.get("members") or []),
            "projects": [{"id": str(p["_id"]), "title": p.get("title"), "status": p.get("status")} for p in projects[:10]],
            "manuscripts": [{"id": str(m["_id"]), "title": m.get("title"), "status": m.get("status")} for m in manuscripts[:10]],
            "milestones": [{"title": m.get("title"), "target_date": m.get("target_date"), "completed": m.get("completed")} for m in milestones[:10]],
        }
    if kind == "project":
        p = await db.projects.find_one({"_id": oid})
        if not p or user_id not in (p.get("members") or []): raise HTTPException(403, "Forbidden")
        return {
            "entity": "project", "id": eid,
            "title": p.get("title"), "abstract": (p.get("description") or "")[:1500],
            "objectives": (p.get("objectives") or "")[:1000],
            "methodology": (p.get("methodology") or "")[:1000],
            "status": p.get("status"),
            "skills_needed": p.get("skills_needed") or [],
        }
    # manuscript
    m = await db.manuscripts.find_one({"_id": oid})
    if not m or user_id not in (m.get("authors") or []): raise HTTPException(403, "Forbidden")
    sec = m.get("sections") or {}
    return {
        "entity": "manuscript", "id": eid,
        "title": m.get("title") or sec.get("title", ""),
        "abstract": (sec.get("abstract") or "")[:2000],
        "introduction_excerpt": (sec.get("introduction") or "")[:600],
        "methodology_excerpt": (sec.get("methodology") or "")[:600],
        "keywords": m.get("keywords") or [],
        "manuscript_type": m.get("manuscript_type"),
        "status": m.get("status"),
        "filled_sections": [k for k, v in sec.items() if v and v.strip()],
    }


def _safe_oid(s: str) -> bool:
    try: ObjectId(s); return True
    except Exception: return False


# =============================== CHAT SESSION ================================
class StartSessionIn(BaseModel):
    entity_kind: str   # workspace | project | manuscript
    entity_id: str
    title: Optional[str] = None


@router.post("/assistant/sessions", dependencies=[Depends(require_feature("ai_manuscript_copilot"))])
async def start_session(body: StartSessionIn, user: dict = Depends(get_current_user)):
    if body.entity_kind not in ENTITY_KINDS: raise HTTPException(400, "Invalid entity_kind")
    context = await _build_context(body.entity_kind, body.entity_id, user["id"])
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    doc = {
        "user_id": user["id"], "entity_kind": body.entity_kind, "entity_id": body.entity_id,
        "title": body.title or f"{body.entity_kind.capitalize()} chat",
        "context_snapshot": context,
        "messages_count": 0,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    r = await db.chat_sessions.insert_one(doc)
    doc["_id"] = r.inserted_id; doc["id"] = str(r.inserted_id); doc.pop("_id")
    return doc


@router.get("/assistant/sessions")
async def list_sessions(entity_kind: Optional[str] = None, entity_id: Optional[str] = None,
                        user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    q: dict = {"user_id": user["id"]}
    if entity_kind: q["entity_kind"] = entity_kind
    if entity_id: q["entity_id"] = entity_id
    docs = await db.chat_sessions.find(q).sort("updated_at", -1).limit(40).to_list(40)
    for d in docs: d["id"] = str(d.pop("_id"))
    return docs


@router.get("/assistant/sessions/{sid}/messages")
async def get_messages(sid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    s = await db.chat_sessions.find_one({"_id": ObjectId(sid)})
    if not s or s.get("user_id") != user["id"]: raise HTTPException(404, "Not found")
    msgs = await db.chat_messages.find({"session_id": sid}).sort("created_at", 1).to_list(200)
    for m in msgs: m["id"] = str(m.pop("_id"))
    sid_str = str(s.pop("_id"))
    return {"session": {**s, "id": sid_str}, "messages": msgs}


class SendMessageIn(BaseModel):
    text: str
    capability: Optional[Literal[
        "literature_synthesis", "citation_generation", "methodology_assistance",
        "research_question_generation", "reviewer_response_drafting",
        "journal_explanation", "conference_explanation", "grant_explanation",
        "freeform",
    ]] = "freeform"


CAPABILITY_DIRECTIVES = {
    "literature_synthesis": "Synthesize related work into themes; cite likely venues. Use numbered themes.",
    "citation_generation": "Produce 3-6 plausible citation-style references in BibTeX-like format.",
    "methodology_assistance": "Propose a rigorous research methodology with measurable steps.",
    "research_question_generation": "Generate 3-5 sharp research questions tied to the entity context.",
    "reviewer_response_drafting": "Draft a polite, point-by-point response to reviewer comments.",
    "journal_explanation": "Explain in 4-6 sentences why a journal would (or wouldn't) be a good fit.",
    "conference_explanation": "Explain in 4-6 sentences why a conference fits, including deadline tradeoffs.",
    "grant_explanation": "Explain in 4-6 sentences fit + eligibility + risks for a grant.",
    "freeform": "Respond conversationally. Be concise (≤8 sentences). Reference the entity context when helpful.",
}


@router.post("/assistant/sessions/{sid}/messages", dependencies=[Depends(require_feature("ai_manuscript_copilot"))])
async def send_message(sid: str, body: SendMessageIn, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    s = await db.chat_sessions.find_one({"_id": ObjectId(sid)})
    if not s or s.get("user_id") != user["id"]: raise HTTPException(404, "Not found")
    # Charge first (refund on failure). consume_credits raises 402 with the
    # standard upgrade-hint payload; the global Axios interceptor turns it
    # into the UpgradeModal.
    charged = await consume_credits(user["id"], "ai_chat_message")
    cost = charged.get("consumed") if isinstance(charged, dict) else ASSISTANT_COST

    # Persist user message
    now = datetime.now(timezone.utc).isoformat()
    await db.chat_messages.insert_one({
        "session_id": sid, "role": "user", "text": body.text,
        "capability": body.capability, "created_at": now,
    })

    # Build system prompt from entity context
    context = s.get("context_snapshot") or {}
    directive = CAPABILITY_DIRECTIVES.get(body.capability or "freeform", CAPABILITY_DIRECTIVES["freeform"])
    system = (
        "You are SYNAPTIQ's Research Assistant. You help the user with their research work on a "
        f"specific {context.get('entity', 'item')}. Use ONLY the provided context as ground truth; "
        "do not fabricate citations or invent facts. When unsure, say so.\n\n"
        f"DIRECTIVE: {directive}\n\n"
        f"CONTEXT:\n{json.dumps(context)}"
    )

    from services.ai.llm import call_llm
    # Build full conversation history from DB for multi-turn context.
    history = await db.chat_messages.find(
        {"session_id": sid, "role": {"$in": ["user", "assistant"]}}
    ).sort("created_at", 1).to_list(100)
    messages = [{"role": m["role"], "content": m["text"]} for m in history]

    started = time.monotonic()
    try:
        text = await call_llm(
            system=system,
            provider=DEFAULT_PROVIDER,
            model=DEFAULT_MODEL,
            messages=messages,
            feature="general.assistant",
            user_id=user["id"],
            db=db,
        )
    except Exception as e:
        await refund_credits(user["id"], "ai_chat_message")
        raise HTTPException(503, f"LLM error: {str(e)[:200]}")
    latency_ms = int((time.monotonic() - started) * 1000)

    # Persist assistant message + ai_requests audit
    asst_id = (await db.chat_messages.insert_one({
        "session_id": sid, "role": "assistant", "text": text,
        "capability": body.capability, "created_at": datetime.now(timezone.utc).isoformat(),
        "latency_ms": latency_ms, "credits_consumed": cost,
    })).inserted_id
    await db.chat_sessions.update_one({"_id": ObjectId(sid)},
        {"$inc": {"messages_count": 2},
         "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}})
    await db.ai_requests.insert_one({
        "user_id": user["id"], "kind": "assistant_message",
        "input": {"session_id": sid, "capability": body.capability, "text_len": len(body.text)},
        "output_excerpt": [{"text_len": len(text)}],
        "credits_consumed": cost, "latency_ms": latency_ms,
        "provider": DEFAULT_PROVIDER, "model": DEFAULT_MODEL,
        "created_at": datetime.now(timezone.utc).isoformat(),
    })
    return {"id": str(asst_id), "role": "assistant", "text": text,
            "credits_consumed": cost, "latency_ms": latency_ms}


@router.delete("/assistant/sessions/{sid}")
async def delete_session(sid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    s = await db.chat_sessions.find_one({"_id": ObjectId(sid)})
    if not s or s.get("user_id") != user["id"]: raise HTTPException(404, "Not found")
    await db.chat_sessions.delete_one({"_id": ObjectId(sid)})
    await db.chat_messages.delete_many({"session_id": sid})
    return {"ok": True}


# =============================== USAGE DASHBOARD =============================
@router.get("/ai/usage")
async def ai_usage(user: dict = Depends(get_current_user)):
    """User dashboard. Admin gets a global=true flag with extra rollups."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    is_admin = is_super_admin(user)
    user_doc = await db.users.find_one({"_id": ObjectId(user["id"])})
    plan_code = user_doc.get("plan_code") or "free"
    balance = user_doc.get("credits_balance") or 0
    base_q = {} if is_admin else {"user_id": user["id"]}
    pipe = [
        {"$match": base_q},
        # Normalize legacy records where credits_consumed was stored as dict.
        {"$set": {"credits_consumed": {
            "$cond": [
                {"$eq": [{"$type": "$credits_consumed"}, "object"]},
                {"$ifNull": ["$credits_consumed.consumed", 0]},
                {"$ifNull": ["$credits_consumed", 0]},
            ]
        }}},
        {"$facet": {
            "by_kind": [
                {"$group": {"_id": "$kind", "calls": {"$sum": 1}, "credits": {"$sum": "$credits_consumed"},
                            "avg_latency": {"$avg": "$latency_ms"}}},
                {"$sort": {"credits": -1}},
            ],
            "last_30d": [
                {"$group": {"_id": {"$substr": ["$created_at", 0, 10]}, "credits": {"$sum": "$credits_consumed"}}},
                {"$sort": {"_id": -1}}, {"$limit": 30},
            ],
            "totals": [
                {"$group": {"_id": None, "calls": {"$sum": 1}, "credits": {"$sum": "$credits_consumed"}}},
            ],
        }},
    ]
    out = await db.ai_requests.aggregate(pipe).to_list(1)
    data = out[0] if out else {"by_kind": [], "last_30d": [], "totals": [{"calls": 0, "credits": 0}]}
    totals = (data["totals"] or [{"calls": 0, "credits": 0}])[0]
    # Cost estimates (USD) — admin-only rough estimate: $0.003 per claude-sonnet message + $0.015 per match (rough)
    PRICE = {"journal_matching": 0.020, "conference_matching": 0.015, "grant_matching": 0.020,
             "reviewer_matching": 0.020, "assistant_message": 0.005}
    cost_usd = sum(PRICE.get(b["_id"], 0.01) * b["calls"] for b in data["by_kind"])
    return {
        "scope": "global" if is_admin else "user",
        "plan_code": plan_code, "credits_balance": balance,
        "totals": totals, "by_kind": data["by_kind"], "last_30d": data["last_30d"],
        "cost_usd_estimate": round(cost_usd, 2),
    }


# ================================ SAVED SEARCHES =============================
class SaveSearchIn(BaseModel):
    kind: Literal["journal", "conference", "grant"]
    name: str
    query: Optional[str] = None
    filters: Optional[dict] = None
    frequency: Literal["off", "daily", "weekly"] = "off"


@router.post("/searches")
async def save_search(body: SaveSearchIn, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    doc = {
        "user_id": user["id"], "kind": body.kind, "name": body.name,
        "query": body.query or "", "filters": body.filters or {},
        "frequency": body.frequency, "last_sent_at": None,
        "last_seen_max_updated_at": datetime.now(timezone.utc).isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    r = await db.saved_searches.insert_one(doc)
    doc["id"] = str(r.inserted_id); doc.pop("_id")
    return doc


@router.get("/searches")
async def list_searches(user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    docs = await db.saved_searches.find({"user_id": user["id"]}).sort("created_at", -1).to_list(100)
    for d in docs: d["id"] = str(d.pop("_id"))
    return docs


@router.patch("/searches/{sid}")
async def update_search(sid: str, body: SaveSearchIn, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    s = await db.saved_searches.find_one({"_id": ObjectId(sid)})
    if not s or s.get("user_id") != user["id"]: raise HTTPException(404, "Not found")
    await db.saved_searches.update_one({"_id": ObjectId(sid)},
        {"$set": {"name": body.name, "query": body.query or "",
                  "filters": body.filters or {}, "frequency": body.frequency}})
    return {"ok": True}


@router.delete("/searches/{sid}")
async def delete_search(sid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    s = await db.saved_searches.find_one({"_id": ObjectId(sid)})
    if not s or s.get("user_id") != user["id"]: raise HTTPException(404, "Not found")
    await db.saved_searches.delete_one({"_id": ObjectId(sid)})
    return {"ok": True}


@router.post("/searches/{sid}/preview")
async def preview_search(sid: str, user: dict = Depends(get_current_user)):
    """Show what the digest would contain right now — useful for the user's
    'Send me a test' flow. Reuses the discovery list endpoints internally."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    s = await db.saved_searches.find_one({"_id": ObjectId(sid)})
    if not s or s.get("user_id") != user["id"]: raise HTTPException(404, "Not found")
    coll = {"journal": "journals", "conference": "conferences", "grant": "grants"}[s["kind"]]
    q: dict = {}
    if s.get("query"): q["$text"] = {"$search": s["query"]}
    f = s.get("filters") or {}
    if s["kind"] == "journal":
        if f.get("subject"): q["subjects"] = f["subject"]
        if f.get("quartile"): q["quartile"] = f["quartile"]
        if f.get("open_access") is not None: q["open_access"] = f["open_access"]
    elif s["kind"] == "conference":
        if f.get("research_area"): q["research_areas"] = f["research_area"]
    elif s["kind"] == "grant":
        if f.get("research_area"): q["research_areas"] = f["research_area"]
        if f.get("country"): q["country"] = f["country"].upper()
    docs = await db[coll].find(q).sort("updated_at", -1).limit(10).to_list(10)
    items = []
    for d in docs:
        items.append({"id": str(d["_id"]),
                      "title": d.get("title") or d.get("name"),
                      "subtitle": d.get("publisher") or d.get("sponsor") or d.get("location"),
                      "deadline": d.get("submission_deadline") or d.get("deadline"),
                      "updated_at": d.get("updated_at")})
    return {"items": items, "kind": s["kind"], "query": s.get("query"), "filters": s.get("filters")}


# ============================== DIGEST SCHEDULER =============================
async def _send_digests(frequency: str) -> dict:
    """Find users with saved_searches frequency=freq, build a small digest per
    user, and send one Resend email per user. Returns counts."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    searches = await db.saved_searches.find({"frequency": frequency}).to_list(2000)
    by_user: dict[str, list] = {}
    for s in searches:
        by_user.setdefault(s["user_id"], []).append(s)
    sent = 0; failed = 0
    for uid, group in by_user.items():
        sections = []
        for s in group:
            preview = await preview_search.__wrapped__ if False else None  # unused; we inline below
            # inline mini-query
            coll = {"journal": "journals", "conference": "conferences", "grant": "grants"}[s["kind"]]
            q: dict = {}
            if s.get("query"): q["$text"] = {"$search": s["query"]}
            since = s.get("last_seen_max_updated_at")
            if since: q["updated_at"] = {"$gt": since}
            docs = await db[coll].find(q).sort("updated_at", -1).limit(5).to_list(5)
            if not docs: continue
            sections.append({"name": s["name"], "kind": s["kind"], "rows": docs})
            # advance high-water mark
            max_upd = max((d.get("updated_at") or "") for d in docs)
            if max_upd:
                await db.saved_searches.update_one({"_id": s["_id"]},
                    {"$set": {"last_seen_max_updated_at": max_upd, "last_sent_at": datetime.now(timezone.utc).isoformat()}})
        if not sections: continue
        # Build HTML and send (or dry-run)
        try:
            user_doc = await db.users.find_one({"_id": ObjectId(uid)})
            if not user_doc or not user_doc.get("email"): continue
            html = _digest_html(user_doc.get("full_name") or "Researcher", sections)
            from services.email_service import send_email
            await send_email(to=user_doc["email"],
                             subject=f"[SYNAPTIQ] Your {frequency} research digest",
                             html=html, event_kind=f"digest_{frequency}")
            sent += 1
        except Exception as e:
            failed += 1
            logger.warning("digest send failed user=%s err=%s", uid, e)
    return {"sent": sent, "failed": failed, "frequency": frequency}


def _digest_html(name: str, sections: list) -> str:
    head = f"<p>Hi {name}, here are the newest items matching your saved searches:</p>"
    parts = []
    for sec in sections:
        rows = "".join(
            f"<li><strong>{(d.get('title') or d.get('name') or '')[:120]}</strong>"
            f" — {(d.get('publisher') or d.get('sponsor') or d.get('location') or '')[:80]}"
            + (f" · deadline {d.get('deadline') or d.get('submission_deadline')}" if (d.get('deadline') or d.get('submission_deadline')) else "")
            + "</li>" for d in sec["rows"]
        )
        parts.append(f"<h3 style='font-family:Georgia,serif;color:#0F2847;'>{sec['name']} <span style='color:#64748B;font-size:12px;'>({sec['kind']})</span></h3><ul>{rows}</ul>")
    return f"<div style='font-family:Helvetica,Arial,sans-serif;max-width:600px;'>{head}{''.join(parts)}<p style='font-size:11px;color:#64748B;'>Manage your saved searches in SYNAPTIQ → Discovery.</p></div>"


@router.post("/searches/digest/run")
async def run_digest(frequency: Literal["daily", "weekly"] = "daily",
                     user: dict = Depends(require_super_admin)):
    """Super-admin manual trigger for the digest job."""
    return await _send_digests(frequency)
