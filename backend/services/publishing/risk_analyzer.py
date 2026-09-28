"""Academic Publishing Intelligence — Publication risk analyzer.

5 manuscript-content risk dimensions: peer review readiness, ethical
compliance, methodological concerns, language quality, citation practice.
All are computed from the manuscript text itself via deterministic
heuristics — no journal-specific data is used.

Phase 0 removed 3 former dimensions (desk rejection, publication delay,
predatory-journal risk) that depended on per-journal acceptance-rate,
review-duration, and predatory-risk figures no real source publishes —
those were fed hardcoded defaults, which violates the "no fabricated
academic data" rule. See AUDIT_PHASE0.md.
"""
from __future__ import annotations

import re
from .models import PublicationRisk, RiskDimension, RiskLevel

_RISK_LEVELS_BY_SCORE = [
    (0.80, RiskLevel.CRITICAL),
    (0.60, RiskLevel.HIGH),
    (0.40, RiskLevel.MODERATE),
    (0.20, RiskLevel.LOW),
    (0.00, RiskLevel.MINIMAL),
]

_ETHICAL_KEYWORDS = [
    "participants", "informed consent", "irb", "ethics committee",
    "anonymised", "deidentified", "privacy", "gdpr", "vulnerable population",
]
_ETHICS_STATEMENT_RE = re.compile(
    r"\bethics\s+(?:approval|statement|committee)\b|\birb\b|\binstitutional\s+review\b",
    re.IGNORECASE,
)
_METHOD_WEAK_RE = re.compile(
    r"\bsmall\s+sample\b|\bn\s*=\s*[1-2]\d\b|\bno\s+control\s+group\b"
    r"|\bconvenience\s+sample\b|\bself[\s-]report\b",
    re.IGNORECASE,
)
_PASSIVE_RE   = re.compile(r"\bwas\s+\w+ed\b|\bwere\s+\w+ed\b", re.IGNORECASE)
_HEDGE_RE     = re.compile(r"\bperhaps\b|\bmaybe\b|\bsomewhat\b|\bseems to\b", re.IGNORECASE)
_CITATION_RE  = re.compile(r"\([\w\s]+,?\s*\d{4}\)|\[\d+\]")
_SELF_CITE_RE = re.compile(r"\bauthor\s+\d*\s*,?\s*\d{4}\b|\bour\s+previous\s+(?:work|study|paper)\b", re.IGNORECASE)


def _level(score: float) -> RiskLevel:
    for threshold, level in _RISK_LEVELS_BY_SCORE:
        if score >= threshold:
            return level
    return RiskLevel.MINIMAL


def _dim_peer_review(manuscript_quality: float, has_statistics: bool) -> RiskDimension:
    base = max(0.1, 1 - manuscript_quality / 100)
    stat_penalty = 0.1 if not has_statistics else 0.0
    score = round(min(0.95, base * 0.8 + stat_penalty), 3)

    signals, mitigations = [], []
    if manuscript_quality < 60:
        signals.append("Below-average manuscript quality")
        mitigations.append("Comprehensive review by senior colleagues before submission")
    if not has_statistics:
        signals.append("No statistical analysis detected")
        mitigations.append("Add quantitative evidence where appropriate")

    return RiskDimension("Peer Review Rejection", _level(score), score,
                         "Risk of rejection during peer review.", signals, mitigations)


def _dim_ethical(text: str, metadata: dict) -> RiskDimension:
    involves_human = any(kw in text.lower() for kw in _ETHICAL_KEYWORDS)
    has_statement = bool(_ETHICS_STATEMENT_RE.search(text)) or metadata.get("has_ethics_statement", False)

    if involves_human and not has_statement:
        score = 0.75
        signals = ["Research involves human participants — no ethics statement found"]
        mitigations = ["Add IRB/ethics approval details to Methods section"]
    elif involves_human and has_statement:
        score = 0.15
        signals = ["Ethics statement present"]
        mitigations = []
    else:
        score = 0.10
        signals = []
        mitigations = []

    return RiskDimension("Ethical Compliance", _level(score), score,
                         "Risk of ethical concerns raised by reviewers or editors.",
                         signals, mitigations)


def _dim_methodological(text: str, manuscript_quality: float) -> RiskDimension:
    weak_count = len(_METHOD_WEAK_RE.findall(text))
    base = weak_count * 0.15 + (0.5 - manuscript_quality / 200)
    score = round(max(0.05, min(0.90, base)), 3)

    signals = []
    mitigations = []
    if weak_count:
        signals.append(f"{weak_count} methodological weakness signal(s) detected")
        mitigations.append("Acknowledge limitations explicitly in Discussion")
    if manuscript_quality < 60:
        mitigations.append("Seek statistical consultation before submission")

    return RiskDimension("Methodological Concerns", _level(score), score,
                         "Risk of methodological criticism.", signals, mitigations)


def _dim_language(text: str) -> RiskDimension:
    word_count = len(text.split())
    passive_density = len(_PASSIVE_RE.findall(text)) / max(word_count / 100, 1)
    hedge_count = len(_HEDGE_RE.findall(text))

    score = round(min(0.85, passive_density * 0.1 + hedge_count * 0.05), 3)
    signals, mitigations = [], []
    if passive_density > 5:
        signals.append(f"High passive voice density ({passive_density:.1f}/100 words)")
        mitigations.append("Reduce passive constructions for clarity")
    if hedge_count > 10:
        signals.append(f"{hedge_count} hedging expressions detected")
        mitigations.append("Replace vague hedges with precise qualifications")

    return RiskDimension("Language Quality", _level(score), score,
                         "Risk of revision requests due to language issues.",
                         signals, mitigations)


def _dim_citation(text: str) -> RiskDimension:
    cite_count = len(_CITATION_RE.findall(text))
    self_cite_count = len(_SELF_CITE_RE.findall(text))

    score = 0.0
    signals, mitigations = [], []
    if cite_count < 10:
        score += 0.4
        signals.append(f"Low citation count ({cite_count})")
        mitigations.append("Expand the reference list; cite relevant prior work")
    if self_cite_count > 5:
        score += 0.3
        signals.append(f"High self-citation count ({self_cite_count})")
        mitigations.append("Reduce self-citations to < 20% of total references")

    score = round(min(0.90, score), 3)
    return RiskDimension("Citation Issues", _level(score), score,
                         "Risk of reviewer criticism about referencing practices.",
                         signals, mitigations)


def analyze_publication_risk(
    text: str,
    manuscript_quality: float,
    metadata: dict | None = None,
) -> PublicationRisk:
    md = metadata or {}
    has_stats = any(kw in text.lower() for kw in ["mean", "standard deviation", "anova", "regression", "p =", "p<", "n ="])

    dims = [
        _dim_peer_review(manuscript_quality, has_stats),
        _dim_ethical(text, md),
        _dim_methodological(text, manuscript_quality),
        _dim_language(text),
        _dim_citation(text),
    ]

    overall = round(sum(d.score for d in dims) / len(dims), 3)
    top_risks = [d.description for d in sorted(dims, key=lambda x: -x.score)[:3]]
    mitigations = list({m for d in dims for m in d.mitigations})[:6]

    return PublicationRisk(
        manuscript_title=md.get("title", "Untitled"),
        overall_risk_score=overall,
        overall_risk_level=_level(overall),
        dimensions=dims,
        top_risks=top_risks,
        mitigation_plan=mitigations,
        # No real basis for a predicted publication-success probability —
        # Phase 0 removed the fabricated formula. See AUDIT_PHASE0.md.
        estimated_success_probability=None,
    )
