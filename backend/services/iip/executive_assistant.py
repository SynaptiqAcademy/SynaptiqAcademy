"""
AI Executive Assistant — rule-based synthesis engine that maps institutional
questions to data queries and composes executive-level responses.

Architecture:
  1. Intent classifier: keyword scoring across 9 intent categories
  2. Data fetcher: calls relevant engines based on intent
  3. Response composer: structured natural-language synthesis from data
"""
import asyncio
from datetime import datetime, timezone


# ── Intent classification ─────────────────────────────────────────────────────

_INTENT_KEYWORDS = {
    "funding":       ["fund", "grant", "money", "budget", "finance", "income", "funder", "award", "cost"],
    "faculty":       ["faculty", "researcher", "professor", "staff", "academic", "promo", "hire", "talent", "retire"],
    "publications":  ["publish", "paper", "journal", "article", "q1", "q2", "citation", "impact", "output"],
    "collaboration": ["collaborat", "partner", "network", "international", "joint"],
    "health":        ["health", "score", "indicator", "kpi", "performance", "overview", "status", "how"],
    "risk":          ["risk", "concern", "danger", "threat", "weak", "problem", "issue", "low"],
    "forecast":      ["forecast", "predict", "future", "trend", "next", "project", "grow"],
    "department":    ["department", "faculty", "unit", "school", "division"],
    "strategy":      ["strateg", "priorit", "recomm", "improve", "plan", "action", "roadmap"],
}


def _classify_intent(query: str) -> list[str]:
    q = query.lower()
    scores: dict[str, int] = {}
    for intent, kws in _INTENT_KEYWORDS.items():
        score = sum(1 for kw in kws if kw in q)
        if score > 0:
            scores[intent] = score
    if not scores:
        return ["health"]  # default
    return sorted(scores, key=lambda k: -scores[k])[:3]


# ── Response composer ─────────────────────────────────────────────────────────

def _compose_response(intents: list[str], data: dict, query: str) -> str:
    primary = intents[0] if intents else "health"
    parts = []

    if primary == "health" or "health" in intents:
        h = data.get("health", {})
        score = h.get("score", 0)
        grade = h.get("grade", "N/A")
        fc = h.get("faculty_count", 0)
        low_indicators = [i for i in h.get("indicators", []) if i["value"] < 50]
        parts.append(
            f"Your institution currently scores **{score}/100** (Grade {grade}) across 15 health indicators, "
            f"covering {fc} researchers."
        )
        if low_indicators:
            names = ", ".join(i["label"] for i in low_indicators[:3])
            parts.append(f"The weakest areas requiring attention are: **{names}**.")

    if "risk" in intents or "risk" in primary:
        risks = data.get("risks", [])
        critical = [r for r in risks if r["level"] == "critical"]
        high = [r for r in risks if r["level"] == "high"]
        if critical:
            parts.append(f"⚠ **{len(critical)} critical risk(s)** detected: {', '.join(r['title'] for r in critical[:2])}.")
        if high:
            parts.append(f"**{len(high)} high-priority risk(s)**: {', '.join(r['title'] for r in high[:2])}.")
        if not critical and not high:
            parts.append("No critical or high-priority institutional risks detected at this time.")

    if "funding" in intents or "funding" in primary:
        g = data.get("grants", {})
        fi = data.get("financial", {})
        parts.append(
            f"Grant portfolio: **{g.get('total', 0)} applications** with a "
            f"**{g.get('success_rate', 0):.1f}% success rate**. "
            f"Total approved research income: **€{fi.get('total_research_income', 0):,.0f}**."
        )
        top_funders = g.get("top_funders", [])[:3]
        if top_funders:
            parts.append(f"Top funders: {', '.join(f['funder'] for f in top_funders)}.")
        if fi.get("funding_dependency_risk") == "high":
            parts.append("⚠ Funding concentration is high — diversification is recommended.")

    if "publications" in intents or "publications" in primary:
        p = data.get("publications", {})
        parts.append(
            f"Publication output: **{p.get('total', 0)} total**, "
            f"**{p.get('q1q2_pct', 0):.1f}% in Q1/Q2 journals**, "
            f"**{p.get('avg_citations', 0):.1f} avg citations**. "
            f"Growth: **{p.get('growth_rate_pct', 0):+.1f}%**."
        )

    if "faculty" in intents or "faculty" in primary:
        f = data.get("faculty", {})
        parts.append(
            f"Faculty: **{f.get('total', 0)} researchers**, "
            f"**{f.get('engagement_rate', 0):.1f}% active** (published in past year). "
            f"**{f.get('inactive', 0)} inactive** researchers may need support."
        )

    if "collaboration" in intents:
        c = data.get("collaboration", {})
        parts.append(
            f"Collaboration network: **{c.get('total', 0)} collaborations**, "
            f"**{c.get('international_pct', 0):.1f}% international**. "
            f"Network density: **{c.get('network_density', 0):.4f}**."
        )

    if "strategy" in intents or "strategy" in primary:
        # Generate strategic recommendations from weakest health indicators
        h = data.get("health", {})
        low = sorted(h.get("indicators", []), key=lambda x: x["value"])[:5]
        if low:
            parts.append("**Strategic priorities** based on weakest indicators:")
            for ind in low:
                parts.append(f"• **{ind['label']}** ({ind['value']:.0f}/100): {ind['description']}")

    if not parts:
        parts.append(
            "I can provide insights on institutional health, publications, grants, faculty, "
            "risks, collaborations, forecasts, and strategic recommendations. "
            "Please refine your question or ask about a specific area."
        )

    return "\n\n".join(parts)


# ── Main entry point ──────────────────────────────────────────────────────────

async def ask_assistant(institution: str, query: str, db) -> dict:
    from services.iip.health_engine import compute_health_score
    from services.iip.risk_engine import detect_institutional_risks
    from services.iip.grant_engine import get_grant_overview
    from services.iip.publication_engine import get_publication_overview
    from services.iip.faculty_engine import get_faculty_overview
    from services.iip.collaboration_engine import get_collaboration_overview
    from services.iip.financial_engine import get_financial_overview

    intents = _classify_intent(query)

    # Fetch data relevant to detected intents in parallel
    tasks = {
        "health":        compute_health_score(institution, db),
        "risks":         detect_institutional_risks(institution, db),
        "grants":        get_grant_overview(institution, db),
        "publications":  get_publication_overview(institution, db),
        "faculty":       get_faculty_overview(institution, db),
        "collaboration": get_collaboration_overview(institution, db),
        "financial":     get_financial_overview(institution, db),
    }

    results = await asyncio.gather(*tasks.values(), return_exceptions=True)
    data = {}
    for key, result in zip(tasks.keys(), results):
        data[key] = result if not isinstance(result, Exception) else {}

    response_text = _compose_response(intents, data, query)

    # Persist to conversation history
    record = {
        "institution": institution,
        "query": query,
        "intents": intents,
        "response": response_text,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.iip_ai_conversations.insert_one(record)
    record.pop("_id", None)

    return {
        "query": query,
        "intents": intents,
        "response": response_text,
        "data_summary": {
            "health_score": data.get("health", {}).get("score"),
            "risk_count": len(data.get("risks", [])),
            "grant_success_rate": data.get("grants", {}).get("success_rate"),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


async def get_conversation_history(institution: str, db, limit: int = 20) -> list:
    docs = await db.iip_ai_conversations.find(
        {"institution": institution},
        {"query": 1, "response": 1, "intents": 1, "created_at": 1, "_id": 0},
    ).sort("created_at", -1).limit(limit).to_list(length=limit)
    return docs
