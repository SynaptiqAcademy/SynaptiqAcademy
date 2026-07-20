"""
Event processor.

Handles incremental twin updates triggered by platform events.
Each event type maps to a specific twin field update.
Events are logged in twin_events for full audit trail.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Literal

from .twin_store import log_event, upsert_twin

logger = logging.getLogger("twin.events")

EventType = Literal[
    "manuscript_created",
    "manuscript_updated",
    "manuscript_submitted",
    "manuscript_published",
    "project_created",
    "project_completed",
    "collaboration_accepted",
    "grant_submitted",
    "grant_awarded",
    "orcid_synced",
    "profile_updated",
    "teaching_lesson_added",
    "citation_updated",
    "lkg_synced",
]


async def process_event(db, user_id: str, event_type: EventType, payload: dict | None = None) -> None:
    """
    Process a single platform event and update the twin accordingly.
    Each event is logged in twin_events.
    """
    payload = payload or {}
    now     = datetime.now(timezone.utc)

    logger.info("Twin event [%s] for user %s: %s", event_type, user_id, payload)

    try:
        from obs.metrics import get_metrics, M_TWIN_UPDATES
        get_metrics().inc(M_TWIN_UPDATES, tags={"event_type": event_type})
    except Exception:
        pass

    if event_type in ("manuscript_created", "manuscript_updated", "manuscript_submitted", "manuscript_published"):
        count = await db.manuscripts.count_documents({"user_id": user_id})
        await upsert_twin(db, user_id, {"activity_summary.manuscripts_count": count, "activity_summary.last_computed": now})
        await log_event(db, user_id, event_type, f"Manuscripts count updated to {count}", [
            {"source": "Synaptiq manuscripts DB", "detail": f"{count} total manuscripts"}
        ])

    elif event_type == "project_created":
        count = await db.projects.count_documents({"user_id": user_id})
        await upsert_twin(db, user_id, {"activity_summary.projects_count": count, "activity_summary.last_computed": now})
        await log_event(db, user_id, event_type, f"Projects count updated to {count}")

    elif event_type == "collaboration_accepted":
        count = await db.collaborations.count_documents({
            "$or": [{"requester_id": user_id}, {"recipient_id": user_id}],
            "status": "accepted",
        })
        await upsert_twin(db, user_id, {"activity_summary.collaborations_count": count, "activity_summary.last_computed": now})
        await log_event(db, user_id, event_type, f"Collaboration count updated to {count}")

    elif event_type == "grant_submitted":
        count = await db.grants.count_documents({"user_id": user_id})
        await upsert_twin(db, user_id, {"activity_summary.grants_count": count, "activity_summary.last_computed": now})
        await log_event(db, user_id, event_type, f"Grant count updated to {count}")

    elif event_type == "teaching_lesson_added":
        try:
            count = await db.lessons.count_documents({"instructor_id": user_id})
        except Exception:
            count = payload.get("lesson_count", 0)
        await upsert_twin(db, user_id, {"activity_summary.teaching_lessons": count, "activity_summary.last_computed": now})
        await log_event(db, user_id, event_type, f"Teaching lesson count updated to {count}")

    elif event_type == "orcid_synced":
        pub_count = payload.get("publications_count", 0)
        await upsert_twin(db, user_id, {"activity_summary.orcid_publications": pub_count, "activity_summary.last_computed": now})
        await log_event(db, user_id, event_type, f"ORCID sync: {pub_count} publications", [
            {"source": "ORCID", "detail": f"{pub_count} verified publications"}
        ])

    elif event_type == "profile_updated":
        await log_event(db, user_id, event_type, "Profile fields updated — twin will rebuild on next sync")

    elif event_type == "lkg_synced":
        node_id = f"researcher:platform:{user_id}"
        try:
            lkg_edge_count = await db.lkg_edges.count_documents({
                "$or": [{"from_id": node_id}, {"to_id": node_id}]
            })
            await upsert_twin(db, user_id, {"activity_summary.lkg_edge_count": lkg_edge_count})
        except Exception:
            pass
        await log_event(db, user_id, event_type, "LKG synchronized")

    else:
        await log_event(db, user_id, event_type, f"Unhandled event type: {event_type}")
