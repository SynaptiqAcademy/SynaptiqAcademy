"""Phase IX Manuscript Intelligence — comprehensive test suite.

Covers: models, doc_parser, section_detector, scientific_reviewer,
writing_reviewer, literature_reviewer, method_reviewer,
statistical_reviewer, journal_matcher, revision_planner,
viz_builder, export_engine, telemetry, engine internals.

Run with: python -m pytest tests/test_manuscript_intelligence.py -v
"""
import asyncio
import pytest

from unittest.mock import AsyncMock, patch


def _run(coro):
    return asyncio.run(coro)


# ── Sample text helpers ────────────────────────────────────────────────────────

_MINIMAL_TEXT = (
    "Abstract\n"
    "This study investigates machine learning for medical diagnosis. "
    "We aim to evaluate CNN accuracy on chest X-rays. "
    "Results show significant improvement (p<0.001, Cohen's d=0.82). "
    "However, limitations include small sample size (n=120).\n\n"
    "Introduction\nMachine learning (ML) has emerged as a transformative technology. "
    "Previous studies (Jones, 2021; Smith et al., 2022; Brown, 2020) have shown promise. "
    "However, no theoretical framework exists for clinical validation.\n\n"
    "Methodology\nThis study employs a randomized controlled trial design. "
    "Participants (n=120) were selected via stratified random sampling. "
    "A validated questionnaire (Cronbach α=0.87) was administered. "
    "Data were analyzed using logistic regression (95% CI [0.72, 0.94]).\n\n"
    "Results\nThe mean accuracy was 94.3% (SD=2.1, p<0.001). "
    "Effect size Cohen's d=0.82 indicates a large effect. "
    "Table 1 and Figure 1 illustrate the findings.\n\n"
    "Discussion\nThe findings align with Jones (2021) but contradict Brown (2020). "
    "Limitations include single-institution data and convenience sampling.\n\n"
    "Conclusions\nCNN achieves superior accuracy for diagnosis. "
    "Future research should replicate across multi-site datasets.\n\n"
    "Ethics Statement\nThis study received IRB approval (No. 2021-045). "
    "Informed consent was obtained from all participants.\n\n"
    "Data Availability\nData available upon reasonable request to the corresponding author.\n\n"
    "Conflict of Interest\nThe authors declare no conflict of interest.\n\n"
    "References\n"
    "Jones, J. (2021). Deep learning in medicine. Nature Medicine, 15(3), 102–108.\n"
    "Smith, A., et al. (2022). CNN for diagnosis. JAMA, 328(10), 1001–1010.\n"
    "Brown, K. (2020). Limitations of AI. Lancet, 396(4), 200–210.\n"
    "Garcia, M. (2019). Clinical validation methods. BMJ, 365, k1234.\n"
    "Lee, S. (2018). Benchmark datasets. IEEE, 12(5), 45–60.\n"
)

_SHORT_TEXT = "This is a short manuscript."
_LATEX_TEXT = r"""
\documentclass{article}
\title{Machine Learning for Diagnosis}
\begin{document}
\section{Abstract}
This study investigates \textit{machine learning} for diagnosis.
We found significant improvement ($p < 0.001$) in accuracy.
\section{Methodology}
We used a randomised controlled trial with $n=200$ participants.
\end{document}
"""
_MARKDOWN_TEXT = """
# Abstract

This study investigates **machine learning** for healthcare.
Results show *significant* improvement.

## Introduction

Previous studies [Jones, 2021] have shown that AI can diagnose accurately.

## Methodology

We conducted a survey with n=150 participants.
"""


# ══════════════════════════════════════════════════════════════════════════════
# 1. Models
# ══════════════════════════════════════════════════════════════════════════════

class TestModels:
    def test_review_depth_enum(self):
        from services.manuscript.models import ReviewDepth
        assert ReviewDepth("quick") == ReviewDepth.QUICK
        assert ReviewDepth("standard") == ReviewDepth.STANDARD
        assert ReviewDepth("deep") == ReviewDepth.DEEP

    def test_export_format_enum_all(self):
        from services.manuscript.models import ExportFormat
        assert len(list(ExportFormat)) == 8

    def test_section_type_enum_count(self):
        from services.manuscript.models import SectionType
        assert len(list(SectionType)) >= 30

    def test_recommendation_enum(self):
        from services.manuscript.models import Recommendation
        assert Recommendation("accept") == Recommendation.ACCEPT
        assert Recommendation("major_revision") == Recommendation.MAJOR_REVISION

    def test_issue_severity_enum(self):
        from services.manuscript.models import IssueSeverity
        assert IssueSeverity("critical") == IssueSeverity.CRITICAL

    def test_opportunity_score_to_dict(self):
        # Not present — testing QualityDimension instead
        from services.manuscript.models import QualityDimension
        d = QualityDimension("Test", score=75.0, weight=1.0, grade="B+")
        di = d.to_dict()
        assert di["score"] == 75.0
        assert di["grade"] == "B+"

    def test_review_dimensions_weighted_score(self):
        from services.manuscript.models import ReviewDimensions, QualityDimension
        dims = ReviewDimensions()
        for attr in ["scientific_rigor", "originality", "methodological_soundness",
                     "clarity", "literature_coverage", "contribution",
                     "statistical_validity", "ethical_compliance"]:
            getattr(dims, attr).score = 80.0
        score = dims.weighted_score()
        assert 79.0 <= score <= 81.0

    def test_review_dimensions_to_dict(self):
        from services.manuscript.models import ReviewDimensions
        d = ReviewDimensions()
        dd = d.to_dict()
        assert "scientific_rigor" in dd
        assert "originality" in dd
        assert "score" in dd["scientific_rigor"]

    def test_publication_readiness_to_dict(self):
        from services.manuscript.models import PublicationReadiness
        pr = PublicationReadiness(overall_score=72.0, acceptance_probability=0.35)
        d = pr.to_dict()
        assert d["overall_score"] == 72.0
        assert d["acceptance_probability"] == 0.35

    def test_journal_match_to_dict(self):
        from services.manuscript.models import JournalMatch
        j = JournalMatch(name="Nature", publisher="Springer", quartile="Q1")
        d = j.to_dict()
        assert d["name"] == "Nature"
        assert d["quartile"] == "Q1"

    def test_manuscript_result_to_summary(self):
        from services.manuscript.models import ManuscriptIntelligenceResult
        r = ManuscriptIntelligenceResult(title="Test Paper", overall_score=75.0, word_count=4000)
        s = r.to_summary()
        assert s["title"] == "Test Paper"
        assert s["overall_score"] == 75.0
        assert "detected_sections" not in s  # heavy field excluded

    def test_manuscript_result_to_dict_complete(self):
        from services.manuscript.models import ManuscriptIntelligenceResult
        r = ManuscriptIntelligenceResult(title="Test", overall_score=70.0)
        d = r.to_dict()
        required = [
            "result_id", "title", "overall_score", "recommendation",
            "review_dimensions", "section_scores", "critical_issues",
            "journal_matches", "revision_roadmap", "visualizations",
        ]
        for key in required:
            assert key in d, f"Missing key: {key}"

    def test_score_to_grade(self):
        from services.manuscript.models import _score_to_grade
        assert _score_to_grade(95) == "A+"
        assert _score_to_grade(85) == "A"
        assert _score_to_grade(72) == "B"
        assert _score_to_grade(55) == "C"
        assert _score_to_grade(30) == "F"

    def test_writing_metrics_to_dict(self):
        from services.manuscript.models import WritingMetrics
        m = WritingMetrics(word_count=4000, avg_sentence_length=20.0)
        d = m.to_dict()
        assert d["word_count"] == 4000
        assert d["avg_sentence_length"] == 20.0

    def test_statistical_metrics_to_dict(self):
        from services.manuscript.models import StatisticalMetrics
        m = StatisticalMetrics(has_p_values=True, p_value_count=5)
        d = m.to_dict()
        assert d["has_p_values"] is True
        assert d["p_value_count"] == 5


# ══════════════════════════════════════════════════════════════════════════════
# 2. Document Parser
# ══════════════════════════════════════════════════════════════════════════════

class TestDocParser:
    def test_parse_txt(self):
        from services.manuscript.doc_parser import parse_txt
        doc = parse_txt(_MINIMAL_TEXT)
        assert doc.word_count > 100
        assert doc.title != ""

    def test_parse_latex(self):
        from services.manuscript.doc_parser import parse_latex
        doc = parse_latex(_LATEX_TEXT)
        assert "machine learning" in doc.full_text.lower()
        assert r"\textit" not in doc.full_text  # LaTeX commands stripped

    def test_parse_markdown(self):
        from services.manuscript.doc_parser import parse_markdown
        doc = parse_markdown(_MARKDOWN_TEXT)
        assert "machine learning" in doc.full_text.lower()
        assert "**" not in doc.full_text  # bold stripped

    def test_detect_format_by_mime(self):
        from services.manuscript.doc_parser import detect_format
        from services.manuscript.models import InputFormat
        assert detect_format("file.pdf", "application/pdf") == InputFormat.PDF
        assert detect_format("file.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document") == InputFormat.DOCX
        # text/plain → TXT by mime; extension takes priority for .md when mime is text/plain
        assert detect_format("file.txt", "text/plain") == InputFormat.TXT
        assert detect_format("file.md", "text/markdown") == InputFormat.MARKDOWN

    def test_detect_format_by_extension(self):
        from services.manuscript.doc_parser import detect_format
        from services.manuscript.models import InputFormat
        assert detect_format("paper.tex", "") == InputFormat.LATEX
        assert detect_format("paper.md", "") == InputFormat.MARKDOWN
        assert detect_format("paper.txt", "") == InputFormat.TXT

    def test_reference_count_extracted(self):
        from services.manuscript.doc_parser import parse_txt
        doc = parse_txt(_MINIMAL_TEXT)
        assert doc.reference_count >= 3

    def test_keyword_extraction(self):
        from services.manuscript.doc_parser import parse_txt
        text = "Keywords: machine learning; healthcare; diagnosis; CNN; deep learning"
        doc = parse_txt(text + "\n\nThis study examines ML.")
        assert len(doc.keywords) >= 3

    def test_abstract_extraction(self):
        from services.manuscript.doc_parser import parse_txt
        # The regex requires "abstract" then a blank line then content
        text = (
            "Abstract\n\n"
            "This study investigates machine learning for diagnosis. "
            "We found that CNNs outperform traditional methods significantly. "
            "The results are promising for clinical deployment in resource-limited settings. "
            "This abstract content is long enough to exceed the 100-character minimum.\n\n"
            "Introduction\nSome intro text here."
        )
        doc = parse_txt(text)
        assert doc.abstract != ""

    def test_word_count_accurate(self):
        from services.manuscript.doc_parser import parse_txt
        text = " ".join(["word"] * 500)
        doc = parse_txt(text)
        assert doc.word_count == 500

    def test_text_truncated_at_max(self):
        from services.manuscript.doc_parser import parse_txt, MAX_CONTENT_CHARS
        long_text = "word " * 20000
        doc = parse_txt(long_text)
        assert len(doc.full_text) <= MAX_CONTENT_CHARS + 100


# ══════════════════════════════════════════════════════════════════════════════
# 3. Section Detector
# ══════════════════════════════════════════════════════════════════════════════

class TestSectionDetector:
    def test_detects_abstract(self):
        from services.manuscript.doc_parser import parse_txt
        from services.manuscript.section_detector import detect_sections
        from services.manuscript.models import SectionType
        doc = parse_txt(_MINIMAL_TEXT)
        sections = detect_sections(doc)
        types = [s.section_type for s in sections]
        assert SectionType.ABSTRACT in types

    def test_detects_methodology(self):
        from services.manuscript.doc_parser import parse_txt
        from services.manuscript.section_detector import detect_sections
        from services.manuscript.models import SectionType
        doc = parse_txt(_MINIMAL_TEXT)
        sections = detect_sections(doc)
        types = [s.section_type for s in sections]
        assert SectionType.METHODOLOGY in types

    def test_detects_ethics_via_content_signal(self):
        from services.manuscript.doc_parser import parse_txt
        from services.manuscript.section_detector import detect_sections
        from services.manuscript.models import SectionType
        doc = parse_txt(_MINIMAL_TEXT)
        sections = detect_sections(doc)
        types = [s.section_type for s in sections]
        assert SectionType.ETHICS in types

    def test_detects_data_availability(self):
        from services.manuscript.doc_parser import parse_txt
        from services.manuscript.section_detector import detect_sections
        from services.manuscript.models import SectionType
        doc = parse_txt(_MINIMAL_TEXT)
        sections = detect_sections(doc)
        types = [s.section_type for s in sections]
        assert SectionType.DATA_AVAILABILITY in types

    def test_sections_have_word_counts(self):
        from services.manuscript.doc_parser import parse_txt
        from services.manuscript.section_detector import detect_sections
        doc = parse_txt(_MINIMAL_TEXT)
        sections = detect_sections(doc)
        for s in sections:
            assert s.word_count >= 0

    def test_sections_sorted_by_position(self):
        from services.manuscript.doc_parser import parse_txt
        from services.manuscript.section_detector import detect_sections
        doc = parse_txt(_MINIMAL_TEXT)
        sections = detect_sections(doc)
        positions = [s.start_char for s in sections]
        assert positions == sorted(positions)

    def test_empty_text_returns_empty(self):
        from services.manuscript.doc_parser import parse_txt
        from services.manuscript.section_detector import detect_sections
        doc = parse_txt("")
        sections = detect_sections(doc)
        assert sections == []

    def test_section_labels(self):
        from services.manuscript.section_detector import section_type_labels
        labels = section_type_labels()
        assert "abstract" in labels
        assert "methodology" in labels


# ══════════════════════════════════════════════════════════════════════════════
# 4. Scientific Reviewer
# ══════════════════════════════════════════════════════════════════════════════

class TestScientificReviewer:
    def _sections(self):
        from services.manuscript.doc_parser import parse_txt
        from services.manuscript.section_detector import detect_sections
        doc = parse_txt(_MINIMAL_TEXT)
        return detect_sections(doc)

    def test_returns_dimension_and_issues(self):
        from services.manuscript.scientific_reviewer import review_scientific_quality
        dim, issues = review_scientific_quality(_MINIMAL_TEXT, self._sections())
        assert dim.score >= 0
        assert isinstance(issues, list)

    def test_good_manuscript_scores_higher(self):
        from services.manuscript.scientific_reviewer import review_scientific_quality
        dim_good, _ = review_scientific_quality(_MINIMAL_TEXT, self._sections())
        dim_bad, _ = review_scientific_quality(_SHORT_TEXT, [])
        assert dim_good.score > dim_bad.score

    def test_missing_ethics_generates_issue(self):
        from services.manuscript.scientific_reviewer import review_scientific_quality
        from services.manuscript.models import IssueSeverity
        text = "Abstract\nWe study ML. No ethics here. No IRB mention at all."
        _, issues = review_scientific_quality(text, [])
        severities = [i.severity for i in issues]
        # Ethics missing generates either CRITICAL or MAJOR depending on context
        assert IssueSeverity.CRITICAL in severities or IssueSeverity.MAJOR in severities

    def test_missing_objectives_generates_major_issue(self):
        from services.manuscript.scientific_reviewer import review_scientific_quality
        from services.manuscript.models import IssueSeverity
        text = "Abstract\nThis paper presents results. Table 1 shows data."
        _, issues = review_scientific_quality(text, [])
        severities = [i.severity for i in issues]
        assert IssueSeverity.MAJOR in severities

    def test_complete_manuscript_has_fewer_issues(self):
        from services.manuscript.scientific_reviewer import review_scientific_quality
        _, issues_good = review_scientific_quality(_MINIMAL_TEXT, self._sections())
        _, issues_bad = review_scientific_quality(_SHORT_TEXT, [])
        assert len(issues_good) <= len(issues_bad)

    def test_dimension_has_grade(self):
        from services.manuscript.scientific_reviewer import review_scientific_quality
        dim, _ = review_scientific_quality(_MINIMAL_TEXT, self._sections())
        assert dim.grade in ("A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D", "F")

    def test_contribution_signals_detected(self):
        from services.manuscript.scientific_reviewer import review_scientific_quality
        text = _MINIMAL_TEXT + "\nThis novel study fills the gap in the literature by proposing an original contribution."
        dim, issues = review_scientific_quality(text, self._sections())
        issue_titles = [i.title for i in issues]
        assert not any("contribution" in t.lower() for t in issue_titles)


# ══════════════════════════════════════════════════════════════════════════════
# 5. Writing Reviewer
# ══════════════════════════════════════════════════════════════════════════════

class TestWritingReviewer:
    def test_returns_three_outputs(self):
        from services.manuscript.writing_reviewer import review_writing_quality
        metrics, dim, issues = review_writing_quality(_MINIMAL_TEXT)
        assert metrics.word_count > 0
        assert dim.score >= 0
        assert isinstance(issues, list)

    def test_empty_text_scores_zero(self):
        from services.manuscript.writing_reviewer import review_writing_quality
        metrics, dim, issues = review_writing_quality("")
        assert metrics.word_count == 0
        assert dim.score == 0.0

    def test_passive_voice_detected(self):
        from services.manuscript.writing_reviewer import review_writing_quality
        text = " ".join([
            "The data were analyzed by the team.",
            "The results were found to be significant.",
            "The samples were processed by the laboratory.",
            "The model was trained using GPU hardware.",
            "The experiment was conducted over three months.",
        ] * 10)
        metrics, _, _ = review_writing_quality(text)
        assert metrics.passive_voice_ratio > 0

    def test_academic_word_ratio_detected(self):
        from services.manuscript.writing_reviewer import review_writing_quality
        _, metrics_dim, _ = review_writing_quality(_MINIMAL_TEXT)
        # Academic words like 'investigate', 'evaluate', 'methodology' present
        assert metrics_dim.score > 0

    def test_long_sentences_penalised(self):
        from services.manuscript.writing_reviewer import review_writing_quality
        # Sentences well over 40 words each
        long_text = (
            "This study demonstrates that machine learning models trained on large-scale "
            "clinical datasets with diverse patient populations and extensive feature engineering "
            "can achieve superior diagnostic accuracy when compared to traditional rule-based systems "
            "in a controlled experimental setting with appropriate validation procedures. " * 30
        )
        _, dim, issues = review_writing_quality(long_text)
        issue_titles = [i.title.lower() for i in issues]
        assert any("sentence" in t for t in issue_titles)

    def test_writing_metrics_word_count(self):
        from services.manuscript.writing_reviewer import review_writing_quality
        text = " ".join(["word"] * 1000)
        metrics, _, _ = review_writing_quality(text)
        assert metrics.word_count == 1000

    def test_syllable_estimation(self):
        from services.manuscript.writing_reviewer import _estimate_syllables
        count = _estimate_syllables("machine learning healthcare")
        assert count >= 5  # ma-chine, learn-ing, health-care = 5-7 depending on algorithm


# ══════════════════════════════════════════════════════════════════════════════
# 6. Literature Reviewer
# ══════════════════════════════════════════════════════════════════════════════

class TestLiteratureReviewer:
    def test_returns_three_outputs(self):
        from services.manuscript.literature_reviewer import review_literature
        metrics, dim, issues = review_literature(_MINIMAL_TEXT, 5)
        assert metrics.reference_count >= 3
        assert dim.score >= 0
        assert isinstance(issues, list)

    def test_recent_ratio_computed(self):
        from services.manuscript.literature_reviewer import review_literature
        metrics, _, _ = review_literature(_MINIMAL_TEXT, 5)
        assert 0.0 <= metrics.recent_ratio <= 1.0

    def test_year_range_detected(self):
        from services.manuscript.literature_reviewer import review_literature
        metrics, _, _ = review_literature(_MINIMAL_TEXT, 5)
        # Year range should include some year from the reference list (2018-2022)
        assert metrics.year_range != "" and metrics.year_range != "N/A"

    def test_few_references_generates_issue(self):
        from services.manuscript.literature_reviewer import review_literature
        from services.manuscript.models import IssueSeverity
        text = "Abstract. One reference (Jones, 2020). No other refs."
        _, _, issues = review_literature(text, reference_count=1)
        assert len(issues) >= 1

    def test_foundational_works_detected(self):
        from services.manuscript.literature_reviewer import review_literature
        text = _MINIMAL_TEXT + " This seminal study is foundational and has been widely cited."
        metrics, _, _ = review_literature(text, 5)
        assert metrics.foundational_works_mentioned is True

    def test_many_references_scores_higher(self):
        from services.manuscript.literature_reviewer import review_literature
        text_many = _MINIMAL_TEXT + " " + " ".join([f"Author{i} ({2020+i%5}). Paper {i}." for i in range(50)])
        _, dim_many, _ = review_literature(text_many, 50)
        _, dim_few, _ = review_literature(_MINIMAL_TEXT, 3)
        assert dim_many.score >= dim_few.score


# ══════════════════════════════════════════════════════════════════════════════
# 7. Methodology Reviewer
# ══════════════════════════════════════════════════════════════════════════════

class TestMethodReviewer:
    def test_returns_dimension_and_issues(self):
        from services.manuscript.method_reviewer import review_methodology
        dim, issues = review_methodology(_MINIMAL_TEXT)
        assert dim.score >= 0
        assert isinstance(issues, list)

    def test_rct_design_detected(self):
        from services.manuscript.method_reviewer import _detect_design
        assert "experimental" in _detect_design("we used a randomized controlled trial with control group")

    def test_survey_design_detected(self):
        from services.manuscript.method_reviewer import _detect_design
        assert "survey" in _detect_design("participants completed a survey questionnaire with likert scale")

    def test_systematic_review_detected(self):
        from services.manuscript.method_reviewer import _detect_design
        assert "systematic_review" in _detect_design("systematic review following PRISMA guidelines")

    def test_sample_size_extracted(self):
        from services.manuscript.method_reviewer import _detect_sample_size
        assert _detect_sample_size("n=120 participants were enrolled") == 120
        assert _detect_sample_size("N = 1,500 respondents") == 1500
        assert _detect_sample_size("no numbers here") == 0

    def test_small_sample_generates_major_issue(self):
        from services.manuscript.method_reviewer import review_methodology
        from services.manuscript.models import IssueSeverity
        text = "Methodology: n=15 participants. Survey design used."
        _, issues = review_methodology(text)
        major_issues = [i for i in issues if i.severity == IssueSeverity.MAJOR]
        assert len(major_issues) >= 1

    def test_missing_design_generates_major_issue(self):
        from services.manuscript.method_reviewer import review_methodology
        from services.manuscript.models import IssueSeverity
        text = "We collected some data and analysed it without specifying design."
        _, issues = review_methodology(text)
        major_issues = [i for i in issues if i.severity == IssueSeverity.MAJOR]
        assert len(major_issues) >= 1

    def test_complete_methods_section_scores_well(self):
        from services.manuscript.method_reviewer import review_methodology
        dim, _ = review_methodology(_MINIMAL_TEXT)
        assert dim.score >= 50


# ══════════════════════════════════════════════════════════════════════════════
# 8. Statistical Reviewer
# ══════════════════════════════════════════════════════════════════════════════

class TestStatisticalReviewer:
    def test_returns_three_outputs(self):
        from services.manuscript.statistical_reviewer import review_statistical_quality
        metrics, dim, issues = review_statistical_quality(_MINIMAL_TEXT)
        assert isinstance(metrics.has_p_values, bool)
        assert dim.score >= 0
        assert isinstance(issues, list)

    def test_p_values_detected(self):
        from services.manuscript.statistical_reviewer import review_statistical_quality
        metrics, _, _ = review_statistical_quality(_MINIMAL_TEXT)
        assert metrics.has_p_values is True
        assert metrics.p_value_count >= 1

    def test_effect_sizes_detected(self):
        from services.manuscript.statistical_reviewer import review_statistical_quality
        metrics, _, _ = review_statistical_quality(_MINIMAL_TEXT)
        assert metrics.has_effect_sizes is True

    def test_confidence_intervals_detected(self):
        from services.manuscript.statistical_reviewer import review_statistical_quality
        metrics, _, _ = review_statistical_quality(_MINIMAL_TEXT)
        assert metrics.has_confidence_intervals is True

    def test_missing_stats_generates_issues(self):
        from services.manuscript.statistical_reviewer import review_statistical_quality
        # Include a quantitative signal so the reviewer doesn't skip as qualitative
        text = ("We conducted a t-test analysis on the data. "
                "Results are presented in the table. Some numbers were found.")
        _, _, issues = review_statistical_quality(text)
        assert len(issues) >= 1

    def test_qualitative_manuscript_not_penalised(self):
        from services.manuscript.statistical_reviewer import review_statistical_quality
        text = ("This qualitative study uses grounded theory methodology. "
                "Participants were interviewed and transcripts were coded thematically. "
                "No statistical tests were required for this interpretive research approach.")
        _, dim, issues = review_statistical_quality(text)
        assert dim.score >= 60  # Not penalised for being qualitative

    def test_stat_tests_identified(self):
        from services.manuscript.statistical_reviewer import review_statistical_quality
        text = _MINIMAL_TEXT + " We used ANOVA and logistic regression for analysis."
        metrics, _, _ = review_statistical_quality(text)
        assert len(metrics.statistical_tests_used) >= 1


# ══════════════════════════════════════════════════════════════════════════════
# 9. Journal Matcher
# ══════════════════════════════════════════════════════════════════════════════

class TestJournalMatcher:
    def test_infer_discipline_medicine(self):
        from services.manuscript.journal_matcher import infer_discipline
        text = "patient diagnosis treatment disease clinical hospital"
        assert infer_discipline(text) == "medicine"

    def test_infer_discipline_ai(self):
        from services.manuscript.journal_matcher import infer_discipline
        text = "neural network machine learning deep learning transformer classification"
        assert infer_discipline(text) == "AI"

    def test_ai_discipline_override(self):
        from services.manuscript.journal_matcher import infer_discipline
        assert infer_discipline("anything", ai_discipline="psychology") == "psychology"

    def test_recommend_journals_returns_list(self):
        from services.manuscript.journal_matcher import recommend_journals
        results = recommend_journals(_MINIMAL_TEXT, "medicine", 72.0)
        assert len(results) >= 1

    def test_journals_are_journal_match_objects(self):
        from services.manuscript.journal_matcher import recommend_journals
        from services.manuscript.models import JournalMatch
        results = recommend_journals(_MINIMAL_TEXT, "AI", 75.0)
        for j in results:
            assert isinstance(j, JournalMatch)

    def test_ai_journals_merged(self):
        from services.manuscript.journal_matcher import recommend_journals
        ai_journals = [{"name": "Test Journal XYZ", "quartile": "Q1",
                        "publisher": "Test Pub", "scope_match": 0.9,
                        "acceptance_probability": 0.15, "submission_notes": "Note",
                        "open_access": True}]
        results = recommend_journals(_MINIMAL_TEXT, "AI", 80.0, ai_journals)
        names = [j.name for j in results]
        assert "Test Journal XYZ" in names

    def test_journal_quartile_valid(self):
        from services.manuscript.journal_matcher import recommend_journals
        results = recommend_journals(_MINIMAL_TEXT, "medicine", 70.0)
        for j in results:
            assert j.quartile in ("Q1", "Q2", "Q3", "Q4")

    def test_max_six_journals_returned(self):
        from services.manuscript.journal_matcher import recommend_journals
        results = recommend_journals(_MINIMAL_TEXT, "general", 75.0)
        assert len(results) <= 6


# ══════════════════════════════════════════════════════════════════════════════
# 10. Revision Planner
# ══════════════════════════════════════════════════════════════════════════════

class TestRevisionPlanner:
    def _make_issue(self, severity, section="Methods", title="Issue"):
        from services.manuscript.models import ReviewIssue, IssueSeverity
        return ReviewIssue(
            severity=IssueSeverity(severity),
            section=section,
            title=title,
            description="Description of issue.",
            recommendation="Fix it.",
        )

    def test_returns_list_of_phases(self):
        from services.manuscript.revision_planner import build_revision_roadmap
        phases = build_revision_roadmap([], [], [], [], 75.0)
        assert isinstance(phases, list)

    def test_critical_issues_create_phase_1(self):
        from services.manuscript.revision_planner import build_revision_roadmap
        criticals = [self._make_issue("critical") for _ in range(2)]
        phases = build_revision_roadmap(criticals, [], [], [], 60.0)
        assert phases[0]["title"] == "Critical Revisions"

    def test_major_issues_create_phase(self):
        from services.manuscript.revision_planner import build_revision_roadmap
        majors = [self._make_issue("major") for _ in range(3)]
        phases = build_revision_roadmap([], majors, [], [], 65.0)
        assert any(p["title"] == "Major Revisions" for p in phases)

    def test_phases_have_required_fields(self):
        from services.manuscript.revision_planner import build_revision_roadmap
        majors = [self._make_issue("major")]
        phases = build_revision_roadmap([], majors, [], [], 65.0)
        for p in phases:
            assert "phase" in p
            assert "title" in p
            assert "estimated_effort" in p
            assert "actions" in p

    def test_no_issues_returns_minimal_roadmap(self):
        from services.manuscript.revision_planner import build_revision_roadmap
        phases = build_revision_roadmap([], [], [], [], 85.0)
        assert isinstance(phases, list)

    def test_lit_issues_grouped_correctly(self):
        from services.manuscript.revision_planner import build_revision_roadmap
        lit_issue = self._make_issue("minor", section="Literature Review", title="Missing refs")
        phases = build_revision_roadmap([], [], [lit_issue], [], 70.0)
        phase_titles = [p["title"] for p in phases]
        assert any("Literature" in t for t in phase_titles)


# ══════════════════════════════════════════════════════════════════════════════
# 11. Visualization Builder
# ══════════════════════════════════════════════════════════════════════════════

class TestVizBuilder:
    def _make_dims(self):
        from services.manuscript.models import ReviewDimensions, QualityDimension
        dims = ReviewDimensions()
        for attr in ["scientific_rigor", "originality", "methodological_soundness",
                     "clarity", "literature_coverage", "contribution",
                     "statistical_validity", "ethical_compliance"]:
            getattr(dims, attr).score = 72.0
            getattr(dims, attr).grade = "B"
        return dims

    def test_quality_radar(self):
        from services.manuscript.viz_builder import build_quality_radar
        result = build_quality_radar(self._make_dims())
        assert result["type"] == "quality_radar"
        assert len(result["axes"]) == 8

    def test_section_heatmap(self):
        from services.manuscript.viz_builder import build_section_heatmap
        from services.manuscript.models import SectionScore, SectionType
        sections = [SectionScore(SectionType.ABSTRACT, "Abstract", score=80.0, grade="A-", detected=True)]
        result = build_section_heatmap(sections)
        assert result["type"] == "section_heatmap"
        assert len(result["cells"]) == 1

    def test_publication_readiness_gauge(self):
        from services.manuscript.viz_builder import build_publication_readiness_gauge
        from services.manuscript.models import PublicationReadiness
        pr = PublicationReadiness(overall_score=72.0, acceptance_probability=0.30)
        result = build_publication_readiness_gauge(pr)
        assert result["type"] == "publication_readiness_gauge"
        assert "band" in result
        assert "probabilities" in result

    def test_issue_severity_breakdown(self):
        from services.manuscript.viz_builder import build_issue_severity_breakdown
        from services.manuscript.models import ReviewIssue, IssueSeverity
        issues = [ReviewIssue(IssueSeverity.MAJOR, "Methods", "Issue", "Desc", "Fix")]
        result = build_issue_severity_breakdown([], issues, [], [])
        assert result["type"] == "issue_severity_breakdown"
        assert result["summary"]["major"] == 1

    def test_revision_timeline(self):
        from services.manuscript.viz_builder import build_revision_timeline
        roadmap = [{"phase": 1, "title": "Revisions", "priority": "high",
                    "estimated_effort": "1–2 weeks", "section_focus": ["Methods"],
                    "actions": ["Fix stats"]}]
        result = build_revision_timeline(roadmap)
        assert result["type"] == "revision_timeline"
        assert len(result["phases"]) == 1

    def test_completeness_checklist(self):
        from services.manuscript.viz_builder import build_completeness_checklist
        from services.manuscript.models import SectionScore, SectionType
        detected = [SectionType.ABSTRACT.value, SectionType.INTRODUCTION.value]
        sections = []
        result = build_completeness_checklist(detected, sections)
        assert result["type"] == "completeness_checklist"
        assert "completeness_score" in result

    def test_writing_metrics_chart(self):
        from services.manuscript.viz_builder import build_writing_metrics_chart
        from services.manuscript.models import WritingMetrics
        m = WritingMetrics(word_count=4000, avg_sentence_length=20.0, passive_voice_ratio=0.15)
        result = build_writing_metrics_chart(m)
        assert result["type"] == "writing_metrics_chart"
        assert len(result["bars"]) == 6

    def test_journal_match_scatter(self):
        from services.manuscript.viz_builder import build_journal_match_scatter
        from services.manuscript.models import JournalMatch
        journals = [JournalMatch("Nature", quartile="Q1", scope_match=0.8, acceptance_probability=0.05)]
        result = build_journal_match_scatter(journals)
        assert result["type"] == "journal_match_scatter"
        assert len(result["points"]) == 1

    def test_build_all_visualizations(self):
        from services.manuscript.viz_builder import build_all_visualizations
        from services.manuscript.models import PublicationReadiness, WritingMetrics
        result = build_all_visualizations(
            dims=self._make_dims(),
            section_scores=[],
            pr=PublicationReadiness(overall_score=72.0),
            critical=[], major=[], minor=[], suggestions=[],
            roadmap=[],
            detected_types=[],
            writing_metrics=WritingMetrics(word_count=4000),
            journal_matches=[],
        )
        expected = [
            "quality_radar", "section_heatmap", "publication_readiness_gauge",
            "issue_severity_breakdown", "revision_timeline", "completeness_checklist",
            "writing_metrics_chart", "journal_match_scatter",
        ]
        for key in expected:
            assert key in result, f"Missing viz: {key}"


# ══════════════════════════════════════════════════════════════════════════════
# 12. Export Engine
# ══════════════════════════════════════════════════════════════════════════════

class TestExportEngine:
    def _make_result(self):
        from services.manuscript.models import (
            ManuscriptIntelligenceResult, ReviewDimensions, QualityDimension,
            PublicationReadiness, JournalMatch, ReviewIssue, IssueSeverity,
            WritingMetrics, LiteratureMetrics, StatisticalMetrics, Recommendation,
        )
        r = ManuscriptIntelligenceResult(
            title="Machine Learning for Cardiac Diagnosis",
            filename="paper.pdf",
            overall_score=72.0,
            recommendation=Recommendation.MAJOR_REVISION,
            executive_summary="This study demonstrates ML potential for cardiac diagnosis.",
            peer_review_text="A thorough review reveals solid methodology but limited literature.",
            editorial_assessment="The manuscript shows promise but requires substantial revision.",
            inferred_discipline="medicine",
        )
        r.review_dimensions.scientific_rigor.score = 72.0
        r.review_dimensions.scientific_rigor.grade = "B"
        r.review_dimensions.scientific_rigor.rationale = "Good scientific rigour overall."
        r.journal_matches = [
            JournalMatch("JAMA", "AMA", "Q1", 0.8, 0.10, 157.3, "Focus on clinical evidence.")
        ]
        r.major_issues = [
            ReviewIssue(IssueSeverity.MAJOR, "Methods", "Small sample", "n=30 is too small.", "Increase sample.")
        ]
        r.revision_roadmap = [
            {"phase": 1, "title": "Major Revisions", "priority": "high",
             "estimated_effort": "2–4 weeks", "section_focus": ["Methods"],
             "actions": ["Increase sample size"], "issue_count": 1}
        ]
        r.writing_metrics = WritingMetrics(word_count=4000, avg_sentence_length=22.0)
        r.literature_metrics = LiteratureMetrics(reference_count=30, year_range="2018–2023")
        r.publication_readiness = PublicationReadiness(
            overall_score=72.0, acceptance_probability=0.30,
            desk_rejection_risk=0.10, estimated_revision_effort="2–4 weeks",
            strengths=["Good methodology"], barriers=["Small sample size"]
        )
        return r

    def test_export_peer_review(self):
        from services.manuscript.export_engine import export_result
        from services.manuscript.models import ExportFormat
        content, filename, ct = export_result(self._make_result(), ExportFormat.PEER_REVIEW)
        assert "Peer Review Report" in content
        assert filename.endswith(".md")
        assert "markdown" in ct

    def test_export_editorial_report(self):
        from services.manuscript.export_engine import export_result
        from services.manuscript.models import ExportFormat
        content, filename, ct = export_result(self._make_result(), ExportFormat.EDITORIAL_REPORT)
        assert "Editorial" in content
        assert "JAMA" in content

    def test_export_supervisor_report(self):
        from services.manuscript.export_engine import export_result
        from services.manuscript.models import ExportFormat
        content, filename, ct = export_result(self._make_result(), ExportFormat.SUPERVISOR_REPORT)
        assert "Supervisor" in content or "supervisor" in content.lower()

    def test_export_revision_checklist(self):
        from services.manuscript.export_engine import export_result
        from services.manuscript.models import ExportFormat
        content, filename, ct = export_result(self._make_result(), ExportFormat.REVISION_CHECKLIST)
        assert "[ ]" in content or "checklist" in content.lower()
        assert "Small sample" in content

    def test_export_publication_readiness(self):
        from services.manuscript.export_engine import export_result
        from services.manuscript.models import ExportFormat
        content, filename, ct = export_result(self._make_result(), ExportFormat.PUBLICATION_READINESS)
        assert "Readiness" in content
        assert "30%" in content or "0.30" in content

    def test_export_markdown(self):
        from services.manuscript.export_engine import export_result
        from services.manuscript.models import ExportFormat
        content, filename, ct = export_result(self._make_result(), ExportFormat.MARKDOWN)
        assert filename.endswith(".md")
        assert "Machine Learning" in content

    def test_export_latex(self):
        from services.manuscript.export_engine import export_result
        from services.manuscript.models import ExportFormat
        content, filename, ct = export_result(self._make_result(), ExportFormat.LATEX)
        assert r"\documentclass" in content
        assert r"\end{document}" in content
        assert filename.endswith(".tex")

    def test_export_text(self):
        from services.manuscript.export_engine import export_result
        from services.manuscript.models import ExportFormat
        content, filename, ct = export_result(self._make_result(), ExportFormat.TEXT)
        assert "MANUSCRIPT REVIEW REPORT" in content
        assert filename.endswith(".txt")

    def test_latex_escape(self):
        from services.manuscript.export_engine import _latex_escape
        assert r"\%" in _latex_escape("100% accuracy")
        assert r"\&" in _latex_escape("biology & chemistry")
        assert r"\_" in _latex_escape("my_variable")


# ══════════════════════════════════════════════════════════════════════════════
# 13. Telemetry
# ══════════════════════════════════════════════════════════════════════════════

class TestTelemetry:
    def _fresh(self):
        from services.manuscript.telemetry import ManuscriptTelemetry
        return ManuscriptTelemetry()

    def test_record_review(self):
        t = self._fresh()
        t.record_review("standard", 75.0, "major_revision", 5000.0)
        stats = t.get_stats()
        assert stats["total_reviews"] == 1
        assert stats["avg_overall_score"] == 75.0

    def test_record_export(self):
        t = self._fresh()
        t.record_export("peer_review")
        stats = t.get_stats()
        assert stats["total_exports"] == 1
        assert stats["export_format_distribution"]["peer_review"] == 1

    def test_record_error(self):
        t = self._fresh()
        t.record_error()
        assert t.get_stats()["review_errors"] == 1

    def test_reset(self):
        t = self._fresh()
        t.record_review("quick", 60.0, "reject", 2000.0)
        t.reset()
        assert t.get_stats()["total_reviews"] == 0

    def test_singleton(self):
        from services.manuscript.telemetry import get_manuscript_telemetry
        t1 = get_manuscript_telemetry()
        t2 = get_manuscript_telemetry()
        assert t1 is t2

    def test_latency_percentiles(self):
        t = self._fresh()
        for i in range(10):
            t.record_review("standard", 70.0, "major_revision", float(i * 1000))
        stats = t.get_stats()
        assert stats["review_p50_ms"] > 0
        assert stats["review_p95_ms"] >= stats["review_p50_ms"]

    def test_recommendation_distribution_tracked(self):
        t = self._fresh()
        t.record_review("quick", 60.0, "reject", 1000.0)
        t.record_review("quick", 80.0, "minor_revision", 1000.0)
        stats = t.get_stats()
        assert stats["recommendation_distribution"]["reject"] == 1
        assert stats["recommendation_distribution"]["minor_revision"] == 1


# ══════════════════════════════════════════════════════════════════════════════
# 14. Engine internals
# ══════════════════════════════════════════════════════════════════════════════

class TestEngineInternals:
    def test_merge_dimensions_ai_takes_priority(self):
        from services.manuscript.engine import _merge_dimensions
        from services.manuscript.models import ReviewDimensions, QualityDimension
        rule = ReviewDimensions()
        rule.scientific_rigor.score = 60.0
        ai_dim = QualityDimension("Scientific Rigor", score=80.0, weight=1.5, grade="A-")
        result = _merge_dimensions(rule, {"scientific_rigor": ai_dim})
        assert result.scientific_rigor.score == 80.0

    def test_merge_dimensions_rule_fills_when_ai_zero(self):
        from services.manuscript.engine import _merge_dimensions
        from services.manuscript.models import ReviewDimensions, QualityDimension
        rule = ReviewDimensions()
        rule.statistical_validity.score = 72.0
        result = _merge_dimensions(rule, {})
        assert result.statistical_validity.score == 72.0

    def test_map_recommendation_from_string(self):
        from services.manuscript.engine import _map_recommendation
        from services.manuscript.models import Recommendation
        assert _map_recommendation("accept", 90.0, 0, 0) == Recommendation.ACCEPT
        assert _map_recommendation("reject", 30.0, 3, 1) == Recommendation.REJECT

    def test_map_recommendation_rule_fallback(self):
        from services.manuscript.engine import _map_recommendation
        from services.manuscript.models import Recommendation
        assert _map_recommendation("", 85.0, 0, 0) == Recommendation.MINOR_REVISION
        assert _map_recommendation("", 35.0, 3, 1) == Recommendation.REJECT

    def test_build_publication_readiness_scores_within_range(self):
        from services.manuscript.engine import _build_publication_readiness
        pr = _build_publication_readiness(72.0, 0, 2, {})
        assert 0.0 <= pr.acceptance_probability <= 1.0
        assert 0.0 <= pr.desk_rejection_risk <= 1.0

    def test_reset_engine_clears_singleton(self):
        from services.manuscript.engine import get_manuscript_engine, reset_manuscript_engine
        reset_manuscript_engine()
        engine = _run(get_manuscript_engine())
        assert engine is not None
        reset_manuscript_engine()
