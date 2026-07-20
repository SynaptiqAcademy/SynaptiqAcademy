"""Academic Career Intelligence Engine — Domain models (Phase XVI)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ── Enumerations ──────────────────────────────────────────────────────────────

class CareerStage(str, Enum):
    UNDERGRADUATE     = "undergraduate"
    MASTER_STUDENT    = "master_student"
    PHD_CANDIDATE     = "phd_candidate"
    POSTDOC           = "postdoc"
    RESEARCHER        = "researcher"
    SENIOR_RESEARCHER = "senior_researcher"
    LECTURER          = "lecturer"
    ASSISTANT_PROF    = "assistant_professor"
    ASSOCIATE_PROF    = "associate_professor"
    PROFESSOR         = "professor"
    INDUSTRY          = "industry_researcher"
    ADMINISTRATOR     = "administrator"


class RoadmapHorizon(str, Enum):
    ONE_YEAR   = "1_year"
    THREE_YEAR = "3_year"
    FIVE_YEAR  = "5_year"
    TEN_YEAR   = "10_year"


class MilestoneType(str, Enum):
    PUBLICATION   = "publication"
    GRANT         = "grant"
    CONFERENCE    = "conference"
    CERTIFICATION = "certification"
    COLLABORATION = "collaboration"
    TEACHING      = "teaching"
    LEADERSHIP    = "leadership"
    MOBILITY      = "international_mobility"
    PROMOTION     = "promotion"
    DEGREE        = "degree"
    SKILL         = "skill_development"


class GoalType(str, Enum):
    PUBLICATION        = "publication"
    H_INDEX            = "h_index"
    GRANT              = "grant"
    DEGREE             = "degree"
    PROMOTION          = "promotion"
    CITATION           = "citation"
    COLLABORATION      = "collaboration"
    TEACHING           = "teaching"
    SKILL              = "skill"
    CONFERENCE         = "conference"


class GoalStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    AT_RISK     = "at_risk"
    COMPLETED   = "completed"


class SkillLevel(str, Enum):
    NONE      = "none"
    BEGINNER  = "beginner"
    DEVELOPING= "developing"
    PROFICIENT= "proficient"
    EXPERT    = "expert"


class SkillGapSeverity(str, Enum):
    CRITICAL = "critical"
    MODERATE = "moderate"
    MINOR    = "minor"


class PromotionTarget(str, Enum):
    PHD_COMPLETION    = "phd_completion"
    POSTDOC           = "postdoc"
    ASSISTANT_PROF    = "assistant_professor"
    ASSOCIATE_PROF    = "associate_professor"
    PROFESSOR         = "professor"
    RESEARCH_DIRECTOR = "research_director"
    DEPARTMENT_HEAD   = "department_head"
    DEAN              = "dean"


class CareerRiskType(str, Enum):
    PUBLICATION_STAGNATION = "publication_stagnation"
    LOW_CITATION_GROWTH    = "low_citation_growth"
    LIMITED_COLLABORATION  = "limited_collaboration"
    LOW_FUNDING            = "low_funding"
    SKILL_GAPS             = "skill_gaps"
    RESEARCH_ISOLATION     = "research_isolation"
    CAREER_STAGNATION      = "career_stagnation"
    BURNOUT_INDICATOR      = "burnout_indicator"


class RiskSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"


class RecommendationType(str, Enum):
    COURSE        = "course"
    BOOK          = "book"
    CONFERENCE    = "conference"
    COLLABORATOR  = "collaborator"
    MENTOR        = "mentor"
    FUNDING       = "funding"
    TOPIC         = "topic"
    REVIEWER      = "reviewer"
    WORKSHOP      = "workshop"
    TRAINING      = "training"


class VizType(str, Enum):
    CAREER_TIMELINE       = "career_timeline"
    GOAL_PROGRESS         = "goal_progress"
    SKILL_RADAR           = "skill_radar"
    PUBLICATION_GROWTH    = "publication_growth"
    CITATION_GROWTH       = "citation_growth"
    COLLABORATION_NETWORK = "collaboration_network"
    CAREER_READINESS      = "career_readiness"
    PROMOTION_READINESS   = "promotion_readiness"
    RESEARCH_IMPACT       = "research_impact"
    DEVELOPMENT_ROADMAP   = "development_roadmap"


class ExportFormat(str, Enum):
    PDF      = "pdf"
    DOCX     = "docx"
    MARKDOWN = "markdown"


class ExportReportType(str, Enum):
    CAREER_REPORT          = "career_report"
    PROMOTION_PORTFOLIO    = "promotion_portfolio"
    RESEARCH_DEVELOPMENT   = "research_development_plan"
    PROFESSIONAL_DEVELOPMENT = "professional_development_plan"
    TEACHING_DEVELOPMENT   = "teaching_development_plan"
    GRANT_DEVELOPMENT      = "grant_development_plan"


# ── Core dataclasses ──────────────────────────────────────────────────────────

@dataclass
class CareerProfile:
    user_id: str
    name: str                             = ""
    institution: str                      = ""
    department: str                       = ""
    country: str                          = ""
    position: str                         = ""
    career_stage: CareerStage             = CareerStage.RESEARCHER
    years_active: int                     = 0
    # Research metrics
    h_index: float                        = 0.0
    publication_count: int                = 0
    citation_count: int                   = 0
    grant_count: int                      = 0
    grant_income: float                   = 0.0
    collaboration_count: int              = 0
    international_collab_ratio: float     = 0.0
    review_count: int                     = 0
    conference_count: int                 = 0
    # Skills
    research_areas: list[str]             = field(default_factory=list)
    research_methods: list[str]           = field(default_factory=list)
    statistical_expertise: list[str]      = field(default_factory=list)
    programming_skills: list[str]         = field(default_factory=list)
    languages: list[str]                  = field(default_factory=list)
    teaching_areas: list[str]             = field(default_factory=list)
    # Platform signals
    availability: float                   = 0.7
    productivity_score: float             = 0.0
    quality_score: float                  = 0.0
    impact_score: float                   = 0.0
    overall_score: float                  = 0.0

    def to_dict(self) -> dict:
        return {
            "user_id":                  self.user_id,
            "name":                     self.name,
            "institution":              self.institution,
            "department":               self.department,
            "country":                  self.country,
            "position":                 self.position,
            "career_stage":             self.career_stage.value,
            "years_active":             self.years_active,
            "h_index":                  self.h_index,
            "publication_count":        self.publication_count,
            "citation_count":           self.citation_count,
            "grant_count":              self.grant_count,
            "grant_income":             self.grant_income,
            "collaboration_count":      self.collaboration_count,
            "international_collab_ratio": self.international_collab_ratio,
            "review_count":             self.review_count,
            "conference_count":         self.conference_count,
            "research_areas":           self.research_areas,
            "research_methods":         self.research_methods,
            "statistical_expertise":    self.statistical_expertise,
            "programming_skills":       self.programming_skills,
            "languages":                self.languages,
            "teaching_areas":           self.teaching_areas,
            "availability":             self.availability,
            "productivity_score":       round(self.productivity_score, 3),
            "quality_score":            round(self.quality_score, 3),
            "impact_score":             round(self.impact_score, 3),
            "overall_score":            round(self.overall_score, 3),
        }


@dataclass
class RoadmapMilestone:
    milestone_type: MilestoneType
    description: str
    year: int
    priority: str           = "medium"   # critical / high / medium / low
    target_metric: str      = ""
    target_value: Any       = None
    resources: list[str]    = field(default_factory=list)
    success_criteria: str   = ""

    def to_dict(self) -> dict:
        return {
            "type":             self.milestone_type.value,
            "description":      self.description,
            "year":             self.year,
            "priority":         self.priority,
            "target_metric":    self.target_metric,
            "target_value":     self.target_value,
            "resources":        self.resources,
            "success_criteria": self.success_criteria,
        }


@dataclass
class CareerRoadmap:
    user_id: str
    career_stage: CareerStage
    horizon: RoadmapHorizon
    milestones: list[RoadmapMilestone]  = field(default_factory=list)
    summary: str                         = ""
    key_focus_areas: list[str]           = field(default_factory=list)
    estimated_completion_year: int       = 0

    def to_dict(self) -> dict:
        return {
            "user_id":                  self.user_id,
            "career_stage":             self.career_stage.value,
            "horizon":                  self.horizon.value,
            "milestones":               [m.to_dict() for m in self.milestones],
            "summary":                  self.summary,
            "key_focus_areas":          self.key_focus_areas,
            "estimated_completion_year": self.estimated_completion_year,
            "total_milestones":         len(self.milestones),
        }


@dataclass
class CareerGoal:
    goal_id: str               = field(default_factory=lambda: str(uuid.uuid4())[:8])
    goal_type: GoalType        = GoalType.PUBLICATION
    description: str           = ""
    target_value: Any          = None
    current_value: Any         = None
    deadline_months: int       = 12
    status: GoalStatus         = GoalStatus.NOT_STARTED
    progress: float            = 0.0   # 0.0 – 1.0
    milestones: list[str]      = field(default_factory=list)
    recommendation: str        = ""

    def to_dict(self) -> dict:
        return {
            "goal_id":        self.goal_id,
            "goal_type":      self.goal_type.value,
            "description":    self.description,
            "target_value":   self.target_value,
            "current_value":  self.current_value,
            "deadline_months": self.deadline_months,
            "status":         self.status.value,
            "progress":       round(self.progress, 3),
            "milestones":     self.milestones,
            "recommendation": self.recommendation,
        }


@dataclass
class SkillAssessment:
    domain: str
    current_level: SkillLevel   = SkillLevel.NONE
    level_score: float          = 0.0   # 0.0 – 1.0
    evidence: list[str]         = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "domain":        self.domain,
            "current_level": self.current_level.value,
            "level_score":   round(self.level_score, 3),
            "evidence":      self.evidence,
        }


@dataclass
class SkillGap:
    domain: str
    current_level: SkillLevel
    required_level: SkillLevel
    severity: SkillGapSeverity
    gap_score: float            = 0.0
    development_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "domain":              self.domain,
            "current_level":       self.current_level.value,
            "required_level":      self.required_level.value,
            "severity":            self.severity.value,
            "gap_score":           round(self.gap_score, 3),
            "development_actions": self.development_actions,
        }


@dataclass
class SkillGapReport:
    user_id: str
    career_stage: CareerStage
    assessments: list[SkillAssessment]  = field(default_factory=list)
    gaps: list[SkillGap]                = field(default_factory=list)
    overall_skill_score: float          = 0.0
    top_strengths: list[str]            = field(default_factory=list)
    critical_gaps: list[str]            = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "user_id":            self.user_id,
            "career_stage":       self.career_stage.value,
            "assessments":        [a.to_dict() for a in self.assessments],
            "gaps":               [g.to_dict() for g in self.gaps],
            "overall_skill_score": round(self.overall_skill_score, 3),
            "top_strengths":      self.top_strengths,
            "critical_gaps":      self.critical_gaps,
        }


@dataclass
class PromotionReadiness:
    target: PromotionTarget
    overall_readiness: float            = 0.0
    requirements_met: list[str]         = field(default_factory=list)
    requirements_missing: list[str]     = field(default_factory=list)
    recommended_actions: list[str]      = field(default_factory=list)
    confidence: float                   = 0.7
    estimated_months: int               = 24

    def to_dict(self) -> dict:
        return {
            "target":                self.target.value,
            "overall_readiness":     round(self.overall_readiness, 3),
            "requirements_met":      self.requirements_met,
            "requirements_missing":  self.requirements_missing,
            "recommended_actions":   self.recommended_actions,
            "confidence":            round(self.confidence, 3),
            "estimated_months":      self.estimated_months,
        }


@dataclass
class ProductivityMetrics:
    user_id: str
    publications_per_year: float        = 0.0
    citation_growth_rate: float         = 0.0
    research_diversity: int             = 0
    collaboration_diversity: int        = 0
    grant_activity: float               = 0.0
    h_index_trajectory: float           = 0.0
    output_score: float                 = 0.0
    impact_score: float                 = 0.0
    consistency_score: float            = 0.0
    overall_productivity: float         = 0.0

    def to_dict(self) -> dict:
        return {
            "user_id":               self.user_id,
            "publications_per_year": round(self.publications_per_year, 2),
            "citation_growth_rate":  round(self.citation_growth_rate, 3),
            "research_diversity":    self.research_diversity,
            "collaboration_diversity": self.collaboration_diversity,
            "grant_activity":        round(self.grant_activity, 3),
            "h_index_trajectory":    round(self.h_index_trajectory, 3),
            "output_score":          round(self.output_score, 3),
            "impact_score":          round(self.impact_score, 3),
            "consistency_score":     round(self.consistency_score, 3),
            "overall_productivity":  round(self.overall_productivity, 3),
        }


@dataclass
class CareerRisk:
    risk_type: CareerRiskType
    severity: RiskSeverity              = RiskSeverity.MEDIUM
    description: str                    = ""
    evidence: list[str]                 = field(default_factory=list)
    mitigation: str                     = ""
    risk_score: float                   = 0.0

    def to_dict(self) -> dict:
        return {
            "risk_type":   self.risk_type.value,
            "severity":    self.severity.value,
            "description": self.description,
            "evidence":    self.evidence,
            "mitigation":  self.mitigation,
            "risk_score":  round(self.risk_score, 3),
        }


@dataclass
class CareerRecommendation:
    rec_type: RecommendationType
    title: str
    reason: str                         = ""
    priority: str                       = "medium"
    tags: list[str]                     = field(default_factory=list)
    estimated_impact: str               = "medium"
    time_investment: str                = ""

    def to_dict(self) -> dict:
        return {
            "type":              self.rec_type.value,
            "title":             self.title,
            "reason":            self.reason,
            "priority":          self.priority,
            "tags":              self.tags,
            "estimated_impact":  self.estimated_impact,
            "time_investment":   self.time_investment,
        }


@dataclass
class CopilotSuggestion:
    category: str
    suggestion: str
    action: str
    urgency: str = "medium"
    benefit: str = ""

    def to_dict(self) -> dict:
        return {
            "category":  self.category,
            "suggestion": self.suggestion,
            "action":    self.action,
            "urgency":   self.urgency,
            "benefit":   self.benefit,
        }
