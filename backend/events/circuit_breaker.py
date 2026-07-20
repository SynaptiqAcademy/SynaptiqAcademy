"""
Circuit Breaker — per-consumer fault protection.

States:
  CLOSED    → handler runs normally
  OPEN      → handler is skipped (too many recent failures)
  HALF_OPEN → one probe allowed; reopens on failure, closes on success

Thresholds (configurable):
  failure_threshold: consecutive failures before opening (default 5)
  recovery_timeout:  seconds before trying HALF_OPEN (default 60)
  success_threshold: successes in HALF_OPEN before closing (default 2)
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class CBState(str, Enum):
    CLOSED    = "closed"
    OPEN      = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    consumer_id:       str
    failure_threshold: int   = 5
    recovery_timeout:  float = 60.0
    success_threshold: int   = 2

    # Internal state
    _state:             CBState = field(default=CBState.CLOSED,  init=False, repr=False)
    _failure_count:     int     = field(default=0,               init=False, repr=False)
    _success_count:     int     = field(default=0,               init=False, repr=False)
    _opened_at:         float   = field(default=0.0,             init=False, repr=False)
    _total_opens:       int     = field(default=0,               init=False, repr=False)

    @property
    def state(self) -> CBState:
        if self._state == CBState.OPEN:
            if time.monotonic() - self._opened_at >= self.recovery_timeout:
                self._state         = CBState.HALF_OPEN
                self._success_count = 0
                logger.info("CircuitBreaker[%s] → HALF_OPEN", self.consumer_id)
        return self._state

    def is_open(self) -> bool:
        return self.state == CBState.OPEN

    def allow_request(self) -> bool:
        """True if the handler should be called."""
        s = self.state
        if s == CBState.CLOSED:
            return True
        if s == CBState.HALF_OPEN:
            return True          # allow probe
        return False             # OPEN — skip

    def record_success(self) -> None:
        s = self.state
        if s == CBState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.success_threshold:
                self._state         = CBState.CLOSED
                self._failure_count = 0
                logger.info("CircuitBreaker[%s] → CLOSED (recovered)", self.consumer_id)
        elif s == CBState.CLOSED:
            self._failure_count = 0   # reset on any success

    def record_failure(self) -> None:
        s = self.state
        if s == CBState.HALF_OPEN:
            self._state    = CBState.OPEN
            self._opened_at = time.monotonic()
            self._total_opens += 1
            logger.warning("CircuitBreaker[%s] → OPEN (probe failed)", self.consumer_id)
        elif s == CBState.CLOSED:
            self._failure_count += 1
            if self._failure_count >= self.failure_threshold:
                self._state    = CBState.OPEN
                self._opened_at = time.monotonic()
                self._total_opens += 1
                logger.warning(
                    "CircuitBreaker[%s] → OPEN (threshold %d reached)",
                    self.consumer_id, self.failure_threshold,
                )

    def reset(self) -> None:
        self._state         = CBState.CLOSED
        self._failure_count = 0
        self._success_count = 0

    def to_dict(self) -> dict:
        return {
            "consumer_id":       self.consumer_id,
            "state":             self.state.value,
            "failure_count":     self._failure_count,
            "total_opens":       self._total_opens,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout":  self.recovery_timeout,
        }


class CircuitBreakerRegistry:
    """Per-consumer circuit breaker storage."""

    def __init__(self) -> None:
        self._breakers: dict[str, CircuitBreaker] = {}

    def get(self, consumer_id: str) -> CircuitBreaker:
        if consumer_id not in self._breakers:
            self._breakers[consumer_id] = CircuitBreaker(consumer_id=consumer_id)
        return self._breakers[consumer_id]

    def all_status(self) -> list[dict]:
        return [cb.to_dict() for cb in self._breakers.values()]

    def reset(self, consumer_id: str) -> None:
        if consumer_id in self._breakers:
            self._breakers[consumer_id].reset()


_registry = CircuitBreakerRegistry()


def get_circuit_breaker(consumer_id: str) -> CircuitBreaker:
    return _registry.get(consumer_id)


def all_circuit_breaker_status() -> list[dict]:
    return _registry.all_status()


def reset_circuit_breaker(consumer_id: str) -> None:
    _registry.reset(consumer_id)
