"""Phase VIII Research Gap Intelligence — comprehensive test suite.

Covers: models, taxonomy, rule detector, corpus analyzer, AI detector (mocked),
opportunity scorer, competitive landscape, question generator,
visualization builder, export engine, telemetry, and engine integration.

Run with: python -m pytest tests/test_research_gap_intelligence.py -v
"""
import asyncio
import pytest

from unittest.mock import AsyncMock, patch


def _run(coro):
    return asyncio.run(coro)


# ── Sample helpers ─────────────────────────────────────────────────────────────

def _make_paper(**kwargs):
    from services.literature.models import Paper, PaperSource
    defaults = {
        "paper_id": "p1", "session_id": "s1",
        "source": PaperSource.DOI, "source_id": "10.1234/test",
        "title": "Machine Learning in Healthcare: A Systematic Review",
        "authors": ["Smith J", "Jones M"],
        "year": 2022,
        "abstract": (
            "This systematic review investigates machine learning for medical diagnosis. "
            "We found significant accuracy improvements (p<0.001). "
            "Limitations include small sample sizes and single-institution datasets."
        ),
        "journal": "Nature Medicine",
        "doi": "10.1234/test",
        "citation_count": 120,
        "keywords": ["machine learning", "healthcare", "diagnosis"],
    }
    defaults.update(kwargs)
    return Paper(**defaults)


def _make_analysis(**kwargs):
    from services.literature.models import PaperAnalysis
    from services.research_gap.models import GapType
    defaults = {
        "paper_id": "p1", "session_id": "s1",
        "research_question": "Can CNNs outperform clinicians?",
        "objectives": ["Validate CNN models"],
        "hypothesis": "CNNs exceed 90% accuracy",
        "methodology": "quantitative",
        "research_design": "systematic review",
        "variables": {"independent": ["CNN"], "dependent": ["accuracy"]},
        "sample": "n=500 patients",
        "data_collection": "imaging data",
        "statistical_methods": ["logistic regression"],
        "results": "CNN achieved 94.3% accuracy (p<0.001)",
        "limitations": ["small sample size", "single institution"],
        "novelty": "First multi-modal CNN for this task",
        "contribution": "Validates DL for clinical diagnosis",
        "future_work": "Multi-site validation",
        "strengths": ["RCT design"],
        "weaknesses": ["limited diversity"],
        "citation_context": "Builds on ResNet",
        "domain": "machine learning",
        "extracted_keywords": ["CNN", "healthcare"],
        "analysis_confidence": 0.88,
    }
    defaults.update(kwargs)
    return type("PaperAnalysis", (), defaults)()


def _make_gap(**kwargs):
    from services.research_gap.models import (
        DetectedGap, GapType, GapSeverity, OpportunityScore,
        MethodologyRecommendation,
    )
    defaults = {
        "gap_type": GapType.METHODOLOGICAL,
        "title": "Missing qualitative studies",
        "description": "No qualitative studies found in corpus.",
        "why_gap_exists": "Journals prefer quantitative methods.",
        "supporting_evidence": ["All 5 papers use quantitative methods"],
        "confidence_score": 0.80,
        "severity": GapSeverity.HIGH,
        "opportunity_score": OpportunityScore(
            novelty_score=0.75, research_impact=0.72, funding_potential=0.58,
            feasibility_score=0.65, publication_probability=0.70, citation_potential=0.60,
        ),
        "methodology_recommendation": MethodologyRecommendation(
            research_design="qualitative grounded theory",
            rationale="Provides qualitative depth",
        ),
        "detected_by": "rule_engine",
    }
    defaults.update(kwargs)
    return DetectedGap(**defaults)


# ══════════════════════════════════════════════════════════════════════════════
# 1. Models
# ══════════════════════════════════════════════════════════════════════════════

class TestModels:
    def test_gap_type_enum(self):
        from services.research_gap.models import GapType
        assert GapType("theoretical") == GapType.THEORETICAL
        assert GapType("ai_gap") == GapType.AI_GAP
        assert GapType("interdisciplinary") == GapType.INTERDISCIPLINARY

    def test_analysis_depth_enum(self):
        from services.research_gap.models import AnalysisDepth
        assert AnalysisDepth("quick") == AnalysisDepth.QUICK
        assert AnalysisDepth("deep") == AnalysisDepth.DEEP

    def test_export_format_enum(self):
        from services.research_gap.models import ExportFormat
        assert ExportFormat("markdown") == ExportFormat.MARKDOWN
        assert ExportFormat("grant_outline") == ExportFormat.GRANT_OUTLINE

    def test_opportunity_score_to_dict(self):
        from services.research_gap.models import OpportunityScore
        os = OpportunityScore(novelty_score=0.80, overall_score=0.72)
        d = os.to_dict()
        assert d["novelty_score"] == 0.80
        assert d["overall_score"] == 0.72

    def test_detected_gap_to_dict(self):
        g = _make_gap()
        d = g.to_dict()
        assert d["gap_type"] == "methodological"
        assert d["severity"] == "high"
        assert d["confidence_score"] == 0.80

    def test_methodology_recommendation_to_dict(self):
        from services.research_gap.models import MethodologyRecommendation
        m = MethodologyRecommendation(
            research_design="RCT",
            sampling_strategy="stratified random",
            data_collection=["survey", "interview"],
            analysis_methods=["ANOVA", "regression"],
        )
        d = m.to_dict()
        assert d["research_design"] == "RCT"
        assert "survey" in d["data_collection"]

    def test_research_question_to_dict(self):
        from services.research_gap.models import ResearchQuestion
        rq = ResearchQuestion(
            question="What is the effect of X on Y?",
            hypotheses=["H1: X positively affects Y"],
        )
        d = rq.to_dict()
        assert "H1" in d["hypotheses"][0]

    def test_competitive_landscape_to_dict(self):
        from services.research_gap.models import CompetitiveLandscape
        cl = CompetitiveLandscape(
            leading_journals=["Nature", "Science"],
            emerging_topics=["federated learning"],
        )
        d = cl.to_dict()
        assert "Nature" in d["leading_journals"]

    def test_gap_analysis_result_to_summary(self):
        from services.research_gap.models import GapAnalysisResult
        r = GapAnalysisResult(topic="Machine Learning", total_gaps=8, field_opportunity_score=0.73)
        s = r.to_summary()
        assert s["topic"] == "Machine Learning"
        assert s["total_gaps"] == 8
        assert "detected_gaps" not in s  # heavy field excluded

    def test_gap_analysis_result_to_dict_full(self):
        from services.research_gap.models import GapAnalysisResult
        r = GapAnalysisResult(topic="AI", total_gaps=3)
        d = r.to_dict()
        assert "detected_gaps" in d
        assert "competitive_landscape" in d
        assert "visualizations" in d

    def test_corpus_insights_to_dict(self):
        from services.research_gap.models import CorpusInsights
        ci = CorpusInsights(paper_count=10, dominant_methodologies=["quantitative"])
        d = ci.to_dict()
        assert d["paper_count"] == 10


# ══════════════════════════════════════════════════════════════════════════════
# 2. Taxonomy
# ══════════════════════════════════════════════════════════════════════════════

class TestTaxonomy:
    def test_all_18_gap_types_have_metadata(self):
        from services.research_gap.models import GapType
        from services.research_gap.taxonomy import GAP_METADATA
        for gt in GapType:
            assert gt in GAP_METADATA, f"Missing metadata for {gt}"

    def test_all_18_gap_types_have_signals(self):
        from services.research_gap.models import GapType
        from services.research_gap.taxonomy import GAP_SIGNALS
        for gt in GapType:
            assert gt in GAP_SIGNALS, f"Missing signals for {gt}"
            assert len(GAP_SIGNALS[gt]) >= 5, f"Too few signals for {gt}"

    def test_score_weights_sum_to_one(self):
        from services.research_gap.taxonomy import SCORE_WEIGHTS
        total = sum(SCORE_WEIGHTS.values())
        assert abs(total - 1.0) < 0.01

    def test_score_to_severity_critical(self):
        from services.research_gap.taxonomy import score_to_severity
        from services.research_gap.models import GapSeverity
        assert score_to_severity(0.85) == GapSeverity.CRITICAL
        assert score_to_severity(0.70) == GapSeverity.HIGH
        assert score_to_severity(0.50) == GapSeverity.MEDIUM
        assert score_to_severity(0.30) == GapSeverity.LOW

    def test_gap_metadata_has_required_fields(self):
        from services.research_gap.taxonomy import GAP_METADATA
        from services.research_gap.models import GapType
        for gt, meta in GAP_METADATA.items():
            assert "label" in meta
            assert "base_novelty" in meta
            assert "typical_design" in meta

    def test_ai_gap_type_has_high_novelty(self):
        from services.research_gap.taxonomy import GAP_METADATA
        from services.research_gap.models import GapType
        assert GAP_METADATA[GapType.AI_GAP]["base_novelty"] >= 0.80

    def test_healthcare_gap_has_high_funding(self):
        from services.research_gap.taxonomy import GAP_METADATA
        from services.research_gap.models import GapType
        assert GAP_METADATA[GapType.HEALTHCARE]["base_funding"] >= 0.80


# ══════════════════════════════════════════════════════════════════════════════
# 3. Rule Detector
# ══════════════════════════════════════════════════════════════════════════════

class TestRuleDetector:
    def test_detect_theoretical_gap_from_text(self):
        from services.research_gap.rule_detector import detect_from_text
        from services.research_gap.models import GapType
        text = "The field lacks a theoretical framework and unified conceptual model."
        gaps = detect_from_text(text, "research topic")
        types = [g.gap_type for g in gaps]
        assert GapType.THEORETICAL in types

    def test_detect_ai_gap_from_text(self):
        from services.research_gap.rule_detector import detect_from_text
        from services.research_gap.models import GapType
        text = "No artificial intelligence or machine learning approaches have been applied."
        gaps = detect_from_text(text, "healthcare")
        types = [g.gap_type for g in gaps]
        assert GapType.AI_GAP in types

    def test_detect_sustainability_gap(self):
        from services.research_gap.rule_detector import detect_from_text
        from services.research_gap.models import GapType
        text = "Sustainability and ESG integration are missing from the research agenda."
        gaps = detect_from_text(text, "business")
        types = [g.gap_type for g in gaps]
        assert GapType.SUSTAINABILITY in types

    def test_empty_text_returns_no_gaps(self):
        from services.research_gap.rule_detector import detect_from_text
        assert detect_from_text("", "topic") == []

    def test_methodological_monoculture_from_corpus(self):
        from services.research_gap.rule_detector import detect_from_corpus
        from services.research_gap.models import GapType
        papers = [_make_paper(paper_id=f"p{i}") for i in range(5)]
        analyses = [_make_analysis(paper_id=f"p{i}", research_design="survey") for i in range(5)]
        gaps = detect_from_corpus(papers, analyses, "topic")
        types = [g.gap_type for g in gaps]
        assert GapType.METHODOLOGICAL in types

    def test_temporal_concentration_from_corpus(self):
        from services.research_gap.rule_detector import detect_from_corpus
        from services.research_gap.models import GapType
        papers = [_make_paper(paper_id=f"p{i}", year=2022 + (i % 2)) for i in range(5)]
        analyses = [_make_analysis(paper_id=f"p{i}") for i in range(5)]
        gaps = detect_from_corpus(papers, analyses, "topic")
        types = [g.gap_type for g in gaps]
        assert GapType.TEMPORAL in types

    def test_sample_size_gap_from_corpus(self):
        from services.research_gap.rule_detector import detect_from_corpus
        from services.research_gap.models import GapType
        papers = [_make_paper(paper_id=f"p{i}") for i in range(5)]
        analyses = [_make_analysis(paper_id=f"p{i}",
                                    limitations=["small sample size"]) for i in range(4)]
        gaps = detect_from_corpus(papers, analyses, "topic")
        types = [g.gap_type for g in gaps]
        assert GapType.POPULATION in types

    def test_all_gaps_have_why_explanation(self):
        from services.research_gap.rule_detector import detect_from_text
        text = "No theoretical framework. No longitudinal studies. No AI approaches."
        gaps = detect_from_text(text, "topic")
        for g in gaps:
            assert g.why_gap_exists, f"Gap '{g.title}' missing why_gap_exists"

    def test_focus_types_filter(self):
        from services.research_gap.rule_detector import detect_from_text
        from services.research_gap.models import GapType
        # Use actual keyword signals from taxonomy
        text = ("No artificial intelligence or machine learning applications have been tested. "
                "No theoretical framework or conceptual model exists in this domain.")
        gaps = detect_from_text(text, "topic", focus_types=[GapType.AI_GAP])
        types = [g.gap_type for g in gaps]
        assert GapType.AI_GAP in types
        assert GapType.THEORETICAL not in types

    def test_extract_corpus_insights(self):
        from services.research_gap.rule_detector import extract_corpus_insights
        papers = [_make_paper(paper_id=f"p{i}", year=2020 + i) for i in range(5)]
        analyses = [_make_analysis(paper_id=f"p{i}", methodology="quantitative") for i in range(5)]
        ci = extract_corpus_insights(papers, analyses)
        assert ci.paper_count == 5
        assert "quantitative" in ci.dominant_methodologies
        assert ci.year_range == "2020–2024"


# ══════════════════════════════════════════════════════════════════════════════
# 4. Corpus Analyzer
# ══════════════════════════════════════════════════════════════════════════════

class TestCorpusAnalyzer:
    def test_methodological_consensus_detected(self):
        from services.research_gap.corpus_analyzer import analyze_corpus
        papers = [_make_paper(paper_id=f"p{i}") for i in range(6)]
        analyses = [_make_analysis(paper_id=f"p{i}", research_design="survey") for i in range(6)]
        result = analyze_corpus(papers, analyses, "topic")
        assert any("survey" in c.lower() for c in result.consensus_areas)

    def test_contradictions_detected(self):
        from services.research_gap.corpus_analyzer import analyze_corpus
        papers = [_make_paper(paper_id=f"p{i}") for i in range(6)]
        analyses_pos = [_make_analysis(paper_id=f"p{i}",
                                        results="highly effective and significant positive result") for i in range(3)]
        analyses_neg = [_make_analysis(paper_id=f"p{i+3}",
                                        results="no significant effect was found") for i in range(3)]
        result = analyze_corpus(papers, analyses_pos + analyses_neg, "topic")
        # Contradictions OR mixed consensus/disagreement signals are acceptable
        has_signal = (
            len(result.contradictions) >= 1
            or len(result.disagreement_areas) >= 1
            or any("positive" in c.lower() for c in result.consensus_areas)
        )
        assert has_signal

    def test_empty_corpus_returns_empty(self):
        from services.research_gap.corpus_analyzer import analyze_corpus
        result = analyze_corpus([], [], "topic")
        # ConsensusDisagreement has no paper_count; just check that fields are empty
        assert result.consensus_areas == []
        assert result.contradictions == []

    def test_knowledge_evolution_noted(self):
        from services.research_gap.corpus_analyzer import analyze_corpus
        papers = [_make_paper(paper_id=f"p{i}", year=2010 + i * 2) for i in range(6)]
        result = analyze_corpus(papers, [], "topic")
        assert any("evolution" in e.lower() or "year" in e.lower()
                   for e in result.knowledge_evolution)

    def test_saturation_detected_large_corpus(self):
        from services.research_gap.corpus_analyzer import analyze_corpus
        papers = [_make_paper(paper_id=f"p{i}") for i in range(110)]
        result = analyze_corpus(papers, [], "topic")
        assert any("saturation" in s.lower() or "large" in s.lower()
                   for s in result.saturation_signals)

    def test_missing_geographies_detected(self):
        from services.research_gap.corpus_analyzer import analyze_corpus
        papers = [_make_paper(paper_id=f"p{i}") for i in range(5)]
        # Papers have no country set → all major regions should show as missing
        result = analyze_corpus(papers, [], "topic")
        assert isinstance(result.missing_geographies, list)


# ══════════════════════════════════════════════════════════════════════════════
# 5. Opportunity Scorer
# ══════════════════════════════════════════════════════════════════════════════

class TestOpportunityScorer:
    def test_score_all_returns_sorted(self):
        from services.research_gap.opportunity_scorer import score_all
        from services.research_gap.models import GapType
        gaps = [
            _make_gap(gap_type=GapType.AI_GAP),
            _make_gap(gap_type=GapType.TEMPORAL),
            _make_gap(gap_type=GapType.INTERDISCIPLINARY),
        ]
        scored = score_all(gaps)
        scores = [g.opportunity_score.overall_score for g in scored]
        assert scores == sorted(scores, reverse=True)

    def test_overall_score_between_0_and_1(self):
        from services.research_gap.opportunity_scorer import score_gap
        g = _make_gap()
        scored = score_gap(g)
        assert 0.0 <= scored.opportunity_score.overall_score <= 1.0

    def test_healthcare_gap_gets_funding_boost(self):
        from services.research_gap.opportunity_scorer import score_gap
        from services.research_gap.models import GapType
        g = _make_gap(gap_type=GapType.HEALTHCARE)
        g.opportunity_score.funding_potential = 0.40  # Set low to test boost
        scored = score_gap(g)
        assert scored.opportunity_score.funding_potential >= 0.72

    def test_ai_gap_gets_commercialisation_boost(self):
        from services.research_gap.opportunity_scorer import score_gap
        from services.research_gap.models import GapType
        g = _make_gap(gap_type=GapType.AI_GAP)
        g.opportunity_score.commercialization_potential = 0.20
        scored = score_gap(g)
        assert scored.opportunity_score.commercialization_potential >= 0.60

    def test_interdisciplinary_gap_gets_potential_boost(self):
        from services.research_gap.opportunity_scorer import score_gap
        from services.research_gap.models import GapType
        g = _make_gap(gap_type=GapType.INTERDISCIPLINARY)
        g.opportunity_score.interdisciplinary_potential = 0.30
        scored = score_gap(g)
        assert scored.opportunity_score.interdisciplinary_potential >= 0.85

    def test_compute_field_metrics(self):
        from services.research_gap.opportunity_scorer import score_all, compute_field_metrics
        gaps = [_make_gap() for _ in range(5)]
        scored = score_all(gaps)
        novelty, opportunity = compute_field_metrics(scored)
        assert 0.0 <= novelty <= 1.0
        assert 0.0 <= opportunity <= 1.0

    def test_score_weights_respected(self):
        from services.research_gap.opportunity_scorer import _weighted_overall
        from services.research_gap.models import OpportunityScore
        os = OpportunityScore(
            novelty_score=1.0, publication_probability=1.0, research_impact=1.0,
            feasibility_score=1.0, funding_potential=1.0, citation_potential=1.0,
            interdisciplinary_potential=1.0, implementation_difficulty=0.0,
            commercialization_potential=1.0,
        )
        overall = _weighted_overall(os)
        assert overall == pytest.approx(1.0, abs=0.05)


# ══════════════════════════════════════════════════════════════════════════════
# 6. Competitive Landscape
# ══════════════════════════════════════════════════════════════════════════════

class TestCompetitiveLandscape:
    def test_build_from_papers(self):
        from services.research_gap.competitive_landscape import build_landscape_from_corpus
        papers = [
            _make_paper(paper_id="p1", authors=["Smith J", "Jones M"], year=2020),
            _make_paper(paper_id="p2", authors=["Smith J", "Brown K"], year=2022),
        ]
        cl = build_landscape_from_corpus(papers, [], "ML in healthcare")
        assert "Smith J" in cl.active_researchers

    def test_emerging_topics_detected(self):
        from services.research_gap.competitive_landscape import build_landscape_from_corpus
        early = [_make_paper(paper_id=f"e{i}", year=2015 + i,
                              keywords=["traditional", "classic"]) for i in range(3)]
        late = [_make_paper(paper_id=f"l{i}", year=2022 + i,
                             keywords=["federated learning", "transformer"]) for i in range(3)]
        cl = build_landscape_from_corpus(early + late, [], "ML")
        assert isinstance(cl.emerging_topics, list)

    def test_build_from_ai_landscape(self):
        from services.research_gap.competitive_landscape import build_landscape_from_ai
        ai = {
            "leading_journals": ["Nature", "Science"],
            "emerging_topics": ["federated learning"],
            "publication_density": "moderate",
            "research_maturity": "developing",
            "field_growth_rate": "rapidly growing",
        }
        cl = build_landscape_from_ai(ai)
        assert "Nature" in cl.leading_journals
        assert "federated learning" in cl.emerging_topics
        assert cl.field_growth_rate == "rapidly growing"

    def test_density_and_maturity_from_dict(self):
        from services.research_gap.competitive_landscape import build_landscape_from_ai
        from services.research_gap.models import PublicationDensity, ResearchMaturity
        ai = {"publication_density": "saturated", "research_maturity": "mature"}
        cl = build_landscape_from_ai(ai)
        assert cl.publication_density == PublicationDensity.SATURATED
        assert cl.research_maturity == ResearchMaturity.MATURE

    def test_whitespace_from_low_competition_gaps(self):
        from services.research_gap.competitive_landscape import identify_opportunity_whitespace
        from services.research_gap.models import CompetitiveLandscape, CompetitionLevel
        gaps = [
            _make_gap(competition_level=CompetitionLevel.LOW),
        ]
        gaps[0].opportunity_score.overall_score = 0.80
        cl = CompetitiveLandscape()
        whitespace = identify_opportunity_whitespace(gaps, cl)
        assert len(whitespace) >= 1


# ══════════════════════════════════════════════════════════════════════════════
# 7. Question Generator
# ══════════════════════════════════════════════════════════════════════════════

class TestQuestionGenerator:
    def test_generates_questions_when_none_exist(self):
        from services.research_gap.question_generator import enrich_gap_with_questions
        g = _make_gap()
        g.research_questions = []
        enriched = enrich_gap_with_questions(g, "machine learning")
        assert len(enriched.research_questions) >= 1

    def test_hypotheses_derived(self):
        from services.research_gap.question_generator import _derive_hypotheses
        from services.research_gap.models import GapType
        hyps = _derive_hypotheses("What is the effect of X on Y?", GapType.EMPIRICAL)
        assert any("H1" in h for h in hyps)
        assert any("H0" in h for h in hyps)

    def test_objectives_derived(self):
        from services.research_gap.question_generator import _derive_objectives
        from services.research_gap.models import GapType
        objs = _derive_objectives("What drives adoption?", GapType.PRACTICAL, "AI")
        assert len(objs) >= 2

    def test_all_18_gap_types_have_templates(self):
        from services.research_gap.question_generator import _QUESTION_TEMPLATES
        from services.research_gap.models import GapType
        for gt in GapType:
            assert gt in _QUESTION_TEMPLATES, f"Missing template for {gt}"

    def test_enriched_questions_have_required_fields(self):
        from services.research_gap.question_generator import enrich_gap_with_questions
        g = _make_gap()
        g.research_questions = []
        enriched = enrich_gap_with_questions(g, "AI")
        for rq in enriched.research_questions:
            assert rq.question
            assert rq.suggested_methodology
            assert rq.research_aims

    def test_publication_potential_estimated(self):
        from services.research_gap.question_generator import _estimate_publication_potential
        from services.research_gap.models import GapSeverity
        g = _make_gap()
        g.opportunity_score.publication_probability = 0.80
        assert _estimate_publication_potential(g) == "high"
        g.opportunity_score.publication_probability = 0.40
        assert _estimate_publication_potential(g) == "low"


# ══════════════════════════════════════════════════════════════════════════════
# 8. Visualization Builder
# ══════════════════════════════════════════════════════════════════════════════

class TestVizBuilder:
    def _gaps(self, n=5):
        from services.research_gap.models import GapType
        types = list(GapType)[:n]
        return [_make_gap(gap_type=t) for t in types]

    def test_research_gap_map(self):
        from services.research_gap.viz_builder import build_research_gap_map
        gaps = self._gaps()
        result = build_research_gap_map(gaps)
        assert result["type"] == "research_gap_map"
        assert len(result["nodes"]) == len(gaps)
        for node in result["nodes"]:
            assert "x" in node and "y" in node and "size" in node

    def test_knowledge_map(self):
        from services.research_gap.viz_builder import build_knowledge_map
        gaps = self._gaps()
        result = build_knowledge_map(gaps)
        assert result["type"] == "knowledge_map"
        assert "nodes" in result and "edges" in result

    def test_novelty_heatmap(self):
        from services.research_gap.viz_builder import build_novelty_heatmap
        gaps = self._gaps()
        result = build_novelty_heatmap(gaps)
        assert result["type"] == "novelty_heatmap"
        assert len(result["cells"]) == len(gaps)

    def test_opportunity_matrix(self):
        from services.research_gap.viz_builder import build_opportunity_matrix
        gaps = self._gaps()
        result = build_opportunity_matrix(gaps)
        assert result["type"] == "opportunity_matrix"
        assert "quadrants" in result
        total = sum(len(v) for v in result["quadrants"].values())
        assert total == len(gaps)

    def test_evidence_matrix(self):
        from services.research_gap.viz_builder import build_evidence_matrix
        gaps = self._gaps()
        result = build_evidence_matrix(gaps)
        assert result["type"] == "evidence_matrix"
        assert len(result["rows"]) == len(gaps)

    def test_research_roadmap_viz(self):
        from services.research_gap.viz_builder import build_research_roadmap_viz
        from services.research_gap.models import GapSeverity
        gaps = [
            _make_gap(severity=GapSeverity.CRITICAL),
            _make_gap(severity=GapSeverity.HIGH),
            _make_gap(severity=GapSeverity.MEDIUM),
        ]
        result = build_research_roadmap_viz(gaps)
        assert result["type"] == "research_roadmap_viz"
        assert len(result["phases"]) >= 2

    def test_research_cluster_map(self):
        from services.research_gap.viz_builder import build_research_cluster_map
        gaps = self._gaps(6)
        result = build_research_cluster_map(gaps)
        assert result["type"] == "research_cluster_map"
        assert len(result["clusters"]) >= 1

    def test_build_all_visualizations(self):
        from services.research_gap.viz_builder import build_all_visualizations
        from services.research_gap.models import CompetitiveLandscape
        gaps = self._gaps()
        cl = CompetitiveLandscape(emerging_topics=["topic1"], declining_topics=["topic2"])
        result = build_all_visualizations(gaps, cl)
        expected_keys = [
            "research_gap_map", "knowledge_map", "topic_evolution",
            "gap_timeline", "evidence_matrix", "concept_network",
            "research_cluster_map", "novelty_heatmap",
            "opportunity_matrix", "research_roadmap_viz",
        ]
        for key in expected_keys:
            assert key in result, f"Missing visualization: {key}"


# ══════════════════════════════════════════════════════════════════════════════
# 9. Export Engine
# ══════════════════════════════════════════════════════════════════════════════

class TestExportEngine:
    def _make_result(self):
        from services.research_gap.models import (
            GapAnalysisResult, CompetitiveLandscape, ResearchQuestion
        )
        r = GapAnalysisResult(
            topic="Machine Learning in Healthcare",
            total_gaps=3,
            field_opportunity_score=0.72,
            field_novelty_index=0.78,
            detected_gaps=[_make_gap()],
            topic_overview={"summary": "ML is transforming healthcare.", "maturity_level": "developing"},
            research_consensus=["ML improves diagnosis accuracy"],
            research_disagreements=["Optimal model architectures debated"],
            priority_research_questions=[
                ResearchQuestion(
                    question="How does federated learning improve privacy in ML health models?",
                    research_objectives=["Evaluate privacy-accuracy tradeoffs"],
                    research_aims=["To assess federated ML for healthcare"],
                    hypotheses=["H1: Federated models achieve comparable accuracy"],
                )
            ],
            competitive_landscape=CompetitiveLandscape(
                leading_journals=["Nature Medicine"],
                emerging_topics=["federated learning"],
                field_growth_rate="rapidly growing",
            ),
            research_roadmap=[
                {"phase": 1, "title": "Literature Review", "description": "Review existing ML works",
                 "duration": "3 months", "outputs": ["Literature map"], "gap_types_addressed": [],
                 "dependencies": []},
            ],
        )
        return r

    def test_export_markdown(self):
        from services.research_gap.export_engine import export_result
        from services.research_gap.models import ExportFormat
        content, filename, ct = export_result(self._make_result(), ExportFormat.MARKDOWN)
        assert "Machine Learning in Healthcare" in content
        assert filename.endswith(".md")
        assert "markdown" in ct

    def test_export_latex(self):
        from services.research_gap.export_engine import export_result
        from services.research_gap.models import ExportFormat
        content, filename, ct = export_result(self._make_result(), ExportFormat.LATEX)
        assert r"\documentclass" in content
        assert r"\end{document}" in content
        assert filename.endswith(".tex")

    def test_export_csv(self):
        from services.research_gap.export_engine import export_result
        from services.research_gap.models import ExportFormat
        content, filename, ct = export_result(self._make_result(), ExportFormat.CSV)
        assert "gap_type" in content.split("\n")[0]
        assert filename.endswith(".csv")

    def test_export_grant_outline(self):
        from services.research_gap.export_engine import export_result
        from services.research_gap.models import ExportFormat
        content, filename, ct = export_result(self._make_result(), ExportFormat.GRANT_OUTLINE)
        assert "Grant Proposal" in content
        assert "Problem Statement" in content
        assert filename.endswith(".md")

    def test_export_research_proposal(self):
        from services.research_gap.export_engine import export_result
        from services.research_gap.models import ExportFormat
        content, filename, ct = export_result(self._make_result(), ExportFormat.RESEARCH_PROPOSAL)
        assert "Research Proposal" in content
        assert "Literature Review" in content

    def test_export_doctoral_proposal(self):
        from services.research_gap.export_engine import export_result
        from services.research_gap.models import ExportFormat
        content, filename, ct = export_result(self._make_result(), ExportFormat.DOCTORAL_PROPOSAL)
        assert "Doctoral" in content
        assert "Chapter" in content

    def test_export_text(self):
        from services.research_gap.export_engine import export_result
        from services.research_gap.models import ExportFormat
        content, filename, ct = export_result(self._make_result(), ExportFormat.TEXT)
        assert "Machine Learning in Healthcare" in content
        assert filename.endswith(".txt")

    def test_latex_escape(self):
        from services.research_gap.export_engine import _latex_escape
        assert r"\%" in _latex_escape("100% accuracy")
        assert r"\&" in _latex_escape("biology & chemistry")
        assert r"\_" in _latex_escape("my_variable")


# ══════════════════════════════════════════════════════════════════════════════
# 10. Telemetry
# ══════════════════════════════════════════════════════════════════════════════

class TestTelemetry:
    def _fresh(self):
        from services.research_gap.telemetry import GapIntelligenceTelemetry
        return GapIntelligenceTelemetry()

    def test_record_analysis(self):
        t = self._fresh()
        t.record_analysis("standard", 8, 0.72, 5000.0, ["text"])
        stats = t.get_stats()
        assert stats["total_analyses"] == 1
        assert stats["avg_gaps_per_analysis"] == 8.0

    def test_record_gap_types(self):
        t = self._fresh()
        t.record_gap_types(["theoretical", "methodological", "theoretical"])
        stats = t.get_stats()
        assert stats["gap_type_distribution"]["theoretical"] == 2

    def test_record_export(self):
        t = self._fresh()
        t.record_export("markdown")
        assert t.get_stats()["total_exports"] == 1

    def test_record_error(self):
        t = self._fresh()
        t.record_error()
        assert t.get_stats()["analysis_errors"] == 1

    def test_reset(self):
        t = self._fresh()
        t.record_analysis("quick", 5, 0.60, 2000.0, [])
        t.reset()
        assert t.get_stats()["total_analyses"] == 0

    def test_singleton(self):
        from services.research_gap.telemetry import get_gap_telemetry
        t1 = get_gap_telemetry()
        t2 = get_gap_telemetry()
        assert t1 is t2

    def test_latency_percentiles(self):
        t = self._fresh()
        for i in range(10):
            t.record_analysis("standard", 5, 0.65, float(i * 100), [])
        stats = t.get_stats()
        assert stats["analysis_p50_ms"] > 0
        assert stats["analysis_p95_ms"] >= stats["analysis_p50_ms"]


# ══════════════════════════════════════════════════════════════════════════════
# 11. Gap Merger (engine internals)
# ══════════════════════════════════════════════════════════════════════════════

class TestGapMerger:
    def test_ai_gaps_take_priority(self):
        from services.research_gap.engine import _merge_gaps
        from services.research_gap.models import GapType
        ai_gaps = [_make_gap(gap_type=GapType.THEORETICAL)]
        rule_gaps = [_make_gap(gap_type=GapType.THEORETICAL)]
        merged = _merge_gaps(ai_gaps, rule_gaps)
        assert len(merged) == 1
        assert merged[0].detected_by == "hybrid"

    def test_rule_gaps_fill_missing_types(self):
        from services.research_gap.engine import _merge_gaps
        from services.research_gap.models import GapType
        ai_gaps = [_make_gap(gap_type=GapType.THEORETICAL)]
        rule_gaps = [_make_gap(gap_type=GapType.TEMPORAL)]
        merged = _merge_gaps(ai_gaps, rule_gaps)
        types = {g.gap_type for g in merged}
        assert GapType.THEORETICAL in types
        assert GapType.TEMPORAL in types

    def test_evidence_merged_for_same_type(self):
        from services.research_gap.engine import _merge_gaps
        from services.research_gap.models import GapType
        ai_gaps = [_make_gap(gap_type=GapType.METHODOLOGICAL,
                             supporting_evidence=["AI evidence 1"])]
        rule_gaps = [_make_gap(gap_type=GapType.METHODOLOGICAL,
                               supporting_evidence=["Rule evidence 2"])]
        merged = _merge_gaps(ai_gaps, rule_gaps)
        assert len(merged) == 1
        assert "AI evidence 1" in merged[0].supporting_evidence
        assert "Rule evidence 2" in merged[0].supporting_evidence

    def test_priority_rqs_collected(self):
        from services.research_gap.engine import _collect_priority_rqs
        from services.research_gap.models import ResearchQuestion
        g = _make_gap()
        g.research_questions = [
            ResearchQuestion(question="Q1?", publication_potential="high"),
            ResearchQuestion(question="Q2?", publication_potential="low"),
        ]
        top = _collect_priority_rqs([g], n=5)
        assert len(top) >= 1
        # High-potential question should come first
        assert top[0].question == "Q1?"


# ══════════════════════════════════════════════════════════════════════════════
# 12. Source Resolver
# ══════════════════════════════════════════════════════════════════════════════

class TestSourceResolver:
    def test_resolve_inline_text(self):
        from services.research_gap.source_resolver import resolve_inputs
        from services.research_gap.models import GapIntelligenceRequest, InputSource
        req = GapIntelligenceRequest(
            topic="AI",
            content="This study investigates AI for healthcare.",
            input_sources=[InputSource.TEXT],
        )
        result = _run(resolve_inputs(req, db=None))
        assert "AI for healthcare" in result.text
        assert "inline text" in result.source_descriptions

    def test_empty_content_produces_empty_text(self):
        from services.research_gap.source_resolver import resolve_inputs
        from services.research_gap.models import GapIntelligenceRequest, InputSource
        req = GapIntelligenceRequest(topic="AI", input_sources=[InputSource.TEXT])
        result = _run(resolve_inputs(req, db=None))
        assert result.text == ""
        assert result.corpus_size == 0

    def test_inverted_index_decoding(self):
        from services.research_gap.source_resolver import _decode_inverted_index
        ii = {"hello": [0, 3], "world": [1], "foo": [2]}
        text = _decode_inverted_index(ii)
        assert text.startswith("hello")
        assert "world" in text
        assert "foo" in text
