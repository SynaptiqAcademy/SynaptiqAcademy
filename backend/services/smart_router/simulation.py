"""LoadSimulator — estimate cost, GPU, and latency at 100–100k concurrent users.

Used by the admin dashboard to answer: "What happens if we get N users?"
All calculations are probabilistic estimates based on observed profiles and
current provider cost rates.
"""
from __future__ import annotations

import random
import statistics
from dataclasses import dataclass, field

from services.smart_router.config import PROVIDER_COSTS, SmartRouterConfig
from services.smart_router.profiles import _PROFILES, get_profile
from services.smart_router.types import ComplexityLevel, SimulationResult

# Typical request rate: 1 request per user per N seconds (steady state)
_REQUESTS_PER_USER_PER_MINUTE = 0.5
# Layer routing probabilities for each complexity level
_LAYER_PROBABILITIES: dict[str, dict[str, float]] = {
    "VERY_LOW": {"rule": 0.95, "local": 0.04, "cloud": 0.01},
    "LOW":      {"rule": 0.30, "local": 0.55, "cloud": 0.15},
    "MEDIUM":   {"rule": 0.10, "local": 0.45, "cloud": 0.45},
    "HIGH":     {"rule": 0.00, "local": 0.20, "cloud": 0.80},
    "CRITICAL": {"rule": 0.00, "local": 0.05, "cloud": 0.95},
}
# Typical latency ranges per layer (ms)
_LATENCY_RANGES: dict[str, tuple[int, int]] = {
    "rule":  (5, 50),
    "local": (300, 2000),
    "cloud": (800, 5000),
}
# GPU utilization per local request (fractional GPU seconds per request)
_GPU_SECONDS_PER_LOCAL = 0.8


@dataclass
class FeatureSimResult:
    feature: str
    requests_per_min: float
    layer_split: dict[str, float]
    cost_per_min_usd: float


class LoadSimulator:
    """Simulates platform behaviour under varying load."""

    def __init__(self, config: SmartRouterConfig) -> None:
        self._config = config

    def simulate(self, concurrent_users: int, duration_minutes: int = 60) -> SimulationResult:
        """Run a Monte Carlo simulation for the given concurrency level."""
        rng = random.Random(concurrent_users)  # deterministic for same input

        total_requests_per_min = concurrent_users * _REQUESTS_PER_USER_PER_MINUTE
        total_requests = int(total_requests_per_min * duration_minutes)

        # Distribute requests across features by priority weight (inverse of priority_score)
        profiles = list(_PROFILES.values())
        weights = [101 - p.priority_score for p in profiles]
        total_weight = sum(weights)
        feature_probs = [w / total_weight for w in weights]

        rule_count = 0
        local_count = 0
        cloud_count = 0
        total_cost = 0.0
        total_gpu_s = 0.0
        latencies: list[float] = []

        for _ in range(min(total_requests, 10_000)):  # cap simulation depth
            profile = rng.choices(profiles, weights=feature_probs, k=1)[0]
            complexity = profile.base_complexity.name
            layer_probs = _LAYER_PROBABILITIES[complexity]

            # Respect profile flags
            adjusted = dict(layer_probs)
            if not profile.allow_rule_downgrade and not profile.allow_local_downgrade:
                adjusted["rule"] = 0
                adjusted["local"] = 0
                adjusted["cloud"] = 1.0
            elif not profile.allow_rule_downgrade:
                adjusted["rule"] = 0
                total_r = adjusted["local"] + adjusted["cloud"]
                if total_r > 0:
                    adjusted["local"] /= total_r
                    adjusted["cloud"] /= total_r

            r = rng.random()
            cumulative = 0.0
            layer = "cloud"
            for lyr, prob in adjusted.items():
                cumulative += prob
                if r < cumulative:
                    layer = lyr
                    break

            if layer == "rule":
                rule_count += 1
                cost = 0.0
            elif layer == "local":
                local_count += 1
                cost = 0.0
                total_gpu_s += _GPU_SECONDS_PER_LOCAL
            else:
                cloud_count += 1
                in_tok = profile.typical_context_tokens
                out_tok = profile.expected_output_tokens
                cost_cfg = PROVIDER_COSTS.get("anthropic")
                cost = cost_cfg.estimate(in_tok, out_tok) if cost_cfg else 0.0

            total_cost += cost
            lo, hi = _LATENCY_RANGES[layer]
            latencies.append(rng.uniform(lo, hi))

        # Scale from simulation sample to full duration
        scale = total_requests / max(len(latencies), 1)
        scaled_cost = total_cost * scale
        scaled_gpu_s = total_gpu_s * scale

        lat_sorted = sorted(latencies)
        n = len(lat_sorted)

        gpu_hours = scaled_gpu_s / 3600
        gpu_count_recommended = max(1, int(gpu_hours / duration_minutes * 60 / 0.5))
        all_cloud_cost = PROVIDER_COSTS["anthropic"].estimate(800, 400) if PROVIDER_COSTS.get("anthropic") else 0.0
        all_cloud_total = all_cloud_cost * total_requests
        savings = round(max(0.0, all_cloud_total - scaled_cost), 2)

        sample = max(len(latencies), 1)

        return SimulationResult(
            n_users=concurrent_users,
            duration_minutes=duration_minutes,
            estimated_requests=int(total_requests),
            layer_distribution={
                "rule": int(rule_count * scale),
                "local": int(local_count * scale),
                "cloud": int(cloud_count * scale),
            },
            estimated_cloud_cost_usd=round(scaled_cost, 2),
            estimated_savings_vs_cloud_usd=savings,
            estimated_gpu_hours=round(gpu_hours, 2),
            estimated_local_requests=int(local_count * scale),
            estimated_rule_requests=int(rule_count * scale),
            p50_latency_ms=round(lat_sorted[n // 2]) if lat_sorted else 0,
            p95_latency_ms=round(lat_sorted[int(n * 0.95)]) if lat_sorted else 0,
            p99_latency_ms=round(lat_sorted[int(n * 0.99)]) if lat_sorted else 0,
            recommended_gpu_count=max(1, gpu_count_recommended),
            recommended_local_model_replicas=max(1, gpu_count_recommended),
            cost_breakdown={
                "hourly_usd": round(scaled_cost / duration_minutes * 60, 2),
                "daily_usd": round(scaled_cost / duration_minutes * 1440, 2),
                "monthly_usd": round(scaled_cost / duration_minutes * 43200, 2),
            },
            warnings=self._build_warnings(concurrent_users, scaled_cost / duration_minutes * 1440),
        )

    def _build_warnings(self, concurrent_users: int, daily_cost: float) -> list[str]:
        warnings = []
        if concurrent_users >= 10_000:
            warnings.append("At 10k+ users, consider Atlas Vector Search for knowledge retrieval.")
        if concurrent_users >= 50_000:
            warnings.append("At 50k+ users, a dedicated GPU cluster is recommended for local AI.")
        if daily_cost > self._config.daily_budget_usd * 0.8:
            warnings.append(
                f"Estimated daily cost ${daily_cost:.2f} exceeds 80% of daily budget "
                f"${self._config.daily_budget_usd:.2f}."
            )
        return warnings

    def compare_scales(self, user_counts: list[int]) -> list[dict]:
        """Compare multiple concurrency levels."""
        results = []
        for n in user_counts:
            r = self.simulate(n)
            results.append({
                "concurrent_users": n,
                "requests_total": r.estimated_requests,
                "cost_per_day_usd": r.cost_breakdown.get("daily_usd", 0),
                "estimated_gpu_hours": r.estimated_gpu_hours,
                "p95_latency_ms": r.p95_latency_ms,
                "layer_distribution": r.layer_distribution,
                "warnings": r.warnings,
            })
        return results
