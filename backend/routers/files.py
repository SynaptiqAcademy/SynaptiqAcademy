"""Research File Layer — uploads/downloads/versioning/permissions/activity.

Files belong to a workspace | project | manuscript (entity_kind+entity_id).
Permissions inherit from the parent entity's membership. Versions chain via
`root_id` so we keep the upload history without forking the entity identity.

Storage: Emergent Object Storage via services/storage_service.py.
"""
from __future__ import annotations
import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Literal, Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, Response, Query
from fastapi.responses import StreamingResponse
import io

from auth_utils import get_current_user
from db import get_db
from services import storage_service as S
from services.audit import write_audit
from services.permissions import assert_storage_quota, is_super_admin
from repo.shim import DBProxy
from repo.security_context import SecurityContext
from zt.deps import zt_check, zt_is_admin, zt_is_super_admin

router = APIRouter(prefix="/api/files", tags=["files"])
log = logging.getLogger("synaptiq.files")

# Allowed types — per user spec.
ALLOWED_MIME = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
    "application/msword": "doc",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
    "application/vnd.ms-excel": "xls",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "application/vnd.ms-powerpoint": "ppt",
    "text/csv": "csv",
    "application/zip": "zip",
    "application/x-zip-compressed": "zip",
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/webp": "webp",
    "image/gif": "gif",
    # SVG intentionally excluded — can embed <script> tags (stored XSS)
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


def _now() -> str: return datetime.now(timezone.utc).isoformat()


async def _resolve_entity_members(entity_kind: str, entity_id: str) -> tuple[Optional[dict], list[str]]:
    """Return (entity_doc, member_user_ids) — covers schema variations."""
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    try: oid = ObjectId(entity_id)
    except Exception: return None, []
    coll = {"workspace": "workspaces", "project": "projects", "manuscript": "manuscripts"}.get(entity_kind)
    if not coll: return None, []
    d = await db[coll].find_one({"_id": oid})
    if not d: return None, []
    members = set(d.get("member_ids") or []) | set(d.get("team") or []) | set(d.get("author_ids") or [])
    if d.get("owner_id"): members.add(d["owner_id"])
    if d.get("created_by"): members.add(d["created_by"])
    return d, list(members)


async def _check_access(entity_kind: str, entity_id: str, user: dict, *, write: bool = False) -> dict:
    d, members = await _resolve_entity_members(entity_kind, entity_id)
    if not d: raise HTTPException(404, "Entity not found")
    if zt_is_admin(user):
        if user["id"] not in members:
            await write_audit(
                actor=user,
                action="admin_file_entity_access",
                entity_kind=entity_kind, entity_id=entity_id,
                metadata={"write": write, "role": user.get("role")},
            )
        return d
    if user["id"] not in members: raise HTTPException(403, "No access to this entity")
    return d


async def _can_read_file(d: dict, user: dict) -> bool:
    """True if user can read this file — either via entity membership OR because
    the file is attached to an open expertise_request the user can see."""
    if zt_is_admin(user):
        _, members = await _resolve_entity_members(d["entity_kind"], d["entity_id"])
        if user["id"] not in members:
            await write_audit(
                actor=user,
                action="admin_file_read_bypass",
                entity_kind=d.get("entity_kind", ""), entity_id=str(d.get("_id", "")),
                metadata={"filename": d.get("filename"), "role": user.get("role")},
            )
        return True
    _, members = await _resolve_entity_members(d["entity_kind"], d["entity_id"])
    if user["id"] in members: return True
    # Attached to an open expertise_request? (Public read for marketplace context.)
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    fid_str = str(d.get("_id") or "")
    if not fid_str: return False
    hit = await db.expertise_requests.find_one(
        {"attached_file_ids": fid_str, "status": "open"}, {"_id": 1})
    return bool(hit)


async def _log_activity(file_id: str, actor_id: str, action: str, *, metadata: Optional[dict] = None):
    db = get_db()
    db = DBProxy(db, SecurityContext.system())

    await db.file_activity.insert_one({
        "file_id": file_id, "actor_id": actor_id, "action": action,
        "metadata": metadata or {}, "created_at": _now(),
    })


# =============================== UPLOAD =====================================
@router.post("/upload")
async def upload(
    entity_kind: Literal["workspace", "project", "manuscript"] = Form(...),
    entity_id: str = Form(...),
    description: Optional[str] = Form(None),
    replaces_id: Optional[str] = Form(None),  # set when uploading a new version
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
):
    await _check_access(entity_kind, entity_id, user, write=True)
    if file.content_type not in ALLOWED_MIME:
        raise HTTPException(415, f"Unsupported file type: {file.content_type}")

    data = await file.read()
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(413, f"File exceeds {MAX_FILE_SIZE//1024//1024} MB limit")
    await assert_storage_quota(user, len(data))
    sha = hashlib.sha256(data).hexdigest()
    ext = ALLOWED_MIME[file.content_type]
    storage_path = S.build_path(user["id"], ext)
    try:
        S.put_object(storage_path, data, file.content_type)
    except Exception as e:
        log.error("Storage upload failed: %s", e)
        raise HTTPException(502, f"Storage upload failed: {str(e)[:200]}")

    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    # Version chain
    root_id = None; version = 1
    if replaces_id:
        try: prev_oid = ObjectId(replaces_id)
        except Exception: raise HTTPException(400, "Invalid replaces_id")
        prev = await db.files.find_one({"_id": prev_oid})
        if not prev: raise HTTPException(404, "Previous version not found")
        root_id = prev.get("root_id") or str(prev_oid)
        # latest version in chain
        latest = await db.files.find({"root_id": root_id}).sort("version", -1).limit(1).to_list(1)
        version = (latest[0]["version"] + 1) if latest else 2

    doc = {
        "entity_kind": entity_kind, "entity_id": entity_id,
        "filename":    file.filename or f"upload.{ext}",
        "ext":         ext, "mime": file.content_type,
        "size_bytes":  len(data),
        "sha256":      sha,
        "owner_id":    user["id"],
        "storage_path": storage_path,
        "description": description,
        "root_id":     root_id,
        "version":     version,
        "is_latest":   True,
        "created_at":  _now(), "updated_at": _now(),
    }
    r = await db.files.insert_one(doc)
    fid = str(r.inserted_id)
    if not root_id:
        # Self-rooted (first version)
        await db.files.update_one({"_id": r.inserted_id}, {"$set": {"root_id": fid}})
        doc["root_id"] = fid
    else:
        # Mark previous latest as not-latest
        await db.files.update_many(
            {"root_id": root_id, "_id": {"$ne": r.inserted_id}},
            {"$set": {"is_latest": False}}
        )
    doc.pop("_id", None)
    doc["id"] = fid
    await _log_activity(fid, user["id"],
                         "upload" if not replaces_id else "version",
                         metadata={"filename": doc["filename"], "version": version})
    return doc


# =============================== LIST =======================================
@router.get("")
async def list_files(
    entity_kind: Optional[Literal["workspace","project","manuscript"]] = None,
    entity_id: Optional[str] = None,
    owner_id: Optional[str] = None,
    include_versions: bool = False,
    limit: int = 100,
    user: dict = Depends(get_current_user),
):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    qf: dict = {}
    if entity_kind and entity_id:
        await _check_access(entity_kind, entity_id, user)
        qf["entity_kind"] = entity_kind
        qf["entity_id"] = entity_id
        if not include_versions: qf["is_latest"] = True
    elif owner_id:
        if owner_id != user["id"]:
            raise HTTPException(403, "Forbidden")
        qf["owner_id"] = owner_id
        if not include_versions: qf["is_latest"] = True
    else:
        # No filter → only owner's files
        qf["owner_id"] = user["id"]
        if not include_versions: qf["is_latest"] = True
    docs = await db.files.find(qf).sort("created_at", -1).limit(limit).to_list(limit)
    out = []
    for d in docs:
        d["id"] = str(d.pop("_id"))
        out.append(d)
    return out


@router.get("/recent")
async def recent_files(limit: int = 10, user: dict = Depends(get_current_user)):
    """Files in entities the user is a member of, most recent first."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    # Find entities user belongs to (cheap union across workspaces/projects/manuscripts).
    ws = await db.workspaces.find(
        {"$or": [{"member_ids": user["id"]}, {"owner_id": user["id"]}]}, {"_id": 1}
    ).to_list(500)
    proj = await db.projects.find(
        {"$or": [{"member_ids": user["id"]}, {"owner_id": user["id"]}]}, {"_id": 1}
    ).to_list(500)
    manus = await db.manuscripts.find({"authors": user["id"]}, {"_id": 1}).to_list(500)
    ws_ids = [str(x["_id"]) for x in ws]
    proj_ids = [str(x["_id"]) for x in proj]
    manus_ids = [str(x["_id"]) for x in manus]
    or_clauses = []
    if ws_ids:    or_clauses.append({"entity_kind": "workspace",  "entity_id": {"$in": ws_ids}})
    if proj_ids:  or_clauses.append({"entity_kind": "project",    "entity_id": {"$in": proj_ids}})
    if manus_ids: or_clauses.append({"entity_kind": "manuscript", "entity_id": {"$in": manus_ids}})
    if not or_clauses: return []
    docs = await db.files.find({"$or": or_clauses, "is_latest": True}) \
        .sort("created_at", -1).limit(limit).to_list(limit)
    for d in docs: d["id"] = str(d.pop("_id"))
    return docs


# =============================== DETAIL / DOWNLOAD ==========================
@router.get("/{fid}")
async def get_file_meta(fid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try: oid = ObjectId(fid)
    except Exception: raise HTTPException(404, "Not found")
    d = await db.files.find_one({"_id": oid})
    if not d: raise HTTPException(404, "Not found")
    await _check_access(d["entity_kind"], d["entity_id"], user)
    d["id"] = str(d.pop("_id"))
    return d


@router.get("/{fid}/versions")
async def file_versions(fid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try: oid = ObjectId(fid)
    except Exception: raise HTTPException(404, "Not found")
    d = await db.files.find_one({"_id": oid})
    if not d: raise HTTPException(404, "Not found")
    await _check_access(d["entity_kind"], d["entity_id"], user)
    chain = await db.files.find({"root_id": d.get("root_id") or fid}) \
        .sort("version", -1).to_list(50)
    for c in chain: c["id"] = str(c.pop("_id"))
    return chain


@router.get("/{fid}/activity")
async def file_activity(fid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try: oid = ObjectId(fid)
    except Exception: raise HTTPException(404, "Not found")
    d = await db.files.find_one({"_id": oid})
    if not d: raise HTTPException(404, "Not found")
    await _check_access(d["entity_kind"], d["entity_id"], user)
    # Activity events for entire chain
    root = d.get("root_id") or fid
    chain = await db.files.find({"root_id": root}, {"_id": 1}).to_list(50)
    fids = [str(x["_id"]) for x in chain]
    rows = await db.file_activity.find({"file_id": {"$in": fids}}) \
        .sort("created_at", -1).limit(50).to_list(50)
    actor_ids = list({r.get("actor_id") for r in rows if r.get("actor_id")})
    udocs = await db.users.find({"_id": {"$in": [ObjectId(u) for u in actor_ids]}},
                                 {"full_name": 1}).to_list(len(actor_ids)) if actor_ids else []
    name_by_id = {str(u["_id"]): u.get("full_name") for u in udocs}
    out = []
    for r in rows:
        r["id"] = str(r.pop("_id"))
        r["actor_name"] = name_by_id.get(r.get("actor_id"))
        out.append(r)
    return out


@router.get("/{fid}/download")
async def download(fid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try: oid = ObjectId(fid)
    except Exception: raise HTTPException(404, "Not found")
    d = await db.files.find_one({"_id": oid})
    if not d: raise HTTPException(404, "Not found")
    if not await _can_read_file(d, user): raise HTTPException(403, "No access")
    try:
        data, ctype = S.get_object(d["storage_path"])
    except Exception as e:
        raise HTTPException(502, f"Storage fetch failed: {str(e)[:200]}")
    await _log_activity(fid, user["id"], "download")
    return StreamingResponse(
        io.BytesIO(data),
        media_type=ctype or d.get("mime") or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{d.get("filename","file")}"',
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/{fid}/preview")
async def preview(fid: str, user: dict = Depends(get_current_user)):
    """Inline-rendered file content (browser-friendly). Used by the preview drawer."""
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try: oid = ObjectId(fid)
    except Exception: raise HTTPException(404, "Not found")
    d = await db.files.find_one({"_id": oid})
    if not d: raise HTTPException(404, "Not found")
    if not await _can_read_file(d, user): raise HTTPException(403, "No access")
    if d["ext"] not in ("pdf", "png", "jpg", "jpeg", "webp", "gif", "csv", "txt", "md", "json"):
        raise HTTPException(415, "Preview not supported for this file type")
    try:
        data, ctype = S.get_object(d["storage_path"])
    except Exception as e:
        raise HTTPException(502, f"Storage fetch failed: {str(e)[:200]}")
    await _log_activity(fid, user["id"], "preview")
    return StreamingResponse(
        io.BytesIO(data),
        media_type=ctype or d.get("mime") or "application/octet-stream",
        headers={
            "Content-Disposition": f'inline; filename="{d.get("filename","file")}"',
            "Cache-Control": "private, max-age=300",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; img-src data:; style-src 'unsafe-inline'",
        },
    )


@router.get("/{fid}/preview-csv")
async def preview_csv(fid: str, rows: int = Query(100, le=500),
                       user: dict = Depends(get_current_user)):
    """Return the first N rows of a CSV/TSV as a JSON grid for in-browser tables."""
    import csv
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try: oid = ObjectId(fid)
    except Exception: raise HTTPException(404, "Not found")
    d = await db.files.find_one({"_id": oid})
    if not d: raise HTTPException(404, "Not found")
    if not await _can_read_file(d, user): raise HTTPException(403, "No access")
    if d["ext"] not in ("csv", "tsv", "txt"):
        raise HTTPException(415, "CSV preview not supported for this file type")
    try:
        data, _ = S.get_object(d["storage_path"])
    except Exception as e:
        raise HTTPException(502, f"Storage fetch failed: {str(e)[:200]}")
    try:
        text = data.decode("utf-8", errors="replace")
    except Exception:
        text = data.decode("latin-1", errors="replace")
    delim = "\t" if (d["ext"] == "tsv" or "\t" in text[:200]) else ","
    reader = csv.reader(text.splitlines(), delimiter=delim)
    out_rows: list[list] = []
    headers: list[str] = []
    for i, row in enumerate(reader):
        if i == 0: headers = row
        else: out_rows.append(row)
        if len(out_rows) >= rows: break
    return {"headers": headers, "rows": out_rows, "delimiter": delim,
            "total_preview_rows": len(out_rows), "truncated": True}


# =============================== DELETE / METADATA ==========================
@router.delete("/{fid}")
async def delete_file(fid: str, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try: oid = ObjectId(fid)
    except Exception: raise HTTPException(404, "Not found")
    d = await db.files.find_one({"_id": oid})
    if not d: raise HTTPException(404, "Not found")
    await _check_access(d["entity_kind"], d["entity_id"], user, write=True)
    is_owner = d["owner_id"] == user["id"]
    is_priv = zt_is_admin(user)
    if not is_owner and not is_priv:
        raise HTTPException(403, "Only the uploader (or admin) can delete")
    if not is_owner and is_priv:
        await write_audit(
            actor=user,
            action="admin_file_delete",
            entity_kind=d.get("entity_kind", ""), entity_id=fid,
            target_user_id=d.get("owner_id"),
            before={"filename": d.get("filename"), "size_bytes": d.get("size_bytes")},
            metadata={"role": user.get("role")},
        )
    await db.files.delete_one({"_id": oid})
    await _log_activity(fid, user["id"], "delete", metadata={"filename": d.get("filename")})
    # Promote previous version to latest if any
    if d.get("is_latest") and d.get("root_id"):
        prev = await db.files.find({"root_id": d["root_id"], "_id": {"$ne": oid}}) \
            .sort("version", -1).limit(1).to_list(1)
        if prev:
            await db.files.update_one({"_id": prev[0]["_id"]}, {"$set": {"is_latest": True}})
    return {"ok": True}


from pydantic import BaseModel
class MetadataPatch(BaseModel):
    description: Optional[str] = None
    filename: Optional[str] = None


@router.patch("/{fid}")
async def patch_metadata(fid: str, payload: MetadataPatch, user: dict = Depends(get_current_user)):
    db = get_db()
    db = DBProxy(db, SecurityContext.from_user(user))

    try: oid = ObjectId(fid)
    except Exception: raise HTTPException(404, "Not found")
    d = await db.files.find_one({"_id": oid})
    if not d: raise HTTPException(404, "Not found")
    await _check_access(d["entity_kind"], d["entity_id"], user, write=True)
    update = {k: v for k, v in payload.model_dump(exclude_unset=True).items() if v is not None}
    if not update: return {"ok": True}
    update["updated_at"] = _now()
    await db.files.update_one({"_id": oid}, {"$set": update})
    await _log_activity(fid, user["id"], "rename" if "filename" in update else "edit",
                         metadata=update)
    d2 = await db.files.find_one({"_id": oid})
    d2["id"] = str(d2.pop("_id"))
    return d2
