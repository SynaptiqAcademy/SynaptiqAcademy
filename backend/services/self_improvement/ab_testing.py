"""A/B Testing Framework — controlled experiments with statistical significance."""
from __future__ import annotations

import math
import threading
import time

from .models import ABExperiment, ExperimentStatus

_MAX_EXPERIMENTS = 200


def _erfc_approx(x: float) -> float:
    """Abramowitz & Stegun erfc approximation — error < 1.5e-7."""
    ax   = abs(x)
    t    = 1.0 / (1.0 + 0.3275911 * ax)
    poly = t * (0.254829592 + t * (-0.284496736 + t * (1.421413741 + t * (-1.453152027 + t * 1.061405429))))
    r    = poly * math.exp(-ax * ax)
    return r if x >= 0 else 2.0 - r


def compute_p_value(n_a: int, s_a: int, n_b: int, s_b: int) -> float:
    """Two-sided z-test for proportions. Returns p-value ∈ [0, 1]."""
    if n_a < 5 or n_b < 5:
        return 1.0
    p_pool = (s_a + s_b) / (n_a + n_b)
    denom  = math.sqrt(p_pool * (1.0 - p_pool) * (1.0 / n_a + 1.0 / n_b))
    if denom < 1e-10:
        return 1.0
    z = abs(s_b / n_b - s_a / n_a) / denom
    return min(_erfc_approx(z / math.sqrt(2)), 1.0)


class ABTestingFramework:
    def __init__(self):
        self._lock         = threading.Lock()
        self._experiments: dict[str, ABExperiment]         = {}
        self._obs:         dict[str, dict[str, list[int]]] = {}  # exp_id → {A:[], B:[]}

    def create_experiment(
        self,
        name:          str,
        engine_type:   str,
        variant_a:     dict,
        variant_b:     dict,
        description:   str   = "",
        traffic_split: float = 0.5,
    ) -> ABExperiment:
        exp = ABExperiment(
            name=name,
            description=description,
            engine_type=engine_type,
            variant_a=variant_a,
            variant_b=variant_b,
            traffic_split=max(0.1, min(0.9, traffic_split)),
            status=ExperimentStatus.RUNNING.value,
            started_at=time.time(),
        )
        with self._lock:
            if len(self._experiments) >= _MAX_EXPERIMENTS:
                oldest = next(iter(self._experiments))
                del self._experiments[oldest]
                self._obs.pop(oldest, None)
            self._experiments[exp.experiment_id] = exp
            self._obs[exp.experiment_id]         = {"A": [], "B": []}
        return exp

    def record_observation(self, experiment_id: str, variant: str, success: bool) -> bool:
        variant = variant.upper()
        if variant not in ("A", "B"):
            return False
        with self._lock:
            if experiment_id not in self._experiments:
                return False
            if self._experiments[experiment_id].status != ExperimentStatus.RUNNING.value:
                return False
            self._obs[experiment_id][variant].append(1 if success else 0)
        return True

    def evaluate_experiment(self, experiment_id: str) -> ABExperiment | None:
        with self._lock:
            exp = self._experiments.get(experiment_id)
            obs = dict(self._obs.get(experiment_id, {"A": [], "B": []}))
        if not exp:
            return None

        obs_a, obs_b      = obs["A"], obs["B"]
        n_a, s_a          = len(obs_a), sum(obs_a)
        n_b, s_b          = len(obs_b), sum(obs_b)
        exp.sample_a      = n_a
        exp.sample_b      = n_b
        exp.metric_a      = round(s_a / n_a, 4) if n_a else 0.0
        exp.metric_b      = round(s_b / n_b, 4) if n_b else 0.0
        exp.p_value       = compute_p_value(n_a, s_a, n_b, s_b)
        if exp.p_value < 0.05:
            exp.winner = "B" if exp.metric_b > exp.metric_a else "A"
        else:
            exp.winner = "no_difference"
        return exp

    def complete_experiment(self, experiment_id: str) -> bool:
        with self._lock:
            exp = self._experiments.get(experiment_id)
            if not exp:
                return False
            exp.status   = ExperimentStatus.COMPLETED.value
            exp.ended_at = time.time()
        return True

    def deploy_winner(self, experiment_id: str) -> bool:
        with self._lock:
            exp = self._experiments.get(experiment_id)
            if not exp or exp.winner not in ("A", "B"):
                return False
            exp.deployed = True
        return True

    def rollback_experiment(self, experiment_id: str) -> bool:
        with self._lock:
            exp = self._experiments.get(experiment_id)
            if not exp:
                return False
            exp.status   = ExperimentStatus.ROLLED_BACK.value
            exp.deployed = False
        return True

    def get_experiment(self, experiment_id: str) -> ABExperiment | None:
        with self._lock:
            return self._experiments.get(experiment_id)

    def get_active_experiments(self) -> list[ABExperiment]:
        with self._lock:
            return [e for e in self._experiments.values() if e.status == ExperimentStatus.RUNNING.value]

    def get_all_experiments(self) -> list[ABExperiment]:
        with self._lock:
            return list(self._experiments.values())
