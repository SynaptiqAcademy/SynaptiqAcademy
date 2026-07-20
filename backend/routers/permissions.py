"""Permission introspection endpoints — used by frontend to render gates.

These endpoints are read-only and inexpensive; the frontend hits them on app
load + after subscription changes to refresh its in-memory feature cache.
"""
from fastapi import APIRouter, Depends

from auth_utils import get_current_user
from services.permissions import access_summary, is_super_admin

router = APIRouter(prefix="/api/permissions", tags=["permissions"])


@router.get("/me")
async def my_permissions(user: dict = Depends(get_current_user)):
    """Returns the full access map for the current user."""
    return await access_summary(user)


@router.get("/can/{feature}")
async def can_access(feature: str, user: dict = Depends(get_current_user)):
    """Soft check for a single feature key. Always returns 200 with a boolean."""
    from plans_catalogue import FEATURE_MIN_PLAN
    from services.permissions import has_plan_at_least
    required = FEATURE_MIN_PLAN.get(feature, "free")
    allowed = is_super_admin(user) or has_plan_at_least(user, required)
    return {
        "feature": feature,
        "allowed": allowed,
        "required_plan": required,
        "current_plan": user.get("plan_code") or "free",
    }
