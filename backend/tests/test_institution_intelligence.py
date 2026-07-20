"""Tests for Phase XV — Institution Intelligence Engine.

118 tests across 15 test classes.
"""
from __future__ import annotations

import asyncio
import pytest


# ── Shared fixtures ───────────────────────────────────────────────────────────

_R1 = {
    "_id": "r1", "full_name": "Alice Chen", "institution": "MIT",
    "country": "United States", "department": "Computer Science",
    "position": "assistant professor",
    "research_areas": ["machine learning", "artificial intelligence"],
    "h_index": 12.0, "publication_count": 28, "citation_count": 500,
    "collaboration_count": 6, "international_collab_ratio": 0.35,
    "availability": 0.7, "grant_count": 2, "grant_success_rate": 0.5,
    "publication_growth": 0.08,
}

_R2 = {
    "_id": "r2", "full_name": "Bob Martinez", "institution": "MIT",
    "country": "United Kingdom", "department": "Medicine",
    "position": "professor",
    "research_areas": ["clinical medicine", "public health", "epidemiology"],
    "h_index": 28.0, "publication_count": 80, "citation_count": 2100,
    "collaboration_count": 20, "international_collab_ratio": 0.55,
    "availability": 0.4, "grant_count": 5, "grant_success_rate": 0.7,
    "publication_growth": 0.05,
}

_R3 = {
    "_id": "r3", "full_name": "Carol Kim", "institution": "MIT",
    "country": "South Korea", "department": "Computer Science",
    "position": "phd student",
    "research_areas": ["deep learning", "computer vision"],
    "h_index": 2.0, "publication_count": 3, "citation_count": 30,
    "collaboration_count": 1, "international_collab_ratio": 0.0,
    "availability": 0.9, "grant_count": 0,
    "publication_growth": 0.0,
}

_G1 = {
    "_id": "g1", "title": "EU Horizon Grant", "amount": 450000.0,
    "status": "active", "department": "Computer Science",
    "funding_organization": "European Commission",
}
_G2 = {
    "_id": "g2", "title": "National Research Grant", "amount": 120000.0,
    "status": "won", "department": "Medicine",
    "funding_organization": "National Science Foundation",
}

_RESEARCHERS = [_R1, _R2, _R3]
_GRANTS = [_G1, _G2]

_INST_DATA = {
    "name": "MIT", "institution_type": "university",
    "country": "United States", "founding_year": 1861,
    "researchers": _RESEARCHERS,
    "grants": _GRANTS,
    "departments": ["Computer Science", "Medicine"],
    "total_budget": 2_000_000.0,
}


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Models
# ═══════════════════════════════════════════════════════════════════════════════

class TestModels:
    def test_institution_type_values(self):
        from services.institution_intelligence.models import InstitutionType
        assert InstitutionType.UNIVERSITY.value == "university"
        assert len(list(InstitutionType)) == 6

    def test_department_status_values(self):
        from services.institution_intelligence.models import DepartmentStatus
        assert DepartmentStatus.HIGH_PERFORMING.value == "high_performing"

    def test_risk_level_values(self):
        from services.institution_intelligence.models import RiskLevel
        assert len(list(RiskLevel)) == 5

    def test_risk_type_values(self):
        from services.institution_intelligence.models import RiskType
        assert len(list(RiskType)) == 10

    def test_forecast_type_values(self):
        from services.institution_intelligence.models import ForecastType
        assert len(list(ForecastType)) == 8

    def test_viz_type_values(self):
        from services.institution_intelligence.models import VizType
        assert len(list(VizType)) == 12

    def test_export_format_values(self):
        from services.institution_intelligence.models import ExportFormat
        assert len(list(ExportFormat)) == 4

    def test_export_report_types(self):
        from services.institution_intelligence.models import ExportReportType
        assert len(list(ExportReportType)) == 7

    def test_institution_kpis_to_dict(self):
        from services.institution_intelligence.models import InstitutionKPIs
        kpis = InstitutionKPIs(publication_output=100, avg_h_index=8.5)
        d = kpis.to_dict()
        assert d["publication_output"] == 100
        assert d["avg_h_index"] == 8.5

    def test_department_profile_to_dict(self):
        from services.institution_intelligence.models import DepartmentProfile, DepartmentStatus
        dp = DepartmentProfile(name="CS", researcher_count=5, status=DepartmentStatus.HIGH_PERFORMING)
        d = dp.to_dict()
        assert d["name"] == "CS"
        assert d["status"] == "high_performing"

    def test_institution_profile_to_dict(self):
        from services.institution_intelligence.models import InstitutionProfile, InstitutionType
        p = InstitutionProfile(institution_id="1", name="Test Uni",
                               institution_type=InstitutionType.UNIVERSITY, overall_score=0.72)
        d = p.to_dict()
        assert d["name"] == "Test Uni"
        assert d["overall_score"] == 0.72

    def test_executive_recommendation_to_dict(self):
        from services.institution_intelligence.models import (
            ExecutiveRecommendation, RecommendationAudience,
        )
        rec = ExecutiveRecommendation(
            category="funding", title="Apply for EU grants",
            audience=RecommendationAudience.RECTOR, confidence=0.8,
        )
        d = rec.to_dict()
        assert d["title"] == "Apply for EU grants"
        assert d["confidence"] == 0.8

    def test_institution_risk_to_dict(self):
        from services.institution_intelligence.models import InstitutionRisk, RiskLevel, RiskType
        r = InstitutionRisk(risk_type=RiskType.GRANT_DEPENDENCY,
                            severity=RiskLevel.HIGH, risk_score=0.65)
        d = r.to_dict()
        assert d["risk_type"] == "grant_dependency"
        assert d["severity"] == "high"

    def test_institution_forecast_to_dict(self):
        from services.institution_intelligence.models import ForecastType, InstitutionForecast
        f = InstitutionForecast(forecast_type=ForecastType.PUBLICATIONS,
                                baseline_value=100.0,
                                predicted_values=[108.0, 116.0, 125.0])
        d = f.to_dict()
        assert d["forecast_type"] == "publications"
        assert len(d["predicted_values"]) == 3

    def test_benchmark_result_to_dict(self):
        from services.institution_intelligence.models import BenchmarkResult
        b = BenchmarkResult(metric="avg_h_index", own_value=8.0, peer_avg=7.0,
                            peer_top=14.0, percentile=0.55)
        d = b.to_dict()
        assert d["metric"] == "avg_h_index"
        assert d["percentile"] == 0.55

    def test_monitoring_alert_to_dict(self):
        from services.institution_intelligence.models import AlertType, MonitoringAlert, RiskLevel
        a = MonitoringAlert(alert_type=AlertType.KPI_DECLINE,
                            severity=RiskLevel.HIGH, metric="grant_success_rate")
        d = a.to_dict()
        assert d["alert_type"] == "kpi_decline"

    def test_knowledge_graph_to_dict(self):
        from services.institution_intelligence.models import (
            InstitutionKnowledgeGraph, KnowledgeGraphEdge, KnowledgeGraphNode,
        )
        g = InstitutionKnowledgeGraph(
            nodes=[KnowledgeGraphNode("n1", "institution", "Test")],
            edges=[KnowledgeGraphEdge("n1", "n2", "has_dept")],
        )
        d = g.to_dict()
        assert d["stats"]["total_nodes"] == 1
        assert d["stats"]["total_edges"] == 1

    def test_talent_profile_to_dict(self):
        from services.institution_intelligence.models import TalentProfile
        t = TalentProfile(user_id="u1", name="John", talent_tag="future_leader", score=0.9)
        d = t.to_dict()
        assert d["talent_tag"] == "future_leader"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Institution Profiler
# ═══════════════════════════════════════════════════════════════════════════════

class TestInstitutionProfiler:
    def _inp(self, data=None):
        from services.institution_intelligence.models import InstitutionInput
        d = data or _INST_DATA
        return InstitutionInput(**{k: d.get(k, InstitutionInput.__dataclass_fields__[k].default
            if hasattr(InstitutionInput.__dataclass_fields__[k].default, '__iter__') else
            InstitutionInput.__dataclass_fields__[k].default) for k in InstitutionInput.__dataclass_fields__
            if k in d} | d)

    def test_builds_profile(self):
        from services.institution_intelligence.institution_profiler import build_institution_profile
        from services.institution_intelligence.models import InstitutionInput
        inp = InstitutionInput(**{k: _INST_DATA.get(k) for k in
                                  ["name", "institution_type", "country", "founding_year",
                                   "researchers", "grants", "departments"]
                                  if _INST_DATA.get(k) is not None})
        p = build_institution_profile(inp)
        assert p.name == "MIT"
        assert p.total_researchers == 3

    def test_aggregate_publications(self):
        from services.institution_intelligence.institution_profiler import build_institution_profile
        from services.institution_intelligence.models import InstitutionInput
        inp = InstitutionInput(researchers=_RESEARCHERS)
        p = build_institution_profile(inp)
        assert p.total_publications == sum(r["publication_count"] for r in _RESEARCHERS)

    def test_infers_institution_type(self):
        from services.institution_intelligence.institution_profiler import build_institution_profile
        from services.institution_intelligence.models import InstitutionInput, InstitutionType
        inp = InstitutionInput(institution_type="hospital", researchers=_RESEARCHERS)
        p = build_institution_profile(inp)
        assert p.institution_type == InstitutionType.HOSPITAL

    def test_top_researchers_by_h_index(self):
        from services.institution_intelligence.institution_profiler import build_institution_profile
        from services.institution_intelligence.models import InstitutionInput
        inp = InstitutionInput(researchers=_RESEARCHERS)
        p = build_institution_profile(inp)
        assert len(p.top_researchers) > 0
        assert "Bob Martinez" == p.top_researchers[0]

    def test_overall_score_in_range(self):
        from services.institution_intelligence.institution_profiler import build_institution_profile
        from services.institution_intelligence.models import InstitutionInput
        inp = InstitutionInput(researchers=_RESEARCHERS, grants=_GRANTS)
        p = build_institution_profile(inp)
        assert 0.0 <= p.overall_score <= 1.0

    def test_empty_input_does_not_crash(self):
        from services.institution_intelligence.institution_profiler import build_institution_profile
        from services.institution_intelligence.models import InstitutionInput
        p = build_institution_profile(InstitutionInput())
        assert p.total_researchers == 0

    def test_departments_built(self):
        from services.institution_intelligence.institution_profiler import build_institution_profile
        from services.institution_intelligence.models import InstitutionInput
        inp = InstitutionInput(researchers=_RESEARCHERS, grants=_GRANTS,
                               departments=["Computer Science", "Medicine"])
        p = build_institution_profile(inp)
        assert len(p.departments) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# 3. KPI Engine
# ═══════════════════════════════════════════════════════════════════════════════

class TestKPIEngine:
    def _inp(self):
        from services.institution_intelligence.models import InstitutionInput
        return InstitutionInput(researchers=_RESEARCHERS, grants=_GRANTS)

    def test_publication_output(self):
        from services.institution_intelligence.kpi_engine import compute_kpis
        kpis = compute_kpis(self._inp())
        assert kpis.publication_output == sum(r["publication_count"] for r in _RESEARCHERS)

    def test_avg_h_index_positive(self):
        from services.institution_intelligence.kpi_engine import compute_kpis
        kpis = compute_kpis(self._inp())
        expected = sum(r["h_index"] for r in _RESEARCHERS) / 3
        assert abs(kpis.avg_h_index - expected) < 0.01

    def test_grant_success_rate_in_range(self):
        from services.institution_intelligence.kpi_engine import compute_kpis
        kpis = compute_kpis(self._inp())
        assert 0.0 <= kpis.grant_success_rate <= 1.0

    def test_research_income_equals_grant_sum(self):
        from services.institution_intelligence.kpi_engine import compute_kpis
        kpis = compute_kpis(self._inp())
        assert abs(kpis.research_income - 570000.0) < 1.0

    def test_internationalization_score_in_range(self):
        from services.institution_intelligence.kpi_engine import compute_kpis
        kpis = compute_kpis(self._inp())
        assert 0.0 <= kpis.internationalization_score <= 1.0

    def test_reputation_score_in_range(self):
        from services.institution_intelligence.kpi_engine import compute_kpis
        kpis = compute_kpis(self._inp())
        assert 0.0 <= kpis.reputation_score <= 1.0

    def test_empty_input_no_crash(self):
        from services.institution_intelligence.kpi_engine import compute_kpis
        from services.institution_intelligence.models import InstitutionInput
        kpis = compute_kpis(InstitutionInput())
        assert kpis.publication_output == 0

    def test_sustainability_score_increases_with_funder_diversity(self):
        from services.institution_intelligence.kpi_engine import compute_kpis
        from services.institution_intelligence.models import InstitutionInput
        many_grants = [
            {"amount": 100000, "status": "active",
             "funding_organization": f"Funder {i}"} for i in range(6)
        ]
        kpis_many = compute_kpis(InstitutionInput(researchers=_RESEARCHERS, grants=many_grants))
        kpis_few  = compute_kpis(InstitutionInput(researchers=_RESEARCHERS, grants=_GRANTS[:1]))
        assert kpis_many.sustainability_score >= kpis_few.sustainability_score

    def test_doctoral_activity_score(self):
        from services.institution_intelligence.kpi_engine import compute_kpis
        from services.institution_intelligence.models import InstitutionInput
        kpis = compute_kpis(InstitutionInput(researchers=_RESEARCHERS))
        assert kpis.doctoral_activity_score > 0


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Organizational Intelligence
# ═══════════════════════════════════════════════════════════════════════════════

class TestOrganizationalIntelligence:
    def _inp(self):
        from services.institution_intelligence.models import InstitutionInput
        return InstitutionInput(researchers=_RESEARCHERS, grants=_GRANTS)

    def test_returns_list(self):
        from services.institution_intelligence.organizational_intelligence import (
            detect_organizational_insights,
        )
        insights = detect_organizational_insights(self._inp())
        assert isinstance(insights, list)

    def test_detects_inactive_researcher(self):
        from services.institution_intelligence.models import InstitutionInput
        from services.institution_intelligence.organizational_intelligence import (
            detect_organizational_insights,
        )
        inactive = {**_R3, "publication_count": 0}
        inp = InstitutionInput(researchers=[_R1, inactive])
        insights = detect_organizational_insights(inp)
        types = [i.insight_type for i in insights]
        assert "inactive_researcher" in types

    def test_detects_high_potential(self):
        from services.institution_intelligence.models import InstitutionInput
        from services.institution_intelligence.organizational_intelligence import (
            detect_organizational_insights,
        )
        # Low-performing peers keep the average low so the postdoc clearly outperforms
        low_peer = {"_id": "low", "publication_count": 2, "h_index": 1.0, "position": "researcher",
                    "collaboration_count": 0, "international_collab_ratio": 0.0, "availability": 0.5}
        star_postdoc = {
            "_id": "star", "full_name": "Star Postdoc", "position": "postdoc",
            "publication_count": 40, "h_index": 12.0,
            "collaboration_count": 8, "international_collab_ratio": 0.6, "availability": 0.8,
        }
        inp = InstitutionInput(researchers=[low_peer, star_postdoc])
        insights = detect_organizational_insights(inp)
        types = [i.insight_type for i in insights]
        assert "high_potential_researcher" in types

    def test_sorted_by_severity(self):
        from services.institution_intelligence.models import InstitutionInput, RiskLevel
        from services.institution_intelligence.organizational_intelligence import (
            detect_organizational_insights,
        )
        inp = InstitutionInput(researchers=_RESEARCHERS)
        insights = detect_organizational_insights(inp)
        level_order = {l: i for i, l in enumerate(RiskLevel)}
        if len(insights) >= 2:
            for a, b in zip(insights, insights[1:]):
                assert level_order.get(a.severity, 99) <= level_order.get(b.severity, 99)

    def test_detects_funding_gap(self):
        from services.institution_intelligence.models import InstitutionInput
        from services.institution_intelligence.organizational_intelligence import (
            detect_organizational_insights,
        )
        no_grant_researchers = [
            {**r, "grant_count": 0} for r in [_R1, _R2, _R3, _R3, _R3, _R3]
        ]
        inp = InstitutionInput(researchers=no_grant_researchers)
        insights = detect_organizational_insights(inp)
        types = [i.insight_type for i in insights]
        assert "funding_gap" in types


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Prediction Engine
# ═══════════════════════════════════════════════════════════════════════════════

class TestPredictionEngine:
    def _inp(self):
        from services.institution_intelligence.models import InstitutionInput
        return InstitutionInput(researchers=_RESEARCHERS, grants=_GRANTS)

    def test_returns_8_forecasts_by_default(self):
        from services.institution_intelligence.prediction_engine import predict_institution
        forecasts = predict_institution(self._inp())
        assert len(forecasts) == 8

    def test_forecasts_have_correct_horizon(self):
        from services.institution_intelligence.prediction_engine import predict_institution
        forecasts = predict_institution(self._inp(), horizon=5)
        for f in forecasts:
            assert len(f.predicted_values) == 5

    def test_ci_bounds_correct(self):
        from services.institution_intelligence.prediction_engine import predict_institution
        forecasts = predict_institution(self._inp(), horizon=3)
        for f in forecasts:
            for lo, v, hi in zip(f.ci_lower, f.predicted_values, f.ci_upper):
                assert lo <= v <= hi

    def test_publications_forecast_above_baseline(self):
        from services.institution_intelligence.models import ForecastType
        from services.institution_intelligence.prediction_engine import predict_institution
        forecasts = predict_institution(self._inp(), horizon=3)
        pub_f = next(f for f in forecasts if f.forecast_type == ForecastType.PUBLICATIONS)
        # With positive growth, year 3 > baseline
        assert pub_f.predicted_values[-1] >= pub_f.baseline_value

    def test_confidence_in_range(self):
        from services.institution_intelligence.prediction_engine import predict_institution
        forecasts = predict_institution(self._inp())
        for f in forecasts:
            assert 0.0 <= f.confidence <= 1.0

    def test_single_type_filter(self):
        from services.institution_intelligence.models import ForecastType
        from services.institution_intelligence.prediction_engine import predict_institution
        forecasts = predict_institution(self._inp(), forecast_types=[ForecastType.CITATIONS])
        assert len(forecasts) == 1
        assert forecasts[0].forecast_type == ForecastType.CITATIONS


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Risk Engine
# ═══════════════════════════════════════════════════════════════════════════════

class TestRiskEngine:
    def test_detects_isolation_risk(self):
        from services.institution_intelligence.models import InstitutionInput, RiskType
        from services.institution_intelligence.risk_engine import detect_risks
        no_intl = [{**r, "international_collab_ratio": 0.0} for r in _RESEARCHERS * 2]
        inp = InstitutionInput(researchers=no_intl)
        risks = detect_risks(inp)
        types = [r.risk_type for r in risks]
        assert RiskType.RESEARCH_ISOLATION in types

    def test_detects_grant_dependency(self):
        from services.institution_intelligence.models import InstitutionInput, RiskType
        from services.institution_intelligence.risk_engine import detect_risks
        concentrated_grants = [
            {"amount": 900000, "status": "active", "funding_organization": "Big Funder"},
            {"amount": 100000, "status": "active", "funding_organization": "Small Funder"},
        ]
        inp = InstitutionInput(researchers=_RESEARCHERS, grants=concentrated_grants)
        risks = detect_risks(inp)
        types = [r.risk_type for r in risks]
        assert RiskType.GRANT_DEPENDENCY in types

    def test_no_grants_critical_instability(self):
        from services.institution_intelligence.models import InstitutionInput, RiskLevel, RiskType
        from services.institution_intelligence.risk_engine import detect_risks
        inp = InstitutionInput(researchers=_RESEARCHERS * 2, grants=[])
        risks = detect_risks(inp)
        types = [r.risk_type for r in risks]
        assert RiskType.FUNDING_INSTABILITY in types

    def test_risk_score_in_range(self):
        from services.institution_intelligence.models import InstitutionInput
        from services.institution_intelligence.risk_engine import detect_risks
        risks = detect_risks(InstitutionInput(researchers=_RESEARCHERS, grants=_GRANTS))
        for r in risks:
            assert 0.0 <= r.risk_score <= 1.0

    def test_sorted_by_severity(self):
        from services.institution_intelligence.models import InstitutionInput, RiskLevel
        from services.institution_intelligence.risk_engine import detect_risks
        risks = detect_risks(InstitutionInput(researchers=_RESEARCHERS, grants=_GRANTS))
        level_order = {l: i for i, l in enumerate(RiskLevel)}
        if len(risks) >= 2:
            for a, b in zip(risks, risks[1:]):
                assert level_order.get(a.severity, 99) <= level_order.get(b.severity, 99)


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Decision Support
# ═══════════════════════════════════════════════════════════════════════════════

class TestDecisionSupport:
    def _inp_kpis(self):
        from services.institution_intelligence.kpi_engine import compute_kpis
        from services.institution_intelligence.models import InstitutionInput
        inp  = InstitutionInput(researchers=_RESEARCHERS, grants=_GRANTS)
        kpis = compute_kpis(inp)
        return inp, kpis

    def test_generates_recommendations(self):
        from services.institution_intelligence.decision_support import generate_recommendations
        inp, kpis = self._inp_kpis()
        recs = generate_recommendations(inp, kpis)
        assert isinstance(recs, list)

    def test_recommendations_have_all_fields(self):
        from services.institution_intelligence.decision_support import generate_recommendations
        inp, kpis = self._inp_kpis()
        recs = generate_recommendations(inp, kpis)
        for r in recs:
            d = r.to_dict()
            assert "title" in d
            assert "reasoning" in d
            assert "evidence" in d
            assert 0.0 <= d["confidence"] <= 1.0

    def test_audience_filter(self):
        from services.institution_intelligence.decision_support import generate_recommendations
        from services.institution_intelligence.models import RecommendationAudience
        inp, kpis = self._inp_kpis()
        recs = generate_recommendations(inp, kpis, audiences=[RecommendationAudience.RECTOR])
        assert all(r.audience == RecommendationAudience.RECTOR for r in recs)

    def test_priority_sorted(self):
        from services.institution_intelligence.decision_support import generate_recommendations
        inp, kpis = self._inp_kpis()
        recs = generate_recommendations(inp, kpis)
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        if len(recs) >= 2:
            for a, b in zip(recs, recs[1:]):
                assert priority_order.get(a.priority, 99) <= priority_order.get(b.priority, 99)

    def test_low_grant_success_triggers_grant_rec(self):
        from services.institution_intelligence.decision_support import generate_recommendations
        from services.institution_intelligence.models import InstitutionInput, InstitutionKPIs
        inp  = InstitutionInput(researchers=_RESEARCHERS, grants=[])
        kpis = InstitutionKPIs(grant_success_rate=0.1)
        recs = generate_recommendations(inp, kpis)
        cats = [r.category for r in recs]
        assert "funding_strategy" in cats or "grant_strategy" in cats


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Resource Optimizer
# ═══════════════════════════════════════════════════════════════════════════════

class TestResourceOptimizer:
    def test_returns_allocations(self):
        from services.institution_intelligence.kpi_engine import compute_kpis
        from services.institution_intelligence.models import InstitutionInput
        from services.institution_intelligence.resource_optimizer import optimise_resources
        inp  = InstitutionInput(researchers=_RESEARCHERS, grants=_GRANTS)
        kpis = compute_kpis(inp)
        allocs = optimise_resources(inp, kpis)
        assert len(allocs) > 0

    def test_all_fields_present(self):
        from services.institution_intelligence.kpi_engine import compute_kpis
        from services.institution_intelligence.models import InstitutionInput
        from services.institution_intelligence.resource_optimizer import optimise_resources
        inp  = InstitutionInput(researchers=_RESEARCHERS, grants=_GRANTS)
        kpis = compute_kpis(inp)
        for a in optimise_resources(inp, kpis):
            d = a.to_dict()
            assert "category" in d
            assert "change_direction" in d
            assert 0.0 <= d["expected_roi"] <= 1.0

    def test_grant_writing_when_low_success(self):
        from services.institution_intelligence.models import InstitutionInput, InstitutionKPIs
        from services.institution_intelligence.resource_optimizer import optimise_resources
        inp  = InstitutionInput(researchers=_RESEARCHERS, grants=[])
        kpis = InstitutionKPIs(grant_success_rate=0.10, internationalization_score=0.1,
                               innovation_score=0.1)
        allocs = optimise_resources(inp, kpis)
        cats = [a.category for a in allocs]
        assert "training" in cats


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Talent Intelligence
# ═══════════════════════════════════════════════════════════════════════════════

class TestTalentIntelligence:
    def test_returns_all_categories(self):
        from services.institution_intelligence.models import InstitutionInput
        from services.institution_intelligence.talent_intelligence import identify_talent
        inp = InstitutionInput(researchers=_RESEARCHERS)
        t = identify_talent(inp)
        expected = {"future_leaders", "high_potential", "promotion_candidates",
                    "retention_risks", "mentorship_providers", "training_needs", "succession_planning"}
        assert set(t.keys()) == expected

    def test_empty_researchers_no_crash(self):
        from services.institution_intelligence.models import InstitutionInput
        from services.institution_intelligence.talent_intelligence import identify_talent
        t = identify_talent(InstitutionInput(researchers=[]))
        assert all(len(v) == 0 for v in t.values())

    def test_professor_in_mentorship(self):
        from services.institution_intelligence.models import InstitutionInput
        from services.institution_intelligence.talent_intelligence import identify_talent
        available_prof = {**_R2, "_id": "r2_avail", "availability": 0.75}
        inp = InstitutionInput(researchers=[_R1, available_prof])
        t = identify_talent(inp)
        ids = [p.user_id for p in t["mentorship_providers"]]
        assert "r2_avail" in ids

    def test_professor_in_succession(self):
        from services.institution_intelligence.models import InstitutionInput
        from services.institution_intelligence.talent_intelligence import identify_talent
        inp = InstitutionInput(researchers=[_R1, _R2])
        t = identify_talent(inp)
        ids = [p.user_id for p in t["succession_planning"]]
        assert "r2" in ids

    def test_talent_profiles_serializable(self):
        from services.institution_intelligence.models import InstitutionInput
        from services.institution_intelligence.talent_intelligence import (
            identify_talent, serialize_talent,
        )
        t  = identify_talent(InstitutionInput(researchers=_RESEARCHERS))
        ts = serialize_talent(t)
        for v in ts.values():
            for item in v:
                assert isinstance(item, dict)
                assert "user_id" in item


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Portfolio Analyzer
# ═══════════════════════════════════════════════════════════════════════════════

class TestPortfolioAnalyzer:
    def test_builds_portfolio(self):
        from services.institution_intelligence.models import InstitutionInput
        from services.institution_intelligence.portfolio_analyzer import analyse_portfolio
        portfolio = analyse_portfolio(InstitutionInput(researchers=_RESEARCHERS))
        assert len(portfolio) > 0

    def test_areas_have_all_fields(self):
        from services.institution_intelligence.models import InstitutionInput
        from services.institution_intelligence.portfolio_analyzer import analyse_portfolio
        portfolio = analyse_portfolio(InstitutionInput(researchers=_RESEARCHERS))
        for p in portfolio:
            d = p.to_dict()
            assert "name" in d
            assert "strategic_priority" in d
            assert "maturity" in d
            assert 0.0 <= d["alignment_score"] <= 1.0

    def test_ai_area_gets_invest_priority(self):
        from services.institution_intelligence.models import InstitutionInput
        from services.institution_intelligence.portfolio_analyzer import analyse_portfolio
        # Users with ai/ml research areas
        portfolio = analyse_portfolio(InstitutionInput(researchers=_RESEARCHERS))
        areas_by_name = {p.name.lower(): p for p in portfolio}
        ai_area = areas_by_name.get("artificial intelligence") or areas_by_name.get("machine learning")
        if ai_area:
            assert ai_area.strategic_priority == "invest"

    def test_portfolio_summary_fields(self):
        from services.institution_intelligence.models import InstitutionInput
        from services.institution_intelligence.portfolio_analyzer import (
            analyse_portfolio, portfolio_summary,
        )
        p = analyse_portfolio(InstitutionInput(researchers=_RESEARCHERS))
        s = portfolio_summary(p)
        assert "total_areas" in s
        assert "average_alignment" in s

    def test_empty_researchers_no_crash(self):
        from services.institution_intelligence.models import InstitutionInput
        from services.institution_intelligence.portfolio_analyzer import analyse_portfolio
        portfolio = analyse_portfolio(InstitutionInput(researchers=[]))
        assert portfolio == []


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Benchmarking Engine
# ═══════════════════════════════════════════════════════════════════════════════

class TestBenchmarkingEngine:
    def _kpis(self):
        from services.institution_intelligence.kpi_engine import compute_kpis
        from services.institution_intelligence.models import InstitutionInput
        return compute_kpis(InstitutionInput(researchers=_RESEARCHERS, grants=_GRANTS))

    def test_returns_results(self):
        from services.institution_intelligence.benchmarking_engine import benchmark
        results = benchmark(self._kpis(), n_researchers=3)
        assert len(results) > 0

    def test_percentiles_in_range(self):
        from services.institution_intelligence.benchmarking_engine import benchmark
        for r in benchmark(self._kpis(), n_researchers=3):
            assert 0.0 <= r.percentile <= 1.0

    def test_sorted_by_percentile(self):
        from services.institution_intelligence.benchmarking_engine import benchmark
        results = benchmark(self._kpis(), n_researchers=3)
        for a, b in zip(results, results[1:]):
            assert a.percentile <= b.percentile

    def test_summary_has_expected_keys(self):
        from services.institution_intelligence.benchmarking_engine import (
            benchmark, benchmark_summary,
        )
        results  = benchmark(self._kpis(), n_researchers=3)
        summary  = benchmark_summary(results)
        assert "overall_percentile" in summary
        assert "strengths" in summary
        assert "weaknesses" in summary

    def test_high_h_index_above_average(self):
        from services.institution_intelligence.benchmarking_engine import benchmark
        from services.institution_intelligence.models import InstitutionKPIs
        kpis = InstitutionKPIs(avg_h_index=20.0, publication_output=200)
        results = benchmark(kpis, n_researchers=10)
        h_result = next((r for r in results if r.metric == "avg_h_index"), None)
        if h_result:
            assert h_result.percentile >= 0.50


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Monitoring Engine
# ═══════════════════════════════════════════════════════════════════════════════

class TestMonitoringEngine:
    def test_generates_alerts(self):
        from services.institution_intelligence.kpi_engine import compute_kpis
        from services.institution_intelligence.models import InstitutionInput
        from services.institution_intelligence.monitoring_engine import monitor
        inp  = InstitutionInput(researchers=_RESEARCHERS, grants=[])
        kpis = compute_kpis(inp)
        alerts = monitor(inp, kpis)
        assert isinstance(alerts, list)

    def test_low_kpi_triggers_alert(self):
        from services.institution_intelligence.models import InstitutionInput, InstitutionKPIs
        from services.institution_intelligence.monitoring_engine import monitor
        inp  = InstitutionInput(researchers=_RESEARCHERS)
        kpis = InstitutionKPIs(grant_success_rate=0.10, internationalization_score=0.05)
        alerts = monitor(inp, kpis)
        metrics = [a.metric for a in alerts]
        assert "grant_success_rate" in metrics or "internationalization_score" in metrics

    def test_high_kpi_generates_opportunity(self):
        from services.institution_intelligence.models import AlertType, InstitutionInput, InstitutionKPIs
        from services.institution_intelligence.monitoring_engine import monitor
        inp  = InstitutionInput(researchers=_RESEARCHERS)
        kpis = InstitutionKPIs(avg_h_index=15.0, collaboration_score=0.7)
        alerts = monitor(inp, kpis)
        types = [a.alert_type for a in alerts]
        assert AlertType.OPPORTUNITY in types

    def test_severity_order(self):
        from services.institution_intelligence.models import InstitutionInput, InstitutionKPIs, RiskLevel
        from services.institution_intelligence.monitoring_engine import monitor
        inp  = InstitutionInput(researchers=_RESEARCHERS)
        kpis = InstitutionKPIs(grant_success_rate=0.05, internationalization_score=0.02,
                               collaboration_score=0.02, reputation_score=0.10)
        alerts = monitor(inp, kpis)
        level_order = {l: i for i, l in enumerate(RiskLevel)}
        if len(alerts) >= 2:
            for a, b in zip(alerts, alerts[1:]):
                assert level_order.get(a.severity, 99) <= level_order.get(b.severity, 99)


# ═══════════════════════════════════════════════════════════════════════════════
# 13. Knowledge Graph
# ═══════════════════════════════════════════════════════════════════════════════

class TestKnowledgeGraph:
    def test_builds_graph(self):
        from services.institution_intelligence.knowledge_graph import build_knowledge_graph
        from services.institution_intelligence.models import InstitutionInput
        graph = build_knowledge_graph(InstitutionInput(name="Test", researchers=_RESEARCHERS,
                                                       grants=_GRANTS))
        assert len(graph.nodes) > 0

    def test_has_institution_root(self):
        from services.institution_intelligence.knowledge_graph import build_knowledge_graph
        from services.institution_intelligence.models import InstitutionInput
        graph = build_knowledge_graph(InstitutionInput(name="MIT", researchers=_RESEARCHERS))
        types = [n.node_type for n in graph.nodes]
        assert "institution" in types

    def test_has_researcher_nodes(self):
        from services.institution_intelligence.knowledge_graph import build_knowledge_graph
        from services.institution_intelligence.models import InstitutionInput
        graph = build_knowledge_graph(InstitutionInput(name="MIT", researchers=_RESEARCHERS))
        types = [n.node_type for n in graph.nodes]
        assert "researcher" in types

    def test_has_grant_nodes(self):
        from services.institution_intelligence.knowledge_graph import build_knowledge_graph
        from services.institution_intelligence.models import InstitutionInput
        graph = build_knowledge_graph(InstitutionInput(name="MIT", researchers=_RESEARCHERS,
                                                       grants=_GRANTS))
        types = [n.node_type for n in graph.nodes]
        assert "grant" in types

    def test_max_nodes_respected(self):
        from services.institution_intelligence.knowledge_graph import build_knowledge_graph
        from services.institution_intelligence.models import InstitutionInput
        graph = build_knowledge_graph(InstitutionInput(name="MIT",
                                                       researchers=_RESEARCHERS * 10,
                                                       grants=_GRANTS),
                                      max_nodes=10)
        assert len(graph.nodes) <= 10

    def test_to_dict_stats(self):
        from services.institution_intelligence.knowledge_graph import build_knowledge_graph
        from services.institution_intelligence.models import InstitutionInput
        graph = build_knowledge_graph(InstitutionInput(name="MIT", researchers=_RESEARCHERS))
        d = graph.to_dict()
        assert d["stats"]["total_nodes"] == len(graph.nodes)


# ═══════════════════════════════════════════════════════════════════════════════
# 14. Visualization Builder
# ═══════════════════════════════════════════════════════════════════════════════

class TestVisualizationBuilder:
    def _profile_kpis(self):
        from services.institution_intelligence.institution_profiler import build_institution_profile
        from services.institution_intelligence.kpi_engine import compute_kpis
        from services.institution_intelligence.models import InstitutionInput
        inp  = InstitutionInput(researchers=_RESEARCHERS, grants=_GRANTS, name="MIT")
        p    = build_institution_profile(inp)
        k    = compute_kpis(inp)
        p.kpis = k
        return inp, p, k

    def test_knowledge_graph_viz(self):
        from services.institution_intelligence.visualization_builder import knowledge_graph_viz
        from services.institution_intelligence.models import VizType
        inp, p, k = self._profile_kpis()
        viz = knowledge_graph_viz(p)
        assert viz["viz_type"] == VizType.KNOWLEDGE_GRAPH.value

    def test_department_heatmap(self):
        from services.institution_intelligence.visualization_builder import department_heatmap_viz
        inp, p, k = self._profile_kpis()
        viz = department_heatmap_viz(p)
        assert "rows" in viz["data"]

    def test_grant_dashboard(self):
        from services.institution_intelligence.visualization_builder import grant_dashboard_viz
        viz = grant_dashboard_viz(_GRANTS)
        assert viz["data"]["total_income"] == 570000.0

    def test_citation_growth(self):
        from services.institution_intelligence.visualization_builder import citation_growth_viz
        inp, p, k = self._profile_kpis()
        viz = citation_growth_viz(k)
        assert len(viz["data"]["years"]) == 5
        assert len(viz["data"]["citations"]) == 5

    def test_risk_matrix(self):
        from services.institution_intelligence.models import InstitutionInput
        from services.institution_intelligence.risk_engine import detect_risks
        from services.institution_intelligence.visualization_builder import risk_matrix_viz
        risks = detect_risks(InstitutionInput(researchers=_RESEARCHERS * 2, grants=[]))
        viz = risk_matrix_viz(risks)
        assert viz["viz_type"] == "strategic_risk_matrix"
        assert "points" in viz["data"]

    def test_faculty_performance(self):
        from services.institution_intelligence.visualization_builder import faculty_performance_viz
        viz = faculty_performance_viz(_RESEARCHERS)
        assert len(viz["data"]["points"]) == 3

    def test_international_map(self):
        from services.institution_intelligence.visualization_builder import (
            international_collaboration_viz,
        )
        viz = international_collaboration_viz(_RESEARCHERS)
        assert viz["metadata"]["total_countries"] == 3

    def test_forecast_dashboard(self):
        from services.institution_intelligence.models import InstitutionInput
        from services.institution_intelligence.prediction_engine import predict_institution
        from services.institution_intelligence.visualization_builder import forecast_dashboard_viz
        forecasts = predict_institution(InstitutionInput(researchers=_RESEARCHERS))
        viz = forecast_dashboard_viz(forecasts)
        assert len(viz["data"]["series"]) == 8


# ═══════════════════════════════════════════════════════════════════════════════
# 15. Telemetry
# ═══════════════════════════════════════════════════════════════════════════════

class TestTelemetry:
    def _fresh(self):
        from services.institution_intelligence.telemetry import InstitutionTelemetry, get_telemetry
        InstitutionTelemetry._instance = None
        return get_telemetry()

    def test_singleton(self):
        t1 = self._fresh()
        from services.institution_intelligence.telemetry import get_telemetry
        t2 = get_telemetry()
        assert t1 is t2

    def test_record_counter(self):
        t = self._fresh()
        t.record("profile_builds")
        assert t.snapshot()["profile_builds"] == 1

    def test_record_error(self):
        t = self._fresh()
        t.record_error()
        assert t.snapshot()["errors"] == 1

    def test_latency(self):
        t = self._fresh()
        t.record_latency(0.05)
        t.record_latency(0.10)
        s = t.snapshot()
        assert s["sample_count"] == 2
        assert abs(s["latency_avg_s"] - 0.075) < 0.01

    def test_reset(self):
        t = self._fresh()
        t.record("kpi_computations")
        t.reset()
        assert t.snapshot()["kpi_computations"] == 0


# ═══════════════════════════════════════════════════════════════════════════════
# 16. Engine Integration
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineIntegration:
    def _engine(self):
        from services.institution_intelligence.engine import (
            get_institution_engine, reset_institution_engine,
        )
        reset_institution_engine()
        return asyncio.run(get_institution_engine())

    def test_singleton(self):
        from services.institution_intelligence.engine import (
            get_institution_engine, reset_institution_engine,
        )
        reset_institution_engine()
        async def _run():
            e1 = await get_institution_engine()
            e2 = await get_institution_engine()
            assert e1 is e2
        asyncio.run(_run())

    def test_build_profile(self):
        e = self._engine()
        p = e.build_profile(_INST_DATA)
        assert p["name"] == "MIT"
        assert p["total_researchers"] == 3

    def test_compute_kpis(self):
        e = self._engine()
        k = e.compute_kpis(_INST_DATA)
        assert "publication_output" in k
        assert k["publication_output"] == 111

    def test_organizational_intelligence(self):
        e = self._engine()
        r = e.organizational_intelligence(_INST_DATA)
        assert "insights" in r
        assert "total" in r

    def test_predict(self):
        e = self._engine()
        r = e.predict(_INST_DATA, horizon=3)
        assert r["horizon_years"] == 3
        assert len(r["forecasts"]) == 8

    def test_optimise_resources(self):
        e = self._engine()
        r = e.optimise_resources(_INST_DATA)
        assert "allocations" in r

    def test_talent_intelligence(self):
        e = self._engine()
        r = e.talent_intelligence(_INST_DATA)
        assert "future_leaders" in r

    def test_analyse_portfolio(self):
        e = self._engine()
        r = e.analyse_portfolio(_INST_DATA)
        assert "portfolio" in r
        assert "summary" in r

    def test_benchmark_institution(self):
        e = self._engine()
        r = e.benchmark_institution(_INST_DATA)
        assert "benchmarks" in r
        assert "summary" in r

    def test_detect_risks(self):
        e = self._engine()
        r = e.detect_risks(_INST_DATA)
        assert "risks" in r
        assert "total" in r

    def test_recommendations(self):
        e = self._engine()
        r = e.recommendations(_INST_DATA)
        assert "recommendations" in r
        assert len(r["recommendations"]) > 0

    def test_monitor(self):
        e = self._engine()
        r = e.monitor(_INST_DATA)
        assert "alerts" in r

    def test_knowledge_graph(self):
        e = self._engine()
        r = e.knowledge_graph(_INST_DATA, max_nodes=50)
        assert "nodes" in r
        assert "edges" in r

    def test_visualization_knowledge_graph(self):
        e = self._engine()
        v = e.visualization("institution_knowledge_graph", _INST_DATA)
        assert v["viz_type"] == "institution_knowledge_graph"

    def test_visualization_department_heatmap(self):
        e = self._engine()
        v = e.visualization("department_heatmap", _INST_DATA)
        assert v["viz_type"] == "department_heatmap"

    def test_export_pdf(self):
        e = self._engine()
        result = e.export_report(_INST_DATA, report_type="executive", export_format="pdf")
        assert result["format"] == "pdf"
        assert "MIT" in result["content"]["title"]

    def test_export_excel(self):
        e = self._engine()
        result = e.export_report(_INST_DATA, report_type="accreditation", export_format="excel")
        assert result["format"] == "excel"
        assert "sheets" in result

    def test_full_analysis(self):
        e = self._engine()
        r = e.full_analysis(_INST_DATA)
        expected_keys = {"profile", "kpis", "organizational", "risks",
                         "recommendations", "benchmarks", "forecasts",
                         "talent", "portfolio_summary", "alerts"}
        assert expected_keys.issubset(set(r.keys()))

    def test_admin_analytics(self):
        e = self._engine()
        r = e.admin_analytics([_INST_DATA, _INST_DATA])
        assert r["total_institutions"] == 2
        assert r["total_researchers"] == 6
