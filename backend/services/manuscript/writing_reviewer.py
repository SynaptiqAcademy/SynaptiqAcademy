"""Rule-based writing quality reviewer — Phase IX.

Analyses text for grammar signals, clarity, sentence complexity,
passive voice, academic vocabulary, transitions, readability.
Returns WritingMetrics + QualityDimension + ReviewIssues.
"""
from __future__ import annotations

import re
from collections import Counter

from .models import (
    WritingMetrics, QualityDimension, ReviewIssue,
    IssueSeverity, _score_to_grade,
)

# ── Word lists ────────────────────────────────────────────────────────────────

_ACADEMIC_WORDS = {
    "analyse", "analysis", "approach", "assess", "assume", "assumption",
    "category", "conceptual", "constitute", "context", "contrast", "contribute",
    "contribution", "demonstrate", "derive", "determine", "dimension", "distribute",
    "empirical", "establish", "evaluate", "evidence", "evident", "examine",
    "examine", "factors?", "framework", "function", "identify", "impact",
    "implement", "indicate", "individual", "interpret", "investigate", "involve",
    "issue", "justify", "mechanism", "method", "methodology", "obtain",
    "occur", "parameter", "perceive", "positive", "potential", "previous",
    "primary", "principle", "process", "propose", "publish", "range",
    "require", "research", "respond", "role", "significant", "similar",
    "source", "specific", "structure", "theory", "validity", "variable",
}

_PASSIVE_PATTERNS = re.compile(
    r"\b(?:is|are|was|were|be|been|being)\s+\w+ed\b",
    re.IGNORECASE,
)
_TRANSITION_WORDS = {
    "however", "therefore", "furthermore", "moreover", "consequently",
    "in addition", "additionally", "nevertheless", "nonetheless", "thus",
    "in contrast", "on the other hand", "as a result", "for example",
    "for instance", "in particular", "specifically", "notably", "finally",
    "subsequently", "previously", "first", "second", "third", "lastly",
    "in summary", "in conclusion", "in short", "to summarise", "to conclude",
    "importantly", "significantly",
}
_HEDGE_WORDS = {
    "might", "may", "could", "seem", "appear", "suggest", "indicate",
    "likely", "probably", "possibly", "perhaps", "approximately",
}
_NOMINALISATIONS = re.compile(
    r"\b\w+(?:tion|sion|ment|ance|ence|ity|ness|ism)\b",
    re.IGNORECASE,
)
_SENTENCE_SPLITTER = re.compile(r"(?<=[.!?])\s+")
_PARAGRAPH_SPLITTER = re.compile(r"\n{2,}")
_FILLER = re.compile(
    r"\b(?:very|really|quite|rather|somewhat|basically|essentially|"
    r"literally|actually|obviously|clearly|certainly|definitely)\b",
    re.IGNORECASE,
)


# ── Analysis ──────────────────────────────────────────────────────────────────

def review_writing_quality(text: str) -> tuple[WritingMetrics, QualityDimension, list[ReviewIssue]]:
    words = text.split()
    word_count = len(words)
    sentences = [s.strip() for s in _SENTENCE_SPLITTER.split(text) if s.strip()]
    sentence_count = len(sentences)
    paragraphs = [p.strip() for p in _PARAGRAPH_SPLITTER.split(text) if p.strip()]

    if word_count == 0:
        empty_dim = QualityDimension("Clarity & Writing Quality", score=0.0, weight=1.0, grade="F")
        return WritingMetrics(), empty_dim, []

    avg_sentence_length = word_count / max(sentence_count, 1)
    long_sentences = [s for s in sentences if len(s.split()) > 40]
    long_ratio = len(long_sentences) / max(sentence_count, 1)

    # Passive voice
    passive_count = len(_PASSIVE_PATTERNS.findall(text))
    passive_ratio = passive_count / max(sentence_count, 1)

    # Academic word ratio
    words_lower = [w.lower().strip(".,!?;:\"'()[]") for w in words]
    academic_count = sum(1 for w in words_lower if w in _ACADEMIC_WORDS)
    academic_ratio = academic_count / max(word_count, 1)

    # Transition density
    text_lower = text.lower()
    trans_count = sum(1 for t in _TRANSITION_WORDS if t in text_lower)
    trans_density = trans_count / max(sentence_count / 5, 1)  # per 5 sentences

    # Filler words
    filler_count = len(_FILLER.findall(text))
    filler_ratio = filler_count / max(word_count, 1)

    # Nominalisations
    nom_count = len(_NOMINALISATIONS.findall(text))
    nom_ratio = nom_count / max(word_count, 1)

    # Flesch reading ease approximation
    syllable_count = _estimate_syllables(text)
    if sentence_count > 0 and word_count > 0:
        asl = word_count / sentence_count
        asw = syllable_count / word_count
        readability = max(0.0, min(100.0, 206.835 - 1.015 * asl - 84.6 * asw))
    else:
        readability = 50.0

    avg_para_length = word_count / max(len(paragraphs), 1)

    metrics = WritingMetrics(
        word_count=word_count,
        sentence_count=sentence_count,
        avg_sentence_length=round(avg_sentence_length, 1),
        long_sentence_ratio=round(long_ratio, 3),
        passive_voice_ratio=round(passive_ratio, 3),
        academic_word_ratio=round(academic_ratio, 3),
        transition_density=round(min(trans_density, 5.0), 3),
        readability_score=round(readability, 1),
        paragraph_count=len(paragraphs),
        avg_paragraph_length=round(avg_para_length, 1),
    )

    issues: list[ReviewIssue] = []
    score_components: list[float] = []
    strengths: list[str] = []
    weaknesses: list[str] = []

    # ── Score rules ────────────────────────────────────────────────────────────

    # 1. Sentence length
    if avg_sentence_length <= 22:
        score_components.append(90.0)
        strengths.append("Sentence length is concise and reader-friendly")
    elif avg_sentence_length <= 30:
        score_components.append(75.0)
    else:
        score_components.append(50.0)
        weaknesses.append("Overly long sentences reduce readability")
        issues.append(ReviewIssue(
            severity=IssueSeverity.MINOR,
            section="Writing Quality",
            title="Sentence length exceeds recommended limit",
            description=(
                f"Average sentence length is {avg_sentence_length:.0f} words "
                f"({long_ratio:.0%} of sentences exceed 40 words). "
                "Academic writing should aim for 18–22 words per sentence."
            ),
            recommendation=(
                "Split long sentences at conjunctions or semicolons. "
                "Use short sentences to introduce key points."
            ),
        ))

    # 2. Passive voice
    if passive_ratio < 0.20:
        score_components.append(85.0)
        strengths.append("Appropriate balance of active and passive voice")
    elif passive_ratio < 0.40:
        score_components.append(70.0)
    else:
        score_components.append(50.0)
        weaknesses.append("Excessive passive voice construction")
        issues.append(ReviewIssue(
            severity=IssueSeverity.MINOR,
            section="Writing Quality",
            title="Overuse of passive voice",
            description=(
                f"Approximately {passive_ratio:.0%} of sentences use passive construction. "
                "Excessive passive voice reduces clarity and agency."
            ),
            recommendation=(
                "Convert passive constructions to active voice where the agent is known. "
                "Retain passive voice for methods sections where it is appropriate."
            ),
        ))

    # 3. Academic vocabulary
    if academic_ratio >= 0.08:
        score_components.append(85.0)
        strengths.append("Strong academic vocabulary")
    elif academic_ratio >= 0.05:
        score_components.append(70.0)
    else:
        score_components.append(55.0)
        weaknesses.append("Limited academic vocabulary")
        issues.append(ReviewIssue(
            severity=IssueSeverity.MINOR,
            section="Writing Quality",
            title="Insufficient academic vocabulary",
            description=(
                "The manuscript has limited academic vocabulary density "
                f"({academic_ratio:.1%}), which may affect publication in academic journals."
            ),
            recommendation=(
                "Incorporate more discipline-specific academic vocabulary. "
                "Review the Academic Word List (AWL) for appropriate substitutions."
            ),
        ))

    # 4. Transitions
    if trans_density >= 1.5:
        score_components.append(85.0)
        strengths.append("Good use of logical transitions between ideas")
    elif trans_density >= 0.8:
        score_components.append(70.0)
    else:
        score_components.append(55.0)
        weaknesses.append("Insufficient logical transitions")
        issues.append(ReviewIssue(
            severity=IssueSeverity.SUGGESTION,
            section="Writing Quality",
            title="Insufficient use of transition words",
            description=(
                "The manuscript lacks transition words that signal logical flow "
                "between sentences and paragraphs."
            ),
            recommendation=(
                "Add transition words to signal contrast (however, nevertheless), "
                "addition (furthermore, moreover), and consequence (therefore, thus)."
            ),
        ))

    # 5. Readability
    if 30 <= readability <= 65:
        score_components.append(90.0)
        strengths.append("Appropriate academic readability level")
    elif readability > 65:
        score_components.append(60.0)
        issues.append(ReviewIssue(
            severity=IssueSeverity.SUGGESTION,
            section="Writing Quality",
            title="Readability score too high for academic journal",
            description=(
                f"Readability score ({readability:.0f}) suggests the text may be too "
                "accessible for a peer-reviewed academic journal. Increase technical depth."
            ),
            recommendation=(
                "Use more precise, discipline-specific terminology and "
                "reduce overly simplified explanations."
            ),
        ))
    else:
        score_components.append(65.0)

    # 6. Filler words
    if filler_ratio < 0.005:
        score_components.append(85.0)
    elif filler_ratio < 0.015:
        score_components.append(70.0)
    else:
        score_components.append(55.0)
        weaknesses.append("Excessive filler words detected")
        issues.append(ReviewIssue(
            severity=IssueSeverity.SUGGESTION,
            section="Writing Quality",
            title="Filler and intensifier words reduce precision",
            description=(
                f"{filler_count} filler/intensifier words found (e.g., 'very', 'basically', "
                "'essentially'). These weaken academic writing."
            ),
            recommendation=(
                "Remove intensifiers (very, really, quite) and replace with precise "
                "quantitative statements where possible."
            ),
        ))

    # 7. Long sentence ratio
    if long_ratio > 0.40:
        score_components.append(50.0)
        issues.append(ReviewIssue(
            severity=IssueSeverity.MINOR,
            section="Writing Quality",
            title="High proportion of long sentences",
            description=(
                f"{long_ratio:.0%} of sentences exceed 40 words. "
                "Complex sentences impede reviewer comprehension."
            ),
            recommendation=(
                "Review each sentence exceeding 40 words and restructure. "
                "Use numbered lists for multi-part statements."
            ),
        ))
    else:
        score_components.append(80.0)

    overall = sum(score_components) / len(score_components) if score_components else 60.0

    dim = QualityDimension(
        name="Clarity & Writing Quality",
        score=round(overall, 1),
        weight=1.0,
        grade=_score_to_grade(overall),
        rationale=(
            f"Writing analysis: avg sentence {avg_sentence_length:.0f} words, "
            f"passive {passive_ratio:.0%}, readability {readability:.0f}. "
            f"{len(strengths)} strengths, {len(weaknesses)} concerns."
        ),
        strengths=strengths[:5],
        weaknesses=weaknesses[:5],
    )
    return metrics, dim, issues


def _estimate_syllables(text: str) -> int:
    """Fast syllable count approximation (no NLTK dependency)."""
    words = re.findall(r"[a-zA-Z]+", text)
    total = 0
    for word in words:
        word = word.lower()
        # Count vowel groups as syllable approximation
        count = len(re.findall(r"[aeiou]+", word))
        # Remove silent e at end
        if word.endswith("e") and count > 1:
            count -= 1
        total += max(1, count)
    return total
