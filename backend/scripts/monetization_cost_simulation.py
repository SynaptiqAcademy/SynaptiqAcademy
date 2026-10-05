"""AI cost & margin simulation for Pro and Pro Advanced.

Uses the SAME configured tables production uses:
  - plans_catalogue.AI_OPERATIONS     (credits per operation, model tier)
  - plans_catalogue.PLANS             (price, monthly credits)
  - plans_catalogue.CREDIT_PACKS      (pack price / credits)
  - services.ai.pricing               (provider prices, model routing;
                                        honours AI_PROVIDER_PRICING_JSON etc.)

Token profiles per operation are ASSUMPTIONS until calibrated from real
telemetry — run with --profiles my_profiles.json to override, and compare
with GET /api/admin/ai/monetization-metrics (by_operation) once traffic exists.

Usage:
    python scripts/monetization_cost_simulation.py [--profiles file.json]
        [--usd-per-eur 1.08] [--vat 0.21] [--json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from plans_catalogue import AI_OPERATIONS, CREDIT_PACKS, get_plan  # noqa: E402
from services.ai.pricing import estimate_cost_usd, model_for_tier  # noqa: E402

DEFAULT_STANDARD_MODEL = "claude-sonnet-4-6"   # feature-registry default model

# (input_tokens, output_tokens) per request — assumptions, see docstring.
TOKEN_PROFILES = {
    "QUICK_ACADEMIC_REWRITE":           (800, 600),
    "RESEARCH_QUESTIONS":               (1_500, 800),
    "ABSTRACT_ANALYSIS":                (1_500, 700),
    "AI_ASSISTANT_SIMPLE":              (3_000, 700),
    "JOURNAL_FIT":                      (6_000, 1_500),
    "CONFERENCE_FIT":                   (6_000, 1_500),
    "GRANT_FIT":                        (6_000, 1_500),
    "MANUSCRIPT_SECTION_REVIEW":        (8_000, 2_500),
    "TEACHING_CONTENT_GENERATION":      (3_000, 3_000),
    "LITERATURE_SYNTHESIS":             (15_000, 3_500),
    "FULL_MANUSCRIPT_REVIEW":           (30_000, 4_000),
    "DEEP_RESEARCH":                    (40_000, 6_000),
    "MULTI_PAPER_SYNTHESIS":            (50_000, 6_000),
    "ADVANCED_MANUSCRIPT_INTELLIGENCE": (60_000, 8_000),
}

# Share of the month's credits a user spends on each operation (by credits).
USAGE_MIXES = {
    "light":   {"spend_ratio": 0.30, "mix": {"AI_ASSISTANT_SIMPLE": 0.5, "QUICK_ACADEMIC_REWRITE": 0.2, "JOURNAL_FIT": 0.3}},
    "typical": {"spend_ratio": 0.75, "mix": {"AI_ASSISTANT_SIMPLE": 0.25, "QUICK_ACADEMIC_REWRITE": 0.05,
                                             "JOURNAL_FIT": 0.15, "MANUSCRIPT_SECTION_REVIEW": 0.2,
                                             "LITERATURE_SYNTHESIS": 0.2, "FULL_MANUSCRIPT_REVIEW": 0.15}},
    "heavy":   {"spend_ratio": 1.00, "mix": {"AI_ASSISTANT_SIMPLE": 0.15, "LITERATURE_SYNTHESIS": 0.25,
                                             "FULL_MANUSCRIPT_REVIEW": 0.3, "DEEP_RESEARCH": 0.15,
                                             "ADVANCED_MANUSCRIPT_INTELLIGENCE": 0.15}},
}

STRIPE_PCT, STRIPE_FIXED_EUR = 0.015, 0.25    # EU card estimate — verify in Stripe


def model_for(op: str) -> str:
    return model_for_tier(AI_OPERATIONS[op]["model_tier"]) or DEFAULT_STANDARD_MODEL


def cost_per_request(op: str, profiles: dict) -> float:
    tin, tout = profiles[op]
    return estimate_cost_usd(model_for(op), tin, tout)


def simulate(plan_code: str, usage: str, profiles: dict, usd_per_eur: float, vat: float) -> dict:
    plan = get_plan(plan_code)
    credits = plan["credits_per_month"] * USAGE_MIXES[usage]["spend_ratio"]
    cost = 0.0
    for op, share in USAGE_MIXES[usage]["mix"].items():
        if plan_code == "researcher" and op in ("DEEP_RESEARCH", "ADVANCED_MANUSCRIPT_INTELLIGENCE"):
            op = "FULL_MANUSCRIPT_REVIEW"   # advanced operations are Pro Advanced features
        n_requests = credits * share / AI_OPERATIONS[op]["credits"]
        cost += n_requests * cost_per_request(op, profiles)
    net_revenue_eur = plan["price_eur_monthly"] / (1 + vat)
    net_revenue_eur -= plan["price_eur_monthly"] * STRIPE_PCT + STRIPE_FIXED_EUR
    cost_eur = cost / usd_per_eur
    return {
        "plan": plan["name"], "usage": usage, "credits_used": round(credits),
        "ai_cost_usd": round(cost, 3), "ai_cost_eur": round(cost_eur, 3),
        "net_revenue_eur": round(net_revenue_eur, 2),
        "gross_margin_eur": round(net_revenue_eur - cost_eur, 2),
        "ai_cost_pct_of_net_revenue": round(100 * cost_eur / net_revenue_eur, 1),
    }


def worst_case(plan_code: str, profiles: dict, usd_per_eur: float) -> dict:
    """All credits spent on the operation with the highest provider cost per credit."""
    allowed = [op for op in AI_OPERATIONS
               if plan_code != "researcher" or op not in ("DEEP_RESEARCH", "ADVANCED_MANUSCRIPT_INTELLIGENCE")]
    per_credit = {op: cost_per_request(op, profiles) / AI_OPERATIONS[op]["credits"] for op in allowed}
    op = max(per_credit, key=per_credit.get)
    credits = get_plan(plan_code)["credits_per_month"]
    return {"plan": get_plan(plan_code)["name"], "worst_operation": op,
            "usd_per_credit": round(per_credit[op], 5),
            "max_monthly_ai_cost_usd": round(credits * per_credit[op], 2),
            "max_monthly_ai_cost_eur": round(credits * per_credit[op] / usd_per_eur, 2)}


def pack_economics(profiles: dict, usd_per_eur: float, vat: float) -> list[dict]:
    worst = max(cost_per_request(op, profiles) / AI_OPERATIONS[op]["credits"] for op in AI_OPERATIONS)
    rows = []
    for p in CREDIT_PACKS:
        net = p["price_eur"] / (1 + vat) - (p["price_eur"] * STRIPE_PCT + STRIPE_FIXED_EUR)
        worst_cost = p["credits"] * worst / usd_per_eur
        rows.append({"pack": p["code"], "price_eur": p["price_eur"], "net_revenue_eur": round(net, 2),
                     "worst_case_ai_cost_eur": round(worst_cost, 2),
                     "worst_case_margin_eur": round(net - worst_cost, 2)})
    return rows


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--profiles")
    ap.add_argument("--usd-per-eur", type=float, default=1.08)
    ap.add_argument("--vat", type=float, default=0.21, help="VAT rate removed from gross price")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    profiles = dict(TOKEN_PROFILES)
    if a.profiles:
        with open(a.profiles) as fh:
            profiles.update({k: tuple(v) for k, v in json.load(fh).items()})

    out = {
        "assumptions": {"usd_per_eur": a.usd_per_eur, "vat": a.vat, "stripe_fee": f"{STRIPE_PCT:.1%} + €{STRIPE_FIXED_EUR}",
                        "token_profiles": "built-in assumptions" if not a.profiles else a.profiles,
                        "models": {op: model_for(op) for op in AI_OPERATIONS}},
        "per_operation": [{"operation": op, "credits": AI_OPERATIONS[op]["credits"], "model": model_for(op),
                           "cost_usd": round(cost_per_request(op, profiles), 4),
                           "usd_per_credit": round(cost_per_request(op, profiles) / AI_OPERATIONS[op]["credits"], 5)}
                          for op in AI_OPERATIONS],
        "scenarios": [simulate(p, u, profiles, a.usd_per_eur, a.vat)
                      for p in ("researcher", "pro_researcher") for u in ("light", "typical", "heavy")],
        "worst_case": [worst_case(p, profiles, a.usd_per_eur) for p in ("researcher", "pro_researcher")],
        "credit_packs": pack_economics(profiles, a.usd_per_eur, a.vat),
    }
    if a.json:
        print(json.dumps(out, indent=2))
        return
    print("Per operation (provider cost per request):")
    for r in out["per_operation"]:
        print(f"  {r['operation']:34s} {r['credits']:3d} cr  {r['model']:28s} ${r['cost_usd']:.4f}  (${r['usd_per_credit']:.5f}/credit)")
    print("\nScenarios (monthly, per user):")
    for r in out["scenarios"]:
        print(f"  {r['plan']:13s} {r['usage']:8s} credits={r['credits_used']:4d}  AI cost €{r['ai_cost_eur']:6.2f}"
              f"  net revenue €{r['net_revenue_eur']:6.2f}  margin €{r['gross_margin_eur']:6.2f}"
              f"  ({r['ai_cost_pct_of_net_revenue']}% of net)")
    print("\nWorst case (all credits on the costliest operation per credit):")
    for r in out["worst_case"]:
        print(f"  {r['plan']:13s} {r['worst_operation']:34s} max AI cost €{r['max_monthly_ai_cost_eur']:.2f}/month")
    print("\nCredit packs (worst-case usage):")
    for r in out["credit_packs"]:
        print(f"  {r['pack']:9s} €{r['price_eur']:6.2f}  net €{r['net_revenue_eur']:6.2f}"
              f"  worst AI cost €{r['worst_case_ai_cost_eur']:6.2f}  margin €{r['worst_case_margin_eur']:6.2f}")
    print("\nAssumptions: token profiles are estimates; prices from services/ai/pricing.py "
          "(verify AI_PROVIDER_PRICING_JSON). Calibrate with /api/admin/ai/monetization-metrics.")


if __name__ == "__main__":
    main()
