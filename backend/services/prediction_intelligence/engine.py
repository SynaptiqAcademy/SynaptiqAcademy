"""Academic Prediction & Forecasting Intelligence Engine — Async singleton facade (Phase XVIII)."""
from __future__ import annotations

import asyncio
import time

from .career_forecaster      import forecast_career
from .collaboration_forecaster import forecast_collaboration
from .conference_predictor   import predict_conference
from .copilot_integration    import enrich_prompt_with_predictions, generate_copilot_forecasts
from .grant_predictor        import predict_grant
from .institution_forecaster import forecast_institution
from .journal_predictor      import predict_journals
from .models                 import ForecastHorizon, VizType
from .publication_predictor  import predict_publication
from .scenario_simulator     import simulate_scenarios, what_if_analysis
from .strategic_advisor      import advise
from .telemetry              import get_telemetry
from .trend_forecaster       import forecast_trends
from .visualization_builder  import build_visualization


class PredictionIntelligenceEngine:
    """Synchronous facade over all prediction and forecasting services."""

    # ── Publication ───────────────────────────────────────────────────────────

    def predict_publication(self, manuscript: dict) -> dict:
        t0 = time.monotonic()
        tel = get_telemetry()
        try:
            result = predict_publication(manuscript)
            tel.inc("publication_predictions")
            return result.to_dict()
        except Exception:
            tel.inc("errors"); raise
        finally:
            tel.record_latency(time.monotonic() - t0)

    # ── Journal ───────────────────────────────────────────────────────────────

    def predict_journals(self, manuscript: dict, max_results: int = 8) -> dict:
        t0 = time.monotonic()
        tel = get_telemetry()
        try:
            result = predict_journals(manuscript, max_results)
            tel.inc("journal_predictions")
            return result.to_dict()
        except Exception:
            tel.inc("errors"); raise
        finally:
            tel.record_latency(time.monotonic() - t0)

    # ── Conference ────────────────────────────────────────────────────────────

    def predict_conference(self, profile: dict) -> list[dict]:
        t0 = time.monotonic()
        tel = get_telemetry()
        try:
            results = predict_conference(profile)
            tel.inc("conference_predictions")
            return [r.to_dict() for r in results]
        except Exception:
            tel.inc("errors"); raise
        finally:
            tel.record_latency(time.monotonic() - t0)

    # ── Grant ─────────────────────────────────────────────────────────────────

    def predict_grant(self, grant: dict) -> dict:
        t0 = time.monotonic()
        tel = get_telemetry()
        try:
            result = predict_grant(grant)
            tel.inc("grant_predictions")
            return result.to_dict()
        except Exception:
            tel.inc("errors"); raise
        finally:
            tel.record_latency(time.monotonic() - t0)

    # ── Career ────────────────────────────────────────────────────────────────

    def forecast_career(self, profile: dict, horizon: str = "3y") -> dict:
        t0 = time.monotonic()
        tel = get_telemetry()
        try:
            try:
                h = ForecastHorizon(horizon)
            except ValueError:
                h = ForecastHorizon.THREE_YEAR
            result = forecast_career(profile, h)
            tel.inc("career_forecasts")
            return result.to_dict()
        except Exception:
            tel.inc("errors"); raise
        finally:
            tel.record_latency(time.monotonic() - t0)

    # ── Collaboration ─────────────────────────────────────────────────────────

    def forecast_collaboration(self, profile: dict) -> dict:
        t0 = time.monotonic()
        tel = get_telemetry()
        try:
            result = forecast_collaboration(profile)
            tel.inc("collaboration_forecasts")
            return result.to_dict()
        except Exception:
            tel.inc("errors"); raise
        finally:
            tel.record_latency(time.monotonic() - t0)

    # ── Institution ───────────────────────────────────────────────────────────

    def forecast_institution(self, profile: dict, horizon: str = "3y") -> dict:
        t0 = time.monotonic()
        tel = get_telemetry()
        try:
            try:
                h = ForecastHorizon(horizon)
            except ValueError:
                h = ForecastHorizon.THREE_YEAR
            result = forecast_institution(profile, h)
            tel.inc("institution_forecasts")
            return result.to_dict()
        except Exception:
            tel.inc("errors"); raise
        finally:
            tel.record_latency(time.monotonic() - t0)

    # ── Trend ─────────────────────────────────────────────────────────────────

    def forecast_trends(self, profile: dict | None = None, top_k: int = 8) -> dict:
        t0 = time.monotonic()
        tel = get_telemetry()
        try:
            result = forecast_trends(profile, top_k)
            tel.inc("trend_forecasts")
            return result.to_dict()
        except Exception:
            tel.inc("errors"); raise
        finally:
            tel.record_latency(time.monotonic() - t0)

    # ── Strategic decision ────────────────────────────────────────────────────

    def strategic_decision(self, question: str, profile: dict) -> dict:
        t0 = time.monotonic()
        tel = get_telemetry()
        try:
            result = advise(question, profile)
            tel.inc("strategic_decisions")
            return result.to_dict()
        except Exception:
            tel.inc("errors"); raise
        finally:
            tel.record_latency(time.monotonic() - t0)

    # ── Scenario simulation ───────────────────────────────────────────────────

    def simulate_scenarios(
        self,
        manuscript: dict,
        scenario_types: list[str] | None = None,
    ) -> dict:
        t0 = time.monotonic()
        tel = get_telemetry()
        try:
            result = simulate_scenarios(manuscript, scenario_types)
            tel.inc("scenario_simulations")
            return result.to_dict()
        except Exception:
            tel.inc("errors"); raise
        finally:
            tel.record_latency(time.monotonic() - t0)

    # ── What-if ───────────────────────────────────────────────────────────────

    def what_if(self, manuscript: dict, factor: str) -> dict:
        t0 = time.monotonic()
        tel = get_telemetry()
        try:
            result = what_if_analysis(manuscript, factor)
            tel.inc("what_if_analyses")
            return result.to_dict()
        except Exception:
            tel.inc("errors"); raise
        finally:
            tel.record_latency(time.monotonic() - t0)

    # ── Visualization ─────────────────────────────────────────────────────────

    def visualize(self, viz_type: str, data: dict) -> dict:
        t0 = time.monotonic()
        tel = get_telemetry()
        try:
            result = build_visualization(viz_type, data)
            tel.inc("visualizations")
            return result
        except Exception:
            tel.inc("errors"); raise
        finally:
            tel.record_latency(time.monotonic() - t0)

    # ── Copilot ───────────────────────────────────────────────────────────────

    def copilot_forecasts(self, workflow: str, profile: dict) -> list[dict]:
        t0 = time.monotonic()
        tel = get_telemetry()
        try:
            result = generate_copilot_forecasts(workflow, profile)
            tel.inc("copilot_enrichments")
            return result
        except Exception:
            tel.inc("errors"); raise
        finally:
            tel.record_latency(time.monotonic() - t0)

    def copilot_enrich_prompt(self, prompt: str, profile: dict) -> str:
        tel = get_telemetry()
        tel.inc("copilot_enrichments")
        return enrich_prompt_with_predictions(prompt, profile)

    # ── Admin ─────────────────────────────────────────────────────────────────

    def admin_analytics(self) -> dict:
        tel = get_telemetry()
        data = tel.to_dict()
        total = sum(v for k, v in data.items()
                    if isinstance(v, int) and k != "errors")
        return {
            "telemetry": data,
            "total_predictions": total,
            "available_prediction_types": [e.value for e in __import__(
                "services.prediction_intelligence.models", fromlist=["PredictionType"]
            ).PredictionType],
            "available_viz_types": [e.value for e in VizType],
        }


# ── Async singleton ───────────────────────────────────────────────────────────

_engine_instance: PredictionIntelligenceEngine | None = None
_engine_lock = asyncio.Lock()


async def get_prediction_engine() -> PredictionIntelligenceEngine:
    global _engine_instance
    async with _engine_lock:
        if _engine_instance is None:
            _engine_instance = PredictionIntelligenceEngine()
    return _engine_instance


def reset_prediction_engine() -> None:
    global _engine_instance
    _engine_instance = None
