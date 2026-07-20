"""
Centralized Handler Registrations — wires all domain handlers to the event bus.

This is the ONLY place where modules subscribe to each other's events.
No service file imports another service file directly for cross-domain purposes.
Instead, each domain registers handlers here via the bus.

Registration pattern:
    bus.subscribe(
        event_type,
        handler_fn,
        consumer_id="domain_service.action",
        description="What this handler does",
    )

All handlers are:
  - Async coroutines: async def handler(event: DomainEvent) -> None
  - Idempotent by default (guarded by EventStore)
  - Wrapped in circuit breaker, retry, and DLQ by HandlerExecutor

IMPORTANT: handlers call service functions, NOT other service files directly.
           All cross-domain effects flow through events.
"""
from __future__ import annotations

import logging

from .bus    import EnterpriseEventBus
from .models import (
    DomainEvent,
    PUBLICATION_CREATED, PUBLICATION_PUBLISHED,
    CITATION_ADDED,
    MISSION_COMPLETED, MISSION_FAILED, MISSION_APPROVAL_NEEDED,
    GRANT_AWARDED, GRANT_SUBMITTED,
    USER_VERIFIED, PROFILE_COMPLETED, ORCID_SYNCED,
    TWIN_GOAL_REACHED,
    WORKSPACE_SHARED,
    RESEARCH_GOAL_REACHED,
    TEACHING_ACTIVITY_CREATED,
    MARKETPLACE_ORDER_CREATED,
    KNOWLEDGE_GRAPH_UPDATED,
    RECOMMENDATION_GENERATED,
    INSTITUTION_MEMBER_ADDED,
    AGENT_FINISHED,
)

logger = logging.getLogger(__name__)


# ── Handler definitions ────────────────────────────────────────────────────────
# Each handler is a thin adapter: it receives a DomainEvent, extracts the
# payload, and calls the appropriate service function.
# Service functions are imported lazily (inside the handler) to avoid circular
# imports at module load time.


# ── Knowledge Graph handlers ───────────────────────────────────────────────────

async def _on_publication_created__update_kg(event: DomainEvent) -> None:
    """Add publication node to the Living Knowledge Graph."""
    try:
        from lkg.service import ingest_publication_event
        await ingest_publication_event(
            event_type=event.event_type,
            aggregate_id=event.aggregate_id,
            user_id=event.user_id,
            payload=event.payload,
        )
    except ImportError:
        pass  # LKG service not loaded in this deployment
    except Exception as exc:
        logger.warning("KG handler (publication.created): %s", exc)
        raise


async def _on_citation_added__update_kg(event: DomainEvent) -> None:
    try:
        from lkg.service import ingest_citation_event
        await ingest_citation_event(
            aggregate_id=event.aggregate_id,
            user_id=event.user_id,
            payload=event.payload,
        )
    except ImportError:
        pass
    except Exception as exc:
        logger.warning("KG handler (citation.added): %s", exc)
        raise


# ── Digital Twin handlers ──────────────────────────────────────────────────────

async def _on_publication_published__update_twin(event: DomainEvent) -> None:
    """Record publication in the digital twin's activity history."""
    try:
        from twin.service import record_activity
        await record_activity(
            user_id=event.user_id,
            activity_type="publication_published",
            metadata={"publication_id": event.aggregate_id, **event.payload},
        )
    except ImportError:
        pass
    except Exception as exc:
        logger.warning("Twin handler (publication.published): %s", exc)
        raise


async def _on_mission_completed__update_twin(event: DomainEvent) -> None:
    try:
        from twin.service import record_activity
        await record_activity(
            user_id=event.user_id,
            activity_type="mission_completed",
            metadata={"mission_id": event.aggregate_id, **event.payload},
        )
    except ImportError:
        pass
    except Exception as exc:
        logger.warning("Twin handler (mission.completed): %s", exc)
        raise


async def _on_grant_awarded__update_twin(event: DomainEvent) -> None:
    try:
        from twin.service import record_activity
        await record_activity(
            user_id=event.user_id,
            activity_type="grant_awarded",
            metadata={"grant_id": event.aggregate_id, **event.payload},
        )
    except ImportError:
        pass
    except Exception as exc:
        logger.warning("Twin handler (grant.awarded): %s", exc)
        raise


# ── Notification handlers ──────────────────────────────────────────────────────

async def _on_mission_completed__notify(event: DomainEvent) -> None:
    try:
        from notifications_service import send_notification
        await send_notification(
            user_id=event.user_id,
            title="Mission Completed",
            message=f"Your research mission has completed successfully.",
            type="success",
            link=f"/agent-workforce/{event.aggregate_id}",
        )
    except (ImportError, Exception) as exc:
        if not isinstance(exc, ImportError):
            logger.debug("Notification handler (mission.completed): %s", exc)


async def _on_mission_failed__notify(event: DomainEvent) -> None:
    try:
        from notifications_service import send_notification
        await send_notification(
            user_id=event.user_id,
            title="Mission Failed",
            message=f"A research mission could not complete. Please review and retry.",
            type="error",
            link=f"/agent-workforce/{event.aggregate_id}",
        )
    except (ImportError, Exception) as exc:
        if not isinstance(exc, ImportError):
            logger.debug("Notification handler (mission.failed): %s", exc)


async def _on_mission_approval_needed__notify(event: DomainEvent) -> None:
    try:
        from notifications_service import send_notification
        await send_notification(
            user_id=event.user_id,
            title="Mission Awaiting Your Approval",
            message="A research mission needs your review before continuing.",
            type="warning",
            link=f"/agent-workforce/{event.aggregate_id}",
        )
    except (ImportError, Exception) as exc:
        if not isinstance(exc, ImportError):
            logger.debug("Notification handler (mission.approval_needed): %s", exc)


async def _on_grant_awarded__notify(event: DomainEvent) -> None:
    try:
        from notifications_service import send_notification
        await send_notification(
            user_id=event.user_id,
            title="Grant Awarded",
            message=f"Congratulations! Your grant application was successful.",
            type="success",
            link=f"/grant-hub/{event.aggregate_id}",
        )
    except (ImportError, Exception) as exc:
        if not isinstance(exc, ImportError):
            logger.debug("Notification handler (grant.awarded): %s", exc)


async def _on_user_verified__notify(event: DomainEvent) -> None:
    try:
        from notifications_service import send_notification
        await send_notification(
            user_id=event.user_id,
            title="Identity Verified",
            message="Your researcher identity has been verified. Your trust score has increased.",
            type="success",
            link="/verification",
        )
    except (ImportError, Exception) as exc:
        if not isinstance(exc, ImportError):
            logger.debug("Notification handler (identity.user_verified): %s", exc)


async def _on_workspace_shared__notify(event: DomainEvent) -> None:
    try:
        from notifications_service import send_notification
        shared_with = event.payload.get("shared_with_user_id")
        if shared_with:
            await send_notification(
                user_id=shared_with,
                title="Workspace Shared With You",
                message=f"A research workspace has been shared with you.",
                type="info",
                link=f"/workspace/{event.aggregate_id}",
            )
    except (ImportError, Exception) as exc:
        if not isinstance(exc, ImportError):
            logger.debug("Notification handler (workspace.shared): %s", exc)


async def _on_twin_goal_reached__notify(event: DomainEvent) -> None:
    try:
        from notifications_service import send_notification
        await send_notification(
            user_id=event.user_id,
            title="Research Goal Reached!",
            message=f"You have achieved one of your research goals.",
            type="success",
            link="/twin",
        )
    except (ImportError, Exception) as exc:
        if not isinstance(exc, ImportError):
            logger.debug("Notification handler (twin.goal_reached): %s", exc)


async def _on_recommendation_generated__notify(event: DomainEvent) -> None:
    try:
        from notifications_service import send_notification
        title = event.payload.get("title", "New AI Recommendation")
        await send_notification(
            user_id=event.user_id,
            title="New Recommendation",
            message=title,
            type="info",
            link="/recommendations",
        )
    except (ImportError, Exception) as exc:
        if not isinstance(exc, ImportError):
            logger.debug("Notification handler (recommendation.generated): %s", exc)


# ── Reputation handlers ────────────────────────────────────────────────────────

async def _on_publication_published__update_reputation(event: DomainEvent) -> None:
    try:
        from services.reputation_service import record_reputation_event
        await record_reputation_event(
            user_id=event.user_id,
            event_type="publication_published",
            aggregate_id=event.aggregate_id,
        )
    except ImportError:
        pass
    except Exception as exc:
        logger.debug("Reputation handler (publication.published): %s", exc)


async def _on_citation_added__update_reputation(event: DomainEvent) -> None:
    try:
        from services.reputation_service import record_reputation_event
        await record_reputation_event(
            user_id=event.user_id,
            event_type="citation_received",
            aggregate_id=event.aggregate_id,
        )
    except ImportError:
        pass
    except Exception as exc:
        logger.debug("Reputation handler (citation.added): %s", exc)


async def _on_grant_awarded__update_reputation(event: DomainEvent) -> None:
    try:
        from services.reputation_service import record_reputation_event
        await record_reputation_event(
            user_id=event.user_id,
            event_type="grant_awarded",
            aggregate_id=event.aggregate_id,
        )
    except ImportError:
        pass
    except Exception as exc:
        logger.debug("Reputation handler (grant.awarded): %s", exc)


# ── Analytics observer ─────────────────────────────────────────────────────────

async def _on_any__analytics(event: DomainEvent) -> None:
    """Wildcard handler — records every event in the analytics pipeline."""
    try:
        from services.analytics_service import record_event_metric
        await record_event_metric(
            event_type=event.event_type,
            user_id=event.user_id,
            aggregate_type=event.aggregate_type,
        )
    except ImportError:
        pass
    except Exception as exc:
        logger.debug("Analytics handler: %s", exc)


# ── Registration function ──────────────────────────────────────────────────────

def register_all_handlers(bus: EnterpriseEventBus) -> None:
    """
    Wire all domain handlers to the event bus.

    Called once at server startup via start_event_bus().
    """

    # ── Knowledge Graph ────────────────────────────────────────────────────────
    bus.subscribe(
        PUBLICATION_CREATED,
        _on_publication_created__update_kg,
        consumer_id="lkg.publication_created",
        description="Add publication node to Living Knowledge Graph",
        timeout_s=20.0,
    )
    bus.subscribe(
        CITATION_ADDED,
        _on_citation_added__update_kg,
        consumer_id="lkg.citation_added",
        description="Add citation edge to Living Knowledge Graph",
        timeout_s=20.0,
    )

    # ── Digital Twin ──────────────────────────────────────────────────────────
    bus.subscribe(
        PUBLICATION_PUBLISHED,
        _on_publication_published__update_twin,
        consumer_id="twin.publication_published",
        description="Record publication in Digital Research Twin",
    )
    bus.subscribe(
        MISSION_COMPLETED,
        _on_mission_completed__update_twin,
        consumer_id="twin.mission_completed",
        description="Record completed mission in Digital Research Twin",
    )
    bus.subscribe(
        GRANT_AWARDED,
        _on_grant_awarded__update_twin,
        consumer_id="twin.grant_awarded",
        description="Record grant award in Digital Research Twin",
    )

    # ── Notifications ──────────────────────────────────────────────────────────
    bus.subscribe(
        MISSION_COMPLETED,
        _on_mission_completed__notify,
        consumer_id="notify.mission_completed",
        description="Notify user when mission completes",
        timeout_s=10.0,
    )
    bus.subscribe(
        MISSION_FAILED,
        _on_mission_failed__notify,
        consumer_id="notify.mission_failed",
        description="Notify user when mission fails",
        timeout_s=10.0,
    )
    bus.subscribe(
        MISSION_APPROVAL_NEEDED,
        _on_mission_approval_needed__notify,
        consumer_id="notify.mission_approval_needed",
        description="Notify user when mission needs human approval",
        timeout_s=10.0,
    )
    bus.subscribe(
        GRANT_AWARDED,
        _on_grant_awarded__notify,
        consumer_id="notify.grant_awarded",
        description="Notify user when grant is awarded",
        timeout_s=10.0,
    )
    bus.subscribe(
        USER_VERIFIED,
        _on_user_verified__notify,
        consumer_id="notify.user_verified",
        description="Notify user when identity verification completes",
        timeout_s=10.0,
    )
    bus.subscribe(
        WORKSPACE_SHARED,
        _on_workspace_shared__notify,
        consumer_id="notify.workspace_shared",
        description="Notify collaborator when workspace is shared with them",
        timeout_s=10.0,
    )
    bus.subscribe(
        TWIN_GOAL_REACHED,
        _on_twin_goal_reached__notify,
        consumer_id="notify.twin_goal_reached",
        description="Notify user when a twin research goal is achieved",
        timeout_s=10.0,
    )
    bus.subscribe(
        RECOMMENDATION_GENERATED,
        _on_recommendation_generated__notify,
        consumer_id="notify.recommendation_generated",
        description="Notify user about new AI recommendation",
        timeout_s=10.0,
    )

    # ── Reputation ─────────────────────────────────────────────────────────────
    bus.subscribe(
        PUBLICATION_PUBLISHED,
        _on_publication_published__update_reputation,
        consumer_id="reputation.publication_published",
        description="Update reputation score on publication",
    )
    bus.subscribe(
        CITATION_ADDED,
        _on_citation_added__update_reputation,
        consumer_id="reputation.citation_added",
        description="Update reputation score when citation is received",
    )
    bus.subscribe(
        GRANT_AWARDED,
        _on_grant_awarded__update_reputation,
        consumer_id="reputation.grant_awarded",
        description="Update reputation score when grant is awarded",
    )

    # ── Analytics (wildcard) ───────────────────────────────────────────────────
    bus.subscribe(
        "*",
        _on_any__analytics,
        consumer_id="analytics.all_events",
        description="Record all events in the analytics pipeline",
        timeout_s=5.0,
        idempotent=False,  # analytics counts are cumulative — idempotency not needed
    )

    # ── Admin OS realtime bridge (wildcard) ────────────────────────────────────
    from .admin_bridge import register as register_admin_bridge
    register_admin_bridge(bus)

    logger.info(
        "EventBus: registered %d handlers across %d event types",
        len(bus.all_handlers()),
        len(bus.registry._by_type),
    )
