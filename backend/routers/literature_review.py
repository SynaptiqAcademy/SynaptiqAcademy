"""AI Literature Review — structured academic literature synthesis via Claude.

A researcher submits a topic, research question, and keywords. Claude synthesises
the state of the field into a ten-section structured review including themes,
authors, theoretical foundations, methodological trends, debates, and a
publication-quality draft narrative.

Endpoints:
  POST /api/literature-review          — generate review (costs 20 credits)
  GET  /api/literature-review/history  — list caller's past reviews (newest first)
  GET  /api/literature-review/{id}     — fetch one review by id (owner only)
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

log = logging.getLogger("synaptiq.literature_review")
router = APIRouter(prefix="/api/literature-review", tags=["literature-review"])


# ─────────────────────────────── request model ───────────────────────────────

class LiteratureReviewRequest(BaseModel):
    topic:                  str = Field(..., min_length=3, max_length=300)
    research_question:      str = Field(..., min_length=10, max_length=1000)
    keywords:               list[str] = Field(..., min_length=1, max_length=20)
    discipline:             Optional[str] = Field(None, max_length=100)
    methodology_preference: Optional[str] = Field(None, max_length=200)
    year_from:              Optional[int] = Field(None, ge=1900, le=2100)
    year_to:                Optional[int] = Field(None, ge=1900, le=2100)


# ─────────────────────────────── Claude prompt ───────────────────────────────

_SYSTEM = """\
You are a distinguished academic scholar with expertise across multiple disciplines,
experienced in conducting systematic and narrative literature reviews for high-impact
journals. Your reviews are analytically rigorous, intellectually honest, and
synthesise concepts rather than merely enumerate studies.

ACCURACY RULES — strictly observed:
1. Reference only scholars and works you genuinely know exist from your training data.
   If uncertain about a specific citation, describe the intellectual tradition in general
   terms rather than attribute it to a person you are unsure about.
2. Do not fabricate journal names, volume numbers, page numbers, or DOIs.
3. If a subtopic is underexplored in your training data, say so explicitly.
4. Avoid generic filler phrases such as "many scholars argue" without substance.
5. The literature draft (section 10) must read as publication-quality academic prose —
   not a list reformatted into sentences.

Return ONLY a single valid JSON object — no markdown fences, no preamble, no commentary.\
"""

_PROMPT = """\
Produce a comprehensive, analytically rigorous literature review on the following topic.

TOPIC:                  {topic}
RESEARCH QUESTION:      {research_question}
KEYWORDS:               {keywords}
DISCIPLINE:             {discipline}
METHODOLOGY PREFERENCE: {methodology_preference}
PUBLICATION YEAR RANGE: {year_range}

Return a JSON object that matches this exact schema. All string fields must be substantive —
never leave them as empty strings or generic placeholders.

{{
  "executive_summary": {{
    "overview": "<3–5 sentence synthesis of the current state of the field>",
    "scope_assessment": "<what aspects of the topic are well-studied vs. sparse in the literature>",
    "review_confidence": "<assessment of how mature and well-evidenced this literature base is>"
  }},
  "major_themes": [
    {{
      "theme": "<concise theme title>",
      "explanation": "<substantive explanation of this theme in the literature>",
      "importance": "<why this theme matters for the field>",
      "current_direction": "<where this theme is heading in current research>"
    }}
  ],
  "key_authors": [
    {{
      "name": "<scholar's full name — only include if you are confident they exist>",
      "affiliation": "<institution if known, otherwise null>",
      "primary_contribution": "<what this scholar specifically contributed to the field>",
      "notable_works": ["<actual work title — only if you are confident it exists>"],
      "theoretical_stance": "<the scholar's theoretical or methodological orientation>"
    }}
  ],
  "theoretical_foundations": [
    {{
      "theory": "<name of theory or framework>",
      "origin": "<who developed it and when, if known>",
      "relevance_to_topic": "<how it applies to the research topic>",
      "key_proponents": ["<name — only if confident>"]
    }}
  ],
  "methodological_trends": {{
    "dominant_methods": ["<method name and brief description>"],
    "emerging_methods": ["<method name and brief description>"],
    "methodological_gaps": ["<gap in current methodology>"],
    "synthesis": "<paragraph synthesising the methodological landscape>"
  }},
  "current_debates": [
    {{
      "debate_title": "<concise debate label>",
      "positions": [
        {{
          "stance": "<label for this position>",
          "key_argument": "<the core argument for this position>",
          "proponents": ["<name — only if confident>"]
        }}
      ],
      "current_state": "<where the field currently stands on this debate>"
    }}
  ],
  "research_limitations": [
    {{
      "limitation": "<specific limitation in existing literature>",
      "prevalence": "common | occasional | notable",
      "impact_on_field": "<how this limitation constrains knowledge development>"
    }}
  ],
  "emerging_directions": [
    {{
      "direction": "<concise label for this emerging direction>",
      "rationale": "<why this direction is gaining traction>",
      "potential_impact": "<how it could advance the field>",
      "early_indicators": "<signals already visible in recent literature>"
    }}
  ],
  "future_research": [
    {{
      "opportunity": "<concise research opportunity title>",
      "suggested_research_question": "<a specific, answerable research question>",
      "suggested_methodology": "<appropriate methodology for this question>",
      "potential_contribution": "<what knowledge this would add>"
    }}
  ],
  "literature_draft": "<600–900 word publication-quality narrative synthesis, written in flowing academic prose with proper paragraph transitions, integrating themes, debates, and methodological trends. This should serve as a genuine starting point for a manuscript's literature review section — not a listicle reformatted as sentences.>"
}}\
"""


async def _run_claude_review(req: LiteratureReviewRequest) -> dict:
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
    )

    raw = await call_llm(
        system=_SYSTEM,
        user_msg=prompt,
        feature="literature_review.synthesis",
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
        log.error("Literature review JSON parse failed: %s | raw[:500]=%s", exc, text[:500])
        raise HTTPException(502, "Review engine returned malformed output. Please try again.")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ser(d: dict) -> dict:
    d = dict(d)
    d["id"] = str(d.pop("_id"))
    return d


# ─────────────────────────────── endpoints ───────────────────────────────────

@router.post("")
async def create_review(
    body: LiteratureReviewRequest,
    user: dict = Depends(require_feature("ai_literature_review")),
):
    """Generate a structured academic literature review.
    Costs 20 research credits. Credits are refunded automatically if generation fails.
    """
    # Consume credits before LLM call — raises 402 if balance insufficient.
    charged = await consume_credits(
        user["id"], "ai_literature_review",
        metadata={
            "topic": body.topic[:100],
            "keywords": body.keywords[:5],
        },
    )
    credits_used = charged.get("consumed", 20)

    started = time.monotonic()
    try:
        review_json = await _run_claude_review(body)
    except HTTPException:
        await refund_credits(user["id"], "ai_literature_review", reason="Review engine error")
        raise
    except Exception as exc:
        await refund_credits(user["id"], "ai_literature_review", reason="Unexpected error")
        log.error("Literature review generation failed: %s", exc)
        raise HTTPException(503, "Review generation failed. Your credits have been refunded.")
    duration_ms = int((time.monotonic() - started) * 1000)

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
        "review_json":      review_json,
        "credits_used":     credits_used,
        "created_at":       _now(),
    }
    result = await db.literature_reviews.insert_one(doc)
    doc["_id"] = result.inserted_id

    try:
        await db.ai_requests.insert_one({
            "user_id":     user["id"],
            "feature":     "ai_literature_review",
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
async def list_reviews(user: dict = Depends(get_current_user)):
    """Return the authenticated user's literature review history, newest first."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    docs = await db.literature_reviews.find(
        {"user_id": user["id"]},
        {"review_json": 0},       # exclude heavy field from list — fetched on demand
    ).sort("created_at", -1).to_list(50)
    return [_ser(d) for d in docs]


@router.get("/{review_id}")
async def get_review(review_id: str, user: dict = Depends(get_current_user)):
    """Fetch a specific review by ID. Only the owner may access it."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(review_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.literature_reviews.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    if doc["user_id"] != user["id"]:
        raise HTTPException(403, "Forbidden")
    return _ser(doc)
