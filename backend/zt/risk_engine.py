"""
Risk Engine — Phase XXXV.8

Assigns a dynamic risk score (0-100) to every request.
High-risk requests require additional verification or trigger alerts.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from .identity import IdentityContext, IdentityType

logger = logging.getLogger(__name__)


class RiskLevel(str, Enum):
    LOW      = "low"       # 0-24
    MEDIUM   = "medium"    # 25-49
    HIGH     = "high"      # 50-74
    CRITICAL = "critical"  # 75-100


@dataclass
class RiskFactor:
    name:   str
    score:  int
    reason: str


@dataclass
class RiskScore:
    score:   int              # 0-100
    level:   RiskLevel
    factors: list[RiskFactor] = field(default_factory=list)

    @classmethod
    def from_score(cls, raw: int, factors: list[RiskFactor]) -> "RiskScore":
        clamped = max(0, min(100, raw))
        if clamped < 25:
            level = RiskLevel.LOW
        elif clamped < 50:
            level = RiskLevel.MEDIUM
        elif clamped < 75:
            level = RiskLevel.HIGH
        else:
            level = RiskLevel.CRITICAL
        return cls(score=clamped, level=level, factors=factors)

    def to_dict(self) -> dict:
        return {
            "score":   self.score,
            "level":   self.level,
            "factors": [{"name": f.name, "score": f.score, "reason": f.reason} for f in self.factors],
        }

    @property
    def requires_mfa(self) -> bool:
        return self.level in (RiskLevel.HIGH, RiskLevel.CRITICAL)

    @property
    def requires_review(self) -> bool:
        return self.level == RiskLevel.CRITICAL


class RiskEngine:
    """
    Evaluates risk of a request using multiple signals.
    Each factor contributes additive risk points (clamped to 100).
    """

    def __init__(self) -> None:
        self._score_history: list[dict] = []    # ring buffer of recent scores

    def score(
        self,
        identity:       IdentityContext,
        path:           str            = "",
        method:         str            = "GET",
        ip:             str            = "",
        user_agent:     str            = "",
        failed_auths:   int            = 0,
        new_device:     bool           = False,
        new_location:   bool           = False,
        off_hours:      bool           = False,
        sensitive_op:   bool           = False,
        data_class:     str            = "internal",
        additional:     dict | None    = None,
    ) -> RiskScore:
        factors: list[RiskFactor] = []
        total   = 0

        # Anonymous user always gets elevated risk
        if not identity.is_authenticated:
            factors.append(RiskFactor("unauthenticated", 40, "No authentication"))
            total += 40

        # Failed authentication attempts
        if failed_auths >= 5:
            factors.append(RiskFactor("multiple_failed_auths", 30, f"{failed_auths} failed attempts"))
            total += 30
        elif failed_auths >= 2:
            factors.append(RiskFactor("failed_auths", 15, f"{failed_auths} failed attempts"))
            total += 15

        # New/untrusted device
        if new_device and not identity.device_trusted:
            factors.append(RiskFactor("new_device", 20, "Unrecognized device"))
            total += 20

        # New location (impossible travel or unusual IP)
        if new_location:
            factors.append(RiskFactor("new_location", 25, "Unusual location"))
            total += 25

        # Off-hours access (e.g. 2-5am local time)
        if off_hours:
            factors.append(RiskFactor("off_hours", 10, "Access outside normal hours"))
            total += 10

        # Sensitive operation without MFA
        if sensitive_op and not identity.mfa_verified:
            factors.append(RiskFactor("sensitive_no_mfa", 25, "Sensitive operation without MFA"))
            total += 25

        # High-classification data access
        if data_class in ("restricted", "sensitive"):
            factors.append(RiskFactor("high_classification", 20, f"Accessing {data_class} data"))
            total += 20

        # High-privilege write operations
        if method in ("DELETE", "PATCH") and any(
            seg in path for seg in ("/admin", "/security", "/users/", "/keys/")
        ):
            factors.append(RiskFactor("privileged_mutation", 20, "High-privilege write"))
            total += 20

        # Demo accounts performing elevated operations
        if identity.is_demo and method not in ("GET", "HEAD"):
            factors.append(RiskFactor("demo_write", 15, "Demo account write operation"))
            total += 15

        # No MFA for admin operations
        if identity.identity_type in (IdentityType.INSTITUTION_ADMIN,) and not identity.mfa_verified:
            factors.append(RiskFactor("admin_no_mfa", 15, "Admin without MFA"))
            total += 15

        # Machine identities on human-facing endpoints
        if identity.is_machine and "/api/users/" in path:
            factors.append(RiskFactor("machine_user_access", 20, "Machine accessing user endpoint"))
            total += 20

        rs = RiskScore.from_score(total, factors)
        self._score_history.append({
            "score":      rs.score,
            "level":      rs.level,
            "subject_id": identity.subject_id,
            "path":       path,
            "ts":         datetime.now(timezone.utc).isoformat(),
        })
        if len(self._score_history) > 1000:
            self._score_history = self._score_history[-1000:]
        return rs

    def stats(self) -> dict:
        if not self._score_history:
            return {"count": 0}
        scores  = [h["score"] for h in self._score_history]
        levels  = [h["level"] for h in self._score_history]
        return {
            "count":          len(scores),
            "avg_score":      round(sum(scores) / len(scores), 1),
            "max_score":      max(scores),
            "critical_count": sum(1 for l in levels if l == RiskLevel.CRITICAL),
            "high_count":     sum(1 for l in levels if l == RiskLevel.HIGH),
        }

    def recent(self, limit: int = 50) -> list[dict]:
        return self._score_history[-limit:]


# ── Singleton ─────────────────────────────────────────────────────────────────

_engine: RiskEngine | None = None


def get_risk_engine() -> RiskEngine:
    global _engine
    if _engine is None:
        _engine = RiskEngine()
    return _engine
