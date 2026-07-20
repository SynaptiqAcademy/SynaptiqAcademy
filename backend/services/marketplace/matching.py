"""Marketplace matching service.

Two-stage pipeline:
  1. `deterministic_rank` — fast, free: TF-IDF-lite over research areas,
     keywords, skills + Jaccard overlap; bonus for shared collaboration
     history; role-tag filter. Returns top-K candidates with sub-scores.
  2. `llm_rerank` — Claude Sonnet via the Anthropic SDK re-ranks the top
     N with a strict JSON response (score, explanation, shared interests).
     Consumes Research Credits.

Result shape:
  {
    "score": 0..100,
    "user": {...serialize_user...},
    "components": { areas: 0..100, keywords: 0..100, skills: 0..100,
                    collab_history: 0..100, activity: 0..100 },
    "shared_areas": [..], "shared_keywords": [..], "shared_skills": [..],
    "explanation": "..." (only after llm_rerank)
  }
"""
from __future__ import annotations
import logging
import os
import re
import time
from typing import Optional

from bson import ObjectId
from fastapi import HTTPException

from auth_utils import serialize_public_user
from db import get_db
from services.credits_service import consume_credits, refund_credits
from repo.shim import DBProxy
from repo.security_context import SecurityContext

logger = logging.getLogger("synaptiq.marketplace.matching")

ROLE_KEYWORDS = {
    "co_author":        ["co-author", "researcher", "phd", "professor", "postdoc"],
    "statistician":     ["statistics", "statistician", "biostatistics", "econometrics", "pls-sem", "sem", "regression"],
    "methodology":      ["methodology", "research methods", "qualitative", "quantitative", "mixed methods", "ethnography"],
    "reviewer":         ["peer review", "reviewer", "editor"],
    "ai_specialist":    ["machine learning", "deep learning", "ai", "nlp", "computer vision", "transformer", "llm"],
    "data_scientist":   ["data science", "data scientist", "analytics", "etl", "pandas", "spark"],
    "editor":           ["editor", "editorial", "copy edit", "manuscript editing"],
    "sme":              ["expert", "specialist", "subject matter"],
}


def _tokenize(text: str) -> set[str]:
    if not text: return set()
    tokens = re.split(r"[\s,;/]+", text.lower())
    return {t.strip("().[]") for t in tokens if len(t) > 2}


def _jaccard(a: set, b: set) -> float:
    if not a or not b: return 0.0
    inter = a & b
    union = a | b
    return len(inter) / max(1, len(union))


def _profile_tokens(u: dict) -> dict[str, set]:
    return {
        "areas":    set(x.lower() for x in (u.get("research_areas") or []) if x),
        "keywords": set(x.lower() for x in ((u.get("research_keywords") or []) +
                                              (u.get("research_interests") or [])) if x),
        "skills":   set(x.lower() for x in (u.get("skills") or []) if x),
        "roles":    set(x.lower() for x in (u.get("expertise_role_tags") or []) if x),
    }


def _role_match_bonus(tokens: dict, role: Optional[str]) -> float:
    """Return 0..1 bonus when role keyword appears in user's profile."""
    if not role: return 0.5
    if role in tokens["roles"]: return 1.0
    needles = ROLE_KEYWORDS.get(role, [])
    pool = " ".join(list(tokens["areas"]) + list(tokens["keywords"]) + list(tokens["skills"]))
    matched = sum(1 for n in needles if n in pool)
    return min(1.0, matched / max(2, len(needles)))


async def _collab_history_bonus(db, requester_id: str, target_id: str) -> tuple[float, int]:
    """0..1 based on # of shared workspaces / co-authored manuscripts."""
    if requester_id == target_id: return 0.0, 0
    shared_ws = await db.workspaces.count_documents(
        {"member_ids": {"$all": [requester_id, target_id]}})
    co_authored = await db.manuscripts.count_documents(
        {"author_ids": {"$all": [requester_id, target_id]}})
    n = shared_ws + co_authored
    return min(1.0, n / 3.0), n


def _score_components(req_tokens: dict, cand_tokens: dict, role: Optional[str],
                      collab_history: float) -> dict:
    areas_score    = _jaccard(req_tokens["areas"], cand_tokens["areas"]) * 100
    keywords_score = _jaccard(req_tokens["keywords"], cand_tokens["keywords"]) * 100
    skills_score   = _jaccard(req_tokens["skills"], cand_tokens["skills"]) * 100
    role_bonus     = _role_match_bonus(cand_tokens, role) * 100
    history_score  = collab_history * 100
    # Weighted overall (heavy on role + keywords).
    overall = (0.30 * role_bonus + 0.25 * keywords_score + 0.20 * areas_score +
               0.15 * skills_score + 0.10 * history_score)
    return {
        "overall": round(overall, 1),
        "areas":         round(areas_score, 1),
        "keywords":      round(keywords_score, 1),
        "skills":        round(skills_score, 1),
        "role_match":    round(role_bonus, 1),
        "collab_history": round(history_score, 1),
    }


async def deterministic_rank(
    *, requester_id: str, role: Optional[str] = None,
    q: Optional[str] = None, areas: Optional[list[str]] = None,
    skills: Optional[list[str]] = None, country: Optional[str] = None,
    institution: Optional[str] = None, availability: Optional[str] = None,
    limit: int = 50, exclude_self: bool = True,
    context_tokens: Optional[dict] = None,
) -> list[dict]:
    """Return up to `limit` ranked candidates.

    `context_tokens` lets callers (e.g. when matching for a manuscript or
    workspace) seed the requester profile with the entity's keywords/areas.
    """
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    requester = await db.users.find_one({"_id": ObjectId(requester_id)})
    if not requester: raise HTTPException(404, "Requester not found")
    req_tokens = _profile_tokens(requester)
    if context_tokens:
        for k in ("areas", "keywords", "skills"):
            req_tokens[k] |= set(context_tokens.get(k, []))

    # Pre-filter candidate set (faster than ranking everyone).
    q_filter: dict = {"is_demo": {"$ne": True}}
    if exclude_self: q_filter["_id"] = {"$ne": ObjectId(requester_id)}
    if country: q_filter["country"] = country
    if institution: q_filter["institution"] = {"$regex": institution, "$options": "i"}
    if availability: q_filter["availability"] = availability
    or_clauses: list = []
    if q:
        or_clauses.extend([
            {"full_name": {"$regex": q, "$options": "i"}},
            {"research_areas": {"$regex": q, "$options": "i"}},
            {"research_keywords": {"$regex": q, "$options": "i"}},
            {"research_interests": {"$regex": q, "$options": "i"}},
            {"skills": {"$regex": q, "$options": "i"}},
            {"biography": {"$regex": q, "$options": "i"}},
        ])
    if areas: or_clauses.append({"research_areas": {"$in": areas}})
    if skills: or_clauses.append({"skills": {"$in": skills}})
    if or_clauses: q_filter["$or"] = or_clauses
    # Pre-narrow to 400 to keep memory bounded, then rank.
    candidates = await db.users.find(q_filter).limit(400).to_list(400)

    # Enrich requester + candidates with ORCID publication signal (concepts + journals).
    cand_user_ids = [str(c["_id"]) for c in candidates] + [requester_id]
    pub_signal: dict[str, set] = {uid: set() for uid in cand_user_ids}
    if cand_user_ids:
        pubs = await db.publications.find(
            {"owner_id": {"$in": cand_user_ids}, "source": "orcid"},
            {"owner_id": 1, "concepts": 1, "topics": 1, "journal": 1}
        ).to_list(2000)
        for p in pubs:
            bag = pub_signal.setdefault(p["owner_id"], set())
            for c in (p.get("concepts") or []): bag.add(str(c).lower())
            for t in (p.get("topics") or []):   bag.add(str(t).lower())
            if p.get("journal"):                 bag.add(str(p["journal"]).lower())
    req_tokens["keywords"] |= pub_signal.get(requester_id, set())

    ranked: list[dict] = []
    for c in candidates:
        c_tokens = _profile_tokens(c)
        # Inject publication-derived keywords so ORCID-imported research signals matching.
        c_tokens["keywords"] |= pub_signal.get(str(c["_id"]), set())
        ch, ch_n = await _collab_history_bonus(db, requester_id, str(c["_id"]))
        comp = _score_components(req_tokens, c_tokens, role, ch)
        if comp["overall"] < 5: continue  # filter noise
        ranked.append({
            "score": comp["overall"],
            "user": serialize_public_user(c),
            "components": comp,
            "shared_areas":    sorted(req_tokens["areas"] & c_tokens["areas"])[:5],
            "shared_keywords": sorted(req_tokens["keywords"] & c_tokens["keywords"])[:5],
            "shared_skills":   sorted(req_tokens["skills"] & c_tokens["skills"])[:5],
            "collab_history_count": ch_n,
        })
    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked[:limit]


# ----------------------------- LLM RERANK -----------------------------------
RERANK_SYSTEM = """You are an expert academic matchmaker. Given a research \
seeker and a list of candidate researchers, you assess fit and produce a \
ranked JSON list. Output STRICTLY valid JSON, no prose, no markdown."""

RERANK_PROMPT_TMPL = """Seeker profile:
{seeker_brief}

Context (if any):
{context}

Role required: {role}

Candidates (top deterministic matches; choose and explain the best fits):
{candidates}

Respond with JSON:
{{
  "rankings": [
    {{
      "user_id": "<candidate id>",
      "score": 0-100,
      "shared_interests": ["..."],
      "why_relevant": "1-2 sentence concrete reason",
      "concerns": "1 sentence or null"
    }}
  ]
}}

Pick the {top_n} best fits. Use the candidate ids exactly as given. Be \
specific about overlap; avoid generic praise."""


def _compact_user(u: dict) -> str:
    parts = [
        f"id={u.get('id')}",
        f"name={u.get('full_name')}",
        f"role={u.get('academic_role')}",
        f"inst={u.get('institution')}",
        f"areas={(u.get('research_areas') or [])[:6]}",
        f"keywords={(u.get('research_interests') or u.get('research_keywords') or [])[:8]}",
        f"skills={(u.get('skills') or [])[:6]}",
        f"avail={u.get('availability')}",
    ]
    return " | ".join(str(p) for p in parts if p)


async def llm_rerank(
    *, requester_id: str, candidates: list[dict], role: Optional[str] = None,
    context: Optional[str] = None, top_n: int = 10,
) -> dict:
    """Rerank `candidates` using LLM; consumes credits.

    `candidates` is the output of `deterministic_rank` (top-50). We pass the
    top 25 to keep prompt small.
    """
    if not candidates:
        return {"rankings": [], "credits_consumed": 0, "latency_ms": 0}

    from services.ai.llm import call_llm
    import json as _json

    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    seeker = await db.users.find_one({"_id": ObjectId(requester_id)})
    seeker_brief = _compact_user(serialize_public_user(seeker)) if seeker else f"id={requester_id}"

    cand_subset = candidates[:25]
    cand_text = "\n".join(f"- {_compact_user(c['user'])}" for c in cand_subset)

    # Charge credits up front; refund on LLM failure.
    charged = await consume_credits(requester_id, "ai_marketplace_rerank",
                                     metadata={"role": role, "n": len(cand_subset)})
    cost = charged.get("consumed", 5) if isinstance(charged, dict) else 5
    t0 = time.time()
    try:
        prompt = RERANK_PROMPT_TMPL.format(
            seeker_brief=seeker_brief, context=context or "(none)",
            role=role or "any", candidates=cand_text, top_n=top_n,
        )
        text = await call_llm(
            system=RERANK_SYSTEM,
            user_msg=prompt,
            feature="marketplace.matching",
            provider=os.environ.get("AI_MATCHING_PROVIDER", "anthropic"),
            model=os.environ.get("AI_MATCHING_MODEL", "claude-sonnet-4-6"),
        )
        m = re.search(r"\{[\s\S]*\}", text)
        parsed = _json.loads(m.group(0)) if m else {"rankings": []}
    except Exception as e:
        await refund_credits(requester_id, cost, reason="ai_marketplace_rerank_failed")
        raise HTTPException(503, f"LLM rerank failed: {str(e)[:200]}")

    latency_ms = int((time.time() - t0) * 1000)
    rankings = parsed.get("rankings", []) or []

    # Merge LLM output back onto candidate cards.
    by_id = {c["user"]["id"]: c for c in cand_subset}
    enriched: list[dict] = []
    for r in rankings[:top_n]:
        c = by_id.get(r.get("user_id"))
        if not c: continue
        merged = {**c}
        merged["llm_score"]        = int(r.get("score") or merged["score"])
        merged["explanation"]      = r.get("why_relevant") or ""
        merged["shared_interests"] = r.get("shared_interests") or merged.get("shared_keywords") or []
        merged["concerns"]         = r.get("concerns") or None
        enriched.append(merged)

    # Audit
    await db.ai_requests.insert_one({
        "user_id": requester_id, "kind": "marketplace_rerank",
        "input": {"role": role, "context_len": len(context or ""), "n_candidates": len(cand_subset)},
        "output_excerpt": [{"user_id": e["user"]["id"], "score": e["llm_score"]} for e in enriched],
        "credits_consumed": cost, "latency_ms": latency_ms,
        "provider": os.environ.get("AI_MATCHING_PROVIDER", "anthropic"),
        "model": os.environ.get("AI_MATCHING_MODEL", "claude-sonnet-4-6"),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S.000+00:00", time.gmtime()),
    })
    return {"rankings": enriched, "credits_consumed": cost, "latency_ms": latency_ms}
