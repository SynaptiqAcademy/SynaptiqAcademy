"""Launch-blocker remediation: coordination, scheduling, quotas, credits,
client IP, shared rate limits, AI budget and non-blocking password hashing.

Runs against the local test MongoDB (tests/conftest.py → synaptiq_test).
"""
from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime, timedelta, timezone

import pytest
from bson import ObjectId
from fastapi import HTTPException
from starlette.requests import Request


@pytest.fixture
async def tdb():
    from motor.motor_asyncio import AsyncIOMotorClient
    client = AsyncIOMotorClient(os.environ["MONGODB_URI"])
    db = client[os.environ["MONGODB_DB_NAME"]]
    yield db
    client.close()


# ───────────────────────────── coordination ─────────────────────────────

class TestLeaseLock:
    async def test_one_holder_at_a_time_and_takeover_after_expiry(self, tdb):
        from services.coordination import LeaseLock
        name = f"test-lease-{ObjectId()}"
        a = LeaseLock(name, ttl_seconds=1, db=tdb, holder="process-a")
        b = LeaseLock(name, ttl_seconds=1, db=tdb, holder="process-b")
        assert await a.acquire() is True
        assert await b.acquire() is False          # held, not expired
        assert await a.renew() is True             # holder keeps it
        await asyncio.sleep(1.2)                   # holder dies: no renewals
        assert await b.acquire() is True           # takeover
        assert await a.acquire() is False
        await b.release()
        assert await a.acquire() is True
        await a.release()

    async def test_concurrent_acquire_has_exactly_one_winner(self, tdb):
        from services.coordination import LeaseLock
        name = f"test-lease-{ObjectId()}"
        locks = [LeaseLock(name, ttl_seconds=30, db=tdb, holder=f"p{i}") for i in range(12)]
        results = await asyncio.gather(*[lk.acquire() for lk in locks])
        assert sum(results) == 1
        await tdb.coordination_leases.delete_one({"_id": name})


class TestRunOnce:
    async def test_job_body_runs_once_per_window_across_concurrent_schedulers(self, tdb):
        from services.coordination import run_once
        job = f"digest_test_{ObjectId()}"
        calls = []

        async def send_digest_emails():
            calls.append(1)
            await asyncio.sleep(0.05)

        outcomes = await asyncio.gather(*[run_once(job, "2026-10-08", send_digest_emails, db=tdb)
                                          for _ in range(8)])
        assert len(calls) == 1
        assert outcomes.count("completed") == 1 and outcomes.count("skipped") == 7
        # Next window runs again.
        assert await run_once(job, "2026-10-09", send_digest_emails, db=tdb) == "completed"
        assert len(calls) == 2

    async def test_failure_is_recorded_and_not_retried_in_same_window(self, tdb):
        from services.coordination import run_once
        job = f"failing_{ObjectId()}"

        async def boom():
            raise RuntimeError("provider down")

        assert await run_once(job, "w1", boom, db=tdb, alert_on_failure=False) == "failed"
        doc = await tdb.job_runs.find_one({"_id": f"{job}:w1"})
        assert doc["status"] == "failed" and doc["error"] == "RuntimeError"
        assert await run_once(job, "w1", boom, db=tdb, alert_on_failure=False) == "skipped"


class TestDiscoverySchedulerElection:
    async def test_only_one_of_several_worker_processes_runs_the_scheduler(self, tdb, monkeypatch):
        """Simulates gunicorn workers: each runs the election loop; one lease holder."""
        from services.coordination import LeaseLock
        from services.discovery import scheduler as sch
        name = f"test-discovery-{ObjectId()}"
        workers = [LeaseLock(name, ttl_seconds=2, db=tdb, holder=f"worker-{i}") for i in range(4)]
        running = set()

        async def election(lock, rounds):
            for _ in range(rounds):
                if await lock.acquire():
                    running.add(lock.holder)
                else:
                    running.discard(lock.holder)
                assert len(running) <= 1, running
                await asyncio.sleep(0.2)

        await asyncio.gather(*[election(w, 6) for w in workers])
        assert len(running) == 1
        # Kill the holder (stop renewing); another worker takes over after the TTL.
        holder = next(iter(running))
        survivors = [w for w in workers if w.holder != holder]
        running.clear()
        await asyncio.sleep(2.2)
        await asyncio.gather(*[election(w, 3) for w in survivors])
        assert len(running) == 1 and holder not in running
        await tdb.coordination_leases.delete_one({"_id": name})
        # The production scheduler wires every job through run_once.
        src = open(sch.__file__).read()
        for job in ("digest_daily", "digest_weekly", "journals_refresh", "grants_refresh",
                    "conferences_refresh", "orcid_weekly_sync", "citation_daily_sync"):
            assert f'run_once("{job}"' in src, job
        assert "_try_acquire_lock" not in src     # no Redis-or-run-everywhere fallback


# ───────────────────────────── credits ─────────────────────────────

class TestStaleReservations:
    async def test_abandoned_request_reservations_are_returned_once(self, tdb, monkeypatch):
        from services import credits_service as cs
        monkeypatch.setattr(cs, "_db", lambda: tdb)
        uid = ObjectId()
        await tdb.users.insert_one({"_id": uid, "email": f"r-{uid}@synaptiq-test.io", "plan_code": "researcher",
                                    "credits_balance": 10, "credits_pack_balance": 5})
        old = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        fresh = datetime.now(timezone.utc).isoformat()
        base = {"user_id": str(uid), "action": "AI_ASSISTANT_SIMPLE", "credits": 7, "from_monthly": 4,
                "from_pack": 3, "status": "RESERVED"}
        abandoned = (await tdb.credit_reservations.insert_one({**base, "origin": "request", "created_at": old})).inserted_id
        in_flight = (await tdb.credit_reservations.insert_one({**base, "origin": "request", "created_at": fresh})).inserted_id
        background = (await tdb.credit_reservations.insert_one({**base, "origin": "background", "created_at": old})).inserted_id
        try:
            # Two sweepers at once (two workers): each reservation is returned once.
            await asyncio.gather(cs.release_stale_reservations(), cs.release_stale_reservations())
            refunds = await tdb.credit_transactions.count_documents(
                {"user_id": str(uid), "ledger_type": "AI_REFUND"})
            assert refunds == 1
            u = await tdb.users.find_one({"_id": uid})
            assert (u["credits_balance"], u["credits_pack_balance"]) == (14, 8)
            st = {str(d["_id"]): d["status"] async for d in tdb.credit_reservations.find({"user_id": str(uid)})}
            assert st[str(abandoned)] == "RELEASED"
            assert st[str(in_flight)] == "RESERVED" and st[str(background)] == "RESERVED"
        finally:
            await tdb.users.delete_one({"_id": uid})
            await tdb.credit_reservations.delete_many({"user_id": str(uid)})
            await tdb.credit_transactions.delete_many({"user_id": str(uid)})

    def test_sweeper_is_scheduled(self):
        src = open(os.path.join(os.path.dirname(__file__), "..", "worker", "__init__.py")).read()
        assert 'job_type="credits.release_stale"' in src and 'cron_expr="*/10 * * * *"' in src
        from worker.handlers import _registry
        assert "credits.release_stale" in _registry.registered_types()


# ───────────────────────────── storage quota ─────────────────────────────

class TestStorageQuotaConcurrency:
    async def test_parallel_uploads_cannot_exceed_the_limit(self, tdb, monkeypatch):
        from services import permissions as P
        import services.coordination as coord
        # Use this test's client (the app's global client may belong to another loop).
        monkeypatch.setattr(coord, "_db", lambda db=None: db if db is not None else tdb)
        uid = str(ObjectId())
        user = {"id": uid, "role": "user", "plan_code": "researcher"}
        limit = 10 * 1024 * 1024
        monkeypatch.setitem(P.STORAGE_LIMITS_BYTES, "researcher", limit)
        monkeypatch.setattr("services.entitlements.effective_plan_code", lambda u: "researcher")
        stored = []

        async def fake_usage(_uid):
            return sum(stored)
        monkeypatch.setattr(P, "get_user_storage_bytes", fake_usage)

        async def upload(size):
            try:
                async with P.storage_upload_slot(user, size, wait_seconds=10):
                    await asyncio.sleep(0.05)          # storage write
                    stored.append(size)                 # file record committed
                return "ok"
            except HTTPException as e:
                return e.status_code

        results = await asyncio.gather(*[upload(3 * 1024 * 1024) for _ in range(6)])
        assert results.count("ok") == 3 and results.count(402) == 3
        assert sum(stored) <= limit


# ───────────────────────────── client IP ─────────────────────────────

def _req(headers=None, client=("10.0.0.2", 1)):
    return Request({"type": "http", "headers": [(k.encode(), v.encode()) for k, v in (headers or {}).items()],
                    "client": client})


class TestClientIp:
    def test_leftmost_forwarded_for_is_never_trusted(self, monkeypatch):
        from services.client_ip import client_ip
        monkeypatch.delenv("CLIENT_IP_SOURCE", raising=False)
        monkeypatch.delenv("TRUSTED_PROXY_HOPS", raising=False)
        # Attacker-chosen first entry, proxy-appended real address last.
        assert client_ip(_req({"x-forwarded-for": "1.2.3.4, 203.0.113.9"})) == "203.0.113.9"
        # Rotating the spoofed entry does not change the key.
        assert client_ip(_req({"x-forwarded-for": "5.6.7.8, 203.0.113.9"})) == "203.0.113.9"
        # Railway's X-Real-IP wins when present.
        assert client_ip(_req({"x-real-ip": "198.51.100.4", "x-forwarded-for": "1.2.3.4"})) == "198.51.100.4"
        # Garbage is ignored; peer address is the fallback.
        assert client_ip(_req({"x-real-ip": "not-an-ip"})) == "10.0.0.2"

    def test_peer_mode_ignores_headers(self, monkeypatch):
        from services.client_ip import client_ip
        monkeypatch.setenv("CLIENT_IP_SOURCE", "peer")
        assert client_ip(_req({"x-real-ip": "198.51.100.4", "x-forwarded-for": "1.2.3.4"})) == "10.0.0.2"

    def test_rate_limit_key_and_every_ip_consumer_use_the_trusted_helper(self):
        from rate_limit import _client_ip
        assert _client_ip(_req({"x-forwarded-for": "1.2.3.4, 203.0.113.9"})) == "203.0.113.9"
        root = os.path.join(os.path.dirname(__file__), "..")
        for rel in ("rate_limit.py", "middleware/__init__.py", "zt/middleware.py", "routers/consent.py",
                    "routers/growth.py", "services/device_service.py", "services/admin_audit.py",
                    "routers/public_demo.py"):
            src = open(os.path.join(root, rel)).read()
            assert 'split(",")[0]' not in src, rel


# ───────────────────────────── shared rate limits ─────────────────────────────

class TestSharedRateLimit:
    def test_limit_is_shared_between_worker_processes(self):
        """Two limiter instances (two gunicorn workers) on the shared MongoDB storage."""
        from limits import parse
        from limits.storage import storage_from_string
        from limits.strategies import MovingWindowRateLimiter
        opts = {"database_name": os.environ["MONGODB_DB_NAME"],
                "counter_collection_name": "rate_limit_counters",
                "window_collection_name": "rate_limit_windows"}
        w1 = MovingWindowRateLimiter(storage_from_string(os.environ["MONGODB_URI"], **opts))
        w2 = MovingWindowRateLimiter(storage_from_string(os.environ["MONGODB_URI"], **opts))
        limit = parse("5/minute")
        key = f"login-test-{ObjectId()}"
        allowed = [(w1 if i % 2 else w2).hit(limit, key) for i in range(10)]
        assert allowed.count(True) == 5

    def test_storage_selection(self, monkeypatch):
        import rate_limit as rl
        monkeypatch.setenv("APP_ENV", "development")
        monkeypatch.setenv("REDIS_URL", "")
        monkeypatch.delenv("RATE_LIMIT_STORAGE", raising=False)
        uri, opts = rl._storage_config()
        assert uri and uri.startswith("mongodb") and opts["counter_collection_name"] == "rate_limit_counters"
        monkeypatch.setenv("RATE_LIMIT_STORAGE", "memory")
        assert rl._storage_config() == (None, {})
        assert "pw@" not in rl._redact("redis://:pw@redis.internal:6379/0")


# ───────────────────────────── AI budget ─────────────────────────────

class TestAiBudget:
    def test_caps_derive_from_the_explicit_budget(self, monkeypatch):
        from services.ai import budget
        monkeypatch.setenv("AI_MONTHLY_BUDGET_USD", "1000")
        monkeypatch.setenv("AI_SYSTEM_BUDGET_SHARE", "0.05")
        monkeypatch.setenv("AI_EXPECTED_COST_PER_CREDIT_USD", "0.02")
        monkeypatch.setenv("AI_USER_HEADROOM", "2")
        assert budget.system_monthly_cap_usd() == 50.0
        assert budget.system_daily_cap_usd() == pytest.approx(50 * 2 / 30, rel=1e-3)
        assert budget.user_caps_usd("PRO") == (2.0, 8.0)              # 200 credits × $0.02 × 2
        assert budget.user_caps_usd("PRO_ADVANCED") == (7.5, 30.0)    # 750 credits × $0.02 × 2

    def test_default_user_caps_are_below_plan_prices(self):
        from services.ai.pricing import COST_GUARDS
        assert COST_GUARDS["PRO"]["monthly_cost_limit_usd"] < 9.99
        assert COST_GUARDS["PRO_ADVANCED"]["monthly_cost_limit_usd"] < 29.99

    async def test_background_ai_stops_at_its_budget(self, monkeypatch):
        from services.ai import cost_guard

        class _Req:
            model = None; provider = None; max_tokens = 100; messages = None; feature = "nightly_enrichment"

        now = datetime.now(timezone.utc)
        day_id, _ = cost_guard._counter_ids(cost_guard.SYSTEM_COUNTER, now)

        class _Counters:
            def __init__(self):
                self.ai_user_cost_counters = self

            def find(self, q):
                class _C:
                    async def to_list(self, n):
                        return [{"_id": day_id, "cost_usd": 10_000.0}]
                return _C()
        monkeypatch.setattr(cost_guard, "_db", lambda: _Counters())
        with pytest.raises(HTTPException) as exc:
            await cost_guard.preflight(_Req(), "sys", "hello")
        assert exc.value.status_code == 429 and exc.value.detail["code"] == "ai_background_budget"


# ───────────────────────────── password hashing ─────────────────────────────

class TestPasswordHashingDoesNotBlock:
    async def test_event_loop_stays_responsive_during_password_checks(self):
        from auth_utils import hash_password, verify_password_async
        h = hash_password("CorrectHorse1!")
        ticks = []

        async def heartbeat():
            end = time.monotonic() + 0.8
            while time.monotonic() < end:
                ticks.append(time.monotonic())
                await asyncio.sleep(0.01)

        await asyncio.gather(heartbeat(), *[verify_password_async("wrong", h) for _ in range(4)])
        gaps = [b - a for a, b in zip(ticks, ticks[1:])]
        assert max(gaps) < 0.15, f"event loop blocked for {max(gaps):.2f}s"

    async def test_unknown_account_still_costs_a_hash(self):
        from auth_utils import verify_password_async, hash_password
        h = hash_password("x")
        t0 = time.monotonic(); assert await verify_password_async("x", None) is False
        unknown = time.monotonic() - t0
        t0 = time.monotonic(); await verify_password_async("y", h)
        known = time.monotonic() - t0
        assert unknown > known * 0.5


# ───────────────────────────── login privacy ─────────────────────────────

class TestLoginGeolocation:
    async def test_no_external_geolocation_unless_configured_over_https(self, monkeypatch):
        from services import risk_engine
        calls = []

        class _Client:
            def __init__(self, *a, **k): pass
            async def __aenter__(self): return self
            async def __aexit__(self, *a): return False
            async def get(self, url, **k):
                calls.append(url)
                raise RuntimeError("no network in tests")

        monkeypatch.setattr(risk_engine.httpx, "AsyncClient", _Client)
        monkeypatch.delenv("LOGIN_GEOLOCATION_URL", raising=False)
        assert await risk_engine.geolocate("203.0.113.9") == {} and calls == []
        monkeypatch.setenv("LOGIN_GEOLOCATION_URL", "http://ip-api.com/json/{ip}")   # plaintext refused
        assert await risk_engine.geolocate("203.0.113.9") == {} and calls == []
        monkeypatch.setenv("LOGIN_GEOLOCATION_URL", "https://geo.example/{ip}")
        await risk_engine.geolocate("203.0.113.9")
        assert calls == ["https://geo.example/203.0.113.9"]

    def test_login_does_not_wait_for_risk_assessment(self):
        src = open(os.path.join(os.path.dirname(__file__), "..", "routers", "auth.py")).read()
        login = src.split("async def login(")[1].split("\n_background_tasks")[0]
        assert "await geolocate(" not in login and "_spawn_background(_assess_login_risk(" in login
