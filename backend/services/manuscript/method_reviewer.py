"""Methodology reviewer — Phase IX.

Evaluates research design, sampling, data collection, analysis methods,
bias mitigation, and replication information.
"""
from __future__ import annotations

import re

from .models import (
    QualityDimension, ReviewIssue, IssueSeverity, _score_to_grade,
)

# ── Research design signals ───────────────────────────────────────────────────

_RESEARCH_DESIGNS: dict[str, list[str]] = {
    "experimental": [
        "experiment", "randomized", "randomised", "rct", "control group",
        "treatment group", "placebo", "double-blind", "single-blind",
    ],
    "quasi_experimental": [
        "quasi-experiment", "pre-test post-test", "pretest posttest",
        "control group", "matched", "propensity score",
    ],
    "survey": [
        "survey", "questionnaire", "likert", "scale", "respondent",
        "cross-sectional", "self-report",
    ],
    "case_study": [
        "case study", "case studies", "in-depth", "single case", "multiple case",
    ],
    "ethnography": [
        "ethnograph", "fieldwork", "participant observation", "immersive",
    ],
    "grounded_theory": [
        "grounded theory", "theoretical saturation", "constant comparison",
        "open coding", "axial coding", "selective coding",
    ],
    "systematic_review": [
        "systematic review", "systematic literature", "PRISMA", "prisma",
        "inclusion criteria", "exclusion criteria", "search strategy",
    ],
    "meta_analysis": [
        "meta-analysis", "meta analysis", "pooled estimate", "forest plot",
        "heterogeneity",
    ],
    "longitudinal": [
        "longitudinal", "panel data", "time series", "cohort", "follow-up",
        "repeated measures",
    ],
    "comparative": [
        "comparative", "cross-country", "cross-national", "multi-site",
        "multi-country",
    ],
    "mixed_methods": [
        "mixed method", "mixed-method", "triangulation", "qual-quant",
        "qualitative and quantitative",
    ],
}

_SAMPLING_METHODS: dict[str, list[str]] = {
    "random": ["random sampling", "simple random", "stratified random", "systematic random"],
    "purposive": ["purposive", "purposeful", "criterion-based", "maximum variation"],
    "snowball": ["snowball", "chain referral"],
    "convenience": ["convenience", "available participants", "opportunistic"],
    "theoretical": ["theoretical sampling", "theoretical saturation"],
    "cluster": ["cluster sampling", "multistage sampling"],
}

_BIAS_SIGNALS = [
    "bias", "confound", "selection bias", "response bias", "social desirability",
    "attrition", "dropout", "missing data", "potential bias", "limitation",
    "threat to validity", "internal validity", "external validity",
    "construct validity",
]
_INSTRUMENT_SIGNALS = [
    "instrument", "validated", "reliability", "cronbach", "validity",
    "test-retest", "inter-rater", "kappa", "alpha", "pilot test",
    "pilot study",
]
_SAMPLE_SIZE_PATTERN = re.compile(
    r"(?:n\s*=\s*|N\s*=\s*|sample(?:\s+size)?\s+(?:of|was|were|is|=)\s*)"
    r"(\d[\d,]*)",
    re.IGNORECASE,
)
_PROCEDURE_SIGNALS = [
    "procedure", "protocol", "step", "phase", "stage", "data collection",
    "administered", "completed", "conducted",
]


def _match_any(text_lower: str, signals: list[str]) -> bool:
    return any(s in text_lower for s in signals)


def _detect_design(text_lower: str) -> str:
    for design, signals in _RESEARCH_DESIGNS.items():
        if _match_any(text_lower, signals):
            return design
    return "unspecified"


def _detect_sampling(text_lower: str) -> str:
    for method, signals in _SAMPLING_METHODS.items():
        if _match_any(text_lower, signals):
            return method
    return "unspecified"


def _detect_sample_size(text: str) -> int:
    m = _SAMPLE_SIZE_PATTERN.search(text)
    if m:
        try:
            return int(m.group(1).replace(",", ""))
        except ValueError:
            pass
    return 0


def review_methodology(
    text: str,
) -> tuple[QualityDimension, list[ReviewIssue]]:
    text_lower = text.lower()
    issues: list[ReviewIssue] = []
    strengths: list[str] = []
    weaknesses: list[str] = []
    score_components: list[float] = []

    design = _detect_design(text_lower)
    sampling = _detect_sampling(text_lower)
    sample_size = _detect_sample_size(text)
    has_instrument = _match_any(text_lower, _INSTRUMENT_SIGNALS)
    has_bias = _match_any(text_lower, _BIAS_SIGNALS)
    has_procedure = _match_any(text_lower, _PROCEDURE_SIGNALS)

    # ── 1. Research design identification ─────────────────────────────────────
    if design != "unspecified":
        score_components.append(88.0)
        strengths.append(f"Research design identified: {design.replace('_', ' ').title()}")
    else:
        score_components.append(45.0)
        weaknesses.append("Research design not clearly specified")
        issues.append(ReviewIssue(
            severity=IssueSeverity.MAJOR,
            section="Methodology",
            title="Research design not clearly specified",
            description=(
                "The methodology section does not clearly identify the research design "
                "(e.g., experimental, survey, case study, systematic review)."
            ),
            recommendation=(
                "Open the Methodology section by explicitly naming the research design: "
                "'This study employs a [design type] design because...' with justification."
            ),
        ))

    # ── 2. Sampling ───────────────────────────────────────────────────────────
    if sampling != "unspecified":
        score_components.append(82.0)
        strengths.append(f"Sampling strategy identified: {sampling.replace('_', ' ').title()}")
    else:
        score_components.append(50.0)
        weaknesses.append("Sampling strategy not explained")
        issues.append(ReviewIssue(
            severity=IssueSeverity.MAJOR,
            section="Methodology / Participants",
            title="Sampling strategy not described",
            description=(
                "The manuscript does not explain how participants/cases were selected. "
                "Sampling adequacy is a core peer-review criterion."
            ),
            recommendation=(
                "Describe the sampling strategy (random, purposive, convenience, etc.), "
                "justify the choice, and explain how it supports representativeness."
            ),
        ))

    # ── 3. Sample size ────────────────────────────────────────────────────────
    if sample_size > 0:
        if sample_size >= 200:
            score_components.append(90.0)
            strengths.append(f"Adequate sample size reported (n={sample_size:,})")
        elif sample_size >= 50:
            score_components.append(72.0)
            strengths.append(f"Sample size stated (n={sample_size:,})")
        else:
            score_components.append(55.0)
            weaknesses.append(f"Small sample size (n={sample_size}) may limit generalisability")
            issues.append(ReviewIssue(
                severity=IssueSeverity.MAJOR,
                section="Methodology / Participants",
                title=f"Small sample size (n={sample_size}) — statistical power concern",
                description=(
                    f"The reported sample size (n={sample_size}) may be insufficient "
                    "for the planned analyses. Small samples reduce statistical power "
                    "and generalisability."
                ),
                recommendation=(
                    "Conduct and report an a priori power analysis justifying the sample size. "
                    "If the sample is small by design (qualitative), explain theoretical saturation."
                ),
            ))
    else:
        score_components.append(45.0)
        weaknesses.append("Sample size not reported")
        issues.append(ReviewIssue(
            severity=IssueSeverity.MAJOR,
            section="Methodology",
            title="Sample size not reported",
            description=(
                "The manuscript does not report the total sample size. "
                "This is a mandatory reporting requirement."
            ),
            recommendation=(
                "Report total N and sub-group n clearly in the Participants section. "
                "Include response rate for surveys."
            ),
        ))

    # ── 4. Instruments / measures ──────────────────────────────────────────────
    if has_instrument:
        score_components.append(80.0)
        strengths.append("Measurement instruments described or validated")
    else:
        score_components.append(55.0)
        weaknesses.append("Measurement instruments not described")
        issues.append(ReviewIssue(
            severity=IssueSeverity.MAJOR,
            section="Methodology / Instruments",
            title="Measurement instruments not described",
            description=(
                "No description of measurement instruments, scales, or questionnaires found. "
                "Without this, readers cannot assess measurement validity."
            ),
            recommendation=(
                "Describe all instruments used, including source (validated scale or "
                "author-developed), number of items, Likert scale range, and "
                "reliability (Cronbach's α ≥ 0.70)."
            ),
        ))

    # ── 5. Bias acknowledgement ───────────────────────────────────────────────
    if has_bias:
        score_components.append(82.0)
        strengths.append("Methodological biases and threats acknowledged")
    else:
        score_components.append(50.0)
        weaknesses.append("No bias mitigation discussed")
        issues.append(ReviewIssue(
            severity=IssueSeverity.MAJOR,
            section="Methodology / Limitations",
            title="Methodological biases not discussed",
            description=(
                "The manuscript does not acknowledge potential biases (selection, response, "
                "social desirability, attrition) or threats to validity."
            ),
            recommendation=(
                "Add a subsection on potential biases and mitigation strategies. "
                "Address internal validity, external validity, and construct validity separately."
            ),
        ))

    # ── 6. Procedure description ───────────────────────────────────────────────
    if has_procedure:
        score_components.append(80.0)
        strengths.append("Data collection procedure described")
    else:
        score_components.append(50.0)
        weaknesses.append("Data collection procedure not described")
        issues.append(ReviewIssue(
            severity=IssueSeverity.MINOR,
            section="Methodology",
            title="Data collection procedure insufficiently described",
            description=(
                "The manuscript does not describe how data were collected, "
                "making replication impossible."
            ),
            recommendation=(
                "Describe the data collection procedure step by step, including "
                "timeline, data collection instruments, and who collected data."
            ),
        ))

    overall = sum(score_components) / len(score_components) if score_components else 55.0

    dim = QualityDimension(
        name="Methodological Soundness",
        score=round(overall, 1),
        weight=1.5,
        grade=_score_to_grade(overall),
        rationale=(
            f"Design: {design}, Sampling: {sampling}, N={sample_size or '?'}. "
            f"Instrument described: {has_instrument}, Bias addressed: {has_bias}."
        ),
        strengths=strengths[:5],
        weaknesses=weaknesses[:5],
    )
    return dim, issues
