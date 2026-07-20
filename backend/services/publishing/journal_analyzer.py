"""Academic Publishing Intelligence — Journal analyzer (Phase XII).

Extended journal database with 30+ fit factors, acceptance probability
modelling, desk rejection risk, and predatory risk scoring.
"""
from __future__ import annotations

import re
from .models import JournalFitScore, JournalProfile, RiskLevel

# ── Extended Journal Database ─────────────────────────────────────────────────
# Fields: name, publisher, quartile, if_, cite_score, snip, sjr,
#         acc, review_wks, pub_wks, oa, hybrid, apc_usd, predatory_risk,
#         tags, language, ref_style, data_sharing, notes

_JOURNALS_EXT: list[dict] = [
    # ── Medicine / Health ─────────────────────────────────────────────────────
    {"name": "The Lancet",            "pub": "Elsevier",     "q": "Q1", "if": 202.7, "cite": 249.0, "snip": 10.8, "sjr": 22.0, "acc": 0.05, "rev": 8,  "pub_wks": 14, "oa": False, "hyb": False, "apc": 0,     "pred": 0.0,  "tags": ["medicine","health","clinical","epidemiology"],             "ref": "Vancouver", "ds": True},
    {"name": "JAMA",                  "pub": "AMA",          "q": "Q1", "if": 157.3, "cite": 180.0, "snip": 9.1,  "sjr": 17.0, "acc": 0.05, "rev": 6,  "pub_wks": 12, "oa": False, "hyb": True,  "apc": 3100,  "pred": 0.0,  "tags": ["medicine","clinical","healthcare"],                         "ref": "AMA",       "ds": True},
    {"name": "BMJ",                   "pub": "BMJ Publishing","q": "Q1", "if": 105.7, "cite": 130.0, "snip": 7.9,  "sjr": 11.5, "acc": 0.07, "rev": 8,  "pub_wks": 14, "oa": True,  "hyb": False, "apc": 4870,  "pred": 0.0,  "tags": ["medicine","clinical","health policy","public health"],      "ref": "Vancouver", "ds": True},
    {"name": "PLOS Medicine",         "pub": "PLOS",         "q": "Q1", "if": 15.8,  "cite": 23.0,  "snip": 2.5,  "sjr": 3.0,  "acc": 0.15, "rev": 10, "pub_wks": 16, "oa": True,  "hyb": False, "apc": 3500,  "pred": 0.0,  "tags": ["medicine","health","public health","epidemiology"],          "ref": "Vancouver", "ds": True},
    {"name": "PLOS ONE",              "pub": "PLOS",         "q": "Q2", "if": 3.7,   "cite": 5.0,   "snip": 1.0,  "sjr": 0.9,  "acc": 0.55, "rev": 6,  "pub_wks": 10, "oa": True,  "hyb": False, "apc": 1895,  "pred": 0.0,  "tags": ["multidisciplinary","science","psychology","biology","medicine"], "ref": "APA",   "ds": True},
    {"name": "Scientific Reports",    "pub": "Nature",       "q": "Q2", "if": 4.6,   "cite": 6.8,   "snip": 1.1,  "sjr": 1.0,  "acc": 0.65, "rev": 5,  "pub_wks": 8,  "oa": True,  "hyb": False, "apc": 2290,  "pred": 0.0,  "tags": ["multidisciplinary","science","biology","engineering"],       "ref": "APA",       "ds": True},
    # ── Psychology ────────────────────────────────────────────────────────────
    {"name": "Psychological Science",                "pub": "SAGE",   "q": "Q1", "if": 7.9,  "cite": 11.5, "snip": 2.8, "sjr": 2.5, "acc": 0.08, "rev": 10, "pub_wks": 18, "oa": False, "hyb": True,  "apc": 3300, "pred": 0.0, "tags": ["psychology","cognitive","behavioural","neuroscience"],                "ref": "APA", "ds": True},
    {"name": "Journal of Personality and Social Psychology", "pub": "APA", "q": "Q1", "if": 8.3, "cite": 12.0, "snip": 3.0, "sjr": 2.8, "acc": 0.10, "rev": 12, "pub_wks": 20, "oa": False, "hyb": True, "apc": 2800, "pred": 0.0, "tags": ["psychology","social","personality"],                                "ref": "APA", "ds": True},
    {"name": "Frontiers in Psychology",              "pub": "Frontiers","q": "Q2","if": 4.2,  "cite": 5.5,  "snip": 1.3, "sjr": 0.9, "acc": 0.50, "rev": 8,  "pub_wks": 12, "oa": True,  "hyb": False, "apc": 2950, "pred": 0.0, "tags": ["psychology","behavioural","cognitive","health psychology"],         "ref": "APA", "ds": False},
    # ── Education ─────────────────────────────────────────────────────────────
    {"name": "Computers & Education",                "pub": "Elsevier","q": "Q1", "if": 12.0, "cite": 16.0, "snip": 3.2, "sjr": 2.6, "acc": 0.15, "rev": 10, "pub_wks": 20, "oa": False, "hyb": True,  "apc": 3600, "pred": 0.0, "tags": ["education","technology","e-learning","learning analytics"],         "ref": "APA", "ds": False},
    {"name": "British Educational Research Journal","pub": "Wiley",   "q": "Q1", "if": 3.2,  "cite": 4.5,  "snip": 1.5, "sjr": 1.0, "acc": 0.18, "rev": 12, "pub_wks": 22, "oa": False, "hyb": True,  "apc": 4200, "pred": 0.0, "tags": ["education","pedagogy","curriculum","higher education"],              "ref": "APA", "ds": False},
    {"name": "Educational Researcher",               "pub": "AERA",   "q": "Q1", "if": 5.9,  "cite": 8.2,  "snip": 2.0, "sjr": 1.8, "acc": 0.12, "rev": 14, "pub_wks": 24, "oa": False, "hyb": True,  "apc": 3000, "pred": 0.0, "tags": ["education","learning","pedagogy","policy"],                          "ref": "APA", "ds": False},
    # ── Management / Business ─────────────────────────────────────────────────
    {"name": "Journal of Management",                "pub": "SAGE",   "q": "Q1", "if": 9.8,  "cite": 13.0, "snip": 4.5, "sjr": 3.5, "acc": 0.08, "rev": 14, "pub_wks": 26, "oa": False, "hyb": True,  "apc": 3800, "pred": 0.0, "tags": ["management","organisation","leadership","strategy","business"],     "ref": "APA", "ds": False},
    {"name": "Academy of Management Journal",        "pub": "AOM",    "q": "Q1", "if": 9.2,  "cite": 12.5, "snip": 4.2, "sjr": 3.2, "acc": 0.06, "rev": 16, "pub_wks": 28, "oa": False, "hyb": False, "apc": 0,    "pred": 0.0, "tags": ["management","organisation","strategy","entrepreneurship"],           "ref": "APA", "ds": False},
    {"name": "International Journal of Management Reviews", "pub": "Wiley", "q": "Q1", "if": 10.5, "cite": 14.0, "snip": 3.8, "sjr": 2.9, "acc": 0.12, "rev": 12, "pub_wks": 22, "oa": False, "hyb": True, "apc": 4500, "pred": 0.0, "tags": ["management","review","business","leadership"],               "ref": "APA", "ds": False},
    {"name": "Leadership Quarterly",                 "pub": "Elsevier","q": "Q1", "if": 8.7,  "cite": 11.5, "snip": 3.4, "sjr": 2.7, "acc": 0.10, "rev": 12, "pub_wks": 20, "oa": False, "hyb": True,  "apc": 3200, "pred": 0.0, "tags": ["management","leadership","organisation","behaviour"],               "ref": "APA", "ds": False},
    # ── Computer Science / AI ─────────────────────────────────────────────────
    {"name": "Nature Machine Intelligence",          "pub": "Nature",  "q": "Q1", "if": 25.9, "cite": 30.0, "snip": 5.2, "sjr": 6.0, "acc": 0.06, "rev": 8,  "pub_wks": 14, "oa": False, "hyb": True,  "apc": 9500, "pred": 0.0, "tags": ["ai","machine learning","deep learning","nlp","computer science"],  "ref": "Nature", "ds": True},
    {"name": "IEEE Transactions on Neural Networks", "pub": "IEEE",    "q": "Q1", "if": 14.3, "cite": 18.0, "snip": 3.6, "sjr": 3.2, "acc": 0.15, "rev": 10, "pub_wks": 18, "oa": False, "hyb": True,  "apc": 2595, "pred": 0.0, "tags": ["ai","neural networks","machine learning","deep learning"],          "ref": "IEEE",   "ds": False},
    {"name": "Artificial Intelligence",              "pub": "Elsevier","q": "Q1", "if": 14.1, "cite": 17.5, "snip": 3.5, "sjr": 3.0, "acc": 0.12, "rev": 12, "pub_wks": 22, "oa": False, "hyb": True,  "apc": 3400, "pred": 0.0, "tags": ["ai","artificial intelligence","computer science","nlp","planning"],  "ref": "Elsevier","ds": False},
    {"name": "Pattern Recognition",                  "pub": "Elsevier","q": "Q1", "if": 8.5,  "cite": 11.0, "snip": 2.5, "sjr": 2.0, "acc": 0.18, "rev": 10, "pub_wks": 18, "oa": False, "hyb": True,  "apc": 3200, "pred": 0.0, "tags": ["ai","computer vision","machine learning","deep learning","image"],    "ref": "Elsevier","ds": False},
    # ── Engineering ───────────────────────────────────────────────────────────
    {"name": "IEEE Transactions on Industrial Electronics","pub": "IEEE","q": "Q1","if": 8.2, "cite": 11.5, "snip": 2.8, "sjr": 2.0, "acc": 0.25, "rev": 10, "pub_wks": 16, "oa": False, "hyb": True,  "apc": 2595, "pred": 0.0, "tags": ["engineering","electronics","control","automation","power systems"],   "ref": "IEEE", "ds": False},
    {"name": "Applied Energy",                       "pub": "Elsevier","q": "Q1", "if": 11.4, "cite": 15.0, "snip": 3.3, "sjr": 2.5, "acc": 0.20, "rev": 8,  "pub_wks": 14, "oa": False, "hyb": True,  "apc": 3500, "pred": 0.0, "tags": ["engineering","energy","renewable","sustainability","power"],        "ref": "Elsevier","ds": False},
    # ── Social Sciences ───────────────────────────────────────────────────────
    {"name": "Social Science & Medicine",            "pub": "Elsevier","q": "Q1", "if": 5.7,  "cite": 8.0,  "snip": 2.2, "sjr": 1.8, "acc": 0.15, "rev": 10, "pub_wks": 18, "oa": False, "hyb": True,  "apc": 3400, "pred": 0.0, "tags": ["social science","public health","medicine","sociology","health"],    "ref": "APA",  "ds": False},
    {"name": "International Journal of Information Management","pub": "Elsevier","q": "Q1","if": 12.7,"cite": 17.0,"snip": 3.5,"sjr": 2.8,"acc": 0.12,"rev": 8,"pub_wks": 14,"oa": False,"hyb": True, "apc": 3600, "pred": 0.0, "tags": ["information systems","management","technology","digital","data"],       "ref": "APA",  "ds": False},
    # ── Environmental / Sustainability ────────────────────────────────────────
    {"name": "Nature Sustainability",                "pub": "Nature",  "q": "Q1", "if": 29.2, "cite": 35.0, "snip": 6.5, "sjr": 7.0, "acc": 0.07, "rev": 8,  "pub_wks": 12, "oa": False, "hyb": True,  "apc": 9500, "pred": 0.0, "tags": ["sustainability","environment","climate","ecology","policy"],          "ref": "Nature", "ds": True},
    {"name": "Global Environmental Change",          "pub": "Elsevier","q": "Q1", "if": 10.9, "cite": 14.5, "snip": 3.8, "sjr": 2.8, "acc": 0.12, "rev": 10, "pub_wks": 20, "oa": False, "hyb": True,  "apc": 3500, "pred": 0.0, "tags": ["environment","climate","sustainability","ecology"],                   "ref": "Elsevier","ds": False},
    # ── Nursing / Allied Health ───────────────────────────────────────────────
    {"name": "Journal of Advanced Nursing",          "pub": "Wiley",   "q": "Q1", "if": 4.4,  "cite": 6.0,  "snip": 1.8, "sjr": 1.2, "acc": 0.18, "rev": 8,  "pub_wks": 16, "oa": False, "hyb": True,  "apc": 4300, "pred": 0.0, "tags": ["nursing","health","clinical","healthcare","qualitative"],           "ref": "APA",  "ds": False},
    # ── Economics / Finance ───────────────────────────────────────────────────
    {"name": "Journal of Financial Economics",       "pub": "Elsevier","q": "Q1", "if": 8.8,  "cite": 12.0, "snip": 4.5, "sjr": 4.0, "acc": 0.08, "rev": 16, "pub_wks": 28, "oa": False, "hyb": False, "apc": 0,    "pred": 0.0, "tags": ["finance","economics","financial markets","investment","accounting"], "ref": "APA",  "ds": False},
]

# ── Publisher trust scores ────────────────────────────────────────────────────
# Used to estimate predatory risk for journals NOT in the database.
_TRUSTED_PUBLISHERS = {
    "elsevier", "springer", "wiley", "taylor & francis", "sage", "oxford",
    "cambridge", "apa", "ama", "bma", "bmj", "nature", "ieee", "acm",
    "plos", "frontiers", "mdpi", "aera", "aom", "lippincott", "thieme",
}

_HIGH_PRED_SIGNALS = [
    "rapid publication", "all manuscripts accepted", "no peer review",
    "guaranteed acceptance", "publishing for everyone",
]


def _to_profile(j: dict) -> JournalProfile:
    return JournalProfile(
        name=j["name"], publisher=j["pub"], quartile=j["q"],
        impact_factor=j["if"], cite_score=j.get("cite", 0.0),
        snip=j.get("snip", 0.0), sjr=j.get("sjr", 0.0),
        acceptance_rate=j["acc"],
        review_duration_weeks=j["rev"],
        time_to_publication_weeks=j.get("pub_wks", j["rev"] + 10),
        open_access=j["oa"], hybrid=j.get("hyb", False),
        apc_usd=j.get("apc", 0),
        predatory_risk=j.get("pred", 0.0),
        tags=j["tags"],
        reference_style=j.get("ref", "APA"),
        requires_data_sharing=j.get("ds", False),
        notes=j.get("notes", ""),
    )


_PROFILES: list[JournalProfile] = [_to_profile(j) for j in _JOURNALS_EXT]

# ── Scoring helpers ───────────────────────────────────────────────────────────

def _scope_match(text: str, discipline: str, journal: JournalProfile) -> float:
    """Measure how well the journal scope aligns with the manuscript topic."""
    text_lower = text.lower()
    disc_lower = discipline.lower()
    hits = sum(1 for t in journal.tags if t in text_lower or t in disc_lower)
    return min(1.0, hits / max(len(journal.tags) * 0.4, 1))


def _acceptance_probability(
    journal: JournalProfile,
    manuscript_quality: float,
    scope: float,
) -> float:
    """Adjust base acceptance rate by manuscript quality and scope match."""
    q = manuscript_quality / 100.0
    adjusted = journal.acceptance_rate * (0.4 + 0.6 * q) * (0.5 + 0.5 * scope)
    return round(min(0.92, max(0.01, adjusted)), 3)


def _desk_rejection_risk(
    journal: JournalProfile,
    scope: float,
    manuscript_quality: float,
) -> float:
    """Estimate desk rejection probability."""
    base = 1.0 - journal.acceptance_rate          # strict journals → higher base
    scope_penalty = max(0, (0.5 - scope)) * 0.6   # poor scope fit ↑ risk
    quality_bonus = (manuscript_quality / 100) * 0.4
    risk = base * 0.4 + scope_penalty - quality_bonus + (journal.predatory_risk * 0.05)
    return round(max(0.02, min(0.95, risk)), 3)


_Q_WEIGHTS = {"Q1": 1.0, "Q2": 0.75, "Q3": 0.55, "Q4": 0.35}


def _overall_fit(
    scope: float,
    acc_prob: float,
    desk_risk: float,
    journal: JournalProfile,
) -> float:
    """Composite overall fit score 0–1."""
    q_weight = _Q_WEIGHTS.get(journal.quartile, 0.5)
    return round(
        0.35 * scope
        + 0.25 * acc_prob
        + 0.20 * (1 - desk_risk)
        + 0.10 * q_weight
        + 0.10 * (1 - journal.predatory_risk),
        3,
    )


def _build_strengths_weaknesses(
    journal: JournalProfile,
    scope: float,
    acc_prob: float,
    desk_risk: float,
    ms_quality: float,
) -> tuple[list[str], list[str]]:
    strengths: list[str] = []
    weaknesses: list[str] = []

    if scope >= 0.7:
        strengths.append(f"Strong topic alignment with {journal.name}'s scope ({journal.tags[:2]})")
    elif scope < 0.3:
        weaknesses.append(f"Weak scope alignment — {journal.name} focuses on {journal.tags[:2]}")

    if acc_prob >= 0.40:
        strengths.append(f"Realistic acceptance probability ({acc_prob:.0%})")
    elif acc_prob < 0.10:
        weaknesses.append(f"Very low acceptance probability ({acc_prob:.0%}) — consider a safer journal")

    if desk_risk < 0.20:
        strengths.append("Low desk rejection risk")
    elif desk_risk > 0.60:
        weaknesses.append(f"High desk rejection risk ({desk_risk:.0%}) — scope mismatch likely")

    if journal.open_access:
        strengths.append("Full open access — maximises discoverability")
    if journal.apc_usd > 3000:
        weaknesses.append(f"High APC (${journal.apc_usd:,}) — confirm funding availability")
    if journal.apc_usd == 0 and not journal.open_access:
        strengths.append("No publication fee (subscription journal)")

    if journal.review_duration_weeks <= 8:
        strengths.append(f"Fast review process (~{journal.review_duration_weeks} weeks)")
    elif journal.review_duration_weeks >= 16:
        weaknesses.append(f"Slow review process (~{journal.review_duration_weeks} weeks)")

    if journal.predatory_risk > 0.5:
        weaknesses.append(f"Elevated predatory risk — verify on DOAJ/Beall's list")

    if journal.impact_factor >= 10:
        strengths.append(f"High-impact journal (IF={journal.impact_factor})")
    elif journal.impact_factor < 2.0 and journal.impact_factor > 0:
        weaknesses.append(f"Moderate impact factor (IF={journal.impact_factor})")

    return strengths[:4], weaknesses[:4]


# ── Public API ────────────────────────────────────────────────────────────────

def get_all_profiles() -> list[JournalProfile]:
    return list(_PROFILES)


def analyze_journal_fit(
    text: str,
    discipline: str,
    manuscript_quality: float,
) -> list[JournalFitScore]:
    """Score every journal in the database against the manuscript and return sorted fits."""
    scored: list[tuple[float, JournalFitScore]] = []
    text_lower = text.lower()

    for journal in _PROFILES:
        scope = _scope_match(text_lower, discipline, journal)
        if scope == 0.0:
            continue  # not in scope at all

        acc = _acceptance_probability(journal, manuscript_quality, scope)
        desk_risk = _desk_rejection_risk(journal, scope, manuscript_quality)
        fit = _overall_fit(scope, acc, desk_risk, journal)
        strengths, weaknesses = _build_strengths_weaknesses(
            journal, scope, acc, desk_risk, manuscript_quality
        )

        fit_score = JournalFitScore(
            journal=journal,
            scope_match=scope,
            acceptance_probability=acc,
            desk_rejection_risk=desk_risk,
            overall_fit=fit,
            strengths=strengths,
            weaknesses=weaknesses,
            rationale=(
                f"{journal.name} ({journal.quartile}, IF={journal.impact_factor}) "
                f"shows {scope:.0%} scope match with estimated {acc:.0%} acceptance probability."
            ),
            submission_notes=journal.notes or (
                f"Review duration ~{journal.review_duration_weeks} weeks. "
                + ("Open access. " if journal.open_access else "Subscription journal. ")
                + f"APC: {'$' + str(journal.apc_usd) if journal.apc_usd else 'None'}."
            ),
        )
        scored.append((fit, fit_score))

    scored.sort(key=lambda x: -x[0])
    return [fs for _, fs in scored]
