/**
 * Admin OS navigation — single source of truth for the sidebar, breadcrumbs,
 * and the admin command palette. Icons are passed in by AdminSidebar.jsx
 * (which owns the lucide-react imports) via ICONS below, keeping this file
 * framework-icon-agnostic so it can also be consumed by non-visual code
 * (breadcrumb matching, search indexing) without pulling in icon components.
 */

export const ADMIN_SECTIONS = [
  {
    label: "Executive",
    items: [
      { label: "Command Center", path: "/admin", end: true },
      { label: "Analytics", path: "/admin/analytics" },
      { label: "Revenue", path: "/admin/revenue" },
      { label: "AI Copilot", path: "/admin/copilot" },
    ],
  },
  {
    label: "Users & Finance",
    items: [
      { label: "Users", path: "/admin/users" },
      { label: "Subscriptions", path: "/admin/subscriptions" },
      { label: "Promotions", path: "/admin/promotions" },
      { label: "Institutions", path: "/admin/institution-center" },
    ],
  },
  {
    label: "Academic",
    items: [
      { label: "Teaching", path: "/admin/teaching-analytics" },
      { label: "Research", path: "/admin/research" },
      { label: "Research Integrity", path: "/admin/research-integrity" },
      { label: "Content", path: "/admin/content" },
      { label: "Reputation", path: "/admin/reputation" },
      { label: "Grant Hub", path: "/admin/grant-hub" },
      { label: "Reviewer Hub", path: "/admin/reviewer-hub" },
    ],
  },
  {
    label: "Platform Ops",
    items: [
      { label: "System Health", path: "/admin/health" },
      { label: "Platform Command", path: "/admin/command-map" },
      { label: "Errors & Incidents", path: "/admin/errors" },
      { label: "Platform Auditor", path: "/admin/platform-auditor" },
      { label: "Database Ops", path: "/admin/database" },
      { label: "Storage", path: "/admin/storage" },
      { label: "Background Jobs", path: "/admin/jobs" },
      { label: "API Monitor", path: "/admin/api-monitor" },
      { label: "Feature Flags", path: "/admin/feature-flags-center" },
      { label: "Releases", path: "/admin/releases" },
    ],
  },
  {
    label: "Governance",
    items: [
      { label: "Data Quality", path: "/admin/data-quality" },
      { label: "Search Observatory", path: "/admin/search" },
      { label: "Reputation Center", path: "/admin/reputation-center" },
      { label: "Recommendation Center", path: "/admin/recommendation-center" },
      { label: "Impact Center", path: "/admin/impact-center" },
      { label: "AI Center", path: "/admin/ai-center" },
      { label: "Profiles", path: "/admin/profiles" },
      { label: "Verification", path: "/admin/verification" },
      { label: "Integrity Center", path: "/admin/integrity-center" },
    ],
  },
  {
    label: "Security & Comms",
    items: [
      { label: "Account Security", path: "/admin/account-security" },
      { label: "MFA Center", path: "/admin/mfa" },
      { label: "Security Hardening", path: "/admin/security-hardening" },
      { label: "Security", path: "/admin/security" },
      { label: "Trust Center", path: "/admin/trust-center" },
      { label: "Audit Center", path: "/admin/audit" },
      { label: "Email Center", path: "/admin/email" },
      { label: "Communications", path: "/admin/communications" },
      { label: "Support Center", path: "/admin/support" },
    ],
  },
];

/** Flat list of every admin page, for the command palette and breadcrumb lookup. */
export function getAllAdminPages() {
  const pages = [];
  for (const section of ADMIN_SECTIONS) {
    for (const item of section.items) {
      pages.push({ label: item.label, to: item.path, group: section.label, end: !!item.end });
    }
  }
  return pages;
}

/** Find the {section, item} for a given pathname, for breadcrumb rendering. */
export function findAdminNavEntry(pathname) {
  for (const section of ADMIN_SECTIONS) {
    for (const item of section.items) {
      if (item.end ? pathname === item.path : pathname.startsWith(item.path)) {
        return { section, item };
      }
    }
  }
  return null;
}

export const ADMIN_QUICK_ACTIONS = [
  { label: "Impersonate User", description: "Start an impersonation session", to: "/admin/users" },
  { label: "Grant Credits", description: "Manually grant credits to a user", to: "/admin/users" },
  { label: "Create Announcement", description: "Publish a platform announcement", to: "/admin/communications" },
  { label: "Enable Maintenance Mode", description: "Toggle platform maintenance mode", to: "/admin/health" },
];
