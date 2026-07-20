"""
Domain Event Models — strongly-typed events for every bounded context.

Every event shares the same base structure (DomainEvent) with full tracing
fields. Each bounded context defines its own event classes so consumers know
exactly what to expect in payload without inspecting raw dicts.

Usage:
    event = PublicationCreated(
        aggregate_id=pub_id,
        user_id=ctx.user_id,
        payload={"title": title, "status": "draft"},
    )
    await bus.publish(event)
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any


# ── Base ──────────────────────────────────────────────────────────────────────

@dataclass
class DomainEvent:
    """
    Base class for every domain event in Synaptiq.

    All fields except payload/metadata are filled automatically.
    Subclasses set EVENT_TYPE and AGGREGATE_TYPE as class attributes and
    call super().__init__() with keyword args.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    event_id:       str      = field(default_factory=lambda: str(uuid.uuid4()))
    event_type:     str      = ""
    version:        int      = 1

    # ── Aggregate ─────────────────────────────────────────────────────────────
    aggregate_id:   str      = ""
    aggregate_type: str      = ""

    # ── Traceability ─────────────────────────────────────────────────────────
    timestamp:      datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    user_id:        str      = ""
    institution:    str      = ""
    workspace_id:   str      = ""
    mission_id:     str      = ""
    correlation_id: str      = field(default_factory=lambda: str(uuid.uuid4()))
    request_id:     str      = ""
    source:         str      = "synaptiq"

    # ── Content ───────────────────────────────────────────────────────────────
    payload:        dict     = field(default_factory=dict)
    metadata:       dict     = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["timestamp"] = self.timestamp.isoformat()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "DomainEvent":
        d = dict(d)
        d.pop("_id", None)
        if "timestamp" in d and isinstance(d["timestamp"], str):
            d["timestamp"] = datetime.fromisoformat(d["timestamp"])
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def with_correlation(self, correlation_id: str) -> "DomainEvent":
        self.correlation_id = correlation_id
        return self

    def with_request(self, request_id: str) -> "DomainEvent":
        self.request_id = request_id
        return self


# ── Event type constants ───────────────────────────────────────────────────────

# Publications
PUBLICATION_CREATED     = "publication.created"
PUBLICATION_UPDATED     = "publication.updated"
PUBLICATION_DELETED     = "publication.deleted"
PUBLICATION_SUBMITTED   = "publication.submitted"
PUBLICATION_PUBLISHED   = "publication.published"

# Citations
CITATION_ADDED          = "citation.added"
CITATION_REMOVED        = "citation.removed"

# Projects / Workspaces
PROJECT_CREATED         = "project.created"
PROJECT_ARCHIVED        = "project.archived"
WORKSPACE_CREATED       = "workspace.created"
WORKSPACE_SHARED        = "workspace.shared"

# Missions / Agents
MISSION_CREATED         = "mission.created"
MISSION_QUEUED          = "mission.queued"
MISSION_STARTED         = "mission.started"
MISSION_PAUSED          = "mission.paused"
MISSION_RESUMED         = "mission.resumed"
MISSION_COMPLETED       = "mission.completed"
MISSION_FAILED          = "mission.failed"
MISSION_CANCELLED       = "mission.cancelled"
MISSION_APPROVAL_NEEDED = "mission.approval_needed"
AGENT_FINISHED          = "agent.finished"

# Step lifecycle
STEP_STARTED            = "step.started"
STEP_COMPLETED          = "step.completed"
STEP_FAILED             = "step.failed"

# Worker / heartbeat
HEARTBEAT_EXPIRED       = "heartbeat.expired"
RETRY_SCHEDULED         = "retry.scheduled"

# Recommendations
RECOMMENDATION_GENERATED = "recommendation.generated"

# Twin
TWIN_UPDATED            = "twin.updated"
TWIN_GOAL_REACHED       = "twin.goal_reached"

# Knowledge Graph
KNOWLEDGE_GRAPH_UPDATED = "knowledge_graph.updated"
KG_NODE_ADDED           = "knowledge_graph.node_added"
KG_EDGE_ADDED           = "knowledge_graph.edge_added"

# Identity / ORCID
ORCID_SYNCED            = "identity.orcid_synced"
USER_VERIFIED           = "identity.user_verified"
PROFILE_COMPLETED       = "identity.profile_completed"

# Grants
GRANT_DISCOVERED        = "grant.discovered"
GRANT_SUBMITTED         = "grant.submitted"
GRANT_AWARDED           = "grant.awarded"

# Institution
INSTITUTION_UPDATED     = "institution.updated"
INSTITUTION_MEMBER_ADDED    = "institution.member_added"
INSTITUTION_MEMBER_REMOVED  = "institution.member_removed"

# Teaching
TEACHING_ACTIVITY_CREATED = "teaching.activity_created"

# Marketplace
MARKETPLACE_ORDER_CREATED = "marketplace.order_created"

# Research
RESEARCH_GOAL_REACHED   = "research.goal_reached"
COLLABORATION_STARTED   = "collaboration.started"

# System
SYSTEM_STARTUP          = "system.startup"
SYSTEM_SHUTDOWN         = "system.shutdown"


# ── Typed event classes ────────────────────────────────────────────────────────

# --- Publications ---

@dataclass
class PublicationCreated(DomainEvent):
    event_type:     str = PUBLICATION_CREATED
    aggregate_type: str = "publication"


@dataclass
class PublicationUpdated(DomainEvent):
    event_type:     str = PUBLICATION_UPDATED
    aggregate_type: str = "publication"


@dataclass
class PublicationDeleted(DomainEvent):
    event_type:     str = PUBLICATION_DELETED
    aggregate_type: str = "publication"


@dataclass
class PublicationSubmitted(DomainEvent):
    event_type:     str = PUBLICATION_SUBMITTED
    aggregate_type: str = "publication"


@dataclass
class PublicationPublished(DomainEvent):
    event_type:     str = PUBLICATION_PUBLISHED
    aggregate_type: str = "publication"


# --- Citations ---

@dataclass
class CitationAdded(DomainEvent):
    event_type:     str = CITATION_ADDED
    aggregate_type: str = "citation"


@dataclass
class CitationRemoved(DomainEvent):
    event_type:     str = CITATION_REMOVED
    aggregate_type: str = "citation"


# --- Projects / Workspaces ---

@dataclass
class ProjectCreated(DomainEvent):
    event_type:     str = PROJECT_CREATED
    aggregate_type: str = "project"


@dataclass
class ProjectArchived(DomainEvent):
    event_type:     str = PROJECT_ARCHIVED
    aggregate_type: str = "project"


@dataclass
class WorkspaceCreated(DomainEvent):
    event_type:     str = WORKSPACE_CREATED
    aggregate_type: str = "workspace"


@dataclass
class WorkspaceShared(DomainEvent):
    event_type:     str = WORKSPACE_SHARED
    aggregate_type: str = "workspace"


# --- Missions ---

@dataclass
class MissionCreated(DomainEvent):
    event_type:     str = MISSION_CREATED
    aggregate_type: str = "mission"


@dataclass
class MissionQueued(DomainEvent):
    event_type:     str = MISSION_QUEUED
    aggregate_type: str = "mission"


@dataclass
class MissionStarted(DomainEvent):
    event_type:     str = MISSION_STARTED
    aggregate_type: str = "mission"


@dataclass
class MissionPaused(DomainEvent):
    event_type:     str = MISSION_PAUSED
    aggregate_type: str = "mission"


@dataclass
class MissionResumed(DomainEvent):
    event_type:     str = MISSION_RESUMED
    aggregate_type: str = "mission"


@dataclass
class MissionCompleted(DomainEvent):
    event_type:     str = MISSION_COMPLETED
    aggregate_type: str = "mission"


@dataclass
class MissionFailed(DomainEvent):
    event_type:     str = MISSION_FAILED
    aggregate_type: str = "mission"


@dataclass
class MissionCancelled(DomainEvent):
    event_type:     str = MISSION_CANCELLED
    aggregate_type: str = "mission"


@dataclass
class MissionApprovalNeeded(DomainEvent):
    event_type:     str = MISSION_APPROVAL_NEEDED
    aggregate_type: str = "mission"


@dataclass
class AgentFinished(DomainEvent):
    event_type:     str = AGENT_FINISHED
    aggregate_type: str = "agent"


@dataclass
class StepStarted(DomainEvent):
    event_type:     str = STEP_STARTED
    aggregate_type: str = "mission"


@dataclass
class StepCompleted(DomainEvent):
    event_type:     str = STEP_COMPLETED
    aggregate_type: str = "mission"


@dataclass
class StepFailed(DomainEvent):
    event_type:     str = STEP_FAILED
    aggregate_type: str = "mission"


@dataclass
class HeartbeatExpired(DomainEvent):
    event_type:     str = HEARTBEAT_EXPIRED
    aggregate_type: str = "mission"


@dataclass
class RetryScheduled(DomainEvent):
    event_type:     str = RETRY_SCHEDULED
    aggregate_type: str = "mission"


# --- AI / Recommendations ---

@dataclass
class RecommendationGenerated(DomainEvent):
    event_type:     str = RECOMMENDATION_GENERATED
    aggregate_type: str = "recommendation"


# --- Twin ---

@dataclass
class TwinUpdated(DomainEvent):
    event_type:     str = TWIN_UPDATED
    aggregate_type: str = "twin"


@dataclass
class TwinGoalReached(DomainEvent):
    event_type:     str = TWIN_GOAL_REACHED
    aggregate_type: str = "twin"


# --- Knowledge Graph ---

@dataclass
class KnowledgeGraphUpdated(DomainEvent):
    event_type:     str = KNOWLEDGE_GRAPH_UPDATED
    aggregate_type: str = "knowledge_graph"


@dataclass
class KGNodeAdded(DomainEvent):
    event_type:     str = KG_NODE_ADDED
    aggregate_type: str = "knowledge_graph"


@dataclass
class KGEdgeAdded(DomainEvent):
    event_type:     str = KG_EDGE_ADDED
    aggregate_type: str = "knowledge_graph"


# --- Identity ---

@dataclass
class ORCIDSynced(DomainEvent):
    event_type:     str = ORCID_SYNCED
    aggregate_type: str = "identity"


@dataclass
class UserVerified(DomainEvent):
    event_type:     str = USER_VERIFIED
    aggregate_type: str = "identity"


@dataclass
class ProfileCompleted(DomainEvent):
    event_type:     str = PROFILE_COMPLETED
    aggregate_type: str = "identity"


# --- Grants ---

@dataclass
class GrantDiscovered(DomainEvent):
    event_type:     str = GRANT_DISCOVERED
    aggregate_type: str = "grant"


@dataclass
class GrantSubmitted(DomainEvent):
    event_type:     str = GRANT_SUBMITTED
    aggregate_type: str = "grant"


@dataclass
class GrantAwarded(DomainEvent):
    event_type:     str = GRANT_AWARDED
    aggregate_type: str = "grant"


# --- Institution ---

@dataclass
class InstitutionUpdated(DomainEvent):
    event_type:     str = INSTITUTION_UPDATED
    aggregate_type: str = "institution"


@dataclass
class InstitutionMemberAdded(DomainEvent):
    event_type:     str = INSTITUTION_MEMBER_ADDED
    aggregate_type: str = "institution"


@dataclass
class InstitutionMemberRemoved(DomainEvent):
    event_type:     str = INSTITUTION_MEMBER_REMOVED
    aggregate_type: str = "institution"


# --- Teaching ---

@dataclass
class TeachingActivityCreated(DomainEvent):
    event_type:     str = TEACHING_ACTIVITY_CREATED
    aggregate_type: str = "teaching"


# --- Marketplace ---

@dataclass
class MarketplaceOrderCreated(DomainEvent):
    event_type:     str = MARKETPLACE_ORDER_CREATED
    aggregate_type: str = "marketplace"


# --- Research ---

@dataclass
class ResearchGoalReached(DomainEvent):
    event_type:     str = RESEARCH_GOAL_REACHED
    aggregate_type: str = "research"


@dataclass
class CollaborationStarted(DomainEvent):
    event_type:     str = COLLABORATION_STARTED
    aggregate_type: str = "collaboration"


# ── Registry of all event classes ─────────────────────────────────────────────

EVENT_CLASS_MAP: dict[str, type[DomainEvent]] = {
    PUBLICATION_CREATED:      PublicationCreated,
    PUBLICATION_UPDATED:      PublicationUpdated,
    PUBLICATION_DELETED:      PublicationDeleted,
    PUBLICATION_SUBMITTED:    PublicationSubmitted,
    PUBLICATION_PUBLISHED:    PublicationPublished,
    CITATION_ADDED:           CitationAdded,
    CITATION_REMOVED:         CitationRemoved,
    PROJECT_CREATED:          ProjectCreated,
    PROJECT_ARCHIVED:         ProjectArchived,
    WORKSPACE_CREATED:        WorkspaceCreated,
    WORKSPACE_SHARED:         WorkspaceShared,
    MISSION_CREATED:          MissionCreated,
    MISSION_QUEUED:           MissionQueued,
    MISSION_STARTED:          MissionStarted,
    MISSION_PAUSED:           MissionPaused,
    MISSION_RESUMED:          MissionResumed,
    MISSION_COMPLETED:        MissionCompleted,
    MISSION_FAILED:           MissionFailed,
    MISSION_CANCELLED:        MissionCancelled,
    MISSION_APPROVAL_NEEDED:  MissionApprovalNeeded,
    AGENT_FINISHED:           AgentFinished,
    STEP_STARTED:             StepStarted,
    STEP_COMPLETED:           StepCompleted,
    STEP_FAILED:              StepFailed,
    HEARTBEAT_EXPIRED:        HeartbeatExpired,
    RETRY_SCHEDULED:          RetryScheduled,
    RECOMMENDATION_GENERATED: RecommendationGenerated,
    TWIN_UPDATED:             TwinUpdated,
    TWIN_GOAL_REACHED:        TwinGoalReached,
    KNOWLEDGE_GRAPH_UPDATED:  KnowledgeGraphUpdated,
    KG_NODE_ADDED:            KGNodeAdded,
    KG_EDGE_ADDED:            KGEdgeAdded,
    ORCID_SYNCED:             ORCIDSynced,
    USER_VERIFIED:            UserVerified,
    PROFILE_COMPLETED:        ProfileCompleted,
    GRANT_DISCOVERED:         GrantDiscovered,
    GRANT_SUBMITTED:          GrantSubmitted,
    GRANT_AWARDED:            GrantAwarded,
    INSTITUTION_UPDATED:      InstitutionUpdated,
    INSTITUTION_MEMBER_ADDED:     InstitutionMemberAdded,
    INSTITUTION_MEMBER_REMOVED:   InstitutionMemberRemoved,
    TEACHING_ACTIVITY_CREATED:    TeachingActivityCreated,
    MARKETPLACE_ORDER_CREATED:    MarketplaceOrderCreated,
    RESEARCH_GOAL_REACHED:        ResearchGoalReached,
    COLLABORATION_STARTED:        CollaborationStarted,
}


def event_from_dict(d: dict) -> DomainEvent:
    """Deserialize a persisted event dict back to its typed class."""
    cls = EVENT_CLASS_MAP.get(d.get("event_type", ""), DomainEvent)
    return cls.from_dict(d)
