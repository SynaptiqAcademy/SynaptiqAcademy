"""Statistical Intelligence 2.0 — Domain models (Phase X).

Pure-Python dataclasses with to_dict() for serialisation.
No Pydantic in the service layer — keeps validation in the router.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


# ── Enumerations ──────────────────────────────────────────────────────────────

class AnalysisDepth(str, Enum):
    QUICK    = "quick"
    STANDARD = "standard"
    DEEP     = "deep"


class ExportFormat(str, Enum):
    STATISTICAL_REVIEW  = "statistical_review"
    METHODOLOGY_REVIEW  = "methodology_review"
    REVIEWER_REPORT     = "reviewer_report"
    SUPERVISOR_REPORT   = "supervisor_report"
    JOURNAL_SUBMISSION  = "journal_submission"
    MARKDOWN            = "markdown"
    LATEX               = "latex"
    TEXT                = "text"


class InputFormat(str, Enum):
    TEXT      = "text"
    CSV       = "csv"
    EXCEL     = "excel"
    JSON      = "json"
    SPSS      = "spss"
    STATA     = "stata"
    R_DATASET = "r_dataset"


class StudyType(str, Enum):
    EXPERIMENTAL      = "experimental"
    RCT               = "rct"
    QUASI_EXPERIMENTAL = "quasi_experimental"
    SURVEY            = "survey"
    CROSS_SECTIONAL   = "cross_sectional"
    LONGITUDINAL      = "longitudinal"
    COHORT            = "cohort"
    CASE_CONTROL      = "case_control"
    CASE_STUDY        = "case_study"
    MIXED_METHODS     = "mixed_methods"
    META_ANALYSIS     = "meta_analysis"
    SYSTEMATIC_REVIEW = "systematic_review"
    QUALITATIVE       = "qualitative"
    OBSERVATIONAL     = "observational"
    UNKNOWN           = "unknown"


class AnalysisMethod(str, Enum):
    T_TEST              = "t_test"
    PAIRED_T_TEST       = "paired_t_test"
    ONE_SAMPLE_T        = "one_sample_t"
    ANOVA               = "anova"
    REPEATED_ANOVA      = "repeated_anova"
    ANCOVA              = "ancova"
    MANOVA              = "manova"
    CHI_SQUARE          = "chi_square"
    FISHER_EXACT        = "fisher_exact"
    PEARSON_CORRELATION = "pearson_correlation"
    SPEARMAN_CORRELATION = "spearman_correlation"
    LINEAR_REGRESSION   = "linear_regression"
    MULTIPLE_REGRESSION = "multiple_regression"
    LOGISTIC_REGRESSION = "logistic_regression"
    ORDINAL_REGRESSION  = "ordinal_regression"
    MIXED_MODELS        = "mixed_models"
    FACTOR_ANALYSIS     = "factor_analysis"
    CFA                 = "cfa"
    PCA                 = "pca"
    CLUSTER_ANALYSIS    = "cluster_analysis"
    SEM                 = "sem"
    PLS_SEM             = "pls_sem"
    TIME_SERIES         = "time_series"
    SURVIVAL_ANALYSIS   = "survival_analysis"
    META_ANALYSIS       = "meta_analysis"
    MANN_WHITNEY        = "mann_whitney"
    KRUSKAL_WALLIS      = "kruskal_wallis"
    WILCOXON            = "wilcoxon"
    FRIEDMAN            = "friedman"
    BAYESIAN            = "bayesian"
    MACHINE_LEARNING    = "machine_learning"
    UNKNOWN             = "unknown"


class AssumptionStatus(str, Enum):
    MET               = "met"
    VIOLATED          = "violated"
    NOT_TESTED        = "not_tested"
    NOT_APPLICABLE    = "not_applicable"
    CANNOT_DETERMINE  = "cannot_determine"


class IssueSeverity(str, Enum):
    CRITICAL = "critical"
    MAJOR    = "major"
    MODERATE = "moderate"
    MINOR    = "minor"


class Priority(str, Enum):
    ESSENTIAL    = "essential"
    RECOMMENDED  = "recommended"
    OPTIONAL     = "optional"


class VerdictLevel(str, Enum):
    STRONG       = "strong"
    ADEQUATE     = "adequate"
    WEAK         = "weak"
    INSUFFICIENT = "insufficient"


# ── Data parser models ────────────────────────────────────────────────────────

@dataclass
class ColumnInfo:
    name: str
    dtype: str = "unknown"
    missing_count: int = 0
    missing_rate: float = 0.0
    unique_count: int = 0
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    mean_val: Optional[float] = None
    std_val: Optional[float] = None
    is_numeric: bool = False
    is_binary: bool = False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "dtype": self.dtype,
            "missing_rate": round(self.missing_rate, 4),
            "unique_count": self.unique_count,
            "is_numeric": self.is_numeric,
            "mean": self.mean_val,
            "std": self.std_val,
        }


@dataclass
class ParsedData:
    raw_text: str = ""
    input_format: InputFormat = InputFormat.TEXT
    has_structured_data: bool = False
    columns: list[ColumnInfo] = field(default_factory=list)
    row_count: int = 0
    word_count: int = 0
    sample_size: int = 0
    numeric_columns: list[str] = field(default_factory=list)
    categorical_columns: list[str] = field(default_factory=list)
    binary_columns: list[str] = field(default_factory=list)
    overall_missing_rate: float = 0.0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "input_format": self.input_format.value,
            "has_structured_data": self.has_structured_data,
            "row_count": self.row_count,
            "word_count": self.word_count,
            "sample_size": self.sample_size,
            "column_count": len(self.columns),
            "numeric_columns": self.numeric_columns,
            "categorical_columns": self.categorical_columns,
            "overall_missing_rate": round(self.overall_missing_rate, 4),
        }


# ── Research design ───────────────────────────────────────────────────────────

@dataclass
class ResearchDesign:
    study_type: StudyType = StudyType.UNKNOWN
    detected_methods: list[AnalysisMethod] = field(default_factory=list)
    primary_method: AnalysisMethod = AnalysisMethod.UNKNOWN
    dependent_variables: list[str] = field(default_factory=list)
    independent_variables: list[str] = field(default_factory=list)
    control_variables: list[str] = field(default_factory=list)
    moderators: list[str] = field(default_factory=list)
    mediators: list[str] = field(default_factory=list)
    confounders: list[str] = field(default_factory=list)
    sample_size: int = 0
    sampling_strategy: str = "not specified"
    is_longitudinal: bool = False
    has_control_group: bool = False
    has_randomisation: bool = False
    discipline: str = "general"

    def to_dict(self) -> dict:
        return {
            "study_type": self.study_type.value,
            "primary_method": self.primary_method.value,
            "detected_methods": [m.value for m in self.detected_methods],
            "dependent_variables": self.dependent_variables,
            "independent_variables": self.independent_variables,
            "control_variables": self.control_variables,
            "sample_size": self.sample_size,
            "sampling_strategy": self.sampling_strategy,
            "is_longitudinal": self.is_longitudinal,
            "has_control_group": self.has_control_group,
            "has_randomisation": self.has_randomisation,
            "discipline": self.discipline,
        }


# ── Sampling ──────────────────────────────────────────────────────────────────

@dataclass
class SamplingAnalysis:
    sample_size: int = 0
    recommended_min: int = 0
    power_estimate: float = 0.0
    effect_size_assumed: str = "medium"
    alpha_level: float = 0.05
    is_adequate: bool = False
    adequacy_verdict: str = "cannot_determine"
    issues: list[str] = field(default_factory=list)
    score: float = 0.0
    grade: str = "N/A"

    def to_dict(self) -> dict:
        return {
            "sample_size": self.sample_size,
            "recommended_min": self.recommended_min,
            "power_estimate": round(self.power_estimate, 3),
            "is_adequate": self.is_adequate,
            "adequacy_verdict": self.adequacy_verdict,
            "issues": self.issues,
            "score": round(self.score, 1),
            "grade": self.grade,
        }


# ── Data quality ──────────────────────────────────────────────────────────────

@dataclass
class DataQualityMetrics:
    overall_missing_rate: float = 0.0
    has_outliers_mentioned: bool = False
    normality_tested: bool = False
    normality_met: Optional[bool] = None
    homoscedasticity_tested: bool = False
    multicollinearity_tested: bool = False
    max_vif: Optional[float] = None
    independence_met: Optional[bool] = None
    linearity_mentioned: bool = False
    score: float = 0.0
    grade: str = "N/A"
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "overall_missing_rate": round(self.overall_missing_rate, 4),
            "has_outliers_mentioned": self.has_outliers_mentioned,
            "normality_tested": self.normality_tested,
            "normality_met": self.normality_met,
            "homoscedasticity_tested": self.homoscedasticity_tested,
            "multicollinearity_tested": self.multicollinearity_tested,
            "max_vif": self.max_vif,
            "score": round(self.score, 1),
            "grade": self.grade,
            "issues": self.issues,
        }


# ── Assumptions ───────────────────────────────────────────────────────────────

@dataclass
class AssumptionCheck:
    name: str
    method: str
    status: AssumptionStatus = AssumptionStatus.CANNOT_DETERMINE
    evidence: str = ""
    consequence: str = ""
    recommendation: str = ""
    severity: IssueSeverity = IssueSeverity.MODERATE

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "method": self.method,
            "status": self.status.value,
            "evidence": self.evidence,
            "consequence": self.consequence,
            "recommendation": self.recommendation,
            "severity": self.severity.value,
        }


# ── Method review ─────────────────────────────────────────────────────────────

@dataclass
class MethodEvaluation:
    method: AnalysisMethod
    is_appropriate: bool = True
    appropriateness_score: float = 70.0
    rationale: str = ""
    alternatives: list[str] = field(default_factory=list)
    missing_reporting: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "method": self.method.value,
            "is_appropriate": self.is_appropriate,
            "appropriateness_score": round(self.appropriateness_score, 1),
            "rationale": self.rationale,
            "alternatives": self.alternatives,
            "missing_reporting": self.missing_reporting,
            "issues": self.issues,
        }


# ── Results interpretation ────────────────────────────────────────────────────

@dataclass
class EffectSizeReport:
    measure: str
    value: str
    magnitude: str = "unknown"
    context: str = ""

    def to_dict(self) -> dict:
        return {"measure": self.measure, "value": self.value,
                "magnitude": self.magnitude, "context": self.context}


@dataclass
class ResultsInterpretation:
    has_p_values: bool = False
    p_value_count: int = 0
    has_effect_sizes: bool = False
    has_confidence_intervals: bool = False
    has_descriptive_stats: bool = False
    statistical_significance_summary: str = ""
    practical_significance_note: str = ""
    effect_sizes: list[EffectSizeReport] = field(default_factory=list)
    model_fit_indices: dict[str, str] = field(default_factory=dict)
    score: float = 0.0
    grade: str = "N/A"

    def to_dict(self) -> dict:
        return {
            "has_p_values": self.has_p_values,
            "has_effect_sizes": self.has_effect_sizes,
            "has_confidence_intervals": self.has_confidence_intervals,
            "effect_sizes": [e.to_dict() for e in self.effect_sizes],
            "model_fit_indices": self.model_fit_indices,
            "score": round(self.score, 1),
            "grade": self.grade,
        }


# ── Validity ──────────────────────────────────────────────────────────────────

@dataclass
class ValidityThreat:
    threat_type: str
    threat: str
    description: str = ""
    mitigation: str = ""
    severity: IssueSeverity = IssueSeverity.MODERATE

    def to_dict(self) -> dict:
        return {
            "threat_type": self.threat_type,
            "threat": self.threat,
            "description": self.description,
            "mitigation": self.mitigation,
            "severity": self.severity.value,
        }


@dataclass
class ReliabilityMetrics:
    cronbach_alpha: Optional[float] = None
    composite_reliability: Optional[float] = None
    ave: Optional[float] = None
    htmt: Optional[float] = None
    kmo: Optional[float] = None
    bartlett_sig: Optional[bool] = None

    def to_dict(self) -> dict:
        return {
            "cronbach_alpha": self.cronbach_alpha,
            "composite_reliability": self.composite_reliability,
            "ave": self.ave,
            "htmt": self.htmt,
            "kmo": self.kmo,
            "bartlett_sig": self.bartlett_sig,
        }


@dataclass
class ValidityAnalysis:
    threats: list[ValidityThreat] = field(default_factory=list)
    reliability: ReliabilityMetrics = field(default_factory=ReliabilityMetrics)
    internal_validity_score: float = 0.0
    external_validity_score: float = 0.0
    construct_validity_score: float = 0.0
    overall_validity_score: float = 0.0
    grade: str = "N/A"

    def to_dict(self) -> dict:
        return {
            "threats": [t.to_dict() for t in self.threats],
            "reliability": self.reliability.to_dict(),
            "internal_validity_score": round(self.internal_validity_score, 1),
            "external_validity_score": round(self.external_validity_score, 1),
            "construct_validity_score": round(self.construct_validity_score, 1),
            "overall_validity_score": round(self.overall_validity_score, 1),
            "grade": self.grade,
        }


# ── Issues & recommendations ──────────────────────────────────────────────────

@dataclass
class StatisticalIssue:
    severity: IssueSeverity
    category: str
    title: str
    description: str
    recommendation: str
    affected_element: str = ""

    def to_dict(self) -> dict:
        return {
            "severity": self.severity.value,
            "category": self.category,
            "title": self.title,
            "description": self.description,
            "recommendation": self.recommendation,
            "affected_element": self.affected_element,
        }


@dataclass
class RecommendedAnalysis:
    analysis: str
    rationale: str
    priority: Priority = Priority.RECOMMENDED
    software_guidance: str = ""

    def to_dict(self) -> dict:
        return {
            "analysis": self.analysis,
            "rationale": self.rationale,
            "priority": self.priority.value,
            "software_guidance": self.software_guidance,
        }


@dataclass
class ReviewerCriticism:
    comment: str
    severity: str = "major"
    suggested_response: str = ""

    def to_dict(self) -> dict:
        return {
            "comment": self.comment,
            "severity": self.severity,
            "suggested_response": self.suggested_response,
        }


# ── Dimension scores ──────────────────────────────────────────────────────────

@dataclass
class DimensionScore:
    name: str
    score: float = 0.0
    weight: float = 1.0
    grade: str = "N/A"
    rationale: str = ""
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "score": round(self.score, 1),
            "weight": self.weight,
            "grade": self.grade,
            "rationale": self.rationale,
            "strengths": self.strengths[:5],
            "weaknesses": self.weaknesses[:5],
        }


@dataclass
class StatisticalDimensions:
    methodological_rigor: DimensionScore = field(
        default_factory=lambda: DimensionScore("Methodological Rigour", weight=2.0))
    sample_adequacy: DimensionScore = field(
        default_factory=lambda: DimensionScore("Sample Adequacy", weight=1.5))
    data_quality: DimensionScore = field(
        default_factory=lambda: DimensionScore("Data Quality", weight=1.5))
    result_validity: DimensionScore = field(
        default_factory=lambda: DimensionScore("Result Validity & Reporting", weight=2.0))
    construct_validity: DimensionScore = field(
        default_factory=lambda: DimensionScore("Construct Validity", weight=1.5))
    reporting_quality: DimensionScore = field(
        default_factory=lambda: DimensionScore("Reporting Quality", weight=1.0))

    def weighted_score(self) -> float:
        dims = [
            self.methodological_rigor, self.sample_adequacy, self.data_quality,
            self.result_validity, self.construct_validity, self.reporting_quality,
        ]
        total_weight = sum(d.weight for d in dims)
        if total_weight == 0:
            return 0.0
        return sum(d.score * d.weight for d in dims) / total_weight

    def to_dict(self) -> dict:
        return {
            "methodological_rigor": self.methodological_rigor.to_dict(),
            "sample_adequacy": self.sample_adequacy.to_dict(),
            "data_quality": self.data_quality.to_dict(),
            "result_validity": self.result_validity.to_dict(),
            "construct_validity": self.construct_validity.to_dict(),
            "reporting_quality": self.reporting_quality.to_dict(),
        }


# ── Publication readiness ─────────────────────────────────────────────────────

@dataclass
class PublicationReadiness:
    overall_score: float = 0.0
    acceptance_probability: float = 0.0
    desk_rejection_risk: float = 0.0
    verdict: VerdictLevel = VerdictLevel.INSUFFICIENT
    strongest_element: str = ""
    critical_barrier: str = ""
    assessment: str = ""

    def to_dict(self) -> dict:
        return {
            "overall_score": round(self.overall_score, 1),
            "acceptance_probability": round(self.acceptance_probability, 3),
            "desk_rejection_risk": round(self.desk_rejection_risk, 3),
            "verdict": self.verdict.value,
            "strongest_element": self.strongest_element,
            "critical_barrier": self.critical_barrier,
            "assessment": self.assessment,
        }


# ── Revision roadmap ──────────────────────────────────────────────────────────

@dataclass
class RevisionPhase:
    phase: int
    title: str
    priority: str
    estimated_effort: str
    actions: list[str]
    issue_count: int = 0

    def to_dict(self) -> dict:
        return {
            "phase": self.phase,
            "title": self.title,
            "priority": self.priority,
            "estimated_effort": self.estimated_effort,
            "actions": self.actions,
            "issue_count": self.issue_count,
        }


# ── Main result ───────────────────────────────────────────────────────────────

@dataclass
class StatisticalIntelligenceResult:
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    topic: str = ""
    research_question: str = ""
    analysis_depth: AnalysisDepth = AnalysisDepth.STANDARD
    input_format: InputFormat = InputFormat.TEXT

    # Design
    research_design: ResearchDesign = field(default_factory=ResearchDesign)
    sampling_analysis: SamplingAnalysis = field(default_factory=SamplingAnalysis)
    data_quality: DataQualityMetrics = field(default_factory=DataQualityMetrics)

    # Review outputs
    assumption_checks: list[AssumptionCheck] = field(default_factory=list)
    method_evaluations: list[MethodEvaluation] = field(default_factory=list)
    results_interpretation: ResultsInterpretation = field(default_factory=ResultsInterpretation)
    validity_analysis: ValidityAnalysis = field(default_factory=ValidityAnalysis)

    # Scoring
    dimensions: StatisticalDimensions = field(default_factory=StatisticalDimensions)
    overall_score: float = 0.0
    overall_verdict: VerdictLevel = VerdictLevel.INSUFFICIENT

    # Issues & recommendations
    critical_issues: list[StatisticalIssue] = field(default_factory=list)
    major_issues: list[StatisticalIssue] = field(default_factory=list)
    moderate_issues: list[StatisticalIssue] = field(default_factory=list)
    minor_issues: list[StatisticalIssue] = field(default_factory=list)
    recommended_analyses: list[RecommendedAnalysis] = field(default_factory=list)
    reviewer_criticisms: list[ReviewerCriticism] = field(default_factory=list)

    # Outputs
    publication_readiness: PublicationReadiness = field(default_factory=PublicationReadiness)
    revision_roadmap: list[RevisionPhase] = field(default_factory=list)
    visualizations: dict = field(default_factory=dict)

    # Text outputs
    executive_summary: str = ""
    statistical_review_text: str = ""
    ai_review: dict = field(default_factory=dict)

    # Metadata
    credits_used: int = 0
    created_at: str = ""

    def to_dict(self) -> dict:
        return {
            "result_id": self.result_id,
            "user_id": self.user_id,
            "topic": self.topic,
            "research_question": self.research_question,
            "analysis_depth": self.analysis_depth.value,
            "input_format": self.input_format.value,
            "research_design": self.research_design.to_dict(),
            "sampling_analysis": self.sampling_analysis.to_dict(),
            "data_quality": self.data_quality.to_dict(),
            "assumption_checks": [a.to_dict() for a in self.assumption_checks],
            "method_evaluations": [m.to_dict() for m in self.method_evaluations],
            "results_interpretation": self.results_interpretation.to_dict(),
            "validity_analysis": self.validity_analysis.to_dict(),
            "dimensions": self.dimensions.to_dict(),
            "overall_score": round(self.overall_score, 1),
            "overall_verdict": self.overall_verdict.value,
            "critical_issues": [i.to_dict() for i in self.critical_issues],
            "major_issues": [i.to_dict() for i in self.major_issues],
            "moderate_issues": [i.to_dict() for i in self.moderate_issues],
            "minor_issues": [i.to_dict() for i in self.minor_issues],
            "recommended_analyses": [r.to_dict() for r in self.recommended_analyses],
            "reviewer_criticisms": [r.to_dict() for r in self.reviewer_criticisms],
            "publication_readiness": self.publication_readiness.to_dict(),
            "revision_roadmap": [p.to_dict() for p in self.revision_roadmap],
            "visualizations": self.visualizations,
            "executive_summary": self.executive_summary,
            "statistical_review_text": self.statistical_review_text,
            "credits_used": self.credits_used,
            "created_at": self.created_at,
        }

    def to_summary(self) -> dict:
        return {
            "result_id": self.result_id,
            "topic": self.topic,
            "overall_score": round(self.overall_score, 1),
            "overall_verdict": self.overall_verdict.value,
            "study_type": self.research_design.study_type.value,
            "primary_method": self.research_design.primary_method.value,
            "sample_size": self.research_design.sample_size,
            "critical_issue_count": len(self.critical_issues),
            "major_issue_count": len(self.major_issues),
            "publication_score": round(self.publication_readiness.overall_score, 1),
            "acceptance_probability": round(self.publication_readiness.acceptance_probability, 3),
            "analysis_depth": self.analysis_depth.value,
            "created_at": self.created_at,
        }


# ── Request ───────────────────────────────────────────────────────────────────

@dataclass
class StatisticalAnalysisRequest:
    content: str
    topic: str = ""
    research_question: str = ""
    methodology: str = ""
    hypotheses: str = ""
    sample_size_text: str = ""
    discipline: str = ""
    analysis_depth: AnalysisDepth = AnalysisDepth.STANDARD
    input_format: InputFormat = InputFormat.TEXT
    user_id: str = ""
    filename: str = ""
    target_journal: str = ""


# ── Grade utility ─────────────────────────────────────────────────────────────

def _score_to_grade(score: float) -> str:
    if score >= 93: return "A+"
    if score >= 88: return "A"
    if score >= 83: return "A-"
    if score >= 78: return "B+"
    if score >= 73: return "B"
    if score >= 68: return "B-"
    if score >= 63: return "C+"
    if score >= 58: return "C"
    if score >= 50: return "C-"
    if score >= 40: return "D"
    return "F"
