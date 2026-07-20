"""
BaseRepository — the single parent class for every bounded-context repository.

Every create/update/delete automatically:
  1. Applies Row-Level Security  (via _scope_query / _assert_writable)
  2. Enforces soft-delete        (deleted_at instead of physical removal)
  3. Enforces optimistic concurrency (version field, $eq check on update)
  4. Writes an audit trail entry
  5. Emits a domain event
  6. Invalidates the relevant cache entry

Routers and services NEVER call db[collection] directly.
They receive a typed repository (MissionRepository, UserRepository, etc.)
and call its named methods.

Generic type T is the document dict (kept as dict for MongoDB compat).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Generic, TypeVar

from bson import ObjectId

from .audit      import AuditTrail
from .cache      import RepositoryCache, get_cache, get_cache_with_redis, DEFAULT_TTL, SHORT_TTL, LONG_TTL
from .events     import RepoEvent, RepoEventBus, get_event_bus  # kept for repo/__init__.py re-export
from .security_context import SecurityContext
from .specs      import QuerySpec

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=dict)


class RepositoryError(Exception):
    pass

class NotFoundError(RepositoryError):
    pass

class PermissionError(RepositoryError):
    pass

class ConflictError(RepositoryError):
    """Raised when optimistic concurrency check fails (stale version)."""
    pass


class BaseRepository(Generic[T]):
    """
    Base class for all bounded-context repositories.

    Subclasses must set:
        collection:   str           # MongoDB collection name
        event_prefix: str           # e.g. "mission", "publication"
        cache_ttl:    int           # seconds

    Subclasses may override:
        _scope_query(filters)       # add extra RLS filters
        _can_read(doc)              # per-document read check
        _can_write(doc)             # per-document write check
        _before_create(data)        # mutate data before insert
        _before_update(data)        # mutate updates before write
        _after_create(doc)          # emit events, side-effects
        _after_update(doc)          # emit events, side-effects
    """

    collection:   str = ""
    event_prefix: str = ""
    cache_ttl:    int = DEFAULT_TTL

    def __init__(self, db, ctx: SecurityContext) -> None:
        if not self.collection:
            raise NotImplementedError(f"{type(self).__name__} must set `collection`")

        # Unwrap DBProxy so BaseRepository uses raw motor collections directly.
        # BaseRepository manages its own timestamps and audit trail — using a
        # CollectionProxy here would double-enrich timestamps and double-audit.
        from .shim import _unwrap_db
        raw_db = _unwrap_db(db)

        self._db    = raw_db
        self._ctx   = ctx
        self._col   = raw_db[self.collection]
        self._audit = AuditTrail(raw_db)

        # Use Redis-backed cache when available for cross-replica cache sharing.
        # Access the module-level client directly (set at startup by init_redis())
        # to avoid async overhead in the synchronous __init__.
        try:
            from services.redis_client import _client as _redis
            self._cache = get_cache_with_redis(self.collection, _redis) if _redis else get_cache(self.collection)
        except Exception:
            self._cache = get_cache(self.collection)

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def ctx(self) -> SecurityContext:
        return self._ctx

    # ── Core CRUD ─────────────────────────────────────────────────────────────

    async def find_one(
        self,
        spec: QuerySpec | None = None,
        *,
        doc_id: str | None = None,
        include_deleted: bool = False,
        bypass_cache: bool = False,
        session=None,
    ) -> T | None:
        """
        Find a single document.

        - If doc_id is given, looks up by _id directly (with cache).
        - If spec is given, finds the first match.
        - Applies RLS + soft-delete filter automatically.
        """
        if doc_id:
            # Cache lookup first.
            # Key is user-scoped for non-admin contexts so cache never leaks
            # across user boundaries (e.g. user A's warm cache → user B's read).
            _scope = None if self._ctx.is_admin else self._ctx.user_id
            _doc_cache_key = self._cache.key_doc(doc_id) + (f":u:{_scope}" if _scope else "")
            if not bypass_cache:
                cached = await self._cache.get(_doc_cache_key)
                if cached is not None:
                    return cached if self._can_read(cached) else None

            try:
                oid = ObjectId(doc_id)
            except Exception:
                return None

            filt = self._scope_filter({"_id": oid}, include_deleted)
            doc  = await self._col.find_one(filt, session=session)

            if doc and not self._can_read(doc):
                return None
            if doc:
                serialized = _serialize(doc)
                if not bypass_cache:
                    await self._cache.set(_doc_cache_key, serialized, self.cache_ttl)
                return serialized
            return None

        if spec is None:
            spec = QuerySpec()

        filt = self._scope_filter(spec.filters, include_deleted)
        proj = spec.projection
        doc  = await self._col.find_one(filt, proj, session=session)

        if doc and not self._can_read(doc):
            return None
        return _serialize(doc) if doc else None

    async def find_many(
        self,
        spec: QuerySpec | None = None,
        *,
        include_deleted: bool = False,
        bypass_cache: bool = False,
        session=None,
    ) -> list[T]:
        """
        Find multiple documents matching spec.

        Results are RLS-filtered; deleted documents excluded unless requested.
        """
        if spec is None:
            spec = QuerySpec()

        # Cache key based on scoped query
        scope_hint = self._ctx.user_id if not self._ctx.is_super_admin else "admin"
        cache_key  = self._cache.key_query(
            {**spec.filters, "_scope": scope_hint},
            spec.sort, spec.limit, spec.skip,
        )
        if not bypass_cache:
            cached = await self._cache.get(cache_key)
            if cached is not None:
                return cached

        filt   = self._scope_filter(spec.filters, include_deleted)
        cursor = self._col.find(filt, spec.projection, session=session)

        if spec.sort:
            cursor = cursor.sort(spec.sort)
        if spec.skip:
            cursor = cursor.skip(spec.skip)
        cursor = cursor.limit(spec.limit)

        docs = await cursor.to_list(length=spec.limit)
        result = [_serialize(d) for d in docs if self._can_read(d)]

        if not bypass_cache:
            await self._cache.set(cache_key, result, self.cache_ttl)
        return result

    async def count(self, spec: QuerySpec | None = None, *, include_deleted: bool = False) -> int:
        if spec is None:
            spec = QuerySpec()
        filt = self._scope_filter(spec.filters, include_deleted)
        return await self._col.count_documents(filt)

    async def create(
        self,
        data: dict,
        *,
        skip_audit: bool = False,
        session=None,
    ) -> T:
        """Insert a new document with automatic metadata fields."""
        now = datetime.now(timezone.utc)
        doc = {
            **data,
            "user_id":    data.get("user_id") or self._ctx.user_id,
            "created_at": data.get("created_at") or now,
            "updated_at": now,
            "version":    1,
            "deleted_at": None,
        }
        if self._ctx.tenant_id and "tenant_id" not in doc:
            doc["tenant_id"] = self._ctx.tenant_id

        doc = await self._before_create(doc)

        result = await self._col.insert_one(doc, session=session)
        doc["_id"] = result.inserted_id
        serialized = _serialize(doc)

        # Audit
        if not skip_audit:
            self._audit.record(
                ctx=self._ctx,
                collection=self.collection,
                operation="create",
                doc_id=str(result.inserted_id),
                after=serialized,
            )

        # Cache
        await self._cache.set(
            self._cache.key_doc(str(result.inserted_id)),
            serialized,
            self.cache_ttl,
        )

        await self._after_create(serialized)
        return serialized

    async def update(
        self,
        doc_id: str,
        updates: dict,
        *,
        expected_version: int | None = None,
        skip_audit: bool = False,
        session=None,
    ) -> T:
        """
        Update a document by id.

        Raises ConflictError if expected_version is given and does not match
        (optimistic concurrency control).
        Raises NotFoundError if the document does not exist or is inaccessible.
        Raises PermissionError if the context cannot write this document.
        """
        existing = await self.find_one(doc_id=doc_id, bypass_cache=True, session=session)
        if not existing:
            raise NotFoundError(f"{self.collection}/{doc_id} not found")

        if not self._can_write(existing):
            raise PermissionError(f"Cannot write {self.collection}/{doc_id}")

        if expected_version is not None and existing.get("version") != expected_version:
            raise ConflictError(
                f"Version conflict: expected {expected_version}, "
                f"got {existing.get('version')} for {self.collection}/{doc_id}"
            )

        updates = await self._before_update(updates)

        now     = datetime.now(timezone.utc)
        set_doc = {
            **updates,
            "updated_at": now,
            "version":    (existing.get("version") or 0) + 1,
        }
        set_doc.pop("_id", None)
        set_doc.pop("created_at", None)

        filt: dict[str, Any] = {"_id": ObjectId(doc_id)}
        if expected_version is not None:
            filt["version"] = expected_version

        result = await self._col.find_one_and_update(
            filt,
            {"$set": set_doc},
            return_document=True,
            session=session,
        )
        if not result:
            raise ConflictError(f"Version conflict on {self.collection}/{doc_id}")

        serialized = _serialize(result)

        # Audit
        if not skip_audit:
            self._audit.record(
                ctx=self._ctx,
                collection=self.collection,
                operation="update",
                doc_id=doc_id,
                before=existing,
                after=serialized,
            )

        # Cache invalidation (clear both admin key and user-scoped key)
        await self._cache.invalidate(self._cache.key_doc(doc_id))
        await self._cache.invalidate(self._cache.key_doc(doc_id) + f":u:{existing.get('user_id', '')}")

        await self._after_update(serialized)
        return serialized

    async def delete(
        self,
        doc_id: str,
        *,
        hard: bool = False,
        session=None,
    ) -> bool:
        """
        Soft-delete by default (sets deleted_at).
        Pass hard=True only for irreversible purge (admin only).
        """
        existing = await self.find_one(doc_id=doc_id, bypass_cache=True, session=session)
        if not existing:
            raise NotFoundError(f"{self.collection}/{doc_id} not found")

        if not self._ctx.can_delete(self.collection):
            raise PermissionError(f"Cannot delete {self.collection}/{doc_id}")

        if hard:
            if not self._ctx.is_admin:
                raise PermissionError("Hard delete requires admin role")
            await self._col.delete_one({"_id": ObjectId(doc_id)}, session=session)
        else:
            now = datetime.now(timezone.utc)
            await self._col.update_one(
                {"_id": ObjectId(doc_id)},
                {"$set": {"deleted_at": now, "updated_at": now}},
                session=session,
            )

        # Audit
        self._audit.record(
            ctx=self._ctx,
            collection=self.collection,
            operation="delete" if hard else "soft_delete",
            doc_id=doc_id,
            before=existing,
        )

        # Cache invalidation
        await self._cache.invalidate(self._cache.key_doc(doc_id))

        return True

    async def restore(self, doc_id: str, *, session=None) -> T:
        """Un-delete a soft-deleted document."""
        if not self._ctx.is_admin:
            raise PermissionError("Restore requires admin role")

        doc = await self.find_one(doc_id=doc_id, include_deleted=True, bypass_cache=True, session=session)
        if not doc:
            raise NotFoundError(f"{self.collection}/{doc_id} not found")

        now = datetime.now(timezone.utc)
        result = await self._col.find_one_and_update(
            {"_id": ObjectId(doc_id)},
            {"$set": {"deleted_at": None, "updated_at": now}},
            return_document=True,
            session=session,
        )
        serialized = _serialize(result)

        self._audit.record(
            ctx=self._ctx,
            collection=self.collection,
            operation="restore",
            doc_id=doc_id,
            after=serialized,
        )

        await self._cache.invalidate(self._cache.key_doc(doc_id))
        return serialized

    async def upsert(
        self,
        filter_doc: dict,
        updates: dict,
        *,
        session=None,
    ) -> T:
        """Find-or-create pattern with automatic metadata."""
        now = datetime.now(timezone.utc)
        scoped = self._scope_filter(filter_doc, include_deleted=False)

        on_insert: dict[str, Any] = {
            "user_id":    self._ctx.user_id,
            "created_at": now,
            "deleted_at": None,
            "version":    1,
        }
        if self._ctx.tenant_id:
            on_insert["tenant_id"] = self._ctx.tenant_id

        result = await self._col.find_one_and_update(
            scoped,
            {
                "$set":         {**updates, "updated_at": now},
                "$setOnInsert": on_insert,
                "$inc":         {"version": 1},
            },
            upsert=True,
            return_document=True,
            session=session,
        )
        return _serialize(result)

    # ── Bulk ops ──────────────────────────────────────────────────────────────

    async def bulk_create(self, items: list[dict], *, session=None) -> list[str]:
        if not items:
            return []
        now = datetime.now(timezone.utc)
        docs = []
        for item in items:
            docs.append({
                **item,
                "user_id":    item.get("user_id") or self._ctx.user_id,
                "created_at": now,
                "updated_at": now,
                "version":    1,
                "deleted_at": None,
            })
        result = await self._col.insert_many(docs, session=session)
        return [str(oid) for oid in result.inserted_ids]

    # ── RLS hooks (override in subclasses) ────────────────────────────────────

    def _scope_filter(self, filters: dict, include_deleted: bool) -> dict:
        """
        Apply Row-Level Security + soft-delete to a filter dict.

        super_admin: no user scoping
        system:      no user scoping
        admin:       no user scoping, but still gets deleted filter
        researcher:  scoped to their user_id (or ownership pattern per subclass)
        """
        base = dict(filters)

        # Soft-delete
        if not include_deleted:
            base["deleted_at"] = None

        # Tenant isolation (enterprise)
        if self._ctx.tenant_id and not self._ctx.is_super_admin:
            if "tenant_id" not in base:
                base["tenant_id"] = self._ctx.tenant_id

        # User-scope (delegates to subclass)
        return self._scope_query(base)

    def _scope_query(self, filters: dict) -> dict:
        """
        Subclass hook: add user-specific scoping.

        Default: researchers see only their own documents.
        Admins / super_admins see everything.
        """
        if self._ctx.is_admin or self._ctx.user_id == "system":
            return filters
        filters["user_id"] = self._ctx.user_id
        return filters

    def _can_read(self, doc: dict) -> bool:
        """Per-document read check (default: allow if in result set)."""
        return True

    def _can_write(self, doc: dict) -> bool:
        """Per-document write check (default: owner or admin)."""
        if self._ctx.is_admin:
            return True
        return self._ctx.owns(doc)

    # ── Lifecycle hooks ───────────────────────────────────────────────────────

    async def _before_create(self, data: dict) -> dict:
        return data

    async def _before_update(self, updates: dict) -> dict:
        return updates

    async def _after_create(self, doc: T) -> None:
        if self.event_prefix:
            from events import get_bus
            from events.models import DomainEvent
            get_bus().publish_sync(DomainEvent(
                event_type=f"{self.event_prefix}.created",
                aggregate_id=doc.get("id", ""),
                aggregate_type=self.event_prefix,
                user_id=self._ctx.user_id,
                request_id=self._ctx.request_id,
                payload={"id": doc.get("id"), "user_id": doc.get("user_id")},
            ))

    async def _after_update(self, doc: T) -> None:
        if self.event_prefix:
            from events import get_bus
            from events.models import DomainEvent
            get_bus().publish_sync(DomainEvent(
                event_type=f"{self.event_prefix}.updated",
                aggregate_id=doc.get("id", ""),
                aggregate_type=self.event_prefix,
                user_id=self._ctx.user_id,
                request_id=self._ctx.request_id,
                payload={"id": doc.get("id"), "user_id": doc.get("user_id")},
            ))

    # ── Direct MongoDB escape hatch (last resort) ─────────────────────────────

    async def raw_find(self, filter_doc: dict, *, limit: int = 100, session=None) -> list[dict]:
        """
        Bypass RLS — for internal/system use ONLY.

        Do NOT call from routers or user-facing services.
        Call sites must be explicitly justified in code comments.
        """
        cursor = self._col.find(filter_doc, session=session).limit(limit)
        docs   = await cursor.to_list(length=limit)
        return [_serialize(d) for d in docs]

    async def raw_update_one(self, filter_doc: dict, update: dict, *, session=None) -> int:
        """Bypass RLS — system use ONLY."""
        result = await self._col.update_one(filter_doc, update, session=session)
        return result.modified_count

    async def raw_aggregate(self, pipeline: list[dict], *, session=None) -> list[dict]:
        """Bypass RLS — system use ONLY."""
        cursor = self._col.aggregate(pipeline, session=session)
        return await cursor.to_list(length=None)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _serialize(doc: dict | None) -> dict | None:
    if doc is None:
        return None
    out = dict(doc)
    if "_id" in out:
        out["id"]  = str(out["_id"])
        out["_id"] = str(out["_id"])
    return out
