"""Statistical Intelligence 2.0 — Validity reviewer (Phase X).

Evaluates internal, external, construct, and statistical conclusion validity.
Also checks reliability metrics: Cronbach α, CR, AVE, HTMT, KMO.
"""
from __future__ import annotations

import re
from .models import (
    IssueSeverity, ReliabilityMetrics, ResearchDesign, StatisticalIssue,
    StudyType, ValidityAnalysis, ValidityThreat, _score_to_grade,
)

# ── Reliability metric patterns ───────────────────────────────────────────────

_CRONBACH_RE  = re.compile(r"(?:cronbach'?s?\s*(?:alpha|α)|α\s*=)\s*[=:]?\s*(\d+\.?\d*)", re.IGNORECASE)
_CR_RE        = re.compile(r"composite reliability\s*[=:>]?\s*[=:]?\s*(\d+\.?\d*)", re.IGNORECASE)
_AVE_RE       = re.compile(r"\bAVE\s*[=:]\s*(\d+\.?\d*)", re.IGNORECASE)
_HTMT_RE      = re.compile(r"\bHTMT\s*[=:]\s*(\d+\.?\d*)", re.IGNORECASE)
_KMO_RE       = re.compile(r"\bKMO\s*[=:]\s*(\d+\.?\d*)", re.IGNORECASE)
_BARTLETT_RE  = re.compile(r"bartlett'?s?\s*test.*?p\s*[=<]\s*(\d+\.?\d*)", re.IGNORECASE)

# ── Validity threat signals ───────────────────────────────────────────────────

_INTERNAL_THREATS: list[tuple[str, list[str], str, str]] = [
    ("History effects",
     ["historical event", "external event during study", "concurrent history"],
     "Uncontrolled historical events may confound pre-post differences.",
     "Use a control group unexposed to the treatment but exposed to history."),
    ("Maturation",
     ["maturation", "natural development", "growth over time"],
     "Natural developmental change may be mistaken for treatment effect.",
     "Include a control group and measure maturation separately."),
    ("Testing effects",
     ["test-retest", "sensitization", "practice effect", "pre-test"],
     "Prior testing may sensitise participants to post-test outcomes.",
     "Use Solomon four-group design or wait-list control."),
    ("Selection bias",
     ["selection bias", "non-random assignment", "self-selection"],
     "Non-random group assignment may cause pre-existing group differences.",
     "Use randomisation or propensity score matching."),
    ("Attrition",
     ["attrition", "differential dropout", "loss to follow-up"],
     "Systematic dropout can bias results if related to the outcome.",
     "Conduct attrition analysis and use ITT analysis."),
    ("Confounding variables",
     ["confound", "confounding", "third variable", "lurking variable"],
     "Uncontrolled confounders may account for the observed relationship.",
     "Add confounders as covariates in ANCOVA or use propensity score methods."),
]

_EXTERNAL_THREATS: list[tuple[str, list[str], str, str]] = [
    ("Sample representativeness",
     ["convenience sample", "non-representative", "limited generalizability",
      "specific population"],
     "A non-representative sample limits generalisation to the broader population.",
     "Discuss scope conditions; use stratified sampling if possible."),
    ("Ecological validity",
     ["lab setting", "artificial", "controlled environment", "low ecological"],
     "Controlled settings may not reflect real-world conditions.",
     "Replicate findings in naturalistic settings."),
    ("Time limitations",
     ["short-term", "limited time", "cross-sectional"],
     "Cross-sectional designs cannot capture long-term effects.",
     "Discuss temporal limitations; conduct follow-up studies."),
]

_CONSTRUCT_THREATS: list[tuple[str, list[str], str, str]] = [
    ("Common method bias",
     ["common method bias", "common method variance", "cmv", "cmb", "harman"],
     "Self-reported predictor and outcome measures introduce common method bias.",
     "Apply Harman's single factor test, marker variable technique, or ULMC."),
    ("Low reliability",
     ["low alpha", "cronbach < .7", "unreliable"],
     "Low Cronbach α (<0.70) indicates insufficient internal consistency.",
     "Remove items that reduce α. Target Cronbach α ≥ 0.70."),
    ("Construct validity not established",
     ["validity not established", "no validity evidence", "untested instrument"],
     "Measurement instrument validity has not been established.",
     "Report CFA results with factor loadings, AVE, and CR to establish validity."),
    ("Social desirability",
     ["social desirability", "demand characteristics", "acquiescence"],
     "Participants may respond according to social norms rather than true attitudes.",
     "Use reverse-coded items and social desirability scales."),
]

_STAT_CONCLUSION_THREATS: list[tuple[str, list[str], str, str]] = [
    ("Low statistical power",
     ["underpowered", "low power", "insufficient power", "small effect"],
     "Low power increases Type II error probability.",
     "Report achieved power; increase sample size in future studies."),
    ("Multiple comparisons",
     ["multiple comparison", "familywise error", "type i inflation",
      "bonferroni", "fdr", "holm"],
     "Multiple tests increase the probability of false positives.",
     "Apply Bonferroni correction, FDR (Benjamini-Hochberg), or report adjusted p-values."),
    ("Violated assumptions",
     ["violated assumption", "assumption violation", "non-normal", "heteroscedastic"],
     "Violated statistical assumptions undermine the validity of test results.",
     "Use assumption-robust alternatives (e.g., bootstrap, robust SE, non-parametrics)."),
]


def _extract_reliability_metrics(text: str) -> ReliabilityMetrics:
    metrics = ReliabilityMetrics()

    ca_m = _CRONBACH_RE.search(text)
    if ca_m:
        try:
            metrics.cronbach_alpha = float(ca_m.group(1))
        except ValueError:
            pass

    cr_m = _CR_RE.search(text)
    if cr_m:
        try:
            metrics.composite_reliability = float(cr_m.group(1))
        except ValueError:
            pass

    ave_m = _AVE_RE.search(text)
    if ave_m:
        try:
            metrics.ave = float(ave_m.group(1))
        except ValueError:
            pass

    htmt_m = _HTMT_RE.search(text)
    if htmt_m:
        try:
            metrics.htmt = float(htmt_m.group(1))
        except ValueError:
            pass

    kmo_m = _KMO_RE.search(text)
    if kmo_m:
        try:
            metrics.kmo = float(kmo_m.group(1))
        except ValueError:
            pass

    bartlett_m = _BARTLETT_RE.search(text)
    if bartlett_m:
        try:
            p = float(bartlett_m.group(1))
            metrics.bartlett_sig = p < 0.05
        except ValueError:
            pass

    return metrics


def _review_reliability(
    metrics: ReliabilityMetrics, issues: list[StatisticalIssue]
) -> None:
    if metrics.cronbach_alpha is not None:
        if metrics.cronbach_alpha < 0.60:
            issues.append(StatisticalIssue(
                severity=IssueSeverity.CRITICAL,
                category="validity",
                title=f"Unacceptable reliability (α={metrics.cronbach_alpha:.2f})",
                description=f"Cronbach α={metrics.cronbach_alpha:.2f} is below the minimum threshold of 0.60.",
                recommendation="Remove problematic items, review scale items, or use a validated instrument.",
            ))
        elif metrics.cronbach_alpha < 0.70:
            issues.append(StatisticalIssue(
                severity=IssueSeverity.MAJOR,
                category="validity",
                title=f"Marginal reliability (α={metrics.cronbach_alpha:.2f})",
                description=f"Cronbach α={metrics.cronbach_alpha:.2f} is below the preferred threshold of 0.70.",
                recommendation="Target α≥0.70. Report item-total correlations to identify weak items.",
            ))

    if metrics.ave is not None and metrics.ave < 0.50:
        issues.append(StatisticalIssue(
            severity=IssueSeverity.MAJOR,
            category="validity",
            title=f"Insufficient AVE (AVE={metrics.ave:.3f})",
            description=(
                f"AVE={metrics.ave:.3f} is below the 0.50 threshold. "
                "More than half the variance is measurement error."
            ),
            recommendation="Improve convergent validity by removing weak indicators (loadings <0.60).",
        ))

    if metrics.htmt is not None and metrics.htmt > 0.90:
        issues.append(StatisticalIssue(
            severity=IssueSeverity.MAJOR,
            category="validity",
            title=f"Poor discriminant validity (HTMT={metrics.htmt:.3f})",
            description=(
                f"HTMT={metrics.htmt:.3f} exceeds 0.90, indicating that constructs "
                "may not be empirically distinguishable."
            ),
            recommendation="Revise constructs to improve discriminant validity. Target HTMT < 0.85.",
        ))

    if metrics.kmo is not None and metrics.kmo < 0.60:
        issues.append(StatisticalIssue(
            severity=IssueSeverity.MAJOR,
            category="validity",
            title=f"Inadequate sampling adequacy (KMO={metrics.kmo:.3f})",
            description=f"KMO={metrics.kmo:.3f} is below 0.60, indicating poor sampling adequacy for factor analysis.",
            recommendation="Reconsider the variable set. KMO < 0.50 is unacceptable.",
        ))


def review_validity(
    text: str, design: ResearchDesign
) -> tuple[ValidityAnalysis, list[StatisticalIssue]]:
    lower = text.lower()
    analysis = ValidityAnalysis()
    issues: list[StatisticalIssue] = []

    # ── Reliability metrics ────────────────────────────────────────────────────
    analysis.reliability = _extract_reliability_metrics(text)
    _review_reliability(analysis.reliability, issues)

    # ── Validity threats ──────────────────────────────────────────────────────
    internal_threats: list[ValidityThreat] = []
    for name, signals, desc, mitigation in _INTERNAL_THREATS:
        if any(s in lower for s in signals):
            threat = ValidityThreat(
                threat_type="internal",
                threat=name,
                description=desc,
                mitigation=mitigation,
                severity=IssueSeverity.MODERATE,
            )
            internal_threats.append(threat)
            analysis.threats.append(threat)

    external_threats: list[ValidityThreat] = []
    for name, signals, desc, mitigation in _EXTERNAL_THREATS:
        if any(s in lower for s in signals):
            threat = ValidityThreat(
                threat_type="external",
                threat=name,
                description=desc,
                mitigation=mitigation,
                severity=IssueSeverity.MODERATE,
            )
            external_threats.append(threat)
            analysis.threats.append(threat)

    construct_threats: list[ValidityThreat] = []
    for name, signals, desc, mitigation in _CONSTRUCT_THREATS:
        if any(s in lower for s in signals):
            threat = ValidityThreat(
                threat_type="construct",
                threat=name,
                description=desc,
                mitigation=mitigation,
                severity=IssueSeverity.MODERATE,
            )
            construct_threats.append(threat)
            analysis.threats.append(threat)

    stat_threats: list[ValidityThreat] = []
    for name, signals, desc, mitigation in _STAT_CONCLUSION_THREATS:
        if any(s in lower for s in signals):
            threat = ValidityThreat(
                threat_type="statistical_conclusion",
                threat=name,
                description=desc,
                mitigation=mitigation,
                severity=IssueSeverity.MAJOR,
            )
            stat_threats.append(threat)
            analysis.threats.append(threat)
            issues.append(StatisticalIssue(
                severity=IssueSeverity.MODERATE,
                category="validity",
                title=f"Validity threat: {name}",
                description=desc,
                recommendation=mitigation,
            ))

    # Non-experimental designs must flag causality
    if design.study_type in (StudyType.CROSS_SECTIONAL, StudyType.SURVEY, StudyType.OBSERVATIONAL):
        if "causal" in lower or "cause" in lower:
            issues.append(StatisticalIssue(
                severity=IssueSeverity.MAJOR,
                category="validity",
                title="Causal language in non-experimental design",
                description=(
                    f"Causal language detected in a {design.study_type.value} design. "
                    "Correlational designs cannot establish causality."
                ),
                recommendation=(
                    "Replace causal language ('X causes Y') with associative language "
                    "('X is associated with Y'). Discuss directionality limitations."
                ),
            ))

    # ── Scoring ────────────────────────────────────────────────────────────────
    total_threats = len(internal_threats) + len(external_threats) + len(construct_threats) + len(stat_threats)
    analysis.internal_validity_score  = max(0, 80 - len(internal_threats) * 15)
    analysis.external_validity_score  = max(0, 80 - len(external_threats) * 15)
    analysis.construct_validity_score = max(0, 80 - len(construct_threats) * 15)

    # Bonus for tested reliability
    if analysis.reliability.cronbach_alpha and analysis.reliability.cronbach_alpha >= 0.70:
        analysis.construct_validity_score = min(100, analysis.construct_validity_score + 10)

    analysis.overall_validity_score = (
        analysis.internal_validity_score * 0.35 +
        analysis.external_validity_score * 0.25 +
        analysis.construct_validity_score * 0.40
    )
    analysis.grade = _score_to_grade(analysis.overall_validity_score)

    return analysis, issues
