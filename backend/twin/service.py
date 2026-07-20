"""
Digital Twin service layer.

Thin wrapper around twin/event_processor.py that maps enterprise event
activity types to twin event types and emits observability metrics.

Called from events/subscriptions.py handlers.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("twin.service")

# Map enterprise activity types to twin event types
_ACTIVITY_MAP: dict[str, str] = {
    "publication_published":  "manuscript_published",
    "publication_created":    "manuscript_created",
    "publication_submitted":  "manuscript_submitted",
    "manuscript_published":   "manuscript_published",
    "manuscript_created":     "manuscript_created",
    "mission_completed":      "project_completed",
    "grant_awarded":          "grant_awarded",
    "grant_submitted":        "grant_submitted",
    "collaboration_started":  "collaboration_accepted",
    "orcid_synced":           "orcid_synced",
    "profile_updated":        "profile_updated",
    "lkg_synced":             "lkg_synced",
    "teaching_activity":      "teaching_lesson_added",
}


async def record_activity(
    user_id: str,
    activity_type: str,
    metadata: dict | None = None,
    db=None,
) -> None:
    """
    Record a platform activity in the digital twin.

    Maps enterprise event activity_type strings to twin event types and
    delegates to twin.event_processor.process_event.
    """
    twin_event = _ACTIVITY_MAP.get(activity_type, activity_type)
    try:
        from obs.metrics import get_metrics, M_TWIN_UPDATES
        get_metrics().inc(M_TWIN_UPDATES, tags={"activity_type": activity_type})
    except Exception:
        pass

    if db is None:
        try:
            from db import get_db
            db = get_db()
        except Exception:
            logger.debug("twin.service: no db available for record_activity(%s)", activity_type)
            return

    try:
        from .event_processor import process_event
        await process_event(db, user_id, twin_event, metadata or {})  # type: ignore[arg-type]
    except Exception as exc:
        logger.debug("twin.service record_activity failed (%s): %s", activity_type, exc)
