"""Adaptive Recommender — privacy-preserving personalization using cohort profiles."""
from __future__ import annotations

import threading
from collections import defaultdict

from .models import FeedbackSignal, RecommendationStatus

_MAX_COHORT_SIGNALS = 500


class AdaptiveRecommender:
    """
    Personalizes recommendation ordering using anonymized cohort preferences.
    No individual user data is stored — only aggregated per-cohort acceptance rates.
    """

    def __init__(self):
        self._lock   = threading.Lock()
        # cohort_id → category → {"accepted": int, "total": int}
        self._prefs: dict[str, dict[str, dict[str, int]]] = defaultdict(
            lambda: defaultdict(lambda: {"accepted": 0, "total": 0})
        )
        self._counts: dict[str, int] = defaultdict(int)

    def record_cohort_feedback(
        self,
        cohort_id:                str,
        recommendation_category:  str,
        accepted:                 bool,
    ) -> None:
        with self._lock:
            if self._counts[cohort_id] >= _MAX_COHORT_SIGNALS:
                return
            p = self._prefs[cohort_id][recommendation_category]
            p["total"]   += 1
            p["accepted"] += int(accepted)
            self._counts[cohort_id] += 1

    def compute_cohort_preferences(self, cohort_id: str) -> dict[str, dict]:
        with self._lock:
            raw = dict(self._prefs.get(cohort_id, {}))
        result = {}
        for cat, counts in raw.items():
            total = counts["total"]
            result[cat] = {
                "acceptance_rate": round(counts["accepted"] / total, 4) if total else 0.5,
                "sample_size":     total,
            }
        return result

    def personalize_recommendations(
        self,
        recommendations: list[dict],
        cohort_id:       str,
        category_key:    str = "category",
        score_key:       str = "score",
    ) -> list[dict]:
        """Re-rank recommendations: 70% original score + 30% cohort preference."""
        prefs = self.compute_cohort_preferences(cohort_id)
        if not prefs:
            return recommendations

        def _boost(rec: dict) -> float:
            cat      = rec.get(category_key, "general")
            acc_rate = prefs.get(cat, {}).get("acceptance_rate", 0.5)
            base     = float(rec.get(score_key, 0.5))
            return base * 0.70 + acc_rate * 0.30

        return sorted(recommendations, key=_boost, reverse=True)

    def build_cohort_profile(self, cohort_id: str, signals: list[FeedbackSignal]) -> dict:
        """Build anonymous cohort profile from a list of FeedbackSignals."""
        cohort_signals = [s for s in signals if s.user_cohort == cohort_id]
        if not cohort_signals:
            return {"cohort_id": cohort_id, "profile": {}, "signal_count": 0}

        engine_acc: dict[str, list[bool]] = defaultdict(list)
        deltas: list[float] = []

        for s in cohort_signals:
            engine_acc[s.engine_type].append(s.recommendation_status == RecommendationStatus.ACCEPTED.value)
            deltas.append(s.quality_delta)

        profile = {
            et: {
                "acceptance_rate": round(sum(v) / len(v), 4),
                "sample_size":     len(v),
            }
            for et, v in engine_acc.items()
        }
        return {
            "cohort_id":         cohort_id,
            "profile":           profile,
            "avg_quality_delta": round(sum(deltas) / len(deltas), 4) if deltas else 0.0,
            "signal_count":      len(cohort_signals),
        }

    def get_cohort_ids(self) -> list[str]:
        with self._lock:
            return list(self._prefs.keys())
