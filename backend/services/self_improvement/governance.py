"""Governance Controller — learning policies and quality thresholds."""
from __future__ import annotations

import threading
import time

from .models import ABExperiment, GovernancePolicy

_singleton: GovernancePolicy | None = None
_lock = threading.Lock()

_ALLOWED_FIELDS = frozenset({
    "learning_enabled", "retention_days", "min_samples_for_optimization",
    "significance_threshold", "min_improvement_threshold", "feedback_weight",
    "auto_apply_optimizations", "require_admin_approval",
    "max_concurrent_experiments", "rollback_window_days", "privacy_level",
})


def get_policy() -> GovernancePolicy:
    global _singleton
    with _lock:
        if _singleton is None:
            _singleton = GovernancePolicy()
    return _singleton


def update_policy(updates: dict, updated_by: str = "admin") -> GovernancePolicy:
    policy = get_policy()
    with _lock:
        for key, val in updates.items():
            if key in _ALLOWED_FIELDS and hasattr(policy, key):
                setattr(policy, key, val)
        policy.updated_at = time.time()
        policy.updated_by = updated_by
    return policy


def can_optimize(samples_evaluated: int, policy: GovernancePolicy | None = None) -> bool:
    if policy is None:
        policy = get_policy()
    return policy.learning_enabled and samples_evaluated >= policy.min_samples_for_optimization


def can_deploy_experiment(
    experiment: ABExperiment,
    policy:     GovernancePolicy | None = None,
) -> bool:
    if policy is None:
        policy = get_policy()
    if not policy.learning_enabled:
        return False
    if experiment.p_value > policy.significance_threshold:
        return False
    if abs(experiment.metric_b - experiment.metric_a) < policy.min_improvement_threshold:
        return False
    return True


def reset_policy() -> None:
    global _singleton
    with _lock:
        _singleton = None
