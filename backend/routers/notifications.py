from datetime import datetime, timezone
from bson import ObjectId
from fastapi import APIRouter, Depends

from auth_utils import get_current_user
from db import get_db
from repo.shim import DBProxy
from repo.security_context import SecurityContext

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


def _ser(d):
    x = dict(d)
    x["id"] = str(x.pop("_id"))
    return x


@router.get("")
async def list_notifications(user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    docs = await db.notifications.find({"user_id": user["id"]}).sort("created_at", -1).limit(100).to_list(100)
    return [_ser(d) for d in docs]


@router.post("/{notification_id}/read")
async def mark_read(notification_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(notification_id)
    except Exception:
        return {"ok": False}
    await db.notifications.update_one(
        {"_id": oid, "user_id": user["id"]},
        {"$set": {"read": True}},
    )
    return {"ok": True}


@router.post("/read-all")
async def mark_all_read(user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    await db.notifications.update_many({"user_id": user["id"], "read": False}, {"$set": {"read": True}})
    return {"ok": True}


@router.delete("/{notification_id}")
async def delete_notification(notification_id: str, user: dict = Depends(get_current_user)):
    """Delete a single notification. Only the owner may delete their own notifications."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        oid = ObjectId(notification_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Not found")
    result = await db.notifications.delete_one({"_id": oid, "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


@router.delete("")
async def delete_read_notifications(user: dict = Depends(get_current_user)):
    """Delete all read notifications for the current user."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    result = await db.notifications.delete_many({"user_id": user["id"], "read": True})
    return {"ok": True, "deleted": result.deleted_count}
