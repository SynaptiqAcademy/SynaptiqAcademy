"""Academic Copilot — Context Aggregator (Phase XI).

Thin wrapper around services.synaptiq_ai.context_engine that enriches the
base context with copilot-specific fields: active engines, user preferences,
content excerpts for engine scanning.
"""
from __future__ import annotations

import logging

logger = logging.getLogger("synaptiq.copilot.context")


async def build_copilot_context(user_id: str, db, include_manuscripts: bool = True) -> dict:
    """Build full platform context for the copilot.

    Delegates to the existing context_engine then adds copilot-specific
    enrichments without duplicating DB queries where possible.
    """
    try:
        from services.synaptiq_ai.context_engine import build_user_context
        context = await build_user_context(user_id, db)
    except Exception as exc:
        logger.warning("base context build failed: %s", exc)
        context = {
            "profile": {}, "manuscripts": [], "projects": [],
            "collaborations": [], "grants_applied": [], "reputation": {},
            "impact": {}, "memory": [], "summary": "",
        }

    # Enrich with manuscript content excerpts (for engine scanning)
    if include_manuscripts:
        try:
            manuscript_excerpts: dict[str, str] = {}
            for ms in (context.get("manuscripts") or [])[:3]:
                mid = ms.get("id")
                if not mid:
                    continue
                from bson import ObjectId
                doc = await db.manuscripts.find_one(
                    {"_id": ObjectId(mid)},
                    {"content": 1, "abstract": 1, "title": 1}
                )
                if doc:
                    body = doc.get("content") or doc.get("abstract") or ""
                    # Limit to 8 000 chars to keep engine scans fast
                    manuscript_excerpts[mid] = (doc.get("title") or "") + "\n\n" + body[:8_000]
            context["manuscript_excerpts"] = manuscript_excerpts
        except Exception as exc:
            logger.debug("manuscript excerpt enrichment failed: %s", exc)
            context["manuscript_excerpts"] = {}

    # Copilot-specific flags
    context["copilot_ready"] = True
    return context


def extract_scan_content(message: str, context: dict, max_chars: int = 8_000) -> str:
    """Pick the best content to send to engine quick-scans.

    Priority:
    1. Text in the user's message (if long enough to be a manuscript excerpt)
    2. Most recent draft manuscript content
    3. Message itself (for topic/keyword scans)
    """
    # If the message itself is a long text, use it directly
    if len(message) >= 500:
        return message[:max_chars]

    # Otherwise use most recent manuscript excerpt
    excerpts = context.get("manuscript_excerpts") or {}
    if excerpts:
        most_recent = next(iter(excerpts.values()), "")
        if most_recent:
            return most_recent[:max_chars]

    return message
