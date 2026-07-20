"""
External Dependency Circuit Breakers — protect handlers from cascading failures.

Each external dependency (LLM providers, academic APIs, graph/twin services)
gets its own circuit breaker. If a dependency fails repeatedly the breaker
OPENS, and jobs that need it are re-queued rather than failing immediately.

State machine: CLOSED → OPEN (after N failures) → HALF_OPEN (after timeout) → CLOSED

Separate from events/circuit_breaker.py which protects event handlers.
This one protects external API calls made inside job handlers.
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class CBState(str, Enum):
    CLOSED    = "closed"
    OPEN      = "open"
    HALF_OPEN = "half_open"


class ExternalDep(str, Enum):
    LLM_ANTHROPIC = "llm.anthropic"
    LLM_OPENAI    = "llm.openai"
    LLM_GOOGLE    = "llm.google"
    OPENALEX      = "openalex"
    CROSSREF      = "crossref"
    ORCID         = "orcid"
    MONGODB       = "mongodb"
    GRAPH_SERVICE = "graph"
    TWIN_SERVICE  = "twin"
    INSTITUTION   = "institution"
    EMAIL         = "email"
    STRIPE        = "stripe"


@dataclass
class ExternalCircuitBreaker:
    dep:               ExternalDep
    failure_threshold: int   = 5
    recovery_timeout_s: float = 60.0
    success_threshold: int   = 2    # successes needed in HALF_OPEN to close

    _failures:       int   = field(default=0,      repr=False)
    _successes:      int   = field(default=0,      repr=False)
    _opened_at:      float = field(default=0.0,    repr=False)
    _lock:           threading.Lock = field(default_factory=threading.Lock, repr=False)

    @property
    def state(self) -> CBState:
        with self._lock:
            if self._failures < self.failure_threshold:
                return CBState.CLOSED
            if time.monotonic() - self._opened_at >= self.recovery_timeout_s:
                return CBState.HALF_OPEN
            return CBState.OPEN

    def allow_request(self) -> bool:
        s = self.state
        return s in (CBState.CLOSED, CBState.HALF_OPEN)

    def record_success(self) -> None:
        with self._lock:
            self._successes += 1
            if self._successes >= self.success_threshold:
                self._failures  = 0
                self._successes = 0
                logger.info("Circuit %s CLOSED", self.dep.value)

    def record_failure(self) -> None:
        with self._lock:
            self._failures  += 1
            self._successes  = 0
            if self._failures >= self.failure_threshold:
                self._opened_at = time.monotonic()
                logger.warning(
                    "Circuit %s OPEN after %d failures", self.dep.value, self._failures
                )

    def reset(self) -> None:
        with self._lock:
            self._failures  = 0
            self._successes = 0
            self._opened_at = 0.0
        logger.info("Circuit %s manually RESET", self.dep.value)

    def to_dict(self) -> dict:
        return {
            "dep":       self.dep.value,
            "state":     self.state.value,
            "failures":  self._failures,
            "successes": self._successes,
        }


class ExternalCircuitBreakerRegistry:
    """Singleton registry of all external-dep circuit breakers."""

    def __init__(self) -> None:
        self._breakers: dict[str, ExternalCircuitBreaker] = {}
        self._lock = threading.Lock()

    def get(self, dep: ExternalDep) -> ExternalCircuitBreaker:
        key = dep.value
        with self._lock:
            if key not in self._breakers:
                self._breakers[key] = ExternalCircuitBreaker(dep=dep)
            return self._breakers[key]

    def all_status(self) -> list[dict]:
        with self._lock:
            return [cb.to_dict() for cb in self._breakers.values()]

    def reset(self, dep: ExternalDep) -> None:
        self.get(dep).reset()

    def reset_all(self) -> None:
        with self._lock:
            for cb in self._breakers.values():
                cb.reset()


_registry = ExternalCircuitBreakerRegistry()


def get_job_cb_registry() -> ExternalCircuitBreakerRegistry:
    return _registry


def get_job_cb(dep: ExternalDep) -> ExternalCircuitBreaker:
    return _registry.get(dep)
