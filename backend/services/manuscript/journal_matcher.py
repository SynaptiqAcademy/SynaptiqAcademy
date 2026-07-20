"""Field-aware journal recommender — Phase IX.

Provides rule-based journal recommendations based on inferred discipline,
manuscript quality score, and methodology type.  AI journal matches from
the AI reviewer are merged with these recommendations.
"""
from __future__ import annotations

import re
from .models import JournalMatch

# ── Journal database ──────────────────────────────────────────────────────────
# Organised by discipline cluster.  Each entry: (name, publisher, quartile,
# base_acceptance, IF, open_access, scope_tags, notes)

_JOURNALS: list[dict] = [
    # ── Medicine / Health ──────────────────────────────────────────────────────
    {"name": "The Lancet", "publisher": "Elsevier", "q": "Q1",
     "acc": 0.05, "if": 202.7, "oa": False,
     "tags": ["medicine", "health", "clinical", "epidemiology"],
     "notes": "Submit only high-impact clinical findings with clear public-health implications."},
    {"name": "JAMA", "publisher": "AMA", "q": "Q1",
     "acc": 0.05, "if": 157.3, "oa": False,
     "tags": ["medicine", "clinical", "healthcare", "public health"],
     "notes": "Focus on clinical evidence; strong methods mandatory."},
    {"name": "BMJ", "publisher": "BMJ Publishing", "q": "Q1",
     "acc": 0.07, "if": 105.7, "oa": True,
     "tags": ["medicine", "clinical", "health policy", "public health"],
     "notes": "Open access option available. Strong on evidence-based medicine."},
    {"name": "PLOS Medicine", "publisher": "PLOS", "q": "Q1",
     "acc": 0.15, "if": 15.8, "oa": True,
     "tags": ["medicine", "health", "public health", "epidemiology"],
     "notes": "Full open access. Strong emphasis on replication and data sharing."},
    {"name": "Journal of Clinical Investigation", "publisher": "ASCI", "q": "Q1",
     "acc": 0.10, "if": 19.5, "oa": False,
     "tags": ["clinical", "medicine", "translational", "biomedical"],
     "notes": "Requires translational significance and mechanistic insights."},
    # ── Psychology ─────────────────────────────────────────────────────────────
    {"name": "Psychological Science", "publisher": "SAGE", "q": "Q1",
     "acc": 0.08, "if": 7.9, "oa": False,
     "tags": ["psychology", "cognitive", "behavioural", "neuroscience"],
     "notes": "High standards for effect sizes and pre-registration."},
    {"name": "Journal of Personality and Social Psychology", "publisher": "APA", "q": "Q1",
     "acc": 0.10, "if": 8.3, "oa": False,
     "tags": ["psychology", "social", "personality", "behaviour"],
     "notes": "APA flagship; open science badges available."},
    {"name": "PLOS ONE", "publisher": "PLOS", "q": "Q2",
     "acc": 0.55, "if": 3.7, "oa": True,
     "tags": ["multidisciplinary", "science", "psychology", "biology"],
     "notes": "Broad scope; reviews soundness not novelty. Good for replication studies."},
    # ── Education ─────────────────────────────────────────────────────────────
    {"name": "Educational Researcher", "publisher": "AERA/SAGE", "q": "Q1",
     "acc": 0.12, "if": 5.9, "oa": False,
     "tags": ["education", "learning", "pedagogy", "policy"],
     "notes": "Flagship of American Educational Research Association."},
    {"name": "British Educational Research Journal", "publisher": "Wiley", "q": "Q1",
     "acc": 0.18, "if": 3.2, "oa": False,
     "tags": ["education", "pedagogy", "curriculum", "higher education"],
     "notes": "Strong on empirical and mixed-methods educational research."},
    {"name": "Computers & Education", "publisher": "Elsevier", "q": "Q1",
     "acc": 0.12, "if": 12.0, "oa": False,
     "tags": ["education", "technology", "e-learning", "digital", "AI"],
     "notes": "Leading journal on educational technology; high impact."},
    {"name": "Teaching and Teacher Education", "publisher": "Elsevier", "q": "Q1",
     "acc": 0.15, "if": 5.0, "oa": False,
     "tags": ["education", "teaching", "teacher", "pedagogy"],
     "notes": "Strong empirical and qualitative work on teacher practice."},
    # ── Computer Science / AI ──────────────────────────────────────────────────
    {"name": "Nature Machine Intelligence", "publisher": "Springer Nature", "q": "Q1",
     "acc": 0.06, "if": 23.8, "oa": False,
     "tags": ["AI", "machine learning", "computer science", "deep learning"],
     "notes": "Very high bar; fundamental advances in AI required."},
    {"name": "IEEE Transactions on Neural Networks and Learning Systems", "publisher": "IEEE", "q": "Q1",
     "acc": 0.10, "if": 14.3, "oa": False,
     "tags": ["AI", "machine learning", "neural networks", "deep learning"],
     "notes": "Strong engineering contributions; algorithmic novelty essential."},
    {"name": "Artificial Intelligence", "publisher": "Elsevier", "q": "Q1",
     "acc": 0.12, "if": 14.4, "oa": False,
     "tags": ["AI", "machine learning", "knowledge representation", "reasoning"],
     "notes": "Broad AI; both theoretical and applied contributions welcome."},
    {"name": "Expert Systems with Applications", "publisher": "Elsevier", "q": "Q1",
     "acc": 0.20, "if": 8.7, "oa": False,
     "tags": ["AI", "machine learning", "applications", "data science"],
     "notes": "Applied AI with real-world applications; strong methodology required."},
    # ── Management / Business ──────────────────────────────────────────────────
    {"name": "Academy of Management Journal", "publisher": "AOM", "q": "Q1",
     "acc": 0.08, "if": 10.4, "oa": False,
     "tags": ["management", "organisation", "leadership", "strategy"],
     "notes": "Top management journal; strong theory development required."},
    {"name": "Journal of Management", "publisher": "SAGE", "q": "Q1",
     "acc": 0.08, "if": 13.6, "oa": False,
     "tags": ["management", "organisation", "leadership", "HR"],
     "notes": "Rigorous empirical and conceptual contributions to management."},
    {"name": "Strategic Management Journal", "publisher": "Wiley", "q": "Q1",
     "acc": 0.10, "if": 10.2, "oa": False,
     "tags": ["management", "strategy", "competitive advantage", "organisation"],
     "notes": "Focus on strategic management theory and empirics."},
    {"name": "Journal of Business Research", "publisher": "Elsevier", "q": "Q2",
     "acc": 0.25, "if": 11.3, "oa": False,
     "tags": ["business", "management", "marketing", "strategy"],
     "notes": "High acceptance relative to Q1 journals; strong empirical work."},
    # ── Environmental / Sustainability ─────────────────────────────────────────
    {"name": "Nature Sustainability", "publisher": "Springer Nature", "q": "Q1",
     "acc": 0.04, "if": 27.6, "oa": False,
     "tags": ["sustainability", "environment", "climate", "policy"],
     "notes": "High-impact sustainability science; broad societal relevance required."},
    {"name": "Journal of Cleaner Production", "publisher": "Elsevier", "q": "Q1",
     "acc": 0.20, "if": 11.1, "oa": False,
     "tags": ["sustainability", "environment", "circular economy", "green"],
     "notes": "High output journal; strong empirical environmental studies."},
    # ── Multidisciplinary ──────────────────────────────────────────────────────
    {"name": "Nature", "publisher": "Springer Nature", "q": "Q1",
     "acc": 0.04, "if": 69.5, "oa": False,
     "tags": ["science", "biology", "physics", "chemistry", "multidisciplinary"],
     "notes": "Submit only groundbreaking discoveries of global significance."},
    {"name": "Science", "publisher": "AAAS", "q": "Q1",
     "acc": 0.04, "if": 56.9, "oa": False,
     "tags": ["science", "biology", "physics", "chemistry", "multidisciplinary"],
     "notes": "Seminal discoveries; must demonstrate broad scientific importance."},
    {"name": "Scientific Reports", "publisher": "Springer Nature", "q": "Q2",
     "acc": 0.45, "if": 4.4, "oa": True,
     "tags": ["science", "multidisciplinary", "biology", "technology"],
     "notes": "Broad open-access journal; good for sound but not landmark papers."},
]

# ── Discipline detection ───────────────────────────────────────────────────────

_DISC_SIGNALS: dict[str, list[str]] = {
    "medicine": ["patient", "clinical", "diagnosis", "treatment", "disease", "drug",
                 "surgery", "therapy", "hospital", "epidemiology", "prevalence"],
    "psychology": ["behaviour", "behavior", "cognitive", "anxiety", "depression",
                   "personality", "emotion", "perception", "memory", "attitude"],
    "education": ["student", "learning", "teaching", "curriculum", "pedagogy",
                  "classroom", "school", "university", "academic achievement", "higher education"],
    "AI": ["neural network", "machine learning", "deep learning", "algorithm",
            "natural language processing", "computer vision", "reinforcement learning",
            "transformer", "llm", "large language model", "classification"],
    "management": ["organisation", "organization", "leadership", "strategy", "firm",
                   "managerial", "corporate", "employee", "performance", "governance"],
    "sustainability": ["sustainable", "green", "carbon", "climate change", "renewable",
                       "circular economy", "environmental", "ESG", "net zero"],
    "science": ["experiment", "hypothesis", "laboratory", "biology", "chemistry",
                "physics", "genome", "protein", "cell", "enzyme"],
}


def infer_discipline(text_lower: str, ai_discipline: str = "") -> str:
    if ai_discipline:
        return ai_discipline
    scores: dict[str, int] = {d: 0 for d in _DISC_SIGNALS}
    for disc, signals in _DISC_SIGNALS.items():
        for sig in signals:
            if sig in text_lower:
                scores[disc] += 1
    if not any(v > 0 for v in scores.values()):
        return "general"
    return max(scores, key=lambda k: scores[k])


def recommend_journals(
    text: str,
    discipline: str,
    overall_score: float,
    ai_journal_dicts: list[dict] | None = None,
) -> list[JournalMatch]:
    """Return up to 6 ranked journal matches, merging rule + AI recommendations."""
    text_lower = text.lower()
    matched: list[tuple[float, JournalMatch]] = []

    for j in _JOURNALS:
        relevance = sum(1 for t in j["tags"] if t.lower() in text_lower or t.lower() in discipline.lower())
        if relevance == 0:
            continue

        # Score-adjusted acceptance probability
        base_acc = j["acc"]
        score_factor = overall_score / 100
        adj_acc = min(0.90, base_acc * (0.5 + score_factor))

        # Scope match
        tag_count = len(j["tags"])
        scope = min(1.0, relevance / max(tag_count * 0.5, 1))

        match = JournalMatch(
            name=j["name"],
            publisher=j["publisher"],
            quartile=j["q"],
            scope_match=round(scope, 3),
            acceptance_probability=round(adj_acc, 3),
            impact_factor=j["if"],
            submission_notes=j["notes"],
            open_access=j["oa"],
        )
        matched.append((scope * adj_acc, match))

    matched.sort(key=lambda x: -x[0])
    results: list[JournalMatch] = [m for _, m in matched[:4]]

    # ── Merge AI recommendations ───────────────────────────────────────────────
    seen = {j.name.lower() for j in results}
    if ai_journal_dicts:
        for jd in ai_journal_dicts:
            name = jd.get("name", "")
            if not name or name.lower() in seen:
                continue
            try:
                q = jd.get("quartile", "Q2")
                if q not in ("Q1", "Q2", "Q3", "Q4"):
                    q = "Q2"
                results.append(JournalMatch(
                    name=name,
                    publisher=jd.get("publisher", ""),
                    quartile=q,
                    scope_match=round(float(jd.get("scope_match", 0.7)), 3),
                    acceptance_probability=round(float(jd.get("acceptance_probability", 0.25)), 3),
                    impact_factor=jd.get("impact_factor"),
                    submission_notes=jd.get("submission_notes", ""),
                    open_access=bool(jd.get("open_access", False)),
                ))
                seen.add(name.lower())
            except (TypeError, ValueError):
                pass

    # Sort final list by Q tier then scope match
    q_order = {"Q1": 0, "Q2": 1, "Q3": 2, "Q4": 3}
    results.sort(key=lambda j: (q_order.get(j.quartile, 9), -j.scope_match))
    return results[:6]
