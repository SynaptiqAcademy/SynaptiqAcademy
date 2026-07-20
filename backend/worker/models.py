"""
Job model, WorkerInfo, Schedule dataclasses and job-type constants.

Job is the universal unit of work for the Enterprise Worker Platform.
Every asynchronous operation is represented as a Job with:
  - job_type → registered handler
  - payload  → all data needed for execution
  - Full state machine (pending → queued → running → completed/failed)
  - Retry, checkpoint, and observability fields built-in
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


# ── Status & Priority ─────────────────────────────────────────────────────────

class JobStatus(str, Enum):
    PENDING   = "pending"
    QUEUED    = "queued"
    RUNNING   = "running"
    WAITING   = "waiting"    # waiting for dependency
    RETRYING  = "retrying"
    PAUSED    = "paused"
    COMPLETED = "completed"
    FAILED    = "failed"
    CANCELLED = "cancelled"
    ARCHIVED  = "archived"


class Priority(int, Enum):
    CRITICAL   = 1
    HIGH       = 2
    NORMAL     = 3
    LOW        = 4
    BACKGROUND = 5


# ── Job Type Constants ────────────────────────────────────────────────────────

JOB_AI_EXECUTION          = "ai.execution"
JOB_MISSION_STEP          = "mission.step"
JOB_KG_UPDATE             = "kg.update"
JOB_TWIN_UPDATE           = "twin.update"
JOB_RECOMMENDATION_GEN    = "recommendation.generate"
JOB_GRANT_DISCOVERY       = "grant.discovery"
JOB_PUBLICATION_MONITOR   = "publication.monitor"
JOB_CITATION_MONITOR      = "citation.monitor"
JOB_ORCID_SYNC            = "orcid.sync"
JOB_ORCID_WEEKLY_SYNC     = "orcid.weekly_sync"
JOB_CITATION_WEEKLY_SYNC  = "citation.weekly_sync"
JOB_INSTITUTION_ANALYTICS = "institution.analytics"
JOB_TEACHING_ANALYTICS    = "teaching.analytics"
JOB_MARKETPLACE_PROCESS   = "marketplace.process"
JOB_NOTIFICATION_DELIVER  = "notification.deliver"
JOB_DATA_IMPORT           = "data.import"
JOB_GRAPH_REBUILD         = "graph.rebuild"
JOB_REPORT_GENERATE       = "report.generate"
JOB_INTEGRITY_ANALYSIS    = "integrity.analysis"
JOB_MEMORY_ENRICH         = "memory.enrich"
JOB_EMAIL_SEND                  = "email.send"
JOB_EMAIL_GETTING_STARTED_CHECK = "email.getting_started_check"

ALL_JOB_TYPES: list[str] = [
    JOB_AI_EXECUTION, JOB_MISSION_STEP, JOB_KG_UPDATE, JOB_TWIN_UPDATE,
    JOB_RECOMMENDATION_GEN, JOB_GRANT_DISCOVERY, JOB_PUBLICATION_MONITOR,
    JOB_CITATION_MONITOR, JOB_ORCID_SYNC, JOB_ORCID_WEEKLY_SYNC,
    JOB_CITATION_WEEKLY_SYNC, JOB_INSTITUTION_ANALYTICS, JOB_TEACHING_ANALYTICS,
    JOB_MARKETPLACE_PROCESS, JOB_NOTIFICATION_DELIVER, JOB_DATA_IMPORT,
    JOB_GRAPH_REBUILD, JOB_REPORT_GENERATE, JOB_INTEGRITY_ANALYSIS, JOB_MEMORY_ENRICH,
    JOB_EMAIL_SEND, JOB_EMAIL_GETTING_STARTED_CHECK,
]

# Queue name constants
QUEUE_DEFAULT   = "default"
QUEUE_AI        = "ai"
QUEUE_GRAPH     = "graph"
QUEUE_INGESTION = "ingestion"
QUEUE_REPORTS   = "reports"

ALL_QUEUES = [QUEUE_DEFAULT, QUEUE_AI, QUEUE_GRAPH, QUEUE_INGESTION, QUEUE_REPORTS]

# Map job types to their preferred queues
JOB_QUEUE_MAP: dict[str, str] = {
    JOB_AI_EXECUTION:          QUEUE_AI,
    JOB_MISSION_STEP:          QUEUE_AI,
    JOB_KG_UPDATE:             QUEUE_GRAPH,
    JOB_GRAPH_REBUILD:         QUEUE_GRAPH,
    JOB_TWIN_UPDATE:           QUEUE_DEFAULT,
    JOB_RECOMMENDATION_GEN:    QUEUE_DEFAULT,
    JOB_GRANT_DISCOVERY:       QUEUE_INGESTION,
    JOB_PUBLICATION_MONITOR:   QUEUE_INGESTION,
    JOB_CITATION_MONITOR:      QUEUE_INGESTION,
    JOB_ORCID_SYNC:            QUEUE_INGESTION,
    JOB_ORCID_WEEKLY_SYNC:     QUEUE_INGESTION,
    JOB_CITATION_WEEKLY_SYNC:  QUEUE_INGESTION,
    JOB_INSTITUTION_ANALYTICS: QUEUE_DEFAULT,
    JOB_TEACHING_ANALYTICS:    QUEUE_DEFAULT,
    JOB_MARKETPLACE_PROCESS:   QUEUE_DEFAULT,
    JOB_NOTIFICATION_DELIVER:  QUEUE_DEFAULT,
    JOB_DATA_IMPORT:           QUEUE_INGESTION,
    JOB_REPORT_GENERATE:       QUEUE_REPORTS,
    JOB_INTEGRITY_ANALYSIS:    QUEUE_DEFAULT,
    JOB_MEMORY_ENRICH:         QUEUE_AI,
    JOB_EMAIL_SEND:                  QUEUE_DEFAULT,
    JOB_EMAIL_GETTING_STARTED_CHECK: QUEUE_DEFAULT,
}


# ── Job Dataclass ─────────────────────────────────────────────────────────────

@dataclass
class Job:
    """Universal unit of work for the Worker Platform."""

    job_type:  str
    payload:   dict

    # Identity
    job_id:         str       = field(default_factory=lambda: str(uuid.uuid4()))
    status:         JobStatus = JobStatus.PENDING
    priority:       Priority  = Priority.NORMAL
    queue_name:     str       = QUEUE_DEFAULT

    # User / tenant context
    user_id:        str | None = None
    institution:    str | None = None
    workspace_id:   str | None = None
    correlation_id: str | None = None

    # Scheduling
    scheduled_at:  datetime       = field(default_factory=datetime.utcnow)
    queued_at:     datetime | None = None
    started_at:    datetime | None = None
    completed_at:  datetime | None = None

    # Worker assignment
    worker_id: str | None = None

    # Retry state
    attempt:       int          = 0
    max_attempts:  int          = 3
    last_error:    str | None   = None
    next_retry_at: datetime | None = None

    # Dependency graph
    depends_on: list[str] = field(default_factory=list)  # job_ids that must be COMPLETED first

    # Mid-execution checkpoint (persisted to DB after each meaningful step)
    checkpoint: dict = field(default_factory=dict)

    # Observability / cost tracking
    duration_ms: float | None = None
    cost_usd:    float | None = None
    tokens_used: int   | None = None
    provider:    str   | None = None
    model:       str   | None = None

    # Metadata
    created_by: str       | None = None
    tags:       list[str]        = field(default_factory=list)

    def to_dict(self) -> dict:
        def _iso(v: datetime | None) -> str | None:
            return v.isoformat() if v else None
        return {
            "job_id":         self.job_id,
            "job_type":       self.job_type,
            "status":         self.status.value,
            "priority":       self.priority.value,
            "queue_name":     self.queue_name,
            "payload":        self.payload,
            "user_id":        self.user_id,
            "institution":    self.institution,
            "workspace_id":   self.workspace_id,
            "correlation_id": self.correlation_id,
            "scheduled_at":   _iso(self.scheduled_at),
            "queued_at":      _iso(self.queued_at),
            "started_at":     _iso(self.started_at),
            "completed_at":   _iso(self.completed_at),
            "worker_id":      self.worker_id,
            "attempt":        self.attempt,
            "max_attempts":   self.max_attempts,
            "last_error":     self.last_error,
            "next_retry_at":  _iso(self.next_retry_at),
            "depends_on":     self.depends_on,
            "checkpoint":     self.checkpoint,
            "duration_ms":    self.duration_ms,
            "cost_usd":       self.cost_usd,
            "tokens_used":    self.tokens_used,
            "provider":       self.provider,
            "model":          self.model,
            "created_by":     self.created_by,
            "tags":           self.tags,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Job":
        def _dt(v: str | None) -> datetime | None:
            return datetime.fromisoformat(v) if v else None
        return cls(
            job_id=d["job_id"],
            job_type=d["job_type"],
            status=JobStatus(d.get("status", JobStatus.PENDING.value)),
            priority=Priority(d.get("priority", Priority.NORMAL.value)),
            queue_name=d.get("queue_name", QUEUE_DEFAULT),
            payload=d.get("payload", {}),
            user_id=d.get("user_id"),
            institution=d.get("institution"),
            workspace_id=d.get("workspace_id"),
            correlation_id=d.get("correlation_id"),
            scheduled_at=_dt(d.get("scheduled_at")),
            queued_at=_dt(d.get("queued_at")),
            started_at=_dt(d.get("started_at")),
            completed_at=_dt(d.get("completed_at")),
            worker_id=d.get("worker_id"),
            attempt=d.get("attempt", 0),
            max_attempts=d.get("max_attempts", 3),
            last_error=d.get("last_error"),
            next_retry_at=_dt(d.get("next_retry_at")),
            depends_on=d.get("depends_on", []),
            checkpoint=d.get("checkpoint", {}),
            duration_ms=d.get("duration_ms"),
            cost_usd=d.get("cost_usd"),
            tokens_used=d.get("tokens_used"),
            provider=d.get("provider"),
            model=d.get("model"),
            created_by=d.get("created_by"),
            tags=d.get("tags", []),
        )


# ── WorkerInfo Dataclass ──────────────────────────────────────────────────────

@dataclass
class WorkerInfo:
    """Registered worker metadata — capabilities, health, and live state."""

    worker_id:    str
    queue_names:  list[str]
    job_types:    list[str]   # capabilities: which job types this worker handles
    concurrency:  int         # max concurrent jobs

    status:       str       = "healthy"  # healthy | unhealthy | draining
    version:      str       = "1.0"
    heartbeat:    datetime  = field(default_factory=datetime.utcnow)
    load:         float     = 0.0        # 0.0–1.0
    current_jobs: list[str] = field(default_factory=list)  # active job_ids
    started_at:   datetime  = field(default_factory=datetime.utcnow)
    hostname:     str       = ""
    pid:          int       = 0

    def to_dict(self) -> dict:
        return {
            "worker_id":    self.worker_id,
            "queue_names":  self.queue_names,
            "job_types":    self.job_types,
            "concurrency":  self.concurrency,
            "status":       self.status,
            "version":      self.version,
            "heartbeat":    self.heartbeat.isoformat(),
            "load":         self.load,
            "current_jobs": self.current_jobs,
            "started_at":   self.started_at.isoformat(),
            "hostname":     self.hostname,
            "pid":          self.pid,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "WorkerInfo":
        def _dt(v: str | None) -> datetime:
            return datetime.fromisoformat(v) if v else datetime.utcnow()
        return cls(
            worker_id=d["worker_id"],
            queue_names=d.get("queue_names", [QUEUE_DEFAULT]),
            job_types=d.get("job_types", []),
            concurrency=d.get("concurrency", 4),
            status=d.get("status", "healthy"),
            version=d.get("version", "1.0"),
            heartbeat=_dt(d.get("heartbeat")),
            load=d.get("load", 0.0),
            current_jobs=d.get("current_jobs", []),
            started_at=_dt(d.get("started_at")),
            hostname=d.get("hostname", ""),
            pid=d.get("pid", 0),
        )


# ── Schedule Dataclass ────────────────────────────────────────────────────────

@dataclass
class Schedule:
    """Persisted schedule definition — drives the Scheduler's tick loop."""

    schedule_id: str
    job_type:    str
    payload:     dict

    mode:        str          # once | recurring | cron | event_triggered

    cron_expr:   str | None  = None   # cron expression for 'cron' mode
    run_at:      datetime | None = None  # absolute time for 'once' mode
    interval_s:  int | None  = None   # seconds for 'recurring' mode
    event_type:  str | None  = None   # event type for 'event_triggered' mode
    timezone:    str          = "UTC"

    enabled:     bool         = True
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None
    run_count:   int          = 0

    priority:    Priority     = Priority.NORMAL
    queue_name:  str          = QUEUE_DEFAULT
    max_attempts: int         = 3
    user_id:     str | None  = None
    tags:        list[str]   = field(default_factory=list)

    def to_dict(self) -> dict:
        def _iso(v: datetime | None) -> str | None:
            return v.isoformat() if v else None
        return {
            "schedule_id": self.schedule_id,
            "job_type":    self.job_type,
            "payload":     self.payload,
            "mode":        self.mode,
            "cron_expr":   self.cron_expr,
            "run_at":      _iso(self.run_at),
            "interval_s":  self.interval_s,
            "event_type":  self.event_type,
            "timezone":    self.timezone,
            "enabled":     self.enabled,
            "last_run_at": _iso(self.last_run_at),
            "next_run_at": _iso(self.next_run_at),
            "run_count":   self.run_count,
            "priority":    self.priority.value,
            "queue_name":  self.queue_name,
            "max_attempts": self.max_attempts,
            "user_id":     self.user_id,
            "tags":        self.tags,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Schedule":
        def _dt(v: str | None) -> datetime | None:
            return datetime.fromisoformat(v) if v else None
        return cls(
            schedule_id=d["schedule_id"],
            job_type=d["job_type"],
            payload=d.get("payload", {}),
            mode=d["mode"],
            cron_expr=d.get("cron_expr"),
            run_at=_dt(d.get("run_at")),
            interval_s=d.get("interval_s"),
            event_type=d.get("event_type"),
            timezone=d.get("timezone", "UTC"),
            enabled=d.get("enabled", True),
            last_run_at=_dt(d.get("last_run_at")),
            next_run_at=_dt(d.get("next_run_at")),
            run_count=d.get("run_count", 0),
            priority=Priority(d.get("priority", Priority.NORMAL.value)),
            queue_name=d.get("queue_name", QUEUE_DEFAULT),
            max_attempts=d.get("max_attempts", 3),
            user_id=d.get("user_id"),
            tags=d.get("tags", []),
        )
