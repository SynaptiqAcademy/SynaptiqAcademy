"""Statistical Intelligence 2.0 — Statistical method reviewer (Phase X).

Evaluates appropriateness of detected statistical methods given study type,
variable structure, measurement level, and research design characteristics.
"""
from __future__ import annotations

import re
from .models import (
    AnalysisMethod, IssueSeverity, MethodEvaluation,
    ResearchDesign, StatisticalIssue, StudyType,
)

# ── Reporting requirements per method ─────────────────────────────────────────

_REQUIRED_REPORTING: dict[AnalysisMethod, list[str]] = {
    AnalysisMethod.T_TEST:              ["t-statistic", "degrees of freedom", "p-value", "effect size (Cohen's d)", "means", "SD"],
    AnalysisMethod.ANOVA:               ["F-statistic", "degrees of freedom", "p-value", "effect size (η² or ω²)", "post-hoc tests"],
    AnalysisMethod.REPEATED_ANOVA:      ["F-statistic", "p-value", "sphericity test (Mauchly's)", "effect size", "within-subjects factor"],
    AnalysisMethod.ANCOVA:              ["F-statistic", "p-value", "covariate effects", "adjusted means", "effect size"],
    AnalysisMethod.MANOVA:              ["Wilks' lambda", "F-statistic", "multivariate effect size", "follow-up ANOVAs"],
    AnalysisMethod.CHI_SQUARE:          ["χ² value", "degrees of freedom", "p-value", "expected frequencies", "Cramér's V"],
    AnalysisMethod.PEARSON_CORRELATION: ["r value", "p-value", "confidence interval", "sample size"],
    AnalysisMethod.MULTIPLE_REGRESSION: ["R²", "adjusted R²", "F-statistic", "β coefficients", "t-statistics", "p-values", "VIF"],
    AnalysisMethod.LOGISTIC_REGRESSION: ["odds ratios", "95% CI", "p-values", "Nagelkerke R²", "Hosmer-Lemeshow test", "ROC AUC"],
    AnalysisMethod.SEM:                 ["CFI", "RMSEA", "SRMR", "TLI", "factor loadings", "path coefficients"],
    AnalysisMethod.PLS_SEM:             ["R²", "path coefficients", "outer loadings", "AVE", "composite reliability", "HTMT"],
    AnalysisMethod.CFA:                 ["factor loadings", "AVE", "composite reliability", "χ²/df", "CFI", "RMSEA"],
    AnalysisMethod.FACTOR_ANALYSIS:     ["factor loadings", "eigenvalues", "explained variance", "KMO", "Bartlett's test"],
    AnalysisMethod.SURVIVAL_ANALYSIS:   ["hazard ratios", "95% CI", "log-rank test", "Kaplan-Meier curve", "p-values"],
    AnalysisMethod.META_ANALYSIS:       ["pooled effect size", "heterogeneity I²", "Q-statistic", "forest plot", "funnel plot", "publication bias"],
    AnalysisMethod.TIME_SERIES:         ["stationarity test", "ACF/PACF", "model diagnostics", "residual analysis"],
    AnalysisMethod.MIXED_MODELS:        ["fixed effects", "random effects", "ICC", "AIC/BIC", "variance components"],
}

# ── Method-design compatibility ───────────────────────────────────────────────
# Maps study type to methods that are generally appropriate

_APPROPRIATE_FOR: dict[StudyType, list[AnalysisMethod]] = {
    StudyType.RCT: [
        AnalysisMethod.T_TEST, AnalysisMethod.PAIRED_T_TEST, AnalysisMethod.ANOVA,
        AnalysisMethod.ANCOVA, AnalysisMethod.MIXED_MODELS, AnalysisMethod.MANN_WHITNEY,
    ],
    StudyType.SURVEY: [
        AnalysisMethod.MULTIPLE_REGRESSION, AnalysisMethod.LOGISTIC_REGRESSION,
        AnalysisMethod.FACTOR_ANALYSIS, AnalysisMethod.CFA, AnalysisMethod.SEM,
        AnalysisMethod.PLS_SEM, AnalysisMethod.PEARSON_CORRELATION,
        AnalysisMethod.SPEARMAN_CORRELATION, AnalysisMethod.CHI_SQUARE,
    ],
    StudyType.CROSS_SECTIONAL: [
        AnalysisMethod.MULTIPLE_REGRESSION, AnalysisMethod.LOGISTIC_REGRESSION,
        AnalysisMethod.CHI_SQUARE, AnalysisMethod.PEARSON_CORRELATION,
        AnalysisMethod.SEM, AnalysisMethod.PLS_SEM,
    ],
    StudyType.LONGITUDINAL: [
        AnalysisMethod.MIXED_MODELS, AnalysisMethod.REPEATED_ANOVA,
        AnalysisMethod.TIME_SERIES, AnalysisMethod.SURVIVAL_ANALYSIS,
    ],
    StudyType.META_ANALYSIS: [AnalysisMethod.META_ANALYSIS],
    StudyType.CASE_CONTROL: [
        AnalysisMethod.LOGISTIC_REGRESSION, AnalysisMethod.CHI_SQUARE,
        AnalysisMethod.MANN_WHITNEY,
    ],
    StudyType.COHORT: [
        AnalysisMethod.SURVIVAL_ANALYSIS, AnalysisMethod.LOGISTIC_REGRESSION,
        AnalysisMethod.MIXED_MODELS, AnalysisMethod.TIME_SERIES,
    ],
}

# ── Method alternatives ───────────────────────────────────────────────────────

_ALTERNATIVES: dict[AnalysisMethod, list[str]] = {
    AnalysisMethod.T_TEST:              ["Mann-Whitney U (non-parametric)", "ANCOVA (with covariates)"],
    AnalysisMethod.ANOVA:               ["Kruskal-Wallis (non-parametric)", "ANCOVA (with covariates)", "Linear Mixed Models"],
    AnalysisMethod.MULTIPLE_REGRESSION: ["Ridge regression (multicollinearity)", "Robust regression", "Quantile regression"],
    AnalysisMethod.LOGISTIC_REGRESSION: ["Probit regression", "Linear Probability Model", "Random Forest (predictive)"],
    AnalysisMethod.FACTOR_ANALYSIS:     ["PCA (data reduction)", "CFA (theory-driven)", "IRT (item-level analysis)"],
    AnalysisMethod.SEM:                 ["PLS-SEM (small samples/complex models)", "CB-SEM (large samples)"],
    AnalysisMethod.PLS_SEM:             ["CB-SEM/LISREL (if n>200)", "Bayesian SEM (uncertainty quantification)"],
}

# ── Reporting patterns (present in text) ─────────────────────────────────────

_REPORTING_SIGNALS: dict[str, list[str]] = {
    "p-value":          [r"p\s*[=<>]", "significance level", "significant"],
    "effect_size":      ["cohen's d", "η²", "eta-squared", "omega squared", "r²",
                         "effect size", "cramér's v", "r =", "d ="],
    "confidence_interval": ["95% ci", "confidence interval", "ci [", "[lower, upper]"],
    "R²":               ["r-squared", "r² =", "r2 =", "coefficient of determination"],
    "fit_indices":      ["cfi", "rmsea", "srmr", "tli", "nfi", "chi-square/df"],
}


def _detect_reported_elements(text: str, required: list[str]) -> list[str]:
    lower = text.lower()
    missing: list[str] = []
    for req in required:
        # Simple heuristic: is the key term present?
        key_terms = req.lower().replace("(", "").replace(")", "").split()
        if not any(t in lower for t in key_terms):
            missing.append(req)
    return missing


def review_methods(
    text: str, design: ResearchDesign
) -> tuple[list[MethodEvaluation], list[StatisticalIssue]]:
    lower = text.lower()
    evaluations: list[MethodEvaluation] = []
    issues: list[StatisticalIssue] = []

    methods = [m for m in design.detected_methods if m != AnalysisMethod.UNKNOWN]
    if not methods:
        issues.append(StatisticalIssue(
            severity=IssueSeverity.MAJOR,
            category="methods",
            title="Statistical method not identified",
            description="No recognizable statistical method was detected in the text.",
            recommendation="Clearly state the statistical method(s) used in the methodology section.",
        ))
        return evaluations, issues

    for method in methods[:5]:  # Evaluate up to 5 methods
        required = _REQUIRED_REPORTING.get(method, ["p-value", "effect size"])
        missing_elements = _detect_reported_elements(text, required)

        # Appropriateness check
        appropriate_methods = _APPROPRIATE_FOR.get(design.study_type, [])
        is_appropriate = (
            not appropriate_methods or  # Unknown study type — can't evaluate
            method in appropriate_methods or
            design.study_type == StudyType.UNKNOWN
        )

        # Score
        score = 70.0
        if is_appropriate:
            score += 15.0
        else:
            score -= 20.0
            issues.append(StatisticalIssue(
                severity=IssueSeverity.MAJOR,
                category="methods",
                title=f"Potential method–design mismatch: {method.value}",
                description=(
                    f"{method.value} may not be the most appropriate method for a "
                    f"{design.study_type.value} design. "
                    f"Consider: {', '.join(_APPROPRIATE_FOR.get(design.study_type, ['unknown'])[:3])}."
                ),
                recommendation=(
                    f"Justify the choice of {method.value} for this research design, "
                    f"or consider alternative methods."
                ),
            ))

        # Missing reporting elements
        score -= min(30.0, len(missing_elements) * 5)
        for elem in missing_elements:
            issues.append(StatisticalIssue(
                severity=IssueSeverity.MODERATE,
                category="reporting",
                title=f"Missing reporting element: {elem}",
                description=f"{elem} was not found in the results for {method.value}.",
                recommendation=f"Report {elem} to meet APA 7th edition reporting standards.",
                affected_element=method.value,
            ))

        rationale = (
            f"{method.value} appears appropriate for the {design.study_type.value} design."
            if is_appropriate else
            f"{method.value} may not optimally suit a {design.study_type.value} design."
        )

        eval_ = MethodEvaluation(
            method=method,
            is_appropriate=is_appropriate,
            appropriateness_score=max(0.0, min(100.0, score)),
            rationale=rationale,
            alternatives=_ALTERNATIVES.get(method, []),
            missing_reporting=missing_elements,
        )
        evaluations.append(eval_)

    return evaluations, issues
