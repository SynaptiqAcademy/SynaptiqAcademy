"""Rule-based scientific quality reviewer — Phase IX.

Checks manuscript text for presence, completeness, and adequacy of
scientific elements: hypotheses, objectives, research questions, ethical
statements, limitations, future work, data availability, replication info.

Returns scored QualityDimension and a list of ReviewIssues.
"""
from __future__ import annotations

import re

from .models import (
    QualityDimension, ReviewIssue, IssueSeverity,
    DetectedSection, SectionType, _score_to_grade,
)

# ── Keyword signals ───────────────────────────────────────────────────────────

_OBJECTIVE_SIGNALS = [
    "objective", "aim of", "purpose of", "goal of", "this study seeks",
    "this paper aims", "we aim", "we seek", "we investigate", "we examine",
    "research objective",
]
_HYPOTHESIS_SIGNALS = [
    r"\bh[0-9]+[:\s]", r"\bhypothes[ie]", r"we hypothesize", r"it is hypothesized",
    r"we predict", r"we expect that", r"proposed that",
]
_RQ_SIGNALS = [
    r"rq[0-9]+[:\s]", r"research question", r"study asks", r"key question",
    r"central question",
]
_LIMITATION_SIGNALS = [
    "limitation", "constraint", "boundary condition", "caveat",
    "weakness", "shortcoming", "threat to validity", "potential bias",
]
_FUTURE_SIGNALS = [
    "future research", "future work", "future studies", "future direction",
    "further research", "further investigation", "next steps",
]
_ETHICS_SIGNALS = [
    "irb", "institutional review board", "ethics committee", "ethical approval",
    "informed consent", "helsinki", "anonymized", "anonymised",
    "privacy", "ethical clearance",
]
_DATA_AVAIL_SIGNALS = [
    "data available", "data will be", "available upon request",
    "dataset", "repository", "github", "zenodo", "figshare", "osf",
    "supplementary data",
]
_REPLICATION_SIGNALS = [
    "reproducib", "replicab", "open code", "code available", "github",
    "transparency", "pre-registration", "preregistration", "open science",
]
_CONTRIBUTION_SIGNALS = [
    "contribution", "contributes to", "extends the literature", "advances",
    "novel", "first study", "original", "unique", "fills the gap",
    "addresses the gap",
]


def _match(text_lower: str, patterns: list[str]) -> bool:
    for pat in patterns:
        if re.search(pat, text_lower):
            return True
    return False


def _contains(text_lower: str, signals: list[str]) -> bool:
    return any(sig in text_lower for sig in signals)


# ── Main reviewer ─────────────────────────────────────────────────────────────

def review_scientific_quality(
    text: str,
    sections: list[DetectedSection],
) -> tuple[QualityDimension, list[ReviewIssue]]:
    """
    Returns (scientific_rigor_dimension, issues).
    Score 0–100 based on presence and adequacy of scientific elements.
    """
    text_lower = text.lower()
    issues: list[ReviewIssue] = []
    checks_passed = 0
    total_checks = 10

    # ── 1. Clear objectives ───────────────────────────────────────────────────
    has_objectives = _contains(text_lower, _OBJECTIVE_SIGNALS)
    if has_objectives:
        checks_passed += 1
    else:
        issues.append(ReviewIssue(
            severity=IssueSeverity.MAJOR,
            section="Introduction / Objectives",
            title="Missing explicit research objectives",
            description=(
                "The manuscript does not clearly state the research objectives or aims. "
                "Reviewers and editors expect explicit, measurable objectives."
            ),
            recommendation=(
                "Add a dedicated paragraph stating 3–5 clear, measurable research "
                "objectives using action verbs (e.g., 'to investigate', 'to compare', 'to develop')."
            ),
        ))

    # ── 2. Research questions or hypotheses ───────────────────────────────────
    has_rq = _match(text_lower, _RQ_SIGNALS)
    has_hyp = _match(text_lower, _HYPOTHESIS_SIGNALS)
    if has_rq or has_hyp:
        checks_passed += 1
    else:
        issues.append(ReviewIssue(
            severity=IssueSeverity.MAJOR,
            section="Introduction / Framework",
            title="No research questions or hypotheses identified",
            description=(
                "The manuscript does not present explicit research questions or testable "
                "hypotheses. This is a fundamental requirement for empirical research."
            ),
            recommendation=(
                "Formulate at least one primary research question (RQ1) or hypothesis (H1). "
                "For experimental studies, include null and alternative hypotheses."
            ),
        ))

    # ── 3. Limitations section ────────────────────────────────────────────────
    has_limitations = _contains(text_lower, _LIMITATION_SIGNALS)
    if has_limitations:
        checks_passed += 1
    else:
        issues.append(ReviewIssue(
            severity=IssueSeverity.MAJOR,
            section="Discussion / Conclusions",
            title="No limitations section",
            description=(
                "No limitations are acknowledged. Failure to address limitations "
                "is a common reason for desk rejection and reviewer criticism."
            ),
            recommendation=(
                "Add a Limitations subsection in Discussion or Conclusions that discusses "
                "at least 3 potential threats to internal validity, external validity, "
                "and methodological limitations."
            ),
        ))

    # ── 4. Future research directions ─────────────────────────────────────────
    has_future = _contains(text_lower, _FUTURE_SIGNALS)
    if has_future:
        checks_passed += 1
    else:
        issues.append(ReviewIssue(
            severity=IssueSeverity.MINOR,
            section="Conclusions",
            title="Missing future research directions",
            description=(
                "The manuscript does not suggest future research directions, "
                "limiting its contribution to the scholarly conversation."
            ),
            recommendation=(
                "Include a brief paragraph on future research directions, addressing "
                "unresolved questions and extensions of the current work."
            ),
        ))

    # ── 5. Ethical compliance ─────────────────────────────────────────────────
    has_ethics = _contains(text_lower, _ETHICS_SIGNALS)
    detected_types = {s.section_type for s in sections}
    has_ethics_section = SectionType.ETHICS in detected_types
    if has_ethics or has_ethics_section:
        checks_passed += 1
    else:
        issues.append(ReviewIssue(
            severity=IssueSeverity.CRITICAL,
            section="Ethics Statement",
            title="Missing ethics statement",
            description=(
                "No ethics statement, IRB approval, or informed consent mention found. "
                "Studies involving human participants require explicit ethics reporting."
            ),
            recommendation=(
                "Add an Ethics Statement section specifying the institutional ethics "
                "approval number, consent procedures, and data anonymisation methods."
            ),
        ))

    # ── 6. Data availability ──────────────────────────────────────────────────
    has_data_avail = _contains(text_lower, _DATA_AVAIL_SIGNALS)
    if has_data_avail:
        checks_passed += 1
    else:
        issues.append(ReviewIssue(
            severity=IssueSeverity.MINOR,
            section="Data Availability",
            title="Missing data availability statement",
            description=(
                "Most high-impact journals now require a Data Availability Statement "
                "explaining where the dataset can be accessed."
            ),
            recommendation=(
                "Add a Data Availability section stating either the repository URL "
                "or 'Data available upon reasonable request to the corresponding author'."
            ),
        ))

    # ── 7. Research contribution ──────────────────────────────────────────────
    has_contribution = _contains(text_lower, _CONTRIBUTION_SIGNALS)
    if has_contribution:
        checks_passed += 1
    else:
        issues.append(ReviewIssue(
            severity=IssueSeverity.MAJOR,
            section="Introduction / Conclusions",
            title="Scientific contribution not clearly articulated",
            description=(
                "The manuscript does not explicitly state its scientific contribution "
                "to the existing body of knowledge."
            ),
            recommendation=(
                "Clearly state 2–3 specific contributions at the end of the Introduction "
                "and reinforce them in the Conclusions."
            ),
        ))

    # ── 8. Reproducibility / replication ─────────────────────────────────────
    has_repro = _contains(text_lower, _REPLICATION_SIGNALS)
    if has_repro:
        checks_passed += 1
    else:
        issues.append(ReviewIssue(
            severity=IssueSeverity.SUGGESTION,
            section="Methodology",
            title="Reproducibility not addressed",
            description=(
                "There is no mention of open code, pre-registration, or procedures "
                "that would enable replication of the study."
            ),
            recommendation=(
                "Consider pre-registering the study, sharing code on GitHub/OSF, "
                "or adding a detailed procedure description enabling replication."
            ),
        ))

    # ── 9. Conflict of interest ───────────────────────────────────────────────
    has_coi = (
        SectionType.CONFLICT_OF_INTEREST in detected_types
        or _contains(text_lower, ["conflict of interest", "no competing", "declare", "the authors declare"])
    )
    if has_coi:
        checks_passed += 1
    else:
        issues.append(ReviewIssue(
            severity=IssueSeverity.MINOR,
            section="Conflict of Interest",
            title="Missing conflict of interest statement",
            description="No conflict of interest declaration found.",
            recommendation="Add a Conflict of Interest statement (even if there is none to declare).",
        ))

    # ── 10. Funding acknowledgement ───────────────────────────────────────────
    has_funding = (
        SectionType.FUNDING in detected_types
        or _contains(text_lower, ["funded by", "grant", "supported by", "fellowship"])
    )
    if has_funding:
        checks_passed += 1
    else:
        issues.append(ReviewIssue(
            severity=IssueSeverity.SUGGESTION,
            section="Acknowledgements",
            title="Funding sources not mentioned",
            description="No funding acknowledgement found.",
            recommendation=(
                "Add a Funding section or mention 'This research received no specific "
                "external funding' if applicable."
            ),
        ))

    # ── Score ─────────────────────────────────────────────────────────────────
    score = (checks_passed / total_checks) * 100
    strengths: list[str] = []
    weaknesses: list[str] = []

    if has_objectives:
        strengths.append("Research objectives clearly stated")
    if has_rq or has_hyp:
        strengths.append("Research questions or hypotheses explicitly formulated")
    if has_limitations:
        strengths.append("Limitations acknowledged")
    if has_ethics or has_ethics_section:
        strengths.append("Ethics compliance reported")
    if has_contribution:
        strengths.append("Scientific contribution articulated")

    for issue in issues:
        if issue.severity in (IssueSeverity.CRITICAL, IssueSeverity.MAJOR):
            weaknesses.append(issue.title)

    dim = QualityDimension(
        name="Scientific Rigor",
        score=round(score, 1),
        weight=1.5,
        grade=_score_to_grade(score),
        rationale=(
            f"Scientific rigor check: {checks_passed}/{total_checks} elements present. "
            f"{'Key elements missing: ' + '; '.join(weaknesses[:3]) if weaknesses else 'All major scientific elements identified.'}"
        ),
        strengths=strengths,
        weaknesses=weaknesses,
    )
    return dim, issues
