"""Shared workspace provisioning — the single place that creates a `workspaces`
document (plus its group conversation + activity log entry), so every part of
the platform that turns a match/acceptance/team-formation into a shared place
to work (collaboration requests, grants, conferences, and the manual
"New Workspace" button) goes through the same code path.

Kept separate from routers/workspaces.py (rather than the reverse) so that
other routers (collaboration_requests, grant_applications, a future
conference_teams) can import provision_workspace without creating a
router-to-router circular import.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger("synaptiq.workspace_provisioning")

WORKSPACE_TYPES = {
    "Research Project", "Manuscript", "Grant Proposal", "Conference Paper",
    "Doctoral Thesis", "Research Group", "Institutional Research Team",
    "Consulting Project", "Systematic Review", "Custom Workspace",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ser(d: dict) -> dict:
    x = dict(d)
    x["id"] = str(x.pop("_id"))
    return x


async def _log_activity(db, workspace_id: str, actor_id: str, actor_name: str,
                        message: str, kind: str = "system") -> None:
    try:
        await db.workspace_activity.insert_one({
            "workspace_id": workspace_id,
            "actor_id":     actor_id,
            "actor_name":   actor_name,
            "message":      message,
            "kind":         kind,
            "created_at":   _now(),
        })
    except Exception as exc:
        logger.warning("activity insert failed: %s", exc)


async def provision_workspace(
    db,
    owner_id: str,
    owner_name: str,
    name: str,
    workspace_type: str,
    *,
    extra_members: dict[str, str] | None = None,
    project_id: str | None = None,
    description: str = "",
    institution: str = "",
    research_area: str = "",
    keywords: list[str] | None = None,
    visibility: str = "private",
    activity_message: str | None = None,
) -> dict:
    """Create a workspace document + its group conversation + activity log entry.

    `extra_members` maps user_id -> role for members beyond the owner (e.g. the
    other party in an accepted collaboration request). The owner always gets
    the "Owner" role regardless of what's passed for their id in extra_members.
    """
    ws_type = workspace_type if workspace_type in WORKSPACE_TYPES else "Research Project"
    now = _now()

    member_roles = {owner_id: "Owner"}
    members = [owner_id]
    for uid, role in (extra_members or {}).items():
        if uid == owner_id:
            continue
        members.append(uid)
        member_roles[uid] = role

    doc = {
        "name":           (name or "Untitled Workspace").strip(),
        "description":    (description or "").strip(),
        "workspace_type": ws_type,
        "visibility":     visibility or "private",
        "institution":    institution or "",
        "research_area":  research_area or "",
        "keywords":       keywords or [],
        "owner_id":       owner_id,
        "members":        members,
        "member_roles":   member_roles,
        "project_ids":    [project_id] if project_id else [],
        "status":         "active",
        "created_at":     now,
        "updated_at":     now,
    }
    res = await db.workspaces.insert_one(doc)
    doc["_id"] = res.inserted_id
    ws_id = str(res.inserted_id)

    # Auto-create workspace group conversation with every initial member
    try:
        conv_key = f"workspace:{ws_id}"
        cr = await db.conversations.insert_one({
            "type": "workspace", "context_id": ws_id, "context_key": conv_key,
            "title": doc["name"], "created_by": owner_id,
            "created_at": now, "last_message_at": now, "last_message_preview": "",
        })
        for mid in members:
            await db.conversation_members.insert_one({
                "conversation_id": str(cr.inserted_id), "user_id": mid,
                "role": "owner" if mid == owner_id else "member",
                "joined_at": now, "last_read_at": now, "muted": False,
            })
    except Exception as exc:
        logger.warning("workspace conversation create failed: %s", exc)

    await _log_activity(
        db, ws_id, owner_id, owner_name or "Someone",
        activity_message or f"Workspace created by {owner_name or 'Someone'}",
        kind="workspace_created",
    )
    return _ser(doc)
