"""AI-powered comprehensive manuscript reviewer — Phase IX.

Sends a structured prompt to the LLM requesting a full scientific review
covering all dimensions. The rule-based results are provided as context
so the AI can focus on higher-level synthesis rather than detection.

Returns: AI-enriched dimensions, executive summary, peer_review_text,
         editorial_assessment, inferred_discipline, journal_matches_ai.
"""
from __future__ import annotations

import json
import logging

from .models import (
    QualityDimension, ReviewIssue, IssueSeverity,
    JournalMatch, ReviewDimensions, _score_to_grade,
)

log = logging.getLogger("synaptiq.manuscript.ai")

_MAX_TEXT_CHARS = 30_000     # ~7k tokens at typical density
_MAX_RULE_ISSUES = 12        # summarised for prompt context

_SYSTEM = (
    "You are a senior academic peer reviewer and journal editor with expertise across "
    "STEM, social sciences, and humanities. You perform rigorous, evidence-based manuscript "
    "evaluations consistent with high-impact journal review standards. "
    "You identify publishable and fundable research, detect methodological flaws, "
    "evaluate novelty and contribution, and provide actionable revision recommendations. "
    "Return ONLY valid JSON — no markdown fences, no prose outside the JSON."
)

_PROMPT = """\
You are reviewing an academic manuscript for publication suitability.

Rule-based pre-screening has already identified the following issues:
{rule_issues_summary}

MANUSCRIPT TEXT (truncated to {char_limit} chars if long):
{manuscript_text}

Produce a comprehensive peer review. Return a single JSON object with EXACTLY this schema:

{{
  "inferred_discipline": "<primary academic discipline>",
  "executive_summary": "<4-6 sentence holistic review. Be specific about strengths and weaknesses.>",
  "peer_review_report": "<full structured peer review text, 400-600 words, as a journal reviewer would write it>",
  "editorial_assessment": "<3-4 sentences from the perspective of a handling editor>",
  "overall_score": <integer 0-100>,
  "recommendation": "accept|minor_revision|major_revision|revise_and_resubmit|reject|reject_with_encouragement",
  "review_dimensions": {{
    "scientific_rigor": {{
      "score": <integer 0-100>,
      "rationale": "<2-3 sentence explanation>",
      "strengths": ["<strength>", ...],
      "weaknesses": ["<weakness>", ...]
    }},
    "originality": {{
      "score": <integer 0-100>,
      "rationale": "<2-3 sentence explanation>",
      "strengths": ["<strength>", ...],
      "weaknesses": ["<weakness>", ...]
    }},
    "methodological_soundness": {{
      "score": <integer 0-100>,
      "rationale": "<2-3 sentence explanation>",
      "strengths": ["<strength>", ...],
      "weaknesses": ["<weakness>", ...]
    }},
    "clarity": {{
      "score": <integer 0-100>,
      "rationale": "<2-3 sentence explanation>",
      "strengths": ["<strength>", ...],
      "weaknesses": ["<weakness>", ...]
    }},
    "literature_coverage": {{
      "score": <integer 0-100>,
      "rationale": "<2-3 sentence explanation>",
      "strengths": ["<strength>", ...],
      "weaknesses": ["<weakness>", ...]
    }},
    "contribution": {{
      "score": <integer 0-100>,
      "rationale": "<2-3 sentence explanation>",
      "strengths": ["<strength>", ...],
      "weaknesses": ["<weakness>", ...]
    }},
    "statistical_validity": {{
      "score": <integer 0-100>,
      "rationale": "<2-3 sentence explanation>",
      "strengths": ["<strength>", ...],
      "weaknesses": ["<weakness>", ...]
    }},
    "ethical_compliance": {{
      "score": <integer 0-100>,
      "rationale": "<2-3 sentence explanation>",
      "strengths": ["<strength>", ...],
      "weaknesses": ["<weakness>", ...]
    }}
  }},
  "additional_critical_issues": [
    {{
      "severity": "critical|major|minor|suggestion",
      "section": "<section name>",
      "title": "<issue title>",
      "description": "<what is wrong and why it matters>",
      "recommendation": "<specific fix recommendation>"
    }}
  ],
  "publication_readiness": {{
    "acceptance_probability": <float 0.0-1.0>,
    "desk_rejection_risk": <float 0.0-1.0>,
    "major_revision_probability": <float 0.0-1.0>,
    "minor_revision_probability": <float 0.0-1.0>,
    "reviewer_difficulty": "low|moderate|high|very_high",
    "estimated_revision_effort": "1-2 days|1 week|2-4 weeks|1-3 months|>3 months",
    "target_tier": "Q1|Q2|Q3|Q4",
    "strengths": ["<strength>", ...],
    "barriers": ["<barrier>", ...]
  }},
  "journal_matches": [
    {{
      "name": "<journal name>",
      "publisher": "<publisher>",
      "quartile": "Q1|Q2|Q3|Q4",
      "scope_match": <float 0.0-1.0>,
      "acceptance_probability": <float 0.0-1.0>,
      "impact_factor": <float or null>,
      "submission_notes": "<brief journal-specific advice>",
      "open_access": <boolean>
    }}
  ]
}}

SCORING GUIDANCE:
- 90-100: Exceptional, accept as is or minor formatting only
- 80-89: Strong, minor revision required
- 70-79: Good, moderate revision required
- 60-69: Adequate, major revision required
- 50-59: Below standard, revise and resubmit with substantial changes
- 40-49: Significant fundamental flaws
- below 40: Reject

Provide 3-5 journal_matches appropriate for this manuscript's discipline, quality, and scope.
Scores must reflect the ACTUAL content of the manuscript — do not assign high scores without evidence.
"""


async def review_with_ai(
    text: str,
    rule_issues: list[ReviewIssue],
    rule_dimensions: ReviewDimensions,
) -> dict:
    """
    Returns a dict with:
      executive_summary, peer_review_report, editorial_assessment,
      inferred_discipline, overall_score, recommendation,
      review_dimensions_ai (dict), additional_issues (list),
      publication_readiness (dict), journal_matches (list[dict])
    """
    from services.ai.llm import call_llm  # deferred — avoid circular import

    truncated = text[:_MAX_TEXT_CHARS]
    if len(text) > _MAX_TEXT_CHARS:
        truncated += f"\n\n[TRUNCATED at {_MAX_TEXT_CHARS} characters]"

    # Summarise rule issues for prompt context
    rule_summary_lines: list[str] = []
    for issue in rule_issues[:_MAX_RULE_ISSUES]:
        rule_summary_lines.append(f"- [{issue.severity.value.upper()}] {issue.title}")
    rule_issues_summary = "\n".join(rule_summary_lines) or "None detected by rule engine."

    prompt = _PROMPT.format(
        rule_issues_summary=rule_issues_summary,
        char_limit=_MAX_TEXT_CHARS,
        manuscript_text=truncated,
    )

    try:
        raw = await call_llm(system=_SYSTEM, user_msg=prompt, feature="manuscript.review", max_tokens=4096)
    except Exception as exc:
        log.error("AI reviewer LLM call failed: %s", exc)
        return _empty_ai_result()

    raw = raw.strip()
    if raw.startswith("```"):
        parts = raw.split("```", 2)
        if len(parts) >= 3:
            inner = parts[1]
            if inner.startswith("json"):
                inner = inner[4:]
            raw = inner.strip()
        else:
            raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        log.error("AI reviewer JSON parse failed: %s | raw[:400]=%s", exc, raw[:400])
        return _empty_ai_result()

    return _normalise_ai_result(parsed)


def _normalise_ai_result(d: dict) -> dict:
    """Normalise and validate the AI output."""
    def _str(key: str, default: str = "") -> str:
        v = d.get(key, default)
        return str(v) if v is not None else default

    def _float(key: str, default: float = 0.0, d_: dict = None) -> float:
        src = d_ if d_ is not None else d
        try:
            return float(src.get(key, default))
        except (TypeError, ValueError):
            return default

    def _int(key: str, default: int = 0, d_: dict = None) -> int:
        src = d_ if d_ is not None else d
        try:
            return int(src.get(key, default))
        except (TypeError, ValueError):
            return default

    def _list(key: str, d_: dict = None) -> list:
        src = d_ if d_ is not None else d
        v = src.get(key, [])
        return v if isinstance(v, list) else []

    # ── Dimensions ─────────────────────────────────────────────────────────────
    dims_raw = d.get("review_dimensions", {})
    dim_weights = {
        "scientific_rigor": 1.5, "originality": 1.5,
        "methodological_soundness": 1.5, "clarity": 1.0,
        "literature_coverage": 1.0, "contribution": 1.5,
        "statistical_validity": 1.0, "ethical_compliance": 0.5,
    }
    dims_out: dict[str, QualityDimension] = {}
    for key, weight in dim_weights.items():
        dr = dims_raw.get(key, {})
        if not isinstance(dr, dict):
            dr = {}
        score = max(0.0, min(100.0, _float("score", 60.0, dr)))
        dims_out[key] = QualityDimension(
            name=key.replace("_", " ").title(),
            score=score,
            weight=weight,
            grade=_score_to_grade(score),
            rationale=_str("rationale", d_=dr),
            strengths=_list("strengths", dr)[:4],
            weaknesses=_list("weaknesses", dr)[:4],
        )

    # ── Additional issues ──────────────────────────────────────────────────────
    add_issues_raw = d.get("additional_critical_issues", [])
    add_issues: list[ReviewIssue] = []
    if isinstance(add_issues_raw, list):
        for item in add_issues_raw[:10]:
            if not isinstance(item, dict):
                continue
            sev_str = str(item.get("severity", "minor")).lower()
            try:
                sev = IssueSeverity(sev_str)
            except ValueError:
                sev = IssueSeverity.MINOR
            add_issues.append(ReviewIssue(
                severity=sev,
                section=str(item.get("section", "")),
                title=str(item.get("title", "")),
                description=str(item.get("description", "")),
                recommendation=str(item.get("recommendation", "")),
            ))

    # ── Publication readiness ──────────────────────────────────────────────────
    pr_raw = d.get("publication_readiness", {})
    if not isinstance(pr_raw, dict):
        pr_raw = {}
    pub_readiness = {
        "acceptance_probability": round(max(0.0, min(1.0, _float("acceptance_probability", 0.25, pr_raw))), 3),
        "desk_rejection_risk": round(max(0.0, min(1.0, _float("desk_rejection_risk", 0.15, pr_raw))), 3),
        "major_revision_probability": round(max(0.0, min(1.0, _float("major_revision_probability", 0.5, pr_raw))), 3),
        "minor_revision_probability": round(max(0.0, min(1.0, _float("minor_revision_probability", 0.2, pr_raw))), 3),
        "reviewer_difficulty": str(pr_raw.get("reviewer_difficulty", "moderate")),
        "estimated_revision_effort": str(pr_raw.get("estimated_revision_effort", "2-4 weeks")),
        "target_tier": str(pr_raw.get("target_tier", "Q2")),
        "strengths": _list("strengths", pr_raw)[:5],
        "barriers": _list("barriers", pr_raw)[:5],
    }

    # ── Journal matches ────────────────────────────────────────────────────────
    jm_raw = d.get("journal_matches", [])
    journal_matches: list[dict] = []
    if isinstance(jm_raw, list):
        for j in jm_raw[:6]:
            if not isinstance(j, dict):
                continue
            journal_matches.append({
                "name": str(j.get("name", "")),
                "publisher": str(j.get("publisher", "")),
                "quartile": str(j.get("quartile", "Q2")),
                "scope_match": round(max(0.0, min(1.0, _float("scope_match", 0.7, j))), 3),
                "acceptance_probability": round(max(0.0, min(1.0, _float("acceptance_probability", 0.25, j))), 3),
                "impact_factor": j.get("impact_factor"),
                "submission_notes": str(j.get("submission_notes", "")),
                "open_access": bool(j.get("open_access", False)),
            })

    rec_raw = str(d.get("recommendation", "major_revision")).lower()
    overall = max(0.0, min(100.0, _float("overall_score", 60.0)))

    return {
        "inferred_discipline": _str("inferred_discipline"),
        "executive_summary": _str("executive_summary"),
        "peer_review_report": _str("peer_review_report"),
        "editorial_assessment": _str("editorial_assessment"),
        "overall_score": overall,
        "recommendation": rec_raw,
        "review_dimensions_ai": dims_out,
        "additional_issues": add_issues,
        "publication_readiness": pub_readiness,
        "journal_matches": journal_matches,
    }


def _empty_ai_result() -> dict:
    return {
        "inferred_discipline": "",
        "executive_summary": "AI review could not be completed. Rule-based analysis is available.",
        "peer_review_report": "",
        "editorial_assessment": "",
        "overall_score": 0.0,
        "recommendation": "major_revision",
        "review_dimensions_ai": {},
        "additional_issues": [],
        "publication_readiness": {
            "acceptance_probability": 0.0,
            "desk_rejection_risk": 0.5,
            "major_revision_probability": 0.5,
            "minor_revision_probability": 0.0,
            "reviewer_difficulty": "moderate",
            "estimated_revision_effort": "unknown",
            "target_tier": "Q2",
            "strengths": [],
            "barriers": ["AI review unavailable"],
        },
        "journal_matches": [],
    }
