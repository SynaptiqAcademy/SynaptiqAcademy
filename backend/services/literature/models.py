"""Literature Intelligence — complete domain model for Phase VII."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# ── Enumerations ───────────────────────────────────────────────────────────────

class PaperSource(str, Enum):
    DOI = "doi"
    PMID = "pmid"
    ARXIV = "arxiv"
    OPENALEX = "openalex"
    SEMANTIC_SCHOLAR = "semantic_scholar"
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    MARKDOWN = "markdown"
    WORKSPACE = "workspace"
    MANUAL = "manual"


class ReviewType(str, Enum):
    NARRATIVE = "narrative"
    SYSTEMATIC = "systematic"
    SCOPING = "scoping"
    CRITICAL = "critical"
    INTEGRATIVE = "integrative"
    STATE_OF_ART = "state_of_art"


class SessionStatus(str, Enum):
    CREATED = "created"
    INGESTING = "ingesting"
    ANALYZING = "analyzing"
    COMPARING = "comparing"
    GENERATING = "generating"
    COMPLETE = "complete"
    FAILED = "failed"


class ExportFormat(str, Enum):
    MARKDOWN = "markdown"
    LATEX = "latex"
    BIBTEX = "bibtex"
    RIS = "ris"
    CSV = "csv"
    TEXT = "text"


class VisualizationType(str, Enum):
    CITATION_GRAPH = "citation_graph"
    TIMELINE = "timeline"
    CLUSTER_MAP = "cluster_map"
    KEYWORD_NETWORK = "keyword_network"
    METHODOLOGY_DISTRIBUTION = "methodology_distribution"
    PUBLICATION_TRENDS = "publication_trends"
    AUTHOR_COLLABORATION = "author_collaboration"
    TOPIC_EVOLUTION = "topic_evolution"
    CONCEPT_MAP = "concept_map"


class EvidenceGrade(str, Enum):
    A = "A"   # High quality — RCT / systematic review, strong rigor
    B = "B"   # Good quality — cohort / well-designed observational
    C = "C"   # Moderate quality — cross-sectional / some limitations
    D = "D"   # Low quality — case study / significant limitations
    F = "F"   # Poor quality — opinion / anecdotal


# ── Paper ─────────────────────────────────────────────────────────────────────

@dataclass
class Paper:
    """Raw ingested paper — metadata + available text."""
    paper_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = ""
    source: PaperSource = PaperSource.MANUAL
    source_id: str = ""             # DOI / PMID / arXiv ID / file name

    title: str = ""
    authors: list[str] = field(default_factory=list)
    year: int = 0
    abstract: str = ""
    full_text: str = ""             # available when PDF/DOCX uploaded
    keywords: list[str] = field(default_factory=list)

    journal: str = ""
    volume: str = ""
    issue: str = ""
    pages: str = ""
    doi: str = ""
    pmid: str = ""
    arxiv_id: str = ""
    openalex_id: str = ""

    citation_count: int = 0
    reference_count: int = 0
    cited_by: list[str] = field(default_factory=list)   # DOIs / IDs
    references: list[str] = field(default_factory=list)  # DOIs / IDs

    language: str = "en"
    country: str = ""
    institution: str = ""
    url: str = ""
    open_access: bool = False

    raw_metadata: dict = field(default_factory=dict)
    ingested_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def analysis_text(self) -> str:
        """Best available text for analysis (full_text preferred, else abstract)."""
        return self.full_text or self.abstract

    @property
    def short_ref(self) -> str:
        first_author = self.authors[0].split(",")[0].strip() if self.authors else "Unknown"
        return f"{first_author} ({self.year})"

    def to_dict(self) -> dict:
        return {
            "paper_id": self.paper_id,
            "session_id": self.session_id,
            "source": self.source.value,
            "source_id": self.source_id,
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "abstract": self.abstract,
            "keywords": self.keywords,
            "journal": self.journal,
            "doi": self.doi,
            "pmid": self.pmid,
            "arxiv_id": self.arxiv_id,
            "citation_count": self.citation_count,
            "reference_count": self.reference_count,
            "language": self.language,
            "country": self.country,
            "institution": self.institution,
            "url": self.url,
            "open_access": self.open_access,
            "has_full_text": bool(self.full_text),
            "ingested_at": self.ingested_at,
        }


# ── Analysis ──────────────────────────────────────────────────────────────────

@dataclass
class EvidenceQuality:
    methodological_quality: float = 0.0
    scientific_rigor: float = 0.0
    citation_impact: float = 0.0
    novelty_score: float = 0.0
    reproducibility_score: float = 0.0
    publication_credibility: float = 0.0
    overall_score: float = 0.0
    grade: EvidenceGrade = EvidenceGrade.C
    study_design: str = ""
    quality_notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "methodological_quality": self.methodological_quality,
            "scientific_rigor": self.scientific_rigor,
            "citation_impact": self.citation_impact,
            "novelty_score": self.novelty_score,
            "reproducibility_score": self.reproducibility_score,
            "publication_credibility": self.publication_credibility,
            "overall_score": self.overall_score,
            "grade": self.grade.value,
            "study_design": self.study_design,
            "quality_notes": self.quality_notes,
        }


@dataclass
class PaperAnalysis:
    """19-field deep academic analysis of a single paper."""
    paper_id: str
    session_id: str = ""

    research_question: str = ""
    objectives: list[str] = field(default_factory=list)
    hypothesis: str = ""
    methodology: str = ""
    research_design: str = ""
    variables: dict[str, list[str]] = field(default_factory=lambda: {
        "independent": [], "dependent": [], "control": []
    })
    sample: str = ""
    data_collection: str = ""
    statistical_methods: list[str] = field(default_factory=list)
    results: str = ""
    limitations: list[str] = field(default_factory=list)
    novelty: str = ""
    contribution: str = ""
    future_work: str = ""
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    citation_context: str = ""
    domain: str = ""
    extracted_keywords: list[str] = field(default_factory=list)

    evidence_quality: EvidenceQuality = field(default_factory=EvidenceQuality)
    analysis_confidence: float = 0.0
    analysis_method: str = "ai"      # "ai" | "rule"
    analyzed_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "paper_id": self.paper_id,
            "research_question": self.research_question,
            "objectives": self.objectives,
            "hypothesis": self.hypothesis,
            "methodology": self.methodology,
            "research_design": self.research_design,
            "variables": self.variables,
            "sample": self.sample,
            "data_collection": self.data_collection,
            "statistical_methods": self.statistical_methods,
            "results": self.results,
            "limitations": self.limitations,
            "novelty": self.novelty,
            "contribution": self.contribution,
            "future_work": self.future_work,
            "strengths": self.strengths,
            "weaknesses": self.weaknesses,
            "citation_context": self.citation_context,
            "domain": self.domain,
            "extracted_keywords": self.extracted_keywords,
            "evidence_quality": self.evidence_quality.to_dict(),
            "analysis_confidence": self.analysis_confidence,
            "analyzed_at": self.analyzed_at,
        }


# ── Comparative Analysis ──────────────────────────────────────────────────────

@dataclass
class ComparisonPoint:
    dimension: str
    agreements: list[str] = field(default_factory=list)
    disagreements: list[str] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class ComparativeAnalysis:
    session_id: str
    paper_count: int = 0

    methodology_comparison: ComparisonPoint = field(
        default_factory=lambda: ComparisonPoint("methodology"))
    findings_comparison: ComparisonPoint = field(
        default_factory=lambda: ComparisonPoint("findings"))
    sample_comparison: ComparisonPoint = field(
        default_factory=lambda: ComparisonPoint("sample"))
    statistics_comparison: ComparisonPoint = field(
        default_factory=lambda: ComparisonPoint("statistics"))

    dominant_methodologies: list[str] = field(default_factory=list)
    contradictory_pairs: list[dict] = field(default_factory=list)
    knowledge_evolution: list[str] = field(default_factory=list)
    topic_evolution: list[str] = field(default_factory=list)
    research_trends: list[str] = field(default_factory=list)
    citation_influence_notes: str = ""
    synthesis_summary: str = ""

    def to_dict(self) -> dict:
        def cp(c: ComparisonPoint) -> dict:
            return {
                "agreements": c.agreements,
                "disagreements": c.disagreements,
                "contradictions": c.contradictions,
                "notes": c.notes,
            }
        return {
            "paper_count": self.paper_count,
            "methodology": cp(self.methodology_comparison),
            "findings": cp(self.findings_comparison),
            "sample": cp(self.sample_comparison),
            "statistics": cp(self.statistics_comparison),
            "dominant_methodologies": self.dominant_methodologies,
            "contradictory_pairs": self.contradictory_pairs,
            "knowledge_evolution": self.knowledge_evolution,
            "topic_evolution": self.topic_evolution,
            "research_trends": self.research_trends,
            "synthesis_summary": self.synthesis_summary,
        }


# ── Clustering ────────────────────────────────────────────────────────────────

@dataclass
class ThematicCluster:
    cluster_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    label: str = ""
    description: str = ""
    paper_ids: list[str] = field(default_factory=list)
    top_keywords: list[str] = field(default_factory=list)
    dominant_methodology: str = ""
    year_range: tuple[int, int] = field(default_factory=lambda: (0, 0))
    coherence_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "cluster_id": self.cluster_id,
            "label": self.label,
            "description": self.description,
            "paper_count": len(self.paper_ids),
            "paper_ids": self.paper_ids,
            "top_keywords": self.top_keywords,
            "dominant_methodology": self.dominant_methodology,
            "year_range": list(self.year_range),
            "coherence_score": self.coherence_score,
        }


# ── Research Evolution ────────────────────────────────────────────────────────

@dataclass
class Milestone:
    year: int
    description: str
    paper_ids: list[str] = field(default_factory=list)
    significance: str = "normal"   # "major" | "normal" | "minor"


@dataclass
class ResearchEvolution:
    session_id: str
    milestones: list[Milestone] = field(default_factory=list)
    emerging_topics: list[str] = field(default_factory=list)
    declining_topics: list[str] = field(default_factory=list)
    future_directions: list[str] = field(default_factory=list)
    earliest_year: int = 0
    latest_year: int = 0
    evolution_summary: str = ""

    def to_dict(self) -> dict:
        return {
            "milestones": [
                {"year": m.year, "description": m.description,
                 "paper_ids": m.paper_ids, "significance": m.significance}
                for m in self.milestones
            ],
            "emerging_topics": self.emerging_topics,
            "declining_topics": self.declining_topics,
            "future_directions": self.future_directions,
            "year_range": [self.earliest_year, self.latest_year],
            "evolution_summary": self.evolution_summary,
        }


# ── Research Gaps ─────────────────────────────────────────────────────────────

@dataclass
class ResearchGap:
    gap_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = ""   # "methodological" | "population" | "geographic" | "temporal" | "theoretical" | "data"
    title: str = ""
    description: str = ""
    evidence: list[str] = field(default_factory=list)
    severity: str = "medium"      # "high" | "medium" | "low"
    opportunity_score: float = 0.0
    suggested_design: str = ""
    related_paper_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "gap_id": self.gap_id,
            "type": self.type,
            "title": self.title,
            "description": self.description,
            "evidence": self.evidence,
            "severity": self.severity,
            "opportunity_score": self.opportunity_score,
            "suggested_design": self.suggested_design,
            "related_paper_count": len(self.related_paper_ids),
        }


# ── Review Session ────────────────────────────────────────────────────────────

@dataclass
class GeneratedReview:
    review_type: ReviewType
    title: str = ""
    content: str = ""
    word_count: int = 0
    section_count: int = 0
    citations_included: int = 0
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "review_type": self.review_type.value,
            "title": self.title,
            "content": self.content,
            "word_count": self.word_count,
            "section_count": self.section_count,
            "citations_included": self.citations_included,
            "generated_at": self.generated_at,
        }


@dataclass
class ReviewSession:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    title: str = ""
    description: str = ""
    review_type: ReviewType = ReviewType.NARRATIVE

    paper_ids: list[str] = field(default_factory=list)
    analysis_ids: list[str] = field(default_factory=list)

    comparative_analysis: ComparativeAnalysis | None = None
    clusters: list[ThematicCluster] = field(default_factory=list)
    evolution: ResearchEvolution | None = None
    gaps: list[ResearchGap] = field(default_factory=list)
    generated_review: GeneratedReview | None = None

    status: SessionStatus = SessionStatus.CREATED
    paper_count: int = 0
    analyzed_count: int = 0
    error_message: str = ""

    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    credits_used: int = 0

    def to_dict(self, include_full: bool = False) -> dict:
        d: dict[str, Any] = {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "review_type": self.review_type.value,
            "status": self.status.value,
            "paper_count": len(self.paper_ids),
            "analyzed_count": self.analyzed_count,
            "has_comparative": self.comparative_analysis is not None,
            "cluster_count": len(self.clusters),
            "has_evolution": self.evolution is not None,
            "gap_count": len(self.gaps),
            "has_review": self.generated_review is not None,
            "error_message": self.error_message,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "credits_used": self.credits_used,
        }
        if include_full:
            if self.comparative_analysis:
                d["comparative_analysis"] = self.comparative_analysis.to_dict()
            d["clusters"] = [c.to_dict() for c in self.clusters]
            if self.evolution:
                d["evolution"] = self.evolution.to_dict()
            d["gaps"] = [g.to_dict() for g in self.gaps]
            if self.generated_review:
                d["generated_review"] = self.generated_review.to_dict()
        return d
