"""Discovery preferences: the member's Network Settings choices, applied to
the field every discovery surface filters on (`users.profile_visibility`;
see routers/discover.py, routers/researchers.py, routers/users.py,
routers/public_profiles.py).

A member is excluded from those surfaces when they chose "Private" or turned
off "Show my profile in researcher discovery".
"""
from __future__ import annotations


def discovery_visibility(settings: dict) -> str:
    if (settings or {}).get("show_in_discovery") is False:
        return "private"
    value = (settings or {}).get("profile_visibility") or "public"
    return value if value in ("public", "network", "private") else "public"


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
