"""
Sprint 1.2 — Repository Layer Tests

Tests:
  - DBProxy attribute routing (CollectionProxy returned for any collection)
  - CollectionProxy.find / find_one delegates to motor unchanged
  - CollectionProxy.insert_one enriches with timestamps and _created_by
  - CollectionProxy.update_one injects updated_at into $set
  - CollectionProxy audit fire is scheduled (fire-and-forget)
  - SecurityContext.from_user builds correct context
  - SecurityContext.system has is_admin=True
  - All new domain repositories instantiate without error
  - DBProxy.list_collection_names delegates to motor db
  - CollectionProxy.aggregate returns motor cursor
  - _enrich_update handles $inc / $push without $set
  - make_db_proxy factory function
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


# ─────────────────────────────── helpers ──────────────────────────────────────

class _FakeInsertResult:
    def __init__(self, oid="new_id"):
        self.inserted_id = oid

class _FakeUpdateResult:
    def __init__(self, modified=1):
        self.modified_count = modified
        self.matched_count = modified

class _FakeDeleteResult:
    def __init__(self, deleted=1):
        self.deleted_count = deleted

class _FakeAuditCol:
    """Fake audit_log motor collection for testing."""
    def __init__(self):
        self.calls = []
    async def insert_one(self, doc):
        self.calls.append(doc)

class _FakeCol:
    """Minimal fake motor collection — avoids MagicMock magic-method issues."""
    def __init__(self, name="test_col"):
        self.name = name
        self.full_name = f"db.{name}"
        self._audit = _FakeAuditCol()
        self._find_one_result = {"_id": "abc", "value": 1}
        self._insert_result = _FakeInsertResult()
        self._cursor = object()  # sentinel
        self._cmd_cursor = object()
        self.calls = {}

        # Fake database reference
        class _FakeDB:
            pass
        self.database = _FakeDB()
        self.database.audit_log = self._audit

    async def find_one(self, *args, **kwargs):
        self.calls["find_one"] = (args, kwargs)
        return self._find_one_result

    def find(self, *args, **kwargs):
        self.calls["find"] = (args, kwargs)
        return self._cursor

    def aggregate(self, pipeline, **kwargs):
        self.calls["aggregate"] = pipeline
        return self._cmd_cursor

    async def insert_one(self, doc, **kwargs):
        self.calls["insert_one"] = doc
        return self._insert_result

    async def insert_many(self, docs, **kwargs):
        self.calls["insert_many"] = docs
        class R: inserted_ids = ["id1", "id2"]
        return R()

    async def update_one(self, filt, upd, **kwargs):
        self.calls["update_one"] = (filt, upd, kwargs)
        return _FakeUpdateResult()

    async def update_many(self, filt, upd, **kwargs):
        self.calls["update_many"] = (filt, upd)
        return _FakeUpdateResult(2)

    async def delete_one(self, filt, **kwargs):
        self.calls["delete_one"] = filt
        return _FakeDeleteResult()

    async def delete_many(self, filt, **kwargs):
        self.calls["delete_many"] = filt
        return _FakeDeleteResult(3)

    async def count_documents(self, filt=None, **kwargs):
        self.calls["count_documents"] = filt
        return 5

    async def distinct(self, key, filt=None, **kwargs):
        self.calls["distinct"] = (key, filt)
        return ["a", "b"]

    async def find_one_and_update(self, filt, upd, **kwargs):
        self.calls["find_one_and_update"] = (filt, upd, kwargs)
        return {"_id": "abc", "updated": True}

    async def replace_one(self, filt, doc, **kwargs):
        self.calls["replace_one"] = (filt, doc)
        return _FakeUpdateResult()

    async def bulk_write(self, reqs, **kwargs):
        self.calls["bulk_write"] = reqs
        class R: bulk_api_result = {}
        return R()

    async def create_index(self, keys, **kwargs):
        return "idx"

    async def estimated_document_count(self, **kwargs):
        return 100


def _fake_motor_col(name="test_col"):
    return _FakeCol(name)


class _FakeMotorDB:
    """Fake motor database — supports attribute and item access."""
    def __init__(self):
        self.name = "synaptiq"
        self._cols: dict[str, _FakeCol] = {}

    def __getitem__(self, name: str) -> _FakeCol:
        if name not in self._cols:
            self._cols[name] = _FakeCol(name)
        return self._cols[name]

    def __getattr__(self, name: str) -> _FakeCol:
        if name.startswith("_") or name == "name":
            raise AttributeError(name)
        return self[name]

    async def list_collection_names(self, **kw):
        return ["users", "projects"]

    async def command(self, cmd, **kw):
        return {"ok": 1}


def _fake_motor_db():
    db = _FakeMotorDB()
    col = db["test_col"]
    return db, col


def _make_user(role="researcher"):
    return {
        "id": "user123",
        "_id": "user123",
        "email": "test@example.com",
        "role": role,
        "institution": "Test University",
    }


# ─────────────────────────────── import checks ────────────────────────────────

def test_shim_imports():
    from repo.shim import DBProxy, CollectionProxy, make_db_proxy
    assert DBProxy
    assert CollectionProxy
    assert make_db_proxy


def test_repo_package_exports():
    import repo
    assert hasattr(repo, "DBProxy")
    assert hasattr(repo, "CollectionProxy")
    assert hasattr(repo, "make_db_proxy")
    assert hasattr(repo, "ManuscriptRepository")
    assert hasattr(repo, "ProjectRepository")
    assert hasattr(repo, "CollaborationRepository")
    assert hasattr(repo, "TeachingWorkspaceRepository")
    assert hasattr(repo, "TeachingLessonRepository")
    assert hasattr(repo, "TeachingAssessmentRepository")
    assert hasattr(repo, "FileRepository")
    assert hasattr(repo, "ConversationRepository")
    assert hasattr(repo, "MessageRepository")
    assert hasattr(repo, "MarketplaceListingRepository")
    assert hasattr(repo, "ExpertiseRequestRepository")
    assert hasattr(repo, "InstitutionMembershipRepository")
    assert hasattr(repo, "AIRequestRepository")
    assert hasattr(repo, "ResearchImpactRepository")


# ─────────────────────────────── SecurityContext ──────────────────────────────

def test_security_context_from_user():
    from repo.security_context import SecurityContext
    user = _make_user("researcher")
    ctx = SecurityContext.from_user(user)
    assert ctx.user_id == "user123"
    assert ctx.email == "test@example.com"
    assert ctx.role == "researcher"
    assert not ctx.is_admin
    assert not ctx.is_super_admin


def test_security_context_admin():
    from repo.security_context import SecurityContext
    user = _make_user("admin")
    ctx = SecurityContext.from_user(user)
    assert ctx.is_admin
    assert not ctx.is_super_admin


def test_security_context_system():
    from repo.security_context import SecurityContext
    ctx = SecurityContext.system()
    assert ctx.user_id == "system"
    assert ctx.is_admin
    assert ctx.is_super_admin


# ─────────────────────────────── DBProxy ──────────────────────────────────────

def test_dbproxy_returns_collection_proxy():
    from repo.shim import DBProxy, CollectionProxy
    from repo.security_context import SecurityContext
    db, _ = _fake_motor_db()
    ctx = SecurityContext.system()
    proxy = DBProxy(db, ctx)
    col_proxy = proxy.users
    assert isinstance(col_proxy, CollectionProxy)


def test_dbproxy_caches_proxies():
    from repo.shim import DBProxy
    from repo.security_context import SecurityContext
    db, _ = _fake_motor_db()
    ctx = SecurityContext.system()
    proxy = DBProxy(db, ctx)
    p1 = proxy.users
    p2 = proxy.users
    assert p1 is p2


def test_dbproxy_getitem_same_as_getattr():
    from repo.shim import DBProxy
    from repo.security_context import SecurityContext
    db, _ = _fake_motor_db()
    ctx = SecurityContext.system()
    proxy = DBProxy(db, ctx)
    assert proxy["users"] is proxy.users


def test_dbproxy_list_collection_names():
    from repo.shim import DBProxy
    from repo.security_context import SecurityContext
    db, _ = _fake_motor_db()
    ctx = SecurityContext.system()
    proxy = DBProxy(db, ctx)
    names = asyncio.run(proxy.list_collection_names())
    assert "users" in names


def test_dbproxy_name_property():
    from repo.shim import DBProxy
    from repo.security_context import SecurityContext
    db, _ = _fake_motor_db()
    ctx = SecurityContext.system()
    proxy = DBProxy(db, ctx)
    assert proxy.name == "synaptiq"


# ─────────────────────────────── CollectionProxy reads ───────────────────────

def test_collection_proxy_find_one_delegates():
    from repo.shim import CollectionProxy
    from repo.security_context import SecurityContext
    col = _fake_motor_col("users")
    ctx = SecurityContext.system()
    proxy = CollectionProxy("users", col, ctx)
    doc = asyncio.run(proxy.find_one({"email": "x@y.com"}))
    assert doc == {"_id": "abc", "value": 1}
    assert col.calls.get("find_one")[0][0] == {"email": "x@y.com"}


def test_collection_proxy_find_one_with_projection():
    from repo.shim import CollectionProxy
    from repo.security_context import SecurityContext
    col = _fake_motor_col("users")
    ctx = SecurityContext.system()
    proxy = CollectionProxy("users", col, ctx)
    asyncio.run(proxy.find_one({"_id": "x"}, {"name": 1}))
    args = col.calls["find_one"][0]
    assert args == ({"_id": "x"}, {"name": 1})


def test_collection_proxy_find_returns_motor_cursor():
    from repo.shim import CollectionProxy
    from repo.security_context import SecurityContext
    col = _fake_motor_col("users")
    ctx = SecurityContext.system()
    proxy = CollectionProxy("users", col, ctx)
    result = proxy.find({"status": "active"})
    assert result is col._cursor
    assert col.calls["find"][0][0] == {"status": "active"}


def test_collection_proxy_aggregate_returns_motor_cursor():
    from repo.shim import CollectionProxy
    from repo.security_context import SecurityContext
    col = _fake_motor_col("projects")
    ctx = SecurityContext.system()
    proxy = CollectionProxy("projects", col, ctx)
    pipeline = [{"$match": {}}]
    result = proxy.aggregate(pipeline)
    assert result is col._cmd_cursor
    assert col.calls["aggregate"] == pipeline


def test_collection_proxy_count_documents():
    from repo.shim import CollectionProxy
    from repo.security_context import SecurityContext
    col = _fake_motor_col()
    ctx = SecurityContext.system()
    proxy = CollectionProxy("test", col, ctx)
    count = asyncio.run(proxy.count_documents({"status": "active"}))
    assert count == 5
    assert col.calls["count_documents"] == {"status": "active"}


def test_collection_proxy_distinct():
    from repo.shim import CollectionProxy
    from repo.security_context import SecurityContext
    col = _fake_motor_col()
    ctx = SecurityContext.system()
    proxy = CollectionProxy("test", col, ctx)
    values = asyncio.run(proxy.distinct("field", {"x": 1}))
    assert values == ["a", "b"]


# ─────────────────────────────── CollectionProxy writes ──────────────────────

def test_insert_one_adds_timestamps():
    from repo.shim import CollectionProxy
    from repo.security_context import SecurityContext
    col = _fake_motor_col()
    ctx = SecurityContext.from_user(_make_user())
    proxy = CollectionProxy("projects", col, ctx)
    asyncio.run(proxy.insert_one({"title": "My Project"}))
    enriched = col.calls["insert_one"]
    assert "created_at" in enriched
    assert "updated_at" in enriched
    assert enriched["title"] == "My Project"


def test_insert_one_adds_created_by():
    from repo.shim import CollectionProxy
    from repo.security_context import SecurityContext
    col = _fake_motor_col()
    ctx = SecurityContext.from_user(_make_user())
    proxy = CollectionProxy("items", col, ctx)
    asyncio.run(proxy.insert_one({"name": "item"}))
    enriched = col.calls["insert_one"]
    assert enriched["_created_by"] == "user123"


def test_insert_one_does_not_overwrite_existing_timestamps():
    from repo.shim import CollectionProxy
    from repo.security_context import SecurityContext
    col = _fake_motor_col()
    ctx = SecurityContext.system()
    proxy = CollectionProxy("items", col, ctx)
    ts = "2026-01-01T00:00:00"
    asyncio.run(proxy.insert_one({"created_at": ts, "val": 1}))
    enriched = col.calls["insert_one"]
    assert enriched["created_at"] == ts  # must not be overwritten


def test_update_one_injects_updated_at():
    from repo.shim import CollectionProxy
    from repo.security_context import SecurityContext
    col = _fake_motor_col()
    ctx = SecurityContext.system()
    proxy = CollectionProxy("users", col, ctx)
    update = {"$set": {"name": "Alice"}}
    asyncio.run(proxy.update_one({"_id": "x"}, update))
    _, used_update, _ = col.calls["update_one"]
    assert "updated_at" in used_update["$set"]
    assert used_update["$set"]["name"] == "Alice"


def test_update_one_with_inc_adds_set_for_timestamp():
    from repo.shim import CollectionProxy
    from repo.security_context import SecurityContext
    col = _fake_motor_col()
    ctx = SecurityContext.system()
    proxy = CollectionProxy("items", col, ctx)
    update = {"$inc": {"count": 1}}
    asyncio.run(proxy.update_one({"_id": "x"}, update))
    _, used_update, _ = col.calls["update_one"]
    assert "$set" in used_update
    assert "updated_at" in used_update["$set"]


def test_update_one_preserves_existing_updated_at():
    from repo.shim import CollectionProxy
    from repo.security_context import SecurityContext
    col = _fake_motor_col()
    ctx = SecurityContext.system()
    proxy = CollectionProxy("items", col, ctx)
    ts = "2026-06-01T00:00:00"
    update = {"$set": {"name": "X", "updated_at": ts}}
    asyncio.run(proxy.update_one({"_id": "x"}, update))
    _, used_update, _ = col.calls["update_one"]
    assert used_update["$set"]["updated_at"] == ts  # must not be overwritten


def test_delete_one_delegates():
    from repo.shim import CollectionProxy
    from repo.security_context import SecurityContext
    col = _fake_motor_col()
    ctx = SecurityContext.system()
    proxy = CollectionProxy("users", col, ctx)
    result = asyncio.run(proxy.delete_one({"_id": "x"}))
    assert col.calls.get("delete_one") == {"_id": "x"}
    assert result.deleted_count == 1


def test_find_one_and_update_injects_timestamp():
    from repo.shim import CollectionProxy
    from repo.security_context import SecurityContext
    col = _fake_motor_col()
    ctx = SecurityContext.system()
    proxy = CollectionProxy("users", col, ctx)
    update = {"$set": {"status": "active"}}
    asyncio.run(
        proxy.find_one_and_update({"_id": "x"}, update, return_document=True)
    )
    _, used_update, _ = col.calls["find_one_and_update"]
    assert "updated_at" in used_update["$set"]


# ─────────────────────────────── Audit ───────────────────────────────────────

def test_audit_skipped_for_audit_log_collection():
    """Audit writes to audit_log itself must not recurse."""
    from repo.shim import CollectionProxy
    from repo.security_context import SecurityContext
    col = _fake_motor_col("audit_log")
    ctx = SecurityContext.system()
    proxy = CollectionProxy("audit_log", col, ctx)

    async def _run():
        await proxy.insert_one({"event": "test"})
        await asyncio.sleep(0.05)

    asyncio.run(_run())
    # Audit entries must NOT be written for audit_log itself
    assert len(col._audit.calls) == 0


def test_audit_fires_for_regular_collection():
    """Audit write should be scheduled for non-exempt collections."""
    from repo.shim import CollectionProxy
    from repo.security_context import SecurityContext
    col = _fake_motor_col("manuscripts")
    ctx = SecurityContext.from_user(_make_user())
    proxy = CollectionProxy("manuscripts", col, ctx)

    async def _run():
        await proxy.insert_one({"title": "Test"})
        await asyncio.sleep(0.05)

    asyncio.run(_run())
    assert len(col._audit.calls) > 0
    entry = col._audit.calls[0]
    assert entry["_collection"] == "manuscripts"
    assert entry["_operation"] == "create"
    assert entry["_user_id"] == "user123"


# ─────────────────────────────── make_db_proxy ───────────────────────────────

def test_make_db_proxy_with_user():
    from repo.shim import DBProxy, make_db_proxy
    from repo.security_context import SecurityContext
    db, _ = _fake_motor_db()
    user = _make_user()
    proxy = make_db_proxy(db, user)
    assert isinstance(proxy, DBProxy)
    assert proxy._ctx.user_id == "user123"
    assert not proxy._ctx.is_admin


def test_make_db_proxy_system():
    from repo.shim import DBProxy, make_db_proxy
    db, _ = _fake_motor_db()
    proxy = make_db_proxy(db, system=True)
    assert isinstance(proxy, DBProxy)
    assert proxy._ctx.is_admin


def test_make_db_proxy_no_user_defaults_to_system():
    from repo.shim import DBProxy, make_db_proxy
    db, _ = _fake_motor_db()
    proxy = make_db_proxy(db)
    assert proxy._ctx.user_id == "system"


# ─────────────────────────────── Domain repos ────────────────────────────────

def _make_ctx(role="researcher"):
    from repo.security_context import SecurityContext
    return SecurityContext.from_user(_make_user(role))


def test_manuscript_repository_instantiates():
    from repo.manuscripts import ManuscriptRepository
    db, _ = _fake_motor_db()
    repo = ManuscriptRepository(db, _make_ctx())
    assert repo.collection == "manuscripts"


def test_project_repository_instantiates():
    from repo.projects import ProjectRepository
    db, _ = _fake_motor_db()
    repo = ProjectRepository(db, _make_ctx())
    assert repo.collection == "projects"


def test_collaboration_repository_instantiates():
    from repo.collaborations import CollaborationRepository
    db, _ = _fake_motor_db()
    repo = CollaborationRepository(db, _make_ctx())
    assert repo.collection == "collaborations"


def test_teaching_workspace_repository_instantiates():
    from repo.teaching import TeachingWorkspaceRepository
    db, _ = _fake_motor_db()
    repo = TeachingWorkspaceRepository(db, _make_ctx())
    assert repo.collection == "teaching_workspaces"


def test_teaching_lesson_repository_instantiates():
    from repo.teaching import TeachingLessonRepository
    db, _ = _fake_motor_db()
    repo = TeachingLessonRepository(db, _make_ctx())
    assert repo.collection == "teaching_lessons"


def test_teaching_assessment_repository_instantiates():
    from repo.teaching import TeachingAssessmentRepository
    db, _ = _fake_motor_db()
    repo = TeachingAssessmentRepository(db, _make_ctx())
    assert repo.collection == "teaching_assessments"


def test_file_repository_instantiates():
    from repo.files_repo import FileRepository
    db, _ = _fake_motor_db()
    repo = FileRepository(db, _make_ctx())
    assert repo.collection == "files"


def test_conversation_repository_instantiates():
    from repo.messaging import ConversationRepository
    db, _ = _fake_motor_db()
    repo = ConversationRepository(db, _make_ctx())
    assert repo.collection == "conversations"


def test_message_repository_instantiates():
    from repo.messaging import MessageRepository
    db, _ = _fake_motor_db()
    repo = MessageRepository(db, _make_ctx())
    assert repo.collection == "messages"


def test_marketplace_listing_repository_instantiates():
    from repo.marketplace import MarketplaceListingRepository
    db, _ = _fake_motor_db()
    repo = MarketplaceListingRepository(db, _make_ctx())
    assert repo.collection == "marketplace_listings"


def test_expertise_request_repository_instantiates():
    from repo.expertise import ExpertiseRequestRepository
    db, _ = _fake_motor_db()
    repo = ExpertiseRequestRepository(db, _make_ctx())
    assert repo.collection == "expertise_requests"


def test_institution_membership_repository_instantiates():
    from repo.institution_members import InstitutionMembershipRepository
    db, _ = _fake_motor_db()
    repo = InstitutionMembershipRepository(db, _make_ctx())
    assert repo.collection == "institution_memberships"


def test_ai_request_repository_instantiates():
    from repo.analytics import AIRequestRepository
    db, _ = _fake_motor_db()
    repo = AIRequestRepository(db, _make_ctx())
    assert repo.collection == "ai_requests"


def test_research_impact_repository_instantiates():
    from repo.analytics import ResearchImpactRepository
    db, _ = _fake_motor_db()
    repo = ResearchImpactRepository(db, _make_ctx())
    assert repo.collection == "research_impact"


# ─────────────────────────────── RLS scoping ─────────────────────────────────

def test_manuscript_repo_scopes_to_user():
    from repo.manuscripts import ManuscriptRepository
    db, _ = _fake_motor_db()
    ctx = _make_ctx("researcher")
    repo = ManuscriptRepository(db, ctx)
    filters = repo._scope_query({})
    assert "$or" in filters
    conditions = filters["$or"]
    user_conditions = [c for c in conditions if c.get("user_id") == "user123"]
    assert user_conditions


def test_manuscript_repo_admin_bypasses_scope():
    from repo.manuscripts import ManuscriptRepository
    db, _ = _fake_motor_db()
    ctx = _make_ctx("admin")
    repo = ManuscriptRepository(db, ctx)
    filters = repo._scope_query({})
    assert "$or" not in filters


def test_project_repo_scopes_to_user():
    from repo.projects import ProjectRepository
    db, _ = _fake_motor_db()
    ctx = _make_ctx("researcher")
    repo = ProjectRepository(db, ctx)
    filters = repo._scope_query({})
    assert "$or" in filters


def test_collaboration_request_repo_scopes_to_user():
    from repo.collaborations import CollaborationRequestRepository
    db, _ = _fake_motor_db()
    ctx = _make_ctx("researcher")
    repo = CollaborationRequestRepository(db, ctx)
    filters = repo._scope_query({})
    assert "$or" in filters


def test_teaching_lesson_repo_scopes_to_user():
    from repo.teaching import TeachingLessonRepository
    db, _ = _fake_motor_db()
    ctx = _make_ctx("researcher")
    repo = TeachingLessonRepository(db, ctx)
    filters = repo._scope_query({})
    assert filters.get("user_id") == "user123"


# ─────────────────────────────── Existing repos still work ───────────────────

def test_mission_repository_still_works():
    from repo.missions import MissionRepository
    db, _ = _fake_motor_db()
    ctx = _make_ctx()
    repo = MissionRepository(db, ctx)
    assert repo.collection == "ara_missions"


def test_user_repository_still_works():
    from repo.users import UserRepository
    db, _ = _fake_motor_db()
    ctx = _make_ctx()
    repo = UserRepository(db, ctx)
    assert repo.collection == "users"


def test_workspace_repository_still_works():
    from repo.workspaces import WorkspaceRepository
    db, _ = _fake_motor_db()
    ctx = _make_ctx()
    repo = WorkspaceRepository(db, ctx)
    assert repo.collection == "workspaces"


def test_grant_repository_still_works():
    from repo.grants import GrantRepository
    db, _ = _fake_motor_db()
    ctx = _make_ctx()
    repo = GrantRepository(db, ctx)
    assert repo.collection == "grants"


def test_notification_repository_still_works():
    from repo.notifications import NotificationRepository
    db, _ = _fake_motor_db()
    ctx = _make_ctx()
    repo = NotificationRepository(db, ctx)
    assert repo.collection == "notifications"
