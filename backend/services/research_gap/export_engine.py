"""Export engine for Research Gap Intelligence.

Supports: Markdown, LaTeX, CSV, Grant Proposal Outline,
Research Proposal Outline, Doctoral Proposal Outline, Text.
"""
from __future__ import annotations

import csv
import io
import re
from datetime import datetime

from .models import GapAnalysisResult, ExportFormat, DetectedGap, GapSeverity


def export_result(
    result: GapAnalysisResult,
    fmt: ExportFormat,
) -> tuple[str, str, str]:
    """Return (content, filename, content_type) for the given format."""
    slug = _slugify(result.topic)
    dt = datetime.now().strftime("%Y%m%d")

    if fmt == ExportFormat.MARKDOWN:
        return _to_markdown(result), f"gap_analysis_{slug}_{dt}.md", "text/markdown"
    if fmt == ExportFormat.LATEX:
        return _to_latex(result), f"gap_analysis_{slug}_{dt}.tex", "application/x-latex"
    if fmt == ExportFormat.CSV:
        return _to_csv(result), f"gap_analysis_{slug}_{dt}.csv", "text/csv"
    if fmt == ExportFormat.GRANT_OUTLINE:
        return _to_grant_outline(result), f"grant_outline_{slug}_{dt}.md", "text/markdown"
    if fmt == ExportFormat.RESEARCH_PROPOSAL:
        return _to_research_proposal(result), f"research_proposal_{slug}_{dt}.md", "text/markdown"
    if fmt == ExportFormat.DOCTORAL_PROPOSAL:
        return _to_doctoral_proposal(result), f"doctoral_proposal_{slug}_{dt}.md", "text/markdown"
    # Default: plain text
    return _to_text(result), f"gap_analysis_{slug}_{dt}.txt", "text/plain"


# ── Markdown ──────────────────────────────────────────────────────────────────

def _to_markdown(result: GapAnalysisResult) -> str:
    lines: list[str] = []
    lines.append(f"# Research Gap Intelligence Report\n")
    lines.append(f"**Topic:** {result.topic}")
    lines.append(f"**Analysis Depth:** {result.analysis_depth.value}")
    lines.append(f"**Generated:** {result.created_at[:10]}")
    lines.append(f"**Total Gaps Detected:** {result.total_gaps}")
    lines.append(f"**Field Opportunity Score:** {result.field_opportunity_score:.2f}")
    lines.append(f"**Field Novelty Index:** {result.field_novelty_index:.2f}\n")

    if result.topic_overview:
        lines.append("## Field Overview\n")
        lines.append(result.topic_overview.get("summary", ""))
        lines.append(f"\n*Maturity:* {result.topic_overview.get('maturity_level', 'N/A')}")
        lines.append(f"*Publication Density:* {result.topic_overview.get('publication_density', 'N/A')}\n")

    if result.research_consensus:
        lines.append("## Research Consensus\n")
        for c in result.research_consensus:
            lines.append(f"- {c}")
        lines.append("")

    if result.research_disagreements:
        lines.append("## Research Disagreements\n")
        for d in result.research_disagreements:
            lines.append(f"- {d}")
        lines.append("")

    lines.append("## Detected Research Gaps\n")
    for i, g in enumerate(result.detected_gaps, 1):
        lines.append(f"### {i}. [{g.gap_type.value.replace('_', ' ').title()}] {g.title}")
        lines.append(f"**Severity:** {g.severity.value.upper()} | "
                     f"**Overall Score:** {g.opportunity_score.overall_score:.2f} | "
                     f"**Confidence:** {g.confidence_score:.0%}")
        lines.append(f"\n{g.description}\n")
        lines.append(f"**Why This Gap Exists:** {g.why_gap_exists}\n")

        lines.append("**Opportunity Scores:**")
        os = g.opportunity_score
        lines.append(f"- Novelty: {os.novelty_score:.2f} | "
                     f"Publication Probability: {os.publication_probability:.2f} | "
                     f"Funding Potential: {os.funding_potential:.2f}")
        lines.append(f"- Research Impact: {os.research_impact:.2f} | "
                     f"Feasibility: {os.feasibility_score:.2f} | "
                     f"Citation Potential: {os.citation_potential:.2f}\n")

        if g.supporting_evidence:
            lines.append("**Supporting Evidence:**")
            for e in g.supporting_evidence[:3]:
                lines.append(f"- {e}")
            lines.append("")

        if g.research_questions:
            lines.append("**Research Questions:**")
            for rq in g.research_questions[:2]:
                lines.append(f"1. {rq.question}")
            lines.append("")

        if g.recommended_next_steps:
            lines.append("**Recommended Next Steps:**")
            for step in g.recommended_next_steps[:3]:
                lines.append(f"- {step}")
            lines.append("")

        lines.append("---\n")

    if result.competitive_landscape:
        cl = result.competitive_landscape
        lines.append("## Competitive Landscape\n")
        if cl.leading_journals:
            lines.append(f"**Leading Journals:** {', '.join(cl.leading_journals[:5])}")
        if cl.emerging_topics:
            lines.append(f"**Emerging Topics:** {', '.join(cl.emerging_topics[:5])}")
        if cl.opportunity_whitespace:
            lines.append(f"**Opportunity Whitespace:** {', '.join(cl.opportunity_whitespace[:4])}")
        lines.append("")

    return "\n".join(lines)


# ── LaTeX ─────────────────────────────────────────────────────────────────────

def _to_latex(result: GapAnalysisResult) -> str:
    esc = _latex_escape
    lines = [
        r"\documentclass[12pt]{article}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage[T1]{fontenc}",
        r"\usepackage{geometry}",
        r"\geometry{margin=2.5cm}",
        r"\usepackage{booktabs}",
        r"\usepackage{hyperref}",
        r"\title{Research Gap Intelligence Report: " + esc(result.topic) + r"}",
        r"\date{" + esc(result.created_at[:10]) + r"}",
        r"\begin{document}",
        r"\maketitle",
        r"\tableofcontents",
        r"\newpage",
        "",
        r"\section{Field Overview}",
        esc(result.topic_overview.get("summary", "")),
        "",
        r"\subsection{Key Metrics}",
        r"\begin{itemize}",
        r"  \item Total Gaps Detected: " + str(result.total_gaps),
        r"  \item Field Opportunity Score: " + f"{result.field_opportunity_score:.2f}",
        r"  \item Field Novelty Index: " + f"{result.field_novelty_index:.2f}",
        r"  \item Analysis Depth: " + esc(result.analysis_depth.value),
        r"\end{itemize}",
        "",
        r"\section{Detected Research Gaps}",
    ]

    for i, g in enumerate(result.detected_gaps, 1):
        lines.append(r"\subsection{" + esc(f"{i}. {g.title}") + r"}")
        lines.append(r"\textbf{Type:} " + esc(g.gap_type.value) + r" \quad "
                     r"\textbf{Severity:} " + esc(g.severity.value) + r" \quad "
                     r"\textbf{Score:} " + f"{g.opportunity_score.overall_score:.2f}")
        lines.append("")
        lines.append(esc(g.description))
        lines.append("")
        lines.append(r"\textbf{Why this gap exists:} " + esc(g.why_gap_exists))
        lines.append("")
        if g.research_questions:
            lines.append(r"\begin{enumerate}")
            for rq in g.research_questions[:2]:
                lines.append(r"  \item " + esc(rq.question))
            lines.append(r"\end{enumerate}")
        lines.append("")

    lines += [
        r"\section{Competitive Landscape}",
        esc(result.competitive_landscape.field_growth_rate),
        r"",
        r"\end{document}",
    ]
    return "\n".join(lines)


def _latex_escape(text: str) -> str:
    for char, repl in [
        ("\\", r"\textbackslash{}"),
        ("&", r"\&"), ("%", r"\%"), ("$", r"\$"),
        ("#", r"\#"), ("_", r"\_"), ("{", r"\{"), ("}", r"\}"),
        ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}"),
    ]:
        text = text.replace(char, repl)
    return text


# ── CSV ───────────────────────────────────────────────────────────────────────

def _to_csv(result: GapAnalysisResult) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=[
        "gap_id", "gap_type", "title", "severity", "confidence_score",
        "novelty_score", "feasibility_score", "publication_probability",
        "funding_potential", "research_impact", "citation_potential",
        "interdisciplinary_potential", "commercialization_potential", "overall_score",
        "competition_level", "detected_by", "description",
    ])
    writer.writeheader()
    for g in result.detected_gaps:
        os = g.opportunity_score
        writer.writerow({
            "gap_id": g.gap_id,
            "gap_type": g.gap_type.value,
            "title": g.title,
            "severity": g.severity.value,
            "confidence_score": round(g.confidence_score, 3),
            "novelty_score": round(os.novelty_score, 3),
            "feasibility_score": round(os.feasibility_score, 3),
            "publication_probability": round(os.publication_probability, 3),
            "funding_potential": round(os.funding_potential, 3),
            "research_impact": round(os.research_impact, 3),
            "citation_potential": round(os.citation_potential, 3),
            "interdisciplinary_potential": round(os.interdisciplinary_potential, 3),
            "commercialization_potential": round(os.commercialization_potential, 3),
            "overall_score": round(os.overall_score, 3),
            "competition_level": g.competition_level.value,
            "detected_by": g.detected_by,
            "description": g.description[:200],
        })
    return buf.getvalue()


# ── Grant Proposal Outline ────────────────────────────────────────────────────

def _to_grant_outline(result: GapAnalysisResult) -> str:
    top_gap = result.detected_gaps[0] if result.detected_gaps else None
    top_rq = result.priority_research_questions[0] if result.priority_research_questions else None

    lines = [
        f"# Grant Proposal Outline",
        f"## {result.topic}",
        f"*Generated by Synaptiq Research Gap Intelligence — {result.created_at[:10]}*\n",

        "## 1. Project Title",
        f"*[Derive from the primary gap: {top_gap.title if top_gap else 'TBD'}]*\n",

        "## 2. Executive Summary / Abstract",
        "Provide a 200-300 word summary covering: the problem, the proposed approach, "
        "the expected contribution, and the team's qualifications.\n",

        "## 3. Problem Statement and Research Gap",
        result.topic_overview.get("summary", ""),
        "",
    ]

    if top_gap:
        lines.append(f"**Primary Gap:** {top_gap.title}")
        lines.append(f"**Why It Exists:** {top_gap.why_gap_exists}\n")
        if top_gap.supporting_evidence:
            lines.append("**Supporting Evidence:**")
            for e in top_gap.supporting_evidence[:3]:
                lines.append(f"- {e}")
        lines.append("")

    if top_rq:
        lines += [
            "## 4. Research Questions and Objectives",
            f"**Primary Research Question:** {top_rq.question}",
            "",
            "**Research Objectives:**",
        ]
        for obj in top_rq.research_objectives:
            lines.append(f"- {obj}")
        lines.append("")
        if top_rq.hypotheses:
            lines.append("**Hypotheses:**")
            for h in top_rq.hypotheses:
                lines.append(f"- {h}")
            lines.append("")

    if top_gap and top_gap.methodology_recommendation:
        m = top_gap.methodology_recommendation
        lines += [
            "## 5. Methodology",
            f"**Research Design:** {m.research_design}",
            f"**Sampling Strategy:** {m.sampling_strategy}",
        ]
        if m.data_collection:
            lines.append(f"**Data Collection:** {', '.join(m.data_collection)}")
        if m.analysis_methods:
            lines.append(f"**Analysis Methods:** {', '.join(m.analysis_methods)}")
        lines.append(f"**Rationale:** {m.rationale}\n")

    lines += [
        "## 6. Expected Contribution and Impact",
        top_gap.expected_contribution if top_gap else "[Describe the scientific contribution]",
        "",
        "## 7. Work Plan and Timeline",
    ]
    if result.research_roadmap:
        for phase in result.research_roadmap[:4]:
            lines.append(f"**Phase {phase.get('phase', '?')}: {phase.get('title', '')} "
                         f"({phase.get('duration', '')})**")
            lines.append(phase.get("description", ""))
            for output in phase.get("outputs", []):
                lines.append(f"- Output: {output}")
            lines.append("")
    else:
        lines.append("[Insert work package timeline here]")

    lines += [
        "",
        "## 8. Budget Justification",
        "- Personnel: [Lead researcher, PhD students, research assistant]",
        "- Equipment: [Data collection tools, software licenses]",
        "- Dissemination: [Conference attendance, open-access publication fees]",
        "- Indirect costs: [Institutional overhead]\n",

        "## 9. Team and Expertise",
        "[Describe team qualifications and prior work in this area]\n",

        "## 10. Ethical Considerations",
        "[Describe IRB/ethics approval plan, data protection, informed consent]\n",

        "## 11. References",
        "[Add references to key works identified in the gap analysis]",
    ]
    return "\n".join(lines)


# ── Research Proposal Outline ──────────────────────────────────────────────────

def _to_research_proposal(result: GapAnalysisResult) -> str:
    top_gap = result.detected_gaps[0] if result.detected_gaps else None
    lines = [
        f"# Research Proposal",
        f"## {result.topic}",
        f"*Synaptiq Research Gap Intelligence — {result.created_at[:10]}*\n",
        "## 1. Introduction and Background",
        result.topic_overview.get("summary", "[Provide background]"), "",
        "## 2. Literature Review Summary",
        "### 2.1 Research Consensus",
    ]
    for c in result.research_consensus[:3]:
        lines.append(f"- {c}")
    lines.append("\n### 2.2 Research Disagreements")
    for d in result.research_disagreements[:3]:
        lines.append(f"- {d}")
    lines.append("")

    lines.append("## 3. Identified Research Gaps")
    for g in result.detected_gaps[:5]:
        lines.append(f"\n### {g.gap_type.value.replace('_', ' ').title()}: {g.title}")
        lines.append(g.description)
        lines.append(f"*Why it exists:* {g.why_gap_exists}")

    if top_gap:
        m = top_gap.methodology_recommendation
        lines += [
            "\n## 4. Proposed Methodology",
            f"**Design:** {m.research_design}",
            f"**Sampling:** {m.sampling_strategy}",
            f"**Analysis:** {', '.join(m.analysis_methods[:3])}",
            f"**Rationale:** {m.rationale}\n",
        ]

    lines += [
        "## 5. Expected Outcomes",
        top_gap.expected_contribution if top_gap else "[Outcomes]",
        "\n## 6. Research Timeline",
    ]
    for phase in result.research_roadmap[:4]:
        lines.append(f"- Phase {phase.get('phase', '?')}: {phase.get('title', '')} — {phase.get('duration', '')}")

    lines.append("\n## 7. References\n[Add bibliography here]")
    return "\n".join(lines)


# ── Doctoral Proposal Outline ──────────────────────────────────────────────────

def _to_doctoral_proposal(result: GapAnalysisResult) -> str:
    lines = [
        f"# Doctoral Research Proposal",
        f"## {result.topic}",
        f"*Synaptiq Research Gap Intelligence — {result.created_at[:10]}*\n",
        "## Chapter 1: Introduction",
        "### 1.1 Research Background",
        result.topic_overview.get("summary", "[Provide research background]"),
        "\n### 1.2 Research Problem",
    ]
    for g in result.detected_gaps[:3]:
        lines.append(f"- **{g.gap_type.value.replace('_', ' ').title()} Gap:** {g.title}")
    lines.append("")

    if result.priority_research_questions:
        rq = result.priority_research_questions[0]
        lines += [
            "### 1.3 Primary Research Question",
            rq.question,
            "\n### 1.4 Research Objectives",
        ]
        for obj in rq.research_objectives:
            lines.append(f"1. {obj}")
        lines.append("\n### 1.5 Research Aims")
        for aim in rq.research_aims:
            lines.append(f"- {aim}")

    lines += [
        "\n### 1.6 Research Significance",
        result.detected_gaps[0].expected_contribution if result.detected_gaps else "[Significance]",

        "\n## Chapter 2: Literature Review",
        "### 2.1 Theoretical Foundations",
        "[Develop from theoretical gaps identified above]",
        "\n### 2.2 Empirical Evidence Review",
        "[Develop from empirical and methodological gaps identified above]",
        "\n### 2.3 Research Gaps Summary",
    ]
    for g in result.detected_gaps[:5]:
        lines.append(f"- {g.title}: {g.description[:100]}")

    top_gap = result.detected_gaps[0] if result.detected_gaps else None
    if top_gap:
        m = top_gap.methodology_recommendation
        lines += [
            "\n## Chapter 3: Research Methodology",
            f"### 3.1 Research Philosophy and Design",
            f"**Design:** {m.research_design}",
            f"**Rationale:** {m.rationale}",
            f"\n### 3.2 Data Collection",
            *[f"- {dc}" for dc in m.data_collection],
            f"\n### 3.3 Data Analysis",
            *[f"- {am}" for am in m.analysis_methods],
            f"\n### 3.4 Validity and Reliability",
            "[Describe triangulation, member checking, or confirmatory factor analysis as appropriate]",
            f"\n### 3.5 Ethical Considerations",
            "[Ethics approval process, informed consent, data protection (GDPR/HIPAA as applicable)]",
        ]

    lines += [
        "\n## Chapter 4: Research Timeline (3-Year Plan)",
    ]
    yr_phases = [
        ("Year 1", "Literature review, research design, ethics approval, pilot study"),
        ("Year 2", "Data collection, primary analysis, conference presentations"),
        ("Year 3", "Advanced analysis, thesis writing, journal submissions, defence"),
    ]
    for yr, desc in yr_phases:
        lines.append(f"- **{yr}:** {desc}")

    lines += [
        "\n## Chapter 5: Contribution to Knowledge",
        top_gap.expected_contribution if top_gap else "[Expected contribution]",
        "\n## References\n[Bibliography to be completed]",
    ]
    return "\n".join(lines)


# ── Plain text ────────────────────────────────────────────────────────────────

def _to_text(result: GapAnalysisResult) -> str:
    md = _to_markdown(result)
    text = re.sub(r"#{1,6}\s*", "", md)
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"\*(.+?)\*", r"\1", text)
    text = re.sub(r"---+\n?", "\n", text)
    return text


# ── Helpers ────────────────────────────────────────────────────────────────────

def _slugify(text: str) -> str:
    text = text.lower().replace(" ", "_")
    return re.sub(r"[^a-z0-9_]", "", text)[:40]
