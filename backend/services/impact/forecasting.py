"""Metric forecasting for the Research Impact Dashboard.

Implements simple linear regression on time-series data extracted from
research_impact_history, producing 6-month forward projections with 80%
confidence intervals.

All functions degrade gracefully when insufficient history is available:
  - linear_trend: requires >= 2 points; raises ValueError otherwise
  - generate_forecasts: returns None for metrics with < 2 data points

No FastAPI dependencies — pure async service functions.
"""
from __future__ import annotations

import math
import logging
from datetime import datetime, timezone
from typing import Optional

log = logging.getLogger("synaptiq.impact.forecasting")


# ─────────────────────────── pure math ───────────────────────────────────────

def linear_trend(points: list[float], steps_ahead: int = 6) -> dict:
    """Simple linear regression on a time series, with forecast + 80% CI.

    Args:
        points: Chronological list of scalar values (e.g., monthly SIS scores).
                Must contain at least 2 elements.
        steps_ahead: Number of future steps to forecast (default 6).

    Returns:
        {
          "slope": float,
          "intercept": float,
          "r_squared": float,
          "forecast": list[float],          # steps_ahead predicted values
          "confidence_low": list[float],    # 80% CI lower bound
          "confidence_high": list[float],   # 80% CI upper bound
          "trend_direction": "increasing" | "stable" | "decreasing",
          "trend_strength":  "strong" | "moderate" | "weak",
        }

    Raises:
        ValueError: if len(points) < 2.
    """
    n = len(points)
    if n < 2:
        raise ValueError(f"linear_trend requires at least 2 points, got {n}.")

    # x values: 0, 1, 2, ..., n-1
    xs = list(range(n))
    ys = [float(p) for p in points]

    # Means
    x_mean = sum(xs) / n
    y_mean = sum(ys) / n

    # Slope and intercept
    ss_xx = sum((x - x_mean) ** 2 for x in xs)
    ss_xy = sum((xs[i] - x_mean) * (ys[i] - y_mean) for i in range(n))

    slope     = ss_xy / ss_xx if ss_xx != 0 else 0.0
    intercept = y_mean - slope * x_mean

    # R-squared
    y_pred   = [intercept + slope * x for x in xs]
    ss_res   = sum((ys[i] - y_pred[i]) ** 2 for i in range(n))
    ss_tot   = sum((y - y_mean) ** 2 for y in ys)
    r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
    r_squared = max(0.0, round(r_squared, 4))

    # Forecast: next steps_ahead steps after the last observed x
    forecast_xs   = list(range(n, n + steps_ahead))
    forecast_vals = [round(intercept + slope * x, 2) for x in forecast_xs]

    # 80% CI using standard error of regression
    # SE_fit^2 = s^2 * (1/n + (x - x_mean)^2 / ss_xx)
    # z_80 = 1.282 (one-sided 10% tail)
    s_squared = ss_res / max(1, n - 2)          # MSE
    s         = math.sqrt(max(0.0, s_squared))
    z_80      = 1.282

    conf_low:  list[float] = []
    conf_high: list[float] = []
    for x in forecast_xs:
        se_fit = s * math.sqrt(1.0 / n + (x - x_mean) ** 2 / max(1e-9, ss_xx))
        margin = z_80 * se_fit
        conf_low.append(round(forecast_vals[x - n] - margin, 2))
        conf_high.append(round(forecast_vals[x - n] + margin, 2))

    # Trend direction: based on slope relative to mean value magnitude
    mean_magnitude = abs(y_mean) if y_mean != 0 else 1.0
    relative_slope = slope / mean_magnitude

    if relative_slope > 0.02:
        trend_direction = "increasing"
    elif relative_slope < -0.02:
        trend_direction = "decreasing"
    else:
        trend_direction = "stable"

    # Trend strength: based on R-squared
    if r_squared >= 0.7:
        trend_strength = "strong"
    elif r_squared >= 0.35:
        trend_strength = "moderate"
    else:
        trend_strength = "weak"

    return {
        "slope":            round(slope, 4),
        "intercept":        round(intercept, 4),
        "r_squared":        r_squared,
        "forecast":         forecast_vals,
        "confidence_low":   conf_low,
        "confidence_high":  conf_high,
        "trend_direction":  trend_direction,
        "trend_strength":   trend_strength,
    }


# ─────────────────────────── async DB query ───────────────────────────────────

async def generate_forecasts(user_id: str, db) -> dict:
    """Generate 6-month forecasts for key metrics using research_impact_history.

    Pulls the last 24 history snapshots for the user (sorted ascending by date)
    and runs linear_trend on each metric series.

    Returns None for a metric when fewer than 2 data points are available.

    Returns:
        {
          "impact_score":  dict | None,
          "collaboration": dict | None,
          "publications":  dict | None,
          "note":          str,
        }
    """
    uid = user_id

    history_docs = await db.research_impact_history.find(
        {"user_id": uid},
        {
            "sis_total":                  1,
            "active_collaborations":      1,
            "total_publications":         1,
            "created_at":                 1,
        },
    ).sort("created_at", 1).limit(24).to_list(24)

    n = len(history_docs)
    note = f"Forecasts based on {n} data point{'s' if n != 1 else ''}."

    def _extract(field: str) -> list[float]:
        return [float(d.get(field) or 0) for d in history_docs]

    def _try_forecast(values: list[float]) -> Optional[dict]:
        if len(values) < 2:
            return None
        try:
            return linear_trend(values)
        except Exception as exc:
            log.warning("linear_trend failed: %s", exc)
            return None

    sis_vals   = _extract("sis_total")
    collab_vals = _extract("active_collaborations")
    pub_vals    = _extract("total_publications")

    return {
        "impact_score":  _try_forecast(sis_vals),
        "collaboration": _try_forecast(collab_vals),
        "publications":  _try_forecast(pub_vals),
        "note":          note,
    }
