"""Academic Publishing Intelligence — Publication risk analyzer (Phase XII).

8 risk dimensions: desk rejection, peer review, ethical, methodological,
language, citation, publication delay, predatory journal.
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


def _dim_desk_rejection(
    scope_match: float,
    manuscript_quality: float,
    journal_acceptance: float,
) -> RiskDimension:
    base = 1 - journal_acceptance
    scope_pen = max(0, 0.5 - scope_match) * 0.6
    quality_bonus = (manuscript_quality / 100) * 0.4
    score = round(max(0.05, min(0.95, base * 0.5 + scope_pen - quality_bonus + 0.1)), 3)

    signals, mitigations = [], []
    if scope_match < 0.4:
        signals.append("Low scope alignment with target journal")
        mitigations.append("Re-evaluate journal fit; consider closer-match journals")
    if manuscript_quality < 60:
        signals.append("Below-average manuscript quality score")
        mitigations.append("Improve overall manuscript quality before submission")
    if journal_acceptance < 0.15:
        signals.append(f"Highly selective journal (acceptance rate < 15%)")
        mitigations.append("Prepare a compelling cover letter emphasising novelty")

    return RiskDimension("Desk Rejection", _level(score), score,
                         "Risk of rejection before peer review.", signals, mitigations)


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


def _dim_delay(journal_review_weeks: int) -> RiskDimension:
    if journal_review_weeks >= 20:
        score, signals, mitigations = 0.7, [f"Review duration {journal_review_weeks} weeks"], ["Consider faster journals if time is critical"]
    elif journal_review_weeks >= 12:
        score, signals, mitigations = 0.4, [f"Moderate review duration ({journal_review_weeks} weeks)"], []
    else:
        score, signals, mitigations = 0.15, [], []

    return RiskDimension("Publication Delay", _level(score), score,
                         "Risk of long time-to-publication.", signals, mitigations)


def _dim_predatory(journal_predatory_risk: float) -> RiskDimension:
    score = journal_predatory_risk
    signals = ["Journal has elevated predatory risk indicators"] if score > 0.3 else []
    mitigations = ["Verify journal on DOAJ, Beall's list, and Scopus before submitting"] if score > 0.3 else []
    return RiskDimension("Predatory Journal Risk", _level(score), score,
                         "Risk that the journal is predatory or low-quality.",
                         signals, mitigations)


def analyze_publication_risk(
    text: str,
    manuscript_quality: float,
    scope_match: float,
    journal_acceptance_rate: float,
    journal_review_weeks: int,
    journal_predatory_risk: float,
    metadata: dict | None = None,
) -> PublicationRisk:
    md = metadata or {}
    has_stats = any(kw in text.lower() for kw in ["mean", "standard deviation", "anova", "regression", "p =", "p<", "n ="])

    dims = [
        _dim_desk_rejection(scope_match, manuscript_quality, journal_acceptance_rate),
        _dim_peer_review(manuscript_quality, has_stats),
        _dim_ethical(text, md),
        _dim_methodological(text, manuscript_quality),
        _dim_language(text),
        _dim_citation(text),
        _dim_delay(journal_review_weeks),
        _dim_predatory(journal_predatory_risk),
    ]

    overall = round(sum(d.score for d in dims) / len(dims), 3)
    top_risks = [d.description for d in sorted(dims, key=lambda x: -x.score)[:3]]
    mitigations = list({m for d in dims for m in d.mitigations})[:6]
    success_prob = round(max(0.05, min(0.95, 1 - overall * 0.8)), 3)

    return PublicationRisk(
        manuscript_title=md.get("title", "Untitled"),
        overall_risk_score=overall,
        overall_risk_level=_level(overall),
        dimensions=dims,
        top_risks=top_risks,
        mitigation_plan=mitigations,
        estimated_success_probability=success_prob,
    )
