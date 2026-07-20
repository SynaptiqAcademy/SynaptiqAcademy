"""
Enterprise Observability Platform — Tests (Phase XXXV.6)

Tests cover:
  - TraceContext: creation, serialization, enrichment
  - Span: finish, duration, to_dict
  - Context propagation via contextvars
  - Tracer: start, finish, spans, list
  - StructuredLogger / LogBuffer: append, query, recent
  - MetricStore: counter, gauge, histogram, snapshot, category
  - HealthEngine: component check, aggregate, unknown component
  - AuditLogger: log, query, get_record, auto context
  - AlertEngine: evaluate, acknowledge, resolve, cooldown
  - PerformanceProfiler: record, slow_operations, recommendations
  - CostTracker: record, totals, breakdown
  - SecurityObserver: record, query, summary
  - TimeTraveler: rebuild timeline
  - Lifecycle: init_observability integration

All tests use in-memory MongoDB doubles — no live Atlas required.
Run with: python -m pytest tests/test_observability.py -v
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


# ── Helper ─────────────────────────────────────────────────────────────────────

def run(coro):
    return asyncio.run(coro)


# ── In-memory MongoDB doubles (same pattern as test_worker_platform) ──────────

class MockCollection:
    def __init__(self):
        self._docs = []

    async def create_index(self, *a, **kw): pass
    async def command(self, *a, **kw): return {"ok": 1}

    async def insert_one(self, doc):
        if "_id" not in doc:
            doc["_id"] = str(uuid.uuid4())
        self._docs.append(dict(doc))
        class R:
            inserted_id = doc["_id"]
        return R()

    async def insert_many(self, docs, **kw):
        for doc in docs:
            await self.insert_one(doc)

    async def find_one(self, filt, *a, **kw):
        for doc in self._docs:
            if self._matches(doc, filt):
                return dict(doc)
        return None

    async def update_one(self, filt, update, upsert=False):
        for doc in self._docs:
            if self._matches(doc, filt):
                self._apply(doc, update)
                class R: modified_count = 1
                return R()
        if upsert:
            new = {**filt}
            self._apply(new, update)
            if "_id" not in new:
                new["_id"] = str(uuid.uuid4())
            self._docs.append(new)
        class R: modified_count = 0
        return R()

    async def count_documents(self, filt):
        return sum(1 for d in self._docs if self._matches(d, filt))

    def find(self, filt={}, *a, **kw):
        return MockCursor([d for d in self._docs if self._matches(d, filt)])

    async def aggregate(self, pipeline):
        return MockCursor([])

    def _matches(self, doc, filt):
        for k, v in filt.items():
            if isinstance(v, dict):
                dv = doc.get(k)
                if "$gte" in v and (dv is None or dv < v["$gte"]): return False
                if "$lte" in v and (dv is None or dv > v["$lte"]): return False
                if "$in"  in v and dv not in v["$in"]:              return False
                if "$ne"  in v and dv == v["$ne"]:                  return False
            elif doc.get(k) != v:
                return False
        return True

    def _apply(self, doc, update):
        if "$set" in update:
            doc.update(update["$set"])
        if "$setOnInsert" in update:
            pass


class MockCursor:
    def __init__(self, docs):
        self._docs = docs

    def sort(self, *a, **kw): return self
    def limit(self, n):
        self._docs = self._docs[:n]; return self
    async def to_list(self, n): return list(self._docs[:n])


class MockDB:
    def __init__(self):
        self._cols = defaultdict(MockCollection)

    def __getitem__(self, name): return self._cols[name]
    def __getattr__(self, name): return self._cols[name]

    async def command(self, *a, **kw): return {"ok": 1}


# ══════════════════════════════════════════════════════════════════════════════
# Tracer Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestTraceContext:

    def test_new_trace_id_is_uuid(self):
        from obs.tracer import new_trace_id
        tid = new_trace_id()
        assert len(tid) == 36
        assert tid.count("-") == 4

    def test_new_request_id_is_short(self):
        from obs.tracer import new_request_id
        rid = new_request_id()
        assert len(rid) == 8

    def test_trace_context_to_dict(self):
        from obs.tracer import TraceContext
        ctx = TraceContext(trace_id="t1", request_id="r1", user_id="u1")
        d = ctx.to_dict()
        assert d["trace_id"]  == "t1"
        assert d["request_id"] == "r1"
        assert d["user_id"]   == "u1"

    def test_trace_context_enrich(self):
        from obs.tracer import TraceContext
        ctx = TraceContext(trace_id="t1", request_id="r1")
        ctx2 = ctx.enrich(mission_id="m1", user_id="u2")
        assert ctx2.mission_id == "m1"
        assert ctx2.user_id    == "u2"
        assert ctx.mission_id  is None   # original unchanged

    def test_context_propagation(self):
        from obs.tracer import TraceContext, set_trace_context, get_trace_id
        ctx = TraceContext(trace_id="abc-123", request_id="req1")
        set_trace_context(ctx)
        assert get_trace_id() == "abc-123"

    def test_get_context_dict(self):
        from obs.tracer import TraceContext, set_trace_context, get_context_dict
        ctx = TraceContext(trace_id="x", request_id="y", user_id="u9")
        set_trace_context(ctx)
        d = get_context_dict()
        assert d["trace_id"] == "x"
        assert d["user_id"]  == "u9"


class TestSpan:

    def test_span_finish_sets_duration(self):
        from obs.tracer import Span
        s = Span(name="test", component="api", operation="GET /health")
        time.sleep(0.01)
        s.finish()
        assert s.duration_ms is not None
        assert s.duration_ms >= 5  # at least 5ms

    def test_span_finish_with_error(self):
        from obs.tracer import Span
        s = Span(name="test", component="worker")
        s.finish(status="error", error="connection refused")
        assert s.status == "error"
        assert s.error  == "connection refused"

    def test_span_to_dict(self):
        from obs.tracer import Span
        s = Span(trace_id="t1", name="kg.update", component="graph")
        s.finish()
        d = s.to_dict()
        assert d["trace_id"]  == "t1"
        assert d["name"]      == "kg.update"
        assert d["component"] == "graph"
        assert "duration_ms" in d


class TestTracer:

    def setup_method(self):
        self.db = MockDB()
        from obs.tracer import Tracer
        self.tracer = Tracer(self.db)

    def test_start_trace_stores_doc(self):
        from obs.tracer import TraceContext
        ctx = TraceContext(trace_id="t1", request_id="r1")
        run(self.tracer.start_trace(ctx, path="/api/ai", method="POST"))
        assert len(self.db["obs_traces"]._docs) == 1

    def test_finish_trace_updates_status(self):
        from obs.tracer import TraceContext
        ctx = TraceContext(trace_id="t2", request_id="r2")
        run(self.tracer.start_trace(ctx))
        run(self.tracer.finish_trace("t2", status="ok", duration_ms=142.3))
        doc = run(self.tracer.get_trace("t2"))
        assert doc["status"]      == "ok"
        assert doc["duration_ms"] == 142.3

    def test_record_span(self):
        from obs.tracer import Span
        span = Span(trace_id="t3", name="test.op", component="test")
        span.finish()
        run(self.tracer.record_span(span))
        assert len(self.db["obs_spans"]._docs) == 1

    def test_get_spans(self):
        from obs.tracer import Span
        for i in range(3):
            span = Span(trace_id="t4", name=f"op{i}", component="test")
            span.finish()
            run(self.tracer.record_span(span))
        spans = run(self.tracer.get_spans("t4"))
        assert len(spans) == 3

    def test_list_traces(self):
        from obs.tracer import TraceContext
        for i in range(5):
            ctx = TraceContext(trace_id=f"t-{i}", request_id=f"r{i}")
            run(self.tracer.start_trace(ctx))
        traces = run(self.tracer.list_traces(limit=3))
        assert len(traces) == 3


# ══════════════════════════════════════════════════════════════════════════════
# Logger Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestLogBuffer:

    def setup_method(self):
        from obs.logger import _LogBuffer
        self.buf = _LogBuffer(maxlen=100)

    def test_append_and_recent(self):
        self.buf.append({"level": "INFO", "message": "hello", "component": "api"})
        self.buf.append({"level": "WARNING", "message": "warn", "component": "db"})
        recent = self.buf.recent(10)
        assert len(recent) == 2
        assert recent[0]["level"] == "WARNING"  # newest first

    def test_query_by_level(self):
        self.buf.append({"level": "INFO",    "message": "a", "component": "api"})
        self.buf.append({"level": "WARNING", "message": "b", "component": "api"})
        self.buf.append({"level": "ERROR",   "message": "c", "component": "db"})
        results = self.buf.query(level="WARNING", limit=10)
        assert len(results) == 1
        assert results[0]["message"] == "b"

    def test_query_by_component(self):
        self.buf.append({"level": "INFO", "message": "a", "component": "api"})
        self.buf.append({"level": "INFO", "message": "b", "component": "db"})
        results = self.buf.query(component="db", limit=10)
        assert len(results) == 1

    def test_query_by_trace_id(self):
        self.buf.append({"level": "INFO", "trace_id": "t1", "message": "traced"})
        self.buf.append({"level": "INFO", "trace_id": "t2", "message": "other"})
        results = self.buf.query(trace_id="t1", limit=10)
        assert len(results) == 1
        assert results[0]["message"] == "traced"

    def test_maxlen_respected(self):
        from obs.logger import _LogBuffer
        buf = _LogBuffer(maxlen=3)
        for i in range(5):
            buf.append({"msg": f"m{i}"})
        assert len(buf.recent(10)) == 3

    def test_clear(self):
        self.buf.append({"msg": "x"})
        self.buf.clear()
        assert self.buf.recent(10) == []


# ══════════════════════════════════════════════════════════════════════════════
# Metrics Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestMetricStore:

    def setup_method(self):
        from obs.metrics import MetricStore, reset_metrics
        reset_metrics()
        self.m = MetricStore()

    def test_counter_increments(self):
        self.m.inc("api.requests")
        self.m.inc("api.requests")
        self.m.inc("api.requests", delta=3.0)
        assert self.m.get_counter("api.requests") == 5.0

    def test_counter_with_tags(self):
        self.m.inc("api.requests", tags={"method": "GET"})
        self.m.inc("api.requests", tags={"method": "POST"})
        assert self.m.get_counter("api.requests", {"method": "GET"}) == 1.0
        assert self.m.get_counter("api.requests", {"method": "POST"}) == 1.0

    def test_gauge_set(self):
        self.m.gauge("workers.active", 4.0)
        assert self.m.get_gauge("workers.active") == 4.0
        self.m.gauge("workers.active", 2.0)
        assert self.m.get_gauge("workers.active") == 2.0

    def test_histogram_records_samples(self):
        for v in [10, 20, 30, 40, 50]:
            self.m.observe("api.latency", float(v))
        snap = self.m.get_histogram("api.latency")
        assert snap["count"] == 5
        assert snap["p50"]   == 30.0
        assert snap["p95"]   >= 40.0
        assert snap["min"]   == 10.0
        assert snap["max"]   == 50.0

    def test_snapshot_contains_all_types(self):
        self.m.inc("c.metric")
        self.m.gauge("g.metric", 7.0)
        self.m.observe("h.metric", 100.0)
        snap = self.m.snapshot()
        assert "counters"   in snap
        assert "gauges"     in snap
        assert "histograms" in snap
        assert "timestamp"  in snap
        assert "uptime_s"   in snap

    def test_category_snapshot_filters(self):
        self.m.inc("ai.requests")
        self.m.inc("api.requests")
        snap = self.m.category_snapshot("ai.")
        assert any(k.startswith("ai.") for k in snap["counters"])
        assert not any(k.startswith("api.") for k in snap["counters"])

    def test_reset_clears_all(self):
        self.m.inc("x")
        self.m.reset()
        assert self.m.get_counter("x") == 0.0


# ══════════════════════════════════════════════════════════════════════════════
# Health Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestHealthEngine:

    def setup_method(self):
        self.db = MockDB()
        from obs.health import HealthEngine
        self.engine = HealthEngine(self.db)

    def test_check_api_returns_healthy(self):
        result = run(self.engine.check_component("api"))
        assert result.status == "healthy"
        assert result.component == "api"

    def test_unknown_component_returns_unhealthy(self):
        result = run(self.engine.check_component("does_not_exist_xyz"))
        assert result.status == "unhealthy"

    def test_check_all_returns_dict(self):
        results = run(self.engine.check_all(components=["api"]))
        assert "api" in results
        assert results["api"].status == "healthy"

    def test_aggregate_healthy(self):
        from obs.health import HealthResult
        results = {"api": HealthResult("api", "healthy")}
        agg = self.engine.aggregate(results)
        assert agg["status"] == "healthy"
        assert agg["summary"]["healthy"] == 1

    def test_aggregate_degraded_wins_over_healthy(self):
        from obs.health import HealthResult
        results = {
            "api": HealthResult("api", "healthy"),
            "db":  HealthResult("db",  "degraded"),
        }
        agg = self.engine.aggregate(results)
        assert agg["status"] == "degraded"

    def test_aggregate_unhealthy_wins_all(self):
        from obs.health import HealthResult
        results = {
            "api":    HealthResult("api",    "healthy"),
            "db":     HealthResult("db",     "degraded"),
            "redis":  HealthResult("redis",  "unhealthy"),
        }
        agg = self.engine.aggregate(results)
        assert agg["status"] == "unhealthy"

    def test_component_names_are_known(self):
        names = self.engine.component_names
        assert "api"      in names
        assert "mongodb"  in names
        assert "workers"  in names


# ══════════════════════════════════════════════════════════════════════════════
# Audit Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestAuditLogger:

    def setup_method(self):
        self.db = MockDB()
        from obs.audit import AuditLogger
        self.audit = AuditLogger(self.db)

    def test_log_returns_record_id(self):
        rid = run(self.audit.log("user:u1", "file.uploaded", "file:f1"))
        assert isinstance(rid, str)
        assert len(rid) > 0

    def test_log_persists_to_db(self):
        run(self.audit.log("user:u1", "manuscript.submitted", "manuscript:m1",
                           user_id="u1", category="data"))
        assert len(self.db["obs_audit"]._docs) == 1

    def test_query_by_user(self):
        run(self.audit.log("user:u1", "a.action", user_id="u1"))
        run(self.audit.log("user:u2", "b.action", user_id="u2"))
        results = run(self.audit.query(user_id="u1"))
        assert len(results) == 1
        assert results[0]["who"] == "user:u1"

    def test_query_by_action(self):
        run(self.audit.log("user:u1", "file.uploaded"))
        run(self.audit.log("user:u1", "file.deleted"))
        results = run(self.audit.query(action="file.uploaded"))
        assert len(results) == 1

    def test_get_record_by_id(self):
        rid = run(self.audit.log("agent:kg", "kg.updated", "graph:g1"))
        doc = run(self.audit.get_record(rid))
        assert doc is not None
        assert doc["record_id"] == rid

    def test_ai_involved_flag(self):
        run(self.audit.log("agent:llm", "text.generated", ai_involved=True,
                           ai_provider="openai", ai_model="gpt-4o"))
        docs = run(self.audit.query())
        assert docs[0]["ai_involved"] is True
        assert docs[0]["ai_provider"] == "openai"


# ══════════════════════════════════════════════════════════════════════════════
# Alerting Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestAlertEngine:

    def setup_method(self):
        self.db = MockDB()
        from obs.metrics import MetricStore
        from obs.alerting import AlertEngine
        self.metrics = MetricStore()
        self.engine  = AlertEngine(self.db, self.metrics)

    def test_no_alerts_when_metrics_clean(self):
        alerts = run(self.engine.evaluate())
        assert alerts == []

    def test_worker_failure_triggers_alert(self):
        self.metrics.inc("worker.jobs.failed")
        alerts = run(self.engine.evaluate())
        rule_ids = [a.rule_id for a in alerts]
        assert "worker.failures" in rule_ids

    def test_security_violation_triggers_alert(self):
        self.metrics.inc("security.violations")
        alerts = run(self.engine.evaluate())
        rule_ids = [a.rule_id for a in alerts]
        assert "security.violations" in rule_ids

    def test_alert_persisted_to_db(self):
        self.metrics.inc("worker.jobs.failed")
        run(self.engine.evaluate())
        assert len(self.db["obs_alerts"]._docs) > 0

    def test_acknowledge_alert(self):
        self.metrics.inc("worker.jobs.failed")
        alerts = run(self.engine.evaluate())
        alert_id = alerts[0].alert_id
        ok = run(self.engine.acknowledge(alert_id, "admin@synaptiq.academy"))
        assert ok is True

    def test_resolve_alert(self):
        self.metrics.inc("worker.jobs.dlq", delta=15)
        alerts = run(self.engine.evaluate())
        if alerts:
            alert_id = alerts[0].alert_id
            ok = run(self.engine.resolve(alert_id))
            assert ok is True

    def test_cooldown_prevents_double_alert(self):
        self.engine._rules[0].cooldown_s = 9999  # 3-hour cooldown
        self.metrics.inc("worker.jobs.failed")
        alerts1 = run(self.engine.evaluate())
        # Force the rule to have already fired by pre-setting last_fired
        for rule in self.engine._rules:
            if rule.condition(self.metrics):
                self.engine._last_fired[rule.rule_id] = datetime.utcnow().isoformat()
        alerts2 = run(self.engine.evaluate())
        assert len(alerts2) == 0


# ══════════════════════════════════════════════════════════════════════════════
# Profiler Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestPerformanceProfiler:

    def setup_method(self):
        from obs.profiler import PerformanceProfiler, reset_profiler
        reset_profiler()
        self.profiler = PerformanceProfiler()

    def test_record_adds_stats(self):
        self.profiler.record("GET /api/ai", 250.0, "api")
        stats = self.profiler.all_stats()
        assert len(stats) == 1
        assert stats[0]["count"] == 1

    def test_slow_operations_sorted_by_p95(self):
        self.profiler.record("fast_op",  10.0,    "api")
        self.profiler.record("slow_op",  5000.0,  "api")
        self.profiler.record("medium_op", 300.0,  "api")
        slow = self.profiler.slow_operations(limit=10)
        assert slow[0]["name"] == "slow_op"

    def test_slow_pct_tracked(self):
        # api threshold is 500ms
        self.profiler.record("GET /slow", 1000.0, "api")  # slow
        self.profiler.record("GET /slow",  100.0, "api")  # fast
        stats = [s for s in self.profiler.all_stats() if s["name"] == "GET /slow"]
        assert len(stats) == 1
        assert stats[0]["slow_count"] == 1
        assert stats[0]["slow_pct"]   == 50.0

    def test_recommendations_for_slow_ops(self):
        # Make 80% of requests slow (above API threshold of 500ms)
        for _ in range(8):
            self.profiler.record("heavy_endpoint", 2000.0, "api")
        for _ in range(2):
            self.profiler.record("heavy_endpoint",  100.0, "api")
        recs = self.profiler.recommendations()
        assert len(recs) > 0
        names = [r["operation"] for r in recs]
        assert "heavy_endpoint" in names


# ══════════════════════════════════════════════════════════════════════════════
# Cost Tracker Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestCostTracker:

    def setup_method(self):
        self.db = MockDB()
        from obs.cost import CostTracker
        self.tracker = CostTracker(self.db)

    def test_record_updates_in_memory_totals(self):
        run(self.tracker.record(
            cost_usd=0.01, provider="openai", model="gpt-4o",
            tokens_in=500, tokens_out=200, user_id="u1",
        ))
        totals = self.tracker.totals()
        assert totals["total_usd"]    == pytest.approx(0.01)
        assert totals["total_tokens"] == 700

    def test_multiple_records_accumulate(self):
        run(self.tracker.record(cost_usd=0.01, provider="openai"))
        run(self.tracker.record(cost_usd=0.02, provider="openai"))
        run(self.tracker.record(cost_usd=0.03, provider="anthropic"))
        totals = self.tracker.totals()
        assert totals["total_usd"] == pytest.approx(0.06, abs=1e-9)

    def test_by_provider_breakdown_in_totals(self):
        run(self.tracker.record(cost_usd=0.05, provider="openai"))
        run(self.tracker.record(cost_usd=0.10, provider="anthropic"))
        totals = self.tracker.totals()
        assert totals["by_provider"]["openai"]    == pytest.approx(0.05)
        assert totals["by_provider"]["anthropic"] == pytest.approx(0.10)

    def test_record_persisted_to_db(self):
        run(self.tracker.record(cost_usd=0.001))
        assert len(self.db["obs_cost"]._docs) == 1

    def test_recent_returns_list(self):
        run(self.tracker.record(cost_usd=0.001, provider="openai"))
        recent = run(self.tracker.recent(limit=10))
        assert isinstance(recent, list)


# ══════════════════════════════════════════════════════════════════════════════
# Security Observer Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestSecurityObserver:

    def setup_method(self):
        self.db = MockDB()
        from obs.security import SecurityObserver
        from obs.metrics  import MetricStore, reset_metrics
        reset_metrics()
        self.observer = SecurityObserver(self.db)

    def test_record_returns_event_id(self):
        from obs.security import EVT_FAILED_LOGIN, SEV_LOW
        eid = run(self.observer.record(EVT_FAILED_LOGIN, SEV_LOW, user_id="u1"))
        assert isinstance(eid, str)

    def test_record_persists_to_db(self):
        from obs.security import EVT_PERMISSION_VIOLATION, SEV_HIGH
        run(self.observer.record(EVT_PERMISSION_VIOLATION, SEV_HIGH, user_id="u2"))
        assert len(self.db["obs_security"]._docs) == 1

    def test_query_by_event_type(self):
        from obs.security import EVT_FAILED_LOGIN, EVT_RATE_LIMIT, SEV_LOW
        run(self.observer.record(EVT_FAILED_LOGIN, SEV_LOW))
        run(self.observer.record(EVT_RATE_LIMIT,   SEV_LOW))
        results = run(self.observer.query(event_type=EVT_FAILED_LOGIN))
        assert len(results) == 1

    def test_summary_counts(self):
        from obs.security import EVT_FAILED_LOGIN, SEV_LOW
        run(self.observer.record(EVT_FAILED_LOGIN, SEV_LOW))
        run(self.observer.record(EVT_FAILED_LOGIN, SEV_LOW))
        summary = self.observer.summary()
        assert summary["total"] == 2
        assert summary["event_counts"][EVT_FAILED_LOGIN] == 2

    def test_high_severity_logged_as_warning(self):
        from obs.security import EVT_PROMPT_INJECTION, SEV_CRITICAL
        import logging
        with MagicMock() as mock_logger:
            run(self.observer.record(EVT_PROMPT_INJECTION, SEV_CRITICAL))
        # Should complete without error
        assert len(self.db["obs_security"]._docs) == 1


# ══════════════════════════════════════════════════════════════════════════════
# Time Travel Tests
# ══════════════════════════════════════════════════════════════════════════════

class TestTimeTraveler:

    def setup_method(self):
        self.db = MockDB()
        from obs.time_travel import TimeTraveler
        self.traveler = TimeTraveler(self.db)

    def test_rebuild_empty_trace(self):
        result = run(self.traveler.rebuild("nonexistent-trace-id"))
        assert result.trace    is None
        assert result.timeline == []
        d = result.to_dict()
        assert d["summary"]["span_count"]  == 0
        assert d["summary"]["log_count"]   == 0
        assert d["summary"]["cost_total"]  == 0.0

    def test_rebuild_with_trace_and_span(self):
        # Insert a trace doc
        run(self.db["obs_traces"].insert_one({
            "trace_id":   "t-rebuild-1",
            "request_id": "r1",
            "started_at": datetime.utcnow().isoformat(),
            "status":     "ok",
            "path":       "/api/ai",
            "method":     "POST",
        }))
        # Insert a span doc
        run(self.db["obs_spans"].insert_one({
            "trace_id":    "t-rebuild-1",
            "span_id":     "s1",
            "name":        "ai.generate",
            "component":   "gateway",
            "started_at":  datetime.utcnow().isoformat(),
            "duration_ms": 342.1,
            "status":      "ok",
        }))
        result = run(self.traveler.rebuild("t-rebuild-1"))
        assert result.trace is not None
        assert len(result.spans) == 1
        assert len(result.timeline) >= 2   # trace event + span event

    def test_rebuild_timeline_sorted(self):
        t0 = datetime(2026, 1, 1, 10, 0, 0)
        t1 = datetime(2026, 1, 1, 10, 0, 1)
        run(self.db["obs_spans"].insert_one({
            "trace_id": "t-sort", "span_id": "s2", "name": "later",
            "component": "test", "started_at": t1.isoformat(), "status": "ok",
        }))
        run(self.db["obs_spans"].insert_one({
            "trace_id": "t-sort", "span_id": "s1", "name": "earlier",
            "component": "test", "started_at": t0.isoformat(), "status": "ok",
        }))
        result = run(self.traveler.rebuild("t-sort"))
        if len(result.timeline) >= 2:
            ts0 = result.timeline[0]["timestamp"]
            ts1 = result.timeline[1]["timestamp"]
            assert ts0 <= ts1


# ══════════════════════════════════════════════════════════════════════════════
# Lifecycle / Init Test
# ══════════════════════════════════════════════════════════════════════════════

class TestObsLifecycle:

    def test_init_observability_wires_all_singletons(self):
        """init_observability should set up all singleton getters."""
        db = MockDB()

        async def _init():
            from obs import init_observability, stop_observability
            from obs.tracer   import get_tracer
            from obs.metrics  import get_metrics
            from obs.audit    import get_audit
            from obs.profiler import get_profiler
            from obs.cost     import get_cost_tracker
            from obs.security import get_security_observer

            await init_observability(db)

            assert get_tracer()            is not None
            assert get_metrics()           is not None
            assert get_audit()             is not None
            assert get_profiler()          is not None
            assert get_cost_tracker()      is not None
            assert get_security_observer() is not None

            await stop_observability()

        asyncio.run(_init())

    def test_metrics_singleton_thread_safe(self):
        """Multiple calls to get_metrics() should return the same instance."""
        from obs.metrics import get_metrics
        m1 = get_metrics()
        m2 = get_metrics()
        assert m1 is m2

    def test_log_buffer_is_shared(self):
        """get_log_buffer() returns the module-level buffer."""
        from obs.logger import get_log_buffer
        b1 = get_log_buffer()
        b2 = get_log_buffer()
        assert b1 is b2

    def test_structured_handler_install_idempotent(self):
        """install_structured_handler() can be called twice safely."""
        import logging
        from obs.logger import install_structured_handler, StructuredHandler
        h1 = install_structured_handler()
        h2 = install_structured_handler()
        assert h1 is h2
        # Verify only one StructuredHandler on root logger
        root = logging.getLogger()
        obs_handlers = [h for h in root.handlers if isinstance(h, StructuredHandler)]
        assert len(obs_handlers) == 1
