"""
Repository Layer — integration tests.

No real MongoDB. Uses in-memory MockDB that mirrors motor's async API.
Tests run with plain asyncio.run() (no pytest-asyncio required).
"""
import asyncio
import sys
import os
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from repo.security_context import SecurityContext, _institution_to_tenant
from repo.specs            import QuerySpec, Specs
from repo.cache            import InProcessCache, RepositoryCache, clear_all_caches
from repo.audit            import AuditTrail, _diff
from repo.events           import RepoEvent, RepoEventBus
from repo.base             import (
    BaseRepository, NotFoundError, PermissionError, ConflictError, _serialize
)


# ── In-memory test doubles ────────────────────────────────────────────────────

class MockCursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, *args, **kwargs):
        return self

    def skip(self, n):
        self._docs = self._docs[n:]
        return self

    def limit(self, n):
        self._docs = self._docs[:n]
        return self

    async def to_list(self, length=None):
        return self._docs[:length] if length else self._docs


class MockCollection:
    def __init__(self, name="test"):
        self.name = name
        self._docs: dict = {}
        self._id_seq = 0

    def _next_id(self):
        from bson import ObjectId
        return ObjectId()

    def find(self, filt=None, projection=None, session=None):
        docs = self._match(filt or {})
        return MockCursor(docs)

    async def find_one(self, filt=None, projection=None, session=None):
        docs = self._match(filt or {})
        return docs[0] if docs else None

    async def insert_one(self, doc, session=None):
        from bson import ObjectId
        oid = doc.get("_id") or self._next_id()
        doc["_id"] = oid
        self._docs[str(oid)] = dict(doc)
        result = MagicMock()
        result.inserted_id = oid
        return result

    async def insert_many(self, docs, session=None):
        ids = []
        for doc in docs:
            r = await self.insert_one(doc)
            ids.append(r.inserted_id)
        result = MagicMock()
        result.inserted_ids = ids
        return result

    async def find_one_and_update(self, filt, update, return_document=True, upsert=False, session=None):
        docs = self._match(filt)
        if not docs:
            if upsert:
                new_doc: dict = {}
                if "$set" in update:
                    new_doc.update(update["$set"])
                if "$setOnInsert" in update:
                    new_doc.update(update["$setOnInsert"])
                r = await self.insert_one(new_doc)
                return self._docs[str(r.inserted_id)]
            return None
        doc = docs[0]
        key = str(doc["_id"])
        if "$set" in update:
            self._docs[key].update(update["$set"])
        if "$inc" in update:
            for k, v in update["$inc"].items():
                self._docs[key][k] = self._docs[key].get(k, 0) + v
        return dict(self._docs[key])

    async def update_one(self, filt, update, session=None):
        docs = self._match(filt)
        count = 0
        for doc in docs[:1]:
            key = str(doc["_id"])
            if "$set" in update:
                self._docs[key].update(update["$set"])
            count += 1
        result = MagicMock()
        result.modified_count = count
        return result

    async def update_many(self, filt, update, session=None):
        docs = self._match(filt)
        for doc in docs:
            key = str(doc["_id"])
            if "$set" in update:
                self._docs[key].update(update["$set"])
        result = MagicMock()
        result.modified_count = len(docs)
        return result

    async def delete_one(self, filt, session=None):
        docs = self._match(filt)
        for doc in docs[:1]:
            self._docs.pop(str(doc["_id"]), None)
        result = MagicMock()
        result.deleted_count = min(1, len(docs))
        return result

    async def count_documents(self, filt):
        return len(self._match(filt))

    def aggregate(self, pipeline, session=None):
        # Simplified: only handle $group by status
        docs = list(self._docs.values())
        for stage in pipeline:
            if "$group" in stage:
                group = stage["$group"]
                by_field = group["_id"].lstrip("$")
                counts: dict = {}
                for doc in docs:
                    val = doc.get(by_field)
                    counts[val] = counts.get(val, 0) + 1
                docs = [{"_id": k, "count": v} for k, v in counts.items()]
        return MockCursor(docs)

    def _match(self, filt: dict) -> list:
        results = []
        for doc in self._docs.values():
            if self._doc_matches(doc, filt):
                results.append(dict(doc))
        return results

    def _doc_matches(self, doc: dict, filt: dict) -> bool:
        from bson import ObjectId
        for k, v in filt.items():
            if k == "$and":
                if not all(self._doc_matches(doc, sub) for sub in v):
                    return False
            elif k == "$or":
                if not any(self._doc_matches(doc, sub) for sub in v):
                    return False
            elif isinstance(v, dict):
                doc_val = doc.get(k)
                for op, op_val in v.items():
                    if op == "$ne" and doc_val == op_val:
                        return False
                    elif op == "$eq" and doc_val != op_val:
                        return False
                    elif op == "$in" and doc_val not in op_val:
                        return False
                    elif op == "$gt" and not (doc_val and doc_val > op_val):
                        return False
                    elif op == "$gte" and not (doc_val is not None and doc_val >= op_val):
                        return False
                    elif op == "$lt" and not (doc_val and doc_val < op_val):
                        return False
                    elif op == "$lte" and not (doc_val is not None and doc_val <= op_val):
                        return False
                    elif op == "$regex":
                        import re
                        flags = re.IGNORECASE if v.get("$options", "") == "i" else 0
                        if not (isinstance(doc_val, str) and re.search(op_val, doc_val, flags)):
                            return False
                    elif op == "$options":
                        pass
            else:
                # Handle ObjectId comparison
                doc_val = doc.get(k)
                if str(doc_val) != str(v) and doc_val != v:
                    return False
        return True


class MockDB:
    def __init__(self):
        self._cols: dict[str, MockCollection] = {}
        self.client = None

    def __getitem__(self, name: str) -> MockCollection:
        if name not in self._cols:
            self._cols[name] = MockCollection(name)
        return self._cols[name]


# ── Concrete test repository ───────────────────────────────────────────────────

class ItemRepository(BaseRepository):
    """Minimal concrete repo for testing BaseRepository behaviour."""
    collection   = "items"
    event_prefix = "item"
    cache_ttl    = 30


def make_ctx(role="researcher", user_id="user1", is_admin=False):
    return SecurityContext(
        user_id=user_id,
        email=f"{user_id}@test.com",
        role=role,
        is_admin=is_admin,
        is_super_admin=(role == "super_admin"),
        permissions=frozenset(["*"] if is_admin else ["read:own", "write:own", "delete:items"]),
    )


def make_admin_ctx():
    return make_ctx(role="admin", user_id="admin1", is_admin=True)


# ══════════════════════════════════════════════════════════════════════════════
# Test Cases
# ══════════════════════════════════════════════════════════════════════════════

class TestSecurityContext(unittest.TestCase):

    def test_system_context(self):
        ctx = SecurityContext.system()
        self.assertEqual(ctx.user_id, "system")
        self.assertTrue(ctx.is_super_admin)
        self.assertIn("*", ctx.permissions)

    def test_from_user_basic(self):
        user = {"_id": "abc123", "email": "test@x.com", "role": "researcher"}
        ctx  = SecurityContext.from_user(user)
        self.assertEqual(ctx.user_id, "abc123")
        self.assertEqual(ctx.role, "researcher")
        self.assertFalse(ctx.is_admin)

    def test_from_user_admin(self):
        user = {"_id": "adm1", "email": "admin@x.com", "role": "admin"}
        ctx  = SecurityContext.from_user(user)
        self.assertTrue(ctx.is_admin)
        self.assertFalse(ctx.is_super_admin)

    def test_from_user_super_admin_email(self):
        user = {"_id": "sa1", "email": "admin@synaptiq.academy", "role": "researcher"}
        ctx  = SecurityContext.from_user(user)
        self.assertTrue(ctx.is_super_admin)

    def test_owns(self):
        ctx = make_ctx(user_id="u1")
        self.assertTrue(ctx.owns({"user_id": "u1"}))
        self.assertFalse(ctx.owns({"user_id": "u2"}))

    def test_can_delete_admin(self):
        ctx = make_admin_ctx()
        self.assertTrue(ctx.can_delete("missions"))

    def test_institution_to_tenant(self):
        t1 = _institution_to_tenant("MIT")
        t2 = _institution_to_tenant("mit")
        self.assertEqual(t1, t2)  # case-insensitive
        self.assertEqual(len(t1), 16)

    def test_to_audit_dict(self):
        ctx = make_ctx()
        d   = ctx.to_audit_dict()
        self.assertIn("user_id", d)
        self.assertIn("role", d)
        self.assertIn("request_id", d)

    def test_frozen(self):
        ctx = make_ctx()
        with self.assertRaises(Exception):
            ctx.user_id = "hacked"  # type: ignore


class TestQuerySpec(unittest.TestCase):

    def test_and_merges_filters(self):
        s = Specs.active().and_(Specs.by_status("running"))
        self.assertEqual(s.filters.get("deleted_at"), None)
        self.assertEqual(s.filters.get("status"), "running")

    def test_and_conflict_wraps_in_and(self):
        s1 = QuerySpec({"status": "a"})
        s2 = QuerySpec({"status": "b"})
        merged = s1.and_(s2)
        self.assertIn("$and", merged.filters)

    def test_or_(self):
        s1 = QuerySpec({"x": 1})
        s2 = QuerySpec({"y": 2})
        s  = s1.or_(s2)
        self.assertIn("$or", s.filters)

    def test_page(self):
        s = Specs.recent(10).page(3, 10)
        self.assertEqual(s.skip, 20)
        self.assertEqual(s.limit, 10)

    def test_specs_by_status_list(self):
        s = Specs.by_status(["a", "b"])
        self.assertEqual(s.filters["status"]["$in"], ["a", "b"])


class TestInProcessCache(unittest.TestCase):

    def setUp(self):
        clear_all_caches()

    def test_set_and_get(self):
        c = InProcessCache()
        c.set("k", {"data": 1}, ttl=60)
        self.assertEqual(c.get("k"), {"data": 1})

    def test_miss_returns_none(self):
        c = InProcessCache()
        self.assertIsNone(c.get("missing"))

    def test_ttl_expiry(self):
        import time
        c = InProcessCache()
        c.set("k", "v", ttl=0)
        time.sleep(0.01)
        self.assertIsNone(c.get("k"))

    def test_delete_prefix(self):
        c = InProcessCache()
        c.set("repo:missions:doc:1", "a")
        c.set("repo:missions:doc:2", "b")
        c.set("repo:users:doc:1", "c")
        removed = c.delete_prefix("repo:missions:")
        self.assertEqual(removed, 2)
        self.assertIsNone(c.get("repo:missions:doc:1"))
        self.assertEqual(c.get("repo:users:doc:1"), "c")

    def test_max_size_eviction(self):
        c = InProcessCache(max_size=5)
        for i in range(10):
            c.set(f"k{i}", i, ttl=600)
        # Should not raise; some entries evicted


class TestAuditDiff(unittest.TestCase):

    def test_diff_added(self):
        d = _diff(None, {"x": 1, "y": 2})
        self.assertIn("added", d)

    def test_diff_removed(self):
        d = _diff({"x": 1}, None)
        self.assertIn("removed", d)

    def test_diff_changed(self):
        d = _diff({"status": "draft"}, {"status": "running"})
        self.assertIn("status", d)
        self.assertEqual(d["status"]["from"], "draft")
        self.assertEqual(d["status"]["to"], "running")

    def test_diff_skips_updated_at(self):
        d = _diff({"updated_at": "old"}, {"updated_at": "new", "x": 1})
        self.assertNotIn("updated_at", d)

    def test_diff_no_change(self):
        d = _diff({"x": 1}, {"x": 1})
        self.assertEqual(d, {})


class TestRepoEventBus(unittest.TestCase):

    def test_subscribe_and_emit(self):
        bus      = RepoEventBus()
        received = []

        async def handler(event):
            received.append(event.type)

        bus.subscribe("test.created", handler)
        event = RepoEvent(type="test.created", payload={})

        async def run():
            await bus.emit_async(event)

        asyncio.run(run())
        self.assertIn("test.created", received)

    def test_wildcard_subscriber(self):
        bus  = RepoEventBus()
        seen = []

        async def handler(e):
            seen.append(e.type)

        bus.subscribe("*", handler)

        async def run():
            await bus.emit_async(RepoEvent(type="a.created"))
            await bus.emit_async(RepoEvent(type="b.updated"))

        asyncio.run(run())
        self.assertEqual(seen, ["a.created", "b.updated"])

    def test_error_in_handler_does_not_block(self):
        bus = RepoEventBus()

        async def bad(e):
            raise RuntimeError("boom")

        async def good(e):
            pass

        bus.subscribe("x.ev", bad)
        bus.subscribe("x.ev", good)

        async def run():
            # Should not raise
            await bus.emit_async(RepoEvent(type="x.ev"))

        asyncio.run(run())  # should not raise

    def test_unsubscribe(self):
        bus  = RepoEventBus()
        seen = []

        async def h(e):
            seen.append(1)

        bus.subscribe("y.ev", h)
        bus.unsubscribe("y.ev", h)

        async def run():
            await bus.emit_async(RepoEvent(type="y.ev"))

        asyncio.run(run())
        self.assertEqual(seen, [])


class TestBaseRepository(unittest.TestCase):

    def _make_repo(self, role="researcher", user_id="user1", is_admin=False):
        db  = MockDB()
        ctx = make_ctx(role=role, user_id=user_id, is_admin=is_admin)
        return ItemRepository(db, ctx), db, ctx

    def test_create_adds_metadata(self):
        async def run():
            repo, db, ctx = self._make_repo()
            doc = await repo.create({"name": "Test Item"})
            self.assertIn("id", doc)
            self.assertEqual(doc["user_id"], ctx.user_id)
            self.assertEqual(doc["version"], 1)
            self.assertIsNone(doc["deleted_at"])

        asyncio.run(run())

    def test_find_one_by_id(self):
        async def run():
            repo, db, ctx = self._make_repo()
            created = await repo.create({"name": "item1"})
            found   = await repo.find_one(doc_id=created["id"])
            self.assertIsNotNone(found)
            self.assertEqual(found["name"], "item1")

        asyncio.run(run())

    def test_find_many_rls_scopes_to_user(self):
        async def run():
            repo1, db, _   = self._make_repo(user_id="alice")
            repo2           = ItemRepository(db, make_ctx(user_id="bob"))

            await repo1.create({"name": "alice_item"})
            await repo2.create({"name": "bob_item"})

            alice_items = await repo1.find_many()
            self.assertEqual(len(alice_items), 1)
            self.assertEqual(alice_items[0]["name"], "alice_item")

        asyncio.run(run())

    def test_admin_sees_all(self):
        async def run():
            repo1, db, _ = self._make_repo(user_id="alice")
            repo2         = ItemRepository(db, make_ctx(user_id="bob"))
            admin_repo    = ItemRepository(db, make_admin_ctx())

            await repo1.create({"name": "alice_item"})
            await repo2.create({"name": "bob_item"})

            all_items = await admin_repo.find_many()
            self.assertEqual(len(all_items), 2)

        asyncio.run(run())

    def test_update_increments_version(self):
        async def run():
            repo, db, _ = self._make_repo()
            doc     = await repo.create({"name": "v1"})
            updated = await repo.update(doc["id"], {"name": "v2"})
            self.assertEqual(updated["version"], 2)
            self.assertEqual(updated["name"], "v2")

        asyncio.run(run())

    def test_update_optimistic_concurrency(self):
        async def run():
            repo, db, _ = self._make_repo()
            doc = await repo.create({"name": "item"})

            with self.assertRaises(ConflictError):
                # expected_version=99 won't match actual version=1
                await repo.update(doc["id"], {"name": "x"}, expected_version=99)

        asyncio.run(run())

    def test_soft_delete(self):
        async def run():
            repo, db, _ = self._make_repo()
            doc    = await repo.create({"name": "del_me"})
            result = await repo.delete(doc["id"])
            self.assertTrue(result)

            # Should not appear in normal find
            found = await repo.find_one(doc_id=doc["id"])
            self.assertIsNone(found)

            # But visible with include_deleted=True
            found_del = await repo.find_one(doc_id=doc["id"], include_deleted=True)
            self.assertIsNotNone(found_del)
            self.assertIsNotNone(found_del["deleted_at"])

        asyncio.run(run())

    def test_restore(self):
        async def run():
            _, db, _      = self._make_repo()
            admin_repo    = ItemRepository(db, make_admin_ctx())
            user_repo     = ItemRepository(db, make_ctx())

            doc    = await user_repo.create({"name": "restore_me"})
            await admin_repo.delete(doc["id"])

            # Non-admin cannot restore
            with self.assertRaises(PermissionError):
                await user_repo.restore(doc["id"])

            restored = await admin_repo.restore(doc["id"])
            self.assertIsNone(restored["deleted_at"])

        asyncio.run(run())

    def test_find_one_not_owned_returns_none(self):
        async def run():
            repo1, db, _ = self._make_repo(user_id="owner")
            repo2         = ItemRepository(db, make_ctx(user_id="stranger"))
            doc = await repo1.create({"name": "private"})
            # stranger cannot find owner's item
            found = await repo2.find_one(doc_id=doc["id"])
            self.assertIsNone(found)

        asyncio.run(run())

    def test_upsert_creates_when_missing(self):
        async def run():
            repo, db, ctx = self._make_repo()
            result = await repo.upsert({"name": "unique_item"}, {"status": "active"})
            self.assertIn("id", result)

        asyncio.run(run())

    def test_bulk_create(self):
        async def run():
            repo, db, _ = self._make_repo()
            ids = await repo.bulk_create([
                {"name": "a"},
                {"name": "b"},
                {"name": "c"},
            ])
            self.assertEqual(len(ids), 3)

        asyncio.run(run())

    def test_count(self):
        async def run():
            repo, db, _ = self._make_repo(user_id="u_count")
            await repo.create({"name": "x"})
            await repo.create({"name": "y"})
            n = await repo.count()
            self.assertEqual(n, 2)

        asyncio.run(run())

    def test_collection_not_set_raises(self):
        class BrokenRepo(BaseRepository):
            collection = ""

        db  = MockDB()
        ctx = make_ctx()
        with self.assertRaises(NotImplementedError):
            BrokenRepo(db, ctx)


class TestMissionRepository(unittest.TestCase):

    def test_list_missions_scoped(self):
        async def run():
            from repo.missions import MissionRepository
            db   = MockDB()
            ctx1 = make_ctx(user_id="researcher1")
            ctx2 = make_ctx(user_id="researcher2")
            r1   = MissionRepository(db, ctx1)
            r2   = MissionRepository(db, ctx2)

            await r1.create({"title": "M1", "status": "draft"})
            await r2.create({"title": "M2", "status": "running"})

            m1 = await r1.list_missions()
            self.assertEqual(len(m1), 1)
            self.assertEqual(m1[0]["title"], "M1")

        asyncio.run(run())

    def test_cancel_mission(self):
        async def run():
            from repo.missions import MissionRepository
            db   = MockDB()
            ctx  = make_ctx(user_id="u1", is_admin=True)
            repo = MissionRepository(db, ctx)
            doc  = await repo.create({"title": "M1", "status": "running"})
            result = await repo.cancel_mission(doc["id"])
            self.assertEqual(result["status"], "cancelled")

        asyncio.run(run())

    def test_cancel_completed_mission_raises(self):
        async def run():
            from repo.missions import MissionRepository
            db   = MockDB()
            ctx  = make_ctx(user_id="u1", is_admin=True)
            repo = MissionRepository(db, ctx)
            doc  = await repo.create({"title": "M1", "status": "completed"})
            with self.assertRaises(ValueError):
                await repo.cancel_mission(doc["id"])

        asyncio.run(run())


class TestNotificationRepository(unittest.TestCase):

    def test_create_and_list(self):
        async def run():
            from repo.notifications import NotificationRepository
            db   = MockDB()
            ctx  = make_ctx(user_id="u1")
            repo = NotificationRepository(db, ctx)

            await repo.create_notification("u1", title="Hello", message="World")
            notifs = await repo.list_notifications()
            self.assertEqual(len(notifs), 1)
            self.assertEqual(notifs[0]["title"], "Hello")

        asyncio.run(run())

    def test_mark_read(self):
        async def run():
            from repo.notifications import NotificationRepository
            db   = MockDB()
            ctx  = make_ctx(user_id="u1", is_admin=True)
            repo = NotificationRepository(db, ctx)
            n    = await repo.create_notification("u1", title="T", message="M")
            updated = await repo.mark_read(n["id"])
            self.assertTrue(updated["read"])

        asyncio.run(run())


class TestSerialize(unittest.TestCase):

    def test_serialize_adds_id(self):
        from bson import ObjectId
        doc    = {"_id": ObjectId("507f1f77bcf86cd799439011"), "name": "x"}
        result = _serialize(doc)
        self.assertEqual(result["id"], "507f1f77bcf86cd799439011")
        self.assertEqual(result["_id"], "507f1f77bcf86cd799439011")

    def test_serialize_none(self):
        self.assertIsNone(_serialize(None))


if __name__ == "__main__":
    unittest.main(verbosity=2)
