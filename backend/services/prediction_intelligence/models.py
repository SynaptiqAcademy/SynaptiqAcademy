"""Academic Prediction & Forecasting Intelligence Engine — Domain models (Phase XVIII)."""
from __future__ import annotations

import datetime
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


def _now_str() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


# ── Enums ─────────────────────────────────────────────────────────────────────

class PredictionType(str, Enum):
    PUBLICATION_ACCEPTANCE = "publication_acceptance"
    DESK_REJECTION         = "desk_rejection"
    MAJOR_REVISION         = "major_revision"
    MINOR_REVISION         = "minor_revision"
    REVIEW_TIME            = "review_time"
    ACCEPTANCE_TIME        = "acceptance_time"
    PUBLICATION_TIME       = "publication_time"
    DELAY_RISK             = "delay_risk"
    CITATION_VELOCITY      = "citation_velocity"
    CITATION_GROWTH        = "citation_growth"
    LONG_TERM_IMPACT       = "long_term_impact"
    FUNDING_PROBABILITY    = "funding_probability"
    GRANT_SCORE            = "grant_score"
    PROMOTION_READINESS    = "promotion_readiness"
    H_INDEX_FORECAST       = "h_index_forecast"
    COLLABORATION_SUCCESS  = "collaboration_success"
    TREND_EMERGENCE        = "trend_emergence"


class ConfidenceLevel(str, Enum):
    VERY_HIGH = "very_high"
    HIGH      = "high"
    MODERATE  = "moderate"
    LOW       = "low"
    VERY_LOW  = "very_low"


class ForecastHorizon(str, Enum):
    ONE_YEAR   = "1y"
    THREE_YEAR = "3y"
    FIVE_YEAR  = "5y"
    TEN_YEAR   = "10y"


class VizType(str, Enum):
    PREDICTION_DASHBOARD  = "prediction_dashboard"
    CAREER_FORECAST       = "career_forecast"
    PUBLICATION_FORECAST  = "publication_forecast"
    CITATION_FORECAST     = "citation_forecast"
    GRANT_FORECAST        = "grant_forecast"
    RISK_MATRIX           = "risk_matrix"
    SCENARIO_COMPARISON   = "scenario_comparison"
    TIMELINE_PROJECTION   = "timeline_projection"


class ScenarioType(str, Enum):
    SUBMIT_NOW          = "submit_now"
    DELAY_3_MONTHS      = "delay_3_months"
    DELAY_6_MONTHS      = "delay_6_months"
    ADD_COLLABORATOR    = "add_collaborator"
    CHANGE_JOURNAL      = "change_journal"
    IMPROVE_MANUSCRIPT  = "improve_manuscript"
    MORE_DATA           = "more_data"


class WhatIfFactor(str, Enum):
    INTERNATIONAL_COLLABORATION = "international_collaboration"
    OPEN_ACCESS                 = "open_access"
    INCREASE_SAMPLE_SIZE        = "increase_sample_size"
    CHANGE_METHODOLOGY          = "change_methodology"
    IMPROVE_STATISTICS          = "improve_statistics"
    DELAY_SUBMISSION            = "delay_submission"
    ADD_AUTHOR                  = "add_author"


class DecisionUrgency(str, Enum):
    IMMEDIATE        = "immediate"
    SOON             = "soon"
    CAN_WAIT         = "can_wait"
    NOT_RECOMMENDED  = "not_recommended"


# ── Atomic prediction unit ────────────────────────────────────────────────────

@dataclass
class Prediction:
    prediction_id:    str
    prediction_type:  str
    value:            float
    confidence:       float
    confidence_level: str
    evidence:         list[str]
    risk_factors:     list[str]
    recommendations:  list[str]
    alternative_outcomes: list[dict]
    uncertainty_lower: float
    uncertainty_upper: float
    unit:             str
    reasoning:        str
    created_at:       str = field(default_factory=_now_str)

    def to_dict(self) -> dict:
        return {
            "prediction_id":     self.prediction_id,
            "prediction_type":   self.prediction_type,
            "value":             round(self.value, 4),
            "confidence":        round(self.confidence, 4),
            "confidence_level":  self.confidence_level,
            "evidence":          self.evidence,
            "risk_factors":      self.risk_factors,
            "recommendations":   self.recommendations,
            "alternative_outcomes": self.alternative_outcomes,
            "uncertainty_lower": round(self.uncertainty_lower, 4),
            "uncertainty_upper": round(self.uncertainty_upper, 4),
            "unit":              self.unit,
            "reasoning":         self.reasoning,
            "created_at":        self.created_at,
        }


def _make_prediction(
    pred_type: PredictionType,
    value: float,
    confidence: float,
    evidence: list[str] | None = None,
    risk_factors: list[str] | None = None,
    recommendations: list[str] | None = None,
    unit: str = "probability",
    reasoning: str = "",
    clamp_probability: bool = True,
    alternative_outcomes: list[dict] | None = None,
) -> Prediction:
    """Factory — always clamps confidence to [0,1] and computes uncertainty range."""
    confidence = max(0.0, min(1.0, confidence))
    if clamp_probability:
        value = max(0.0, min(1.0, value))

    uncertainty = (1.0 - confidence) * 0.25
    if clamp_probability:
        lower = max(0.0, value - uncertainty)
        upper = min(1.0, value + uncertainty)
    else:
        lower = max(0.0, value - uncertainty * value)
        upper = value + uncertainty * value

    if confidence >= 0.85:
        level = ConfidenceLevel.VERY_HIGH
    elif confidence >= 0.70:
        level = ConfidenceLevel.HIGH
    elif confidence >= 0.50:
        level = ConfidenceLevel.MODERATE
    elif confidence >= 0.30:
        level = ConfidenceLevel.LOW
    else:
        level = ConfidenceLevel.VERY_LOW

    return Prediction(
        prediction_id=str(uuid.uuid4()),
        prediction_type=pred_type.value,
        value=round(value, 4),
        confidence=round(confidence, 4),
        confidence_level=level.value,
        evidence=evidence or [],
        risk_factors=risk_factors or [],
        recommendations=recommendations or [],
        alternative_outcomes=alternative_outcomes or [],
        uncertainty_lower=round(lower, 4),
        uncertainty_upper=round(upper, 4),
        unit=unit,
        reasoning=reasoning,
    )


# ── Composite prediction models ───────────────────────────────────────────────

@dataclass
class PublicationPrediction:
    acceptance:                Prediction
    desk_rejection:            Prediction
    major_revision:            Prediction
    minor_revision:            Prediction
    expected_review_weeks:     Prediction
    expected_acceptance_months: Prediction
    expected_publication_months: Prediction
    delay_risk:                Prediction
    citation_velocity_y1:      Prediction
    citation_growth_3y:        Prediction
    long_term_impact:          Prediction
    overall_confidence:        float
    strategic_recommendation:  str
    manuscript_score:          float

    def to_dict(self) -> dict:
        return {
            "acceptance":                 self.acceptance.to_dict(),
            "desk_rejection":             self.desk_rejection.to_dict(),
            "major_revision":             self.major_revision.to_dict(),
            "minor_revision":             self.minor_revision.to_dict(),
            "expected_review_weeks":      self.expected_review_weeks.to_dict(),
            "expected_acceptance_months": self.expected_acceptance_months.to_dict(),
            "expected_publication_months":self.expected_publication_months.to_dict(),
            "delay_risk":                 self.delay_risk.to_dict(),
            "citation_velocity_y1":       self.citation_velocity_y1.to_dict(),
            "citation_growth_3y":         self.citation_growth_3y.to_dict(),
            "long_term_impact":           self.long_term_impact.to_dict(),
            "overall_confidence":         round(self.overall_confidence, 3),
            "strategic_recommendation":   self.strategic_recommendation,
            "manuscript_score":           round(self.manuscript_score, 3),
        }


@dataclass
class JournalMatch:
    journal_name:          str
    acceptance_probability: float
    impact_score:          float
    publication_speed_weeks: float
    rejection_risk:        float
    scope_match:           float
    reviewer_concerns:     list[str]
    editor_concerns:       list[str]
    recommendation_score:  float

    def to_dict(self) -> dict:
        return {
            "journal_name":           self.journal_name,
            "acceptance_probability": round(self.acceptance_probability, 3),
            "impact_score":           round(self.impact_score, 3),
            "publication_speed_weeks": round(self.publication_speed_weeks, 1),
            "rejection_risk":         round(self.rejection_risk, 3),
            "scope_match":            round(self.scope_match, 3),
            "reviewer_concerns":      self.reviewer_concerns,
            "editor_concerns":        self.editor_concerns,
            "recommendation_score":   round(self.recommendation_score, 3),
        }


@dataclass
class JournalPredictionResult:
    best_journal:        JournalMatch
    highest_impact:      JournalMatch
    fastest_publication: JournalMatch
    lowest_rejection:    JournalMatch
    all_matches:         list[JournalMatch]
    confidence:          float
    reasoning:           str

    def to_dict(self) -> dict:
        return {
            "best_journal":        self.best_journal.to_dict(),
            "highest_impact":      self.highest_impact.to_dict(),
            "fastest_publication": self.fastest_publication.to_dict(),
            "lowest_rejection":    self.lowest_rejection.to_dict(),
            "all_matches":         [j.to_dict() for j in self.all_matches],
            "confidence":          round(self.confidence, 3),
            "reasoning":           self.reasoning,
        }


@dataclass
class ConferencePrediction:
    conference_name:        str
    acceptance_probability: Prediction
    presentation_quality:   Prediction
    networking_value:       Prediction
    future_collaborations:  Prediction
    career_impact:          Prediction
    publication_opportunities: Prediction
    overall_score:          float
    recommendation:         str

    def to_dict(self) -> dict:
        return {
            "conference_name":         self.conference_name,
            "acceptance_probability":  self.acceptance_probability.to_dict(),
            "presentation_quality":    self.presentation_quality.to_dict(),
            "networking_value":        self.networking_value.to_dict(),
            "future_collaborations":   self.future_collaborations.to_dict(),
            "career_impact":           self.career_impact.to_dict(),
            "publication_opportunities": self.publication_opportunities.to_dict(),
            "overall_score":           round(self.overall_score, 3),
            "recommendation":          self.recommendation,
        }


@dataclass
class GrantPrediction:
    funding_probability:   Prediction
    competitiveness:       Prediction
    evaluation_score:      Prediction
    budget_adequacy:       Prediction
    reviewer_concerns:     list[str]
    required_improvements: list[str]
    missing_partners:      list[str]
    expected_success_rate: float
    confidence:            float

    def to_dict(self) -> dict:
        return {
            "funding_probability":   self.funding_probability.to_dict(),
            "competitiveness":       self.competitiveness.to_dict(),
            "evaluation_score":      self.evaluation_score.to_dict(),
            "budget_adequacy":       self.budget_adequacy.to_dict(),
            "reviewer_concerns":     self.reviewer_concerns,
            "required_improvements": self.required_improvements,
            "missing_partners":      self.missing_partners,
            "expected_success_rate": round(self.expected_success_rate, 3),
            "confidence":            round(self.confidence, 3),
        }


@dataclass
class CareerForecast:
    horizon:                str
    h_index:                Prediction
    citations:              Prediction
    publications:           Prediction
    productivity:           Prediction
    promotion_readiness:    Prediction
    international_visibility: Prediction
    research_influence:     Prediction
    academic_reputation:    Prediction
    leadership_potential:   Prediction
    milestones:             list[dict]
    confidence:             float

    def to_dict(self) -> dict:
        return {
            "horizon":                  self.horizon,
            "h_index":                  self.h_index.to_dict(),
            "citations":                self.citations.to_dict(),
            "publications":             self.publications.to_dict(),
            "productivity":             self.productivity.to_dict(),
            "promotion_readiness":      self.promotion_readiness.to_dict(),
            "international_visibility": self.international_visibility.to_dict(),
            "research_influence":       self.research_influence.to_dict(),
            "academic_reputation":      self.academic_reputation.to_dict(),
            "leadership_potential":     self.leadership_potential.to_dict(),
            "milestones":               self.milestones,
            "confidence":               round(self.confidence, 3),
        }


@dataclass
class CollaborationForecast:
    success_probability:       Prediction
    expected_publications:     Prediction
    expected_citation_impact:  Prediction
    grant_competitiveness_boost: Prediction
    team_productivity:         Prediction
    research_longevity:        Prediction
    interdisciplinary_impact:  Prediction
    overall_recommendation:    str
    confidence:                float

    def to_dict(self) -> dict:
        return {
            "success_probability":        self.success_probability.to_dict(),
            "expected_publications":      self.expected_publications.to_dict(),
            "expected_citation_impact":   self.expected_citation_impact.to_dict(),
            "grant_competitiveness_boost":self.grant_competitiveness_boost.to_dict(),
            "team_productivity":          self.team_productivity.to_dict(),
            "research_longevity":         self.research_longevity.to_dict(),
            "interdisciplinary_impact":   self.interdisciplinary_impact.to_dict(),
            "overall_recommendation":     self.overall_recommendation,
            "confidence":                 round(self.confidence, 3),
        }


@dataclass
class InstitutionForecast:
    horizon:             str
    publication_output:  Prediction
    funding_growth:      Prediction
    citation_growth:     Prediction
    ranking_trend:       Prediction
    research_impact:     Prediction
    strategic_risks:     list[str]
    department_highlights: list[dict]
    confidence:          float

    def to_dict(self) -> dict:
        return {
            "horizon":              self.horizon,
            "publication_output":   self.publication_output.to_dict(),
            "funding_growth":       self.funding_growth.to_dict(),
            "citation_growth":      self.citation_growth.to_dict(),
            "ranking_trend":        self.ranking_trend.to_dict(),
            "research_impact":      self.research_impact.to_dict(),
            "strategic_risks":      self.strategic_risks,
            "department_highlights":self.department_highlights,
            "confidence":           round(self.confidence, 3),
        }


@dataclass
class ResearchTrend:
    topic:           str
    trend_type:      str   # emerging, declining, hot, stable
    score:           float
    growth_rate:     float
    confidence:      float
    evidence:        list[str]
    time_horizon:    str
    related_funding: list[str]

    def to_dict(self) -> dict:
        return {
            "topic":           self.topic,
            "trend_type":      self.trend_type,
            "score":           round(self.score, 3),
            "growth_rate":     round(self.growth_rate, 3),
            "confidence":      round(self.confidence, 3),
            "evidence":        self.evidence,
            "time_horizon":    self.time_horizon,
            "related_funding": self.related_funding,
        }


@dataclass
class TrendForecastResult:
    emerging_topics:       list[ResearchTrend]
    declining_topics:      list[ResearchTrend]
    hot_topics:            list[ResearchTrend]
    funding_priorities:    list[dict]
    journal_trends:        list[dict]
    conference_trends:     list[dict]
    future_methodologies:  list[dict]
    future_technologies:   list[dict]
    confidence:            float

    def to_dict(self) -> dict:
        return {
            "emerging_topics":    [t.to_dict() for t in self.emerging_topics],
            "declining_topics":   [t.to_dict() for t in self.declining_topics],
            "hot_topics":         [t.to_dict() for t in self.hot_topics],
            "funding_priorities": self.funding_priorities,
            "journal_trends":     self.journal_trends,
            "conference_trends":  self.conference_trends,
            "future_methodologies": self.future_methodologies,
            "future_technologies":  self.future_technologies,
            "confidence":         round(self.confidence, 3),
        }


@dataclass
class Scenario:
    scenario_id:   str
    name:          str
    scenario_type: str
    description:   str
    key_metrics:   dict
    confidence:    float
    pros:          list[str]
    cons:          list[str]

    def to_dict(self) -> dict:
        return {
            "scenario_id":   self.scenario_id,
            "name":          self.name,
            "scenario_type": self.scenario_type,
            "description":   self.description,
            "key_metrics":   self.key_metrics,
            "confidence":    round(self.confidence, 3),
            "pros":          self.pros,
            "cons":          self.cons,
        }


@dataclass
class ScenarioComparison:
    scenarios:            list[Scenario]
    comparison_matrix:    dict
    recommended_scenario: str
    reasoning:            str
    confidence:           float

    def to_dict(self) -> dict:
        return {
            "scenarios":            [s.to_dict() for s in self.scenarios],
            "comparison_matrix":    self.comparison_matrix,
            "recommended_scenario": self.recommended_scenario,
            "reasoning":            self.reasoning,
            "confidence":           round(self.confidence, 3),
        }


@dataclass
class WhatIfAnalysis:
    base_scenario:      dict
    what_if_factor:     str
    base_prediction:    dict
    modified_prediction: dict
    delta_summary:      dict
    net_benefit:        float
    recommendation:     str
    confidence:         float

    def to_dict(self) -> dict:
        return {
            "base_scenario":       self.base_scenario,
            "what_if_factor":      self.what_if_factor,
            "base_prediction":     self.base_prediction,
            "modified_prediction": self.modified_prediction,
            "delta_summary":       self.delta_summary,
            "net_benefit":         round(self.net_benefit, 3),
            "recommendation":      self.recommendation,
            "confidence":          round(self.confidence, 3),
        }


@dataclass
class StrategicDecision:
    question:         str
    recommendation:   str
    confidence:       float
    urgency:          str
    evidence:         list[str]
    action_items:     list[str]
    alternatives:     list[dict]
    risk_if_ignored:  str
    expected_outcome: str

    def to_dict(self) -> dict:
        return {
            "question":         self.question,
            "recommendation":   self.recommendation,
            "confidence":       round(self.confidence, 3),
            "urgency":          self.urgency,
            "evidence":         self.evidence,
            "action_items":     self.action_items,
            "alternatives":     self.alternatives,
            "risk_if_ignored":  self.risk_if_ignored,
            "expected_outcome": self.expected_outcome,
        }
