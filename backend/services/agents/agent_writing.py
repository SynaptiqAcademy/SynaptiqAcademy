"""Academic Writing Agent (Phase XIII)."""
from __future__ import annotations

import re
import time

from .base_agent import AcademicAgent, AgentRegistry
from .models import AgentContext, AgentResult, AgentTask, AgentType

_PASSIVE_RE    = re.compile(r"\b(?:was|were|is|are|been|being)\s+\w+ed\b", re.IGNORECASE)
_HEDGE_RE      = re.compile(r"\b(?:perhaps|maybe|somewhat|seems to|appears to|might be|could be)\b", re.IGNORECASE)
_FIRST_PERSON  = re.compile(r"\b(?:I|we|our|my)\b", re.IGNORECASE)
_TRANSITION_RE = re.compile(
    r"\b(?:however|therefore|moreover|furthermore|in addition|consequently|thus|hence|"
    r"in contrast|on the other hand|in conclusion|finally|nevertheless)\b",
    re.IGNORECASE,
)
_SPELL_ERR_RE  = re.compile(
    r"\bteh\b|\brecieve\b|\boccured\b|\bseperate\b|\bdefinate\b|\bexistance\b", re.IGNORECASE
)
_SECTION_RE    = re.compile(
    r"\b(?:abstract|introduction|method|result|discussion|conclusion|limitation|reference)\b",
    re.IGNORECASE,
)
_LONG_SENT_RE  = re.compile(r"[^.!?]{200,}[.!?]")


@AgentRegistry.register
class AcademicWritingAgent(AcademicAgent):
    agent_id = "academic_writing_agent_v1"
    agent_type = AgentType.ACADEMIC_WRITING
    name = "Academic Writing Agent"
    domain = "Academic Writing Quality"
    capabilities = [
        "clarity_analysis", "tone_assessment", "grammar_check", "cohesion_analysis",
        "readability_scoring", "structure_review",
    ]

    async def execute(self, task: AgentTask, context: AgentContext) -> AgentResult:
        t0 = time.monotonic()
        text = task.content
        words = text.split()
        word_count = len(words)
        sentences = re.split(r"[.!?]+", text)
        sentence_count = max(1, len([s for s in sentences if s.strip()]))

        avg_sentence_length = word_count / sentence_count

        # Feature analysis
        passive_count = len(_PASSIVE_RE.findall(text))
        hedge_count = len(_HEDGE_RE.findall(text))
        first_person_count = len(_FIRST_PERSON.findall(text))
        transition_count = len(_TRANSITION_RE.findall(text))
        spell_errors = _SPELL_ERR_RE.findall(text)
        sections_present = len(set(_SECTION_RE.findall(text.lower())))
        long_sentences = _LONG_SENT_RE.findall(text)

        passive_rate = passive_count / max(sentence_count, 1)
        transition_rate = transition_count / max(sentence_count, 1)

        issues: list[str] = []
        if passive_rate > 0.4:
            issues.append(f"High passive voice rate ({passive_rate:.0%}) — reduce for clarity")
        if avg_sentence_length > 35:
            issues.append(f"Average sentence length is {avg_sentence_length:.0f} words — aim for <25")
        if hedge_count > 10:
            issues.append(f"{hedge_count} vague hedging expressions — use precise qualifications")
        if spell_errors:
            issues.append(f"Spelling errors detected: {set(spell_errors)}")
        if transition_rate < 0.1 and sentence_count > 10:
            issues.append("Low use of transitional phrases — improve cohesion with connectives")
        if sections_present < 3 and word_count > 1000:
            issues.append("Missing or unlabelled manuscript sections — use clear section headers")
        if long_sentences:
            issues.append(f"{len(long_sentences)} overly long sentence(s) — split for readability")

        # Flesch readability approximation
        avg_syllables = 1.5  # approximation for academic text
        flesch = max(0, min(100, 206.835 - 1.015 * avg_sentence_length - 84.6 * avg_syllables))

        # Confidence: high if few issues and good structure
        quality_score = 1 - min(1.0, len(issues) * 0.15)
        confidence = round(0.5 + 0.4 * quality_score, 3)

        output = {
            "word_count": word_count,
            "sentence_count": sentence_count,
            "avg_sentence_length": round(avg_sentence_length, 1),
            "passive_voice_rate": round(passive_rate, 3),
            "hedge_count": hedge_count,
            "first_person_count": first_person_count,
            "transition_count": transition_count,
            "transition_rate": round(transition_rate, 3),
            "sections_detected": sections_present,
            "spelling_errors": list(set(spell_errors)),
            "flesch_readability_approx": round(flesch, 1),
            "writing_issues": issues,
            "quality_score": round(quality_score, 3),
            "recommendations": [
                "Use active voice for stronger, clearer prose",
                "Keep sentences under 25 words on average",
                "Add transitional phrases to improve logical flow",
                "Eliminate vague hedges — replace with specific qualifications",
                "Run through Grammarly/ProWritingAid before submission",
            ],
        }

        return self._timed_result(
            task, output, confidence,
            reasoning=(
                f"Writing quality: {quality_score:.0%}. "
                f"Passive voice rate: {passive_rate:.0%}. "
                f"Avg sentence length: {avg_sentence_length:.1f} words. "
                f"{len(issues)} writing issues detected."
            ),
            evidence=issues[:5],
            t0=t0,
        )
