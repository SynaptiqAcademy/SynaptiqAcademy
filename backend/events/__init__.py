"""
Enterprise Event Bus — the communication backbone of Synaptiq.

All domain events flow through the EnterpriseEventBus. No module calls
another module directly for cross-domain side-effects.

Quick start:
    from events import get_bus, PublicationCreated

    bus = get_bus()

    # Publish
    event = PublicationCreated(aggregate_id=pub_id, user_id=user_id, payload={...})
    await bus.publish(event)

    # Subscribe
    async def on_pub_created(event):
        ...
    bus.subscribe("publication.created", on_pub_created, consumer_id="my_handler")
"""
from .bus     import EnterpriseEventBus, get_bus, reset_bus
from .outbox  import OutboxPublisher
from .store   import EventStore
from .registry import catalog as event_catalog
from .replay  import ReplayEngine
from .dlq     import DeadLetterQueue
from .observability import get_observability
from .circuit_breaker import get_circuit_breaker

# Domain event classes
from .models import (
    DomainEvent,
    event_from_dict,
    EVENT_CLASS_MAP,

    # Publications
    PublicationCreated, PublicationUpdated, PublicationDeleted,
    PublicationSubmitted, PublicationPublished,

    # Citations
    CitationAdded, CitationRemoved,

    # Projects / Workspaces
    ProjectCreated, ProjectArchived,
    WorkspaceCreated, WorkspaceShared,

    # Missions
    MissionCreated, MissionQueued, MissionStarted, MissionPaused, MissionResumed,
    MissionCompleted, MissionFailed, MissionCancelled,
    MissionApprovalNeeded, AgentFinished,

    # Steps / Worker
    StepStarted, StepCompleted, StepFailed,
    HeartbeatExpired, RetryScheduled,

    # AI
    RecommendationGenerated,

    # Twin
    TwinUpdated, TwinGoalReached,

    # Knowledge Graph
    KnowledgeGraphUpdated, KGNodeAdded, KGEdgeAdded,

    # Identity
    ORCIDSynced, UserVerified, ProfileCompleted,

    # Grants
    GrantDiscovered, GrantSubmitted, GrantAwarded,

    # Institution
    InstitutionUpdated, InstitutionMemberAdded, InstitutionMemberRemoved,

    # Teaching
    TeachingActivityCreated,

    # Marketplace
    MarketplaceOrderCreated,

    # Research
    ResearchGoalReached, CollaborationStarted,

    # Type constants
    PUBLICATION_CREATED, PUBLICATION_UPDATED, PUBLICATION_DELETED,
    PUBLICATION_SUBMITTED, PUBLICATION_PUBLISHED,
    CITATION_ADDED, CITATION_REMOVED,
    PROJECT_CREATED, PROJECT_ARCHIVED,
    WORKSPACE_CREATED, WORKSPACE_SHARED,
    MISSION_CREATED, MISSION_QUEUED, MISSION_STARTED, MISSION_PAUSED, MISSION_RESUMED,
    MISSION_COMPLETED, MISSION_FAILED, MISSION_CANCELLED,
    MISSION_APPROVAL_NEEDED, AGENT_FINISHED,
    STEP_STARTED, STEP_COMPLETED, STEP_FAILED,
    HEARTBEAT_EXPIRED, RETRY_SCHEDULED,
    RECOMMENDATION_GENERATED,
    TWIN_UPDATED, TWIN_GOAL_REACHED,
    KNOWLEDGE_GRAPH_UPDATED, KG_NODE_ADDED, KG_EDGE_ADDED,
    ORCID_SYNCED, USER_VERIFIED, PROFILE_COMPLETED,
    GRANT_DISCOVERED, GRANT_SUBMITTED, GRANT_AWARDED,
    INSTITUTION_UPDATED, INSTITUTION_MEMBER_ADDED, INSTITUTION_MEMBER_REMOVED,
    TEACHING_ACTIVITY_CREATED,
    MARKETPLACE_ORDER_CREATED,
    RESEARCH_GOAL_REACHED, COLLABORATION_STARTED,
)


async def start_event_bus(db) -> EnterpriseEventBus:
    """
    Start the enterprise event bus and register all domain handlers.

    Called once at server startup.
    """
    from .subscriptions import register_all_handlers
    bus = get_bus()
    await bus.start(db)
    register_all_handlers(bus)
    return bus


async def stop_event_bus() -> None:
    """Gracefully stop the event bus. Called at server shutdown."""
    bus = get_bus()
    await bus.stop()


__all__ = [
    "EnterpriseEventBus", "get_bus", "reset_bus",
    "start_event_bus", "stop_event_bus",
    "OutboxPublisher", "EventStore", "ReplayEngine",
    "DeadLetterQueue", "get_observability", "get_circuit_breaker",
    "event_catalog", "event_from_dict", "EVENT_CLASS_MAP",
    "DomainEvent",
    # Events
    "PublicationCreated", "PublicationUpdated", "PublicationDeleted",
    "PublicationSubmitted", "PublicationPublished",
    "CitationAdded", "CitationRemoved",
    "ProjectCreated", "ProjectArchived",
    "WorkspaceCreated", "WorkspaceShared",
    "MissionCreated", "MissionStarted", "MissionCompleted", "MissionFailed",
    "MissionApprovalNeeded", "AgentFinished",
    "RecommendationGenerated",
    "TwinUpdated", "TwinGoalReached",
    "KnowledgeGraphUpdated", "KGNodeAdded", "KGEdgeAdded",
    "ORCIDSynced", "UserVerified", "ProfileCompleted",
    "GrantDiscovered", "GrantSubmitted", "GrantAwarded",
    "InstitutionUpdated", "InstitutionMemberAdded", "InstitutionMemberRemoved",
    "TeachingActivityCreated", "MarketplaceOrderCreated",
    "ResearchGoalReached", "CollaborationStarted",
    # Constants
    "PUBLICATION_CREATED", "PUBLICATION_UPDATED", "PUBLICATION_DELETED",
    "MISSION_CREATED", "MISSION_QUEUED", "MISSION_STARTED", "MISSION_PAUSED",
    "MISSION_RESUMED", "MISSION_COMPLETED", "MISSION_FAILED", "MISSION_CANCELLED",
    "MISSION_APPROVAL_NEEDED",
    "STEP_STARTED", "STEP_COMPLETED", "STEP_FAILED",
    "HEARTBEAT_EXPIRED", "RETRY_SCHEDULED",
    "GRANT_AWARDED", "USER_VERIFIED",
    "MissionCreated", "MissionQueued", "MissionStarted", "MissionPaused",
    "MissionResumed", "MissionCompleted", "MissionFailed", "MissionCancelled",
    "MissionApprovalNeeded",
    "StepStarted", "StepCompleted", "StepFailed",
    "HeartbeatExpired", "RetryScheduled",
]
