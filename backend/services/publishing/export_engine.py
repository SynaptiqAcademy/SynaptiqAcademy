"""Academic Publishing Intelligence — Export engine (Phase XII).

Formats: markdown, latex, text
Export types: submission_package, cover_letter, reviewer_response,
              publication_roadmap, journal_comparison, grant_readiness
"""
from __future__ import annotations

from .models import (
    CoverLetter, ExportFormat, GrantFit, JournalFitScore,
    PublicationRisk, PublicationStrategy, ReviewerResponse,
    SmartJournalMatch, SubmissionReadiness,
)


def _md_header(level: int, text: str) -> str:
    return "#" * level + " " + text + "\n\n"


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    sep = " | "
    h = sep.join(headers)
    divider = sep.join(["---"] * len(headers))
    body = "\n".join(sep.join(row) for row in rows)
    return "| " + h + " |\n| " + divider + " |\n" + "\n".join("| " + r + " |" for r in [sep.join(row) for row in rows]) + "\n\n"


def _latex_section(title: str, content: str) -> str:
    return f"\\section{{{title}}}\n{content}\n"


def _latex_table(headers: list[str], rows: list[list[str]]) -> str:
    cols = " | ".join(["l"] * len(headers))
    h = " & ".join(headers) + " \\\\"
    body = "\n".join(" & ".join(row) + " \\\\" for row in rows)
    return (
        f"\\begin{{tabular}}{{{cols}}}\n"
        f"\\hline\n{h}\n\\hline\n{body}\n\\hline\n"
        f"\\end{{tabular}}\n"
    )


# ── Export functions ──────────────────────────────────────────────────────────

def export_cover_letter(letter: CoverLetter, fmt: ExportFormat) -> str:
    if fmt == ExportFormat.LATEX:
        return (
            "\\documentclass{letter}\n\\begin{document}\n\n"
            f"\\begin{{letter}}{{{letter.journal}}}\n"
            f"\\opening{{Dear {letter.editor_title},}}\n\n"
            + letter.text.replace("\n\n", "\n\n\\medskip\n\n")
            + "\n\n\\closing{Yours sincerely,}\n\\end{letter}\n\\end{document}"
        )
    return letter.text


def export_reviewer_response(response: ReviewerResponse, fmt: ExportFormat) -> str:
    if fmt == ExportFormat.LATEX:
        sections = [
            "\\documentclass{article}\n\\usepackage{geometry}\n\\begin{document}\n",
            f"\\title{{Response to Reviewers: {response.manuscript_title}}}\n\\maketitle\n\n",
            "\\section{General Response}\n" + response.general_response + "\n\n",
        ]
        for c in response.comments:
            sections.append(
                f"\\subsection{{{c.reviewer_id} — Comment {c.comment_number}}}\n"
                f"\\textbf{{Original:}} {c.original_comment[:200]}\n\n"
                f"\\textbf{{Response:}} {c.response_text}\n\n"
                f"\\textbf{{Action:}} {c.action_taken}\n\n"
            )
        sections.append("\\end{document}")
        return "".join(sections)
    return response.full_text


def export_journal_comparison(
    matches: list[SmartJournalMatch],
    fmt: ExportFormat,
) -> str:
    headers = ["Journal", "Publisher", "Q", "IF", "Acc%", "OA", "APC", "Review Wks"]
    rows = []
    seen: set[str] = set()
    for sm in matches:
        for f in sm.fits[:3]:
            j = f.journal
            if j.name in seen:
                continue
            seen.add(j.name)
            rows.append([
                j.name[:40], j.publisher[:20], j.quartile,
                str(j.impact_factor), f"{j.acceptance_rate:.0%}",
                "Yes" if j.open_access else "No",
                f"${j.apc_usd:,}" if j.apc_usd else "Free",
                str(j.review_duration_weeks),
            ])
        if len(rows) >= 15:
            break

    if fmt == ExportFormat.LATEX:
        return (
            "\\documentclass{article}\n\\usepackage{booktabs,longtable}\n\\begin{document}\n"
            "\\section{Journal Comparison}\n"
            + _latex_table(headers, rows[:12])
            + "\n\\end{document}"
        )
    return (
        _md_header(1, "Journal Comparison")
        + _md_table(headers, rows[:12])
    )


def export_publication_roadmap(
    strategy: PublicationStrategy,
    fmt: ExportFormat,
) -> str:
    rec = strategy.recommended_option
    if not rec:
        return "No strategy available."

    if fmt == ExportFormat.LATEX:
        steps = "\n".join(f"\\item {s}" for s in rec.steps)
        return (
            "\\documentclass{article}\n\\begin{document}\n"
            f"\\section{{Publication Roadmap: {strategy.manuscript_title}}}\n"
            f"\\subsection{{Recommended Strategy: {rec.title}}}\n"
            f"{rec.description}\n\n"
            f"\\begin{{enumerate}}\n{steps}\n\\end{{enumerate}}\n"
            f"\n\\subsection{{Timeline}}\n{strategy.timeline_summary}\n"
            f"\n\\end{{document}}"
        )

    lines = [
        _md_header(1, f"Publication Roadmap: {strategy.manuscript_title}"),
        _md_header(2, f"Recommended Strategy: {rec.title}"),
        rec.description + "\n\n",
        "**Steps:**\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(rec.steps)) + "\n\n",
        f"**Timeline:** {strategy.timeline_summary}\n\n",
        f"**Backup Journals:** {', '.join(strategy.backup_journals)}\n\n",
    ]
    for opt in strategy.options[1:]:
        lines.append(_md_header(3, f"Alternative: {opt.title}"))
        lines.append(opt.description + "\n\n")
    return "".join(lines)


def export_grant_readiness(
    grants: list[GrantFit],
    fmt: ExportFormat,
) -> str:
    headers = ["Grant", "Funder", "Amount", "Topic Fit", "Elig.", "Fund Prob."]
    rows = [
        [
            g.title[:40], g.funder, f"${g.amount_usd:,}",
            f"{g.topic_fit:.0%}", f"{g.eligibility_score:.0%}",
            f"{g.funding_probability:.0%}",
        ]
        for g in grants[:10]
    ]

    if fmt == ExportFormat.LATEX:
        return (
            "\\documentclass{article}\n\\usepackage{booktabs}\n\\begin{document}\n"
            "\\section{Grant Readiness Report}\n"
            + _latex_table(headers, rows)
            + "\n\\end{document}"
        )

    parts = [_md_header(1, "Grant Readiness Report"), _md_table(headers, rows)]
    for g in grants[:5]:
        parts.append(_md_header(3, g.title))
        parts.append(f"**Funder:** {g.funder} | **Amount:** ${g.amount_usd:,}\n\n")
        if g.strengths:
            parts.append("**Strengths:** " + "; ".join(g.strengths) + "\n\n")
        if g.missing_elements:
            parts.append("**Gaps:** " + "; ".join(g.missing_elements) + "\n\n")
    return "".join(parts)


def export_submission_package(
    readiness: SubmissionReadiness,
    cover_letter: CoverLetter | None,
    fmt: ExportFormat,
) -> str:
    parts = [
        _md_header(1, f"Submission Package: {readiness.manuscript_title}"),
        _md_header(2, "Submission Readiness"),
        f"**Level:** {readiness.level.value} | **Score:** {readiness.overall_score:.1f}/100 | **Grade:** {readiness.grade}\n\n",
    ]
    if readiness.critical_blockers:
        parts.append("**Critical blockers:**\n" + "\n".join(f"- {b}" for b in readiness.critical_blockers) + "\n\n")
    if readiness.major_issues:
        parts.append("**Major issues:**\n" + "\n".join(f"- {i}" for i in readiness.major_issues) + "\n\n")
    parts.append("**Checklist:**\n" + "\n".join(readiness.submission_checklist) + "\n\n")

    if cover_letter:
        parts.append(_md_header(2, "Cover Letter"))
        parts.append(cover_letter.text + "\n\n")

    return "".join(parts)


# ── Main entry point ──────────────────────────────────────────────────────────

def export(
    export_type: ExportFormat,
    fmt: ExportFormat,
    payload: dict,
) -> str:
    if export_type == ExportFormat.COVER_LETTER:
        letter = payload.get("cover_letter")
        return export_cover_letter(letter, fmt) if letter else "No cover letter provided."

    if export_type == ExportFormat.REVIEWER_RESPONSE:
        resp = payload.get("reviewer_response")
        return export_reviewer_response(resp, fmt) if resp else "No reviewer response provided."

    if export_type == ExportFormat.JOURNAL_COMPARISON:
        return export_journal_comparison(payload.get("matches", []), fmt)

    if export_type == ExportFormat.PUBLICATION_ROADMAP:
        strategy = payload.get("strategy")
        return export_publication_roadmap(strategy, fmt) if strategy else "No strategy provided."

    if export_type == ExportFormat.GRANT_READINESS:
        return export_grant_readiness(payload.get("grants", []), fmt)

    if export_type == ExportFormat.SUBMISSION_PACKAGE:
        return export_submission_package(
            payload.get("readiness"), payload.get("cover_letter"), fmt
        )

    return "Export type not supported."
