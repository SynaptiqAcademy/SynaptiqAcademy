"""Statistical Intelligence 2.0 — Result interpreter (Phase X).

Evaluates p-values, confidence intervals, effect sizes, model fit,
practical significance, and reporting completeness.
"""
from __future__ import annotations

import re
from .models import (
    EffectSizeReport, IssueSeverity, ResultsInterpretation,
    StatisticalIssue, _score_to_grade,
)

# ── Regex patterns ─────────────────────────────────────────────────────────────

_P_VALUE_RE = re.compile(r"\bp\s*[=<>]\s*([\d.]+)", re.IGNORECASE)
_CI_RE = re.compile(r"(?:95%\s*CI|confidence interval)[\s\[]*([.\d]+),?\s*([.\d]+)", re.IGNORECASE)
_COHENS_D_RE = re.compile(r"cohen'?s?\s*d\s*[=:]\s*(-?[\d.]+)", re.IGNORECASE)
_ETA_SQ_RE = re.compile(r"η²?\s*[=:]\s*([\d.]+)|eta.squared\s*[=:]\s*([\d.]+)", re.IGNORECASE)
_OMEGA_SQ_RE = re.compile(r"ω²?\s*[=:]\s*([\d.]+)|omega.squared\s*[=:]\s*([\d.]+)", re.IGNORECASE)
_R_SQUARED_RE = re.compile(r"\bR²?\s*[=:]\s*([\d.]+)|\br-squared\s*[=:]\s*([\d.]+)", re.IGNORECASE)
_PATH_COEF_RE = re.compile(r"(?:path coefficient|β|beta)\s*[=:]\s*(-?[\d.]+)", re.IGNORECASE)
_CRAMERS_V_RE = re.compile(r"cramér'?s?\s*v\s*[=:]\s*([\d.]+)", re.IGNORECASE)
_ODDS_RE = re.compile(r"(?:OR|odds ratio)\s*[=:]\s*([\d.]+)", re.IGNORECASE)
_CFI_RE = re.compile(r"\bCFI\s*[=:]\s*([\d.]+)", re.IGNORECASE)
_RMSEA_RE = re.compile(r"\bRMSEA\s*[=:]\s*([\d.]+)", re.IGNORECASE)
_SRMR_RE = re.compile(r"\bSRMR\s*[=:]\s*([\d.]+)", re.IGNORECASE)
_AVE_RE = re.compile(r"\bAVE\s*[=:]\s*([\d.]+)", re.IGNORECASE)
_CR_RE = re.compile(r"(?:composite reliability|CR)\s*[=:>\s]*([\d.]+)", re.IGNORECASE)
_HTMT_RE = re.compile(r"\bHTMT\s*[=:]\s*([\d.]+)", re.IGNORECASE)
_CRONBACH_RE = re.compile(r"(?:cronbach'?s?\s*alpha|α)\s*[=:]\s*([\d.]+)", re.IGNORECASE)

_DESCRIPTIVE_SIGNALS = [
    "mean", "median", "standard deviation", "sd", "se", "standard error",
    "min", "max", "range", "frequency", "percentage",
]
_PRACTICAL_SIGNALS = [
    "practically significant", "clinical significance", "meaningful difference",
    "effect size", "practical importance", "real-world impact",
]
_APA_SIGNALS = [
    "apa", "reporting standard", "consort", "strobe", "prisma", "equator",
]


def _cohen_d_magnitude(d: float) -> str:
    d = abs(d)
    if d < 0.2: return "negligible"
    if d < 0.5: return "small"
    if d < 0.8: return "medium"
    return "large"


def _eta_sq_magnitude(eta: float) -> str:
    if eta < 0.01: return "negligible"
    if eta < 0.06: return "small"
    if eta < 0.14: return "medium"
    return "large"


def _r_sq_magnitude(r2: float) -> str:
    if r2 < 0.02: return "negligible"
    if r2 < 0.13: return "small"
    if r2 < 0.26: return "medium"
    return "large"


def _cfi_adequate(cfi: float) -> bool:
    return cfi >= 0.90


def _rmsea_adequate(rmsea: float) -> bool:
    return rmsea <= 0.08


def interpret_results(text: str) -> tuple[ResultsInterpretation, list[StatisticalIssue]]:
    lower = text.lower()
    interp = ResultsInterpretation()
    issues: list[StatisticalIssue] = []

    # ── P-values ───────────────────────────────────────────────────────────────
    p_matches = _P_VALUE_RE.findall(text)
    interp.has_p_values = bool(p_matches)
    interp.p_value_count = len(p_matches)

    if not interp.has_p_values:
        issues.append(StatisticalIssue(
            severity=IssueSeverity.MAJOR,
            category="reporting",
            title="P-values not reported",
            description="No p-values were found in the results.",
            recommendation="Report exact p-values (e.g., p=0.023) rather than p<0.05 where possible. Use APA format.",
        ))
    else:
        # Check for exclusive p<0.05 thresholding without exact values
        has_exact = any("=" in p for p in p_matches)
        if not has_exact and interp.p_value_count > 0:
            issues.append(StatisticalIssue(
                severity=IssueSeverity.MINOR,
                category="reporting",
                title="Exact p-values not reported",
                description="Only threshold comparisons (p<0.05) found. Exact p-values preferred.",
                recommendation="Report exact p-values (e.g., p=0.003) per APA 7th edition guidelines.",
            ))

    # ── Confidence intervals ───────────────────────────────────────────────────
    ci_matches = _CI_RE.findall(text)
    interp.has_confidence_intervals = bool(ci_matches) or "confidence interval" in lower
    if not interp.has_confidence_intervals:
        issues.append(StatisticalIssue(
            severity=IssueSeverity.MAJOR,
            category="reporting",
            title="Confidence intervals not reported",
            description="No 95% confidence intervals were found. CIs are required by most journals.",
            recommendation="Report 95% CIs for all main estimates (means, regression coefficients, ORs, etc.).",
        ))

    # ── Effect sizes ──────────────────────────────────────────────────────────
    effect_sizes: list[EffectSizeReport] = []

    d_matches = _COHENS_D_RE.findall(text)
    for val in d_matches[:3]:
        try:
            d = float(val)
            effect_sizes.append(EffectSizeReport(
                measure="Cohen's d", value=str(d),
                magnitude=_cohen_d_magnitude(d),
                context=f"Standardised mean difference of {d:.2f}.",
            ))
        except ValueError:
            pass

    eta_m = _ETA_SQ_RE.search(text)
    if eta_m:
        val = eta_m.group(1) or eta_m.group(2)
        try:
            eta = float(val)
            effect_sizes.append(EffectSizeReport(
                measure="η²", value=str(eta),
                magnitude=_eta_sq_magnitude(eta),
                context=f"Eta-squared of {eta:.3f}.",
            ))
        except ValueError:
            pass

    r2_m = _R_SQUARED_RE.search(text)
    if r2_m:
        val = r2_m.group(1) or r2_m.group(2)
        try:
            r2 = float(val)
            effect_sizes.append(EffectSizeReport(
                measure="R²", value=str(r2),
                magnitude=_r_sq_magnitude(r2),
                context=f"Model explains {r2*100:.1f}% of variance.",
            ))
        except ValueError:
            pass

    cramers_m = _CRAMERS_V_RE.search(text)
    if cramers_m:
        try:
            v = float(cramers_m.group(1))
            effect_sizes.append(EffectSizeReport(
                measure="Cramér's V", value=str(v),
                magnitude="small" if v < 0.1 else "medium" if v < 0.3 else "large",
                context=f"Cramér's V = {v:.3f}.",
            ))
        except ValueError:
            pass

    odds_matches = _ODDS_RE.findall(text)
    for val in odds_matches[:2]:
        try:
            or_val = float(val)
            effect_sizes.append(EffectSizeReport(
                measure="Odds Ratio", value=str(or_val),
                magnitude="negligible" if abs(or_val - 1) < 0.2 else
                           "small" if abs(or_val - 1) < 0.5 else "large",
                context=f"OR = {or_val:.2f}.",
            ))
        except ValueError:
            pass

    interp.has_effect_sizes = bool(effect_sizes)
    interp.effect_sizes = effect_sizes

    if not interp.has_effect_sizes:
        issues.append(StatisticalIssue(
            severity=IssueSeverity.MAJOR,
            category="reporting",
            title="Effect sizes not reported",
            description=(
                "No effect size measures were found. "
                "Effect sizes are required by APA and most high-impact journals."
            ),
            recommendation=(
                "Report Cohen's d (t-tests), η² (ANOVA), R² (regression), "
                "Cramér's V (chi-square), or odds ratios (logistic regression)."
            ),
        ))

    # ── Descriptive statistics ─────────────────────────────────────────────────
    interp.has_descriptive_stats = any(s in lower for s in _DESCRIPTIVE_SIGNALS)
    if not interp.has_descriptive_stats:
        issues.append(StatisticalIssue(
            severity=IssueSeverity.MODERATE,
            category="reporting",
            title="Descriptive statistics not reported",
            description="No means, SDs, or frequencies were found.",
            recommendation="Report descriptive statistics (M, SD for continuous; n, % for categorical) for all variables.",
        ))

    # ── Model fit (SEM/PLS) ────────────────────────────────────────────────────
    fit_indices: dict[str, str] = {}

    cfi_m = _CFI_RE.search(text)
    if cfi_m:
        cfi = float(cfi_m.group(1))
        fit_indices["CFI"] = str(cfi)
        if not _cfi_adequate(cfi):
            issues.append(StatisticalIssue(
                severity=IssueSeverity.MAJOR,
                category="model_fit",
                title=f"Poor model fit: CFI={cfi:.3f}",
                description=f"CFI={cfi:.3f} is below the acceptable threshold of 0.90.",
                recommendation="Revise the model using modification indices. Report all fit indices.",
            ))

    rmsea_m = _RMSEA_RE.search(text)
    if rmsea_m:
        rmsea = float(rmsea_m.group(1))
        fit_indices["RMSEA"] = str(rmsea)
        if not _rmsea_adequate(rmsea):
            issues.append(StatisticalIssue(
                severity=IssueSeverity.MAJOR,
                category="model_fit",
                title=f"Poor model fit: RMSEA={rmsea:.3f}",
                description=f"RMSEA={rmsea:.3f} exceeds the acceptable threshold of 0.08.",
                recommendation="Acceptable RMSEA is <0.08; excellent is <0.05. Revise model specification.",
            ))

    srmr_m = _SRMR_RE.search(text)
    if srmr_m:
        fit_indices["SRMR"] = str(float(srmr_m.group(1)))

    interp.model_fit_indices = fit_indices

    # ── Practical significance ─────────────────────────────────────────────────
    has_practical = any(s in lower for s in _PRACTICAL_SIGNALS)
    interp.statistical_significance_summary = (
        f"{interp.p_value_count} p-value(s) detected."
        if interp.has_p_values else "No p-values reported."
    )
    interp.practical_significance_note = (
        "Practical significance discussed." if has_practical else
        "Practical significance not addressed — statistical significance alone is insufficient."
    )
    if not has_practical and interp.has_p_values:
        issues.append(StatisticalIssue(
            severity=IssueSeverity.MINOR,
            category="interpretation",
            title="Practical significance not discussed",
            description="Statistical significance is reported but practical/clinical significance is not addressed.",
            recommendation=(
                "Discuss the practical meaning of statistically significant results. "
                "A statistically significant effect may be trivially small in practice."
            ),
        ))

    # ── Score ──────────────────────────────────────────────────────────────────
    checks = [
        interp.has_p_values,
        interp.has_confidence_intervals,
        interp.has_effect_sizes,
        interp.has_descriptive_stats,
        bool(fit_indices),
        has_practical,
    ]
    score = (sum(1 for c in checks if c) / len(checks)) * 100
    score = max(0.0, score - sum(1 for i in issues if i.severity == IssueSeverity.MAJOR) * 10)
    interp.score = max(0.0, min(100.0, score))
    interp.grade = _score_to_grade(interp.score)

    return interp, issues
