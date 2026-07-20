"""
Retry Policy — for event handler execution.

Separate from the ARA retry policy (ara/engine/retry.py) which handles
mission-level retries. This one handles per-handler retries for event dispatch.

Classification:
  - Transient errors: timeout, connection, rate limit → retry with backoff
  - Permanent errors: import error, validation, assertion → no retry → DLQ
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Transient error indicators
_TRANSIENT_PATTERNS = (
    "timeout", "timed out", "connection", "network",
    "service unavailable", "rate limit", "too many requests",
    "temporarily unavailable", "try again",
)

# Permanent error types
_PERMANENT_TYPES = (
    ImportError, AttributeError, TypeError, ValueError,
    AssertionError, NotImplementedError, KeyError,
)


@dataclass
class HandlerRetryPolicy:
    max_attempts:    int   = 3
    initial_delay_s: float = 1.0
    backoff_factor:  float = 2.0
    max_delay_s:     float = 60.0
    jitter:          bool  = True

    def get_delay(self, attempt: int) -> float:
        delay = min(
            self.initial_delay_s * (self.backoff_factor ** attempt),
            self.max_delay_s,
        )
        if self.jitter:
            import random
            delay *= (0.8 + random.random() * 0.4)
        return delay

    def should_retry(self, exc: Exception, attempt: int) -> bool:
        if attempt >= self.max_attempts:
            return False
        if isinstance(exc, _PERMANENT_TYPES):
            return False
        msg = str(exc).lower()
        return any(p in msg for p in _TRANSIENT_PATTERNS)


DEFAULT_RETRY_POLICY = HandlerRetryPolicy()


async def execute_with_retry(
    handler,
    event,
    *,
    policy: HandlerRetryPolicy = DEFAULT_RETRY_POLICY,
    consumer_id: str = "",
    on_retry=None,
) -> None:
    """
    Execute handler with retry on transient failures.

    Raises the last exception if all retries are exhausted or error is permanent.
    """
    last_exc: Exception | None = None

    for attempt in range(policy.max_attempts):
        try:
            await handler(event)
            return
        except asyncio.TimeoutError as exc:
            last_exc = exc
            if attempt + 1 < policy.max_attempts:
                delay = policy.get_delay(attempt)
                logger.warning(
                    "Handler %s timeout (attempt %d/%d), retry in %.1fs",
                    consumer_id, attempt + 1, policy.max_attempts, delay,
                )
                if on_retry:
                    on_retry(attempt + 1)
                await asyncio.sleep(delay)
        except Exception as exc:
            last_exc = exc
            if policy.should_retry(exc, attempt + 1):
                delay = policy.get_delay(attempt)
                logger.warning(
                    "Handler %s transient error (attempt %d/%d), retry in %.1fs: %s",
                    consumer_id, attempt + 1, policy.max_attempts, delay, exc,
                )
                if on_retry:
                    on_retry(attempt + 1)
                await asyncio.sleep(delay)
            else:
                raise exc   # permanent error — don't retry

    raise last_exc  # type: ignore[misc]
