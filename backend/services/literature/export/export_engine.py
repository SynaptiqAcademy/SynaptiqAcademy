"""Multi-format export engine — Markdown, LaTeX, BibTeX, RIS, CSV, Text."""
from __future__ import annotations

import csv
import io
import re
from typing import Any

from services.literature.models import ExportFormat, Paper, PaperAnalysis, ReviewSession


def export_session(
    session: ReviewSession,
    papers: list[Paper],
    analyses: list[PaperAnalysis],
    fmt: ExportFormat,
) -> tuple[str, str, str]:
    """Export a review session.

    Returns: (content, filename, content_type)
    """
    safe_title = re.sub(r"[^\w\s-]", "", session.title or "review")[:40].strip().replace(" ", "_")

    if fmt == ExportFormat.MARKDOWN:
        content = _to_markdown(session, papers, analyses)
        return content, f"{safe_title}.md", "text/markdown"

    if fmt == ExportFormat.LATEX:
        content = _to_latex(session, papers, analyses)
        return content, f"{safe_title}.tex", "application/x-tex"

    if fmt == ExportFormat.BIBTEX:
        content = _to_bibtex(papers)
        return content, f"{safe_title}.bib", "application/x-bibtex"

    if fmt == ExportFormat.RIS:
        content = _to_ris(papers)
        return content, f"{safe_title}.ris", "application/x-research-info-systems"

    if fmt == ExportFormat.CSV:
        content = _to_csv(papers, analyses)
        return content, f"{safe_title}.csv", "text/csv"

    # TEXT (default)
    content = _to_text(session, papers, analyses)
    return content, f"{safe_title}.txt", "text/plain"


# ── Markdown ──────────────────────────────────────────────────────────────────

def _to_markdown(session: ReviewSession, papers: list[Paper], analyses: list[PaperAnalysis]) -> str:
    lines: list[str] = []
    lines.append(f"# {session.title or 'Literature Review'}")
    lines.append(f"\n**Review Type:** {session.review_type.value.replace('_', ' ').title()}")
    lines.append(f"**Papers Analysed:** {len(papers)}")
    lines.append(f"**Generated:** {session.updated_at[:10]}")

    # Generated review
    if session.generated_review:
        lines.append("\n---\n")
        lines.append(session.generated_review.content)

    # Paper summaries
    lines.append("\n---\n## Paper Summaries\n")
    analysis_map = {a.paper_id: a for a in analyses}
    for p in papers:
        a = analysis_map.get(p.paper_id)
        lines.append(f"### {p.short_ref} — {p.title}")
        if p.journal:
            lines.append(f"*{p.journal}*")
        if p.doi:
            lines.append(f"DOI: {p.doi}")
        if p.abstract:
            lines.append(f"\n**Abstract:** {p.abstract[:500]}...")
        if a:
            if a.research_question:
                lines.append(f"\n**Research Question:** {a.research_question}")
            if a.methodology:
                lines.append(f"**Methodology:** {a.methodology}")
            if a.results:
                lines.append(f"**Results:** {a.results}")
            if a.limitations:
                lines.append(f"**Limitations:** {'; '.join(a.limitations[:3])}")
        lines.append("")

    # Gaps
    if session.gaps:
        lines.append("---\n## Research Gaps\n")
        for g in session.gaps[:8]:
            lines.append(f"### {g.title}")
            lines.append(f"*Type: {g.type} | Severity: {g.severity}*\n")
            lines.append(g.description)
            if g.suggested_design:
                lines.append(f"\n**Suggested approach:** {g.suggested_design}")
            lines.append("")

    # References
    lines.append("---\n## References\n")
    for p in sorted(papers, key=lambda x: (x.authors[0] if x.authors else "Unknown")):
        authors = ", ".join(p.authors[:3]) + (" et al." if len(p.authors) > 3 else "")
        doi_str = f" https://doi.org/{p.doi}" if p.doi else ""
        lines.append(f"- {authors} ({p.year}). {p.title}. *{p.journal}*.{doi_str}")

    return "\n".join(lines)


# ── LaTeX ─────────────────────────────────────────────────────────────────────

def _to_latex(session: ReviewSession, papers: list[Paper], analyses: list[PaperAnalysis]) -> str:
    title = _latex_escape(session.title or "Literature Review")
    lines: list[str] = [
        r"\documentclass[12pt,a4paper]{article}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage[T1]{fontenc}",
        r"\usepackage{hyperref}",
        r"\usepackage{natbib}",
        r"\usepackage{geometry}",
        r"\geometry{margin=2.5cm}",
        r"\title{" + title + "}",
        r"\date{\today}",
        r"\begin{document}",
        r"\maketitle",
        r"\tableofcontents",
        r"\newpage",
    ]

    if session.generated_review:
        # Convert markdown headings to LaTeX sections
        content = _md_to_latex(session.generated_review.content)
        lines.append(content)
    else:
        lines.append(r"\section{Introduction}")
        lines.append(f"This review synthesises {len(papers)} papers.")

    # Bibliography
    lines.append(r"\begin{thebibliography}{99}")
    for p in papers:
        citekey = _make_citekey(p)
        authors_str = " and ".join(_latex_escape(a) for a in p.authors[:5])
        lines.append(
            rf"\bibitem{{{citekey}}}"
            f"\n{authors_str} ({p.year}). "
            f"\\textit{{{_latex_escape(p.title)}}}. "
            f"{_latex_escape(p.journal)}."
        )
    lines.append(r"\end{thebibliography}")
    lines.append(r"\end{document}")
    return "\n".join(lines)


def _md_to_latex(text: str) -> str:
    text = re.sub(r"^## (.+)$", r"\\section{\1}", text, flags=re.MULTILINE)
    text = re.sub(r"^# (.+)$", r"\\section{\1}", text, flags=re.MULTILINE)
    text = re.sub(r"\*\*(.+?)\*\*", r"\\textbf{\1}", text)
    text = re.sub(r"\*(.+?)\*", r"\\textit{\1}", text)
    return text


def _make_citekey(p: Paper) -> str:
    author = (p.authors[0].split(",")[0].strip() if p.authors else "Unknown")
    author = re.sub(r"[^\w]", "", author)
    return f"{author}{p.year}"


def _latex_escape(text: str) -> str:
    chars = {"&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_",
             "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}",
             "^": r"\textasciicircum{}"}
    return "".join(chars.get(c, c) for c in text)


# ── BibTeX ────────────────────────────────────────────────────────────────────

def _to_bibtex(papers: list[Paper]) -> str:
    entries: list[str] = []
    seen_keys: set[str] = set()

    for p in papers:
        base_key = _make_citekey(p)
        key = base_key
        suffix = "a"
        while key in seen_keys:
            key = base_key + suffix
            suffix = chr(ord(suffix) + 1)
        seen_keys.add(key)

        entry_type = "article" if p.journal else "misc"
        lines = [f"@{entry_type}{{{key},"]
        lines.append(f'  title     = {{{p.title}}},')
        if p.authors:
            lines.append(f'  author    = {{{" and ".join(p.authors[:10])}}},')
        if p.year:
            lines.append(f'  year      = {{{p.year}}},')
        if p.journal:
            lines.append(f'  journal   = {{{p.journal}}},')
        if p.volume:
            lines.append(f'  volume    = {{{p.volume}}},')
        if p.issue:
            lines.append(f'  number    = {{{p.issue}}},')
        if p.pages:
            lines.append(f'  pages     = {{{p.pages}}},')
        if p.doi:
            lines.append(f'  doi       = {{{p.doi}}},')
        if p.url:
            lines.append(f'  url       = {{{p.url}}},')
        lines.append("}")
        entries.append("\n".join(lines))

    return "\n\n".join(entries)


# ── RIS ──────────────────────────────────────────────────────────────────────

def _to_ris(papers: list[Paper]) -> str:
    blocks: list[str] = []
    for p in papers:
        lines = ["TY  - JOUR" if p.journal else "TY  - GEN"]
        for author in p.authors[:10]:
            lines.append(f"AU  - {author}")
        lines.append(f"TI  - {p.title}")
        if p.journal:
            lines.append(f"JO  - {p.journal}")
        if p.year:
            lines.append(f"PY  - {p.year}")
        if p.volume:
            lines.append(f"VL  - {p.volume}")
        if p.issue:
            lines.append(f"IS  - {p.issue}")
        if p.pages:
            lines.append(f"SP  - {p.pages}")
        if p.doi:
            lines.append(f"DO  - {p.doi}")
        if p.url:
            lines.append(f"UR  - {p.url}")
        if p.abstract:
            lines.append(f"AB  - {p.abstract[:500]}")
        for kw in p.keywords[:10]:
            lines.append(f"KW  - {kw}")
        lines.append("ER  -")
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


# ── CSV ───────────────────────────────────────────────────────────────────────

def _to_csv(papers: list[Paper], analyses: list[PaperAnalysis]) -> str:
    analysis_map = {a.paper_id: a for a in analyses}
    buf = io.StringIO()
    headers = [
        "title", "authors", "year", "journal", "doi", "arxiv_id", "pmid",
        "citation_count", "open_access", "source",
        "research_design", "methodology", "domain", "evidence_grade",
        "has_limitations", "novelty_score",
    ]
    writer = csv.DictWriter(buf, fieldnames=headers, extrasaction="ignore")
    writer.writeheader()
    for p in papers:
        a = analysis_map.get(p.paper_id)
        row: dict[str, Any] = {
            "title": p.title,
            "authors": "; ".join(p.authors[:5]),
            "year": p.year,
            "journal": p.journal,
            "doi": p.doi,
            "arxiv_id": p.arxiv_id,
            "pmid": p.pmid,
            "citation_count": p.citation_count,
            "open_access": p.open_access,
            "source": p.source.value,
            "research_design": a.research_design if a else "",
            "methodology": a.methodology if a else "",
            "domain": a.domain if a else "",
            "evidence_grade": a.evidence_quality.grade.value if a else "",
            "has_limitations": bool(a.limitations) if a else "",
            "novelty_score": a.evidence_quality.novelty_score if a else "",
        }
        writer.writerow(row)
    return buf.getvalue()


# ── Plain Text ────────────────────────────────────────────────────────────────

def _to_text(session: ReviewSession, papers: list[Paper], analyses: list[PaperAnalysis]) -> str:
    if session.generated_review:
        # Strip markdown headings
        text = session.generated_review.content
        text = re.sub(r"^#{1,3} ", "", text, flags=re.MULTILINE)
        return text
    lines = [f"LITERATURE REVIEW: {session.title or 'Untitled'}", "=" * 60, ""]
    for p in papers:
        lines.append(f"• {p.short_ref}: {p.title}")
    return "\n".join(lines)
