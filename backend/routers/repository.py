from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Depends

from auth_utils import get_current_user
from db import get_db
from models import RepositoryItemCreate
from repo.shim import DBProxy
from repo.security_context import SecurityContext

router = APIRouter(prefix="/api/repository", tags=["repository"])


def _ser(d):
    if not d:
        return None
    x = dict(d)
    x["id"] = str(x.pop("_id"))
    return x


def _now():
    return datetime.now(timezone.utc).isoformat()


@router.get("")
async def list_items(
    item_type: Optional[str] = None,
    q: Optional[str] = None,
    project_id: Optional[str] = None,
    workspace_id: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    # Visible: items I own OR public items
    query = {"$or": [{"owner_id": user["id"]}, {"visibility": "public"}]}
    extra = {}
    if item_type:
        extra["type"] = item_type
    if q:
        extra["$or"] = [
            {"title": {"$regex": q, "$options": "i"}},
            {"description": {"$regex": q, "$options": "i"}},
            {"tags": {"$regex": q, "$options": "i"}},
        ]
    if project_id:
        extra["project_id"] = project_id
    if workspace_id:
        extra["workspace_id"] = workspace_id
    if extra:
        full_query = {"$and": [query, extra]}
    else:
        full_query = query
    docs = await db.repository_items.find(full_query).sort("created_at", -1).limit(200).to_list(200)
    return [_ser(d) for d in docs]


@router.post("")
async def create_item(payload: RepositoryItemCreate, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    doc = {
        "title": payload.title,
        "type": payload.type,  # Document | Dataset | Template | Literature
        "description": payload.description or "",
        "url": payload.url or "",
        "tags": payload.tags or [],
        "owner_id": user["id"],
        "owner_name": user.get("full_name", ""),
        "project_id": payload.project_id or "",
        "workspace_id": payload.workspace_id or "",
        "visibility": payload.visibility or "private",
        "created_at": _now(),
    }
    res = await db.repository_items.insert_one(doc)
    doc["_id"] = res.inserted_id
    return _ser(doc)


@router.get("/{item_id}")
async def get_item(item_id: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try:
        doc = await db.repository_items.find_one({"_id": ObjectId(item_id)})
    except Exception:
        raise HTTPException(status_code=404, detail="Not found")
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    if doc.get("visibility") != "public" and doc["owner_id"] != user["id"]:
        raise HTTPException(status_code=403, detail="Forbidden")
    return _ser(doc)
