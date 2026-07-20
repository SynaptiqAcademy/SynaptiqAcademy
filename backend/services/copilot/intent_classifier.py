"""Academic Copilot — Multi-intent classifier (Phase XI).

Extends the routing vocabulary from synaptiq_ai/orchestrator.py with
intelligence-engine intents (manuscript, literature, gap, statistical).
Returns ALL detected intents with confidence scores; the planner decides
which to include based on confidence threshold.
"""
from __future__ import annotations

import re
from .models import DetectedIntent, IntentType

# Minimum confidence to include an intent in the workflow
CONFIDENCE_THRESHOLD = 0.35

# ── Intent signal patterns ────────────────────────────────────────────────────
# Each entry: (IntentType, weight, list_of_keyword_patterns)
# Weight ∈ (0,1): added to confidence when the pattern matches.
# Multiple patterns can fire; confidence is capped at 1.0.

_INTENT_RULES: list[tuple[IntentType, float, list[str]]] = [

    # ── High-specificity intelligence-engine intents ──────────────────────────
    (IntentType.MANUSCRIPT_REVIEW, 0.6, [
        r"\breview\s+(?:my\s+)?(?:manuscript|paper|article|chapter)\b",
        r"\bmanuscript\s+review\b", r"\bpeer\s+review\b",
        r"\bcheck\s+(?:my\s+)?(?:paper|manuscript|writing)\b",
        r"\bfeedback\s+on\s+(?:my\s+)?(?:manuscript|paper|article)\b",
        r"\bproofread\b", r"\bcopyedit\b",
    ]),
    (IntentType.MANUSCRIPT_REVIEW, 0.35, [
        r"\bwriting\s+quality\b", r"\bacademic\s+writing\b",
        r"\bstructure\s+of\s+(?:my\s+)?paper\b", r"\bmissing\s+section\b",
        r"\bintroduction\s+(?:section|improvement)\b",
        r"\bconclusion\s+(?:section|improvement)\b",
    ]),

    (IntentType.LITERATURE_REVIEW, 0.7, [
        r"\bliterature\s+review\b", r"\bsystematic\s+review\b",
        r"\bscoping\s+review\b", r"\bsearch\s+literature\b",
        r"\breview\s+existing\s+(?:literature|research|studies)\b",
        r"\bwhat\s+(?:research|papers|studies)\s+(?:exist|have been done)\b",
    ]),
    (IntentType.LITERATURE_REVIEW, 0.35, [
        r"\brelated\s+work\b", r"\bprior\s+research\b",
        r"\btheoretical\s+background\b", r"\bstate\s+of\s+the\s+art\b",
        r"\bcurrent\s+literature\b", r"\bprevious\s+studies\b",
    ]),

    (IntentType.GAP_ANALYSIS, 0.7, [
        r"\bresearch\s+gaps?\b", r"\bgap\s+in\s+(?:the\s+)?literature\b",
        r"\bnovelty\b", r"\bwhat(?:'s| is)\s+missing\b",
        r"\bunderstudied\b", r"\bunderexplored\b", r"\bunaddressed\b",
    ]),
    (IntentType.GAP_ANALYSIS, 0.35, [
        r"\boriginal\s+contribution\b", r"\bfuture\s+research\b",
        r"\bno\s+study\s+has\b", r"\blimited\s+research\b",
        r"\bfew\s+studies\b", r"\black\s+of\s+research\b",
    ]),

    (IntentType.STATISTICAL_REVIEW, 0.7, [
        r"\bstatistical\s+(?:review|analysis|check|feedback)\b",
        r"\bdata\s+analysis\s+review\b", r"\bstatistics\s+review\b",
        r"\bcheck\s+(?:my\s+)?statistics\b", r"\bcheck\s+(?:my\s+)?data\s+analysis\b",
        r"\bmethod(?:ology|ological)\s+review\b",
    ]),
    (IntentType.STATISTICAL_REVIEW, 0.35, [
        r"\bregression\b", r"\banova\b", r"\bsem\b", r"\bpls\b",
        r"\bp[\s-]value\b", r"\beffect\s+size\b", r"\bsample\s+size\b",
        r"\bpower\s+analysis\b", r"\bassumption\s+check\b",
    ]),

    # ── Journal and submission ─────────────────────────────────────────────────
    (IntentType.JOURNAL_REC, 0.7, [
        r"\bwhich\s+journal\b", r"\bwhere\s+(?:to\s+)?(?:publish|submit)\b",
        r"\bjournal\s+recommend\w*\b", r"\bbest\s+journal\b",
        r"\bsuitable\s+journal\b", r"\btarget\s+journal\b",
        r"\bjournal\s+match\w*\b", r"\bsubmit\s+(?:to|my)\b",
    ]),
    (IntentType.JOURNAL_REC, 0.35, [
        r"\bimpact\s+factor\b", r"\bopen\s+access\b", r"\bq1\b", r"\bq2\b",
        r"\bpredatory\b", r"\bdesk\s+rejection\b", r"\bscimago\b",
    ]),

    # ── Grant guidance ────────────────────────────────────────────────────────
    (IntentType.GRANT_GUIDANCE, 0.7, [
        r"\bgrant\s+(?:proposal|application|writing|review|readiness)\b",
        r"\bfunding\s+(?:opportunity|application|proposal)\b",
        r"\bfellowship\s+(?:application|advice)\b",
        r"\bnsf|nih|erc|horizon\s+europe|marie\s+curie\b",
        r"\bapply\s+for\s+(?:a\s+)?(?:grant|funding|fellowship)\b",
    ]),
    (IntentType.GRANT_GUIDANCE, 0.35, [
        r"\bgrant\b", r"\bfunding\b", r"\bscholarship\b",
        r"\bresearch\s+award\b", r"\bgrant\s+deadline\b",
    ]),

    # ── Conference ────────────────────────────────────────────────────────────
    (IntentType.CONFERENCE_GUIDANCE, 0.7, [
        r"\bconference\s+(?:recommend\w*|submission|strategy|abstract)\b",
        r"\bwhich\s+conference\b", r"\bcfp\b", r"\bcall\s+for\s+papers\b",
        r"\bpresent\s+(?:at|my)\s+(?:a\s+)?conference\b",
    ]),
    (IntentType.CONFERENCE_GUIDANCE, 0.35, [
        r"\bconference\b", r"\bpresentation\b", r"\bposter\b",
        r"\bproceed\w*\b",
    ]),

    # ── Methodology ───────────────────────────────────────────────────────────
    (IntentType.METHODOLOGY_ADVICE, 0.65, [
        r"\bmethodology\s+(?:advice|review|recommendation|help)\b",
        r"\bwhich\s+(?:method|methodology|approach)\b",
        r"\bbest\s+(?:method|methodology|approach)\s+(?:to|for)\b",
        r"\bresearch\s+design\b", r"\bmixed\s+method\b",
        r"\bqualitative\s+(?:vs|versus|or)\s+quantitative\b",
    ]),
    (IntentType.METHODOLOGY_ADVICE, 0.35, [
        r"\bsurv(?:ey|eys)\b", r"\binterview\b", r"\bcase\s+study\b",
        r"\bexperiment(?:al)?\b", r"\bthematic\s+analysis\b",
    ]),

    # ── Career planning ───────────────────────────────────────────────────────
    (IntentType.CAREER_PLANNING, 0.65, [
        r"\bcareer\s+(?:plan|advice|goal|development|strategy|path)\b",
        r"\bacademic\s+career\b", r"\btenure\s+track\b",
        r"\bphd\s+(?:completion|timeline|advice)\b",
        r"\bpostdoc\b", r"\bjob\s+market\b", r"\bacademic\s+position\b",
    ]),
    (IntentType.CAREER_PLANNING, 0.35, [
        r"\bpromotion\b", r"\btenure\b", r"\bcareer\b",
        r"\bvisibility\b", r"\breputation\b",
    ]),

    # ── Writing coaching ──────────────────────────────────────────────────────
    (IntentType.WRITING_COACHING, 0.6, [
        r"\bwriting\s+(?:coach|advice|tips|improvement|skills)\b",
        r"\bimprove\s+(?:my\s+)?writing\b", r"\bacademic\s+writing\b",
        r"\bhow\s+to\s+write\b", r"\bwriting\s+style\b",
        r"\bclarity\b", r"\bflow\b", r"\bcohesion\b",
    ]),
    (IntentType.WRITING_COACHING, 0.3, [
        r"\bsentence\s+structure\b", r"\bpassive\s+voice\b",
        r"\bword\s+choice\b", r"\bsyllog\w*\b", r"\bparagraph\b",
    ]),

    # ── Roadmap request ───────────────────────────────────────────────────────
    (IntentType.ROADMAP_REQUEST, 0.8, [
        r"\broadmap\b", r"\bresearch\s+plan\b", r"\bpublication\s+plan\b",
        r"\bgrant\s+plan\b", r"\bphd\s+plan\b", r"\btimeline\b",
        r"\bstep[\s-]by[\s-]step\s+plan\b", r"\baction\s+plan\b",
    ]),
    (IntentType.ROADMAP_REQUEST, 0.35, [
        r"\bplan\s+(?:for|to|my)\b", r"\bschedule\b",
        r"\bmilestone\b", r"\bdeadline\b",
    ]),

    # ── Project planning ──────────────────────────────────────────────────────
    (IntentType.PROJECT_PLANNING, 0.6, [
        r"\bproject\s+(?:plan|management|tracking|status|update)\b",
        r"\btrack\s+(?:my\s+)?(?:progress|project|research)\b",
        r"\btask\s+(?:list|management)\b", r"\bmilestone\s+(?:tracking|review)\b",
        r"\bdeadline\s+(?:management|tracking)\b",
    ]),
]

# Intents that are mutually inclusive with literature review
_COMPOSITE_TRIGGERS: dict[str, list[IntentType]] = {
    "publish a paper": [
        IntentType.LITERATURE_REVIEW, IntentType.GAP_ANALYSIS,
        IntentType.MANUSCRIPT_REVIEW, IntentType.JOURNAL_REC,
    ],
    "publish an article": [
        IntentType.LITERATURE_REVIEW, IntentType.GAP_ANALYSIS,
        IntentType.MANUSCRIPT_REVIEW, IntentType.JOURNAL_REC,
    ],
    "complete my phd": [
        IntentType.ROADMAP_REQUEST, IntentType.CAREER_PLANNING,
        IntentType.MANUSCRIPT_REVIEW, IntentType.GRANT_GUIDANCE,
    ],
    "start my research": [
        IntentType.LITERATURE_REVIEW, IntentType.GAP_ANALYSIS,
        IntentType.METHODOLOGY_ADVICE, IntentType.ROADMAP_REQUEST,
    ],
    "write a grant proposal": [
        IntentType.GRANT_GUIDANCE, IntentType.ROADMAP_REQUEST,
        IntentType.LITERATURE_REVIEW,
    ],
    "submit my manuscript": [
        IntentType.MANUSCRIPT_REVIEW, IntentType.JOURNAL_REC,
        IntentType.STATISTICAL_REVIEW,
    ],
    "review my paper": [
        IntentType.MANUSCRIPT_REVIEW, IntentType.STATISTICAL_REVIEW,
        IntentType.JOURNAL_REC,
    ],
}

# Engine required per intent
_INTENT_ENGINES: dict[IntentType, list[str]] = {
    IntentType.MANUSCRIPT_REVIEW:   ["manuscript"],
    IntentType.LITERATURE_REVIEW:   ["literature"],
    IntentType.GAP_ANALYSIS:        ["gap"],
    IntentType.STATISTICAL_REVIEW:  ["statistical"],
    IntentType.JOURNAL_REC:         [],
    IntentType.GRANT_GUIDANCE:      [],
    IntentType.CONFERENCE_GUIDANCE: [],
    IntentType.METHODOLOGY_ADVICE:  [],
    IntentType.CAREER_PLANNING:     [],
    IntentType.WRITING_COACHING:    [],
    IntentType.ROADMAP_REQUEST:     [],
    IntentType.PROJECT_PLANNING:    [],
    IntentType.GENERAL_CHAT:        [],
}


def classify_intents(message: str) -> list[DetectedIntent]:
    """Return all detected intents above CONFIDENCE_THRESHOLD, sorted by confidence."""
    lower = message.lower()
    scores: dict[IntentType, tuple[float, list[str]]] = {}

    for intent_type, weight, patterns in _INTENT_RULES:
        for pattern in patterns:
            if re.search(pattern, lower):
                cur_score, cur_signals = scores.get(intent_type, (0.0, []))
                new_score = min(1.0, cur_score + weight)
                cur_signals.append(pattern)
                scores[intent_type] = (new_score, cur_signals[:5])

    # Check composite triggers
    for trigger, added_intents in _COMPOSITE_TRIGGERS.items():
        if trigger in lower:
            for intent_type in added_intents:
                cur_score, cur_signals = scores.get(intent_type, (0.0, []))
                new_score = min(1.0, cur_score + 0.5)
                cur_signals.append(f"composite:{trigger}")
                scores[intent_type] = (new_score, cur_signals[:5])

    results: list[DetectedIntent] = []
    for intent_type, (confidence, signals) in scores.items():
        if confidence >= CONFIDENCE_THRESHOLD:
            results.append(DetectedIntent(
                intent_type=intent_type,
                confidence=confidence,
                signals=signals,
                requires_engines=_INTENT_ENGINES.get(intent_type, []),
            ))

    results.sort(key=lambda x: x.confidence, reverse=True)

    if not results:
        results.append(DetectedIntent(
            intent_type=IntentType.GENERAL_CHAT,
            confidence=1.0,
            signals=["fallback"],
            requires_engines=[],
        ))

    return results


def primary_intent(message: str) -> DetectedIntent:
    return classify_intents(message)[0]
