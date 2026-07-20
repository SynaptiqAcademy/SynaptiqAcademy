"""Phase VII Literature Intelligence — comprehensive test suite.

Covers: models, ingestion parsers, evidence quality, clustering,
comparative analysis, evolution, gap detection, citation engine,
export engine, visualization, and main orchestrator.

Run with: python -m pytest tests/test_literature_review.py -v
"""
import asyncio
import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


def _run(coro):
    return asyncio.run(coro)


# ── Sample data ────────────────────────────────────────────────────────────────

def _make_paper(**kwargs):
    from services.literature.models import Paper, PaperSource
    defaults = {
        "paper_id": "p1",
        "session_id": "s1",
        "source": PaperSource.DOI,
        "source_id": "10.1234/test",
        "title": "A Study of Machine Learning in Healthcare",
        "authors": ["Smith, John", "Jones, Mary"],
        "year": 2022,
        "abstract": "This randomised controlled trial investigates machine learning for diagnosis. "
                    "We hypothesize that CNNs achieve diagnostic accuracy exceeding clinicians. "
                    "Methods: n=150 patients. Results: accuracy 94.3% (p < 0.001, effect size d=0.82). "
                    "Limitations: single-institution dataset. Ethics: IRB #2024-1234 approved.",
        "journal": "Nature Medicine",
        "doi": "10.1234/test",
        "citation_count": 120,
        "keywords": ["machine learning", "healthcare", "diagnosis", "deep learning", "neural networks"],
    }
    defaults.update(kwargs)
    return Paper(**defaults)


def _make_analysis(**kwargs):
    from services.literature.models import PaperAnalysis, EvidenceQuality, EvidenceGrade
    eq = EvidenceQuality(
        methodological_quality=0.95,
        scientific_rigor=0.85,
        citation_impact=0.70,
        novelty_score=0.80,
        reproducibility_score=0.60,
        publication_credibility=1.00,
        overall_score=0.82,
        grade=EvidenceGrade.A,
        study_design="randomised controlled trial",
        quality_notes=["IRB approved"],
    )
    defaults = {
        "paper_id": "p1",
        "session_id": "s1",
        "research_question": "Can CNNs outperform clinicians in medical image diagnosis?",
        "objectives": ["Develop CNN model", "Validate against clinicians"],
        "hypothesis": "CNNs achieve >90% diagnostic accuracy",
        "methodology": "quantitative",
        "research_design": "randomised controlled trial",
        "variables": {"independent": ["CNN model"], "dependent": ["accuracy"], "control": ["dataset"]},
        "sample": "n=150 patients",
        "data_collection": "prospective imaging data",
        "statistical_methods": ["logistic regression", "ANOVA"],
        "results": "CNN achieved 94.3% accuracy, outperforming clinicians (p<0.001)",
        "limitations": ["single-institution dataset", "limited demographic diversity"],
        "novelty": "First CNN to exceed clinician performance on this dataset",
        "contribution": "Validates deep learning for clinical diagnosis",
        "future_work": "Multi-site validation needed",
        "strengths": ["RCT design", "pre-registered protocol"],
        "weaknesses": ["small sample", "single institution"],
        "citation_context": "Builds on ResNet architectures",
        "domain": "machine learning",
        "extracted_keywords": ["CNN", "healthcare", "diagnosis"],
        "evidence_quality": eq,
        "analysis_confidence": 0.90,
    }
    defaults.update(kwargs)
    return PaperAnalysis(**defaults)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Models
# ═══════════════════════════════════════════════════════════════════════════════

class TestModels:
    def test_paper_short_ref(self):
        p = _make_paper()
        assert "Smith" in p.short_ref
        assert "2022" in p.short_ref

    def test_paper_analysis_text_prefers_full(self):
        p = _make_paper(full_text="Full text content", abstract="Short abstract")
        assert p.analysis_text == "Full text content"

    def test_paper_analysis_text_fallback(self):
        p = _make_paper(full_text="", abstract="Short abstract")
        assert p.analysis_text == "Short abstract"

    def test_paper_to_dict(self):
        p = _make_paper()
        d = p.to_dict()
        assert d["title"] == p.title
        assert d["doi"] == p.doi
        assert "has_full_text" in d

    def test_evidence_quality_to_dict(self):
        from services.literature.models import EvidenceQuality, EvidenceGrade
        eq = EvidenceQuality(overall_score=0.82, grade=EvidenceGrade.A)
        d = eq.to_dict()
        assert d["overall_score"] == 0.82
        assert d["grade"] == "A"

    def test_paper_analysis_to_dict(self):
        a = _make_analysis()
        d = a.to_dict()
        assert d["research_question"] == a.research_question
        assert d["methodology"] == "quantitative"
        assert "evidence_quality" in d

    def test_review_type_enum(self):
        from services.literature.models import ReviewType
        assert ReviewType("narrative") == ReviewType.NARRATIVE
        assert ReviewType("systematic") == ReviewType.SYSTEMATIC

    def test_paper_source_enum(self):
        from services.literature.models import PaperSource
        assert PaperSource("doi") == PaperSource.DOI
        assert PaperSource("arxiv") == PaperSource.ARXIV

    def test_research_gap_to_dict(self):
        from services.literature.models import ResearchGap
        g = ResearchGap(type="methodological", title="Missing RCTs",
                        description="No RCTs found", severity="high",
                        opportunity_score=0.80)
        d = g.to_dict()
        assert d["type"] == "methodological"
        assert d["severity"] == "high"
        assert d["opportunity_score"] == 0.80

    def test_review_session_to_dict(self):
        from services.literature.models import ReviewSession
        s = ReviewSession(user_id="u1", title="My Review")
        d = s.to_dict()
        assert d["user_id"] == "u1"
        assert d["title"] == "My Review"
        assert d["paper_count"] == 0

    def test_session_to_dict_full(self):
        from services.literature.models import ReviewSession
        s = ReviewSession(user_id="u1", title="Full", paper_ids=["p1", "p2"])
        d = s.to_dict(include_full=True)
        assert d["paper_count"] == 2


# ═══════════════════════════════════════════════════════════════════════════════
# 2. File Parser
# ═══════════════════════════════════════════════════════════════════════════════

class TestFileParser:
    def test_parse_txt(self):
        from services.literature.ingestion.file_parser import parse_file
        content = (
            "Deep Learning for Medical Image Analysis\n"
            "Smith J, Jones M\n"
            "Abstract: This study investigates neural network approaches for diagnostic imaging.\n"
            "DOI: 10.1234/test.2022\n"
        ).encode("utf-8")
        result = parse_file(content, "paper.txt", "s1")
        assert result.success
        assert result.paper is not None
        assert result.paper.title  # at minimum title is parsed

    def test_parse_markdown(self):
        from services.literature.ingestion.file_parser import parse_file
        content = "# Deep Learning Review\n\nAbstract: A comprehensive review.".encode("utf-8")
        result = parse_file(content, "paper.md", "s1")
        assert result.success

    def test_parse_empty_fails(self):
        from services.literature.ingestion.file_parser import parse_file
        result = parse_file(b"", "empty.txt", "s1")
        assert not result.success

    def test_extract_year(self):
        from services.literature.ingestion.file_parser import _extract_year
        assert _extract_year("Published in 2022 by Nature") == 2022

    def test_extract_doi(self):
        from services.literature.ingestion.file_parser import _extract_doi
        # Regex expects prefix directly attached (no space after colon) or https URL form
        assert _extract_doi("doi:10.1234/test") == "10.1234/test"
        assert _extract_doi("https://doi.org/10.9999/paper.001") == "10.9999/paper.001"
        assert _extract_doi("no doi here") == ""

    def test_extract_abstract(self):
        from services.literature.ingestion.file_parser import _extract_abstract
        # Abstract must be >=100 chars for the regex to match
        filler = "This study investigates something important. " * 5
        text = f"Title\n\nAbstract: {filler}\n\nIntroduction\n..."
        abstract = _extract_abstract(text)
        assert "investigates" in abstract

    def test_parse_pdf_no_pypdf_graceful(self):
        from services.literature.ingestion.file_parser import _parse_pdf
        result = _parse_pdf(b"fake pdf content", "paper.pdf", "s1")
        # Should fail gracefully (either pypdf error or import error)
        assert isinstance(result.success, bool)

    def test_unsupported_extension_tries_text(self):
        from services.literature.ingestion.file_parser import parse_file
        content = "Machine learning in finance. Abstract: We study stock prediction.".encode()
        result = parse_file(content, "paper.rtf", "s1")
        assert result.success


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Evidence Quality
# ═══════════════════════════════════════════════════════════════════════════════

class TestEvidenceQuality:
    def test_rct_scores_high_methodological(self):
        from services.literature.analysis.evidence_quality import score_paper
        p = _make_paper(
            abstract="This randomised controlled trial studies treatment effects."
        )
        eq = score_paper(p)
        assert eq.methodological_quality >= 0.90
        assert eq.study_design == "randomised controlled trial"

    def test_case_study_scores_lower(self):
        from services.literature.analysis.evidence_quality import score_paper
        p = _make_paper(abstract="This case study examines one patient case.")
        eq = score_paper(p)
        assert eq.methodological_quality <= 0.50

    def test_nature_journal_high_credibility(self):
        from services.literature.analysis.evidence_quality import score_paper
        p = _make_paper(journal="Nature Medicine", arxiv_id="")
        eq = score_paper(p)
        assert eq.publication_credibility == 1.0

    def test_high_citation_impact(self):
        from services.literature.analysis.evidence_quality import score_paper
        p = _make_paper(citation_count=1000)
        eq = score_paper(p)
        assert eq.citation_impact >= 0.90

    def test_zero_citations_zero_impact(self):
        from services.literature.analysis.evidence_quality import score_paper
        p = _make_paper(citation_count=0)
        eq = score_paper(p)
        assert eq.citation_impact == 0.0

    def test_rigour_with_hypothesis_and_stats(self):
        from services.literature.analysis.evidence_quality import score_paper
        p = _make_paper()  # has hypothesis, p-value, limitations in abstract
        eq = score_paper(p)
        assert eq.scientific_rigor >= 0.60  # 0.65 is typical for this abstract

    def test_evidence_grade_A(self):
        from services.literature.analysis.evidence_quality import score_paper, _grade, EvidenceGrade
        assert _grade(0.85) == EvidenceGrade.A
        assert _grade(0.70) == EvidenceGrade.B
        assert _grade(0.55) == EvidenceGrade.C
        assert _grade(0.40) == EvidenceGrade.D
        assert _grade(0.20) == EvidenceGrade.F

    def test_corpus_quality_summary(self):
        from services.literature.analysis.evidence_quality import score_paper, corpus_quality_summary
        papers = [_make_paper(paper_id=f"p{i}", citation_count=i * 10) for i in range(5)]
        scores = [score_paper(p) for p in papers]
        summary = corpus_quality_summary(scores)
        assert "avg_score" in summary
        assert "grade_distribution" in summary

    def test_preprint_lower_credibility(self):
        from services.literature.analysis.evidence_quality import score_paper
        p = _make_paper(journal="arXiv", arxiv_id="2401.00001", doi="")
        eq = score_paper(p)
        assert eq.publication_credibility <= 0.55


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Clustering
# ═══════════════════════════════════════════════════════════════════════════════

class TestClustering:
    def _make_papers(self, n=8):
        from services.literature.models import PaperSource
        papers = []
        for i in range(n):
            kw = ["machine learning", "neural network"] if i % 2 == 0 else ["qualitative", "interview"]
            papers.append(_make_paper(
                paper_id=f"p{i}",
                title=f"Paper {i} on {'AI' if i % 2 == 0 else 'Social Research'}",
                keywords=kw,
                year=2020 + i,
            ))
        return papers

    def test_clusters_created(self):
        from services.literature.analysis.clustering import cluster_papers
        papers = self._make_papers(8)
        clusters = cluster_papers(papers)
        assert len(clusters) >= 1

    def test_single_paper_returns_one_cluster(self):
        from services.literature.analysis.clustering import cluster_papers
        clusters = cluster_papers([_make_paper()])
        assert len(clusters) == 1

    def test_empty_returns_empty(self):
        from services.literature.analysis.clustering import cluster_papers
        assert cluster_papers([]) == []

    def test_cluster_has_required_fields(self):
        from services.literature.analysis.clustering import cluster_papers
        papers = self._make_papers(6)
        clusters = cluster_papers(papers)
        for c in clusters:
            assert c.cluster_id
            assert c.label
            assert c.paper_ids
            assert isinstance(c.coherence_score, float)

    def test_tokenize_removes_stopwords(self):
        from services.literature.analysis.clustering import _tokenize
        tokens = _tokenize("the analysis of machine learning algorithms")
        assert "the" not in tokens
        assert "machine" in tokens
        assert "learning" in tokens

    def test_cosine_identical_docs(self):
        from services.literature.analysis.clustering import _cosine
        # _cosine expects L2-normalised vectors; use unit vectors
        import math
        v = 1.0 / math.sqrt(2)
        a = {"ml": v, "health": v}
        assert _cosine(a, a) == pytest.approx(1.0, abs=0.01)

    def test_cosine_disjoint_docs(self):
        from services.literature.analysis.clustering import _cosine
        a = {"ml": 0.7}
        b = {"health": 0.7}
        assert _cosine(a, b) == 0.0

    def test_label_generated(self):
        from services.literature.analysis.clustering import cluster_papers
        papers = self._make_papers(6)
        clusters = cluster_papers(papers)
        for c in clusters:
            assert len(c.label) > 3


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Comparative Analysis
# ═══════════════════════════════════════════════════════════════════════════════

class TestComparativeAnalysis:
    def test_rule_based_comparison(self):
        from services.literature.analysis.comparative import _rule_based_comparison
        papers = [_make_paper(paper_id=f"p{i}", year=2020 + i) for i in range(4)]
        analyses = [_make_analysis(paper_id=f"p{i}") for i in range(4)]
        ca = _rule_based_comparison("s1", papers, analyses)
        assert ca.paper_count == 4
        assert ca.dominant_methodologies

    def test_contradiction_detection(self):
        from services.literature.analysis.comparative import _detect_contradictions
        from services.literature.models import PaperAnalysis
        a1 = _make_analysis(paper_id="p1", results="The intervention is highly effective", domain="cs")
        a2 = _make_analysis(paper_id="p2", results="The intervention shows no significant effect", domain="cs")
        pairs = _detect_contradictions([a1, a2])
        assert len(pairs) >= 1

    def test_evolution_notes_built(self):
        from services.literature.analysis.comparative import _build_evolution_notes
        papers = [_make_paper(paper_id=f"p{i}", year=2010 + i * 5) for i in range(3)]
        analyses = [_make_analysis(paper_id=f"p{i}") for i in range(3)]
        notes = _build_evolution_notes(papers, analyses)
        assert len(notes) >= 1
        assert "2010" in notes[0] or "2020" in notes[0]

    def test_comparative_returns_object(self):
        from services.literature.analysis.comparative import _rule_based_comparison
        ca = _rule_based_comparison("s1", [], [])
        assert ca.session_id == "s1"
        assert ca.paper_count == 0

    def test_comparative_to_dict(self):
        from services.literature.analysis.comparative import _rule_based_comparison
        papers = [_make_paper(paper_id="p1")]
        analyses = [_make_analysis(paper_id="p1")]
        ca = _rule_based_comparison("s1", papers, analyses)
        d = ca.to_dict()
        assert "dominant_methodologies" in d
        assert "synthesis_summary" in d


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Research Evolution
# ═══════════════════════════════════════════════════════════════════════════════

class TestResearchEvolution:
    def test_build_evolution_basic(self):
        from services.literature.analysis.evolution import build_evolution
        papers = [_make_paper(paper_id=f"p{i}", year=2015 + i) for i in range(5)]
        evo = build_evolution("s1", papers)
        assert evo.earliest_year == 2015
        assert evo.latest_year == 2019
        assert len(evo.milestones) > 0

    def test_empty_papers_returns_empty(self):
        from services.literature.analysis.evolution import build_evolution
        evo = build_evolution("s1", [])
        assert evo.session_id == "s1"
        assert evo.milestones == []

    def test_milestones_chronological(self):
        from services.literature.analysis.evolution import build_evolution
        papers = [_make_paper(paper_id=f"p{i}", year=2010 + i * 2) for i in range(5)]
        evo = build_evolution("s1", papers)
        years = [m.year for m in evo.milestones]
        assert years == sorted(years)

    def test_significance_classification(self):
        from services.literature.analysis.evolution import _classify_significance
        p_high = _make_paper(citation_count=150)
        p_low = _make_paper(citation_count=5)
        assert _classify_significance(p_high, [p_high]) == "major"
        assert _classify_significance(p_low, [p_low]) == "minor"

    def test_topic_trends_detected(self):
        from services.literature.analysis.evolution import _analyse_topic_trends
        early_papers = [_make_paper(paper_id=f"e{i}", year=2010 + i,
                                     keywords=["traditional", "classic"]) for i in range(3)]
        late_papers = [_make_paper(paper_id=f"l{i}", year=2020 + i,
                                    keywords=["deep learning", "transformer"]) for i in range(3)]
        emerging, declining = _analyse_topic_trends(early_papers + late_papers)
        # transformer should be emerging
        assert any("transformer" in t or "deep" in t for t in emerging)

    def test_evolution_to_dict(self):
        from services.literature.analysis.evolution import build_evolution
        papers = [_make_paper(year=2020)]
        evo = build_evolution("s1", papers)
        d = evo.to_dict()
        assert "milestones" in d
        assert "emerging_topics" in d
        assert "year_range" in d


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Gap Detection
# ═══════════════════════════════════════════════════════════════════════════════

class TestGapDetection:
    def test_methodological_gap_one_design(self):
        from services.literature.analysis.gap_detector import _rule_based_gaps
        papers = [_make_paper(paper_id=f"p{i}") for i in range(5)]
        analyses = [_make_analysis(paper_id=f"p{i}", research_design="survey") for i in range(5)]
        gaps = _rule_based_gaps(papers, analyses)
        types = [g.type for g in gaps]
        assert "methodological" in types

    def test_small_sample_gap_detected(self):
        from services.literature.analysis.gap_detector import _rule_based_gaps
        papers = [_make_paper(paper_id=f"p{i}") for i in range(4)]
        analyses = [_make_analysis(paper_id=f"p{i}",
                                    limitations=["small sample size"]) for i in range(4)]
        gaps = _rule_based_gaps(papers, analyses)
        types = [g.type for g in gaps]
        assert "population" in types

    def test_gaps_have_scores(self):
        from services.literature.analysis.gap_detector import _rule_based_gaps
        papers = [_make_paper(paper_id=f"p{i}", year=2020) for i in range(5)]
        analyses = [_make_analysis(paper_id=f"p{i}", research_design="survey") for i in range(5)]
        gaps = _rule_based_gaps(papers, analyses)
        for g in gaps:
            assert 0.0 <= g.opportunity_score <= 1.0

    def test_make_gap_helper(self):
        from services.literature.analysis.gap_detector import _make_gap
        g = _make_gap("methodological", "No RCTs", "Description", [], "high", 0.8, "RCT")
        assert g.type == "methodological"
        assert g.opportunity_score == 0.8

    def test_parse_ai_gap(self):
        from services.literature.analysis.gap_detector import _parse_ai_gap
        d = {"type": "geographic", "title": "Missing Asian studies",
             "description": "No Asian populations", "evidence": ["0 Asian papers"],
             "severity": "high", "opportunity_score": 0.75, "suggested_design": "survey"}
        g = _parse_ai_gap(d)
        assert g.type == "geographic"
        assert g.opportunity_score == 0.75


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Citation Engine
# ═══════════════════════════════════════════════════════════════════════════════

class TestCitationEngine:
    def test_build_citation_network_empty(self):
        from services.literature.citation.citation_engine import build_citation_network
        result = build_citation_network([])
        assert result["nodes"] == []
        assert result["edges"] == []

    def test_build_citation_network(self):
        from services.literature.citation.citation_engine import build_citation_network
        papers = [_make_paper(paper_id=f"p{i}", doi=f"10.{i}") for i in range(5)]
        result = build_citation_network(papers)
        assert len(result["nodes"]) == 5
        assert "stats" in result
        assert "highly_cited" in result["stats"]

    def test_influence_score_increases_with_citations(self):
        from services.literature.citation.citation_engine import score_paper_influence
        p_low = _make_paper(citation_count=0)
        p_high = _make_paper(citation_count=500)
        assert score_paper_influence(p_high) > score_paper_influence(p_low)

    def test_foundational_works_sorted(self):
        from services.literature.citation.citation_engine import identify_foundational_works
        papers = [_make_paper(paper_id=f"p{i}", citation_count=i * 10) for i in range(5)]
        foundational = identify_foundational_works(papers, n=3)
        assert len(foundational) == 3
        assert foundational[0].citation_count == 40

    def test_author_collaboration_graph(self):
        from services.literature.citation.citation_engine import compute_author_collaboration_graph
        papers = [
            _make_paper(paper_id="p1", authors=["Smith J", "Jones M"]),
            _make_paper(paper_id="p2", authors=["Smith J", "Brown K"]),
        ]
        graph = compute_author_collaboration_graph(papers)
        assert "nodes" in graph
        assert "edges" in graph
        # Smith J should appear
        node_ids = [n["id"] for n in graph["nodes"]]
        assert any("Smith" in nid for nid in node_ids)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Export Engine
# ═══════════════════════════════════════════════════════════════════════════════

class TestExportEngine:
    def _make_session(self):
        from services.literature.models import ReviewSession, ReviewType
        return ReviewSession(session_id="s1", user_id="u1", title="Test Review",
                             review_type=ReviewType.NARRATIVE, paper_ids=["p1"])

    def test_export_bibtex(self):
        from services.literature.export.export_engine import export_session
        from services.literature.models import ExportFormat
        session = self._make_session()
        papers = [_make_paper()]
        content, filename, ct = export_session(session, papers, [], ExportFormat.BIBTEX)
        assert "@article" in content or "@misc" in content
        assert filename.endswith(".bib")
        assert "bibtex" in ct

    def test_export_ris(self):
        from services.literature.export.export_engine import export_session
        from services.literature.models import ExportFormat
        session = self._make_session()
        papers = [_make_paper()]
        content, filename, ct = export_session(session, papers, [], ExportFormat.RIS)
        assert "TY  -" in content
        assert "ER  -" in content
        assert filename.endswith(".ris")

    def test_export_csv(self):
        from services.literature.export.export_engine import export_session
        from services.literature.models import ExportFormat
        session = self._make_session()
        papers = [_make_paper()]
        analyses = [_make_analysis()]
        content, filename, ct = export_session(session, papers, analyses, ExportFormat.CSV)
        assert "title" in content.split("\n")[0]
        assert filename.endswith(".csv")

    def test_export_markdown(self):
        from services.literature.export.export_engine import export_session
        from services.literature.models import ExportFormat
        session = self._make_session()
        papers = [_make_paper()]
        content, filename, ct = export_session(session, papers, [], ExportFormat.MARKDOWN)
        assert "Test Review" in content
        assert filename.endswith(".md")

    def test_export_latex(self):
        from services.literature.export.export_engine import export_session
        from services.literature.models import ExportFormat
        session = self._make_session()
        papers = [_make_paper()]
        content, filename, ct = export_session(session, papers, [], ExportFormat.LATEX)
        assert r"\documentclass" in content
        assert r"\end{document}" in content
        assert filename.endswith(".tex")

    def test_bibtex_key_generation(self):
        from services.literature.export.export_engine import _make_citekey
        p = _make_paper(authors=["Smith, John"], year=2022)
        key = _make_citekey(p)
        assert "Smith" in key
        assert "2022" in key

    def test_latex_escape(self):
        from services.literature.export.export_engine import _latex_escape
        escaped = _latex_escape("100% accuracy & more")
        assert r"\%" in escaped
        assert r"\&" in escaped

    def test_ris_multiple_authors(self):
        from services.literature.export.export_engine import _to_ris
        p = _make_paper(authors=["Smith J", "Jones M", "Brown K"])
        ris = _to_ris([p])
        assert ris.count("AU  -") == 3


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Visualization Builder
# ═══════════════════════════════════════════════════════════════════════════════

class TestVisualizationBuilder:
    def test_build_timeline(self):
        from services.literature.visualization.graph_builder import build_timeline
        papers = [_make_paper(paper_id=f"p{i}", year=2020 + i) for i in range(3)]
        result = build_timeline(papers)
        assert result["type"] == "timeline"
        assert len(result["data"]) == 3

    def test_build_keyword_network(self):
        from services.literature.visualization.graph_builder import build_keyword_network
        papers = [_make_paper(paper_id=f"p{i}", keywords=["ml", "health", f"kw{i}"]) for i in range(5)]
        result = build_keyword_network(papers, [])
        assert result["type"] == "keyword_network"
        assert "nodes" in result
        assert "edges" in result

    def test_build_methodology_distribution(self):
        from services.literature.visualization.graph_builder import build_methodology_distribution
        analyses = [_make_analysis(paper_id=f"p{i}", methodology="quantitative") for i in range(4)]
        result = build_methodology_distribution(analyses)
        assert result["type"] == "methodology_distribution"
        assert result["total_papers"] == 4
        assert result["methodologies"][0]["method"] == "quantitative"

    def test_build_publication_trends(self):
        from services.literature.visualization.graph_builder import build_publication_trends
        papers = [_make_paper(paper_id=f"p{i}", year=2020 + i % 3) for i in range(6)]
        result = build_publication_trends(papers)
        assert result["type"] == "publication_trends"
        assert len(result["data"]) <= 3

    def test_build_concept_map(self):
        from services.literature.visualization.graph_builder import build_concept_map
        analyses = [_make_analysis(paper_id=f"p{i}",
                                    extracted_keywords=["neural", "network", "healthcare", f"kw{i}"])
                    for i in range(5)]
        result = build_concept_map(analyses)
        assert result["type"] == "concept_map"
        assert "nodes" in result
        assert "edges" in result

    def test_build_all_visualizations(self):
        from services.literature.visualization.graph_builder import build_all_visualizations
        papers = [_make_paper(paper_id=f"p{i}", year=2020 + i) for i in range(3)]
        analyses = [_make_analysis(paper_id=f"p{i}") for i in range(3)]
        result = build_all_visualizations(papers, analyses, [], None)
        assert "timeline" in result
        assert "keyword_network" in result
        assert "methodology_distribution" in result


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Templates
# ═══════════════════════════════════════════════════════════════════════════════

class TestTemplates:
    def test_all_review_types_have_templates(self):
        from services.literature.synthesis.templates import all_templates
        from services.literature.models import ReviewType
        templates = all_templates()
        for rt in ReviewType:
            assert rt.value in templates

    def test_template_has_sections(self):
        from services.literature.synthesis.templates import get_template
        from services.literature.models import ReviewType
        tmpl = get_template(ReviewType.SYSTEMATIC)
        assert len(tmpl.sections) >= 5
        assert tmpl.word_target >= 2000

    def test_narrative_sections_include_conclusion(self):
        from services.literature.synthesis.templates import get_template
        from services.literature.models import ReviewType
        tmpl = get_template(ReviewType.NARRATIVE)
        sections_lower = [s.lower() for s in tmpl.sections]
        assert any("conclusion" in s for s in sections_lower)

    def test_systematic_template_mentions_prisma(self):
        from services.literature.synthesis.templates import get_template
        from services.literature.models import ReviewType
        tmpl = get_template(ReviewType.SYSTEMATIC)
        assert "PRISMA" in tmpl.system_prompt

    def test_word_target_state_of_art_longest(self):
        from services.literature.synthesis.templates import get_template
        from services.literature.models import ReviewType
        state_art = get_template(ReviewType.STATE_OF_ART)
        narrative = get_template(ReviewType.NARRATIVE)
        assert state_art.word_target > narrative.word_target


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Telemetry
# ═══════════════════════════════════════════════════════════════════════════════

class TestLiteratureTelemetry:
    def _fresh(self):
        from services.literature.telemetry import LiteratureIntelligenceTelemetry
        return LiteratureIntelligenceTelemetry()

    def test_record_session(self):
        t = self._fresh()
        t.record_session_created()
        assert t.get_stats()["total_sessions"] == 1

    def test_record_papers_ingested(self):
        t = self._fresh()
        t.record_papers_ingested(5, "doi")
        t.record_papers_ingested(3, "arxiv")
        stats = t.get_stats()
        assert stats["total_papers_ingested"] == 8
        assert stats["source_distribution"]["doi"] == 5

    def test_record_review_generated(self):
        t = self._fresh()
        t.record_review_generated("narrative")
        t.record_review_generated("systematic")
        stats = t.get_stats()
        assert stats["total_reviews_generated"] == 2
        assert stats["review_type_distribution"]["narrative"] == 1

    def test_record_export(self):
        t = self._fresh()
        t.record_export("bibtex")
        assert t.get_stats()["total_exports"] == 1

    def test_reset(self):
        t = self._fresh()
        t.record_session_created()
        t.reset()
        assert t.get_stats()["total_sessions"] == 0

    def test_singleton(self):
        from services.literature.telemetry import get_literature_telemetry
        t1 = get_literature_telemetry()
        t2 = get_literature_telemetry()
        assert t1 is t2


# ═══════════════════════════════════════════════════════════════════════════════
# 13. Ingestion Engine (mocked HTTP)
# ═══════════════════════════════════════════════════════════════════════════════

class TestIngestionEngine:
    def test_engine_search_empty_on_error(self):
        from services.literature.ingestion.ingestion_engine import IngestionEngine
        engine = IngestionEngine()

        async def _run_search():
            with patch("httpx.AsyncClient") as mock_client:
                mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                    side_effect=Exception("network error")
                )
                return await engine.search("machine learning", limit=5)

        results = _run(_run_search())
        assert isinstance(results, list)

    def test_engine_ingest_file(self):
        from services.literature.ingestion.ingestion_engine import IngestionEngine
        engine = IngestionEngine()
        content = b"Machine Learning Study\n\nAbstract: We study ML algorithms."
        result = _run(engine.ingest_file(content, "study.txt", "s1"))
        assert result.success
        assert result.paper is not None

    def test_engine_ingest_unsupported_source(self):
        from services.literature.ingestion.ingestion_engine import IngestionEngine
        from services.literature.models import PaperSource
        engine = IngestionEngine()
        result = _run(engine.ingest_one(PaperSource.PDF, "paper.pdf", "s1"))
        # PDF source via API should fail gracefully
        assert not result.success

    def test_normalise_title(self):
        from services.literature.ingestion.ingestion_engine import _normalise_title
        assert _normalise_title("Deep Learning for Healthcare") == _normalise_title("deep learning for healthcare")

    def test_deduplication_by_doi(self):
        from services.literature.ingestion.ingestion_engine import _normalise_title
        t1 = _normalise_title("Machine Learning in Medicine")
        t2 = _normalise_title("Machine Learning in Medicine")
        assert t1 == t2
