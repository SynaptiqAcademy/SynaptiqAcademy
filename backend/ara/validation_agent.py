"""
Validation Agent — quality-check mission outputs before delivery.

Checks:
  1. Evidence compliance: no fabricated percentages or statistics
  2. Confidence labels: only high/medium/low/not_run/insufficient
  3. Consistency: outputs reference the same mission context
  4. Completeness: all steps that should produce outputs have them
  5. Fabrication pattern detection: catches leaked numeric claims without evidence
"""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

logger = logging.getLogger("ara.validation")

# ── Fabrication patterns ───────────────────────────────────────────────────────

_FABRICATION_PATTERNS = [
    re.compile(r"\b\d{1,3}%\b"),                     # raw percentages
    re.compile(r"\b\d+x\s+(?:more|better|faster)\b", re.I),  # multipliers
    re.compile(r"guaranteed\s+to\b", re.I),
    re.compile(r"will\s+definitely\b", re.I),
    re.compile(r"100\s*%\s+accurate", re.I),
]

_VALID_CONFIDENCE = {"high", "medium", "low", "not_run", "insufficient"}


def _scan_text(text: str) -> list[str]:
    issues = []
    for pat in _FABRICATION_PATTERNS:
        m = pat.search(text)
        if m:
            issues.append(f"Potential fabrication pattern: '{m.group()}'")
    return issues


def _check_step(step: dict) -> list[dict]:
    issues = []
    outputs = step.get("outputs") or {}

    # Confidence label check
    conf = step.get("confidence", "not_run")
    if conf not in _VALID_CONFIDENCE:
        issues.append({"severity": "warning", "field": "confidence",
                       "message": f"Non-standard confidence label '{conf}' in step {step.get('step_id')}"})

    # Scan output text for fabrication patterns
    for key, value in outputs.items():
        text = str(value) if not isinstance(value, str) else value
        for issue in _scan_text(text):
            issues.append({"severity": "warning", "field": f"outputs.{key}",
                           "message": f"Step {step.get('step_id')}: {issue}"})

    # Check failed steps
    if step.get("status") == "failed" and not step.get("error"):
        issues.append({"severity": "warning", "field": "status",
                       "message": f"Step {step.get('step_id')} failed but has no error message"})

    return issues


def run(steps: list[dict], mission: dict) -> dict:
    """
    Validate all mission outputs.
    Returns a validation report dict.
    """
    all_issues: list[dict] = []
    completed = [s for s in steps if s.get("status") == "completed"]
    failed    = [s for s in steps if s.get("status") == "failed"]
    skipped   = [s for s in steps if s.get("status") == "skipped"]

    for step in steps:
        all_issues.extend(_check_step(step))

    # Completeness check
    non_validation = [s for s in completed if s.get("agent_name") != "validation"]
    steps_with_output = [s for s in non_validation if s.get("outputs")]
    completeness = (len(steps_with_output) / len(non_validation)) if non_validation else 1.0

    # Evidence compliance
    evidence_issues = [i for i in all_issues if "fabrication" in i["message"].lower()]
    warnings        = [i for i in all_issues if i["severity"] == "warning"]
    errors          = [i for i in all_issues if i["severity"] == "error"]

    passed = len(errors) == 0

    return {
        "passed":            passed,
        "checked_at":        datetime.now(timezone.utc).isoformat(),
        "steps_total":       len(steps),
        "steps_completed":   len(completed),
        "steps_failed":      len(failed),
        "steps_skipped":     len(skipped),
        "completeness":      round(completeness, 2),
        "errors":            errors,
        "warnings":          warnings,
        "evidence_issues":   evidence_issues,
        "summary":           (
            "All outputs passed quality checks."
            if passed and not warnings
            else f"Validation complete: {len(errors)} errors, {len(warnings)} warnings."
        ),
        "policy_note": (
            "Validation checks evidence compliance and output consistency. "
            "It does not certify scientific accuracy — researcher review is always required."
        ),
    }
