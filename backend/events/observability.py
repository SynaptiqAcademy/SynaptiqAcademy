"""
Event Observability — tracks metrics for the enterprise event bus.

Tracks per-event-type and per-consumer metrics:
  - publish count
  - dispatch count (per consumer)
  - success / failure / dlq counts
  - processing latency (rolling average)
  - retry count
  - replay count

All metrics are in-process (no external metrics backend required).
The admin API exposes them via /api/events/metrics.
"""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class EventTypeMetrics:
    event_type:      str
    publish_count:   int   = 0
    dispatch_count:  int   = 0
    success_count:   int   = 0
    failure_count:   int   = 0
    dlq_count:       int   = 0
    retry_count:     int   = 0
    replay_count:    int   = 0
    # Rolling avg latency (ms) — exponential moving average
    avg_latency_ms:  float = 0.0
    _ema_alpha:      float = 0.1   # EMA smoothing factor

    def record_publish(self) -> None:
        self.publish_count += 1

    def record_dispatch(self) -> None:
        self.dispatch_count += 1

    def record_success(self, latency_ms: float) -> None:
        self.success_count += 1
        if self.avg_latency_ms == 0:
            self.avg_latency_ms = latency_ms
        else:
            self.avg_latency_ms = (self._ema_alpha * latency_ms) + (1 - self._ema_alpha) * self.avg_latency_ms

    def record_failure(self) -> None:
        self.failure_count += 1

    def record_dlq(self) -> None:
        self.dlq_count += 1

    def record_retry(self) -> None:
        self.retry_count += 1

    def record_replay(self) -> None:
        self.replay_count += 1

    def to_dict(self) -> dict:
        return {
            "event_type":     self.event_type,
            "publish_count":  self.publish_count,
            "dispatch_count": self.dispatch_count,
            "success_count":  self.success_count,
            "failure_count":  self.failure_count,
            "dlq_count":      self.dlq_count,
            "retry_count":    self.retry_count,
            "replay_count":   self.replay_count,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
        }


@dataclass
class ConsumerMetrics:
    consumer_id:   str
    success_count: int   = 0
    failure_count: int   = 0
    dlq_count:     int   = 0
    skipped_count: int   = 0    # circuit breaker open
    avg_latency_ms: float = 0.0
    _ema_alpha:    float = 0.1

    def record_success(self, latency_ms: float) -> None:
        self.success_count += 1
        if self.avg_latency_ms == 0:
            self.avg_latency_ms = latency_ms
        else:
            self.avg_latency_ms = (self._ema_alpha * latency_ms) + (1 - self._ema_alpha) * self.avg_latency_ms

    def record_failure(self) -> None:
        self.failure_count += 1

    def record_dlq(self) -> None:
        self.dlq_count += 1

    def record_skipped(self) -> None:
        self.skipped_count += 1

    def to_dict(self) -> dict:
        return {
            "consumer_id":    self.consumer_id,
            "success_count":  self.success_count,
            "failure_count":  self.failure_count,
            "dlq_count":      self.dlq_count,
            "skipped_count":  self.skipped_count,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
        }


class EventObservability:
    """Thread-safe metrics store for the event bus."""

    def __init__(self) -> None:
        self._lock    = threading.Lock()
        self._events:    dict[str, EventTypeMetrics]  = {}
        self._consumers: dict[str, ConsumerMetrics]   = {}
        self._started_at = time.time()

    # ── Type metrics ──────────────────────────────────────────────────────────

    def _event(self, event_type: str) -> EventTypeMetrics:
        if event_type not in self._events:
            self._events[event_type] = EventTypeMetrics(event_type)
        return self._events[event_type]

    def record_published(self, event_type: str) -> None:
        with self._lock:
            self._event(event_type).record_publish()

    def record_dispatched(self, event_type: str) -> None:
        with self._lock:
            self._event(event_type).record_dispatch()

    def record_success(self, event_type: str, consumer_id: str, latency_ms: float) -> None:
        with self._lock:
            self._event(event_type).record_success(latency_ms)
            self._consumer(consumer_id).record_success(latency_ms)

    def record_failure(self, event_type: str, consumer_id: str) -> None:
        with self._lock:
            self._event(event_type).record_failure()
            self._consumer(consumer_id).record_failure()

    def record_dlq(self, event_type: str, consumer_id: str) -> None:
        with self._lock:
            self._event(event_type).record_dlq()
            self._consumer(consumer_id).record_dlq()

    def record_retry(self, event_type: str) -> None:
        with self._lock:
            self._event(event_type).record_retry()

    def record_skipped(self, consumer_id: str) -> None:
        with self._lock:
            self._consumer(consumer_id).record_skipped()

    def record_replay(self, event_type: str) -> None:
        with self._lock:
            self._event(event_type).record_replay()

    # ── Consumer metrics ──────────────────────────────────────────────────────

    def _consumer(self, consumer_id: str) -> ConsumerMetrics:
        if consumer_id not in self._consumers:
            self._consumers[consumer_id] = ConsumerMetrics(consumer_id)
        return self._consumers[consumer_id]

    # ── Read ──────────────────────────────────────────────────────────────────

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "uptime_seconds":   round(time.time() - self._started_at),
                "event_types":      [m.to_dict() for m in self._events.values()],
                "consumers":        [m.to_dict() for m in self._consumers.values()],
                "totals": {
                    "published":    sum(m.publish_count  for m in self._events.values()),
                    "dispatched":   sum(m.dispatch_count for m in self._events.values()),
                    "successes":    sum(m.success_count  for m in self._consumers.values()),
                    "failures":     sum(m.failure_count  for m in self._consumers.values()),
                    "dlq":          sum(m.dlq_count      for m in self._consumers.values()),
                },
            }


# Module-level singleton
_obs = EventObservability()


def get_observability() -> EventObservability:
    return _obs
