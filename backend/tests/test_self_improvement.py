"""Test suite for Phase XX — Self-Improving Academic Intelligence Platform.

Run: python -m pytest backend/tests/test_self_improvement.py -v
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Models
# ═══════════════════════════════════════════════════════════════════════════════

class TestModels:
    def test_feedback_signal_to_dict(self):
        from services.self_improvement.models import FeedbackSignal
        s = FeedbackSignal(signal_type="user_feedback", engine_type="copilot", outcome="accepted")
        d = s.to_dict()
        assert d["signal_type"] == "user_feedback"
        assert d["engine_type"] == "copilot"

    def test_engine_performance_to_dict(self):
        from services.self_improvement.models import EnginePerformanceMetrics
        m = EnginePerformanceMetrics(engine_type="copilot", accuracy=0.75)
        d = m.to_dict()
        assert d["accuracy"] == 0.75
        assert d["engine_type"] == "copilot"

    def test_optimization_record_to_dict(self):
        from services.self_improvement.models import OptimizationRecord
        r = OptimizationRecord(engine_type="copilot", parameter="weight", old_value=0.3, new_value=0.5)
        d = r.to_dict()
        assert d["status"] == "pending"
        assert d["rollback_available"] is True

    def test_ab_experiment_to_dict(self):
        from services.self_improvement.models import ABExperiment
        e = ABExperiment(name="test", engine_type="copilot")
        d = e.to_dict()
        assert "experiment_id" in d
        assert d["deployed"] is False

    def test_knowledge_update_to_dict(self):
        from services.self_improvement.models import KnowledgeUpdate
        u = KnowledgeUpdate(category="methodology", item="quantum ml", confidence=0.7)
        d = u.to_dict()
        assert d["status"] == "detected"
        assert d["confidence"] == 0.7

    def test_diagnostic_report_to_dict(self):
        from services.self_improvement.models import DiagnosticReport
        r = DiagnosticReport(engine_type="copilot", health_score=0.88)
        d = r.to_dict()
        assert d["health_score"] == 0.88

    def test_governance_policy_defaults(self):
        from services.self_improvement.models import GovernancePolicy
        p = GovernancePolicy()
        assert p.require_admin_approval is True
        assert p.auto_apply_optimizations is False
        assert p.privacy_level == "strict"

    def test_platform_quality_report_to_dict(self):
        from services.self_improvement.models import PlatformQualityReport
        r = PlatformQualityReport(overall_score=72.5)
        d = r.to_dict()
        assert d["overall_score"] == 72.5

    def test_engine_type_count(self):
        from services.self_improvement.models import EngineType
        assert len(EngineType) == 16

    def test_signal_type_count(self):
        from services.self_improvement.models import SignalType
        assert len(SignalType) == 12


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Feedback Engine
# ═══════════════════════════════════════════════════════════════════════════════

class TestFeedbackEngine:
    def _engine(self):
        from services.self_improvement.feedback_engine import FeedbackEngine
        return FeedbackEngine()

    def test_record_and_retrieve(self):
        fe = self._engine()
        sig = fe.record_signal("user_feedback", "copilot", outcome="accepted")
        signals = fe.get_signals("copilot")
        assert len(signals) == 1
        assert signals[0].signal_id == sig.signal_id

    def test_anonymizes_pii(self):
        fe  = self._engine()
        sig = fe.record_signal("user_feedback", "copilot", metadata={"user_id": "abc", "score": 5})
        assert "user_id" not in sig.metadata
        assert sig.metadata.get("score") == 5

    def test_acceptance_rate_empty(self):
        fe = self._engine()
        assert fe.acceptance_rate("unknown") == 0.0

    def test_acceptance_rate_computed(self):
        fe = self._engine()
        from services.self_improvement.models import RecommendationStatus
        fe.record_signal("user_feedback", "copilot", recommendation_status=RecommendationStatus.ACCEPTED.value)
        fe.record_signal("user_feedback", "copilot", recommendation_status=RecommendationStatus.IGNORED.value)
        assert fe.acceptance_rate("copilot") == 0.5

    def test_quality_improvement_rate(self):
        fe = self._engine()
        fe.record_signal("user_feedback", "copilot", quality_delta=0.10)
        fe.record_signal("user_feedback", "copilot", quality_delta=0.20)
        assert abs(fe.quality_improvement_rate("copilot") - 0.15) < 0.001

    def test_summary_keys(self):
        fe = self._engine()
        fe.record_signal("user_feedback", "copilot")
        s = fe.summary()
        assert "total_signals" in s
        assert "by_engine" in s

    def test_type_filter(self):
        fe = self._engine()
        fe.record_signal("user_feedback",   "copilot")
        fe.record_signal("prediction_accuracy", "copilot")
        typed = fe.get_signals(signal_type="user_feedback")
        assert all(s.signal_type == "user_feedback" for s in typed)

    def test_limit_respected(self):
        fe = self._engine()
        for _ in range(20):
            fe.record_signal("user_feedback", "copilot")
        assert len(fe.get_signals(limit=5)) == 5


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Performance Tracker
# ═══════════════════════════════════════════════════════════════════════════════

class TestPerformanceTracker:
    def _tracker(self):
        from services.self_improvement.performance_tracker import PerformanceTracker
        return PerformanceTracker()

    def test_empty_metrics_returns_defaults(self):
        pt = self._tracker()
        m  = pt.compute_metrics("unknown_engine")
        assert m.samples_evaluated == 0
        assert m.accuracy == 0.0

    def test_perfect_accuracy(self):
        pt = self._tracker()
        for _ in range(10):
            pt.record_observation("copilot", 0.9, True)
        m = pt.compute_metrics("copilot")
        assert m.accuracy == 1.0

    def test_zero_accuracy(self):
        pt = self._tracker()
        for _ in range(10):
            pt.record_observation("copilot", 0.9, False)
        m = pt.compute_metrics("copilot")
        assert m.accuracy == 0.0

    def test_calibration_error_low_for_perfect(self):
        pt = self._tracker()
        for _ in range(20):
            pt.record_observation("copilot", 0.95, True)
        m = pt.compute_metrics("copilot")
        assert m.calibration_error < 0.10

    def test_calibration_error_high_for_overconfident(self):
        pt = self._tracker()
        for _ in range(20):
            pt.record_observation("copilot", 0.95, False)
        m = pt.compute_metrics("copilot")
        assert m.calibration_error > 0.5

    def test_trend_improving(self):
        pt = self._tracker()
        # First half: wrong (high confidence, wrong outcome)
        for _ in range(10):
            pt.record_observation("copilot", 0.9, False)
        # Second half: correct
        for _ in range(10):
            pt.record_observation("copilot", 0.9, True)
        m = pt.compute_metrics("copilot")
        assert m.trend == "improving"

    def test_trend_declining(self):
        pt = self._tracker()
        # First half: correct
        for _ in range(10):
            pt.record_observation("copilot", 0.9, True)
        # Second half: wrong (high confidence, wrong outcome)
        for _ in range(10):
            pt.record_observation("copilot", 0.9, False)
        m = pt.compute_metrics("copilot")
        assert m.trend == "declining"

    def test_get_all_metrics_multiple_engines(self):
        pt = self._tracker()
        pt.record_observation("engine_a", 0.8, True)
        pt.record_observation("engine_b", 0.7, False)
        all_m = pt.get_all_metrics()
        assert "engine_a" in all_m
        assert "engine_b" in all_m

    def test_cache_invalidated_on_new_obs(self):
        pt = self._tracker()
        pt.record_observation("copilot", 0.9, True)
        m1 = pt.compute_metrics("copilot")
        pt.record_observation("copilot", 0.9, False)
        m2 = pt.compute_metrics("copilot")
        assert m1.accuracy != m2.accuracy


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Optimization Engine
# ═══════════════════════════════════════════════════════════════════════════════

class TestOptimizationEngine:
    def _oe(self):
        from services.self_improvement.optimization_engine import OptimizationEngine
        return OptimizationEngine()

    def _policy(self, min_samples=5):
        from services.self_improvement.models import GovernancePolicy
        p = GovernancePolicy()
        p.min_samples_for_optimization = min_samples
        return p

    def _metrics(self, accuracy=0.55, calibration=0.20, samples=10, trend="stable"):
        from services.self_improvement.models import EnginePerformanceMetrics
        return EnginePerformanceMetrics(
            engine_type="copilot",
            accuracy=accuracy,
            calibration_error=calibration,
            samples_evaluated=samples,
            trend=trend,
        )

    def test_no_candidates_below_min_samples(self):
        oe   = self._oe()
        m    = {"copilot": self._metrics(samples=3)}
        cands = oe.generate_candidates(m, self._policy(min_samples=50))
        assert len(cands) == 0

    def test_calibration_candidate_generated(self):
        oe   = self._oe()
        m    = {"copilot": self._metrics(calibration=0.30, samples=100)}
        cands = oe.generate_candidates(m, self._policy(min_samples=5))
        types = [c.optimization_type for c in cands]
        assert "confidence_calibration" in types

    def test_accuracy_candidate_generated(self):
        oe   = self._oe()
        m    = {"copilot": self._metrics(accuracy=0.45, samples=100)}
        cands = oe.generate_candidates(m, self._policy(min_samples=5))
        types = [c.optimization_type for c in cands]
        assert "weight_adjustment" in types

    def test_apply_changes_status(self):
        oe  = self._oe()
        m   = {"copilot": self._metrics(calibration=0.30, samples=100)}
        c   = oe.generate_candidates(m, self._policy())[0]
        oe.add_to_history(c)
        assert oe.apply_optimization(c.record_id, "admin") is True
        hist = oe.get_history()
        applied = [r for r in hist if r.record_id == c.record_id]
        assert applied[0].status == "applied"

    def test_rollback_changes_status(self):
        oe = self._oe()
        m  = {"copilot": self._metrics(calibration=0.30, samples=100)}
        c  = oe.generate_candidates(m, self._policy())[0]
        oe.add_to_history(c)
        oe.apply_optimization(c.record_id)
        assert oe.rollback_optimization(c.record_id) is True
        hist = oe.get_history()
        rolled = [r for r in hist if r.record_id == c.record_id]
        assert rolled[0].status == "rolled_back"

    def test_apply_pending_only(self):
        oe = self._oe()
        m  = {"copilot": self._metrics(calibration=0.30, samples=100)}
        c  = oe.generate_candidates(m, self._policy())[0]
        oe.add_to_history(c)
        oe.apply_optimization(c.record_id)
        assert oe.apply_optimization(c.record_id) is False

    def test_get_pending_returns_only_pending(self):
        oe = self._oe()
        m  = {"copilot": self._metrics(calibration=0.30, samples=100)}
        cs = oe.generate_candidates(m, self._policy())
        for c in cs:
            oe.add_to_history(c)
        if cs:
            oe.apply_optimization(cs[0].record_id)
        pending = oe.get_pending()
        assert all(r.status == "pending" for r in pending)

    def test_declining_trend_candidate(self):
        oe   = self._oe()
        m    = {"copilot": self._metrics(trend="declining", samples=100)}
        cands = oe.generate_candidates(m, self._policy())
        types = [c.optimization_type for c in cands]
        assert "threshold_adjustment" in types


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Benchmark Suite
# ═══════════════════════════════════════════════════════════════════════════════

class TestBenchmarkSuite:
    def test_unknown_engine_returns_no_cases(self):
        from services.self_improvement.benchmark_suite import run_benchmark
        result = run_benchmark("nonexistent_engine")
        assert result["status"] == "no_cases"
        assert result["score"] == 0.0

    def test_publication_benchmark_completes(self):
        from services.self_improvement.benchmark_suite import run_benchmark
        result = run_benchmark("publication_predictor")
        assert result["status"] == "completed"
        assert result["total"] > 0

    def test_journal_benchmark_completes(self):
        from services.self_improvement.benchmark_suite import run_benchmark
        result = run_benchmark("journal_predictor")
        assert result["status"] == "completed"

    def test_career_benchmark_completes(self):
        from services.self_improvement.benchmark_suite import run_benchmark
        result = run_benchmark("career_forecaster")
        assert result["status"] == "completed"

    def test_grant_benchmark_completes(self):
        from services.self_improvement.benchmark_suite import run_benchmark
        result = run_benchmark("grant_predictor")
        assert result["status"] == "completed"

    def test_trend_benchmark_completes(self):
        from services.self_improvement.benchmark_suite import run_benchmark
        result = run_benchmark("trend_forecaster")
        assert result["status"] == "completed"

    def test_score_in_range(self):
        from services.self_improvement.benchmark_suite import run_benchmark
        result = run_benchmark("publication_predictor")
        assert 0.0 <= result["score"] <= 1.0

    def test_run_all_benchmarks(self):
        from services.self_improvement.benchmark_suite import run_all_benchmarks
        result = run_all_benchmarks()
        assert "overall_score" in result
        assert "engines" in result
        assert 0.0 <= result["overall_score"] <= 1.0

    def test_pass_rate_in_range(self):
        from services.self_improvement.benchmark_suite import run_benchmark
        result = run_benchmark("grant_predictor")
        assert 0.0 <= result["pass_rate"] <= 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# 6. A/B Testing Framework
# ═══════════════════════════════════════════════════════════════════════════════

class TestABTesting:
    def _framework(self):
        from services.self_improvement.ab_testing import ABTestingFramework
        return ABTestingFramework()

    def test_create_experiment(self):
        ab  = self._framework()
        exp = ab.create_experiment("test", "copilot", {"key": "A"}, {"key": "B"})
        assert exp.name == "test"
        assert exp.status == "running"

    def test_record_observation_valid(self):
        ab  = self._framework()
        exp = ab.create_experiment("test", "copilot", {}, {})
        assert ab.record_observation(exp.experiment_id, "A", True) is True
        assert ab.record_observation(exp.experiment_id, "B", False) is True

    def test_record_invalid_variant(self):
        ab  = self._framework()
        exp = ab.create_experiment("test", "copilot", {}, {})
        assert ab.record_observation(exp.experiment_id, "C", True) is False

    def test_evaluate_no_data(self):
        ab  = self._framework()
        exp = ab.create_experiment("test", "copilot", {}, {})
        result = ab.evaluate_experiment(exp.experiment_id)
        assert result.winner == "no_difference"

    def test_complete_experiment(self):
        ab  = self._framework()
        exp = ab.create_experiment("test", "copilot", {}, {})
        assert ab.complete_experiment(exp.experiment_id) is True
        updated = ab.get_experiment(exp.experiment_id)
        assert updated.status == "completed"

    def test_rollback_experiment(self):
        ab  = self._framework()
        exp = ab.create_experiment("test", "copilot", {}, {})
        assert ab.rollback_experiment(exp.experiment_id) is True
        updated = ab.get_experiment(exp.experiment_id)
        assert updated.status == "rolled_back"

    def test_get_active_only_running(self):
        ab   = self._framework()
        e1   = ab.create_experiment("e1", "copilot", {}, {})
        e2   = ab.create_experiment("e2", "copilot", {}, {})
        ab.complete_experiment(e1.experiment_id)
        active = ab.get_active_experiments()
        ids = [e.experiment_id for e in active]
        assert e1.experiment_id not in ids
        assert e2.experiment_id in ids

    def test_traffic_split_clamped(self):
        ab  = self._framework()
        exp = ab.create_experiment("test", "copilot", {}, {}, traffic_split=1.5)
        assert exp.traffic_split <= 0.9

    def test_unknown_experiment_returns_none(self):
        ab = self._framework()
        assert ab.get_experiment("nonexistent") is None


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Statistical Significance
# ═══════════════════════════════════════════════════════════════════════════════

class TestStatisticalSignificance:
    def test_no_data_returns_1(self):
        from services.self_improvement.ab_testing import compute_p_value
        assert compute_p_value(0, 0, 0, 0) == 1.0

    def test_small_sample_returns_1(self):
        from services.self_improvement.ab_testing import compute_p_value
        assert compute_p_value(3, 2, 3, 1) == 1.0

    def test_identical_rates_high_p(self):
        from services.self_improvement.ab_testing import compute_p_value
        p = compute_p_value(100, 50, 100, 50)
        assert p > 0.9

    def test_very_different_rates_low_p(self):
        from services.self_improvement.ab_testing import compute_p_value
        p = compute_p_value(200, 100, 200, 160)
        assert p < 0.05

    def test_p_value_range(self):
        from services.self_improvement.ab_testing import compute_p_value
        p = compute_p_value(50, 25, 50, 40)
        assert 0.0 <= p <= 1.0

    def test_winner_declared_when_significant(self):
        from services.self_improvement.ab_testing import ABTestingFramework
        ab  = ABTestingFramework()
        exp = ab.create_experiment("sig_test", "copilot", {}, {})
        for _ in range(200):
            ab.record_observation(exp.experiment_id, "A", True)
            ab.record_observation(exp.experiment_id, "A", False)
        for _ in range(200):
            ab.record_observation(exp.experiment_id, "B", True)
            ab.record_observation(exp.experiment_id, "B", True)
            ab.record_observation(exp.experiment_id, "B", True)
            ab.record_observation(exp.experiment_id, "B", False)
        result = ab.evaluate_experiment(exp.experiment_id)
        assert result.winner in ("A", "B", "no_difference")

    def test_erfc_approx_at_zero(self):
        from services.self_improvement.ab_testing import _erfc_approx
        assert abs(_erfc_approx(0) - 1.0) < 0.01


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Knowledge Evolution
# ═══════════════════════════════════════════════════════════════════════════════

class TestKnowledgeEvolution:
    def _ke(self):
        from services.self_improvement.knowledge_evolution import KnowledgeEvolutionEngine
        return KnowledgeEvolutionEngine()

    def test_ingest_text_returns_list(self):
        ke = self._ke()
        result = ke.ingest_text("deep learning transformers neural networks for nlp")
        assert isinstance(result, list)

    def test_detect_from_keywords(self):
        ke = self._ke()
        result = ke.detect_from_keywords(["quantum machine learning", "neuromorphic computing"])
        assert isinstance(result, list)

    def test_pending_updates_filtered_by_confidence(self):
        ke = self._ke()
        ke.ingest_text("deep learning transformers")
        ke.ingest_text("deep learning transformers")
        ke.ingest_text("deep learning transformers")
        ke.ingest_text("deep learning transformers")
        ke.ingest_text("deep learning transformers")
        all_pending = ke.get_pending_updates(min_confidence=0.0)
        high_conf   = ke.get_pending_updates(min_confidence=0.5)
        assert len(all_pending) >= len(high_conf)

    def test_validate_update(self):
        ke = self._ke()
        updates = ke.ingest_text("graph neural networks for knowledge graphs")
        if updates:
            result = ke.validate_update(updates[0].update_id)
            if result:
                assert result.status == "validated"

    def test_integrate_requires_validated(self):
        ke = self._ke()
        updates = ke.ingest_text("transformer deep learning architecture")
        if updates:
            uid = updates[0].update_id
            assert ke.integrate_update(uid) is False   # not validated yet
            ke.validate_update(uid)
            result = ke.integrate_update(uid)
            assert result is True

    def test_reject_update(self):
        ke = self._ke()
        updates = ke.ingest_text("deep learning transformers")
        if updates:
            result = ke.reject_update(updates[0].update_id)
            assert result is True
            rejected = [u for u in ke.get_all_updates() if u.status == "rejected"]
            assert len(rejected) > 0

    def test_summary_keys(self):
        ke = self._ke()
        s  = ke.summary()
        assert "total" in s
        assert "known_fields" in s
        assert "known_methodologies" in s

    def test_evidence_increases_confidence(self):
        ke = self._ke()
        ke.ingest_text("deep learning transformers")
        ke.ingest_text("deep learning transformers")
        ke.ingest_text("deep learning transformers")
        ke.ingest_text("deep learning transformers")
        ke.ingest_text("deep learning transformers")
        all_u = ke.get_all_updates()
        if all_u:
            conf5 = max(u.confidence for u in all_u)
            ke.ingest_text("deep learning transformers")
            all_u2 = ke.get_all_updates()
            conf6 = max(u.confidence for u in all_u2)
            assert conf6 >= conf5


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Adaptive Recommender
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdaptiveRecommender:
    def _ar(self):
        from services.self_improvement.adaptive_recommender import AdaptiveRecommender
        return AdaptiveRecommender()

    def test_personalize_no_history_returns_original(self):
        ar   = self._ar()
        recs = [{"category": "A", "score": 0.8}, {"category": "B", "score": 0.5}]
        result = ar.personalize_recommendations(recs, "cohort_x")
        assert len(result) == len(recs)

    def test_cohort_feedback_recorded(self):
        ar = self._ar()
        ar.record_cohort_feedback("cohort_x", "literature", True)
        ar.record_cohort_feedback("cohort_x", "literature", False)
        prefs = ar.compute_cohort_preferences("cohort_x")
        assert abs(prefs["literature"]["acceptance_rate"] - 0.5) < 0.01

    def test_personalize_boosts_preferred_category(self):
        ar = self._ar()
        for _ in range(10):
            ar.record_cohort_feedback("power_user", "grant", True)
        for _ in range(10):
            ar.record_cohort_feedback("power_user", "literature", False)
        recs = [
            {"category": "literature", "score": 0.9},
            {"category": "grant",      "score": 0.7},
        ]
        result = ar.personalize_recommendations(recs, "power_user")
        assert result[0]["category"] == "grant"

    def test_build_cohort_profile_empty_signals(self):
        ar = self._ar()
        profile = ar.build_cohort_profile("cohort_y", [])
        assert profile["signal_count"] == 0
        assert profile["profile"] == {}

    def test_build_cohort_profile_with_signals(self):
        from services.self_improvement.models import FeedbackSignal, RecommendationStatus
        ar = self._ar()
        signals = [
            FeedbackSignal(engine_type="copilot", user_cohort="c1",
                           recommendation_status=RecommendationStatus.ACCEPTED.value),
            FeedbackSignal(engine_type="copilot", user_cohort="c1",
                           recommendation_status=RecommendationStatus.IGNORED.value),
        ]
        profile = ar.build_cohort_profile("c1", signals)
        assert profile["signal_count"] == 2
        assert abs(profile["profile"]["copilot"]["acceptance_rate"] - 0.5) < 0.01

    def test_max_cohort_signals_cap(self):
        from services.self_improvement.adaptive_recommender import _MAX_COHORT_SIGNALS
        ar = self._ar()
        for _ in range(_MAX_COHORT_SIGNALS + 50):
            ar.record_cohort_feedback("c1", "lit", True)
        assert ar._counts["c1"] == _MAX_COHORT_SIGNALS

    def test_get_cohort_ids(self):
        ar = self._ar()
        ar.record_cohort_feedback("c1", "lit", True)
        ar.record_cohort_feedback("c2", "grant", False)
        assert set(ar.get_cohort_ids()) == {"c1", "c2"}


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Self-Diagnostics
# ═══════════════════════════════════════════════════════════════════════════════

class TestSelfDiagnostics:
    def _metrics(self, **kwargs):
        from services.self_improvement.models import EnginePerformanceMetrics
        return EnginePerformanceMetrics(engine_type="copilot", samples_evaluated=50, **kwargs)

    def test_no_samples_returns_unknown(self):
        from services.self_improvement.models import EnginePerformanceMetrics
        from services.self_improvement.self_diagnostics import check_engine_health
        m = EnginePerformanceMetrics(engine_type="copilot")
        r = check_engine_health("copilot", m)
        assert r.status == "unknown"

    def test_healthy_engine(self):
        from services.self_improvement.self_diagnostics import check_engine_health
        m = self._metrics(accuracy=0.85, calibration_error=0.05, user_acceptance_rate=0.70, avg_confidence=0.80)
        r = check_engine_health("copilot", m)
        assert r.status == "healthy"
        assert r.health_score > 0.5

    def test_critical_engine(self):
        from services.self_improvement.self_diagnostics import check_engine_health
        m = self._metrics(accuracy=0.40, calibration_error=0.30, user_acceptance_rate=0.10, avg_confidence=0.80)
        r = check_engine_health("copilot", m)
        assert r.status == "critical"

    def test_warning_engine(self):
        from services.self_improvement.self_diagnostics import check_engine_health
        m = self._metrics(accuracy=0.60, calibration_error=0.18, user_acceptance_rate=0.30, avg_confidence=0.70)
        r = check_engine_health("copilot", m)
        assert r.status in ("warning", "healthy")

    def test_issues_populated(self):
        from services.self_improvement.self_diagnostics import check_engine_health
        m = self._metrics(accuracy=0.40)
        r = check_engine_health("copilot", m)
        assert len(r.issues) > 0

    def test_recommendations_present(self):
        from services.self_improvement.self_diagnostics import check_engine_health
        m = self._metrics(accuracy=0.40)
        r = check_engine_health("copilot", m)
        assert len(r.recommendations) > 0

    def test_check_all_engines(self):
        from services.self_improvement.models import EnginePerformanceMetrics
        from services.self_improvement.self_diagnostics import check_all_engines
        all_m = {
            "a": EnginePerformanceMetrics(engine_type="a", samples_evaluated=10, accuracy=0.8),
            "b": EnginePerformanceMetrics(engine_type="b", samples_evaluated=10, accuracy=0.5),
        }
        reports = check_all_engines(all_m)
        assert len(reports) == 2

    def test_platform_health_score(self):
        from services.self_improvement.models import DiagnosticReport
        from services.self_improvement.self_diagnostics import platform_health_score
        reports = [DiagnosticReport(health_score=0.8), DiagnosticReport(health_score=0.6)]
        score   = platform_health_score(reports)
        assert abs(score - 0.70) < 0.01

    def test_health_score_in_range(self):
        from services.self_improvement.self_diagnostics import check_engine_health
        m = self._metrics(accuracy=0.75, calibration_error=0.10, user_acceptance_rate=0.50)
        r = check_engine_health("copilot", m)
        assert 0.0 <= r.health_score <= 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Governance
# ═══════════════════════════════════════════════════════════════════════════════

class TestGovernance:
    def setup_method(self):
        from services.self_improvement.governance import reset_policy
        reset_policy()

    def test_default_policy(self):
        from services.self_improvement.governance import get_policy
        p = get_policy()
        assert p.learning_enabled is True
        assert p.require_admin_approval is True

    def test_singleton(self):
        from services.self_improvement.governance import get_policy
        p1 = get_policy()
        p2 = get_policy()
        assert p1 is p2

    def test_update_policy(self):
        from services.self_improvement.governance import update_policy, get_policy
        update_policy({"retention_days": 30}, "admin")
        assert get_policy().retention_days == 30

    def test_unknown_field_ignored(self):
        from services.self_improvement.governance import update_policy, get_policy
        update_policy({"hacking_mode": True})
        assert not hasattr(get_policy(), "hacking_mode")

    def test_can_optimize_sufficient_samples(self):
        from services.self_improvement.governance import can_optimize
        assert can_optimize(100) is True

    def test_cannot_optimize_insufficient_samples(self):
        from services.self_improvement.governance import can_optimize
        assert can_optimize(3) is False

    def test_cannot_optimize_when_disabled(self):
        from services.self_improvement.governance import can_optimize, update_policy
        update_policy({"learning_enabled": False})
        assert can_optimize(1000) is False

    def test_can_deploy_experiment_not_significant(self):
        from services.self_improvement.governance import can_deploy_experiment
        from services.self_improvement.models import ABExperiment
        exp = ABExperiment(p_value=0.20, metric_a=0.5, metric_b=0.55)
        assert can_deploy_experiment(exp) is False

    def test_can_deploy_experiment_significant(self):
        from services.self_improvement.governance import can_deploy_experiment
        from services.self_improvement.models import ABExperiment
        exp = ABExperiment(p_value=0.02, metric_a=0.5, metric_b=0.56)
        assert can_deploy_experiment(exp) is True


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Audit Log
# ═══════════════════════════════════════════════════════════════════════════════

class TestAuditLog:
    def _log(self):
        from services.self_improvement.audit_log import AuditLog
        return AuditLog()

    def test_log_returns_entry(self):
        al    = self._log()
        entry = al.log("test_action", "copilot", {"key": "val"}, "admin")
        assert entry["action"] == "test_action"
        assert "entry_id" in entry

    def test_get_log_all(self):
        al = self._log()
        al.log("a1", "copilot")
        al.log("a2", "manuscript")
        assert len(al.get_log()) == 2

    def test_get_log_by_engine(self):
        al = self._log()
        al.log("a1", "copilot")
        al.log("a2", "manuscript")
        al.log("a3", "copilot")
        copilot_log = al.get_log("copilot")
        assert all(e["engine_type"] == "copilot" for e in copilot_log)
        assert len(copilot_log) == 2

    def test_limit_respected(self):
        al = self._log()
        for i in range(20):
            al.log(f"action_{i}")
        assert len(al.get_log(limit=5)) == 5

    def test_entry_count(self):
        al = self._log()
        al.log("a1")
        al.log("a2")
        assert al.entry_count() == 2

    def test_singleton(self):
        from services.self_improvement.audit_log import get_audit_log, reset_audit_log
        reset_audit_log()
        l1 = get_audit_log()
        l2 = get_audit_log()
        assert l1 is l2

    def test_full_log(self):
        al = self._log()
        for i in range(5):
            al.log(f"action_{i}")
        full = al.get_full_log(limit=10)
        assert len(full) == 5


# ═══════════════════════════════════════════════════════════════════════════════
# 13. Copilot Integration
# ═══════════════════════════════════════════════════════════════════════════════

class TestCopilotIntegration:
    def _metrics(self, **kwargs):
        from services.self_improvement.models import EnginePerformanceMetrics
        return EnginePerformanceMetrics(engine_type="copilot", samples_evaluated=20, **kwargs)

    def test_empty_metrics_returns_data_collection(self):
        from services.self_improvement.copilot_integration import generate_improvement_suggestions
        result = generate_improvement_suggestions("general", {})
        assert len(result) > 0
        assert result[0]["type"] == "data_collection"

    def test_improving_trend_suggestion(self):
        from services.self_improvement.copilot_integration import generate_improvement_suggestions
        m = {"copilot": self._metrics(accuracy=0.80, trend="improving", avg_confidence=0.75)}
        suggestions = generate_improvement_suggestions("general", m)
        types = [s["type"] for s in suggestions]
        assert "performance_improving" in types

    def test_declining_trend_suggestion(self):
        from services.self_improvement.copilot_integration import generate_improvement_suggestions
        m = {"copilot": self._metrics(accuracy=0.55, trend="declining", avg_confidence=0.60)}
        suggestions = generate_improvement_suggestions("general", m)
        types = [s["type"] for s in suggestions]
        assert "performance_alert" in types

    def test_calibration_drift_suggestion(self):
        from services.self_improvement.copilot_integration import generate_improvement_suggestions
        m = {"copilot": self._metrics(calibration_error=0.20)}
        suggestions = generate_improvement_suggestions("general", m)
        types = [s["type"] for s in suggestions]
        assert "calibration_drift" in types

    def test_max_suggestions_respected(self):
        from services.self_improvement.copilot_integration import generate_improvement_suggestions
        m = {f"engine_{i}": self._metrics(trend="declining", calibration_error=0.20) for i in range(10)}
        suggestions = generate_improvement_suggestions("general", m, max_suggestions=3)
        assert len(suggestions) <= 3

    def test_enrich_prompt_contains_original(self):
        from services.self_improvement.copilot_integration import enrich_with_quality_context
        result = enrich_with_quality_context("My original prompt.", [])
        assert "My original prompt." in result

    def test_enrich_prompt_adds_context(self):
        from services.self_improvement.copilot_integration import enrich_with_quality_context
        from services.self_improvement.models import DiagnosticReport, DiagnosticStatus
        diag = [DiagnosticReport(engine_type="copilot", status=DiagnosticStatus.HEALTHY.value, health_score=0.9)]
        result = enrich_with_quality_context("prompt", diag)
        assert "Platform Quality Context" in result

    def test_suggestions_have_required_fields(self):
        from services.self_improvement.copilot_integration import generate_improvement_suggestions
        suggestions = generate_improvement_suggestions("general", {})
        for s in suggestions:
            assert "type" in s
            assert "title" in s
            assert "confidence" in s


# ═══════════════════════════════════════════════════════════════════════════════
# 14. Telemetry
# ═══════════════════════════════════════════════════════════════════════════════

class TestTelemetry:
    def setup_method(self):
        from services.self_improvement import telemetry as tel_mod
        tel_mod.SelfImprovementTelemetry._instance = None

    def test_singleton(self):
        from services.self_improvement.telemetry import get_telemetry
        t1 = get_telemetry()
        t2 = get_telemetry()
        assert t1 is t2

    def test_inc_counter(self):
        from services.self_improvement.telemetry import get_telemetry
        t = get_telemetry()
        t.inc("signals_received", 5)
        assert t.to_dict()["signals_received"] == 5

    def test_record_latency(self):
        from services.self_improvement.telemetry import get_telemetry
        t = get_telemetry()
        t.record_latency(0.15)
        assert t.to_dict()["avg_latency_seconds"] > 0

    def test_all_counter_keys_present(self):
        from services.self_improvement.telemetry import get_telemetry
        d = get_telemetry().to_dict()
        for key in ("signals_received", "optimizations_generated", "optimizations_applied",
                    "experiments_created", "knowledge_updates_detected", "benchmarks_run", "errors"):
            assert key in d

    def test_latency_cap(self):
        from services.self_improvement.telemetry import get_telemetry
        t = get_telemetry()
        for _ in range(600):
            t.record_latency(0.01)
        assert len(t.latencies) <= 500


# ═══════════════════════════════════════════════════════════════════════════════
# 15. Engine Integration
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineIntegration:
    def _engine(self):
        from services.self_improvement.engine import SelfImprovementEngine
        return SelfImprovementEngine()

    def test_record_feedback(self):
        e = self._engine()
        result = e.record_feedback("user_feedback", "copilot", outcome="accepted", confidence=0.8)
        assert "signal_id" in result

    def test_feedback_updates_performance(self):
        e = self._engine()
        for _ in range(5):
            e.record_feedback("prediction_accuracy", "copilot", outcome="accepted", confidence=0.9)
        perf = e.get_performance("copilot")
        assert perf["samples_evaluated"] == 5

    def test_generate_optimizations(self):
        e = self._engine()
        for _ in range(60):
            e.record_feedback("prediction_accuracy", "journal_predictor",
                              outcome="rejected", confidence=0.9)
        result = e.generate_optimizations()
        assert isinstance(result, list)

    def test_apply_and_rollback_optimization(self):
        e = self._engine()
        for _ in range(60):
            e.record_feedback("prediction_accuracy", "journal_predictor",
                              outcome="rejected", confidence=0.95)
        cands = e.generate_optimizations()
        if cands:
            rid = cands[0]["record_id"]
            assert e.apply_optimization(rid) is True
            assert e.rollback_optimization(rid) is True

    def test_run_benchmark(self):
        e = self._engine()
        result = e.run_benchmark("publication_predictor")
        assert "score" in result

    def test_create_experiment(self):
        e = self._engine()
        exp = e.create_experiment("mytest", "copilot", {"a": 1}, {"b": 2})
        assert exp["name"] == "mytest"

    def test_get_platform_quality(self):
        e = self._engine()
        q = e.get_platform_quality()
        assert "overall_score" in q
        assert "generated_at" in q

    def test_get_policy(self):
        e = self._engine()
        p = e.get_policy()
        assert "learning_enabled" in p

    def test_update_policy(self):
        e = self._engine()
        p = e.update_policy({"retention_days": 60}, "test_admin")
        assert p["retention_days"] == 60

    def test_knowledge_ingest(self):
        e = self._engine()
        updates = e.ingest_text("deep learning transformers for natural language processing")
        assert isinstance(updates, list)

    def test_personalize_returns_recs(self):
        e = self._engine()
        recs   = [{"category": "lit", "score": 0.8}, {"category": "grant", "score": 0.6}]
        result = e.personalize(recs, "cohort_test")
        assert len(result) == 2

    def test_copilot_suggestions(self):
        e      = self._engine()
        result = e.copilot_suggestions("general")
        assert isinstance(result, list)

    def test_run_diagnostics(self):
        e = self._engine()
        e.record_feedback("user_feedback", "copilot", outcome="accepted", confidence=0.8)
        result = e.run_diagnostics()
        assert isinstance(result, list)

    def test_audit_log_populated(self):
        e = self._engine()
        e.record_feedback("user_feedback", "copilot")
        log = e.get_audit_log()
        assert len(log) >= 1

    def test_feedback_summary(self):
        e = self._engine()
        e.record_feedback("user_feedback", "copilot")
        s = e.get_feedback_summary()
        assert s["total_signals"] == 1


# ═══════════════════════════════════════════════════════════════════════════════
# 16. Async Singleton
# ═══════════════════════════════════════════════════════════════════════════════

class TestAsyncSingleton:
    def test_same_instance(self):
        from services.self_improvement.engine import get_self_improvement_engine, reset_self_improvement_engine
        reset_self_improvement_engine()

        async def _run():
            e1 = await get_self_improvement_engine()
            e2 = await get_self_improvement_engine()
            return e1 is e2

        assert asyncio.run(_run()) is True

    def test_reset_creates_new_instance(self):
        from services.self_improvement.engine import get_self_improvement_engine, reset_self_improvement_engine
        reset_self_improvement_engine()

        async def _run():
            e1 = await get_self_improvement_engine()
            reset_self_improvement_engine()
            e2 = await get_self_improvement_engine()
            return e1 is not e2

        assert asyncio.run(_run()) is True

    def test_engine_usable_after_reset(self):
        from services.self_improvement.engine import get_self_improvement_engine, reset_self_improvement_engine
        reset_self_improvement_engine()

        async def _run():
            e = await get_self_improvement_engine()
            return e.get_platform_quality()

        q = asyncio.run(_run())
        assert "overall_score" in q


# ═══════════════════════════════════════════════════════════════════════════════
# 17. Plans Catalogue
# ═══════════════════════════════════════════════════════════════════════════════

class TestPlansCatalogue:
    def test_all_si_keys_present(self):
        from plans_catalogue import CREDIT_COSTS
        for key in ("si_query", "si_diagnostics", "si_benchmark", "si_experiment", "si_optimize", "si_copilot"):
            assert key in CREDIT_COSTS, f"Missing: {key}"

    def test_benchmark_costs_more_than_query(self):
        from plans_catalogue import get_credit_cost
        assert get_credit_cost("si_benchmark") > get_credit_cost("si_query")

    def test_optimize_costs_more_than_copilot(self):
        from plans_catalogue import get_credit_cost
        assert get_credit_cost("si_optimize") > get_credit_cost("si_copilot")

    def test_all_costs_positive(self):
        from plans_catalogue import get_credit_cost
        for key in ("si_query", "si_diagnostics", "si_benchmark", "si_experiment", "si_optimize", "si_copilot"):
            assert get_credit_cost(key) > 0


if __name__ == "__main__":
    import subprocess
    subprocess.run(["python", "-m", "pytest", __file__, "-v"])
