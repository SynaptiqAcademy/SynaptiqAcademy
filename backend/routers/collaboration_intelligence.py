"""Collaboration Intelligence — AI-powered researcher matchmaking.

Analyses the current user's research profile and finds the most compatible
researchers in the platform using a two-stage approach:
  1. Local pre-scoring via field overlap (research areas, keywords, skills)
  2. Claude enrichment for ranked compatibility scores + transparent explanations

Endpoints:
  POST /api/collaboration-intelligence/generate    — run fresh recommendations (15 credits)
  GET  /api/collaboration-intelligence/recommendations — return latest cached recommendations
  GET  /api/collaboration-intelligence/history     — list past generation runs
  GET  /api/collaboration-intelligence/{run_id}    — fetch one run (owner only)
"""
from __future__ import annotations

import json
import logging
import math
import time
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from db import get_db
from services.ai.llm import call_llm
from services.credits_service import consume_credits, refund_credits
from services.permissions import require_feature
from repo.shim import DBProxy
from repo.security_context import SecurityContext

log = logging.getLogger("synaptiq.collaboration_intelligence")
router = APIRouter(prefix="/api/collaboration-intelligence", tags=["collaboration-intelligence"])

_MAX_CANDIDATES = 100
_PRESCORE_POOL = 15   # pre-score this many, send top N to Claude
_CLAUDE_POOL = 10     # how many candidates Claude scores per run


# ──────────────────────────────── request model ──────────────────────────────

class GenerateRequest(BaseModel):
    research_areas:  list[str] = Field(default_factory=list, max_length=10)
    methods:         list[str] = Field(default_factory=list, max_length=10)
    country:         Optional[str] = Field(None, max_length=100)
    user_type:       Optional[str] = Field(None, max_length=50)
    primary_domain:  Optional[str] = Field(None, max_length=20)
    min_score:       int = Field(default=0, ge=0, le=100)


# ──────────────────────────────── pre-scorer ─────────────────────────────────

def _safe_set(values) -> set:
    if not values:
        return set()
    return {str(v).lower().strip() for v in values if v}


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    union = a | b
    return len(a & b) / len(union)


def _prescore(user: dict, candidate: dict) -> dict:
    """Fast local similarity estimate. Returns 0-100 integer pre-score + overlaps."""
    u_areas   = _safe_set(user.get("research_areas"))
    c_areas   = _safe_set(candidate.get("research_areas"))
    u_kw      = _safe_set(user.get("research_keywords"))
    c_kw      = _safe_set(candidate.get("research_keywords"))
    u_skills  = _safe_set(user.get("skills"))
    c_skills  = _safe_set(candidate.get("skills"))
    u_looking = _safe_set(user.get("looking_for"))
    c_offers  = _safe_set(candidate.get("can_contribute"))
    c_looking = _safe_set(candidate.get("looking_for"))
    u_offers  = _safe_set(user.get("can_contribute"))

    area_sim   = _jaccard(u_areas, c_areas)
    kw_sim     = _jaccard(u_kw, c_kw)
    skill_sim  = _jaccard(u_skills, c_skills)
    need_match = len((u_looking & c_offers) | (c_looking & u_offers))

    # Weighted components → max 100
    topic_raw  = min(30, int(area_sim * 30 + kw_sim * 10))
    method_raw = min(20, int(skill_sim * 20))
    collab_raw = min(15, need_match * 5)
    # Publication and funding gaps are filled by Claude
    total = topic_raw + method_raw + collab_raw

    return {
        "prescore": min(100, total),
        "area_overlap":  list(u_areas & c_areas)[:6],
        "kw_overlap":    list(u_kw & c_kw)[:8],
        "skill_overlap": list(u_skills & c_skills)[:6],
    }


# ──────────────────────────────── Claude prompt ──────────────────────────────

_USER_TEMPLATE = """\
Score the compatibility between RESEARCHER A (the user) and each CANDIDATE below.

RESEARCHER A:
Name:            {name}
Role:            {role}
Institution:     {institution}
Country:         {country}
Research Areas:  {research_areas}
Keywords:        {keywords}
Skills:          {skills}
Looking For:     {looking_for}
Can Contribute:  {can_contribute}
Publications:    {publications_count}

CANDIDATES (score each separately):
{candidates_block}

Return a JSON object with this exact schema:
{{
  "recommendations": [
    {{
      "candidate_id": "<the id field from the candidate>",
      "compatibility_score": <integer 0-100>,
      "score_components": {{
        "topic_match": <integer 0-30, how well research themes align>,
        "method_match": <integer 0-20, how well methods/skills align>,
        "publication_match": <integer 0-20, inferred from publication counts and areas>,
        "funding_match": <integer 0-15, alignment on goals and looking_for>,
        "collaboration_potential": <integer 0-15, complementarity of offerings>
      }},
      "why_text": "<exactly two sentences naming specific data from both profiles>",
      "match_reasons": [
        "<specific reason 1 — name exact shared topic, skill, or goal>",
        "<specific reason 2>",
        "<specific reason 3>"
      ],
      "complementary_strengths": [
        "<what the candidate offers that researcher A may lack>"
      ],
      "potential_collaboration_types": [
        "<e.g., Co-authored journal article on X>",
        "<e.g., Joint grant application for Y>"
      ],
      "caution": "<one sentence on any potential friction, or null if none>"
    }}
  ]
}}

The recommendations array must contain exactly {n} items, one per candidate,
in the same order as the CANDIDATES block above.\
"""


def _profile_block(idx: int, cid: str, p: dict) -> str:
    role_line = p.get("user_type") or ""
    if p.get("academic_role"):
        role_line = f"{role_line} ({p['academic_role']})" if role_line else p["academic_role"]
    if not role_line:
        role_line = "Researcher"
    domain = p.get("primary_domain") or ""
    return (
        f"[{idx + 1}] id: {cid}\n"
        f"    Name:            {p.get('full_name') or 'Unknown'}\n"
        f"    Type:            {role_line}\n"
        f"    Primary Domain:  {domain or 'Not specified'}\n"
        f"    Institution:     {p.get('institution') or 'Unknown'}\n"
        f"    Country:         {p.get('country') or 'Unknown'}\n"
        f"    Research Areas:  {', '.join(p.get('research_areas') or []) or 'Not specified'}\n"
        f"    Keywords:        {', '.join(p.get('research_keywords') or []) or 'Not specified'}\n"
        f"    Skills:          {', '.join(p.get('skills') or []) or 'Not specified'}\n"
        f"    Looking For:     {', '.join(p.get('looking_for') or []) or 'Not specified'}\n"
        f"    Can Contribute:  {', '.join(p.get('can_contribute') or []) or 'Not specified'}\n"
        f"    Publications:    {p.get('publications_count') or 0}"
    )


async def _run_claude(
    user: dict,
    candidates: list[dict],
    *,
    user_id: str | None = None,
    db=None,
) -> list[dict]:
    """Call the AI gateway to score and explain compatibility for each candidate."""
    candidates_block = "\n\n".join(
        _profile_block(i, str(c["_id"]), c) for i, c in enumerate(candidates)
    )
    _user_role_line = user.get("user_type") or ""
    if user.get("academic_role"):
        _user_role_line = (
            f"{_user_role_line} ({user['academic_role']})" if _user_role_line else user["academic_role"]
        )
    user_message = _USER_TEMPLATE.format(
        name=user.get("full_name") or "Researcher",
        role=_user_role_line or "Researcher",
        institution=user.get("institution") or "Unknown",
        country=user.get("country") or "Unknown",
        research_areas=", ".join(user.get("research_areas") or []) or "Not specified",
        keywords=", ".join(user.get("research_keywords") or []) or "Not specified",
        skills=", ".join(user.get("skills") or []) or "Not specified",
        looking_for=", ".join(user.get("looking_for") or []) or "Not specified",
        can_contribute=", ".join(user.get("can_contribute") or []) or "Not specified",
        publications_count=user.get("publications_count") or 0,
        candidates_block=candidates_block,
        n=len(candidates),
    )

    raw = await call_llm(
        prompt_id="collaboration.researcher_matching",
        variables={"user_message": user_message},
        feature="collaboration.researcher_matching",
        user_id=user_id,
        db=db,
        max_tokens=6000,
    )
    text = raw.strip()
    if text.startswith("```"):
        parts = text.split("```", 2)
        inner = parts[1] if len(parts) >= 2 else text
        if inner.startswith("json"):
            inner = inner[4:]
        text = inner.strip()
        if "```" in text:
            text = text.split("```")[0].strip()

    try:
        parsed = json.loads(text)
        return parsed.get("recommendations", [])
    except json.JSONDecodeError as exc:
        log.error("Collaboration Intelligence JSON parse failed: %s | raw[:500]=%s", exc, text[:500])
        raise HTTPException(502, "Recommendation engine returned malformed output. Please try again.")


# ──────────────────────────────── helpers ────────────────────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ser_doc(d: dict) -> dict:
    d = dict(d)
    if "_id" in d:
        d["id"] = str(d.pop("_id"))
    return d


def _public_profile(u: dict) -> dict:
    """Return only public-safe fields for embedding in recommendation results."""
    return {
        "id":               str(u["_id"]),
        "full_name":        u.get("full_name") or "",
        "academic_role":    u.get("academic_role") or "",
        "user_type":        u.get("user_type") or None,
        "primary_domain":   u.get("primary_domain") or None,
        "institution":      u.get("institution") or "",
        "department":       u.get("department") or "",
        "country":          u.get("country") or "",
        "research_areas":   u.get("research_areas") or [],
        "research_keywords": u.get("research_keywords") or [],
        "skills":           u.get("skills") or [],
        "looking_for":      u.get("looking_for") or [],
        "can_contribute":   u.get("can_contribute") or [],
        "publications_count": u.get("publications_count") or 0,
        "avatar_url":       u.get("avatar_url") or None,
        "orcid":            u.get("orcid") or None,
        "biography":        u.get("biography") or "",
    }


# ──────────────────────────────── endpoints ──────────────────────────────────

@router.post("/generate")
async def generate_recommendations(
    body: GenerateRequest,
    user: dict = Depends(require_feature("collaboration_intelligence")),
):
    """Generate fresh collaboration recommendations. Costs 15 credits."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    user_id = user["id"]

    # Fetch full user profile (auth token may have stale data)
    full_user = await db.users.find_one({"_id": ObjectId(user_id)})
    if not full_user:
        raise HTTPException(404, "User not found")

    # Build candidate query — exclude demo accounts from AI recommendations
    candidate_filter: dict = {
        "_id":                {"$ne": ObjectId(user_id)},
        "onboarding_complete": True,
        "is_demo":            {"$ne": True},
    }
    if body.country:
        candidate_filter["country"] = body.country
    if body.user_type:
        candidate_filter["user_type"] = body.user_type
    if body.primary_domain:
        candidate_filter["primary_domain"] = body.primary_domain
    if body.research_areas:
        candidate_filter["research_areas"] = {"$in": body.research_areas}

    # Charge credits
    charged = await consume_credits(
        user_id, "ai_collaboration_intelligence",
        metadata={"filters": {
            "research_areas": body.research_areas[:3],
            "country": body.country,
            "user_type": body.user_type,
            "primary_domain": body.primary_domain,
        }},
    )
    credits_used = charged.get("consumed", 15)

    started = time.monotonic()
    try:
        # Fetch candidates
        raw_candidates = await db.users.find(
            candidate_filter,
            {
                "password_hash": 0, "email": 0,
                "reset_token": 0, "refresh_token": 0,
            },
        ).limit(_MAX_CANDIDATES).to_list(_MAX_CANDIDATES)

        if not raw_candidates:
            # No candidates found — refund and return empty
            await refund_credits(user_id, "ai_collaboration_intelligence",
                                 reason="No candidates found in platform")
            return {
                "id": None,
                "recommendations": [],
                "credits_used": 0,
                "created_at": _now(),
                "message": "No other researchers found matching your filters. Try broadening your search.",
            }

        # Pre-score all candidates
        prescored = []
        for c in raw_candidates:
            sc = _prescore(full_user, c)
            prescored.append((sc["prescore"], sc, c))

        prescored.sort(key=lambda x: x[0], reverse=True)
        top_candidates = [c for _, _, c in prescored[:_CLAUDE_POOL]]

        # AI enrichment via gateway
        claude_recs = await _run_claude(full_user, top_candidates, user_id=user_id, db=db)

    except HTTPException:
        await refund_credits(user_id, "ai_collaboration_intelligence",
                             reason="Recommendation engine error")
        raise
    except Exception as exc:
        await refund_credits(user_id, "ai_collaboration_intelligence",
                             reason="Unexpected error")
        log.error("Collaboration intelligence failed: %s", exc)
        raise HTTPException(503, "Recommendation engine failed. Credits refunded.")

    # Merge Claude results with candidate profiles
    candidate_map = {str(c["_id"]): c for c in top_candidates}
    enriched = []
    for rec in claude_recs:
        cid = rec.get("candidate_id", "")
        candidate = candidate_map.get(cid)
        if not candidate:
            continue
        score = rec.get("compatibility_score", 0)
        if score < body.min_score:
            continue
        enriched.append({
            **rec,
            "researcher": _public_profile(candidate),
        })

    # Sort by score descending
    enriched.sort(key=lambda r: r.get("compatibility_score", 0), reverse=True)

    # Persist collaboration_scores (individual pair records)
    now = _now()
    if enriched:
        score_docs = []
        for r in enriched:
            score_docs.append({
                "requester_id":    user_id,
                "candidate_id":    r.get("candidate_id"),
                "compatibility_score": r.get("compatibility_score", 0),
                "score_components":    r.get("score_components", {}),
                "why_text":            r.get("why_text", ""),
                "match_reasons":       r.get("match_reasons", []),
                "complementary_strengths": r.get("complementary_strengths", []),
                "potential_collaboration_types": r.get("potential_collaboration_types", []),
                "caution":             r.get("caution"),
                "created_at":          now,
            })
        await db.collaboration_scores.insert_many(score_docs)

    # Persist recommendation run
    run_doc = {
        "user_id":              user_id,
        "recommendations":      enriched,
        "recommendation_count": len(enriched),
        "filters_used": {
            "research_areas": body.research_areas,
            "methods":        body.methods,
            "country":        body.country,
            "user_type":      body.user_type,
            "primary_domain": body.primary_domain,
            "min_score":      body.min_score,
        },
        "credits_used":         credits_used,
        "created_at":           now,
    }
    result = await db.collaboration_recommendations.insert_one(run_doc)
    run_doc["_id"] = result.inserted_id

    try:
        await db.ai_requests.insert_one({
            "user_id":     user_id,
            "feature":     "ai_collaboration_intelligence",
            "credits":     credits_used,
            "duration_ms": int((time.monotonic() - started) * 1000),
            "success":     True,
            "ref_id":      str(result.inserted_id),
            "created_at":  now,
        })
    except Exception:
        pass

    return _ser_doc(run_doc)


@router.get("/recommendations")
async def get_latest_recommendations(
    research_area:  Optional[str] = Query(None),
    country:        Optional[str] = Query(None),
    user_type:      Optional[str] = Query(None),
    primary_domain: Optional[str] = Query(None),
    min_score:      int = Query(default=0, ge=0, le=100),
    user: dict = Depends(get_current_user),
):
    """Return the user's most recent recommendation run, optionally filtered."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    run = await db.collaboration_recommendations.find_one(
        {"user_id": user["id"]},
        sort=[("created_at", -1)],
    )
    if not run:
        return {"recommendations": [], "run": None}

    recs = run.get("recommendations", [])

    # Apply post-fetch filters
    if research_area:
        area_lower = research_area.lower()
        recs = [
            r for r in recs
            if area_lower in [a.lower() for a in (r.get("researcher", {}).get("research_areas") or [])]
        ]
    if country:
        recs = [
            r for r in recs
            if (r.get("researcher", {}).get("country") or "").lower() == country.lower()
        ]
    if user_type:
        recs = [
            r for r in recs
            if (r.get("researcher", {}).get("user_type") or "") == user_type
        ]
    if primary_domain:
        recs = [
            r for r in recs
            if (r.get("researcher", {}).get("primary_domain") or "") == primary_domain
        ]
    if min_score > 0:
        recs = [r for r in recs if r.get("compatibility_score", 0) >= min_score]

    run_meta = {
        "id":               str(run["_id"]),
        "created_at":       run.get("created_at"),
        "recommendation_count": run.get("recommendation_count", 0),
        "filters_used":     run.get("filters_used", {}),
        "credits_used":     run.get("credits_used", 0),
    }
    return {"recommendations": recs, "run": run_meta}


@router.get("/history")
async def list_runs(user: dict = Depends(get_current_user)):
    """List past recommendation runs for the current user (no embedded recommendations)."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    runs = await db.collaboration_recommendations.find(
        {"user_id": user["id"]},
        {"recommendations": 0},
    ).sort("created_at", -1).to_list(50)
    return [_ser_doc(r) for r in runs]


@router.get("/{run_id}")
async def get_run(run_id: str, user: dict = Depends(get_current_user)):
    """Fetch one recommendation run by ID. Owner only."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(run_id)
    except Exception:
        raise HTTPException(404, "Not found")
    run = await db.collaboration_recommendations.find_one({"_id": oid})
    if not run:
        raise HTTPException(404, "Not found")
    if run["user_id"] != user["id"]:
        raise HTTPException(403, "Forbidden")
    return _ser_doc(run)
