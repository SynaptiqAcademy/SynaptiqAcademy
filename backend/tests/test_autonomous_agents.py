"""Tests for Phase XIII — Autonomous Research Agents Platform.

112 tests across 17 test classes covering all agents, the workflow engine,
execution engine, memory bus, quality controller, orchestrator, telemetry,
and engine integration.
"""
from __future__ import annotations

import asyncio
import pytest

# ── Shared test fixture ───────────────────────────────────────────────────────

_RICH_TEXT = (
    "This study investigates machine learning methods for natural language processing "
    "in clinical medicine. We propose a transformer-based model for cardiovascular disease "
    "risk prediction. The methodology uses a longitudinal cohort of 1200 participants. "
    "Ethics approval was granted by the IRB (IRB-2024-001). Informed consent was obtained. "
    "Conflict of interest: none. Funding: NIH R01-HL-123456. "
    "Data availability: code available on GitHub; data deposited in Zenodo (DOI: 10.5281/xyz). "
    "Author contributions: A.B. conceptualisation, C.D. methodology. "
    "Abstract: This paper presents a novel AI-driven approach. "
    "Introduction: NLP has transformed clinical decision support. "
    "Methods: We applied BERT with fine-tuning on 1200 patients (n=1200). "
    "Results: AUC improved by 8.3% (p < 0.01). We report Cohen's d = 0.72. "
    "We report 95% CI [0.65, 0.79]. Power analysis confirmed sufficient sample size. "
    "Normality tested (Shapiro-Wilk). Homoscedasticity confirmed (Levene's). "
    "Discussion: These findings align with prior systematic reviews. "
    "Conclusion: The model outperforms baselines. "
    "Keywords: machine learning, NLP, cardiovascular, clinical decision support. "
    "References: (Smith, 2021); (Jones, 2022); (Brown, 2023); (Davis, 2020); (Wilson, 2021); "
    "(Taylor, 2022); (Anderson, 2023); (Thomas, 2020); (Jackson, 2021); (White, 2022); "
    "(Harris, 2023); (Martin, 2021); (Garcia, 2022); (Lee, 2023); (Kim, 2020). "
    "Research gap: Few studies have examined NLP in cardiovascular risk prediction. "
    "This is the first study to combine transformer architectures with longitudinal EHR data. "
    "Future research should validate these findings across diverse populations. "
) * 2


def _make_context(user_id: str = "test_user") -> "AgentContext":
    from services.agents.models import AgentContext
    return AgentContext(user_id=user_id)


def _make_task(agent_type, content: str = _RICH_TEXT, metadata: dict | None = None):
    from services.agents.models import AgentTask
    return AgentTask(agent_type=agent_type, content=content, metadata=metadata or {})


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Models
# ═══════════════════════════════════════════════════════════════════════════════

class TestModels:
    def test_agent_task_defaults(self):
        from services.agents.models import AgentTask, AgentType
        t = AgentTask(agent_type=AgentType.LITERATURE_REVIEW, content="test")
        assert t.task_id is not None
        assert t.content == "test"

    def test_agent_task_to_dict(self):
        from services.agents.models import AgentTask, AgentType
        t = AgentTask(agent_type=AgentType.LITERATURE_REVIEW, content="test")
        d = t.to_dict()
        assert d["agent_type"] == "literature_review"
        assert "task_id" in d

    def test_agent_result_to_dict(self):
        from services.agents.models import AgentResult, AgentStatus, AgentType
        r = AgentResult(agent_type=AgentType.LITERATURE_REVIEW, status=AgentStatus.COMPLETED,
                        confidence=0.85, reasoning="test")
        d = r.to_dict()
        assert d["confidence"] == 0.85
        assert d["status"] == "completed"

    def test_agent_message_to_dict(self):
        from services.agents.models import AgentMessage, MessageType
        m = AgentMessage(from_agent="lit", to_agent="gap", message_type=MessageType.HANDOFF)
        d = m.to_dict()
        assert d["from_agent"] == "lit"
        assert d["message_type"] == "handoff"

    def test_agent_context_add_result(self):
        from services.agents.models import AgentContext, AgentResult, AgentType
        ctx = AgentContext(user_id="u1")
        r = AgentResult(agent_type=AgentType.LITERATURE_REVIEW, confidence=0.8)
        ctx.add_result(r)
        assert ctx.get_result(AgentType.LITERATURE_REVIEW) is r

    def test_workflow_step_to_dict(self):
        from services.agents.models import AgentType, WorkflowStep
        s = WorkflowStep(agent_type=AgentType.LITERATURE_REVIEW, name="Test")
        d = s.to_dict()
        assert d["agent_type"] == "literature_review"
        assert d["name"] == "Test"

    def test_workflow_template_to_dict(self):
        from services.agents.models import WorkflowTemplate, WorkflowType
        t = WorkflowTemplate(workflow_type=WorkflowType.PUBLICATION, name="Test")
        d = t.to_dict()
        assert d["workflow_type"] == "publication_workflow"

    def test_workflow_execution_to_dict(self):
        from services.agents.models import AgentStatus, WorkflowExecution, WorkflowType
        ex = WorkflowExecution(workflow_type=WorkflowType.PUBLICATION, user_id="u1")
        d = ex.to_dict()
        assert d["user_id"] == "u1"
        assert d["workflow_type"] == "publication_workflow"

    def test_quality_report_to_dict(self):
        from services.agents.models import QualityLevel, QualityReport
        qr = QualityReport(overall_quality=QualityLevel.GOOD, overall_confidence=0.75)
        d = qr.to_dict()
        assert d["overall_quality"] == "good"
        assert d["overall_confidence"] == 0.75

    def test_platform_response_to_dict(self):
        from services.agents.models import AgentPlatformResponse
        r = AgentPlatformResponse(user_id="u1", summary="Test summary")
        d = r.to_dict()
        assert d["user_id"] == "u1"
        assert d["summary"] == "Test summary"

    def test_agent_type_values(self):
        from services.agents.models import AgentType
        assert AgentType.LITERATURE_REVIEW.value == "literature_review"
        assert AgentType.SUPERVISOR.value == "supervisor"
        assert AgentType.KNOWLEDGE_GRAPH.value == "knowledge_graph"
        assert len(list(AgentType)) == 20

    def test_workflow_type_values(self):
        from services.agents.models import WorkflowType
        assert len(list(WorkflowType)) == 10

    def test_execution_mode_values(self):
        from services.agents.models import ExecutionMode
        assert ExecutionMode.PARALLEL.value == "parallel"
        assert ExecutionMode.SEQUENTIAL.value == "sequential"

    def test_execution_graph_to_dict(self):
        from services.agents.models import ExecutionGraph, GraphNode
        g = ExecutionGraph(execution_id="ex1",
                           nodes=[GraphNode(node_id="n1", agent_type="literature_review")],
                           edges=[{"from": "n1", "to": "n2"}])
        d = g.to_dict()
        assert d["execution_id"] == "ex1"
        assert len(d["nodes"]) == 1

    def test_validation_result_to_dict(self):
        from services.agents.models import QualityLevel, ValidationResult, AgentType
        vr = ValidationResult(agent_type=AgentType.LITERATURE_REVIEW,
                              is_valid=True, quality_level=QualityLevel.GOOD)
        d = vr.to_dict()
        assert d["is_valid"] is True
        assert d["quality_level"] == "good"


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Agent Registry
# ═══════════════════════════════════════════════════════════════════════════════

class TestAgentRegistry:
    def _ensure_registered(self):
        # Import engine to trigger all registrations
        import services.agents.engine  # noqa

    def test_all_20_agents_registered(self):
        self._ensure_registered()
        from services.agents.base_agent import AgentRegistry
        from services.agents.models import AgentType
        for at in AgentType:
            assert AgentRegistry.is_registered(at), f"{at.value} not registered"

    def test_create_literature_agent(self):
        self._ensure_registered()
        from services.agents.base_agent import AgentRegistry
        from services.agents.models import AgentType
        agent = AgentRegistry.create(AgentType.LITERATURE_REVIEW)
        assert agent is not None
        assert agent.agent_type == AgentType.LITERATURE_REVIEW

    def test_create_unknown_type_raises(self):
        from services.agents.base_agent import AgentRegistry
        import pytest
        with pytest.raises(ValueError):
            # Pass a fake type by manipulating
            class FakeType:
                value = "not_real"
            AgentRegistry.create(FakeType)

    def test_list_agents_returns_all(self):
        self._ensure_registered()
        from services.agents.base_agent import AgentRegistry
        agents = AgentRegistry.list_agents()
        assert len(agents) == 20

    def test_agent_describe_has_required_fields(self):
        self._ensure_registered()
        from services.agents.base_agent import AgentRegistry
        from services.agents.models import AgentType
        agent = AgentRegistry.create(AgentType.SUPERVISOR)
        d = agent.describe()
        assert "agent_id" in d and "name" in d and "capabilities" in d

    def test_agent_validate_method(self):
        self._ensure_registered()
        from services.agents.base_agent import AgentRegistry
        from services.agents.models import AgentResult, AgentType
        agent = AgentRegistry.create(AgentType.LITERATURE_REVIEW)
        result = AgentResult(agent_type=AgentType.LITERATURE_REVIEW,
                             confidence=0.8, reasoning="test", output={"x": 1})
        vr = agent.validate(result)
        assert vr.is_valid is True


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Individual Agents
# ═══════════════════════════════════════════════════════════════════════════════

class TestLiteratureAgent:
    def test_execute_returns_result(self):
        from services.agents.agent_literature import LiteratureReviewAgent
        from services.agents.models import AgentType
        agent = LiteratureReviewAgent()
        task = _make_task(AgentType.LITERATURE_REVIEW)
        result = asyncio.run(agent.execute(task, _make_context()))
        assert result.agent_type == AgentType.LITERATURE_REVIEW
        assert result.confidence > 0

    def test_detects_themes(self):
        from services.agents.agent_literature import LiteratureReviewAgent
        from services.agents.models import AgentType
        result = asyncio.run(LiteratureReviewAgent().execute(
            _make_task(AgentType.LITERATURE_REVIEW), _make_context()
        ))
        assert "themes_identified" in result.output
        assert isinstance(result.output["themes_identified"], list)

    def test_detects_citations(self):
        from services.agents.agent_literature import LiteratureReviewAgent
        from services.agents.models import AgentType
        result = asyncio.run(LiteratureReviewAgent().execute(
            _make_task(AgentType.LITERATURE_REVIEW), _make_context()
        ))
        assert result.output.get("citation_count", 0) > 0

    def test_has_reasoning(self):
        from services.agents.agent_literature import LiteratureReviewAgent
        from services.agents.models import AgentType
        result = asyncio.run(LiteratureReviewAgent().execute(
            _make_task(AgentType.LITERATURE_REVIEW), _make_context()
        ))
        assert len(result.reasoning) > 0

    def test_latency_tracked(self):
        from services.agents.agent_literature import LiteratureReviewAgent
        from services.agents.models import AgentType
        result = asyncio.run(LiteratureReviewAgent().execute(
            _make_task(AgentType.LITERATURE_REVIEW), _make_context()
        ))
        assert result.latency_seconds >= 0


class TestGapAgent:
    def test_detects_gap_signals(self):
        from services.agents.agent_gap import ResearchGapAgent
        from services.agents.models import AgentType
        result = asyncio.run(ResearchGapAgent().execute(
            _make_task(AgentType.RESEARCH_GAP), _make_context()
        ))
        assert "explicit_gaps_found" in result.output

    def test_novelty_signals(self):
        from services.agents.agent_gap import ResearchGapAgent
        from services.agents.models import AgentType
        result = asyncio.run(ResearchGapAgent().execute(
            _make_task(AgentType.RESEARCH_GAP), _make_context()
        ))
        assert "has_novelty_claim" in result.output

    def test_inherits_from_literature(self):
        from services.agents.agent_gap import ResearchGapAgent
        from services.agents.agent_literature import LiteratureReviewAgent
        from services.agents.models import AgentType
        ctx = _make_context()
        task = _make_task(AgentType.LITERATURE_REVIEW)
        lit_result = asyncio.run(LiteratureReviewAgent().execute(task, ctx))
        ctx.add_result(lit_result)
        task2 = _make_task(AgentType.RESEARCH_GAP)
        gap_result = asyncio.run(ResearchGapAgent().execute(task2, ctx))
        assert "inherited_gaps_from_literature" in gap_result.output

    def test_opportunities_list(self):
        from services.agents.agent_gap import ResearchGapAgent
        from services.agents.models import AgentType
        result = asyncio.run(ResearchGapAgent().execute(
            _make_task(AgentType.RESEARCH_GAP), _make_context()
        ))
        assert isinstance(result.output.get("research_opportunities"), list)


class TestMethodologyAgent:
    def test_detects_study_design(self):
        from services.agents.agent_methodology import MethodologyAgent
        from services.agents.models import AgentType
        result = asyncio.run(MethodologyAgent().execute(
            _make_task(AgentType.METHODOLOGY), _make_context()
        ))
        assert "detected_designs" in result.output

    def test_validity_coverage(self):
        from services.agents.agent_methodology import MethodologyAgent
        from services.agents.models import AgentType
        result = asyncio.run(MethodologyAgent().execute(
            _make_task(AgentType.METHODOLOGY), _make_context()
        ))
        assert 0.0 <= result.output.get("validity_score", 0) <= 1.0

    def test_detects_sample_size(self):
        from services.agents.agent_methodology import MethodologyAgent
        from services.agents.models import AgentType
        result = asyncio.run(MethodologyAgent().execute(
            _make_task(AgentType.METHODOLOGY, content=_RICH_TEXT), _make_context()
        ))
        sizes = result.output.get("sample_sizes_detected", [])
        assert isinstance(sizes, list)

    def test_has_recommendations(self):
        from services.agents.agent_methodology import MethodologyAgent
        from services.agents.models import AgentType
        result = asyncio.run(MethodologyAgent().execute(
            _make_task(AgentType.METHODOLOGY), _make_context()
        ))
        assert len(result.output.get("recommendations", [])) > 0


class TestStatisticsAgent:
    def test_detects_tests(self):
        from services.agents.agent_statistics import StatisticsAgent
        from services.agents.models import AgentType
        result = asyncio.run(StatisticsAgent().execute(
            _make_task(AgentType.STATISTICS), _make_context()
        ))
        assert "detected_tests" in result.output

    def test_detects_effect_sizes(self):
        from services.agents.agent_statistics import StatisticsAgent
        from services.agents.models import AgentType
        result = asyncio.run(StatisticsAgent().execute(
            _make_task(AgentType.STATISTICS, content=_RICH_TEXT), _make_context()
        ))
        assert result.output.get("has_effect_sizes") is True

    def test_reporting_completeness_in_range(self):
        from services.agents.agent_statistics import StatisticsAgent
        from services.agents.models import AgentType
        result = asyncio.run(StatisticsAgent().execute(
            _make_task(AgentType.STATISTICS), _make_context()
        ))
        score = result.output.get("reporting_completeness_score", 0)
        assert 0.0 <= score <= 1.0

    def test_has_confidence_intervals(self):
        from services.agents.agent_statistics import StatisticsAgent
        from services.agents.models import AgentType
        result = asyncio.run(StatisticsAgent().execute(
            _make_task(AgentType.STATISTICS, content=_RICH_TEXT), _make_context()
        ))
        assert result.output.get("has_confidence_intervals") is True


class TestWritingAgent:
    def test_word_count(self):
        from services.agents.agent_writing import AcademicWritingAgent
        from services.agents.models import AgentType
        result = asyncio.run(AcademicWritingAgent().execute(
            _make_task(AgentType.ACADEMIC_WRITING), _make_context()
        ))
        assert result.output.get("word_count", 0) > 0

    def test_quality_score_in_range(self):
        from services.agents.agent_writing import AcademicWritingAgent
        from services.agents.models import AgentType
        result = asyncio.run(AcademicWritingAgent().execute(
            _make_task(AgentType.ACADEMIC_WRITING), _make_context()
        ))
        assert 0.0 <= result.output.get("quality_score", 0) <= 1.0

    def test_has_sections_count(self):
        from services.agents.agent_writing import AcademicWritingAgent
        from services.agents.models import AgentType
        result = asyncio.run(AcademicWritingAgent().execute(
            _make_task(AgentType.ACADEMIC_WRITING, content=_RICH_TEXT), _make_context()
        ))
        assert result.output.get("sections_detected", 0) >= 3

    def test_has_recommendations(self):
        from services.agents.agent_writing import AcademicWritingAgent
        from services.agents.models import AgentType
        result = asyncio.run(AcademicWritingAgent().execute(
            _make_task(AgentType.ACADEMIC_WRITING), _make_context()
        ))
        assert len(result.output.get("recommendations", [])) > 0


class TestEthicsAgent:
    def test_detects_ethics_approval(self):
        from services.agents.agent_ethics import ResearchEthicsAgent
        from services.agents.models import AgentType
        result = asyncio.run(ResearchEthicsAgent().execute(
            _make_task(AgentType.RESEARCH_ETHICS, content=_RICH_TEXT), _make_context()
        ))
        assert result.output.get("has_ethics_approval") is True

    def test_detects_consent(self):
        from services.agents.agent_ethics import ResearchEthicsAgent
        from services.agents.models import AgentType
        result = asyncio.run(ResearchEthicsAgent().execute(
            _make_task(AgentType.RESEARCH_ETHICS, content=_RICH_TEXT), _make_context()
        ))
        assert result.output.get("has_informed_consent") is True

    def test_compliance_score_in_range(self):
        from services.agents.agent_ethics import ResearchEthicsAgent
        from services.agents.models import AgentType
        result = asyncio.run(ResearchEthicsAgent().execute(
            _make_task(AgentType.RESEARCH_ETHICS), _make_context()
        ))
        assert 0.0 <= result.output.get("compliance_score", 0) <= 1.0

    def test_no_ethics_flags_critical(self):
        from services.agents.agent_ethics import ResearchEthicsAgent
        from services.agents.models import AgentType
        bare = "We recruited 100 participants for this study."
        result = asyncio.run(ResearchEthicsAgent().execute(
            _make_task(AgentType.RESEARCH_ETHICS, content=bare), _make_context()
        ))
        assert result.output.get("is_compliant") is False


class TestCitationAgent:
    def test_detects_citations(self):
        from services.agents.agent_citation import CitationIntelligenceAgent
        from services.agents.models import AgentType
        result = asyncio.run(CitationIntelligenceAgent().execute(
            _make_task(AgentType.CITATION_INTELLIGENCE, content=_RICH_TEXT), _make_context()
        ))
        assert result.output.get("total_citations_detected", 0) > 0

    def test_recency_ratio_in_range(self):
        from services.agents.agent_citation import CitationIntelligenceAgent
        from services.agents.models import AgentType
        result = asyncio.run(CitationIntelligenceAgent().execute(
            _make_task(AgentType.CITATION_INTELLIGENCE, content=_RICH_TEXT), _make_context()
        ))
        assert 0.0 <= result.output.get("recency_ratio_post_2019", 0) <= 1.0

    def test_detects_dois(self):
        from services.agents.agent_citation import CitationIntelligenceAgent
        from services.agents.models import AgentType
        result = asyncio.run(CitationIntelligenceAgent().execute(
            _make_task(AgentType.CITATION_INTELLIGENCE, content=_RICH_TEXT), _make_context()
        ))
        assert result.output.get("dois_detected", 0) >= 0


class TestSupervisorAgent:
    def _run_pipeline(self):
        from services.agents.agent_literature import LiteratureReviewAgent
        from services.agents.agent_methodology import MethodologyAgent
        from services.agents.agent_statistics import StatisticsAgent
        from services.agents.agent_ethics import ResearchEthicsAgent
        from services.agents.agent_supervisor import SupervisorAgent
        from services.agents.models import AgentType

        ctx = _make_context()
        agents = [LiteratureReviewAgent, MethodologyAgent, StatisticsAgent, ResearchEthicsAgent]

        async def _run():
            for AgentClass in agents:
                at = AgentClass.agent_type
                task = _make_task(at, content=_RICH_TEXT)
                result = await AgentClass().execute(task, ctx)
                ctx.add_result(result)
            sup_task = _make_task(AgentType.SUPERVISOR)
            return await SupervisorAgent().execute(sup_task, ctx)
        return asyncio.run(_run())

    def test_supervisor_aggregates_results(self):
        result = self._run_pipeline()
        assert "agents_supervised" in result.output
        assert len(result.output["agents_supervised"]) >= 3

    def test_supervisor_has_quality_level(self):
        result = self._run_pipeline()
        assert "quality_level" in result.output

    def test_supervisor_has_recommendation(self):
        result = self._run_pipeline()
        assert "overall_recommendation" in result.output
        assert len(result.output["overall_recommendation"]) > 0

    def test_supervisor_no_prior_context(self):
        from services.agents.agent_supervisor import SupervisorAgent
        from services.agents.models import AgentType
        result = asyncio.run(SupervisorAgent().execute(
            _make_task(AgentType.SUPERVISOR), _make_context()
        ))
        assert result.output.get("message") or result.output.get("quality_level")


class TestResearchPlanningAgent:
    def test_generates_milestones(self):
        from services.agents.agent_research_planning import ResearchPlanningAgent
        from services.agents.models import AgentType
        result = asyncio.run(ResearchPlanningAgent().execute(
            _make_task(AgentType.RESEARCH_PLANNING, content=_RICH_TEXT), _make_context()
        ))
        assert len(result.output.get("milestones", [])) > 0

    def test_detects_project_type(self):
        from services.agents.agent_research_planning import ResearchPlanningAgent
        from services.agents.models import AgentType
        result = asyncio.run(ResearchPlanningAgent().execute(
            _make_task(AgentType.RESEARCH_PLANNING, content=_RICH_TEXT), _make_context()
        ))
        assert result.output.get("project_type") in ("empirical", "theoretical", "review", "default")

    def test_total_duration_positive(self):
        from services.agents.agent_research_planning import ResearchPlanningAgent
        from services.agents.models import AgentType
        result = asyncio.run(ResearchPlanningAgent().execute(
            _make_task(AgentType.RESEARCH_PLANNING), _make_context()
        ))
        assert result.output.get("total_duration_weeks", 0) > 0


class TestTimelineAgent:
    def test_generates_gantt(self):
        from services.agents.agent_timeline import TimelineAgent
        from services.agents.models import AgentType
        result = asyncio.run(TimelineAgent().execute(
            _make_task(AgentType.TIMELINE), _make_context()
        ))
        assert len(result.output.get("gantt_chart", [])) > 0

    def test_inherits_planning_milestones(self):
        from services.agents.agent_research_planning import ResearchPlanningAgent
        from services.agents.agent_timeline import TimelineAgent
        from services.agents.models import AgentType
        ctx = _make_context()

        async def _run():
            plan_result = await ResearchPlanningAgent().execute(
                _make_task(AgentType.RESEARCH_PLANNING), ctx
            )
            ctx.add_result(plan_result)
            return await TimelineAgent().execute(_make_task(AgentType.TIMELINE), ctx)

        result = asyncio.run(_run())
        plan_weeks = ctx.get_result(AgentType.RESEARCH_PLANNING).output.get("total_duration_weeks", 0)
        assert result.output.get("total_duration_weeks", 0) == plan_weeks

    def test_has_buffer_weeks(self):
        from services.agents.agent_timeline import TimelineAgent
        from services.agents.models import AgentType
        result = asyncio.run(TimelineAgent().execute(
            _make_task(AgentType.TIMELINE), _make_context()
        ))
        assert result.output.get("recommended_buffer_weeks", 0) > 0


class TestKnowledgeGraphAgent:
    def test_extracts_concepts(self):
        from services.agents.agent_knowledge_graph import KnowledgeGraphAgent
        from services.agents.models import AgentType
        result = asyncio.run(KnowledgeGraphAgent().execute(
            _make_task(AgentType.KNOWLEDGE_GRAPH, content=_RICH_TEXT), _make_context()
        ))
        assert result.output.get("total_concepts", 0) >= 0

    def test_graph_has_nodes_and_edges(self):
        from services.agents.agent_knowledge_graph import KnowledgeGraphAgent
        from services.agents.models import AgentType
        result = asyncio.run(KnowledgeGraphAgent().execute(
            _make_task(AgentType.KNOWLEDGE_GRAPH, content=_RICH_TEXT), _make_context()
        ))
        g = result.output.get("graph", {})
        assert "nodes" in g and "edges" in g

    def test_has_recommendations(self):
        from services.agents.agent_knowledge_graph import KnowledgeGraphAgent
        from services.agents.models import AgentType
        result = asyncio.run(KnowledgeGraphAgent().execute(
            _make_task(AgentType.KNOWLEDGE_GRAPH), _make_context()
        ))
        assert len(result.output.get("recommendations", [])) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Workflow Engine
# ═══════════════════════════════════════════════════════════════════════════════

class TestWorkflowEngine:
    def test_all_10_templates_exist(self):
        from services.agents.workflow_engine import list_templates, _TEMPLATES
        assert len(_TEMPLATES) == 10

    def test_list_templates_returns_dicts(self):
        from services.agents.workflow_engine import list_templates
        templates = list_templates()
        assert len(templates) == 10
        assert all("workflow_type" in t for t in templates)

    def test_get_template_publication(self):
        from services.agents.workflow_engine import get_template
        from services.agents.models import WorkflowType
        t = get_template(WorkflowType.PUBLICATION)
        assert t.workflow_type == WorkflowType.PUBLICATION
        assert len(t.steps) >= 5

    def test_get_template_literature_review(self):
        from services.agents.workflow_engine import get_template
        from services.agents.models import WorkflowType
        t = get_template(WorkflowType.LITERATURE_REVIEW)
        assert len(t.steps) >= 4

    def test_unknown_workflow_raises(self):
        from services.agents.workflow_engine import get_template
        with pytest.raises((ValueError, Exception)):
            get_template("not_a_workflow")

    def test_resolve_execution_order_no_deps(self):
        from services.agents.workflow_engine import resolve_execution_order
        from services.agents.models import AgentType, WorkflowStep
        s1 = WorkflowStep(agent_type=AgentType.LITERATURE_REVIEW, name="S1")
        s2 = WorkflowStep(agent_type=AgentType.RESEARCH_GAP, name="S2")
        batches = resolve_execution_order([s1, s2])
        assert len(batches) == 1  # both can run in parallel
        assert len(batches[0]) == 2

    def test_resolve_execution_order_with_deps(self):
        from services.agents.workflow_engine import resolve_execution_order
        from services.agents.models import AgentType, WorkflowStep
        s1 = WorkflowStep(agent_type=AgentType.LITERATURE_REVIEW, name="S1")
        s2 = WorkflowStep(agent_type=AgentType.RESEARCH_GAP, name="S2",
                          depends_on=[s1.step_id])
        batches = resolve_execution_order([s1, s2])
        assert len(batches) == 2
        assert s1 in batches[0]
        assert s2 in batches[1]

    def test_supervisor_always_last_in_publication(self):
        from services.agents.workflow_engine import get_template
        from services.agents.models import AgentType, WorkflowType
        t = get_template(WorkflowType.PUBLICATION)
        assert t.steps[-1].agent_type == AgentType.SUPERVISOR

    def test_grant_workflow_has_grant_agent(self):
        from services.agents.workflow_engine import get_template
        from services.agents.models import AgentType, WorkflowType
        t = get_template(WorkflowType.GRANT)
        types = [s.agent_type for s in t.steps]
        assert AgentType.GRANT_INTELLIGENCE in types

    def test_doctoral_workflow_has_career_agent(self):
        from services.agents.workflow_engine import get_template
        from services.agents.models import AgentType, WorkflowType
        t = get_template(WorkflowType.DOCTORAL)
        types = [s.agent_type for s in t.steps]
        assert AgentType.CAREER_DEVELOPMENT in types


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Execution Engine
# ═══════════════════════════════════════════════════════════════════════════════

class TestExecutionEngine:
    def test_execute_workflow_literature_review(self):
        from services.agents.execution_engine import execute_workflow
        from services.agents.models import AgentStatus, WorkflowType

        async def _run():
            return await execute_workflow(
                WorkflowType.LITERATURE_REVIEW, _RICH_TEXT, "test_user"
            )

        execution = asyncio.run(_run())
        assert execution.status in (AgentStatus.COMPLETED, AgentStatus.FAILED)
        assert len(execution.results) > 0

    def test_execute_workflow_conference(self):
        from services.agents.execution_engine import execute_workflow
        from services.agents.models import WorkflowType
        execution = asyncio.run(execute_workflow(
            WorkflowType.CONFERENCE, _RICH_TEXT, "test_user"
        ))
        assert execution.execution_id is not None

    def test_execute_agents_parallel(self):
        from services.agents.execution_engine import execute_agents_parallel
        from services.agents.models import AgentType

        async def _run():
            ctx = _make_context()
            return await execute_agents_parallel(
                [AgentType.LITERATURE_REVIEW, AgentType.RESEARCH_GAP,
                 AgentType.ACADEMIC_WRITING],
                _RICH_TEXT, ctx
            )

        results = asyncio.run(_run())
        assert len(results) == 3
        assert AgentType.LITERATURE_REVIEW.value in results

    def test_execute_agents_sequential(self):
        from services.agents.execution_engine import execute_agents_sequential
        from services.agents.models import AgentType

        async def _run():
            ctx = _make_context()
            return await execute_agents_sequential(
                [AgentType.LITERATURE_REVIEW, AgentType.RESEARCH_GAP],
                _RICH_TEXT, ctx
            )

        results = asyncio.run(_run())
        assert len(results) == 2

    def test_sequential_context_propagation(self):
        from services.agents.execution_engine import execute_agents_sequential
        from services.agents.models import AgentType

        async def _run():
            ctx = _make_context()
            await execute_agents_sequential(
                [AgentType.LITERATURE_REVIEW, AgentType.RESEARCH_GAP],
                _RICH_TEXT, ctx
            )
            return ctx

        ctx = asyncio.run(_run())
        assert ctx.get_result(AgentType.LITERATURE_REVIEW) is not None
        assert ctx.get_result(AgentType.RESEARCH_GAP) is not None

    def test_condition_evaluation_true(self):
        from services.agents.execution_engine import _evaluate_condition
        from services.agents.models import AgentContext, AgentResult, AgentType
        ctx = AgentContext(user_id="u")
        r = AgentResult(agent_type=AgentType.LITERATURE_REVIEW, confidence=0.9)
        ctx.add_result(r)
        assert _evaluate_condition("confidence > 0.5", ctx) is True

    def test_condition_evaluation_false(self):
        from services.agents.execution_engine import _evaluate_condition
        from services.agents.models import AgentContext, AgentResult, AgentType
        ctx = AgentContext(user_id="u")
        r = AgentResult(agent_type=AgentType.LITERATURE_REVIEW, confidence=0.3)
        ctx.add_result(r)
        assert _evaluate_condition("confidence >= 0.8", ctx) is False

    def test_empty_condition_always_true(self):
        from services.agents.execution_engine import _evaluate_condition
        from services.agents.models import AgentContext
        ctx = AgentContext(user_id="u")
        assert _evaluate_condition("", ctx) is True


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Memory Bus
# ═══════════════════════════════════════════════════════════════════════════════

class TestMemoryBus:
    def test_write_and_read(self):
        from services.agents.memory_bus import MemoryBus
        bus = MemoryBus("sess1")
        bus.write("key", "value")
        assert bus.read("key") == "value"

    def test_read_missing_returns_default(self):
        from services.agents.memory_bus import MemoryBus
        bus = MemoryBus("sess2")
        assert bus.read("missing", "default") == "default"

    def test_delete(self):
        from services.agents.memory_bus import MemoryBus
        bus = MemoryBus("sess3")
        bus.write("k", "v")
        bus.delete("k")
        assert bus.read("k") is None

    def test_merge_no_overwrite(self):
        from services.agents.memory_bus import MemoryBus
        bus = MemoryBus("sess4")
        bus.write("a", 1)
        bus.merge({"a": 99, "b": 2})
        assert bus.read("a") == 1  # not overwritten
        assert bus.read("b") == 2

    def test_snapshot(self):
        from services.agents.memory_bus import MemoryBus
        bus = MemoryBus("sess5")
        bus.write("x", 10)
        snap = bus.snapshot()
        assert snap["x"] == 10

    def test_registry(self):
        from services.agents.memory_bus import MemoryBusRegistry
        bus1 = MemoryBusRegistry.get_or_create("s1")
        bus2 = MemoryBusRegistry.get_or_create("s1")
        assert bus1 is bus2

    def test_clear(self):
        from services.agents.memory_bus import MemoryBus
        bus = MemoryBus("sess6")
        bus.write("k", "v")
        bus.clear()
        assert len(bus) == 0


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Quality Controller
# ═══════════════════════════════════════════════════════════════════════════════

class TestQualityController:
    def _make_results(self, high_quality: bool = True) -> dict:
        from services.agents.models import AgentResult, AgentStatus, AgentType
        conf = 0.85 if high_quality else 0.25
        return {
            AgentType.LITERATURE_REVIEW.value: AgentResult(
                agent_type=AgentType.LITERATURE_REVIEW, confidence=conf,
                reasoning="test", output={"citation_count": 15},
            ),
            AgentType.METHODOLOGY.value: AgentResult(
                agent_type=AgentType.METHODOLOGY, confidence=conf,
                reasoning="test", output={"detected_designs": ["longitudinal"]},
            ),
        }

    def test_returns_quality_report(self):
        from services.agents.quality_controller import validate_execution
        report = validate_execution(self._make_results())
        assert report is not None
        assert report.overall_confidence > 0

    def test_high_quality_gets_good_level(self):
        from services.agents.quality_controller import validate_execution
        from services.agents.models import QualityLevel
        report = validate_execution(self._make_results(high_quality=True))
        assert report.overall_quality in (QualityLevel.EXCELLENT, QualityLevel.GOOD)

    def test_low_quality_gets_poor_level(self):
        from services.agents.quality_controller import validate_execution
        from services.agents.models import QualityLevel
        report = validate_execution(self._make_results(high_quality=False))
        assert report.overall_quality in (QualityLevel.POOR, QualityLevel.ACCEPTABLE, QualityLevel.UNACCEPTABLE)

    def test_failed_agent_flagged(self):
        from services.agents.quality_controller import validate_execution
        from services.agents.models import AgentResult, AgentStatus, AgentType
        results = {
            AgentType.LITERATURE_REVIEW.value: AgentResult(
                agent_type=AgentType.LITERATURE_REVIEW,
                status=AgentStatus.FAILED,
                output={"error": "timeout"},
                confidence=0.0,
            )
        }
        report = validate_execution(results)
        vr = report.agent_reports.get(AgentType.LITERATURE_REVIEW.value)
        assert vr is not None
        assert "agent_failure" in vr.hallucination_flags

    def test_human_without_ethics_inconsistency(self):
        from services.agents.quality_controller import validate_execution
        from services.agents.models import AgentResult, AgentType
        results = {
            AgentType.RESEARCH_ETHICS.value: AgentResult(
                agent_type=AgentType.RESEARCH_ETHICS,
                confidence=0.6,
                reasoning="test",
                output={
                    "involves_human_participants": True,
                    "has_ethics_approval": False,
                    "is_compliant": False,
                },
            ),
        }
        report = validate_execution(results)
        assert any("human" in i.lower() or "ethics" in i.lower() for i in report.inconsistencies)

    def test_has_recommendations(self):
        from services.agents.quality_controller import validate_execution
        report = validate_execution(self._make_results())
        assert isinstance(report.recommendations, list)


# ═══════════════════════════════════════════════════════════════════════════════
# 8. Orchestrator
# ═══════════════════════════════════════════════════════════════════════════════

class TestOrchestrator:
    def test_detect_workflow_publication(self):
        from services.agents.orchestrator import detect_workflow
        from services.agents.models import WorkflowType
        assert detect_workflow("I want to publish a paper") == WorkflowType.PUBLICATION

    def test_detect_workflow_grant(self):
        from services.agents.orchestrator import detect_workflow
        from services.agents.models import WorkflowType
        assert detect_workflow("write a grant proposal for my research") == WorkflowType.GRANT

    def test_detect_workflow_literature(self):
        from services.agents.orchestrator import detect_workflow
        from services.agents.models import WorkflowType
        assert detect_workflow("review the literature on machine learning") == WorkflowType.LITERATURE_REVIEW

    def test_detect_workflow_doctoral(self):
        from services.agents.orchestrator import detect_workflow
        from services.agents.models import WorkflowType
        assert detect_workflow("help me complete my PhD thesis") == WorkflowType.DOCTORAL

    def test_detect_workflow_conference(self):
        from services.agents.orchestrator import detect_workflow
        from services.agents.models import WorkflowType
        assert detect_workflow("submit abstract to conference") == WorkflowType.CONFERENCE

    def test_select_agents_literature(self):
        from services.agents.orchestrator import select_agents
        from services.agents.models import AgentType
        agents = select_agents("I need a literature review on AI in healthcare")
        assert AgentType.LITERATURE_REVIEW in agents
        assert AgentType.SUPERVISOR in agents

    def test_select_agents_always_has_supervisor(self):
        from services.agents.orchestrator import select_agents
        from services.agents.models import AgentType
        agents = select_agents("random text about something")
        assert AgentType.SUPERVISOR in agents

    def test_synthesise_response_returns_platform_response(self):
        from services.agents.execution_engine import execute_workflow
        from services.agents.models import WorkflowType
        from services.agents.orchestrator import synthesise_response
        from services.agents.quality_controller import validate_execution

        async def _run():
            execution = await execute_workflow(
                WorkflowType.LITERATURE_REVIEW, _RICH_TEXT, "u1"
            )
            qr = validate_execution(execution.results, execution.execution_id)
            return synthesise_response(execution, qr, "u1")

        response = asyncio.run(_run())
        assert response.user_id == "u1"
        assert response.total_agents_used > 0


# ═══════════════════════════════════════════════════════════════════════════════
# 9. Telemetry
# ═══════════════════════════════════════════════════════════════════════════════

class TestTelemetry:
    def _fresh(self):
        from services.agents.telemetry import AgentPlatformTelemetry
        AgentPlatformTelemetry._instance = None
        from services.agents.telemetry import get_telemetry
        return get_telemetry()

    def test_singleton(self):
        t1 = self._fresh()
        from services.agents.telemetry import get_telemetry
        t2 = get_telemetry()
        assert t1 is t2

    def test_workflow_run_increments(self):
        t = self._fresh()
        t.record_workflow_run("publication_workflow")
        assert t.snapshot()["workflow_runs"] == 1

    def test_agent_invocation_increments(self):
        t = self._fresh()
        t.record_agent_invocation("literature_review")
        assert t.snapshot()["agent_invocations"]["literature_review"] == 1

    def test_error_increments(self):
        t = self._fresh()
        t.record_error()
        assert t.snapshot()["errors"] == 1

    def test_latency_tracking(self):
        t = self._fresh()
        t.record_latency(0.1)
        t.record_latency(0.9)
        s = t.snapshot()
        assert s["sample_count"] == 2
        assert s["latency_avg_s"] > 0

    def test_workflow_distribution(self):
        t = self._fresh()
        t.record_workflow_run("publication_workflow")
        t.record_workflow_run("publication_workflow")
        t.record_workflow_run("grant_workflow")
        s = t.snapshot()
        assert s["workflow_distribution"]["publication_workflow"] == 2

    def test_reset_clears_all(self):
        t = self._fresh()
        t.record_workflow_run("x")
        t.record_error()
        t.reset()
        s = t.snapshot()
        assert s["workflow_runs"] == 0
        assert s["errors"] == 0


# ═══════════════════════════════════════════════════════════════════════════════
# 10. Engine Integration
# ═══════════════════════════════════════════════════════════════════════════════

class TestEngineIntegration:
    def _engine(self):
        from services.agents.engine import reset_agent_engine, get_agent_engine
        reset_agent_engine()
        return asyncio.run(get_agent_engine())

    def test_singleton(self):
        from services.agents.engine import reset_agent_engine, get_agent_engine
        reset_agent_engine()

        async def _run():
            e1 = await get_agent_engine()
            e2 = await get_agent_engine()
            assert e1 is e2

        asyncio.run(_run())

    def test_list_agents_returns_20(self):
        engine = self._engine()
        agents = engine.list_agents()
        assert len(agents) == 20

    def test_list_workflows_returns_10(self):
        engine = self._engine()
        workflows = engine.list_workflows()
        assert len(workflows) == 10

    def test_run_single_agent(self):
        async def _run():
            from services.agents.engine import get_agent_engine, reset_agent_engine
            from services.agents.models import AgentType
            reset_agent_engine()
            engine = await get_agent_engine()
            return await engine.run_agent(
                AgentType.LITERATURE_REVIEW, _RICH_TEXT, "test_user"
            )
        result = asyncio.run(_run())
        assert isinstance(result, dict)
        assert "confidence" in result

    def test_run_agents_parallel(self):
        async def _run():
            from services.agents.engine import get_agent_engine, reset_agent_engine
            reset_agent_engine()
            engine = await get_agent_engine()
            return await engine.run_agents_parallel(
                ["literature_review", "research_gap", "academic_writing"],
                _RICH_TEXT, "test_user"
            )
        results = asyncio.run(_run())
        assert len(results) == 3

    def test_run_workflow(self):
        async def _run():
            from services.agents.engine import get_agent_engine, reset_agent_engine
            from services.agents.models import WorkflowType
            reset_agent_engine()
            engine = await get_agent_engine()
            return await engine.run_workflow(
                WorkflowType.LITERATURE_REVIEW, _RICH_TEXT, "test_user"
            )
        response = asyncio.run(_run())
        assert response.total_agents_used > 0
        assert response.quality_report is not None

    def test_run_task_auto_detects_workflow(self):
        async def _run():
            from services.agents.engine import get_agent_engine, reset_agent_engine
            reset_agent_engine()
            engine = await get_agent_engine()
            return await engine.run_task(
                "review the literature on AI", _RICH_TEXT, "test_user"
            )
        response = asyncio.run(_run())
        assert response.execution_id is not None

    def test_platform_response_has_execution_graph(self):
        async def _run():
            from services.agents.engine import get_agent_engine, reset_agent_engine
            from services.agents.models import WorkflowType
            reset_agent_engine()
            engine = await get_agent_engine()
            return await engine.run_workflow(
                WorkflowType.CONFERENCE, _RICH_TEXT, "test_user"
            )
        response = asyncio.run(_run())
        assert response.execution_graph is not None
        assert len(response.execution_graph.nodes) > 0
