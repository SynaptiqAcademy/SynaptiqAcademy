"""Runtime checks for admin-controlled platform-wide toggles.

Backed by the existing `feature_flags` collection (see routers/admin_operations.py
and routers/admin_expansion.py for the admin CRUD already exposed for it).
"""
from __future__ import annotations

REGISTRATION_FLAG = "public_registration"

REGISTRATION_CLOSED_MESSAGE = (
    "New account registration is temporarily closed while we finish rolling out "
    "billing. Please check back soon."
)


async def is_registration_open(db) -> bool:
    """True unless an admin has explicitly disabled public sign-up via the
    Feature Flags admin panel. Defaults to open if the flag was never set."""
    flag = await db.feature_flags.find_one({"name": REGISTRATION_FLAG})
    if flag is None:
        return True
    return bool(flag.get("enabled", True))
