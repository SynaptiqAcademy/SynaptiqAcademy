"""Phase VI Academic Intelligence Engine — comprehensive test suite.

Covers: domain model, ontology, weakness detection, knowledge graph,
memory, validation, quality engine, strategy, telemetry, and main engine.

Run with: python -m pytest tests/test_academic_intelligence.py -v
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest


def _run(coro):
    return asyncio.run(coro)


# ── Sample academic texts ──────────────────────────────────────────────────────

MANUSCRIPT_TEXT = """
Abstract: This study investigates the application of deep learning algorithms for
medical image diagnosis. We hypothesize that convolutional neural networks can achieve
diagnostic accuracy exceeding radiologist performance.

Introduction: Medical imaging diagnosis represents a critical challenge in healthcare.
The aim of this study is to develop and validate a deep learning model.
This study contributes a novel benchmark dataset and a new architecture.

Methodology: We conducted a randomized controlled study with n=150 participants.
Data was collected prospectively. The study was approved by the Institutional Review Board
(protocol #2024-1234). Participants provided informed consent.

Results: The model achieved 94.3% accuracy (p < 0.001, 95% CI [91.2%, 97.4%]).
Effect size: Cohen's d = 0.82. Power analysis confirmed adequate sample size (power=0.90).

Discussion: These results suggest deep learning can augment radiologist performance.
Furthermore, the model demonstrates generalizability across imaging modalities.

Limitations: This study is limited by its single-institution dataset.
Future research should validate these findings across multiple sites.

Conflict of Interest: The authors declare no conflict of interest.
Data Availability: Code available at https://github.com/example/repo
References: (Smith, 2020), (Jones, 2021), (Brown, 2022), (Davis, 2023), (Wilson, 2024)
"""

WEAK_TEXT = """
I studied some stuff about machine learning. It seems to work pretty well.
I used some data from the internet. Results were good.
In conclusion, machine learning is useful.
"""

SHORT_TEXT = "Hello world."

QUALITATIVE_TEXT = """
We conducted in-depth interviews with 20 participants using purposive sampling.
Thematic analysis revealed three main themes: trust, communication, and collaboration.
Data collection continued until theoretical saturation was reached.
Future research should explore these themes in different cultural contexts.
"""


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Domain Model (models.py)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAcademicModels:
    def test_academic_domain_values(self):
        from services.academic.models import AcademicDomain
        assert AcademicDomain.COMPUTER_SCIENCE.value == "computer_science"
        assert AcademicDomain.MEDICINE_HEALTH.value == "medicine_health"

    def test_weakness_type_exists(self):
        from services.academic.models import WeaknessType
        assert WeaknessType.MISSING_HYPOTHESIS
        assert WeaknessType.WEAK_NOVELTY
        assert WeaknessType.MISSING_CITATIONS
        assert WeaknessType.MISSING_LIMITATIONS

    def test_confidence_level_from_score(self):
        from services.academic.models import ConfidenceLevel
        assert ConfidenceLevel.from_score(0.20) == ConfidenceLevel.VERY_LOW
        assert ConfidenceLevel.from_score(0.50) == ConfidenceLevel.LOW
        assert ConfidenceLevel.from_score(0.65) == ConfidenceLevel.MEDIUM
        assert ConfidenceLevel.from_score(0.80) == ConfidenceLevel.HIGH
        assert ConfidenceLevel.from_score(0.95) == ConfidenceLevel.VERY_HIGH

    def test_academic_weakness_to_dict(self):
        from services.academic.models import AcademicWeakness, WeaknessType, WeaknessSeverity
        w = AcademicWeakness(
            type=WeaknessType.MISSING_HYPOTHESIS,
            severity=WeaknessSeverity.HIGH,
            description="No hypothesis found",
            suggestion="Add a hypothesis",
        )
        d = w.to_dict()
        assert d["type"] == "missing_hypothesis"
        assert d["severity"] == "high"

    def test_academic_context_critical_weaknesses(self):
        from services.academic.models import (AcademicContext, AcademicWeakness,
                                               WeaknessType, WeaknessSeverity, AcademicDomain)
        ctx = AcademicContext(feature="manuscript_review", user_id="u1")
        ctx.detected_weaknesses = [
            AcademicWeakness(WeaknessType.MISSING_HYPOTHESIS, WeaknessSeverity.HIGH, "", ""),
            AcademicWeakness(WeaknessType.MISSING_CITATIONS, WeaknessSeverity.CRITICAL, "", ""),
            AcademicWeakness(WeaknessType.MISSING_LIMITATIONS, WeaknessSeverity.LOW, "", ""),
        ]
        critical = ctx.get_critical_weaknesses()
        assert len(critical) == 2

    def test_quality_score_from_dimensions(self):
        from services.academic.models import QualityScore, QualityDimension
        dims = [
            QualityDimension("clarity", 0.80, 0.5),
            QualityDimension("structure", 0.60, 0.5),
        ]
        qs = QualityScore.from_dimensions(dims, threshold=0.70, feature="ai_chat")
        assert qs.overall_score == pytest.approx(0.70, abs=0.01)
        assert not qs.needs_improvement  # 0.70 == threshold

    def test_quality_score_needs_improvement(self):
        from services.academic.models import QualityScore, QualityDimension
        dims = [QualityDimension("clarity", 0.40, 1.0, issues=["Too short"])]
        qs = QualityScore.from_dimensions(dims, threshold=0.70)
        assert qs.needs_improvement
        assert "Too short" in qs.improvement_hints

    def test_quality_score_to_dict(self):
        from services.academic.models import QualityScore, QualityDimension
        dims = [QualityDimension("rigor", 0.80, 1.0)]
        qs = QualityScore.from_dimensions(dims)
        d = qs.to_dict()
        assert "overall_score" in d
        assert "dimensions" in d
        assert "needs_improvement" in d

    def test_strategy_recommendation_to_dict(self):
        from services.academic.models import StrategyRecommendation
        r = StrategyRecommendation(
            type="next_publication",
            title="Publish a paper",
            description="You should publish",
            priority=1,
            rationale="Impact",
        )
        d = r.to_dict()
        assert d["type"] == "next_publication"
        assert d["priority"] == 1

    def test_academic_user_profile_to_dict(self):
        from services.academic.models import AcademicUserProfile
        p = AcademicUserProfile(user_id="u1", primary_domain="computer_science")
        d = p.to_dict()
        assert d["user_id"] == "u1"
        assert d["primary_domain"] == "computer_science"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Ontology
# ═══════════════════════════════════════════════════════════════════════════════

class TestOntology:
    def test_academic_features_not_empty(self):
        from services.academic.ontology import ACADEMIC_FEATURES
        assert len(ACADEMIC_FEATURES) >= 20
        assert "manuscript_review" in ACADEMIC_FEATURES
        assert "literature_review" in ACADEMIC_FEATURES
        assert "ai_chat" in ACADEMIC_FEATURES

    def test_get_reasoning_framework_known(self):
        from services.academic.ontology import get_reasoning_framework
        f = get_reasoning_framework("manuscript_review")
        assert len(f) > 50
        assert "IMRAD" in f or "methodology" in f.lower()

    def test_get_reasoning_framework_unknown(self):
        from services.academic.ontology import get_reasoning_framework
        f = get_reasoning_framework("nonexistent_feature")
        assert len(f) > 0  # returns default

    def test_get_quality_threshold_known(self):
        from services.academic.ontology import get_quality_threshold
        assert get_quality_threshold("manuscript_review") == 0.78
        assert get_quality_threshold("statistical_review") == 0.80

    def test_get_quality_threshold_default(self):
        from services.academic.ontology import get_quality_threshold
        assert get_quality_threshold("unknown_feature_xyz") == 0.65

    def test_domain_keywords_populated(self):
        from services.academic.ontology import DOMAIN_KEYWORDS
        assert "computer_science" in DOMAIN_KEYWORDS
        assert "deep learning" in DOMAIN_KEYWORDS["computer_science"]

    def test_methodology_keywords_populated(self):
        from services.academic.ontology import METHODOLOGY_KEYWORDS
        assert "quantitative" in METHODOLOGY_KEYWORDS
        assert "survey" in METHODOLOGY_KEYWORDS["quantitative"]


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Weakness Detector
# ═══════════════════════════════════════════════════════════════════════════════

class TestWeaknessDetector:
    def setup_method(self):
        from services.academic.reasoning.detector import AcademicWeaknessDetector
        self.detector = AcademicWeaknessDetector()

    def test_detect_domain_cs(self):
        from services.academic.models import AcademicDomain
        domain, confidence = self.detector.detect_domain(
            "deep learning algorithm neural network classification dataset"
        )
        assert domain == AcademicDomain.COMPUTER_SCIENCE
        assert confidence > 0.3

    def test_detect_domain_medicine(self):
        from services.academic.models import AcademicDomain
        domain, confidence = self.detector.detect_domain(
            "randomized controlled trial patient treatment clinical diagnosis"
        )
        assert domain == AcademicDomain.MEDICINE_HEALTH

    def test_detect_domain_unknown(self):
        from services.academic.models import AcademicDomain
        domain, confidence = self.detector.detect_domain("xyz abc 123")
        assert domain == AcademicDomain.UNKNOWN
        assert confidence == 0.0

    def test_detect_methodology_quantitative(self):
        from services.academic.models import MethodologyType
        meth, _ = self.detector.detect_methodology(
            "survey questionnaire n=250 participants statistical analysis regression"
        )
        assert meth == MethodologyType.QUANTITATIVE

    def test_detect_methodology_qualitative(self):
        from services.academic.models import MethodologyType
        meth, _ = self.detector.detect_methodology(
            "in-depth interviews thematic analysis grounded theory saturation"
        )
        assert meth == MethodologyType.QUALITATIVE

    def test_detect_sections_all_present(self):
        sections = self.detector.detect_sections(MANUSCRIPT_TEXT)
        assert "abstract" in sections
        assert "methodology" in sections
        assert "results" in sections
        assert "limitations" in sections

    def test_count_citations_apa(self):
        text = "As shown by (Smith, 2020) and (Jones, 2021), this is true (Brown, 2022)."
        count = self.detector.count_citations(text)
        assert count >= 3

    def test_count_citations_numbered(self):
        text = "As shown [1][2], it is also confirmed [3] and [4]."
        count = self.detector.count_citations(text)
        assert count >= 4

    def test_count_citations_zero(self):
        count = self.detector.count_citations(WEAK_TEXT)
        assert count == 0

    def test_structure_flags_full_manuscript(self):
        flags = self.detector.build_structure_flags(MANUSCRIPT_TEXT)
        assert flags["has_abstract"]
        assert flags["has_hypothesis"]
        assert flags["has_methodology"]
        assert flags["has_results"]
        assert flags["has_limitations"]
        assert flags["has_ethics"]
        assert flags["has_conflicts_of_interest"]

    def test_detect_weaknesses_weak_text(self):
        from services.academic.models import AcademicDomain, MethodologyType
        weaknesses = self.detector.detect(
            WEAK_TEXT,
            feature="manuscript_review",
            domain=AcademicDomain.COMPUTER_SCIENCE,
            methodology=MethodologyType.QUANTITATIVE,
        )
        types = [w.type.value for w in weaknesses]
        assert "missing_hypothesis" in types
        assert "missing_citations" in types

    def test_detect_weaknesses_strong_text(self):
        from services.academic.models import AcademicDomain, MethodologyType
        weaknesses = self.detector.detect(
            MANUSCRIPT_TEXT,
            feature="manuscript_review",
            domain=AcademicDomain.COMPUTER_SCIENCE,
            methodology=MethodologyType.QUANTITATIVE,
        )
        types = [w.type.value for w in weaknesses]
        assert "missing_hypothesis" not in types
        assert "missing_citations" not in types
        assert "missing_limitations" not in types

    def test_detect_qualitative_skips_stats_check(self):
        from services.academic.models import AcademicDomain, MethodologyType
        weaknesses = self.detector.detect(
            QUALITATIVE_TEXT,
            feature="manuscript_review",
            domain=AcademicDomain.SOCIAL_SCIENCES,
            methodology=MethodologyType.QUALITATIVE,
        )
        types = [w.type.value for w in weaknesses]
        assert "missing_power_analysis" not in types
        assert "missing_effect_size" not in types

    def test_small_sample_size_flagged(self):
        from services.academic.models import AcademicDomain, MethodologyType
        text = "We collected data from n=8 participants using quantitative methods."
        weaknesses = self.detector.detect(
            text, feature="statistical_review",
            domain=AcademicDomain.SOCIAL_SCIENCES,
            methodology=MethodologyType.QUANTITATIVE,
        )
        types = [w.type.value for w in weaknesses]
        assert "small_sample_size" in types

    def test_missing_effect_size_flagged(self):
        from services.academic.models import AcademicDomain, MethodologyType
        text = "The results were significant (p < 0.001) across all conditions."
        weaknesses = self.detector.detect(
            text, feature="statistical_review",
            domain=AcademicDomain.MEDICINE_HEALTH,
            methodology=MethodologyType.QUANTITATIVE,
        )
        types = [w.type.value for w in weaknesses]
        assert "missing_effect_size" in types

    def test_missing_ethics_for_medical_manuscript(self):
        from services.academic.models import AcademicDomain, MethodologyType
        text = "We recruited 50 patients for this clinical study."
        weaknesses = self.detector.detect(
            text, feature="manuscript_review",
            domain=AcademicDomain.MEDICINE_HEALTH,
            methodology=MethodologyType.QUANTITATIVE,
        )
        types = [w.type.value for w in weaknesses]
        assert "missing_ethics_approval" in types


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Academic Validator
# ═══════════════════════════════════════════════════════════════════════════════

class TestAcademicValidator:
    def setup_method(self):
        from services.academic.validation.validator import AcademicValidator
        from services.academic.models import AcademicContext
        self.validator = AcademicValidator()
        self.ctx = AcademicContext(feature="manuscript_review", user_id="u1")

    def test_validates_good_response(self):
        result = self.validator.validate(MANUSCRIPT_TEXT, self.ctx)
        assert result.is_valid

    def test_rejects_too_short(self):
        result = self.validator.validate("Too short.", self.ctx)
        assert not result.is_valid
        assert any("short" in i.lower() for i in result.issues)

    def test_rejects_empty(self):
        result = self.validator.validate("", self.ctx)
        assert not result.is_valid

    def test_warns_on_absolute_claims(self):
        text = "This study proves definitively that AI always outperforms humans."
        result = self.validator.validate(text, self.ctx)
        assert len(result.warnings) > 0

    def test_valid_result_has_no_issues(self):
        result = self.validator.validate(MANUSCRIPT_TEXT, self.ctx)
        assert result.issues == []

    def test_validation_result_to_dict(self):
        result = self.validator.validate(MANUSCRIPT_TEXT, self.ctx)
        d = result.to_dict()
        assert "is_valid" in d
        assert "issues" in d


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Academic Quality Engine
# ═══════════════════════════════════════════════════════════════════════════════

class TestAcademicQualityEngine:
    def setup_method(self):
        from services.academic.validation.validator import AcademicQualityEngine
        self.engine = AcademicQualityEngine()

    def test_strong_text_scores_high(self):
        qs = self.engine.score(MANUSCRIPT_TEXT, "manuscript_review")
        assert qs.overall_score >= 0.60

    def test_weak_text_scores_low(self):
        qs = self.engine.score(WEAK_TEXT, "manuscript_review")
        assert qs.overall_score < 0.75

    def test_empty_returns_zero(self):
        qs = self.engine.score("", "ai_chat")
        assert qs.overall_score == 0.0

    def test_has_8_dimensions(self):
        qs = self.engine.score(MANUSCRIPT_TEXT, "manuscript_review")
        assert len(qs.dimensions) == 8

    def test_all_dimensions_in_range(self):
        qs = self.engine.score(MANUSCRIPT_TEXT, "ai_chat")
        for dim in qs.dimensions:
            assert 0.0 <= dim.score <= 1.0

    def test_needs_improvement_for_weak(self):
        # Very short weak text below any threshold
        qs = self.engine.score("This is brief.", "manuscript_review")
        assert qs.needs_improvement

    def test_citation_quality_scored_for_reviews(self):
        qs = self.engine.score(MANUSCRIPT_TEXT, "manuscript_review")
        cit_dim = next((d for d in qs.dimensions if d.name == "citation_quality"), None)
        assert cit_dim is not None
        assert cit_dim.score >= 0.70  # has 5 APA citations

    def test_citation_quality_neutral_for_ai_chat(self):
        qs = self.engine.score("Some chat response here.", "ai_chat")
        cit_dim = next((d for d in qs.dimensions if d.name == "citation_quality"), None)
        assert cit_dim is not None
        assert cit_dim.score >= 0.70  # neutral (0.75 for non-citation features)

    def test_structured_response_scores_higher(self):
        structured = "## Introduction\n\nContent here.\n\n## Methods\n\nDetails.\n\n## Results\n\nFindings."
        qs_struct = self.engine.score(structured, "manuscript_review")
        qs_plain = self.engine.score("Introduction: content. Methods: details. Results: findings.", "manuscript_review")
        struct_dim = next(d for d in qs_struct.dimensions if d.name == "structure")
        plain_dim = next(d for d in qs_plain.dimensions if d.name == "structure")
        assert struct_dim.score >= plain_dim.score


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Strategy Engine
# ═══════════════════════════════════════════════════════════════════════════════

class TestStrategyEngine:
    def setup_method(self):
        from services.academic.strategy.strategy_engine import AcademicStrategyEngine
        self.engine = AcademicStrategyEngine()

    def test_generates_for_new_user(self):
        from services.academic.models import AcademicUserProfile
        profile = AcademicUserProfile(user_id="u1")
        recs = self.engine.generate(profile)
        assert isinstance(recs, list)

    def test_generates_for_experienced_user(self):
        from services.academic.models import AcademicUserProfile
        profile = AcademicUserProfile(
            user_id="u2",
            interaction_count=10,
            primary_domain="computer_science",
            preferred_journals=["Nature", "Science"],
            known_weaknesses=["missing_hypothesis", "missing_effect_size"],
            avg_quality_score=0.82,
        )
        recs = self.engine.generate(profile)
        assert len(recs) >= 3

    def test_recommendation_types_are_valid(self):
        from services.academic.models import AcademicUserProfile
        profile = AcademicUserProfile(user_id="u3", interaction_count=5)
        recs = self.engine.generate(profile)
        valid_types = {
            "next_publication", "next_journal", "methodology_improvement",
            "missing_collaboration", "next_grant", "career_progression",
        }
        for r in recs:
            assert r.type in valid_types

    def test_recommendations_sorted_by_priority(self):
        from services.academic.models import AcademicUserProfile
        profile = AcademicUserProfile(user_id="u4", interaction_count=8,
                                       avg_quality_score=0.80,
                                       known_weaknesses=["missing_citations"])
        recs = self.engine.generate(profile)
        priorities = [r.priority for r in recs]
        assert priorities == sorted(priorities)

    def test_high_quality_user_gets_career_rec(self):
        from services.academic.models import AcademicUserProfile
        profile = AcademicUserProfile(user_id="u5", avg_quality_score=0.80)
        recs = self.engine.generate(profile)
        types = {r.type for r in recs}
        assert "career_progression" in types


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Academic Telemetry
# ═══════════════════════════════════════════════════════════════════════════════

class TestAcademicTelemetry:
    def setup_method(self):
        from services.academic.telemetry import AcademicIntelligenceTelemetry
        self.t = AcademicIntelligenceTelemetry()

    def test_record_enrichment(self):
        self.t.record_enrichment("manuscript_review", "computer_science", 3, 0.75)
        stats = self.t.get_stats()
        assert stats["total_requests"] == 1
        assert stats["enriched_requests"] == 1
        assert stats["total_weaknesses_detected"] == 3

    def test_record_weakness(self):
        self.t.record_weakness("missing_hypothesis")
        self.t.record_weakness("missing_hypothesis")
        self.t.record_weakness("missing_citations")
        stats = self.t.get_stats()
        assert stats["most_common_weaknesses"]["missing_hypothesis"] == 2

    def test_record_validation(self):
        self.t.record_validation(True)
        self.t.record_validation(True)
        self.t.record_validation(False)
        stats = self.t.get_stats()
        assert stats["validation_passes"] == 2
        assert stats["validation_failures"] == 1
        assert stats["validation_pass_rate_pct"] == pytest.approx(66.7, abs=0.1)

    def test_record_quality(self):
        self.t.record_quality(0.85, False)
        self.t.record_quality(0.55, True)
        stats = self.t.get_stats()
        assert stats["quality_checks"] == 2
        assert stats["avg_quality_score"] == pytest.approx(0.70, abs=0.01)
        assert stats["quality_improvement_rate_pct"] == 50.0

    def test_reset_clears_stats(self):
        self.t.record_enrichment("ai_chat", "education", 1, 0.6)
        self.t.reset()
        stats = self.t.get_stats()
        assert stats["total_requests"] == 0

    def test_top_features(self):
        for _ in range(3):
            self.t.record_enrichment("literature_review", "social_sciences", 0, 0.7)
        for _ in range(2):
            self.t.record_enrichment("ai_chat", "education", 0, 0.6)
        stats = self.t.get_stats()
        top = dict(stats["top_features"])
        assert top["literature_review"] == 3
        assert top["ai_chat"] == 2

    def test_singleton(self):
        from services.academic.telemetry import get_academic_telemetry
        t1 = get_academic_telemetry()
        t2 = get_academic_telemetry()
        assert t1 is t2


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Academic Memory
# ═══════════════════════════════════════════════════════════════════════════════

def _make_mock_db():
    mock_coll = MagicMock()
    mock_coll.find_one = AsyncMock(return_value=None)
    mock_coll.insert_one = AsyncMock(return_value=None)
    mock_coll.update_one = AsyncMock(return_value=None)
    mock_coll.delete_many = AsyncMock(return_value=MagicMock(deleted_count=5))
    mock_coll.count_documents = AsyncMock(return_value=0)
    find_mock = MagicMock()
    find_mock.sort.return_value.limit.return_value.to_list = AsyncMock(return_value=[])
    find_mock.limit.return_value.to_list = AsyncMock(return_value=[])
    mock_coll.find = MagicMock(return_value=find_mock)
    mock_coll.aggregate = MagicMock(return_value=MagicMock(
        to_list=AsyncMock(return_value=[])
    ))
    mock_db = MagicMock()
    mock_db.__getitem__ = MagicMock(return_value=mock_coll)
    return mock_db


class TestAcademicMemory:
    def test_record_interaction_no_error(self):
        from services.academic.memory.academic_memory import AcademicMemory
        db = _make_mock_db()
        memory = AcademicMemory(db)
        _run(memory.record_interaction(
            user_id="u1", feature="manuscript_review",
            domain="computer_science", quality_score=0.80
        ))

    def test_empty_user_id_skipped(self):
        from services.academic.memory.academic_memory import AcademicMemory
        db = _make_mock_db()
        memory = AcademicMemory(db)
        _run(memory.record_interaction(user_id="", feature="ai_chat"))
        # Should not raise

    def test_get_user_profile_returns_default(self):
        from services.academic.memory.academic_memory import AcademicMemory
        from services.academic.models import AcademicUserProfile
        db = _make_mock_db()
        memory = AcademicMemory(db)
        profile = _run(memory.get_user_profile("u1"))
        assert isinstance(profile, AcademicUserProfile)
        assert profile.user_id == "u1"
        assert profile.interaction_count == 0

    def test_get_recent_interactions_empty(self):
        from services.academic.memory.academic_memory import AcademicMemory
        db = _make_mock_db()
        memory = AcademicMemory(db)
        interactions = _run(memory.get_recent_interactions("u1"))
        assert interactions == []

    def test_clear_memory(self):
        from services.academic.memory.academic_memory import AcademicMemory
        db = _make_mock_db()
        memory = AcademicMemory(db)
        deleted = _run(memory.clear_memory("u1"))
        assert deleted == 5

    def test_get_memory_summary(self):
        from services.academic.memory.academic_memory import AcademicMemory
        db = _make_mock_db()
        memory = AcademicMemory(db)
        summary = _run(memory.get_memory_summary("u1"))
        assert "profile" in summary
        assert "recent_interactions" in summary

    def test_get_stats(self):
        from services.academic.memory.academic_memory import AcademicMemory
        db = _make_mock_db()
        memory = AcademicMemory(db)
        stats = _run(memory.get_stats())
        assert "total_interactions" in stats
        assert "total_users" in stats


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Knowledge Graph
# ═══════════════════════════════════════════════════════════════════════════════

class TestKnowledgeGraph:
    def test_upsert_entity(self):
        from services.academic.knowledge_graph.graph import AcademicKnowledgeGraph
        db = _make_mock_db()
        graph = AcademicKnowledgeGraph(db)
        _run(graph.upsert_entity("topic", "ml_in_health", {"name": "ML in Health"}))

    def test_invalid_entity_type_raises(self):
        from services.academic.knowledge_graph.graph import AcademicKnowledgeGraph
        db = _make_mock_db()
        graph = AcademicKnowledgeGraph(db)
        with pytest.raises(ValueError):
            _run(graph.upsert_entity("invalid_type", "x", {}))

    def test_get_entity_returns_none(self):
        from services.academic.knowledge_graph.graph import AcademicKnowledgeGraph
        db = _make_mock_db()
        graph = AcademicKnowledgeGraph(db)
        result = _run(graph.get_entity("topic", "nonexistent"))
        assert result is None

    def test_add_relation(self):
        from services.academic.knowledge_graph.graph import AcademicKnowledgeGraph
        db = _make_mock_db()
        graph = AcademicKnowledgeGraph(db)
        _run(graph.add_relation("researcher", "user1", "authored_by", "publication", "pub1"))

    def test_invalid_relation_type_raises(self):
        from services.academic.knowledge_graph.graph import AcademicKnowledgeGraph
        db = _make_mock_db()
        graph = AcademicKnowledgeGraph(db)
        with pytest.raises(ValueError):
            _run(graph.add_relation("researcher", "u1", "invalid_relation", "topic", "t1"))

    def test_get_related_topics_empty(self):
        from services.academic.knowledge_graph.graph import AcademicKnowledgeGraph
        db = _make_mock_db()
        graph = AcademicKnowledgeGraph(db)
        topics = _run(graph.get_related_topics("machine learning"))
        assert topics == []

    def test_get_stats(self):
        from services.academic.knowledge_graph.graph import AcademicKnowledgeGraph
        db = _make_mock_db()
        db_coll = MagicMock()
        db_coll.count_documents = AsyncMock(return_value=42)
        db_coll.aggregate = MagicMock(return_value=MagicMock(to_list=AsyncMock(return_value=[])))
        db = MagicMock()
        db.__getitem__ = MagicMock(return_value=db_coll)
        graph = AcademicKnowledgeGraph(db)
        stats = _run(graph.get_stats())
        assert "total_entities" in stats
        assert stats["total_entities"] == 42


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Academic Intelligence Engine (main orchestrator)
# ═══════════════════════════════════════════════════════════════════════════════

def _make_engine():
    from services.academic.engine import AcademicIntelligenceEngine
    return AcademicIntelligenceEngine(_make_mock_db())


class TestAcademicIntelligenceEngine:
    def test_analyze_manuscript(self):
        engine = _make_engine()
        analysis = _run(engine.analyze(MANUSCRIPT_TEXT, "manuscript_review", "u1"))
        assert analysis.context.feature == "manuscript_review"
        assert analysis.quality.overall_score > 0
        assert analysis.processing_time_ms >= 0

    def test_analyze_weak_text(self):
        engine = _make_engine()
        analysis = _run(engine.analyze(WEAK_TEXT, "manuscript_review"))
        assert len(analysis.context.detected_weaknesses) > 0

    def test_analyze_returns_domain(self):
        engine = _make_engine()
        analysis = _run(engine.analyze(MANUSCRIPT_TEXT, "manuscript_review"))
        assert analysis.context.domain.value in (
            "computer_science", "medicine_health", "unknown"
        )

    def test_analyze_to_dict(self):
        engine = _make_engine()
        analysis = _run(engine.analyze(WEAK_TEXT, "ai_chat"))
        d = analysis.to_dict()
        assert "domain" in d
        assert "quality" in d
        assert "validation" in d
        assert "confidence" in d

    def test_build_system_guidance_contains_framework(self):
        engine = _make_engine()
        context = _run(engine._build_context("manuscript_review", MANUSCRIPT_TEXT, "u1"))
        guidance = engine._build_system_guidance(context)
        assert "ACADEMIC INTELLIGENCE CONTEXT" in guidance
        assert "REASONING FRAMEWORK" in guidance

    def test_build_system_guidance_lists_weaknesses(self):
        engine = _make_engine()
        context = _run(engine._build_context("manuscript_review", WEAK_TEXT, "u1"))
        guidance = engine._build_system_guidance(context)
        assert "DETECTED ISSUES" in guidance

    def test_enrich_request_non_academic_unchanged(self):
        engine = _make_engine()

        class FakeRequest:
            feature = "grammar_correction"
            messages = [{"role": "user", "content": "Fix this text."}]
            system = "original"
            user_id = "u1"
            workspace_id = None

        req = FakeRequest()
        result = _run(engine.enrich_request(req))
        assert result.system == "original"

    def test_enrich_request_academic_adds_context(self):
        engine = _make_engine()

        class FakeRequest:
            feature = "manuscript_review"
            messages = [{"role": "user", "content": MANUSCRIPT_TEXT[:200]}]
            system = "You are a reviewer."
            user_id = "u1"
            workspace_id = None

        req = FakeRequest()
        result = _run(engine.enrich_request(req))
        assert "ACADEMIC INTELLIGENCE CONTEXT" in result.system

    def test_enrich_request_too_short_unchanged(self):
        engine = _make_engine()

        class FakeRequest:
            feature = "literature_review"
            messages = [{"role": "user", "content": "Hi"}]
            system = "original"
            user_id = "u1"
            workspace_id = None

        req = FakeRequest()
        result = _run(engine.enrich_request(req))
        assert result.system == "original"

    def test_post_process_returns_response(self):
        engine = _make_engine()

        class FakeRequest:
            feature = "manuscript_review"
            user_id = "u1"

        class FakeResponse:
            text = MANUSCRIPT_TEXT
            provider = "anthropic"
            model = "claude-sonnet-4-6"

        req = FakeRequest()
        resp = FakeResponse()
        result = _run(engine.post_process(req, resp))
        assert result is not None

    def test_post_process_adds_quality_metadata(self):
        engine = _make_engine()

        class FakeRequest:
            feature = "manuscript_review"
            user_id = "u1"

        class FakeResponse:
            text = MANUSCRIPT_TEXT

        req = FakeRequest()
        resp = FakeResponse()
        result = _run(engine.post_process(req, resp))
        assert hasattr(result, "__dict__")
        assert "academic_quality_score" in result.__dict__

    def test_get_strategy_returns_list(self):
        engine = _make_engine()
        strategy = _run(engine.get_strategy("u1"))
        assert isinstance(strategy, list)

    def test_telemetry_stats_structure(self):
        engine = _make_engine()
        stats = engine.get_telemetry_stats()
        assert "total_requests" in stats
        assert "most_common_weaknesses" in stats

    def test_compute_confidence_increases_with_quality(self):
        engine = _make_engine()
        from services.academic.models import AcademicContext, QualityScore, QualityDimension

        ctx = AcademicContext(feature="ai_chat", user_id="u1")
        ctx.domain_confidence = 0.8
        ctx.has_hypothesis = True
        ctx.has_methodology = True
        ctx.citation_count = 6
        qs_high = QualityScore.from_dimensions([QualityDimension("x", 0.90, 1.0)])
        qs_low = QualityScore.from_dimensions([QualityDimension("x", 0.30, 1.0)])

        conf_high = engine._compute_confidence(ctx, qs_high)
        conf_low = engine._compute_confidence(ctx, qs_low)
        assert conf_high > conf_low

    def test_reset_telemetry(self):
        engine = _make_engine()
        engine._telemetry.record_enrichment("x", "y", 0, 0.5)
        engine.reset_telemetry()
        assert engine.get_telemetry_stats()["total_requests"] == 0

    def test_singleton_reset(self):
        from services.academic.engine import reset_academic_engine
        reset_academic_engine()
        from services.academic.engine import _engine
        assert _engine is None
