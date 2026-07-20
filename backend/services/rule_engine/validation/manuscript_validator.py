"""Manuscript structure and content validators."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ManuscriptIssue:
    severity: str  # 'error' | 'warning' | 'info'
    code: str
    message: str
    field: str = ""
    suggestion: str = ""


@dataclass
class ManuscriptValidationReport:
    valid: bool
    score: float  # 0–100 completeness score
    issues: list[ManuscriptIssue] = field(default_factory=list)
    passed: list[str] = field(default_factory=list)

    def errors(self) -> list[ManuscriptIssue]:
        return [i for i in self.issues if i.severity == "error"]

    def warnings(self) -> list[ManuscriptIssue]:
        return [i for i in self.issues if i.severity == "warning"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "score": self.score,
            "issues": [
                {
                    "severity": i.severity,
                    "code": i.code,
                    "message": i.message,
                    "field": i.field,
                    "suggestion": i.suggestion,
                }
                for i in self.issues
            ],
            "passed": self.passed,
            "error_count": len(self.errors()),
            "warning_count": len(self.warnings()),
        }


# ── Required sections ─────────────────────────────────────────────────────────

_REQUIRED_SECTIONS = [
    ("abstract", re.compile(r"\babstract\b", re.IGNORECASE)),
    ("introduction", re.compile(r"\bintroduction\b", re.IGNORECASE)),
    ("methods", re.compile(r"\b(?:method(?:s|ology)?|materials?\s+and\s+method)\b", re.IGNORECASE)),
    ("results", re.compile(r"\bresults?\b", re.IGNORECASE)),
    ("discussion", re.compile(r"\bdiscussion\b", re.IGNORECASE)),
    ("conclusion", re.compile(r"\bconclusion\b", re.IGNORECASE)),
    ("references", re.compile(r"\breferences?\b", re.IGNORECASE)),
]

_RECOMMENDED_SECTIONS = [
    ("acknowledgements", re.compile(r"\backnowledge?ments?\b", re.IGNORECASE)),
    ("ethics_statement", re.compile(r"\bethics\s+(?:statement|declaration|approval)\b", re.IGNORECASE)),
    ("funding", re.compile(r"\bfunding\b", re.IGNORECASE)),
    ("conflict_of_interest", re.compile(r"\bconflict(?:s)?\s+of\s+interest\b", re.IGNORECASE)),
    ("data_availability", re.compile(r"\bdata\s+availability\b", re.IGNORECASE)),
]


def validate_abstract(
    text: str,
    min_words: int = 150,
    max_words: int = 350,
    min_sentences: int = 4,
) -> ManuscriptValidationReport:
    issues: list[ManuscriptIssue] = []
    passed: list[str] = []
    words = len(text.split())
    sentences = len(re.findall(r"[.!?]+", text))

    if words < min_words:
        issues.append(ManuscriptIssue(
            severity="error", code="ABSTRACT_TOO_SHORT", field="abstract",
            message=f"Abstract has {words} words; minimum is {min_words}.",
            suggestion="Expand the abstract to cover background, method, results, and conclusion.",
        ))
    elif words > max_words:
        issues.append(ManuscriptIssue(
            severity="warning", code="ABSTRACT_TOO_LONG", field="abstract",
            message=f"Abstract has {words} words; recommended maximum is {max_words}.",
            suggestion="Condense to key information only.",
        ))
    else:
        passed.append(f"Abstract length ({words} words) is within acceptable range.")

    if sentences < min_sentences:
        issues.append(ManuscriptIssue(
            severity="warning", code="ABSTRACT_FEW_SENTENCES", field="abstract",
            message=f"Abstract has only {sentences} sentence(s); consider at least {min_sentences}.",
        ))
    else:
        passed.append("Abstract has adequate sentence count.")

    # Check for common abstract components
    for component, pattern in [
        ("objective/background", re.compile(r"\b(?:aim|objective|purpose|background|investigat)\b", re.IGNORECASE)),
        ("method", re.compile(r"\b(?:method|approach|design|study|experiment)\b", re.IGNORECASE)),
        ("result", re.compile(r"\b(?:result|found|showed?|demonstrat|reveal)\b", re.IGNORECASE)),
        ("conclusion", re.compile(r"\b(?:conclus|suggest|implicat|therefore|thus)\b", re.IGNORECASE)),
    ]:
        if not pattern.search(text):
            issues.append(ManuscriptIssue(
                severity="warning", code=f"ABSTRACT_MISSING_{component.upper().replace('/', '_')}",
                field="abstract",
                message=f"Abstract may be missing a clear {component} statement.",
            ))
        else:
            passed.append(f"Abstract includes {component}.")

    score = max(0.0, 100.0 - len([i for i in issues if i.severity == "error"]) * 25
                - len([i for i in issues if i.severity == "warning"]) * 10)
    return ManuscriptValidationReport(
        valid=not any(i.severity == "error" for i in issues),
        score=score,
        issues=issues,
        passed=passed,
    )


def validate_keywords(
    keywords: list[str],
    min_count: int = 4,
    max_count: int = 8,
    min_term_len: int = 3,
) -> ManuscriptValidationReport:
    issues: list[ManuscriptIssue] = []
    passed: list[str] = []

    n = len(keywords)
    if n < min_count:
        issues.append(ManuscriptIssue(
            severity="error", code="KEYWORDS_TOO_FEW", field="keywords",
            message=f"Only {n} keyword(s) provided; minimum is {min_count}.",
            suggestion=f"Add {min_count - n} more specific keyword(s) describing the study topic.",
        ))
    elif n > max_count:
        issues.append(ManuscriptIssue(
            severity="warning", code="KEYWORDS_TOO_MANY", field="keywords",
            message=f"{n} keywords provided; recommended maximum is {max_count}.",
        ))
    else:
        passed.append(f"Keyword count ({n}) is within acceptable range.")

    for kw in keywords:
        if len(kw.strip()) < min_term_len:
            issues.append(ManuscriptIssue(
                severity="warning", code="KEYWORD_TOO_SHORT", field="keywords",
                message=f"Keyword '{kw}' is too short (< {min_term_len} characters).",
            ))
        if kw != kw.lower() and not kw[0].isupper():
            issues.append(ManuscriptIssue(
                severity="info", code="KEYWORD_CAPITALIZATION", field="keywords",
                message=f"Keyword '{kw}' has inconsistent capitalization.",
            ))

    seen: set[str] = set()
    for kw in keywords:
        normalized = kw.strip().lower()
        if normalized in seen:
            issues.append(ManuscriptIssue(
                severity="error", code="KEYWORD_DUPLICATE", field="keywords",
                message=f"Duplicate keyword detected: '{kw}'.",
            ))
        seen.add(normalized)

    score = max(0.0, 100.0 - len([i for i in issues if i.severity == "error"]) * 30
                - len([i for i in issues if i.severity == "warning"]) * 10)
    return ManuscriptValidationReport(
        valid=not any(i.severity == "error" for i in issues),
        score=score,
        issues=issues,
        passed=passed,
    )


def validate_manuscript_sections(full_text: str) -> ManuscriptValidationReport:
    issues: list[ManuscriptIssue] = []
    passed: list[str] = []

    for name, pattern in _REQUIRED_SECTIONS:
        if pattern.search(full_text):
            passed.append(f"Section '{name}' found.")
        else:
            issues.append(ManuscriptIssue(
                severity="error", code=f"MISSING_SECTION_{name.upper()}", field=name,
                message=f"Required section '{name}' is missing.",
                suggestion=f"Add a clearly labelled '{name.title()}' section.",
            ))

    for name, pattern in _RECOMMENDED_SECTIONS:
        if pattern.search(full_text):
            passed.append(f"Recommended section '{name}' found.")
        else:
            issues.append(ManuscriptIssue(
                severity="warning", code=f"MISSING_RECOMMENDED_{name.upper()}", field=name,
                message=f"Recommended section '{name}' is missing.",
            ))

    error_count = len([i for i in issues if i.severity == "error"])
    score = max(0.0, 100.0 - error_count * 15
                - len([i for i in issues if i.severity == "warning"]) * 5)
    return ManuscriptValidationReport(
        valid=error_count == 0,
        score=score,
        issues=issues,
        passed=passed,
    )


def validate_reference_count(
    reference_count: int,
    manuscript_type: str = "research_article",
) -> ManuscriptValidationReport:
    limits = {
        "research_article": (15, 60),
        "review_article": (40, 200),
        "case_report": (5, 30),
        "short_communication": (5, 20),
        "letter": (3, 15),
        "editorial": (1, 10),
    }
    lo, hi = limits.get(manuscript_type, (10, 100))
    issues: list[ManuscriptIssue] = []
    passed: list[str] = []

    if reference_count < lo:
        issues.append(ManuscriptIssue(
            severity="warning", code="FEW_REFERENCES", field="references",
            message=f"{reference_count} references; typical minimum for {manuscript_type} is {lo}.",
        ))
    elif reference_count > hi:
        issues.append(ManuscriptIssue(
            severity="info", code="MANY_REFERENCES", field="references",
            message=f"{reference_count} references; typical maximum for {manuscript_type} is {hi}.",
        ))
    else:
        passed.append(f"Reference count ({reference_count}) is appropriate for {manuscript_type}.")

    return ManuscriptValidationReport(
        valid=True,
        score=100.0 if not issues else 80.0,
        issues=issues,
        passed=passed,
    )


def validate_manuscript(
    title: str,
    abstract: str,
    keywords: list[str],
    full_text: str,
    references: list[str],
    manuscript_type: str = "research_article",
) -> ManuscriptValidationReport:
    """Full manuscript validation combining all checks."""
    issues: list[ManuscriptIssue] = []
    passed: list[str] = []

    if not title or len(title.strip()) < 10:
        issues.append(ManuscriptIssue(
            severity="error", code="MISSING_TITLE", field="title",
            message="Title is missing or too short (< 10 characters).",
        ))
    elif len(title) > 300:
        issues.append(ManuscriptIssue(
            severity="warning", code="TITLE_TOO_LONG", field="title",
            message=f"Title is {len(title)} characters; consider being more concise (< 150).",
        ))
    else:
        passed.append("Title length is acceptable.")

    for sub_report in [
        validate_abstract(abstract),
        validate_keywords(keywords),
        validate_manuscript_sections(full_text),
        validate_reference_count(len(references), manuscript_type),
    ]:
        issues.extend(sub_report.issues)
        passed.extend(sub_report.passed)

    error_count = len([i for i in issues if i.severity == "error"])
    warning_count = len([i for i in issues if i.severity == "warning"])
    score = max(0.0, 100.0 - error_count * 12 - warning_count * 5)

    return ManuscriptValidationReport(
        valid=error_count == 0,
        score=round(score, 1),
        issues=issues,
        passed=passed,
    )
