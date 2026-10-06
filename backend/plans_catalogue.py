"""Plan catalogue, credit cost catalogue, and credit-pack catalogue.

Single source of truth for monetisation. Loaded by:
- routers/billing.py (public pricing)
- routers/credits.py (cost transparency)
- services/credits_service.py (consume/refund)
- seed.py (DB upsert)

Internal plan codes are stable identifiers that existing users, subscriptions
and audit history already carry, so they are NOT renamed. Customer tiers:
    free           -> FREE
    researcher     -> PRO           ("Pro")
    pro_researcher -> PRO_ADVANCED  ("Pro Advanced")
institution / enterprise are legacy, non-self-serve codes and receive
PRO_ADVANCED capabilities (see TIER_BY_PLAN).
"""
import json
import logging
import os

_log = logging.getLogger("synaptiq.plans_catalogue")

# =====================================================================
# Subscription plans
# =====================================================================
PLANS = [
    {
        # FREE is identity only (owner decision, monetization spec §FREE):
        # profile, public research page, ORCID + publication import, and being
        # discoverable to paid researchers. No AI, no credits, no general
        # storage, no projects/workspaces, no messaging/collaboration, no
        # discovery. Enforced server-side by services/entitlements.py.
        "code": "free",
        "name": "Free",
        "tagline": "Build your academic presence",
        "price_eur_monthly": 0,
        "price_eur_annual": 0,
        "future_price_eur_monthly": None,
        "badge": None,
        "credits_per_month": 0,
        "limits": {
            "active_projects": 0,
            "workspaces": 0,
            "repository_gb": 0,
            "team_seats": 1,
            "journal_recs_per_month": 0,
            "conference_recs_per_month": 0,
            "grant_recs_per_month": 0,
        },
        "price_label": "Forever",
        "features": [
            "Academic profile",
            "Public research page",
            "ORCID integration",
            "Publication import from ORCID",
        ],
        "excluded": [
            "AI tools and AI credits",
            "Messaging and collaboration requests",
            "Projects and workspaces",
            "Journal, conference and grant discovery",
            "Analytics",
        ],
        "cta": "Create Free Profile",
        "stripe_price_id_monthly": "",
        "stripe_price_id_annual": "",
    },
    {
        # Backend code stays "researcher" — entitlement logic, quotas, and
        # FEATURE_MIN_PLAN all key off this and are unchanged. "name" is the
        # canonical customer-facing display name (already the established
        # pattern via get_plan(code)["name"] — see credits_service.py,
        # services/permissions.py::access_summary) — renamed per the owner's
        # Phase 9A commercial decision: a subscription tier describes
        # product access, not a professional identity.
        "code": "researcher",
        "name": "Pro",
        "key": "pro",
        "tagline": "For active researchers who want to collaborate, publish and work with AI.",
        "price_eur_monthly": 9.99,
        "price_eur_annual": 7.99,
        "future_price_eur_monthly": 14.99,
        "badge": "Early Access",
        "recommended": True,
        "credits_per_month": 200,
        "limits": {
            "active_projects": -1,
            "workspaces": 10,
            "repository_gb": 10,
            "team_seats": 1,
            "journal_recs_per_month": -1,
            "conference_recs_per_month": -1,
            "grant_recs_per_month": -1,
        },
        "features": [
            "Everything in Free",
            "Research network & researcher matching",
            "Direct messaging & collaboration",
            "Unlimited projects",
            "10 workspaces",
            "10 GB storage",
            "Journal, conference & grant discovery",
            "AI Research Assistant",
            "Manuscript Copilot",
            "Teaching Hub",
            "Publication tracking",
            "Research analytics",
            # "Priority support" is not listed: there is no support queue or
            # routing behind it yet. Re-add once it has an operational meaning.
        ],
        "excluded": [],
        "cta": "Choose Pro",
        # Stripe price ids come from the environment only — never hardcoded.
        "stripe_price_id_monthly": os.environ.get("STRIPE_PRICE_PRO_MONTHLY", ""),
        # Older prices of this plan still recognised on webhooks (e.g. the
        # €9.99 Early Access price after a future €14.99 price becomes the
        # default for new subscribers). Comma-separated env list.
        "stripe_price_ids_legacy": [x.strip() for x in os.environ.get("STRIPE_PRICE_PRO_LEGACY_IDS", "").split(",") if x.strip()],
        "stripe_price_id_annual": "",   # annual billing is not offered
    },
    {
        # Backend code stays "pro_researcher" — see note on "researcher" above.
        "code": "pro_researcher",
        "name": "Pro Advanced",
        "key": "pro_advanced",
        "tagline": "For researchers who need advanced intelligence, analytics and research impact tools.",
        "price_eur_monthly": 29.99,
        "price_eur_annual": 23.99,
        "future_price_eur_monthly": None,
        "badge": None,
        "credits_per_month": 750,
        "limits": {
            "active_projects": -1,
            "workspaces": -1,
            "repository_gb": 50,
            "team_seats": 1,
            "journal_recs_per_month": -1,
            "conference_recs_per_month": -1,
            "grant_recs_per_month": -1,
        },
        "features": [
            "Everything in Pro",
            "Unlimited workspaces",
            "50 GB storage",
            # The Advanced AI Research Assistant, as implemented: the four
            # Pro Advanced research tools (FEATURE_MIN_PLAN) ...
            "Literature review, research gap finder, study design advisor and statistical review",
            # ... and extended context (services/ai/pricing.py guards:
            # 150k vs 60k input tokens, 8k vs 4k output).
            "Larger AI requests: about 112,000 words instead of 45,000",
            "Collaboration Intelligence",
            "Research Impact Dashboard",
            "Citation Monitoring",
            # Not listed until they exist as working features: Priority AI
            # processing, Advanced Research Analytics, Advanced Manuscript
            # Intelligence (API only, no screen), Advanced AI Teaching Tools,
            # Priority support.
        ],
        "excluded": [],
        "cta": "Choose Pro Advanced",
        "stripe_price_id_monthly": os.environ.get("STRIPE_PRICE_PRO_ADVANCED_MONTHLY", ""),
        "stripe_price_ids_legacy": [x.strip() for x in os.environ.get("STRIPE_PRICE_PRO_ADVANCED_LEGACY_IDS", "").split(",") if x.strip()],
        "stripe_price_id_annual": "",   # annual billing is not offered
    },
    {
        # No self-service checkout (§7) — institution access is granted only
        # via real organization membership, never a purchasable plan_code
        # on an individual account (see services/permissions.py's
        # require_institution_member). price_eur_monthly/annual are kept as
        # an internal/sales reference only — never render them publicly
        # (frontend already doesn't; this is what would leak if a future
        # caller ever rendered plan.price_eur_monthly generically for every
        # plan without institution's existing special-case).
        "code": "institution",
        "name": "Institutional",
        "tagline": "For universities, research institutions and organizations",
        "price_eur_monthly": 299,
        "price_eur_annual": 239,
        "future_price_eur_monthly": None,
        "badge": None,
        "credits_per_month": 20000,
        "limits": {
            "active_projects": -1,
            "workspaces": -1,
            "repository_gb": 2048,
            "team_seats": 25,
            "journal_recs_per_month": -1,
            "conference_recs_per_month": -1,
            "grant_recs_per_month": -1,
        },
        # Public-facing description of the organization product — real,
        # membership-based capabilities only. Seat count, credits and storage
        # are set per agreement (Custom / Contact Sales), so fixed numbers
        # aren't advertised here; the limits dict above remains the internal
        # reference for this legacy plan_code.
        "features": [
            "Approved membership: institutional email, invitation or admin review",
            "Departments with their own admins and coordinators",
            "Member directory by research area",
            "Admin roles and an activity log of admin actions",
        ],
        "excluded": [],
        "cta": "Contact Sales",
        "stripe_price_id_monthly": "",
        "stripe_price_id_annual": "",
    },
    {
        "code": "enterprise",
        "name": "Enterprise",
        "tagline": "Universities, governments & large research networks",
        "price_eur_monthly": 0,           # custom — contact sales
        "price_eur_annual": 0,            # custom — contract-negotiated
        "future_price_eur_monthly": None,
        "badge": "Contact Sales",
        "credits_per_month": -1,          # unlimited
        "limits": {
            "active_projects": -1,
            "workspaces": -1,
            "repository_gb": -1,          # unlimited / custom quota
            "team_seats": -1,             # unlimited / site license
            "journal_recs_per_month": -1,
            "conference_recs_per_month": -1,
            "grant_recs_per_month": -1,
        },
        "features": [
            "Unlimited Research Credits",
            "Unlimited Users (Site License)",
            "Unlimited Projects & Workspaces",
            "Unlimited Repository Storage",
            "Full Institutional Analytics Suite",
            "Department & Faculty Management",
            "Dedicated Account Manager",
            "SLA-backed Support (99.9% uptime)",
            "SSO / SAML / LDAP Integration",
            "Custom Data Retention & GDPR DPA",
            "On-premise / Private Cloud Option",
            "Custom AI Models & Integrations",
            "Compliance Exports (GDPR, ISO 27001, SOC2)",
            "Annual Licensing & Multi-year Contracts",
        ],
        "excluded": [],
        "cta": "Contact Sales",
        "stripe_price_id_monthly": "",    # fulfilled via custom Stripe invoices
        "stripe_price_id_annual": "",
        "contact_sales": True,            # front-end renders "Contact Sales" CTA
        "custom_pricing": True,
    },
]


# =====================================================================
# AI operation catalogue — the customer-facing credit price list
# =====================================================================
# Server-side only; the frontend reads it from /api/billing/credit-usage-catalogue
# and never hardcodes costs. Each operation can be overridden at deploy time
# with AI_OPERATION_COSTS_JSON='{"JOURNAL_FIT": 6}' (positive ints only).
# `model_tier` drives cost-aware routing (services/ai/pricing.py):
#   simple   -> cheapest configured model
#   standard -> default model
#   advanced -> default model with extended context/output budget
AI_OPERATIONS: dict[str, dict] = {
    "QUICK_ACADEMIC_REWRITE":           {"credits": 1,  "label": "Quick academic rewrite",            "model_tier": "simple"},
    "RESEARCH_QUESTIONS":               {"credits": 2,  "label": "Research question generation",      "model_tier": "simple"},
    "ABSTRACT_ANALYSIS":                {"credits": 2,  "label": "Abstract analysis",                 "model_tier": "simple"},
    "AI_ASSISTANT_SIMPLE":              {"credits": 2,  "label": "AI assistant message",              "model_tier": "simple"},
    "JOURNAL_FIT":                      {"credits": 5,  "label": "Journal fit analysis",              "model_tier": "standard"},
    "CONFERENCE_FIT":                   {"credits": 5,  "label": "Conference fit analysis",           "model_tier": "standard"},
    "GRANT_FIT":                        {"credits": 5,  "label": "Grant fit analysis",                "model_tier": "standard"},
    "MANUSCRIPT_SECTION_REVIEW":        {"credits": 10, "label": "Manuscript section review",         "model_tier": "standard"},
    "TEACHING_CONTENT_GENERATION":      {"credits": 10, "label": "Teaching content generation",       "model_tier": "standard"},
    "LITERATURE_SYNTHESIS":             {"credits": 15, "label": "Literature synthesis",              "model_tier": "standard"},
    "FULL_MANUSCRIPT_REVIEW":           {"credits": 30, "label": "Full manuscript review",            "model_tier": "advanced"},
    "DEEP_RESEARCH":                    {"credits": 40, "label": "Deep research",                     "model_tier": "advanced"},
    "MULTI_PAPER_SYNTHESIS":            {"credits": 40, "label": "Multi-paper synthesis",             "model_tier": "advanced"},
    "ADVANCED_MANUSCRIPT_INTELLIGENCE": {"credits": 50, "label": "Advanced manuscript intelligence",  "model_tier": "advanced"},
}


def _apply_operation_cost_overrides() -> None:
    raw = os.environ.get("AI_OPERATION_COSTS_JSON", "").strip()
    if not raw:
        return
    try:
        overrides = json.loads(raw)
    except ValueError:
        _log.error("AI_OPERATION_COSTS_JSON is not valid JSON — ignored")
        return
    for op, cost in (overrides or {}).items():
        if op in AI_OPERATIONS and isinstance(cost, int) and not isinstance(cost, bool) and cost > 0:
            AI_OPERATIONS[op]["credits"] = cost
        else:
            _log.error("AI_OPERATION_COSTS_JSON: ignored invalid entry %r=%r", op, cost)


_apply_operation_cost_overrides()


# Existing call sites charge by a feature "action" key (100+ call sites).
# Rather than rewrite them, each action that corresponds to a catalogue
# operation is priced BY that operation, so one table sets every price.
ACTION_OPERATION: dict[str, str] = {
    "ai_rewriting":               "QUICK_ACADEMIC_REWRITE",
    "ai_citation_generation":     "QUICK_ACADEMIC_REWRITE",
    "copilot_suggestions":        "QUICK_ACADEMIC_REWRITE",
    "ai_abstract_generator":      "ABSTRACT_ANALYSIS",
    "ai_research_assistant":      "AI_ASSISTANT_SIMPLE",
    "ai_chat_message":            "AI_ASSISTANT_SIMPLE",   # Manuscript Copilot message
    "ai_teaching_assistant":      "AI_ASSISTANT_SIMPLE",
    "ai_os_message":              "AI_ASSISTANT_SIMPLE",
    "copilot_chat":               "AI_ASSISTANT_SIMPLE",
    "copilot_dashboard":          "AI_ASSISTANT_SIMPLE",
    "research_need_interpret":    "RESEARCH_QUESTIONS",
    "ai_journal_matching":        "JOURNAL_FIT",
    "publishing_journal_match":   "JOURNAL_FIT",
    "publishing_journal_analyse": "JOURNAL_FIT",
    "ai_conference_matching":     "CONFERENCE_FIT",
    "publishing_conference_match": "CONFERENCE_FIT",
    "ai_grant_matching":          "GRANT_FIT",
    "publishing_grant_match":     "GRANT_FIT",
    "ai_methodology_builder":     "MANUSCRIPT_SECTION_REVIEW",
    "ai_methodology_assistance":  "MANUSCRIPT_SECTION_REVIEW",
    "ai_research_design_advisor": "MANUSCRIPT_SECTION_REVIEW",
    "ai_statistical_review":      "MANUSCRIPT_SECTION_REVIEW",
    "ai_lesson_plan_generate":    "TEACHING_CONTENT_GENERATION",
    "ai_assessment_generate":     "TEACHING_CONTENT_GENERATION",
    "ai_literature_review":       "LITERATURE_SYNTHESIS",
    "ai_literature_synthesis":    "LITERATURE_SYNTHESIS",
    "ai_research_gap_finder":     "LITERATURE_SYNTHESIS",
    "ai_collaboration_intelligence": "LITERATURE_SYNTHESIS",
    "ai_manuscript_review":       "FULL_MANUSCRIPT_REVIEW",
}


# Actions with no catalogue operation keep a per-action price. These are
# secondary/experimental engines (knowledge graph, career, prediction, …);
# they are still credit-billed and entitlement-gated like everything else.
_LEGACY_ACTION_COSTS = {
    "team_blueprint_generate":   5,
    "copilot_roadmap":            5,
    # Publishing Intelligence (Phase XII)
    "publishing_readiness_check": 2,
    "publishing_cover_letter":    4,
    "publishing_reviewer_response":4,
    "publishing_strategy":        5,
    "publishing_risk_analysis":   3,
    "publishing_dashboard":       2,
    "publishing_export":          2,
    # Autonomous Research Agents (Phase XIII)
    "agents_workflow_run":        8,
    "agents_task_run":            6,
    "agents_single_run":          2,
    "agents_parallel_run":        4,
    # Research Collaboration Intelligence (Phase XIV)
    "collab_match":               3,
    "collab_rank":                4,
    "collab_opportunities":       4,
    "collab_team_build":          6,
    "collab_team_simulate":       4,
    "collab_introduction":        2,
    "collab_network":             5,
    "collab_prediction":          3,
    "collab_recommendations":     4,
    "collab_social_graph":        5,
    # Institution Intelligence Engine (Phase XV)
    "institution_profile":        3,
    "institution_kpis":           2,
    "institution_organizational": 4,
    "institution_predict":        5,
    "institution_resources":      4,
    "institution_talent":         4,
    "institution_portfolio":      3,
    "institution_benchmark":      3,
    "institution_risks":          3,
    "institution_recommendations":5,
    "institution_monitor":        2,
    "institution_knowledge_graph":4,
    "institution_visualization":  2,
    "institution_export":         5,
    "institution_full_analysis":  10,
    # Phase XVI — Academic Career Intelligence Engine
    "career_profile":            2,
    "career_roadmap":            5,
    "career_goals":              3,
    "career_skill_gaps":         4,
    "career_promotion":          5,
    "career_productivity":       3,
    "career_risks":              4,
    "career_recommendations":    3,
    "career_copilot":            2,
    "career_visualization":      2,
    "career_export":             5,
    "career_full_analysis":      12,
    # Knowledge Graph (Phase XVII)
    "kg_import":                 10,
    "kg_add_node":                1,
    "kg_add_edge":                1,
    "kg_stats":                   1,
    "kg_analytics":               5,
    "kg_communities":             5,
    "kg_embeddings":              3,
    "kg_reasoning":               6,
    "kg_discovery":               4,
    "kg_query":                   3,
    "kg_visualization":           3,
    "kg_copilot":                 4,
    # Prediction & Forecasting Intelligence (Phase XVIII)
    "prediction_publication":     6,
    "prediction_journal_ranking": 5,
    "prediction_conference":      4,
    "prediction_grant":           8,
    "prediction_career_forecast": 7,
    "prediction_collaboration":   5,
    "prediction_institution":     8,
    "prediction_trend":           5,
    "prediction_strategic":       4,
    "prediction_scenario":        8,
    "prediction_what_if":         4,
    "prediction_visualization":   2,
    "prediction_copilot":         3,
    # Self-Improving Academic Intelligence Platform (Phase XX)
    "si_query":       2,
    "si_diagnostics": 2,
    "si_benchmark":   5,
    "si_experiment":  3,
    "si_optimize":    4,
    "si_copilot":     2,
    # Academic OS (Phase XXI)
    "aos_workflow":   5,
    "aos_project":    2,
    "aos_search":     2,
    "aos_dashboard":  1,
    "aos_automation": 3,
    # Free actions (logged but never deducted)
    "researcher_discovery":       0,
    "profile_creation":           0,
    "collaboration_request":      0,
    # Matching aliases with no catalogue operation
    "ai_reviewer_matching":       5,
    "ai_collaborator_matching":   5,
    "ai_marketplace_rerank":      5,
}


def _build_credit_costs() -> dict[str, int]:
    costs = dict(_LEGACY_ACTION_COSTS)
    for action, op in ACTION_OPERATION.items():
        costs[action] = AI_OPERATIONS[op]["credits"]
    # Operation codes are valid action keys themselves, for new call sites.
    for op, meta in AI_OPERATIONS.items():
        costs[op] = meta["credits"]
    return costs


CREDIT_COSTS: dict[str, int] = _build_credit_costs()


def operation_for_action(action: str) -> str | None:
    """Catalogue operation an action is priced by (None for legacy actions)."""
    if action in AI_OPERATIONS:
        return action
    return ACTION_OPERATION.get(action)


# Display rows for the pricing page and the in-app credit catalogue —
# generated from AI_OPERATIONS so there is exactly one price list.
CREDIT_USAGE_DISPLAY = [
    {"operation": op, "label": meta["label"], "cost": meta["credits"], "unit": "per request", "free": False}
    for op, meta in sorted(AI_OPERATIONS.items(), key=lambda kv: (kv[1]["credits"], kv[0]))
]


# =====================================================================
# Feature gating — what each plan unlocks
# =====================================================================
# Use a stable string key. Endpoints declare `require_feature("ai_assistant")`.
# Mapping kept tight; expand without code changes by adding rows.
FEATURE_MIN_PLAN = {
    # Free — identity only
    "academic_profile":            "free",
    "orcid":                       "free",
    "public_profile":              "free",
    # Pro+ (Free is identity only — no network, messaging, collaboration,
    # projects, workspaces, discovery or AI)
    "network":                     "researcher",
    "messaging":                   "researcher",
    "basic_discovery":             "researcher",
    "project_create":              "researcher",   # respects per-plan quota
    "workspace_create":            "researcher",   # respects per-plan quota
    "collaboration_request":       "researcher",
    "teaching_hub":                "researcher",
    "credit_purchase":             "researcher",
    "ai_assistant":                "researcher",
    "ai_manuscript_copilot":       "researcher",
    "publication_tracking":        "researcher",
    "advanced_analytics":          "researcher",   # standard research analytics page
    "full_discovery":              "researcher",
    "ai_journal_matching":         "researcher",
    "ai_conference_matching":      "researcher",
    "ai_grant_matching":           "researcher",
    "ai_manuscript_review":        "researcher",
    "ai_methodology_builder":      "researcher",
    "ai_research_assistant":       "researcher",
    "ai_rewriting":                "researcher",
    "ai_abstract_generator":       "researcher",
    # Pro Advanced+
    "ai_advanced_assistant":       "pro_researcher",
    "ai_literature_review":        "pro_researcher",
    "ai_statistical_review":       "pro_researcher",
    "ai_research_design_advisor":  "pro_researcher",
    "ai_research_gap_finder":      "pro_researcher",
    "collaboration_intelligence":  "pro_researcher",
    "research_analytics_suite":    "pro_researcher",   # "Advanced Analytics"
    "citation_monitoring":         "pro_researcher",
    "research_impact_dashboard":   "pro_researcher",
    "premium_collaboration":       "pro_researcher",
    "advanced_manuscript_intelligence": "pro_researcher",
    "advanced_ai_teaching":        "pro_researcher",
    # Institution
    "sso":                         "institution",
    "governance_console":          "institution",
    "institutional_analytics":     "institution",
    "department_management":       "institution",
}


# Per-plan resource quotas (centralised for assert_quota checks).
# -1 = unlimited, 0 = not available on this plan.
PLAN_QUOTAS = {
    "free":           {"projects": 0,  "workspaces": 0,  "manuscripts": 0},
    "researcher":     {"projects": -1, "workspaces": 10, "manuscripts": -1},
    "pro_researcher": {"projects": -1, "workspaces": -1, "manuscripts": -1},
    "institution":    {"projects": -1, "workspaces": -1, "manuscripts": -1},
    "enterprise":     {"projects": -1, "workspaces": -1, "manuscripts": -1},
}

_GB = 1024 * 1024 * 1024

# Per-plan general storage limits in bytes. Must match PLANS[].limits.repository_gb.
# Free has no general storage: profile photo / ORCID data are not counted
# against this (they are not stored in the `files` collection).
STORAGE_LIMITS_BYTES: dict[str, int] = {
    "free":           0,
    "researcher":     10 * _GB,
    "pro_researcher": 50 * _GB,
    "institution":    2048 * _GB,   # legacy contract plan — unchanged
    "enterprise":     -1,           # contract-defined
}


# Ordered tier rank — used by require_plan / has_plan_at_least.
PLAN_RANK = {"free": 0, "researcher": 1, "pro_researcher": 2, "institution": 3, "enterprise": 4}


# =====================================================================
# Customer tiers and capability entitlements
# =====================================================================
TIER_FREE, TIER_PRO, TIER_PRO_ADVANCED = "FREE", "PRO", "PRO_ADVANCED"

TIER_BY_PLAN = {
    "free":           TIER_FREE,
    "researcher":     TIER_PRO,
    "pro_researcher": TIER_PRO_ADVANCED,
    "institution":    TIER_PRO_ADVANCED,   # legacy, non-self-serve
    "enterprise":     TIER_PRO_ADVANCED,   # legacy, non-self-serve
}

# Boolean capabilities per tier. The backend is authoritative; the frontend
# only mirrors these (GET /api/permissions/me) to decide what to render.
_PRO_CAPS = {
    "can_use_research_network":         True,
    "can_discover_researchers":         True,
    "can_message_researchers":          True,
    "can_send_collaboration_request":   True,
    "can_accept_collaboration":         True,
    "can_join_collaboration_workflows": True,
    "can_create_project":               True,
    "can_create_workspace":             True,
    "can_use_journal_discovery":        True,
    "can_use_conference_discovery":     True,
    "can_use_grant_discovery":          True,
    "can_use_research_assistant":       True,
    "can_use_manuscript_copilot":       True,
    "can_use_teaching_hub":             True,
    "can_use_teaching_ai":              True,
    "can_use_publication_tracking":     True,
    "can_view_research_analytics":      True,
    "can_purchase_ai_credits":          True,
    "can_use_collaboration_intelligence": False,
    "can_use_citation_monitoring":      False,
    "can_view_impact_dashboard":        False,
    "can_view_advanced_analytics":      False,
    "can_use_advanced_ai":              False,
    "can_use_advanced_manuscript_intelligence": False,
    "can_use_advanced_teaching_ai":     False,
}
TIER_CAPABILITIES: dict[str, dict[str, bool]] = {
    TIER_FREE: {k: False for k in _PRO_CAPS},
    TIER_PRO: dict(_PRO_CAPS),
    TIER_PRO_ADVANCED: {k: True for k in _PRO_CAPS},
}
# Identity capabilities every tier has.
for _caps in TIER_CAPABILITIES.values():
    _caps.update({
        "can_edit_academic_profile": True,
        "can_publish_public_profile": True,
        "can_connect_orcid": True,
        "can_import_orcid_publications": True,
        "can_receive_collaboration_invites": True,
    })
CAPABILITIES = sorted(TIER_CAPABILITIES[TIER_PRO_ADVANCED])

# Capability -> FEATURE_MIN_PLAN key used for per-user admin overrides, so an
# admin grant of e.g. "citation_monitoring" also unlocks the capability.
CAPABILITY_FEATURE = {
    "can_use_research_network":         "network",
    "can_discover_researchers":         "network",
    "can_message_researchers":          "messaging",
    "can_send_collaboration_request":   "collaboration_request",
    "can_accept_collaboration":         "collaboration_request",
    "can_join_collaboration_workflows": "collaboration_request",
    "can_create_project":               "project_create",
    "can_create_workspace":             "workspace_create",
    "can_use_journal_discovery":        "basic_discovery",
    "can_use_conference_discovery":     "basic_discovery",
    "can_use_grant_discovery":          "basic_discovery",
    "can_use_research_assistant":       "ai_research_assistant",
    "can_use_manuscript_copilot":       "ai_manuscript_copilot",
    "can_use_teaching_hub":             "teaching_hub",
    "can_use_teaching_ai":              "teaching_hub",
    "can_use_publication_tracking":     "publication_tracking",
    "can_view_research_analytics":      "advanced_analytics",
    "can_purchase_ai_credits":          "credit_purchase",
    "can_use_collaboration_intelligence": "collaboration_intelligence",
    "can_use_citation_monitoring":      "citation_monitoring",
    "can_view_impact_dashboard":        "research_impact_dashboard",
    "can_view_advanced_analytics":      "research_analytics_suite",
    "can_use_advanced_ai":              "ai_advanced_assistant",
    "can_use_advanced_manuscript_intelligence": "advanced_manuscript_intelligence",
    "can_use_advanced_teaching_ai":     "advanced_ai_teaching",
}

# Minimum plan code that grants a capability (for upgrade prompts).
def capability_min_plan(capability: str) -> str:
    for code in ("free", "researcher", "pro_researcher"):
        if TIER_CAPABILITIES[TIER_BY_PLAN[code]].get(capability):
            return code
    return "pro_researcher"


# =====================================================================
# Credit packs — one-time purchases for paid plans; purchased credits
# never expire, but can only be used while on a paid plan.
# =====================================================================
# Prices are configurable (CREDIT_PACK_PRICES_JSON='{"pack_100": 4.99}');
# Stripe price ids come only from the environment.
CREDIT_PACKS = [
    # code = stable internal id (stored on purchases); key = what the browser sends.
    {"code": "pack_100", "key": "small", "name": "AI Small", "credits": 100, "price_eur": 4.99,
     "label": "100 AI Credits", "stripe_price_id": os.environ.get("STRIPE_PRICE_CREDITS_100", "")},
    {"code": "pack_300", "key": "plus", "name": "AI Plus", "credits": 300, "price_eur": 11.99,
     "label": "300 AI Credits", "stripe_price_id": os.environ.get("STRIPE_PRICE_CREDITS_300", "")},
    {"code": "pack_750", "key": "max", "name": "AI Max", "credits": 750, "price_eur": 24.99,
     "label": "750 AI Credits", "stripe_price_id": os.environ.get("STRIPE_PRICE_CREDITS_750", "")},
]


def _apply_pack_price_overrides() -> None:
    raw = os.environ.get("CREDIT_PACK_PRICES_JSON", "").strip()
    if not raw:
        return
    try:
        overrides = json.loads(raw)
    except ValueError:
        _log.error("CREDIT_PACK_PRICES_JSON is not valid JSON — ignored")
        return
    for pack in CREDIT_PACKS:
        v = (overrides or {}).get(pack["code"])
        if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0:
            pack["price_eur"] = float(v)


_apply_pack_price_overrides()


def get_plan(code: str) -> dict:
    for p in PLANS:
        if p["code"] == code:
            return p
    return PLANS[0]


def get_credit_cost(key: str, default: int = 0) -> int:
    return CREDIT_COSTS.get(key, default)


def get_credit_pack(code: str) -> dict | None:
    """Resolve a pack by internal code (pack_100) or public key (small/plus/max).
    Anything else — including a Stripe price id or an amount — resolves to None."""
    for p in CREDIT_PACKS:
        if code and code in (p["code"], p["key"]):
            return p
    return None


# Public plan keys the browser may send -> internal plan codes.
PLAN_KEY_TO_CODE = {"pro": "researcher", "pro_advanced": "pro_researcher",
                    "researcher": "researcher", "pro_researcher": "pro_researcher"}


def get_plan_by_price_id(stripe_price_id: str) -> tuple[str, str] | None:
    """Resolve (plan_code, billing_period) from a Stripe price id.

    Used by the Stripe webhook to determine which plan a subscription
    belongs to without depending on Checkout Session metadata surviving
    onto the Subscription object (Stripe does not copy it there by default).
    """
    if not stripe_price_id:
        return None
    for p in PLANS:
        if p.get("stripe_price_id_monthly") == stripe_price_id:
            return p["code"], "monthly"
        if stripe_price_id in (p.get("stripe_price_ids_legacy") or []):
            return p["code"], "monthly"
        if p.get("stripe_price_id_annual") == stripe_price_id:
            return p["code"], "annual"
    return None


# =====================================================================
# Feature comparison matrix (per spec)
# =====================================================================
# Tuple shape: (label, free_value, researcher_value, pro_value, institution_value)
# Use True/False booleans or strings; the frontend renders them uniformly.
def _credits_label(code: str) -> str:
    """Credit allocation for the matrix, derived from PLANS — never a second
    hardcoded copy that can drift from credits_per_month (§13)."""
    n = next((p["credits_per_month"] for p in PLANS if p["code"] == code), 0)
    return "Unlimited" if n == -1 else f"{n:,}"


def _storage_label(code: str) -> str:
    n = STORAGE_LIMITS_BYTES.get(code, 0)
    if n == -1:
        return "Custom"
    if n == 0:
        return "Profile only"
    gb = n // _GB
    return f"{gb // 1024} TB" if gb >= 1024 and gb % 1024 == 0 else f"{gb} GB"


def _quota_label(code: str, resource: str) -> str:
    n = PLAN_QUOTAS[code][resource]
    return "Unlimited" if n == -1 else ("—" if n == 0 else str(n))


_MATRIX_PLANS = ("free", "researcher", "pro_researcher", "institution", "enterprise")


def _cap_row(label: str, capability: str):
    return (label, *(TIER_CAPABILITIES[TIER_BY_PLAN[c]].get(capability, False) for c in _MATRIX_PLANS))


# Columns: free, researcher (Pro), pro_researcher (Pro Advanced), institution, enterprise.
# Every quantitative row is DERIVED from the canonical tables above, and every
# capability row from TIER_CAPABILITIES — no second hardcoded copy to drift.
FEATURE_MATRIX = [
    ("AI Credits / month", *(_credits_label(c) for c in _MATRIX_PLANS)),
    ("Projects", *(_quota_label(c, "projects") for c in _MATRIX_PLANS)),
    ("Workspaces", *(_quota_label(c, "workspaces") for c in _MATRIX_PLANS)),
    ("Storage", *(_storage_label(c) for c in _MATRIX_PLANS)),
    ("Academic profile & public research page", True, True, True, True, True),
    ("ORCID integration & publication import", True, True, True, True, True),
    ("Can be found by Pro members", True, True, True, True, True),
    _cap_row("Research network, discovery & matching", "can_use_research_network"),
    _cap_row("Messaging", "can_message_researchers"),
    _cap_row("Send & accept collaboration requests", "can_send_collaboration_request"),
    _cap_row("Journal, conference & grant discovery", "can_use_journal_discovery"),
    _cap_row("AI Research Assistant", "can_use_research_assistant"),
    _cap_row("Manuscript Copilot", "can_use_manuscript_copilot"),
    _cap_row("Teaching Hub", "can_use_teaching_hub"),
    _cap_row("Publication tracking", "can_use_publication_tracking"),
    _cap_row("Research analytics", "can_view_research_analytics"),
    _cap_row("Buy extra AI credits", "can_purchase_ai_credits"),
    _cap_row("Advanced research tools & larger AI requests", "can_use_advanced_ai"),
    _cap_row("Collaboration Intelligence", "can_use_collaboration_intelligence"),
    _cap_row("Impact Dashboard", "can_view_impact_dashboard"),
    _cap_row("Citation Monitoring", "can_use_citation_monitoring"),
    # Not listed until they exist as working features (capability flags only,
    # no screen or behaviour yet): Advanced Analytics, Advanced Manuscript
    # Intelligence, Advanced AI Teaching, Priority support / Priority AI.
]

# Comparison grouping for the pricing page (by what the person wants to do).
FEATURE_MATRIX_GROUPS = {
    "Academic profile & public research page": "Identity",
    "ORCID integration & publication import": "Identity",
    "Can be found by Pro members": "Identity",
    "Research network, discovery & matching": "Network & collaboration",
    "Messaging": "Network & collaboration",
    "Send & accept collaboration requests": "Network & collaboration",
    "Collaboration Intelligence": "Network & collaboration",
    "Projects": "Research work",
    "Workspaces": "Research work",
    "Storage": "Research work",
    "Journal, conference & grant discovery": "Discovery",
    "AI Credits / month": "AI",
    "AI Research Assistant": "AI",
    "Manuscript Copilot": "AI",
    "Advanced research tools & larger AI requests": "AI",
    "Buy extra AI credits": "AI",
    "Publication tracking": "Impact & analytics",
    "Research analytics": "Impact & analytics",
    "Impact Dashboard": "Impact & analytics",
    "Citation Monitoring": "Impact & analytics",
    "Teaching Hub": "Teaching",
}
