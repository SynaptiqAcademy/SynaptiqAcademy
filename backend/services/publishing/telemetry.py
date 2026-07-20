"""Academic Publishing Intelligence — Thread-safe telemetry singleton (Phase XII)."""
from __future__ import annotations

import threading
import time


class PublishingTelemetry:
    _instance: "PublishingTelemetry | None" = None
    _lock = threading.Lock()

    def __new__(cls) -> "PublishingTelemetry":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._init()
                    cls._instance = inst
        return cls._instance

    def _init(self) -> None:
        self._mu = threading.Lock()
        self._journal_analyses: int = 0
        self._journal_matches: int = 0
        self._conference_matches: int = 0
        self._grant_matches: int = 0
        self._readiness_checks: int = 0
        self._cover_letters: int = 0
        self._reviewer_responses: int = 0
        self._strategies: int = 0
        self._risk_analyses: int = 0
        self._dashboard_views: int = 0
        self._exports: int = 0
        self._errors: int = 0
        self._latencies: list[float] = []

    # ── Increment helpers ─────────────────────────────────────────────────────

    def record_journal_analysis(self) -> None:
        with self._mu: self._journal_analyses += 1

    def record_journal_match(self) -> None:
        with self._mu: self._journal_matches += 1

    def record_conference_match(self) -> None:
        with self._mu: self._conference_matches += 1

    def record_grant_match(self) -> None:
        with self._mu: self._grant_matches += 1

    def record_readiness_check(self) -> None:
        with self._mu: self._readiness_checks += 1

    def record_cover_letter(self) -> None:
        with self._mu: self._cover_letters += 1

    def record_reviewer_response(self) -> None:
        with self._mu: self._reviewer_responses += 1

    def record_strategy(self) -> None:
        with self._mu: self._strategies += 1

    def record_risk_analysis(self) -> None:
        with self._mu: self._risk_analyses += 1

    def record_dashboard_view(self) -> None:
        with self._mu: self._dashboard_views += 1

    def record_export(self) -> None:
        with self._mu: self._exports += 1

    def record_error(self) -> None:
        with self._mu: self._errors += 1

    def record_latency(self, seconds: float) -> None:
        with self._mu:
            self._latencies.append(seconds)
            if len(self._latencies) > 1000:
                self._latencies = self._latencies[-1000:]

    # ── Read ──────────────────────────────────────────────────────────────────

    def snapshot(self) -> dict:
        with self._mu:
            lats = sorted(self._latencies)
            n = len(lats)
            p50 = lats[int(n * 0.50)] if n else 0.0
            p95 = lats[int(n * 0.95)] if n else 0.0
            avg = sum(lats) / n if n else 0.0
            return {
                "journal_analyses":    self._journal_analyses,
                "journal_matches":     self._journal_matches,
                "conference_matches":  self._conference_matches,
                "grant_matches":       self._grant_matches,
                "readiness_checks":    self._readiness_checks,
                "cover_letters":       self._cover_letters,
                "reviewer_responses":  self._reviewer_responses,
                "strategies":          self._strategies,
                "risk_analyses":       self._risk_analyses,
                "dashboard_views":     self._dashboard_views,
                "exports":             self._exports,
                "errors":              self._errors,
                "latency_p50_s":       round(p50, 4),
                "latency_p95_s":       round(p95, 4),
                "latency_avg_s":       round(avg, 4),
                "sample_count":        n,
            }

    def reset(self) -> None:
        with self._mu:
            self._init()


def get_telemetry() -> PublishingTelemetry:
    return PublishingTelemetry()
