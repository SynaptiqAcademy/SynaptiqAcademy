"""Discovery preferences: the member's Network Settings choices, applied to
the field every discovery surface filters on (`users.profile_visibility`;
see routers/discover.py, routers/researchers.py, routers/users.py,
routers/public_profiles.py).

Visibility choices (Network → Network Settings):

  Public   visible on the public research page, the directory and discovery
           (subject to the other rules: discovery switch, blocking).
  Network  "visible to group/community members only": excluded from every
           general surface above; shown only in Network discovery, and only to
           members who share a group or community with them
           (network_visible_to + discovery_engine.search_people).
  Private  excluded everywhere; no public page.

The user record therefore carries "private" for Network and Private choices
(the general surfaces only ever need "not public"); the member's actual
choice stays in network_settings.
"""
from __future__ import annotations


def discovery_visibility(settings: dict) -> str:
    """The value stored on the user record, read by every general surface."""
    if (settings or {}).get("show_in_discovery") is False:
        return "private"
    value = (settings or {}).get("profile_visibility") or "public"
    if value in ("network", "private"):
        return "private"
    return "public"


async def network_visible_to(db, viewer_id: str | None) -> list[str]:
    """Members who chose Network visibility and share a group or community
    with the viewer: the only people a Network member is visible to."""
    if not viewer_id:
        return []
    group_ids = [m["group_id"] async for m in db.network_group_members.find({"user_id": viewer_id}, {"group_id": 1})]
    comm_ids = [m["community_id"] async for m in db.network_community_members.find({"user_id": viewer_id}, {"community_id": 1})]
    co: set[str] = set()
    if group_ids:
        async for m in db.network_group_members.find({"group_id": {"$in": group_ids}}, {"user_id": 1}):
            co.add(m["user_id"])
    if comm_ids:
        async for m in db.network_community_members.find({"community_id": {"$in": comm_ids}}, {"user_id": 1}):
            co.add(m["user_id"])
    co.discard(viewer_id)
    if not co:
        return []
    return [s["user_id"] async for s in db.network_settings.find(
        {"user_id": {"$in": list(co)}, "profile_visibility": "network", "show_in_discovery": {"$ne": False}},
        {"user_id": 1})]


async def sync_all(db) -> int:
    """Apply every saved Network Settings choice to the user record.
    Idempotent; run daily by services/cleanup_service.py."""
    from bson import ObjectId
    n = 0
    async for s in db.network_settings.find({}, {"user_id": 1, "profile_visibility": 1, "show_in_discovery": 1}):
        try:
            oid = ObjectId(s["user_id"])
        except Exception:
            continue
        want = discovery_visibility(s)
        res = await db.users.update_one({"_id": oid, "profile_visibility": {"$ne": want}},
                                        {"$set": {"profile_visibility": want}})
        n += res.modified_count
    return n
