"""AI Research Design Advisor — transform a research idea into a defensible study design.

The researcher provides a topic, research question, and objective. Claude produces a
twelve-section design advisory: methodology recommendation, framework, objectives
assessment, hypothesis development, variables, sampling, data collection, analysis plan,
validity threats, ethical considerations, publication readiness score, and improvement plan.

Endpoints:
  POST /api/research-design-advisor          — run advisory (costs 10 credits)
  GET  /api/research-design-advisor/history  — list caller's past advisories
  GET  /api/research-design-advisor/{id}     — fetch one advisory (owner only)
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

log = logging.getLogger("synaptiq.research_design_advisor")
router = APIRouter(prefix="/api/research-design-advisor", tags=["research-design-advisor"])


# ──────────────────────────────── request model ──────────────────────────────

class DesignAdvisorRequest(BaseModel):
    topic:                str = Field(..., min_length=3, max_length=300)
    research_question:    str = Field(..., min_length=10, max_length=1000)
    research_objective:   str = Field(..., min_length=10, max_length=1000)
    discipline:           Optional[str] = Field(None, max_length=100)
    target_journal_type:  Optional[str] = Field(None, max_length=200)
    preferred_methodology: Optional[str] = Field(None, max_length=200)
    target_population:    Optional[str] = Field(None, max_length=300)
    expected_sample_size: Optional[str] = Field(None, max_length=100)
    available_data_sources: Optional[str] = Field(None, max_length=500)


# ──────────────────────────────── Claude prompt ──────────────────────────────

_USER_TEMPLATE = """\
Produce a comprehensive research design advisory for the study described below. Every
recommendation must be justified by the specific characteristics of this study — not
generic academic advice.

TOPIC:                  {topic}
RESEARCH QUESTION:      {research_question}
RESEARCH OBJECTIVE:     {research_objective}
DISCIPLINE:             {discipline}
TARGET JOURNAL TYPE:    {target_journal_type}
PREFERRED METHODOLOGY:  {preferred_methodology}
TARGET POPULATION:      {target_population}
EXPECTED SAMPLE SIZE:   {expected_sample_size}
AVAILABLE DATA SOURCES: {available_data_sources}

Return a JSON object matching this exact schema. All string fields must be substantive and
specific to this study. Do not use filler phrases.

{{
  "research_design_recommendation": {{
    "recommended_design": "qualitative | quantitative | mixed_methods",
    "design_type": "<specific design within that category — e.g. cross-sectional survey, longitudinal cohort, grounded theory, case study, experimental RCT, quasi-experimental, systematic review>",
    "justification": "<paragraph explaining why this design best answers the specific research question>",
    "alternative_considered": "<one credible alternative design and why it was not recommended>",
    "feasibility_note": "<honest assessment of whether this design is realistic given the stated constraints>"
  }},
  "research_framework": {{
    "conceptual_model": "<description of the conceptual model appropriate for this study>",
    "theoretical_structure": "<underlying theoretical tradition(s) — e.g. social cognitive theory, TPB, grounded theory, constructivism, positivism>",
    "key_constructs": [
      {{
        "construct": "<name of construct>",
        "definition": "<working definition for this study>",
        "role": "independent | dependent | mediator | moderator | outcome | descriptive"
      }}
    ],
    "framework_rationale": "<why this framework fits the research question>"
  }},
  "research_objectives_assessment": {{
    "clarity_score": <integer 0-10>,
    "clarity_assessment": "<specific assessment of how clearly the objective is stated>",
    "measurability_score": <integer 0-10>,
    "measurability_assessment": "<specific assessment of how measurable the objective is>",
    "alignment_score": <integer 0-10>,
    "alignment_assessment": "<specific assessment of how well the objective aligns with the research question>",
    "refined_objective": "<a rewritten, improved version of the stated objective if improvement is needed; null if the original is strong>",
    "overall_assessment": "<1-2 sentence overall verdict>"
  }},
  "hypothesis_development": {{
    "hypotheses_appropriate": true,
    "hypotheses_not_appropriate_reason": null,
    "hypotheses": [
      {{
        "id": "H1",
        "statement": "<specific, testable hypothesis statement>",
        "null_hypothesis": "<corresponding null hypothesis>",
        "rationale": "<why this hypothesis follows from the framework and objective>",
        "test_type": "<statistical or analytical test most appropriate to test this hypothesis>"
      }}
    ]
  }},
  "variables": {{
    "independent_variables": [
      {{
        "variable": "<variable name>",
        "operationalisation": "<how it will be measured or manipulated>",
        "measurement_level": "nominal | ordinal | interval | ratio | categorical"
      }}
    ],
    "dependent_variables": [
      {{
        "variable": "<variable name>",
        "operationalisation": "<how it will be measured>",
        "measurement_level": "nominal | ordinal | interval | ratio | categorical"
      }}
    ],
    "moderators": [
      {{
        "variable": "<moderator variable>",
        "rationale": "<why this variable may moderate the relationship>"
      }}
    ],
    "mediators": [
      {{
        "variable": "<mediator variable>",
        "rationale": "<why this variable may mediate the relationship>"
      }}
    ],
    "control_variables": [
      {{
        "variable": "<control variable>",
        "rationale": "<why this must be controlled>"
      }}
    ]
  }},
  "sampling_strategy": {{
    "target_population": "<precise definition of the population>",
    "sampling_method": "<specific method — e.g. stratified random sampling, purposive sampling, snowball, cluster>",
    "sampling_method_justification": "<why this method is appropriate for this study>",
    "recommended_sample_size": "<specific recommendation or range with justification>",
    "sample_size_rationale": "<power analysis basis, saturation reasoning, or practical justification>",
    "inclusion_criteria": ["<criterion>"],
    "exclusion_criteria": ["<criterion>"],
    "recruitment_strategy": "<practical suggestion for how to reach this population>"
  }},
  "data_collection_strategy": {{
    "primary_method": "<main data collection approach>",
    "primary_method_justification": "<why this is the right primary method>",
    "secondary_methods": ["<additional collection method if applicable>"],
    "instruments": [
      {{
        "instrument": "<name or type — e.g. Likert-scale survey, semi-structured interview guide>",
        "purpose": "<what it measures or elicits>",
        "validation_note": "<whether to use validated instruments, adapt existing ones, or develop new>",
        "estimated_duration": "<how long data collection per participant will take>"
      }}
    ],
    "data_quality_measures": ["<specific measure to ensure data quality>"],
    "timeline_estimate": "<realistic estimate of data collection duration>"
  }},
  "data_analysis_plan": {{
    "primary_analysis_method": "<specific method — e.g. hierarchical multiple regression, SEM with AMOS, PLS-SEM with SmartPLS, thematic analysis, grounded theory constant comparison>",
    "primary_method_justification": "<why this is the right analytical approach>",
    "software_recommendation": "<specific software — e.g. SPSS, R, Python, ATLAS.ti, NVivo, SmartPLS>",
    "secondary_analyses": ["<additional analyses>"],
    "analysis_steps": [
      {{
        "step": <integer>,
        "description": "<specific analysis step>"
      }}
    ],
    "reporting_standards": "<relevant reporting standards — e.g. STROBE, CONSORT, COREQ, APA>",
    "statistical_assumptions": ["<assumption that must be met and how to test it>"]
  }},
  "threats_to_validity": {{
    "internal_validity": [
      {{
        "threat": "<specific threat name>",
        "description": "<how it threatens internal validity in this specific study>",
        "mitigation": "<specific mitigation strategy>"
      }}
    ],
    "external_validity": [
      {{
        "threat": "<specific threat name>",
        "description": "<how it limits generalisability>",
        "mitigation": "<specific mitigation strategy>"
      }}
    ],
    "construct_validity": [
      {{
        "threat": "<specific threat name>",
        "description": "<how it threatens construct validity>",
        "mitigation": "<specific mitigation strategy>"
      }}
    ]
  }},
  "ethical_considerations": {{
    "irb_required": true,
    "key_ethical_risks": [
      {{
        "risk": "<specific ethical risk relevant to this study>",
        "mitigation": "<how to address it>"
      }}
    ],
    "consent_approach": "<description of informed consent approach appropriate for this study>",
    "data_privacy": "<how participant data will be protected and stored>",
    "vulnerable_populations": "<whether the study involves vulnerable groups and what additional safeguards apply>",
    "additional_considerations": "<any other ethical notes specific to this study type or population>"
  }},
  "publication_readiness": {{
    "score": <integer 0-100>,
    "assessment": "<honest 3-4 sentence assessment of publishability given the stated design>",
    "strongest_elements": ["<element of the design that strengthens publishability>"],
    "weakest_elements": ["<element that most undermines publishability>"],
    "recommended_target_journals": "<type of journals best suited to this study — not specific names>"
  }},
  "improvement_plan": {{
    "high_priority": [
      {{
        "action": "<specific action to take>",
        "reason": "<why this is critical to the study's success>"
      }}
    ],
    "medium_priority": [
      {{
        "action": "<specific action to take>",
        "reason": "<why this improves the study>"
      }}
    ],
    "low_priority": [
      {{
        "action": "<specific action to take>",
        "reason": "<why this is a nice-to-have improvement>"
      }}
    ]
  }}
}}

IMPORTANT CONSTRAINTS:
- hypotheses_development.hypotheses must contain 2–4 hypotheses for quantitative/mixed studies.
- If the design is qualitative and exploratory, set hypotheses_appropriate to false and
  hypotheses_not_appropriate_reason to a specific explanation; set hypotheses to [].
- variables.moderators and variables.mediators may be empty arrays if not applicable.
- All array fields must have at least one item unless explicitly marked optional above.
- The improvement_plan must have at least 2 items in high_priority.\
"""


async def _run_advisory(
    req: DesignAdvisorRequest,
    *,
    user_id: str | None = None,
    db=None,
) -> dict:
    user_message = _USER_TEMPLATE.format(
        topic=req.topic,
        research_question=req.research_question,
        research_objective=req.research_objective,
        discipline=req.discipline or "Not specified",
        target_journal_type=req.target_journal_type or "Not specified",
        preferred_methodology=req.preferred_methodology or "No preference",
        target_population=req.target_population or "Not specified",
        expected_sample_size=req.expected_sample_size or "Not specified",
        available_data_sources=req.available_data_sources or "Not specified",
    )

    raw = await call_llm(
        prompt_id="research_design.advisor",
        variables={"user_message": user_message},
        feature="research_design.advisor",
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
        return json.loads(text)
    except json.JSONDecodeError as exc:
        log.error("Design advisory JSON parse failed: %s | raw[:500]=%s", exc, text[:500])
        raise HTTPException(502, "Analysis engine returned malformed output. Please try again.")


def _extract_publication_score(review_json: dict) -> int:
    try:
        score = review_json["publication_readiness"]["score"]
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
async def create_advisory(
    body: DesignAdvisorRequest,
    user: dict = Depends(require_feature("ai_research_design_advisor")),
):
    """Run a research design advisory. Costs 10 credits; refunded automatically on failure."""
    charged = await consume_credits(
        user["id"], "ai_research_design_advisor",
        metadata={"topic": body.topic[:100]},
    )
    credits_used = charged.get("consumed", 10)

    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    started = time.monotonic()
    try:
        review_json = await _run_advisory(body, user_id=user["id"], db=db)
    except HTTPException:
        await refund_credits(user["id"], "ai_research_design_advisor", reason="Analysis engine error")
        raise
    except Exception as exc:
        await refund_credits(user["id"], "ai_research_design_advisor", reason="Unexpected error")
        log.error("Research design advisory failed: %s", exc)
        raise HTTPException(503, "Advisory failed. Your credits have been refunded.")
    duration_ms = int((time.monotonic() - started) * 1000)

    publication_score = _extract_publication_score(review_json)

    doc = {
        "user_id":          user["id"],
        "topic":            body.topic,
        "research_question": body.research_question,
        "research_objective": body.research_objective,
        "discipline":       body.discipline,
        "target_journal_type": body.target_journal_type,
        "preferred_methodology": body.preferred_methodology,
        "target_population": body.target_population,
        "expected_sample_size": body.expected_sample_size,
        "available_data_sources": body.available_data_sources,
        "review_json":      review_json,
        "publication_score": publication_score,
        "credits_used":     credits_used,
        "created_at":       _now(),
    }
    result = await db.research_design_reviews.insert_one(doc)
    doc["_id"] = result.inserted_id

    try:
        await db.ai_requests.insert_one({
            "user_id":     user["id"],
            "feature":     "ai_research_design_advisor",
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
async def list_advisories(user: dict = Depends(get_current_user)):
    """Return the authenticated user's design advisories, newest first.
    The heavy review_json field is excluded from list results."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    docs = await db.research_design_reviews.find(
        {"user_id": user["id"]},
        {"review_json": 0},
    ).sort("created_at", -1).to_list(50)
    return [_ser(d) for d in docs]


@router.get("/{advisory_id}")
async def get_advisory(advisory_id: str, user: dict = Depends(get_current_user)):
    """Fetch one design advisory by ID. Only the owner may access it."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(advisory_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.research_design_reviews.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    if doc["user_id"] != user["id"]:
        raise HTTPException(403, "Forbidden")
    return _ser(doc)
