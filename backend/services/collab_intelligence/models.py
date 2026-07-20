"""Research Collaboration Intelligence Engine — Domain models (Phase XIV)."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ── Enumerations ──────────────────────────────────────────────────────────────

class CareerStage(str, Enum):
    STUDENT          = "student"
    POSTDOC          = "postdoc"
    EARLY_CAREER     = "early_career"
    MID_CAREER       = "mid_career"
    SENIOR           = "senior"
    EMERITUS         = "emeritus"


class CollabType(str, Enum):
    CO_AUTHOR          = "co_author"
    MENTOR             = "mentor"
    SUPERVISOR         = "supervisor"
    REVIEWER           = "reviewer"
    GRANT_PARTNER      = "grant_partner"
    INDUSTRY           = "industry"
    INTERNATIONAL      = "international"
    INTERDISCIPLINARY  = "interdisciplinary"
    CONFERENCE         = "conference"
    DOCTORAL_ADVISOR   = "doctoral_advisor"


class TeamType(str, Enum):
    INTERDISCIPLINARY  = "interdisciplinary"
    GRANT              = "grant"
    JOURNAL            = "journal"
    CONFERENCE         = "conference"
    DOCTORAL           = "doctoral"
    TEACHING           = "teaching"
    INNOVATION         = "innovation"
    INDUSTRY           = "industry"
    INTERNATIONAL      = "international"


class OpportunityType(str, Enum):
    CO_AUTHOR         = "co_author"
    MENTOR            = "mentor"
    SUPERVISOR        = "supervisor"
    PEER_REVIEWER     = "peer_reviewer"
    GRANT_PARTNER     = "grant_partner"
    INSTITUTION       = "institution"
    LABORATORY        = "laboratory"
    INDUSTRY          = "industry"
    DOCTORAL_ADVISOR  = "doctoral_advisor"
    INTERNATIONAL     = "international"


class InsightSeverity(str, Enum):
    INFO        = "info"
    WARNING     = "warning"
    OPPORTUNITY = "opportunity"
    CRITICAL    = "critical"


class NetworkNodeType(str, Enum):
    RESEARCHER   = "researcher"
    INSTITUTION  = "institution"
    TOPIC        = "topic"
    METHOD       = "method"
    JOURNAL      = "journal"
    GRANT        = "grant"
    PROJECT      = "project"


class VisualizationType(str, Enum):
    NETWORK_GRAPH    = "network_graph"
    HEATMAP          = "heatmap"
    EXPERTISE_MAP    = "expertise_map"
    INSTITUTION_NET  = "institution_network"
    COUNTRY_NET      = "country_network"
    CLUSTER_MAP      = "cluster_map"
    COMPATIBILITY    = "compatibility_matrix"
    TIMELINE         = "collaboration_timeline"
    IMPACT_PROJECTION = "impact_projection"


# ── Core dataclasses ──────────────────────────────────────────────────────────

@dataclass
class CompetencyNode:
    concept: str
    level: float          # 0-1 proficiency
    evidence_count: int = 1
    domain: str = ""

    def to_dict(self) -> dict:
        return {
            "concept": self.concept,
            "level": round(self.level, 3),
            "evidence_count": self.evidence_count,
            "domain": self.domain,
        }


@dataclass
class CompetencyGraph:
    user_id: str
    research_domains: list[CompetencyNode] = field(default_factory=list)
    methodologies: list[CompetencyNode]    = field(default_factory=list)
    statistical_techniques: list[CompetencyNode] = field(default_factory=list)
    software_tools: list[CompetencyNode]   = field(default_factory=list)
    programming_languages: list[CompetencyNode] = field(default_factory=list)
    lab_skills: list[CompetencyNode]       = field(default_factory=list)
    teaching_skills: list[CompetencyNode]  = field(default_factory=list)
    peer_review_count: int    = 0
    grant_success_rate: float = 0.0
    writing_quality: float    = 0.5
    leadership_score: float   = 0.0
    overall_score: float      = 0.0

    def all_concepts(self) -> list[str]:
        nodes = (
            self.research_domains + self.methodologies +
            self.statistical_techniques + self.software_tools +
            self.programming_languages + self.lab_skills + self.teaching_skills
        )
        return [n.concept for n in nodes]

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "research_domains": [n.to_dict() for n in self.research_domains],
            "methodologies": [n.to_dict() for n in self.methodologies],
            "statistical_techniques": [n.to_dict() for n in self.statistical_techniques],
            "software_tools": [n.to_dict() for n in self.software_tools],
            "programming_languages": [n.to_dict() for n in self.programming_languages],
            "lab_skills": [n.to_dict() for n in self.lab_skills],
            "teaching_skills": [n.to_dict() for n in self.teaching_skills],
            "peer_review_count": self.peer_review_count,
            "grant_success_rate": round(self.grant_success_rate, 3),
            "writing_quality": round(self.writing_quality, 3),
            "leadership_score": round(self.leadership_score, 3),
            "overall_score": round(self.overall_score, 3),
        }


@dataclass
class ResearcherProfile:
    user_id: str
    name: str                          = ""
    institution: str                   = ""
    department: str                    = ""
    country: str                       = ""
    languages: list[str]               = field(default_factory=list)
    career_stage: CareerStage          = CareerStage.EARLY_CAREER
    domains: list[str]                 = field(default_factory=list)
    keywords: list[str]                = field(default_factory=list)
    methods: list[str]                 = field(default_factory=list)
    statistical_expertise: list[str]   = field(default_factory=list)
    programming_skills: list[str]      = field(default_factory=list)
    h_index: float                     = 0.0
    publication_count: int             = 0
    citation_count: int                = 0
    collaboration_count: int           = 0
    international_collab_ratio: float  = 0.0
    availability: float                = 0.5
    response_rate: float               = 0.7
    productivity_score: float          = 0.0
    quality_score: float               = 0.0
    impact_score: float                = 0.0
    competency_graph: CompetencyGraph | None = None

    def all_interests(self) -> set[str]:
        return set(d.lower() for d in self.domains + self.keywords)

    def all_methods(self) -> set[str]:
        return set(m.lower() for m in self.methods + self.statistical_expertise)

    def all_skills(self) -> set[str]:
        return set(s.lower() for s in self.programming_skills)

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "name": self.name,
            "institution": self.institution,
            "department": self.department,
            "country": self.country,
            "languages": self.languages,
            "career_stage": self.career_stage.value,
            "domains": self.domains,
            "keywords": self.keywords,
            "methods": self.methods,
            "statistical_expertise": self.statistical_expertise,
            "programming_skills": self.programming_skills,
            "h_index": self.h_index,
            "publication_count": self.publication_count,
            "citation_count": self.citation_count,
            "collaboration_count": self.collaboration_count,
            "international_collab_ratio": round(self.international_collab_ratio, 3),
            "availability": round(self.availability, 3),
            "response_rate": round(self.response_rate, 3),
            "productivity_score": round(self.productivity_score, 3),
            "quality_score": round(self.quality_score, 3),
            "impact_score": round(self.impact_score, 3),
            "competency_graph": self.competency_graph.to_dict() if self.competency_graph else None,
        }


@dataclass
class CollabMatch:
    researcher_a_id: str
    researcher_b_id: str
    overall_score: float               = 0.0
    research_similarity: float         = 0.0
    complementarity: float             = 0.0
    methodological_compatibility: float = 0.0
    publication_synergy: float         = 0.0
    citation_overlap: float            = 0.0
    grant_compatibility: float         = 0.0
    diversity_score: float             = 0.0
    availability_compatibility: float  = 0.0
    career_stage_compatibility: float  = 0.5
    shared_keywords: list[str]         = field(default_factory=list)
    complementary_skills: list[str]    = field(default_factory=list)
    explanation: str                   = ""
    collab_type: CollabType            = CollabType.CO_AUTHOR

    def to_dict(self) -> dict:
        return {
            "researcher_a_id": self.researcher_a_id,
            "researcher_b_id": self.researcher_b_id,
            "overall_score": round(self.overall_score, 3),
            "dimensions": {
                "research_similarity": round(self.research_similarity, 3),
                "complementarity": round(self.complementarity, 3),
                "methodological_compatibility": round(self.methodological_compatibility, 3),
                "publication_synergy": round(self.publication_synergy, 3),
                "citation_overlap": round(self.citation_overlap, 3),
                "grant_compatibility": round(self.grant_compatibility, 3),
                "diversity_score": round(self.diversity_score, 3),
                "availability_compatibility": round(self.availability_compatibility, 3),
                "career_stage_compatibility": round(self.career_stage_compatibility, 3),
            },
            "shared_keywords": self.shared_keywords,
            "complementary_skills": self.complementary_skills,
            "explanation": self.explanation,
            "collab_type": self.collab_type.value,
        }


@dataclass
class TeamMember:
    user_id: str
    name: str                = ""
    role: str                = "researcher"
    expertise_coverage: list[str] = field(default_factory=list)
    contribution_weight: float = 0.5

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "name": self.name,
            "role": self.role,
            "expertise_coverage": self.expertise_coverage,
            "contribution_weight": round(self.contribution_weight, 3),
        }


@dataclass
class TeamComposition:
    objective: str
    team_type: TeamType                = TeamType.INTERDISCIPLINARY
    members: list[TeamMember]          = field(default_factory=list)
    overall_score: float               = 0.0
    expertise_coverage: float          = 0.0
    diversity_score: float             = 0.0
    skill_gaps: list[str]              = field(default_factory=list)
    strengths: list[str]               = field(default_factory=list)
    predicted_productivity: float      = 0.0
    predicted_grant_success: float     = 0.0
    predicted_publication_quality: float = 0.0
    team_id: str                       = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def to_dict(self) -> dict:
        return {
            "team_id": self.team_id,
            "objective": self.objective,
            "team_type": self.team_type.value,
            "members": [m.to_dict() for m in self.members],
            "overall_score": round(self.overall_score, 3),
            "expertise_coverage": round(self.expertise_coverage, 3),
            "diversity_score": round(self.diversity_score, 3),
            "skill_gaps": self.skill_gaps,
            "strengths": self.strengths,
            "predicted_productivity": round(self.predicted_productivity, 3),
            "predicted_grant_success": round(self.predicted_grant_success, 3),
            "predicted_publication_quality": round(self.predicted_publication_quality, 3),
        }


@dataclass
class CollabOpportunity:
    opportunity_type: OpportunityType
    target_researcher_id: str
    target_name: str         = ""
    score: float             = 0.0
    reason: str              = ""
    shared_interests: list[str]    = field(default_factory=list)
    complementary_skills: list[str] = field(default_factory=list)
    action_recommended: str        = ""
    opportunity_id: str            = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def to_dict(self) -> dict:
        return {
            "opportunity_id": self.opportunity_id,
            "opportunity_type": self.opportunity_type.value,
            "target_researcher_id": self.target_researcher_id,
            "target_name": self.target_name,
            "score": round(self.score, 3),
            "reason": self.reason,
            "shared_interests": self.shared_interests,
            "complementary_skills": self.complementary_skills,
            "action_recommended": self.action_recommended,
        }


@dataclass
class SmartIntroduction:
    researcher_a_id: str
    researcher_b_id: str
    narrative: str                    = ""
    shared_interests: list[str]       = field(default_factory=list)
    complementary_expertise: list[str] = field(default_factory=list)
    expected_outcomes: list[str]      = field(default_factory=list)
    collaboration_hooks: list[str]    = field(default_factory=list)
    match_score: float                = 0.0

    def to_dict(self) -> dict:
        return {
            "researcher_a_id": self.researcher_a_id,
            "researcher_b_id": self.researcher_b_id,
            "narrative": self.narrative,
            "shared_interests": self.shared_interests,
            "complementary_expertise": self.complementary_expertise,
            "expected_outcomes": self.expected_outcomes,
            "collaboration_hooks": self.collaboration_hooks,
            "match_score": round(self.match_score, 3),
        }


@dataclass
class NetworkNode:
    node_id: str
    node_type: NetworkNodeType
    label: str
    centrality: float     = 0.0
    cluster_id: str       = ""
    connections: int      = 0
    metadata: dict        = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "label": self.label,
            "centrality": round(self.centrality, 4),
            "cluster_id": self.cluster_id,
            "connections": self.connections,
            "metadata": self.metadata,
        }


@dataclass
class NetworkEdge:
    from_id: str
    to_id: str
    weight: float    = 1.0
    edge_type: str   = "collaboration"

    def to_dict(self) -> dict:
        return {
            "from": self.from_id,
            "to": self.to_id,
            "weight": round(self.weight, 3),
            "type": self.edge_type,
        }


@dataclass
class ResearchNetwork:
    nodes: list[NetworkNode]    = field(default_factory=list)
    edges: list[NetworkEdge]    = field(default_factory=list)
    clusters: list[dict]        = field(default_factory=list)
    density: float              = 0.0
    diameter_estimate: int      = 0
    most_central: list[str]     = field(default_factory=list)
    isolated_nodes: list[str]   = field(default_factory=list)
    bridge_nodes: list[str]     = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "clusters": self.clusters,
            "metrics": {
                "density": round(self.density, 4),
                "diameter_estimate": self.diameter_estimate,
                "most_central": self.most_central,
                "isolated_nodes": self.isolated_nodes,
                "bridge_nodes": self.bridge_nodes,
            },
        }


@dataclass
class CollabPrediction:
    researcher_a_id: str
    researcher_b_id: str
    success_probability: float      = 0.0
    publication_probability: float  = 0.0
    grant_probability: float        = 0.0
    expected_citation_growth: float = 0.0
    long_term_potential: float      = 0.0
    risk_factors: list[str]         = field(default_factory=list)
    success_factors: list[str]      = field(default_factory=list)
    confidence: float               = 0.7
    time_to_first_output_months: int = 12

    def to_dict(self) -> dict:
        return {
            "researcher_a_id": self.researcher_a_id,
            "researcher_b_id": self.researcher_b_id,
            "probabilities": {
                "collaboration_success": round(self.success_probability, 3),
                "publication": round(self.publication_probability, 3),
                "grant_success": round(self.grant_probability, 3),
            },
            "projections": {
                "expected_citation_growth": round(self.expected_citation_growth, 2),
                "long_term_potential": round(self.long_term_potential, 3),
                "time_to_first_output_months": self.time_to_first_output_months,
            },
            "risk_factors": self.risk_factors,
            "success_factors": self.success_factors,
            "confidence": round(self.confidence, 3),
        }


@dataclass
class TeamSimulation:
    team_member_ids: list[str]
    objective: str
    expected_productivity: float        = 0.0
    publication_quality_estimate: float = 0.0
    grant_competitiveness: float        = 0.0
    expertise_coverage: float           = 0.0
    diversity_score: float              = 0.0
    skill_gaps: list[str]               = field(default_factory=list)
    potential_weaknesses: list[str]     = field(default_factory=list)
    recommendations: list[str]          = field(default_factory=list)
    simulation_id: str                  = field(default_factory=lambda: str(uuid.uuid4())[:8])

    def to_dict(self) -> dict:
        return {
            "simulation_id": self.simulation_id,
            "team_member_ids": self.team_member_ids,
            "objective": self.objective,
            "estimated_outputs": {
                "productivity": round(self.expected_productivity, 3),
                "publication_quality": round(self.publication_quality_estimate, 3),
                "grant_competitiveness": round(self.grant_competitiveness, 3),
            },
            "team_health": {
                "expertise_coverage": round(self.expertise_coverage, 3),
                "diversity_score": round(self.diversity_score, 3),
            },
            "skill_gaps": self.skill_gaps,
            "potential_weaknesses": self.potential_weaknesses,
            "recommendations": self.recommendations,
        }


@dataclass
class CollabInsight:
    insight_type: str
    message: str
    severity: InsightSeverity = InsightSeverity.INFO
    metric_value: float       = 0.0
    benchmark_value: float    = 0.5
    recommendation: str       = ""

    def to_dict(self) -> dict:
        return {
            "type": self.insight_type,
            "message": self.message,
            "severity": self.severity.value,
            "metric_value": round(self.metric_value, 3),
            "benchmark_value": round(self.benchmark_value, 3),
            "recommendation": self.recommendation,
        }


@dataclass
class Recommendation:
    target_id: str
    target_type: str   # researcher / institution / lab
    target_name: str   = ""
    score: float       = 0.0
    reason: str        = ""
    tags: list[str]    = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "target_id": self.target_id,
            "target_type": self.target_type,
            "target_name": self.target_name,
            "score": round(self.score, 3),
            "reason": self.reason,
            "tags": self.tags,
        }


@dataclass
class VisualizationData:
    viz_type: VisualizationType
    data: dict
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "viz_type": self.viz_type.value,
            "data": self.data,
            "metadata": self.metadata,
        }
