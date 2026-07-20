"""Quality Control Agent — validates all agent outputs before the final response."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal

logger = logging.getLogger("copilot.quality")

# Known fabrication patterns to catch before delivery
FABRICATION_PATTERNS = [
    ("% more", "percentage without evidence"),
    ("% less", "percentage without evidence"),
    ("x faster", "multiplier without evidence"),
    ("times faster", "multiplier without evidence"),
    ("times more likely", "multiplier without evidence"),
    ("acceptance probability", "fabricated probability"),
    ("guaranteed to", "unverifiable guarantee"),
    ("will definitely", "unverifiable certainty"),
    ("research shows that", "vague citation"),
    ("studies show that", "vague citation"),
]

# Evidence policy: these statuses are considered acceptable
ACCEPTABLE_STATUSES = {"success", "partial", "insufficient_data"}


@dataclass
class QualityResult:
    passed:    bool
    score:     int        # 0-100
    issues:    list[str]  = field(default_factory=list)
    warnings:  list[str]  = field(default_factory=list)
    agent_statuses: dict  = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "passed":         self.passed,
            "score":          self.score,
            "issues":         self.issues,
            "warnings":       self.warnings,
            "agent_statuses": self.agent_statuses,
        }


class QualityAgent:
    name = "quality"

    def validate(self, outputs: list, user_input: str) -> QualityResult:
        """
        Validate all agent outputs synchronously.
        Returns QualityResult with issues/warnings list.
        """
        issues:   list[str] = []
        warnings: list[str] = []
        agent_statuses: dict = {}

        if not outputs:
            return QualityResult(passed=False, score=0, issues=["No agent outputs produced."])

        total = len(outputs)
        ok    = 0

        for output in outputs:
            name   = output.agent_name
            status = output.status
            agent_statuses[name] = status

            if status == "error":
                issues.append(f"{name}: agent execution error")
            elif status == "insufficient_data":
                warnings.append(f"{name}: insufficient data — limitations will be shown to user")
                ok += 0.5
            elif status in ("success", "partial"):
                ok += 1

            # Check for fabrication patterns in content
            content_lower = output.content.lower()
            for pattern, label in FABRICATION_PATTERNS:
                if pattern in content_lower:
                    # Warn but don't block — the AI output may legitimately use these phrases
                    # in appropriate statistical contexts (e.g., user provided their own data)
                    warnings.append(f"{name}: contains '{pattern}' — verify this is from real evidence ({label})")

            # Check evidence policy
            if status == "success" and not output.evidence:
                issues.append(f"{name}: status=success but evidence[] is empty — evidence policy violation")
                ok -= 0.5

        # Check consistency between agents
        # E.g., if literature agent found papers but citation agent claims none exist
        lit_out   = next((o for o in outputs if o.agent_name == "literature"), None)
        cite_out  = next((o for o in outputs if o.agent_name == "citation"), None)
        if lit_out and cite_out and lit_out.status == "success" and cite_out.status == "insufficient_data":
            warnings.append("citation: insufficient_data despite literature agent finding papers — consider passing papers to citation agent")

        score   = max(0, min(100, int(ok / total * 100))) if total else 0
        passed  = score >= 40 and len(issues) == 0

        return QualityResult(
            passed=passed,
            score=score,
            issues=issues,
            warnings=warnings,
            agent_statuses=agent_statuses,
        )


QUALITY_AGENT = QualityAgent()
