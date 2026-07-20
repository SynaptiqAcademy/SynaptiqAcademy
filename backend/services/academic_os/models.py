"""Academic Operating System — Data models (Phase XXI)."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum


class WorkflowType(Enum):
    RESEARCH_PIPELINE      = "research_pipeline"
    MANUSCRIPT_PIPELINE    = "manuscript_pipeline"
    GRANT_PIPELINE         = "grant_pipeline"
    CAREER_PIPELINE        = "career_pipeline"
    COLLABORATION_PIPELINE = "collaboration_pipeline"
    CUSTOM                 = "custom"


class WorkflowStatus(Enum):
    DRAFT     = "draft"
    RUNNING   = "running"
    PAUSED    = "paused"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"


class StepStatus(Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    SKIPPED   = "skipped"
    FAILED    = "failed"


class EntityType(Enum):
    USER         = "user"
    PROJECT      = "project"
    DOCUMENT     = "document"
    PUBLICATION  = "publication"
    GRANT        = "grant"
    JOURNAL      = "journal"
    CONFERENCE   = "conference"
    DATASET      = "dataset"
    WORKSPACE    = "workspace"
    NOTE         = "note"
    CONVERSATION = "conversation"
    TASK         = "task"
    REPOSITORY   = "repository"
    MESSAGE      = "message"
    INSTITUTION  = "institution"


class ActivityEventType(Enum):
    UPLOAD         = "upload"
    PUBLICATION    = "publication"
    REVIEW         = "review"
    AI_ACTIVITY    = "ai_activity"
    COLLABORATION  = "collaboration"
    CITATION       = "citation"
    GRANT          = "grant"
    CONFERENCE     = "conference"
    DEADLINE       = "deadline"
    TEACHING       = "teaching"
    MILESTONE      = "milestone"
    WORKFLOW_STEP  = "workflow_step"
    PROJECT_UPDATE = "project_update"
    SYNC_EVENT     = "sync_event"


class NotificationPriority(Enum):
    CRITICAL = "critical"
    HIGH     = "high"
    NORMAL   = "normal"
    LOW      = "low"


class NotificationType(Enum):
    GRANT_DEADLINE          = "grant_deadline"
    CONFERENCE_DEADLINE     = "conference_deadline"
    JOURNAL_RECOMMENDATION  = "journal_recommendation"
    REVIEW_COMPLETE         = "review_complete"
    AI_INSIGHT              = "ai_insight"
    COLLABORATION_REQUEST   = "collaboration_request"
    PUBLICATION_ALERT       = "publication_alert"
    CITATION_ALERT          = "citation_alert"
    CAREER_ALERT            = "career_alert"
    INSTITUTION_ALERT       = "institution_alert"
    WORKFLOW_COMPLETE       = "workflow_complete"
    AUTOMATION_TRIGGERED    = "automation_triggered"
    SYSTEM_ALERT            = "system_alert"


class UserRole(Enum):
    STUDENT        = "student"
    MASTER_STUDENT = "master_student"
    PHD_CANDIDATE  = "phd_candidate"
    RESEARCHER     = "researcher"
    PROFESSOR      = "professor"
    INSTITUTION    = "institution"
    ADMINISTRATOR  = "administrator"


class TriggerType(Enum):
    MANUSCRIPT_QUALITY       = "manuscript_quality"
    WORKFLOW_STEP_COMPLETE   = "workflow_step_complete"
    DEADLINE_APPROACHING     = "deadline_approaching"
    CITATION_THRESHOLD       = "citation_threshold"
    COLLABORATION_ACCEPTED   = "collaboration_accepted"
    GRANT_STATUS_CHANGE      = "grant_status_change"
    ENTITY_CREATED           = "entity_created"
    PROJECT_UPDATED          = "project_updated"


class SyncChangeType(Enum):
    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    LINKED  = "linked"


# ── Dataclasses ────────────────────────────────────────────────────────────────

@dataclass
class WorkflowStep:
    step_id:      str   = field(default_factory=lambda: str(uuid.uuid4()))
    name:         str   = ""
    engine_type:  str   = ""
    description:  str   = ""
    status:       str   = StepStatus.PENDING.value
    order:        int   = 0
    input_schema: dict  = field(default_factory=dict)
    output_data:  dict  = field(default_factory=dict)
    started_at:   float = 0.0
    completed_at: float = 0.0
    error:        str   = ""
    skippable:    bool  = False

    def to_dict(self) -> dict:
        return {
            "step_id":      self.step_id,
            "name":         self.name,
            "engine_type":  self.engine_type,
            "description":  self.description,
            "status":       self.status,
            "order":        self.order,
            "output_data":  self.output_data,
            "started_at":   self.started_at,
            "completed_at": self.completed_at,
            "error":        self.error,
            "skippable":    self.skippable,
        }


@dataclass
class WorkflowDefinition:
    workflow_id:         str   = field(default_factory=lambda: str(uuid.uuid4()))
    workflow_type:       str   = WorkflowType.CUSTOM.value
    name:                str   = ""
    description:         str   = ""
    status:              str   = WorkflowStatus.DRAFT.value
    steps:               list  = field(default_factory=list)
    current_step_index:  int   = 0
    owner_cohort:        str   = "general"
    project_id:          str   = ""
    created_at:          float = field(default_factory=time.time)
    updated_at:          float = field(default_factory=time.time)
    completed_at:        float = 0.0
    context:             dict  = field(default_factory=dict)
    progress_pct:        float = 0.0

    def current_step(self) -> WorkflowStep | None:
        if self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    def _update_progress(self) -> None:
        if not self.steps:
            self.progress_pct = 0.0
            return
        done = sum(1 for s in self.steps if s.status == StepStatus.COMPLETED.value)
        self.progress_pct = round(done / len(self.steps), 4)

    def to_dict(self) -> dict:
        self._update_progress()
        return {
            "workflow_id":        self.workflow_id,
            "workflow_type":      self.workflow_type,
            "name":               self.name,
            "description":        self.description,
            "status":             self.status,
            "steps":              [s.to_dict() for s in self.steps],
            "current_step_index": self.current_step_index,
            "owner_cohort":       self.owner_cohort,
            "project_id":         self.project_id,
            "created_at":         self.created_at,
            "updated_at":         self.updated_at,
            "completed_at":       self.completed_at,
            "progress_pct":       self.progress_pct,
            "context":            self.context,
        }


@dataclass
class ResearchProject:
    project_id:          str   = field(default_factory=lambda: str(uuid.uuid4()))
    name:                str   = ""
    description:         str   = ""
    status:              str   = "active"
    owner_cohort:        str   = "general"
    team_cohorts:        list  = field(default_factory=list)
    workspace_id:        str   = ""
    document_ids:        list  = field(default_factory=list)
    grant_ids:           list  = field(default_factory=list)
    publication_ids:     list  = field(default_factory=list)
    journal_targets:     list  = field(default_factory=list)
    conference_targets:  list  = field(default_factory=list)
    workflow_id:         str   = ""
    tasks:               list  = field(default_factory=list)
    tags:                list  = field(default_factory=list)
    created_at:          float = field(default_factory=time.time)
    updated_at:          float = field(default_factory=time.time)
    metadata:            dict  = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "project_id":         self.project_id,
            "name":               self.name,
            "description":        self.description,
            "status":             self.status,
            "owner_cohort":       self.owner_cohort,
            "team_cohorts":       self.team_cohorts,
            "workspace_id":       self.workspace_id,
            "document_ids":       self.document_ids,
            "grant_ids":          self.grant_ids,
            "publication_ids":    self.publication_ids,
            "journal_targets":    self.journal_targets,
            "conference_targets": self.conference_targets,
            "workflow_id":        self.workflow_id,
            "tasks":              self.tasks,
            "tags":               self.tags,
            "created_at":         self.created_at,
            "updated_at":         self.updated_at,
            "metadata":           self.metadata,
        }


@dataclass
class SearchIndex:
    entity_type:  str   = ""
    entity_id:    str   = ""
    title:        str   = ""
    content:      str   = ""
    tags:         list  = field(default_factory=list)
    owner_cohort: str   = "general"
    indexed_at:   float = field(default_factory=time.time)
    metadata:     dict  = field(default_factory=dict)

    def searchable_text(self) -> str:
        return f"{self.title} {self.content} {' '.join(self.tags)}".lower()


@dataclass
class SearchResult:
    result_id:      str   = field(default_factory=lambda: str(uuid.uuid4()))
    entity_type:    str   = ""
    entity_id:      str   = ""
    title:          str   = ""
    excerpt:        str   = ""
    score:          float = 0.0
    matched_fields: list  = field(default_factory=list)
    metadata:       dict  = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "result_id":      self.result_id,
            "entity_type":    self.entity_type,
            "entity_id":      self.entity_id,
            "title":          self.title,
            "excerpt":        self.excerpt,
            "score":          round(self.score, 4),
            "matched_fields": self.matched_fields,
            "metadata":       self.metadata,
        }


@dataclass
class ActivityEvent:
    event_id:    str   = field(default_factory=lambda: str(uuid.uuid4()))
    event_type:  str   = ""
    entity_type: str   = ""
    entity_id:   str   = ""
    user_cohort: str   = "general"
    description: str   = ""
    timestamp:   float = field(default_factory=time.time)
    project_id:  str   = ""
    metadata:    dict  = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "event_id":    self.event_id,
            "event_type":  self.event_type,
            "entity_type": self.entity_type,
            "entity_id":   self.entity_id,
            "user_cohort": self.user_cohort,
            "description": self.description,
            "timestamp":   self.timestamp,
            "project_id":  self.project_id,
        }


@dataclass
class Notification:
    notification_id:   str   = field(default_factory=lambda: str(uuid.uuid4()))
    notification_type: str   = ""
    priority:          str   = NotificationPriority.NORMAL.value
    title:             str   = ""
    body:              str   = ""
    action_url:        str   = ""
    user_cohort:       str   = "general"
    read:              bool  = False
    created_at:        float = field(default_factory=time.time)
    expires_at:        float = 0.0
    metadata:          dict  = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "notification_id":   self.notification_id,
            "notification_type": self.notification_type,
            "priority":          self.priority,
            "title":             self.title,
            "body":              self.body,
            "action_url":        self.action_url,
            "user_cohort":       self.user_cohort,
            "read":              self.read,
            "created_at":        self.created_at,
            "expires_at":        self.expires_at,
        }


@dataclass
class DashboardWidget:
    widget_id:   str  = field(default_factory=lambda: str(uuid.uuid4()))
    widget_type: str  = ""
    title:       str  = ""
    data_source: str  = ""
    position:    dict = field(default_factory=lambda: {"x": 0, "y": 0, "w": 4, "h": 2})
    config:      dict = field(default_factory=dict)
    visible:     bool = True

    def to_dict(self) -> dict:
        return {
            "widget_id":   self.widget_id,
            "widget_type": self.widget_type,
            "title":       self.title,
            "data_source": self.data_source,
            "position":    self.position,
            "config":      self.config,
            "visible":     self.visible,
        }


@dataclass
class DashboardConfig:
    config_id:       str   = field(default_factory=lambda: str(uuid.uuid4()))
    user_role:       str   = ""
    widgets:         list  = field(default_factory=list)
    personalization: dict  = field(default_factory=dict)
    generated_at:    float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "config_id":       self.config_id,
            "user_role":       self.user_role,
            "widgets":         [w.to_dict() for w in self.widgets],
            "personalization": self.personalization,
            "generated_at":    self.generated_at,
        }


@dataclass
class AutomationRule:
    rule_id:           str   = field(default_factory=lambda: str(uuid.uuid4()))
    name:              str   = ""
    trigger_type:      str   = ""
    trigger_condition: dict  = field(default_factory=dict)
    actions:           list  = field(default_factory=list)
    enabled:           bool  = True
    created_at:        float = field(default_factory=time.time)
    last_triggered:    float = 0.0
    trigger_count:     int   = 0

    def to_dict(self) -> dict:
        return {
            "rule_id":           self.rule_id,
            "name":              self.name,
            "trigger_type":      self.trigger_type,
            "trigger_condition": self.trigger_condition,
            "actions":           self.actions,
            "enabled":           self.enabled,
            "created_at":        self.created_at,
            "last_triggered":    self.last_triggered,
            "trigger_count":     self.trigger_count,
        }


@dataclass
class SyncEvent:
    sync_id:        str   = field(default_factory=lambda: str(uuid.uuid4()))
    source_module:  str   = ""
    target_modules: list  = field(default_factory=list)
    entity_type:    str   = ""
    entity_id:      str   = ""
    change_type:    str   = ""
    payload:        dict  = field(default_factory=dict)
    status:         str   = "pending"
    created_at:     float = field(default_factory=time.time)
    processed_at:   float = 0.0
    results:        dict  = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "sync_id":        self.sync_id,
            "source_module":  self.source_module,
            "target_modules": self.target_modules,
            "entity_type":    self.entity_type,
            "entity_id":      self.entity_id,
            "change_type":    self.change_type,
            "status":         self.status,
            "created_at":     self.created_at,
            "processed_at":   self.processed_at,
            "results":        self.results,
        }


@dataclass
class OSHealthReport:
    report_id:               str   = field(default_factory=lambda: str(uuid.uuid4()))
    overall_health:          float = 0.0
    active_workflows:        int   = 0
    active_projects:         int   = 0
    notifications_pending:   int   = 0
    sync_queue_depth:        int   = 0
    automation_rules_active: int   = 0
    search_index_size:       int   = 0
    timeline_events_24h:     int   = 0
    generated_at:            float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "report_id":               self.report_id,
            "overall_health":          round(self.overall_health, 4),
            "active_workflows":        self.active_workflows,
            "active_projects":         self.active_projects,
            "notifications_pending":   self.notifications_pending,
            "sync_queue_depth":        self.sync_queue_depth,
            "automation_rules_active": self.automation_rules_active,
            "search_index_size":       self.search_index_size,
            "timeline_events_24h":     self.timeline_events_24h,
            "generated_at":            self.generated_at,
        }
