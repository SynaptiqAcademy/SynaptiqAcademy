/**
 * Client-side mirror of the backend entitlement model — for RENDERING only
 * (locked nav items, paywall copy, cost labels). The backend is
 * authoritative and enforces every capability itself; nothing here grants
 * access. Capabilities and paywall copy come from GET /api/permissions/me.
 */
import { useAuth } from "@/contexts/AuthContext";

// Page route prefix -> capability that unlocks it (longest prefix wins).
// Projects / workspaces / messages are deliberately NOT listed: they stay
// reachable read-only so a downgraded user can still see their data.
export const ROUTE_CAPABILITIES = {
  "/network": "can_use_research_network",
  "/researchers": "can_use_research_network",
  "/expertise": "can_use_research_network",
  "/reviewer-marketplace": "can_use_research_network",
  "/marketplace": "can_use_research_network",
  "/collaborations": "can_join_collaboration_workflows",
  "/grant-collaboration-hub": "can_join_collaboration_workflows",
  "/teams": "can_join_collaboration_workflows",
  "/journals": "can_use_journal_discovery",
  "/conferences": "can_use_conference_discovery",
  "/grants": "can_use_grant_discovery",
  "/funding": "can_use_grant_discovery",
  "/teaching": "can_use_teaching_hub",
  "/analytics": "can_view_research_analytics",
  "/publication-hub": "can_use_publication_tracking",
  "/ai/rewrite": "can_use_research_assistant",
  "/ai/abstract": "can_use_research_assistant",
  "/copilot": "can_use_research_assistant",
  "/ai-suite": "can_use_research_assistant",
  "/manuscript-review": "can_use_manuscript_copilot",
  "/literature-review": "can_use_advanced_ai",
  "/research-gap-finder": "can_use_advanced_ai",
  "/research-design-advisor": "can_use_advanced_ai",
  "/statistical-review": "can_use_advanced_ai",
  "/impact-dashboard": "can_view_impact_dashboard",
  "/research-impact": "can_view_impact_dashboard",
  "/citation-monitoring": "can_use_citation_monitoring",
  "/collaboration-intelligence": "can_use_collaboration_intelligence",
};

export function capabilityForRoute(path) {
  if (!path) return null;
  let best = null;
  for (const prefix of Object.keys(ROUTE_CAPABILITIES)) {
    if ((path === prefix || path.startsWith(prefix + "/")) && (!best || prefix.length > best.length)) {
      best = prefix;
    }
  }
  return best ? ROUTE_CAPABILITIES[best] : null;
}

/** { has(cap), lockedFor(path), paywall(cap), entitlements, tier } — while
 *  entitlements are loading nothing is reported locked (no flash of locks). */
export function useEntitlements() {
  const { entitlements: summary } = useAuth() || {};
  const ent = summary?.entitlements || null;
  const caps = ent?.capabilities || null;
  const has = (cap) => (caps ? caps[cap] !== false : true);
  const paywall = (cap) => {
    const p = summary?.paywall?.[cap] || {};
    return {
      code: "upgrade_required",
      capability: cap,
      message: p.message || "This feature requires an upgrade.",
      required_plan: p.required_plan || "researcher",
      required_plan_name: p.required_plan_name || "Pro",
      upgrade_url: "/pricing",
    };
  };
  const lockedFor = (path) => {
    const cap = capabilityForRoute(path);
    return cap && !has(cap) ? cap : null;
  };
  return { entitlements: ent, tier: ent?.tier || null, has, lockedFor, paywall, summary };
}

/** Open the global upgrade explanation (components/billing/UpgradeModal). */
export function openPaywall(detail) {
  try {
    window.dispatchEvent(new CustomEvent("synaptiq:gate", { detail: { ...detail, source: "nav" } }));
  } catch (_) {}
}
