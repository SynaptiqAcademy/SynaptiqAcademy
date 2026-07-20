"""SYNAPTIQ Phase 6 — AI matching service.

A single typed wrapper around the Anthropic SDK for ranking-style
tasks (journal/conference/grant/reviewer matching). All four matchers follow
the same pattern:

  1. Retrieve a *candidate set* from the existing Discovery DB (or user network
     for reviewers) using cheap heuristics — keyword text search + filters.
  2. Pass a compact JSON list of candidates + the manuscript's abstract to the
     LLM with a strict response schema (top-N items, each with score, rationale,
     concerns).
  3. Parse, persist to `ai_requests`, return the enriched response.

We deliberately keep the LLM prompt short (≤ 5,000 tokens) by serialising only
the fields that matter for the ranking decision. Heavy join data (publications,
collaborations) is loaded *after* the LLM picks winners so we don't blow context.

Provider abstraction:
  - Default: anthropic / claude-sonnet-4-6 (per playbook recommendation).
  - Override via env `AI_MATCHING_PROVIDER=openai|anthropic|gemini` and
    `AI_MATCHING_MODEL=<model-name>`.
"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from fastapi import HTTPException

from db import get_db
from services.credits_service import consume_credits, refund_credits
from repo.shim import DBProxy
from repo.security_context import SecurityContext

logger = logging.getLogger("synaptiq.ai.matching")


# --------------------------------- provider ---------------------------------
DEFAULT_PROVIDER = os.environ.get("AI_MATCHING_PROVIDER", "anthropic")
DEFAULT_MODEL = os.environ.get("AI_MATCHING_MODEL", "claude-sonnet-4-6")


async def _call_llm_json(*, system: str, prompt: str, session_id: str,
                          provider: str = DEFAULT_PROVIDER, model: str = DEFAULT_MODEL) -> dict:
    """Single-shot LLM call, parsed as JSON. Raises HTTPException on failure."""
    from services.ai.llm import call_llm
    try:
        text = await call_llm(system=system, user_msg=prompt, feature="collaboration.matching", provider=provider, model=model)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"LLM error: {str(e)[:200]}")
    # Find the JSON block (LLMs sometimes wrap with ```json ... ```)
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        raise HTTPException(status_code=502, detail="LLM did not return JSON")
    try:
        return json.loads(m.group(0))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM JSON parse failed: {e}")


# --------------------------------- audit ------------------------------------
async def _record_request(*, user_id: str, kind: str, input_summary: dict,
                          output: dict, credits: int, latency_ms: int,
                          provider: str, model: str) -> str:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    doc = {
        "user_id": user_id, "kind": kind,
        "input": input_summary, "output_excerpt": (output.get("recommendations") or [])[:10],
        "credits_consumed": credits, "latency_ms": latency_ms,
        "provider": provider, "model": model,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    r = await db.ai_requests.insert_one(doc)
    return str(r.inserted_id)


# ------------------------------ shared helpers -------------------------------
async def _load_manuscript(mid: str, user_id: str) -> dict:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    try: oid = ObjectId(mid)
    except Exception: raise HTTPException(404, "Manuscript not found")
    m = await db.manuscripts.find_one({"_id": oid})
    if not m: raise HTTPException(404, "Manuscript not found")
    if user_id not in m.get("authors", []): raise HTTPException(403, "Forbidden")
    return m


def _manuscript_compact(m: dict) -> dict:
    sec = m.get("sections") or {}
    return {
        "title": m.get("title") or sec.get("title", ""),
        "abstract": (sec.get("abstract") or "")[:1500],
        "keywords": m.get("keywords") or [],
        "manuscript_type": m.get("manuscript_type"),
    }


def _safe_oid(s: str) -> bool:
    try: ObjectId(s); return True
    except Exception: return False


def _short(text: str, n: int = 240) -> str:
    if not text: return ""
    return text[:n]


# ============================== JOURNAL MATCHING =============================
async def match_journals(*, user_id: str, manuscript_id: str, top_n: int = 6) -> dict:
    m = await _load_manuscript(manuscript_id, user_id)
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    mc = _manuscript_compact(m)
    q = " ".join(filter(None, [mc["title"], " ".join(mc["keywords"][:10])])).strip() or "research"
    # Retrieve candidate set — bias toward Q1/Q2 + popularity
    candidates = await db.journals.find(
        {"$text": {"$search": q}}, {"score": {"$meta": "textScore"}}
    ).sort([("score", {"$meta": "textScore"}), ("popularity_score", -1)]).limit(40).to_list(40)
    if len(candidates) < 8:
        # Fall back to popularity if text search starves the candidate set
        extra = await db.journals.find({}).sort("popularity_score", -1).limit(40 - len(candidates)).to_list(40)
        seen = {str(c["_id"]) for c in candidates}
        candidates += [c for c in extra if str(c["_id"]) not in seen]
    # Compact candidates for the LLM
    cand_json = []
    for c in candidates[:30]:
        cand_json.append({
            "id": str(c["_id"]),
            "title": c.get("title"), "publisher": c.get("publisher") or "",
            "subjects": c.get("subjects", [])[:5],
            "quartile": c.get("quartile"), "open_access": c.get("open_access"),
            "apc_usd": c.get("apc_usd"), "works": c.get("works_count"),
            "popularity": c.get("popularity_score"),
            "mean_citedness_2yr": c.get("mean_citedness_2yr"),
        })

    cost = await _charge(user_id, "ai_journal_matching")
    started = time.monotonic()
    try:
        result = await _call_llm_json(
            system=(
                "You are SYNAPTIQ's academic publishing strategist. "
                "Rank candidate journals for a manuscript. Return ONLY valid JSON."
            ),
            prompt=(
                f"MANUSCRIPT:\n{json.dumps(mc)}\n\n"
                f"CANDIDATES (rank these, do NOT invent new ones):\n{json.dumps(cand_json)}\n\n"
                f"Return JSON with exactly this schema:\n"
                "{\n"
                '  "recommendations": [\n'
                "    {\n"
                '      "journal_id": "<id from candidates>",\n'
                '      "score": <int 0-100, calibrated>,\n'
                '      "rationale": "<2 sentences why this journal fits>",\n'
                '      "concerns": "<1 short sentence on risks (scope mismatch, APC, review time, low acceptance)>"\n'
                "    }\n"
                f"  ]   // top {top_n} by score, highest first\n"
                "}\n"
                "Calibration: 90+ = strong scope+quartile fit, 70-89 = good, 50-69 = plausible, <50 = weak."
            ),
            session_id=f"journal-match-{user_id}-{manuscript_id}",
        )
    except Exception:
        await refund_credits(user_id, "ai_journal_matching"); raise
    latency_ms = int((time.monotonic() - started) * 1000)

    # Hydrate winners with full records
    by_id = {str(c["_id"]): c for c in candidates}
    recs = (result.get("recommendations") or [])[:top_n]
    enriched = []
    for r in recs:
        c = by_id.get(r.get("journal_id"))
        if not c: continue
        enriched.append({
            "journal": {"id": str(c["_id"]), "title": c.get("title"),
                         "publisher": c.get("publisher"), "quartile": c.get("quartile"),
                         "open_access": c.get("open_access"), "apc_usd": c.get("apc_usd"),
                         "subjects": c.get("subjects", [])[:5],
                         "homepage_url": c.get("homepage_url"),
                         "works_count": c.get("works_count"),
                         "review_time_weeks": c.get("review_time_weeks"),
                         "acceptance_rate": c.get("acceptance_rate")},
            "score": int(r.get("score") or 0),
            "rationale": _short(r.get("rationale", ""), 600),
            "concerns": _short(r.get("concerns", ""), 280),
        })
    request_id = await _record_request(
        user_id=user_id, kind="journal_matching",
        input_summary={"manuscript_id": manuscript_id, "title": mc["title"]},
        output={"recommendations": [{"journal_id": e["journal"]["id"], "score": e["score"]} for e in enriched]},
        credits=cost, latency_ms=latency_ms, provider=DEFAULT_PROVIDER, model=DEFAULT_MODEL,
    )
    return {"request_id": request_id, "manuscript_id": manuscript_id,
            "recommendations": enriched, "credits_consumed": cost, "latency_ms": latency_ms}


# ============================ CONFERENCE MATCHING ============================
async def match_conferences(*, user_id: str, manuscript_id: str, top_n: int = 6) -> dict:
    m = await _load_manuscript(manuscript_id, user_id)
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    mc = _manuscript_compact(m)
    q = " ".join(filter(None, [mc["title"], " ".join(mc["keywords"][:10])])).strip() or "research"
    today = datetime.now(timezone.utc).date().isoformat()
    base_filter = {"$text": {"$search": q},
                   "$or": [{"submission_deadline": {"$gte": today}}, {"submission_deadline": None},
                           {"start_date": {"$gte": today}}]}
    candidates = await db.conferences.find(base_filter, {"score": {"$meta": "textScore"}}) \
        .sort([("score", {"$meta": "textScore"})]).limit(40).to_list(40)
    if len(candidates) < 8:
        extra = await db.conferences.find({"start_date": {"$gte": today}}).sort("start_date", 1).limit(40 - len(candidates)).to_list(40)
        seen = {str(c["_id"]) for c in candidates}
        candidates += [c for c in extra if str(c["_id"]) not in seen]
    cand_json = [{
        "id": str(c["_id"]), "name": c.get("name"), "acronym": c.get("acronym"),
        "rank": c.get("rank"), "topics": c.get("topics", [])[:5],
        "research_areas": c.get("research_areas", [])[:3],
        "submission_deadline": c.get("submission_deadline"),
        "start_date": c.get("start_date"), "location": c.get("location"),
        "format": c.get("format"),
    } for c in candidates[:30]]

    cost = await _charge(user_id, "ai_conference_matching")
    started = time.monotonic()
    try:
        result = await _call_llm_json(
            system="You are SYNAPTIQ's conference strategist. Rank candidate conferences. JSON only.",
            prompt=(
                f"MANUSCRIPT:\n{json.dumps(mc)}\n\nCANDIDATES:\n{json.dumps(cand_json)}\n\n"
                "Return JSON: {recommendations:[{conference_id,score(0-100),rationale,concerns}]} "
                f"top {top_n}. Consider topical fit, rank (A*/A>B/C), and whether deadline is still feasible."
            ),
            session_id=f"conference-match-{user_id}-{manuscript_id}",
        )
    except Exception:
        await refund_credits(user_id, "ai_conference_matching"); raise
    latency_ms = int((time.monotonic() - started) * 1000)

    by_id = {str(c["_id"]): c for c in candidates}
    recs = (result.get("recommendations") or [])[:top_n]
    enriched = []
    for r in recs:
        c = by_id.get(r.get("conference_id"))
        if not c: continue
        enriched.append({
            "conference": {"id": str(c["_id"]), "name": c.get("name"),
                            "acronym": c.get("acronym"), "rank": c.get("rank"),
                            "topics": c.get("topics", [])[:5],
                            "submission_deadline": c.get("submission_deadline"),
                            "start_date": c.get("start_date"),
                            "location": c.get("location"), "format": c.get("format"),
                            "website": c.get("website")},
            "score": int(r.get("score") or 0),
            "rationale": _short(r.get("rationale", ""), 600),
            "concerns": _short(r.get("concerns", ""), 280),
        })
    request_id = await _record_request(
        user_id=user_id, kind="conference_matching",
        input_summary={"manuscript_id": manuscript_id, "title": mc["title"]},
        output={"recommendations": [{"conference_id": e["conference"]["id"], "score": e["score"]} for e in enriched]},
        credits=cost, latency_ms=latency_ms, provider=DEFAULT_PROVIDER, model=DEFAULT_MODEL,
    )
    return {"request_id": request_id, "manuscript_id": manuscript_id,
            "recommendations": enriched, "credits_consumed": cost, "latency_ms": latency_ms}


# =============================== GRANT MATCHING ==============================
async def match_grants(*, user_id: str, manuscript_id: Optional[str] = None,
                       project_id: Optional[str] = None, query: Optional[str] = None,
                       top_n: int = 6) -> dict:
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    user = await db.users.find_one({"_id": ObjectId(user_id)})
    profile = {
        "research_areas": user.get("research_areas") or [],
        "institution": user.get("institution") or "",
        "country": user.get("country") or "",
        "career_stage": user.get("career_stage") or "any",
    }
    context = {"query": query or ""}
    if manuscript_id and _safe_oid(manuscript_id):
        m = await db.manuscripts.find_one({"_id": ObjectId(manuscript_id)})
        if m and user_id in m.get("authors", []):
            context["manuscript"] = _manuscript_compact(m)
    if project_id and _safe_oid(project_id):
        p = await db.projects.find_one({"_id": ObjectId(project_id)})
        if p: context["project"] = {"title": p.get("title"), "abstract": (p.get("description") or "")[:800]}

    q = (context.get("manuscript", {}).get("title") or context.get("project", {}).get("title")
         or " ".join(profile["research_areas"]) or query or "research")
    today = datetime.now(timezone.utc).date().isoformat()
    base = {"$text": {"$search": q},
            "$or": [{"deadline": {"$gte": today}}, {"deadline": None}]}
    candidates = await db.grants.find(base, {"score": {"$meta": "textScore"}}) \
        .sort([("score", {"$meta": "textScore"})]).limit(40).to_list(40)
    if len(candidates) < 8:
        extra = await db.grants.find({"deadline": {"$gte": today}}).sort("deadline", 1).limit(40 - len(candidates)).to_list(40)
        seen = {str(c["_id"]) for c in candidates}
        candidates += [c for c in extra if str(c["_id"]) not in seen]
    cand_json = [{
        "id": str(c["_id"]), "title": c.get("title"), "sponsor": c.get("sponsor"),
        "program": c.get("program"), "research_areas": c.get("research_areas", [])[:4],
        "amount": (c.get("funding_amount") or {}).get("amount"),
        "currency": (c.get("funding_amount") or {}).get("currency"),
        "deadline": c.get("deadline"), "country": c.get("country"),
        "funding_type": c.get("funding_type"), "career_stage": c.get("career_stage"),
        "abstract": (c.get("abstract_text") or c.get("summary") or "")[:400],
    } for c in candidates[:30]]

    cost = await _charge(user_id, "ai_grant_matching")
    started = time.monotonic()
    try:
        result = await _call_llm_json(
            system="You are SYNAPTIQ's funding strategist. Rank grants for a researcher. JSON only.",
            prompt=(
                f"USER PROFILE:\n{json.dumps(profile)}\n\nCONTEXT:\n{json.dumps(context)}\n\n"
                f"CANDIDATES:\n{json.dumps(cand_json)}\n\n"
                "Return JSON: {recommendations:[{grant_id,score(0-100),rationale,concerns,eligibility_match (high|medium|low)}]} "
                f"top {top_n}. Penalize geography mismatch and career-stage mismatch. Reward topic overlap."
            ),
            session_id=f"grant-match-{user_id}",
        )
    except Exception:
        await refund_credits(user_id, "ai_grant_matching"); raise
    latency_ms = int((time.monotonic() - started) * 1000)

    by_id = {str(c["_id"]): c for c in candidates}
    enriched = []
    for r in (result.get("recommendations") or [])[:top_n]:
        g = by_id.get(r.get("grant_id"))
        if not g: continue
        enriched.append({
            "grant": {"id": str(g["_id"]), "title": g.get("title"),
                       "sponsor": g.get("sponsor"), "program": g.get("program"),
                       "funding_amount": g.get("funding_amount"),
                       "deadline": g.get("deadline"), "country": g.get("country"),
                       "funding_type": g.get("funding_type"),
                       "research_areas": g.get("research_areas", [])[:4],
                       "url": g.get("url")},
            "score": int(r.get("score") or 0),
            "rationale": _short(r.get("rationale", ""), 600),
            "concerns": _short(r.get("concerns", ""), 280),
            "eligibility_match": r.get("eligibility_match", "medium"),
        })
    request_id = await _record_request(
        user_id=user_id, kind="grant_matching",
        input_summary={"manuscript_id": manuscript_id, "project_id": project_id, "query": query},
        output={"recommendations": [{"grant_id": e["grant"]["id"], "score": e["score"]} for e in enriched]},
        credits=cost, latency_ms=latency_ms, provider=DEFAULT_PROVIDER, model=DEFAULT_MODEL,
    )
    return {"request_id": request_id, "manuscript_id": manuscript_id, "project_id": project_id,
            "recommendations": enriched, "credits_consumed": cost, "latency_ms": latency_ms}


# ============================= REVIEWER MATCHING =============================
async def match_reviewers(*, user_id: str, manuscript_id: str, top_n: int = 6) -> dict:
    """Recommend reviewers from the SYNAPTIQ user network. Excludes manuscript
    authors. Includes collaboration_risk_indicator (prior collab w/ any author).
    """
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    m = await _load_manuscript(manuscript_id, user_id)
    mc = _manuscript_compact(m)
    author_ids = set(m.get("authors") or [])
    # Prior-collab risk: any project / workspace overlapping with any author
    author_projects = set()
    if author_ids:
        ap = await db.projects.find({"members": {"$in": list(author_ids)}}, {"members": 1}).to_list(200)
        for pr in ap:
            author_projects.update(pr.get("members") or [])
    # Pull a broad pool — onboarded users not in authors
    cursor = db.users.find({
        "onboarded": True, "_id": {"$nin": [ObjectId(a) for a in author_ids if _safe_oid(a)]},
    }).limit(120)
    users = await cursor.to_list(120)
    cand_json = []
    for u in users:
        cand_json.append({
            "id": str(u["_id"]),
            "name": u.get("full_name", ""), "academic_role": u.get("academic_role"),
            "institution": u.get("institution") or "",
            "research_areas": (u.get("research_areas") or [])[:6],
            "skills": (u.get("skills") or [])[:8],
            "h_index": u.get("h_index"),
            "publications_count": u.get("publications_count") or len(u.get("publications") or []),
            "prior_collab_with_authors": str(u["_id"]) in author_projects,
        })

    cost = await _charge(user_id, "ai_reviewer_matching")
    started = time.monotonic()
    try:
        result = await _call_llm_json(
            system=("You are SYNAPTIQ's peer-review coordinator. Suggest unbiased, expert reviewers. "
                    "Avoid candidates with prior_collab_with_authors=true unless their expertise is unique. JSON only."),
            prompt=(
                f"MANUSCRIPT:\n{json.dumps(mc)}\n\nRESEARCHERS:\n{json.dumps(cand_json)}\n\n"
                "Return JSON: {recommendations:[{user_id,score(0-100),rationale,concerns,expertise_areas:[]}]} "
                f"top {top_n}. Heavily weight topical+method expertise overlap with manuscript abstract."
            ),
            session_id=f"reviewer-match-{user_id}-{manuscript_id}",
        )
    except Exception:
        await refund_credits(user_id, "ai_reviewer_matching"); raise
    latency_ms = int((time.monotonic() - started) * 1000)

    by_id = {str(u["_id"]): u for u in users}
    enriched = []
    for r in (result.get("recommendations") or [])[:top_n]:
        u = by_id.get(r.get("user_id"))
        if not u: continue
        enriched.append({
            "reviewer": {"id": str(u["_id"]), "full_name": u.get("full_name", ""),
                          "avatar_url": u.get("avatar_url"),
                          "institution": u.get("institution"),
                          "academic_role": u.get("academic_role"),
                          "research_areas": (u.get("research_areas") or [])[:6],
                          "h_index": u.get("h_index"),
                          "publications_count": u.get("publications_count") or len(u.get("publications") or [])},
            "score": int(r.get("score") or 0),
            "rationale": _short(r.get("rationale", ""), 600),
            "concerns": _short(r.get("concerns", ""), 280),
            "expertise_areas": (r.get("expertise_areas") or [])[:8],
            "collaboration_risk": "high" if str(u["_id"]) in author_projects else "low",
        })
    request_id = await _record_request(
        user_id=user_id, kind="reviewer_matching",
        input_summary={"manuscript_id": manuscript_id, "title": mc["title"]},
        output={"recommendations": [{"user_id": e["reviewer"]["id"], "score": e["score"]} for e in enriched]},
        credits=cost, latency_ms=latency_ms, provider=DEFAULT_PROVIDER, model=DEFAULT_MODEL,
    )
    return {"request_id": request_id, "manuscript_id": manuscript_id,
            "recommendations": enriched, "credits_consumed": cost, "latency_ms": latency_ms}


# --------------------------- credit-charge wrapper --------------------------
async def _charge(user_id: str, action_key: str) -> int:
    """Wrapper that surfaces a friendlier 402 when credits are out. Returns the int cost."""
    try:
        res = await consume_credits(user_id, action_key)
        # consume_credits returns {"consumed": int, "balance": int, "action": str}
        if isinstance(res, dict):
            return int(res.get("consumed") or res.get("cost") or 0)
        return int(res)
    except HTTPException as e:
        if e.status_code == 402:
            raise HTTPException(status_code=402,
                detail="Not enough Research Credits for this action. Upgrade your plan or wait for monthly reset.")
        raise
