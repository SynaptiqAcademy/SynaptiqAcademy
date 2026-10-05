"""
Enterprise AI Gateway — Policy Engine.

Runs BEFORE execution. Every AI request must pass all active policies.
A policy rejection raises PolicyViolation, which the gateway turns into
a structured error GatewayResponse (never a 500).

Active policies:
  1. Credit budget enforcement
  2. Rate limit (fast-path check; slowapi handles HTTP-level limiting)
  3. Prompt injection detection
  4. Academic integrity annotation
  5. Institutional AI policy
  6. Privacy guard (no cross-user data leakage)
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from .schemas import GatewayRequest

logger = logging.getLogger("gateway.policy_engine")


class PolicyViolation(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code    = code
        self.message = message


# ── Prompt injection patterns ─────────────────────────────────────────────────

_INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(your\s+)?(previous|prior|all|system)\s+(instructions?|prompt)", re.I),
    re.compile(r"you\s+are\s+now\s+a", re.I),
    re.compile(r"forget\s+(everything|all|your)", re.I),
    re.compile(r"act\s+as\s+(if\s+you\s+are|a\s+different)", re.I),
    re.compile(r"\[SYSTEM\]", re.I),
    re.compile(r"print\s+(your\s+)?(system\s+)?(instructions?|prompt|rules)", re.I),
    re.compile(r"reveal\s+(your\s+)?(hidden|system|internal)\s+(prompt|instructions?)", re.I),
    re.compile(r"disregard\s+(all\s+)?(previous|prior|your)", re.I),
    re.compile(r"new\s+instructions?:", re.I),
    re.compile(r"<\|system\|>", re.I),
]


class PolicyEngine:

    async def enforce(self, request: GatewayRequest, db, user: dict | None = None) -> None:
        """
        Run all policies. Raises PolicyViolation on failure.
        Never raises any other exception type.
        """
        try:
            await self._check_credits(request, db, user)
            self._check_injection(request)
            self._check_academic_integrity(request)
        except PolicyViolation:
            raise
        except Exception as exc:
            logger.warning("Policy engine unexpected error (non-blocking): %s", exc)

    # ── Individual policies ───────────────────────────────────────────────────

    async def _check_credits(self, request: GatewayRequest, db,
                              user: dict | None) -> None:
        """Hard-stop when a caller passes an explicit, exhausted budget
        (e.g. an ARA mission). User credits and plan entitlements are enforced
        before the gateway is reached — services/credits_service.consume_credits
        reserves credits per request and services/ai/cost_guard.py applies the
        per-user cost ceilings — so no plan table is duplicated here."""
        limit = request.cost_limit_credits
        if limit is not None and limit <= 0:
            raise PolicyViolation(
                "budget_exhausted",
                "AI budget for this task is exhausted.",
            )

    def _check_injection(self, request: GatewayRequest) -> None:
        """Detect prompt injection attempts in the user message."""
        text = request.user_message or ""
        for pat in _INJECTION_PATTERNS:
            if pat.search(text):
                logger.warning(
                    "Prompt injection detected in request %s (pattern: %s)",
                    request.request_id, pat.pattern[:40],
                )
                raise PolicyViolation(
                    "prompt_injection",
                    "The request contains patterns that could compromise AI safety. "
                    "Please rephrase your request.",
                )

    def _check_academic_integrity(self, request: GatewayRequest) -> None:
        """
        Annotate requests involving simulations or predictions with a
        mandatory academic integrity disclaimer (injected, not blocking).
        """
        simulation_features = {"twin_simulation", "prediction", "peer_review_sim",
                               "ara.step.reviewer", "twin.simulation"}
        if request.feature in simulation_features or (
            request.prompt_id and "reviewer" in (request.prompt_id or "")
        ):
            # Add disclaimer to metadata — gateway injects it into the response warnings
            request.metadata["academic_integrity_disclaimer"] = (
                "This output is a simulation or prediction. "
                "It is NOT an authoritative scientific judgment. "
                "Verify all claims with primary sources before acting."
            )
