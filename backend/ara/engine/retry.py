"""
Retry Engine — exponential backoff with transient/permanent error classification.

Every step and every mission follows a RetryPolicy.
Transient errors are retried with exponential backoff.
Permanent errors immediately mark the mission as failed.
No mission retries forever.

Default policy: 3 retries, 5s → 10s → 20s backoff, max 300s delay.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger("ara.engine.retry")

# ── Error classification ───────────────────────────────────────────────────────

TRANSIENT_ERRORS: frozenset[str] = frozenset({
    "timeout",
    "llm_timeout",
    "llm_unavailable",
    "network_error",
    "connection_error",
    "db_timeout",
    "db_unavailable",
    "redis_unavailable",
    "provider_overloaded",
    "rate_limited",
    "knowledge_graph_unavailable",
    "twin_unavailable",
    "temporary_failure",
})

PERMANENT_ERRORS: frozenset[str] = frozenset({
    "permission_denied",
    "cancelled",
    "plan_rejected",
    "invalid_mission",
    "agent_not_found",
    "safety_block",
    "policy_rejected",
    "budget_exhausted",
    "max_retries_exceeded",
    "human_rejected",
})


def classify_error(error: str) -> str:
    """Return 'transient', 'permanent', or 'unknown'."""
    error_lower = error.lower()
    for keyword in TRANSIENT_ERRORS:
        if keyword in error_lower:
            return "transient"
    for keyword in PERMANENT_ERRORS:
        if keyword in error_lower:
            return "permanent"
    return "unknown"


# ── Retry policy ───────────────────────────────────────────────────────────────

@dataclass
class RetryPolicy:
    max_retries:     int   = 3
    initial_delay_s: float = 5.0
    backoff_factor:  float = 2.0
    max_delay_s:     float = 300.0
    timeout_s:       float = 300.0
    retry_on_unknown: bool = True  # retry unclassified errors (safe default)


DEFAULT_POLICY = RetryPolicy()


# ── Retry engine ───────────────────────────────────────────────────────────────

class RetryEngine:

    def should_retry(
        self,
        retry_count: int,
        error:       str,
        policy:      RetryPolicy = DEFAULT_POLICY,
    ) -> bool:
        """
        Return True if the mission/step should be retried.
        Never retries permanently-failed missions.
        Never exceeds max_retries.
        """
        if retry_count >= policy.max_retries:
            return False

        classification = classify_error(error)
        if classification == "permanent":
            return False
        if classification == "transient":
            return True
        # unknown — use policy default
        return policy.retry_on_unknown

    def get_delay(
        self,
        retry_count: int,
        policy:      RetryPolicy = DEFAULT_POLICY,
    ) -> float:
        """Exponential backoff: initial_delay * backoff_factor^retry_count, capped at max_delay."""
        delay = policy.initial_delay_s * (policy.backoff_factor ** retry_count)
        return min(delay, policy.max_delay_s)

    async def schedule_retry(
        self,
        db,
        queue,
        mission_id:  str,
        error:       str,
        retry_count: int,
        policy:      RetryPolicy = DEFAULT_POLICY,
    ) -> bool:
        """
        Schedule a retry by requeueing the mission with delay.
        Returns True if retry was scheduled, False if permanently failed.
        """
        from ara import mission_store

        if not self.should_retry(retry_count, error, policy):
            await mission_store.update_mission(db, mission_id, {
                "status":     "failed",
                "last_error": f"Max retries exceeded. Last error: {error}",
            })
            await mission_store.append_log(db, mission_id, "retry_engine", "max_retries_exceeded",
                                           f"Giving up after {retry_count} retries. Error: {error}")
            logger.warning("Mission %s exceeded max retries (%d). Marking failed.", mission_id, retry_count)
            return False

        delay = self.get_delay(retry_count, policy)
        new_count = retry_count + 1

        await mission_store.update_mission(db, mission_id, {
            "status":      "retrying",
            "retry_count": new_count,
            "last_error":  error,
        })
        await mission_store.append_log(db, mission_id, "retry_engine", "retry_scheduled",
                                       f"Retry {new_count}/{policy.max_retries} in {delay:.0f}s. Error: {error}")
        await queue.enqueue(mission_id, priority=2, delay_seconds=delay)
        logger.info("Mission %s retry %d/%d scheduled in %.0fs", mission_id, new_count, policy.max_retries, delay)
        return True


# ── Singleton ──────────────────────────────────────────────────────────────────

_engine: RetryEngine | None = None


def get_retry_engine() -> RetryEngine:
    global _engine
    if _engine is None:
        _engine = RetryEngine()
    return _engine
