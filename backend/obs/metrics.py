"""
Metrics Platform — Phase XXXV.6

Thread-safe, tagged metric store covering every subsystem:
  - Counter  : monotonically increasing (requests, errors, events)
  - Gauge    : current value (active workers, queue depth, cache size)
  - Histogram: value distribution with P50/P95/P99 (latency, cost, tokens)

All metrics are kept in memory for speed. Snapshots are persisted to
MongoDB `obs_metrics` on demand or periodically.

Usage:
    from obs.metrics import get_metrics
    m = get_metrics()
    m.inc("api.requests", tags={"method": "POST", "path": "/api/ai"})
    m.gauge("worker.active", 4, tags={"queue": "ai"})
    m.observe("api.latency_ms", 142.3, tags={"path": "/api/ai"})
"""
from __future__ import annotations

import math
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


# ── Metric types ──────────────────────────────────────────────────────────────

@dataclass
class Counter:
    name:   str
    tags:   dict
    value:  float = 0.0

    def inc(self, delta: float = 1.0) -> None:
        self.value += delta


@dataclass
class Gauge:
    name:  str
    tags:  dict
    value: float = 0.0

    def set(self, value: float) -> None:
        self.value = value

    def inc(self, delta: float = 1.0) -> None:
        self.value += delta

    def dec(self, delta: float = 1.0) -> None:
        self.value -= delta


@dataclass
class Histogram:
    name:    str
    tags:    dict
    samples: list = field(default_factory=list)
    count:   int = 0
    total:   float = 0.0
    min_val: float = math.inf
    max_val: float = -math.inf

    def observe(self, value: float) -> None:
        self.samples.append(value)
        self.count += 1
        self.total += value
        if value < self.min_val:
            self.min_val = value
        if value > self.max_val:
            self.max_val = value
        # Keep only last 1000 samples to bound memory
        if len(self.samples) > 1000:
            self.samples = self.samples[-1000:]

    @property
    def mean(self) -> float:
        return self.total / self.count if self.count else 0.0

    def percentile(self, p: float) -> float:
        if not self.samples:
            return 0.0
        s = sorted(self.samples)
        idx = max(0, min(int(math.ceil(p / 100 * len(s))) - 1, len(s) - 1))
        return s[idx]

    def snapshot(self) -> dict:
        return {
            "count": self.count,
            "mean":  round(self.mean, 2),
            "p50":   round(self.percentile(50), 2),
            "p95":   round(self.percentile(95), 2),
            "p99":   round(self.percentile(99), 2),
            "min":   round(self.min_val, 2) if self.count else 0.0,
            "max":   round(self.max_val, 2) if self.count else 0.0,
            "total": round(self.total, 4),
        }


# ── Metric key helper ─────────────────────────────────────────────────────────

def _key(name: str, tags: dict) -> str:
    if not tags:
        return name
    tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
    return f"{name}{{{tag_str}}}"


# ── Central metric store ──────────────────────────────────────────────────────

class MetricStore:
    """Thread-safe central metric store for all Synaptiq subsystems."""

    def __init__(self) -> None:
        self._lock:       threading.Lock = threading.Lock()
        self._counters:   dict[str, Counter]   = {}
        self._gauges:     dict[str, Gauge]      = {}
        self._histograms: dict[str, Histogram]  = {}
        self._started_at: datetime = datetime.utcnow()

    # ── Write API ─────────────────────────────────────────────────────────────

    def inc(self, name: str, delta: float = 1.0, tags: dict | None = None) -> None:
        tags = tags or {}
        k = _key(name, tags)
        with self._lock:
            if k not in self._counters:
                self._counters[k] = Counter(name=name, tags=tags)
            self._counters[k].inc(delta)

    def gauge(self, name: str, value: float, tags: dict | None = None) -> None:
        tags = tags or {}
        k = _key(name, tags)
        with self._lock:
            if k not in self._gauges:
                self._gauges[k] = Gauge(name=name, tags=tags)
            self._gauges[k].set(value)

    def observe(self, name: str, value: float, tags: dict | None = None) -> None:
        tags = tags or {}
        k = _key(name, tags)
        with self._lock:
            if k not in self._histograms:
                self._histograms[k] = Histogram(name=name, tags=tags)
            self._histograms[k].observe(value)

    # ── Read API ──────────────────────────────────────────────────────────────

    def get_counter(self, name: str, tags: dict | None = None) -> float:
        k = _key(name, tags or {})
        with self._lock:
            return self._counters[k].value if k in self._counters else 0.0

    def get_gauge(self, name: str, tags: dict | None = None) -> float:
        k = _key(name, tags or {})
        with self._lock:
            return self._gauges[k].value if k in self._gauges else 0.0

    def get_histogram(self, name: str, tags: dict | None = None) -> dict:
        k = _key(name, tags or {})
        with self._lock:
            return self._histograms[k].snapshot() if k in self._histograms else {}

    def snapshot(self) -> dict:
        """Return complete metrics snapshot for the dashboard."""
        with self._lock:
            counters   = {k: v.value          for k, v in self._counters.items()}
            gauges     = {k: v.value          for k, v in self._gauges.items()}
            histograms = {k: v.snapshot()     for k, v in self._histograms.items()}
        return {
            "timestamp":  datetime.utcnow().isoformat(),
            "uptime_s":   round((datetime.utcnow() - self._started_at).total_seconds(), 1),
            "counters":   counters,
            "gauges":     gauges,
            "histograms": histograms,
        }

    def category_snapshot(self, prefix: str) -> dict:
        """Return snapshot filtered to metrics whose name starts with prefix."""
        snap = self.snapshot()
        return {
            "timestamp":  snap["timestamp"],
            "uptime_s":   snap["uptime_s"],
            "counters":   {k: v for k, v in snap["counters"].items()   if k.startswith(prefix)},
            "gauges":     {k: v for k, v in snap["gauges"].items()     if k.startswith(prefix)},
            "histograms": {k: v for k, v in snap["histograms"].items() if k.startswith(prefix)},
        }

    def reset(self) -> None:
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._histograms.clear()
            self._started_at = datetime.utcnow()

    async def persist(self, db: Any) -> None:
        """Persist a snapshot to MongoDB. Best-effort."""
        try:
            snap = self.snapshot()
            snap["_type"] = "snapshot"
            await db["obs_metrics"].insert_one(snap)
        except Exception:
            pass


# ── Pre-defined metric name constants ─────────────────────────────────────────

# API
M_API_REQUESTS     = "api.requests"
M_API_ERRORS       = "api.errors"
M_API_LATENCY      = "api.latency_ms"

# AI Gateway
M_AI_REQUESTS      = "ai.requests"
M_AI_ERRORS        = "ai.errors"
M_AI_LATENCY       = "ai.latency_ms"
M_AI_TOKENS_IN     = "ai.tokens.prompt"
M_AI_TOKENS_OUT    = "ai.tokens.completion"
M_AI_COST          = "ai.cost_usd"
M_AI_CACHE_HITS    = "ai.cache.hits"
M_AI_RETRIES       = "ai.retries"

# Workers
M_WORKER_JOBS_ENQ  = "worker.jobs.enqueued"
M_WORKER_JOBS_DONE = "worker.jobs.completed"
M_WORKER_JOBS_FAIL = "worker.jobs.failed"
M_WORKER_JOBS_DLQ  = "worker.jobs.dlq"
M_WORKER_LATENCY   = "worker.latency_ms"
M_WORKER_ACTIVE    = "worker.active"
M_WORKER_QUEUE_D   = "worker.queue_depth"

# Mission / ARA
M_MISSION_STARTED  = "mission.started"
M_MISSION_DONE     = "mission.completed"
M_MISSION_FAILED   = "mission.failed"
M_MISSION_LATENCY  = "mission.latency_ms"
M_MISSION_STEPS    = "mission.steps"
M_MISSION_RETRIES  = "mission.retries"

# Knowledge Graph
M_KG_NODES         = "kg.nodes"
M_KG_EDGES         = "kg.edges"
M_KG_UPDATES       = "kg.updates"
M_KG_LATENCY       = "kg.latency_ms"
M_KG_INFERENCES    = "kg.inferences"

# Digital Twin
M_TWIN_UPDATES     = "twin.updates"
M_TWIN_SIMULATIONS = "twin.simulations"
M_TWIN_LATENCY     = "twin.latency_ms"

# Event Bus
M_BUS_PUBLISHED    = "bus.published"
M_BUS_CONSUMED     = "bus.consumed"
M_BUS_DLQ          = "bus.dlq"
M_BUS_RETRIES      = "bus.retries"

# Database
M_DB_LATENCY       = "db.latency_ms"
M_DB_ERRORS        = "db.errors"

# Cache
M_CACHE_HITS       = "cache.hits"
M_CACHE_MISSES     = "cache.misses"

# Security
M_SEC_FAILED_LOGIN = "security.failed_login"
M_SEC_VIOLATIONS   = "security.violations"
M_SEC_INJECTIONS   = "security.injection_attempts"


# ── Singleton ─────────────────────────────────────────────────────────────────

_store: MetricStore | None = None


def init_metrics() -> MetricStore:
    global _store
    _store = MetricStore()
    return _store


def get_metrics() -> MetricStore:
    global _store
    if _store is None:
        _store = MetricStore()
    return _store


def reset_metrics() -> None:
    global _store
    _store = MetricStore()
