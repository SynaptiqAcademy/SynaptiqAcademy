"""AcademicValidator + AcademicQualityEngine — post-response evaluation.

Validator checks logical/scientific consistency.
QualityEngine scores across 8 academic dimensions and can flag for retry.
"""
from __future__ import annotations

import re

from services.academic.models import (
    AcademicContext, QualityDimension, QualityScore, ValidationResult,
)
from services.academic.ontology import get_quality_threshold

# ── Consistency patterns ───────────────────────────────────────────────────────

_CONTRADICTION_PAIRS: list[tuple[str, str]] = [
    (r"no significant (?:difference|effect)", r"significant (?:difference|effect)"),
    (r"qualitative (study|approach)", r"statistical significance"),
    (r"all participants", r"some participants"),
    (r"100%", r"\d+ percent"),
    (r"\bn\s?=\s?0\b", r"participants? were"),
]

_HEDGING_PHRASES = [
    "may", "might", "could", "suggests", "appears to", "seems to",
    "possibly", "potentially", "tentatively", "arguably",
]

_CERTAINTY_PHRASES = [
    "proves", "conclusively", "definitively", "absolutely", "always",
    "never", "impossible", "guarantees", "without doubt",
]

_ACADEMIC_VOICE_WORDS = [
    "furthermore", "moreover", "however", "therefore", "consequently",
    "in conclusion", "in summary", "notably", "specifically",
    "significant", "demonstrate", "indicate", "reveal",
]


class AcademicValidator:
    """Validate academic response for logical and scientific consistency."""

    def validate(self, text: str, context: AcademicContext) -> ValidationResult:
        issues: list[str] = []
        warnings: list[str] = []

        if not text or len(text) < 50:
            return ValidationResult(
                is_valid=False,
                issues=["Response is too short for an academic answer."],
            )

        # Check for internal contradictions
        for pat_a, pat_b in _CONTRADICTION_PAIRS:
            if re.search(pat_a, text, re.IGNORECASE) and re.search(pat_b, text, re.IGNORECASE):
                warnings.append(
                    f"Potential contradiction: patterns '{pat_a}' and '{pat_b}' both appear."
                )

        # Check for unsupported absolute claims
        absolute_matches = [p for p in _CERTAINTY_PHRASES if p in text.lower()]
        if absolute_matches:
            warnings.append(
                f"Overly certain language detected: {', '.join(absolute_matches[:3])}. "
                "Consider hedging for academic precision."
            )

        # Check minimum response length for complex features
        word_count = len(text.split())
        if context.feature in _VERBOSE_FEATURES and word_count < 150:
            issues.append(
                f"Response too brief ({word_count} words) for '{context.feature}'. "
                "Academic analysis typically requires more depth."
            )

        # Check that critical weaknesses from context are addressed
        critical = context.get_critical_weaknesses()
        if critical:
            weakness_mentions = sum(
                1 for w in critical
                if any(keyword in text.lower() for keyword in w.type.value.split("_"))
            )
            if weakness_mentions == 0 and len(critical) >= 2:
                warnings.append(
                    f"{len(critical)} critical academic weaknesses were flagged but may "
                    "not be addressed in the response."
                )

        is_valid = len(issues) == 0
        return ValidationResult(is_valid=is_valid, issues=issues, warnings=warnings)


class AcademicQualityEngine:
    """Score academic responses across 8 dimensions."""

    _DIMENSIONS = [
        ("academic_rigor",       0.20),
        ("scientific_accuracy",  0.18),
        ("clarity",              0.12),
        ("structure",            0.12),
        ("completeness",         0.15),
        ("citation_quality",     0.08),
        ("reasoning_quality",    0.10),
        ("publication_readiness", 0.05),
    ]

    def score(self, text: str, feature: str, context: AcademicContext | None = None) -> QualityScore:
        if not text:
            return QualityScore(overall_score=0.0, threshold=get_quality_threshold(feature), feature=feature)

        threshold = get_quality_threshold(feature)
        dims = [
            self._score_academic_rigor(text, feature, context),
            self._score_scientific_accuracy(text, context),
            self._score_clarity(text),
            self._score_structure(text, feature),
            self._score_completeness(text, feature, context),
            self._score_citation_quality(text, feature),
            self._score_reasoning_quality(text),
            self._score_publication_readiness(text, feature),
        ]
        return QualityScore.from_dimensions(dims, threshold=threshold, feature=feature)

    def _score_academic_rigor(
        self, text: str, feature: str, context: AcademicContext | None
    ) -> QualityDimension:
        score = 0.50
        issues: list[str] = []
        lower = text.lower()

        academic_voice_count = sum(1 for w in _ACADEMIC_VOICE_WORDS if w in lower)
        score += min(0.20, academic_voice_count * 0.04)

        if any(p in lower for p in _HEDGING_PHRASES[:5]):
            score += 0.10  # appropriate hedging
        if any(p in lower for p in _CERTAINTY_PHRASES[:3]):
            score -= 0.10
            issues.append("Avoid absolute claims; use hedged academic language.")

        if context and context.detected_weaknesses:
            weaknesses_mentioned = sum(
                1 for w in context.detected_weaknesses
                if any(kw in lower for kw in w.type.value.replace("_", " ").split())
            )
            coverage = weaknesses_mentioned / len(context.detected_weaknesses)
            score += coverage * 0.15
            if coverage < 0.3 and context.detected_weaknesses:
                issues.append("Detected academic weaknesses not fully addressed.")

        return QualityDimension("academic_rigor", round(min(1.0, max(0.0, score)), 3),
                                self._DIMENSIONS[0][1], issues)

    def _score_scientific_accuracy(
        self, text: str, context: AcademicContext | None
    ) -> QualityDimension:
        score = 0.70
        issues: list[str] = []
        lower = text.lower()

        contradiction_count = sum(
            1 for a, b in _CONTRADICTION_PAIRS
            if re.search(a, text, re.IGNORECASE) and re.search(b, text, re.IGNORECASE)
        )
        score -= contradiction_count * 0.15
        if contradiction_count > 0:
            issues.append(f"Potential contradiction(s) detected ({contradiction_count}).")

        absolute = sum(1 for p in _CERTAINTY_PHRASES if p in lower)
        if absolute > 0:
            score -= 0.05 * absolute
            issues.append("Absolute language reduces scientific credibility.")

        return QualityDimension("scientific_accuracy", round(min(1.0, max(0.0, score)), 3),
                                self._DIMENSIONS[1][1], issues)

    def _score_clarity(self, text: str) -> QualityDimension:
        score = 0.65
        issues: list[str] = []

        sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
        if sentences:
            avg_words = sum(len(s.split()) for s in sentences) / len(sentences)
            if avg_words > 40:
                score -= 0.15
                issues.append("Sentences are very long on average; improve readability.")
            elif avg_words < 8:
                score -= 0.10
                issues.append("Sentences are very short; add explanatory depth.")
            else:
                score += 0.20

        word_count = len(text.split())
        if word_count > 50:
            score += 0.10

        return QualityDimension("clarity", round(min(1.0, max(0.0, score)), 3),
                                self._DIMENSIONS[2][1], issues)

    def _score_structure(self, text: str, feature: str) -> QualityDimension:
        score = 0.60
        issues: list[str] = []

        has_headings = bool(re.search(r'^#{1,3}\s|\*\*.+\*\*|[A-Z][A-Z\s]{4,}:', text, re.MULTILINE))
        has_lists = bool(re.search(r'^\s*[-•*\d+\.]\s', text, re.MULTILINE))
        has_paragraphs = text.count('\n\n') >= 2

        if has_headings:
            score += 0.15
        if has_lists:
            score += 0.10
        if has_paragraphs:
            score += 0.10

        if feature in _STRUCTURED_FEATURES and not (has_headings or has_lists):
            score -= 0.15
            issues.append("Structured feature response should use headings or bullet points.")

        return QualityDimension("structure", round(min(1.0, max(0.0, score)), 3),
                                self._DIMENSIONS[3][1], issues)

    def _score_completeness(
        self, text: str, feature: str, context: AcademicContext | None
    ) -> QualityDimension:
        score = 0.60
        issues: list[str] = []
        word_count = len(text.split())

        min_words = _MIN_WORD_COUNTS.get(feature, 100)
        if word_count >= min_words * 2:
            score += 0.25
        elif word_count >= min_words:
            score += 0.15
        else:
            deficit = (min_words - word_count) / min_words
            score -= deficit * 0.30
            issues.append(f"Response may be incomplete ({word_count} words; expected ~{min_words}+).")

        if context:
            sections_needed = _REQUIRED_SECTIONS.get(feature, [])
            sections_found = sum(
                1 for s in sections_needed if s.lower() in text.lower()
            )
            if sections_needed:
                coverage = sections_found / len(sections_needed)
                score += coverage * 0.10
                if coverage < 0.5:
                    missing = [s for s in sections_needed if s.lower() not in text.lower()]
                    issues.append(f"Missing expected sections: {', '.join(missing[:3])}")

        return QualityDimension("completeness", round(min(1.0, max(0.0, score)), 3),
                                self._DIMENSIONS[4][1], issues)

    def _score_citation_quality(self, text: str, feature: str) -> QualityDimension:
        score = 0.60
        issues: list[str] = []

        if feature not in _CITATION_SCORED_FEATURES:
            return QualityDimension("citation_quality", 0.75, self._DIMENSIONS[5][1], [])

        apa_count = len(re.findall(r'\([A-Z][a-z]+[^)]*\d{4}\)', text))
        num_count = len(re.findall(r'\[\d+\]', text))
        et_al_count = len(re.findall(r'et al\.', text))
        total = max(apa_count, num_count, et_al_count)

        if total >= 5:
            score = 0.90
        elif total >= 3:
            score = 0.80
        elif total >= 1:
            score = 0.65
        else:
            score = 0.30
            issues.append("No citations detected; academic responses require references.")

        return QualityDimension("citation_quality", round(score, 3),
                                self._DIMENSIONS[5][1], issues)

    def _score_reasoning_quality(self, text: str) -> QualityDimension:
        score = 0.65
        issues: list[str] = []
        lower = text.lower()

        reasoning_markers = [
            "because", "therefore", "thus", "as a result", "consequently",
            "evidence", "suggests", "demonstrates", "indicates", "shows",
            "first", "second", "third", "finally", "in addition",
        ]
        marker_count = sum(1 for m in reasoning_markers if m in lower)
        score += min(0.25, marker_count * 0.025)

        if marker_count < 3:
            issues.append("Response lacks explicit reasoning markers; add causal connectors.")

        return QualityDimension("reasoning_quality", round(min(1.0, max(0.0, score)), 3),
                                self._DIMENSIONS[6][1], issues)

    def _score_publication_readiness(self, text: str, feature: str) -> QualityDimension:
        if feature not in _PUBLICATION_READY_FEATURES:
            return QualityDimension("publication_readiness", 0.75, self._DIMENSIONS[7][1], [])

        score = 0.60
        issues: list[str] = []
        lower = text.lower()

        jargon_avoidance = not bool(re.search(r'\bi think\b|\bi believe\b|\bi feel\b', lower))
        passive_voice_count = len(re.findall(r'\bwas\s+\w+ed\b|\bwere\s+\w+ed\b', lower))
        formal_connectors = sum(1 for m in ["furthermore", "moreover", "however", "consequently"]
                                if m in lower)

        if jargon_avoidance:
            score += 0.15
        if formal_connectors >= 2:
            score += 0.10
        if 0 < passive_voice_count < 10:
            score += 0.10  # some passive voice is appropriate in academic writing

        return QualityDimension("publication_readiness", round(min(1.0, max(0.0, score)), 3),
                                self._DIMENSIONS[7][1], issues)


# ── Feature configuration constants ───────────────────────────────────────────

_VERBOSE_FEATURES = {
    "manuscript_review", "literature_review", "research_gap_finder",
    "statistical_review", "research_design_advisor",
}

_STRUCTURED_FEATURES = {
    "manuscript_review", "literature_review", "research_design_advisor",
    "grant_gap_detection", "teaching_lesson_generation",
}

_CITATION_SCORED_FEATURES = {
    "manuscript_review", "literature_review", "research_gap_finder",
    "statistical_review",
}

_PUBLICATION_READY_FEATURES = {
    "manuscript_review", "abstract_generator", "literature_review",
}

_MIN_WORD_COUNTS: dict[str, int] = {
    "manuscript_review": 300,
    "literature_review": 400,
    "research_gap_finder": 200,
    "statistical_review": 200,
    "research_design_advisor": 200,
    "abstract_generator": 100,
    "grant_gap_detection": 200,
    "ai_chat": 50,
    "ai_assistant": 80,
    "summarization": 80,
}

_REQUIRED_SECTIONS: dict[str, list[str]] = {
    "manuscript_review": ["hypothesis", "methodology", "results", "discussion", "limitation"],
    "literature_review": ["gap", "conclusion", "recommendation"],
    "research_design_advisor": ["design", "methodology", "validity"],
    "grant_gap_detection": ["objective", "methodology", "impact"],
}
