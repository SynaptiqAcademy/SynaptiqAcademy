"""Academic Intelligence Engine — complete domain model.

Every entity, relationship, weakness, and scoring type used across the engine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ── Domain taxonomy ────────────────────────────────────────────────────────────

class AcademicDomain(str, Enum):
    COMPUTER_SCIENCE = "computer_science"
    MEDICINE_HEALTH = "medicine_health"
    SOCIAL_SCIENCES = "social_sciences"
    NATURAL_SCIENCES = "natural_sciences"
    ENGINEERING = "engineering"
    BUSINESS_MANAGEMENT = "business_management"
    EDUCATION = "education"
    HUMANITIES = "humanities"
    LAW = "law"
    PSYCHOLOGY = "psychology"
    ECONOMICS = "economics"
    ENVIRONMENTAL_SCIENCES = "environmental_sciences"
    MATHEMATICS_STATISTICS = "mathematics_statistics"
    INTERDISCIPLINARY = "interdisciplinary"
    UNKNOWN = "unknown"


class MethodologyType(str, Enum):
    QUANTITATIVE = "quantitative"
    QUALITATIVE = "qualitative"
    MIXED_METHODS = "mixed_methods"
    THEORETICAL = "theoretical"
    COMPUTATIONAL = "computational"
    EXPERIMENTAL = "experimental"
    UNKNOWN = "unknown"


class ResearchDesign(str, Enum):
    RANDOMIZED_CONTROLLED_TRIAL = "rct"
    CASE_STUDY = "case_study"
    SURVEY = "survey"
    CROSS_SECTIONAL = "cross_sectional"
    LONGITUDINAL = "longitudinal"
    COHORT = "cohort"
    SYSTEMATIC_REVIEW = "systematic_review"
    SCOPING_REVIEW = "scoping_review"
    META_ANALYSIS = "meta_analysis"
    NARRATIVE_REVIEW = "narrative_review"
    GROUNDED_THEORY = "grounded_theory"
    ETHNOGRAPHY = "ethnography"
    ACTION_RESEARCH = "action_research"
    DELPHI = "delphi"
    SIMULATION = "simulation"
    BENCHMARK = "benchmark"
    ABLATION = "ablation"
    UNKNOWN = "unknown"


class WeaknessType(str, Enum):
    # Hypothesis / Objectives
    MISSING_HYPOTHESIS = "missing_hypothesis"
    UNCLEAR_OBJECTIVE = "unclear_objective"
    MISSING_RESEARCH_QUESTION = "missing_research_question"

    # Novelty / Contribution
    WEAK_NOVELTY = "weak_novelty"
    MISSING_CONTRIBUTION = "missing_contribution"
    MISSING_COMPARISON_WITH_BASELINES = "missing_comparison_with_baselines"

    # Methodology
    WEAK_METHODOLOGY = "weak_methodology"
    MISSING_METHODOLOGY_JUSTIFICATION = "missing_methodology_justification"
    SAMPLING_ISSUE = "sampling_issue"
    SMALL_SAMPLE_SIZE = "small_sample_size"
    SELECTION_BIAS = "selection_bias"

    # Statistical
    STATISTICAL_WEAKNESS = "statistical_weakness"
    MISSING_EFFECT_SIZE = "missing_effect_size"
    MISSING_CONFIDENCE_INTERVAL = "missing_confidence_interval"
    MISSING_POWER_ANALYSIS = "missing_power_analysis"
    INAPPROPRIATE_STATISTICAL_TEST = "inappropriate_statistical_test"

    # Citations / Evidence
    MISSING_CITATIONS = "missing_citations"
    OUTDATED_REFERENCES = "outdated_references"
    MISSING_SEMINAL_WORKS = "missing_seminal_works"
    CITATION_INCONSISTENCY = "citation_inconsistency"

    # Structure / Writing
    LOGICAL_INCONSISTENCY = "logical_inconsistency"
    UNSUPPORTED_CONCLUSION = "unsupported_conclusion"
    MISSING_LIMITATIONS = "missing_limitations"
    MISSING_FUTURE_WORK = "missing_future_work"
    POOR_DISCUSSION = "poor_discussion"
    WEAK_ABSTRACT = "weak_abstract"

    # Ethics / Compliance
    MISSING_ETHICS_APPROVAL = "missing_ethics_approval"
    MISSING_CONFLICT_OF_INTEREST = "missing_conflict_of_interest"
    MISSING_DATA_AVAILABILITY = "missing_data_availability"
    MISSING_AUTHOR_CONTRIBUTIONS = "missing_author_contributions"

    # Scope / Fit
    JOURNAL_INCOMPATIBILITY = "journal_incompatibility"
    PUBLICATION_RISK = "publication_risk"
    SCOPE_TOO_BROAD = "scope_too_broad"
    SCOPE_TOO_NARROW = "scope_too_narrow"


class WeaknessSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConfidenceLevel(str, Enum):
    VERY_LOW = "very_low"    # < 0.40
    LOW = "low"              # 0.40–0.59
    MEDIUM = "medium"        # 0.60–0.74
    HIGH = "high"            # 0.75–0.89
    VERY_HIGH = "very_high"  # ≥ 0.90

    @classmethod
    def from_score(cls, score: float) -> "ConfidenceLevel":
        if score < 0.40:
            return cls.VERY_LOW
        if score < 0.60:
            return cls.LOW
        if score < 0.75:
            return cls.MEDIUM
        if score < 0.90:
            return cls.HIGH
        return cls.VERY_HIGH


# ── Academic entities ──────────────────────────────────────────────────────────

@dataclass
class AcademicWeakness:
    type: WeaknessType
    severity: WeaknessSeverity
    description: str
    suggestion: str
    confidence: float = 0.8
    location: str = ""           # section where detected

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "severity": self.severity.value,
            "description": self.description,
            "suggestion": self.suggestion,
            "confidence": self.confidence,
            "location": self.location,
        }


@dataclass
class AcademicContext:
    """Rich academic context built from a request — injected into system prompts."""
    feature: str
    user_id: str

    # Domain analysis
    domain: AcademicDomain = AcademicDomain.UNKNOWN
    domain_confidence: float = 0.0
    sub_domains: list[str] = field(default_factory=list)

    # Methodology analysis
    methodology_type: MethodologyType = MethodologyType.UNKNOWN
    research_design: ResearchDesign = ResearchDesign.UNKNOWN
    detected_methodology_keywords: list[str] = field(default_factory=list)

    # Structural analysis
    detected_sections: list[str] = field(default_factory=list)
    word_count: int = 0
    citation_count: int = 0
    has_abstract: bool = False
    has_hypothesis: bool = False
    has_methodology: bool = False
    has_results: bool = False
    has_limitations: bool = False
    has_future_work: bool = False
    has_ethics: bool = False
    has_conflicts_of_interest: bool = False

    # Weaknesses
    detected_weaknesses: list[AcademicWeakness] = field(default_factory=list)

    # User memory context
    user_preferences: dict[str, Any] = field(default_factory=dict)
    recent_topics: list[str] = field(default_factory=list)
    preferred_methodology: str = ""
    interaction_count: int = 0

    # Quality expectations
    expected_quality_threshold: float = 0.70

    # Reasoning framework (feature-specific guidance)
    reasoning_framework: str = ""
    quality_criteria: list[str] = field(default_factory=list)

    # Knowledge graph entities
    related_topics: list[str] = field(default_factory=list)
    related_journals: list[str] = field(default_factory=list)

    def get_critical_weaknesses(self) -> list[AcademicWeakness]:
        return [w for w in self.detected_weaknesses
                if w.severity in (WeaknessSeverity.CRITICAL, WeaknessSeverity.HIGH)]

    def weakness_summary(self) -> str:
        if not self.detected_weaknesses:
            return ""
        lines = [f"⚠ Detected {len(self.detected_weaknesses)} potential issue(s):"]
        for w in sorted(self.detected_weaknesses, key=lambda x: x.severity.value):
            lines.append(f"  [{w.severity.value.upper()}] {w.description}")
        return "\n".join(lines)


@dataclass
class QualityDimension:
    name: str
    score: float        # 0.0–1.0
    weight: float       # relative importance
    issues: list[str] = field(default_factory=list)


@dataclass
class QualityScore:
    """Multi-dimensional quality evaluation of an academic AI response."""
    overall_score: float = 0.0
    threshold: float = 0.70
    dimensions: list[QualityDimension] = field(default_factory=list)
    needs_improvement: bool = False
    improvement_hints: list[str] = field(default_factory=list)
    feature: str = ""

    @classmethod
    def from_dimensions(cls, dims: list[QualityDimension], threshold: float = 0.70,
                        feature: str = "") -> "QualityScore":
        if not dims:
            return cls(overall_score=0.0, threshold=threshold)
        total_weight = sum(d.weight for d in dims)
        overall = sum(d.score * d.weight for d in dims) / total_weight if total_weight > 0 else 0.0
        needs_imp = overall < threshold
        hints: list[str] = []
        for dim in sorted(dims, key=lambda x: x.score):
            if dim.score < 0.65:
                hints.extend(dim.issues[:2])
        return cls(
            overall_score=round(overall, 3),
            threshold=threshold,
            dimensions=dims,
            needs_improvement=needs_imp,
            improvement_hints=hints[:5],
            feature=feature,
        )

    def to_dict(self) -> dict:
        return {
            "overall_score": self.overall_score,
            "threshold": self.threshold,
            "needs_improvement": self.needs_improvement,
            "improvement_hints": self.improvement_hints,
            "dimensions": [
                {"name": d.name, "score": d.score, "weight": d.weight, "issues": d.issues}
                for d in self.dimensions
            ],
        }


@dataclass
class ValidationResult:
    is_valid: bool = True
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    auto_improved: bool = False
    improved_text: str = ""

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "issues": self.issues,
            "warnings": self.warnings,
            "auto_improved": self.auto_improved,
        }


@dataclass
class AcademicMemoryRecord:
    user_id: str
    feature: str
    timestamp: str
    domain: str = ""
    methodology: str = ""
    quality_score: float = 0.0
    detected_weaknesses: list[str] = field(default_factory=list)
    topics: list[str] = field(default_factory=list)
    accepted_suggestions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "feature": self.feature,
            "timestamp": self.timestamp,
            "domain": self.domain,
            "methodology": self.methodology,
            "quality_score": self.quality_score,
            "detected_weaknesses": self.detected_weaknesses,
            "topics": self.topics,
        }


@dataclass
class AcademicUserProfile:
    user_id: str
    interaction_count: int = 0
    primary_domain: str = ""
    preferred_methodology: str = ""
    active_research_topics: list[str] = field(default_factory=list)
    preferred_journals: list[str] = field(default_factory=list)
    known_weaknesses: list[str] = field(default_factory=list)     # recurring issues
    avg_quality_score: float = 0.0
    last_seen: str = ""

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "interaction_count": self.interaction_count,
            "primary_domain": self.primary_domain,
            "preferred_methodology": self.preferred_methodology,
            "active_research_topics": self.active_research_topics,
            "preferred_journals": self.preferred_journals,
            "known_weaknesses": self.known_weaknesses,
            "avg_quality_score": self.avg_quality_score,
            "last_seen": self.last_seen,
        }


@dataclass
class StrategyRecommendation:
    type: str          # "next_publication", "next_journal", "next_experiment", etc.
    title: str
    description: str
    priority: int      # 1 = highest
    rationale: str
    evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "rationale": self.rationale,
            "evidence": self.evidence,
        }


@dataclass
class AcademicAnalysis:
    """Complete academic analysis output — returned from engine.analyze()."""
    context: AcademicContext
    quality: QualityScore
    validation: ValidationResult
    strategy: list[StrategyRecommendation] = field(default_factory=list)
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    overall_confidence_score: float = 0.65
    enriched_system_guidance: str = ""
    processing_time_ms: int = 0

    def to_dict(self) -> dict:
        return {
            "domain": self.context.domain.value,
            "methodology_type": self.context.methodology_type.value,
            "research_design": self.context.research_design.value,
            "detected_weaknesses": [w.to_dict() for w in self.context.detected_weaknesses],
            "quality": self.quality.to_dict(),
            "validation": self.validation.to_dict(),
            "strategy": [s.to_dict() for s in self.strategy],
            "confidence": self.confidence.value,
            "confidence_score": self.overall_confidence_score,
            "processing_time_ms": self.processing_time_ms,
        }
