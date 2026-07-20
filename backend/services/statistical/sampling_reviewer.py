"""Statistical Intelligence 2.0 — Sampling reviewer (Phase X).

Evaluates sample adequacy, power, bias, attrition, representativeness.
Rule-based — no LLM dependencies.
"""
from __future__ import annotations

import re
from .models import (
    AnalysisMethod, IssueSeverity, ResearchDesign, SamplingAnalysis,
    StatisticalIssue, _score_to_grade,
)

# ── Minimum sample size heuristics per method ─────────────────────────────────
# Based on Cohen (1988) and established methodological guidelines.

_MIN_SAMPLE: dict[AnalysisMethod, int] = {
    AnalysisMethod.T_TEST:               30,
    AnalysisMethod.PAIRED_T_TEST:        30,
    AnalysisMethod.ONE_SAMPLE_T:         20,
    AnalysisMethod.ANOVA:                30,
    AnalysisMethod.REPEATED_ANOVA:       20,
    AnalysisMethod.ANCOVA:               40,
    AnalysisMethod.MANOVA:               50,
    AnalysisMethod.CHI_SQUARE:           30,
    AnalysisMethod.FISHER_EXACT:         10,
    AnalysisMethod.PEARSON_CORRELATION:  30,
    AnalysisMethod.SPEARMAN_CORRELATION: 20,
    AnalysisMethod.LINEAR_REGRESSION:    50,
    AnalysisMethod.MULTIPLE_REGRESSION:  100,
    AnalysisMethod.LOGISTIC_REGRESSION:  100,
    AnalysisMethod.ORDINAL_REGRESSION:   100,
    AnalysisMethod.MIXED_MODELS:         30,
    AnalysisMethod.FACTOR_ANALYSIS:      100,
    AnalysisMethod.CFA:                  150,
    AnalysisMethod.PCA:                  100,
    AnalysisMethod.SEM:                  200,
    AnalysisMethod.PLS_SEM:              100,
    AnalysisMethod.CLUSTER_ANALYSIS:     50,
    AnalysisMethod.TIME_SERIES:          30,
    AnalysisMethod.META_ANALYSIS:        5,
    AnalysisMethod.MANN_WHITNEY:         20,
    AnalysisMethod.KRUSKAL_WALLIS:       20,
    AnalysisMethod.WILCOXON:             20,
    AnalysisMethod.BAYESIAN:             20,
    AnalysisMethod.MACHINE_LEARNING:     100,
    AnalysisMethod.SURVIVAL_ANALYSIS:    50,
}

# ── Text signals ──────────────────────────────────────────────────────────────

_POWER_RE = re.compile(
    r"(?:power|statistical power|power analysis|a priori power)\s*[=:>]\s*(\d+\.?\d*)",
    re.IGNORECASE,
)
_ATTRITION_RE = re.compile(
    r"(?:attrition|dropout|drop-out|lost to follow-up)\s*(?:rate)?\s*[=:]\s*(\d+\.?\d*)",
    re.IGNORECASE,
)
_RESPONSE_RE = re.compile(
    r"(?:response rate|return rate|completion rate)\s*[=:]\s*(\d+\.?\d*)\s*%?",
    re.IGNORECASE,
)
_EFFECT_SIZE_RE = re.compile(
    r"(?:cohen'?s?\s*d|effect size|f\s*=\s*\d|η²|omega²|r²)\s*[=:]\s*(\d+\.?\d*)",
    re.IGNORECASE,
)

_POWER_ANALYSIS_MENTIONS = [
    "g*power", "power analysis", "a priori", "sample size calculation",
    "effect size", "statistical power",
]
_BIAS_SIGNALS = {
    "selection bias":     ["selection bias", "volunteer bias", "healthy worker effect"],
    "response bias":      ["response bias", "social desirability", "acquiescence bias"],
    "attrition bias":     ["attrition bias", "differential dropout", "loss to follow-up"],
    "non-response bias":  ["non-response bias", "nonresponse", "non-respondents"],
    "sampling bias":      ["convenience sample", "availability sample", "self-selected"],
}


def review_sampling(text: str, design: ResearchDesign) -> tuple[SamplingAnalysis, list[StatisticalIssue]]:
    lower = text.lower()
    n = design.sample_size
    primary = design.primary_method
    issues: list[StatisticalIssue] = []

    # Recommended minimum for method
    recommended_min = _MIN_SAMPLE.get(primary, 50)

    # Power mentioned?
    power_match = _POWER_RE.search(text)
    power_estimate = float(power_match.group(1)) / 100 if power_match else 0.0
    if power_estimate > 1.0:
        power_estimate /= 100

    has_power_analysis = any(s in lower for s in _POWER_ANALYSIS_MENTIONS)

    # Response rate
    resp_match = _RESPONSE_RE.search(text)
    response_rate = float(resp_match.group(1)) if resp_match else None

    # Attrition
    att_match = _ATTRITION_RE.search(text)
    attrition = float(att_match.group(1)) if att_match else None

    # Scoring
    score = 70.0  # baseline

    if n == 0:
        adequacy_verdict = "cannot_determine"
        is_adequate = False
        score = 40.0
        issues.append(StatisticalIssue(
            severity=IssueSeverity.MAJOR,
            category="sampling",
            title="Sample size not reported",
            description="No sample size (N) was identified in the text.",
            recommendation="Report the exact sample size used in the analysis.",
        ))
    elif n < recommended_min // 2:
        adequacy_verdict = "critically_inadequate"
        is_adequate = False
        score = 25.0
        issues.append(StatisticalIssue(
            severity=IssueSeverity.CRITICAL,
            category="sampling",
            title=f"Critically small sample (n={n})",
            description=(
                f"The sample size n={n} is far below the recommended minimum of n={recommended_min} "
                f"for {primary.value}. Results are likely underpowered and unstable."
            ),
            recommendation=(
                f"Increase sample to at least n={recommended_min}. "
                f"Conduct a post-hoc power analysis using G*Power to quantify the problem."
            ),
        ))
    elif n < recommended_min:
        adequacy_verdict = "marginal"
        is_adequate = False
        score = 50.0
        issues.append(StatisticalIssue(
            severity=IssueSeverity.MAJOR,
            category="sampling",
            title=f"Sample size below recommended minimum (n={n}, min={recommended_min})",
            description=(
                f"The sample size n={n} falls below the recommended minimum of n={recommended_min} "
                f"for {primary.value}. Statistical power may be insufficient."
            ),
            recommendation=(
                f"Report a power analysis. Consider whether results can be generalised "
                f"given the limited sample. A post-hoc power analysis is essential."
            ),
        ))
    else:
        adequacy_verdict = "adequate"
        is_adequate = True
        score = 75.0 + min(25.0, (n - recommended_min) / recommended_min * 20)

    if not has_power_analysis:
        score -= 10
        issues.append(StatisticalIssue(
            severity=IssueSeverity.MAJOR,
            category="sampling",
            title="Power analysis not reported",
            description=(
                "No a priori or post-hoc power analysis was found. "
                "This makes it impossible to evaluate whether the study was adequately powered."
            ),
            recommendation=(
                "Conduct and report a power analysis. Use G*Power or pwr (R) to compute "
                "the achieved power given n, α=0.05, and the detected effect size."
            ),
        ))

    if response_rate is not None and response_rate < 70:
        score -= 10
        issues.append(StatisticalIssue(
            severity=IssueSeverity.MAJOR if response_rate < 50 else IssueSeverity.MODERATE,
            category="sampling",
            title=f"Low response rate ({response_rate:.0f}%)",
            description=(
                f"A response rate of {response_rate:.0f}% increases non-response bias risk. "
                "The final sample may not represent the target population."
            ),
            recommendation=(
                "Compare respondents and non-respondents on key demographics. "
                "Discuss potential non-response bias in limitations."
            ),
        ))

    if attrition is not None and attrition > 20:
        issues.append(StatisticalIssue(
            severity=IssueSeverity.MAJOR,
            category="sampling",
            title=f"High attrition rate ({attrition:.0f}%)",
            description=(
                f"Attrition of {attrition:.0f}% threatens the validity of longitudinal findings. "
                "Differential dropout may introduce systematic bias."
            ),
            recommendation=(
                "Conduct attrition analysis comparing drop-outs with completers on baseline measures. "
                "Consider multiple imputation to handle missing data."
            ),
        ))

    # Check for detected biases
    for bias_name, signals in _BIAS_SIGNALS.items():
        if any(s in lower for s in signals) and "acknowledged" not in lower:
            issues.append(StatisticalIssue(
                severity=IssueSeverity.MODERATE,
                category="sampling",
                title=f"Potential {bias_name}",
                description=(
                    f"Signals of {bias_name} detected. This may limit the "
                    "representativeness and generalisability of findings."
                ),
                recommendation=(
                    f"Explicitly acknowledge {bias_name} as a limitation and discuss "
                    "its potential impact on conclusions."
                ),
            ))

    score = max(0.0, min(100.0, score))
    grade = _score_to_grade(score)

    analysis = SamplingAnalysis(
        sample_size=n,
        recommended_min=recommended_min,
        power_estimate=power_estimate,
        is_adequate=is_adequate,
        adequacy_verdict=adequacy_verdict,
        issues=[i.title for i in issues],
        score=score,
        grade=grade,
    )
    return analysis, issues
