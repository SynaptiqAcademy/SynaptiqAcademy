"""
Job Retry Engine — classifies errors and computes retry schedules.

Separate from events/retry.py — this handles job-level retries which
have different semantics (job state persists in MongoDB between retries,
workers compete for re-queued jobs rather than re-calling immediately).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta


# Errors that should NEVER be retried (programming errors / data corruption)
_PERMANENT_TYPES = (
    TypeError,
    ValueError,
    AttributeError,
    KeyError,
    AssertionError,
    NotImplementedError,
    ImportError,
)

# Error message substrings indicating a transient condition
_TRANSIENT_PATTERNS = (
    "timeout", "connection", "rate limit", "too many requests",
    "service unavailable", "temporarily", "try again", "503", "429",
    "network", "socket", "reset by peer",
)


@dataclass
class JobRetryPolicy:
    max_attempts:   int   = 3
    initial_delay_s: float = 5.0
    backoff_factor:  float = 2.0
    max_delay_s:     float = 300.0   # 5 minutes cap
    jitter:          bool  = True


DEFAULT_JOB_RETRY_POLICY = JobRetryPolicy()


def classify_error(exc: Exception) -> str:
    """Return 'permanent' or 'transient'."""
    if isinstance(exc, _PERMANENT_TYPES):
        return "permanent"
    msg = str(exc).lower()
    for pat in _TRANSIENT_PATTERNS:
        if pat in msg:
            return "transient"
    return "permanent"  # default: don't retry unknown errors


def should_retry(exc: Exception, attempt: int, policy: JobRetryPolicy) -> bool:
    if attempt >= policy.max_attempts:
        return False
    return classify_error(exc) == "transient"


def compute_retry_at(attempt: int, policy: JobRetryPolicy) -> datetime:
    """Return the datetime at which the job should be retried."""
    delay = min(
        policy.initial_delay_s * (policy.backoff_factor ** attempt),
        policy.max_delay_s,
    )
    if policy.jitter:
        delay = delay * (0.75 + random.random() * 0.5)
    return datetime.utcnow() + timedelta(seconds=delay)
