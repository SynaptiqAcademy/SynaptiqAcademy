"""Plan catalogue, credit cost catalogue, and credit-pack catalogue.

Single source of truth for monetisation. Loaded by:
- routers/billing.py (public pricing)
- routers/credits.py (cost transparency)
- services/credits_service.py (consume/refund)
- seed.py (DB upsert)
"""

# =====================================================================
# Subscription plans
# =====================================================================
PLANS = [
    {
        "code": "free",
        "name": "Free",
        "tagline": "Get started",
        "price_eur_monthly": 0,
        "price_eur_annual": 0,
        "future_price_eur_monthly": None,
        "badge": None,
        "credits_per_month": 50,
        "limits": {
            "active_projects": 1,
            "workspaces": 1,
            "repository_gb": 0.5,           # 500 MB
            "team_seats": 1,
            "journal_recs_per_month": 5,
            "conference_recs_per_month": 5,
            "grant_recs_per_month": 3,
        },
        "features": [
            "50 Research Credits / month",
            "Academic Profile",
            "ORCID Integration",
            "Research Network Access",
            "1 Active Project",
            "1 Workspace",
            "500 MB Repository Storage",
            "5 Journal Recommendations / month",
            "5 Conference Recommendations / month",
            "3 Grant Recommendations / month",
            "Basic Profile Visibility",
        ],
        "excluded": [
            "AI Research Assistant",
            "AI Manuscript Copilot",
            "Publication Tracking",
            "Advanced Analytics",
            "Unlimited Discovery Tools",
            "Advanced Collaboration Features",
            "Priority Support",
        ],
        "cta": "Get Started Free",
        "stripe_price_id_monthly": "",
        "stripe_price_id_annual": "",
    },
    {
        "code": "researcher",
        "name": "Researcher",
        "tagline": "For active researchers",
        "price_eur_monthly": 9.99,
        "price_eur_annual": 7.99,
        "future_price_eur_monthly": 14.99,
        "badge": "Early Access",
        "credits_per_month": 300,
        "limits": {
            "active_projects": -1,
            "workspaces": 10,
            "repository_gb": 100,
            "team_seats": 1,
            "journal_recs_per_month": -1,
            "conference_recs_per_month": -1,
            "grant_recs_per_month": -1,
        },
        "features": [
            "300 Research Credits / month",
            "Unlimited Projects",
            "Up to 10 Workspaces",
            "Repository 100 GB",
            "Full Journal Discovery",
            "Full Conference Discovery",
            "Full Grant Discovery",
            "Publication Tracking",
            "Advanced Analytics",
            "AI Research Assistant",
            "AI Manuscript Copilot",
            "Priority Support",
        ],
        "excluded": [],
        "cta": "Choose Researcher",
        "stripe_price_id_monthly": "",
        "stripe_price_id_annual": "",
    },
    {
        "code": "pro_researcher",
        "name": "Pro Researcher",
        "tagline": "For power users",
        "price_eur_monthly": 29.99,
        "price_eur_annual": 23.99,
        "future_price_eur_monthly": None,
        "badge": "Best Value",
        "credits_per_month": 1000,
        "limits": {
            "active_projects": -1,
            "workspaces": -1,
            "repository_gb": 500,
            "team_seats": 1,
            "journal_recs_per_month": -1,
            "conference_recs_per_month": -1,
            "grant_recs_per_month": -1,
        },
        "features": [
            "1,000 Research Credits / month",
            "Unlimited Projects",
            "Unlimited Workspaces",
            "Repository 500 GB",
            "Advanced AI Research Assistant",
            "Advanced Manuscript Copilot",
            "Collaboration Intelligence",
            "Research Analytics Suite",
            "Citation Monitoring",
            "Research Impact Dashboard",
            "Priority Support",
        ],
        "excluded": [],
        "cta": "Choose Pro",
        "stripe_price_id_monthly": "",
        "stripe_price_id_annual": "",
    },
    {
        "code": "institution",
        "name": "Institution",
        "tagline": "Universities & labs",
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
        "features": [
            "20,000 Research Credits / month",
            "25 Users Included",
            "Unlimited Projects",
            "Unlimited Workspaces",
            "Repository 2 TB",
            "Institutional Analytics",
            "Department Management",
            "Dedicated Support",
        ],
        "excluded": [],
        "cta": "Choose Institution",
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
# Credit cost per AI action (per updated academic-usage spec)
# =====================================================================
CREDIT_COSTS = {
    # Heavy-weight reviews
    "ai_manuscript_review":      20,
    "ai_literature_review":      20,
    "ai_statistical_review":     25,
    # Mid-weight builders/advisors
    "ai_methodology_builder":    10,
    "ai_research_design_advisor":10,
    "ai_research_gap_finder":    10,
    "ai_collaboration_intelligence": 15,
    # Recommendations
    "ai_journal_matching":        5,
    "ai_conference_matching":     5,
    "ai_grant_matching":          5,
    "ai_abstract_generator":      5,
    # Lightweight assistants
    "ai_research_assistant":      2,
    "ai_chat_message":            2,    # Manuscript Copilot — per message
    "ai_os_message":              3,    # Synaptiq AI OS — per message (Phase XXIII)
    # Academic Copilot (Phase XI)
    "copilot_chat":               3,    # Copilot chat message (multi-engine)
    "copilot_dashboard":          2,    # Personalised academic dashboard
    "copilot_roadmap":            5,    # Academic roadmap generation
    "copilot_suggestions":        1,    # Proactive suggestion scan
    # Publishing Intelligence (Phase XII)
    "publishing_journal_analyse": 3,   # Journal fit analysis (30+ factors)
    "publishing_journal_match":   5,   # Smart journal matching (6 types)
    "publishing_conference_match":3,   # Conference matching
    "publishing_grant_match":     3,   # Grant matching
    "publishing_readiness_check": 2,   # Submission readiness (15+ checks)
    "publishing_cover_letter":    4,   # AI cover letter generation
    "publishing_reviewer_response":4,  # Reviewer response document
    "publishing_strategy":        5,   # Publication strategy builder
    "publishing_risk_analysis":   3,   # Risk analysis (8 dimensions)
    "publishing_dashboard":       2,   # Publishing dashboard
    "publishing_export":          2,   # Document export
    # Autonomous Research Agents (Phase XIII)
    "agents_workflow_run":        8,   # Full multi-agent workflow execution
    "agents_task_run":            6,   # Auto-detected task workflow
    "agents_single_run":          2,   # Single agent execution
    "agents_parallel_run":        4,   # Parallel multi-agent execution
    # Research Collaboration Intelligence (Phase XIV)
    "collab_match":               3,   # Two-researcher compatibility match
    "collab_rank":                4,   # Rank candidates by compatibility
    "collab_opportunities":       4,   # Detect collaboration opportunities
    "collab_team_build":          6,   # Build optimal research team
    "collab_team_simulate":       4,   # Simulate team composition
    "collab_introduction":        2,   # Smart introduction narrative
    "collab_network":             5,   # Network analysis
    "collab_prediction":          3,   # Collaboration success prediction
    "collab_recommendations":     4,   # Ranked recommendations
    "collab_social_graph":        5,   # Build academic social graph
    # Institution Intelligence Engine (Phase XV)
    "institution_profile":        3,   # Build institution profile
    "institution_kpis":           2,   # Compute 20 KPIs
    "institution_organizational": 4,   # Organizational intelligence
    "institution_predict":        5,   # Multi-year forecasts
    "institution_resources":      4,   # Resource optimization
    "institution_talent":         4,   # Talent intelligence
    "institution_portfolio":      3,   # Portfolio analysis
    "institution_benchmark":      3,   # Peer benchmarking
    "institution_risks":          3,   # Risk detection
    "institution_recommendations":5,   # Executive recommendations
    "institution_monitor":        2,   # Autonomous monitoring
    "institution_knowledge_graph":4,   # Knowledge graph
    "institution_visualization":  2,   # Visualization data
    "institution_export":         5,   # Report export
    "institution_full_analysis":  10,  # Full analysis (all engines)
    # Phase XVI — Academic Career Intelligence Engine
    "career_profile":            2,   # Build career profile
    "career_roadmap":            5,   # Generate 1/3/5/10-year roadmap
    "career_goals":              3,   # Goal evaluation & tracking
    "career_skill_gaps":         4,   # 15-domain skill gap analysis
    "career_promotion":          5,   # Promotion readiness assessment
    "career_productivity":       3,   # Research productivity analysis
    "career_risks":              4,   # Career risk detection
    "career_recommendations":    3,   # Personalized recommendations
    "career_copilot":            2,   # Copilot suggestions
    "career_visualization":      2,   # Visualization data
    "career_export":             5,   # Report export (6 types × 3 formats)
    "career_full_analysis":      12,  # Full career intelligence analysis
    # Knowledge Graph (Phase XVII)
    "kg_import":                 10,  # Bulk platform data import
    "kg_add_node":                1,  # Add a single node
    "kg_add_edge":                1,  # Add a single edge
    "kg_stats":                   1,  # Graph statistics
    "kg_analytics":               5,  # PageRank / influence scores
    "kg_communities":             5,  # Community detection
    "kg_embeddings":              3,  # Node embeddings / similarity
    "kg_reasoning":               6,  # Semantic reasoning (hidden collabs, etc.)
    "kg_discovery":               4,  # Knowledge discovery
    "kg_query":                   3,  # Graph queries
    "kg_visualization":           3,  # Visualization data
    "kg_copilot":                 4,  # Copilot context enrichment
    # Prediction & Forecasting Intelligence (Phase XVIII)
    "prediction_publication":     6,   # Full publication outcome prediction
    "prediction_journal_ranking": 5,   # Journal selection ranking
    "prediction_conference":      4,   # Conference outcome prediction
    "prediction_grant":           8,   # Grant funding probability
    "prediction_career_forecast": 7,   # Career forecasting (1/3/5/10 year)
    "prediction_collaboration":   5,   # Collaboration success forecast
    "prediction_institution":     8,   # Institution-level forecasting
    "prediction_trend":           5,   # Research trend forecasting
    "prediction_strategic":       4,   # Strategic decision advisor
    "prediction_scenario":        8,   # Multi-scenario simulation
    "prediction_what_if":         4,   # What-if analysis
    "prediction_visualization":   2,   # Visualization data
    "prediction_copilot":         3,   # Copilot forecast enrichment
    # Self-Improving Academic Intelligence Platform (Phase XX)
    "si_query":       2,   # Performance metrics, quality reports
    "si_diagnostics": 2,   # Engine health diagnostics
    "si_benchmark":   5,   # Run benchmark suite (compute-intensive)
    "si_experiment":  3,   # Create A/B experiment
    "si_optimize":    4,   # Generate optimization candidates
    "si_copilot":     2,   # Copilot improvement suggestions
    # Academic OS (Phase XXI)
    "aos_workflow":   5,   # Start a full workflow pipeline
    "aos_project":    2,   # Create a research project
    "aos_search":     2,   # Global cross-entity search
    "aos_dashboard":  1,   # Generate personalized dashboard
    "aos_automation": 3,   # Fire automation event
    "ai_rewriting":               2,
    # Free actions (logged but never deducted)
    "researcher_discovery":       0,
    "profile_creation":           0,
    "collaboration_request":      0,
    # Teaching Hub AI tools
    "ai_lesson_plan_generate":   10,    # AI lesson plan generation
    "ai_assessment_generate":    10,    # AI assessment generation
    "ai_teaching_assistant":      2,    # AI teaching assistant per message
    # Backwards-compat aliases for older call sites
    "ai_reviewer_matching":       5,
    "ai_collaborator_matching":   5,
    "ai_literature_synthesis":   20,    # alias -> literature review
    "ai_citation_generation":     2,    # alias -> rewriting cost
    "ai_methodology_assistance": 10,    # alias -> methodology builder
    "ai_marketplace_rerank":      5,
}


# Human-readable display rows for the pricing page (Research Credit Usage section).
CREDIT_USAGE_DISPLAY = [
    {"label": "AI Manuscript Review",       "cost": 20, "unit": "per review",  "free": False},
    {"label": "AI Literature Review",       "cost": 20, "unit": "per review",  "free": False},
    {"label": "AI Statistical Review",      "cost": 25, "unit": "per review",  "free": False},
    {"label": "AI Methodology Builder",     "cost": 10, "unit": "per build",   "free": False},
    {"label": "AI Research Design Advisor", "cost": 10, "unit": "per session", "free": False},
    {"label": "AI Research Gap Finder",     "cost": 10, "unit": "per scan",    "free": False},
    {"label": "AI Journal Matching",        "cost": 5,  "unit": "per match",   "free": False},
    {"label": "AI Conference Matching",     "cost": 5,  "unit": "per match",   "free": False},
    {"label": "AI Grant Matching",          "cost": 5,  "unit": "per match",   "free": False},
    {"label": "AI Abstract Generator",      "cost": 5,  "unit": "per abstract","free": False},
    {"label": "AI Research Assistant",      "cost": 2,  "unit": "per query",   "free": False},
    {"label": "AI Manuscript Copilot",      "cost": 2,  "unit": "per message", "free": False},
    {"label": "AI Rewriting",               "cost": 2,  "unit": "per request", "free": False},
    {"label": "Researcher Discovery",       "cost": 0,  "unit": "",            "free": True},
    {"label": "Profile Creation",           "cost": 0,  "unit": "",            "free": True},
    {"label": "Collaboration Requests",     "cost": 0,  "unit": "",            "free": True},
]


# =====================================================================
# Feature gating — what each plan unlocks
# =====================================================================
# Use a stable string key. Endpoints declare `require_feature("ai_assistant")`.
# Mapping kept tight; expand without code changes by adding rows.
FEATURE_MIN_PLAN = {
    # Free for everyone
    "academic_profile":            "free",
    "orcid":                       "free",
    "network":                     "free",
    "messaging":                   "free",
    "basic_discovery":             "free",
    "project_create":              "free",      # respects per-plan quota
    "workspace_create":            "free",      # respects per-plan quota
    "collaboration_request":       "free",
    # Researcher+
    "ai_assistant":                "researcher",
    "ai_manuscript_copilot":       "researcher",
    "publication_tracking":        "researcher",
    "advanced_analytics":          "researcher",
    "full_discovery":              "researcher",
    "ai_journal_matching":         "researcher",
    "ai_conference_matching":      "researcher",
    "ai_grant_matching":           "researcher",
    "ai_manuscript_review":        "researcher",
    "ai_methodology_builder":      "researcher",
    "ai_research_assistant":       "researcher",
    "ai_rewriting":                "researcher",
    "ai_abstract_generator":       "researcher",
    # Pro Researcher+
    "ai_advanced_assistant":       "pro_researcher",
    "ai_literature_review":        "pro_researcher",
    "ai_statistical_review":       "pro_researcher",
    "ai_research_design_advisor":  "pro_researcher",
    "ai_research_gap_finder":      "pro_researcher",
    "collaboration_intelligence":  "pro_researcher",
    "research_analytics_suite":    "pro_researcher",
    "citation_monitoring":         "pro_researcher",
    "research_impact_dashboard":   "pro_researcher",
    "premium_collaboration":       "pro_researcher",
    # Institution
    "sso":                         "institution",
    "governance_console":          "institution",
    "institutional_analytics":     "institution",
    "department_management":       "institution",
}


# Per-plan resource quotas (centralised for require_quota checks).
PLAN_QUOTAS = {
    "free":           {"projects": 1,  "workspaces": 1,  "manuscripts": 3},
    "researcher":     {"projects": -1, "workspaces": 10, "manuscripts": -1},
    "pro_researcher": {"projects": -1, "workspaces": -1, "manuscripts": -1},
    "institution":    {"projects": -1, "workspaces": -1, "manuscripts": -1},
    "enterprise":     {"projects": -1, "workspaces": -1, "manuscripts": -1},
}

# Per-plan repository storage limits in bytes. Must match PLANS[].limits.repository_gb.
STORAGE_LIMITS_BYTES: dict[str, int] = {
    "free":           500 * 1024 * 1024,               # 500 MB
    "researcher":     100 * 1024 * 1024 * 1024,        # 100 GB
    "pro_researcher": 500 * 1024 * 1024 * 1024,        # 500 GB
    "institution":    2 * 1024 * 1024 * 1024 * 1024,   # 2 TB
    "enterprise":     -1,                              # unlimited / contract-defined
}


# Ordered tier rank — used by require_plan / has_plan_at_least.
PLAN_RANK = {"free": 0, "researcher": 1, "pro_researcher": 2, "institution": 3, "enterprise": 4}


# =====================================================================
# Credit packs — one-time purchases, never expire
# =====================================================================
CREDIT_PACKS = [
    {"code": "pack_100",   "credits":  100, "price_eur":  5, "label": "100 Credits",   "stripe_price_id": ""},
    {"code": "pack_250",   "credits":  250, "price_eur": 10, "label": "250 Credits",   "stripe_price_id": ""},
    {"code": "pack_1000",  "credits": 1000, "price_eur": 29, "label": "1,000 Credits", "stripe_price_id": ""},
    {"code": "pack_5000",  "credits": 5000, "price_eur": 99, "label": "5,000 Credits", "stripe_price_id": ""},
]


def get_plan(code: str) -> dict:
    for p in PLANS:
        if p["code"] == code:
            return p
    return PLANS[0]


def get_credit_cost(key: str, default: int = 0) -> int:
    return CREDIT_COSTS.get(key, default)


def get_credit_pack(code: str) -> dict | None:
    for p in CREDIT_PACKS:
        if p["code"] == code:
            return p
    return None


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
        if p.get("stripe_price_id_annual") == stripe_price_id:
            return p["code"], "annual"
    return None


# =====================================================================
# Feature comparison matrix (per spec)
# =====================================================================
# Tuple shape: (label, free_value, researcher_value, pro_value, institution_value)
# Use True/False booleans or strings; the frontend renders them uniformly.
FEATURE_MATRIX = [
    ("Research Credits / month",       "50",         "300",        "1,000",      "20,000",    "Unlimited"),
    ("Active Projects",                "1",          "Unlimited",  "Unlimited",  "Unlimited", "Unlimited"),
    ("Workspaces",                     "1",          "10",         "Unlimited",  "Unlimited", "Unlimited"),
    ("Repository Storage",             "500 MB",     "100 GB",     "500 GB",     "2 TB",      "Custom"),
    ("Users Included",                 "1",          "1",          "1",          "25",        "Unlimited"),
    ("Academic Profile",               True,         True,         True,         True,        True),
    ("ORCID Integration",              True,         True,         True,         True,        True),
    ("Research Network Access",        True,         True,         True,         True,        True),
    ("Journal Discovery",              "5 / mo",     "Full",       "Full",       "Full",      "Full"),
    ("Conference Discovery",           "5 / mo",     "Full",       "Full",       "Full",      "Full"),
    ("Grant Discovery",                "3 / mo",     "Full",       "Full",       "Full",      "Full"),
    ("Publication Tracking",           False,        True,         True,         True,        True),
    ("Advanced Analytics",             False,        True,         True,         True,        True),
    ("AI Research Assistant",          False,        True,         "Advanced",   "Advanced",  "Advanced"),
    ("AI Manuscript Copilot",          False,        True,         "Advanced",   "Advanced",  "Advanced"),
    ("Collaboration Intelligence",     False,        False,        True,         True,        True),
    ("Research Analytics Suite",       False,        False,        True,         True,        True),
    ("Citation Monitoring",            False,        False,        True,         True,        True),
    ("Research Impact Dashboard",      False,        False,        True,         True,        True),
    ("Institutional Analytics",        False,        False,        False,        True,        True),
    ("Department Management",          False,        False,        False,        True,        True),
    ("SSO / SAML Integration",         False,        False,        False,        False,       True),
    ("Custom AI Models",               False,        False,        False,        False,       True),
    ("On-premise / Private Cloud",     False,        False,        False,        False,       True),
    ("SLA-backed Uptime",              False,        False,        False,        False,       "99.9%"),
    ("Support",                        "Community",  "Priority",   "Priority",   "Dedicated", "Account Manager"),
]
