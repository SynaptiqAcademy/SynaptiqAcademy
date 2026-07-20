/**
 * Synaptiq — Shared Navigation Data
 *
 * Single source of truth for all sub-navigation items.
 * No page may define its own nav arrays.
 * Import from here and pass to NavTabs or the layout's subNav slot.
 */

// ── AI Research OS — shared across all AI tool pages ─────────────────────────
export const AI_NAV_ITEMS = [
  { id: "/ai",                          label: "AI Hub"          },
  { id: "/literature-review",           label: "Literature"      },
  { id: "/research-gap-finder",         label: "Gaps"            },
  { id: "/research-design-advisor",     label: "Study Design"    },
  { id: "/statistical-review",          label: "Statistics"      },
  { id: "/manuscript-review",           label: "Manuscript"      },
  { id: "/ai/abstract",                 label: "Abstract"        },
  { id: "/ai/rewrite",                  label: "Rewriting"       },
  { id: "/collaboration-intelligence",  label: "Collaboration"   },
  { id: "/recommendations",             label: "Recommendations" },
  { id: "/ai-usage",                    label: "Usage"           },
];

// ── Intelligence / Impact nav — shared across impact/analytics pages ──────────
export const INTEL_NAV_ITEMS = [
  { id: "/impact",              label: "Research Impact"   },
  { id: "/reputation",          label: "Reputation"        },
  { id: "/analytics",           label: "Analytics"         },
  { id: "/citation-monitoring", label: "Citation Monitor"  },
  { id: "/verification-center", label: "Verification"      },
  { id: "/ai-usage",            label: "AI Usage"          },
  { id: "/leaderboards",        label: "Leaderboards"      },
];

// ── Institution Platform nav — shared across institution_platform/* pages ─────
export const INSTITUTION_NAV_ITEMS = [
  { id: "/institution-hub",                              label: "Overview"       },
  { id: "/institution-platform/executive-dashboard",    label: "Executive"      },
  { id: "/institution-platform/department-intelligence",label: "Departments"    },
  { id: "/institution-platform/faculty-intelligence",   label: "Faculty"        },
  { id: "/institution-platform/publication-intelligence",label: "Publications"  },
  { id: "/institution-platform/grant-intelligence",     label: "Grants"         },
  { id: "/institution-platform/benchmark-center",       label: "Benchmarks"     },
  { id: "/institution-platform/risk-intelligence",      label: "Risk"           },
  { id: "/institution-platform/financial-intelligence", label: "Financial"      },
  { id: "/institution-platform/strategic-planning",     label: "Strategy"       },
  { id: "/institution-platform/reports",                label: "Reports"        },
];

// ── SIE (Synaptiq Intelligence Engine) nav ────────────────────────────────────
export const SIE_NAV_ITEMS = [
  { id: "/sie/command-center",    label: "Command Center" },
  { id: "/sie/research-missions", label: "Missions"       },
  { id: "/sie/research-planning", label: "Planning"       },
  { id: "/sie/career-planner",    label: "Career"         },
  { id: "/sie/goal-manager",      label: "Goals"          },
  { id: "/sie/weekly-planner",    label: "Weekly"         },
  { id: "/sie/daily-agenda",      label: "Daily"          },
  { id: "/sie/recommendations",   label: "Insights"       },
  { id: "/sie/grant-planner",     label: "Grant Planner"  },
  { id: "/sie/publication-roadmap",label: "Publication"   },
  { id: "/sie/ai-memory",         label: "Memory"         },
  { id: "/sie/settings",          label: "Settings"       },
];

// ── Profile tabs ──────────────────────────────────────────────────────────────
export const PROFILE_TAB_ITEMS = [
  { id: "overview",        label: "Overview"        },
  { id: "publications",    label: "Publications"    },
  { id: "grants",          label: "Grants"          },
  { id: "collaborations",  label: "Collaborations"  },
  { id: "reviews",         label: "Reviews"         },
  { id: "about",           label: "About"           },
];

// ── Settings nav ──────────────────────────────────────────────────────────────
export const SETTINGS_NAV_ITEMS = [
  {
    group: "Account",
    items: [
      { id: "/settings/security",  label: "Security"    },
      { id: "/settings/billing",   label: "Billing"     },
    ],
  },
  {
    group: "Notifications",
    items: [
      { id: "/notifications",      label: "Notifications" },
    ],
  },
  {
    group: "Research",
    items: [
      { id: "/ai-policy",          label: "AI Policy"   },
      { id: "/academic-passport#research_integrations", label: "Research Integrations" },
    ],
  },
  {
    group: "Privacy",
    items: [
      { id: "/settings?section=privacy", label: "Privacy & Consent" },
      { id: "/gdpr",               label: "Data & Privacy" },
    ],
  },
];
