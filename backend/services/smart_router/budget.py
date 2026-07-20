"""BudgetManager — tracks and enforces daily/weekly/monthly AI spending.

Uses MongoDB for persistent spend tracking. All operations are best-effort —
if MongoDB is unavailable, budget checks pass to avoid service disruption.
"""
from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any

from services.smart_router.config import SmartRouterConfig
from services.smart_router.types import BudgetStatus, RouterSignal

logger = logging.getLogger(__name__)

_COLL = "smart_router_budget"


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _week_key() -> str:
    now = datetime.now(timezone.utc)
    return f"{now.year}-W{now.isocalendar().week:02d}"


def _month_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m")


class BudgetManager:
    """Per-platform budget enforcement with automatic downgrade signals."""

    def __init__(self, config: SmartRouterConfig, db: Any) -> None:
        self._config = config
        self._db = db
        self._cache: dict[str, tuple[float, float]] = {}  # key → (value, expires)
        self._lock = asyncio.Lock()

    async def check(
        self,
        estimated_cost_usd: float,
        user_id: str = "platform",
    ) -> BudgetStatus:
        """Check if the estimated cost is within budget. Returns routing signal."""
        try:
            daily = await self._get_spend("day", _today())
            monthly = await self._get_spend("month", _month_key())

            daily_limit = self._config.daily_budget_usd
            monthly_limit = self._config.monthly_budget_usd

            daily_after = daily + estimated_cost_usd
            monthly_after = monthly + estimated_cost_usd

            daily_pct = (daily_after / daily_limit * 100) if daily_limit > 0 else 0
            monthly_pct = (monthly_after / monthly_limit * 100) if monthly_limit > 0 else 0

            max_pct = max(daily_pct, monthly_pct)

            if max_pct >= self._config.budget_reject_pct:
                signal = RouterSignal.REJECT
            elif max_pct >= self._config.budget_throttle_pct:
                signal = RouterSignal.DOWNGRADE
            elif max_pct >= self._config.budget_alert_pct:
                signal = RouterSignal.THROTTLE
            else:
                signal = RouterSignal.PROCEED

            return BudgetStatus(
                signal=signal,
                daily_used_usd=round(daily, 4),
                daily_limit_usd=daily_limit,
                monthly_used_usd=round(monthly, 4),
                monthly_limit_usd=monthly_limit,
                remaining_daily_usd=round(max(0.0, daily_limit - daily), 4),
                remaining_monthly_usd=round(max(0.0, monthly_limit - monthly), 4),
                utilization_pct=round(max_pct, 1),
                recommended_layer="local" if signal == RouterSignal.DOWNGRADE else None,
            )
        except Exception as exc:
            logger.warning("Budget check failed (permissive): %s", exc)
            return BudgetStatus(signal=RouterSignal.PROCEED)

    async def record(
        self,
        actual_cost_usd: float,
        feature: str = "",
        layer: str = "",
        user_id: str = "platform",
    ) -> None:
        """Record actual cost after execution."""
        if actual_cost_usd <= 0:
            return
        try:
            now = datetime.now(timezone.utc)
            await self._db[_COLL].update_one(
                {"_id": f"day:{_today()}"},
                {
                    "$inc": {"total_usd": actual_cost_usd, "requests": 1},
                    "$set": {"date": _today()},
                    "$push": {
                        "recent": {
                            "$each": [{"feature": feature, "layer": layer,
                                       "cost": actual_cost_usd, "ts": now.isoformat()}],
                            "$slice": -100,
                        }
                    },
                },
                upsert=True,
            )
            await self._db[_COLL].update_one(
                {"_id": f"month:{_month_key()}"},
                {
                    "$inc": {"total_usd": actual_cost_usd, "requests": 1},
                    "$set": {"month": _month_key()},
                },
                upsert=True,
            )
            # Invalidate cache
            async with self._lock:
                self._cache.pop(f"day:{_today()}", None)
                self._cache.pop(f"month:{_month_key()}", None)
        except Exception as exc:
            logger.warning("Budget record failed: %s", exc)

    async def get_summary(self) -> dict:
        """Return current budget utilization summary."""
        try:
            daily = await self._get_spend("day", _today())
            weekly = await self._get_spend("week", _week_key())
            monthly = await self._get_spend("month", _month_key())
            return {
                "daily": {
                    "used_usd": round(daily, 4),
                    "limit_usd": self._config.daily_budget_usd,
                    "remaining_usd": round(max(0, self._config.daily_budget_usd - daily), 4),
                    "utilization_pct": round(daily / self._config.daily_budget_usd * 100, 1)
                    if self._config.daily_budget_usd > 0 else 0,
                },
                "weekly": {
                    "used_usd": round(weekly, 4),
                    "limit_usd": self._config.weekly_budget_usd,
                    "remaining_usd": round(max(0, self._config.weekly_budget_usd - weekly), 4),
                },
                "monthly": {
                    "used_usd": round(monthly, 4),
                    "limit_usd": self._config.monthly_budget_usd,
                    "remaining_usd": round(max(0, self._config.monthly_budget_usd - monthly), 4),
                    "utilization_pct": round(monthly / self._config.monthly_budget_usd * 100, 1)
                    if self._config.monthly_budget_usd > 0 else 0,
                },
                "date": _today(),
            }
        except Exception as exc:
            logger.warning("Budget summary failed: %s", exc)
            return {}

    async def get_daily_breakdown(self, days: int = 7) -> list[dict]:
        """Return per-day cost breakdown for the last N days."""
        try:
            docs = await self._db[_COLL].find(
                {"_id": {"$regex": r"^day:"}},
            ).sort("date", -1).limit(days).to_list(length=days)
            return [
                {
                    "date": d.get("date", ""),
                    "total_usd": round(d.get("total_usd", 0), 4),
                    "requests": d.get("requests", 0),
                }
                for d in docs
            ]
        except Exception:
            return []

    async def _get_spend(self, period: str, key: str) -> float:
        cache_key = f"{period}:{key}"
        async with self._lock:
            if cache_key in self._cache:
                val, expires = self._cache[cache_key]
                if time.monotonic() < expires:
                    return val
        try:
            doc = await self._db[_COLL].find_one({"_id": f"{period}:{key}"})
            val = float(doc.get("total_usd", 0)) if doc else 0.0
        except Exception:
            val = 0.0
        async with self._lock:
            self._cache[cache_key] = (val, time.monotonic() + 30.0)  # 30s cache
        return val
