"""Self-Improving Academic Intelligence Engine — Async singleton facade (Phase XX)."""
from __future__ import annotations

import asyncio
import time

from .ab_testing          import ABTestingFramework
from .adaptive_recommender import AdaptiveRecommender
from .audit_log           import get_audit_log
from .benchmark_suite     import run_all_benchmarks, run_benchmark
from .copilot_integration import enrich_with_quality_context, generate_improvement_suggestions
from .feedback_engine     import FeedbackEngine
from .governance          import can_deploy_experiment, get_policy, update_policy
from .knowledge_evolution import KnowledgeEvolutionEngine
from .models              import FeedbackSignal, PlatformQualityReport
from .optimization_engine import OptimizationEngine
from .performance_tracker import PerformanceTracker
from .self_diagnostics    import check_all_engines, check_engine_health, platform_health_score
from .telemetry           import get_telemetry


class SelfImprovementEngine:
    def __init__(self):
        self._feedback    = FeedbackEngine()
        self._performance = PerformanceTracker()
        self._optimizer   = OptimizationEngine()
        self._ab          = ABTestingFramework()
        self._knowledge   = KnowledgeEvolutionEngine()
        self._recommender = AdaptiveRecommender()
        self._audit       = get_audit_log()

    # ── Feedback ──────────────────────────────────────────────────────────────

    def record_feedback(
        self,
        signal_type:           str,
        engine_type:           str,
        outcome:               str   = "",
        recommendation_status: str   = "pending",
        quality_delta:         float = 0.0,
        confidence:            float = 0.0,
        user_cohort:           str   = "general",
        metadata:              dict | None = None,
    ) -> dict:
        tel = get_telemetry()
        t0  = time.monotonic()
        try:
            sig = self._feedback.record_signal(
                signal_type=signal_type,
                engine_type=engine_type,
                outcome=outcome,
                recommendation_status=recommendation_status,
                quality_delta=quality_delta,
                confidence_at_recommendation=confidence,
                user_cohort=user_cohort,
                metadata=metadata or {},
            )
            if outcome in ("accepted", "rejected"):
                self._performance.record_observation(
                    engine_type, confidence, outcome == "accepted",
                    accepted=(recommendation_status == "accepted"),
                )
            tel.inc("signals_received")
            self._audit.log("feedback_recorded", engine_type,
                            {"signal_type": signal_type, "outcome": outcome})
            return sig.to_dict()
        except Exception:
            tel.inc("errors"); raise
        finally:
            tel.record_latency(time.monotonic() - t0)

    def get_feedback_summary(self) -> dict:
        return self._feedback.summary()

    def get_signals(self, engine_type: str | None = None, limit: int = 50) -> list[dict]:
        return [s.to_dict() for s in self._feedback.get_signals(engine_type=engine_type, limit=limit)]

    # ── Performance ───────────────────────────────────────────────────────────

    def get_performance(self, engine_type: str) -> dict:
        return self._performance.compute_metrics(engine_type).to_dict()

    def get_all_performance(self) -> dict:
        return {et: m.to_dict() for et, m in self._performance.get_all_metrics().items()}

    # ── Optimization ──────────────────────────────────────────────────────────

    def generate_optimizations(self) -> list[dict]:
        tel     = get_telemetry()
        policy  = get_policy()
        metrics = self._performance.get_all_metrics()
        cands   = self._optimizer.generate_candidates(metrics, policy)
        for c in cands:
            self._optimizer.add_to_history(c)
        tel.inc("optimizations_generated", len(cands))
        self._audit.log("optimizations_generated", details={"count": len(cands)})
        return [c.to_dict() for c in cands]

    def apply_optimization(self, record_id: str, approved_by: str = "admin") -> bool:
        tel    = get_telemetry()
        result = self._optimizer.apply_optimization(record_id, approved_by)
        if result:
            tel.inc("optimizations_applied")
            self._audit.log("optimization_applied",
                            details={"record_id": record_id, "approved_by": approved_by})
        return result

    def rollback_optimization(self, record_id: str) -> bool:
        tel    = get_telemetry()
        result = self._optimizer.rollback_optimization(record_id)
        if result:
            tel.inc("optimizations_rolled_back")
            self._audit.log("optimization_rolled_back", details={"record_id": record_id})
        return result

    def get_optimization_history(self, engine_type: str | None = None, limit: int = 50) -> list[dict]:
        return [r.to_dict() for r in self._optimizer.get_history(engine_type, limit)]

    def get_pending_optimizations(self) -> list[dict]:
        return [r.to_dict() for r in self._optimizer.get_pending()]

    # ── Benchmarks ────────────────────────────────────────────────────────────

    def run_benchmark(self, engine_type: str) -> dict:
        tel = get_telemetry()
        tel.inc("benchmarks_run")
        self._audit.log("benchmark_run", engine_type)
        return run_benchmark(engine_type)

    def run_all_benchmarks(self) -> dict:
        tel = get_telemetry()
        tel.inc("benchmarks_run")
        self._audit.log("all_benchmarks_run")
        return run_all_benchmarks()

    # ── A/B Testing ───────────────────────────────────────────────────────────

    def create_experiment(
        self,
        name:          str,
        engine_type:   str,
        variant_a:     dict,
        variant_b:     dict,
        description:   str   = "",
        traffic_split: float = 0.5,
    ) -> dict:
        tel = get_telemetry()
        exp = self._ab.create_experiment(name, engine_type, variant_a, variant_b, description, traffic_split)
        tel.inc("experiments_created")
        self._audit.log("experiment_created", engine_type, {"name": name, "id": exp.experiment_id})
        return exp.to_dict()

    def record_experiment_observation(self, experiment_id: str, variant: str, success: bool) -> bool:
        return self._ab.record_observation(experiment_id, variant, success)

    def evaluate_experiment(self, experiment_id: str) -> dict | None:
        exp = self._ab.evaluate_experiment(experiment_id)
        return exp.to_dict() if exp else None

    def complete_experiment(self, experiment_id: str) -> bool:
        tel    = get_telemetry()
        result = self._ab.complete_experiment(experiment_id)
        if result:
            tel.inc("experiments_completed")
            self._audit.log("experiment_completed", details={"experiment_id": experiment_id})
        return result

    def deploy_experiment_winner(self, experiment_id: str) -> dict:
        tel    = get_telemetry()
        policy = get_policy()
        exp    = self._ab.evaluate_experiment(experiment_id)
        if not exp:
            return {"success": False, "reason": "experiment_not_found"}
        if not can_deploy_experiment(exp, policy):
            return {"success": False, "reason": "significance_threshold_not_met",
                    "p_value": exp.p_value,
                    "improvement": round(abs(exp.metric_b - exp.metric_a), 4)}
        deployed = self._ab.deploy_winner(experiment_id)
        if deployed:
            tel.inc("experiments_deployed")
            self._audit.log("experiment_deployed", exp.engine_type,
                            {"experiment_id": experiment_id, "winner": exp.winner})
        return {"success": deployed, "winner": exp.winner, "p_value": exp.p_value}

    def rollback_experiment(self, experiment_id: str) -> bool:
        result = self._ab.rollback_experiment(experiment_id)
        if result:
            self._audit.log("experiment_rolled_back", details={"experiment_id": experiment_id})
        return result

    def get_active_experiments(self) -> list[dict]:
        return [e.to_dict() for e in self._ab.get_active_experiments()]

    def get_all_experiments(self) -> list[dict]:
        return [e.to_dict() for e in self._ab.get_all_experiments()]

    # ── Knowledge Evolution ───────────────────────────────────────────────────

    def ingest_text(self, text: str, source: str = "user") -> list[dict]:
        tel     = get_telemetry()
        updates = self._knowledge.ingest_text(text, source)
        tel.inc("knowledge_updates_detected", len(updates))
        return [u.to_dict() for u in updates]

    def get_pending_knowledge_updates(self, min_confidence: float = 0.0) -> list[dict]:
        return [u.to_dict() for u in self._knowledge.get_pending_updates(min_confidence)]

    def validate_knowledge_update(self, update_id: str) -> dict | None:
        upd = self._knowledge.validate_update(update_id)
        if upd:
            self._audit.log("knowledge_validated", details={"update_id": update_id, "item": upd.item})
        return upd.to_dict() if upd else None

    def integrate_knowledge_update(self, update_id: str) -> bool:
        tel    = get_telemetry()
        result = self._knowledge.integrate_update(update_id)
        if result:
            tel.inc("knowledge_updates_integrated")
            self._audit.log("knowledge_integrated", details={"update_id": update_id})
        return result

    def reject_knowledge_update(self, update_id: str) -> bool:
        result = self._knowledge.reject_update(update_id)
        if result:
            self._audit.log("knowledge_rejected", details={"update_id": update_id})
        return result

    def knowledge_summary(self) -> dict:
        return self._knowledge.summary()

    # ── Adaptive Recommendations ──────────────────────────────────────────────

    def personalize(
        self,
        recommendations: list[dict],
        cohort_id:       str,
        category_key:    str = "category",
        score_key:       str = "score",
    ) -> list[dict]:
        return self._recommender.personalize_recommendations(recommendations, cohort_id, category_key, score_key)

    def record_cohort_feedback(self, cohort_id: str, category: str, accepted: bool) -> None:
        self._recommender.record_cohort_feedback(cohort_id, category, accepted)

    def get_cohort_profile(self, cohort_id: str) -> dict:
        signals = self._feedback.get_signals(limit=500)
        return self._recommender.build_cohort_profile(cohort_id, signals)

    # ── Diagnostics ───────────────────────────────────────────────────────────

    def run_diagnostics(self) -> list[dict]:
        tel     = get_telemetry()
        metrics = self._performance.get_all_metrics()
        reports = check_all_engines(metrics)
        tel.inc("diagnostics_run")
        return [r.to_dict() for r in reports]

    def run_engine_diagnostic(self, engine_type: str) -> dict:
        tel     = get_telemetry()
        metrics = self._performance.compute_metrics(engine_type)
        report  = check_engine_health(engine_type, metrics)
        tel.inc("diagnostics_run")
        return report.to_dict()

    # ── Platform Quality ──────────────────────────────────────────────────────

    def get_platform_quality(self) -> dict:
        all_metrics  = self._performance.get_all_metrics()
        all_reports  = check_all_engines(all_metrics)
        engine_scores = {r.engine_type: r.health_score for r in all_reports}
        health        = platform_health_score(all_reports) if all_reports else 0.5

        engines = list(all_metrics.values())
        avg_acc = sum(m.accuracy for m in engines) / len(engines) if engines else 0.0
        avg_cal = sum(m.calibration_error for m in engines) / len(engines) if engines else 0.0
        acc_rates = [self._feedback.acceptance_rate(et) for et in all_metrics]
        avg_acceptance = sum(acc_rates) / len(acc_rates) if acc_rates else 0.0

        report = PlatformQualityReport(
            overall_score=round(health * 100, 2),
            engine_scores=engine_scores,
            recommendation_acceptance_rate=round(avg_acceptance, 4),
            prediction_accuracy=round(avg_acc, 4),
            validation_quality=round(max(0.0, 1.0 - avg_cal * 2), 4),
            retrieval_quality=round(health * 0.9, 4),
            routing_efficiency=round(health, 4),
            user_satisfaction=round(avg_acceptance * 0.7 + health * 0.3, 4),
            active_experiments=len(self._ab.get_active_experiments()),
            pending_optimizations=len(self._optimizer.get_pending()),
            knowledge_updates_pending=len(self._knowledge.get_pending_updates()),
        )
        return report.to_dict()

    # ── Governance ────────────────────────────────────────────────────────────

    def get_policy(self) -> dict:
        return get_policy().to_dict()

    def update_policy(self, updates: dict, updated_by: str = "admin") -> dict:
        policy = update_policy(updates, updated_by)
        self._audit.log("policy_updated", details={"updates": updates, "by": updated_by})
        return policy.to_dict()

    # ── Audit ─────────────────────────────────────────────────────────────────

    def get_audit_log(self, engine_type: str | None = None, limit: int = 100) -> list[dict]:
        return self._audit.get_log(engine_type, limit)

    # ── Copilot ───────────────────────────────────────────────────────────────

    def copilot_suggestions(self, workflow: str, max_suggestions: int = 5) -> list[dict]:
        all_metrics = self._performance.get_all_metrics()
        return generate_improvement_suggestions(workflow, all_metrics, max_suggestions)

    def copilot_enrich_prompt(self, prompt: str) -> str:
        all_metrics = self._performance.get_all_metrics()
        reports     = check_all_engines(all_metrics)
        return enrich_with_quality_context(prompt, reports)

    # ── Telemetry ─────────────────────────────────────────────────────────────

    def get_telemetry(self) -> dict:
        return get_telemetry().to_dict()


# ── Async singleton ────────────────────────────────────────────────────────────

_engine_instance: SelfImprovementEngine | None = None
_engine_lock = asyncio.Lock()


async def get_self_improvement_engine() -> SelfImprovementEngine:
    global _engine_instance
    async with _engine_lock:
        if _engine_instance is None:
            _engine_instance = SelfImprovementEngine()
    return _engine_instance


def reset_self_improvement_engine() -> None:
    global _engine_instance
    _engine_instance = None
