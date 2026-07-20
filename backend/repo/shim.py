"""
DBProxy / CollectionProxy — transparent security shim for MongoDB access.

Wraps a motor database so every collection attribute returns a CollectionProxy
instead of a raw motor collection. CollectionProxy:

  - Enriches INSERT operations  → adds created_at, updated_at, _created_by
  - Enriches UPDATE operations  → adds updated_at to $set
  - Records audit entries       → fire-and-forget, never blocks the request
  - Returns REAL motor results  → InsertOneResult, UpdateResult, motor cursors
    so all calling code is unchanged after swapping get_db() → DBProxy(...)

Usage in routers:

    # authenticated endpoint
    db = DBProxy(get_db(), SecurityContext.from_user(user))

    # public / internal endpoint
    db = DBProxy(get_db(), SecurityContext.system())

    # All subsequent db.collection.method() calls are now proxied.
    doc = await db.users.find_one({"email": email})        # unchanged
    docs = await db.posts.find({}).sort("ts", -1).to_list(50)  # unchanged
    result = await db.items.insert_one(item)               # gets timestamps
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from .security_context import SecurityContext

log = logging.getLogger(__name__)

# Collections that are append-only audit / log tables — skip audit recursion
_AUDIT_EXEMPT = frozenset({
    "audit_log", "data_audit", "error_logs", "api_error_log", "email_log",
    "security_events", "session_events", "ai_usage_logs", "billing_events",
})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class CollectionProxy:
    """
    Drop-in replacement for a motor collection. Returns real motor types
    (cursors, InsertOneResult, etc.) so callers need zero changes.
    """

    __slots__ = ("_name", "_col", "_ctx")

    def __init__(self, name: str, motor_col: Any, ctx: Optional[SecurityContext]) -> None:
        object.__setattr__(self, "_name", name)
        object.__setattr__(self, "_col", motor_col)
        object.__setattr__(self, "_ctx", ctx)

    # ── Properties mirrored from motor ───────────────────────────────────────

    @property
    def name(self) -> str:
        return self._name

    @property
    def database(self):
        return self._col.database

    @property
    def full_name(self) -> str:
        return self._col.full_name

    # ── Read operations — pass through to motor unchanged ────────────────────

    async def find_one(self, filter_doc=None, projection=None, **kwargs):
        if projection is not None:
            return await self._col.find_one(filter_doc or {}, projection, **kwargs)
        return await self._col.find_one(filter_doc or {}, **kwargs)

    def find(self, filter_doc=None, projection=None, *args, **kwargs):
        """Returns a real motor cursor — .sort()/.limit()/.to_list() work natively."""
        if projection is not None:
            return self._col.find(filter_doc or {}, projection, *args, **kwargs)
        return self._col.find(filter_doc or {}, *args, **kwargs)

    def aggregate(self, pipeline, **kwargs):
        """Returns a real motor CommandCursor."""
        return self._col.aggregate(pipeline, **kwargs)

    async def count_documents(self, filter_doc=None, **kwargs):
        return await self._col.count_documents(filter_doc or {}, **kwargs)

    async def estimated_document_count(self, **kwargs):
        return await self._col.estimated_document_count(**kwargs)

    async def distinct(self, key: str, filter_doc=None, **kwargs):
        return await self._col.distinct(key, filter_doc, **kwargs)

    async def find_one_and_delete(self, filter_doc, **kwargs):
        result = await self._col.find_one_and_delete(filter_doc, **kwargs)
        self._audit_fire("delete", str(filter_doc))
        return result

    # ── Write operations — enrich then delegate to motor ────────────────────

    async def insert_one(self, doc: dict, **kwargs):
        enriched = self._enrich_create(doc)
        result = await self._col.insert_one(enriched, **kwargs)
        self._audit_fire("create", str(result.inserted_id))
        return result

    async def insert_many(self, docs: list, **kwargs):
        enriched = [self._enrich_create(d) for d in docs]
        return await self._col.insert_many(enriched, **kwargs)

    async def update_one(self, filter_doc, update, **kwargs):
        self._enrich_update(update)
        result = await self._col.update_one(filter_doc, update, **kwargs)
        self._audit_fire("update", str(filter_doc))
        return result

    async def update_many(self, filter_doc, update, **kwargs):
        self._enrich_update(update)
        return await self._col.update_many(filter_doc, update, **kwargs)

    async def find_one_and_update(self, filter_doc, update, **kwargs):
        self._enrich_update(update)
        result = await self._col.find_one_and_update(filter_doc, update, **kwargs)
        self._audit_fire("update", str(filter_doc))
        return result

    async def find_one_and_replace(self, filter_doc, replacement, **kwargs):
        return await self._col.find_one_and_replace(filter_doc, replacement, **kwargs)

    async def replace_one(self, filter_doc, replacement, **kwargs):
        result = await self._col.replace_one(filter_doc, replacement, **kwargs)
        self._audit_fire("replace", str(filter_doc))
        return result

    async def delete_one(self, filter_doc, **kwargs):
        result = await self._col.delete_one(filter_doc, **kwargs)
        self._audit_fire("delete", str(filter_doc))
        return result

    async def delete_many(self, filter_doc, **kwargs):
        return await self._col.delete_many(filter_doc, **kwargs)

    async def bulk_write(self, requests, **kwargs):
        return await self._col.bulk_write(requests, **kwargs)

    # ── Index / admin ops — transparent passthrough ──────────────────────────

    async def create_index(self, keys, **kwargs):
        return await self._col.create_index(keys, **kwargs)

    async def create_indexes(self, indexes, **kwargs):
        return await self._col.create_indexes(indexes, **kwargs)

    async def drop_index(self, index_or_name, **kwargs):
        return await self._col.drop_index(index_or_name, **kwargs)

    async def drop(self, **kwargs):
        return await self._col.drop(**kwargs)

    async def index_information(self):
        return await self._col.index_information()

    async def options(self):
        return await self._col.options()

    async def rename(self, new_name: str, **kwargs):
        return await self._col.rename(new_name, **kwargs)

    # ── Internal enrichment ──────────────────────────────────────────────────

    def _enrich_create(self, doc: dict) -> dict:
        """Add standard metadata fields to a new document."""
        now = _now()
        enriched = dict(doc)
        enriched.setdefault("created_at", now)
        enriched.setdefault("updated_at", now)
        ctx = self._ctx
        if ctx and ctx.user_id and ctx.user_id != "system":
            enriched.setdefault("_created_by", ctx.user_id)
        return enriched

    def _enrich_update(self, update: dict) -> None:
        """Inject updated_at into $set if present; mutates in-place."""
        now = _now()
        if "$set" in update:
            update["$set"].setdefault("updated_at", now)
        elif "$unset" in update or "$push" in update or "$pull" in update or "$inc" in update or "$addToSet" in update:
            # Operator update without $set — add $set for timestamp
            update.setdefault("$set", {})["updated_at"] = now
        # Replacement-style (no operators): add directly
        elif not any(k.startswith("$") for k in update):
            update.setdefault("updated_at", now)

    def _audit_fire(self, operation: str, ref: str) -> None:
        """Fire-and-forget audit entry — never raises, never blocks the caller."""
        if self._name in _AUDIT_EXEMPT:
            return
        ctx = self._ctx

        async def _write() -> None:
            try:
                await self._col.database.audit_log.insert_one({
                    "_source":      "shim",
                    "_collection":  self._name,
                    "_operation":   operation,
                    "_ref":         ref[:200],
                    "_user_id":     ctx.user_id if ctx else None,
                    "_institution": ctx.institution if ctx else None,
                    "_request_id":  ctx.request_id if ctx else None,
                    "_ts":          _now(),
                })
            except Exception:
                pass  # audit must never fail the request

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(_write())
        except RuntimeError:
            pass  # no event loop — skip (e.g. during startup index creation)


class DBProxy:
    """
    Wraps a motor AsyncIOMotorDatabase; every attribute access returns a
    CollectionProxy instead of a raw motor collection.

        db = DBProxy(get_db(), SecurityContext.from_user(user))
        doc = await db.users.find_one({"email": e})   # same API as before

    Database-level operations (list_collection_names, command, etc.) are
    forwarded to the underlying motor database unchanged.
    """

    __slots__ = ("_db", "_ctx", "_cache")

    def __init__(self, db, ctx: Optional[SecurityContext] = None) -> None:
        # Unwrap an existing DBProxy so we never double-wrap the motor database
        raw = object.__getattribute__(db, "_db") if isinstance(db, DBProxy) else db
        object.__setattr__(self, "_db", raw)
        object.__setattr__(self, "_ctx", ctx)
        object.__setattr__(self, "_cache", {})

    def __getattr__(self, name: str) -> CollectionProxy:
        if name.startswith("_"):
            raise AttributeError(name)
        cache = object.__getattribute__(self, "_cache")
        if name not in cache:
            db = object.__getattribute__(self, "_db")
            ctx = object.__getattribute__(self, "_ctx")
            cache[name] = CollectionProxy(name, db[name], ctx)
        return cache[name]

    def __getitem__(self, name: str) -> CollectionProxy:
        return self.__getattr__(name)

    # ── Database-level pass-through ──────────────────────────────────────────

    async def list_collection_names(self, **kwargs):
        return await self._db.list_collection_names(**kwargs)

    async def command(self, command, **kwargs):
        return await self._db.command(command, **kwargs)

    async def validate_collection(self, name_or_col, **kwargs):
        return await self._db.validate_collection(name_or_col, **kwargs)

    async def create_collection(self, name: str, **kwargs):
        return await self._db.create_collection(name, **kwargs)

    async def drop_collection(self, name_or_col, **kwargs):
        return await self._db.drop_collection(name_or_col, **kwargs)

    @property
    def name(self) -> str:
        return self._db.name

    @property
    def client(self):
        return self._db.client

    @property
    def codec_options(self):
        return self._db.codec_options


# ── Helpers ───────────────────────────────────────────────────────────────────

def _unwrap_db(db):
    """Return the raw motor database, stripping any DBProxy wrapper."""
    if isinstance(db, DBProxy):
        return object.__getattribute__(db, "_db")
    return db


# ── Convenience factory ───────────────────────────────────────────────────────

def make_db_proxy(db, user: dict | None = None, *, system: bool = False) -> DBProxy:
    """
    Build a DBProxy from a motor database and an optional user dict.

        db = make_db_proxy(get_db(), user)           # authenticated
        db = make_db_proxy(get_db(), system=True)    # worker / internal
    """
    if system or user is None:
        ctx = SecurityContext.system()
    else:
        ctx = SecurityContext.from_user(user)
    return DBProxy(db, ctx)
