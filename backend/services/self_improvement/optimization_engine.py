"""Optimization Engine — generate, apply, and roll back governed improvements."""
from __future__ import annotations

import threading

from .models import EnginePerformanceMetrics, GovernancePolicy, OptimizationRecord, OptimizationType

_MAX_HISTORY = 1_000


class OptimizationEngine:
    def __init__(self):
        self._lock:    threading.Lock                    = threading.Lock()
        self._history: list[OptimizationRecord]          = []
        self._pending: dict[str, OptimizationRecord]     = {}

    # ── Candidate generation ──────────────────────────────────────────────────

    def generate_candidates(
        self,
        all_metrics: dict[str, EnginePerformanceMetrics],
        policy:      GovernancePolicy,
    ) -> list[OptimizationRecord]:
        candidates: list[OptimizationRecord] = []

        for engine_type, m in all_metrics.items():
            if m.samples_evaluated < policy.min_samples_for_optimization:
                continue

            if m.calibration_error > 0.10:
                candidates.append(OptimizationRecord(
                    optimization_type=OptimizationType.CONFIDENCE_CALIBRATION.value,
                    engine_type=engine_type,
                    parameter="confidence_threshold_very_high",
                    old_value=0.85,
                    new_value=round(max(0.85 - m.calibration_error * 0.5, 0.70), 3),
                    rationale=f"Calibration error {m.calibration_error:.3f} > 0.10 — recalibrate thresholds",
                    expected_improvement=round(min(m.calibration_error * 0.6, 0.08), 4),
                ))

            if m.accuracy < 0.60 and m.trend != "declining":
                candidates.append(OptimizationRecord(
                    optimization_type=OptimizationType.WEIGHT_ADJUSTMENT.value,
                    engine_type=engine_type,
                    parameter="ranking_weight_confidence",
                    old_value=0.35,
                    new_value=0.45,
                    rationale=f"Accuracy {m.accuracy:.3f} below 0.60 — upweight confidence signals",
                    expected_improvement=0.03,
                ))

            if m.samples_evaluated >= policy.min_samples_for_optimization and m.accuracy > 0.80:
                candidates.append(OptimizationRecord(
                    optimization_type=OptimizationType.CACHE_STRATEGY.value,
                    engine_type=engine_type,
                    parameter="cache_ttl_seconds",
                    old_value=300,
                    new_value=600,
                    rationale=f"High accuracy ({m.accuracy:.3f}) — extend cache lifetime to reduce compute",
                    expected_improvement=0.01,
                ))

            if m.trend == "declining":
                candidates.append(OptimizationRecord(
                    optimization_type=OptimizationType.THRESHOLD_ADJUSTMENT.value,
                    engine_type=engine_type,
                    parameter="min_confidence_to_serve",
                    old_value=0.30,
                    new_value=0.40,
                    rationale="Declining trend detected — raise minimum confidence before serving recommendation",
                    expected_improvement=0.02,
                ))

        return candidates

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def add_to_history(self, record: OptimizationRecord) -> None:
        with self._lock:
            self._history.append(record)
            if len(self._history) > _MAX_HISTORY:
                self._history.pop(0)
            self._pending[record.record_id] = record

    def apply_optimization(self, record_id: str, approved_by: str = "admin") -> bool:
        with self._lock:
            rec = self._pending.get(record_id)
            if not rec or rec.status != "pending":
                return False
            rec.status      = "applied"
            rec.approved_by = approved_by
        return True

    def rollback_optimization(self, record_id: str) -> bool:
        with self._lock:
            rec = self._pending.get(record_id)
            if not rec or rec.status != "applied":
                return False
            rec.status             = "rolled_back"
            rec.rollback_available = False
        return True

    def update_measured_improvement(self, record_id: str, improvement: float) -> None:
        with self._lock:
            rec = self._pending.get(record_id)
            if rec:
                rec.measured_improvement = round(improvement, 4)

    def get_history(self, engine_type: str | None = None, limit: int = 50) -> list[OptimizationRecord]:
        with self._lock:
            src = [r for r in self._history if r.engine_type == engine_type] if engine_type else self._history
            return list(src[-limit:])

    def get_pending(self) -> list[OptimizationRecord]:
        with self._lock:
            return [r for r in self._pending.values() if r.status == "pending"]
