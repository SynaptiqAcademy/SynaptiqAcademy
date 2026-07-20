"""Pure-Python statistical computation engine — no external dependencies."""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any


class StatsEngine:
    """All operations are static methods — no instantiation required."""

    @staticmethod
    def mean(values: list[float]) -> float:
        if not values:
            return 0.0
        return sum(values) / len(values)

    @staticmethod
    def median(values: list[float]) -> float:
        if not values:
            return 0.0
        s = sorted(values)
        n = len(s)
        mid = n // 2
        return (s[mid - 1] + s[mid]) / 2.0 if n % 2 == 0 else float(s[mid])

    @staticmethod
    def mode(values: list[float]) -> list[float]:
        if not values:
            return []
        from collections import Counter
        counts = Counter(values)
        max_count = max(counts.values())
        return sorted(k for k, v in counts.items() if v == max_count)

    @staticmethod
    def variance(values: list[float], sample: bool = True) -> float:
        n = len(values)
        if n < 2:
            return 0.0
        m = StatsEngine.mean(values)
        denom = n - 1 if sample else n
        return sum((x - m) ** 2 for x in values) / denom

    @staticmethod
    def std_dev(values: list[float], sample: bool = True) -> float:
        return math.sqrt(StatsEngine.variance(values, sample))

    @staticmethod
    def percentile(values: list[float], p: float) -> float:
        """p in [0, 100]. Linear interpolation (method 7 / nearest-rank)."""
        if not values:
            return 0.0
        s = sorted(values)
        n = len(s)
        idx = (p / 100.0) * (n - 1)
        lo = int(idx)
        hi = lo + 1
        if hi >= n:
            return float(s[-1])
        frac = idx - lo
        return s[lo] * (1.0 - frac) + s[hi] * frac

    @staticmethod
    def quartiles(values: list[float]) -> dict[str, float]:
        return {
            "q1": StatsEngine.percentile(values, 25),
            "q2": StatsEngine.percentile(values, 50),
            "q3": StatsEngine.percentile(values, 75),
            "iqr": StatsEngine.percentile(values, 75) - StatsEngine.percentile(values, 25),
        }

    @staticmethod
    def z_score(value: float, mean: float, std: float) -> float:
        return (value - mean) / std if std != 0 else 0.0

    @staticmethod
    def z_scores(values: list[float]) -> list[float]:
        m = StatsEngine.mean(values)
        s = StatsEngine.std_dev(values)
        return [StatsEngine.z_score(v, m, s) for v in values]

    @staticmethod
    def normalize(values: list[float]) -> list[float]:
        """Min-max normalization to [0, 1]."""
        if not values:
            return []
        lo, hi = min(values), max(values)
        if hi == lo:
            return [0.5] * len(values)
        return [(v - lo) / (hi - lo) for v in values]

    @staticmethod
    def standardize(values: list[float]) -> list[float]:
        """Z-score standardization (mean=0, std=1)."""
        return StatsEngine.z_scores(values)

    @staticmethod
    def growth_rate(old: float, new: float) -> float:
        """Percentage growth from old to new. Returns 0 if old==0."""
        if old == 0:
            return 100.0 if new > 0 else 0.0
        return round((new - old) / abs(old) * 100, 2)

    @staticmethod
    def moving_average(values: list[float], window: int) -> list[float]:
        if window < 1 or not values:
            return list(values)
        result: list[float] = []
        for i in range(len(values)):
            start = max(0, i - window + 1)
            chunk = values[start:i + 1]
            result.append(sum(chunk) / len(chunk))
        return result

    @staticmethod
    def exponential_moving_average(values: list[float], alpha: float = 0.3) -> list[float]:
        if not values:
            return []
        ema = [values[0]]
        for v in values[1:]:
            ema.append(alpha * v + (1 - alpha) * ema[-1])
        return ema

    @staticmethod
    def linear_trend(values: list[float]) -> dict[str, Any]:
        """OLS linear regression on index sequence. Returns slope, intercept, r_squared, direction."""
        n = len(values)
        if n < 2:
            return {
                "slope": 0.0,
                "intercept": float(values[0]) if values else 0.0,
                "r_squared": 0.0,
                "direction": "stable",
                "predicted_next": float(values[0]) if values else 0.0,
            }
        xs = list(range(n))
        sx = sum(xs)
        sy = sum(values)
        sxy = sum(i * v for i, v in zip(xs, values))
        sx2 = sum(i * i for i in xs)
        denom = n * sx2 - sx * sx
        if denom == 0:
            return {"slope": 0.0, "intercept": sy / n, "r_squared": 0.0,
                    "direction": "stable", "predicted_next": sy / n}
        slope = (n * sxy - sx * sy) / denom
        intercept = (sy - slope * sx) / n
        y_mean = sy / n
        ss_tot = sum((v - y_mean) ** 2 for v in values)
        y_pred = [slope * i + intercept for i in xs]
        ss_res = sum((v - p) ** 2 for v, p in zip(values, y_pred))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 1.0
        direction = "stable"
        if slope > 0.01 * (abs(y_mean) + 1e-9):
            direction = "increasing"
        elif slope < -0.01 * (abs(y_mean) + 1e-9):
            direction = "decreasing"
        return {
            "slope": round(slope, 6),
            "intercept": round(intercept, 4),
            "r_squared": round(max(0.0, r2), 4),
            "direction": direction,
            "predicted_next": round(slope * n + intercept, 4),
        }

    @staticmethod
    def forecast(values: list[float], steps: int = 6) -> list[float]:
        """Simple linear extrapolation for `steps` future values."""
        t = StatsEngine.linear_trend(values)
        n = len(values)
        return [round(t["slope"] * (n + i) + t["intercept"], 4) for i in range(steps)]

    @staticmethod
    def distribution(values: list[float], bins: int = 10) -> list[dict[str, Any]]:
        if not values:
            return []
        lo, hi = min(values), max(values)
        if lo == hi:
            return [{"range": f"{lo:.2f}–{hi:.2f}", "count": len(values), "frequency": 1.0}]
        width = (hi - lo) / bins
        counts = [0] * bins
        for v in values:
            idx = min(int((v - lo) / width), bins - 1)
            counts[idx] += 1
        total = len(values)
        return [
            {
                "range": f"{lo + i * width:.2f}–{lo + (i + 1) * width:.2f}",
                "count": counts[i],
                "frequency": round(counts[i] / total, 4),
            }
            for i in range(bins)
        ]

    @staticmethod
    def outliers(values: list[float], threshold: float = 2.0) -> list[float]:
        """Return values whose |z-score| > threshold."""
        zs = StatsEngine.z_scores(values)
        return [v for v, z in zip(values, zs) if abs(z) > threshold]

    @staticmethod
    def covariance(xs: list[float], ys: list[float], sample: bool = True) -> float:
        n = min(len(xs), len(ys))
        if n < 2:
            return 0.0
        mx, my = StatsEngine.mean(xs[:n]), StatsEngine.mean(ys[:n])
        denom = n - 1 if sample else n
        return sum((x - mx) * (y - my) for x, y in zip(xs[:n], ys[:n])) / denom

    @staticmethod
    def correlation(xs: list[float], ys: list[float]) -> float:
        sx = StatsEngine.std_dev(xs)
        sy = StatsEngine.std_dev(ys)
        if sx == 0 or sy == 0:
            return 0.0
        return StatsEngine.covariance(xs, ys) / (sx * sy)

    @staticmethod
    def cumulative_sum(values: list[float]) -> list[float]:
        total = 0.0
        result = []
        for v in values:
            total += v
            result.append(total)
        return result

    @staticmethod
    def rank(values: list[float], ascending: bool = False) -> list[int]:
        """Returns rank (1 = best) for each value. Ties share the same rank."""
        if not values:
            return []
        indexed = sorted(enumerate(values), key=lambda x: x[1], reverse=not ascending)
        ranks = [0] * len(values)
        r = 1
        for pos, (orig_idx, _) in enumerate(indexed):
            if pos > 0 and indexed[pos][1] == indexed[pos - 1][1]:
                ranks[orig_idx] = ranks[indexed[pos - 1][0]]
            else:
                ranks[orig_idx] = r
            r += 1
        return ranks

    @staticmethod
    def percentile_rank(value: float, population: list[float]) -> float:
        """Returns percentile rank (0–100) of `value` within `population`."""
        if not population:
            return 50.0
        below = sum(1 for v in population if v < value)
        at = sum(1 for v in population if v == value)
        return round((below + 0.5 * at) / len(population) * 100, 1)

    @staticmethod
    def time_series_aggregate(
        points: list[dict],
        period: str = "month",
        value_key: str = "value",
        date_key: str = "date",
    ) -> list[dict[str, Any]]:
        """Aggregate time-series dicts into period buckets.

        Returns list of {period, sum, mean, count, min, max} sorted ascending.
        period: 'day' | 'week' | 'month' | 'quarter' | 'year'
        """
        if not points:
            return []

        def _period_key(raw: Any) -> str:
            if isinstance(raw, datetime):
                dt = raw
            else:
                try:
                    dt = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
                except Exception:
                    return str(raw)[:7]
            if period == "day":
                return dt.strftime("%Y-%m-%d")
            elif period == "week":
                iso = dt.isocalendar()
                return f"{iso[0]}-W{iso[1]:02d}"
            elif period == "month":
                return dt.strftime("%Y-%m")
            elif period == "quarter":
                q = (dt.month - 1) // 3 + 1
                return f"{dt.year}-Q{q}"
            return str(dt.year)

        buckets: dict[str, list[float]] = {}
        for p in points:
            key = _period_key(p.get(date_key, ""))
            try:
                val = float(p.get(value_key, 0))
            except (TypeError, ValueError):
                val = 0.0
            buckets.setdefault(key, []).append(val)

        return [
            {
                "period": k,
                "sum": round(sum(vs), 4),
                "mean": round(sum(vs) / len(vs), 4),
                "count": len(vs),
                "min": min(vs),
                "max": max(vs),
            }
            for k, vs in sorted(buckets.items())
        ]

    @staticmethod
    def summary(values: list[float]) -> dict[str, Any]:
        """Full descriptive statistics summary."""
        if not values:
            return {
                "count": 0, "sum": 0, "mean": 0, "median": 0, "std_dev": 0,
                "variance": 0, "min": 0, "max": 0, "range": 0,
                "p25": 0, "p75": 0, "iqr": 0,
            }
        q = StatsEngine.quartiles(values)
        return {
            "count": len(values),
            "sum": round(sum(values), 4),
            "mean": round(StatsEngine.mean(values), 4),
            "median": round(StatsEngine.median(values), 4),
            "std_dev": round(StatsEngine.std_dev(values), 4),
            "variance": round(StatsEngine.variance(values), 4),
            "min": min(values),
            "max": max(values),
            "range": round(max(values) - min(values), 4),
            "p25": round(q["q1"], 4),
            "p75": round(q["q3"], 4),
            "iqr": round(q["iqr"], 4),
        }
