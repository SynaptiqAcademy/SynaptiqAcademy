"""Statistical Intelligence 2.0 — AI Statistical Advisor (Phase X).

Sends statistical results + rule findings to the LLM for comprehensive
expert review. Returns structured JSON covering all 6 dimensions,
recommendations, reviewer criticisms, and publication readiness.
AI is primary; rule-based fills any missing dimensions.
"""
from __future__ import annotations

import json
import logging
from typing import Any

log = logging.getLogger("synaptiq.statistical.ai")

_MAX_TEXT_CHARS = 30_000

_SYSTEM = """\
You are a senior biostatistician and research methodologist with expertise in applied
statistics across medicine, psychology, education, management, and engineering.
You evaluate statistical analyses as a senior reviewer at a high-impact journal would:
rigorous, honest, specific, and grounded entirely in what was provided.

ACCURACY RULES:
1. Base all interpretations on the provided statistical output. Do not invent numbers.
2. If output is incomplete, say so explicitly.
3. Name real tests, indices, and standards (VIF, CFI, RMSEA, Cohen's d, APA 7th edition).
4. Calibrate publication readiness realistically — a score above 80 requires genuinely strong statistics.
5. Flag serious violations clearly. Do not soften findings.
6. Return ONLY valid JSON — no markdown fences, no preamble.\
"""

_PROMPT_TEMPLATE = """\
Perform a comprehensive statistical intelligence review of the analysis below.
All assessments must be grounded in the statistical output provided.

TOPIC:             {topic}
RESEARCH QUESTION: {research_question}
METHODOLOGY:       {methodology}
HYPOTHESES:        {hypotheses}
DISCIPLINE:        {discipline}

RULE-BASED FINDINGS (preliminary):
Detected methods: {detected_methods}
Study type: {study_type}
Sample size: {sample_size}
Critical issues found: {critical_issue_count}
Major issues found: {major_issue_count}

STATISTICAL OUTPUT:
---
{content}
---

Return a JSON object with this exact schema:

{{
  "executive_summary": "<2-4 sentence expert summary of overall statistical quality>",
  "statistical_review_text": "<full peer-reviewer quality narrative — 400-800 words covering all key aspects>",
  "overall_verdict": "strong | adequate | weak | insufficient",
  "dimensions": {{
    "methodological_rigor": {{
      "score": <0-100>,
      "grade": "<A+|A|A-|B+|B|B-|C+|C|C-|D|F>",
      "rationale": "<specific rationale based on the output>",
      "strengths": ["<strength>"],
      "weaknesses": ["<weakness>"]
    }},
    "sample_adequacy": {{
      "score": <0-100>, "grade": "<grade>",
      "rationale": "<rationale>", "strengths": [], "weaknesses": []
    }},
    "data_quality": {{
      "score": <0-100>, "grade": "<grade>",
      "rationale": "<rationale>", "strengths": [], "weaknesses": []
    }},
    "result_validity": {{
      "score": <0-100>, "grade": "<grade>",
      "rationale": "<rationale>", "strengths": [], "weaknesses": []
    }},
    "construct_validity": {{
      "score": <0-100>, "grade": "<grade>",
      "rationale": "<rationale>", "strengths": [], "weaknesses": []
    }},
    "reporting_quality": {{
      "score": <0-100>, "grade": "<grade>",
      "rationale": "<rationale>", "strengths": [], "weaknesses": []
    }}
  }},
  "additional_critical_issues": [
    {{
      "severity": "critical | major | moderate | minor",
      "category": "<methods|sampling|data_quality|assumptions|reporting|interpretation|validity>",
      "title": "<concise title>",
      "description": "<specific description grounded in the output>",
      "recommendation": "<specific actionable recommendation>"
    }}
  ],
  "recommended_analyses": [
    {{
      "analysis": "<specific analysis>",
      "rationale": "<why needed given the current results>",
      "priority": "essential | recommended | optional",
      "software_guidance": "<software or command>"
    }}
  ],
  "reviewer_criticisms": [
    {{
      "comment": "<realistic peer reviewer comment in reviewer voice>",
      "severity": "fatal | major | minor",
      "suggested_response": "<how the author should respond>"
    }}
  ],
  "publication_readiness": {{
    "overall_score": <0-100>,
    "acceptance_probability": <0.0-1.0>,
    "desk_rejection_risk": <0.0-1.0>,
    "verdict": "strong | adequate | weak | insufficient",
    "strongest_element": "<strongest statistical element>",
    "critical_barrier": "<single most important barrier to publication>",
    "assessment": "<honest 3-sentence assessment>"
  }},
  "revision_roadmap": [
    {{
      "phase": <1-5>,
      "title": "<phase title>",
      "priority": "high | medium | low",
      "estimated_effort": "<e.g. 1-2 weeks>",
      "actions": ["<specific action>"]
    }}
  ]
}}

CONSTRAINTS:
- recommended_analyses must have at least 3 entries
- reviewer_criticisms must have at least 3 entries
- revision_roadmap must have at least 2 phases
- additional_critical_issues can be empty if no further issues exist beyond rule findings\
"""


def _empty_ai_result() -> dict:
    return {
        "executive_summary": "",
        "statistical_review_text": "",
        "overall_verdict": "insufficient",
        "dimensions": {},
        "additional_critical_issues": [],
        "recommended_analyses": [],
        "reviewer_criticisms": [],
        "publication_readiness": {
            "overall_score": 0,
            "acceptance_probability": 0.0,
            "desk_rejection_risk": 1.0,
            "verdict": "insufficient",
            "strongest_element": "",
            "critical_barrier": "AI advisor unavailable",
            "assessment": "Statistical review could not be completed by the AI advisor.",
        },
        "revision_roadmap": [],
    }


def _normalise(d: dict) -> dict:
    """Ensure required keys exist with sensible defaults."""
    d.setdefault("executive_summary", "")
    d.setdefault("statistical_review_text", "")
    d.setdefault("overall_verdict", "insufficient")
    d.setdefault("dimensions", {})
    d.setdefault("additional_critical_issues", [])
    d.setdefault("recommended_analyses", [])
    d.setdefault("reviewer_criticisms", [])
    d.setdefault("revision_roadmap", [])
    pr = d.setdefault("publication_readiness", {})
    pr.setdefault("overall_score", 0)
    pr.setdefault("acceptance_probability", 0.0)
    pr.setdefault("desk_rejection_risk", 1.0)
    pr.setdefault("verdict", "insufficient")
    pr.setdefault("strongest_element", "")
    pr.setdefault("critical_barrier", "")
    pr.setdefault("assessment", "")
    return d


async def review_with_ai(
    content: str,
    topic: str,
    research_question: str,
    methodology: str,
    hypotheses: str,
    discipline: str,
    detected_methods: list[str],
    study_type: str,
    sample_size: int,
    critical_issue_count: int,
    major_issue_count: int,
) -> dict:
    try:
        from services.ai.llm import call_llm
    except ImportError:
        log.warning("LLM service not available; returning empty AI result")
        return _empty_ai_result()

    truncated = content[:_MAX_TEXT_CHARS]
    if len(content) > _MAX_TEXT_CHARS:
        truncated += f"\n\n[... content truncated at {_MAX_TEXT_CHARS} characters ...]"

    prompt = _PROMPT_TEMPLATE.format(
        topic=topic or "Not specified",
        research_question=research_question or "Not specified",
        methodology=methodology or "Not specified",
        hypotheses=hypotheses or "Not stated",
        discipline=discipline or "general",
        detected_methods=", ".join(detected_methods) or "unknown",
        study_type=study_type,
        sample_size=sample_size or "unknown",
        critical_issue_count=critical_issue_count,
        major_issue_count=major_issue_count,
        content=truncated,
    )

    try:
        raw = await call_llm(system=_SYSTEM, user_msg=prompt, feature="statistical.advisor", max_tokens=4000)
        text = raw.strip()
        if text.startswith("```"):
            parts = text.split("```", 2)
            inner = parts[1] if len(parts) >= 2 else text
            if inner.startswith("json"):
                inner = inner[4:]
            text = inner.split("```")[0].strip()
        result = json.loads(text)
        return _normalise(result)
    except Exception as exc:
        log.error("AI statistical advisor failed: %s", exc)
        return _empty_ai_result()
