"""Research Gap Intelligence — complete domain model for Phase VIII."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


# ══════════════════════════════════════════════════════════════════════════════
# Enumerations
# ══════════════════════════════════════════════════════════════════════════════

class GapType(str, Enum):
    THEORETICAL = "theoretical"
    METHODOLOGICAL = "methodological"
    EMPIRICAL = "empirical"
    PRACTICAL = "practical"
    TECHNOLOGICAL = "technological"
    REGIONAL = "regional"
    POPULATION = "population"
    INDUSTRY = "industry"
    TEMPORAL = "temporal"
    POLICY = "policy"
    EDUCATIONAL = "educational"
    HEALTHCARE = "healthcare"
    DIGITAL_TRANSFORMATION = "digital_transformation"
    SUSTAINABILITY = "sustainability"
    INNOVATION = "innovation"
    AI_GAP = "ai_gap"
    INTERDISCIPLINARY = "interdisciplinary"
    FUTURE_RESEARCH = "future_research"


class AnalysisDepth(str, Enum):
    QUICK = "quick"        # text + AI only; ~30s; 5 credits
    STANDARD = "standard"  # + rule engine + scoring; ~2min; 10 credits
    DEEP = "deep"          # + corpus analysis from lit session; ~5min; 20 credits


class GapSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class CompetitionLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


class ResearchMaturity(str, Enum):
    NASCENT = "nascent"
    DEVELOPING = "developing"
    ESTABLISHED = "established"
    MATURE = "mature"


class PublicationDensity(str, Enum):
    SPARSE = "sparse"
    MODERATE = "moderate"
    DENSE = "dense"
    SATURATED = "saturated"


class ExportFormat(str, Enum):
    MARKDOWN = "markdown"
    LATEX = "latex"
    CSV = "csv"
    GRANT_OUTLINE = "grant_outline"
    RESEARCH_PROPOSAL = "research_proposal"
    DOCTORAL_PROPOSAL = "doctoral_proposal"
    TEXT = "text"


class InputSource(str, Enum):
    TEXT = "text"
    LIT_SESSION = "lit_session"
    DOI = "doi"
    PMID = "pmid"
    ARXIV = "arxiv"
    OPENALEX = "openalex"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    PDF = "pdf"
    DOCX = "docx"
    MARKDOWN_FILE = "markdown_file"
    ORCID = "orcid"
    WORKSPACE = "workspace"


# ══════════════════════════════════════════════════════════════════════════════
# Scoring
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class OpportunityScore:
    """10-dimension opportunity assessment for a single detected gap."""
    novelty_score: float = 0.0
    feasibility_score: float = 0.0
    publication_probability: float = 0.0
    funding_potential: float = 0.0
    implementation_difficulty: float = 0.5   # higher = harder (inverted in overall)
    research_impact: float = 0.0
    citation_potential: float = 0.0
    interdisciplinary_potential: float = 0.0
    commercialization_potential: float = 0.0
    overall_score: float = 0.0

    novelty_rationale: str = ""
    feasibility_rationale: str = ""
    publication_rationale: str = ""
    funding_rationale: str = ""
    impact_rationale: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ══════════════════════════════════════════════════════════════════════════════
# Methodology Recommendation
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class MethodologyRecommendation:
    research_design: str = ""
    sampling_strategy: str = ""
    data_collection: list[str] = field(default_factory=list)
    analysis_methods: list[str] = field(default_factory=list)
    statistical_techniques: list[str] = field(default_factory=list)
    qualitative_techniques: list[str] = field(default_factory=list)
    mixed_methods_approach: str = ""
    ai_approaches: list[str] = field(default_factory=list)
    survey_design: str = ""
    case_study_notes: str = ""
    experimental_design: str = ""
    rationale: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ══════════════════════════════════════════════════════════════════════════════
# Research Question
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ResearchQuestion:
    question: str = ""
    rationale: str = ""
    novelty_statement: str = ""
    suggested_methodology: str = ""
    expected_contribution: str = ""
    publication_potential: str = "medium"    # "high" | "medium" | "low"
    target_journal_type: str = ""
    hypotheses: list[str] = field(default_factory=list)
    research_objectives: list[str] = field(default_factory=list)
    research_aims: list[str] = field(default_factory=list)
    alternative_paths: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ══════════════════════════════════════════════════════════════════════════════
# Detected Gap
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class DetectedGap:
    gap_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    gap_type: GapType = GapType.THEORETICAL
    title: str = ""
    description: str = ""
    why_gap_exists: str = ""          # explicit WHY reasoning

    # Evidence
    supporting_evidence: list[str] = field(default_factory=list)
    supporting_publications: list[str] = field(default_factory=list)
    contradicting_evidence: list[str] = field(default_factory=list)

    # Assessment
    confidence_score: float = 0.5
    severity: GapSeverity = GapSeverity.MEDIUM
    opportunity_score: OpportunityScore = field(default_factory=OpportunityScore)

    # Actionability
    methodology_recommendation: MethodologyRecommendation = field(default_factory=MethodologyRecommendation)
    research_questions: list[ResearchQuestion] = field(default_factory=list)

    # Context
    alternative_interpretations: list[str] = field(default_factory=list)
    potential_risks: list[str] = field(default_factory=list)
    expected_contribution: str = ""
    recommended_next_steps: list[str] = field(default_factory=list)

    # Competitive context
    competition_level: CompetitionLevel = CompetitionLevel.MEDIUM
    active_researchers_estimate: str = ""
    leading_venues: list[str] = field(default_factory=list)

    # Source tracking
    detected_by: str = "ai"   # "rule_engine" | "ai" | "corpus_analysis" | "hybrid"
    detection_timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        d = asdict(self)
        d["gap_type"] = self.gap_type.value
        d["severity"] = self.severity.value
        d["competition_level"] = self.competition_level.value
        return d


# ══════════════════════════════════════════════════════════════════════════════
# Competitive Landscape
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class CompetitiveLandscape:
    active_researchers: list[str] = field(default_factory=list)
    leading_institutions: list[str] = field(default_factory=list)
    leading_journals: list[str] = field(default_factory=list)
    leading_conferences: list[str] = field(default_factory=list)
    emerging_topics: list[str] = field(default_factory=list)
    declining_topics: list[str] = field(default_factory=list)
    publication_density: PublicationDensity = PublicationDensity.MODERATE
    research_maturity: ResearchMaturity = ResearchMaturity.DEVELOPING
    competition_hotspots: list[str] = field(default_factory=list)
    opportunity_whitespace: list[str] = field(default_factory=list)
    field_growth_rate: str = ""
    interdisciplinary_links: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["publication_density"] = self.publication_density.value
        d["research_maturity"] = self.research_maturity.value
        return d


# ══════════════════════════════════════════════════════════════════════════════
# Corpus Insights (from multi-paper analysis)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class CorpusInsights:
    paper_count: int = 0
    dominant_methodologies: list[str] = field(default_factory=list)
    consensus_areas: list[str] = field(default_factory=list)
    disagreement_areas: list[str] = field(default_factory=list)
    missing_methodologies: list[str] = field(default_factory=list)
    underexplored_populations: list[str] = field(default_factory=list)
    missing_geographies: list[str] = field(default_factory=list)
    missing_datasets: list[str] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)
    saturation_signals: list[str] = field(default_factory=list)
    fragmentation_signals: list[str] = field(default_factory=list)
    knowledge_evolution_notes: list[str] = field(default_factory=list)
    year_range: str = ""
    common_limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


# ══════════════════════════════════════════════════════════════════════════════
# Analysis Request
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class GapIntelligenceRequest:
    topic: str = ""
    content: str = ""                           # raw text, abstract, notes, etc.
    lit_session_id: str = ""                    # link to Literature Intelligence session
    input_sources: list[InputSource] = field(default_factory=lambda: [InputSource.TEXT])
    analysis_depth: AnalysisDepth = AnalysisDepth.STANDARD
    focus_gap_types: list[GapType] = field(default_factory=list)  # empty = all
    discipline: str = ""
    methodology_preference: str = ""
    year_from: Optional[int] = None
    year_to: Optional[int] = None
    target_journal_type: str = ""
    additional_context: str = ""
    user_id: str = ""


# ══════════════════════════════════════════════════════════════════════════════
# Analysis Result
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class GapAnalysisResult:
    result_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    topic: str = ""
    analysis_depth: AnalysisDepth = AnalysisDepth.STANDARD

    # Input metadata
    input_sources: list[str] = field(default_factory=list)
    corpus_size: int = 0
    lit_session_id: str = ""

    # Core outputs
    detected_gaps: list[DetectedGap] = field(default_factory=list)
    total_gaps: int = 0

    # Synthesis
    topic_overview: dict = field(default_factory=dict)
    research_consensus: list[str] = field(default_factory=list)
    research_disagreements: list[str] = field(default_factory=list)
    knowledge_evolution: list[str] = field(default_factory=list)
    saturation_map: dict = field(default_factory=dict)
    missing_variables: list[str] = field(default_factory=list)

    # Aggregate scoring
    field_novelty_index: float = 0.0
    field_opportunity_score: float = 0.0

    # Generated content
    competitive_landscape: CompetitiveLandscape = field(default_factory=CompetitiveLandscape)
    priority_research_questions: list[ResearchQuestion] = field(default_factory=list)
    research_roadmap: list[dict] = field(default_factory=list)

    # Visualizations (JSON-ready for frontend)
    visualizations: dict = field(default_factory=dict)

    # Meta
    analysis_duration_ms: int = 0
    credits_used: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        d = {
            "result_id": self.result_id,
            "user_id": self.user_id,
            "topic": self.topic,
            "analysis_depth": self.analysis_depth.value,
            "input_sources": self.input_sources,
            "corpus_size": self.corpus_size,
            "lit_session_id": self.lit_session_id,
            "detected_gaps": [g.to_dict() for g in self.detected_gaps],
            "total_gaps": self.total_gaps,
            "topic_overview": self.topic_overview,
            "research_consensus": self.research_consensus,
            "research_disagreements": self.research_disagreements,
            "knowledge_evolution": self.knowledge_evolution,
            "saturation_map": self.saturation_map,
            "missing_variables": self.missing_variables,
            "field_novelty_index": round(self.field_novelty_index, 3),
            "field_opportunity_score": round(self.field_opportunity_score, 3),
            "competitive_landscape": self.competitive_landscape.to_dict(),
            "priority_research_questions": [q.to_dict() for q in self.priority_research_questions],
            "research_roadmap": self.research_roadmap,
            "visualizations": self.visualizations,
            "analysis_duration_ms": self.analysis_duration_ms,
            "credits_used": self.credits_used,
            "created_at": self.created_at,
        }
        return d

    def to_summary(self) -> dict:
        """Light view for list endpoints — excludes heavy fields."""
        return {
            "result_id": self.result_id,
            "topic": self.topic,
            "analysis_depth": self.analysis_depth.value,
            "total_gaps": self.total_gaps,
            "field_opportunity_score": round(self.field_opportunity_score, 3),
            "field_novelty_index": round(self.field_novelty_index, 3),
            "corpus_size": self.corpus_size,
            "credits_used": self.credits_used,
            "created_at": self.created_at,
        }
