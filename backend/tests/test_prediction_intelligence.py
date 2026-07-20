"""Test suite for Phase XVIII — Academic Prediction & Forecasting Intelligence Engine.

Run: python -m pytest backend/tests/test_prediction_intelligence.py -v
"""
import asyncio
import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Sample fixtures ────────────────────────────────────────────────────────────

SAMPLE_MANUSCRIPT = {
    "word_count": 7500,
    "reference_count": 45,
    "methodology_score": 0.75,
    "novelty_score": 0.70,
    "statistical_quality": 0.80,
    "prior_submissions": 0,
    "scope_match": 0.85,
    "abstract_word_count": 250,
    "authors": [
        {"h_index": 12, "publication_count": 25, "name": "Alice"},
        {"h_index": 8,  "publication_count": 15, "name": "Bob"},
    ],
    "target_journal": {
        "name": "PLOS ONE",
        "impact_factor": 3.7,
        "acceptance_rate": 0.69,
        "avg_review_weeks": 10,
    },
    "keywords": ["machine learning", "neural networks", "deep learning"],
}

SAMPLE_CAREER = {
    "current_h_index": 8,
    "total_citations": 320,
    "total_publications": 22,
    "publications_per_year": 4.0,
    "citations_per_year": 55,
    "career_stage": "early_career",
    "years_active": 6,
    "collaboration_count": 12,
    "international_collaboration_count": 4,
    "research_domains": ["machine learning", "NLP"],
    "current_grants": 1,
    "teaching_load": 0.3,
    "admin_load": 0.1,
}

SAMPLE_GRANT = {
    "grant_type": "basic_research",
    "budget_requested": 250000,
    "typical_budget_range": [100000, 500000],
    "team_size": 4,
    "prior_publications_on_topic": 8,
    "pi_h_index": 15,
    "novelty_score": 0.75,
    "relevance_to_priorities": 0.80,
    "preliminary_data_score": 0.70,
    "methodology_rigor": 0.80,
    "collaboration_breadth": 3,
    "international_partners": 2,
    "budget_justification_score": 0.75,
    "prior_grants": 2,
}

SAMPLE_COLLABORATION = {
    "collaborators": [
        {"h_index": 15, "publications": 40, "domain": "NLP", "name": "Prof X"},
        {"h_index": 20, "publications": 65, "domain": "CV",  "name": "Prof Y"},
    ],
    "collaboration_type": "co_author",
    "duration_planned_months": 24,
    "domains": ["NLP", "Computer Vision", "Machine Learning"],
    "prior_collaboration_history": True,
    "geographic_spread": 3,
}

SAMPLE_INSTITUTION = {
    "name": "MIT",
    "total_faculty": 150,
    "avg_faculty_h_index": 18,
    "publications_per_year": 450,
    "citations_per_year": 8500,
    "active_grants": 85,
    "total_funding_eur": 45_000_000,
    "research_domains": ["engineering", "computer science", "physics"],
    "rankings": {"QS": 5, "THE": 3},
    "international_collaboration_pct": 0.65,
}


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Models
# ═══════════════════════════════════════════════════════════════════════════════

class TestModels:
    def test_prediction_type_count(self):
        from services.prediction_intelligence.models import PredictionType
        assert len(PredictionType) == 17

    def test_confidence_level_count(self):
        from services.prediction_intelligence.models import ConfidenceLevel
        assert len(ConfidenceLevel) == 5

    def test_forecast_horizon_count(self):
        from services.prediction_intelligence.models import ForecastHorizon
        assert len(ForecastHorizon) == 4

    def test_viz_type_count(self):
        from services.prediction_intelligence.models import VizType
        assert len(VizType) == 8

    def test_scenario_type_count(self):
        from services.prediction_intelligence.models import ScenarioType
        assert len(ScenarioType) == 7

    def test_what_if_factor_count(self):
        from services.prediction_intelligence.models import WhatIfFactor
        assert len(WhatIfFactor) == 7

    def test_make_prediction_clamps_probability(self):
        from services.prediction_intelligence.models import PredictionType, _make_prediction
        p = _make_prediction(PredictionType.PUBLICATION_ACCEPTANCE, 1.5, 0.8)
        assert p.value == 1.0

    def test_make_prediction_negative_clamped(self):
        from services.prediction_intelligence.models import PredictionType, _make_prediction
        p = _make_prediction(PredictionType.DESK_REJECTION, -0.3, 0.7)
        assert p.value == 0.0

    def test_make_prediction_confidence_clamped(self):
        from services.prediction_intelligence.models import PredictionType, _make_prediction
        p = _make_prediction(PredictionType.CITATION_VELOCITY, 0.5, 1.5)
        assert 0.0 <= p.confidence <= 1.0

    def test_make_prediction_no_clamp(self):
        from services.prediction_intelligence.models import PredictionType, _make_prediction
        p = _make_prediction(PredictionType.REVIEW_TIME, 15.0, 0.7, unit="weeks", clamp_probability=False)
        assert p.value == 15.0

    def test_prediction_to_dict_keys(self):
        from services.prediction_intelligence.models import PredictionType, _make_prediction
        p = _make_prediction(PredictionType.FUNDING_PROBABILITY, 0.35, 0.70)
        d = p.to_dict()
        for key in ("prediction_id", "value", "confidence", "evidence", "reasoning", "unit"):
            assert key in d

    def test_confidence_level_assignment(self):
        from services.prediction_intelligence.models import PredictionType, _make_prediction, ConfidenceLevel
        p_high  = _make_prediction(PredictionType.GRANT_SCORE, 0.5, 0.90)
        p_low   = _make_prediction(PredictionType.GRANT_SCORE, 0.5, 0.20)
        assert p_high.confidence_level == ConfidenceLevel.VERY_HIGH.value
        assert p_low.confidence_level  == ConfidenceLevel.VERY_LOW.value


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Confidence Model
# ═══════════════════════════════════════════════════════════════════════════════

class TestConfidenceModel:
    def test_output_in_range(self):
        from services.prediction_intelligence.confidence_model import compute_confidence
        c = compute_confidence(0.8, 0.7, "publication_acceptance", 5)
        assert 0.0 <= c <= 1.0

    def test_high_completeness_raises_confidence(self):
        from services.prediction_intelligence.confidence_model import compute_confidence
        c1 = compute_confidence(0.2, 0.5)
        c2 = compute_confidence(0.9, 0.5)
        assert c2 > c1

    def test_high_signal_raises_confidence(self):
        from services.prediction_intelligence.confidence_model import compute_confidence
        c1 = compute_confidence(0.5, 0.2)
        c2 = compute_confidence(0.5, 0.9)
        assert c2 > c1

    def test_graph_evidence_raises_confidence(self):
        from services.prediction_intelligence.confidence_model import compute_confidence
        c1 = compute_confidence(0.6, 0.6, graph_evidence_count=0)
        c2 = compute_confidence(0.6, 0.6, graph_evidence_count=20)
        assert c2 > c1

    def test_data_completeness_function(self):
        from services.prediction_intelligence.confidence_model import data_completeness
        profile = {"a": 1, "b": None, "c": 3}
        dc = data_completeness(profile, ["a", "b", "c"])
        assert abs(dc - 2/3) < 0.01

    def test_signal_quality_average(self):
        from services.prediction_intelligence.confidence_model import signal_quality
        sq = signal_quality(0.6, 0.8)
        assert abs(sq - 0.7) < 0.01

    def test_signal_quality_clamps(self):
        from services.prediction_intelligence.confidence_model import signal_quality
        sq = signal_quality(1.5, -0.5)
        assert 0.0 <= sq <= 1.0

    def test_empty_required_keys(self):
        from services.prediction_intelligence.confidence_model import data_completeness
        assert data_completeness({}, []) == 0.5


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Publication Predictor
# ═══════════════════════════════════════════════════════════════════════════════

class TestPublicationPredictor:
    def test_returns_result(self):
        from services.prediction_intelligence.publication_predictor import predict_publication
        result = predict_publication(SAMPLE_MANUSCRIPT)
        assert result is not None

    def test_acceptance_probability_in_range(self):
        from services.prediction_intelligence.publication_predictor import predict_publication
        result = predict_publication(SAMPLE_MANUSCRIPT)
        assert 0.0 <= result.acceptance.value <= 1.0

    def test_desk_rejection_in_range(self):
        from services.prediction_intelligence.publication_predictor import predict_publication
        result = predict_publication(SAMPLE_MANUSCRIPT)
        assert 0.0 <= result.desk_rejection.value <= 1.0

    def test_empty_manuscript_no_crash(self):
        from services.prediction_intelligence.publication_predictor import predict_publication
        result = predict_publication({})
        assert result is not None
        assert 0.0 <= result.acceptance.value <= 1.0

    def test_low_quality_lowers_acceptance(self):
        from services.prediction_intelligence.publication_predictor import predict_publication
        good_ms = {**SAMPLE_MANUSCRIPT, "methodology_score": 0.90, "novelty_score": 0.90}
        poor_ms = {**SAMPLE_MANUSCRIPT, "methodology_score": 0.20, "novelty_score": 0.20}
        assert predict_publication(good_ms).acceptance.value > predict_publication(poor_ms).acceptance.value

    def test_high_prior_submissions_penalty(self):
        from services.prediction_intelligence.publication_predictor import predict_publication
        ms0 = {**SAMPLE_MANUSCRIPT, "prior_submissions": 0}
        ms5 = {**SAMPLE_MANUSCRIPT, "prior_submissions": 5}
        assert predict_publication(ms0).acceptance.value > predict_publication(ms5).acceptance.value

    def test_strategic_recommendation_present(self):
        from services.prediction_intelligence.publication_predictor import predict_publication
        result = predict_publication(SAMPLE_MANUSCRIPT)
        assert isinstance(result.strategic_recommendation, str)
        assert len(result.strategic_recommendation) > 0

    def test_manuscript_score_in_range(self):
        from services.prediction_intelligence.publication_predictor import predict_publication
        result = predict_publication(SAMPLE_MANUSCRIPT)
        assert 0.0 <= result.manuscript_score <= 1.0

    def test_citation_velocity_non_negative(self):
        from services.prediction_intelligence.publication_predictor import predict_publication
        result = predict_publication(SAMPLE_MANUSCRIPT)
        assert result.citation_velocity_y1.value >= 0.0

    def test_to_dict_serializable(self):
        from services.prediction_intelligence.publication_predictor import predict_publication
        result = predict_publication(SAMPLE_MANUSCRIPT)
        d = result.to_dict()
        assert "acceptance" in d
        assert "strategic_recommendation" in d


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Journal Predictor
# ═══════════════════════════════════════════════════════════════════════════════

class TestJournalPredictor:
    def test_returns_result(self):
        from services.prediction_intelligence.journal_predictor import predict_journals
        result = predict_journals(SAMPLE_MANUSCRIPT)
        assert result is not None

    def test_all_matches_non_empty(self):
        from services.prediction_intelligence.journal_predictor import predict_journals
        result = predict_journals(SAMPLE_MANUSCRIPT)
        assert len(result.all_matches) > 0

    def test_acceptance_probabilities_in_range(self):
        from services.prediction_intelligence.journal_predictor import predict_journals
        result = predict_journals(SAMPLE_MANUSCRIPT)
        for j in result.all_matches:
            assert 0.0 <= j.acceptance_probability <= 1.0

    def test_best_journal_has_highest_rec_score(self):
        from services.prediction_intelligence.journal_predictor import predict_journals
        result = predict_journals(SAMPLE_MANUSCRIPT)
        best_score = result.best_journal.recommendation_score
        for j in result.all_matches:
            assert j.recommendation_score <= best_score + 0.001

    def test_fastest_pub_is_fastest(self):
        from services.prediction_intelligence.journal_predictor import predict_journals
        result = predict_journals(SAMPLE_MANUSCRIPT)
        fastest = result.fastest_publication.publication_speed_weeks
        for j in result.all_matches:
            assert j.publication_speed_weeks >= fastest - 0.1

    def test_empty_manuscript_no_crash(self):
        from services.prediction_intelligence.journal_predictor import predict_journals
        result = predict_journals({})
        assert len(result.all_matches) > 0

    def test_confidence_in_range(self):
        from services.prediction_intelligence.journal_predictor import predict_journals
        result = predict_journals(SAMPLE_MANUSCRIPT)
        assert 0.0 <= result.confidence <= 1.0

    def test_reasoning_present(self):
        from services.prediction_intelligence.journal_predictor import predict_journals
        result = predict_journals(SAMPLE_MANUSCRIPT)
        assert len(result.reasoning) > 0

    def test_to_dict_keys(self):
        from services.prediction_intelligence.journal_predictor import predict_journals
        d = predict_journals(SAMPLE_MANUSCRIPT).to_dict()
        assert "best_journal" in d
        assert "all_matches" in d


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Conference Predictor
# ═══════════════════════════════════════════════════════════════════════════════

class TestConferencePredictor:
    def test_returns_list(self):
        from services.prediction_intelligence.conference_predictor import predict_conference
        results = predict_conference({"manuscript_quality": 0.75, "novelty_score": 0.70,
                                       "conference_tier": 1, "keywords": ["deep learning"]})
        assert isinstance(results, list)
        assert len(results) > 0

    def test_acceptance_in_range(self):
        from services.prediction_intelligence.conference_predictor import predict_conference
        results = predict_conference({"manuscript_quality": 0.7, "conference_tier": 2})
        for r in results:
            assert 0.0 <= r.acceptance_probability.value <= 1.0

    def test_overall_score_in_range(self):
        from services.prediction_intelligence.conference_predictor import predict_conference
        results = predict_conference({"conference_tier": 2})
        for r in results:
            assert 0.0 <= r.overall_score <= 1.0

    def test_empty_profile_no_crash(self):
        from services.prediction_intelligence.conference_predictor import predict_conference
        results = predict_conference({})
        assert isinstance(results, list)

    def test_to_dict_keys(self):
        from services.prediction_intelligence.conference_predictor import predict_conference
        results = predict_conference({"conference_tier": 1})
        if results:
            d = results[0].to_dict()
            assert "conference_name" in d
            assert "acceptance_probability" in d

    def test_recommendation_present(self):
        from services.prediction_intelligence.conference_predictor import predict_conference
        results = predict_conference({"conference_tier": 2, "manuscript_quality": 0.7})
        for r in results:
            assert isinstance(r.recommendation, str)

    def test_sorted_by_score(self):
        from services.prediction_intelligence.conference_predictor import predict_conference
        results = predict_conference({"conference_tier": 2})
        scores = [r.overall_score for r in results]
        assert scores == sorted(scores, reverse=True)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Grant Predictor
# ═══════════════════════════════════════════════════════════════════════════════

class TestGrantPredictor:
    def test_returns_result(self):
        from services.prediction_intelligence.grant_predictor import predict_grant
        result = predict_grant(SAMPLE_GRANT)
        assert result is not None

    def test_funding_probability_in_range(self):
        from services.prediction_intelligence.grant_predictor import predict_grant
        result = predict_grant(SAMPLE_GRANT)
        assert 0.0 <= result.funding_probability.value <= 1.0

    def test_budget_adequacy_in_range(self):
        from services.prediction_intelligence.grant_predictor import predict_grant
        result = predict_grant(SAMPLE_GRANT)
        assert 0.0 <= result.budget_adequacy.value <= 1.0

    def test_reviewer_concerns_non_empty(self):
        from services.prediction_intelligence.grant_predictor import predict_grant
        result = predict_grant(SAMPLE_GRANT)
        assert len(result.reviewer_concerns) > 0

    def test_high_quality_higher_prob(self):
        from services.prediction_intelligence.grant_predictor import predict_grant
        strong = {**SAMPLE_GRANT, "novelty_score": 0.95, "methodology_rigor": 0.95}
        weak   = {**SAMPLE_GRANT, "novelty_score": 0.20, "methodology_rigor": 0.20}
        assert predict_grant(strong).funding_probability.value > predict_grant(weak).funding_probability.value

    def test_empty_grant_no_crash(self):
        from services.prediction_intelligence.grant_predictor import predict_grant
        result = predict_grant({})
        assert 0.0 <= result.funding_probability.value <= 1.0

    def test_required_improvements_list(self):
        from services.prediction_intelligence.grant_predictor import predict_grant
        result = predict_grant(SAMPLE_GRANT)
        assert isinstance(result.required_improvements, list)

    def test_to_dict_keys(self):
        from services.prediction_intelligence.grant_predictor import predict_grant
        d = predict_grant(SAMPLE_GRANT).to_dict()
        assert "funding_probability" in d
        assert "reviewer_concerns" in d

    def test_confidence_in_range(self):
        from services.prediction_intelligence.grant_predictor import predict_grant
        result = predict_grant(SAMPLE_GRANT)
        assert 0.0 <= result.confidence <= 1.0

    def test_expected_success_rate_matches_prob(self):
        from services.prediction_intelligence.grant_predictor import predict_grant
        result = predict_grant(SAMPLE_GRANT)
        assert abs(result.expected_success_rate - result.funding_probability.value) < 0.001


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Career Forecaster
# ═══════════════════════════════════════════════════════════════════════════════

class TestCareerForecaster:
    def test_returns_result(self):
        from services.prediction_intelligence.career_forecaster import forecast_career, ForecastHorizon
        result = forecast_career(SAMPLE_CAREER, ForecastHorizon.THREE_YEAR)
        assert result is not None

    def test_h_index_above_current(self):
        from services.prediction_intelligence.career_forecaster import forecast_career, ForecastHorizon
        result = forecast_career(SAMPLE_CAREER, ForecastHorizon.THREE_YEAR)
        assert result.h_index.value >= SAMPLE_CAREER["current_h_index"]

    def test_citations_above_current(self):
        from services.prediction_intelligence.career_forecaster import forecast_career, ForecastHorizon
        result = forecast_career(SAMPLE_CAREER, ForecastHorizon.THREE_YEAR)
        assert result.citations.value >= SAMPLE_CAREER["total_citations"]

    def test_promotion_readiness_in_range(self):
        from services.prediction_intelligence.career_forecaster import forecast_career, ForecastHorizon
        result = forecast_career(SAMPLE_CAREER, ForecastHorizon.THREE_YEAR)
        assert 0.0 <= result.promotion_readiness.value <= 1.0

    def test_longer_horizon_higher_h(self):
        from services.prediction_intelligence.career_forecaster import forecast_career, ForecastHorizon
        r1 = forecast_career(SAMPLE_CAREER, ForecastHorizon.ONE_YEAR)
        r5 = forecast_career(SAMPLE_CAREER, ForecastHorizon.FIVE_YEAR)
        assert r5.h_index.value >= r1.h_index.value

    def test_empty_profile_no_crash(self):
        from services.prediction_intelligence.career_forecaster import forecast_career, ForecastHorizon
        result = forecast_career({}, ForecastHorizon.ONE_YEAR)
        assert result is not None

    def test_milestones_list(self):
        from services.prediction_intelligence.career_forecaster import forecast_career, ForecastHorizon
        result = forecast_career(SAMPLE_CAREER, ForecastHorizon.THREE_YEAR)
        assert isinstance(result.milestones, list)

    def test_to_dict_has_horizon(self):
        from services.prediction_intelligence.career_forecaster import forecast_career, ForecastHorizon
        result = forecast_career(SAMPLE_CAREER, ForecastHorizon.FIVE_YEAR)
        d = result.to_dict()
        assert d["horizon"] == "5y"

    def test_confidence_in_range(self):
        from services.prediction_intelligence.career_forecaster import forecast_career, ForecastHorizon
        result = forecast_career(SAMPLE_CAREER, ForecastHorizon.THREE_YEAR)
        assert 0.0 <= result.confidence <= 1.0

    def test_leadership_potential_in_range(self):
        from services.prediction_intelligence.career_forecaster import forecast_career, ForecastHorizon
        result = forecast_career(SAMPLE_CAREER, ForecastHorizon.THREE_YEAR)
        assert 0.0 <= result.leadership_potential.value <= 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Collaboration Forecaster
# ═══════════════════════════════════════════════════════════════════════════════

class TestCollaborationForecaster:
    def test_returns_result(self):
        from services.prediction_intelligence.collaboration_forecaster import forecast_collaboration
        result = forecast_collaboration(SAMPLE_COLLABORATION)
        assert result is not None

    def test_success_in_range(self):
        from services.prediction_intelligence.collaboration_forecaster import forecast_collaboration
        result = forecast_collaboration(SAMPLE_COLLABORATION)
        assert 0.0 <= result.success_probability.value <= 1.0

    def test_prior_history_boosts_success(self):
        from services.prediction_intelligence.collaboration_forecaster import forecast_collaboration
        with_hist    = {**SAMPLE_COLLABORATION, "prior_collaboration_history": True}
        without_hist = {**SAMPLE_COLLABORATION, "prior_collaboration_history": False}
        assert forecast_collaboration(with_hist).success_probability.value > \
               forecast_collaboration(without_hist).success_probability.value

    def test_empty_profile_no_crash(self):
        from services.prediction_intelligence.collaboration_forecaster import forecast_collaboration
        result = forecast_collaboration({})
        assert 0.0 <= result.success_probability.value <= 1.0

    def test_recommendation_present(self):
        from services.prediction_intelligence.collaboration_forecaster import forecast_collaboration
        result = forecast_collaboration(SAMPLE_COLLABORATION)
        assert isinstance(result.overall_recommendation, str)

    def test_to_dict_keys(self):
        from services.prediction_intelligence.collaboration_forecaster import forecast_collaboration
        d = forecast_collaboration(SAMPLE_COLLABORATION).to_dict()
        assert "success_probability" in d
        assert "overall_recommendation" in d

    def test_confidence_in_range(self):
        from services.prediction_intelligence.collaboration_forecaster import forecast_collaboration
        result = forecast_collaboration(SAMPLE_COLLABORATION)
        assert 0.0 <= result.confidence <= 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Institution Forecaster
# ═══════════════════════════════════════════════════════════════════════════════

class TestInstitutionForecaster:
    def test_returns_result(self):
        from services.prediction_intelligence.institution_forecaster import forecast_institution, ForecastHorizon
        result = forecast_institution(SAMPLE_INSTITUTION, ForecastHorizon.THREE_YEAR)
        assert result is not None

    def test_publication_output_positive(self):
        from services.prediction_intelligence.institution_forecaster import forecast_institution, ForecastHorizon
        result = forecast_institution(SAMPLE_INSTITUTION, ForecastHorizon.THREE_YEAR)
        assert result.publication_output.value > 0

    def test_strategic_risks_list(self):
        from services.prediction_intelligence.institution_forecaster import forecast_institution, ForecastHorizon
        result = forecast_institution(SAMPLE_INSTITUTION, ForecastHorizon.THREE_YEAR)
        assert isinstance(result.strategic_risks, list)
        assert len(result.strategic_risks) > 0

    def test_funding_probability_in_range(self):
        from services.prediction_intelligence.institution_forecaster import forecast_institution, ForecastHorizon
        result = forecast_institution(SAMPLE_INSTITUTION, ForecastHorizon.THREE_YEAR)
        assert 0.0 <= result.funding_growth.value <= 1.0

    def test_empty_profile_no_crash(self):
        from services.prediction_intelligence.institution_forecaster import forecast_institution, ForecastHorizon
        result = forecast_institution({}, ForecastHorizon.ONE_YEAR)
        assert result is not None

    def test_to_dict_has_horizon(self):
        from services.prediction_intelligence.institution_forecaster import forecast_institution, ForecastHorizon
        d = forecast_institution(SAMPLE_INSTITUTION, ForecastHorizon.FIVE_YEAR).to_dict()
        assert d["horizon"] == "5y"

    def test_confidence_in_range(self):
        from services.prediction_intelligence.institution_forecaster import forecast_institution, ForecastHorizon
        result = forecast_institution(SAMPLE_INSTITUTION, ForecastHorizon.THREE_YEAR)
        assert 0.0 <= result.confidence <= 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Trend Forecaster
# ═══════════════════════════════════════════════════════════════════════════════

class TestTrendForecaster:
    def test_returns_result(self):
        from services.prediction_intelligence.trend_forecaster import forecast_trends
        result = forecast_trends()
        assert result is not None

    def test_emerging_topics_non_empty(self):
        from services.prediction_intelligence.trend_forecaster import forecast_trends
        result = forecast_trends()
        assert len(result.emerging_topics) > 0

    def test_hot_topics_non_empty(self):
        from services.prediction_intelligence.trend_forecaster import forecast_trends
        result = forecast_trends()
        assert len(result.hot_topics) > 0

    def test_declining_topics_non_empty(self):
        from services.prediction_intelligence.trend_forecaster import forecast_trends
        result = forecast_trends()
        assert len(result.declining_topics) > 0

    def test_topic_scores_in_range(self):
        from services.prediction_intelligence.trend_forecaster import forecast_trends
        result = forecast_trends()
        for t in result.emerging_topics + result.hot_topics + result.declining_topics:
            assert 0.0 <= t.score <= 1.0

    def test_with_domain_profile(self):
        from services.prediction_intelligence.trend_forecaster import forecast_trends
        result = forecast_trends({"research_domains": ["machine learning"]})
        assert result is not None

    def test_future_methodologies_non_empty(self):
        from services.prediction_intelligence.trend_forecaster import forecast_trends
        result = forecast_trends()
        assert len(result.future_methodologies) > 0

    def test_to_dict_keys(self):
        from services.prediction_intelligence.trend_forecaster import forecast_trends
        d = forecast_trends().to_dict()
        assert "emerging_topics" in d
        assert "declining_topics" in d
        assert "future_methodologies" in d


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Scenario Simulator
# ═══════════════════════════════════════════════════════════════════════════════

class TestScenarioSimulator:
    def test_returns_comparison(self):
        from services.prediction_intelligence.scenario_simulator import simulate_scenarios
        result = simulate_scenarios(SAMPLE_MANUSCRIPT)
        assert result is not None
        assert len(result.scenarios) > 0

    def test_recommended_scenario_set(self):
        from services.prediction_intelligence.scenario_simulator import simulate_scenarios
        result = simulate_scenarios(SAMPLE_MANUSCRIPT)
        assert isinstance(result.recommended_scenario, str)
        assert len(result.recommended_scenario) > 0

    def test_comparison_matrix_populated(self):
        from services.prediction_intelligence.scenario_simulator import simulate_scenarios
        result = simulate_scenarios(SAMPLE_MANUSCRIPT)
        assert "acceptance_probability" in result.comparison_matrix

    def test_custom_scenarios(self):
        from services.prediction_intelligence.scenario_simulator import simulate_scenarios
        result = simulate_scenarios(SAMPLE_MANUSCRIPT, ["submit_now", "delay_3_months"])
        assert len(result.scenarios) == 2

    def test_improve_scenario_higher_acceptance(self):
        from services.prediction_intelligence.scenario_simulator import simulate_scenarios
        result = simulate_scenarios(SAMPLE_MANUSCRIPT, ["submit_now", "delay_6_months"])
        acc_now = result.comparison_matrix["acceptance_probability"].get("Submit Now", 0)
        acc_del = result.comparison_matrix["acceptance_probability"].get("Delay 6 Months", 0)
        assert acc_del >= acc_now

    def test_what_if_returns_analysis(self):
        from services.prediction_intelligence.scenario_simulator import what_if_analysis
        result = what_if_analysis(SAMPLE_MANUSCRIPT, "improve_statistics")
        assert result is not None

    def test_what_if_positive_benefit(self):
        from services.prediction_intelligence.scenario_simulator import what_if_analysis
        result = what_if_analysis(SAMPLE_MANUSCRIPT, "improve_statistics")
        assert result.delta_summary["acceptance_change"] >= 0

    def test_what_if_unknown_factor(self):
        from services.prediction_intelligence.scenario_simulator import what_if_analysis
        result = what_if_analysis(SAMPLE_MANUSCRIPT, "nonexistent_factor")
        assert result is not None

    def test_to_dict_keys(self):
        from services.prediction_intelligence.scenario_simulator import simulate_scenarios
        d = simulate_scenarios(SAMPLE_MANUSCRIPT).to_dict()
        assert "scenarios" in d
        assert "recommended_scenario" in d


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Strategic Advisor
# ═══════════════════════════════════════════════════════════════════════════════

class TestStrategicAdvisor:
    def test_submission_advice(self):
        from services.prediction_intelligence.strategic_advisor import advise
        result = advise("Should I submit now?", SAMPLE_MANUSCRIPT)
        assert result is not None
        assert isinstance(result.recommendation, str)

    def test_journal_advice(self):
        from services.prediction_intelligence.strategic_advisor import advise
        result = advise("Which journal should I target?", SAMPLE_MANUSCRIPT)
        assert result is not None
        assert result.confidence > 0

    def test_collaboration_advice(self):
        from services.prediction_intelligence.strategic_advisor import advise
        result = advise("Should I add collaborators?", SAMPLE_COLLABORATION)
        assert result is not None

    def test_grant_advice(self):
        from services.prediction_intelligence.strategic_advisor import advise
        result = advise("Should I pursue this grant?", SAMPLE_GRANT)
        assert result is not None

    def test_general_advice(self):
        from services.prediction_intelligence.strategic_advisor import advise
        result = advise("What should I do next?", SAMPLE_CAREER)
        assert result is not None

    def test_urgency_valid_value(self):
        from services.prediction_intelligence.strategic_advisor import advise
        from services.prediction_intelligence.models import DecisionUrgency
        result = advise("Should I submit now?", SAMPLE_MANUSCRIPT)
        assert result.urgency in [e.value for e in DecisionUrgency]

    def test_action_items_non_empty(self):
        from services.prediction_intelligence.strategic_advisor import advise
        result = advise("Should I submit now?", SAMPLE_MANUSCRIPT)
        assert len(result.action_items) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# 13. Visualization Builder
# ═══════════════════════════════════════════════════════════════════════════════

class TestVisualizationBuilder:
    def _pub_data(self):
        from services.prediction_intelligence.publication_predictor import predict_publication
        return predict_publication(SAMPLE_MANUSCRIPT).to_dict()

    def _career_data(self):
        from services.prediction_intelligence.career_forecaster import forecast_career, ForecastHorizon
        return forecast_career(SAMPLE_CAREER, ForecastHorizon.THREE_YEAR).to_dict()

    def test_prediction_dashboard(self):
        from services.prediction_intelligence.visualization_builder import build_visualization
        result = build_visualization("prediction_dashboard", self._pub_data())
        assert result["type"] == "prediction_dashboard"
        assert "items" in result

    def test_career_forecast_viz(self):
        from services.prediction_intelligence.visualization_builder import build_visualization
        result = build_visualization("career_forecast", self._career_data())
        assert result["type"] == "career_forecast"

    def test_publication_forecast_viz(self):
        from services.prediction_intelligence.visualization_builder import build_visualization
        result = build_visualization("publication_forecast", self._pub_data())
        assert result["type"] == "publication_forecast"
        assert "distribution" in result

    def test_citation_forecast_viz(self):
        from services.prediction_intelligence.visualization_builder import build_visualization
        result = build_visualization("citation_forecast", self._pub_data())
        assert result["type"] == "citation_forecast"
        assert "series" in result

    def test_grant_forecast_viz(self):
        from services.prediction_intelligence.visualization_builder import build_visualization
        from services.prediction_intelligence.grant_predictor import predict_grant
        data = predict_grant(SAMPLE_GRANT).to_dict()
        result = build_visualization("grant_forecast", data)
        assert result["type"] == "grant_forecast"

    def test_risk_matrix_viz(self):
        from services.prediction_intelligence.visualization_builder import build_visualization
        result = build_visualization("risk_matrix", self._pub_data())
        assert result["type"] == "risk_matrix"
        assert "items" in result

    def test_scenario_comparison_viz(self):
        from services.prediction_intelligence.visualization_builder import build_visualization
        from services.prediction_intelligence.scenario_simulator import simulate_scenarios
        data = simulate_scenarios(SAMPLE_MANUSCRIPT).to_dict()
        result = build_visualization("scenario_comparison", data)
        assert result["type"] == "scenario_comparison"

    def test_timeline_projection_viz(self):
        from services.prediction_intelligence.visualization_builder import build_visualization
        result = build_visualization("timeline_projection", self._career_data())
        assert result["type"] == "timeline_projection"

    def test_invalid_viz_type(self):
        from services.prediction_intelligence.visualization_builder import build_visualization
        result = build_visualization("nonexistent_type", {})
        assert "error" in result

    def test_empty_data_no_crash(self):
        from services.prediction_intelligence.visualization_builder import build_visualization
        result = build_visualization("prediction_dashboard", {})
        assert result["type"] == "prediction_dashboard"


# ═══════════════════════════════════════════════════════════════════════════════
# 14. Copilot Integration
# ═══════════════════════════════════════════════════════════════════════════════

class TestCopilotIntegration:
    def test_returns_suggestions(self):
        from services.prediction_intelligence.copilot_integration import generate_copilot_forecasts
        result = generate_copilot_forecasts("submission", SAMPLE_MANUSCRIPT)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_suggestions_have_required_fields(self):
        from services.prediction_intelligence.copilot_integration import generate_copilot_forecasts
        result = generate_copilot_forecasts("general", SAMPLE_MANUSCRIPT)
        for s in result:
            assert "type" in s
            assert "title" in s
            assert "confidence" in s

    def test_enrich_prompt(self):
        from services.prediction_intelligence.copilot_integration import enrich_prompt_with_predictions
        enriched = enrich_prompt_with_predictions("What should I do?", SAMPLE_MANUSCRIPT)
        assert "What should I do?" in enriched

    def test_empty_profile_no_crash(self):
        from services.prediction_intelligence.copilot_integration import generate_copilot_forecasts
        result = generate_copilot_forecasts("general", {})
        assert isinstance(result, list)

    def test_max_suggestions_respected(self):
        from services.prediction_intelligence.copilot_integration import generate_copilot_forecasts
        result = generate_copilot_forecasts("general", SAMPLE_MANUSCRIPT, max_suggestions=2)
        assert len(result) <= 2

    def test_trend_always_included(self):
        from services.prediction_intelligence.copilot_integration import generate_copilot_forecasts
        result = generate_copilot_forecasts("general", {})
        types = [s["type"] for s in result]
        assert "trend_alert" in types


# ═══════════════════════════════════════════════════════════════════════════════
# 15. Engine Integration
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineIntegration:
    def _engine(self):
        from services.prediction_intelligence.engine import PredictionIntelligenceEngine
        return PredictionIntelligenceEngine()

    def test_predict_publication(self):
        e = self._engine()
        result = e.predict_publication(SAMPLE_MANUSCRIPT)
        assert "acceptance" in result

    def test_predict_journals(self):
        e = self._engine()
        result = e.predict_journals(SAMPLE_MANUSCRIPT)
        assert "all_matches" in result

    def test_predict_conference(self):
        e = self._engine()
        result = e.predict_conference({"conference_tier": 2, "manuscript_quality": 0.7})
        assert isinstance(result, list)

    def test_predict_grant(self):
        e = self._engine()
        result = e.predict_grant(SAMPLE_GRANT)
        assert "funding_probability" in result

    def test_forecast_career(self):
        e = self._engine()
        result = e.forecast_career(SAMPLE_CAREER, "3y")
        assert "h_index" in result

    def test_forecast_collaboration(self):
        e = self._engine()
        result = e.forecast_collaboration(SAMPLE_COLLABORATION)
        assert "success_probability" in result

    def test_forecast_institution(self):
        e = self._engine()
        result = e.forecast_institution(SAMPLE_INSTITUTION, "3y")
        assert "publication_output" in result

    def test_forecast_trends(self):
        e = self._engine()
        result = e.forecast_trends()
        assert "emerging_topics" in result

    def test_strategic_decision(self):
        e = self._engine()
        result = e.strategic_decision("Should I submit now?", SAMPLE_MANUSCRIPT)
        assert "recommendation" in result

    def test_simulate_scenarios(self):
        e = self._engine()
        result = e.simulate_scenarios(SAMPLE_MANUSCRIPT)
        assert "scenarios" in result

    def test_what_if(self):
        e = self._engine()
        result = e.what_if(SAMPLE_MANUSCRIPT, "improve_statistics")
        assert "net_benefit" in result

    def test_visualize(self):
        e = self._engine()
        pub = e.predict_publication(SAMPLE_MANUSCRIPT)
        result = e.visualize("publication_forecast", pub)
        assert "type" in result

    def test_copilot_forecasts(self):
        e = self._engine()
        result = e.copilot_forecasts("submission", SAMPLE_MANUSCRIPT)
        assert isinstance(result, list)

    def test_admin_analytics(self):
        e = self._engine()
        _ = e.predict_publication(SAMPLE_MANUSCRIPT)
        analytics = e.admin_analytics()
        assert "telemetry" in analytics
        assert analytics["telemetry"]["publication_predictions"] >= 1

    def test_invalid_horizon_fallback(self):
        e = self._engine()
        result = e.forecast_career(SAMPLE_CAREER, "invalid_horizon")
        assert "h_index" in result


# ═══════════════════════════════════════════════════════════════════════════════
# 16. Async Singleton
# ═══════════════════════════════════════════════════════════════════════════════

class TestAsyncSingleton:
    def test_singleton_same_instance(self):
        from services.prediction_intelligence.engine import get_prediction_engine, reset_prediction_engine
        reset_prediction_engine()

        async def _run():
            e1 = await get_prediction_engine()
            e2 = await get_prediction_engine()
            return e1 is e2

        assert asyncio.run(_run()) is True

    def test_reset_clears_singleton(self):
        from services.prediction_intelligence.engine import get_prediction_engine, reset_prediction_engine
        reset_prediction_engine()

        async def _run():
            e1 = await get_prediction_engine()
            reset_prediction_engine()
            e2 = await get_prediction_engine()
            return e1 is not e2

        assert asyncio.run(_run()) is True

    def test_telemetry_singleton(self):
        from services.prediction_intelligence.telemetry import get_telemetry
        t1 = get_telemetry()
        t2 = get_telemetry()
        assert t1 is t2

    def test_telemetry_counters(self):
        from services.prediction_intelligence import telemetry as tel_mod
        tel_mod.PredictionTelemetry._instance = None
        tel = tel_mod.get_telemetry()
        tel.inc("publication_predictions", 3)
        assert tel.to_dict()["publication_predictions"] == 3


# ═══════════════════════════════════════════════════════════════════════════════
# 17. Plans Catalogue
# ═══════════════════════════════════════════════════════════════════════════════

class TestPlansCatalogue:
    def test_all_prediction_keys_present(self):
        from plans_catalogue import CREDIT_COSTS
        keys = [
            "prediction_publication", "prediction_journal_ranking", "prediction_conference",
            "prediction_grant", "prediction_career_forecast", "prediction_collaboration",
            "prediction_institution", "prediction_trend", "prediction_strategic",
            "prediction_scenario", "prediction_what_if", "prediction_visualization",
            "prediction_copilot",
        ]
        for k in keys:
            assert k in CREDIT_COSTS, f"Missing: {k}"

    def test_heavy_operations_cost_more(self):
        from plans_catalogue import get_credit_cost
        assert get_credit_cost("prediction_scenario") > get_credit_cost("prediction_visualization")

    def test_publication_cost_positive(self):
        from plans_catalogue import get_credit_cost
        assert get_credit_cost("prediction_publication") > 0

    def test_copilot_cost_reasonable(self):
        from plans_catalogue import get_credit_cost
        assert 1 <= get_credit_cost("prediction_copilot") <= 10


if __name__ == "__main__":
    import subprocess
    subprocess.run(["python", "-m", "pytest", __file__, "-v"])
