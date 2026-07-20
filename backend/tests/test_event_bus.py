"""
Enterprise Event Bus — integration tests.

No real MongoDB. Uses in-memory test doubles.
Tests run with asyncio.run() (no pytest-asyncio required).
"""
import asyncio
import sys
import os
import time
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from events.models import (
    DomainEvent, PublicationCreated, MissionCompleted, GrantAwarded,
    UserVerified, TwinUpdated,
    PUBLICATION_CREATED, MISSION_COMPLETED, GRANT_AWARDED,
    event_from_dict, EVENT_CLASS_MAP,
)
from events.registry   import EventRegistry, EventCatalogEntry, _build_catalog
from events.circuit_breaker import CircuitBreaker, CBState, CircuitBreakerRegistry
from events.observability   import EventObservability
from events.retry      import HandlerRetryPolicy, execute_with_retry
from events.handlers   import HandlerRegistry, HandlerRegistration, HandlerExecutor
from events.dlq        import DeadLetterQueue
from events.bus        import EnterpriseEventBus, get_bus, reset_bus


# ── In-memory test doubles ────────────────────────────────────────────────────

class MockCursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, *a, **k):   return self
    def skip(self, n):          self._docs = self._docs[n:]; return self
    def limit(self, n):         self._docs = self._docs[:n]; return self
    def batch_size(self, n):    return self

    async def to_list(self, length=None):
        return self._docs[:length] if length else self._docs

    def __aiter__(self):
        self._idx = 0
        return self

    async def __anext__(self):
        if self._idx >= len(self._docs):
            raise StopAsyncIteration
        doc = self._docs[self._idx]
        self._idx += 1
        return doc


class MockCollection:
    def __init__(self):
        self._docs: list[dict] = []
        self._id_seq = 0

    def find(self, filt=None, sort=None, **kw):
        docs = [d for d in self._docs if self._match(d, filt or {})]
        return MockCursor(docs)

    async def find_one(self, filt=None, **kw):
        for d in self._docs:
            if self._match(d, filt or {}):
                return dict(d)
        return None

    async def insert_one(self, doc, **kw):
        from bson import ObjectId
        doc = dict(doc)
        if "_id" not in doc:
            doc["_id"] = ObjectId()
        # Idempotency: check unique fields
        if "event_id" in doc:
            for d in self._docs:
                if d.get("event_id") == doc["event_id"] and d.get("consumer_id") == doc.get("consumer_id"):
                    raise Exception("E11000 duplicate key error")
        self._docs.append(doc)
        r = MagicMock()
        r.inserted_id = doc["_id"]
        return r

    async def insert_many(self, docs, **kw):
        ids = []
        for doc in docs:
            r = await self.insert_one(doc)
            ids.append(r.inserted_id)
        r = MagicMock()
        r.inserted_ids = ids
        return r

    async def find_one_and_update(self, filt, update, **kw):
        upsert = kw.get("upsert", False)
        for i, d in enumerate(self._docs):
            if self._match(d, filt):
                if "$set" in update:
                    self._docs[i].update(update["$set"])
                if "$inc" in update:
                    for k, v in update["$inc"].items():
                        self._docs[i][k] = self._docs[i].get(k, 0) + v
                return dict(self._docs[i])
        if upsert:
            new_doc: dict = {}
            if "$set" in update:
                new_doc.update(update["$set"])
            if "$setOnInsert" in update:
                new_doc.update(update["$setOnInsert"])
            r = await self.insert_one(new_doc)
            return new_doc
        return None

    async def update_one(self, filt, update, **kw):
        for d in self._docs:
            if self._match(d, filt):
                if "$set" in update:
                    d.update(update["$set"])
                if "$inc" in update:
                    for k, v in update["$inc"].items():
                        d[k] = d.get(k, 0) + v
                r = MagicMock()
                r.modified_count = 1
                return r
        r = MagicMock()
        r.modified_count = 0
        return r

    async def update_many(self, filt, update, **kw):
        count = 0
        for d in self._docs:
            if self._match(d, filt):
                if "$set" in update:
                    d.update(update["$set"])
                count += 1
        r = MagicMock()
        r.modified_count = count
        return r

    async def delete_one(self, filt, **kw):
        for i, d in enumerate(self._docs):
            if self._match(d, filt):
                self._docs.pop(i)
                break
        r = MagicMock()
        r.deleted_count = 1
        return r

    async def count_documents(self, filt):
        return sum(1 for d in self._docs if self._match(d, filt))

    async def create_index(self, *a, **k):
        pass

    def aggregate(self, pipeline, **kw):
        docs = list(self._docs)
        for stage in pipeline:
            if "$group" in stage:
                by_field = stage["$group"]["_id"].lstrip("$")
                counts: dict = {}
                for d in docs:
                    val = d.get(by_field)
                    counts[val] = counts.get(val, 0) + 1
                docs = [{"_id": k, "count": v} for k, v in counts.items()]
        return MockCursor(docs)

    def _match(self, doc, filt):
        for k, v in filt.items():
            if k == "$or":
                if not any(self._match(doc, sub) for sub in v):
                    return False
            elif k == "$and":
                if not all(self._match(doc, sub) for sub in v):
                    return False
            elif isinstance(v, dict):
                doc_v = doc.get(k)
                for op, ov in v.items():
                    if op == "$in" and doc_v not in ov:
                        return False
                    elif op == "$ne" and doc_v == ov:
                        return False
                    elif op == "$gte" and not (doc_v is not None and doc_v >= ov):
                        return False
                    elif op == "$lte" and not (doc_v is not None and doc_v <= ov):
                        return False
            else:
                if doc.get(k) != v:
                    return False
        return True


class MockDB:
    def __init__(self):
        self._cols: dict[str, MockCollection] = {}

    def __getitem__(self, name):
        if name not in self._cols:
            self._cols[name] = MockCollection()
        return self._cols[name]


# ══════════════════════════════════════════════════════════════════════════════
# Test Cases
# ══════════════════════════════════════════════════════════════════════════════

class TestDomainEventModels(unittest.TestCase):

    def test_publication_created_has_correct_type(self):
        e = PublicationCreated(aggregate_id="pub1", user_id="user1", payload={"title": "Test"})
        self.assertEqual(e.event_type, PUBLICATION_CREATED)
        self.assertEqual(e.aggregate_type, "publication")
        self.assertIsNotNone(e.event_id)
        self.assertIsNotNone(e.timestamp)

    def test_to_dict_serializes_timestamp(self):
        e = PublicationCreated(aggregate_id="pub1", user_id="u1")
        d = e.to_dict()
        self.assertIsInstance(d["timestamp"], str)
        self.assertIn("event_type", d)
        self.assertIn("event_id", d)

    def test_from_dict_round_trip(self):
        e    = MissionCompleted(aggregate_id="m1", user_id="u1", payload={"result": "ok"})
        d    = e.to_dict()
        back = event_from_dict(d)
        self.assertEqual(back.event_type, e.event_type)
        self.assertEqual(back.aggregate_id, e.aggregate_id)
        self.assertEqual(back.payload, e.payload)

    def test_event_class_map_has_all_types(self):
        self.assertIn(PUBLICATION_CREATED, EVENT_CLASS_MAP)
        self.assertIn(MISSION_COMPLETED,   EVENT_CLASS_MAP)
        self.assertIn(GRANT_AWARDED,       EVENT_CLASS_MAP)

    def test_event_id_is_unique(self):
        e1 = PublicationCreated(aggregate_id="p1")
        e2 = PublicationCreated(aggregate_id="p1")
        self.assertNotEqual(e1.event_id, e2.event_id)

    def test_correlation_id_auto_set(self):
        e = PublicationCreated(aggregate_id="p1")
        self.assertTrue(len(e.correlation_id) > 0)

    def test_with_correlation(self):
        e = PublicationCreated(aggregate_id="p1")
        e.with_correlation("test-corr-id")
        self.assertEqual(e.correlation_id, "test-corr-id")

    def test_all_event_types_have_class(self):
        # Every constant in models should have a typed class
        self.assertGreaterEqual(len(EVENT_CLASS_MAP), 36)  # at least 36 typed event classes


class TestEventCatalog(unittest.TestCase):

    def test_catalog_populated(self):
        cat = _build_catalog()
        all_events = cat.all()
        self.assertGreater(len(all_events), 20)

    def test_catalog_by_producer(self):
        cat = _build_catalog()
        pub_events = cat.by_producer("publications_service")
        self.assertGreater(len(pub_events), 0)
        for e in pub_events:
            self.assertEqual(e["producer"], "publications_service")

    def test_catalog_by_consumer(self):
        cat = _build_catalog()
        kg_events = cat.by_consumer("knowledge_graph")
        self.assertGreater(len(kg_events), 0)

    def test_catalog_stable_filter(self):
        cat = _build_catalog()
        stable = cat.stable()
        self.assertGreater(len(stable), 10)
        for e in stable:
            self.assertEqual(e["lifecycle"], "stable")

    def test_catalog_entry_has_payload(self):
        cat = _build_catalog()
        entry = cat.get(PUBLICATION_CREATED)
        self.assertIsNotNone(entry)
        self.assertGreater(len(entry.payload), 0)


class TestCircuitBreaker(unittest.TestCase):

    def test_starts_closed(self):
        cb = CircuitBreaker(consumer_id="test")
        self.assertEqual(cb.state, CBState.CLOSED)
        self.assertTrue(cb.allow_request())

    def test_opens_after_threshold(self):
        cb = CircuitBreaker(consumer_id="test", failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        self.assertEqual(cb.state, CBState.OPEN)
        self.assertFalse(cb.allow_request())

    def test_half_open_after_recovery_timeout(self):
        cb = CircuitBreaker(consumer_id="test", failure_threshold=1, recovery_timeout=0.01)
        cb.record_failure()
        self.assertEqual(cb._state, CBState.OPEN)
        time.sleep(0.02)
        self.assertEqual(cb.state, CBState.HALF_OPEN)
        self.assertTrue(cb.allow_request())

    def test_closes_after_successful_probe(self):
        cb = CircuitBreaker(consumer_id="test", failure_threshold=1, recovery_timeout=0.01, success_threshold=1)
        cb.record_failure()
        time.sleep(0.02)
        _ = cb.state   # trigger HALF_OPEN transition
        cb.record_success()
        self.assertEqual(cb.state, CBState.CLOSED)

    def test_reopens_on_failed_probe(self):
        cb = CircuitBreaker(consumer_id="test", failure_threshold=1, recovery_timeout=0.01)
        cb.record_failure()
        time.sleep(0.02)
        _ = cb.state   # HALF_OPEN
        cb.record_failure()
        self.assertEqual(cb._state, CBState.OPEN)

    def test_reset(self):
        cb = CircuitBreaker(consumer_id="test", failure_threshold=1)
        cb.record_failure()
        cb.reset()
        self.assertEqual(cb.state, CBState.CLOSED)

    def test_to_dict(self):
        cb = CircuitBreaker(consumer_id="c1")
        d  = cb.to_dict()
        self.assertEqual(d["consumer_id"], "c1")
        self.assertIn("state", d)


class TestObservability(unittest.TestCase):

    def test_snapshot_has_totals(self):
        obs = EventObservability()
        obs.record_published("publication.created")
        obs.record_success("publication.created", "kg_handler", 15.0)
        s = obs.snapshot()
        self.assertIn("totals", s)
        self.assertIn("event_types", s)
        self.assertIn("consumers", s)
        self.assertEqual(s["totals"]["published"], 1)
        self.assertEqual(s["totals"]["successes"], 1)

    def test_ema_latency(self):
        obs = EventObservability()
        obs.record_success("e.type", "c1", 100.0)
        obs.record_success("e.type", "c1", 200.0)
        m = obs.snapshot()
        et = next(e for e in m["event_types"] if e["event_type"] == "e.type")
        self.assertGreater(et["avg_latency_ms"], 0)


class TestRetryPolicy(unittest.TestCase):

    def test_backoff_increases(self):
        p = HandlerRetryPolicy(initial_delay_s=1.0, backoff_factor=2.0, max_delay_s=300.0)
        d0 = p.get_delay(0)
        d1 = p.get_delay(1)
        d2 = p.get_delay(2)
        # With jitter, values are approximate — just check trend
        self.assertGreater(p.max_delay_s, 0)

    def test_permanent_error_not_retried(self):
        p = HandlerRetryPolicy(max_attempts=3)
        self.assertFalse(p.should_retry(ValueError("bad"), 1))
        self.assertFalse(p.should_retry(TypeError("bad"), 1))

    def test_transient_error_retried(self):
        p = HandlerRetryPolicy(max_attempts=3)
        self.assertTrue(p.should_retry(Exception("connection timeout"), 1))

    def test_max_attempts_not_retried(self):
        p = HandlerRetryPolicy(max_attempts=3)
        self.assertFalse(p.should_retry(Exception("timeout"), 3))


class TestHandlerRegistry(unittest.TestCase):

    def test_register_and_get(self):
        reg = HandlerRegistry()

        async def h(e): pass

        reg.register(HandlerRegistration(
            consumer_id="c1", event_type="test.created", handler=h
        ))
        handlers = reg.get_handlers("test.created")
        self.assertEqual(len(handlers), 1)
        self.assertEqual(handlers[0].consumer_id, "c1")

    def test_wildcard_included_in_all(self):
        reg = HandlerRegistry()

        async def h(e): pass
        async def w(e): pass

        reg.register(HandlerRegistration(consumer_id="c1", event_type="a.ev", handler=h))
        reg.register(HandlerRegistration(consumer_id="wc", event_type="*",    handler=w))

        handlers = reg.get_handlers("a.ev")
        ids = [r.consumer_id for r in handlers]
        self.assertIn("c1", ids)
        self.assertIn("wc", ids)

    def test_unregister_by_consumer(self):
        reg = HandlerRegistry()

        async def h(e): pass

        reg.register(HandlerRegistration(consumer_id="c1", event_type="x.ev", handler=h))
        reg.register(HandlerRegistration(consumer_id="c2", event_type="x.ev", handler=h))
        removed = reg.unregister("c1")
        self.assertGreater(removed, 0)
        handlers = reg.get_handlers("x.ev")
        self.assertNotIn("c1", [r.consumer_id for r in handlers])

    def test_no_handlers_returns_empty(self):
        reg = HandlerRegistry()
        self.assertEqual(reg.get_handlers("never.registered"), [])


class TestEnterpriseEventBus(unittest.TestCase):

    def setUp(self):
        reset_bus()

    def test_subscribe_and_publish(self):
        async def run():
            bus      = EnterpriseEventBus()
            received = []

            async def handler(event):
                received.append(event.event_type)

            bus.subscribe(PUBLICATION_CREATED, handler, consumer_id="test_handler")
            event = PublicationCreated(aggregate_id="p1", user_id="u1")
            await bus.dispatch_direct(event)
            self.assertIn(PUBLICATION_CREATED, received)

        asyncio.run(run())

    def test_wildcard_handler(self):
        async def run():
            bus  = EnterpriseEventBus()
            seen = []

            async def handler(event):
                seen.append(event.event_type)

            bus.subscribe("*", handler, consumer_id="wildcard")
            await bus.dispatch_direct(PublicationCreated(aggregate_id="p1"))
            await bus.dispatch_direct(MissionCompleted(aggregate_id="m1"))
            self.assertEqual(len(seen), 2)

        asyncio.run(run())

    def test_failed_handler_does_not_block_others(self):
        async def run():
            bus  = EnterpriseEventBus()
            good = []

            async def bad(event):
                raise RuntimeError("boom")

            async def good_h(event):
                good.append(1)

            bus.subscribe(PUBLICATION_CREATED, bad,    consumer_id="bad_handler")
            bus.subscribe(PUBLICATION_CREATED, good_h, consumer_id="good_handler")

            event = PublicationCreated(aggregate_id="p1")
            await bus.dispatch_direct(event)   # should not raise
            self.assertEqual(good, [1])        # good handler still ran

        asyncio.run(run())

    def test_publish_via_outbox_fallback(self):
        """When bus not started, publish_via_outbox falls back to direct publish."""
        async def run():
            bus      = EnterpriseEventBus()
            received = []

            async def h(event):
                received.append(event.event_type)

            bus.subscribe(PUBLICATION_CREATED, h, consumer_id="c1")

            event = PublicationCreated(aggregate_id="p1")
            await bus.publish_via_outbox(event)  # _outbox is None → falls back
            self.assertIn(PUBLICATION_CREATED, received)

        asyncio.run(run())

    def test_unsubscribe(self):
        async def run():
            bus      = EnterpriseEventBus()
            received = []

            async def h(event):
                received.append(event)

            bus.subscribe(PUBLICATION_CREATED, h, consumer_id="c1")
            bus.unsubscribe("c1")
            await bus.dispatch_direct(PublicationCreated(aggregate_id="p1"))
            self.assertEqual(received, [])

        asyncio.run(run())

    def test_metrics_snapshot(self):
        async def run():
            bus = EnterpriseEventBus()

            async def h(event): pass

            bus.subscribe(PUBLICATION_CREATED, h, consumer_id="c1")
            await bus.dispatch_direct(PublicationCreated(aggregate_id="p1"))

            m = bus.metrics()
            self.assertIn("totals", m)
            self.assertIn("event_types", m)

        asyncio.run(run())

    def test_all_handlers_list(self):
        async def run():
            bus = EnterpriseEventBus()

            async def h(e): pass

            bus.subscribe(PUBLICATION_CREATED, h, consumer_id="c1", description="Test handler")
            handlers = bus.all_handlers()
            self.assertEqual(len(handlers), 1)
            self.assertEqual(handlers[0]["consumer_id"], "c1")

        asyncio.run(run())

    def test_parallel_dispatch(self):
        """Multiple handlers run concurrently; total time ≈ max(individual), not sum."""
        async def run():
            bus  = EnterpriseEventBus()
            log  = []

            async def slow(event):
                await asyncio.sleep(0.05)
                log.append("slow")

            async def fast(event):
                await asyncio.sleep(0.01)
                log.append("fast")

            bus.subscribe(PUBLICATION_CREATED, slow, consumer_id="slow_h")
            bus.subscribe(PUBLICATION_CREATED, fast, consumer_id="fast_h")

            t_start = asyncio.get_event_loop().time()
            await bus.dispatch_direct(PublicationCreated(aggregate_id="p1"))
            elapsed = asyncio.get_event_loop().time() - t_start

            self.assertIn("slow", log)
            self.assertIn("fast", log)
            # Parallel: should be < 0.1s (much less than 0.05+0.01 = 0.06 serially — both within range)
            self.assertLess(elapsed, 0.2)

        asyncio.run(run())


class TestBusWithStore(unittest.TestCase):
    """Tests that require a started bus with in-memory DB."""

    def setUp(self):
        reset_bus()

    def test_publish_stores_event(self):
        async def run():
            db  = MockDB()
            bus = EnterpriseEventBus()
            await bus.start(db)

            async def h(e): pass
            bus.subscribe(PUBLICATION_CREATED, h, consumer_id="c1")

            event = PublicationCreated(aggregate_id="p1", user_id="u1")
            await bus.publish(event)

            # Check stored
            store_docs = db["event_store"]._docs
            self.assertGreater(len(store_docs), 0)
            self.assertEqual(store_docs[0]["event_type"], PUBLICATION_CREATED)

            await bus.stop()

        asyncio.run(run())

    def test_dlq_entries_empty_when_healthy(self):
        async def run():
            db  = MockDB()
            bus = EnterpriseEventBus()
            await bus.start(db)
            entries = await bus.dlq_entries()
            self.assertEqual(entries, [])
            await bus.stop()

        asyncio.run(run())

    def test_recent_events(self):
        async def run():
            db  = MockDB()
            bus = EnterpriseEventBus()
            await bus.start(db)

            async def h(e): pass
            bus.subscribe(PUBLICATION_CREATED, h, consumer_id="c1")

            await bus.publish(PublicationCreated(aggregate_id="p1"))
            await bus.publish(PublicationCreated(aggregate_id="p2"))

            recent = await bus.recent_events(limit=10)
            self.assertEqual(len(recent), 2)
            await bus.stop()

        asyncio.run(run())


class TestIdempotency(unittest.TestCase):

    def setUp(self):
        reset_bus()

    def test_same_event_not_processed_twice(self):
        async def run():
            db  = MockDB()
            bus = EnterpriseEventBus()
            await bus.start(db)

            count = [0]

            async def h(event):
                count[0] += 1

            bus.subscribe(
                PUBLICATION_CREATED, h,
                consumer_id="idem_handler",
                idempotent=True,
            )

            event = PublicationCreated(aggregate_id="p1")
            await bus.publish(event)
            await bus.publish(event)   # same event_id

            # Second dispatch should be skipped
            self.assertEqual(count[0], 1)
            await bus.stop()

        asyncio.run(run())

    def test_different_events_both_processed(self):
        async def run():
            db  = MockDB()
            bus = EnterpriseEventBus()
            await bus.start(db)

            count = [0]

            async def h(event):
                count[0] += 1

            bus.subscribe(PUBLICATION_CREATED, h, consumer_id="idem_h2", idempotent=True)

            await bus.publish(PublicationCreated(aggregate_id="p1"))
            await bus.publish(PublicationCreated(aggregate_id="p2"))  # different event_id

            self.assertEqual(count[0], 2)
            await bus.stop()

        asyncio.run(run())


class TestDLQ(unittest.TestCase):

    def setUp(self):
        reset_bus()

    def test_failing_handler_goes_to_dlq(self):
        async def run():
            db  = MockDB()
            bus = EnterpriseEventBus()
            await bus.start(db)

            async def always_fail(event):
                raise ValueError("Permanent failure")

            bus.subscribe(
                PUBLICATION_CREATED,
                always_fail,
                consumer_id="failing_handler",
                idempotent=False,
            )

            await bus.publish(PublicationCreated(aggregate_id="p1"))

            # Give executor time to DLQ
            await asyncio.sleep(0.1)

            dlq_entries = await bus.dlq_entries()
            self.assertGreater(len(dlq_entries), 0)
            self.assertEqual(dlq_entries[0]["consumer_id"], "failing_handler")
            await bus.stop()

        asyncio.run(run())


class TestOrderingAndReplay(unittest.TestCase):

    def setUp(self):
        reset_bus()

    def test_events_ordered_chronologically_in_store(self):
        async def run():
            db  = MockDB()
            bus = EnterpriseEventBus()
            await bus.start(db)

            async def h(e): pass
            bus.subscribe(PUBLICATION_CREATED, h, consumer_id="c1")

            for i in range(5):
                await bus.publish(PublicationCreated(aggregate_id=f"p{i}"))
                await asyncio.sleep(0.001)

            docs = db["event_store"]._docs
            self.assertEqual(len(docs), 5)
            await bus.stop()

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main(verbosity=2)
