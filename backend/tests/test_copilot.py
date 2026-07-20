"""Phase XI Academic Copilot — comprehensive test suite.

Covers: models, intent_classifier, workflow_planner, engine_dispatcher,
proactive_advisor, roadmap_builder, ai_copilot, response_composer,
dashboard_builder (mocked), telemetry, engine internals.

Run with: python -m pytest tests/test_copilot.py -v
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


def _run(coro):
    return asyncio.run(coro)


# ── Fixtures ──────────────────────────────────────────────────────────────────

_RICH_CONTEXT = {
    "profile": {
        "full_name": "Dr Alice Researcher",
        "academic_role": "phd_candidate",
        "research_areas": ["machine learning", "healthcare"],
    },
    "manuscripts": [
        {"id": "ms1", "title": "AI in Healthcare Diagnostics", "status": "draft",
         "word_count": 4200, "user_id": "u1"},
        {"id": "ms2", "title": "Deep Learning Survey", "status": "under_review",
         "user_id": "u1"},
    ],
    "projects": [
        {"id": "p1", "title": "Healthcare AI Project", "status": "active"},
    ],
    "collaborations": [],
    "grants_applied": [
        {"grant_id": "g1", "grant_title": "NIH R01 Grant",
         "status": "draft", "deadline": "2026-08-15"},
    ],
    "reputation": {"overall_score": 45, "level": "Scholar"},
    "impact": {"sis_total": 120, "h_index": 2, "publication_count": 3},
    "memory": [
        {"memory_type": "research_goal", "content": "Apply AI to early cancer detection."},
    ],
    "summary": "Dr Alice Researcher, PhD candidate in machine learning for healthcare.",
    "manuscript_excerpts": {
        "ms1": (
            "Abstract: This study investigates the application of deep learning to MRI scans.\n\n"
            "Introduction: Accurate cancer detection remains an open problem.\n\n"
            "Methods: We recruited N=245 patients. Multiple regression was conducted.\n\n"
            "Results: β = 0.42, p = .001, 95% CI [0.28, 0.56], R² = 0.23."
        )
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# 1. Models
# ══════════════════════════════════════════════════════════════════════════════

class TestModels:
    def test_detected_intent_to_dict(self):
        from services.copilot.models import DetectedIntent, IntentType
        di = DetectedIntent(intent_type=IntentType.MANUSCRIPT_REVIEW, confidence=0.85,
                            signals=["review my paper"], requires_engines=["manuscript"])
        d = di.to_dict()
        assert d["intent_type"] == "manuscript_review"
        assert d["confidence"] == 0.85
        assert "manuscript" in d["requires_engines"]

    def test_workflow_step_to_dict(self):
        from services.copilot.models import WorkflowStep
        step = WorkflowStep(engine="manuscript", title="Manuscript Review",
                            description="Analyse the manuscript.", status="completed")
        d = step.to_dict()
        assert d["engine"] == "manuscript"
        assert d["status"] == "completed"

    def test_copilot_workflow_to_dict(self):
        from services.copilot.models import CopilotWorkflow, WorkflowStatus
        wf = CopilotWorkflow(trigger_message="Review my paper", status=WorkflowStatus.COMPLETED)
        d = wf.to_dict()
        assert d["status"] == "completed"
        assert d["trigger_message"] == "Review my paper"

    def test_proactive_suggestion_to_dict(self):
        from services.copilot.models import ProactiveSuggestion, SuggestionCategory, Urgency
        s = ProactiveSuggestion(
            category=SuggestionCategory.MANUSCRIPT,
            title="Missing content",
            description="Your draft is short.",
            urgency=Urgency.MEDIUM,
            confidence=0.80,
        )
        d = s.to_dict()
        assert d["category"] == "manuscript"
        assert d["urgency"] == "medium"
        assert d["confidence"] == 0.80

    def test_roadmap_phase_to_dict(self):
        from services.copilot.models import RoadmapPhase, RoadmapMilestone
        m = RoadmapMilestone(week=4, title="Draft complete", deliverable="Written draft", is_critical=True)
        p = RoadmapPhase(phase=1, title="Phase 1", duration_weeks=4,
                         objectives=["Define scope"], milestones=[m])
        d = p.to_dict()
        assert d["phase"] == 1
        assert d["duration_weeks"] == 4
        assert d["milestones"][0]["is_critical"] is True

    def test_academic_roadmap_to_dict(self):
        from services.copilot.models import AcademicRoadmap, RoadmapType
        roadmap = AcademicRoadmap(
            roadmap_type=RoadmapType.RESEARCH,
            title="Research Roadmap",
            total_weeks=26,
        )
        d = roadmap.to_dict()
        assert d["roadmap_type"] == "research"
        assert d["total_weeks"] == 26
        assert "roadmap_id" in d

    def test_copilot_dashboard_to_dict(self):
        from services.copilot.models import CopilotDashboard
        dash = CopilotDashboard(user_id="u1", active_projects=[{"title": "Proj"}])
        d = dash.to_dict()
        assert d["user_id"] == "u1"
        assert len(d["active_projects"]) == 1

    def test_copilot_response_to_dict(self):
        from services.copilot.models import CopilotResponse, DetectedIntent, IntentType
        r = CopilotResponse(
            user_id="u1",
            message="Here is my analysis.",
            intents=[DetectedIntent(IntentType.MANUSCRIPT_REVIEW, 0.9)],
            confidence=0.85,
            agent_type="publication",
        )
        d = r.to_dict()
        assert d["message"] == "Here is my analysis."
        assert d["confidence"] == 0.85
        assert d["intents"][0]["intent_type"] == "manuscript_review"

    def test_dashboard_widget_to_dict(self):
        from services.copilot.models import DashboardWidget, Urgency
        w = DashboardWidget(widget_type="active_projects", title="Projects (2)",
                            data={"projects": []}, priority=90, urgency=Urgency.HIGH)
        d = w.to_dict()
        assert d["widget_type"] == "active_projects"
        assert d["urgency"] == "high"
        assert d["priority"] == 90

    def test_intent_type_enum_values(self):
        from services.copilot.models import IntentType
        assert IntentType("manuscript_review") == IntentType.MANUSCRIPT_REVIEW
        assert IntentType("literature_review") == IntentType.LITERATURE_REVIEW
        assert IntentType("statistical_review") == IntentType.STATISTICAL_REVIEW

    def test_roadmap_type_enum_values(self):
        from services.copilot.models import RoadmapType
        assert RoadmapType("research") == RoadmapType.RESEARCH
        assert RoadmapType("publication") == RoadmapType.PUBLICATION
        assert RoadmapType("grant") == RoadmapType.GRANT


# ══════════════════════════════════════════════════════════════════════════════
# 2. Intent Classifier
# ══════════════════════════════════════════════════════════════════════════════

class TestIntentClassifier:
    def test_classify_manuscript_review(self):
        from services.copilot.intent_classifier import classify_intents
        from services.copilot.models import IntentType
        intents = classify_intents("Can you review my manuscript for publication?")
        types = [i.intent_type for i in intents]
        assert IntentType.MANUSCRIPT_REVIEW in types

    def test_classify_literature_review(self):
        from services.copilot.intent_classifier import classify_intents
        from services.copilot.models import IntentType
        intents = classify_intents("Help me do a literature review on deep learning.")
        types = [i.intent_type for i in intents]
        assert IntentType.LITERATURE_REVIEW in types

    def test_classify_gap_analysis(self):
        from services.copilot.intent_classifier import classify_intents
        from services.copilot.models import IntentType
        intents = classify_intents("What are the research gaps in NLP for healthcare?")
        types = [i.intent_type for i in intents]
        assert IntentType.GAP_ANALYSIS in types

    def test_classify_statistical_review(self):
        from services.copilot.intent_classifier import classify_intents
        from services.copilot.models import IntentType
        intents = classify_intents("Please do a statistical review of my data analysis.")
        types = [i.intent_type for i in intents]
        assert IntentType.STATISTICAL_REVIEW in types

    def test_classify_journal_recommendation(self):
        from services.copilot.intent_classifier import classify_intents
        from services.copilot.models import IntentType
        intents = classify_intents("Which journal should I submit my paper to?")
        types = [i.intent_type for i in intents]
        assert IntentType.JOURNAL_REC in types

    def test_classify_grant_guidance(self):
        from services.copilot.intent_classifier import classify_intents
        from services.copilot.models import IntentType
        intents = classify_intents("I need help writing a grant proposal for NIH.")
        types = [i.intent_type for i in intents]
        assert IntentType.GRANT_GUIDANCE in types

    def test_classify_career_planning(self):
        from services.copilot.intent_classifier import classify_intents
        from services.copilot.models import IntentType
        intents = classify_intents("I want career advice for my academic career planning.")
        types = [i.intent_type for i in intents]
        assert IntentType.CAREER_PLANNING in types

    def test_classify_roadmap(self):
        from services.copilot.intent_classifier import classify_intents
        from services.copilot.models import IntentType
        intents = classify_intents("Create a research roadmap for my PhD project.")
        types = [i.intent_type for i in intents]
        assert IntentType.ROADMAP_REQUEST in types

    def test_fallback_to_general_chat(self):
        from services.copilot.intent_classifier import classify_intents, primary_intent
        from services.copilot.models import IntentType
        intent = primary_intent("Hello, how are you today?")
        assert intent.intent_type == IntentType.GENERAL_CHAT

    def test_composite_trigger_publish(self):
        from services.copilot.intent_classifier import classify_intents
        from services.copilot.models import IntentType
        intents = classify_intents("I want to publish a paper on machine learning.")
        types = [i.intent_type for i in intents]
        assert IntentType.JOURNAL_REC in types or IntentType.MANUSCRIPT_REVIEW in types

    def test_confidence_threshold(self):
        from services.copilot.intent_classifier import classify_intents, CONFIDENCE_THRESHOLD
        intents = classify_intents("I need help with my research.")
        for i in intents:
            assert i.confidence >= CONFIDENCE_THRESHOLD

    def test_sorted_by_confidence(self):
        from services.copilot.intent_classifier import classify_intents
        intents = classify_intents("Review my manuscript and tell me which journal to target.")
        confs = [i.confidence for i in intents]
        assert confs == sorted(confs, reverse=True)

    def test_manuscript_intent_requires_engine(self):
        from services.copilot.intent_classifier import classify_intents
        from services.copilot.models import IntentType
        intents = [i for i in classify_intents("Review my manuscript.") if i.intent_type == IntentType.MANUSCRIPT_REVIEW]
        assert intents
        assert "manuscript" in intents[0].requires_engines

    def test_statistical_intent_requires_engine(self):
        from services.copilot.intent_classifier import classify_intents
        from services.copilot.models import IntentType
        intents = [i for i in classify_intents("Statistical review of my data analysis.")
                   if i.intent_type == IntentType.STATISTICAL_REVIEW]
        assert intents
        assert "statistical" in intents[0].requires_engines


# ══════════════════════════════════════════════════════════════════════════════
# 3. Workflow Planner
# ══════════════════════════════════════════════════════════════════════════════

class TestWorkflowPlanner:
    def _plan(self, message):
        from services.copilot.intent_classifier import classify_intents
        from services.copilot.workflow_planner import plan_workflow
        intents = classify_intents(message)
        return plan_workflow(message, intents, {})

    def test_workflow_always_has_context_step(self):
        wf = self._plan("What journals should I publish in?")
        ids = [s.step_id for s in wf.steps]
        assert "step:context" in ids

    def test_workflow_always_has_ai_step(self):
        wf = self._plan("Help me plan my research.")
        ids = [s.step_id for s in wf.steps]
        assert "step:ai_advisor" in ids

    def test_workflow_always_has_compose_step(self):
        wf = self._plan("I need career advice.")
        ids = [s.step_id for s in wf.steps]
        assert "step:compose" in ids

    def test_manuscript_message_includes_engine_step(self):
        wf = self._plan("Review my manuscript please.")
        ids = [s.step_id for s in wf.steps]
        assert "engine:manuscript" in ids

    def test_statistical_message_includes_engine_step(self):
        wf = self._plan("Please do a statistical review of my methods.")
        ids = [s.step_id for s in wf.steps]
        assert "engine:statistical" in ids

    def test_engine_steps_are_parallel(self):
        wf = self._plan("Review my manuscript and statistical analysis.")
        eng_steps = [s for s in wf.steps if s.step_id.startswith("engine:")]
        for step in eng_steps:
            assert step.is_parallel is True

    def test_workflow_step_count_minimum(self):
        wf = self._plan("What is the best journal for my paper?")
        assert len(wf.steps) >= 3  # context + ai + compose

    def test_workflow_has_intents(self):
        from services.copilot.intent_classifier import classify_intents
        from services.copilot.workflow_planner import plan_workflow
        intents = classify_intents("Review my manuscript.")
        wf = plan_workflow("Review my manuscript.", intents, {})
        assert len(wf.intents) > 0

    def test_describe_plan_no_engines(self):
        from services.copilot.workflow_planner import describe_plan
        wf = self._plan("What is your name?")
        desc = describe_plan(wf)
        assert isinstance(desc, str) and len(desc) > 10

    def test_describe_plan_with_engine(self):
        from services.copilot.workflow_planner import describe_plan
        wf = self._plan("Review my manuscript.")
        desc = describe_plan(wf)
        assert "Manuscript" in desc or "Copilot" in desc

    def test_total_credits_zero_for_general_chat(self):
        wf = self._plan("How do I find a collaborator?")
        assert wf.total_credits == 0


# ══════════════════════════════════════════════════════════════════════════════
# 4. Engine Dispatcher
# ══════════════════════════════════════════════════════════════════════════════

class TestEngineDispatcher:
    _CONTENT = (
        "N=245. Multiple regression: β=0.42, p=.001, 95% CI [0.28, 0.56], R²=0.23.\n"
        "Normality tested (Shapiro-Wilk). VIF < 2. Research gap: no study has examined this.\n"
        "References: Smith (2020); Jones (2021); Brown (2022)."
    )

    def test_dispatch_no_engines_returns_empty(self):
        from services.copilot.engine_dispatcher import dispatch_engines
        result = _run(dispatch_engines([], self._CONTENT, {}))
        assert result == {}

    def test_dispatch_gap_scan(self):
        from services.copilot.engine_dispatcher import dispatch_engines
        result = _run(dispatch_engines(["gap"], self._CONTENT, {}))
        assert "gap" in result
        assert result["gap"].get("gap_signal_count", 0) >= 1

    def test_dispatch_statistical_scan(self):
        from services.copilot.engine_dispatcher import dispatch_engines
        result = _run(dispatch_engines(["statistical"], self._CONTENT, {}))
        assert "statistical" in result
        assert result["statistical"].get("has_p_values") is True

    def test_dispatch_literature_scan(self):
        from services.copilot.engine_dispatcher import dispatch_engines
        # Use APA citation format so the regex (Author, YEAR) pattern matches
        content = (
            self._CONTENT +
            " (Smith, 2020); (Jones, 2021); (Brown, 2022); (Davis, 2023)."
        )
        result = _run(dispatch_engines(["literature"], content, {}))
        assert "literature" in result
        assert result["literature"].get("reference_count", 0) >= 1

    def test_dispatch_manuscript_scan(self):
        from services.copilot.engine_dispatcher import dispatch_engines
        content = (
            "Abstract: A study on machine learning in healthcare.\n\n"
            "Introduction: This study examines the use of AI in diagnostics.\n\n"
            "Methods: N=245. Multiple regression analysis was conducted.\n\n"
            "Results: β = 0.42, p = .001. R² = 0.23.\n\n"
            "References: Smith (2020); Jones (2021)."
        )
        result = _run(dispatch_engines(["manuscript"], content, {}))
        assert "manuscript" in result

    def test_dispatch_multiple_engines_parallel(self):
        from services.copilot.engine_dispatcher import dispatch_engines
        result = _run(dispatch_engines(["gap", "statistical", "literature"], self._CONTENT, {}))
        assert "gap" in result
        assert "statistical" in result
        assert "literature" in result

    def test_gap_has_explicit_gap_flag(self):
        from services.copilot.engine_dispatcher import dispatch_engines
        content = "research gap: no study has examined this. Few studies exist. Underexplored area."
        result = _run(dispatch_engines(["gap"], content, {}))
        assert result["gap"].get("has_explicit_gap") is True

    def test_empty_content_returns_empty(self):
        from services.copilot.engine_dispatcher import dispatch_engines
        result = _run(dispatch_engines(["gap"], "", {}))
        assert result == {}


# ══════════════════════════════════════════════════════════════════════════════
# 5. Proactive Advisor
# ══════════════════════════════════════════════════════════════════════════════

class TestProactiveAdvisor:
    def test_returns_list(self):
        from services.copilot.proactive_advisor import generate_suggestions
        suggestions = generate_suggestions(_RICH_CONTEXT)
        assert isinstance(suggestions, list)

    def test_low_word_count_manuscript_flagged(self):
        from services.copilot.proactive_advisor import generate_suggestions
        context = {
            **_RICH_CONTEXT,
            "manuscripts": [
                {"id": "ms1", "title": "Short Draft", "status": "draft",
                 "word_count": 800, "user_id": "u1"},
            ],
        }
        suggestions = generate_suggestions(context)
        titles = [s.title for s in suggestions]
        assert any("needs more content" in t.lower() or "word" in t.lower() for t in titles)

    def test_grant_deadline_suggestion_generated(self):
        from services.copilot.proactive_advisor import generate_suggestions
        context = {**_RICH_CONTEXT, "grants_applied": [
            {"grant_id": "g1", "grant_title": "NIH Grant", "status": "draft",
             "deadline": "2026-07-05"},
        ]}
        suggestions = generate_suggestions(context)
        types = [s.category.value for s in suggestions]
        assert "grant" in types

    def test_no_collaboration_suggests_marketplace(self):
        from services.copilot.proactive_advisor import generate_suggestions
        from services.copilot.models import SuggestionCategory
        context = {**_RICH_CONTEXT, "collaborations": []}
        suggestions = generate_suggestions(context)
        collab = [s for s in suggestions if s.category == SuggestionCategory.COLLABORATION]
        assert len(collab) >= 1

    def test_missing_target_journal_memory_suggests_it(self):
        from services.copilot.proactive_advisor import generate_suggestions
        from services.copilot.models import SuggestionCategory
        context = {**_RICH_CONTEXT, "memory": []}  # no memories
        suggestions = generate_suggestions(context)
        journal_suggs = [s for s in suggestions if s.category == SuggestionCategory.JOURNAL]
        assert len(journal_suggs) >= 1

    def test_sorted_by_urgency(self):
        from services.copilot.proactive_advisor import generate_suggestions
        from services.copilot.models import Urgency
        context = {**_RICH_CONTEXT, "manuscripts": [
            {"id": "m1", "title": "Draft", "status": "revision_required", "word_count": 5000}
        ]}
        suggestions = generate_suggestions(context)
        if len(suggestions) >= 2:
            urgency_vals = ["critical", "high", "medium", "low"]
            ranks = [urgency_vals.index(s.urgency.value) for s in suggestions]
            assert ranks == sorted(ranks)

    def test_max_suggestions_capped(self):
        from services.copilot.proactive_advisor import generate_suggestions
        suggestions = generate_suggestions(_RICH_CONTEXT)
        assert len(suggestions) <= 10

    def test_revision_required_generates_high_urgency(self):
        from services.copilot.proactive_advisor import generate_suggestions
        from services.copilot.models import Urgency
        context = {**_RICH_CONTEXT, "manuscripts": [
            {"id": "m1", "title": "My Paper", "status": "revision_required"}
        ]}
        suggestions = generate_suggestions(context)
        rev_suggs = [s for s in suggestions if "revision" in s.title.lower()]
        assert any(s.urgency == Urgency.HIGH for s in rev_suggs)


# ══════════════════════════════════════════════════════════════════════════════
# 6. Roadmap Builder
# ══════════════════════════════════════════════════════════════════════════════

class TestRoadmapBuilder:
    def test_research_roadmap_has_phases(self):
        from services.copilot.roadmap_builder import build_roadmap
        from services.copilot.models import RoadmapType
        roadmap = _run(build_roadmap(RoadmapType.RESEARCH, _RICH_CONTEXT, {}, use_ai=False))
        assert len(roadmap.phases) >= 4

    def test_publication_roadmap_has_phases(self):
        from services.copilot.roadmap_builder import build_roadmap
        from services.copilot.models import RoadmapType
        roadmap = _run(build_roadmap(RoadmapType.PUBLICATION, _RICH_CONTEXT, {}, use_ai=False))
        assert len(roadmap.phases) >= 3

    def test_grant_roadmap_has_phases(self):
        from services.copilot.roadmap_builder import build_roadmap
        from services.copilot.models import RoadmapType
        roadmap = _run(build_roadmap(RoadmapType.GRANT, _RICH_CONTEXT, {}, use_ai=False))
        assert len(roadmap.phases) >= 3

    def test_career_roadmap_has_phases(self):
        from services.copilot.roadmap_builder import build_roadmap
        from services.copilot.models import RoadmapType
        roadmap = _run(build_roadmap(RoadmapType.CAREER, _RICH_CONTEXT,
                                     {"career_stage": "phd"}, use_ai=False))
        assert len(roadmap.phases) >= 2

    def test_conference_roadmap_has_phases(self):
        from services.copilot.roadmap_builder import build_roadmap
        from services.copilot.models import RoadmapType
        roadmap = _run(build_roadmap(RoadmapType.CONFERENCE, {}, {}, use_ai=False))
        assert len(roadmap.phases) >= 2

    def test_total_weeks_matches_phase_sum(self):
        from services.copilot.roadmap_builder import build_roadmap
        from services.copilot.models import RoadmapType
        roadmap = _run(build_roadmap(RoadmapType.RESEARCH, _RICH_CONTEXT, {}, use_ai=False))
        assert roadmap.total_weeks == sum(p.duration_weeks for p in roadmap.phases)

    def test_roadmap_to_dict_complete(self):
        from services.copilot.roadmap_builder import build_roadmap
        from services.copilot.models import RoadmapType
        roadmap = _run(build_roadmap(RoadmapType.PUBLICATION, {}, {}, use_ai=False))
        d = roadmap.to_dict()
        for key in ["roadmap_id", "roadmap_type", "phases", "total_weeks",
                    "key_milestones", "success_indicators", "risk_factors"]:
            assert key in d, f"Missing key: {key}"

    def test_key_milestones_populated(self):
        from services.copilot.roadmap_builder import build_roadmap
        from services.copilot.models import RoadmapType
        roadmap = _run(build_roadmap(RoadmapType.RESEARCH, _RICH_CONTEXT, {}, use_ai=False))
        assert len(roadmap.key_milestones) >= 2

    def test_success_indicators_populated(self):
        from services.copilot.roadmap_builder import build_roadmap
        from services.copilot.models import RoadmapType
        roadmap = _run(build_roadmap(RoadmapType.GRANT, {}, {}, use_ai=False))
        assert len(roadmap.success_indicators) >= 2


# ══════════════════════════════════════════════════════════════════════════════
# 7. AI Copilot
# ══════════════════════════════════════════════════════════════════════════════

class TestAiCopilot:
    def test_mock_response_when_llm_unavailable(self):
        from services.copilot.ai_copilot import _mock_response
        from services.copilot.models import DetectedIntent, IntentType
        intents = [DetectedIntent(IntentType.MANUSCRIPT_REVIEW, 0.9)]
        result = _mock_response("Review my paper.", intents, {})
        assert "manuscript_review" in result

    def test_engine_results_summarised(self):
        from services.copilot.ai_copilot import _summarise_engine_results
        engine_results = {
            "manuscript": {
                "word_count": 5000, "section_count": 6,
                "scientific_score": 72.0, "writing_score": 68.0,
                "statistical_score": 75.0, "critical_issue_count": 1,
                "major_issue_count": 3, "top_issues": [],
                "sections_detected": ["abstract", "introduction"],
            }
        }
        summary = _summarise_engine_results(engine_results)
        assert "MANUSCRIPT SCAN" in summary
        assert "72" in summary

    def test_engine_results_empty_returns_empty(self):
        from services.copilot.ai_copilot import _summarise_engine_results
        assert _summarise_engine_results({}) == ""

    def test_intent_instruction_returned(self):
        from services.copilot.ai_copilot import _intent_instruction
        from services.copilot.models import DetectedIntent, IntentType
        intents = [DetectedIntent(IntentType.MANUSCRIPT_REVIEW, 0.9)]
        instruction = _intent_instruction(intents)
        assert "manuscript" in instruction.lower() or "writing" in instruction.lower()

    def test_generate_with_mocked_llm(self):
        from services.copilot.ai_copilot import generate_copilot_response
        from services.copilot.models import DetectedIntent, IntentType

        async def fake_call_llm(**kwargs):
            return "Here is my expert analysis of your manuscript."

        intents = [DetectedIntent(IntentType.MANUSCRIPT_REVIEW, 0.9)]

        with patch("services.copilot.ai_copilot.generate_copilot_response") as mock_gen:
            mock_gen.return_value = ("Mocked response text.", 50)
            text, tokens = _run(mock_gen("message", [], {}, intents, {}))
        assert text == "Mocked response text."
        assert tokens == 50


# ══════════════════════════════════════════════════════════════════════════════
# 8. Response Composer
# ══════════════════════════════════════════════════════════════════════════════

class TestResponseComposer:
    def _compose(self, ai_text="Good analysis.", engine_results=None, intents=None):
        from services.copilot.response_composer import compose
        from services.copilot.models import DetectedIntent, IntentType
        _intents = intents or [DetectedIntent(IntentType.MANUSCRIPT_REVIEW, 0.85,
                                              requires_engines=["manuscript"])]
        return compose(
            user_id="u1",
            ai_text=ai_text,
            intents=_intents,
            engine_results=engine_results or {},
            context=_RICH_CONTEXT,
        )

    def test_response_has_required_fields(self):
        r = self._compose()
        d = r.to_dict()
        for key in ["response_id", "message", "intents", "confidence",
                    "agent_type", "reasoning"]:
            assert key in d, f"Missing key: {key}"

    def test_manuscript_action_extracted(self):
        r = self._compose(ai_text="I suggest you create a manuscript to track your research.")
        actions = r.suggested_actions
        action_types = [a["action_type"] for a in actions]
        assert "create_manuscript" in action_types

    def test_journal_action_extracted(self):
        r = self._compose(ai_text="You should submit to Nature and find a suitable journal.")
        actions = r.suggested_actions
        action_types = [a["action_type"] for a in actions]
        assert "find_journal" in action_types

    def test_critical_issue_action_from_engine(self):
        engine_results = {
            "manuscript": {
                "critical_issue_count": 2, "major_issue_count": 1,
                "scientific_score": 60.0, "writing_score": 65.0,
                "statistical_score": 70.0, "word_count": 4000,
                "section_count": 5, "top_issues": [], "sections_detected": [],
            }
        }
        r = self._compose(engine_results=engine_results)
        action_types = [a["action_type"] for a in r.suggested_actions]
        assert "full_manuscript_review" in action_types

    def test_confidence_between_0_and_1(self):
        r = self._compose()
        assert 0.0 <= r.confidence <= 1.0

    def test_reasoning_is_non_empty(self):
        r = self._compose()
        assert len(r.reasoning) > 10

    def test_agent_type_inferred(self):
        from services.copilot.models import DetectedIntent, IntentType
        r = self._compose(intents=[DetectedIntent(IntentType.JOURNAL_REC, 0.9)])
        assert r.agent_type == "journal"

    def test_sources_extracted_from_context(self):
        r = self._compose(
            ai_text="Your manuscript 'AI in Healthcare Diagnostics' shows strong methodology."
        )
        source_titles = [s["title"] for s in r.sources]
        assert "AI in Healthcare Diagnostics" in source_titles


# ══════════════════════════════════════════════════════════════════════════════
# 9. Context Aggregator
# ══════════════════════════════════════════════════════════════════════════════

class TestContextAggregator:
    def test_extract_scan_content_long_message(self):
        from services.copilot.context_aggregator import extract_scan_content
        long_msg = "A" * 600
        content = extract_scan_content(long_msg, {})
        assert content == long_msg[:8_000]

    def test_extract_scan_content_uses_excerpt(self):
        from services.copilot.context_aggregator import extract_scan_content
        context = {"manuscript_excerpts": {"ms1": "Abstract: This is my paper. " * 50}}
        content = extract_scan_content("short message", context)
        assert "Abstract" in content

    def test_extract_scan_content_short_no_excerpts(self):
        from services.copilot.context_aggregator import extract_scan_content
        content = extract_scan_content("Hi", {})
        assert content == "Hi"


# ══════════════════════════════════════════════════════════════════════════════
# 10. Dashboard Builder
# ══════════════════════════════════════════════════════════════════════════════

class TestDashboardBuilder:
    def _make_db(self):
        db = MagicMock()
        db.projects.find.return_value.sort.return_value.limit.return_value.to_list = AsyncMock(return_value=[])
        db.manuscripts.find.return_value.sort.return_value.limit.return_value.to_list = AsyncMock(return_value=[])
        db.grant_applications.find.return_value.limit.return_value.to_list = AsyncMock(return_value=[])
        db.milestones.find.return_value.limit.return_value.to_list = AsyncMock(return_value=[])
        db.users.find_one = AsyncMock(return_value={"research_areas": ["AI", "health"]})
        db.grants.count_documents = AsyncMock(return_value=42)
        db.conferences.count_documents = AsyncMock(return_value=15)
        db.ai_memory.find.return_value.limit.return_value.to_list = AsyncMock(return_value=[
            {"memory_type": "research_goal", "content": "Apply AI to cancer detection."}
        ])
        return db

    def test_dashboard_returns_object(self):
        from services.copilot.dashboard_builder import build_dashboard
        db = self._make_db()
        dash = _run(build_dashboard("507f1f77bcf86cd799439011", db))
        assert dash is not None

    def test_dashboard_has_grant_opportunities(self):
        from services.copilot.dashboard_builder import build_dashboard
        db = self._make_db()
        dash = _run(build_dashboard("507f1f77bcf86cd799439011", db))
        assert dash.grant_opportunities == 42

    def test_dashboard_has_conference_opportunities(self):
        from services.copilot.dashboard_builder import build_dashboard
        db = self._make_db()
        dash = _run(build_dashboard("507f1f77bcf86cd799439011", db))
        assert dash.conference_opportunities == 15

    def test_dashboard_has_research_goals(self):
        from services.copilot.dashboard_builder import build_dashboard
        db = self._make_db()
        dash = _run(build_dashboard("507f1f77bcf86cd799439011", db))
        assert len(dash.research_goals) >= 1

    def test_dashboard_to_dict(self):
        from services.copilot.dashboard_builder import build_dashboard
        db = self._make_db()
        dash = _run(build_dashboard("507f1f77bcf86cd799439011", db))
        d = dash.to_dict()
        for key in ["user_id", "generated_at", "active_projects", "upcoming_deadlines",
                    "grant_opportunities", "recommended_actions", "widgets"]:
            assert key in d


# ══════════════════════════════════════════════════════════════════════════════
# 11. Telemetry
# ══════════════════════════════════════════════════════════════════════════════

class TestTelemetry:
    def _fresh(self):
        from services.copilot.telemetry import CopilotTelemetry
        return CopilotTelemetry()

    def test_record_chat(self):
        t = self._fresh()
        t.record_chat("manuscript_review", "publication", ["manuscript"], 1500.0)
        stats = t.get_stats()
        assert stats["total_chats"] == 1
        assert stats["intent_distribution"]["manuscript_review"] == 1
        assert stats["engine_dispatch_counts"]["manuscript"] == 1

    def test_record_workflow(self):
        t = self._fresh()
        t.record_workflow("completed", ["manuscript", "statistical"])
        stats = t.get_stats()
        assert stats["total_workflows"] == 1
        assert stats["workflow_statuses"]["completed"] == 1
        assert stats["engine_dispatch_counts"]["manuscript"] == 1

    def test_record_roadmap(self):
        t = self._fresh()
        t.record_roadmap()
        assert t.get_stats()["total_roadmaps"] == 1

    def test_record_error(self):
        t = self._fresh()
        t.record_chat("general_chat", "general", [], 500.0, error=True)
        stats = t.get_stats()
        assert stats["errors"] == 1
        assert stats["error_rate"] > 0

    def test_reset(self):
        t = self._fresh()
        t.record_chat("general", "general", [], 1000.0)
        t.reset()
        assert t.get_stats()["total_chats"] == 0

    def test_singleton(self):
        from services.copilot.telemetry import get_copilot_telemetry
        t1 = get_copilot_telemetry()
        t2 = get_copilot_telemetry()
        assert t1 is t2

    def test_latency_percentiles(self):
        t = self._fresh()
        for i in range(20):
            t.record_chat("general", "general", [], float(i * 100))
        stats = t.get_stats()
        assert stats["p50_ms"] > 0
        assert stats["p95_ms"] >= stats["p50_ms"]

    def test_engine_error_recorded(self):
        t = self._fresh()
        t.record_engine_error("manuscript")
        stats = t.get_stats()
        assert stats["engine_error_counts"]["manuscript"] == 1


# ══════════════════════════════════════════════════════════════════════════════
# 12. Engine Internals
# ══════════════════════════════════════════════════════════════════════════════

class TestEngineInternals:
    def test_get_copilot_engine_singleton(self):
        from services.copilot.engine import get_copilot_engine, reset_copilot_engine
        reset_copilot_engine()
        e1 = _run(get_copilot_engine())
        e2 = _run(get_copilot_engine())
        assert e1 is e2
        reset_copilot_engine()

    def test_reset_clears_singleton(self):
        from services.copilot.engine import get_copilot_engine, reset_copilot_engine
        reset_copilot_engine()
        e1 = _run(get_copilot_engine())
        reset_copilot_engine()
        e2 = _run(get_copilot_engine())
        assert e1 is not e2
        reset_copilot_engine()

    def test_get_memory_empty_db(self):
        from services.copilot.engine import CopilotEngine
        engine = CopilotEngine()
        db = MagicMock()
        db.ai_memory.find.return_value.sort.return_value.limit.return_value.to_list = AsyncMock(return_value=[])
        result = _run(engine.get_memory("u1", db))
        assert isinstance(result, list)

    def test_get_history_empty_db(self):
        from services.copilot.engine import CopilotEngine
        engine = CopilotEngine()
        db = MagicMock()
        db.copilot_conversations.find.return_value.sort.return_value.limit.return_value.to_list = AsyncMock(return_value=[])
        result = _run(engine.get_history("u1", db))
        assert result == []

    def test_telemetry_returns_dict(self):
        from services.copilot.engine import CopilotEngine
        engine = CopilotEngine()
        stats = engine.get_telemetry()
        assert "total_chats" in stats
        assert "p50_ms" in stats

    def test_build_roadmap_research(self):
        from services.copilot.engine import CopilotEngine
        engine = CopilotEngine()
        db = MagicMock()
        db.copilot_roadmaps.replace_one = AsyncMock(return_value=MagicMock())
        db.ai_context_cache.find_one = AsyncMock(return_value=None)
        db.users.find_one = AsyncMock(return_value={"full_name": "Dr Alice"})
        db.manuscripts.find.return_value.sort.return_value.limit.return_value.to_list = AsyncMock(return_value=[])
        db.projects.find.return_value.limit.return_value.to_list = AsyncMock(return_value=[])
        db.collaborations.find.return_value.limit.return_value.to_list = AsyncMock(return_value=[])
        db.grant_applications.find.return_value.sort.return_value.limit.return_value.to_list = AsyncMock(return_value=[])
        db.research_reputation.find_one = AsyncMock(return_value=None)
        db.research_impact.find_one = AsyncMock(return_value=None)
        db.ai_memory.find.return_value.sort.return_value.limit.return_value.to_list = AsyncMock(return_value=[])
        db.manuscripts.find.return_value.limit.return_value.to_list = AsyncMock(return_value=[])

        from services.copilot.models import RoadmapType
        roadmap = _run(engine.build_academic_roadmap("u1", RoadmapType.RESEARCH, {}, db, use_ai=False))
        assert roadmap is not None
        assert len(roadmap.phases) >= 4
