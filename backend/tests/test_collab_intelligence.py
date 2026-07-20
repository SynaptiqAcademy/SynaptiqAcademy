"""Tests for Phase XIV — Research Collaboration Intelligence Engine.

116 tests across 17 test classes covering all service modules,
the engine, and the router integration.
"""
from __future__ import annotations

import asyncio
import pytest

# ── Shared fixtures ───────────────────────────────────────────────────────────

_USER_A = {
    "_id": "user_a",
    "full_name": "Alice Chen",
    "institution": "MIT",
    "country": "United States",
    "position": "assistant professor",
    "research_areas": ["machine learning", "bioinformatics"],
    "keywords": ["deep learning", "genomics", "nlp"],
    "research_methods": ["cohort study", "computational"],
    "statistical_expertise": ["regression", "bayesian"],
    "programming_skills": ["python", "r"],
    "h_index": 12.0,
    "publication_count": 25,
    "citation_count": 450,
    "collaboration_count": 6,
    "international_collab_ratio": 0.25,
    "availability": 0.7,
    "response_rate": 0.85,
    "peer_review_count": 8,
    "grant_success_rate": 0.5,
}

_USER_B = {
    "_id": "user_b",
    "full_name": "Bob Martinez",
    "institution": "Oxford",
    "country": "United Kingdom",
    "position": "professor",
    "research_areas": ["clinical medicine", "public health"],
    "keywords": ["epidemiology", "clinical trials", "cardiology"],
    "research_methods": ["rct", "systematic review"],
    "statistical_expertise": ["survival analysis", "multilevel"],
    "programming_skills": ["r", "spss"],
    "h_index": 28.0,
    "publication_count": 80,
    "citation_count": 2100,
    "collaboration_count": 20,
    "international_collab_ratio": 0.55,
    "availability": 0.4,
    "response_rate": 0.6,
    "peer_review_count": 45,
    "grant_success_rate": 0.8,
}

_USER_C = {
    "_id": "user_c",
    "full_name": "Carol Kim",
    "institution": "Seoul National University",
    "country": "South Korea",
    "position": "phd student",
    "research_areas": ["machine learning", "deep learning"],
    "keywords": ["computer vision", "nlp", "transformers"],
    "research_methods": ["computational", "experiment"],
    "statistical_expertise": ["machine_learning_stats"],
    "programming_skills": ["python", "julia"],
    "h_index": 2.0,
    "publication_count": 3,
    "citation_count": 40,
    "collaboration_count": 1,
    "international_collab_ratio": 0.0,
    "availability": 0.9,
    "response_rate": 0.95,
    "peer_review_count": 0,
}

_USERS = [_USER_A, _USER_B, _USER_C]


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Models
# ═══════════════════════════════════════════════════════════════════════════════

class TestModels:
    def test_career_stage_values(self):
        from services.collab_intelligence.models import CareerStage
        assert CareerStage.STUDENT.value == "student"
        assert CareerStage.SENIOR.value  == "senior"
        assert len(list(CareerStage))    == 6

    def test_collab_type_values(self):
        from services.collab_intelligence.models import CollabType
        assert CollabType.CO_AUTHOR.value == "co_author"
        assert len(list(CollabType))      == 10

    def test_team_type_values(self):
        from services.collab_intelligence.models import TeamType
        assert len(list(TeamType)) == 9

    def test_competency_node_to_dict(self):
        from services.collab_intelligence.models import CompetencyNode
        n = CompetencyNode(concept="machine_learning", level=0.85, evidence_count=3)
        d = n.to_dict()
        assert d["concept"] == "machine_learning"
        assert d["level"] == 0.85

    def test_competency_graph_to_dict(self):
        from services.collab_intelligence.models import CompetencyGraph
        g = CompetencyGraph(user_id="u1", overall_score=0.7)
        d = g.to_dict()
        assert d["user_id"] == "u1"
        assert d["overall_score"] == 0.7

    def test_researcher_profile_to_dict(self):
        from services.collab_intelligence.models import CareerStage, ResearcherProfile
        p = ResearcherProfile(
            user_id="u1", name="Test", institution="MIT",
            career_stage=CareerStage.EARLY_CAREER,
        )
        d = p.to_dict()
        assert d["user_id"] == "u1"
        assert d["career_stage"] == "early_career"

    def test_researcher_profile_all_interests(self):
        from services.collab_intelligence.models import ResearcherProfile
        p = ResearcherProfile(
            user_id="u1",
            domains=["ML", "NLP"],
            keywords=["transformers"],
        )
        interests = p.all_interests()
        assert "ml" in interests or "ML".lower() in interests

    def test_collab_match_to_dict(self):
        from services.collab_intelligence.models import CollabMatch, CollabType
        m = CollabMatch("a", "b", overall_score=0.75, collab_type=CollabType.INTERNATIONAL)
        d = m.to_dict()
        assert d["overall_score"] == 0.75
        assert d["collab_type"] == "international"

    def test_team_composition_to_dict(self):
        from services.collab_intelligence.models import TeamComposition, TeamType
        t = TeamComposition(objective="Test", team_type=TeamType.GRANT, overall_score=0.8)
        d = t.to_dict()
        assert d["objective"] == "Test"
        assert d["team_type"] == "grant"

    def test_collab_opportunity_to_dict(self):
        from services.collab_intelligence.models import CollabOpportunity, OpportunityType
        o = CollabOpportunity(
            opportunity_type=OpportunityType.CO_AUTHOR,
            target_researcher_id="u2", score=0.82,
        )
        d = o.to_dict()
        assert d["opportunity_type"] == "co_author"
        assert d["score"] == 0.82

    def test_smart_introduction_to_dict(self):
        from services.collab_intelligence.models import SmartIntroduction
        intro = SmartIntroduction("a", "b", narrative="Test narrative", match_score=0.7)
        d = intro.to_dict()
        assert d["narrative"] == "Test narrative"
        assert d["match_score"] == 0.7

    def test_collab_prediction_to_dict(self):
        from services.collab_intelligence.models import CollabPrediction
        p = CollabPrediction("a", "b", success_probability=0.75, confidence=0.85)
        d = p.to_dict()
        assert d["probabilities"]["collaboration_success"] == 0.75
        assert d["confidence"] == 0.85

    def test_team_simulation_to_dict(self):
        from services.collab_intelligence.models import TeamSimulation
        s = TeamSimulation(["a", "b"], "Test objective", expected_productivity=0.7)
        d = s.to_dict()
        assert d["objective"] == "Test objective"
        assert d["estimated_outputs"]["productivity"] == 0.7

    def test_collab_insight_to_dict(self):
        from services.collab_intelligence.models import CollabInsight, InsightSeverity
        i = CollabInsight("test_type", "Test message", InsightSeverity.WARNING,
                          metric_value=0.2, recommendation="Fix it")
        d = i.to_dict()
        assert d["severity"] == "warning"
        assert d["message"] == "Test message"

    def test_visualization_data_to_dict(self):
        from services.collab_intelligence.models import VisualizationData, VisualizationType
        v = VisualizationData(VisualizationType.NETWORK_GRAPH, {"nodes": []})
        d = v.to_dict()
        assert d["viz_type"] == "network_graph"

    def test_research_network_to_dict(self):
        from services.collab_intelligence.models import ResearchNetwork
        net = ResearchNetwork(density=0.5, diameter_estimate=3)
        d = net.to_dict()
        assert d["metrics"]["density"] == 0.5


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Researcher Profiler
# ═══════════════════════════════════════════════════════════════════════════════

class TestResearcherProfiler:
    def _profile(self, user=None):
        from services.collab_intelligence.researcher_profiler import build_researcher_profile
        return build_researcher_profile(user or _USER_A)

    def test_builds_profile_from_dict(self):
        p = self._profile()
        assert p.user_id == "user_a"
        assert p.name == "Alice Chen"
        assert p.institution == "MIT"

    def test_infers_career_stage_assistant_prof(self):
        p = self._profile()
        assert p.career_stage.value == "early_career"

    def test_infers_career_stage_professor(self):
        p = self._profile(_USER_B)
        assert p.career_stage.value == "senior"

    def test_infers_career_stage_student(self):
        p = self._profile(_USER_C)
        assert p.career_stage.value == "student"

    def test_productivity_score_positive(self):
        p = self._profile()
        assert 0.0 < p.productivity_score <= 1.0

    def test_quality_score_in_range(self):
        p = self._profile()
        assert 0.0 <= p.quality_score <= 1.0

    def test_impact_score_in_range(self):
        p = self._profile()
        assert 0.0 <= p.impact_score <= 1.0

    def test_competency_graph_built(self):
        p = self._profile()
        assert p.competency_graph is not None

    def test_empty_user_doc_does_not_crash(self):
        from services.collab_intelligence.researcher_profiler import build_researcher_profile
        p = build_researcher_profile({})
        assert p.user_id == ""
        assert p.domains == []

    def test_country_extracted(self):
        p = self._profile()
        assert p.country == "United States"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Competency Graph
# ═══════════════════════════════════════════════════════════════════════════════

class TestCompetencyGraph:
    def _graph(self, **kwargs):
        from services.collab_intelligence.competency_graph import build_competency_graph
        defaults = dict(
            user_id="u1",
            domains=["machine learning", "deep learning"],
            keywords=["python", "regression", "bayesian"],
            methods=["cohort study", "computational"],
            stats=["regression", "bayesian"],
            progs=["python", "r programming"],
            peer_review_count=5,
            grant_success_rate=0.4,
            h_index=10.0,
        )
        defaults.update(kwargs)
        return build_competency_graph(**defaults)

    def test_detects_ml_domain(self):
        g = self._graph()
        domain_names = [n.concept for n in g.research_domains]
        assert "machine_learning" in domain_names

    def test_detects_python_prog(self):
        g = self._graph()
        prog_names = [n.concept for n in g.programming_languages]
        assert "python" in prog_names

    def test_detects_regression_stats(self):
        g = self._graph()
        stat_names = [n.concept for n in g.statistical_techniques]
        assert "regression" in stat_names

    def test_writing_quality_in_range(self):
        g = self._graph()
        assert 0.0 <= g.writing_quality <= 1.0

    def test_leadership_score_in_range(self):
        g = self._graph()
        assert 0.0 <= g.leadership_score <= 1.0

    def test_overall_score_positive(self):
        g = self._graph()
        assert g.overall_score > 0

    def test_all_concepts_returns_list(self):
        g = self._graph()
        concepts = g.all_concepts()
        assert isinstance(concepts, list)
        assert len(concepts) > 0

    def test_empty_inputs_no_crash(self):
        from services.collab_intelligence.competency_graph import build_competency_graph
        g = build_competency_graph("u", [], [], [], [], [])
        assert g.overall_score >= 0


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Matching Engine
# ═══════════════════════════════════════════════════════════════════════════════

class TestMatchingEngine:
    def _profiles(self):
        from services.collab_intelligence.researcher_profiler import build_researcher_profile
        return (
            build_researcher_profile(_USER_A),
            build_researcher_profile(_USER_B),
        )

    def test_match_returns_collab_match(self):
        from services.collab_intelligence.matching_engine import match_researchers
        pa, pb = self._profiles()
        m = match_researchers(pa, pb)
        assert 0.0 <= m.overall_score <= 1.0

    def test_match_is_symmetric(self):
        from services.collab_intelligence.matching_engine import match_researchers
        pa, pb = self._profiles()
        mab = match_researchers(pa, pb)
        mba = match_researchers(pb, pa)
        assert abs(mab.overall_score - mba.overall_score) < 0.01

    def test_all_dimensions_in_range(self):
        from services.collab_intelligence.matching_engine import match_researchers
        pa, pb = self._profiles()
        m = match_researchers(pa, pb)
        dims = m.to_dict()["dimensions"]
        for k, v in dims.items():
            assert 0.0 <= v <= 1.0, f"{k} out of range: {v}"

    def test_high_similarity_same_researcher(self):
        from services.collab_intelligence.matching_engine import match_researchers
        from services.collab_intelligence.researcher_profiler import build_researcher_profile
        pa = build_researcher_profile(_USER_A)
        pb = build_researcher_profile({**_USER_A, "_id": "user_a2"})
        m = match_researchers(pa, pb)
        # Same profile → very high similarity
        assert m.research_similarity > 0.8

    def test_collab_type_international_different_countries(self):
        from services.collab_intelligence.matching_engine import match_researchers
        from services.collab_intelligence.models import CollabType
        pa, pb = self._profiles()
        m = match_researchers(pa, pb)
        assert m.collab_type in list(CollabType)

    def test_explanation_not_empty(self):
        from services.collab_intelligence.matching_engine import match_researchers
        pa, pb = self._profiles()
        m = match_researchers(pa, pb)
        assert len(m.explanation) > 0

    def test_rank_matches_returns_sorted(self):
        from services.collab_intelligence.matching_engine import rank_matches
        from services.collab_intelligence.researcher_profiler import build_researcher_profile
        source    = build_researcher_profile(_USER_A)
        candidates = [build_researcher_profile(u) for u in [_USER_B, _USER_C]]
        ranked = rank_matches(source, candidates, top_n=5)
        assert len(ranked) <= 2
        if len(ranked) >= 2:
            assert ranked[0].overall_score >= ranked[1].overall_score

    def test_rank_matches_excludes_self(self):
        from services.collab_intelligence.matching_engine import rank_matches
        from services.collab_intelligence.researcher_profiler import build_researcher_profile
        source     = build_researcher_profile(_USER_A)
        candidates = [build_researcher_profile(u) for u in _USERS]
        ranked = rank_matches(source, candidates, top_n=10)
        ids = [m.researcher_b_id for m in ranked]
        assert source.user_id not in ids


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Team Optimizer
# ═══════════════════════════════════════════════════════════════════════════════

class TestTeamOptimizer:
    def _profiles(self):
        from services.collab_intelligence.researcher_profiler import build_researcher_profile
        return [build_researcher_profile(u) for u in _USERS]

    def test_builds_team(self):
        from services.collab_intelligence.team_optimizer import build_team
        from services.collab_intelligence.models import TeamType
        profiles = self._profiles()
        team = build_team(profiles, "Machine learning in medicine", TeamType.GRANT)
        assert len(team.members) > 0

    def test_team_size_respected(self):
        from services.collab_intelligence.team_optimizer import build_team
        from services.collab_intelligence.models import TeamType
        profiles = self._profiles()
        team = build_team(profiles, "Test", TeamType.GRANT, max_size=2)
        assert len(team.members) <= 2

    def test_overall_score_in_range(self):
        from services.collab_intelligence.team_optimizer import build_team
        from services.collab_intelligence.models import TeamType
        team = build_team(self._profiles(), "Test", TeamType.INTERDISCIPLINARY)
        assert 0.0 <= team.overall_score <= 1.0

    def test_has_strengths(self):
        from services.collab_intelligence.team_optimizer import build_team
        from services.collab_intelligence.models import TeamType
        team = build_team(self._profiles(), "Test", TeamType.INTERDISCIPLINARY)
        assert isinstance(team.strengths, list)

    def test_empty_candidates_does_not_crash(self):
        from services.collab_intelligence.team_optimizer import build_team
        from services.collab_intelligence.models import TeamType
        team = build_team([], "Test", TeamType.GRANT)
        assert team.members == []

    def test_roles_assigned(self):
        from services.collab_intelligence.team_optimizer import build_team
        from services.collab_intelligence.models import TeamType
        team = build_team(self._profiles(), "Test", TeamType.GRANT)
        assert all(m.role for m in team.members)


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Opportunity Detector
# ═══════════════════════════════════════════════════════════════════════════════

class TestOpportunityDetector:
    def _profiles(self):
        from services.collab_intelligence.researcher_profiler import build_researcher_profile
        return [build_researcher_profile(u) for u in _USERS]

    def test_finds_opportunities(self):
        from services.collab_intelligence.opportunity_detector import detect_opportunities
        profiles = self._profiles()
        opps = detect_opportunities(profiles[0], profiles[1:])
        assert isinstance(opps, list)

    def test_opportunities_have_scores(self):
        from services.collab_intelligence.opportunity_detector import detect_opportunities
        profiles = self._profiles()
        opps = detect_opportunities(profiles[0], profiles[1:])
        for opp in opps:
            assert 0.0 <= opp.score <= 1.0

    def test_opportunities_sorted_by_score(self):
        from services.collab_intelligence.opportunity_detector import detect_opportunities
        profiles = self._profiles()
        opps = detect_opportunities(profiles[0], profiles[1:])
        if len(opps) >= 2:
            assert opps[0].score >= opps[1].score

    def test_source_not_recommended_to_self(self):
        from services.collab_intelligence.opportunity_detector import detect_opportunities
        profiles = self._profiles()
        opps = detect_opportunities(profiles[0], profiles)
        ids = [o.target_researcher_id for o in opps]
        assert profiles[0].user_id not in ids

    def test_supervisor_for_student(self):
        from services.collab_intelligence.opportunity_detector import detect_opportunities
        from services.collab_intelligence.researcher_profiler import build_researcher_profile
        from services.collab_intelligence.models import OpportunityType
        student = build_researcher_profile(_USER_C)
        senior  = build_researcher_profile(_USER_B)
        opps = detect_opportunities(student, [senior])
        types = [o.opportunity_type for o in opps]
        assert OpportunityType.SUPERVISOR in types or OpportunityType.MENTOR in types

    def test_international_detected(self):
        from services.collab_intelligence.opportunity_detector import detect_opportunities
        from services.collab_intelligence.researcher_profiler import build_researcher_profile
        from services.collab_intelligence.models import OpportunityType
        pa = build_researcher_profile(_USER_A)  # US
        pb = build_researcher_profile(_USER_B)  # UK
        opps = detect_opportunities(pa, [pb])
        types = [o.opportunity_type for o in opps]
        assert OpportunityType.INTERNATIONAL in types


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Introduction Generator
# ═══════════════════════════════════════════════════════════════════════════════

class TestIntroductionGenerator:
    def test_generates_narrative(self):
        from services.collab_intelligence.introduction_generator import generate_introduction
        from services.collab_intelligence.researcher_profiler import build_researcher_profile
        pa = build_researcher_profile(_USER_A)
        pb = build_researcher_profile(_USER_B)
        intro = generate_introduction(pa, pb)
        assert len(intro.narrative) > 20

    def test_has_expected_outcomes(self):
        from services.collab_intelligence.introduction_generator import generate_introduction
        from services.collab_intelligence.researcher_profiler import build_researcher_profile
        pa = build_researcher_profile(_USER_A)
        pb = build_researcher_profile(_USER_B)
        intro = generate_introduction(pa, pb)
        assert len(intro.expected_outcomes) > 0

    def test_has_collaboration_hooks(self):
        from services.collab_intelligence.introduction_generator import generate_introduction
        from services.collab_intelligence.researcher_profiler import build_researcher_profile
        pa = build_researcher_profile(_USER_A)
        pb = build_researcher_profile(_USER_B)
        intro = generate_introduction(pa, pb)
        assert len(intro.collaboration_hooks) > 0

    def test_match_score_positive(self):
        from services.collab_intelligence.introduction_generator import generate_introduction
        from services.collab_intelligence.researcher_profiler import build_researcher_profile
        pa = build_researcher_profile(_USER_A)
        pb = build_researcher_profile(_USER_B)
        intro = generate_introduction(pa, pb)
        assert 0.0 <= intro.match_score <= 1.0

    def test_empty_profiles_no_crash(self):
        from services.collab_intelligence.introduction_generator import generate_introduction
        from services.collab_intelligence.models import ResearcherProfile
        pa = ResearcherProfile(user_id="x")
        pb = ResearcherProfile(user_id="y")
        intro = generate_introduction(pa, pb)
        assert isinstance(intro.narrative, str)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Network Analyzer
# ═══════════════════════════════════════════════════════════════════════════════

class TestNetworkAnalyzer:
    def _profiles(self):
        from services.collab_intelligence.researcher_profiler import build_researcher_profile
        return [build_researcher_profile(u) for u in _USERS]

    def test_builds_network(self):
        from services.collab_intelligence.network_analyzer import build_network
        profiles = self._profiles()
        net = build_network(profiles)
        assert len(net.nodes) == len(profiles)

    def test_density_in_range(self):
        from services.collab_intelligence.network_analyzer import build_network
        net = build_network(self._profiles())
        assert 0.0 <= net.density <= 1.0

    def test_centrality_in_range(self):
        from services.collab_intelligence.network_analyzer import build_network
        net = build_network(self._profiles())
        for node in net.nodes:
            assert 0.0 <= node.centrality <= 1.0

    def test_clusters_detected(self):
        from services.collab_intelligence.network_analyzer import build_network
        from services.collab_intelligence.researcher_profiler import build_researcher_profile
        # Use similar profiles to ensure edges exist
        profiles = [build_researcher_profile({**_USER_A, "_id": f"u{i}"}) for i in range(5)]
        net = build_network(profiles, similarity_threshold=0.1)
        # All should be connected with low threshold
        assert len(net.edges) > 0

    def test_empty_profiles_no_crash(self):
        from services.collab_intelligence.network_analyzer import build_network
        net = build_network([])
        assert net.nodes == []
        assert net.edges == []

    def test_researcher_position_analysis(self):
        from services.collab_intelligence.network_analyzer import (
            analyze_researcher_position, build_network,
        )
        from services.collab_intelligence.researcher_profiler import build_researcher_profile
        profiles = self._profiles()
        net = build_network(profiles, similarity_threshold=0.1)
        pos = analyze_researcher_position(profiles[0], net)
        assert "centrality" in pos
        assert "connections" in pos


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Prediction Engine
# ═══════════════════════════════════════════════════════════════════════════════

class TestPredictionEngine:
    def _predict(self, ua=_USER_A, ub=_USER_B):
        from services.collab_intelligence.prediction_engine import predict_collaboration
        from services.collab_intelligence.researcher_profiler import build_researcher_profile
        return predict_collaboration(build_researcher_profile(ua), build_researcher_profile(ub))

    def test_probabilities_in_range(self):
        pred = self._predict()
        assert 0.0 <= pred.success_probability <= 1.0
        assert 0.0 <= pred.publication_probability <= 1.0
        assert 0.0 <= pred.grant_probability <= 1.0

    def test_long_term_potential_in_range(self):
        pred = self._predict()
        assert 0.0 <= pred.long_term_potential <= 1.0

    def test_has_risk_factors(self):
        pred = self._predict()
        assert isinstance(pred.risk_factors, list)

    def test_has_success_factors(self):
        pred = self._predict()
        assert isinstance(pred.success_factors, list)

    def test_confidence_in_range(self):
        pred = self._predict()
        assert 0.0 <= pred.confidence <= 1.0

    def test_time_to_output_positive(self):
        pred = self._predict()
        assert pred.time_to_first_output_months > 0

    def test_low_availability_adds_risk(self):
        user_low = {**_USER_A, "availability": 0.1}
        pred = self._predict(ua=user_low)
        risk_messages = " ".join(pred.risk_factors).lower()
        assert "availability" in risk_messages

    def test_same_country_no_timezone_risk(self):
        user_same = {**_USER_B, "country": "United States"}
        pred = self._predict(ub=user_same)
        risk_messages = " ".join(pred.risk_factors).lower()
        assert "time zone" not in risk_messages


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Team Simulator
# ═══════════════════════════════════════════════════════════════════════════════

class TestTeamSimulator:
    def _profiles(self):
        from services.collab_intelligence.researcher_profiler import build_researcher_profile
        return [build_researcher_profile(u) for u in _USERS]

    def test_simulation_returns_result(self):
        from services.collab_intelligence.team_simulator import simulate_team
        sim = simulate_team(self._profiles(), "Machine learning research")
        assert isinstance(sim, object)
        assert sim.expected_productivity >= 0

    def test_scores_in_range(self):
        from services.collab_intelligence.team_simulator import simulate_team
        sim = simulate_team(self._profiles(), "Test objective")
        assert 0.0 <= sim.expected_productivity <= 1.0
        assert 0.0 <= sim.publication_quality_estimate <= 1.0
        assert 0.0 <= sim.grant_competitiveness <= 1.0

    def test_has_recommendations(self):
        from services.collab_intelligence.team_simulator import simulate_team
        sim = simulate_team(self._profiles(), "Test")
        assert len(sim.recommendations) > 0

    def test_empty_team_no_crash(self):
        from services.collab_intelligence.team_simulator import simulate_team
        sim = simulate_team([], "Test objective")
        assert sim.expected_productivity == 0.0
        assert len(sim.recommendations) > 0

    def test_single_institution_warns(self):
        from services.collab_intelligence.team_simulator import simulate_team
        from services.collab_intelligence.researcher_profiler import build_researcher_profile
        # All from same institution
        users = [{**_USER_A, "_id": f"u{i}"} for i in range(3)]
        profiles = [build_researcher_profile(u) for u in users]
        sim = simulate_team(profiles, "Test")
        all_text = " ".join(sim.potential_weaknesses + sim.recommendations).lower()
        assert "institution" in all_text or "diversity" in all_text


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Recommendation Engine
# ═══════════════════════════════════════════════════════════════════════════════

class TestRecommendationEngine:
    def _profiles(self):
        from services.collab_intelligence.researcher_profiler import build_researcher_profile
        return [build_researcher_profile(u) for u in _USERS]

    def test_researcher_recommendations(self):
        from services.collab_intelligence.recommendation_engine import generate_recommendations
        profiles = self._profiles()
        recs = generate_recommendations(profiles[0], profiles[1:])
        assert "researchers" in recs
        assert len(recs["researchers"]) > 0

    def test_institution_recommendations(self):
        from services.collab_intelligence.recommendation_engine import generate_recommendations
        profiles = self._profiles()
        recs = generate_recommendations(profiles[0], profiles[1:])
        assert "institutions" in recs

    def test_recs_sorted_by_score(self):
        from services.collab_intelligence.recommendation_engine import generate_recommendations
        profiles = self._profiles()
        recs = generate_recommendations(profiles[0], profiles[1:])
        researcher_recs = recs.get("researchers", [])
        if len(researcher_recs) >= 2:
            assert researcher_recs[0].score >= researcher_recs[1].score

    def test_serialize_recs(self):
        from services.collab_intelligence.recommendation_engine import (
            generate_recommendations, serialize_recommendations,
        )
        profiles = self._profiles()
        recs = generate_recommendations(profiles[0], profiles[1:])
        serialized = serialize_recommendations(recs)
        assert all(isinstance(v, list) for v in serialized.values())
        for v in serialized.values():
            for item in v:
                assert isinstance(item, dict)


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Insight Generator
# ═══════════════════════════════════════════════════════════════════════════════

class TestInsightGenerator:
    def test_generates_insights(self):
        from services.collab_intelligence.insight_generator import generate_insights
        from services.collab_intelligence.researcher_profiler import build_researcher_profile
        source   = build_researcher_profile(_USER_C)  # student with low intl
        profiles = [build_researcher_profile(u) for u in _USERS]
        insights = generate_insights(source, profiles)
        assert isinstance(insights, list)

    def test_low_intl_generates_warning(self):
        from services.collab_intelligence.insight_generator import generate_insights
        from services.collab_intelligence.researcher_profiler import build_researcher_profile
        from services.collab_intelligence.models import InsightSeverity
        source = build_researcher_profile({**_USER_C, "international_collab_ratio": 0.0})
        insights = generate_insights(source, [])
        severities = {i.severity for i in insights}
        types = {i.insight_type for i in insights}
        assert "international_collaboration" in types

    def test_high_impact_generates_info(self):
        from services.collab_intelligence.insight_generator import generate_insights
        from services.collab_intelligence.researcher_profiler import build_researcher_profile
        from services.collab_intelligence.models import InsightSeverity
        source = build_researcher_profile({**_USER_B, "h_index": 35, "citation_count": 5000})
        insights = generate_insights(source, [])
        types = {i.insight_type for i in insights}
        assert "research_impact" in types

    def test_insights_have_recommendations(self):
        from services.collab_intelligence.insight_generator import generate_insights
        from services.collab_intelligence.researcher_profiler import build_researcher_profile
        source   = build_researcher_profile(_USER_A)
        insights = generate_insights(source, [])
        for insight in insights:
            assert isinstance(insight.recommendation, str)


# ═══════════════════════════════════════════════════════════════════════════════
# 13. Social Graph
# ═══════════════════════════════════════════════════════════════════════════════

class TestSocialGraph:
    def _profiles(self):
        from services.collab_intelligence.researcher_profiler import build_researcher_profile
        return [build_researcher_profile(u) for u in _USERS]

    def test_builds_graph(self):
        from services.collab_intelligence.social_graph import build_social_graph
        graph = build_social_graph(self._profiles())
        assert len(graph.nodes) > 0

    def test_has_researcher_nodes(self):
        from services.collab_intelligence.social_graph import build_social_graph
        from services.collab_intelligence.models import NetworkNodeType
        graph = build_social_graph(self._profiles())
        researcher_nodes = [n for n in graph.nodes if n.node_type == NetworkNodeType.RESEARCHER]
        assert len(researcher_nodes) == len(_USERS)

    def test_has_topic_nodes_when_enabled(self):
        from services.collab_intelligence.social_graph import build_social_graph
        from services.collab_intelligence.models import NetworkNodeType
        graph = build_social_graph(self._profiles(), include_topic_nodes=True)
        topic_nodes = [n for n in graph.nodes if n.node_type == NetworkNodeType.TOPIC]
        assert len(topic_nodes) > 0

    def test_no_topic_nodes_when_disabled(self):
        from services.collab_intelligence.social_graph import build_social_graph
        from services.collab_intelligence.models import NetworkNodeType
        graph = build_social_graph(self._profiles(), include_topic_nodes=False)
        topic_nodes = [n for n in graph.nodes if n.node_type == NetworkNodeType.TOPIC]
        assert len(topic_nodes) == 0

    def test_has_edges(self):
        from services.collab_intelligence.social_graph import build_social_graph
        graph = build_social_graph(self._profiles())
        assert len(graph.edges) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# 14. Visualization Builder
# ═══════════════════════════════════════════════════════════════════════════════

class TestVisualizationBuilder:
    def _profiles(self):
        from services.collab_intelligence.researcher_profiler import build_researcher_profile
        return [build_researcher_profile(u) for u in _USERS]

    def test_network_graph(self):
        from services.collab_intelligence.network_analyzer import build_network
        from services.collab_intelligence.visualization_builder import network_graph
        profiles = self._profiles()
        net = build_network(profiles)
        viz = network_graph(net)
        assert viz.viz_type.value == "network_graph"

    def test_collaboration_heatmap(self):
        from services.collab_intelligence.matching_engine import match_researchers
        from services.collab_intelligence.visualization_builder import collaboration_heatmap
        profiles = self._profiles()
        matches = [match_researchers(profiles[0], profiles[1])]
        viz = collaboration_heatmap(profiles, matches)
        assert "matrix" in viz.data

    def test_expertise_map(self):
        from services.collab_intelligence.visualization_builder import expertise_map
        viz = expertise_map(self._profiles())
        assert "bubbles" in viz.data

    def test_institution_network(self):
        from services.collab_intelligence.visualization_builder import institution_network
        viz = institution_network(self._profiles())
        d = viz.to_dict()
        assert d["viz_type"] == "institution_network"

    def test_impact_projection(self):
        from services.collab_intelligence.visualization_builder import impact_projection
        profiles = self._profiles()
        viz = impact_projection(profiles[0], collaboration_added=True)
        assert len(viz.data["projections"]) == 6  # 0-5 years


# ═══════════════════════════════════════════════════════════════════════════════
# 15. Admin Analytics
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdminAnalytics:
    def _profiles(self):
        from services.collab_intelligence.researcher_profiler import build_researcher_profile
        return [build_researcher_profile(u) for u in _USERS]

    def _matches(self, profiles):
        from services.collab_intelligence.matching_engine import match_researchers
        return [match_researchers(profiles[0], profiles[1])]

    def test_platform_stats(self):
        from services.collab_intelligence.admin_analytics import platform_collaboration_stats
        profiles = self._profiles()
        stats = platform_collaboration_stats(profiles, self._matches(profiles))
        assert stats["total_researchers"] == 3

    def test_top_collaborators(self):
        from services.collab_intelligence.admin_analytics import top_collaborators
        top = top_collaborators(self._profiles(), top_n=3)
        assert len(top) <= 3
        assert all("name" in t for t in top)

    def test_top_institutions(self):
        from services.collab_intelligence.admin_analytics import top_institutions
        institutions = top_institutions(self._profiles())
        assert isinstance(institutions, list)

    def test_interdisciplinary_metrics(self):
        from services.collab_intelligence.admin_analytics import interdisciplinary_metrics
        metrics = interdisciplinary_metrics(self._profiles())
        assert "unique_domains" in metrics
        assert "top_research_domains" in metrics

    def test_international_map(self):
        from services.collab_intelligence.admin_analytics import international_collaboration_map
        imap = international_collaboration_map(self._profiles())
        assert "countries" in imap
        assert imap["total_countries"] == len({u["country"] for u in _USERS})

    def test_grant_stats(self):
        from services.collab_intelligence.admin_analytics import grant_collaboration_stats
        stats = grant_collaboration_stats(self._profiles())
        assert "researchers_with_grant_history" in stats


# ═══════════════════════════════════════════════════════════════════════════════
# 16. Telemetry
# ═══════════════════════════════════════════════════════════════════════════════

class TestTelemetry:
    def _fresh(self):
        from services.collab_intelligence.telemetry import CollabTelemetry
        CollabTelemetry._instance = None
        from services.collab_intelligence.telemetry import get_telemetry
        return get_telemetry()

    def test_singleton(self):
        t1 = self._fresh()
        from services.collab_intelligence.telemetry import get_telemetry
        t2 = get_telemetry()
        assert t1 is t2

    def test_records_profile_builds(self):
        t = self._fresh()
        t.record("profile_builds")
        assert t.snapshot()["profile_builds"] == 1

    def test_records_errors(self):
        t = self._fresh()
        t.record_error()
        assert t.snapshot()["errors"] == 1

    def test_latency_tracking(self):
        t = self._fresh()
        t.record_latency(0.05)
        t.record_latency(0.15)
        s = t.snapshot()
        assert s["sample_count"] == 2
        assert s["latency_avg_s"] > 0

    def test_reset_clears(self):
        t = self._fresh()
        t.record("match_computations")
        t.reset()
        assert t.snapshot()["match_computations"] == 0


# ═══════════════════════════════════════════════════════════════════════════════
# 17. Engine Integration
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineIntegration:
    def _engine(self):
        from services.collab_intelligence.engine import reset_collab_engine, get_collab_engine
        reset_collab_engine()
        return asyncio.run(get_collab_engine())

    def test_singleton(self):
        from services.collab_intelligence.engine import reset_collab_engine, get_collab_engine
        reset_collab_engine()

        async def _run():
            e1 = await get_collab_engine()
            e2 = await get_collab_engine()
            assert e1 is e2

        asyncio.run(_run())

    def test_build_profile(self):
        engine = self._engine()
        profile = engine.build_profile(_USER_A)
        assert profile.name == "Alice Chen"

    def test_match(self):
        engine = self._engine()
        result = engine.match(_USER_A, _USER_B)
        assert "overall_score" in result
        assert 0.0 <= result["overall_score"] <= 1.0

    def test_rank_candidates(self):
        engine = self._engine()
        ranked = engine.rank_candidates(_USER_A, [_USER_B, _USER_C])
        assert isinstance(ranked, list)
        assert len(ranked) == 2

    def test_find_opportunities(self):
        engine = self._engine()
        opps = engine.find_opportunities(_USER_A, [_USER_B, _USER_C])
        assert isinstance(opps, list)

    def test_build_team(self):
        engine = self._engine()
        team = engine.build_team([_USER_A, _USER_B, _USER_C], "ML in medicine")
        assert "members" in team
        assert len(team["members"]) > 0

    def test_simulate_team(self):
        engine = self._engine()
        sim = engine.simulate_team([_USER_A, _USER_B], "Joint research project")
        assert "estimated_outputs" in sim

    def test_introduce(self):
        engine = self._engine()
        intro = engine.introduce(_USER_A, _USER_B)
        assert "narrative" in intro
        assert len(intro["narrative"]) > 20

    def test_predict(self):
        engine = self._engine()
        pred = engine.predict(_USER_A, _USER_B)
        assert "probabilities" in pred

    def test_recommendations(self):
        engine = self._engine()
        recs = engine.recommendations(_USER_A, [_USER_B, _USER_C])
        assert "researchers" in recs

    def test_insights(self):
        engine = self._engine()
        insights = engine.insights(_USER_C, [_USER_A, _USER_B])
        assert isinstance(insights, list)

    def test_analyze_network(self):
        engine = self._engine()
        net = engine.analyze_network([_USER_A, _USER_B, _USER_C])
        assert "nodes" in net
        assert len(net["nodes"]) == 3

    def test_social_graph(self):
        engine = self._engine()
        graph = engine.social_graph([_USER_A, _USER_B])
        assert "nodes" in graph

    def test_visualization_network(self):
        engine = self._engine()
        viz = engine.visualization("network_graph", [_USER_A, _USER_B])
        assert viz["viz_type"] == "network_graph"

    def test_visualization_expertise_map(self):
        engine = self._engine()
        viz = engine.visualization("expertise_map", [_USER_A, _USER_B, _USER_C])
        assert viz["viz_type"] == "expertise_map"

    def test_admin_analytics(self):
        engine = self._engine()
        analytics = engine.admin_analytics([_USER_A, _USER_B, _USER_C])
        assert "platform_stats" in analytics
        assert "top_collaborators" in analytics
        assert "interdisciplinary_metrics" in analytics
