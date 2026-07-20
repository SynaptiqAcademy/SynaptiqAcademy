"""AI Research Gap Finder — identify publishable research gaps via Claude.

A researcher submits a topic, research question, and keywords. Claude analyses
the state of the field and returns a twelve-section gap analysis: over-studied
and under-studied areas, contradictions, methodological/geographic/population/data
gaps, emerging opportunities, a publication-potential score, and ten ranked
publishable research questions with rationale and novelty assessments.

Endpoints:
  POST /api/research-gap-finder          — run analysis (costs 10 credits)
  GET  /api/research-gap-finder/history  — list caller's past analyses
  GET  /api/research-gap-finder/{id}     — fetch one analysis (owner only)
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from db import get_db
from services.ai.llm import call_llm
from services.credits_service import consume_credits, refund_credits
from services.permissions import require_feature
from repo.shim import DBProxy
from repo.security_context import SecurityContext

log = logging.getLogger("synaptiq.research_gap_finder")
router = APIRouter(prefix="/api/research-gap-finder", tags=["research-gap-finder"])


# ──────────────────────────────── request model ──────────────────────────────

class GapFinderRequest(BaseModel):
    topic:                  str = Field(..., min_length=3, max_length=300)
    research_question:      str = Field(..., min_length=10, max_length=1000)
    keywords:               list[str] = Field(..., min_length=1, max_length=20)
    discipline:             Optional[str] = Field(None, max_length=100)
    methodology_preference: Optional[str] = Field(None, max_length=200)
    year_from:              Optional[int] = Field(None, ge=1900, le=2100)
    year_to:                Optional[int] = Field(None, ge=1900, le=2100)
    target_journal_type:    Optional[str] = Field(None, max_length=200)


# ──────────────────────────────── Claude prompt ──────────────────────────────

_SYSTEM = """\
You are a senior research strategist and bibliometric expert who specialises in
identifying publishable research gaps. You have deep knowledge of academic literature
across disciplines and can distinguish genuinely novel directions from incremental work.

ACCURACY RULES — strictly followed:
1. Do not invent specific papers, authors, journal titles, volume numbers, or DOIs.
2. Draw only on knowledge from your training data. If a field is outside your expertise,
   state this explicitly rather than inventing plausible-sounding content.
3. Be specific: name real methodologies, real theoretical traditions, real geographic
   regions, and real population groups where you have genuine knowledge.
4. When you are uncertain, qualify your assessment: "Based on available evidence…",
   "Evidence on this is limited…", "This appears underexplored, though verification
   with a live database search is recommended."
5. Distinguish between gaps that are under-researched because they are genuinely novel
   versus those that are neglected for practical reasons (e.g. data access, ethics).
6. The publication potential score must reflect realistic academic publishing conditions
   for the topic — not an optimistic estimate to please the researcher.

Return ONLY a single valid JSON object — no markdown fences, no preamble, no commentary.\
"""

_PROMPT = """\
Perform a comprehensive research gap analysis for the following topic. Your goal is to
identify the most compelling and genuinely publishable opportunities a researcher could
pursue, based on what the field has and has not covered.

TOPIC:               {topic}
RESEARCH QUESTION:   {research_question}
KEYWORDS:            {keywords}
DISCIPLINE:          {discipline}
METHODOLOGY PREF:    {methodology_preference}
YEAR RANGE:          {year_range}
TARGET JOURNAL TYPE: {target_journal_type}

Return a JSON object that matches this exact schema. All string fields must be substantive.
Do not use filler phrases like "further research is needed" without specific context.

{{
  "topic_overview": {{
    "summary": "<2-4 sentences accurately characterising this field and its research landscape>",
    "maturity_level": "emerging | developing | mature | saturated",
    "research_volume": "<characterisation of how much literature exists — sparse / moderate / extensive / very extensive>",
    "key_disciplines_involved": ["<discipline>"],
    "knowledge_basis_note": "<honest note on how well Claude knows this specific topic>"
  }},
  "current_state_of_research": {{
    "dominant_paradigms": ["<paradigm or theoretical approach that dominates the field>"],
    "established_consensus": ["<specific area of strong agreement in the literature>"],
    "active_frontiers": ["<area currently attracting significant new research attention>"],
    "synthesis": "<paragraph synthesising the current research landscape>"
  }},
  "highly_studied_areas": [
    {{
      "area": "<specific over-researched area or angle>",
      "reason": "<why this area is saturated>",
      "saturation_signal": "<observable signal that it is over-studied — e.g. diminishing marginal returns, meta-analyses exist, journals declining submissions>"
    }}
  ],
  "underexplored_areas": [
    {{
      "area": "<specific underexplored area>",
      "explanation": "<what is missing and why it matters>",
      "why_neglected": "<practical or historical reason this area was avoided>",
      "opportunity_level": "high | medium | low"
    }}
  ],
  "contradictory_findings": [
    {{
      "topic": "<the specific issue where contradictions exist>",
      "position_a": "<one side of the contradiction>",
      "position_b": "<the other side>",
      "source_of_disagreement": "<why this contradiction exists — methodological, definitional, sample differences, etc.>",
      "resolution_opportunity": "<how a new study could resolve this>"
    }}
  ],
  "methodological_gaps": [
    {{
      "gap": "<specific methodological gap>",
      "current_approach": "<what researchers typically do now>",
      "missing_approach": "<what is not being done and should be>",
      "impact": "<what answering this methodologically would unlock>"
    }}
  ],
  "geographic_gaps": [
    {{
      "region": "<specific region, country, or context>",
      "nature_of_gap": "<what type of research is absent for this region>",
      "why_it_matters": "<why this geographic perspective is important>"
    }}
  ],
  "population_gaps": [
    {{
      "population": "<specific population group>",
      "nature_of_gap": "<what is missing for this group>",
      "why_it_matters": "<scientific or social significance>"
    }}
  ],
  "data_gaps": [
    {{
      "gap": "<specific type of data that is absent or inadequate>",
      "what_is_missing": "<precise description of the missing data>",
      "potential_impact_if_addressed": "<what new knowledge this would enable>"
    }}
  ],
  "emerging_opportunities": [
    {{
      "opportunity": "<specific emerging research opportunity>",
      "driving_forces": "<what is driving this opportunity — new technology, social change, policy shift, etc.>",
      "window_of_opportunity": "<is this time-sensitive, and why>",
      "interdisciplinary_potential": "<what adjacent disciplines could contribute>"
    }}
  ],
  "publication_potential": {{
    "score": <integer 0-100 reflecting realistic publication prospects for new work in this area>,
    "assessment": "<honest 3-4 sentence assessment of publication difficulty, competition, and opportunity>",
    "strongest_angle": "<the single most publishable gap or angle identified above>",
    "recommended_journal_types": ["<e.g. interdisciplinary journals, specialist journals, open-access, etc.>"],
    "timing_advantage": "<whether the field timing favours publication now — and why>"
  }},
  "publishable_research_questions": [
    {{
      "question": "<specific, answerable research question — not a broad topic>",
      "rationale": "<why this question has not been answered and why it matters>",
      "novelty": "<precisely what is novel — this must be specific, not generic>",
      "publication_potential": "high | medium | low",
      "suggested_methodology": "<most appropriate method to answer this question>",
      "target_journal_type": "<type of journal this would fit — e.g. 'high-impact general science', 'specialist clinical', 'interdisciplinary'>"
    }}
  ]
}}

The publishable_research_questions array must contain exactly 10 items, ordered from highest
to lowest publication potential. Each question must be specific enough that a researcher
could begin designing a study from it today.\
"""


async def _run_gap_analysis(req: GapFinderRequest) -> dict:
    year_range = "Not specified"
    if req.year_from and req.year_to:
        year_range = f"{req.year_from}–{req.year_to}"
    elif req.year_from:
        year_range = f"{req.year_from} onwards"
    elif req.year_to:
        year_range = f"up to {req.year_to}"

    prompt = _PROMPT.format(
        topic=req.topic,
        research_question=req.research_question,
        keywords=", ".join(req.keywords),
        discipline=req.discipline or "Not specified",
        methodology_preference=req.methodology_preference or "No preference",
        year_range=year_range,
        target_journal_type=req.target_journal_type or "Not specified",
    )

    raw = await call_llm(
        system=_SYSTEM,
        user_msg=prompt,
        feature="research_gap.finder",
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
        return json.loads(text)
    except json.JSONDecodeError as exc:
        log.error("Gap analysis JSON parse failed: %s | raw[:500]=%s", exc, text[:500])
        raise HTTPException(502, "Analysis engine returned malformed output. Please try again.")


def _extract_publication_score(gap_json: dict) -> int:
    try:
        score = gap_json["publication_potential"]["score"]
        return int(score) if isinstance(score, (int, float)) and 0 <= score <= 100 else 0
    except (KeyError, TypeError, ValueError):
        return 0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ser(d: dict) -> dict:
    d = dict(d)
    d["id"] = str(d.pop("_id"))
    return d


# ──────────────────────────────── endpoints ──────────────────────────────────

@router.post("")
async def create_analysis(
    body: GapFinderRequest,
    user: dict = Depends(require_feature("ai_research_gap_finder")),
):
    """Run a research gap analysis. Costs 10 credits; refunded automatically on failure."""
    charged = await consume_credits(
        user["id"], "ai_research_gap_finder",
        metadata={"topic": body.topic[:100], "keywords": body.keywords[:5]},
    )
    credits_used = charged.get("consumed", 10)

    started = time.monotonic()
    try:
        gap_json = await _run_gap_analysis(body)
    except HTTPException:
        await refund_credits(user["id"], "ai_research_gap_finder", reason="Analysis engine error")
        raise
    except Exception as exc:
        await refund_credits(user["id"], "ai_research_gap_finder", reason="Unexpected error")
        log.error("Research gap analysis failed: %s", exc)
        raise HTTPException(503, "Analysis failed. Your credits have been refunded.")
    duration_ms = int((time.monotonic() - started) * 1000)

    publication_score = _extract_publication_score(gap_json)

    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    doc = {
        "user_id":          user["id"],
        "topic":            body.topic,
        "research_question": body.research_question,
        "keywords":         body.keywords,
        "discipline":       body.discipline,
        "methodology_preference": body.methodology_preference,
        "year_from":        body.year_from,
        "year_to":          body.year_to,
        "target_journal_type": body.target_journal_type,
        "gap_json":         gap_json,
        "publication_score": publication_score,
        "credits_used":     credits_used,
        "created_at":       _now(),
    }
    result = await db.research_gap_reviews.insert_one(doc)
    doc["_id"] = result.inserted_id

    try:
        await db.ai_requests.insert_one({
            "user_id":     user["id"],
            "feature":     "ai_research_gap_finder",
            "credits":     credits_used,
            "duration_ms": duration_ms,
            "success":     True,
            "ref_id":      str(result.inserted_id),
            "created_at":  _now(),
        })
    except Exception:
        pass

    return _ser(doc)


@router.get("/history")
async def list_analyses(user: dict = Depends(get_current_user)):
    """Return the authenticated user's gap analyses, newest first.
    The heavy gap_json field is excluded from list results."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    docs = await db.research_gap_reviews.find(
        {"user_id": user["id"]},
        {"gap_json": 0},
    ).sort("created_at", -1).to_list(50)
    return [_ser(d) for d in docs]


@router.get("/{analysis_id}")
async def get_analysis(analysis_id: str, user: dict = Depends(get_current_user)):
    """Fetch one gap analysis by ID. Only the owner may access it."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(analysis_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.research_gap_reviews.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    if doc["user_id"] != user["id"]:
        raise HTTPException(403, "Forbidden")
    return _ser(doc)
