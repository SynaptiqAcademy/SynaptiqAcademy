"""Academic Publishing Intelligence — Submission readiness checker (Phase XII).

15 rule-based checks across formatting, references, ethics, content, data,
and language dimensions. Returns SubmissionReadiness with level and grade.
"""
from __future__ import annotations

import re
from .models import (
    ReadinessCheck, ReadinessLevel, SubmissionReadiness, _score_to_grade,
)

# ── Compiled patterns ─────────────────────────────────────────────────────────
_ABSTRACT_RE    = re.compile(r"\babstract\b", re.IGNORECASE)
_KEYWORD_RE     = re.compile(r"\bkeyword[s]?\b", re.IGNORECASE)
_INTRO_RE       = re.compile(r"\bintroduction\b", re.IGNORECASE)
_METHODS_RE     = re.compile(r"\b(?:method[s]?|methodology|materials?\s+and\s+methods?)\b", re.IGNORECASE)
_RESULTS_RE     = re.compile(r"\bresult[s]?\b", re.IGNORECASE)
_DISCUSSION_RE  = re.compile(r"\bdiscussion\b", re.IGNORECASE)
_CONCLUSION_RE  = re.compile(r"\bconclusion[s]?\b", re.IGNORECASE)
_REFERENCES_RE  = re.compile(r"\breferences?\b", re.IGNORECASE)
_ETHICS_RE      = re.compile(r"\bethic[s]?\s*(?:statement|approval|declaration|committee|review)\b|\birb\b|\binstitutional\s+review\b", re.IGNORECASE)
_DATA_AVAIL_RE  = re.compile(r"\bdata\s+(?:availability|availability\s+statement|access(?:ibility)?)\b", re.IGNORECASE)
_AUTHOR_CONTRIB_RE = re.compile(r"\bauthor\s+contribution[s]?\b|\bcontribution[s]?\s+of\s+author[s]?\b", re.IGNORECASE)
_CONFLICT_RE    = re.compile(r"\bconflict[s]?\s+of\s+interest\b|\bcompeting\s+interest[s]?\b|\bdisclosure[s]?\b", re.IGNORECASE)
_FIGURE_RE      = re.compile(r"\bfig(?:ure)?[s]?\s*\d+\b|\bfigure\b", re.IGNORECASE)
_TABLE_RE       = re.compile(r"\btable[s]?\s*\d+\b|\btable\b", re.IGNORECASE)
_CITATION_RE    = re.compile(r"\([\w\s]+,?\s*\d{4}\)|\[\d+\]", re.IGNORECASE)
_COVER_LETTER_RE= re.compile(r"\bcover\s+letter\b|\bdear\s+editor\b|\bwe\s+herewith\b", re.IGNORECASE)
_FUNDING_RE     = re.compile(r"\bfunding\b|\backnowledgem\w+\b|\bgrant\s+(?:no|number|\#)\b", re.IGNORECASE)
_SUPPLEMENTARY_RE = re.compile(r"\bsupplementary\b|\bsupplemental\b|\bappendix\b", re.IGNORECASE)
_SPELL_ERRORS_RE = re.compile(r"\bteh\b|\brecieve\b|\boccured\b|\bseperate\b|\bdefinate\b|\bexistance\b|\bopportunites\b", re.IGNORECASE)


def _check_abstract(text: str, metadata: dict) -> ReadinessCheck:
    has = bool(_ABSTRACT_RE.search(text))
    wc = metadata.get("abstract_word_count", 0)
    if has and wc and (wc < 100 or wc > 350):
        return ReadinessCheck("Abstract length", "formatting", False, "minor",
                              f"Abstract is {wc} words; most journals require 150–300 words.",
                              "Revise abstract to 150–300 words.")
    return ReadinessCheck("Abstract present", "formatting", has, "major" if not has else "minor",
                          "Abstract found." if has else "No abstract detected.",
                          "" if has else "Add a structured abstract (Background, Objectives, Methods, Results, Conclusions).")


def _check_keywords(text: str, metadata: dict) -> ReadinessCheck:
    has = bool(_KEYWORD_RE.search(text)) or bool(metadata.get("keywords"))
    return ReadinessCheck("Keywords present", "formatting", has, "minor",
                          "Keywords found." if has else "No keywords detected.",
                          "" if has else "Add 5–8 keywords as required by most journals.")


def _check_imrad(text: str) -> ReadinessCheck:
    sections = {
        "Introduction": _INTRO_RE,
        "Methods": _METHODS_RE,
        "Results": _RESULTS_RE,
        "Discussion": _DISCUSSION_RE,
    }
    missing = [s for s, rx in sections.items() if not rx.search(text)]
    if not missing:
        return ReadinessCheck("IMRaD structure", "content", True, "major",
                              "Core IMRaD sections detected.", "")
    return ReadinessCheck("IMRaD structure", "content", False, "major",
                          f"Missing sections: {', '.join(missing)}.",
                          f"Add the missing IMRaD sections: {', '.join(missing)}.")


def _check_conclusion(text: str) -> ReadinessCheck:
    has = bool(_CONCLUSION_RE.search(text))
    return ReadinessCheck("Conclusion section", "content", has, "minor",
                          "Conclusion found." if has else "No conclusion section detected.",
                          "" if has else "Add a conclusion section summarising findings and implications.")


def _check_references(text: str, metadata: dict) -> ReadinessCheck:
    has = bool(_REFERENCES_RE.search(text))
    ref_count = metadata.get("reference_count", 0)
    if has and ref_count and ref_count < 10:
        return ReadinessCheck("Reference list", "references", False, "minor",
                              f"Only {ref_count} references detected; most journals expect 20+.",
                              "Expand the reference list.")
    if has and ref_count and ref_count > 200:
        return ReadinessCheck("Reference list", "references", False, "minor",
                              f"{ref_count} references may exceed journal limits.",
                              "Check the journal reference limit and trim if needed.")
    return ReadinessCheck("Reference list present", "references", has, "major" if not has else "minor",
                          f"Reference list found ({ref_count} references)." if has else "No reference list found.",
                          "" if has else "Add a properly formatted reference list.")


def _check_in_text_citations(text: str) -> ReadinessCheck:
    count = len(_CITATION_RE.findall(text))
    ok = count >= 3
    return ReadinessCheck("In-text citations", "references", ok, "major" if not ok else "minor",
                          f"{count} in-text citations detected." if ok else "Very few or no in-text citations found.",
                          "" if ok else "Ensure all claims are supported by in-text citations.")


def _check_ethics(text: str, metadata: dict) -> ReadinessCheck:
    has = bool(_ETHICS_RE.search(text)) or metadata.get("has_ethics_statement", False)
    return ReadinessCheck("Ethics statement", "ethics", has, "critical" if not has else "minor",
                          "Ethics statement / IRB approval found." if has else "No ethics statement detected.",
                          "" if has else "Add ethics approval details or a statement indicating exemption.")


def _check_conflict_of_interest(text: str) -> ReadinessCheck:
    has = bool(_CONFLICT_RE.search(text))
    return ReadinessCheck("Conflict of interest disclosure", "ethics", has, "major" if not has else "minor",
                          "Conflict of interest statement found." if has else "No conflict of interest statement detected.",
                          "" if has else "Add a conflict of interest / competing interests declaration.")


def _check_data_availability(text: str, metadata: dict) -> ReadinessCheck:
    has = bool(_DATA_AVAIL_RE.search(text)) or metadata.get("has_data_statement", False)
    return ReadinessCheck("Data availability statement", "data", has, "minor" if not has else "minor",
                          "Data availability statement found." if has else "No data availability statement detected.",
                          "" if has else "Add a data availability statement (even if data is not available).")


def _check_author_contributions(text: str) -> ReadinessCheck:
    has = bool(_AUTHOR_CONTRIB_RE.search(text))
    return ReadinessCheck("Author contributions", "ethics", has, "minor",
                          "Author contributions section found." if has else "No author contribution statement.",
                          "" if has else "Add CRediT author contribution statements.")


def _check_figures(text: str, metadata: dict) -> ReadinessCheck:
    has_ref = bool(_FIGURE_RE.search(text))
    fig_count = metadata.get("figure_count", 0)
    if fig_count and fig_count > 15:
        return ReadinessCheck("Figure count", "formatting", False, "minor",
                              f"{fig_count} figures may exceed journal limits (usually 8–12).",
                              "Check journal limits; move supplementary figures to appendix.")
    return ReadinessCheck("Figures present", "formatting", has_ref, "minor",
                          f"Figures referenced in text ({fig_count} found)." if has_ref else "No figure references detected.",
                          "" if has_ref else "Ensure figures are referenced and captioned.")


def _check_funding(text: str) -> ReadinessCheck:
    has = bool(_FUNDING_RE.search(text))
    return ReadinessCheck("Funding acknowledgement", "ethics", has, "minor",
                          "Funding / acknowledgements section found." if has else "No funding statement detected.",
                          "" if has else "Add a funding acknowledgement (or state no funding was received).")


def _check_word_count(text: str, metadata: dict) -> ReadinessCheck:
    wc = metadata.get("word_count", len(text.split()))
    min_wc = metadata.get("journal_min_words", 3000)
    max_wc = metadata.get("journal_max_words", 8000)
    ok = min_wc <= wc <= max_wc
    return ReadinessCheck("Word count", "formatting", ok, "major" if not ok else "minor",
                          f"Word count is {wc} (target: {min_wc}–{max_wc}).",
                          f"Expand to at least {min_wc} words." if wc < min_wc else f"Reduce to under {max_wc} words.")


def _check_cover_letter(text: str, metadata: dict) -> ReadinessCheck:
    has = bool(_COVER_LETTER_RE.search(text)) or metadata.get("has_cover_letter", False)
    return ReadinessCheck("Cover letter", "content", has, "minor",
                          "Cover letter detected." if has else "No cover letter present.",
                          "" if has else "Prepare a cover letter introducing your manuscript to the editor.")


def _check_spell_errors(text: str) -> ReadinessCheck:
    errors = _SPELL_ERRORS_RE.findall(text)
    ok = len(errors) == 0
    return ReadinessCheck("Obvious spelling errors", "language", ok, "minor" if not ok else "minor",
                          f"{len(errors)} common misspellings detected: {set(errors)}" if not ok else "No obvious spelling errors detected.",
                          "" if ok else "Run a spell-check before submission.")


_SEVERITY_WEIGHTS = {"critical": 30, "major": 15, "minor": 5}


def check_submission_readiness(
    text: str,
    metadata: dict | None = None,
) -> SubmissionReadiness:
    md = metadata or {}
    checks = [
        _check_abstract(text, md),
        _check_keywords(text, md),
        _check_imrad(text),
        _check_conclusion(text),
        _check_references(text, md),
        _check_in_text_citations(text),
        _check_ethics(text, md),
        _check_conflict_of_interest(text),
        _check_data_availability(text, md),
        _check_author_contributions(text),
        _check_figures(text, md),
        _check_funding(text),
        _check_word_count(text, md),
        _check_cover_letter(text, md),
        _check_spell_errors(text),
    ]

    passed = sum(1 for c in checks if c.passed)
    total = len(checks)
    failed = [c for c in checks if not c.passed]

    critical_blockers = [c.message for c in failed if c.severity == "critical"]
    major_issues      = [c.message for c in failed if c.severity == "major"]
    minor_issues      = [c.message for c in failed if c.severity == "minor"]

    # Score: start at 100, deduct by severity
    penalty = sum(_SEVERITY_WEIGHTS.get(c.severity, 5) for c in failed)
    score = max(0.0, 100.0 - penalty)
    grade = _score_to_grade(score)

    if critical_blockers:
        level = ReadinessLevel.NOT_READY
    elif len(major_issues) >= 3:
        level = ReadinessLevel.MAJOR_ISSUES
    elif major_issues or len(minor_issues) > 4:
        level = ReadinessLevel.MINOR_ISSUES
    else:
        level = ReadinessLevel.READY

    revision_days = (
        len(critical_blockers) * 14
        + len(major_issues) * 5
        + len(minor_issues) * 1
    )

    checklist = [
        f"✓ {c.criterion}" if c.passed else f"☐ {c.criterion} — {c.recommendation}"
        for c in checks
    ]

    return SubmissionReadiness(
        manuscript_title=md.get("title", "Untitled Manuscript"),
        target_journal=md.get("target_journal", ""),
        level=level,
        overall_score=score,
        grade=grade,
        checks=checks,
        critical_blockers=critical_blockers,
        major_issues=major_issues,
        minor_issues=minor_issues,
        passed_checks=passed,
        total_checks=total,
        estimated_revision_days=revision_days,
        submission_checklist=checklist,
    )
