"""Methodology Agent (Phase XIII)."""
from __future__ import annotations

import re
import time

from .base_agent import AcademicAgent, AgentRegistry
from .models import AgentContext, AgentResult, AgentTask, AgentType

_DESIGN_SIGNALS = {
    "experimental": ["experiment", "rct", "randomised", "randomized", "control group", "intervention"],
    "quasi-experimental": ["quasi", "pre-post", "interrupted time series", "natural experiment"],
    "cross-sectional": ["cross-section", "survey", "questionnaire", "snapshot"],
    "longitudinal": ["longitudinal", "panel", "cohort", "follow-up", "tracking"],
    "qualitative": ["interview", "focus group", "thematic analysis", "grounded theory", "ethnograph"],
    "mixed methods": ["mixed method", "triangulate", "qual", "quant"],
    "case study": ["case study", "single case", "multiple case", "yin"],
    "systematic review": ["systematic review", "meta-analysis", "prisma", "cochrane"],
}

_VALIDITY_SIGNALS = {
    "internal": ["confound", "selection bias", "attrition", "random assignment", "blinding"],
    "external": ["generalis", "generaliz", "external validity", "sample representat"],
    "construct": ["construct validity", "cronbach", "reliability", "convergent", "discriminant"],
    "statistical": ["power", "effect size", "sample size", "type i", "type ii"],
}

_SAMPLING_RE = re.compile(r"\bn\s*=\s*(\d+)\b|\bsample\s+(?:of|size|n)\s*[:=]?\s*(\d+)\b", re.IGNORECASE)


@AgentRegistry.register
class MethodologyAgent(AcademicAgent):
    agent_id = "methodology_agent_v1"
    agent_type = AgentType.METHODOLOGY
    name = "Methodology Agent"
    domain = "Research Methodology"
    capabilities = [
        "study_design_assessment", "variable_identification", "sampling_analysis",
        "validity_assessment", "methods_recommendation",
    ]

    async def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        t0 = time.monotonic()
        text = task.content
        text_lower = text.lower()

        # Detect study design
        designs = {d: any(s in text_lower for s in signals)
                   for d, signals in _DESIGN_SIGNALS.items()}
        detected_designs = [d for d, found in designs.items() if found]

        # Validity coverage
        validity = {dim: any(s in text_lower for s in signals)
                    for dim, signals in _VALIDITY_SIGNALS.items()}
        validity_coverage = sum(validity.values()) / len(validity)

        # Sample size
        sample_matches = _SAMPLING_RE.findall(text)
        sample_sizes = []
        for m in sample_matches:
            val = next((int(v) for v in m if v), None)
            if val:
                sample_sizes.append(val)
        has_sample_info = bool(sample_sizes)
        max_sample = max(sample_sizes) if sample_sizes else 0

        # Issues
        issues: list[str] = []
        if not detected_designs:
            issues.append("No study design identified — specify research design explicitly")
        if not validity["statistical"]:
            issues.append("Statistical power/sample size justification missing")
        if not validity["internal"]:
            issues.append("Internal validity threats not addressed")
        if max_sample < 30 and max_sample > 0:
            issues.append(f"Small sample (n={max_sample}) — power may be insufficient for parametric tests")
        if "control group" not in text_lower and "experimental" in str(detected_designs).lower():
            issues.append("Experimental design without explicit control group")

        confidence = min(0.92, 0.4 + 0.15 * len(detected_designs) + 0.2 * validity_coverage)

        output = {
            "detected_designs": detected_designs,
            "primary_design": detected_designs[0] if detected_designs else "unspecified",
            "sample_sizes_detected": sample_sizes[:5],
            "validity_coverage": {k: v for k, v in validity.items()},
            "validity_score": round(validity_coverage, 3),
            "methodological_issues": issues,
            "recommendations": [
                "Pre-register the study at OSF or clinicaltrials.gov if applicable",
                "Conduct a priori power analysis to justify sample size",
                "Address all four validity types: internal, external, construct, statistical",
                "Use a CONSORT/PRISMA/STROBE checklist appropriate to your design",
            ],
        }

        return self._timed_result(
            task, output, confidence,
            reasoning=(
                f"Detected design(s): {', '.join(detected_designs) or 'none'}. "
                f"Validity coverage: {validity_coverage:.0%}. "
                f"{len(issues)} methodological issues found."
            ),
            evidence=[f"Design signal: {d}" for d in detected_designs[:4]],
            t0=t0,
        )
