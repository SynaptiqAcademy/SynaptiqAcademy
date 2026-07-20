"""Revision planner — Phase IX.

Generates a phased, prioritised revision roadmap from detected issues.
Each phase has estimated effort, outputs, and section focus.
"""
from __future__ import annotations

from .models import ReviewIssue, IssueSeverity


def build_revision_roadmap(
    critical_issues: list[ReviewIssue],
    major_issues: list[ReviewIssue],
    minor_issues: list[ReviewIssue],
    suggestions: list[ReviewIssue],
    overall_score: float,
) -> list[dict]:
    """
    Returns a list of revision phases ordered from most to least urgent.
    Each phase: {phase, title, description, priority, estimated_effort,
                 section_focus, actions, issue_count}
    """
    roadmap: list[dict] = []
    phase = 1

    # ── Phase 1: Critical issues (must fix before resubmission) ───────────────
    if critical_issues:
        actions = [
            f"{i.title}: {i.recommendation}"
            for i in critical_issues
        ]
        roadmap.append({
            "phase": phase,
            "title": "Critical Revisions",
            "description": (
                "Address all critical issues before any submission attempt. "
                "These issues will result in desk rejection if unresolved."
            ),
            "priority": "critical",
            "estimated_effort": _estimate_effort(critical_issues, "critical"),
            "section_focus": _unique_sections(critical_issues),
            "actions": actions,
            "issue_count": len(critical_issues),
        })
        phase += 1

    # ── Phase 2: Major revisions (required for acceptance) ────────────────────
    if major_issues:
        # Group major issues by section
        by_section: dict[str, list[ReviewIssue]] = {}
        for issue in major_issues:
            sec = issue.section or "General"
            by_section.setdefault(sec, []).append(issue)

        actions = [f"{i.title}: {i.recommendation}" for i in major_issues]
        roadmap.append({
            "phase": phase,
            "title": "Major Revisions",
            "description": (
                "Substantial changes required to methodology, results, or discussion. "
                "These will be flagged by reviewers as mandatory changes."
            ),
            "priority": "high",
            "estimated_effort": _estimate_effort(major_issues, "major"),
            "section_focus": _unique_sections(major_issues),
            "actions": actions,
            "issue_count": len(major_issues),
        })
        phase += 1

    # ── Phase 3: Literature and referencing ───────────────────────────────────
    lit_issues = [i for i in minor_issues if _is_lit_issue(i)]
    if lit_issues:
        roadmap.append({
            "phase": phase,
            "title": "Literature & References",
            "description": (
                "Update and expand the literature review with recent publications "
                "and address citation quality issues."
            ),
            "priority": "medium",
            "estimated_effort": "3–7 days",
            "section_focus": ["Literature Review", "References"],
            "actions": [f"{i.title}: {i.recommendation}" for i in lit_issues],
            "issue_count": len(lit_issues),
        })
        phase += 1

    # ── Phase 4: Writing quality ───────────────────────────────────────────────
    writing_issues = [i for i in minor_issues if _is_writing_issue(i)]
    if writing_issues:
        roadmap.append({
            "phase": phase,
            "title": "Writing Quality Improvements",
            "description": (
                "Improve clarity, sentence structure, transitions, "
                "and academic writing style."
            ),
            "priority": "medium",
            "estimated_effort": "2–5 days",
            "section_focus": ["All Sections"],
            "actions": [f"{i.title}: {i.recommendation}" for i in writing_issues],
            "issue_count": len(writing_issues),
        })
        phase += 1

    # ── Phase 5: Minor issues and suggestions ─────────────────────────────────
    remaining_minor = [i for i in minor_issues if not _is_lit_issue(i) and not _is_writing_issue(i)]
    remaining_minor.extend(suggestions)
    if remaining_minor:
        roadmap.append({
            "phase": phase,
            "title": "Minor Improvements & Formatting",
            "description": (
                "Address minor issues including missing statements, "
                "formatting inconsistencies, and optional enhancements."
            ),
            "priority": "low",
            "estimated_effort": "1–2 days",
            "section_focus": _unique_sections(remaining_minor),
            "actions": [f"{i.title}: {i.recommendation}" for i in remaining_minor[:10]],
            "issue_count": len(remaining_minor),
        })
        phase += 1

    # ── Phase 6: Final review ─────────────────────────────────────────────────
    if overall_score < 80:
        roadmap.append({
            "phase": phase,
            "title": "Final Proofreading & Journal Formatting",
            "description": (
                "After all revisions, perform a final proofreading pass, "
                "format according to the target journal's author guidelines, "
                "and prepare the response-to-reviewers document."
            ),
            "priority": "low",
            "estimated_effort": "1–2 days",
            "section_focus": ["All Sections"],
            "actions": [
                "Proofread entire manuscript for grammar and spelling",
                "Check reference formatting against journal style guide",
                "Verify figure and table captions comply with guidelines",
                "Prepare cover letter highlighting contributions",
                "Prepare point-by-point response to reviewer comments",
            ],
            "issue_count": 0,
        })

    return roadmap


def _estimate_effort(issues: list[ReviewIssue], severity: str) -> str:
    n = len(issues)
    if severity == "critical":
        return "1–3 weeks" if n >= 3 else "3–7 days"
    if severity == "major":
        return "2–4 weeks" if n >= 5 else "1–2 weeks"
    return "1–5 days"


def _unique_sections(issues: list[ReviewIssue]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for i in issues:
        sec = i.section or "General"
        if sec not in seen:
            seen.add(sec)
            result.append(sec)
    return result[:6]


def _is_lit_issue(i: ReviewIssue) -> bool:
    return any(k in i.section.lower() for k in ("literature", "reference", "citation"))


def _is_writing_issue(i: ReviewIssue) -> bool:
    return any(k in i.section.lower() or k in i.title.lower()
               for k in ("writing", "clarity", "sentence", "grammar", "passive",
                         "filler", "transition", "readability"))
