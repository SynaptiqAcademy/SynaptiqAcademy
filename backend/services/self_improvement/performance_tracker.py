"""Performance Tracker — measure accuracy and calibration of every engine."""
from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from .models import EnginePerformanceMetrics

_WINDOW = 200  # rolling observation window per engine


class PerformanceTracker:
    def __init__(self):
        self._lock        = threading.Lock()
        self._obs:  dict[str, deque]        = defaultdict(lambda: deque(maxlen=_WINDOW))
        self._acc:  dict[str, list[bool]]   = defaultdict(list)
        self._cache: dict[str, EnginePerformanceMetrics] = {}

    def record_observation(
        self,
        engine_type:    str,
        predicted_prob: float,
        actual_outcome: bool,
        accepted:       bool = False,
    ) -> None:
        with self._lock:
            self._obs[engine_type].append((predicted_prob, actual_outcome))
            self._acc[engine_type].append(accepted)
            self._cache.pop(engine_type, None)

    def compute_metrics(self, engine_type: str) -> EnginePerformanceMetrics:
        with self._lock:
            if engine_type in self._cache:
                return self._cache[engine_type]
            obs = list(self._obs.get(engine_type, []))
            acc = list(self._acc.get(engine_type, []))

        if not obs:
            return EnginePerformanceMetrics(engine_type=engine_type)

        calibration_error = sum(abs(p - float(a)) for p, a in obs) / len(obs)

        correct   = sum(1 for p, a in obs if (p >= 0.5) == bool(a))
        accuracy  = correct / len(obs)

        tp = sum(1 for p, a in obs if p >= 0.5 and bool(a))
        fp = sum(1 for p, a in obs if p >= 0.5 and not bool(a))
        fn = sum(1 for p, a in obs if p <  0.5 and bool(a))
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0

        accept_rate = sum(acc) / len(acc) if acc else 0.0
        avg_conf    = sum(p for p, _ in obs) / len(obs)

        half = len(obs) // 2
        if half > 0:
            a1 = sum(1 for p, a in obs[:half]  if (p >= 0.5) == bool(a)) / half
            a2 = sum(1 for p, a in obs[half:]  if (p >= 0.5) == bool(a)) / max(len(obs) - half, 1)
            trend = "improving" if a2 > a1 + 0.02 else ("declining" if a2 < a1 - 0.02 else "stable")
        else:
            trend = "stable"

        m = EnginePerformanceMetrics(
            engine_type=engine_type,
            accuracy=round(accuracy, 4),
            precision=round(precision, 4),
            recall=round(recall, 4),
            user_acceptance_rate=round(accept_rate, 4),
            avg_confidence=round(avg_conf, 4),
            calibration_error=round(calibration_error, 4),
            samples_evaluated=len(obs),
            trend=trend,
            last_updated=time.time(),
        )
        with self._lock:
            self._cache[engine_type] = m
        return m

    def get_all_metrics(self) -> dict[str, EnginePerformanceMetrics]:
        with self._lock:
            keys = list(self._obs.keys())
        return {k: self.compute_metrics(k) for k in keys}
