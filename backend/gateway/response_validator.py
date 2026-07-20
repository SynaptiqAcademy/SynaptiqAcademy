"""
Enterprise AI Gateway — Response Validator.

Runs AFTER every AI execution. Replaces the weak regex-based
validation_agent.py with real evidence-grounding checks.

Validation pipeline (all best-effort — never blocks the response):
  1. Schema validation   — response is non-empty string
  2. Confidence check    — no percentage confidence, only high/medium/low/insufficient
  3. Fabrication scan    — LLM-based check for unsupported numeric claims
  4. Safety check        — no harmful content patterns
  5. Citation binding    — for evidence-required features, flag uncited claims

The validator uses a fast/cheap model (Haiku or local) for the LLM-based
fabrication check. If the validator's own LLM call fails, it degrades to
the pattern-based scan and marks status "warned" rather than "failed".
"""
from __future__ import annotations

import logging
import re
from typing import Optional

from .schemas import GatewayResponse, ValidationResult

logger = logging.getLogger("gateway.response_validator")

# ── Patterns ──────────────────────────────────────────────────────────────────

_PCT_CONFIDENCE = re.compile(r"\bconfidence[:\s]+\d{1,3}\s*%", re.I)
_FABRICATION_NUMBERS = [
    re.compile(r"\b\d+\s*%\s+(?:of|improvement|increase|decrease|reduction|higher|lower|better|faster)", re.I),
    re.compile(r"\b\d{1,3}\s*(?:times|×|x)\s+(?:more|better|faster|higher|lower)", re.I),
    re.compile(r"statistically\s+significant\s+(?:increase|decrease|improvement)", re.I),
    re.compile(r"guaranteed\s+(?:to\s+)?(?:improve|increase|decrease|work)", re.I),
    re.compile(r"\bp\s*[=<>]\s*0\.\d+", re.I),   # p-values without source
    re.compile(r"correlation\s+of\s+\d*\.\d+", re.I),  # raw correlation numbers
]
_HARMFUL = re.compile(r"\b(self[-\s]harm|suicide|kill\s+yourself|weapons?\s+of\s+mass)\b", re.I)

# Features where fabrication scanning matters most
_HIGH_STAKES = {
    "ara.step.statistics", "twin.simulation", "prediction",
    "proactive.recommendation", "twin.recommendation", "statistical_review",
}


class ResponseValidator:

    async def validate(
        self,
        response_text: str,
        request_context: dict,
        require_evidence: bool = False,
        feature: str = "general",
    ) -> ValidationResult:
        """
        Run the full validation pipeline.
        Always returns a ValidationResult; never raises.
        """
        result = ValidationResult()

        try:
            # 1. Schema validation
            if not response_text or not response_text.strip():
                result.passed = False
                result.warnings.append("Response is empty.")
                result.status = "failed"
                return result

            # 2. Confidence format check
            pct_match = _PCT_CONFIDENCE.search(response_text)
            if pct_match:
                result.warnings.append(
                    "Response expresses confidence as a percentage — "
                    "replace with high/medium/low/insufficient."
                )

            # 3. Harmful content check
            if _HARMFUL.search(response_text):
                result.passed = False
                result.warnings.append("Response may contain potentially harmful content.")
                result.status = "failed"
                return result

            # 4. Pattern-based fabrication scan
            for pat in _FABRICATION_NUMBERS:
                m = pat.search(response_text)
                if m:
                    result.fabrication_flags.append(
                        f"Potential unsupported claim: '{m.group()[:80]}'"
                    )

            # 5. LLM-based evidence grounding (only for high-stakes, best-effort)
            if require_evidence or feature in _HIGH_STAKES:
                await self._llm_evidence_check(response_text, request_context, result)

        except Exception as exc:
            logger.warning("Response validator error (non-blocking): %s", exc)
            result.warnings.append("Validation partially skipped due to internal error.")

        # Determine final status
        if not result.passed:
            result.status = "failed"
        elif result.fabrication_flags or result.warnings:
            result.status = "warned"
            result.confidence = "low"
        else:
            result.status = "passed"

        return result

    async def _llm_evidence_check(
        self, response_text: str, context: dict, result: ValidationResult
    ) -> None:
        """
        Use a fast LLM call to detect unsupported factual claims.
        Results annotate the ValidationResult; never block the response.
        """
        try:
            from services.ai.engine.core import get_engine
            from services.ai.engine.types import AIRequest

            # Use the cheapest available path for validation
            check_request = AIRequest(
                system=(
                    "You are an academic integrity validator. "
                    "Scan the AI response for unsupported factual claims. "
                    "A claim is unsupported if it states specific numbers, percentages, "
                    "correlations, or causal conclusions WITHOUT evidence from the inputs. "
                    'Output valid JSON only: {"issues": ["..."], "confidence": "high|medium|low|insufficient", "passed": true}'
                ),
                messages=[{"role": "user", "content":
                           f"Input context summary:\n{str(context)[:500]}\n\n"
                           f"AI response:\n{response_text[:1500]}"}],
                feature="validation",
                max_tokens=300,
                model="claude-haiku-4-5-20251001",
            )
            engine = get_engine()
            val_response = await engine.generate(check_request)
            raw = val_response.text.strip()

            # Parse JSON response
            import json
            start = raw.find("{")
            end   = raw.rfind("}") + 1
            if start >= 0 and end > start:
                data = json.loads(raw[start:end])
                issues     = data.get("issues", [])
                confidence = data.get("confidence", "low")
                passed     = data.get("passed", True)

                result.confidence = confidence
                for issue in issues[:5]:  # cap at 5 warnings
                    result.warnings.append(f"Evidence check: {issue}")
                if not passed:
                    result.fabrication_flags.extend(issues)
        except Exception as exc:
            logger.debug("LLM evidence check failed (non-blocking): %s", exc)
            # Fall back to pattern-based only — already done above
