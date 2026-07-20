"""Memory Service — CRUD for user AI memory items stored in ai_memory collection."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from bson import ObjectId

logger = logging.getLogger("synaptiq.ai.memory_service")

VALID_MEMORY_TYPES = {
    "research_goal",
    "publication_goal",
    "target_journal",
    "target_conference",
    "target_grant",
    "preferred_method",
    "career_goal",
    "teaching_goal",
    "collaboration_preference",
    "general",
}

# ── Patterns for heuristic memory extraction ──────────────────────────────────
# (pattern_regex, memory_type)
_MEMORY_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Research goals
    (re.compile(r"\bi\s+want\s+to\s+research\b(.{10,120})", re.IGNORECASE), "research_goal"),
    (re.compile(r"\bmy\s+research\s+goal\s+is\b(.{5,120})", re.IGNORECASE), "research_goal"),
    (re.compile(r"\bi(?:'m|\s+am)\s+investigating\b(.{5,120})", re.IGNORECASE), "research_goal"),
    (re.compile(r"\bi(?:'m|\s+am)\s+researching\b(.{5,120})", re.IGNORECASE), "research_goal"),
    # Publication goals
    (re.compile(r"\bmy\s+goal\s+is\s+to\s+publish\b(.{5,120})", re.IGNORECASE), "publication_goal"),
    (re.compile(r"\bi\s+want\s+to\s+publish\b(.{5,120})", re.IGNORECASE), "publication_goal"),
    (re.compile(r"\bi(?:'m|\s+am)\s+writing\s+a\s+(paper|manuscript|article)\b(.{0,80})", re.IGNORECASE), "publication_goal"),
    # Target journals
    (re.compile(r"\bi(?:'m|\s+am)\s+targeting\s+(?:the\s+)?([A-Z][A-Za-z\s&\-]{3,80})\s+journal", re.IGNORECASE), "target_journal"),
    (re.compile(r"\bsubmit\s+to\s+(?:the\s+)?([A-Z][A-Za-z\s&\-]{3,80})", re.IGNORECASE), "target_journal"),
    # Target grants
    (re.compile(r"\bapplying\s+for\b(.{5,120})\s+grant", re.IGNORECASE), "target_grant"),
    (re.compile(r"\bi\s+want\s+to\s+apply\s+for\b(.{5,120})", re.IGNORECASE), "target_grant"),
    # Career goals
    (re.compile(r"\bmy\s+career\s+goal\s+is\b(.{5,120})", re.IGNORECASE), "career_goal"),
    (re.compile(r"\bi\s+want\s+to\s+become\b(.{5,120})", re.IGNORECASE), "career_goal"),
    (re.compile(r"\bi\s+am\s+aiming\s+for\b(.{5,120})", re.IGNORECASE), "career_goal"),
    # Preferred methods
    (re.compile(r"\bi\s+prefer\s+(?:using\s+)?(?:a\s+)?([a-z\s\-]{5,80})\s+(?:method|approach|technique)", re.IGNORECASE), "preferred_method"),
    # General goals
    (re.compile(r"\bmy\s+goal\s+is\b(.{5,120})", re.IGNORECASE), "general"),
    (re.compile(r"\bi(?:'m|\s+am)\s+focused\s+on\b(.{5,120})", re.IGNORECASE), "general"),
    (re.compile(r"\bi\s+am\s+working\s+on\b(.{5,120})", re.IGNORECASE), "general"),
    (re.compile(r"\bmy\s+priority\s+is\b(.{5,120})", re.IGNORECASE), "general"),
]


async def get_user_memory(user_id: str, db) -> list[dict]:
    """Return all active memory items for user, sorted by created_at ascending."""
    try:
        cursor = db.ai_memory.find(
            {"user_id": user_id, "is_active": True}
        ).sort("created_at", 1)
        items = await cursor.to_list(100)
        result = []
        for item in items:
            doc = dict(item)
            doc["id"] = str(doc.pop("_id"))
            result.append(doc)
        return result
    except Exception as exc:
        logger.error("get_user_memory failed user=%s err=%s", user_id, exc)
        return []


async def save_memory(user_id: str, memory_type: str, content: str, db) -> dict:
    """
    Upsert a memory item of the given type.
    If an active item of the same memory_type already exists, update it.
    Otherwise insert a new one.

    Returns the saved document.
    """
    if memory_type not in VALID_MEMORY_TYPES:
        memory_type = "general"

    content = content.strip()[:1000]  # cap length
    now = datetime.now(timezone.utc).isoformat()

    try:
        existing = await db.ai_memory.find_one({
            "user_id": user_id,
            "memory_type": memory_type,
            "is_active": True,
        })

        if existing:
            await db.ai_memory.update_one(
                {"_id": existing["_id"]},
                {"$set": {"content": content, "updated_at": now}},
            )
            doc = dict(existing)
            doc["content"] = content
            doc["updated_at"] = now
            doc["id"] = str(doc.pop("_id"))
            return doc
        else:
            new_doc = {
                "user_id": user_id,
                "memory_type": memory_type,
                "content": content,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            }
            result = await db.ai_memory.insert_one(new_doc)
            new_doc["id"] = str(result.inserted_id)
            new_doc.pop("_id", None)
            return new_doc

    except Exception as exc:
        logger.error("save_memory failed user=%s err=%s", user_id, exc)
        return {"error": str(exc)}


async def delete_memory(user_id: str, memory_id: str, db) -> bool:
    """Delete a specific memory item. Returns True if deleted."""
    try:
        result = await db.ai_memory.delete_one({
            "_id": ObjectId(memory_id),
            "user_id": user_id,
        })
        return result.deleted_count > 0
    except Exception as exc:
        logger.error("delete_memory failed user=%s memory_id=%s err=%s", user_id, memory_id, exc)
        return False


async def clear_all_memory(user_id: str, db) -> int:
    """GDPR: delete all memory items for user. Returns count deleted."""
    try:
        result = await db.ai_memory.delete_many({"user_id": user_id})
        return result.deleted_count
    except Exception as exc:
        logger.error("clear_all_memory failed user=%s err=%s", user_id, exc)
        return 0


async def extract_memory_from_response(response: str, user_message: str) -> list[dict]:
    """
    Heuristically detect if the user message or response contains something worth remembering.
    Searches both the user message and any explicit "I want to" / "my goal is" type phrases.
    Returns list of {memory_type, content} dicts.
    Does NOT call LLM — pure string matching.
    """
    found: list[dict] = []
    seen_contents: set[str] = set()

    # Search primarily in the user message (what the user said about themselves)
    texts_to_search = [user_message]

    for text in texts_to_search:
        for pattern, memory_type in _MEMORY_PATTERNS:
            matches = pattern.findall(text)
            for match in matches:
                # match can be a tuple (when there are multiple capture groups) or a string
                if isinstance(match, tuple):
                    content_raw = " ".join(str(m) for m in match if m).strip()
                else:
                    content_raw = str(match).strip()

                # Clean up common trailing junk
                content = re.sub(r"[.,;:!?]+$", "", content_raw).strip()
                content = re.sub(r"\s+", " ", content)

                if len(content) < 8:
                    continue

                # Deduplicate
                key = f"{memory_type}:{content.lower()[:60]}"
                if key in seen_contents:
                    continue
                seen_contents.add(key)

                found.append({
                    "memory_type": memory_type,
                    "content": content,
                })

    # Cap at 3 items per call to avoid noise
    return found[:3]
