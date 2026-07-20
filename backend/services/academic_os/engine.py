"""Academic OS Engine — unified facade composing all OS subsystems."""
from __future__ import annotations

import asyncio
import time

from .activity_timeline   import ActivityTimeline
from .dashboard_engine    import get_dashboard, get_available_roles
from .global_search       import GlobalSearch
from .knowledge_sync      import KnowledgeSync
from .models              import OSHealthReport, WorkflowType, UserRole
from .notification_engine import NotificationEngine
from .project_center      import ProjectCenter
from .telemetry           import get_aos_telemetry
from .workflow_automation import WorkflowAutomation
from .workflow_engine     import WorkflowEngine

_engine_instance: "AcademicOSEngine | None" = None
_engine_lock                                 = asyncio.Lock()


class AcademicOSEngine:
    def __init__(self):
        self.workflows     = WorkflowEngine()
        self.projects      = ProjectCenter()
        self.search        = GlobalSearch()
        self.timeline      = ActivityTimeline()
        self.notifications = NotificationEngine()
        self.automation    = WorkflowAutomation()
        self.sync          = KnowledgeSync()
        self._telemetry    = get_aos_telemetry()

        # Install sensible default automation rules
        self.automation.install_default_rules()

    # ── Workflow operations ────────────────────────────────────────────────────

    def start_workflow(
        self,
        workflow_type: str,
        name:          str,
        owner_cohort:  str,
        project_id:    str = "",
        context:       dict | None = None,
    ) -> dict:
        t0 = time.time()
        wf = self.workflows.create_workflow(
            workflow_type=workflow_type,
            name=name,
            owner_cohort=owner_cohort,
            project_id=project_id,
            context=context or {},
        )
        # Emit sync event
        self.sync.emit("workflow_engine", "workflow", wf.workflow_id, "created", {"type": workflow_type})
        # Record timeline
        self.timeline.record_event("workflow_step", "workflow", wf.workflow_id, owner_cohort,
                                   f"Started workflow: {name}", project_id)
        self._telemetry.inc("workflows_created")
        self._telemetry.record_latency(time.time() - t0)
        return wf.to_dict()

    def advance_workflow_step(
        self,
        workflow_id:  str,
        step_output:  dict | None = None,
    ) -> dict | None:
        wf = self.workflows.advance_step(workflow_id, step_output)
        if not wf:
            return None
        self._telemetry.inc("workflow_steps_advanced")
        # Notify on completion
        if wf.status == "completed":
            self.notifications.notify(
                notification_type="workflow_complete",
                user_cohort=wf.owner_cohort,
                title=f"Workflow complete: {wf.name}",
                body="All workflow steps have been completed successfully.",
            )
            self.timeline.record_event("milestone", "workflow", workflow_id, wf.owner_cohort,
                                       f"Workflow completed: {wf.name}", wf.project_id)
        return wf.to_dict()

    # ── Project operations ────────────────────────────────────────────────────

    def create_project(
        self,
        name:         str,
        owner_cohort: str,
        description:  str       = "",
        tags:         list      | None = None,
        auto_index:   bool              = True,
    ) -> dict:
        t0 = time.time()
        project = self.projects.create_project(name, owner_cohort, description, tags)
        if auto_index:
            self.search.index_entity(
                entity_type="project",
                entity_id=project.project_id,
                title=name,
                content=description,
                tags=project.tags,
                owner_cohort=owner_cohort,
            )
        self.timeline.record_event("project_update", "project", project.project_id, owner_cohort,
                                   f"Created project: {name}")
        # Fire automation rules
        self._eval_automation("entity_created", {"entity_type": "project", "entity_id": project.project_id})
        self._telemetry.inc("projects_created")
        self._telemetry.record_latency(time.time() - t0)
        return project.to_dict()

    # ── Search ────────────────────────────────────────────────────────────────

    def global_search(
        self,
        query:        str,
        entity_types: list[str] | None = None,
        owner_cohort: str       | None = None,
        limit:        int               = 20,
    ) -> dict:
        t0      = time.time()
        results = self.search.search(query, entity_types, owner_cohort, limit)
        self._telemetry.inc("searches_run")
        self._telemetry.record_latency(time.time() - t0)
        return {
            "query":   query,
            "total":   len(results),
            "results": [r.to_dict() for r in results],
        }

    def index_entity(
        self,
        entity_type:  str,
        entity_id:    str,
        title:        str,
        content:      str       = "",
        tags:         list      | None = None,
        owner_cohort: str       = "general",
    ) -> dict:
        entry = self.search.index_entity(entity_type, entity_id, title, content, tags, owner_cohort)
        self._telemetry.inc("entities_indexed")
        # Sync to search dependents
        self.sync.emit("search", entity_type, entity_id, "updated")
        return {"indexed": True, "entity_type": entity_type, "entity_id": entity_id, "indexed_at": entry.indexed_at}

    # ── Timeline ──────────────────────────────────────────────────────────────

    def record_activity(
        self,
        event_type:  str,
        entity_type: str       = "",
        entity_id:   str       = "",
        user_cohort: str       = "general",
        description: str       = "",
        project_id:  str       = "",
        metadata:    dict      | None = None,
    ) -> dict:
        event = self.timeline.record_event(event_type, entity_type, entity_id,
                                           user_cohort, description, project_id, metadata)
        self._telemetry.inc("timeline_events")
        return event.to_dict()

    def get_timeline(
        self,
        user_cohort:  str | None = None,
        event_types:  list[str] | None = None,
        project_id:   str | None = None,
        since:        float | None = None,
        limit:        int = 50,
    ) -> list[dict]:
        events = self.timeline.get_timeline(user_cohort, event_types, None, project_id, since, limit)
        return [e.to_dict() for e in events]

    # ── Notifications ─────────────────────────────────────────────────────────

    def send_notification(
        self,
        notification_type: str,
        user_cohort:       str,
        title:             str,
        body:              str       = "",
        priority:          str | None = None,
        action_url:        str       = "",
    ) -> dict:
        notif = self.notifications.notify(notification_type, user_cohort, title, body, priority, action_url)
        self._telemetry.inc("notifications_sent")
        return notif.to_dict()

    def get_notifications(
        self,
        user_cohort: str,
        unread_only: bool = False,
        limit:       int  = 50,
    ) -> list[dict]:
        notifs = self.notifications.get_notifications(user_cohort, unread_only, limit)
        return [n.to_dict() for n in notifs]

    # ── Dashboard ─────────────────────────────────────────────────────────────

    def get_dashboard(self, user_role: str, metrics: dict | None = None) -> dict:
        config = get_dashboard(user_role, metrics)
        self._telemetry.inc("dashboards_generated")
        return config.to_dict()

    def get_available_roles(self) -> list[str]:
        return get_available_roles()

    # ── Automation ────────────────────────────────────────────────────────────

    def _eval_automation(self, event_type: str, payload: dict) -> list[dict]:
        triggered = self.automation.evaluate_event(event_type, payload)
        if triggered:
            self._telemetry.inc("automation_triggered", len(triggered))
        return triggered

    def fire_automation_event(self, event_type: str, payload: dict) -> dict:
        triggered = self._eval_automation(event_type, payload)
        return {"event_type": event_type, "rules_triggered": len(triggered), "actions": triggered}

    # ── Knowledge Sync ────────────────────────────────────────────────────────

    def emit_sync(
        self,
        source_module: str,
        entity_type:   str,
        entity_id:     str,
        change_type:   str,
        payload:       dict | None = None,
    ) -> dict:
        event = self.sync.emit(source_module, entity_type, entity_id, change_type, payload)
        self._telemetry.inc("sync_events_emitted")
        return event.to_dict()

    def process_sync_queue(self, max_batch: int = 20) -> list[dict]:
        return self.sync.process_pending(max_batch)

    # ── Health ────────────────────────────────────────────────────────────────

    def get_health(self) -> dict:
        now        = time.time()
        since_24h  = now - 86400

        wf_summary   = self.workflows.summary()
        proj_stats   = self.projects.stats()
        notif_stats  = self.notifications.stats()
        sync_stats   = self.sync.stats()
        auto_stats   = self.automation.stats()
        search_stats = self.search.stats()
        events_24h   = self.timeline.count_since(since_24h)

        active_wf    = wf_summary["by_status"].get("running", 0)
        overall      = min(1.0, (
            0.3 * min(proj_stats["active"] / max(1, proj_stats["total"]), 1.0)
            + 0.2 * min(active_wf / 10, 1.0)
            + 0.2 * (1 - min(sync_stats["pending"] / 200, 1.0))
            + 0.15 * min(events_24h / 100, 1.0)
            + 0.15 * min(auto_stats["enabled"] / max(1, auto_stats["total"]), 1.0)
        ))

        report = OSHealthReport(
            overall_health=round(overall, 4),
            active_workflows=active_wf,
            active_projects=proj_stats["active"],
            notifications_pending=notif_stats["unread"],
            sync_queue_depth=sync_stats["pending"],
            automation_rules_active=auto_stats["enabled"],
            search_index_size=search_stats["total_indexed"],
            timeline_events_24h=events_24h,
        )
        return report.to_dict()

    def get_telemetry(self) -> dict:
        return self._telemetry.snapshot()

    def admin_summary(self) -> dict:
        return {
            "workflows":      self.workflows.summary(),
            "projects":       self.projects.stats(),
            "search":         self.search.stats(),
            "timeline":       self.timeline.summary(),
            "notifications":  self.notifications.stats(),
            "automation":     self.automation.stats(),
            "sync":           self.sync.stats(),
            "telemetry":      self._telemetry.snapshot(),
        }


async def get_academic_os_engine() -> AcademicOSEngine:
    global _engine_instance
    if _engine_instance is None:
        async with _engine_lock:
            if _engine_instance is None:
                _engine_instance = AcademicOSEngine()
    return _engine_instance


async def reset_academic_os_engine() -> None:
    global _engine_instance
    async with _engine_lock:
        _engine_instance = None
