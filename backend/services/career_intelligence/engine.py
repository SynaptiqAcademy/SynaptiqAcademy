"""Academic Career Intelligence Engine — Async singleton facade (Phase XVI)."""
from __future__ import annotations

import asyncio
import time
from typing import Any

from .career_profiler       import build_career_profile
from .copilot_integration   import generate_copilot_suggestions
from .export_engine         import generate_export
from .goal_manager          import evaluate_goals, infer_default_goals
from .models                import (
    ExportFormat, ExportReportType, PromotionTarget, RoadmapHorizon,
)
from .productivity_analyzer import analyse_productivity
from .promotion_readiness   import assess_promotion_readiness
from .recommendation_engine import generate_recommendations
from .risk_analyzer         import detect_career_risks
from .roadmap_builder       import build_roadmap
from .skill_gap_analyzer    import analyse_skill_gaps
from .telemetry             import get_telemetry
from .visualization_builder import build_visualization


class CareerIntelligenceEngine:
    """Synchronous pure-Python engine; wrapped by async singleton below."""

    # ── Core methods ──────────────────────────────────────────────────────────

    def build_profile(self, user: dict) -> dict:
        t0 = time.monotonic()
        tel = get_telemetry()
        try:
            result = build_career_profile(user).to_dict()
            tel.inc("profile_builds")
            return result
        except Exception as exc:
            tel.inc("errors")
            raise
        finally:
            tel.record_latency(time.monotonic() - t0)

    def build_roadmap(self, user: dict, horizon: str = "3_year") -> dict:
        t0 = time.monotonic()
        tel = get_telemetry()
        try:
            profile = build_career_profile(user)
            try:
                h = RoadmapHorizon(horizon)
            except ValueError:
                h = RoadmapHorizon.THREE_YEAR
            result = build_roadmap(profile, h).to_dict()
            tel.inc("roadmap_builds")
            return result
        except Exception:
            tel.inc("errors")
            raise
        finally:
            tel.record_latency(time.monotonic() - t0)

    def evaluate_goals(self, user: dict, goals: list[dict] | None = None) -> dict:
        t0 = time.monotonic()
        tel = get_telemetry()
        try:
            profile = build_career_profile(user)
            if goals:
                evaluated = evaluate_goals(profile, goals)
            else:
                evaluated = infer_default_goals(profile)
            tel.inc("goal_evaluations")
            return {"goals": [g.to_dict() for g in evaluated], "total": len(evaluated)}
        except Exception:
            tel.inc("errors")
            raise
        finally:
            tel.record_latency(time.monotonic() - t0)

    def analyse_skill_gaps(self, user: dict) -> dict:
        t0 = time.monotonic()
        tel = get_telemetry()
        try:
            profile = build_career_profile(user)
            result  = analyse_skill_gaps(profile).to_dict()
            tel.inc("skill_analyses")
            return result
        except Exception:
            tel.inc("errors")
            raise
        finally:
            tel.record_latency(time.monotonic() - t0)

    def assess_promotion(self, user: dict, target: str = "associate_professor") -> dict:
        t0 = time.monotonic()
        tel = get_telemetry()
        try:
            profile = build_career_profile(user)
            try:
                pt = PromotionTarget(target)
            except ValueError:
                pt = PromotionTarget.ASSOCIATE_PROF
            result = assess_promotion_readiness(profile, pt).to_dict()
            tel.inc("promotion_checks")
            return result
        except Exception:
            tel.inc("errors")
            raise
        finally:
            tel.record_latency(time.monotonic() - t0)

    def analyse_productivity(self, user: dict) -> dict:
        t0 = time.monotonic()
        tel = get_telemetry()
        try:
            profile = build_career_profile(user)
            result  = analyse_productivity(profile).to_dict()
            tel.inc("productivity_checks")
            return result
        except Exception:
            tel.inc("errors")
            raise
        finally:
            tel.record_latency(time.monotonic() - t0)

    def detect_risks(self, user: dict) -> dict:
        t0 = time.monotonic()
        tel = get_telemetry()
        try:
            profile = build_career_profile(user)
            risks   = detect_career_risks(profile)
            tel.inc("risk_analyses")
            return {"risks": [r.to_dict() for r in risks], "total": len(risks)}
        except Exception:
            tel.inc("errors")
            raise
        finally:
            tel.record_latency(time.monotonic() - t0)

    def generate_recommendations(self, user: dict) -> dict:
        t0 = time.monotonic()
        tel = get_telemetry()
        try:
            profile = build_career_profile(user)
            result  = generate_recommendations(profile)
            tel.inc("recommendation_runs")
            return result
        except Exception:
            tel.inc("errors")
            raise
        finally:
            tel.record_latency(time.monotonic() - t0)

    def copilot_suggestions(self, user: dict) -> dict:
        t0 = time.monotonic()
        tel = get_telemetry()
        try:
            profile = build_career_profile(user)
            result  = generate_copilot_suggestions(profile)
            tel.inc("copilot_suggestions")
            return {"suggestions": result, "total": len(result)}
        except Exception:
            tel.inc("errors")
            raise
        finally:
            tel.record_latency(time.monotonic() - t0)

    def visualization(self, user: dict, viz_type: str, **kwargs: Any) -> dict:
        t0 = time.monotonic()
        tel = get_telemetry()
        try:
            profile = build_career_profile(user)
            result  = build_visualization(viz_type, profile=profile, **kwargs)
            tel.inc("visualizations")
            return result
        except Exception:
            tel.inc("errors")
            raise
        finally:
            tel.record_latency(time.monotonic() - t0)

    def export_report(
        self,
        user: dict,
        report_type: str = "career_report",
        export_format: str = "pdf",
    ) -> dict:
        t0 = time.monotonic()
        tel = get_telemetry()
        try:
            profile      = build_career_profile(user)
            productivity = analyse_productivity(profile)
            risks        = detect_career_risks(profile)
            recs         = generate_recommendations(profile)
            skill_report = analyse_skill_gaps(profile).to_dict()
            result = generate_export(
                report_type=report_type,
                export_format=export_format,
                profile=profile,
                productivity=productivity,
                risks=[r.to_dict() for r in risks],
                recommendations=recs,
                skill_report=skill_report,
            )
            tel.inc("exports")
            return result
        except Exception:
            tel.inc("errors")
            raise
        finally:
            tel.record_latency(time.monotonic() - t0)

    def full_analysis(self, user: dict) -> dict:
        """Run all engines and return a comprehensive career intelligence report."""
        t0 = time.monotonic()
        tel = get_telemetry()
        try:
            profile      = build_career_profile(user)
            roadmap      = build_roadmap(profile, RoadmapHorizon.THREE_YEAR)
            goals        = infer_default_goals(profile)
            skill_report = analyse_skill_gaps(profile)
            readiness    = assess_promotion_readiness(profile, PromotionTarget.ASSOCIATE_PROF)
            productivity = analyse_productivity(profile)
            risks        = detect_career_risks(profile)
            recs         = generate_recommendations(profile)
            copilot      = generate_copilot_suggestions(profile)

            tel.inc("full_analyses")
            return {
                "profile":       profile.to_dict(),
                "roadmap":       roadmap.to_dict(),
                "goals":         [g.to_dict() for g in goals],
                "skill_gaps":    skill_report.to_dict(),
                "promotion":     readiness.to_dict(),
                "productivity":  productivity.to_dict(),
                "risks":         [r.to_dict() for r in risks],
                "recommendations": recs,
                "copilot":       copilot,
            }
        except Exception:
            tel.inc("errors")
            raise
        finally:
            tel.record_latency(time.monotonic() - t0)

    def admin_analytics(self, users: list[dict]) -> dict:
        """Aggregate career intelligence across a list of user dicts."""
        profiles = [build_career_profile(u) for u in users]
        if not profiles:
            return {"total_users": 0}
        avg_h   = round(sum(p.h_index for p in profiles) / len(profiles), 2)
        avg_pub = round(sum(p.publication_count for p in profiles) / len(profiles), 2)
        stage_counts: dict[str, int] = {}
        for p in profiles:
            stage_counts[p.career_stage.value] = stage_counts.get(p.career_stage.value, 0) + 1
        return {
            "total_users":        len(profiles),
            "avg_h_index":        avg_h,
            "avg_publications":   avg_pub,
            "stage_distribution": stage_counts,
        }


# ── Async singleton ───────────────────────────────────────────────────────────

_engine_instance: CareerIntelligenceEngine | None = None
_engine_lock = asyncio.Lock()


async def get_career_engine() -> CareerIntelligenceEngine:
    global _engine_instance
    async with _engine_lock:
        if _engine_instance is None:
            _engine_instance = CareerIntelligenceEngine()
    return _engine_instance


def reset_career_engine() -> None:
    global _engine_instance
    _engine_instance = None
