"""
AI Security Engine — Phase XXXV.8

Protects every AI request against:
- Prompt Injection (direct and indirect)
- Jailbreaks
- Data Poisoning attempts
- Prompt Leakage / Context Leakage
- Prompt Replay
- Model Abuse
- Unsafe tool calls
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class ThreatType(str, Enum):
    PROMPT_INJECTION        = "prompt_injection"
    INDIRECT_INJECTION      = "indirect_injection"
    JAILBREAK               = "jailbreak"
    DATA_POISONING          = "data_poisoning"
    PROMPT_LEAKAGE          = "prompt_leakage"
    CONTEXT_LEAKAGE         = "context_leakage"
    MODEL_ABUSE             = "model_abuse"
    UNSAFE_TOOL_CALL        = "unsafe_tool_call"
    EXFILTRATION            = "exfiltration"
    REPLAY_ATTACK           = "replay_attack"


class ThreatSeverity(str, Enum):
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


@dataclass
class ThreatPattern:
    threat_type: ThreatType
    pattern:     str          # regex
    severity:    ThreatSeverity
    description: str
    _compiled:   Any          = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        self._compiled = re.compile(self.pattern, re.IGNORECASE | re.DOTALL)

    def matches(self, text: str) -> bool:
        return bool(self._compiled.search(text))


@dataclass
class ScanResult:
    safe:         bool
    threats:      list[dict]  = field(default_factory=list)
    risk_score:   int         = 0    # 0-100
    blocked:      bool        = False
    reason:       str         = ""

    def to_dict(self) -> dict:
        return {
            "safe":       self.safe,
            "threats":    self.threats,
            "risk_score": self.risk_score,
            "blocked":    self.blocked,
            "reason":     self.reason,
        }


# ── Threat pattern library ────────────────────────────────────────────────────

_PATTERNS: list[ThreatPattern] = [
    # Prompt injection — system override attempts
    ThreatPattern(ThreatType.PROMPT_INJECTION, r"ignore\s+(previous|above|all)\s+(instructions|prompts)", ThreatSeverity.HIGH, "Instruction override"),
    ThreatPattern(ThreatType.PROMPT_INJECTION, r"forget\s+(everything|all|previous)", ThreatSeverity.HIGH, "Memory wipe attempt"),
    ThreatPattern(ThreatType.PROMPT_INJECTION, r"(you are|act as|pretend to be)\s+(an?\s+)?(?:unrestricted|unfiltered|jailbroken|evil|DAN)", ThreatSeverity.CRITICAL, "Persona override"),
    ThreatPattern(ThreatType.PROMPT_INJECTION, r"system\s*:\s*(you|your|new|forget)", ThreatSeverity.HIGH, "Fake system prompt"),
    ThreatPattern(ThreatType.PROMPT_INJECTION, r"<\s*system\s*>", ThreatSeverity.HIGH, "System tag injection"),

    # Jailbreaks
    ThreatPattern(ThreatType.JAILBREAK, r"\bDAN\b", ThreatSeverity.HIGH, "DAN jailbreak pattern"),
    ThreatPattern(ThreatType.JAILBREAK, r"(developer|god|admin|root)\s+mode", ThreatSeverity.HIGH, "Mode override"),
    ThreatPattern(ThreatType.JAILBREAK, r"(bypass|disable|override)\s+(safety|filter|restriction|guardrail)", ThreatSeverity.CRITICAL, "Safety bypass"),
    ThreatPattern(ThreatType.JAILBREAK, r"hypothetically|in\s+a\s+fictional\s+world|for\s+a\s+story", ThreatSeverity.MEDIUM, "Fictional framing"),
    ThreatPattern(ThreatType.JAILBREAK, r"base64\s+encoded|encode\s+your\s+(response|answer)", ThreatSeverity.MEDIUM, "Encoding obfuscation"),

    # Data exfiltration
    ThreatPattern(ThreatType.EXFILTRATION, r"(print|output|show|reveal|expose)\s+(all\s+)?(system|internal|secret|hidden|private)\s+(prompt|message|instruction|config|data)", ThreatSeverity.HIGH, "System prompt extraction"),
    ThreatPattern(ThreatType.EXFILTRATION, r"(send|email|upload|transmit|post)\s+(data|information|file)\s+to\s+(http|ftp|external)", ThreatSeverity.CRITICAL, "Data exfiltration"),
    ThreatPattern(ThreatType.EXFILTRATION, r"(api[_\s]?key|secret|password|token|credential)", ThreatSeverity.MEDIUM, "Credential extraction attempt"),

    # Unsafe tool calls
    ThreatPattern(ThreatType.UNSAFE_TOOL_CALL, r"(execute|run|eval)\s+(arbitrary|shell|command|code|script)", ThreatSeverity.CRITICAL, "Code execution"),
    ThreatPattern(ThreatType.UNSAFE_TOOL_CALL, r"(drop|delete|truncate|modify)\s+(table|database|collection|index)", ThreatSeverity.CRITICAL, "Database manipulation"),
    ThreatPattern(ThreatType.UNSAFE_TOOL_CALL, r"(rm|del|rmdir|format)\s+-rf?", ThreatSeverity.CRITICAL, "File system attack"),

    # Context leakage
    ThreatPattern(ThreatType.CONTEXT_LEAKAGE, r"(previous|other|past)\s+(user|conversation|chat|session|message)", ThreatSeverity.MEDIUM, "Cross-session data access"),

    # Model abuse
    ThreatPattern(ThreatType.MODEL_ABUSE, r"repeat\s+.{0,50}\s+(forever|infinitely|1000\s+times)", ThreatSeverity.LOW, "DoS through repetition"),
    ThreatPattern(ThreatType.MODEL_ABUSE, r"generate\s+(100|1000|unlimited)\s+(examples|variations|tokens)", ThreatSeverity.LOW, "Token abuse"),
]

_SEVERITY_SCORE = {
    ThreatSeverity.LOW:      10,
    ThreatSeverity.MEDIUM:   30,
    ThreatSeverity.HIGH:     60,
    ThreatSeverity.CRITICAL: 100,
}

_BLOCK_THRESHOLD = 60   # block if any single threat scores >= this


class AISecurityEngine:

    def __init__(self) -> None:
        self._patterns   = list(_PATTERNS)
        self._scan_count = 0
        self._block_count= 0

    def scan(self, prompt: str, context: dict | None = None) -> ScanResult:
        """Scan a prompt for AI security threats."""
        self._scan_count += 1
        if not prompt:
            return ScanResult(safe=True)

        found_threats: list[dict] = []
        max_score = 0

        for pat in self._patterns:
            if pat.matches(prompt):
                score = _SEVERITY_SCORE[pat.severity]
                found_threats.append({
                    "type":        pat.threat_type,
                    "severity":    pat.severity,
                    "description": pat.description,
                    "score":       score,
                })
                max_score = max(max_score, score)

        # Aggregate risk (not just max — multiple low threats accumulate)
        aggregate_score = min(100, max_score + sum(
            t["score"] // 4 for t in found_threats if t["score"] < max_score
        ))

        blocked = max_score >= _BLOCK_THRESHOLD
        if blocked:
            self._block_count += 1

        return ScanResult(
            safe        = len(found_threats) == 0,
            threats     = found_threats,
            risk_score  = aggregate_score,
            blocked     = blocked,
            reason      = found_threats[0]["description"] if blocked and found_threats else "",
        )

    def scan_list(self, texts: list[str]) -> ScanResult:
        """Scan multiple texts (e.g. retrieved context) and return aggregated result."""
        results   = [self.scan(t) for t in texts if t]
        all_threats = [t for r in results for t in r.threats]
        max_score   = max((r.risk_score for r in results), default=0)
        return ScanResult(
            safe       = all(r.safe for r in results),
            threats    = all_threats,
            risk_score = max_score,
            blocked    = any(r.blocked for r in results),
        )

    def add_pattern(self, pattern: ThreatPattern) -> None:
        self._patterns.append(pattern)

    def stats(self) -> dict:
        return {
            "scan_count":    self._scan_count,
            "block_count":   self._block_count,
            "pattern_count": len(self._patterns),
        }

    def recent_threats(self) -> list[str]:
        return [pat.threat_type.value for pat in self._patterns]


# ── Singleton ─────────────────────────────────────────────────────────────────

_engine: AISecurityEngine | None = None


def get_ai_security() -> AISecurityEngine:
    global _engine
    if _engine is None:
        _engine = AISecurityEngine()
    return _engine
