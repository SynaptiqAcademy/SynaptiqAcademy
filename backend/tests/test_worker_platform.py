"""
Enterprise Worker Platform — Integration Tests (Phase XXXV.5)

Tests cover:
  - Job model serialization / round-trip
  - Priority ordering
  - MongoQueueBackend CRUD (in-memory doubles)
  - WorkerRegistry heartbeat + stale recovery
  - JobRetryPolicy: backoff, transient vs permanent, max attempts
  - CheckpointEngine: save / load / clear
  - JobDLQ: enqueue, list, resolve, delete
  - ExternalCircuitBreaker: state transitions, probe, reset
  - ConcurrencyManager: singleton lock acquire / release / is_locked
  - DependencyGraph: satisfied / unsatisfied deps
  - JobObservability: totals, per-type, per-worker
  - HandlerRegistry: register, get, wildcard
  - JobExecutor: success path, transient retry, permanent DLQ, dependency deferred
  - WorkerPool: instantiation, start/stop interface
  - Scheduler: add_cron / add_once / add_recurring interface, list
  - enqueue_job public API

All tests use in-memory MongoDB doubles — no live Atlas connection required.
Run with: python -m pytest tests/test_worker_platform.py -v
"""
from __future__ import annotations

import asyncio
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


# ── In-memory MongoDB double ──────────────────────────────────────────────────

class MockCollection:
    def __init__(self):
        self._docs: list[dict] = []
        self._indexes: list = []

    async def create_index(self, *args, **kwargs):
        pass

    async def insert_one(self, doc: dict):
        if "_id" not in doc:
            doc["_id"] = str(uuid.uuid4())
        # Enforce unique index on job_id and worker_id (skip None — not a unique constraint in real Mongo)
        for field in ("job_id", "worker_id", "schedule_id", "lock_key"):
            if field in doc and doc[field] is not None:
                for d in self._docs:
                    if d.get(field) == doc[field]:
                        raise Exception(f"E11000 duplicate key: {field}={doc[field]}")
        self._docs.append(dict(doc))

        class InsertResult:
            inserted_id = doc["_id"]
        return InsertResult()

    async def find_one(self, filt: dict, *args, **kwargs) -> dict | None:
        for doc in self._docs:
            if self._matches(doc, filt):
                return dict(doc)
        return None

    async def find_one_and_update(self, filt: dict, update: dict, sort=None, return_document=None, **kwargs) -> dict | None:
        candidates = [d for d in self._docs if self._matches(d, filt)]

        if sort:
            def sort_key(d):
                keys = []
                for field, direction in sort:
                    val = d.get(field)
                    if isinstance(val, (int, float)):
                        keys.append(val * direction)
                    elif isinstance(val, str):
                        # For strings (ISO dates, etc.), sort lexicographically
                        keys.append(val if direction > 0 else "".join(chr(0x10FFFF - ord(c)) for c in val))
                    else:
                        keys.append(0)
                return keys
            candidates.sort(key=sort_key)

        if not candidates:
            return None
        doc = candidates[0]
        self._apply_update(doc, update)
        return dict(doc)

    async def update_one(self, filt: dict, update: dict, upsert=False) -> Any:
        for doc in self._docs:
            if self._matches(doc, filt):
                self._apply_update(doc, update)

                class UpdateResult:
                    modified_count = 1
                return UpdateResult()

        if upsert:
            new_doc = {**filt}
            self._apply_update(new_doc, update)
            if "_id" not in new_doc:
                new_doc["_id"] = str(uuid.uuid4())
            self._docs.append(new_doc)

        class UpdateResult:
            modified_count = 0
        return UpdateResult()

    async def update_many(self, filt: dict, update: dict) -> Any:
        count = 0
        for doc in self._docs:
            if self._matches(doc, filt):
                self._apply_update(doc, update)
                count += 1

        class UpdateResult:
            modified_count = count
        return UpdateResult()

    async def delete_one(self, filt: dict) -> Any:
        for i, doc in enumerate(self._docs):
            if self._matches(doc, filt):
                self._docs.pop(i)
                class R:
                    deleted_count = 1
                return R()
        class R:
            deleted_count = 0
        return R()

    async def count_documents(self, filt: dict) -> int:
        return sum(1 for d in self._docs if self._matches(d, filt))

    def find(self, filt: dict = {}, *args, **kwargs):
        return MockCursor([d for d in self._docs if self._matches(d, filt)])

    async def aggregate(self, pipeline: list) -> "MockCursor":
        return MockCursor([])

    def _matches(self, doc: dict, filt: dict) -> bool:
        for k, v in filt.items():
            if isinstance(v, dict):
                dv = doc.get(k)
                if "$in" in v:
                    if dv not in v["$in"]:
                        return False
                elif "$lte" in v:
                    if dv is None or dv > v["$lte"]:
                        return False
                elif "$gte" in v:
                    if dv is None or dv < v["$gte"]:
                        return False
                elif "$lt" in v:
                    if dv is None or dv >= v["$lt"]:
                        return False
                elif "$ne" in v:
                    if dv == v["$ne"]:
                        return False
            else:
                if doc.get(k) != v:
                    return False
        return True

    def _apply_update(self, doc: dict, update: dict):
        if "$set" in update:
            doc.update(update["$set"])
        if "$inc" in update:
            for k, v in update["$inc"].items():
                doc[k] = doc.get(k, 0) + v
        if "$setOnInsert" in update:
            pass  # only on insert, skip here


class MockCursor:
    def __init__(self, docs: list):
        self._docs = docs

    def sort(self, *args, **kwargs):
        return self

    def limit(self, n: int):
        self._docs = self._docs[:n]
        return self

    async def to_list(self, n: int) -> list:
        return list(self._docs[:n])


class MockDB:
    def __init__(self):
        self._cols: dict[str, MockCollection] = defaultdict(MockCollection)

    def __getitem__(self, name: str) -> MockCollection:
        return self._cols[name]

    def __getattr__(self, name: str) -> MockCollection:
        return self._cols[name]


# ── Helpers ───────────────────────────────────────────────────────────────────

def run(coro):
    return asyncio.run(coro)


# ══════════════════════════════════════════════════════════════════════════════
# Job Model Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestJobModel:

    def test_job_default_status(self):
        from worker.models import Job, JobStatus
        j = Job(job_type="test.job", payload={})
        assert j.status == JobStatus.PENDING

    def test_job_serialization_round_trip(self):
        from worker.models import Job, JobStatus, Priority
        j = Job(
            job_type="kg.update",
            payload={"entity": "pub:123"},
            priority=Priority.HIGH,
            user_id="user_abc",
            depends_on=["job_xyz"],
        )
        d  = j.to_dict()
        j2 = Job.from_dict(d)
        assert j2.job_id    == j.job_id
        assert j2.job_type  == "kg.update"
        assert j2.priority  == Priority.HIGH
        assert j2.user_id   == "user_abc"
        assert j2.depends_on == ["job_xyz"]

    def test_priority_ordering(self):
        from worker.models import Priority
        assert Priority.CRITICAL < Priority.HIGH < Priority.NORMAL < Priority.LOW < Priority.BACKGROUND

    def test_job_type_constants(self):
        from worker.models import ALL_JOB_TYPES, JOB_AI_EXECUTION, JOB_GRAPH_REBUILD
        assert JOB_AI_EXECUTION in ALL_JOB_TYPES
        assert JOB_GRAPH_REBUILD in ALL_JOB_TYPES
        assert len(ALL_JOB_TYPES) >= 20

    def test_worker_info_round_trip(self):
        from worker.models import WorkerInfo
        w = WorkerInfo(worker_id="w1", queue_names=["default"], job_types=["ai.execution"], concurrency=4)
        d  = w.to_dict()
        w2 = WorkerInfo.from_dict(d)
        assert w2.worker_id   == "w1"
        assert w2.concurrency == 4

    def test_schedule_round_trip(self):
        from worker.models import Schedule, Priority
        s = Schedule(
            schedule_id="s1", job_type="orcid.weekly_sync", payload={},
            mode="cron", cron_expr="0 2 * * 0", priority=Priority.LOW,
        )
        d  = s.to_dict()
        s2 = Schedule.from_dict(d)
        assert s2.schedule_id == "s1"
        assert s2.cron_expr   == "0 2 * * 0"


# ══════════════════════════════════════════════════════════════════════════════
# Queue Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestMongoQueue:

    def setup_method(self):
        self.db = MockDB()
        from worker.queue import MongoQueueBackend
        self.q = MongoQueueBackend(self.db)

    def test_enqueue_sets_queued_status(self):
        from worker.models import Job
        j = Job(job_type="ai.execution", payload={})
        run(self.q.enqueue(j))
        fetched = run(self.q.get_job(j.job_id))
        assert fetched is not None
        from worker.models import JobStatus
        assert fetched.status == JobStatus.QUEUED

    def test_dequeue_atomic(self):
        from worker.models import Job
        j = Job(job_type="ai.execution", payload={})
        run(self.q.enqueue(j))
        result = run(self.q.dequeue("default", "worker-1", ["ai.execution"]))
        assert result is not None
        assert result.job_id == j.job_id

    def test_dequeue_respects_priority(self):
        from worker.models import Job, Priority
        j_low  = Job(job_type="ai.execution", payload={}, priority=Priority.LOW)
        j_high = Job(job_type="ai.execution", payload={}, priority=Priority.CRITICAL)
        run(self.q.enqueue(j_low))
        run(self.q.enqueue(j_high))
        first = run(self.q.dequeue("default", "w1", ["ai.execution"]))
        assert first.job_id == j_high.job_id

    def test_dequeue_wrong_type_returns_none(self):
        from worker.models import Job
        j = Job(job_type="ai.execution", payload={})
        run(self.q.enqueue(j))
        result = run(self.q.dequeue("default", "w1", ["kg.update"]))
        assert result is None

    def test_ack_marks_completed(self):
        from worker.models import Job, JobStatus
        j = Job(job_type="ai.execution", payload={})
        run(self.q.enqueue(j))
        run(self.q.dequeue("default", "w1", []))
        run(self.q.ack(j.job_id))
        fetched = run(self.q.get_job(j.job_id))
        assert fetched.status == JobStatus.COMPLETED

    def test_nack_with_retry_sets_retrying(self):
        from worker.models import Job, JobStatus
        j = Job(job_type="ai.execution", payload={})
        run(self.q.enqueue(j))
        run(self.q.dequeue("default", "w1", []))
        retry_at = datetime.utcnow() + timedelta(seconds=5)
        run(self.q.nack(j.job_id, "timeout error", retry_at=retry_at))
        fetched = run(self.q.get_job(j.job_id))
        assert fetched.status == JobStatus.RETRYING

    def test_nack_without_retry_sets_failed(self):
        from worker.models import Job, JobStatus
        j = Job(job_type="ai.execution", payload={})
        run(self.q.enqueue(j))
        run(self.q.dequeue("default", "w1", []))
        run(self.q.nack(j.job_id, "permanent error"))
        fetched = run(self.q.get_job(j.job_id))
        assert fetched.status == JobStatus.FAILED

    def test_cancel_pending_job(self):
        from worker.models import Job, JobStatus
        j = Job(job_type="ai.execution", payload={})
        run(self.q.enqueue(j))
        done = run(self.q.cancel(j.job_id))
        assert done
        fetched = run(self.q.get_job(j.job_id))
        assert fetched.status == JobStatus.CANCELLED

    def test_requeue_failed_job(self):
        from worker.models import Job, JobStatus
        j = Job(job_type="ai.execution", payload={})
        run(self.q.enqueue(j))
        run(self.q.mark_failed(j.job_id, "test error"))
        done = run(self.q.requeue(j.job_id))
        assert done
        fetched = run(self.q.get_job(j.job_id))
        assert fetched.status == JobStatus.QUEUED

    def test_idempotent_enqueue(self):
        from worker.models import Job
        j = Job(job_type="ai.execution", payload={}, job_id="fixed-id")
        run(self.q.enqueue(j))
        # Second enqueue should not raise
        run(self.q.enqueue(j))
        docs = run(self.q.list_jobs())
        assert sum(1 for d in docs if d.job_id == "fixed-id") == 1

    def test_checkpoint_update(self):
        from worker.models import Job
        j = Job(job_type="data.import", payload={})
        run(self.q.enqueue(j))
        run(self.q.update_checkpoint(j.job_id, {"offset": 100}))
        fetched = run(self.q.get_job(j.job_id))
        assert fetched.checkpoint == {"offset": 100}


# ══════════════════════════════════════════════════════════════════════════════
# Worker Registry Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestWorkerRegistry:

    def setup_method(self):
        self.db = MockDB()
        from worker.registry import WorkerRegistry
        self.reg = WorkerRegistry(self.db)

    def test_register_and_get(self):
        from worker.models import WorkerInfo
        w = WorkerInfo(worker_id="w1", queue_names=["default"], job_types=["ai.execution"], concurrency=4)
        run(self.reg.register(w))
        fetched = run(self.reg.get("w1"))
        assert fetched is not None
        assert fetched.worker_id == "w1"

    def test_deregister(self):
        from worker.models import WorkerInfo
        w = WorkerInfo(worker_id="w2", queue_names=["default"], job_types=[], concurrency=4)
        run(self.reg.register(w))
        run(self.reg.deregister("w2"))
        fetched = run(self.reg.get("w2"))
        assert fetched is None

    def test_heartbeat_updates_status(self):
        from worker.models import WorkerInfo
        w = WorkerInfo(worker_id="w3", queue_names=["default"], job_types=[], concurrency=4)
        run(self.reg.register(w))
        run(self.reg.heartbeat("w3", ["job1"], 0.5))
        fetched = run(self.reg.get("w3"))
        assert fetched.load == 0.5

    def test_mark_unhealthy(self):
        from worker.models import WorkerInfo
        w = WorkerInfo(worker_id="w4", queue_names=["default"], job_types=[], concurrency=4)
        run(self.reg.register(w))
        run(self.reg.mark_unhealthy("w4"))
        fetched = run(self.reg.get("w4"))
        assert fetched.status == "unhealthy"


# ══════════════════════════════════════════════════════════════════════════════
# Retry Policy Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestRetryPolicy:

    def test_transient_error_retried(self):
        from worker.retry import should_retry, DEFAULT_JOB_RETRY_POLICY
        exc = ConnectionError("connection reset by peer")
        assert should_retry(exc, 0, DEFAULT_JOB_RETRY_POLICY) is True
        assert should_retry(exc, 1, DEFAULT_JOB_RETRY_POLICY) is True

    def test_max_attempts_stops_retry(self):
        from worker.retry import should_retry, DEFAULT_JOB_RETRY_POLICY
        exc = ConnectionError("timeout")
        assert should_retry(exc, 3, DEFAULT_JOB_RETRY_POLICY) is False

    def test_permanent_error_not_retried(self):
        from worker.retry import should_retry, DEFAULT_JOB_RETRY_POLICY
        exc = ValueError("bad payload")
        assert should_retry(exc, 0, DEFAULT_JOB_RETRY_POLICY) is False

    def test_type_error_permanent(self):
        from worker.retry import should_retry, DEFAULT_JOB_RETRY_POLICY
        exc = TypeError("missing argument")
        assert should_retry(exc, 0, DEFAULT_JOB_RETRY_POLICY) is False

    def test_backoff_increases(self):
        from worker.retry import compute_retry_at, JobRetryPolicy
        policy = JobRetryPolicy(initial_delay_s=1.0, backoff_factor=2.0, jitter=False)
        t0 = datetime.utcnow()
        r0 = compute_retry_at(0, policy)
        r1 = compute_retry_at(1, policy)
        assert r1 > r0

    def test_classify_transient(self):
        from worker.retry import classify_error
        assert classify_error(ConnectionError("connection refused")) == "transient"
        assert classify_error(RuntimeError("rate limit exceeded")) == "transient"

    def test_classify_permanent(self):
        from worker.retry import classify_error
        assert classify_error(ValueError("bad input")) == "permanent"
        assert classify_error(KeyError("missing key")) == "permanent"


# ══════════════════════════════════════════════════════════════════════════════
# Checkpoint Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestCheckpoint:

    def setup_method(self):
        self.db = MockDB()
        from worker.queue import MongoQueueBackend
        from worker.checkpoint import CheckpointEngine
        self.q  = MongoQueueBackend(self.db)
        self.cp = CheckpointEngine(self.q)

    def test_save_and_load(self):
        from worker.models import Job
        j = Job(job_type="data.import", payload={})
        run(self.q.enqueue(j))
        run(self.cp.save(j.job_id, {"offset": 50, "page": 2}))
        loaded = run(self.cp.load(j.job_id))
        assert loaded["offset"] == 50
        assert loaded["page"]   == 2

    def test_load_returns_empty_for_unknown(self):
        loaded = run(self.cp.load("nonexistent-job-id"))
        assert loaded == {}

    def test_clear_removes_checkpoint(self):
        from worker.models import Job
        j = Job(job_type="data.import", payload={})
        run(self.q.enqueue(j))
        run(self.cp.save(j.job_id, {"offset": 99}))
        run(self.cp.clear(j.job_id))
        loaded = run(self.cp.load(j.job_id))
        assert loaded == {}


# ══════════════════════════════════════════════════════════════════════════════
# DLQ Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestJobDLQ:

    def setup_method(self):
        self.db = MockDB()
        from worker.dlq import JobDLQ
        self.dlq = JobDLQ(self.db)

    def test_enqueue_and_list(self):
        from worker.models import Job
        j = Job(job_type="ai.execution", payload={})
        run(self.dlq.enqueue(j, "permanent failure", 3))
        items = run(self.dlq.list_pending())
        assert len(items) == 1
        assert items[0]["job_id"] == j.job_id

    def test_idempotent_enqueue(self):
        from worker.models import Job
        j = Job(job_type="ai.execution", payload={}, job_id="dlq-fixed")
        run(self.dlq.enqueue(j, "error", 3))
        run(self.dlq.enqueue(j, "error", 3))  # should not raise
        items = run(self.dlq.list_pending())
        assert len(items) == 1

    def test_pending_count(self):
        from worker.models import Job
        j1 = Job(job_type="ai.execution", payload={})
        j2 = Job(job_type="kg.update", payload={})
        run(self.dlq.enqueue(j1, "err", 3))
        run(self.dlq.enqueue(j2, "err", 3))
        assert run(self.dlq.pending_count()) == 2

    def test_mark_resolved(self):
        from worker.models import Job
        j = Job(job_type="ai.execution", payload={})
        run(self.dlq.enqueue(j, "err", 3))
        run(self.dlq.mark_resolved(j.job_id, "fixed manually"))
        items = run(self.dlq.list_pending())
        assert len(items) == 0

    def test_delete(self):
        from worker.models import Job
        j = Job(job_type="ai.execution", payload={})
        run(self.dlq.enqueue(j, "err", 3))
        deleted = run(self.dlq.delete(j.job_id))
        assert deleted is True
        assert run(self.dlq.pending_count()) == 0


# ══════════════════════════════════════════════════════════════════════════════
# Circuit Breaker Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestExternalCircuitBreaker:

    def setup_method(self):
        from worker.circuit_breaker import ExternalCircuitBreakerRegistry, ExternalDep
        self.reg = ExternalCircuitBreakerRegistry()
        self.dep = ExternalDep.LLM_ANTHROPIC

    def test_initial_state_closed(self):
        from worker.circuit_breaker import CBState
        cb = self.reg.get(self.dep)
        assert cb.state == CBState.CLOSED
        assert cb.allow_request() is True

    def test_opens_after_threshold(self):
        from worker.circuit_breaker import CBState
        cb = self.reg.get(self.dep)
        cb.failure_threshold = 3
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CBState.OPEN
        assert cb.allow_request() is False

    def test_transitions_to_half_open_after_timeout(self):
        from worker.circuit_breaker import CBState
        cb = self.reg.get(self.dep)
        cb.failure_threshold = 1
        cb.recovery_timeout_s = 0.01
        cb.record_failure()
        time.sleep(0.02)
        assert cb.state == CBState.HALF_OPEN
        assert cb.allow_request() is True

    def test_closes_after_successes_in_half_open(self):
        from worker.circuit_breaker import CBState
        cb = self.reg.get(self.dep)
        cb.failure_threshold   = 1
        cb.success_threshold   = 2
        cb.recovery_timeout_s  = 0.01
        cb.record_failure()
        time.sleep(0.02)
        # now half-open
        cb.record_success()
        cb.record_success()
        assert cb.state == CBState.CLOSED

    def test_manual_reset(self):
        from worker.circuit_breaker import CBState
        cb = self.reg.get(self.dep)
        cb.failure_threshold = 1
        cb.record_failure()
        assert cb.state == CBState.OPEN
        cb.reset()
        assert cb.state == CBState.CLOSED


# ══════════════════════════════════════════════════════════════════════════════
# Concurrency Manager Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestConcurrencyManager:

    def setup_method(self):
        self.db = MockDB()
        from worker.concurrency import ConcurrencyManager
        self.mgr = ConcurrencyManager(self.db)

    def test_acquire_lock(self):
        acquired = run(self.mgr.acquire_distributed_lock("lock:test"))
        assert acquired is True

    def test_duplicate_lock_fails(self):
        run(self.mgr.acquire_distributed_lock("lock:singleton"))
        second = run(self.mgr.acquire_distributed_lock("lock:singleton"))
        assert second is False

    def test_release_allows_reacquire(self):
        run(self.mgr.acquire_distributed_lock("lock:release-test"))
        run(self.mgr.release_distributed_lock("lock:release-test"))
        reacquired = run(self.mgr.acquire_distributed_lock("lock:release-test"))
        assert reacquired is True

    def test_is_locked(self):
        assert run(self.mgr.is_locked("lock:new")) is False
        run(self.mgr.acquire_distributed_lock("lock:new"))
        assert run(self.mgr.is_locked("lock:new")) is True

    def test_singleton_job_types(self):
        from worker.concurrency import SINGLETON_JOB_TYPES
        assert "orcid.weekly_sync" in SINGLETON_JOB_TYPES
        assert "graph.rebuild" in SINGLETON_JOB_TYPES

    def test_semaphore_created_for_limited_type(self):
        import asyncio
        sem = self.mgr.get_semaphore("ai.execution")
        assert sem is not None
        assert isinstance(sem, asyncio.Semaphore)

    def test_no_semaphore_for_unlimited_type(self):
        sem = self.mgr.get_semaphore("unknown.job.type")
        assert sem is None


# ══════════════════════════════════════════════════════════════════════════════
# Dependency Graph Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestDependencyGraph:

    def setup_method(self):
        self.db = MockDB()
        from worker.queue import MongoQueueBackend
        from worker.dependency import DependencyGraph
        self.q    = MongoQueueBackend(self.db)
        self.deps = DependencyGraph(self.q)

    def test_no_deps_always_satisfied(self):
        from worker.models import Job
        j = Job(job_type="kg.update", payload={}, depends_on=[])
        assert run(self.deps.all_satisfied(j)) is True

    def test_completed_dep_satisfied(self):
        from worker.models import Job, JobStatus
        dep = Job(job_type="data.import", payload={})
        run(self.q.enqueue(dep))
        run(self.q.dequeue("default", "w1", []))
        run(self.q.ack(dep.job_id))

        child = Job(job_type="kg.update", payload={}, depends_on=[dep.job_id])
        assert run(self.deps.all_satisfied(child)) is True

    def test_pending_dep_not_satisfied(self):
        from worker.models import Job
        dep   = Job(job_type="data.import", payload={})
        run(self.q.enqueue(dep))
        child = Job(job_type="kg.update", payload={}, depends_on=[dep.job_id])
        assert run(self.deps.all_satisfied(child)) is False

    def test_missing_dep_not_satisfied(self):
        from worker.models import Job
        child = Job(job_type="kg.update", payload={}, depends_on=["nonexistent-job"])
        assert run(self.deps.all_satisfied(child)) is False


# ══════════════════════════════════════════════════════════════════════════════
# Observability Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestJobObservability:

    def setup_method(self):
        from worker.observability import JobObservability, reset_job_observability
        reset_job_observability()
        self.obs = JobObservability()

    def test_record_success_updates_totals(self):
        self.obs.record_enqueued("ai.execution")
        self.obs.record_start("ai.execution", "w1")
        self.obs.record_success("ai.execution", "w1", 50.0, cost_usd=0.001, tokens=100)
        snap = self.obs.snapshot()
        assert snap["totals"]["enqueued"]  == 1
        assert snap["totals"]["completed"] == 1
        assert snap["totals"]["failed"]    == 0

    def test_record_failure_updates_totals(self):
        self.obs.record_failure("ai.execution", "w1")
        snap = self.obs.snapshot()
        assert snap["totals"]["failed"] == 1

    def test_per_type_metrics(self):
        self.obs.record_success("kg.update", "w1", 100.0)
        self.obs.record_success("kg.update", "w1", 200.0)
        snap = self.obs.snapshot()
        by_type = {m["job_type"]: m for m in snap["by_job_type"]}
        assert by_type["kg.update"]["successes"] == 2

    def test_ema_latency(self):
        self.obs.record_success("ai.execution", "w1", 1000.0)
        snap = self.obs.snapshot()
        by_type = {m["job_type"]: m for m in snap["by_job_type"]}
        assert by_type["ai.execution"]["ema_latency_ms"] > 0

    def test_dlq_tracking(self):
        self.obs.record_dlq("ai.execution")
        snap = self.obs.snapshot()
        assert snap["totals"]["dlq"] == 1


# ══════════════════════════════════════════════════════════════════════════════
# Handler Registry Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestHandlerRegistry:

    def test_all_job_types_registered(self):
        from worker.handlers import get_handler_registry
        from worker.models   import ALL_JOB_TYPES
        reg   = get_handler_registry()
        types = reg.registered_types()
        for jt in ALL_JOB_TYPES:
            assert jt in types, f"Handler missing for {jt}"

    def test_custom_handler_registration(self):
        from worker.handlers import HandlerRegistry, HandlerResult
        from worker.models   import Job
        reg = HandlerRegistry()

        @reg.register("custom.test")
        async def my_handler(job, ctx):
            return HandlerResult(output={"done": True})

        assert reg.get("custom.test") is not None

    def test_get_returns_none_for_unknown(self):
        from worker.handlers import HandlerRegistry
        reg = HandlerRegistry()
        assert reg.get("nonexistent.type") is None


# ══════════════════════════════════════════════════════════════════════════════
# Job Executor Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestJobExecutor:

    def setup_method(self):
        self.db = MockDB()
        from worker.queue        import MongoQueueBackend
        from worker.dlq          import JobDLQ
        from worker.concurrency  import ConcurrencyManager
        from worker.executor     import JobExecutor
        from worker.handlers     import HandlerRegistry, HandlerResult
        from worker.observability import reset_job_observability

        reset_job_observability()

        self.q   = MongoQueueBackend(self.db)
        self.dlq = JobDLQ(self.db)
        self.mgr = ConcurrencyManager(self.db)

        # Register test handlers
        self.handler_reg = HandlerRegistry()

        @self.handler_reg.register("test.success")
        async def success_handler(job, ctx):
            return HandlerResult(output={"ok": True})

        @self.handler_reg.register("test.transient_fail")
        async def transient_handler(job, ctx):
            raise ConnectionError("connection reset by peer")

        @self.handler_reg.register("test.permanent_fail")
        async def permanent_handler(job, ctx):
            raise ValueError("invalid payload")

        self.executor = JobExecutor(
            db=self.db, concurrency=self.mgr, dlq=self.dlq, queue=self.q
        )
        # Inject test registry
        self.executor._registry = self.handler_reg

    def test_success_marks_completed(self):
        from worker.models import Job, JobStatus
        j = Job(job_type="test.success", payload={})
        run(self.q.enqueue(j))
        job = run(self.q.dequeue("default", "w1", ["test.success"]))
        run(self.executor.execute(job, "w1"))
        fetched = run(self.q.get_job(j.job_id))
        assert fetched.status == JobStatus.COMPLETED

    def test_transient_failure_retries(self):
        from worker.models import Job, JobStatus
        j = Job(job_type="test.transient_fail", payload={}, max_attempts=3)
        run(self.q.enqueue(j))
        job = run(self.q.dequeue("default", "w1", ["test.transient_fail"]))
        run(self.executor.execute(job, "w1"))
        fetched = run(self.q.get_job(j.job_id))
        # Should be RETRYING (not FAILED) on first attempt
        assert fetched.status == JobStatus.RETRYING

    def test_permanent_failure_goes_to_dlq(self):
        from worker.models import Job, JobStatus
        j = Job(job_type="test.permanent_fail", payload={}, max_attempts=3)
        run(self.q.enqueue(j))
        job = run(self.q.dequeue("default", "w1", ["test.permanent_fail"]))
        run(self.executor.execute(job, "w1"))
        fetched = run(self.q.get_job(j.job_id))
        assert fetched.status == JobStatus.FAILED
        dlq_items = run(self.dlq.list_pending())
        assert any(d["job_id"] == j.job_id for d in dlq_items)

    def test_no_handler_marks_failed(self):
        from worker.models import Job, JobStatus
        j = Job(job_type="unknown.type.xyz", payload={})
        run(self.q.enqueue(j))
        job = run(self.q.dequeue("default", "w1", []))
        run(self.executor.execute(job, "w1"))
        fetched = run(self.q.get_job(j.job_id))
        assert fetched.status == JobStatus.FAILED

    def test_dependency_not_met_marks_waiting(self):
        from worker.models import Job, JobStatus
        dep   = Job(job_type="data.import", payload={})
        run(self.q.enqueue(dep))
        child = Job(job_type="test.success", payload={}, depends_on=[dep.job_id])
        run(self.q.enqueue(child))
        job = run(self.q.dequeue("default", "w1", ["test.success"]))
        assert job is not None
        run(self.executor.execute(job, "w1"))
        fetched = run(self.q.get_job(child.job_id))
        assert fetched.status == JobStatus.WAITING


# ══════════════════════════════════════════════════════════════════════════════
# enqueue_job public API Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestEnqueueJobAPI:

    def test_enqueue_job_returns_job_id(self):
        db = MockDB()
        from worker import enqueue_job
        from worker.models import Job
        j = Job(job_type="ai.execution", payload={"prompt": "hello"}, user_id="u1")
        job_id = run(enqueue_job(j, db))
        assert job_id == j.job_id

    def test_enqueue_job_is_queued_in_db(self):
        db = MockDB()
        from worker import enqueue_job
        from worker.queue import MongoQueueBackend
        from worker.models import Job, JobStatus
        j = Job(job_type="kg.update", payload={})
        run(enqueue_job(j, db))
        q = MongoQueueBackend(db)
        fetched = run(q.get_job(j.job_id))
        assert fetched is not None
        assert fetched.status == JobStatus.QUEUED

    def test_enqueue_job_updates_observability(self):
        db = MockDB()
        from worker import enqueue_job
        from worker.models import Job
        from worker.observability import reset_job_observability, get_job_observability
        reset_job_observability()
        j = Job(job_type="twin.update", payload={})
        run(enqueue_job(j, db))
        snap = get_job_observability().snapshot()
        assert snap["totals"]["enqueued"] == 1


# ══════════════════════════════════════════════════════════════════════════════
# WorkerPool Interface Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestWorkerPool:

    def test_worker_pool_instantiation(self):
        db = MockDB()
        from worker.worker import WorkerPool
        pool = WorkerPool(db)
        assert pool.worker_count == 0

    def test_set_and_get_worker_pool(self):
        db = MockDB()
        from worker.worker import WorkerPool, _set_worker_pool, get_worker_pool
        pool = WorkerPool(db)
        _set_worker_pool(pool)
        assert get_worker_pool() is pool
        _set_worker_pool(None)
        assert get_worker_pool() is None


# ══════════════════════════════════════════════════════════════════════════════
# Scheduler Interface Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestSchedulerInterface:

    def setup_method(self):
        self.db = MockDB()
        from worker.queue import MongoQueueBackend
        self.q = MongoQueueBackend(self.db)

    def test_add_cron_persists_schedule(self):
        from worker.scheduler import Scheduler
        from unittest.mock import patch, MagicMock

        with patch("worker.scheduler.AsyncIOScheduler") as MockAPS:
            instance = MagicMock()
            MockAPS.return_value = instance
            sched = Scheduler(self.db, self.q)
            # manually call _ensure_indexes inline by mocking
            sched._aps = instance

            run(sched._ensure_indexes())
            sid = run(sched.add_cron(
                job_type="orcid.weekly_sync",
                payload={},
                cron_expr="0 2 * * 0",
                schedule_id="test-cron-1",
            ))
            assert sid == "test-cron-1"
            scheds = run(sched.list_schedules())
            assert any(s.schedule_id == "test-cron-1" for s in scheds)

    def test_add_once_persists_schedule(self):
        from worker.scheduler import Scheduler
        from unittest.mock import patch, MagicMock

        with patch("worker.scheduler.AsyncIOScheduler") as MockAPS:
            instance = MagicMock()
            MockAPS.return_value = instance
            sched = Scheduler(self.db, self.q)
            sched._aps = instance

            run(sched._ensure_indexes())
            run_at = datetime.utcnow() + timedelta(hours=1)
            sid = run(sched.add_once(
                job_type="report.generate",
                payload={"report_type": "annual"},
                run_at=run_at,
                schedule_id="test-once-1",
            ))
            assert sid == "test-once-1"
            s = run(sched.get("test-once-1"))
            assert s is not None
            assert s.mode == "once"

    def test_remove_schedule(self):
        from worker.scheduler import Scheduler
        from unittest.mock import patch, MagicMock

        with patch("worker.scheduler.AsyncIOScheduler") as MockAPS:
            instance = MagicMock()
            MockAPS.return_value = instance
            sched = Scheduler(self.db, self.q)
            sched._aps = instance

            run(sched._ensure_indexes())
            run(sched.add_recurring(
                job_type="citation.monitor",
                payload={},
                interval_s=3600,
                schedule_id="test-recurring-1",
            ))
            run(sched.remove("test-recurring-1"))
            s = run(sched.get("test-recurring-1"))
            assert s is None
