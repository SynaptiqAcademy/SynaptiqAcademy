"""Data Analysis Agent (Phase XIII)."""
from __future__ import annotations

import re
import time

from .base_agent import AcademicAgent, AgentRegistry
from .models import AgentContext, AgentResult, AgentTask, AgentType

_TOOL_SIGNALS = {
    "R": [r"\bR\s*\(", r"\bggplot\b", r"\bdplyr\b", r"\brmarkdown\b", r"\blavaan\b", r"\blme4\b"],
    "Python": [r"\bpython\b", r"\bpandas\b", r"\bnumpy\b", r"\bscipy\b", r"\bsklearn\b"],
    "SPSS": [r"\bspss\b", r"\bibm\s+spss\b"],
    "Stata": [r"\bstata\b"],
    "SAS": [r"\bsas\b"],
    "MATLAB": [r"\bmatlab\b"],
    "Excel": [r"\bexcel\b", r"\bmicrosoft\s+excel\b"],
}

_DATA_TYPE_SIGNALS = {
    "survey": [r"\bsurvey\b", r"\bquestionnaire\b", r"\blikert\b"],
    "clinical": [r"\bclinical\b", r"\bpatient\b", r"\bmedical\s+record\b", r"\behr\b"],
    "experimental": [r"\bexperiment\b", r"\blaboratory\b", r"\btrial\b"],
    "observational": [r"\bobservation\b", r"\bfield\s+data\b", r"\bnaturalistic\b"],
    "secondary": [r"\bsecondary\s+data\b", r"\bexisting\s+dataset\b", r"\barchive\b"],
    "text/NLP": [r"\btext\s+data\b", r"\bnlp\b", r"\bcorpus\b", r"\btweet\b"],
    "spatial": [r"\bgis\b", r"\bgeospatial\b", r"\bspatial\s+analysis\b"],
}

_MISSING_RE = re.compile(r"\bmissing\s+data\b|\bimputation\b|\bmultiple\s+imputation\b|\blistwise\b", re.IGNORECASE)
_OUTLIER_RE = re.compile(r"\boutlier[s]?\b|\binfluential\s+case\b|\bwinsoris\b", re.IGNORECASE)


@AgentRegistry.register
class DataAnalysisAgent(AcademicAgent):
    agent_id = "data_analysis_agent_v1"
    agent_type = AgentType.DATA_ANALYSIS
    name = "Data Analysis Agent"
    domain = "Data Analysis & Reproducibility"
    capabilities = [
        "tool_detection", "data_type_classification", "pipeline_review",
        "reproducibility_assessment", "missing_data_handling",
    ]

    async def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        t0 = time.monotonic()
        text = task.content
        text_lower = text.lower()

        tools = {t: any(re.search(p, text_lower) for p in patterns)
                 for t, patterns in _TOOL_SIGNALS.items()}
        detected_tools = [t for t, found in tools.items() if found]

        data_types = {dt: any(re.search(p, text_lower) for p in patterns)
                      for dt, patterns in _DATA_TYPE_SIGNALS.items()}
        detected_types = [dt for dt, found in data_types.items() if found]

        handles_missing = bool(_MISSING_RE.search(text))
        handles_outliers = bool(_OUTLIER_RE.search(text))
        has_open_data = any(kw in text_lower for kw in ["github", "zenodo", "osf", "dryad", "figshare", "code available"])
        has_reproducibility = any(kw in text_lower for kw in ["reproducible", "replication", "open code", "rmarkdown", "jupyter"])

        issues: list[str] = []
        if not detected_tools:
            issues.append("Analysis tool not specified — declare software (R, Python, SPSS, etc.)")
        if not handles_missing:
            issues.append("Missing data handling strategy not described")
        if not handles_outliers:
            issues.append("Outlier detection/handling not mentioned")
        if not has_reproducibility:
            issues.append("Reproducibility strategy missing — share code on GitHub/OSF")

        repro_score = (handles_missing * 0.25 + handles_outliers * 0.25 + has_open_data * 0.25 + has_reproducibility * 0.25)
        confidence = min(0.92, 0.4 + 0.15 * bool(detected_tools) + 0.1 * bool(detected_types) + 0.3 * repro_score)

        output = {
            "detected_tools": detected_tools,
            "detected_data_types": detected_types,
            "handles_missing_data": handles_missing,
            "handles_outliers": handles_outliers,
            "has_open_data": has_open_data,
            "reproducibility_score": round(repro_score, 3),
            "analysis_issues": issues,
            "recommendations": [
                "Share analysis code on GitHub or OSF for reproducibility",
                "Document all data preprocessing steps",
                "Use R Markdown or Jupyter Notebooks for reproducible reports",
                "Deposit data in Zenodo/Dryad with a DOI",
                "Report software version numbers (e.g., R 4.3.2, Python 3.11)",
            ],
        }

        return self._timed_result(
            task, output, confidence,
            reasoning=(
                f"Tools: {', '.join(detected_tools) or 'none detected'}. "
                f"Data types: {', '.join(detected_types) or 'unspecified'}. "
                f"Reproducibility score: {repro_score:.0%}."
            ),
            evidence=detected_tools + detected_types,
            t0=t0,
        )
