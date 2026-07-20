"""Phase XXI — Academic OS test suite. Target: 143+ tests."""
import asyncio
import time
import uuid

import pytest

# ── Service imports ────────────────────────────────────────────────────────────
from services.academic_os.models import (
    ActivityEvent, ActivityEventType, AutomationRule, DashboardConfig,
    DashboardWidget, EntityType, Notification, NotificationPriority,
    NotificationType, OSHealthReport, ResearchProject, SearchIndex,
    SearchResult, StepStatus, SyncChangeType, SyncEvent, TriggerType,
    UserRole, WorkflowDefinition, WorkflowStatus, WorkflowStep, WorkflowType,
)
from services.academic_os.workflow_engine  import WorkflowEngine, _make_steps
from services.academic_os.project_center   import ProjectCenter
from services.academic_os.global_search    import GlobalSearch, _tokenize, _idf, _tf
from services.academic_os.activity_timeline import ActivityTimeline
from services.academic_os.notification_engine import NotificationEngine
from services.academic_os.dashboard_engine import get_dashboard, get_available_roles
from services.academic_os.workflow_automation import WorkflowAutomation
from services.academic_os.knowledge_sync   import KnowledgeSync
from services.academic_os.telemetry        import AOSTelemetry, get_aos_telemetry, reset_aos_telemetry
from services.academic_os.engine           import AcademicOSEngine, get_academic_os_engine, reset_academic_os_engine


# ══════════════════════════════════════════════════════════════════════════════
# TestModels
# ══════════════════════════════════════════════════════════════════════════════
class TestModels:
    def test_workflow_type_values(self):
        assert WorkflowType.RESEARCH_PIPELINE.value  == "research_pipeline"
        assert WorkflowType.MANUSCRIPT_PIPELINE.value == "manuscript_pipeline"
        assert WorkflowType.GRANT_PIPELINE.value      == "grant_pipeline"
        assert WorkflowType.CAREER_PIPELINE.value     == "career_pipeline"
        assert WorkflowType.COLLABORATION_PIPELINE.value == "collaboration_pipeline"
        assert WorkflowType.CUSTOM.value              == "custom"

    def test_workflow_status_values(self):
        assert WorkflowStatus.DRAFT.value     == "draft"
        assert WorkflowStatus.RUNNING.value   == "running"
        assert WorkflowStatus.COMPLETED.value == "completed"
        assert WorkflowStatus.FAILED.value    == "failed"

    def test_step_status_values(self):
        assert StepStatus.PENDING.value   == "pending"
        assert StepStatus.RUNNING.value   == "running"
        assert StepStatus.COMPLETED.value == "completed"
        assert StepStatus.SKIPPED.value   == "skipped"

    def test_entity_type_values(self):
        assert EntityType.USER.value        == "user"
        assert EntityType.PROJECT.value     == "project"
        assert EntityType.PUBLICATION.value == "publication"

    def test_notification_priority_order(self):
        vals = [e.value for e in NotificationPriority]
        assert "critical" in vals and "low" in vals

    def test_user_role_values(self):
        roles = [r.value for r in UserRole]
        assert "student" in roles
        assert "professor" in roles
        assert "administrator" in roles
        assert len(roles) == 7

    def test_workflow_step_to_dict(self):
        step = WorkflowStep(name="Lit Review", engine_type="literature_review", order=0)
        d    = step.to_dict()
        assert d["name"]        == "Lit Review"
        assert d["engine_type"] == "literature_review"
        assert d["order"]       == 0
        assert d["status"]      == StepStatus.PENDING.value

    def test_workflow_definition_to_dict(self):
        wf = WorkflowDefinition(
            workflow_type=WorkflowType.MANUSCRIPT_PIPELINE.value,
            name="Test WF",
            steps=[WorkflowStep(name="S1", order=0), WorkflowStep(name="S2", order=1)],
        )
        d = wf.to_dict()
        assert d["workflow_type"] == "manuscript_pipeline"
        assert len(d["steps"]) == 2

    def test_workflow_definition_progress(self):
        wf = WorkflowDefinition(
            steps=[
                WorkflowStep(name="S1", order=0, status=StepStatus.COMPLETED.value),
                WorkflowStep(name="S2", order=1, status=StepStatus.PENDING.value),
            ]
        )
        wf._update_progress()
        assert wf.progress_pct == 0.5

    def test_research_project_to_dict(self):
        p = ResearchProject(name="My Project", owner_cohort="user1")
        d = p.to_dict()
        assert d["name"]         == "My Project"
        assert d["owner_cohort"] == "user1"
        assert isinstance(d["document_ids"], list)

    def test_search_index_searchable_text(self):
        entry = SearchIndex(title="Quantum Computing", content="superposition", tags=["physics"])
        text = entry.searchable_text()
        assert "quantum" in text
        assert "superposition" in text
        assert "physics" in text

    def test_search_result_to_dict(self):
        r = SearchResult(entity_type="publication", entity_id="p1", title="Test", score=0.75)
        d = r.to_dict()
        assert d["score"] == 0.75
        assert d["entity_type"] == "publication"

    def test_activity_event_to_dict(self):
        e = ActivityEvent(event_type="upload", user_cohort="u1")
        d = e.to_dict()
        assert d["event_type"] == "upload"

    def test_notification_to_dict(self):
        n = Notification(notification_type="grant_deadline", title="Apply now!", user_cohort="u1")
        d = n.to_dict()
        assert d["title"] == "Apply now!"
        assert d["read"]  is False

    def test_dashboard_widget_to_dict(self):
        w = DashboardWidget(widget_type="research_impact", title="Impact")
        d = w.to_dict()
        assert d["widget_type"] == "research_impact"
        assert d["visible"] is True

    def test_automation_rule_to_dict(self):
        r = AutomationRule(name="Test Rule", trigger_type="manuscript_quality")
        d = r.to_dict()
        assert d["name"] == "Test Rule"
        assert d["enabled"] is True

    def test_sync_event_to_dict(self):
        e = SyncEvent(source_module="manuscript", entity_type="document", entity_id="d1", change_type="updated")
        d = e.to_dict()
        assert d["source_module"] == "manuscript"
        assert d["status"] == "pending"

    def test_os_health_report_to_dict(self):
        r = OSHealthReport(overall_health=0.87, active_workflows=3)
        d = r.to_dict()
        assert d["overall_health"] == 0.87
        assert d["active_workflows"] == 3


# ══════════════════════════════════════════════════════════════════════════════
# TestWorkflowEngine
# ══════════════════════════════════════════════════════════════════════════════
class TestWorkflowEngine:
    def setup_method(self):
        self.engine = WorkflowEngine()

    def test_create_research_pipeline(self):
        wf = self.engine.create_workflow(
            workflow_type=WorkflowType.RESEARCH_PIPELINE.value,
            name="My PhD Pipeline",
            owner_cohort="user1",
        )
        assert wf.workflow_type == WorkflowType.RESEARCH_PIPELINE.value
        assert wf.status        == WorkflowStatus.RUNNING.value
        assert len(wf.steps)    == 17

    def test_first_step_is_running(self):
        wf = self.engine.create_workflow(
            workflow_type=WorkflowType.MANUSCRIPT_PIPELINE.value,
            name="Manuscript Flow",
            owner_cohort="user1",
        )
        assert wf.steps[0].status == StepStatus.RUNNING.value
        assert wf.steps[0].started_at > 0

    def test_advance_step_moves_to_next(self):
        wf = self.engine.create_workflow(
            workflow_type=WorkflowType.MANUSCRIPT_PIPELINE.value,
            name="WF",
            owner_cohort="u1",
        )
        updated = self.engine.advance_step(wf.workflow_id, {"result": "ok"})
        assert updated.current_step_index == 1
        assert updated.steps[0].status == StepStatus.COMPLETED.value
        assert updated.steps[1].status == StepStatus.RUNNING.value

    def test_advance_all_steps_completes_workflow(self):
        wf = self.engine.create_workflow(
            workflow_type=WorkflowType.GRANT_PIPELINE.value,
            name="Grant WF",
            owner_cohort="u1",
        )
        n = len(wf.steps)
        for _ in range(n):
            wf = self.engine.advance_step(wf.workflow_id)
        assert wf.status == WorkflowStatus.COMPLETED.value
        assert wf.completed_at > 0

    def test_skip_step(self):
        wf = self.engine.create_workflow(
            workflow_type=WorkflowType.CAREER_PIPELINE.value,
            name="Career WF",
            owner_cohort="u1",
        )
        updated = self.engine.advance_step(wf.workflow_id, None, skip_current=True)
        assert updated.steps[0].status == StepStatus.SKIPPED.value

    def test_fail_step(self):
        wf = self.engine.create_workflow(
            workflow_type=WorkflowType.MANUSCRIPT_PIPELINE.value,
            name="Fail WF",
            owner_cohort="u1",
        )
        failed = self.engine.fail_step(wf.workflow_id, "Timeout")
        assert failed.status == WorkflowStatus.FAILED.value
        assert failed.steps[0].error == "Timeout"

    def test_pause_and_resume(self):
        wf = self.engine.create_workflow(
            workflow_type=WorkflowType.COLLABORATION_PIPELINE.value,
            name="Collab WF",
            owner_cohort="u1",
        )
        ok = self.engine.pause_workflow(wf.workflow_id)
        assert ok
        got = self.engine.get_workflow(wf.workflow_id)
        assert got.status == WorkflowStatus.PAUSED.value

        ok2 = self.engine.resume_workflow(wf.workflow_id)
        assert ok2
        assert self.engine.get_workflow(wf.workflow_id).status == WorkflowStatus.RUNNING.value

    def test_cancel_workflow(self):
        wf = self.engine.create_workflow(
            workflow_type=WorkflowType.MANUSCRIPT_PIPELINE.value,
            name="Cancel WF",
            owner_cohort="u1",
        )
        ok = self.engine.cancel_workflow(wf.workflow_id)
        assert ok
        assert self.engine.get_workflow(wf.workflow_id).status == WorkflowStatus.CANCELLED.value

    def test_update_context(self):
        wf = self.engine.create_workflow(
            workflow_type=WorkflowType.CUSTOM.value,
            name="Custom WF",
            owner_cohort="u1",
        )
        ok = self.engine.update_context(wf.workflow_id, {"topic": "AI"})
        assert ok
        assert self.engine.get_workflow(wf.workflow_id).context["topic"] == "AI"

    def test_get_workflows_by_project(self):
        project_id = str(uuid.uuid4())
        self.engine.create_workflow(
            workflow_type=WorkflowType.GRANT_PIPELINE.value,
            name="WF1",
            owner_cohort="u1",
            project_id=project_id,
        )
        results = self.engine.get_workflows_by_project(project_id)
        assert len(results) == 1

    def test_get_active_workflows(self):
        self.engine.create_workflow(WorkflowType.MANUSCRIPT_PIPELINE.value, "WF", "u1")
        active = self.engine.get_active_workflows()
        assert len(active) >= 1

    def test_summary(self):
        self.engine.create_workflow(WorkflowType.MANUSCRIPT_PIPELINE.value, "WF", "u1")
        s = self.engine.summary()
        assert s["total"] >= 1
        assert "running" in s["by_status"]

    def test_custom_steps(self):
        custom = [
            {"name": "Step A", "engine_type": "copilot"},
            {"name": "Step B", "engine_type": "manuscript"},
        ]
        wf = self.engine.create_workflow(
            workflow_type=WorkflowType.CUSTOM.value,
            name="Custom",
            owner_cohort="u1",
            custom_steps=custom,
        )
        assert len(wf.steps) == 2
        assert wf.steps[0].name == "Step A"


# ══════════════════════════════════════════════════════════════════════════════
# TestProjectCenter
# ══════════════════════════════════════════════════════════════════════════════
class TestProjectCenter:
    def setup_method(self):
        self.center = ProjectCenter()

    def test_create_project(self):
        p = self.center.create_project("AI Research", "user1", tags=["ai", "ml"])
        assert p.name == "AI Research"
        assert "ai" in p.tags
        assert p.status == "active"

    def test_get_project(self):
        p   = self.center.create_project("Test", "user1")
        got = self.center.get_project(p.project_id)
        assert got.project_id == p.project_id

    def test_get_project_not_found(self):
        assert self.center.get_project("nonexistent") is None

    def test_update_project(self):
        p = self.center.create_project("Old Name", "user1")
        updated = self.center.update_project(p.project_id, {"name": "New Name", "status": "archived"})
        assert updated.name   == "New Name"
        assert updated.status == "archived"

    def test_update_project_not_found(self):
        assert self.center.update_project("x", {"name": "Y"}) is None

    def test_get_projects_by_cohort(self):
        self.center.create_project("P1", "cohort_a")
        self.center.create_project("P2", "cohort_a")
        self.center.create_project("P3", "cohort_b")
        ps = self.center.get_projects_by_cohort("cohort_a")
        assert len(ps) == 2

    def test_filter_by_status(self):
        p = self.center.create_project("P", "u1")
        self.center.update_project(p.project_id, {"status": "archived"})
        active   = self.center.get_projects_by_cohort("u1", status="active")
        archived = self.center.get_projects_by_cohort("u1", status="archived")
        assert len(active)   == 0
        assert len(archived) == 1

    def test_link_entity(self):
        p  = self.center.create_project("P", "u1")
        ok = self.center.link_entity(p.project_id, "document", "doc123")
        assert ok
        got = self.center.get_project(p.project_id)
        assert "doc123" in got.document_ids

    def test_link_unknown_entity_type(self):
        p  = self.center.create_project("P", "u1")
        ok = self.center.link_entity(p.project_id, "unknown_type", "id1")
        assert not ok

    def test_unlink_entity(self):
        p = self.center.create_project("P", "u1")
        self.center.link_entity(p.project_id, "grant", "g1")
        ok = self.center.unlink_entity(p.project_id, "grant", "g1")
        assert ok
        assert "g1" not in self.center.get_project(p.project_id).grant_ids

    def test_get_project_summary(self):
        p = self.center.create_project("P", "u1")
        self.center.link_entity(p.project_id, "document", "d1")
        self.center.link_entity(p.project_id, "grant", "g1")
        s = self.center.get_project_summary(p.project_id)
        assert s["document_count"] == 1
        assert s["grant_count"]    == 1

    def test_search_projects(self):
        self.center.create_project("Quantum Gravity Research", "u1")
        self.center.create_project("Machine Learning Models",  "u1")
        results = self.center.search_projects("quantum", "u1")
        assert len(results) == 1
        assert results[0].name == "Quantum Gravity Research"

    def test_stats(self):
        self.center.create_project("P", "u1")
        s = self.center.stats()
        assert s["total"] >= 1
        assert s["active"] >= 1

    def test_no_duplicate_link(self):
        p = self.center.create_project("P", "u1")
        self.center.link_entity(p.project_id, "document", "d1")
        self.center.link_entity(p.project_id, "document", "d1")
        got = self.center.get_project(p.project_id)
        assert got.document_ids.count("d1") == 1


# ══════════════════════════════════════════════════════════════════════════════
# TestGlobalSearch
# ══════════════════════════════════════════════════════════════════════════════
class TestGlobalSearch:
    def setup_method(self):
        self.search = GlobalSearch()

    def test_tokenize(self):
        tokens = _tokenize("Quantum Computing in Physics")
        assert "quantum" in tokens
        assert "physics" in tokens
        assert len(tokens) >= 3

    def test_tokenize_strips_punctuation(self):
        tokens = _tokenize("hello, world.")
        assert "hello" in tokens
        assert "world" in tokens

    def test_index_entity(self):
        entry = self.search.index_entity("publication", "p1", "Neural Networks", "deep learning", ["ai"])
        assert entry.entity_type == "publication"
        assert entry.entity_id   == "p1"

    def test_search_basic(self):
        self.search.index_entity("publication", "p1", "Quantum Computing Research")
        results = self.search.search("quantum")
        assert len(results) >= 1
        assert results[0].entity_type == "publication"

    def test_title_boost(self):
        self.search.index_entity("doc", "d1", "Quantum Computing", "other content", [])
        self.search.index_entity("doc", "d2", "Other Title", "quantum computing is used here", [])
        results = self.search.search("quantum")
        assert results[0].entity_id == "d1"  # title match should score higher

    def test_tag_boost(self):
        self.search.index_entity("doc", "d1", "Research Paper", "content", ["quantum"])
        self.search.index_entity("doc", "d2", "Research Paper", "quantum content here again", [])
        results = self.search.search("quantum")
        # d1 has tag match (1.5x), d2 has content match (1.0x)
        assert results[0].entity_id == "d1"

    def test_filter_by_entity_type(self):
        self.search.index_entity("publication", "p1", "Physics Research")
        self.search.index_entity("grant",       "g1", "Physics Grant")
        results = self.search.search("physics", entity_types=["grant"])
        assert all(r.entity_type == "grant" for r in results)

    def test_filter_by_owner_cohort(self):
        self.search.index_entity("doc", "d1", "Private Research", owner_cohort="user1")
        self.search.index_entity("doc", "d2", "Private Research", owner_cohort="user2")
        results = self.search.search("private", owner_cohort="user1")
        assert all(r.entity_id in ("d1",) for r in results)

    def test_empty_query_returns_empty(self):
        self.search.index_entity("doc", "d1", "Research")
        results = self.search.search("")
        assert results == []

    def test_remove_entity(self):
        self.search.index_entity("doc", "d1", "Removable Research")
        ok = self.search.remove_entity("doc", "d1")
        assert ok
        results = self.search.search("removable")
        assert len(results) == 0

    def test_remove_nonexistent(self):
        assert not self.search.remove_entity("doc", "nonexistent")

    def test_update_existing_entity(self):
        self.search.index_entity("doc", "d1", "Old Title")
        self.search.index_entity("doc", "d1", "New Title Quantum")
        results = self.search.search("quantum")
        assert results[0].entity_id == "d1"
        results_old = self.search.search("old")
        assert len(results_old) == 0

    def test_stats(self):
        self.search.index_entity("doc",  "d1", "Research One")
        self.search.index_entity("user", "u1", "Researcher Profile")
        s = self.search.stats()
        assert s["total_indexed"] == 2
        assert "doc" in s["by_entity_type"]

    def test_no_results_for_unknown_term(self):
        self.search.index_entity("doc", "d1", "Machine Learning")
        assert self.search.search("zxqwerty") == []

    def test_limit_results(self):
        for i in range(10):
            self.search.index_entity("doc", f"d{i}", f"Deep Learning Paper {i}")
        results = self.search.search("deep", limit=3)
        assert len(results) <= 3


# ══════════════════════════════════════════════════════════════════════════════
# TestActivityTimeline
# ══════════════════════════════════════════════════════════════════════════════
class TestActivityTimeline:
    def setup_method(self):
        self.tl = ActivityTimeline()

    def test_record_event(self):
        e = self.tl.record_event("upload", "document", "d1", "u1", "Uploaded paper")
        assert e.event_type  == "upload"
        assert e.entity_type == "document"
        assert e.user_cohort == "u1"

    def test_get_timeline_all(self):
        self.tl.record_event("upload", user_cohort="u1")
        self.tl.record_event("review", user_cohort="u1")
        events = self.tl.get_timeline(user_cohort="u1")
        assert len(events) >= 2

    def test_filter_by_event_type(self):
        self.tl.record_event("upload", user_cohort="u1")
        self.tl.record_event("review", user_cohort="u1")
        events = self.tl.get_timeline(event_types=["upload"])
        assert all(e.event_type == "upload" for e in events)

    def test_filter_by_project(self):
        pid = "proj1"
        self.tl.record_event("upload", project_id=pid, user_cohort="u1")
        self.tl.record_event("review",                 user_cohort="u1")
        events = self.tl.get_project_timeline(pid)
        assert all(e.project_id == pid for e in events)

    def test_filter_since(self):
        t_before = time.time() - 10
        self.tl.record_event("upload", user_cohort="u1")
        events = self.tl.get_timeline(since=t_before)
        assert len(events) >= 1

    def test_timeline_most_recent_first(self):
        self.tl.record_event("upload", user_cohort="u1")
        time.sleep(0.01)
        self.tl.record_event("review", user_cohort="u1")
        events = self.tl.get_timeline(user_cohort="u1", limit=2)
        assert events[0].event_type == "review"  # most recent first

    def test_get_recent_activity(self):
        for i in range(5):
            self.tl.record_event("upload", user_cohort="u1")
        recent = self.tl.get_recent_activity(limit=3)
        assert len(recent) == 3

    def test_count_since(self):
        t0 = time.time()
        self.tl.record_event("upload", user_cohort="u1")
        self.tl.record_event("review", user_cohort="u1")
        count = self.tl.count_since(t0 - 1)
        assert count >= 2

    def test_summary(self):
        self.tl.record_event("upload", user_cohort="u1")
        self.tl.record_event("upload", user_cohort="u1")
        s = self.tl.summary()
        assert s["total_events"] >= 2
        assert s["by_type"]["upload"] >= 2

    def test_general_cohort_visible_to_all(self):
        self.tl.record_event("system_alert", user_cohort="general")
        events = self.tl.get_timeline(user_cohort="specific_user")
        assert any(e.user_cohort == "general" for e in events)


# ══════════════════════════════════════════════════════════════════════════════
# TestNotificationEngine
# ══════════════════════════════════════════════════════════════════════════════
class TestNotificationEngine:
    def setup_method(self):
        self.engine = NotificationEngine()

    def test_notify_basic(self):
        n = self.engine.notify("grant_deadline", "u1", "Grant closing soon")
        assert n.title == "Grant closing soon"
        assert n.priority == NotificationPriority.HIGH.value

    def test_auto_priority_system_alert(self):
        n = self.engine.notify("system_alert", "u1", "Critical issue")
        assert n.priority == NotificationPriority.CRITICAL.value

    def test_auto_priority_ai_insight(self):
        n = self.engine.notify("ai_insight", "u1", "AI found something")
        assert n.priority == NotificationPriority.LOW.value

    def test_override_priority(self):
        n = self.engine.notify("ai_insight", "u1", "Important!", priority="critical")
        assert n.priority == "critical"

    def test_get_notifications(self):
        self.engine.notify("grant_deadline", "u1", "Grant 1")
        self.engine.notify("review_complete", "u1", "Review done")
        notifs = self.engine.get_notifications("u1")
        assert len(notifs) == 2

    def test_unread_only(self):
        n = self.engine.notify("grant_deadline", "u1", "Grant")
        self.engine.mark_read(n.notification_id, "u1")
        self.engine.notify("review_complete", "u1", "Review")
        unread = self.engine.get_notifications("u1", unread_only=True)
        assert len(unread) == 1

    def test_mark_read(self):
        n = self.engine.notify("citation_alert", "u1", "Cited!")
        ok = self.engine.mark_read(n.notification_id, "u1")
        assert ok
        notifs = self.engine.get_notifications("u1")
        assert next(x for x in notifs if x.notification_id == n.notification_id).read

    def test_mark_all_read(self):
        self.engine.notify("grant_deadline", "u1", "N1")
        self.engine.notify("review_complete", "u1", "N2")
        count = self.engine.mark_all_read("u1")
        assert count == 2

    def test_dismiss(self):
        n  = self.engine.notify("ai_insight", "u1", "Insight")
        ok = self.engine.dismiss(n.notification_id, "u1")
        assert ok
        notifs = self.engine.get_notifications("u1")
        assert not any(x.notification_id == n.notification_id for x in notifs)

    def test_unread_count(self):
        self.engine.notify("grant_deadline", "u1", "N1")
        self.engine.notify("review_complete", "u1", "N2")
        assert self.engine.get_unread_count("u1") == 2

    def test_broadcast(self):
        notifs = self.engine.broadcast("system_alert", ["u1", "u2", "u3"], "System update")
        assert len(notifs) == 3
        assert self.engine.get_unread_count("u1") == 1

    def test_priority_sort(self):
        self.engine.notify("ai_insight", "u1", "Low",      priority="low")
        self.engine.notify("system_alert","u1", "Critical", priority="critical")
        self.engine.notify("grant_deadline","u1","High",    priority="high")
        notifs = self.engine.get_notifications("u1")
        priorities = [n.priority for n in notifs]
        assert priorities[0] == "critical"

    def test_stats(self):
        self.engine.notify("grant_deadline", "u1", "N")
        s = self.engine.stats()
        assert s["total"] >= 1
        assert s["unread"] >= 1


# ══════════════════════════════════════════════════════════════════════════════
# TestDashboardEngine
# ══════════════════════════════════════════════════════════════════════════════
class TestDashboardEngine:
    def test_student_dashboard(self):
        config = get_dashboard("student")
        assert config.user_role == "student"
        assert len(config.widgets) >= 4

    def test_researcher_dashboard(self):
        config = get_dashboard("researcher")
        widget_types = [w.widget_type for w in config.widgets]
        assert "research_impact" in widget_types

    def test_professor_dashboard(self):
        config = get_dashboard("professor")
        widget_types = [w.widget_type for w in config.widgets]
        assert "teaching_analytics" in widget_types

    def test_administrator_dashboard(self):
        config = get_dashboard("administrator")
        widget_types = [w.widget_type for w in config.widgets]
        assert "platform_health" in widget_types
        assert "security_center" in widget_types

    def test_institution_dashboard(self):
        config = get_dashboard("institution")
        widget_types = [w.widget_type for w in config.widgets]
        assert "institution_analytics" in widget_types

    def test_phd_candidate_dashboard(self):
        config = get_dashboard("phd_candidate")
        widget_types = [w.widget_type for w in config.widgets]
        assert "citation_tracker" in widget_types

    def test_master_student_dashboard(self):
        config = get_dashboard("master_student")
        widget_types = [w.widget_type for w in config.widgets]
        assert "literature_map" in widget_types

    def test_unknown_role_falls_back_to_researcher(self):
        config = get_dashboard("super_alien_role")
        assert config.user_role == "researcher"

    def test_personalization_with_metrics(self):
        config = get_dashboard("researcher", metrics={"active_grants": 5})
        assert config.personalization.get("grant_widgets_expanded") is True

    def test_dashboard_to_dict(self):
        config = get_dashboard("student")
        d = config.to_dict()
        assert "widgets" in d
        assert "user_role" in d
        assert d["user_role"] == "student"

    def test_get_available_roles(self):
        roles = get_available_roles()
        assert len(roles) == 7
        assert "student" in roles
        assert "administrator" in roles


# ══════════════════════════════════════════════════════════════════════════════
# TestWorkflowAutomation
# ══════════════════════════════════════════════════════════════════════════════
class TestWorkflowAutomation:
    def setup_method(self):
        self.auto = WorkflowAutomation()

    def test_create_rule(self):
        rule = self.auto.create_rule(
            "My Rule", "manuscript_quality",
            {"threshold_key": "quality_score", "threshold_value": 0.90, "operator": "gte"},
            [{"action": "notify"}],
        )
        assert rule.name        == "My Rule"
        assert rule.enabled     is True
        assert rule.trigger_count == 0

    def test_get_rule(self):
        rule = self.auto.create_rule("R", "grant_deadline", {}, [])
        got  = self.auto.get_rule(rule.rule_id)
        assert got.rule_id == rule.rule_id

    def test_list_rules(self):
        self.auto.create_rule("R1", "manuscript_quality", {}, [])
        self.auto.create_rule("R2", "deadline_approaching", {}, [])
        rules = self.auto.list_rules()
        assert len(rules) >= 2

    def test_toggle_disable(self):
        rule = self.auto.create_rule("R", "manuscript_quality", {}, [])
        ok   = self.auto.toggle_rule(rule.rule_id, False)
        assert ok
        got = self.auto.get_rule(rule.rule_id)
        assert got.enabled is False

    def test_delete_rule(self):
        rule = self.auto.create_rule("R", "manuscript_quality", {}, [])
        ok   = self.auto.delete_rule(rule.rule_id)
        assert ok
        assert self.auto.get_rule(rule.rule_id) is None

    def test_evaluate_event_triggers_matching_rule(self):
        self.auto.create_rule(
            "Quality Check", "manuscript_quality",
            {"threshold_key": "quality_score", "threshold_value": 0.90, "operator": "gte"},
            [{"action": "notify"}],
        )
        triggered = self.auto.evaluate_event("manuscript_quality", {"quality_score": 0.95})
        assert len(triggered) == 1

    def test_evaluate_event_no_match(self):
        self.auto.create_rule(
            "Quality Check", "manuscript_quality",
            {"threshold_key": "quality_score", "threshold_value": 0.90, "operator": "gte"},
            [{"action": "notify"}],
        )
        triggered = self.auto.evaluate_event("manuscript_quality", {"quality_score": 0.50})
        assert len(triggered) == 0

    def test_disabled_rule_not_triggered(self):
        rule = self.auto.create_rule("R", "manuscript_quality", {}, [{"action": "x"}])
        self.auto.toggle_rule(rule.rule_id, False)
        triggered = self.auto.evaluate_event("manuscript_quality", {"quality_score": 1.0})
        assert len(triggered) == 0

    def test_install_default_rules(self):
        rules = self.auto.install_default_rules()
        assert len(rules) == 3

    def test_rule_trigger_count_increments(self):
        rule = self.auto.create_rule(
            "Counter Rule", "manuscript_quality", {}, [{"action": "count"}]
        )
        self.auto.evaluate_event("manuscript_quality", {})
        self.auto.evaluate_event("manuscript_quality", {})
        got = self.auto.get_rule(rule.rule_id)
        assert got.trigger_count == 2

    def test_match_key_condition(self):
        rule = self.auto.create_rule(
            "Entity Rule", "entity_created",
            {"match_key": "entity_type", "match_value": "publication"},
            [{"action": "update_career"}],
        )
        triggered = self.auto.evaluate_event("entity_created", {"entity_type": "publication"})
        assert len(triggered) == 1
        triggered2 = self.auto.evaluate_event("entity_created", {"entity_type": "dataset"})
        assert len(triggered2) == 0

    def test_stats(self):
        self.auto.create_rule("R1", "manuscript_quality", {}, [])
        self.auto.create_rule("R2", "deadline_approaching", {}, [])
        s = self.auto.stats()
        assert s["total"] >= 2
        assert s["enabled"] >= 2


# ══════════════════════════════════════════════════════════════════════════════
# TestKnowledgeSync
# ══════════════════════════════════════════════════════════════════════════════
class TestKnowledgeSync:
    def setup_method(self):
        self.sync = KnowledgeSync()

    def test_emit_event(self):
        e = self.sync.emit("manuscript", "document", "d1", "updated", {"words": 5000})
        assert e.source_module == "manuscript"
        assert e.entity_type   == "document"
        assert e.status        == "pending"

    def test_auto_targets_from_map(self):
        e = self.sync.emit("manuscript", "document", "d1", "updated")
        assert "project_center" in e.target_modules
        assert "knowledge_graph" in e.target_modules

    def test_custom_targets(self):
        e = self.sync.emit("custom", "entity", "e1", "created", target_modules=["alpha", "beta"])
        assert "alpha" in e.target_modules

    def test_get_event(self):
        e   = self.sync.emit("grant", "grant", "g1", "created")
        got = self.sync.get_event(e.sync_id)
        assert got.sync_id == e.sync_id

    def test_process_pending(self):
        self.sync.emit("manuscript", "doc", "d1", "updated")
        self.sync.emit("grant",      "grant", "g1", "created")
        processed = self.sync.process_pending(max_batch=10)
        assert len(processed) == 2

    def test_queue_depth(self):
        self.sync.emit("career", "profile", "p1", "updated")
        assert self.sync.queue_depth() >= 1

    def test_process_clears_queue(self):
        self.sync.emit("publication", "pub", "p1", "created")
        self.sync.process_pending()
        assert self.sync.queue_depth() == 0

    def test_get_log_filter_by_module(self):
        self.sync.emit("manuscript", "doc", "d1", "updated")
        self.sync.emit("grant",      "grant", "g1", "created")
        events = self.sync.get_log(source_module="manuscript")
        assert all(e.source_module == "manuscript" for e in events)

    def test_get_targets(self):
        targets = self.sync.get_targets("project_center")
        assert "knowledge_graph" in targets
        assert "analytics" in targets

    def test_stats(self):
        self.sync.emit("career", "profile", "p1", "updated")
        s = self.sync.stats()
        assert s["total_events"] >= 1
        assert s["pending"] >= 1


# ══════════════════════════════════════════════════════════════════════════════
# TestTelemetry
# ══════════════════════════════════════════════════════════════════════════════
class TestTelemetry:
    def setup_method(self):
        reset_aos_telemetry()

    def teardown_method(self):
        reset_aos_telemetry()

    def test_singleton(self):
        t1 = get_aos_telemetry()
        t2 = get_aos_telemetry()
        assert t1 is t2

    def test_reset(self):
        t1 = get_aos_telemetry()
        reset_aos_telemetry()
        t2 = get_aos_telemetry()
        assert t1 is not t2

    def test_inc_counter(self):
        t = get_aos_telemetry()
        t.inc("workflows_created")
        t.inc("workflows_created")
        snap = t.snapshot()
        assert snap["counters"]["workflows_created"] == 2

    def test_inc_unknown_counter_noop(self):
        t = get_aos_telemetry()
        t.inc("nonexistent_counter")
        # Should not raise

    def test_record_latency(self):
        t = get_aos_telemetry()
        t.record_latency(0.05)
        t.record_latency(0.15)
        snap = t.snapshot()
        assert snap["latency"]["samples"] == 2
        assert abs(snap["latency"]["avg_seconds"] - 0.1) < 0.001

    def test_latency_cap(self):
        t = get_aos_telemetry()
        for i in range(600):
            t.record_latency(0.01)
        snap = t.snapshot()
        assert snap["latency"]["samples"] <= 500

    def test_snapshot_has_all_counters(self):
        t    = get_aos_telemetry()
        snap = t.snapshot()
        assert "workflows_created" in snap["counters"]
        assert "errors" in snap["counters"]


# ══════════════════════════════════════════════════════════════════════════════
# TestEngineIntegration
# ══════════════════════════════════════════════════════════════════════════════
class TestEngineIntegration:
    def setup_method(self):
        reset_aos_telemetry()
        self.engine = AcademicOSEngine()

    def test_start_workflow(self):
        result = self.engine.start_workflow(
            workflow_type="manuscript_pipeline",
            name="My Manuscript Flow",
            owner_cohort="u1",
        )
        assert result["workflow_type"] == "manuscript_pipeline"
        assert result["status"]        == "running"

    def test_advance_workflow_step(self):
        result = self.engine.start_workflow("manuscript_pipeline", "WF", "u1")
        wid    = result["workflow_id"]
        adv    = self.engine.advance_workflow_step(wid, {"output": "done"})
        assert adv["current_step_index"] == 1

    def test_workflow_completion_sends_notification(self):
        result = self.engine.start_workflow("grant_pipeline", "Grant Flow", "u1")
        wid    = result["workflow_id"]
        wf_obj = self.engine.workflows.get_workflow(wid)
        n      = len(wf_obj.steps)
        for _ in range(n):
            self.engine.advance_workflow_step(wid)
        notifs = self.engine.get_notifications("u1")
        assert any("complete" in n["title"].lower() or "Workflow" in n["title"] for n in notifs)

    def test_create_project_indexes_in_search(self):
        self.engine.create_project("AI Cancer Research", "u1", "Applying AI to oncology")
        results = self.engine.global_search("cancer", owner_cohort="u1")
        assert results["total"] >= 1

    def test_create_project_records_timeline(self):
        t0 = time.time() - 1
        self.engine.create_project("Timeline Test Project", "u1")
        events = self.engine.get_timeline("u1", since=t0)
        assert any("Timeline Test Project" in e["description"] for e in events)

    def test_global_search_respects_limit(self):
        for i in range(10):
            self.engine.search.index_entity("doc", f"d{i}", f"Neural Network Paper {i}", owner_cohort="u1")
        results = self.engine.global_search("neural", owner_cohort="u1", limit=3)
        assert len(results["results"]) <= 3

    def test_record_activity(self):
        event = self.engine.record_activity("review", "manuscript", "m1", "u1", "Peer review complete")
        assert event["event_type"]  == "review"
        assert event["entity_type"] == "manuscript"

    def test_send_notification(self):
        n = self.engine.send_notification("grant_deadline", "u1", "Grant closing", "Apply by Friday")
        assert n["title"] == "Grant closing"

    def test_get_notifications_user_inbox(self):
        self.engine.send_notification("citation_alert", "u1", "You were cited!")
        notifs = self.engine.get_notifications("u1")
        assert len(notifs) >= 1

    def test_dashboard_generation(self):
        config = self.engine.get_dashboard("researcher")
        assert "widgets" in config
        assert config["user_role"] == "researcher"

    def test_dashboard_personalization(self):
        config = self.engine.get_dashboard("researcher", metrics={"publications_per_year": 10})
        assert config.get("personalization", {}).get("publication_focus") is True

    def test_fire_automation_event(self):
        result = self.engine.fire_automation_event(
            "manuscript_quality", {"quality_score": 0.95}
        )
        assert "rules_triggered" in result

    def test_emit_sync(self):
        event = self.engine.emit_sync("grant", "grant", "g1", "created", {"funder": "NSF"})
        assert event["source_module"] == "grant"
        assert event["status"]        == "pending"

    def test_process_sync_queue(self):
        self.engine.emit_sync("career", "profile", "p1", "updated")
        self.engine.emit_sync("manuscript", "doc", "d1", "updated")
        processed = self.engine.process_sync_queue(max_batch=10)
        assert len(processed) == 2

    def test_health_report(self):
        health = self.engine.get_health()
        assert "overall_health" in health
        assert 0.0 <= health["overall_health"] <= 1.0

    def test_telemetry_increments(self):
        self.engine.start_workflow("manuscript_pipeline", "WF", "u1")
        snap = self.engine.get_telemetry()
        assert snap["counters"]["workflows_created"] >= 1

    def test_admin_summary(self):
        summary = self.engine.admin_summary()
        assert "workflows"  in summary
        assert "projects"   in summary
        assert "search"     in summary
        assert "telemetry"  in summary

    def test_index_entity(self):
        result = self.engine.index_entity("publication", "pub1", "Nobel Prize Research")
        assert result["indexed"] is True

    def test_get_available_roles(self):
        roles = self.engine.get_available_roles()
        assert "administrator" in roles


# ══════════════════════════════════════════════════════════════════════════════
# TestAsyncSingleton
# ══════════════════════════════════════════════════════════════════════════════
class TestAsyncSingleton:
    def test_singleton_same_instance(self):
        asyncio.run(reset_academic_os_engine())

        async def run():
            e1 = await get_academic_os_engine()
            e2 = await get_academic_os_engine()
            return e1 is e2
        assert asyncio.run(run()) is True

    def test_reset_creates_new_instance(self):
        async def run():
            await reset_academic_os_engine()
            e1 = await get_academic_os_engine()
            await reset_academic_os_engine()
            e2 = await get_academic_os_engine()
            return e1 is not e2
        assert asyncio.run(run()) is True

    def test_engine_starts_with_default_rules(self):
        async def run():
            await reset_academic_os_engine()
            engine = await get_academic_os_engine()
            return engine.automation.list_rules(enabled_only=True)
        rules = asyncio.run(run())
        assert len(rules) >= 3


# ══════════════════════════════════════════════════════════════════════════════
# TestPlansCatalogue
# ══════════════════════════════════════════════════════════════════════════════
class TestPlansCatalogue:
    def test_aos_workflow_cost(self):
        from plans_catalogue import get_credit_cost
        assert get_credit_cost("aos_workflow", 0)   == 5

    def test_aos_project_cost(self):
        from plans_catalogue import get_credit_cost
        assert get_credit_cost("aos_project", 0)    == 2

    def test_aos_search_cost(self):
        from plans_catalogue import get_credit_cost
        assert get_credit_cost("aos_search", 0)     == 2

    def test_aos_dashboard_cost(self):
        from plans_catalogue import get_credit_cost
        assert get_credit_cost("aos_dashboard", 0)  == 1

    def test_aos_automation_cost(self):
        from plans_catalogue import get_credit_cost
        assert get_credit_cost("aos_automation", 0) == 3


# ══════════════════════════════════════════════════════════════════════════════
# TestWorkflowStepTemplates
# ══════════════════════════════════════════════════════════════════════════════
class TestWorkflowStepTemplates:
    def test_research_pipeline_has_17_steps(self):
        steps = _make_steps("research_pipeline")
        assert len(steps) == 17

    def test_manuscript_pipeline_has_6_steps(self):
        steps = _make_steps("manuscript_pipeline")
        assert len(steps) == 6

    def test_grant_pipeline_has_6_steps(self):
        steps = _make_steps("grant_pipeline")
        assert len(steps) == 6

    def test_career_pipeline_has_5_steps(self):
        steps = _make_steps("career_pipeline")
        assert len(steps) == 5

    def test_collaboration_pipeline_has_5_steps(self):
        steps = _make_steps("collaboration_pipeline")
        assert len(steps) == 5

    def test_custom_workflow_empty_steps(self):
        steps = _make_steps("custom")
        assert steps == []

    def test_steps_have_correct_order(self):
        steps = _make_steps("manuscript_pipeline")
        for i, step in enumerate(steps):
            assert step.order == i

    def test_steps_are_workflow_step_instances(self):
        steps = _make_steps("grant_pipeline")
        for step in steps:
            assert isinstance(step, WorkflowStep)


# ══════════════════════════════════════════════════════════════════════════════
# TestSearchHelpers
# ══════════════════════════════════════════════════════════════════════════════
class TestSearchHelpers:
    def test_tf_exact(self):
        tokens = ["quantum", "computing", "quantum"]
        assert _tf(tokens, "quantum") == pytest.approx(2/3)

    def test_tf_zero(self):
        tokens = ["physics", "chemistry"]
        assert _tf(tokens, "quantum") == 0.0

    def test_tf_empty_tokens(self):
        assert _tf([], "quantum") == 0.0

    def test_idf_basic(self):
        score = _idf(10, 5)
        assert score > 0

    def test_idf_more_docs_higher_score_for_rare(self):
        rare   = _idf(100, 1)
        common = _idf(100, 90)
        assert rare > common

    def test_tokenize_removes_short(self):
        tokens = _tokenize("a an the quantum")
        assert "a" not in tokens
        assert "quantum" in tokens

    def test_tokenize_lowercase(self):
        tokens = _tokenize("QUANTUM Computing")
        assert "quantum" in tokens
        assert "computing" in tokens
