"""AI Statistical Review — evaluate and interpret statistical analyses before publication.

The researcher submits a research topic, research question, and statistical results
(free-text, CSV paste, SPSS/regression/SEM/ANOVA output, etc.). Claude produces a
twelve-section review: executive assessment, analysis appropriateness, assumption
review, results interpretation, hypothesis evaluation, weaknesses, validity threats,
publication risk, recommended additional analyses, simulated reviewer criticisms,
publication readiness score, and a revision roadmap.

Endpoints:
  POST /api/statistical-review          — run review (costs 25 credits)
  GET  /api/statistical-review/history  — list caller's past reviews
  GET  /api/statistical-review/{id}     — fetch one review (owner only)
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

log = logging.getLogger("synaptiq.statistical_review")
router = APIRouter(prefix="/api/statistical-review", tags=["statistical-review"])

MAX_RESULTS_CHARS = 80_000
MIN_RESULTS_CHARS = 20


# ──────────────────────────────── request model ──────────────────────────────

class StatisticalReviewRequest(BaseModel):
    topic:              str = Field(..., min_length=3, max_length=300)
    research_question:  str = Field(..., min_length=10, max_length=1000)
    statistical_results: str = Field(..., min_length=MIN_RESULTS_CHARS, max_length=MAX_RESULTS_CHARS)
    methodology:        Optional[str] = Field(None, max_length=300)
    sample_size:        Optional[str] = Field(None, max_length=100)
    variables:          Optional[str] = Field(None, max_length=500)
    hypotheses:         Optional[str] = Field(None, max_length=2000)
    analysis_technique: Optional[str] = Field(None, max_length=200)


# ──────────────────────────────── Claude prompt ──────────────────────────────

_SYSTEM = """\
You are a senior biostatistician and research methodologist with expertise in applied
statistics across the social sciences, health sciences, natural sciences, and engineering.
You evaluate statistical analyses for academic publication — providing the kind of rigorous,
honest critique a statistical editor or reviewer at a high-impact journal would give.

ACCURACY RULES — strictly followed:
1. Base your interpretation solely on the statistical output provided. Do not invent
   findings, p-values, coefficients, or effect sizes that are not present in the input.
2. If the statistical output is incomplete, ambiguous, or insufficient to draw a
   conclusion, say so explicitly rather than speculating.
3. Name real statistical tests, indices, thresholds, and reporting standards
   (e.g., VIF, CFI, RMSEA, Cohen's d, Bonferroni correction, CONSORT, APA 7th edition).
4. Publication readiness score must be calibrated to realistic journal standards.
   A score above 80 requires genuinely strong statistics. Flag any serious violations
   clearly — do not soften findings to please the researcher.
5. Simulated reviewer criticisms must reflect the standards of peer review at
   reputable journals — not generic comments.
6. When hypothesis evaluation cannot be determined from the provided output, state
   this explicitly rather than guessing.

Return ONLY a single valid JSON object — no markdown fences, no preamble, no commentary.\
"""

_PROMPT = """\
Perform a comprehensive statistical review of the analysis described below. Every
assessment must be grounded in the statistical output provided — not generic advice.

RESEARCH TOPIC:         {topic}
RESEARCH QUESTION:      {research_question}
METHODOLOGY:            {methodology}
SAMPLE SIZE:            {sample_size}
VARIABLES:              {variables}
HYPOTHESES:             {hypotheses}
ANALYSIS TECHNIQUE:     {analysis_technique}

STATISTICAL RESULTS (full output follows):
---
{statistical_results}
---

Return a JSON object matching this exact schema. All interpretations must be grounded
in the specific values, indices, and patterns visible in the provided output above.

{{
  "executive_statistical_assessment": {{
    "summary": "<2–4 sentence honest summary of the overall statistical quality and key findings>",
    "overall_verdict": "strong | adequate | weak | insufficient",
    "key_strengths": ["<specific statistical strength visible in the output>"],
    "critical_issues": ["<specific critical issue that must be addressed before submission>"],
    "output_completeness": "<assessment of whether sufficient statistical output was provided to conduct a full review>"
  }},
  "analysis_appropriateness": {{
    "method_used": "<the statistical method identified from the output>",
    "is_appropriate": true,
    "appropriateness_rationale": "<paragraph explaining why the method is or is not appropriate for this research question>",
    "alternative_methods": ["<credible alternative that could have been used, with brief justification>"],
    "reporting_standard_compliance": "<assessment of compliance with relevant reporting standards — e.g. APA, CONSORT, STROBE, PRISMA>",
    "missing_reporting_elements": ["<specific element that should be reported but is absent>"]
  }},
  "assumption_review": {{
    "assumptions_assessed": [
      {{
        "assumption": "<assumption name — e.g. normality, independence, homoscedasticity, multicollinearity, sphericity>",
        "applicable": true,
        "status": "met | violated | not_tested | cannot_determine",
        "evidence": "<specific evidence from the output — e.g. specific test result, index value, or explicit absence of test>",
        "consequence": "<what the violation or untested assumption means for the results>",
        "recommended_action": "<specific corrective action if violated or not tested>"
      }}
    ],
    "overall_assumption_verdict": "assumptions_met | minor_concerns | major_concerns | cannot_assess"
  }},
  "results_interpretation": {{
    "narrative_interpretation": "<full academic-language interpretation of the results — specific to the values and patterns in the output>",
    "effect_sizes": [
      {{
        "measure": "<effect size measure — e.g. Cohen's d, eta-squared, R-squared, path coefficient>",
        "value": "<value from the output>",
        "interpretation": "negligible | small | medium | large",
        "context": "<what this means in the context of this specific study>"
      }}
    ],
    "statistical_significance_assessment": "<interpretation of which results are significant and what that means — with appropriate caveats about p-values>",
    "practical_significance": "<assessment of whether statistically significant results are also practically meaningful>",
    "confidence_intervals": "<interpretation of confidence intervals if present; flag their absence if not reported>"
  }},
  "hypothesis_evaluation": [
    {{
      "hypothesis": "<hypothesis text as provided, or 'H1', 'H2' etc. if not provided>",
      "verdict": "supported | partially_supported | not_supported | cannot_determine",
      "rationale": "<specific statistical evidence from the output that supports this verdict>",
      "caveats": "<conditions or limitations that qualify this verdict>"
    }}
  ],
  "statistical_weaknesses": [
    {{
      "weakness": "<specific weakness — e.g. low statistical power, small sample size, model misspecification, multicollinearity, missing confounders>",
      "severity": "critical | major | moderate | minor",
      "evidence": "<specific evidence from the output or its absence>",
      "impact": "<how this weakness affects the validity or generalisability of conclusions>",
      "remediation": "<specific action to address this weakness>"
    }}
  ],
  "threats_to_validity": {{
    "statistical_conclusion_validity": [
      {{
        "threat": "<specific threat name>",
        "description": "<how it undermines statistical conclusions in this study>",
        "mitigation": "<specific mitigation>"
      }}
    ],
    "internal_validity": [
      {{
        "threat": "<specific threat name>",
        "description": "<how it threatens causal interpretation>",
        "mitigation": "<specific mitigation>"
      }}
    ],
    "external_validity": [
      {{
        "threat": "<specific threat name>",
        "description": "<how it limits generalisability>",
        "mitigation": "<specific mitigation>"
      }}
    ],
    "construct_validity": [
      {{
        "threat": "<specific threat name>",
        "description": "<how it threatens measurement validity>",
        "mitigation": "<specific mitigation>"
      }}
    ]
  }},
  "publication_risk_assessment": {{
    "major_concerns": [
      {{
        "concern": "<specific major concern that could lead to outright rejection>",
        "likelihood_of_rejection": "high | moderate",
        "action_required": "<what must be done to resolve this>"
      }}
    ],
    "moderate_concerns": [
      {{
        "concern": "<concern likely to trigger major revisions>",
        "action_required": "<what should be done>"
      }}
    ],
    "minor_concerns": [
      {{
        "concern": "<concern likely to trigger minor revisions>",
        "action_required": "<what could be improved>"
      }}
    ]
  }},
  "recommended_additional_analyses": [
    {{
      "analysis": "<specific analysis to add — e.g. sensitivity analysis, power analysis, bootstrap confidence intervals>",
      "rationale": "<why this analysis is needed given the current results>",
      "priority": "essential | recommended | optional",
      "software_guidance": "<software or command to use — e.g. G*Power for power analysis, lavaan in R for CFA>"
    }}
  ],
  "reviewer_perspective": {{
    "likely_criticisms": [
      {{
        "reviewer_comment": "<realistic peer reviewer comment written in reviewer voice>",
        "severity": "fatal | major | minor",
        "suggested_response": "<how the author should address this in a response letter>"
      }}
    ],
    "editorial_assessment": "<what an editor would likely say about the statistical rigour of this submission>"
  }},
  "publication_readiness": {{
    "score": <integer 0-100>,
    "assessment": "<honest 3–4 sentence assessment of publication readiness based on the statistical quality alone>",
    "strongest_statistical_element": "<the single strongest statistical element that supports publication>",
    "most_critical_barrier": "<the single most important barrier to publication>"
  }},
  "revision_roadmap": {{
    "high_priority": [
      {{
        "action": "<specific revision action — must be actionable, not vague>",
        "reason": "<why this is critical to acceptance>"
      }}
    ],
    "medium_priority": [
      {{
        "action": "<specific revision action>",
        "reason": "<why this strengthens the paper>"
      }}
    ],
    "low_priority": [
      {{
        "action": "<specific polish action>",
        "reason": "<why this improves readability or completeness>"
      }}
    ]
  }}
}}

CONSTRAINTS:
- hypothesis_evaluation must have one entry per hypothesis provided. If no hypotheses
  were stated, produce one entry reflecting whether the research question was answered.
- statistical_weaknesses must have at least 2 entries.
- recommended_additional_analyses must have at least 2 entries.
- reviewer_perspective.likely_criticisms must have at least 3 entries.
- revision_roadmap.high_priority must have at least 2 entries.
- All interpretations must reference the actual values in the statistical output.
  If a value is ambiguous or missing, say so in the relevant field.\
"""


async def _run_statistical_review(req: StatisticalReviewRequest) -> dict:
    prompt = _PROMPT.format(
        topic=req.topic,
        research_question=req.research_question,
        methodology=req.methodology or "Not specified",
        sample_size=req.sample_size or "Not specified",
        variables=req.variables or "Not specified",
        hypotheses=req.hypotheses or "Not stated",
        analysis_technique=req.analysis_technique or "Not specified",
        statistical_results=req.statistical_results,
    )

    raw = await call_llm(
        system=_SYSTEM,
        user_msg=prompt,
        feature="statistical.advisor",
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
        log.error("Statistical review JSON parse failed: %s | raw[:500]=%s", exc, text[:500])
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
async def create_review(
    body: StatisticalReviewRequest,
    user: dict = Depends(require_feature("ai_statistical_review")),
):
    """Run a statistical review. Costs 25 credits; refunded automatically on failure."""
    charged = await consume_credits(
        user["id"], "ai_statistical_review",
        metadata={"topic": body.topic[:100]},
    )
    credits_used = charged.get("consumed", 25)

    started = time.monotonic()
    try:
        review_json = await _run_statistical_review(body)
    except HTTPException:
        await refund_credits(user["id"], "ai_statistical_review", reason="Analysis engine error")
        raise
    except Exception as exc:
        await refund_credits(user["id"], "ai_statistical_review", reason="Unexpected error")
        log.error("Statistical review failed: %s", exc)
        raise HTTPException(503, "Review failed. Your credits have been refunded.")
    duration_ms = int((time.monotonic() - started) * 1000)

    publication_score = _extract_publication_score(review_json)

    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    doc = {
        "user_id":          user["id"],
        "topic":            body.topic,
        "research_question": body.research_question,
        "methodology":      body.methodology,
        "sample_size":      body.sample_size,
        "analysis_technique": body.analysis_technique,
        "review_json":      review_json,
        "publication_score": publication_score,
        "credits_used":     credits_used,
        "created_at":       _now(),
    }
    result = await db.statistical_reviews.insert_one(doc)
    doc["_id"] = result.inserted_id

    try:
        await db.ai_requests.insert_one({
            "user_id":     user["id"],
            "feature":     "ai_statistical_review",
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
    """Return the authenticated user's statistical reviews, newest first.
    The heavy review_json field is excluded from list results."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    docs = await db.statistical_reviews.find(
        {"user_id": user["id"]},
        {"review_json": 0},
    ).sort("created_at", -1).to_list(50)
    return [_ser(d) for d in docs]


@router.get("/{review_id}")
async def get_review(review_id: str, user: dict = Depends(get_current_user)):
    """Fetch one statistical review by ID. Only the owner may access it."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(review_id)
    except Exception:
        raise HTTPException(404, "Not found")
    doc = await db.statistical_reviews.find_one({"_id": oid})
    if not doc:
        raise HTTPException(404, "Not found")
    if doc["user_id"] != user["id"]:
        raise HTTPException(403, "Forbidden")
    return _ser(doc)
