"""Statistical Intelligence 2.0 — Data quality reviewer (Phase X).

Inspects text for quality indicators (missing values, outliers, normality,
homoscedasticity, multicollinearity, independence, linearity).
For structured data (ParsedData.has_structured_data=True) computes directly.
"""
from __future__ import annotations

import re
from .models import (
    DataQualityMetrics, IssueSeverity, ParsedData,
    StatisticalIssue, _score_to_grade,
)

# ── Text-based detectors ──────────────────────────────────────────────────────

_VIF_RE = re.compile(r"\bVIF\b\s*[=:]\s*(\d+\.?\d*)", re.IGNORECASE)
_MISSING_RE = re.compile(
    r"(?:missing\s+(?:data|values?|cases?)|listwise|pairwise)\s*[=:\s]*(\d+\.?\d*)\s*%?",
    re.IGNORECASE,
)
_NORMALITY_TESTS = [
    "shapiro-wilk", "shapiro wilk", "kolmogorov-smirnov", "anderson-darling",
    "jarque-bera", "d'agostino", "skewness", "kurtosis", "qq plot", "q-q plot",
]
_HOMOSCEDASTICITY_TESTS = [
    "levene", "bartlett", "homogeneity of variance", "homoscedasticity",
    "heteroscedasticity", "breusch-pagan", "white test", "equal variances",
]
_MULTICOLLINEARITY_SIGNALS = [
    "vif", "variance inflation", "multicollinearity", "collinearity",
    "tolerance", "condition index", "correlation matrix", "inter-item",
]
_INDEPENDENCE_SIGNALS = [
    "durbin-watson", "autocorrelation", "independence", "residual plots",
    "independence of errors", "independent observations",
]
_LINEARITY_SIGNALS = [
    "linearity", "linear relationship", "scatter plot", "residual vs fitted",
    "harvey-collier", "rainbow test",
]
_OUTLIER_SIGNALS = [
    "outlier", "extreme value", "cook's distance", "mahalanobis", "leverage",
    "influential case", "z-score", "3 standard deviation",
]
_IMPUTATION_SIGNALS = [
    "multiple imputation", "single imputation", "mice", "mean imputation",
    "listwise deletion", "pairwise deletion", "em algorithm",
]


def review_data_quality(text: str, parsed: ParsedData) -> tuple[DataQualityMetrics, list[StatisticalIssue]]:
    lower = text.lower()
    issues: list[StatisticalIssue] = []
    metrics = DataQualityMetrics()

    # ── Missing values ────────────────────────────────────────────────────────
    if parsed.has_structured_data:
        metrics.overall_missing_rate = parsed.overall_missing_rate
    else:
        miss_m = _MISSING_RE.search(text)
        if miss_m:
            try:
                metrics.overall_missing_rate = float(miss_m.group(1)) / 100
            except ValueError:
                pass

    if metrics.overall_missing_rate > 0.05:
        handled = any(s in lower for s in _IMPUTATION_SIGNALS)
        sev = IssueSeverity.MAJOR if metrics.overall_missing_rate > 0.20 else IssueSeverity.MODERATE
        issues.append(StatisticalIssue(
            severity=sev,
            category="data_quality",
            title=f"Missing data ({metrics.overall_missing_rate*100:.0f}%)",
            description=(
                f"Approximately {metrics.overall_missing_rate*100:.0f}% of values are missing. "
                + ("Imputation strategy detected." if handled else "No imputation strategy reported.")
            ),
            recommendation=(
                "Apply multiple imputation (MICE in R/Python) or maximum likelihood estimation. "
                "Report a missing data analysis comparing complete and incomplete cases."
                if not handled else
                "Document the imputation method and report sensitivity analyses."
            ),
        ))
    elif "missing" in lower and metrics.overall_missing_rate == 0.0:
        metrics.overall_missing_rate = 0.0  # mentioned but handled

    # ── Outliers ──────────────────────────────────────────────────────────────
    metrics.has_outliers_mentioned = any(s in lower for s in _OUTLIER_SIGNALS)
    if not metrics.has_outliers_mentioned:
        issues.append(StatisticalIssue(
            severity=IssueSeverity.MINOR,
            category="data_quality",
            title="Outlier analysis not reported",
            description="No outlier detection or handling strategy was identified.",
            recommendation=(
                "Report outlier detection using Cook's distance, Mahalanobis distance, "
                "or z-scores (|z| > 3). Describe how outliers were handled."
            ),
        ))

    # ── Normality ─────────────────────────────────────────────────────────────
    metrics.normality_tested = any(s in lower for s in _NORMALITY_TESTS)
    if metrics.normality_tested:
        # Check if violation reported
        if any(word in lower for word in
               ["non-normal", "violated", "p < .05", "p < 0.05", "reject null",
                "skewed", "kurtosis"]):
            metrics.normality_met = False
            issues.append(StatisticalIssue(
                severity=IssueSeverity.MAJOR,
                category="data_quality",
                title="Normality violation detected",
                description=(
                    "Normality tests indicate a significant violation. "
                    "Parametric tests may produce unreliable results."
                ),
                recommendation=(
                    "Consider non-parametric alternatives (Mann-Whitney, Kruskal-Wallis). "
                    "For larger samples (n>30), invoke CLT but report the violation. "
                    "Bootstrap confidence intervals are a robust alternative."
                ),
            ))
        else:
            metrics.normality_met = True
    else:
        issues.append(StatisticalIssue(
            severity=IssueSeverity.MODERATE,
            category="data_quality",
            title="Normality not formally tested",
            description=(
                "No normality test (Shapiro-Wilk, K-S) was reported. "
                "Parametric test assumptions cannot be verified."
            ),
            recommendation=(
                "Report Shapiro-Wilk (n<50) or Kolmogorov-Smirnov (n>50) results. "
                "Supplement with Q-Q plots and skewness/kurtosis statistics."
            ),
        ))

    # ── Homoscedasticity ──────────────────────────────────────────────────────
    metrics.homoscedasticity_tested = any(s in lower for s in _HOMOSCEDASTICITY_TESTS)
    if not metrics.homoscedasticity_tested:
        issues.append(StatisticalIssue(
            severity=IssueSeverity.MODERATE,
            category="data_quality",
            title="Homoscedasticity/equal variance not tested",
            description=(
                "No test for homogeneity of variance (Levene's, Bartlett's) was reported."
            ),
            recommendation=(
                "Report Levene's test for ANOVA/t-test, or Breusch-Pagan for regression. "
                "If violated, use Welch's correction or robust standard errors."
            ),
        ))

    # ── Multicollinearity ─────────────────────────────────────────────────────
    metrics.multicollinearity_tested = any(s in lower for s in _MULTICOLLINEARITY_SIGNALS)
    vif_matches = _VIF_RE.findall(text)
    if vif_matches:
        metrics.max_vif = max(float(v) for v in vif_matches)
        if metrics.max_vif >= 10:
            issues.append(StatisticalIssue(
                severity=IssueSeverity.CRITICAL,
                category="data_quality",
                title=f"Severe multicollinearity (VIF={metrics.max_vif:.1f})",
                description=(
                    f"VIF={metrics.max_vif:.1f} exceeds the critical threshold of 10, "
                    "indicating severe multicollinearity. Regression coefficients are unreliable."
                ),
                recommendation=(
                    "Remove highly correlated predictors, apply ridge regression, "
                    "or use PCA to reduce dimensionality before regression."
                ),
            ))
        elif metrics.max_vif >= 5:
            issues.append(StatisticalIssue(
                severity=IssueSeverity.MAJOR,
                category="data_quality",
                title=f"Moderate multicollinearity (VIF={metrics.max_vif:.1f})",
                description=f"VIF={metrics.max_vif:.1f} indicates moderate multicollinearity.",
                recommendation=(
                    "Report VIF values for all predictors. "
                    "Consider removing correlated predictors or using regularisation."
                ),
            ))
    elif not metrics.multicollinearity_tested:
        issues.append(StatisticalIssue(
            severity=IssueSeverity.MINOR,
            category="data_quality",
            title="Multicollinearity not assessed",
            description="No VIF or tolerance values were reported for regression predictors.",
            recommendation=(
                "Report VIF values for all predictors in regression models. "
                "Flag any VIF > 5 as a potential concern."
            ),
        ))

    # ── Independence ─────────────────────────────────────────────────────────
    metrics.independence_met = any(s in lower for s in _INDEPENDENCE_SIGNALS)

    # ── Linearity ─────────────────────────────────────────────────────────────
    metrics.linearity_mentioned = any(s in lower for s in _LINEARITY_SIGNALS)

    # ── Score ─────────────────────────────────────────────────────────────────
    checks = [
        metrics.normality_tested,
        metrics.homoscedasticity_tested,
        metrics.multicollinearity_tested,
        metrics.has_outliers_mentioned,
        metrics.independence_met,
        metrics.linearity_mentioned,
        metrics.overall_missing_rate < 0.10,
    ]
    score = (sum(1 for c in checks if c) / len(checks)) * 100
    # Penalise for critical issues
    critical_count = sum(1 for i in issues if i.severity == IssueSeverity.CRITICAL)
    score = max(0.0, score - critical_count * 15)

    metrics.score = score
    metrics.grade = _score_to_grade(score)
    metrics.issues = [i.title for i in issues]

    return metrics, issues
