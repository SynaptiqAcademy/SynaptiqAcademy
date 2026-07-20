"""Export engine — Phase IX.

Generates 8 export formats from a ManuscriptIntelligenceResult:
  peer_review, editorial_report, supervisor_report, revision_checklist,
  publication_readiness, markdown, latex, text
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from .models import ManuscriptIntelligenceResult, ExportFormat


def export_result(
    result: ManuscriptIntelligenceResult,
    fmt: ExportFormat,
) -> tuple[str, str, str]:
    """
    Returns (content, filename, content_type).
    All content is UTF-8 text.
    """
    title_slug = re.sub(r"[^\w\-]", "_", result.title[:40] or result.filename[:30]).strip("_")
    ts = datetime.now(timezone.utc).strftime("%Y%m%d")

    dispatch = {
        ExportFormat.PEER_REVIEW: (_to_peer_review, f"peer_review_{title_slug}_{ts}.md", "text/markdown"),
        ExportFormat.EDITORIAL_REPORT: (_to_editorial_report, f"editorial_{title_slug}_{ts}.md", "text/markdown"),
        ExportFormat.SUPERVISOR_REPORT: (_to_supervisor_report, f"supervisor_{title_slug}_{ts}.md", "text/markdown"),
        ExportFormat.REVISION_CHECKLIST: (_to_revision_checklist, f"revision_checklist_{title_slug}_{ts}.md", "text/markdown"),
        ExportFormat.PUBLICATION_READINESS: (_to_publication_readiness, f"pub_readiness_{title_slug}_{ts}.md", "text/markdown"),
        ExportFormat.MARKDOWN: (_to_markdown, f"manuscript_review_{title_slug}_{ts}.md", "text/markdown"),
        ExportFormat.LATEX: (_to_latex, f"manuscript_review_{title_slug}_{ts}.tex", "text/x-latex"),
        ExportFormat.TEXT: (_to_text, f"manuscript_review_{title_slug}_{ts}.txt", "text/plain"),
    }

    fn, filename, ct = dispatch[fmt]
    content = fn(result)
    return content, filename, ct


# ── Peer review ───────────────────────────────────────────────────────────────

def _to_peer_review(r: ManuscriptIntelligenceResult) -> str:
    lines = [
        f"# Peer Review Report",
        f"**Manuscript:** {r.title or r.filename}",
        f"**Review Date:** {r.created_at[:10]}",
        f"**Recommendation:** {r.recommendation.value.replace('_', ' ').title()}",
        f"**Overall Score:** {r.overall_score:.0f}/100",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        r.executive_summary or "_No executive summary available._",
        "",
        "---",
        "",
        "## Detailed Review",
        "",
        r.peer_review_text or "_Full peer review text not generated for this review depth._",
        "",
        "---",
        "",
        "## Review Dimensions",
        "",
    ]
    d = r.review_dimensions
    for label, dim in [
        ("Scientific Rigor", d.scientific_rigor),
        ("Originality & Novelty", d.originality),
        ("Methodological Soundness", d.methodological_soundness),
        ("Clarity & Writing Quality", d.clarity),
        ("Literature Coverage", d.literature_coverage),
        ("Scientific Contribution", d.contribution),
        ("Statistical Validity", d.statistical_validity),
        ("Ethical Compliance", d.ethical_compliance),
    ]:
        lines += [
            f"### {label} — {dim.score:.0f}/100 ({dim.grade})",
            "",
            f"*{dim.rationale}*",
            "",
        ]
        if dim.strengths:
            lines += ["**Strengths:**"] + [f"- {s}" for s in dim.strengths] + [""]
        if dim.weaknesses:
            lines += ["**Weaknesses:**"] + [f"- {w}" for w in dim.weaknesses] + [""]

    lines += ["---", "", "## Issues Identified", ""]

    for severity, issues, label in [
        ("critical", r.critical_issues, "Critical Issues"),
        ("major", r.major_issues, "Major Issues"),
        ("minor", r.minor_issues, "Minor Issues"),
        ("suggestion", r.suggestions, "Suggestions"),
    ]:
        if issues:
            lines += [f"### {label}", ""]
            for i in issues:
                lines += [
                    f"**{i.title}** *(Section: {i.section})*",
                    "",
                    i.description,
                    "",
                    f"*Recommendation: {i.recommendation}*",
                    "",
                ]

    lines += [
        "---",
        "",
        "## Revision Checklist",
        "",
    ]
    for phase in r.revision_roadmap:
        lines += [
            f"### Phase {phase.get('phase', '')}: {phase.get('title', '')}",
            f"*Priority: {phase.get('priority', '')} | Effort: {phase.get('estimated_effort', '')}*",
            "",
        ]
        for action in phase.get("actions", []):
            lines.append(f"- [ ] {action}")
        lines.append("")

    return "\n".join(lines)


# ── Editorial report ──────────────────────────────────────────────────────────

def _to_editorial_report(r: ManuscriptIntelligenceResult) -> str:
    pr = r.publication_readiness
    lines = [
        f"# Editorial Assessment Report",
        f"**Manuscript Title:** {r.title or r.filename}",
        f"**Review Date:** {r.created_at[:10]}",
        f"**Editor Decision:** {r.recommendation.value.replace('_', ' ').title()}",
        f"**Overall Quality Score:** {r.overall_score:.0f}/100",
        f"**Acceptance Probability:** {pr.acceptance_probability:.0%}",
        f"**Desk Rejection Risk:** {pr.desk_rejection_risk:.0%}",
        f"**Estimated Revision Effort:** {pr.estimated_revision_effort}",
        f"**Target Tier:** {pr.target_tier}",
        "",
        "---",
        "",
        "## Editorial Assessment",
        "",
        r.editorial_assessment or "_Editorial assessment not available._",
        "",
        "---",
        "",
        "## Quality Overview",
        "",
        f"| Dimension | Score | Grade |",
        f"|-----------|-------|-------|",
    ]
    d = r.review_dimensions
    for label, dim in [
        ("Scientific Rigor", d.scientific_rigor),
        ("Originality", d.originality),
        ("Methodology", d.methodological_soundness),
        ("Writing Quality", d.clarity),
        ("Literature", d.literature_coverage),
        ("Contribution", d.contribution),
        ("Statistics", d.statistical_validity),
        ("Ethics", d.ethical_compliance),
    ]:
        lines.append(f"| {label} | {dim.score:.0f}/100 | {dim.grade} |")

    lines += [
        "",
        "---",
        "",
        "## Issue Summary",
        "",
        f"- **Critical Issues:** {len(r.critical_issues)}",
        f"- **Major Issues:** {len(r.major_issues)}",
        f"- **Minor Issues:** {len(r.minor_issues)}",
        f"- **Suggestions:** {len(r.suggestions)}",
        "",
        "---",
        "",
        "## Journal Recommendations",
        "",
        f"| Journal | Quartile | Scope Match | Acceptance Prob. | Open Access |",
        f"|---------|----------|-------------|-------------------|-------------|",
    ]
    for j in r.journal_matches:
        lines.append(
            f"| {j.name} | {j.quartile} | {j.scope_match:.0%} | "
            f"{j.acceptance_probability:.0%} | {'Yes' if j.open_access else 'No'} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Major Concerns for Authors",
        "",
    ]
    for issue in r.critical_issues + r.major_issues:
        lines += [f"- **{issue.title}**: {issue.recommendation}"]

    return "\n".join(lines)


# ── Supervisor report ─────────────────────────────────────────────────────────

def _to_supervisor_report(r: ManuscriptIntelligenceResult) -> str:
    lines = [
        f"# Doctoral Supervisor Review Report",
        f"**Manuscript:** {r.title or r.filename}",
        f"**Review Date:** {r.created_at[:10]}",
        f"**Overall Assessment:** {r.recommendation.value.replace('_', ' ').title()}",
        f"**Score:** {r.overall_score:.0f}/100",
        "",
        "---",
        "",
        "## Overall Feedback",
        "",
        r.executive_summary or "_Not available._",
        "",
        "---",
        "",
        "## Scientific Quality",
        "",
        f"**Scientific Rigor:** {r.review_dimensions.scientific_rigor.score:.0f}/100 ({r.review_dimensions.scientific_rigor.grade})",
        "",
        r.review_dimensions.scientific_rigor.rationale or "",
        "",
        f"**Originality & Contribution:** {r.review_dimensions.originality.score:.0f}/100 ({r.review_dimensions.originality.grade})",
        "",
        r.review_dimensions.originality.rationale or "",
        "",
        "---",
        "",
        "## Methodological Review",
        "",
        f"**Methodology Score:** {r.review_dimensions.methodological_soundness.score:.0f}/100 ({r.review_dimensions.methodological_soundness.grade})",
        "",
        r.review_dimensions.methodological_soundness.rationale or "",
        "",
        "---",
        "",
        "## Literature Review",
        "",
        f"**Literature Score:** {r.review_dimensions.literature_coverage.score:.0f}/100 ({r.review_dimensions.literature_coverage.grade})",
        "",
        f"- References: ~{r.literature_metrics.reference_count}",
        f"- Year range: {r.literature_metrics.year_range}",
        f"- Recent (last 5 years): {r.literature_metrics.recent_ratio:.0%}",
        "",
        "---",
        "",
        "## Writing Quality",
        "",
        f"**Clarity Score:** {r.review_dimensions.clarity.score:.0f}/100 ({r.review_dimensions.clarity.grade})",
        "",
        f"- Word count: {r.word_count:,}",
        f"- Avg sentence length: {r.writing_metrics.avg_sentence_length:.0f} words",
        f"- Passive voice: {r.writing_metrics.passive_voice_ratio:.0%}",
        f"- Readability: {r.writing_metrics.readability_score:.0f}",
        "",
        "---",
        "",
        "## Priority Actions Before Submission",
        "",
    ]
    for i, phase in enumerate(r.revision_roadmap[:3], 1):
        lines += [f"### {i}. {phase.get('title', '')}"]
        for action in phase.get("actions", [])[:5]:
            lines.append(f"- {action}")
        lines.append("")

    lines += [
        "---",
        "",
        "## Recommended Journals",
        "",
    ]
    for j in r.journal_matches[:3]:
        lines.append(
            f"- **{j.name}** ({j.quartile}, IF={j.impact_factor or 'N/A'}): "
            f"{j.submission_notes}"
        )

    return "\n".join(lines)


# ── Revision checklist ────────────────────────────────────────────────────────

def _to_revision_checklist(r: ManuscriptIntelligenceResult) -> str:
    lines = [
        f"# Revision Checklist",
        f"**Manuscript:** {r.title or r.filename}",
        f"**Generated:** {r.created_at[:10]}",
        f"**Total Issues:** {len(r.critical_issues) + len(r.major_issues) + len(r.minor_issues)}",
        "",
        "---",
        "",
        "## CRITICAL — Must Fix (will cause rejection)",
        "",
    ]
    for issue in r.critical_issues:
        lines += [
            f"- [ ] **{issue.title}** *(Section: {issue.section})*",
            f"  - {issue.recommendation}",
        ]
    if not r.critical_issues:
        lines.append("- [x] No critical issues identified")

    lines += ["", "## MAJOR — Required for Acceptance", ""]
    for issue in r.major_issues:
        lines += [
            f"- [ ] **{issue.title}** *(Section: {issue.section})*",
            f"  - {issue.recommendation}",
        ]
    if not r.major_issues:
        lines.append("- [x] No major issues identified")

    lines += ["", "## MINOR — Should Fix", ""]
    for issue in r.minor_issues:
        lines += [f"- [ ] {issue.title} ({issue.section})"]
    if not r.minor_issues:
        lines.append("- [x] No minor issues identified")

    lines += ["", "## SUGGESTIONS — Consider", ""]
    for sug in r.suggestions:
        lines += [f"- [ ] {sug.title}"]
    if not r.suggestions:
        lines.append("- [x] No suggestions")

    lines += [
        "",
        "---",
        "",
        "## Revision Phases",
        "",
    ]
    for phase in r.revision_roadmap:
        lines += [
            f"### Phase {phase.get('phase', '')}: {phase.get('title', '')}",
            f"*Estimated effort: {phase.get('estimated_effort', 'TBD')}*",
            "",
        ]
        for action in phase.get("actions", []):
            lines.append(f"- [ ] {action}")
        lines.append("")

    return "\n".join(lines)


# ── Publication readiness report ──────────────────────────────────────────────

def _to_publication_readiness(r: ManuscriptIntelligenceResult) -> str:
    pr = r.publication_readiness
    lines = [
        f"# Publication Readiness Report",
        f"**Manuscript:** {r.title or r.filename}",
        f"**Generated:** {r.created_at[:10]}",
        "",
        "---",
        "",
        "## Publication Readiness Score",
        "",
        f"**Overall Score:** {pr.overall_score:.0f}/100",
        f"**Recommendation:** {r.recommendation.value.replace('_', ' ').title()}",
        f"**Target Tier:** {pr.target_tier}",
        "",
        "| Outcome | Probability |",
        "|---------|------------|",
        f"| Acceptance | {pr.acceptance_probability:.0%} |",
        f"| Minor Revision | {pr.minor_revision_probability:.0%} |",
        f"| Major Revision | {pr.major_revision_probability:.0%} |",
        f"| Desk Rejection | {pr.desk_rejection_risk:.0%} |",
        "",
        f"**Reviewer Difficulty:** {pr.reviewer_difficulty.replace('_', ' ').title()}",
        f"**Estimated Revision Effort:** {pr.estimated_revision_effort}",
        "",
        "---",
        "",
        "## Strengths",
        "",
    ]
    for s in pr.strengths:
        lines.append(f"- {s}")

    lines += ["", "## Barriers to Publication", ""]
    for b in pr.barriers:
        lines.append(f"- {b}")

    lines += [
        "",
        "---",
        "",
        "## Journal Recommendations",
        "",
    ]
    for j in r.journal_matches:
        lines += [
            f"### {j.name} ({j.quartile})",
            f"- **Publisher:** {j.publisher}",
            f"- **Impact Factor:** {j.impact_factor or 'Not listed'}",
            f"- **Scope Match:** {j.scope_match:.0%}",
            f"- **Acceptance Probability:** {j.acceptance_probability:.0%}",
            f"- **Open Access:** {'Yes' if j.open_access else 'No'}",
            f"- **Submission Notes:** {j.submission_notes}",
            "",
        ]

    return "\n".join(lines)


# ── Markdown (full report) ────────────────────────────────────────────────────

def _to_markdown(r: ManuscriptIntelligenceResult) -> str:
    return _to_peer_review(r)   # Full peer review is the Markdown format


# ── LaTeX ─────────────────────────────────────────────────────────────────────

def _latex_escape(s: str) -> str:
    for ch, rep in [
        ("\\", r"\textbackslash{}"), ("&", r"\&"), ("%", r"\%"),
        ("$", r"\$"), ("#", r"\#"), ("_", r"\_"), ("{", r"\{"), ("}", r"\}"),
        ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}"),
    ]:
        s = s.replace(ch, rep)
    return s


def _to_latex(r: ManuscriptIntelligenceResult) -> str:
    title = _latex_escape(r.title or r.filename)
    date = r.created_at[:10]
    lines = [
        r"\documentclass[12pt]{article}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage{booktabs}",
        r"\usepackage{longtable}",
        r"\usepackage{geometry}",
        r"\geometry{margin=2.5cm}",
        r"\usepackage{hyperref}",
        r"\title{Manuscript Review Report}",
        fr"\author{{Synaptiq Manuscript Intelligence}}",
        fr"\date{{{date}}}",
        r"\begin{document}",
        r"\maketitle",
        r"\tableofcontents",
        r"\newpage",
        "",
        r"\section{Executive Summary}",
        "",
        _latex_escape(r.executive_summary or "Not available."),
        "",
        r"\section{Review Dimensions}",
        "",
        r"\begin{tabular}{lcc}",
        r"\toprule",
        r"Dimension & Score & Grade \\",
        r"\midrule",
    ]
    d = r.review_dimensions
    for label, dim in [
        ("Scientific Rigor", d.scientific_rigor),
        ("Originality", d.originality),
        ("Methodology", d.methodological_soundness),
        ("Writing Quality", d.clarity),
        ("Literature", d.literature_coverage),
        ("Contribution", d.contribution),
        ("Statistics", d.statistical_validity),
        ("Ethics", d.ethical_compliance),
    ]:
        lines.append(fr"{_latex_escape(label)} & {dim.score:.0f}/100 & {dim.grade} \\")
    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        "",
        r"\section{Issues}",
        "",
    ]
    for severity, issues, label in [
        ("critical", r.critical_issues, "Critical"),
        ("major", r.major_issues, "Major"),
        ("minor", r.minor_issues, "Minor"),
    ]:
        if issues:
            lines.append(fr"\subsection{{{label} Issues}}")
            lines.append(r"\begin{itemize}")
            for issue in issues:
                lines.append(fr"\item \textbf{{{_latex_escape(issue.title)}}}: {_latex_escape(issue.recommendation)}")
            lines.append(r"\end{itemize}")
            lines.append("")

    lines += [
        r"\section{Revision Roadmap}",
        "",
        r"\begin{enumerate}",
    ]
    for phase in r.revision_roadmap:
        lines.append(fr"\item \textbf{{{_latex_escape(phase.get('title', ''))}}} ({_latex_escape(phase.get('estimated_effort', ''))})")
    lines += [r"\end{enumerate}", "", r"\end{document}"]

    return "\n".join(lines)


# ── Plain text ────────────────────────────────────────────────────────────────

def _to_text(r: ManuscriptIntelligenceResult) -> str:
    lines = [
        "MANUSCRIPT REVIEW REPORT",
        "=" * 60,
        f"Manuscript: {r.title or r.filename}",
        f"Date: {r.created_at[:10]}",
        f"Recommendation: {r.recommendation.value.replace('_', ' ').upper()}",
        f"Overall Score: {r.overall_score:.0f}/100",
        "",
        "EXECUTIVE SUMMARY",
        "-" * 40,
        r.executive_summary or "Not available.",
        "",
        "REVIEW DIMENSIONS",
        "-" * 40,
    ]
    d = r.review_dimensions
    for label, dim in [
        ("Scientific Rigor", d.scientific_rigor),
        ("Originality", d.originality),
        ("Methodology", d.methodological_soundness),
        ("Writing Quality", d.clarity),
        ("Literature", d.literature_coverage),
        ("Contribution", d.contribution),
        ("Statistics", d.statistical_validity),
        ("Ethics", d.ethical_compliance),
    ]:
        lines.append(f"{label}: {dim.score:.0f}/100 ({dim.grade}) — {dim.rationale}")

    lines += [
        "",
        "CRITICAL ISSUES",
        "-" * 40,
    ]
    for issue in r.critical_issues:
        lines += [f"[{issue.severity.value.upper()}] {issue.title}", f"  → {issue.recommendation}"]

    lines += ["", "MAJOR ISSUES", "-" * 40]
    for issue in r.major_issues:
        lines += [f"[MAJOR] {issue.title}", f"  → {issue.recommendation}"]

    lines += ["", "JOURNAL RECOMMENDATIONS", "-" * 40]
    for j in r.journal_matches[:3]:
        lines.append(f"• {j.name} ({j.quartile}) — {j.submission_notes}")

    return "\n".join(lines)
