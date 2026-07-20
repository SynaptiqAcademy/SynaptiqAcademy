"""Manuscript Intelligence 2.0 — Phase IX domain model.

All dataclasses use field() defaults so they are safe to construct with
keyword arguments only.  to_dict() produces plain dicts ready for MongoDB
and JSON serialisation.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


# ══════════════════════════════════════════════════════════════════════════════
# Enumerations
# ══════════════════════════════════════════════════════════════════════════════

class ReviewDepth(str, Enum):
    QUICK = "quick"        # 5 credits  — AI review only
    STANDARD = "standard"  # 15 credits — rule-based + AI
    DEEP = "deep"          # 25 credits — full pipeline + lit session


class ExportFormat(str, Enum):
    PEER_REVIEW = "peer_review"
    EDITORIAL_REPORT = "editorial_report"
    SUPERVISOR_REPORT = "supervisor_report"
    REVISION_CHECKLIST = "revision_checklist"
    PUBLICATION_READINESS = "publication_readiness"
    MARKDOWN = "markdown"
    LATEX = "latex"
    TEXT = "text"


class IssueSeverity(str, Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    SUGGESTION = "suggestion"


class Recommendation(str, Enum):
    ACCEPT = "accept"
    MINOR_REVISION = "minor_revision"
    MAJOR_REVISION = "major_revision"
    REVISE_AND_RESUBMIT = "revise_and_resubmit"
    REJECT = "reject"
    REJECT_WITH_ENCOURAGEMENT = "reject_with_encouragement"


class SectionType(str, Enum):
    TITLE = "title"
    ABSTRACT = "abstract"
    KEYWORDS = "keywords"
    INTRODUCTION = "introduction"
    BACKGROUND = "background"
    LITERATURE_REVIEW = "literature_review"
    RESEARCH_GAP = "research_gap"
    OBJECTIVES = "objectives"
    RESEARCH_QUESTIONS = "research_questions"
    HYPOTHESES = "hypotheses"
    THEORETICAL_FRAMEWORK = "theoretical_framework"
    CONCEPTUAL_FRAMEWORK = "conceptual_framework"
    METHODOLOGY = "methodology"
    RESEARCH_DESIGN = "research_design"
    PARTICIPANTS = "participants"
    INSTRUMENTS = "instruments"
    DATA_COLLECTION = "data_collection"
    DATA_ANALYSIS = "data_analysis"
    RESULTS = "results"
    FINDINGS = "findings"
    DISCUSSION = "discussion"
    IMPLICATIONS = "implications"
    LIMITATIONS = "limitations"
    FUTURE_WORK = "future_work"
    CONCLUSIONS = "conclusions"
    ACKNOWLEDGEMENTS = "acknowledgements"
    FUNDING = "funding"
    ETHICS = "ethics"
    CONFLICT_OF_INTEREST = "conflict_of_interest"
    DATA_AVAILABILITY = "data_availability"
    REFERENCES = "references"
    APPENDIX = "appendix"
    FIGURES = "figures"
    TABLES = "tables"
    SUPPLEMENTARY = "supplementary"


class InputFormat(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    LATEX = "latex"
    MARKDOWN = "markdown"
    TXT = "txt"
    TEXT = "text"


# ══════════════════════════════════════════════════════════════════════════════
# Parsed document
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class DetectedSection:
    section_type: SectionType
    heading: str = ""
    content: str = ""
    word_count: int = 0
    start_char: int = 0
    end_char: int = 0
    confidence: float = 1.0

    def to_dict(self) -> dict:
        return {
            "section_type": self.section_type.value,
            "heading": self.heading,
            "word_count": self.word_count,
            "confidence": self.confidence,
        }


@dataclass
class ParsedDocument:
    full_text: str = ""
    sections: list[DetectedSection] = field(default_factory=list)
    title: str = ""
    abstract: str = ""
    keywords: list[str] = field(default_factory=list)
    word_count: int = 0
    page_count: int = 0
    figure_count: int = 0
    table_count: int = 0
    reference_count: int = 0
    input_format: InputFormat = InputFormat.TXT
    metadata: dict = field(default_factory=dict)


# ══════════════════════════════════════════════════════════════════════════════
# Review building blocks
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ReviewIssue:
    severity: IssueSeverity
    section: str
    title: str
    description: str
    recommendation: str
    page_reference: str = ""

    def to_dict(self) -> dict:
        return {
            "severity": self.severity.value,
            "section": self.section,
            "title": self.title,
            "description": self.description,
            "recommendation": self.recommendation,
            "page_reference": self.page_reference,
        }


@dataclass
class QualityDimension:
    name: str
    score: float = 0.0   # 0–100
    weight: float = 1.0
    grade: str = "N/A"
    rationale: str = ""
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "score": self.score,
            "weight": self.weight,
            "grade": self.grade,
            "rationale": self.rationale,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
        }


@dataclass
class SectionScore:
    section_type: SectionType
    label: str
    score: float = 0.0   # 0–100
    grade: str = "N/A"
    detected: bool = True
    word_count: int = 0
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "section_type": self.section_type.value,
            "label": self.label,
            "score": self.score,
            "grade": self.grade,
            "detected": self.detected,
            "word_count": self.word_count,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "recommendations": self.recommendations,
        }


@dataclass
class ReviewDimensions:
    scientific_rigor: QualityDimension = field(
        default_factory=lambda: QualityDimension("Scientific Rigor", weight=1.5)
    )
    originality: QualityDimension = field(
        default_factory=lambda: QualityDimension("Originality & Novelty", weight=1.5)
    )
    methodological_soundness: QualityDimension = field(
        default_factory=lambda: QualityDimension("Methodological Soundness", weight=1.5)
    )
    clarity: QualityDimension = field(
        default_factory=lambda: QualityDimension("Clarity & Writing Quality", weight=1.0)
    )
    literature_coverage: QualityDimension = field(
        default_factory=lambda: QualityDimension("Literature Coverage", weight=1.0)
    )
    contribution: QualityDimension = field(
        default_factory=lambda: QualityDimension("Scientific Contribution", weight=1.5)
    )
    statistical_validity: QualityDimension = field(
        default_factory=lambda: QualityDimension("Statistical Validity", weight=1.0)
    )
    ethical_compliance: QualityDimension = field(
        default_factory=lambda: QualityDimension("Ethical Compliance", weight=0.5)
    )

    def weighted_score(self) -> float:
        dims = [
            self.scientific_rigor, self.originality, self.methodological_soundness,
            self.clarity, self.literature_coverage, self.contribution,
            self.statistical_validity, self.ethical_compliance,
        ]
        total_w = sum(d.weight for d in dims)
        total_s = sum(d.score * d.weight for d in dims)
        return round(total_s / total_w, 1) if total_w else 0.0

    def to_dict(self) -> dict:
        return {
            "scientific_rigor": self.scientific_rigor.to_dict(),
            "originality": self.originality.to_dict(),
            "methodological_soundness": self.methodological_soundness.to_dict(),
            "clarity": self.clarity.to_dict(),
            "literature_coverage": self.literature_coverage.to_dict(),
            "contribution": self.contribution.to_dict(),
            "statistical_validity": self.statistical_validity.to_dict(),
            "ethical_compliance": self.ethical_compliance.to_dict(),
        }


@dataclass
class PublicationReadiness:
    overall_score: float = 0.0        # 0–100
    acceptance_probability: float = 0.0  # 0–1
    desk_rejection_risk: float = 0.0
    reviewer_difficulty: str = "moderate"
    major_revision_probability: float = 0.0
    minor_revision_probability: float = 0.0
    estimated_revision_effort: str = "unknown"
    target_tier: str = "Q2"
    strengths: list[str] = field(default_factory=list)
    barriers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "overall_score": self.overall_score,
            "acceptance_probability": self.acceptance_probability,
            "desk_rejection_risk": self.desk_rejection_risk,
            "reviewer_difficulty": self.reviewer_difficulty,
            "major_revision_probability": self.major_revision_probability,
            "minor_revision_probability": self.minor_revision_probability,
            "estimated_revision_effort": self.estimated_revision_effort,
            "target_tier": self.target_tier,
            "strengths": self.strengths,
            "barriers": self.barriers,
        }


@dataclass
class JournalMatch:
    name: str
    publisher: str = ""
    quartile: str = "Q2"
    scope_match: float = 0.70     # 0–1
    acceptance_probability: float = 0.25
    impact_factor: Optional[float] = None
    submission_notes: str = ""
    url: str = ""
    open_access: bool = False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "publisher": self.publisher,
            "quartile": self.quartile,
            "scope_match": self.scope_match,
            "acceptance_probability": self.acceptance_probability,
            "impact_factor": self.impact_factor,
            "submission_notes": self.submission_notes,
            "url": self.url,
            "open_access": self.open_access,
        }


@dataclass
class WritingMetrics:
    word_count: int = 0
    sentence_count: int = 0
    avg_sentence_length: float = 0.0
    long_sentence_ratio: float = 0.0   # fraction of sentences >40 words
    passive_voice_ratio: float = 0.0
    academic_word_ratio: float = 0.0
    transition_density: float = 0.0
    readability_score: float = 70.0   # Flesch approximation (higher = easier)
    paragraph_count: int = 0
    avg_paragraph_length: float = 0.0

    def to_dict(self) -> dict:
        return {
            "word_count": self.word_count,
            "sentence_count": self.sentence_count,
            "avg_sentence_length": self.avg_sentence_length,
            "long_sentence_ratio": self.long_sentence_ratio,
            "passive_voice_ratio": self.passive_voice_ratio,
            "academic_word_ratio": self.academic_word_ratio,
            "transition_density": self.transition_density,
            "readability_score": self.readability_score,
            "paragraph_count": self.paragraph_count,
            "avg_paragraph_length": self.avg_paragraph_length,
        }


@dataclass
class LiteratureMetrics:
    reference_count: int = 0
    year_range: str = ""
    oldest_year: Optional[int] = None
    newest_year: Optional[int] = None
    recent_ratio: float = 0.0       # references in last 5 years / total
    self_citation_estimate: float = 0.0
    foundational_works_mentioned: bool = False
    citation_diversity_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "reference_count": self.reference_count,
            "year_range": self.year_range,
            "oldest_year": self.oldest_year,
            "newest_year": self.newest_year,
            "recent_ratio": self.recent_ratio,
            "self_citation_estimate": self.self_citation_estimate,
            "foundational_works_mentioned": self.foundational_works_mentioned,
            "citation_diversity_score": self.citation_diversity_score,
        }


@dataclass
class StatisticalMetrics:
    has_p_values: bool = False
    has_confidence_intervals: bool = False
    has_effect_sizes: bool = False
    has_sample_size: bool = False
    has_power_analysis: bool = False
    p_value_count: int = 0
    statistical_tests_used: list[str] = field(default_factory=list)
    assumption_checks_mentioned: bool = False
    descriptive_stats_present: bool = False

    def to_dict(self) -> dict:
        return {
            "has_p_values": self.has_p_values,
            "has_confidence_intervals": self.has_confidence_intervals,
            "has_effect_sizes": self.has_effect_sizes,
            "has_sample_size": self.has_sample_size,
            "has_power_analysis": self.has_power_analysis,
            "p_value_count": self.p_value_count,
            "statistical_tests_used": self.statistical_tests_used,
            "assumption_checks_mentioned": self.assumption_checks_mentioned,
            "descriptive_stats_present": self.descriptive_stats_present,
        }


# ══════════════════════════════════════════════════════════════════════════════
# Main result
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ManuscriptIntelligenceResult:
    # ── Identity ───────────────────────────────────────────────────────────────
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    filename: str = ""
    manuscript_id: str = ""
    review_depth: ReviewDepth = ReviewDepth.STANDARD

    # ── Document structure ─────────────────────────────────────────────────────
    title: str = ""
    abstract: str = ""
    keywords: list[str] = field(default_factory=list)
    detected_sections: list[str] = field(default_factory=list)
    section_scores: list[SectionScore] = field(default_factory=list)
    word_count: int = 0
    page_count: int = 0
    figure_count: int = 0
    table_count: int = 0
    reference_count: int = 0

    # ── Review ─────────────────────────────────────────────────────────────────
    review_dimensions: ReviewDimensions = field(default_factory=ReviewDimensions)
    overall_score: float = 0.0
    recommendation: Recommendation = Recommendation.MAJOR_REVISION
    executive_summary: str = ""

    # ── Issues ────────────────────────────────────────────────────────────────
    critical_issues: list[ReviewIssue] = field(default_factory=list)
    major_issues: list[ReviewIssue] = field(default_factory=list)
    minor_issues: list[ReviewIssue] = field(default_factory=list)
    suggestions: list[ReviewIssue] = field(default_factory=list)

    # ── Specialised analyses ───────────────────────────────────────────────────
    writing_metrics: WritingMetrics = field(default_factory=WritingMetrics)
    literature_metrics: LiteratureMetrics = field(default_factory=LiteratureMetrics)
    statistical_metrics: StatisticalMetrics = field(default_factory=StatisticalMetrics)
    publication_readiness: PublicationReadiness = field(default_factory=PublicationReadiness)

    # ── Journal matching ──────────────────────────────────────────────────────
    journal_matches: list[JournalMatch] = field(default_factory=list)
    inferred_discipline: str = ""

    # ── Revision plan ─────────────────────────────────────────────────────────
    revision_roadmap: list[dict] = field(default_factory=list)

    # ── Outputs ───────────────────────────────────────────────────────────────
    peer_review_text: str = ""
    editorial_assessment: str = ""
    visualizations: dict = field(default_factory=dict)

    # ── Meta ──────────────────────────────────────────────────────────────────
    analysis_duration_ms: int = 0
    credits_used: int = 0
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_summary(self) -> dict:
        return {
            "result_id": self.result_id,
            "filename": self.filename,
            "title": self.title,
            "overall_score": self.overall_score,
            "recommendation": self.recommendation.value,
            "review_depth": self.review_depth.value,
            "word_count": self.word_count,
            "critical_issues": len(self.critical_issues),
            "major_issues": len(self.major_issues),
            "minor_issues": len(self.minor_issues),
            "acceptance_probability": self.publication_readiness.acceptance_probability,
            "inferred_discipline": self.inferred_discipline,
            "credits_used": self.credits_used,
            "created_at": self.created_at,
        }

    def to_dict(self) -> dict:
        return {
            "result_id": self.result_id,
            "user_id": self.user_id,
            "filename": self.filename,
            "manuscript_id": self.manuscript_id,
            "review_depth": self.review_depth.value,
            "title": self.title,
            "abstract": self.abstract,
            "keywords": self.keywords,
            "detected_sections": self.detected_sections,
            "section_scores": [s.to_dict() for s in self.section_scores],
            "word_count": self.word_count,
            "page_count": self.page_count,
            "figure_count": self.figure_count,
            "table_count": self.table_count,
            "reference_count": self.reference_count,
            "review_dimensions": self.review_dimensions.to_dict(),
            "overall_score": self.overall_score,
            "recommendation": self.recommendation.value,
            "executive_summary": self.executive_summary,
            "critical_issues": [i.to_dict() for i in self.critical_issues],
            "major_issues": [i.to_dict() for i in self.major_issues],
            "minor_issues": [i.to_dict() for i in self.minor_issues],
            "suggestions": [i.to_dict() for i in self.suggestions],
            "writing_metrics": self.writing_metrics.to_dict(),
            "literature_metrics": self.literature_metrics.to_dict(),
            "statistical_metrics": self.statistical_metrics.to_dict(),
            "publication_readiness": self.publication_readiness.to_dict(),
            "journal_matches": [j.to_dict() for j in self.journal_matches],
            "inferred_discipline": self.inferred_discipline,
            "revision_roadmap": self.revision_roadmap,
            "peer_review_text": self.peer_review_text,
            "editorial_assessment": self.editorial_assessment,
            "visualizations": self.visualizations,
            "analysis_duration_ms": self.analysis_duration_ms,
            "credits_used": self.credits_used,
            "created_at": self.created_at,
        }


# ══════════════════════════════════════════════════════════════════════════════
# Request model (pure dataclass — Pydantic lives in router)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ManuscriptReviewRequest:
    content: str                           # full extracted text
    filename: str = "manuscript"
    input_format: InputFormat = InputFormat.TXT
    review_depth: ReviewDepth = ReviewDepth.STANDARD
    user_id: str = ""
    manuscript_id: str = ""
    target_journal: str = ""
    discipline: str = ""
    word_count_hint: int = 0               # from parser; avoid re-counting
    lit_session_id: str = ""


def _score_to_grade(score: float) -> str:
    if score >= 90:
        return "A+"
    if score >= 85:
        return "A"
    if score >= 80:
        return "A-"
    if score >= 75:
        return "B+"
    if score >= 70:
        return "B"
    if score >= 65:
        return "B-"
    if score >= 60:
        return "C+"
    if score >= 55:
        return "C"
    if score >= 50:
        return "C-"
    if score >= 40:
        return "D"
    return "F"
