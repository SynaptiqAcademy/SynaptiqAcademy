"""Statistical quality reviewer — Phase IX.

Inspects manuscript text for statistical reporting completeness:
p-values, confidence intervals, effect sizes, sample sizes,
power analysis, descriptive stats, assumption checks, model selection.
"""
from __future__ import annotations

import re

from .models import (
    StatisticalMetrics, QualityDimension, ReviewIssue,
    IssueSeverity, _score_to_grade,
)

# ── Statistical patterns ──────────────────────────────────────────────────────

_P_VALUE = re.compile(
    r"\bp\s*[<>=≤≥]\s*0?\.\d+|\bp\s*[<>=]\s*\.?\d+|p-value",
    re.IGNORECASE,
)
_CI = re.compile(
    r"\d+\s*%\s*(?:CI|confidence\s+interval)|"
    r"(?:95|90|99)\s*%\s*CI|"
    r"CI\s*[\[\(]\s*[-\d\.]+\s*[,;]\s*[-\d\.]+\s*[\]\)]",
    re.IGNORECASE,
)
_EFFECT_SIZE = re.compile(
    r"Cohen(?:'s)?\s+[dDgG]|"
    r"[Hh]edge(?:'s)?\s+[gG]|"
    r"\bEta\s*(?:squared|²)|\bωeta\s*squared|\bOmega\s*squared|\bω²|"
    r"\b(?:partial\s+)?η²|\bη[²p]|"
    r"Cramer(?:'s)?\s+[Vv]|"
    r"odds\s+ratio|\bOR\s*=|\bHR\s*=|"
    r"relative\s+risk|\bRR\s*=|"
    r"standardized\s+(?:mean\s+)?difference|"
    r"\br\s*=\s*[-\d\.]+",
    re.IGNORECASE,
)
_SAMPLE_SIZE = re.compile(r"\b[Nn]\s*=\s*\d+")
_POWER = re.compile(
    r"(?:statistical\s+)?power\s+(?:analysis|calculation)|"
    r"power\s*=\s*\d|"
    r"a\s+priori\s+power|"
    r"sample\s+size\s+calculation",
    re.IGNORECASE,
)
_DESCRIPTIVE = re.compile(
    r"\b(?:mean|median|mode|average|SD|standard\s+deviation|"
    r"IQR|interquartile|variance|frequency|percentage|proportion|"
    r"minimum|maximum|range)\b",
    re.IGNORECASE,
)
_ASSUMPTION = re.compile(
    r"normal(?:ity)?(?:\s+test)?|"
    r"homogeneity\s+of\s+variance|"
    r"Levene|Shapiro.?Wilk|Kolmogorov.?Smirnov|"
    r"multicollinearity|VIF|tolerance|"
    r"autocorrelation|Durbin.?Watson|"
    r"sphericity|Mauchly|"
    r"assumption(?:s)?\s+(?:test|check|violation|met|verified)",
    re.IGNORECASE,
)
_STAT_TESTS = re.compile(
    r"\bt-test|ANOVA|MANOVA|ANCOVA|"
    r"chi.?square|\bχ²|\bchi²|"
    r"regression|logistic\s+regression|linear\s+regression|"
    r"Mann.?Whitney|Wilcoxon|Kruskal.?Wallis|"
    r"Pearson\s+correlation|Spearman|Kendall|"
    r"structural\s+equation|SEM|path\s+analysis|"
    r"factor\s+analysis|PCA|cluster\s+analysis|"
    r"mixed\s+model|multilevel|hierarchical\s+linear|"
    r"survival\s+analysis|Cox\s+regression|"
    r"Bayesian|MCMC|bootstrap",
    re.IGNORECASE,
)
_APA_NUMBER = re.compile(r"\b\d+\.\d{2,}\b")


def review_statistical_quality(
    text: str,
) -> tuple[StatisticalMetrics, QualityDimension, list[ReviewIssue]]:
    issues: list[ReviewIssue] = []
    strengths: list[str] = []
    weaknesses: list[str] = []
    score_components: list[float] = []

    p_values = _P_VALUE.findall(text)
    cis = _CI.findall(text)
    effect_sizes = _EFFECT_SIZE.findall(text)
    sample_size_mentions = _SAMPLE_SIZE.findall(text)
    power_matches = _POWER.findall(text)
    descriptive = _DESCRIPTIVE.findall(text)
    assumption_checks = _ASSUMPTION.findall(text)
    stat_tests = _STAT_TESTS.findall(text)

    # Unique test names
    unique_tests = list({t.lower().strip() for t in stat_tests})[:10]

    metrics = StatisticalMetrics(
        has_p_values=bool(p_values),
        has_confidence_intervals=bool(cis),
        has_effect_sizes=bool(effect_sizes),
        has_sample_size=bool(sample_size_mentions),
        has_power_analysis=bool(power_matches),
        p_value_count=len(p_values),
        statistical_tests_used=unique_tests,
        assumption_checks_mentioned=bool(assumption_checks),
        descriptive_stats_present=bool(descriptive),
    )

    # Determine if this is a quantitative manuscript
    is_quantitative = bool(stat_tests) or bool(p_values) or bool(descriptive)

    if not is_quantitative:
        # Qualitative manuscript — statistical review less relevant
        dim = QualityDimension(
            name="Statistical Validity",
            score=70.0,
            weight=1.0,
            grade="B",
            rationale="Qualitative or theoretical manuscript — statistical review not applicable.",
            strengths=["Qualitative/theoretical study — statistical reporting not required"],
            weaknesses=[],
        )
        return metrics, dim, issues

    # ── 1. p-values ────────────────────────────────────────────────────────────
    if p_values:
        score_components.append(85.0)
        strengths.append(f"{len(p_values)} p-value(s) reported")
    else:
        score_components.append(40.0)
        weaknesses.append("No p-values reported")
        issues.append(ReviewIssue(
            severity=IssueSeverity.MAJOR,
            section="Results / Statistical Analysis",
            title="p-values not reported",
            description=(
                "No statistical significance values (p-values) were found. "
                "For quantitative studies, this is a mandatory reporting requirement."
            ),
            recommendation=(
                "Report exact p-values for all inferential tests (e.g., p = 0.023, not p < 0.05). "
                "Follow APA 7th edition statistical reporting guidelines."
            ),
        ))

    # ── 2. Confidence intervals ───────────────────────────────────────────────
    if cis:
        score_components.append(88.0)
        strengths.append(f"Confidence intervals reported ({len(cis)} found)")
    else:
        score_components.append(50.0)
        weaknesses.append("No confidence intervals reported")
        issues.append(ReviewIssue(
            severity=IssueSeverity.MAJOR,
            section="Results",
            title="Confidence intervals missing",
            description=(
                "Confidence intervals (CIs) are absent from the statistical results. "
                "Most high-impact journals now require CIs alongside p-values."
            ),
            recommendation=(
                "Report 95% confidence intervals for all key estimates: "
                "means, differences, odds ratios, correlations. "
                "Format: 95% CI [lower, upper]."
            ),
        ))

    # ── 3. Effect sizes ───────────────────────────────────────────────────────
    if effect_sizes:
        score_components.append(90.0)
        strengths.append(f"Effect sizes reported (e.g., {effect_sizes[0][:30]})")
    else:
        score_components.append(45.0)
        weaknesses.append("Effect sizes not reported")
        issues.append(ReviewIssue(
            severity=IssueSeverity.MAJOR,
            section="Results",
            title="Effect sizes not reported",
            description=(
                "No effect size measures found (Cohen's d, η², OR, r, etc.). "
                "Effect sizes are mandatory in APA-style reporting and expected by most journals."
            ),
            recommendation=(
                "Report appropriate effect size for each test: "
                "Cohen's d for t-tests, η² for ANOVA, r for correlations, "
                "OR for logistic regression. Include interpretation (small/medium/large)."
            ),
        ))

    # ── 4. Descriptive statistics ─────────────────────────────────────────────
    if descriptive:
        score_components.append(85.0)
        strengths.append("Descriptive statistics (mean, SD, etc.) present")
    else:
        score_components.append(45.0)
        weaknesses.append("Descriptive statistics missing")
        issues.append(ReviewIssue(
            severity=IssueSeverity.MAJOR,
            section="Results",
            title="Descriptive statistics not reported",
            description=(
                "No descriptive statistics (means, standard deviations, percentages) found. "
                "These must precede inferential statistics."
            ),
            recommendation=(
                "Present a descriptive statistics table (mean, SD, range, n) for "
                "all key variables before reporting inferential tests."
            ),
        ))

    # ── 5. Statistical assumption checks ──────────────────────────────────────
    if assumption_checks:
        score_components.append(85.0)
        strengths.append("Statistical assumptions verified")
    else:
        score_components.append(55.0)
        weaknesses.append("Statistical assumptions not checked or reported")
        issues.append(ReviewIssue(
            severity=IssueSeverity.MINOR,
            section="Methodology / Results",
            title="Statistical assumption checks not reported",
            description=(
                "No mention of assumption testing (normality, homogeneity of variance, "
                "multicollinearity, etc.) was found."
            ),
            recommendation=(
                "Report assumption checks: "
                "Shapiro-Wilk (normality), Levene (homogeneity), VIF (multicollinearity). "
                "If assumptions are violated, justify the chosen test or use non-parametric alternatives."
            ),
        ))

    # ── 6. Power analysis ─────────────────────────────────────────────────────
    if power_matches:
        score_components.append(88.0)
        strengths.append("Power analysis or sample size justification provided")
    else:
        score_components.append(55.0)
        weaknesses.append("No power analysis reported")
        issues.append(ReviewIssue(
            severity=IssueSeverity.MINOR,
            section="Methodology",
            title="No sample size justification or power analysis",
            description=(
                "No a priori power analysis or sample size calculation was reported. "
                "Reviewers increasingly require statistical power justification."
            ),
            recommendation=(
                "Conduct and report an a priori power analysis (e.g., using G*Power). "
                "State: target power (≥0.80), alpha (0.05), expected effect size, "
                "and resulting minimum sample size."
            ),
        ))

    # ── 7. Statistical tests identified ───────────────────────────────────────
    if unique_tests:
        score_components.append(80.0)
        strengths.append(f"Statistical tests identified: {', '.join(unique_tests[:3])}")
    else:
        score_components.append(50.0)
        weaknesses.append("Statistical tests not clearly identified")
        issues.append(ReviewIssue(
            severity=IssueSeverity.MINOR,
            section="Methodology / Results",
            title="Statistical tests not clearly identified",
            description=(
                "No specific statistical tests were mentioned in the methodology or results. "
                "Readers must know which tests were used and why."
            ),
            recommendation=(
                "Name each statistical test used (e.g., independent samples t-test, "
                "one-way ANOVA) and justify why it is appropriate for the research design."
            ),
        ))

    overall = sum(score_components) / len(score_components) if score_components else 50.0

    dim = QualityDimension(
        name="Statistical Validity",
        score=round(overall, 1),
        weight=1.0,
        grade=_score_to_grade(overall),
        rationale=(
            f"Stats: p-values={bool(p_values)}, CIs={bool(cis)}, "
            f"effect sizes={bool(effect_sizes)}, assumptions={bool(assumption_checks)}, "
            f"power={bool(power_matches)}, tests={', '.join(unique_tests[:2]) or 'none'}."
        ),
        strengths=strengths[:5],
        weaknesses=weaknesses[:5],
    )
    return metrics, dim, issues
