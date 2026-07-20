"""Literature review quality evaluator — Phase IX.

Analyses citation coverage, currency, recency, diversity, and balance
from the extracted manuscript text.
"""
from __future__ import annotations

import re
from datetime import datetime

from .models import (
    LiteratureMetrics, QualityDimension, ReviewIssue,
    IssueSeverity, _score_to_grade,
)

# ── Patterns ──────────────────────────────────────────────────────────────────

_YEAR_IN_TEXT = re.compile(r"\b(19[6-9]\d|20[0-2]\d)\b")
_AUTHOR_YEAR = re.compile(r"(?:[A-Z][a-z]+(?:\s+et\s+al\.?)?)\s*[\(\[]((?:19|20)\d{2})[\)\]]")
_NUMERIC_REF = re.compile(r"\[(\d+(?:[-–,\s]\d+)*)\]")
_SELF_CITE_SIGNALS = re.compile(r"as (?:previously\s+)?(?:shown|noted|reported|described|demonstrated)\s+by\s+(?:the\s+)?(?:authors?|us|we|our)", re.IGNORECASE)
_FOUNDATIONAL_SIGNALS = [
    "seminal", "pioneering", "foundational", "landmark", "classic",
    "original work", "first study", "early work",
]
_MISSING_LIT_SIGNALS = {
    "no previous", "no prior", "none of the", "limited research",
    "little research", "scarce literature", "under-researched", "unexplored",
}

_CURRENT_YEAR = datetime.now().year


def _extract_citation_years(text: str) -> list[int]:
    """Extract all 4-digit years that appear in citation contexts."""
    years: list[int] = []

    # Author-year format: Jones (2021)
    for m in _AUTHOR_YEAR.finditer(text):
        try:
            y = int(m.group(1))
            if 1960 <= y <= _CURRENT_YEAR:
                years.append(y)
        except ValueError:
            pass

    # All 4-digit years in text as fallback
    if not years:
        for m in _YEAR_IN_TEXT.finditer(text):
            y = int(m.group(0))
            if 1960 <= y <= _CURRENT_YEAR:
                years.append(y)

    return years


def review_literature(
    text: str,
    reference_count: int = 0,
) -> tuple[LiteratureMetrics, QualityDimension, list[ReviewIssue]]:
    text_lower = text.lower()
    years = _extract_citation_years(text)

    # ── Metrics ────────────────────────────────────────────────────────────────
    ref_count = reference_count or len(set(years))
    oldest = min(years) if years else None
    newest = max(years) if years else None
    year_range = f"{oldest}–{newest}" if oldest and newest else "unknown"

    recent_threshold = _CURRENT_YEAR - 5
    recent_count = sum(1 for y in years if y >= recent_threshold)
    recent_ratio = recent_count / max(len(years), 1)

    # Self-citation estimate
    self_cite_count = len(_SELF_CITE_SIGNALS.findall(text))
    self_cite_estimate = min(0.5, self_cite_count / max(ref_count, 1))

    # Foundational works
    has_foundational = any(s in text_lower for s in _FOUNDATIONAL_SIGNALS)

    # Citation diversity (heuristic: unique years as proxy for unique sources)
    unique_years = len(set(years))
    diversity_score = min(1.0, unique_years / max(ref_count, 1)) if ref_count else 0.0

    metrics = LiteratureMetrics(
        reference_count=ref_count,
        year_range=year_range,
        oldest_year=oldest,
        newest_year=newest,
        recent_ratio=round(recent_ratio, 3),
        self_citation_estimate=round(self_cite_estimate, 3),
        foundational_works_mentioned=has_foundational,
        citation_diversity_score=round(diversity_score, 3),
    )

    issues: list[ReviewIssue] = []
    score_components: list[float] = []
    strengths: list[str] = []
    weaknesses: list[str] = []

    # ── 1. Number of references ───────────────────────────────────────────────
    if ref_count >= 40:
        score_components.append(90.0)
        strengths.append(f"Strong reference base ({ref_count} citations)")
    elif ref_count >= 25:
        score_components.append(75.0)
        strengths.append(f"Adequate reference count ({ref_count} citations)")
    elif ref_count >= 15:
        score_components.append(60.0)
        weaknesses.append(f"Reference count may be insufficient ({ref_count})")
        issues.append(ReviewIssue(
            severity=IssueSeverity.MINOR,
            section="Literature Review / References",
            title="Limited number of references",
            description=(
                f"The manuscript cites approximately {ref_count} references. "
                "Most journals expect 30–60+ references for empirical articles."
            ),
            recommendation=(
                "Expand the literature review to include more current and foundational works. "
                "Consider searching Scopus, Web of Science, and Google Scholar systematically."
            ),
        ))
    else:
        score_components.append(40.0)
        weaknesses.append(f"Very few references ({ref_count})")
        issues.append(ReviewIssue(
            severity=IssueSeverity.MAJOR,
            section="Literature Review / References",
            title="Insufficient references for academic publication",
            description=(
                f"Only ~{ref_count} references detected. This is substantially below "
                "the minimum expected for journal submission."
            ),
            recommendation=(
                "Conduct a systematic literature search and significantly expand the reference list. "
                "A minimum of 25–40 references is expected for most journal articles."
            ),
        ))

    # ── 2. Citation recency ───────────────────────────────────────────────────
    if recent_ratio >= 0.50:
        score_components.append(90.0)
        strengths.append(f"{recent_ratio:.0%} of citations from last 5 years — excellent currency")
    elif recent_ratio >= 0.30:
        score_components.append(75.0)
        strengths.append("Adequate citation currency")
    elif years:
        score_components.append(50.0)
        weaknesses.append("Literature review lacks recent publications")
        issues.append(ReviewIssue(
            severity=IssueSeverity.MAJOR,
            section="Literature Review",
            title="Insufficient recent literature coverage",
            description=(
                f"Only {recent_ratio:.0%} of citations are from the last 5 years ({recent_threshold}–{_CURRENT_YEAR}). "
                "Reviewers expect engagement with current literature."
            ),
            recommendation=(
                "Search for publications from the last 3–5 years in leading journals. "
                f"Aim for at least 40–50% of references from {recent_threshold} onwards."
            ),
        ))
    else:
        score_components.append(40.0)

    # ── 3. Foundational works ─────────────────────────────────────────────────
    if has_foundational:
        score_components.append(80.0)
        strengths.append("Foundational/seminal works referenced")
    else:
        score_components.append(60.0)
        issues.append(ReviewIssue(
            severity=IssueSeverity.SUGGESTION,
            section="Literature Review",
            title="Foundational works not explicitly highlighted",
            description=(
                "No explicit reference to seminal or foundational works in the field. "
                "Grounding the review in landmark papers strengthens credibility."
            ),
            recommendation=(
                "Identify and include the 3–5 most influential foundational works "
                "in this research area and explain their relevance."
            ),
        ))

    # ── 4. Self-citation ──────────────────────────────────────────────────────
    if self_cite_estimate > 0.25:
        score_components.append(50.0)
        weaknesses.append("Potentially high self-citation")
        issues.append(ReviewIssue(
            severity=IssueSeverity.MINOR,
            section="References",
            title="Potential over-reliance on self-citations",
            description=(
                "The manuscript contains multiple references to 'as previously reported' "
                "or 'as shown in our earlier work', suggesting potentially high self-citation."
            ),
            recommendation=(
                "Ensure self-citations are necessary and proportionate. "
                "Most journals flag manuscripts with >15–20% self-citation rate."
            ),
        ))
    else:
        score_components.append(80.0)

    # ── 5. Year span ──────────────────────────────────────────────────────────
    if oldest and newest:
        span = newest - oldest
        if span >= 15:
            score_components.append(85.0)
            strengths.append(f"Wide temporal coverage ({year_range})")
        elif span >= 8:
            score_components.append(70.0)
        else:
            score_components.append(55.0)
            weaknesses.append("Narrow temporal range of citations")
            issues.append(ReviewIssue(
                severity=IssueSeverity.MINOR,
                section="Literature Review",
                title="Narrow temporal range of references",
                description=(
                    f"Citations span only {span} years ({year_range}). "
                    "A comprehensive literature review should cover the full development of the field."
                ),
                recommendation=(
                    "Include seminal older works to provide historical context, "
                    "alongside the most current publications."
                ),
            ))
    else:
        score_components.append(60.0)

    overall = sum(score_components) / len(score_components) if score_components else 50.0

    dim = QualityDimension(
        name="Literature Coverage",
        score=round(overall, 1),
        weight=1.0,
        grade=_score_to_grade(overall),
        rationale=(
            f"Literature analysis: ~{ref_count} refs, "
            f"{recent_ratio:.0%} recent (last 5 yrs), span={year_range}. "
            f"{len(strengths)} strengths, {len(weaknesses)} concerns."
        ),
        strengths=strengths[:5],
        weaknesses=weaknesses[:5],
    )
    return metrics, dim, issues
