"""Statistics Agent (Phase XIII)."""
from __future__ import annotations

import re
import time

from .base_agent import AcademicAgent, AgentRegistry
from .models import AgentContext, AgentResult, AgentTask, AgentType

_TEST_SIGNALS = {
    "t-test": [r"\bt[\s-]test\b", r"\bindependent\s+samples\b", r"\bpaired\s+t\b"],
    "ANOVA": [r"\banova\b", r"\banalysis\s+of\s+variance\b", r"\bf[\s-]test\b"],
    "regression": [r"\bregression\b", r"\bols\b", r"\blm\s*\(", r"\bpredictor[s]?\b"],
    "chi-square": [r"\bchi[\s-]?square\b", r"\bχ²\b", r"\bcategorical\s+analysis\b"],
    "correlation": [r"\bcorrelation\b", r"\bpearson\b", r"\bspearman\b"],
    "SEM": [r"\bsem\b", r"\bstructural\s+equation\b", r"\blavaan\b"],
    "survival": [r"\bsurvival\s+analysis\b", r"\bkaplan[\s-]meier\b", r"\bhazard\b"],
    "mixed models": [r"\bmixed\s+model\b", r"\bhlm\b", r"\blme4\b", r"\bnested\b"],
    "factor analysis": [r"\bfactor\s+analysis\b", r"\befa\b", r"\bcfa\b", r"\bpca\b"],
    "non-parametric": [r"\bmann[\s-]whitney\b", r"\bwilcoxon\b", r"\bkruskal\b", r"\bfriedman\b"],
}

_EFFECT_RE    = re.compile(r"\bcohen'?s?\s*d\b|\bhedge'?s?\s*g\b|\bη[²2]?\b|\bomega[\s_]?squared\b", re.IGNORECASE)
_PVAL_RE      = re.compile(r"\bp\s*[<=<]\s*[\d.]+\b|\bp\s*=\s*[\d.]+\b", re.IGNORECASE)
_CI_RE        = re.compile(r"\b95\s*%\s*ci\b|\bconfidence\s+interval\b", re.IGNORECASE)


@AgentRegistry.register
class StatisticsAgent(AcademicAgent):
    agent_id = "statistics_agent_v1"
    agent_type = AgentType.STATISTICS
    name = "Statistics Agent"
    domain = "Statistical Analysis"
    capabilities = [
        "statistical_test_identification", "power_analysis", "effect_size_assessment",
        "assumption_checking", "model_selection", "result_interpretation",
    ]

    async def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        t0 = time.monotonic()
        text = task.content
        text_lower = text.lower()

        # Detect statistical tests
        detected_tests = []
        for test_name, patterns in _TEST_SIGNALS.items():
            if any(re.search(p, text_lower) for p in patterns):
                detected_tests.append(test_name)

        # Detect reporting quality
        has_effect_size = bool(_EFFECT_RE.search(text))
        p_values = _PVAL_RE.findall(text)
        has_ci = bool(_CI_RE.search(text))
        has_power = any(kw in text_lower for kw in ["power analysis", "power =", "1 - β", "power of"])
        has_assumptions = any(kw in text_lower for kw in [
            "normality", "homogeneity", "levene", "shapiro", "bartlett", "multicollinearity",
        ])

        issues: list[str] = []
        if not detected_tests:
            issues.append("No statistical tests identified")
        if not has_effect_size:
            issues.append("Effect sizes not reported — add Cohen's d, η², or equivalent")
        if not has_ci:
            issues.append("Confidence intervals not reported")
        if not has_power:
            issues.append("Power analysis not reported — justify sample size")
        if not has_assumptions:
            issues.append("Statistical assumption checks not documented")
        if p_values and not has_effect_size:
            issues.append("P-values reported without effect sizes — statistical significance ≠ practical significance")

        # Inherit methodology context
        prev_method = context.get_result(AgentType.METHODOLOGY)
        sample_sizes = []
        if prev_method:
            sample_sizes = prev_method.output.get("sample_sizes_detected", [])

        reporting_score = (
            has_effect_size * 0.25
            + has_ci * 0.25
            + has_power * 0.25
            + has_assumptions * 0.25
        )
        confidence = min(0.92, 0.45 + 0.1 * len(detected_tests) + 0.25 * reporting_score)

        output = {
            "detected_tests": detected_tests,
            "p_value_count": len(p_values),
            "has_effect_sizes": has_effect_size,
            "has_confidence_intervals": has_ci,
            "has_power_analysis": has_power,
            "has_assumption_checks": has_assumptions,
            "reporting_completeness_score": round(reporting_score, 3),
            "statistical_issues": issues,
            "inherited_sample_sizes": sample_sizes,
            "recommendations": [
                "Report effect sizes alongside all p-values (Cohen's d, η², ω²)",
                "Include 95% confidence intervals for primary outcomes",
                "Document all assumption checks (normality, homoscedasticity, etc.)",
                "Consider using JASP or R for reproducible statistical reporting",
                "Pre-register your analysis plan to reduce p-hacking risk",
            ],
        }

        return self._timed_result(
            task, output, confidence,
            reasoning=(
                f"Detected {len(detected_tests)} statistical method(s). "
                f"Reporting completeness: {reporting_score:.0%}. "
                f"{len(issues)} statistical issues found."
            ),
            evidence=[f"Test detected: {t}" for t in detected_tests[:5]] + p_values[:3],
            t0=t0,
        )
