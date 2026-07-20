"""Phase XVI — Academic Career Intelligence Engine test suite.

Run with:  python -m pytest backend/tests/test_career_intelligence.py -v
All tests are pure-Python (no DB, no network, no mocking).
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Shared fixtures ───────────────────────────────────────────────────────────

_PHD = {
    "_id": "u_phd", "full_name": "Ana Doe", "position": "phd student",
    "h_index": 1, "publication_count": 2, "citation_count": 5,
    "grant_count": 0, "grant_income": 0, "collaboration_count": 1,
    "international_collab_ratio": 0.0, "peer_review_count": 0,
    "conference_count": 2, "research_areas": ["machine learning", "nlp"],
    "research_methods": ["survey", "experiment"],
    "statistical_expertise": [], "programming_skills": ["python"],
    "teaching_areas": [], "availability": 0.8,
}

_POSTDOC = {
    "_id": "u_pd", "full_name": "Bob Smith", "position": "postdoctoral researcher",
    "h_index": 5, "publication_count": 12, "citation_count": 120,
    "grant_count": 1, "grant_income": 30000, "collaboration_count": 6,
    "international_collab_ratio": 0.3, "peer_review_count": 8,
    "conference_count": 5, "research_areas": ["bioinformatics"],
    "research_methods": ["rct", "cohort"], "statistical_expertise": ["regression"],
    "programming_skills": ["python", "r"], "teaching_areas": ["statistics"],
    "availability": 0.7,
}

_PROFESSOR = {
    "_id": "u_prof", "full_name": "Carol Jones", "position": "professor",
    "h_index": 28, "publication_count": 85, "citation_count": 3500,
    "grant_count": 8, "grant_income": 450000, "collaboration_count": 30,
    "international_collab_ratio": 0.5, "peer_review_count": 40,
    "conference_count": 25, "research_areas": ["physics", "materials science"],
    "research_methods": ["experiment", "simulation"],
    "statistical_expertise": ["bayesian", "multilevel"],
    "programming_skills": ["python", "matlab"],
    "teaching_areas": ["thermodynamics", "quantum mechanics"],
    "availability": 0.6,
}

_EMPTY = {"_id": "u_empty"}


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Models
# ═══════════════════════════════════════════════════════════════════════════════

class TestModels:
    def test_career_stage_values(self):
        from services.career_intelligence.models import CareerStage
        assert CareerStage.PHD_CANDIDATE.value == "phd_candidate"
        assert CareerStage.PROFESSOR.value == "professor"

    def test_roadmap_horizon_values(self):
        from services.career_intelligence.models import RoadmapHorizon
        assert set(h.value for h in RoadmapHorizon) == {"1_year", "3_year", "5_year", "10_year"}

    def test_milestone_type_values(self):
        from services.career_intelligence.models import MilestoneType
        assert MilestoneType.PUBLICATION.value == "publication"
        assert MilestoneType.DEGREE.value == "degree"

    def test_goal_type_values(self):
        from services.career_intelligence.models import GoalType
        assert GoalType.H_INDEX.value == "h_index"
        assert GoalType.PROMOTION.value == "promotion"

    def test_goal_status_values(self):
        from services.career_intelligence.models import GoalStatus
        assert GoalStatus.COMPLETED.value == "completed"
        assert GoalStatus.AT_RISK.value == "at_risk"

    def test_skill_level_order(self):
        from services.career_intelligence.models import SkillLevel
        levels = [SkillLevel.NONE, SkillLevel.BEGINNER, SkillLevel.DEVELOPING,
                  SkillLevel.PROFICIENT, SkillLevel.EXPERT]
        assert [l.value for l in levels] == ["none", "beginner", "developing", "proficient", "expert"]

    def test_promotion_target_values(self):
        from services.career_intelligence.models import PromotionTarget
        assert len(list(PromotionTarget)) == 8

    def test_career_risk_types(self):
        from services.career_intelligence.models import CareerRiskType
        assert len(list(CareerRiskType)) == 8

    def test_viz_type_count(self):
        from services.career_intelligence.models import VizType
        assert len(list(VizType)) == 10

    def test_export_report_type_count(self):
        from services.career_intelligence.models import ExportReportType
        assert len(list(ExportReportType)) == 6

    def test_export_format_values(self):
        from services.career_intelligence.models import ExportFormat
        assert ExportFormat.MARKDOWN.value == "markdown"

    def test_career_profile_to_dict(self):
        from services.career_intelligence.models import CareerProfile, CareerStage
        p = CareerProfile(user_id="x", career_stage=CareerStage.POSTDOC,
                          h_index=5.0, publication_count=12)
        d = p.to_dict()
        assert d["user_id"] == "x"
        assert d["career_stage"] == "postdoc"
        assert d["h_index"] == 5.0

    def test_roadmap_milestone_to_dict(self):
        from services.career_intelligence.models import MilestoneType, RoadmapMilestone
        m = RoadmapMilestone(milestone_type=MilestoneType.PUBLICATION,
                             description="Publish 3 papers", year=2)
        d = m.to_dict()
        assert d["type"] == "publication"
        assert d["year"] == 2

    def test_career_roadmap_to_dict(self):
        from services.career_intelligence.models import CareerRoadmap, CareerStage, RoadmapHorizon
        r = CareerRoadmap(user_id="u1", career_stage=CareerStage.PHD_CANDIDATE,
                          horizon=RoadmapHorizon.THREE_YEAR, milestones=[])
        d = r.to_dict()
        assert d["horizon"] == "3_year"
        assert d["total_milestones"] == 0

    def test_career_goal_to_dict(self):
        from services.career_intelligence.models import CareerGoal, GoalStatus, GoalType
        g = CareerGoal(goal_type=GoalType.PUBLICATION, description="Publish 3 papers",
                       target_value=3, current_value=1, status=GoalStatus.IN_PROGRESS,
                       progress=0.333)
        d = g.to_dict()
        assert d["goal_type"] == "publication"
        assert d["progress"] == 0.333

    def test_skill_gap_to_dict(self):
        from services.career_intelligence.models import SkillGap, SkillGapSeverity, SkillLevel
        gap = SkillGap(domain="statistics", current_level=SkillLevel.NONE,
                       required_level=SkillLevel.PROFICIENT,
                       severity=SkillGapSeverity.CRITICAL, gap_score=0.75)
        d = gap.to_dict()
        assert d["severity"] == "critical"
        assert d["gap_score"] == 0.75

    def test_promotion_readiness_to_dict(self):
        from services.career_intelligence.models import PromotionReadiness, PromotionTarget
        pr = PromotionReadiness(target=PromotionTarget.ASSOCIATE_PROF,
                                overall_readiness=0.6, estimated_months=24)
        d = pr.to_dict()
        assert d["target"] == "associate_professor"
        assert d["overall_readiness"] == 0.6

    def test_career_risk_to_dict(self):
        from services.career_intelligence.models import CareerRisk, CareerRiskType, RiskSeverity
        r = CareerRisk(risk_type=CareerRiskType.LOW_FUNDING,
                       severity=RiskSeverity.HIGH, risk_score=0.65)
        d = r.to_dict()
        assert d["risk_type"] == "low_funding"
        assert d["severity"] == "high"

    def test_copilot_suggestion_to_dict(self):
        from services.career_intelligence.models import CopilotSuggestion
        s = CopilotSuggestion(category="writing", suggestion="Publish more",
                              action="Use manuscript engine", urgency="high")
        d = s.to_dict()
        assert d["category"] == "writing"
        assert d["urgency"] == "high"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Career Profiler
# ═══════════════════════════════════════════════════════════════════════════════

class TestCareerProfiler:
    def test_phd_stage_detected(self):
        from services.career_intelligence.career_profiler import build_career_profile
        from services.career_intelligence.models import CareerStage
        p = build_career_profile(_PHD)
        assert p.career_stage == CareerStage.PHD_CANDIDATE

    def test_postdoc_stage_detected(self):
        from services.career_intelligence.career_profiler import build_career_profile
        from services.career_intelligence.models import CareerStage
        p = build_career_profile(_POSTDOC)
        assert p.career_stage == CareerStage.POSTDOC

    def test_professor_stage_detected(self):
        from services.career_intelligence.career_profiler import build_career_profile
        from services.career_intelligence.models import CareerStage
        p = build_career_profile(_PROFESSOR)
        assert p.career_stage == CareerStage.PROFESSOR

    def test_empty_user_does_not_crash(self):
        from services.career_intelligence.career_profiler import build_career_profile
        p = build_career_profile(_EMPTY)
        assert p.user_id == "u_empty"

    def test_scores_in_range(self):
        from services.career_intelligence.career_profiler import build_career_profile
        for user in [_PHD, _POSTDOC, _PROFESSOR, _EMPTY]:
            p = build_career_profile(user)
            assert 0.0 <= p.productivity_score <= 1.0
            assert 0.0 <= p.quality_score <= 1.0
            assert 0.0 <= p.impact_score <= 1.0
            assert 0.0 <= p.overall_score <= 1.0

    def test_professor_has_higher_score_than_phd(self):
        from services.career_intelligence.career_profiler import build_career_profile
        p_phd  = build_career_profile(_PHD)
        p_prof = build_career_profile(_PROFESSOR)
        assert p_prof.overall_score > p_phd.overall_score

    def test_research_areas_extracted(self):
        from services.career_intelligence.career_profiler import build_career_profile
        p = build_career_profile(_PHD)
        assert "machine learning" in p.research_areas

    def test_programming_skills_extracted(self):
        from services.career_intelligence.career_profiler import build_career_profile
        p = build_career_profile(_POSTDOC)
        assert "python" in p.programming_skills

    def test_to_dict_keys(self):
        from services.career_intelligence.career_profiler import build_career_profile
        p = build_career_profile(_POSTDOC)
        d = p.to_dict()
        for key in ["user_id", "career_stage", "h_index", "publication_count",
                    "productivity_score", "overall_score"]:
            assert key in d

    def test_fallback_stage_from_hindex(self):
        from services.career_intelligence.career_profiler import build_career_profile
        from services.career_intelligence.models import CareerStage
        user = {"_id": "u_h", "h_index": 10, "publication_count": 25}
        p = build_career_profile(user)
        assert p.career_stage == CareerStage.ASSOCIATE_PROF

    def test_years_active_positive(self):
        from services.career_intelligence.career_profiler import build_career_profile
        p = build_career_profile(_PROFESSOR)
        assert p.years_active > 0


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Roadmap Builder
# ═══════════════════════════════════════════════════════════════════════════════

class TestRoadmapBuilder:
    def _profile(self, user):
        from services.career_intelligence.career_profiler import build_career_profile
        return build_career_profile(user)

    def test_phd_1yr_roadmap(self):
        from services.career_intelligence.models import RoadmapHorizon
        from services.career_intelligence.roadmap_builder import build_roadmap
        r = build_roadmap(self._profile(_PHD), RoadmapHorizon.ONE_YEAR)
        assert r.horizon.value == "1_year"
        assert len(r.milestones) >= 1
        assert all(m.year <= 1 for m in r.milestones)

    def test_postdoc_3yr_roadmap(self):
        from services.career_intelligence.models import RoadmapHorizon
        from services.career_intelligence.roadmap_builder import build_roadmap
        r = build_roadmap(self._profile(_POSTDOC), RoadmapHorizon.THREE_YEAR)
        assert len(r.milestones) >= 3
        assert all(m.year <= 3 for m in r.milestones)

    def test_professor_10yr_roadmap(self):
        from services.career_intelligence.models import RoadmapHorizon
        from services.career_intelligence.roadmap_builder import build_roadmap
        r = build_roadmap(self._profile(_PROFESSOR), RoadmapHorizon.TEN_YEAR)
        assert len(r.milestones) >= 5

    def test_milestones_sorted_by_year(self):
        from services.career_intelligence.models import RoadmapHorizon
        from services.career_intelligence.roadmap_builder import build_roadmap
        r = build_roadmap(self._profile(_PHD), RoadmapHorizon.FIVE_YEAR)
        years = [m.year for m in r.milestones]
        assert years == sorted(years)

    def test_summary_not_empty(self):
        from services.career_intelligence.models import RoadmapHorizon
        from services.career_intelligence.roadmap_builder import build_roadmap
        r = build_roadmap(self._profile(_POSTDOC), RoadmapHorizon.THREE_YEAR)
        assert len(r.summary) > 10

    def test_key_focus_areas(self):
        from services.career_intelligence.models import RoadmapHorizon
        from services.career_intelligence.roadmap_builder import build_roadmap
        r = build_roadmap(self._profile(_PHD), RoadmapHorizon.THREE_YEAR)
        assert len(r.key_focus_areas) >= 2

    def test_to_dict_roundtrip(self):
        from services.career_intelligence.models import RoadmapHorizon
        from services.career_intelligence.roadmap_builder import build_roadmap
        r  = build_roadmap(self._profile(_POSTDOC), RoadmapHorizon.THREE_YEAR)
        d  = r.to_dict()
        assert d["total_milestones"] == len(r.milestones)
        assert d["horizon"] == "3_year"

    def test_estimated_completion_year_is_future(self):
        import datetime
        from services.career_intelligence.models import RoadmapHorizon
        from services.career_intelligence.roadmap_builder import build_roadmap
        r = build_roadmap(self._profile(_PHD), RoadmapHorizon.THREE_YEAR)
        assert r.estimated_completion_year >= datetime.date.today().year + 1


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Goal Manager
# ═══════════════════════════════════════════════════════════════════════════════

class TestGoalManager:
    def _profile(self, user):
        from services.career_intelligence.career_profiler import build_career_profile
        return build_career_profile(user)

    def test_evaluate_publication_goal(self):
        from services.career_intelligence.goal_manager import evaluate_goals
        goals = [{"goal_type": "publication", "description": "Publish 5 papers",
                  "target_value": 5, "current_value": 2, "deadline_months": 12}]
        result = evaluate_goals(self._profile(_PHD), goals)
        assert len(result) == 1
        assert result[0].goal_type.value == "publication"
        assert 0.0 < result[0].progress < 1.0

    def test_completed_goal_status(self):
        from services.career_intelligence.goal_manager import evaluate_goals
        goals = [{"goal_type": "publication", "target_value": 2, "current_value": 5}]
        result = evaluate_goals(self._profile(_PHD), goals)
        assert result[0].status.value == "completed"

    def test_at_risk_goal_status(self):
        from services.career_intelligence.goal_manager import evaluate_goals
        goals = [{"goal_type": "publication", "target_value": 20, "current_value": 1,
                  "deadline_months": 3}]
        result = evaluate_goals(self._profile(_PHD), goals)
        assert result[0].status.value == "at_risk"

    def test_infer_default_goals_phd(self):
        from services.career_intelligence.goal_manager import infer_default_goals
        goals = infer_default_goals(self._profile(_PHD))
        assert len(goals) >= 2
        types = [g.goal_type.value for g in goals]
        assert "publication" in types

    def test_infer_default_goals_professor(self):
        from services.career_intelligence.goal_manager import infer_default_goals
        goals = infer_default_goals(self._profile(_PROFESSOR))
        assert len(goals) >= 1

    def test_goal_has_milestones(self):
        from services.career_intelligence.goal_manager import evaluate_goals
        goals = [{"goal_type": "publication", "target_value": 5, "current_value": 2}]
        result = evaluate_goals(self._profile(_POSTDOC), goals)
        assert len(result[0].milestones) > 0

    def test_goal_has_recommendation(self):
        from services.career_intelligence.goal_manager import evaluate_goals
        goals = [{"goal_type": "grant", "target_value": 2, "current_value": 0}]
        result = evaluate_goals(self._profile(_PHD), goals)
        assert len(result[0].recommendation) > 0

    def test_h_index_goal_current_inferred(self):
        from services.career_intelligence.goal_manager import evaluate_goals
        goals = [{"goal_type": "h_index", "target_value": 10}]
        result = evaluate_goals(self._profile(_POSTDOC), goals)
        assert result[0].current_value == _POSTDOC["h_index"]

    def test_invalid_goal_type_falls_back(self):
        from services.career_intelligence.goal_manager import evaluate_goals
        goals = [{"goal_type": "nonexistent_type", "target_value": 5}]
        result = evaluate_goals(self._profile(_PHD), goals)
        assert len(result) == 1


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Skill Gap Analyzer
# ═══════════════════════════════════════════════════════════════════════════════

class TestSkillGapAnalyzer:
    def _profile(self, user):
        from services.career_intelligence.career_profiler import build_career_profile
        return build_career_profile(user)

    def test_returns_15_domains(self):
        from services.career_intelligence.skill_gap_analyzer import analyse_skill_gaps
        report = analyse_skill_gaps(self._profile(_POSTDOC))
        assert len(report.assessments) == 15

    def test_phd_has_gaps(self):
        from services.career_intelligence.skill_gap_analyzer import analyse_skill_gaps
        report = analyse_skill_gaps(self._profile(_PHD))
        assert len(report.gaps) > 0

    def test_gaps_have_development_actions(self):
        from services.career_intelligence.skill_gap_analyzer import analyse_skill_gaps
        report = analyse_skill_gaps(self._profile(_PHD))
        for gap in report.gaps:
            assert len(gap.development_actions) > 0

    def test_overall_skill_score_in_range(self):
        from services.career_intelligence.skill_gap_analyzer import analyse_skill_gaps
        for user in [_PHD, _POSTDOC, _PROFESSOR, _EMPTY]:
            report = analyse_skill_gaps(self._profile(user))
            assert 0.0 <= report.overall_skill_score <= 1.0

    def test_professor_higher_score_than_phd(self):
        from services.career_intelligence.skill_gap_analyzer import analyse_skill_gaps
        r_phd  = analyse_skill_gaps(self._profile(_PHD))
        r_prof = analyse_skill_gaps(self._profile(_PROFESSOR))
        assert r_prof.overall_skill_score > r_phd.overall_skill_score

    def test_critical_gaps_listed_correctly(self):
        from services.career_intelligence.models import SkillGapSeverity
        from services.career_intelligence.skill_gap_analyzer import analyse_skill_gaps
        report = analyse_skill_gaps(self._profile(_PHD))
        for domain in report.critical_gaps:
            gap = next((g for g in report.gaps if g.domain == domain), None)
            assert gap is not None
            assert gap.severity == SkillGapSeverity.CRITICAL

    def test_to_dict_roundtrip(self):
        from services.career_intelligence.skill_gap_analyzer import analyse_skill_gaps
        report = analyse_skill_gaps(self._profile(_POSTDOC))
        d = report.to_dict()
        assert "assessments" in d
        assert "gaps" in d
        assert "critical_gaps" in d

    def test_programming_skill_detected(self):
        from services.career_intelligence.models import SkillLevel
        from services.career_intelligence.skill_gap_analyzer import analyse_skill_gaps
        report = analyse_skill_gaps(self._profile(_POSTDOC))
        prog = next((a for a in report.assessments if a.domain == "programming"), None)
        assert prog is not None
        assert prog.current_level != SkillLevel.NONE

    def test_empty_profile_no_crash(self):
        from services.career_intelligence.skill_gap_analyzer import analyse_skill_gaps
        report = analyse_skill_gaps(self._profile(_EMPTY))
        # project_management and leadership always produce small non-zero scores
        assert 0.0 <= report.overall_skill_score < 0.1


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Promotion Readiness
# ═══════════════════════════════════════════════════════════════════════════════

class TestPromotionReadiness:
    def _profile(self, user):
        from services.career_intelligence.career_profiler import build_career_profile
        return build_career_profile(user)

    def test_professor_high_readiness_for_associate(self):
        from services.career_intelligence.models import PromotionTarget
        from services.career_intelligence.promotion_readiness import assess_promotion_readiness
        r = assess_promotion_readiness(self._profile(_PROFESSOR), PromotionTarget.ASSOCIATE_PROF)
        assert r.overall_readiness > 0.5

    def test_phd_low_readiness_for_professor(self):
        from services.career_intelligence.models import PromotionTarget
        from services.career_intelligence.promotion_readiness import assess_promotion_readiness
        r = assess_promotion_readiness(self._profile(_PHD), PromotionTarget.PROFESSOR)
        assert r.overall_readiness < 0.4

    def test_requirements_met_and_missing_cover_all(self):
        from services.career_intelligence.models import PromotionTarget
        from services.career_intelligence.promotion_readiness import assess_promotion_readiness, _REQUIREMENTS
        r = assess_promotion_readiness(self._profile(_POSTDOC), PromotionTarget.ASSISTANT_PROF)
        total = len(r.requirements_met) + len(r.requirements_missing)
        expected = len(_REQUIREMENTS[PromotionTarget.ASSISTANT_PROF])
        assert total == expected

    def test_readiness_in_range(self):
        from services.career_intelligence.models import PromotionTarget
        from services.career_intelligence.promotion_readiness import assess_promotion_readiness
        for target in PromotionTarget:
            r = assess_promotion_readiness(self._profile(_POSTDOC), target)
            assert 0.0 <= r.overall_readiness <= 1.0

    def test_estimated_months_positive(self):
        from services.career_intelligence.models import PromotionTarget
        from services.career_intelligence.promotion_readiness import assess_promotion_readiness
        r = assess_promotion_readiness(self._profile(_PHD), PromotionTarget.PHD_COMPLETION)
        assert r.estimated_months > 0

    def test_recommended_actions_for_missing_reqs(self):
        from services.career_intelligence.models import PromotionTarget
        from services.career_intelligence.promotion_readiness import assess_promotion_readiness
        r = assess_promotion_readiness(self._profile(_PHD), PromotionTarget.PROFESSOR)
        assert len(r.recommended_actions) > 0

    def test_to_dict_keys(self):
        from services.career_intelligence.models import PromotionTarget
        from services.career_intelligence.promotion_readiness import assess_promotion_readiness
        r = assess_promotion_readiness(self._profile(_POSTDOC), PromotionTarget.ASSOCIATE_PROF)
        d = r.to_dict()
        for key in ["target", "overall_readiness", "requirements_met",
                    "requirements_missing", "recommended_actions", "estimated_months"]:
            assert key in d

    def test_phd_completion_requirements(self):
        from services.career_intelligence.models import PromotionTarget
        from services.career_intelligence.promotion_readiness import assess_promotion_readiness
        r = assess_promotion_readiness(self._profile(_POSTDOC), PromotionTarget.PHD_COMPLETION)
        # Postdoc has pubs ≥ 2, conferences ≥ 2, h-index ≥ 1, methods
        assert r.overall_readiness == 1.0


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Productivity Analyzer
# ═══════════════════════════════════════════════════════════════════════════════

class TestProductivityAnalyzer:
    def _profile(self, user):
        from services.career_intelligence.career_profiler import build_career_profile
        return build_career_profile(user)

    def test_all_scores_in_range(self):
        from services.career_intelligence.productivity_analyzer import analyse_productivity
        for user in [_PHD, _POSTDOC, _PROFESSOR, _EMPTY]:
            m = analyse_productivity(self._profile(user))
            for attr in ["output_score", "impact_score", "consistency_score", "overall_productivity"]:
                val = getattr(m, attr)
                assert 0.0 <= val <= 1.0, f"{attr}={val} out of range for {user['_id']}"

    def test_professor_higher_productivity(self):
        from services.career_intelligence.productivity_analyzer import analyse_productivity
        m_phd  = analyse_productivity(self._profile(_PHD))
        m_prof = analyse_productivity(self._profile(_PROFESSOR))
        assert m_prof.overall_productivity > m_phd.overall_productivity

    def test_pub_per_year_positive(self):
        from services.career_intelligence.productivity_analyzer import analyse_productivity
        m = analyse_productivity(self._profile(_PROFESSOR))
        assert m.publications_per_year > 0

    def test_empty_profile_no_crash(self):
        from services.career_intelligence.productivity_analyzer import analyse_productivity
        m = analyse_productivity(self._profile(_EMPTY))
        assert m.overall_productivity == 0.0

    def test_to_dict_keys(self):
        from services.career_intelligence.productivity_analyzer import analyse_productivity
        m = analyse_productivity(self._profile(_POSTDOC))
        d = m.to_dict()
        for key in ["publications_per_year", "overall_productivity", "output_score",
                    "impact_score", "consistency_score"]:
            assert key in d

    def test_research_diversity_counts_areas(self):
        from services.career_intelligence.productivity_analyzer import analyse_productivity
        m = analyse_productivity(self._profile(_PROFESSOR))
        assert m.research_diversity == 2  # physics + materials science


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Risk Analyzer
# ═══════════════════════════════════════════════════════════════════════════════

class TestRiskAnalyzer:
    def _profile(self, user):
        from services.career_intelligence.career_profiler import build_career_profile
        return build_career_profile(user)

    def test_phd_has_risks(self):
        from services.career_intelligence.risk_analyzer import detect_career_risks
        risks = detect_career_risks(self._profile(_PHD))
        assert len(risks) > 0

    def test_risks_sorted_by_severity(self):
        from services.career_intelligence.models import RiskSeverity
        from services.career_intelligence.risk_analyzer import detect_career_risks
        _SEV = {RiskSeverity.CRITICAL: 0, RiskSeverity.HIGH: 1,
                RiskSeverity.MEDIUM: 2, RiskSeverity.LOW: 3}
        risks = detect_career_risks(self._profile(_PHD))
        sevs = [_SEV[r.severity] for r in risks]
        assert sevs == sorted(sevs)

    def test_risk_scores_in_range(self):
        from services.career_intelligence.risk_analyzer import detect_career_risks
        risks = detect_career_risks(self._profile(_PHD))
        for r in risks:
            assert 0.0 <= r.risk_score <= 1.0

    def test_no_grant_risk_for_early_stage(self):
        from services.career_intelligence.models import CareerRiskType
        from services.career_intelligence.risk_analyzer import detect_career_risks
        risks = detect_career_risks(self._profile(_PHD))
        types = [r.risk_type for r in risks]
        # PHD candidates should NOT trigger low_funding risk
        assert CareerRiskType.LOW_FUNDING not in types

    def test_professor_has_fewer_risks(self):
        from services.career_intelligence.risk_analyzer import detect_career_risks
        r_phd  = detect_career_risks(self._profile(_PHD))
        r_prof = detect_career_risks(self._profile(_PROFESSOR))
        assert len(r_prof) <= len(r_phd)

    def test_risk_to_dict_keys(self):
        from services.career_intelligence.risk_analyzer import detect_career_risks
        risks = detect_career_risks(self._profile(_PHD))
        if risks:
            d = risks[0].to_dict()
            for key in ["risk_type", "severity", "description", "evidence", "mitigation"]:
                assert key in d

    def test_isolation_risk_for_no_intl_collab(self):
        from services.career_intelligence.models import CareerRiskType
        from services.career_intelligence.risk_analyzer import detect_career_risks
        user_no_intl = {**_POSTDOC, "international_collab_ratio": 0.0}
        risks = detect_career_risks(self._profile(user_no_intl))
        types = [r.risk_type for r in risks]
        assert CareerRiskType.RESEARCH_ISOLATION in types

    def test_stagnation_risk_for_long_low_hindex(self):
        from services.career_intelligence.models import CareerRiskType
        from services.career_intelligence.risk_analyzer import detect_career_risks
        user = {**_PHD, "position": "researcher", "h_index": 2, "publication_count": 4,
                "phd_year": 8}
        risks = detect_career_risks(self._profile(user))
        types = [r.risk_type for r in risks]
        assert CareerRiskType.CAREER_STAGNATION in types

    def test_empty_profile_no_crash(self):
        from services.career_intelligence.risk_analyzer import detect_career_risks
        risks = detect_career_risks(self._profile(_EMPTY))
        assert isinstance(risks, list)


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Recommendation Engine
# ═══════════════════════════════════════════════════════════════════════════════

class TestRecommendationEngine:
    def _profile(self, user):
        from services.career_intelligence.career_profiler import build_career_profile
        return build_career_profile(user)

    def test_returns_7_categories(self):
        from services.career_intelligence.recommendation_engine import generate_recommendations
        recs = generate_recommendations(self._profile(_PHD))
        assert set(recs.keys()) == {"courses", "conferences", "mentors", "funding",
                                    "topics", "peer_review", "books"}

    def test_courses_for_phd(self):
        from services.career_intelligence.recommendation_engine import generate_recommendations
        recs = generate_recommendations(self._profile(_PHD))
        assert len(recs["courses"]) >= 1

    def test_funding_for_postdoc(self):
        from services.career_intelligence.recommendation_engine import generate_recommendations
        recs = generate_recommendations(self._profile(_POSTDOC))
        assert len(recs["funding"]) >= 1

    def test_all_recs_have_title(self):
        from services.career_intelligence.recommendation_engine import generate_recommendations
        recs = generate_recommendations(self._profile(_PHD))
        for cat, items in recs.items():
            for item in items:
                assert item.get("title"), f"Missing title in category {cat}"

    def test_grant_course_when_no_grants(self):
        from services.career_intelligence.recommendation_engine import generate_recommendations
        recs = generate_recommendations(self._profile(_PHD))
        course_titles = [r["title"] for r in recs["courses"]]
        assert any("grant" in t.lower() or "Grant" in t for t in course_titles)

    def test_conference_recommendations_present(self):
        from services.career_intelligence.recommendation_engine import generate_recommendations
        recs = generate_recommendations(self._profile(_POSTDOC))
        assert len(recs["conferences"]) >= 1

    def test_mentor_recommendations_present(self):
        from services.career_intelligence.recommendation_engine import generate_recommendations
        recs = generate_recommendations(self._profile(_PHD))
        assert len(recs["mentors"]) >= 1

    def test_empty_profile_no_crash(self):
        from services.career_intelligence.recommendation_engine import generate_recommendations
        recs = generate_recommendations(self._profile(_EMPTY))
        assert isinstance(recs, dict)


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Copilot Integration
# ═══════════════════════════════════════════════════════════════════════════════

class TestCopilotIntegration:
    def _profile(self, user):
        from services.career_intelligence.career_profiler import build_career_profile
        return build_career_profile(user)

    def test_returns_list(self):
        from services.career_intelligence.copilot_integration import generate_copilot_suggestions
        result = generate_copilot_suggestions(self._profile(_PHD))
        assert isinstance(result, list)

    def test_suggestions_have_required_keys(self):
        from services.career_intelligence.copilot_integration import generate_copilot_suggestions
        result = generate_copilot_suggestions(self._profile(_POSTDOC))
        for s in result:
            for key in ["category", "suggestion", "action", "urgency"]:
                assert key in s

    def test_phd_gets_career_planning_suggestion(self):
        from services.career_intelligence.copilot_integration import generate_copilot_suggestions
        result = generate_copilot_suggestions(self._profile(_PHD))
        categories = [s["category"] for s in result]
        assert "career_planning" in categories

    def test_postdoc_gets_critical_career_planning(self):
        from services.career_intelligence.copilot_integration import generate_copilot_suggestions
        result = generate_copilot_suggestions(self._profile(_POSTDOC))
        critical = [s for s in result if s["urgency"] == "critical"]
        assert len(critical) >= 1

    def test_no_grant_triggers_funding_suggestion(self):
        from services.career_intelligence.copilot_integration import generate_copilot_suggestions
        result = generate_copilot_suggestions(self._profile(_PHD))
        # PHD with no grants should have a grant-related suggestion
        grant_sugs = [s for s in result if "grant" in s["action"].lower()
                      or "Grant" in s["suggestion"]]
        assert len(grant_sugs) >= 1

    def test_max_8_suggestions(self):
        from services.career_intelligence.copilot_integration import generate_copilot_suggestions
        for user in [_PHD, _POSTDOC, _PROFESSOR]:
            result = generate_copilot_suggestions(self._profile(user))
            assert len(result) <= 8


# ═══════════════════════════════════════════════════════════════════════════════
# 11. Visualization Builder
# ═══════════════════════════════════════════════════════════════════════════════

class TestVisualizationBuilder:
    def _profile(self, user):
        from services.career_intelligence.career_profiler import build_career_profile
        return build_career_profile(user)

    def test_career_timeline_has_data(self):
        from services.career_intelligence.visualization_builder import build_visualization
        result = build_visualization("career_timeline", profile=self._profile(_POSTDOC))
        assert result["type"] == "career_timeline"
        assert len(result["data"]) >= 1

    def test_goal_progress_viz(self):
        from services.career_intelligence.visualization_builder import build_visualization
        goals = [{"description": "Publish 5 papers", "progress": 0.4, "status": "in_progress"}]
        result = build_visualization("goal_progress", goals=goals)
        assert result["type"] == "goal_progress"
        assert len(result["data"]) == 1

    def test_publication_growth_viz(self):
        from services.career_intelligence.visualization_builder import build_visualization
        result = build_visualization("publication_growth", profile=self._profile(_PROFESSOR))
        assert "series" in result
        assert result["total"] == 85

    def test_citation_growth_viz(self):
        from services.career_intelligence.visualization_builder import build_visualization
        result = build_visualization("citation_growth", profile=self._profile(_PROFESSOR))
        assert "h_index" in result
        assert result["h_index"] == 28

    def test_collaboration_network_viz(self):
        from services.career_intelligence.visualization_builder import build_visualization
        result = build_visualization("collaboration_network", profile=self._profile(_PROFESSOR))
        assert "nodes" in result
        assert "edges" in result
        assert len(result["nodes"]) >= 1

    def test_career_readiness_viz_dimensions(self):
        from services.career_intelligence.visualization_builder import build_visualization
        result = build_visualization("career_readiness", profile=self._profile(_PROFESSOR))
        assert "dimensions" in result
        assert len(result["dimensions"]) == 6

    def test_research_impact_viz(self):
        from services.career_intelligence.visualization_builder import build_visualization
        result = build_visualization("research_impact", profile=self._profile(_PROFESSOR))
        assert "metrics" in result
        assert len(result["metrics"]) == 3

    def test_unknown_viz_type_returns_error(self):
        from services.career_intelligence.visualization_builder import build_visualization
        result = build_visualization("nonexistent_viz_type")
        assert "error" in result

    def test_skill_radar_viz_with_report(self):
        from services.career_intelligence.career_profiler import build_career_profile
        from services.career_intelligence.skill_gap_analyzer import analyse_skill_gaps
        from services.career_intelligence.visualization_builder import build_visualization
        profile = build_career_profile(_POSTDOC)
        report  = analyse_skill_gaps(profile)
        result  = build_visualization("skill_radar", skill_report=report)
        assert result["type"] == "skill_radar"
        assert len(result["labels"]) == 15

    def test_promotion_readiness_viz(self):
        from services.career_intelligence.career_profiler import build_career_profile
        from services.career_intelligence.models import PromotionTarget
        from services.career_intelligence.promotion_readiness import assess_promotion_readiness
        from services.career_intelligence.visualization_builder import build_visualization
        profile   = build_career_profile(_PROFESSOR)
        readiness = assess_promotion_readiness(profile, PromotionTarget.PROFESSOR)
        result    = build_visualization("promotion_readiness", readiness=readiness)
        assert result["type"] == "promotion_readiness"
        assert "gauge" in result


# ═══════════════════════════════════════════════════════════════════════════════
# 12. Export Engine
# ═══════════════════════════════════════════════════════════════════════════════

class TestExportEngine:
    def _profile(self, user):
        from services.career_intelligence.career_profiler import build_career_profile
        return build_career_profile(user)

    def test_pdf_career_report(self):
        from services.career_intelligence.export_engine import generate_export
        result = generate_export("career_report", "pdf", self._profile(_POSTDOC))
        assert result["format"] == "pdf"
        assert "sections" in result
        assert len(result["sections"]) >= 3

    def test_docx_promotion_portfolio(self):
        from services.career_intelligence.export_engine import generate_export
        result = generate_export("promotion_portfolio", "docx", self._profile(_PROFESSOR))
        assert result["format"] == "docx"
        assert "sections" in result

    def test_markdown_research_development(self):
        from services.career_intelligence.export_engine import generate_export
        result = generate_export("research_development_plan", "markdown", self._profile(_PHD))
        assert result["format"] == "markdown"
        assert "content" in result
        assert "##" in result["content"]

    def test_all_report_types_no_crash(self):
        from services.career_intelligence.export_engine import generate_export
        from services.career_intelligence.models import ExportReportType
        for rt in ExportReportType:
            result = generate_export(rt.value, "pdf", self._profile(_POSTDOC))
            assert "sections" in result

    def test_all_formats_no_crash(self):
        from services.career_intelligence.export_engine import generate_export
        from services.career_intelligence.models import ExportFormat
        for fmt in ExportFormat:
            result = generate_export("career_report", fmt.value, self._profile(_PHD))
            assert result.get("format") == fmt.value

    def test_invalid_type_falls_back(self):
        from services.career_intelligence.export_engine import generate_export
        result = generate_export("nonexistent_type", "pdf", self._profile(_PHD))
        assert "sections" in result

    def test_sections_have_title_and_content(self):
        from services.career_intelligence.export_engine import generate_export
        result = generate_export("career_report", "pdf", self._profile(_PROFESSOR))
        for sec in result["sections"]:
            assert "title" in sec
            assert "content" in sec

    def test_title_contains_name(self):
        from services.career_intelligence.export_engine import generate_export
        result = generate_export("career_report", "pdf", self._profile(_PROFESSOR))
        assert "Carol Jones" in result["title"]


# ═══════════════════════════════════════════════════════════════════════════════
# 13. Telemetry
# ═══════════════════════════════════════════════════════════════════════════════

class TestTelemetry:
    def _fresh(self):
        from services.career_intelligence.telemetry import CareerTelemetry
        CareerTelemetry._instance = None
        from services.career_intelligence.telemetry import get_telemetry
        return get_telemetry()

    def test_singleton_same_instance(self):
        from services.career_intelligence.telemetry import get_telemetry
        t1 = get_telemetry()
        t2 = get_telemetry()
        assert t1 is t2

    def test_inc_profile_builds(self):
        tel = self._fresh()
        tel.inc("profile_builds")
        tel.inc("profile_builds")
        assert tel.profile_builds == 2

    def test_record_latency(self):
        tel = self._fresh()
        tel.record_latency(0.123)
        tel.record_latency(0.456)
        assert len(tel.latencies) == 2

    def test_to_dict_keys(self):
        tel = self._fresh()
        d = tel.to_dict()
        for key in ["profile_builds", "roadmap_builds", "skill_analyses",
                    "promotion_checks", "risk_analyses", "exports",
                    "full_analyses", "errors", "avg_latency_seconds",
                    "total_requests"]:
            assert key in d

    def test_avg_latency_computed(self):
        tel = self._fresh()
        tel.record_latency(0.1)
        tel.record_latency(0.3)
        d = tel.to_dict()
        assert abs(d["avg_latency_seconds"] - 0.2) < 0.01

    def test_latency_capped_at_500(self):
        tel = self._fresh()
        for _ in range(600):
            tel.record_latency(0.01)
        assert len(tel.latencies) == 500


# ═══════════════════════════════════════════════════════════════════════════════
# 14. Engine Integration
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineIntegration:
    def _engine(self):
        from services.career_intelligence.engine import (
            CareerIntelligenceEngine, reset_career_engine,
        )
        reset_career_engine()
        return CareerIntelligenceEngine()

    def test_build_profile(self):
        engine = self._engine()
        result = engine.build_profile(_POSTDOC)
        assert result["career_stage"] == "postdoc"
        assert "overall_score" in result

    def test_build_roadmap(self):
        engine = self._engine()
        result = engine.build_roadmap(_PHD, horizon="3_year")
        assert result["horizon"] == "3_year"
        assert "milestones" in result

    def test_evaluate_goals_default(self):
        engine = self._engine()
        result = engine.evaluate_goals(_PHD)
        assert "goals" in result
        assert result["total"] >= 1

    def test_evaluate_goals_custom(self):
        engine = self._engine()
        goals  = [{"goal_type": "publication", "target_value": 5, "current_value": 2}]
        result = engine.evaluate_goals(_PHD, goals=goals)
        assert result["total"] == 1

    def test_analyse_skill_gaps(self):
        engine = self._engine()
        result = engine.analyse_skill_gaps(_POSTDOC)
        assert "assessments" in result
        assert len(result["assessments"]) == 15

    def test_assess_promotion(self):
        engine = self._engine()
        result = engine.assess_promotion(_PROFESSOR, target="professor")
        assert 0.0 <= result["overall_readiness"] <= 1.0

    def test_analyse_productivity(self):
        engine = self._engine()
        result = engine.analyse_productivity(_PROFESSOR)
        assert "overall_productivity" in result

    def test_detect_risks(self):
        engine = self._engine()
        result = engine.detect_risks(_PHD)
        assert "risks" in result
        assert "total" in result

    def test_generate_recommendations(self):
        engine = self._engine()
        result = engine.generate_recommendations(_POSTDOC)
        assert "courses" in result
        assert "funding" in result

    def test_copilot_suggestions(self):
        engine = self._engine()
        result = engine.copilot_suggestions(_PHD)
        assert "suggestions" in result
        assert result["total"] >= 1

    def test_visualization(self):
        engine = self._engine()
        result = engine.visualization(_PROFESSOR, "career_readiness")
        assert result.get("type") == "career_readiness"

    def test_export_report_pdf(self):
        engine = self._engine()
        result = engine.export_report(_POSTDOC, report_type="career_report",
                                      export_format="pdf")
        assert result["format"] == "pdf"
        assert "sections" in result

    def test_export_report_markdown(self):
        engine = self._engine()
        result = engine.export_report(_PHD, report_type="research_development_plan",
                                      export_format="markdown")
        assert result["format"] == "markdown"

    def test_full_analysis_keys(self):
        engine = self._engine()
        result = engine.full_analysis(_POSTDOC)
        for key in ["profile", "roadmap", "goals", "skill_gaps", "promotion",
                    "productivity", "risks", "recommendations", "copilot"]:
            assert key in result, f"Missing key: {key}"

    def test_full_analysis_profile_correct(self):
        engine = self._engine()
        result = engine.full_analysis(_PROFESSOR)
        assert result["profile"]["career_stage"] == "professor"

    def test_admin_analytics_aggregation(self):
        engine = self._engine()
        result = engine.admin_analytics([_PHD, _POSTDOC, _PROFESSOR])
        assert result["total_users"] == 3
        assert "avg_h_index" in result
        assert "stage_distribution" in result

    def test_admin_analytics_empty(self):
        engine = self._engine()
        result = engine.admin_analytics([])
        assert result["total_users"] == 0


# ═══════════════════════════════════════════════════════════════════════════════
# 15. Async Engine Singleton
# ═══════════════════════════════════════════════════════════════════════════════

class TestAsyncEngineSingleton:
    def test_singleton_returns_same_instance(self):
        from services.career_intelligence.engine import (
            get_career_engine, reset_career_engine,
        )
        reset_career_engine()
        e1 = asyncio.run(get_career_engine())
        e2 = asyncio.run(get_career_engine())
        assert e1 is e2

    def test_reset_clears_singleton(self):
        from services.career_intelligence.engine import (
            get_career_engine, reset_career_engine,
        )
        reset_career_engine()
        e1 = asyncio.run(get_career_engine())
        reset_career_engine()
        e2 = asyncio.run(get_career_engine())
        assert e1 is not e2

    def test_engine_is_correct_type(self):
        from services.career_intelligence.engine import (
            CareerIntelligenceEngine, get_career_engine, reset_career_engine,
        )
        reset_career_engine()
        e = asyncio.run(get_career_engine())
        assert isinstance(e, CareerIntelligenceEngine)
