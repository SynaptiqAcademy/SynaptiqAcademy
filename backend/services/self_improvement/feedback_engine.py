"""Feedback Engine — collect and analyze anonymized learning signals."""
from __future__ import annotations

import threading
from collections import defaultdict

from .models import FeedbackSignal, RecommendationStatus

_MAX_SIGNALS = 10_000
_PII_KEYS    = frozenset({"user_id", "email", "name", "institution_id", "ip_address", "user_name"})


class FeedbackEngine:
    def __init__(self):
        self._lock     = threading.Lock()
        self._signals: list[FeedbackSignal]              = []
        self._by_engine: dict[str, list[FeedbackSignal]] = defaultdict(list)

    def record_signal(
        self,
        signal_type:                 str,
        engine_type:                 str,
        outcome:                     str   = "",
        recommendation_status:       str   = RecommendationStatus.PENDING.value,
        quality_delta:               float = 0.0,
        confidence_at_recommendation: float = 0.0,
        user_cohort:                 str   = "general",
        metadata:                    dict | None = None,
    ) -> FeedbackSignal:
        signal = FeedbackSignal(
            signal_type=signal_type,
            engine_type=engine_type,
            outcome=outcome,
            recommendation_status=recommendation_status,
            quality_delta=quality_delta,
            confidence_at_recommendation=confidence_at_recommendation,
            user_cohort=user_cohort,
            metadata=self._anonymize(metadata or {}),
        )
        with self._lock:
            self._signals.append(signal)
            self._by_engine[engine_type].append(signal)
            if len(self._signals) > _MAX_SIGNALS:
                oldest = self._signals.pop(0)
                eng_list = self._by_engine[oldest.engine_type]
                for i, s in enumerate(eng_list):
                    if s.signal_id == oldest.signal_id:
                        eng_list.pop(i)
                        break
        return signal

    def get_signals(
        self,
        engine_type: str | None = None,
        signal_type: str | None = None,
        limit:       int        = 100,
    ) -> list[FeedbackSignal]:
        with self._lock:
            src = list(self._by_engine.get(engine_type, [])) if engine_type else list(self._signals)
        if signal_type:
            src = [s for s in src if s.signal_type == signal_type]
        return src[-limit:]

    def acceptance_rate(self, engine_type: str) -> float:
        with self._lock:
            signals = list(self._by_engine.get(engine_type, []))
        if not signals:
            return 0.0
        accepted = sum(1 for s in signals if s.recommendation_status == RecommendationStatus.ACCEPTED.value)
        return round(accepted / len(signals), 4)

    def quality_improvement_rate(self, engine_type: str) -> float:
        with self._lock:
            signals = list(self._by_engine.get(engine_type, []))
        if not signals:
            return 0.0
        return round(sum(s.quality_delta for s in signals) / len(signals), 4)

    def summary(self) -> dict:
        with self._lock:
            total    = len(self._signals)
            by_eng   = {k: len(v) for k, v in self._by_engine.items()}
            by_type: dict[str, int] = {}
            for s in self._signals:
                by_type[s.signal_type] = by_type.get(s.signal_type, 0) + 1
        return {"total_signals": total, "by_engine": by_eng, "by_signal_type": by_type}

    @staticmethod
    def _anonymize(metadata: dict) -> dict:
        return {k: v for k, v in metadata.items() if k not in _PII_KEYS}
