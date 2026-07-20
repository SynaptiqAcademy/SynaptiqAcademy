"""Academic OS Router — Phase XXI Enterprise Academic Operating System."""
from __future__ import annotations

from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth_utils import get_current_user
from plans_catalogue import get_credit_cost
from services.credits_service import consume_credits
from services.academic_os import get_academic_os_engine

router       = APIRouter(prefix="/api/aos", tags=["Academic OS"])
admin_router = APIRouter(prefix="/api/admin/aos", tags=["Admin: Academic OS"])


# ── Request models ────────────────────────────────────────────────────────────

class StartWorkflowRequest(BaseModel):
    workflow_type: str
    name:          str
    project_id:    str  = ""
    context:       dict = Field(default_factory=dict)


class AdvanceStepRequest(BaseModel):
    workflow_id: str
    step_output: Optional[dict] = None


class FailStepRequest(BaseModel):
    workflow_id: str
    error:       str


class PauseResumeRequest(BaseModel):
    workflow_id: str


class UpdateWorkflowContextRequest(BaseModel):
    workflow_id:      str
    context_updates:  dict


class CreateProjectRequest(BaseModel):
    name:        str
    description: str  = ""
    tags:        List[str] = Field(default_factory=list)


class UpdateProjectRequest(BaseModel):
    updates: dict


class LinkEntityRequest(BaseModel):
    entity_type: str
    entity_id:   str


class SearchRequest(BaseModel):
    query:        str
    entity_types: Optional[List[str]] = None
    limit:        int                  = 20


class IndexEntityRequest(BaseModel):
    entity_type:  str
    entity_id:    str
    title:        str
    content:      str       = ""
    tags:         List[str] = Field(default_factory=list)


class ActivityRequest(BaseModel):
    event_type:  str
    entity_type: str  = ""
    entity_id:   str  = ""
    description: str  = ""
    project_id:  str  = ""


class NotificationRequest(BaseModel):
    notification_type: str
    title:             str
    body:              str       = ""
    priority:          Optional[str] = None
    action_url:        str       = ""


class BroadcastRequest(BaseModel):
    notification_type: str
    cohorts:           List[str]
    title:             str
    body:              str = ""


class DashboardRequest(BaseModel):
    user_role: str
    metrics:   Optional[dict] = None


class AutomationRuleRequest(BaseModel):
    name:              str
    trigger_type:      str
    trigger_condition: dict
    actions:           List[dict]


class AutomationEventRequest(BaseModel):
    event_type: str
    payload:    dict = Field(default_factory=dict)


class SyncEmitRequest(BaseModel):
    source_module:  str
    entity_type:    str
    entity_id:      str
    change_type:    str
    payload:        dict = Field(default_factory=dict)
    target_modules: Optional[List[str]] = None


# ── User endpoints ────────────────────────────────────────────────────────────

@router.get("/available-workflow-types")
async def get_workflow_types(user: dict = Depends(get_current_user)):
    from services.academic_os.models import WorkflowType
    return {"workflow_types": [wt.value for wt in WorkflowType]}


@router.post("/workflow/start")
async def start_workflow(req: StartWorkflowRequest, user: dict = Depends(get_current_user)):
    cost    = get_credit_cost("aos_workflow", 5)
    user_id = str(user.get("_id", ""))
    await consume_credits(user_id, cost)
    engine  = await get_academic_os_engine()
    result  = engine.start_workflow(
        workflow_type=req.workflow_type,
        name=req.name,
        owner_cohort=user_id,
        project_id=req.project_id,
        context=req.context,
    )
    return {"success": True, "workflow": result}


@router.post("/workflow/advance")
async def advance_step(req: AdvanceStepRequest, user: dict = Depends(get_current_user)):
    engine = await get_academic_os_engine()
    result = engine.advance_workflow_step(req.workflow_id, req.step_output)
    if result is None:
        raise HTTPException(status_code=404, detail="Workflow not found or not running")
    return {"success": True, "workflow": result}


@router.post("/workflow/fail-step")
async def fail_step(req: FailStepRequest, user: dict = Depends(get_current_user)):
    engine = await get_academic_os_engine()
    result = engine.workflows.fail_step(req.workflow_id, req.error)
    if not result:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"success": True, "workflow": result.to_dict()}


@router.post("/workflow/pause")
async def pause_workflow(req: PauseResumeRequest, user: dict = Depends(get_current_user)):
    engine = await get_academic_os_engine()
    ok = engine.workflows.pause_workflow(req.workflow_id)
    return {"success": ok}


@router.post("/workflow/resume")
async def resume_workflow(req: PauseResumeRequest, user: dict = Depends(get_current_user)):
    engine = await get_academic_os_engine()
    ok = engine.workflows.resume_workflow(req.workflow_id)
    return {"success": ok}


@router.post("/workflow/cancel")
async def cancel_workflow(req: PauseResumeRequest, user: dict = Depends(get_current_user)):
    engine = await get_academic_os_engine()
    ok = engine.workflows.cancel_workflow(req.workflow_id)
    return {"success": ok}


@router.post("/workflow/update-context")
async def update_workflow_context(req: UpdateWorkflowContextRequest, user: dict = Depends(get_current_user)):
    engine = await get_academic_os_engine()
    ok = engine.workflows.update_context(req.workflow_id, req.context_updates)
    return {"success": ok}


@router.get("/workflow/{workflow_id}")
async def get_workflow(workflow_id: str, user: dict = Depends(get_current_user)):
    engine = await get_academic_os_engine()
    wf = engine.workflows.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf.to_dict()


@router.get("/workflows/my")
async def get_my_workflows(user: dict = Depends(get_current_user)):
    engine   = await get_academic_os_engine()
    user_id  = str(user.get("_id", ""))
    all_wfs  = engine.workflows.get_all_workflows(limit=200)
    my_wfs   = [w for w in all_wfs if w.owner_cohort == user_id]
    return {"workflows": [w.to_dict() for w in my_wfs]}


# ── Project endpoints ──────────────────────────────────────────────────────────

@router.post("/project/create")
async def create_project(req: CreateProjectRequest, user: dict = Depends(get_current_user)):
    cost    = get_credit_cost("aos_project", 2)
    user_id = str(user.get("_id", ""))
    await consume_credits(user_id, cost)
    engine  = await get_academic_os_engine()
    result  = engine.create_project(req.name, user_id, req.description, req.tags)
    return {"success": True, "project": result}


@router.get("/project/{project_id}")
async def get_project(project_id: str, user: dict = Depends(get_current_user)):
    engine = await get_academic_os_engine()
    project = engine.projects.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project.to_dict()


@router.get("/project/{project_id}/summary")
async def get_project_summary(project_id: str, user: dict = Depends(get_current_user)):
    engine  = await get_academic_os_engine()
    summary = engine.projects.get_project_summary(project_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Project not found")
    return summary


@router.put("/project/{project_id}")
async def update_project(project_id: str, req: UpdateProjectRequest, user: dict = Depends(get_current_user)):
    engine  = await get_academic_os_engine()
    project = engine.projects.update_project(project_id, req.updates)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"success": True, "project": project.to_dict()}


@router.post("/project/{project_id}/link")
async def link_entity_to_project(project_id: str, req: LinkEntityRequest, user: dict = Depends(get_current_user)):
    engine = await get_academic_os_engine()
    ok = engine.projects.link_entity(project_id, req.entity_type, req.entity_id)
    return {"success": ok}


@router.delete("/project/{project_id}/link")
async def unlink_entity_from_project(project_id: str, req: LinkEntityRequest, user: dict = Depends(get_current_user)):
    engine = await get_academic_os_engine()
    ok = engine.projects.unlink_entity(project_id, req.entity_type, req.entity_id)
    return {"success": ok}


@router.get("/projects/my")
async def get_my_projects(user: dict = Depends(get_current_user)):
    engine   = await get_academic_os_engine()
    user_id  = str(user.get("_id", ""))
    projects = engine.projects.get_projects_by_cohort(user_id)
    return {"projects": [p.to_dict() for p in projects]}


# ── Search endpoints ──────────────────────────────────────────────────────────

@router.post("/search")
async def global_search(req: SearchRequest, user: dict = Depends(get_current_user)):
    cost    = get_credit_cost("aos_search", 2)
    user_id = str(user.get("_id", ""))
    await consume_credits(user_id, cost)
    engine  = await get_academic_os_engine()
    return engine.global_search(req.query, req.entity_types, user_id, req.limit)


@router.post("/search/index")
async def index_entity(req: IndexEntityRequest, user: dict = Depends(get_current_user)):
    user_id = str(user.get("_id", ""))
    engine  = await get_academic_os_engine()
    return engine.index_entity(req.entity_type, req.entity_id, req.title, req.content, req.tags, user_id)


# ── Timeline endpoints ────────────────────────────────────────────────────────

@router.post("/timeline/record")
async def record_activity(req: ActivityRequest, user: dict = Depends(get_current_user)):
    user_id = str(user.get("_id", ""))
    engine  = await get_academic_os_engine()
    return engine.record_activity(req.event_type, req.entity_type, req.entity_id,
                                  user_id, req.description, req.project_id)


@router.get("/timeline")
async def get_timeline(limit: int = 50, since: Optional[float] = None, user: dict = Depends(get_current_user)):
    user_id = str(user.get("_id", ""))
    engine  = await get_academic_os_engine()
    return {"events": engine.get_timeline(user_id, limit=limit, since=since)}


@router.get("/timeline/project/{project_id}")
async def get_project_timeline(project_id: str, limit: int = 50, user: dict = Depends(get_current_user)):
    engine = await get_academic_os_engine()
    events = engine.timeline.get_project_timeline(project_id, limit)
    return {"events": [e.to_dict() for e in events]}


# ── Notification endpoints ────────────────────────────────────────────────────

@router.get("/notifications")
async def get_notifications(unread_only: bool = False, limit: int = 50, user: dict = Depends(get_current_user)):
    user_id = str(user.get("_id", ""))
    engine  = await get_academic_os_engine()
    return {"notifications": engine.get_notifications(user_id, unread_only, limit)}


@router.get("/notifications/unread-count")
async def get_unread_count(user: dict = Depends(get_current_user)):
    user_id = str(user.get("_id", ""))
    engine  = await get_academic_os_engine()
    return {"unread_count": engine.notifications.get_unread_count(user_id)}


@router.post("/notifications/mark-read/{notification_id}")
async def mark_notification_read(notification_id: str, user: dict = Depends(get_current_user)):
    user_id = str(user.get("_id", ""))
    engine  = await get_academic_os_engine()
    ok = engine.notifications.mark_read(notification_id, user_id)
    return {"success": ok}


@router.post("/notifications/mark-all-read")
async def mark_all_read(user: dict = Depends(get_current_user)):
    user_id = str(user.get("_id", ""))
    engine  = await get_academic_os_engine()
    count = engine.notifications.mark_all_read(user_id)
    return {"marked_read": count}


@router.delete("/notifications/{notification_id}")
async def dismiss_notification(notification_id: str, user: dict = Depends(get_current_user)):
    user_id = str(user.get("_id", ""))
    engine  = await get_academic_os_engine()
    ok = engine.notifications.dismiss(notification_id, user_id)
    return {"success": ok}


# ── Dashboard endpoints ───────────────────────────────────────────────────────

@router.post("/dashboard")
async def get_dashboard(req: DashboardRequest, user: dict = Depends(get_current_user)):
    cost    = get_credit_cost("aos_dashboard", 1)
    user_id = str(user.get("_id", ""))
    await consume_credits(user_id, cost)
    engine  = await get_academic_os_engine()
    return engine.get_dashboard(req.user_role, req.metrics)


@router.get("/dashboard/roles")
async def get_dashboard_roles(user: dict = Depends(get_current_user)):
    engine = await get_academic_os_engine()
    return {"roles": engine.get_available_roles()}


# ── Automation endpoints ──────────────────────────────────────────────────────

@router.get("/automation/rules")
async def list_automation_rules(user: dict = Depends(get_current_user)):
    engine = await get_academic_os_engine()
    rules  = engine.automation.list_rules(enabled_only=False)
    return {"rules": [r.to_dict() for r in rules]}


@router.post("/automation/fire-event")
async def fire_automation_event(req: AutomationEventRequest, user: dict = Depends(get_current_user)):
    cost    = get_credit_cost("aos_automation", 3)
    user_id = str(user.get("_id", ""))
    await consume_credits(user_id, cost)
    engine  = await get_academic_os_engine()
    return engine.fire_automation_event(req.event_type, req.payload)


# ── Sync endpoints ────────────────────────────────────────────────────────────

@router.post("/sync/emit")
async def emit_sync_event(req: SyncEmitRequest, user: dict = Depends(get_current_user)):
    engine = await get_academic_os_engine()
    return engine.emit_sync(
        req.source_module, req.entity_type, req.entity_id,
        req.change_type, req.payload,
    )


@router.get("/sync/targets/{module}")
async def get_sync_targets(module: str, user: dict = Depends(get_current_user)):
    engine = await get_academic_os_engine()
    return {"module": module, "targets": engine.sync.get_targets(module)}


# ── Health endpoint ───────────────────────────────────────────────────────────

@router.get("/health")
async def get_health(user: dict = Depends(get_current_user)):
    engine = await get_academic_os_engine()
    return engine.get_health()


# ═══════════════════════════════════════════════════════════════════════════════
# Admin endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@admin_router.get("/summary")
async def admin_summary(user: dict = Depends(get_current_user)):
    engine = await get_academic_os_engine()
    return engine.admin_summary()


@admin_router.get("/telemetry")
async def admin_telemetry(user: dict = Depends(get_current_user)):
    engine = await get_academic_os_engine()
    return engine.get_telemetry()


@admin_router.get("/workflows")
async def admin_list_workflows(limit: int = 100, user: dict = Depends(get_current_user)):
    engine = await get_academic_os_engine()
    wfs    = engine.workflows.get_all_workflows(limit)
    return {"total": len(wfs), "workflows": [w.to_dict() for w in wfs]}


@admin_router.get("/workflows/active")
async def admin_active_workflows(user: dict = Depends(get_current_user)):
    engine = await get_academic_os_engine()
    wfs    = engine.workflows.get_active_workflows()
    return {"total": len(wfs), "workflows": [w.to_dict() for w in wfs]}


@admin_router.get("/projects")
async def admin_list_projects(limit: int = 100, user: dict = Depends(get_current_user)):
    engine   = await get_academic_os_engine()
    projects = engine.projects.get_all_projects(limit)
    return {"total": len(projects), "projects": [p.to_dict() for p in projects]}


@admin_router.get("/search/stats")
async def admin_search_stats(user: dict = Depends(get_current_user)):
    engine = await get_academic_os_engine()
    return engine.search.stats()


@admin_router.get("/timeline/recent")
async def admin_recent_activity(limit: int = 50, user: dict = Depends(get_current_user)):
    engine = await get_academic_os_engine()
    events = engine.timeline.get_recent_activity(limit)
    return {"events": [e.to_dict() for e in events]}


@admin_router.get("/notifications/stats")
async def admin_notification_stats(user: dict = Depends(get_current_user)):
    engine = await get_academic_os_engine()
    return engine.notifications.stats()


@admin_router.post("/notifications/broadcast")
async def admin_broadcast(req: BroadcastRequest, user: dict = Depends(get_current_user)):
    engine = await get_academic_os_engine()
    notifs = engine.notifications.broadcast(req.notification_type, req.cohorts, req.title, req.body)
    return {"sent": len(notifs), "notifications": [n.to_dict() for n in notifs]}


@admin_router.post("/automation/rules")
async def admin_create_rule(req: AutomationRuleRequest, user: dict = Depends(get_current_user)):
    engine = await get_academic_os_engine()
    rule   = engine.automation.create_rule(req.name, req.trigger_type, req.trigger_condition, req.actions)
    return {"success": True, "rule": rule.to_dict()}


@admin_router.post("/automation/install-defaults")
async def admin_install_defaults(user: dict = Depends(get_current_user)):
    engine = await get_academic_os_engine()
    rules  = engine.automation.install_default_rules()
    return {"installed": len(rules), "rules": [r.to_dict() for r in rules]}


@admin_router.put("/automation/rules/{rule_id}/toggle")
async def admin_toggle_rule(rule_id: str, enabled: bool, user: dict = Depends(get_current_user)):
    engine = await get_academic_os_engine()
    ok     = engine.automation.toggle_rule(rule_id, enabled)
    return {"success": ok}


@admin_router.delete("/automation/rules/{rule_id}")
async def admin_delete_rule(rule_id: str, user: dict = Depends(get_current_user)):
    engine = await get_academic_os_engine()
    ok     = engine.automation.delete_rule(rule_id)
    return {"success": ok}


@admin_router.get("/sync/log")
async def admin_sync_log(limit: int = 50, user: dict = Depends(get_current_user)):
    engine = await get_academic_os_engine()
    events = engine.sync.get_log(limit=limit)
    return {"events": [e.to_dict() for e in events]}


@admin_router.post("/sync/process-queue")
async def admin_process_sync_queue(max_batch: int = 20, user: dict = Depends(get_current_user)):
    engine = await get_academic_os_engine()
    return {"processed": engine.process_sync_queue(max_batch)}


@admin_router.post("/reset")
async def admin_reset(user: dict = Depends(get_current_user)):
    from services.academic_os import reset_academic_os_engine
    from services.academic_os.telemetry import reset_aos_telemetry
    await reset_academic_os_engine()
    reset_aos_telemetry()
    return {"reset": True}
