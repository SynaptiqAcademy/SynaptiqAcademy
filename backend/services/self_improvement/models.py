"""Self-Improving Academic Intelligence Platform — Data models (Phase XX)."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum


class OutcomeType(Enum):
    ACCEPTED        = "accepted"
    REJECTED        = "rejected"
    MAJOR_REVISION  = "major_revision"
    MINOR_REVISION  = "minor_revision"
    WITHDRAWN       = "withdrawn"
    PENDING         = "pending"


class SignalType(Enum):
    MANUSCRIPT_RECOMMENDATION = "manuscript_recommendation"
    JOURNAL_SUBMISSION        = "journal_submission"
    GRANT_APPLICATION         = "grant_application"
    CONFERENCE_SUBMISSION     = "conference_submission"
    CITATION_IMPACT           = "citation_impact"
    USER_FEEDBACK             = "user_feedback"
    COLLABORATION_OUTCOME     = "collaboration_outcome"
    CAREER_MILESTONE          = "career_milestone"
    TEACHING_FEEDBACK         = "teaching_feedback"
    PREDICTION_ACCURACY       = "prediction_accuracy"
    REVIEWER_RESPONSE         = "reviewer_response"
    INSTITUTIONAL_FEEDBACK    = "institutional_feedback"


class RecommendationStatus(Enum):
    ACCEPTED = "accepted"
    IGNORED  = "ignored"
    MODIFIED = "modified"
    PENDING  = "pending"


class EngineType(Enum):
    LITERATURE_REVIEW        = "literature_review"
    RESEARCH_GAP             = "research_gap"
    MANUSCRIPT               = "manuscript"
    STATISTICAL              = "statistical"
    JOURNAL_PREDICTOR        = "journal_predictor"
    GRANT_PREDICTOR          = "grant_predictor"
    CONFERENCE_PREDICTOR     = "conference_predictor"
    CAREER_FORECASTER        = "career_forecaster"
    COLLABORATION_FORECASTER = "collaboration_forecaster"
    INSTITUTION_FORECASTER   = "institution_forecaster"
    TREND_FORECASTER         = "trend_forecaster"
    KNOWLEDGE_GRAPH          = "knowledge_graph"
    RECOMMENDATION_ENGINE    = "recommendation_engine"
    COPILOT                  = "copilot"
    SMART_ROUTER             = "smart_router"
    PUBLICATION_PREDICTOR    = "publication_predictor"


class OptimizationType(Enum):
    THRESHOLD_ADJUSTMENT    = "threshold_adjustment"
    WEIGHT_ADJUSTMENT       = "weight_adjustment"
    RANKING_ADJUSTMENT      = "ranking_adjustment"
    CACHE_STRATEGY          = "cache_strategy"
    ROUTING_RULE            = "routing_rule"
    KNOWLEDGE_UPDATE        = "knowledge_update"
    CONFIDENCE_CALIBRATION  = "confidence_calibration"


class ExperimentStatus(Enum):
    DRAFT       = "draft"
    RUNNING     = "running"
    COMPLETED   = "completed"
    ROLLED_BACK = "rolled_back"


class DiagnosticStatus(Enum):
    HEALTHY  = "healthy"
    WARNING  = "warning"
    CRITICAL = "critical"
    UNKNOWN  = "unknown"


# ── Dataclasses ────────────────────────────────────────────────────────────────

@dataclass
class FeedbackSignal:
    signal_id:                   str   = field(default_factory=lambda: str(uuid.uuid4()))
    signal_type:                 str   = ""
    engine_type:                 str   = ""
    user_cohort:                 str   = "general"
    outcome:                     str   = ""
    recommendation_status:       str   = ""
    quality_delta:               float = 0.0
    confidence_at_recommendation: float = 0.0
    timestamp:                   float = field(default_factory=time.time)
    metadata:                    dict  = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "signal_id":                    self.signal_id,
            "signal_type":                  self.signal_type,
            "engine_type":                  self.engine_type,
            "user_cohort":                  self.user_cohort,
            "outcome":                      self.outcome,
            "recommendation_status":        self.recommendation_status,
            "quality_delta":                self.quality_delta,
            "confidence_at_recommendation": self.confidence_at_recommendation,
            "timestamp":                    self.timestamp,
        }


@dataclass
class EnginePerformanceMetrics:
    engine_type:          str   = ""
    accuracy:             float = 0.0
    precision:            float = 0.0
    recall:               float = 0.0
    user_acceptance_rate: float = 0.0
    avg_confidence:       float = 0.0
    calibration_error:    float = 0.0
    samples_evaluated:    int   = 0
    trend:                str   = "stable"
    last_updated:         float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "engine_type":          self.engine_type,
            "accuracy":             round(self.accuracy, 4),
            "precision":            round(self.precision, 4),
            "recall":               round(self.recall, 4),
            "user_acceptance_rate": round(self.user_acceptance_rate, 4),
            "avg_confidence":       round(self.avg_confidence, 4),
            "calibration_error":    round(self.calibration_error, 4),
            "samples_evaluated":    self.samples_evaluated,
            "trend":                self.trend,
            "last_updated":         self.last_updated,
        }


@dataclass
class OptimizationRecord:
    record_id:            str   = field(default_factory=lambda: str(uuid.uuid4()))
    optimization_type:    str   = ""
    engine_type:          str   = ""
    parameter:            str   = ""
    old_value:            float = 0.0
    new_value:            float = 0.0
    rationale:            str   = ""
    approved_by:          str   = "system"
    expected_improvement: float = 0.0
    measured_improvement: float = 0.0
    status:               str   = "pending"
    timestamp:            float = field(default_factory=time.time)
    rollback_available:   bool  = True

    def to_dict(self) -> dict:
        return {
            "record_id":            self.record_id,
            "optimization_type":    self.optimization_type,
            "engine_type":          self.engine_type,
            "parameter":            self.parameter,
            "old_value":            self.old_value,
            "new_value":            self.new_value,
            "rationale":            self.rationale,
            "approved_by":          self.approved_by,
            "expected_improvement": round(self.expected_improvement, 4),
            "measured_improvement": round(self.measured_improvement, 4),
            "status":               self.status,
            "timestamp":            self.timestamp,
            "rollback_available":   self.rollback_available,
        }


@dataclass
class ABExperiment:
    experiment_id: str   = field(default_factory=lambda: str(uuid.uuid4()))
    name:          str   = ""
    description:   str   = ""
    engine_type:   str   = ""
    variant_a:     dict  = field(default_factory=dict)
    variant_b:     dict  = field(default_factory=dict)
    traffic_split: float = 0.5
    status:        str   = ExperimentStatus.DRAFT.value
    started_at:    float = 0.0
    ended_at:      float = 0.0
    metric_a:      float = 0.0
    metric_b:      float = 0.0
    p_value:       float = 1.0
    sample_a:      int   = 0
    sample_b:      int   = 0
    winner:        str   = ""
    deployed:      bool  = False

    def to_dict(self) -> dict:
        return {
            "experiment_id": self.experiment_id,
            "name":          self.name,
            "description":   self.description,
            "engine_type":   self.engine_type,
            "variant_a":     self.variant_a,
            "variant_b":     self.variant_b,
            "traffic_split": self.traffic_split,
            "status":        self.status,
            "started_at":    self.started_at,
            "ended_at":      self.ended_at,
            "metric_a":      round(self.metric_a, 4),
            "metric_b":      round(self.metric_b, 4),
            "p_value":       round(self.p_value, 4),
            "sample_a":      self.sample_a,
            "sample_b":      self.sample_b,
            "winner":        self.winner,
            "deployed":      self.deployed,
        }


@dataclass
class KnowledgeUpdate:
    update_id:     str   = field(default_factory=lambda: str(uuid.uuid4()))
    category:      str   = ""
    item:          str   = ""
    evidence_count: int  = 0
    confidence:    float = 0.0
    status:        str   = "detected"
    detected_at:   float = field(default_factory=time.time)
    integrated_at: float = 0.0

    def to_dict(self) -> dict:
        return {
            "update_id":     self.update_id,
            "category":      self.category,
            "item":          self.item,
            "evidence_count": self.evidence_count,
            "confidence":    round(self.confidence, 4),
            "status":        self.status,
            "detected_at":   self.detected_at,
            "integrated_at": self.integrated_at,
        }


@dataclass
class DiagnosticReport:
    report_id:       str   = field(default_factory=lambda: str(uuid.uuid4()))
    engine_type:     str   = ""
    status:          str   = DiagnosticStatus.UNKNOWN.value
    health_score:    float = 0.0
    issues:          list  = field(default_factory=list)
    metrics:         dict  = field(default_factory=dict)
    recommendations: list  = field(default_factory=list)
    checked_at:      float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "report_id":       self.report_id,
            "engine_type":     self.engine_type,
            "status":          self.status,
            "health_score":    round(self.health_score, 4),
            "issues":          self.issues,
            "metrics":         self.metrics,
            "recommendations": self.recommendations,
            "checked_at":      self.checked_at,
        }


@dataclass
class GovernancePolicy:
    policy_id:                   str   = field(default_factory=lambda: str(uuid.uuid4()))
    learning_enabled:            bool  = True
    retention_days:              int   = 90
    min_samples_for_optimization: int  = 50
    significance_threshold:      float = 0.05
    min_improvement_threshold:   float = 0.02
    feedback_weight:             dict  = field(default_factory=lambda: {
        "user_explicit": 1.0, "outcome_implicit": 0.7, "institutional": 0.8,
    })
    auto_apply_optimizations:    bool  = False
    require_admin_approval:      bool  = True
    max_concurrent_experiments:  int   = 5
    rollback_window_days:        int   = 7
    privacy_level:               str   = "strict"
    updated_at:                  float = field(default_factory=time.time)
    updated_by:                  str   = "system"

    def to_dict(self) -> dict:
        return {
            "policy_id":                    self.policy_id,
            "learning_enabled":             self.learning_enabled,
            "retention_days":               self.retention_days,
            "min_samples_for_optimization": self.min_samples_for_optimization,
            "significance_threshold":       self.significance_threshold,
            "min_improvement_threshold":    self.min_improvement_threshold,
            "feedback_weight":              self.feedback_weight,
            "auto_apply_optimizations":     self.auto_apply_optimizations,
            "require_admin_approval":       self.require_admin_approval,
            "max_concurrent_experiments":   self.max_concurrent_experiments,
            "rollback_window_days":         self.rollback_window_days,
            "privacy_level":               self.privacy_level,
            "updated_at":                   self.updated_at,
            "updated_by":                   self.updated_by,
        }


@dataclass
class PlatformQualityReport:
    report_id:                    str   = field(default_factory=lambda: str(uuid.uuid4()))
    overall_score:                float = 0.0
    engine_scores:                dict  = field(default_factory=dict)
    recommendation_acceptance_rate: float = 0.0
    prediction_accuracy:          float = 0.0
    validation_quality:           float = 0.0
    retrieval_quality:            float = 0.0
    routing_efficiency:           float = 0.0
    user_satisfaction:            float = 0.0
    active_experiments:           int   = 0
    pending_optimizations:        int   = 0
    knowledge_updates_pending:    int   = 0
    generated_at:                 float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "report_id":                      self.report_id,
            "overall_score":                  round(self.overall_score, 2),
            "engine_scores":                  {k: round(v, 4) for k, v in self.engine_scores.items()},
            "recommendation_acceptance_rate": round(self.recommendation_acceptance_rate, 4),
            "prediction_accuracy":            round(self.prediction_accuracy, 4),
            "validation_quality":             round(self.validation_quality, 4),
            "retrieval_quality":              round(self.retrieval_quality, 4),
            "routing_efficiency":             round(self.routing_efficiency, 4),
            "user_satisfaction":              round(self.user_satisfaction, 4),
            "active_experiments":             self.active_experiments,
            "pending_optimizations":          self.pending_optimizations,
            "knowledge_updates_pending":      self.knowledge_updates_pending,
            "generated_at":                   self.generated_at,
        }
