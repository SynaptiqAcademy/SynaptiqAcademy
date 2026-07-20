"""Statistical Intelligence 2.0 — Assumption checker (Phase X).

Verifies assumptions for each detected statistical method.
Operates on text signals — no heavy NLP dependencies.
"""
from __future__ import annotations

import re
from .models import (
    AnalysisMethod, AssumptionCheck, AssumptionStatus,
    IssueSeverity, ResearchDesign, StatisticalIssue,
)

# ── Assumption definitions per method ─────────────────────────────────────────
# Each entry: (assumption_name, detection_signals, violation_signals, recommendation)

_ASSUMPTIONS: dict[AnalysisMethod, list[tuple[str, list[str], list[str], str]]] = {
    AnalysisMethod.T_TEST: [
        ("Normality", ["shapiro", "normal distribution", "q-q plot", "normality"],
         ["non-normal", "violation", "skew"],
         "Use Welch's t-test or Mann-Whitney U for non-normal data."),
        ("Independence of observations", ["independent", "independence"],
         ["correlated", "repeated", "matched"],
         "If observations are paired, use a paired t-test."),
        ("Equal variances (homoscedasticity)", ["levene", "equal variances", "homoscedasticity"],
         ["unequal variances", "heteroscedastic", "levene significant"],
         "Use Welch's t-test (default in most software) when variances are unequal."),
    ],
    AnalysisMethod.ANOVA: [
        ("Normality", ["shapiro", "normal", "normality test"],
         ["non-normal", "violated normality"],
         "Use Kruskal-Wallis for non-normal outcomes."),
        ("Homogeneity of variances", ["levene", "bartlett", "equal variances", "homogeneity"],
         ["unequal variances", "levene significant", "violated"],
         "Apply Welch ANOVA or Kruskal-Wallis when variances are unequal."),
        ("Independence", ["independent observations", "independence"],
         ["clustered", "nested", "repeated"],
         "Use linear mixed models for non-independent data."),
    ],
    AnalysisMethod.REPEATED_ANOVA: [
        ("Sphericity", ["mauchly", "sphericity", "epsilon"],
         ["violated sphericity", "sphericity violated", "p < .05"],
         "Apply Greenhouse-Geisser or Huynh-Feldt correction."),
        ("Normality of residuals", ["normal residuals", "normality"],
         ["non-normal"],
         "Consider non-parametric Friedman test."),
    ],
    AnalysisMethod.MULTIPLE_REGRESSION: [
        ("Linearity", ["linear relationship", "linearity", "partial plots", "scatter"],
         ["non-linear", "curvilinear", "polynomial"],
         "Add polynomial terms or use non-linear regression."),
        ("Independence of residuals", ["durbin-watson", "independence", "autocorrelation"],
         ["autocorrelation", "durbin-watson < 1.5", "durbin-watson > 2.5"],
         "Address autocorrelation with time series methods or GLS."),
        ("Homoscedasticity of residuals", ["breusch-pagan", "white test", "homoscedasticity",
                                            "residual plot"],
         ["heteroscedastic", "heteroscedasticity", "fan pattern"],
         "Use heteroscedasticity-robust standard errors (HC3)."),
        ("Normality of residuals", ["normal residuals", "normality", "q-q plot"],
         ["non-normal residuals"],
         "Check for influential outliers; bootstrap CIs are robust to non-normality."),
        ("No multicollinearity", ["vif", "variance inflation", "tolerance", "multicollinearity"],
         ["vif > 10", "high vif", "multicollinearity"],
         "Remove highly correlated predictors or use ridge regression."),
    ],
    AnalysisMethod.LOGISTIC_REGRESSION: [
        ("Binary outcome", ["binary", "dichotomous", "0/1"],
         [],
         "Ensure the dependent variable is truly binary."),
        ("Independence", ["independent", "independence"],
         ["clustered", "repeated"],
         "Use multilevel logistic regression for clustered data."),
        ("No multicollinearity", ["vif", "multicollinearity", "correlation matrix"],
         ["high vif", "multicollinearity"],
         "Report VIF and remove collinear predictors."),
        ("Adequate sample size", ["events per variable", "sample size"],
         ["small sample", "sparse data", "complete separation"],
         "Rule of thumb: ≥10 events per predictor variable."),
    ],
    AnalysisMethod.SEM: [
        ("Multivariate normality", ["multivariate normality", "mardia", "normal"],
         ["non-normal", "violated normality"],
         "Use MLR or WLSMV estimator for non-normal data."),
        ("Model fit", ["cfi", "rmsea", "srmr", "tli", "model fit"],
         ["poor fit", "rmsea > .08", "cfi < .95"],
         "Revise model specification based on modification indices."),
        ("Adequate sample size", ["sample size", "n ="],
         ["small sample"],
         "SEM generally requires n≥200; use PLS-SEM for smaller samples."),
    ],
    AnalysisMethod.PLS_SEM: [
        ("Measurement model validity", ["ave", "composite reliability", "outer loading", "htmt"],
         ["ave < .5", "cr < .7", "htmt > .85"],
         "Ensure AVE≥0.5, CR≥0.7, HTMT<0.85 for all constructs."),
        ("Reflective vs formative distinction", ["reflective", "formative"],
         [],
         "Explicitly justify whether constructs are reflective or formative."),
    ],
    AnalysisMethod.FACTOR_ANALYSIS: [
        ("Sampling adequacy (KMO)", ["kmo", "kaiser-meyer-olkin", "sampling adequacy"],
         ["kmo < .6", "unacceptable", "poor"],
         "KMO should exceed 0.6; below 0.5 is unacceptable."),
        ("Bartlett's test of sphericity", ["bartlett", "sphericity", "correlation matrix"],
         ["not significant", "p > .05"],
         "Bartlett's test must be significant (p<.05) to justify factor analysis."),
        ("Sample size", ["sample size", "n ="],
         ["small sample"],
         "Minimum 5–10 participants per variable; absolute minimum n=100."),
    ],
    AnalysisMethod.PEARSON_CORRELATION: [
        ("Normality", ["normal", "normality", "shapiro"],
         ["non-normal"],
         "Use Spearman correlation for non-normal or ordinal data."),
        ("Linearity", ["linear", "scatter plot", "linearity"],
         ["non-linear", "curvilinear"],
         "Pearson r only measures linear association; use Spearman for monotonic."),
        ("No outliers", ["outlier", "influential", "mahalanobis"],
         ["outliers present", "influential cases"],
         "Remove or Winsorize outliers; robust correlation alternatives exist."),
    ],
    AnalysisMethod.CHI_SQUARE: [
        ("Expected cell frequencies ≥5", ["expected frequency", "expected count", "cell count"],
         ["expected < 5", "sparse", "small expected"],
         "Use Fisher's Exact test when expected frequencies <5 in any cell."),
        ("Independence", ["independent", "independence"],
         [],
         "Chi-square tests independence; McNemar is appropriate for paired data."),
    ],
    AnalysisMethod.META_ANALYSIS: [
        ("Publication bias", ["funnel plot", "egger", "trim and fill", "publication bias"],
         ["publication bias", "asymmetric funnel"],
         "Report Egger's test and trim-and-fill analysis."),
        ("Heterogeneity", ["i²", "q-statistic", "heterogeneity", "tau²"],
         ["high heterogeneity", "i² > 75"],
         "Explore heterogeneity with subgroup analyses and meta-regression."),
    ],
}

# Methods with no established mandatory assumptions in text context
_NO_ASSUMPTION_METHODS = {
    AnalysisMethod.CLUSTER_ANALYSIS,
    AnalysisMethod.MACHINE_LEARNING,
    AnalysisMethod.BAYESIAN,
    AnalysisMethod.TIME_SERIES,
    AnalysisMethod.SURVIVAL_ANALYSIS,
}


def check_assumptions(
    text: str, design: ResearchDesign
) -> tuple[list[AssumptionCheck], list[StatisticalIssue]]:
    lower = text.lower()
    checks: list[AssumptionCheck] = []
    issues: list[StatisticalIssue] = []

    methods = [m for m in design.detected_methods if m != AnalysisMethod.UNKNOWN]
    seen_assumptions: set[str] = set()

    for method in methods[:3]:  # Limit to 3 methods
        if method in _NO_ASSUMPTION_METHODS:
            continue
        assumptions = _ASSUMPTIONS.get(method, [])
        for (name, detect_signals, violation_signals, recommendation) in assumptions:
            key = f"{method.value}:{name}"
            if key in seen_assumptions:
                continue
            seen_assumptions.add(key)

            detected = any(s in lower for s in detect_signals)
            violated = any(s in lower for s in violation_signals) if detected else False

            if violated:
                status = AssumptionStatus.VIOLATED
                sev = IssueSeverity.MAJOR
                evidence = f"Violation signals detected: {', '.join(s for s in violation_signals if s in lower)}"
            elif detected:
                status = AssumptionStatus.MET
                sev = IssueSeverity.MINOR
                evidence = f"Assumption tested and reported."
            else:
                status = AssumptionStatus.NOT_TESTED
                sev = IssueSeverity.MODERATE
                evidence = "No testing signals found in the text."

            check = AssumptionCheck(
                name=name,
                method=method.value,
                status=status,
                evidence=evidence,
                consequence=(
                    "Violation may invalidate statistical conclusions."
                    if violated else
                    "Results cannot be verified without this test."
                    if status == AssumptionStatus.NOT_TESTED else
                    "Assumption verified."
                ),
                recommendation=recommendation if status != AssumptionStatus.MET else "",
                severity=sev,
            )
            checks.append(check)

            if status in (AssumptionStatus.VIOLATED, AssumptionStatus.NOT_TESTED):
                issues.append(StatisticalIssue(
                    severity=sev,
                    category="assumptions",
                    title=f"{name} — {status.value.replace('_', ' ')} ({method.value})",
                    description=evidence,
                    recommendation=recommendation,
                    affected_element=method.value,
                ))

    return checks, issues
