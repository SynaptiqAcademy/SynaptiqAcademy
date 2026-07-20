"""Autonomous Research Agents — Quality controller (Phase XIII).

Cross-validates agent outputs, detects inconsistencies, flags hallucinations,
and produces a QualityReport with overall confidence.
"""
from __future__ import annotations

from .models import (
    AgentResult, AgentStatus, AgentType, QualityLevel, QualityReport,
    ValidationResult,
)


def _level_from_score(score: float) -> QualityLevel:
    if score >= 0.85: return QualityLevel.EXCELLENT
    if score >= 0.70: return QualityLevel.GOOD
    if score >= 0.50: return QualityLevel.ACCEPTABLE
    if score >= 0.30: return QualityLevel.POOR
    return QualityLevel.UNACCEPTABLE


def _validate_result(result: AgentResult) -> ValidationResult:
    """Validate a single agent result."""
    issues: list[str] = []
    flags: list[str] = []

    if result.status == AgentStatus.FAILED:
        issues.append(f"Agent failed: {result.output.get('error', 'unknown error')}")
        flags.append("agent_failure")

    if result.confidence < 0.15:
        issues.append("Confidence critically low — result unreliable")
        flags.append("low_confidence")

    if not result.output or result.output == {"error": ""}:
        issues.append("Empty output")
        flags.append("empty_output")

    if not result.reasoning:
        issues.append("No reasoning provided — explainability missing")

    # Agent-specific validation
    if result.agent_type == AgentType.RESEARCH_ETHICS:
        if result.output.get("critical_issues"):
            issues.extend(result.output["critical_issues"][:2])
            flags.append("ethics_violation")

    if result.agent_type == AgentType.STATISTICS:
        if not result.output.get("has_effect_sizes") and result.output.get("p_value_count", 0) > 0:
            issues.append("P-values without effect sizes — incomplete statistical reporting")

    if result.agent_type == AgentType.LITERATURE_REVIEW:
        if result.output.get("citation_count", 1) < 5:
            issues.append("Very few citations — literature coverage may be insufficient")

    adj_confidence = result.confidence * (0.9 if issues else 1.0)
    is_valid = AgentStatus.FAILED not in [result.status] and "agent_failure" not in flags

    return ValidationResult(
        agent_type=result.agent_type,
        is_valid=is_valid,
        quality_level=_level_from_score(adj_confidence),
        issues=issues,
        confidence_after_validation=round(adj_confidence, 3),
        hallucination_flags=flags,
    )


def _cross_check(results: dict[str, AgentResult]) -> list[str]:
    """Detect cross-agent inconsistencies."""
    inconsistencies: list[str] = []

    lit = results.get(AgentType.LITERATURE_REVIEW.value)
    meth = results.get(AgentType.METHODOLOGY.value)
    stat = results.get(AgentType.STATISTICS.value)
    ethics = results.get(AgentType.RESEARCH_ETHICS.value)
    writing = results.get(AgentType.ACADEMIC_WRITING.value)

    if meth and stat:
        designs = meth.output.get("detected_designs", [])
        tests = stat.output.get("detected_tests", [])
        if "qualitative" in designs and tests:
            inconsistencies.append(
                "Inconsistency: qualitative design detected (Methodology) "
                "but quantitative tests found (Statistics) — verify mixed-methods rationale"
            )

    if lit and stat:
        lit_cites = lit.output.get("citation_count", 0)
        stat_tests = stat.output.get("detected_tests", [])
        if lit_cites < 5 and len(stat_tests) >= 3:
            inconsistencies.append(
                "Inconsistency: weak literature base but complex statistical analysis — "
                "ensure theoretical grounding for the chosen tests"
            )

    if ethics:
        if ethics.output.get("involves_human_participants") and not ethics.output.get("has_ethics_approval"):
            inconsistencies.append(
                "CRITICAL INCONSISTENCY: Research involves human participants "
                "but no ethics approval is declared"
            )

    if writing and meth:
        writing_score = writing.output.get("quality_score", 1.0)
        validity = meth.output.get("validity_score", 1.0)
        if writing_score < 0.4 and validity > 0.7:
            inconsistencies.append(
                "Inconsistency: strong methodology but poor writing quality — "
                "methodology descriptions may not be clearly communicated"
            )

    return inconsistencies


def validate_execution(
    results: dict[str, AgentResult],
    execution_id: str = "",
) -> QualityReport:
    """Cross-validate all agent results and produce a QualityReport."""
    agent_reports: dict[str, ValidationResult] = {}
    all_issues: list[str] = []
    all_flags: list[str] = []

    for agent_type_val, result in results.items():
        if not isinstance(result, AgentResult):
            continue
        vr = _validate_result(result)
        agent_reports[agent_type_val] = vr
        all_issues.extend(vr.issues)
        all_flags.extend(vr.hallucination_flags)

    inconsistencies = _cross_check(results)

    # Overall confidence: weighted average of per-agent post-validation confidences
    confidences = [vr.confidence_after_validation for vr in agent_reports.values()]
    overall_conf = round(sum(confidences) / max(len(confidences), 1), 3)

    # Penalise for inconsistencies and flags
    penalty = len(inconsistencies) * 0.05 + len(all_flags) * 0.03
    overall_conf = max(0.05, overall_conf - penalty)

    overall_quality = _level_from_score(overall_conf)

    # Citation issues
    citation_issues: list[str] = []
    cite_result = results.get(AgentType.CITATION_INTELLIGENCE.value)
    if cite_result and isinstance(cite_result, AgentResult):
        citation_issues = cite_result.output.get("citation_issues", [])

    # Methodology issues
    meth_issues: list[str] = []
    meth_result = results.get(AgentType.METHODOLOGY.value)
    if meth_result and isinstance(meth_result, AgentResult):
        meth_issues = meth_result.output.get("methodological_issues", [])

    recommendations: list[str] = []
    if overall_quality in (QualityLevel.POOR, QualityLevel.UNACCEPTABLE):
        recommendations.append("Fundamental revision required — address all critical issues before proceeding")
    if "ethics_violation" in all_flags:
        recommendations.append("Resolve ethics compliance issues immediately — this is a submission blocker")
    if inconsistencies:
        recommendations.append("Resolve cross-agent inconsistencies — they signal logical gaps in the research")
    if overall_conf >= 0.75:
        recommendations.append("Research quality is strong — proceed to submission preparation")

    return QualityReport(
        execution_id=execution_id,
        overall_quality=overall_quality,
        agent_reports=agent_reports,
        inconsistencies=inconsistencies,
        hallucination_flags=all_flags,
        citation_issues=citation_issues,
        methodology_issues=meth_issues,
        overall_confidence=overall_conf,
        recommendations=recommendations,
    )
