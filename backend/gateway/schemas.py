"""
Enterprise AI Gateway — Unified request / response schemas.

Every AI feature uses exactly these two objects.
GatewayRequest replaces ad-hoc (system, user_msg, feature) tuples.
GatewayResponse is the single structured output every caller receives.

Backward compat: call_llm() still exists and returns GatewayResponse.text.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


@dataclass
class GatewayRequest:
    """Normalized input to the Enterprise AI Gateway."""

    # ── Identity ──────────────────────────────────────────────────────────────
    request_id:   str = field(default_factory=lambda: str(uuid.uuid4()))
    feature:      str = "general"
    plugin_name:  Optional[str] = None   # registered plugin ID (overrides feature)
    prompt_id:    Optional[str] = None   # versioned prompt from PromptRegistry

    # ── Content ───────────────────────────────────────────────────────────────
    system:       str = ""
    user_message: str = ""
    messages:     Optional[list[dict]] = None  # multi-turn; if set, user_message ignored

    # ── User / session context ────────────────────────────────────────────────
    user_id:        Optional[str] = None
    mission_id:     Optional[str] = None   # ARA mission — enables used_credits tracking
    workspace_id:   Optional[str] = None
    institution_id: Optional[str] = None

    # ── Context loading flags (what ContextBuilder should load) ───────────────
    load_twin:        bool = False
    load_lkg:         bool = False
    load_workspace:   bool = False
    load_institution: bool = False
    load_recent_ai:   bool = False

    # ── Execution hints ───────────────────────────────────────────────────────
    provider:         Optional[str] = None
    model:            Optional[str] = None
    max_tokens:       int = 2048
    temperature:      Optional[float] = None
    stream:           bool = False
    require_evidence: bool = False
    cost_limit_credits: Optional[float] = None

    # ── Prompt variables (if prompt_id is set) ────────────────────────────────
    variables:    dict = field(default_factory=dict)

    # ── Passthrough metadata ──────────────────────────────────────────────────
    metadata:     dict = field(default_factory=dict)


@dataclass
class ValidationResult:
    passed:            bool = True
    confidence:        str = "low"       # high/medium/low/insufficient
    warnings:          list[str] = field(default_factory=list)
    evidence:          list[dict] = field(default_factory=list)
    citations:         list[str] = field(default_factory=list)
    fabrication_flags: list[str] = field(default_factory=list)
    status:            str = "not_run"   # not_run / passed / warned / failed


@dataclass
class GatewayResponse:
    """
    Unified output from the Enterprise AI Gateway.

    Every AI feature receives exactly this object.
    Backward compat: .text property returns response string directly.
    """

    # ── Core output ───────────────────────────────────────────────────────────
    request_id:        str = ""
    response:          str = ""
    reasoning_summary: str = ""

    # ── Evidence & quality ────────────────────────────────────────────────────
    confidence:        str = "low"   # high/medium/low/insufficient — never a percentage
    evidence:          list[dict] = field(default_factory=list)
    citations:         list[str] = field(default_factory=list)
    sources:           list[str] = field(default_factory=list)
    warnings:          list[str] = field(default_factory=list)

    # ── Validation ────────────────────────────────────────────────────────────
    validation:        ValidationResult = field(default_factory=ValidationResult)
    validation_status: str = "not_run"  # not_run / passed / warned / failed

    # ── Cost & execution ─────────────────────────────────────────────────────
    cost_credits:      float = 0.0
    cost_usd:          float = 0.0
    latency_ms:        int = 0
    provider:          str = ""
    model:             str = ""
    tokens_in:         int = 0
    tokens_out:        int = 0
    from_cache:        bool = False
    fallback_reason:   Optional[str] = None

    # ── Meta ─────────────────────────────────────────────────────────────────
    feature:           str = "general"
    plugin_name:       Optional[str] = None
    prompt_id:         Optional[str] = None
    timestamp:         str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def text(self) -> str:
        """Backward-compat accessor used by call_llm() callers."""
        return self.response

    def to_dict(self) -> dict:
        return {
            "request_id":        self.request_id,
            "response":          self.response,
            "reasoning_summary": self.reasoning_summary,
            "confidence":        self.confidence,
            "evidence":          self.evidence,
            "citations":         self.citations,
            "sources":           self.sources,
            "warnings":          self.warnings,
            "validation_status": self.validation_status,
            "cost_credits":      self.cost_credits,
            "latency_ms":        self.latency_ms,
            "provider":          self.provider,
            "model":             self.model,
            "tokens_in":         self.tokens_in,
            "tokens_out":        self.tokens_out,
            "from_cache":        self.from_cache,
            "feature":           self.feature,
            "timestamp":         self.timestamp,
        }
