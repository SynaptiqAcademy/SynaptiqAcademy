/**
 * The single canonical backend-plan-code → customer-facing-name mapping
 * (Phase 9A Final Commercial Decisions, §10).
 *
 * Backend plan codes (researcher, pro_researcher, ...) stay exactly as they
 * are — they're authoritative for entitlement logic, quotas, and billing,
 * and renaming them would mean touching FEATURE_MIN_PLAN, PLAN_QUOTAS,
 * Stripe metadata, and every test that asserts on plan_code. This mapping
 * is the ONE place a customer-facing surface converts a code to a name —
 * nothing else should hardcode "Pro"/"Pro Advanced"/etc. against a
 * plan_code, and nothing should display a raw code (or a crude
 * code.replace("_"," ")) to a customer.
 *
 * Mirrors plans_catalogue.PLANS[*].name exactly — that backend field is
 * already the authoritative source (GET /billing/plans, GET
 * /permissions/me, GET /credits/balance all return it as plan_name/
 * plan.name). This frontend copy exists only for the handful of places
 * that need a name before/without an API round trip (e.g. a gate payload
 * that only carries the raw code).
 */
export const PLAN_DISPLAY_NAMES = {
  free: "Free",
  researcher: "Pro",
  pro_researcher: "Pro Advanced",
  institution: "Institution",
  enterprise: "Enterprise",
};

export function planDisplayName(code) {
  return PLAN_DISPLAY_NAMES[code] || "Pro";
}
