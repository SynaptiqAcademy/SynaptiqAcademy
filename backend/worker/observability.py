"""
Job Observability — tracks queue depth, worker utilization, and execution metrics.

Metrics per job type: count, successes, failures, DLQ, retries, EMA latency.
Metrics per worker:   count, successes, failures, active jobs, EMA latency.
Cost tracking:        total cost_usd, total tokens per model/provider.

All state is in-process (resets on restart). The admin snapshot() endpoint
provides a live view; historical data lives in the job documents in MongoDB.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any


_EMA_ALPHA = 0.1   # smoothing factor — more weight to recent values


@dataclass
class JobTypeMetrics:
    job_type:    str
    count:       int   = 0
    successes:   int   = 0
    failures:    int   = 0
    retries:     int   = 0
    dlq_count:   int   = 0
    ema_latency: float = 0.0   # milliseconds
    total_cost:  float = 0.0   # USD
    total_tokens: int  = 0

    def record_success(self, latency_ms: float, cost: float = 0.0, tokens: int = 0) -> None:
        self.count     += 1
        self.successes += 1
        self.ema_latency = (
            _EMA_ALPHA * latency_ms + (1 - _EMA_ALPHA) * self.ema_latency
        )
        self.total_cost   += cost
        self.total_tokens += tokens

    def record_failure(self) -> None:
        self.count    += 1
        self.failures += 1

    def record_retry(self) -> None:
        self.retries += 1

    def record_dlq(self) -> None:
        self.dlq_count += 1

    def to_dict(self) -> dict:
        return {
            "job_type":     self.job_type,
            "count":        self.count,
            "successes":    self.successes,
            "failures":     self.failures,
            "retries":      self.retries,
            "dlq_count":    self.dlq_count,
            "ema_latency_ms": round(self.ema_latency, 1),
            "total_cost_usd": round(self.total_cost, 6),
            "total_tokens":  self.total_tokens,
        }


@dataclass
class WorkerMetrics:
    worker_id:   str
    processed:   int   = 0
    successes:   int   = 0
    failures:    int   = 0
    active_jobs: int   = 0
    ema_latency: float = 0.0

    def record_success(self, latency_ms: float) -> None:
        self.processed  += 1
        self.successes  += 1
        self.active_jobs = max(0, self.active_jobs - 1)
        self.ema_latency = (
            _EMA_ALPHA * latency_ms + (1 - _EMA_ALPHA) * self.ema_latency
        )

    def record_failure(self) -> None:
        self.processed  += 1
        self.failures   += 1
        self.active_jobs = max(0, self.active_jobs - 1)

    def record_start(self) -> None:
        self.active_jobs += 1

    def to_dict(self) -> dict:
        return {
            "worker_id":      self.worker_id,
            "processed":      self.processed,
            "successes":      self.successes,
            "failures":       self.failures,
            "active_jobs":    self.active_jobs,
            "ema_latency_ms": round(self.ema_latency, 1),
        }


class JobObservability:
    """Thread-safe in-process metrics store."""

    def __init__(self) -> None:
        self._by_type:   dict[str, JobTypeMetrics]  = {}
        self._by_worker: dict[str, WorkerMetrics]   = {}
        self._lock       = threading.Lock()
        self._total_published = 0
        self._total_completed = 0
        self._total_failed    = 0
        self._total_dlq       = 0
        self._total_retries   = 0

    def _type_metrics(self, job_type: str) -> JobTypeMetrics:
        if job_type not in self._by_type:
            self._by_type[job_type] = JobTypeMetrics(job_type=job_type)
        return self._by_type[job_type]

    def _worker_metrics(self, worker_id: str) -> WorkerMetrics:
        if worker_id not in self._by_worker:
            self._by_worker[worker_id] = WorkerMetrics(worker_id=worker_id)
        return self._by_worker[worker_id]

    def record_enqueued(self, job_type: str) -> None:
        with self._lock:
            self._total_published += 1

    def record_start(self, job_type: str, worker_id: str) -> None:
        with self._lock:
            self._worker_metrics(worker_id).record_start()

    def record_success(
        self,
        job_type: str,
        worker_id: str,
        latency_ms: float,
        cost_usd: float = 0.0,
        tokens: int = 0,
    ) -> None:
        with self._lock:
            self._total_completed += 1
            self._type_metrics(job_type).record_success(latency_ms, cost_usd, tokens)
            self._worker_metrics(worker_id).record_success(latency_ms)

    def record_failure(self, job_type: str, worker_id: str) -> None:
        with self._lock:
            self._total_failed += 1
            self._type_metrics(job_type).record_failure()
            self._worker_metrics(worker_id).record_failure()

    def record_retry(self, job_type: str) -> None:
        with self._lock:
            self._total_retries += 1
            self._type_metrics(job_type).record_retry()

    def record_dlq(self, job_type: str) -> None:
        with self._lock:
            self._total_dlq += 1
            self._type_metrics(job_type).record_dlq()

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "totals": {
                    "enqueued":  self._total_published,
                    "completed": self._total_completed,
                    "failed":    self._total_failed,
                    "dlq":       self._total_dlq,
                    "retries":   self._total_retries,
                },
                "by_job_type": [m.to_dict() for m in self._by_type.values()],
                "by_worker":   [m.to_dict() for m in self._by_worker.values()],
            }


_obs: JobObservability | None = None


def get_job_observability() -> JobObservability:
    global _obs
    if _obs is None:
        _obs = JobObservability()
    return _obs


def reset_job_observability() -> None:
    global _obs
    _obs = None
