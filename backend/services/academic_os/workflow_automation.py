"""Workflow Automation — rule-based automation triggered by platform events."""
from __future__ import annotations

import threading
import time

from .models import AutomationRule, TriggerType

_MAX_RULES = 500


class WorkflowAutomation:
    def __init__(self):
        self._lock  = threading.Lock()
        self._rules: dict[str, AutomationRule] = {}

    # ── Rule management ───────────────────────────────────────────────────────

    def create_rule(
        self,
        name:              str,
        trigger_type:      str,
        trigger_condition: dict,
        actions:           list,
    ) -> AutomationRule:
        rule = AutomationRule(
            name=name,
            trigger_type=trigger_type,
            trigger_condition=trigger_condition,
            actions=actions,
        )
        with self._lock:
            self._rules[rule.rule_id] = rule
            if len(self._rules) > _MAX_RULES:
                oldest = next(iter(self._rules))
                del self._rules[oldest]
        return rule

    def get_rule(self, rule_id: str) -> AutomationRule | None:
        with self._lock:
            return self._rules.get(rule_id)

    def list_rules(self, enabled_only: bool = False) -> list[AutomationRule]:
        with self._lock:
            rules = list(self._rules.values())
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        return rules

    def toggle_rule(self, rule_id: str, enabled: bool) -> bool:
        with self._lock:
            rule = self._rules.get(rule_id)
            if not rule:
                return False
            rule.enabled = enabled
        return True

    def delete_rule(self, rule_id: str) -> bool:
        with self._lock:
            if rule_id not in self._rules:
                return False
            del self._rules[rule_id]
        return True

    # ── Event evaluation ──────────────────────────────────────────────────────

    def evaluate_event(
        self,
        event_type: str,
        payload:    dict,
    ) -> list[dict]:
        """Evaluate all enabled rules against an incoming event. Returns triggered actions."""
        with self._lock:
            rules = [r for r in self._rules.values() if r.enabled]

        triggered: list[dict] = []
        for rule in rules:
            if self._matches(rule, event_type, payload):
                with self._lock:
                    rule.last_triggered = time.time()
                    rule.trigger_count  += 1
                triggered.append({
                    "rule_id":   rule.rule_id,
                    "rule_name": rule.name,
                    "actions":   list(rule.actions),
                    "triggered_at": rule.last_triggered,
                })
        return triggered

    @staticmethod
    def _matches(rule: AutomationRule, event_type: str, payload: dict) -> bool:
        if rule.trigger_type != event_type:
            return False
        cond = rule.trigger_condition
        # Threshold check (e.g. manuscript_quality >= 0.90)
        if "threshold_key" in cond and "threshold_value" in cond:
            actual = payload.get(cond["threshold_key"], 0)
            op     = cond.get("operator", "gte")
            tval   = cond["threshold_value"]
            if op == "gte"  and not (actual >= tval): return False
            if op == "gt"   and not (actual >  tval): return False
            if op == "lte"  and not (actual <= tval): return False
            if op == "lt"   and not (actual <  tval): return False
            if op == "eq"   and not (actual == tval): return False
        # Match key equals value
        if "match_key" in cond and "match_value" in cond:
            if payload.get(cond["match_key"]) != cond["match_value"]:
                return False
        return True

    # ── Pre-built templates ───────────────────────────────────────────────────

    def install_default_rules(self) -> list[AutomationRule]:
        defaults = [
            {
                "name": "Auto Journal Recommendation at 90% Quality",
                "trigger_type": TriggerType.MANUSCRIPT_QUALITY.value,
                "trigger_condition": {"threshold_key": "quality_score", "threshold_value": 0.90, "operator": "gte"},
                "actions": [
                    {"action": "run_statistical_review"},
                    {"action": "run_manuscript_review"},
                    {"action": "recommend_journals"},
                    {"action": "notify", "message": "Manuscript ready for journal submission"},
                ],
            },
            {
                "name": "Grant Deadline Notification (30 days)",
                "trigger_type": TriggerType.DEADLINE_APPROACHING.value,
                "trigger_condition": {"threshold_key": "days_remaining", "threshold_value": 30, "operator": "lte"},
                "actions": [
                    {"action": "notify", "message": "Grant deadline approaching in 30 days"},
                    {"action": "check_grant_readiness"},
                ],
            },
            {
                "name": "Career Update After Publication",
                "trigger_type": TriggerType.ENTITY_CREATED.value,
                "trigger_condition": {"match_key": "entity_type", "match_value": "publication"},
                "actions": [
                    {"action": "update_career_metrics"},
                    {"action": "update_research_impact"},
                    {"action": "start_citation_monitoring"},
                ],
            },
        ]
        created = []
        for d in defaults:
            rule = self.create_rule(
                name=d["name"],
                trigger_type=d["trigger_type"],
                trigger_condition=d["trigger_condition"],
                actions=d["actions"],
            )
            created.append(rule)
        return created

    def stats(self) -> dict:
        with self._lock:
            total   = len(self._rules)
            enabled = sum(1 for r in self._rules.values() if r.enabled)
            fired   = sum(r.trigger_count for r in self._rules.values())
        return {"total": total, "enabled": enabled, "total_fired": fired}
