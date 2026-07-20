"""Institution Analytics — Forecasting Engine.

Simple linear extrapolation for publication, citation, and funding forecasts.
No external ML dependencies — pure Python statistics.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _now_year() -> int:
    return _now().year


async def _get_member_ids(institution_id: str, db) -> list[str]:
    rows = await db.institution_memberships.find(
        {"institution_id": institution_id, "status": "active"},
        {"user_id": 1},
    ).to_list(5000)
    return [r["user_id"] for r in rows if r.get("user_id")]


def _linear_regression(xs: list[float], ys: list[float]) -> tuple[float, float]:
    """Return (slope, intercept) for the least-squares line through xs, ys."""
    n = len(xs)
    if n < 2:
        return 0.0, (ys[0] if ys else 0.0)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denominator = sum((x - mean_x) ** 2 for x in xs)
    if denominator == 0:
        return 0.0, mean_y
    slope = numerator / denominator
    intercept = mean_y - slope * mean_x
    return slope, intercept


def _make_forecast(
    xs: list[float],
    ys: list[float],
    future_years: list[int],
    confidence_pct: float = 0.20,
) -> list[dict[str, Any]]:
    """Generate forecasted values with ±confidence_pct confidence band."""
    slope, intercept = _linear_regression(xs, ys)
    result = []
    for yr in future_years:
        predicted = max(0.0, slope * yr + intercept)
        delta = predicted * confidence_pct
        result.append({
            "year": yr,
            "predicted": round(predicted, 2),
            "confidence_low": round(max(0.0, predicted - delta), 2),
            "confidence_high": round(predicted + delta, 2),
        })
    return result


async def generate_forecasts(institution_id: str, db) -> dict:
    """Run linear forecasting for publications, citations, and funding."""
    member_ids = await _get_member_ids(institution_id, db)

    current_year = _now_year()
    history_cutoff = current_year - 5
    future_years = [current_year + 1, current_year + 2, current_year + 3]

    # Fetch historical data in parallel
    pub_history, funding_apps = await asyncio.gather(
        db.publications.aggregate([
            {"$match": {
                "author_ids": {"$in": member_ids} if member_ids else {"$in": []},
                "year": {"$gte": history_cutoff, "$lte": current_year},
            }},
            {"$group": {
                "_id": "$year",
                "publications": {"$sum": 1},
                "citations": {"$sum": {"$ifNull": ["$citation_count", 0]}},
            }},
            {"$sort": {"_id": 1}},
        ]).to_list(10),
        db.grant_applications.find(
            {
                "user_id": {"$in": member_ids} if member_ids else {"$in": []},
                "status": {"$in": ["funded", "awarded", "approved"]},
            },
            {"amount_awarded": 1, "created_at": 1},
        ).to_list(10000),
    )

    # Build year-indexed series
    pub_by_year: dict[int, int] = {}
    cite_by_year: dict[int, int] = {}
    for row in pub_history:
        yr = row["_id"]
        if yr is not None:
            pub_by_year[int(yr)] = int(row["publications"])
            cite_by_year[int(yr)] = int(row["citations"])

    # Funding by year from awarded grant apps
    fund_by_year: dict[int, float] = {}
    for app in funding_apps:
        created = app.get("created_at")
        yr = created.year if created and hasattr(created, "year") else None
        if yr and history_cutoff <= yr <= current_year:
            fund_by_year[yr] = fund_by_year.get(yr, 0.0) + float(app.get("amount_awarded") or 0)

    # Fill all years in range for smooth regression
    all_years = list(range(history_cutoff, current_year + 1))
    xs = [float(yr) for yr in all_years]
    pub_ys = [float(pub_by_year.get(yr, 0)) for yr in all_years]
    cite_ys = [float(cite_by_year.get(yr, 0)) for yr in all_years]
    fund_ys = [fund_by_year.get(yr, 0.0) for yr in all_years]

    years_of_history = len([y for y in pub_by_year if y <= current_year])

    pubs_forecast = _make_forecast(xs, pub_ys, future_years)
    citations_forecast = _make_forecast(xs, cite_ys, future_years)
    funding_forecast = _make_forecast(xs, fund_ys, future_years)

    generated_at = _now().isoformat()
    forecast_data = {
        "publications_forecast": pubs_forecast,
        "citations_forecast": citations_forecast,
        "funding_forecast": funding_forecast,
    }

    # Store in institution_forecasts
    await db.institution_forecasts.update_one(
        {"institution_id": institution_id},
        {"$set": {
            "institution_id": institution_id,
            "forecast_data": forecast_data,
            "model_type": "linear",
            "years_of_history": years_of_history,
            "generated_at": _now(),
        }},
        upsert=True,
    )

    return {
        "publications_forecast": pubs_forecast,
        "citations_forecast": citations_forecast,
        "funding_forecast": funding_forecast,
        "generated_at": generated_at,
        "model_type": "linear",
        "years_of_history": years_of_history,
    }


async def get_latest_forecasts(institution_id: str, db) -> dict | None:
    """Return cached forecast if generated within the last 7 days, else None."""
    doc = await db.institution_forecasts.find_one({"institution_id": institution_id})
    if not doc:
        return None

    generated_at = doc.get("generated_at")
    if not generated_at:
        return None

    if not isinstance(generated_at, datetime):
        return None

    if generated_at.tzinfo is None:
        generated_at = generated_at.replace(tzinfo=timezone.utc)

    age = _now() - generated_at
    if age > timedelta(days=7):
        return None

    forecast_data = doc.get("forecast_data", {})
    return {
        "publications_forecast": forecast_data.get("publications_forecast", []),
        "citations_forecast": forecast_data.get("citations_forecast", []),
        "funding_forecast": forecast_data.get("funding_forecast", []),
        "generated_at": generated_at.isoformat(),
        "model_type": doc.get("model_type", "linear"),
        "years_of_history": doc.get("years_of_history", 0),
    }
