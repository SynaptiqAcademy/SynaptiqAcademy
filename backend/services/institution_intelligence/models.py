"""Institution Intelligence Engine — Domain models (Phase XV)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ── Enumerations ──────────────────────────────────────────────────────────────

class InstitutionType(str, Enum):
    UNIVERSITY           = "university"
    RESEARCH_INSTITUTE   = "research_institute"
    HOSPITAL             = "hospital"
    COMPANY              = "company"
    GOVERNMENT           = "government"
    NGO                  = "ngo"


class DepartmentStatus(str, Enum):
    HIGH_PERFORMING   = "high_performing"
    PERFORMING        = "performing"
    UNDERPERFORMING   = "underperforming"
    EMERGING          = "emerging"
    DECLINING         = "declining"
    STABLE            = "stable"


class RiskLevel(str, Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    MEDIUM   = "medium"
    LOW      = "low"
    MINIMAL  = "minimal"


class RiskType(str, Enum):
    RESEARCH_DECLINE        = "research_decline"
    GRANT_DEPENDENCY        = "grant_dependency"
    PUBLICATION_CONCENTRATION = "publication_concentration"
    STAFF_TURNOVER          = "staff_turnover"
    RESEARCH_ISOLATION      = "research_isolation"
    LOW_COLLABORATION       = "low_collaboration"
    FUNDING_INSTABILITY     = "funding_instability"
    LOW_DOCTORAL_RECRUITMENT = "low_doctoral_recruitment"
    STRATEGIC_VULNERABILITY = "strategic_vulnerability"
    TALENT_RETENTION        = "talent_retention"


class RecommendationAudience(str, Enum):
    RECTOR            = "rector"
    VICE_RECTOR       = "vice_rector"
    DEAN              = "dean"
    DEPARTMENT_HEAD   = "department_head"
    RESEARCH_DIRECTOR = "research_director"
    GRANT_OFFICE      = "grant_office"
    HR                = "hr"
    ADMINISTRATOR     = "administrator"


class ForecastType(str, Enum):
    PUBLICATIONS        = "publications"
    CITATIONS           = "citations"
    GRANT_INCOME        = "grant_income"
    COLLABORATIONS      = "collaborations"
    H_INDEX             = "h_index"
    DOCTORAL_COMPLETIONS = "doctoral_completions"
    FACULTY_SIZE        = "faculty_size"
    RESEARCH_INCOME     = "research_income"


class VizType(str, Enum):
    KNOWLEDGE_GRAPH          = "institution_knowledge_graph"
    RESEARCH_PORTFOLIO       = "research_portfolio_map"
    FACULTY_PERFORMANCE      = "faculty_performance_map"
    DEPARTMENT_HEATMAP       = "department_heatmap"
    GRANT_DASHBOARD          = "grant_dashboard"
    FUNDING_FLOW             = "funding_flow"
    CITATION_GROWTH          = "citation_growth"
    PUBLICATION_TIMELINE     = "publication_timeline"
    INTERNATIONAL_MAP        = "international_collaboration_map"
    TALENT_PIPELINE          = "talent_pipeline"
    RISK_MATRIX              = "strategic_risk_matrix"
    FORECAST_DASHBOARD       = "institution_forecast_dashboard"


class ExportFormat(str, Enum):
    PDF       = "pdf"
    DOCX      = "docx"
    EXCEL     = "excel"
    POWERPOINT = "powerpoint"


class ExportReportType(str, Enum):
    EXECUTIVE      = "executive"
    ACCREDITATION  = "accreditation"
    RESEARCH_STRATEGY = "research_strategy"
    GRANT_STRATEGY = "grant_strategy"
    FACULTY        = "faculty_performance"
    DEPARTMENT     = "department"
    BENCHMARK      = "benchmark"


class AlertType(str, Enum):
    KPI_DECLINE      = "kpi_decline"
    RISK_THRESHOLD   = "risk_threshold"
    OPPORTUNITY      = "opportunity"
    TARGET_ACHIEVED  = "target_achieved"
    TREND_REVERSAL   = "trend_reversal"


# ── Input model ───────────────────────────────────────────────────────────────

@dataclass
class InstitutionInput:
    """
    Structured input: caller populates from MongoDB collections.
    All fields are optional — engine degrades gracefully.
    """
    name: str                          = ""
    institution_type: str              = "university"
    country: str                       = ""
    founding_year: int                 = 0
    researchers: list[dict]            = field(default_factory=list)
    grants: list[dict]                 = field(default_factory=list)
    publications: list[dict]           = field(default_factory=list)
    projects: list[dict]               = field(default_factory=list)
    departments: list[str]             = field(default_factory=list)
    total_budget: float                = 0.0
    total_students: int                = 0
    metadata: dict                     = field(default_factory=dict)


# ── KPI dataclass ─────────────────────────────────────────────────────────────

@dataclass
class InstitutionKPIs:
    publication_output: int           = 0
    publication_growth: float         = 0.0
    citation_growth: float            = 0.0
    avg_h_index: float                = 0.0
    avg_fwci: float                   = 0.0     # Field-Weighted Citation Impact proxy
    research_income: float            = 0.0
    grant_success_rate: float         = 0.0
    acceptance_rate: float            = 0.0
    q1_ratio: float                   = 0.0
    conference_performance: float     = 0.0
    collaboration_score: float        = 0.0
    internationalization_score: float = 0.0
    innovation_score: float           = 0.0
    open_science_score: float         = 0.0
    research_efficiency: float        = 0.0
    sustainability_score: float       = 0.0
    reputation_score: float           = 0.0
    faculty_performance: float        = 0.0
    department_performance: float     = 0.0
    doctoral_activity_score: float    = 0.0

    def to_dict(self) -> dict:
        return {
            "publication_output":          self.publication_output,
            "publication_growth":          round(self.publication_growth, 3),
            "citation_growth":             round(self.citation_growth, 3),
            "avg_h_index":                 round(self.avg_h_index, 2),
            "avg_fwci":                    round(self.avg_fwci, 3),
            "research_income":             round(self.research_income, 2),
            "grant_success_rate":          round(self.grant_success_rate, 3),
            "acceptance_rate":             round(self.acceptance_rate, 3),
            "q1_ratio":                    round(self.q1_ratio, 3),
            "conference_performance":      round(self.conference_performance, 3),
            "collaboration_score":         round(self.collaboration_score, 3),
            "internationalization_score":  round(self.internationalization_score, 3),
            "innovation_score":            round(self.innovation_score, 3),
            "open_science_score":          round(self.open_science_score, 3),
            "research_efficiency":         round(self.research_efficiency, 3),
            "sustainability_score":        round(self.sustainability_score, 3),
            "reputation_score":            round(self.reputation_score, 3),
            "faculty_performance":         round(self.faculty_performance, 3),
            "department_performance":      round(self.department_performance, 3),
            "doctoral_activity_score":     round(self.doctoral_activity_score, 3),
        }


# ── Core output dataclasses ───────────────────────────────────────────────────

@dataclass
class DepartmentProfile:
    name: str
    researcher_count: int              = 0
    publication_count: int             = 0
    citation_count: int                = 0
    grant_count: int                   = 0
    grant_income: float                = 0.0
    avg_h_index: float                 = 0.0
    collaboration_score: float         = 0.0
    international_ratio: float         = 0.0
    publication_growth: float          = 0.0
    status: DepartmentStatus           = DepartmentStatus.STABLE
    strengths: list[str]               = field(default_factory=list)
    weaknesses: list[str]              = field(default_factory=list)
    top_researchers: list[str]         = field(default_factory=list)
    research_domains: list[str]        = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name":                 self.name,
            "researcher_count":     self.researcher_count,
            "publication_count":    self.publication_count,
            "citation_count":       self.citation_count,
            "grant_count":          self.grant_count,
            "grant_income":         round(self.grant_income, 2),
            "avg_h_index":          round(self.avg_h_index, 2),
            "collaboration_score":  round(self.collaboration_score, 3),
            "international_ratio":  round(self.international_ratio, 3),
            "publication_growth":   round(self.publication_growth, 3),
            "status":               self.status.value,
            "strengths":            self.strengths,
            "weaknesses":           self.weaknesses,
            "top_researchers":      self.top_researchers,
            "research_domains":     self.research_domains,
        }


@dataclass
class InstitutionProfile:
    institution_id: str
    name: str                          = ""
    institution_type: InstitutionType  = InstitutionType.UNIVERSITY
    country: str                       = ""
    founding_year: int                 = 0
    total_researchers: int             = 0
    total_publications: int            = 0
    total_citations: int               = 0
    total_grants: int                  = 0
    total_grant_income: float          = 0.0
    departments: list[DepartmentProfile] = field(default_factory=list)
    kpis: InstitutionKPIs              = field(default_factory=InstitutionKPIs)
    research_areas: list[str]          = field(default_factory=list)
    top_researchers: list[str]         = field(default_factory=list)
    international_partners: list[str]  = field(default_factory=list)
    overall_score: float               = 0.0

    def to_dict(self) -> dict:
        return {
            "institution_id":      self.institution_id,
            "name":                self.name,
            "type":                self.institution_type.value,
            "country":             self.country,
            "founding_year":       self.founding_year,
            "total_researchers":   self.total_researchers,
            "total_publications":  self.total_publications,
            "total_citations":     self.total_citations,
            "total_grants":        self.total_grants,
            "total_grant_income":  round(self.total_grant_income, 2),
            "departments":         [d.to_dict() for d in self.departments],
            "kpis":                self.kpis.to_dict(),
            "research_areas":      self.research_areas,
            "top_researchers":     self.top_researchers,
            "international_partners": self.international_partners,
            "overall_score":       round(self.overall_score, 3),
        }


@dataclass
class OrganizationalInsight:
    insight_type: str
    entity_id: str                     = ""
    entity_name: str                   = ""
    severity: RiskLevel                = RiskLevel.LOW
    message: str                       = ""
    evidence: list[str]                = field(default_factory=list)
    recommendation: str                = ""
    confidence: float                  = 0.7

    def to_dict(self) -> dict:
        return {
            "insight_type":   self.insight_type,
            "entity_id":      self.entity_id,
            "entity_name":    self.entity_name,
            "severity":       self.severity.value,
            "message":        self.message,
            "evidence":       self.evidence,
            "recommendation": self.recommendation,
            "confidence":     round(self.confidence, 3),
        }


@dataclass
class InstitutionForecast:
    forecast_type: ForecastType
    horizon_years: int                 = 3
    baseline_value: float              = 0.0
    predicted_values: list[float]      = field(default_factory=list)  # per year
    ci_lower: list[float]              = field(default_factory=list)
    ci_upper: list[float]              = field(default_factory=list)
    key_drivers: list[str]             = field(default_factory=list)
    confidence: float                  = 0.7
    trend: str                         = "stable"

    def to_dict(self) -> dict:
        return {
            "forecast_type":      self.forecast_type.value,
            "horizon_years":      self.horizon_years,
            "baseline_value":     round(self.baseline_value, 3),
            "predicted_values":   [round(v, 3) for v in self.predicted_values],
            "confidence_interval": {
                "lower": [round(v, 3) for v in self.ci_lower],
                "upper": [round(v, 3) for v in self.ci_upper],
            },
            "key_drivers":        self.key_drivers,
            "confidence":         round(self.confidence, 3),
            "trend":              self.trend,
        }


@dataclass
class InstitutionRisk:
    risk_type: RiskType
    severity: RiskLevel                = RiskLevel.MEDIUM
    entity_id: str                     = ""
    entity_name: str                   = ""
    description: str                   = ""
    evidence: list[str]                = field(default_factory=list)
    mitigation: str                    = ""
    probability: float                 = 0.5
    impact: float                      = 0.5
    risk_score: float                  = 0.0

    def to_dict(self) -> dict:
        return {
            "risk_type":    self.risk_type.value,
            "severity":     self.severity.value,
            "entity_id":    self.entity_id,
            "entity_name":  self.entity_name,
            "description":  self.description,
            "evidence":     self.evidence,
            "mitigation":   self.mitigation,
            "probability":  round(self.probability, 3),
            "impact":       round(self.impact, 3),
            "risk_score":   round(self.risk_score, 3),
        }


@dataclass
class ExecutiveRecommendation:
    category: str
    title: str
    description: str                   = ""
    audience: RecommendationAudience   = RecommendationAudience.RECTOR
    reasoning: str                     = ""
    evidence: list[str]                = field(default_factory=list)
    confidence: float                  = 0.7
    expected_impact: str               = "medium"
    implementation_difficulty: str     = "medium"
    priority: str                      = "medium"
    timeline: str                      = "6-12 months"
    recommendation_id: str             = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def to_dict(self) -> dict:
        return {
            "recommendation_id":         self.recommendation_id,
            "category":                  self.category,
            "title":                     self.title,
            "description":               self.description,
            "audience":                  self.audience.value,
            "reasoning":                 self.reasoning,
            "evidence":                  self.evidence,
            "confidence":                round(self.confidence, 3),
            "expected_impact":           self.expected_impact,
            "implementation_difficulty": self.implementation_difficulty,
            "priority":                  self.priority,
            "timeline":                  self.timeline,
        }


@dataclass
class BenchmarkResult:
    metric: str
    own_value: float                   = 0.0
    peer_avg: float                    = 0.0
    peer_top: float                    = 0.0
    percentile: float                  = 0.5
    trend: str                         = "stable"
    delta_vs_peer: float               = 0.0
    recommendation: str                = ""

    def to_dict(self) -> dict:
        return {
            "metric":           self.metric,
            "own_value":        round(self.own_value, 3),
            "peer_avg":         round(self.peer_avg, 3),
            "peer_top":         round(self.peer_top, 3),
            "percentile":       round(self.percentile, 3),
            "trend":            self.trend,
            "delta_vs_peer":    round(self.delta_vs_peer, 3),
            "recommendation":   self.recommendation,
        }


@dataclass
class ResourceAllocation:
    category: str
    target: str
    current_allocation: float          = 0.0
    recommended_allocation: float      = 0.0
    change_direction: str              = "maintain"  # increase/decrease/maintain
    reasoning: str                     = ""
    expected_roi: float                = 0.0
    priority: str                      = "medium"

    def to_dict(self) -> dict:
        return {
            "category":               self.category,
            "target":                 self.target,
            "current_allocation":     round(self.current_allocation, 3),
            "recommended_allocation": round(self.recommended_allocation, 3),
            "change_direction":       self.change_direction,
            "reasoning":              self.reasoning,
            "expected_roi":           round(self.expected_roi, 3),
            "priority":               self.priority,
        }


@dataclass
class TalentProfile:
    user_id: str
    name: str                          = ""
    department: str                    = ""
    career_stage: str                  = ""
    talent_tag: str                    = ""   # future_leader/high_potential/retention_risk
    h_index: float                     = 0.0
    publication_count: int             = 0
    score: float                       = 0.0
    recommendation: str                = ""
    rationale: str                     = ""

    def to_dict(self) -> dict:
        return {
            "user_id":          self.user_id,
            "name":             self.name,
            "department":       self.department,
            "career_stage":     self.career_stage,
            "talent_tag":       self.talent_tag,
            "h_index":          self.h_index,
            "publication_count": self.publication_count,
            "score":            round(self.score, 3),
            "recommendation":   self.recommendation,
            "rationale":        self.rationale,
        }


@dataclass
class PortfolioArea:
    name: str
    publication_count: int             = 0
    citation_count: int                = 0
    researcher_count: int              = 0
    grant_count: int                   = 0
    growth_rate: float                 = 0.0
    maturity: str                      = "mature"   # emerging/growing/mature/declining
    strategic_priority: str            = "maintain" # invest/grow/maintain/divest
    alignment_score: float             = 0.5

    def to_dict(self) -> dict:
        return {
            "name":              self.name,
            "publication_count": self.publication_count,
            "citation_count":    self.citation_count,
            "researcher_count":  self.researcher_count,
            "grant_count":       self.grant_count,
            "growth_rate":       round(self.growth_rate, 3),
            "maturity":          self.maturity,
            "strategic_priority": self.strategic_priority,
            "alignment_score":   round(self.alignment_score, 3),
        }


@dataclass
class MonitoringAlert:
    alert_type: AlertType
    severity: RiskLevel                = RiskLevel.LOW
    metric: str                        = ""
    entity: str                        = ""
    message: str                       = ""
    current_value: float               = 0.0
    threshold: float                   = 0.0
    recommended_action: str            = ""
    alert_id: str                      = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def to_dict(self) -> dict:
        return {
            "alert_id":           self.alert_id,
            "alert_type":         self.alert_type.value,
            "severity":           self.severity.value,
            "metric":             self.metric,
            "entity":             self.entity,
            "message":            self.message,
            "current_value":      round(self.current_value, 3),
            "threshold":          round(self.threshold, 3),
            "recommended_action": self.recommended_action,
        }


@dataclass
class KnowledgeGraphNode:
    node_id: str
    node_type: str     # institution/department/researcher/grant/publication/topic
    label: str
    properties: dict   = field(default_factory=dict)
    size: float        = 1.0

    def to_dict(self) -> dict:
        return {
            "id":         self.node_id,
            "type":       self.node_type,
            "label":      self.label,
            "properties": self.properties,
            "size":       round(self.size, 3),
        }


@dataclass
class KnowledgeGraphEdge:
    from_id: str
    to_id: str
    relation: str
    weight: float = 1.0

    def to_dict(self) -> dict:
        return {"from": self.from_id, "to": self.to_id, "relation": self.relation,
                "weight": round(self.weight, 3)}


@dataclass
class InstitutionKnowledgeGraph:
    nodes: list[KnowledgeGraphNode] = field(default_factory=list)
    edges: list[KnowledgeGraphEdge] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "stats": {
                "total_nodes": len(self.nodes),
                "total_edges": len(self.edges),
                "node_types":  list({n.node_type for n in self.nodes}),
            },
        }
