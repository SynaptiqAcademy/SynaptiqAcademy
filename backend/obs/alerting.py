"""
Alerting Engine — Phase XXXV.6

Evaluates metric thresholds and platform events against a set of built-in
alert rules. Generated alerts are stored in `obs_alerts` and can be
acknowledged via the Operations Center.

Built-in rules cover:
  - Provider failures (circuit breaker opens)
  - Mission failures
  - Queue depth growth
  - Worker crashes
  - High API/DB latency
  - AI cost anomalies
  - Security events
  - Validation failures

Usage:
    engine = AlertEngine(db, metrics)
    alerts = await engine.evaluate()
    await engine.acknowledge(alert_id, acknowledged_by="admin")
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from .metrics import MetricStore, get_metrics

logger = logging.getLogger(__name__)

_COL = "obs_alerts"


# ── Data types ────────────────────────────────────────────────────────────────

@dataclass
class AlertRule:
    rule_id:    str
    name:       str
    description: str
    severity:   str          # info | warning | critical
    category:   str          # provider | mission | worker | latency | cost | security | queue
    condition:  Callable[[MetricStore], bool]
    message_fn: Callable[[MetricStore], str]
    cooldown_s: int = 300    # Don't re-alert within this window


@dataclass
class Alert:
    alert_id:        str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    rule_id:         str = ""
    name:            str = ""
    description:     str = ""
    severity:        str = "info"
    category:        str = "general"
    message:         str = ""
    status:          str = "active"    # active | acknowledged | resolved
    created_at:      str = field(default_factory=lambda: datetime.utcnow().isoformat())
    acknowledged_at: str | None = None
    acknowledged_by: str | None = None
    resolved_at:     str | None = None
    details:         dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if v is not None}


# ── Built-in alert rules ──────────────────────────────────────────────────────

def _build_builtin_rules() -> list[AlertRule]:
    return [
        AlertRule(
            rule_id="provider.failure",
            name="LLM Provider Failure",
            description="One or more LLM provider circuit breakers are open",
            severity="critical",
            category="provider",
            condition=lambda m: m.get_counter("ai.errors") > 0,
            message_fn=lambda m: f"AI errors detected: {m.get_counter('ai.errors'):.0f} total",
        ),
        AlertRule(
            rule_id="mission.failure_rate",
            name="Mission Failure Rate",
            description="Mission failure count has increased",
            severity="warning",
            category="mission",
            condition=lambda m: m.get_counter("mission.failed") > 0,
            message_fn=lambda m: f"Missions failed: {m.get_counter('mission.failed'):.0f}",
        ),
        AlertRule(
            rule_id="worker.queue_depth",
            name="Worker Queue Depth High",
            description="Job queue depth exceeds normal operating levels",
            severity="warning",
            category="queue",
            condition=lambda m: m.get_gauge("worker.queue_depth") > 500,
            message_fn=lambda m: f"Queue depth: {m.get_gauge('worker.queue_depth'):.0f} jobs",
        ),
        AlertRule(
            rule_id="worker.failures",
            name="Worker Job Failures",
            description="Worker job failure count is non-zero",
            severity="warning",
            category="worker",
            condition=lambda m: m.get_counter("worker.jobs.failed") > 0,
            message_fn=lambda m: f"Worker failures: {m.get_counter('worker.jobs.failed'):.0f}",
        ),
        AlertRule(
            rule_id="worker.dlq",
            name="Dead Letter Queue Growing",
            description="Jobs are accumulating in the dead letter queue",
            severity="warning",
            category="worker",
            condition=lambda m: m.get_counter("worker.jobs.dlq") > 10,
            message_fn=lambda m: f"DLQ entries: {m.get_counter('worker.jobs.dlq'):.0f}",
        ),
        AlertRule(
            rule_id="api.high_latency",
            name="API High Latency",
            description="API P95 latency exceeds 2000ms",
            severity="warning",
            category="latency",
            condition=lambda m: m.get_histogram("api.latency_ms").get("p95", 0) > 2000,
            message_fn=lambda m: f"API P95 latency: {m.get_histogram('api.latency_ms').get('p95', 0):.0f}ms",
        ),
        AlertRule(
            rule_id="ai.high_cost",
            name="AI Cost Spike",
            description="AI cost has exceeded expected threshold",
            severity="warning",
            category="cost",
            condition=lambda m: m.get_counter("ai.cost_usd") > 50.0,
            message_fn=lambda m: f"AI cost total: ${m.get_counter('ai.cost_usd'):.2f}",
        ),
        AlertRule(
            rule_id="security.violations",
            name="Security Violations Detected",
            description="Permission violations or suspicious activity detected",
            severity="critical",
            category="security",
            condition=lambda m: m.get_counter("security.violations") > 0,
            message_fn=lambda m: f"Security violations: {m.get_counter('security.violations'):.0f}",
        ),
        AlertRule(
            rule_id="security.injection",
            name="Prompt Injection Attempts",
            description="Potential prompt injection attempts detected",
            severity="critical",
            category="security",
            condition=lambda m: m.get_counter("security.injection_attempts") > 0,
            message_fn=lambda m: f"Injection attempts: {m.get_counter('security.injection_attempts'):.0f}",
        ),
        AlertRule(
            rule_id="db.high_latency",
            name="Database High Latency",
            description="MongoDB P95 latency exceeds 500ms",
            severity="warning",
            category="latency",
            condition=lambda m: m.get_histogram("db.latency_ms").get("p95", 0) > 500,
            message_fn=lambda m: f"DB P95 latency: {m.get_histogram('db.latency_ms').get('p95', 0):.0f}ms",
        ),
        AlertRule(
            rule_id="bus.dlq_growth",
            name="Event Bus DLQ Growing",
            description="Event bus dead letter queue is accumulating",
            severity="warning",
            category="queue",
            condition=lambda m: m.get_counter("bus.dlq") > 20,
            message_fn=lambda m: f"Bus DLQ: {m.get_counter('bus.dlq'):.0f} events",
        ),
        AlertRule(
            rule_id="ai.high_latency",
            name="AI Gateway High Latency",
            description="AI P95 latency exceeds 10 seconds",
            severity="warning",
            category="latency",
            condition=lambda m: m.get_histogram("ai.latency_ms").get("p95", 0) > 10_000,
            message_fn=lambda m: f"AI P95 latency: {m.get_histogram('ai.latency_ms').get('p95', 0):.0f}ms",
        ),
    ]


# ── Alert Engine ──────────────────────────────────────────────────────────────

class AlertEngine:

    def __init__(self, db: Any, metrics: MetricStore | None = None) -> None:
        self._db      = db
        self._metrics = metrics or get_metrics()
        self._rules   = _build_builtin_rules()
        self._last_fired: dict[str, str] = {}   # rule_id → ISO timestamp

    def add_rule(self, rule: AlertRule) -> None:
        self._rules.append(rule)

    async def evaluate(self) -> list[Alert]:
        """Evaluate all rules; persist and return newly fired alerts."""
        now     = datetime.utcnow()
        alerts: list[Alert] = []
        for rule in self._rules:
            try:
                if not rule.condition(self._metrics):
                    continue
                # Cooldown: skip if fired recently
                last = self._last_fired.get(rule.rule_id)
                if last:
                    from datetime import timedelta
                    elapsed = (now - datetime.fromisoformat(last)).total_seconds()
                    if elapsed < rule.cooldown_s:
                        continue
                alert = Alert(
                    rule_id     = rule.rule_id,
                    name        = rule.name,
                    description = rule.description,
                    severity    = rule.severity,
                    category    = rule.category,
                    message     = rule.message_fn(self._metrics),
                )
                alerts.append(alert)
                self._last_fired[rule.rule_id] = now.isoformat()
                try:
                    await self._db[_COL].insert_one(alert.to_dict())
                except Exception as exc:
                    logger.debug("Alert persist error: %s", exc)
            except Exception as exc:
                logger.debug("Alert rule %s eval error: %s", rule.rule_id, exc)
        return alerts

    async def list_alerts(
        self,
        status:   str | None = None,
        severity: str | None = None,
        category: str | None = None,
        limit:    int = 50,
    ) -> list[dict]:
        try:
            filt: dict = {}
            if status:   filt["status"]   = status
            if severity: filt["severity"] = severity
            if category: filt["category"] = category
            return await self._db[_COL].find(
                filt, {"_id": 0}
            ).sort("created_at", -1).limit(limit).to_list(limit)
        except Exception:
            return []

    async def acknowledge(self, alert_id: str, acknowledged_by: str = "admin") -> bool:
        try:
            r = await self._db[_COL].update_one(
                {"alert_id": alert_id, "status": "active"},
                {"$set": {
                    "status":           "acknowledged",
                    "acknowledged_at":  datetime.utcnow().isoformat(),
                    "acknowledged_by":  acknowledged_by,
                }},
            )
            return r.modified_count > 0
        except Exception:
            return False

    async def resolve(self, alert_id: str) -> bool:
        try:
            r = await self._db[_COL].update_one(
                {"alert_id": alert_id},
                {"$set": {
                    "status":      "resolved",
                    "resolved_at": datetime.utcnow().isoformat(),
                }},
            )
            return r.modified_count > 0
        except Exception:
            return False

    async def active_count(self) -> int:
        try:
            return await self._db[_COL].count_documents({"status": "active"})
        except Exception:
            return 0


# ── Singleton ─────────────────────────────────────────────────────────────────

_engine: AlertEngine | None = None


def init_alerting(db: Any, metrics: MetricStore | None = None) -> AlertEngine:
    global _engine
    _engine = AlertEngine(db, metrics)
    return _engine


def get_alert_engine() -> AlertEngine | None:
    return _engine
