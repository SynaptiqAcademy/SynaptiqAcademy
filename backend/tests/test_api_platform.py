"""
Phase XXXV.7 — Enterprise API Platform tests.

All tests use in-memory doubles — no live MongoDB, no network calls.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


# ── In-memory mock DB ─────────────────────────────────────────────────────────

from collections import defaultdict


class MockCursor:
    def __init__(self, docs, sort_field=None, sort_dir=1, skip_n=0, limit_n=0):
        self._docs = list(docs)
        if sort_field:
            rev = sort_dir == -1
            self._docs.sort(key=lambda d: d.get(sort_field, ""), reverse=rev)
        if skip_n:
            self._docs = self._docs[skip_n:]
        if limit_n:
            self._docs = self._docs[:limit_n]
        self._i = 0

    def sort(self, field, direction=1):
        rev = direction == -1
        self._docs.sort(key=lambda d: d.get(field, ""), reverse=rev)
        return self

    def skip(self, n):
        self._docs = self._docs[n:]
        return self

    def limit(self, n):
        if n:
            self._docs = self._docs[:n]
        return self

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._i >= len(self._docs):
            raise StopAsyncIteration
        doc = dict(self._docs[self._i])
        self._i += 1
        return doc


class MockCollection:
    def __init__(self):
        self._docs: list[dict] = []

    async def insert_one(self, doc: dict):
        d = dict(doc)
        # unique check on key_id, webhook_id, delivery_id (skip None)
        for field in ("key_id", "key_hash", "webhook_id", "delivery_id"):
            if field in d and d[field] is not None:
                for existing in self._docs:
                    if existing.get(field) == d[field]:
                        raise Exception(f"E11000 duplicate key: {field}={d[field]}")
        self._docs.append(d)

    async def find_one(self, filt: dict) -> dict | None:
        for doc in self._docs:
            if all(doc.get(k) == v for k, v in filt.items()):
                return dict(doc)
        return None

    def find(self, filt: dict = {}, proj: dict = {}) -> MockCursor:
        result = []
        for doc in self._docs:
            if all(doc.get(k) == v for k, v in filt.items()):
                result.append(dict(doc))
        return MockCursor(result)

    async def update_one(self, filt: dict, update: dict) -> object:
        class R:
            modified_count = 0
        r = R()
        for doc in self._docs:
            if all(doc.get(k) == v for k, v in filt.items()):
                if "$set" in update:
                    doc.update(update["$set"])
                if "$inc" in update:
                    for k, v in update["$inc"].items():
                        doc[k] = doc.get(k, 0) + v
                r.modified_count = 1
                break
        return r

    async def delete_one(self, filt: dict) -> object:
        class R:
            deleted_count = 0
        r = R()
        for i, doc in enumerate(self._docs):
            if all(doc.get(k) == v for k, v in filt.items()):
                self._docs.pop(i)
                r.deleted_count = 1
                break
        return r

    async def count_documents(self, filt: dict = {}) -> int:
        return sum(1 for d in self._docs if all(d.get(k) == v for k, v in filt.items()))

    async def create_index(self, *args, **kwargs):
        pass


class MockDB:
    def __init__(self):
        self._cols: dict[str, MockCollection] = defaultdict(MockCollection)

    def __getitem__(self, name: str) -> MockCollection:
        return self._cols[name]

    def __getattr__(self, name: str) -> MockCollection:
        if name.startswith("_"):
            raise AttributeError(name)
        return self._cols[name]


# ── Helpers ───────────────────────────────────────────────────────────────────

def run(coro):
    return asyncio.run(coro)


# ═════════════════════════════════════════════════════════════════════════════
# 1. VERSIONING
# ═════════════════════════════════════════════════════════════════════════════

class TestVersioning:

    def test_v1_path_rewrite(self):
        from api.versioning import V1CompatMiddleware

        received = {}

        async def fake_app(scope, receive, send):
            received["path"] = scope.get("path")

        mw = V1CompatMiddleware(fake_app)

        async def _run():
            await mw({"type": "http", "path": "/api/v1/users/me"}, None, lambda m: None)

        run(_run())
        assert received["path"] == "/api/users/me"

    def test_non_versioned_path_unchanged(self):
        from api.versioning import V1CompatMiddleware

        received = {}

        async def fake_app(scope, receive, send):
            received["path"] = scope.get("path")

        mw = V1CompatMiddleware(fake_app)

        async def _run():
            await mw({"type": "http", "path": "/api/health"}, None, lambda m: None)

        run(_run())
        assert received["path"] == "/api/health"

    def test_websocket_scope_passthrough(self):
        from api.versioning import V1CompatMiddleware

        received = {}

        async def fake_app(scope, receive, send):
            received["type"] = scope.get("type")

        mw = V1CompatMiddleware(fake_app)

        async def _run():
            await mw({"type": "websocket", "path": "/ws/test"}, None, lambda m: None)

        run(_run())
        assert received["type"] == "websocket"

    def test_response_gets_version_header(self):
        from api.versioning import V1CompatMiddleware

        sent_messages = []

        async def fake_app(scope, receive, send):
            await send({"type": "http.response.start", "headers": [], "status": 200})
            await send({"type": "http.response.body", "body": b""})

        async def capture_send(msg):
            sent_messages.append(msg)

        mw = V1CompatMiddleware(fake_app)

        async def _run():
            await mw({"type": "http", "path": "/api/v1/test"}, None, capture_send)

        run(_run())
        start = next(m for m in sent_messages if m["type"] == "http.response.start")
        header_names = [h[0] for h in start["headers"]]
        assert b"x-api-version" in header_names

    def test_exact_version_path(self):
        from api.versioning import V1CompatMiddleware

        received = {}

        async def fake_app(scope, receive, send):
            received["path"] = scope.get("path")

        mw = V1CompatMiddleware(fake_app)

        async def _run():
            await mw({"type": "http", "path": "/api/v1"}, None, lambda m: None)

        run(_run())
        assert received["path"] == "/api"

    def test_deprecation_registry_register_and_get(self):
        from api.versioning import DeprecationRegistry
        reg = DeprecationRegistry()
        reg.register("/api/old", method="GET", replacement="/api/new", reason="test")
        assert reg.is_deprecated("GET", "/api/old")
        entry = reg.get("GET", "/api/old")
        assert entry.replacement == "/api/new"

    def test_deprecation_registry_unknown(self):
        from api.versioning import DeprecationRegistry
        reg = DeprecationRegistry()
        assert not reg.is_deprecated("GET", "/api/nonexistent")
        assert reg.get("GET", "/api/nonexistent") is None

    def test_deprecate_decorator_registers(self):
        from api.versioning import deprecate, get_deprecation_registry
        _reg = get_deprecation_registry()
        initial = len(_reg.all())

        @deprecate("/api/test-deprecated", method="POST", replacement="/api/test-new")
        async def my_endpoint():
            pass

        assert hasattr(my_endpoint, "_deprecated")
        assert len(_reg.all()) == initial + 1

    def test_get_version_info(self):
        from api.versioning import get_version_info
        info = get_version_info()
        assert info["current"] == "v1"
        assert "v1" in info["supported"]
        assert "/api/v1" in info["base_urls"]["v1"]


# ═════════════════════════════════════════════════════════════════════════════
# 2. RESPONSE ENVELOPE
# ═════════════════════════════════════════════════════════════════════════════

class TestResponseEnvelope:

    def test_wrap_simple(self):
        from api.response import wrap
        r = wrap({"id": "123"})
        assert r["ok"] is True
        assert r["data"]["id"] == "123"
        assert "version" in r

    def test_wrap_with_message(self):
        from api.response import wrap
        r = wrap([], message="no results")
        assert r["message"] == "no results"

    def test_wrap_with_meta(self):
        from api.response import wrap
        r = wrap({}, meta={"page": 1})
        assert r["meta"]["page"] == 1

    def test_wrap_error(self):
        from api.response import wrap_error
        r = wrap_error("not found", code="NOT_FOUND", status=404)
        assert r["ok"] is False
        assert r["error"]["code"] == "NOT_FOUND"
        assert r["error"]["status"] == 404

    def test_paginated_response(self):
        from api.response import PaginatedResponse
        pr = PaginatedResponse(items=[1, 2, 3], total=10, page=1, per_page=3, has_more=True)
        d = pr.to_dict()
        assert d["data"]["total"] == 10
        assert d["data"]["has_more"] is True
        assert d["data"]["page"] == 1

    def test_api_response_no_message_omitted(self):
        from api.response import ApiResponse
        r = ApiResponse(data={"x": 1}).to_dict()
        assert "message" not in r


# ═════════════════════════════════════════════════════════════════════════════
# 3. ERRORS
# ═════════════════════════════════════════════════════════════════════════════

class TestErrors:

    def test_not_found_error(self):
        from api.errors import NotFoundError, EC
        err = NotFoundError("resource missing")
        assert err.status_code == 404
        assert err.error_code == EC.NOT_FOUND
        resp = err.to_response()
        assert resp.status_code == 404

    def test_permission_denied_error(self):
        from api.errors import PermissionDeniedError
        err = PermissionDeniedError("access denied")
        assert err.status_code == 403

    def test_validation_error_with_detail(self):
        from api.errors import ValidationError
        err = ValidationError("bad input", detail={"field": "name"})
        resp = err.to_response()
        body = json.loads(resp.body)
        assert body["error"]["detail"]["field"] == "name"

    def test_api_error_hierarchy(self):
        from api.errors import (
            ApiError, ValidationError, AuthRequiredError,
            RateLimitError, InternalError
        )
        for cls in (ValidationError, AuthRequiredError, RateLimitError, InternalError):
            assert issubclass(cls, ApiError)

    def test_register_exception_handlers_no_crash(self):
        from api.errors import register_exception_handlers

        class FakeApp:
            handlers = []
            def add_exception_handler(self, exc_class, handler):
                self.handlers.append(exc_class)

        app = FakeApp()
        register_exception_handlers(app)
        assert len(app.handlers) >= 2


# ═════════════════════════════════════════════════════════════════════════════
# 4. PAGINATION
# ═════════════════════════════════════════════════════════════════════════════

class TestPagination:

    def test_paginate_list_first_page(self):
        from api.pagination import PaginationParams, paginate_list
        items = list(range(25))
        params = PaginationParams(page=1, limit=10)
        result = paginate_list(items, params)
        assert result.items == list(range(10))
        assert result.total == 25
        assert result.has_more is True

    def test_paginate_list_last_page(self):
        from api.pagination import PaginationParams, paginate_list
        items = list(range(25))
        params = PaginationParams(page=3, limit=10)
        result = paginate_list(items, params)
        assert result.items == [20, 21, 22, 23, 24]
        assert result.has_more is False

    def test_paginate_list_empty(self):
        from api.pagination import PaginationParams, paginate_list
        result = paginate_list([], PaginationParams(page=1, limit=10))
        assert result.items == []
        assert result.total == 0
        assert result.has_more is False

    def test_cursor_encode_decode_roundtrip(self):
        from api.pagination import encode_cursor, decode_cursor
        data = {"id": "abc123", "ts": "2026-01-01T00:00:00"}
        encoded = encode_cursor(data)
        assert isinstance(encoded, str)
        decoded = decode_cursor(encoded)
        assert decoded["id"] == "abc123"

    def test_decode_invalid_cursor_returns_empty(self):
        from api.pagination import decode_cursor
        result = decode_cursor("not-valid-base64!!!")
        assert result == {}

    def test_page_result_to_dict(self):
        from api.pagination import PageResult
        pr = PageResult(items=["a"], total=5, page=1, per_page=10, has_more=False, cursor_next="tok")
        d = pr.to_dict()
        assert d["cursor_next"] == "tok"
        assert d["total"] == 5

    def test_pagination_params_offset(self):
        from api.pagination import PaginationParams
        assert PaginationParams(page=3, limit=10).offset() == 20


# ═════════════════════════════════════════════════════════════════════════════
# 5. API KEYS
# ═════════════════════════════════════════════════════════════════════════════

class TestApiKeys:

    def _make_manager(self):
        from api.keys import ApiKeyManager
        return ApiKeyManager(MockDB())

    def test_create_key_returns_raw_key(self):
        mgr = self._make_manager()
        async def _():
            raw_key, record = await mgr.create("test", "user1", ["read"])
            assert raw_key.startswith("sk-syn-")
            assert "key_id" in record
            assert "key_hash" not in record  # hash not exposed
        run(_())

    def test_validate_valid_key(self):
        mgr = self._make_manager()
        async def _():
            raw_key, _ = await mgr.create("test", "user1", ["read"])
            result = await mgr.validate(raw_key)
            assert result is not None
            assert result["user_id"] == "user1"
        run(_())

    def test_validate_wrong_key(self):
        mgr = self._make_manager()
        async def _():
            result = await mgr.validate("sk-syn-wrongkey123456789012")
            assert result is None
        run(_())

    def test_validate_bad_prefix(self):
        mgr = self._make_manager()
        async def _():
            result = await mgr.validate("invalid-key-format")
            assert result is None
        run(_())

    def test_revoke_key(self):
        mgr = self._make_manager()
        async def _():
            raw_key, record = await mgr.create("test", "user1", ["read"])
            ok = await mgr.revoke(record["key_id"], "user1")
            assert ok is True
            result = await mgr.validate(raw_key)
            assert result is None
        run(_())

    def test_revoke_wrong_user_fails(self):
        mgr = self._make_manager()
        async def _():
            _, record = await mgr.create("test", "user1", ["read"])
            ok = await mgr.revoke(record["key_id"], "user999")
            assert ok is False
        run(_())

    def test_rotate_key(self):
        mgr = self._make_manager()
        async def _():
            raw_key, record = await mgr.create("test", "user1", ["read"])
            new_raw, new_rec = await mgr.rotate(record["key_id"], "user1")
            assert new_raw is not None
            assert new_raw != raw_key
            assert new_rec["user_id"] == "user1"
            # Old key invalid
            assert await mgr.validate(raw_key) is None
        run(_())

    def test_rotate_nonexistent_key(self):
        mgr = self._make_manager()
        async def _():
            result, rec = await mgr.rotate("key_nonexistent", "user1")
            assert result is None
            assert rec is None
        run(_())

    def test_list_for_user(self):
        mgr = self._make_manager()
        async def _():
            await mgr.create("key1", "userA", ["read"])
            await mgr.create("key2", "userA", ["write"])
            await mgr.create("other", "userB", ["read"])
            keys = await mgr.list_for_user("userA")
            assert len(keys) == 2
        run(_())

    def test_get_key_by_id(self):
        mgr = self._make_manager()
        async def _():
            _, record = await mgr.create("mykey", "user1", ["admin"])
            fetched = await mgr.get(record["key_id"])
            assert fetched["name"] == "mykey"
        run(_())

    def test_validate_increments_usage(self):
        mgr = self._make_manager()
        async def _():
            raw_key, record = await mgr.create("test", "user1", ["read"])
            await mgr.validate(raw_key)
            await mgr.validate(raw_key)
            fetched = await mgr.get(record["key_id"])
            assert fetched["usage_count"] == 2
        run(_())

    def test_key_hash_not_in_list(self):
        mgr = self._make_manager()
        async def _():
            await mgr.create("k", "u1", ["read"])
            keys = await mgr.list_for_user("u1")
            assert all("key_hash" not in k for k in keys)
        run(_())


# ═════════════════════════════════════════════════════════════════════════════
# 6. WEBHOOKS
# ═════════════════════════════════════════════════════════════════════════════

class TestWebhooks:

    def _make_engine(self):
        from api.webhooks import WebhookEngine
        return WebhookEngine(MockDB())

    def test_create_webhook(self):
        engine = self._make_engine()
        async def _():
            result = await engine.create(
                user_id="u1", url="https://example.com/hook",
                events=["mission.completed"], name="my hook"
            )
            assert result["webhook_id"].startswith("wh_")
            assert "secret" in result   # exposed once at creation
        run(_())

    def test_list_webhooks_hides_secret(self):
        engine = self._make_engine()
        async def _():
            await engine.create("u1", "https://example.com/hook", ["alert.fired"])
            hooks = await engine.list_for_user("u1")
            assert len(hooks) == 1
            assert "secret" not in hooks[0]
        run(_())

    def test_delete_webhook(self):
        engine = self._make_engine()
        async def _():
            result = await engine.create("u1", "https://h.com", ["ai.complete"])
            ok = await engine.delete(result["webhook_id"], "u1")
            assert ok is True
            hooks = await engine.list_for_user("u1")
            assert len(hooks) == 0
        run(_())

    def test_delete_wrong_user_fails(self):
        engine = self._make_engine()
        async def _():
            result = await engine.create("u1", "https://h.com", ["ai.complete"])
            ok = await engine.delete(result["webhook_id"], "u999")
            assert ok is False
        run(_())

    def test_update_webhook(self):
        engine = self._make_engine()
        async def _():
            result = await engine.create("u1", "https://old.com", [])
            ok = await engine.update(result["webhook_id"], "u1", url="https://new.com")
            assert ok is True
        run(_())

    def test_hmac_sign_and_verify(self):
        from api.webhooks import sign_payload, verify_signature
        secret = "testsecret"
        body   = b'{"event": "test"}'
        sig    = sign_payload(secret, body)
        assert sig.startswith("sha256=")
        assert verify_signature(secret, body, sig)

    def test_hmac_wrong_secret_fails(self):
        from api.webhooks import sign_payload, verify_signature
        sig = sign_payload("correct", b"data")
        assert not verify_signature("wrong", b"data", sig)

    def test_webhook_event_constants(self):
        from api.webhooks import WebhookEvent
        assert WebhookEvent.MISSION_COMPLETED in WebhookEvent.ALL
        assert len(WebhookEvent.ALL) >= 8


# ═════════════════════════════════════════════════════════════════════════════
# 7. SDK GENERATION
# ═════════════════════════════════════════════════════════════════════════════

class TestSdkGen:

    def _spec(self, paths: dict) -> dict:
        return {"info": {"title": "Test", "version": "v1"}, "paths": paths}

    def test_python_sdk_has_client_class(self):
        from api.sdk_gen import generate_python_sdk
        code = generate_python_sdk(self._spec({}))
        assert "class SynaptiqClient" in code
        assert "def _request" in code

    def test_python_sdk_method_generated(self):
        from api.sdk_gen import generate_python_sdk
        spec = self._spec({
            "/api/users": {
                "get": {"operationId": "listUsers", "summary": "List users"}
            }
        })
        code = generate_python_sdk(spec)
        assert "list_users" in code

    def test_typescript_sdk_has_class(self):
        from api.sdk_gen import generate_typescript_sdk
        code = generate_typescript_sdk(self._spec({}))
        assert "class SynaptiqClient" in code
        assert "async request" in code

    def test_typescript_sdk_method_generated(self):
        from api.sdk_gen import generate_typescript_sdk
        spec = self._spec({
            "/api/papers": {
                "get": {"operationId": "listPapers", "summary": "List papers"}
            }
        })
        code = generate_typescript_sdk(spec)
        assert "listPapers" in code

    def test_sdk_compiles_as_python(self):
        from api.sdk_gen import generate_python_sdk
        code = generate_python_sdk(self._spec({}))
        compile(code, "<sdk>", "exec")   # would raise SyntaxError if broken


# ═════════════════════════════════════════════════════════════════════════════
# 8. CONTRACTS
# ═════════════════════════════════════════════════════════════════════════════

class TestContracts:

    def test_contract_decorator_registers(self):
        from api.contracts import ContractRegistry, contract as contract_dec

        reg = ContractRegistry()
        # Test the dataclass directly without registry side effects
        from api.contracts import EndpointContract
        c = EndpointContract(
            path="/api/test", method="GET", summary="test", version="v1",
            stability="stable", auth_required=True
        )
        reg.register(c)
        assert len(reg) == 1

    def test_get_by_method_path(self):
        from api.contracts import ContractRegistry, EndpointContract
        reg = ContractRegistry()
        c = EndpointContract(path="/api/foo", method="POST", version="v1", stability="beta")
        reg.register(c)
        result = reg.get("POST", "/api/foo")
        assert result is not None
        assert result.stability == "beta"

    def test_all_returns_dicts(self):
        from api.contracts import ContractRegistry, EndpointContract
        reg = ContractRegistry()
        reg.register(EndpointContract(path="/a", method="GET", version="v1", stability="stable"))
        reg.register(EndpointContract(path="/b", method="POST", version="v1", stability="alpha"))
        all_c = reg.all()
        assert len(all_c) == 2
        assert all(isinstance(c, dict) for c in all_c)

    def test_by_stability_filter(self):
        from api.contracts import ContractRegistry, EndpointContract
        reg = ContractRegistry()
        reg.register(EndpointContract(path="/stable", method="GET", version="v1", stability="stable"))
        reg.register(EndpointContract(path="/beta", method="GET", version="v1", stability="beta"))
        stable = reg.by_stability("stable")
        assert len(stable) == 1
        assert stable[0]["path"] == "/stable"

    def test_endpoint_contract_to_dict(self):
        from api.contracts import EndpointContract
        c = EndpointContract(
            path="/api/x", method="DELETE", stability="deprecated",
            breaking_after="2027-01-01", scopes=["admin"], version="v1"
        )
        d = c.to_dict()
        assert d["breaking_after"] == "2027-01-01"
        assert "admin" in d["scopes"]

    def test_contract_decorator_wraps_function(self):
        from api.contracts import contract as contract_dec

        @contract_dec("/api/wrapped", method="GET", summary="Wrapped endpoint")
        async def my_handler():
            return "ok"

        assert hasattr(my_handler, "_contract")
        assert asyncio.run(my_handler()) == "ok"


# ═════════════════════════════════════════════════════════════════════════════
# 9. INIT / LIFECYCLE
# ═════════════════════════════════════════════════════════════════════════════

class TestApiPlatformLifecycle:

    def test_init_api_platform_initialises_managers(self):
        from api.keys import _manager as before_keys
        from api.webhooks import _engine as before_hooks

        db  = MockDB()

        class FakeApp:
            _middleware = []
            _handlers   = []
            def add_middleware(self, cls, **kw):
                self._middleware.append(cls.__name__ if hasattr(cls, "__name__") else str(cls))
            def add_exception_handler(self, exc_class, handler):
                self._handlers.append(exc_class)

        app = FakeApp()

        async def _():
            from api import init_api_platform, stop_api_platform
            await init_api_platform(app, db)
            await stop_api_platform()

        run(_())

        from api.keys import get_key_manager
        from api.webhooks import get_webhook_engine
        assert get_key_manager() is not None
        assert get_webhook_engine() is not None

    def test_v1compat_in_middleware_list(self):
        from api.versioning import V1CompatMiddleware

        registered = []

        class FakeApp:
            _handlers = []
            def add_middleware(self, cls, **kw):
                registered.append(cls)
            def add_exception_handler(self, *a):
                pass

        async def _():
            db = MockDB()
            from api import init_api_platform
            await init_api_platform(FakeApp(), db)

        run(_())
        assert V1CompatMiddleware in registered

    def test_package_re_exports(self):
        import api
        for name in (
            "wrap", "wrap_error", "ApiResponse", "PaginatedResponse",
            "paginate_list", "encode_cursor", "decode_cursor",
            "ApiKeyManager", "WebhookEngine", "WebhookEvent",
            "generate_python_sdk", "generate_typescript_sdk",
            "contract", "EndpointContract", "ContractRegistry",
            "V1CompatMiddleware", "deprecate",
            "ApiError", "NotFoundError", "ValidationError",
            "register_exception_handlers",
        ):
            assert hasattr(api, name), f"api package missing export: {name}"


# ═════════════════════════════════════════════════════════════════════════════
# 10. INTEGRATION — key hash
# ═════════════════════════════════════════════════════════════════════════════

class TestKeyHashIntegrity:

    def test_sha256_hash_of_key_stored(self):
        from api.keys import ApiKeyManager, _KEY_PREFIX
        mgr = ApiKeyManager(MockDB())

        async def _():
            raw_key, record = await mgr.create("x", "u", ["read"])
            key_id  = record["key_id"]
            # Reach into collection to confirm hash stored
            stored = mgr._col._docs[0]
            expected_hash = hashlib.sha256(raw_key.encode()).hexdigest()
            assert stored["key_hash"] == expected_hash
        run(_())

    def test_two_creates_produce_different_keys(self):
        from api.keys import ApiKeyManager
        mgr = ApiKeyManager(MockDB())

        async def _():
            k1, _ = await mgr.create("a", "u", ["read"])
            k2, _ = await mgr.create("b", "u", ["read"])
            assert k1 != k2
        run(_())
