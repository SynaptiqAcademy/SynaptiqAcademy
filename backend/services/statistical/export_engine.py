"""Statistical Intelligence 2.0 — Export engine (Phase X).

Exports statistical intelligence results in 8 formats.
"""
from __future__ import annotations

import re
from .models import ExportFormat, IssueSeverity, StatisticalIntelligenceResult


def export_result(
    result: StatisticalIntelligenceResult,
    fmt: ExportFormat,
) -> tuple[str, str, str]:
    """Return (content, filename, content_type)."""
    slug = re.sub(r"[^a-z0-9]+", "_", result.topic.lower())[:40] or "statistical_review"
    dispatch = {
        ExportFormat.STATISTICAL_REVIEW:  _to_statistical_review,
        ExportFormat.METHODOLOGY_REVIEW:  _to_methodology_review,
        ExportFormat.REVIEWER_REPORT:     _to_reviewer_report,
        ExportFormat.SUPERVISOR_REPORT:   _to_supervisor_report,
        ExportFormat.JOURNAL_SUBMISSION:  _to_journal_submission,
        ExportFormat.MARKDOWN:            _to_markdown,
        ExportFormat.LATEX:               _to_latex,
        ExportFormat.TEXT:                _to_text,
    }
    fn_map = {
        ExportFormat.STATISTICAL_REVIEW:  (f"{slug}_statistical_review.md", "text/markdown"),
        ExportFormat.METHODOLOGY_REVIEW:  (f"{slug}_methodology_review.md", "text/markdown"),
        ExportFormat.REVIEWER_REPORT:     (f"{slug}_reviewer_report.md", "text/markdown"),
        ExportFormat.SUPERVISOR_REPORT:   (f"{slug}_supervisor_report.md", "text/markdown"),
        ExportFormat.JOURNAL_SUBMISSION:  (f"{slug}_journal_submission.md", "text/markdown"),
        ExportFormat.MARKDOWN:            (f"{slug}_review.md", "text/markdown"),
        ExportFormat.LATEX:               (f"{slug}_review.tex", "application/x-latex"),
        ExportFormat.TEXT:                (f"{slug}_review.txt", "text/plain"),
    }
    content = dispatch[fmt](result)
    filename, content_type = fn_map[fmt]
    return content, filename, content_type


# ── Helpers ───────────────────────────────────────────────────────────────────

def _latex_escape(s: str) -> str:
    chars = [("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"),
             ("$", r"\$"), ("#", r"\#"), ("_", r"\_"), ("{", r"\{"),
             ("}", r"\}"), ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}")]
    for ch, rep in chars:
        s = s.replace(ch, rep)
    return s


def _issue_section_md(title: str, issues: list, severity_label: str) -> str:
    if not issues:
        return ""
    lines = [f"\n### {title}\n"]
    for i in issues:
        lines.append(f"- **{i.title}** ({severity_label}): {i.description}")
        lines.append(f"  - *Recommendation:* {i.recommendation}")
    return "\n".join(lines)


# ── Export formats ────────────────────────────────────────────────────────────

def _to_statistical_review(r: StatisticalIntelligenceResult) -> str:
    dims = r.dimensions
    pr = r.publication_readiness
    lines = [
        f"# Statistical Review Report",
        f"\n**Topic:** {r.topic}",
        f"**Research Question:** {r.research_question}",
        f"**Study Type:** {r.research_design.study_type.value}",
        f"**Primary Method:** {r.research_design.primary_method.value}",
        f"**Sample Size:** {r.research_design.sample_size or 'Not reported'}",
        f"**Overall Score:** {r.overall_score:.1f}/100 ({r.overall_verdict.value})",
        f"**Analysis Depth:** {r.analysis_depth.value}",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        r.executive_summary or "_Statistical review summary not available._",
        "",
        "---",
        "",
        "## Statistical Review",
        "",
        r.statistical_review_text or "_Detailed review not available._",
        "",
        "---",
        "",
        "## Quality Dimensions",
        "",
        "| Dimension | Score | Grade |",
        "|---|---|---|",
        f"| Methodological Rigour | {dims.methodological_rigor.score:.1f} | {dims.methodological_rigor.grade} |",
        f"| Sample Adequacy | {dims.sample_adequacy.score:.1f} | {dims.sample_adequacy.grade} |",
        f"| Data Quality | {dims.data_quality.score:.1f} | {dims.data_quality.grade} |",
        f"| Result Validity | {dims.result_validity.score:.1f} | {dims.result_validity.grade} |",
        f"| Construct Validity | {dims.construct_validity.score:.1f} | {dims.construct_validity.grade} |",
        f"| Reporting Quality | {dims.reporting_quality.score:.1f} | {dims.reporting_quality.grade} |",
        "",
        "---",
        "",
        "## Statistical Issues",
    ]

    lines.append(_issue_section_md("Critical Issues", r.critical_issues, "CRITICAL"))
    lines.append(_issue_section_md("Major Issues", r.major_issues, "MAJOR"))
    lines.append(_issue_section_md("Moderate Issues", r.moderate_issues, "MODERATE"))
    lines.append(_issue_section_md("Minor Issues", r.minor_issues, "MINOR"))

    lines += [
        "",
        "---",
        "",
        "## Assumption Verification",
        "",
        "| Assumption | Method | Status |",
        "|---|---|---|",
    ]
    for a in r.assumption_checks:
        lines.append(f"| {a.name} | {a.method} | {a.status.value} |")

    lines += [
        "",
        "---",
        "",
        "## Recommended Analyses",
        "",
    ]
    for rec in r.recommended_analyses:
        lines.append(f"- **{rec.analysis}** ({rec.priority.value}): {rec.rationale}")
        if rec.software_guidance:
            lines.append(f"  - *Software:* {rec.software_guidance}")

    lines += [
        "",
        "---",
        "",
        "## Publication Readiness",
        "",
        f"**Score:** {pr.overall_score:.1f}/100",
        f"**Acceptance Probability:** {pr.acceptance_probability*100:.0f}%",
        f"**Desk Rejection Risk:** {pr.desk_rejection_risk*100:.0f}%",
        f"**Verdict:** {pr.verdict.value}",
        f"**Strongest Element:** {pr.strongest_element}",
        f"**Critical Barrier:** {pr.critical_barrier}",
        "",
        pr.assessment,
        "",
        "---",
        "",
        "## Revision Roadmap",
        "",
    ]
    for phase in r.revision_roadmap:
        pd = phase if isinstance(phase, dict) else phase.to_dict()
        lines.append(f"### Phase {pd.get('phase','')}: {pd.get('title','')} ({pd.get('priority','')})")
        lines.append(f"*Estimated effort:* {pd.get('estimated_effort', 'Unknown')}")
        for action in pd.get("actions", []):
            lines.append(f"- {action}")
        lines.append("")

    return "\n".join(lines)


def _to_methodology_review(r: StatisticalIntelligenceResult) -> str:
    design = r.research_design
    sampling = r.sampling_analysis
    dq = r.data_quality
    lines = [
        "# Methodology Review Report",
        "",
        f"**Topic:** {r.topic}",
        f"**Study Type:** {design.study_type.value}",
        f"**Statistical Methods:** {', '.join(m.value for m in design.detected_methods[:5])}",
        f"**Sample Size:** {design.sample_size or 'Not reported'}",
        "",
        "---",
        "",
        "## Research Design",
        "",
        f"- **Study type:** {design.study_type.value}",
        f"- **Sampling strategy:** {design.sampling_strategy}",
        f"- **Longitudinal:** {'Yes' if design.is_longitudinal else 'No'}",
        f"- **Control group:** {'Yes' if design.has_control_group else 'No'}",
        f"- **Randomisation:** {'Yes' if design.has_randomisation else 'No'}",
        f"- **Discipline:** {design.discipline}",
        "",
        "### Variables Identified",
        f"- Dependent: {', '.join(design.dependent_variables) or 'Not specified'}",
        f"- Independent: {', '.join(design.independent_variables) or 'Not specified'}",
        f"- Control: {', '.join(design.control_variables) or 'None identified'}",
        f"- Moderators: {', '.join(design.moderators) or 'None identified'}",
        f"- Mediators: {', '.join(design.mediators) or 'None identified'}",
        "",
        "---",
        "",
        "## Sampling Analysis",
        "",
        f"- **Sample size:** {sampling.sample_size}",
        f"- **Recommended minimum:** {sampling.recommended_min}",
        f"- **Adequacy verdict:** {sampling.adequacy_verdict}",
        f"- **Estimated power:** {sampling.power_estimate*100:.0f}%" if sampling.power_estimate else "- **Power:** Not reported",
        f"- **Adequacy score:** {sampling.score:.1f}/100 ({sampling.grade})",
        "",
        "---",
        "",
        "## Data Quality",
        "",
        f"- **Missing data rate:** {dq.overall_missing_rate*100:.1f}%",
        f"- **Normality tested:** {'Yes' if dq.normality_tested else 'No'}",
        f"- **Homoscedasticity tested:** {'Yes' if dq.homoscedasticity_tested else 'No'}",
        f"- **Multicollinearity assessed:** {'Yes' if dq.multicollinearity_tested else 'No'}",
        f"- **Max VIF:** {dq.max_vif:.1f}" if dq.max_vif else "- **VIF:** Not reported",
        f"- **Data quality score:** {dq.score:.1f}/100 ({dq.grade})",
        "",
        "---",
        "",
        "## Method Evaluations",
        "",
    ]
    for me in r.method_evaluations:
        med = me.to_dict()
        lines += [
            f"### {me.method.value}",
            f"- **Appropriate:** {'Yes' if me.is_appropriate else 'No — see rationale'}",
            f"- **Score:** {me.appropriateness_score:.1f}/100",
            f"- {me.rationale}",
            f"- **Missing elements:** {', '.join(me.missing_reporting) or 'None detected'}",
        ]
        if me.alternatives:
            lines.append(f"- **Alternatives:** {', '.join(me.alternatives[:3])}")
        lines.append("")

    return "\n".join(lines)


def _to_reviewer_report(r: StatisticalIntelligenceResult) -> str:
    lines = [
        "# Peer Reviewer Statistical Report",
        "",
        f"*This report adopts the perspective of a senior statistical reviewer.*",
        "",
        f"**Manuscript topic:** {r.topic}",
        f"**Research question:** {r.research_question}",
        f"**Recommendation:** {r.overall_verdict.value.replace('_', ' ').title()}",
        "",
        "---",
        "",
        "## Reviewer Assessment",
        "",
        r.statistical_review_text or r.executive_summary or "_Review text not available._",
        "",
        "---",
        "",
        "## Specific Reviewer Comments",
        "",
    ]
    for i, crit in enumerate(r.reviewer_criticisms, 1):
        c = crit if isinstance(crit, dict) else crit.to_dict()
        lines += [
            f"**Comment {i}** ({c.get('severity', 'major').upper()})",
            "",
            c.get("comment", ""),
            "",
            f"*Suggested author response:* {c.get('suggested_response', '')}",
            "",
        ]

    lines += [
        "---",
        "",
        "## Critical Statistical Concerns",
        "",
    ]
    for issue in r.critical_issues + r.major_issues:
        lines.append(f"- **{issue.title}**: {issue.description}")
        lines.append(f"  - Required action: {issue.recommendation}")
    lines.append("")

    lines += [
        "---",
        "",
        "## Publication Readiness Score",
        "",
        f"**Statistical quality score:** {r.publication_readiness.overall_score:.1f}/100",
        f"**Acceptance probability:** {r.publication_readiness.acceptance_probability*100:.0f}%",
        f"**Verdict:** {r.publication_readiness.verdict.value}",
        "",
        r.publication_readiness.assessment,
    ]
    return "\n".join(lines)


def _to_supervisor_report(r: StatisticalIntelligenceResult) -> str:
    lines = [
        "# Supervisor Statistical Review Report",
        "",
        "*This report is written for a student/researcher in a supervisory context.*",
        "",
        f"**Study topic:** {r.topic}",
        f"**Research question:** {r.research_question}",
        f"**Overall statistical quality:** {r.overall_score:.1f}/100",
        "",
        "---",
        "",
        "## Summary for Student",
        "",
        r.executive_summary or "_No summary available._",
        "",
        "---",
        "",
        "## What You Did Well",
        "",
    ]
    # Collect strengths from dimensions
    all_strengths = []
    for attr in ["methodological_rigor", "sample_adequacy", "data_quality",
                 "result_validity", "construct_validity", "reporting_quality"]:
        dim = getattr(r.dimensions, attr)
        all_strengths.extend(dim.strengths[:2])
    for s in all_strengths[:8]:
        lines.append(f"- {s}")

    lines += [
        "",
        "---",
        "",
        "## Issues to Address (Before Submission)",
        "",
        "### Priority 1 — Must Fix",
        "",
    ]
    for issue in r.critical_issues + r.major_issues:
        lines.append(f"**{issue.title}**")
        lines.append(f"> {issue.description}")
        lines.append(f"> *Action required:* {issue.recommendation}")
        lines.append("")

    lines += [
        "### Priority 2 — Should Improve",
        "",
    ]
    for issue in r.moderate_issues:
        lines.append(f"- **{issue.title}**: {issue.recommendation}")

    lines += [
        "",
        "---",
        "",
        "## Additional Analyses Recommended",
        "",
    ]
    for rec in r.recommended_analyses:
        rd = rec if isinstance(rec, dict) else rec.to_dict()
        lines.append(f"- **{rd.get('analysis', '')}** ({rd.get('priority', '')}): {rd.get('rationale', '')}")
        if rd.get("software_guidance"):
            lines.append(f"  - *How:* {rd['software_guidance']}")
    return "\n".join(lines)


def _to_journal_submission(r: StatisticalIntelligenceResult) -> str:
    lines = [
        "# Statistical Methods — Journal Submission Report",
        "",
        "*Supplementary statistical documentation for journal reviewers.*",
        "",
        f"**Topic:** {r.topic}",
        f"**Design:** {r.research_design.study_type.value}",
        f"**Methods:** {', '.join(m.value for m in r.research_design.detected_methods[:5])}",
        f"**N:** {r.research_design.sample_size or 'See methods section'}",
        "",
        "---",
        "",
        "## Statistical Methods Summary",
        "",
        r.statistical_review_text or r.executive_summary,
        "",
        "---",
        "",
        "## Assumption Verification",
        "",
        "| Test | Method | Result |",
        "|---|---|---|",
    ]
    for a in r.assumption_checks:
        lines.append(f"| {a.name} | {a.method} | {a.status.value} |")

    lines += [
        "",
        "---",
        "",
        "## Validity Evidence",
        "",
        f"- Internal validity score: {r.validity_analysis.internal_validity_score:.1f}/100",
        f"- External validity score: {r.validity_analysis.external_validity_score:.1f}/100",
        f"- Construct validity score: {r.validity_analysis.construct_validity_score:.1f}/100",
    ]
    rel = r.validity_analysis.reliability
    if rel.cronbach_alpha:
        lines.append(f"- Cronbach α: {rel.cronbach_alpha:.3f}")
    if rel.ave:
        lines.append(f"- AVE: {rel.ave:.3f}")
    if rel.composite_reliability:
        lines.append(f"- Composite Reliability: {rel.composite_reliability:.3f}")

    return "\n".join(lines)


def _to_markdown(r: StatisticalIntelligenceResult) -> str:
    return _to_statistical_review(r)


def _to_latex(r: StatisticalIntelligenceResult) -> str:
    topic = _latex_escape(r.topic)
    lines = [
        r"\documentclass[12pt]{article}",
        r"\usepackage{booktabs,longtable,geometry,hyperref}",
        r"\geometry{margin=2.5cm}",
        r"\begin{document}",
        "",
        r"\title{Statistical Intelligence Review}",
        rf"\author{{SYNAPTiQ Statistical Intelligence System}}",
        r"\date{\today}",
        r"\maketitle",
        "",
        r"\section{Overview}",
        "",
        r"\begin{tabular}{ll}",
        r"\toprule",
        rf"\textbf{{Topic}} & {topic} \\",
        rf"\textbf{{Study Type}} & {_latex_escape(r.research_design.study_type.value)} \\",
        rf"\textbf{{Overall Score}} & {r.overall_score:.1f}/100 \\",
        rf"\textbf{{Verdict}} & {_latex_escape(r.overall_verdict.value)} \\",
        rf"\textbf{{Sample Size}} & {r.research_design.sample_size or 'Not reported'} \\",
        r"\bottomrule",
        r"\end{tabular}",
        "",
        r"\section{Executive Summary}",
        "",
        _latex_escape(r.executive_summary or "Not available."),
        "",
        r"\section{Quality Dimensions}",
        "",
        r"\begin{tabular}{lcc}",
        r"\toprule",
        r"\textbf{Dimension} & \textbf{Score} & \textbf{Grade} \\",
        r"\midrule",
    ]
    dims_data = [
        ("Methodological Rigour", r.dimensions.methodological_rigor),
        ("Sample Adequacy",       r.dimensions.sample_adequacy),
        ("Data Quality",          r.dimensions.data_quality),
        ("Result Validity",       r.dimensions.result_validity),
        ("Construct Validity",    r.dimensions.construct_validity),
        ("Reporting Quality",     r.dimensions.reporting_quality),
    ]
    for name, dim in dims_data:
        lines.append(rf"{_latex_escape(name)} & {dim.score:.1f} & {dim.grade} \\")
    lines += [r"\bottomrule", r"\end{tabular}", ""]

    lines += [r"\section{Critical and Major Issues}", ""]
    for issue in r.critical_issues + r.major_issues:
        lines.append(
            rf"\textbf{{{_latex_escape(issue.title)}}} "
            rf"(\textit{{{_latex_escape(issue.severity.value)}}}): "
            rf"{_latex_escape(issue.description)}"
            r" \textbf{Action:} " + _latex_escape(issue.recommendation) + r" \\"
        )

    lines += ["", r"\section{Assumption Checks}", "",
              r"\begin{tabular}{lll}", r"\toprule",
              r"\textbf{Assumption} & \textbf{Method} & \textbf{Status} \\", r"\midrule"]
    for a in r.assumption_checks:
        lines.append(
            rf"{_latex_escape(a.name)} & {_latex_escape(a.method)} & {_latex_escape(a.status.value)} \\"
        )
    lines += [r"\bottomrule", r"\end{tabular}", ""]

    lines += [
        r"\section{Publication Readiness}",
        "",
        rf"Score: {r.publication_readiness.overall_score:.1f}/100. "
        rf"Acceptance probability: {r.publication_readiness.acceptance_probability*100:.0f}\%. ",
        "",
        _latex_escape(r.publication_readiness.assessment or ""),
        "",
        r"\end{document}",
    ]
    return "\n".join(lines)


def _to_text(r: StatisticalIntelligenceResult) -> str:
    sep = "=" * 60
    lines = [
        sep,
        "STATISTICAL INTELLIGENCE REVIEW REPORT",
        sep,
        "",
        f"Topic: {r.topic}",
        f"Research Question: {r.research_question}",
        f"Study Type: {r.research_design.study_type.value}",
        f"Primary Method: {r.research_design.primary_method.value}",
        f"Sample Size: {r.research_design.sample_size or 'Not reported'}",
        f"Overall Score: {r.overall_score:.1f}/100 ({r.overall_verdict.value})",
        "",
        sep,
        "EXECUTIVE SUMMARY",
        sep,
        "",
        r.executive_summary or "Not available.",
        "",
        sep,
        "QUALITY DIMENSIONS",
        sep,
        "",
        f"Methodological Rigour:  {r.dimensions.methodological_rigor.score:.1f}/100 ({r.dimensions.methodological_rigor.grade})",
        f"Sample Adequacy:        {r.dimensions.sample_adequacy.score:.1f}/100 ({r.dimensions.sample_adequacy.grade})",
        f"Data Quality:           {r.dimensions.data_quality.score:.1f}/100 ({r.dimensions.data_quality.grade})",
        f"Result Validity:        {r.dimensions.result_validity.score:.1f}/100 ({r.dimensions.result_validity.grade})",
        f"Construct Validity:     {r.dimensions.construct_validity.score:.1f}/100 ({r.dimensions.construct_validity.grade})",
        f"Reporting Quality:      {r.dimensions.reporting_quality.score:.1f}/100 ({r.dimensions.reporting_quality.grade})",
        "",
        sep,
        f"ISSUES ({len(r.critical_issues)} critical, {len(r.major_issues)} major, {len(r.moderate_issues)} moderate)",
        sep,
        "",
    ]
    for issue in r.critical_issues + r.major_issues + r.moderate_issues:
        lines.append(f"[{issue.severity.value.upper()}] {issue.title}")
        lines.append(f"  {issue.description}")
        lines.append(f"  Action: {issue.recommendation}")
        lines.append("")

    lines += [
        sep,
        "PUBLICATION READINESS",
        sep,
        "",
        f"Score: {r.publication_readiness.overall_score:.1f}/100",
        f"Acceptance probability: {r.publication_readiness.acceptance_probability*100:.0f}%",
        f"Verdict: {r.publication_readiness.verdict.value}",
        "",
        r.publication_readiness.assessment or "",
    ]
    return "\n".join(lines)
