/**
 * Public-marketing-funnel events only (Phase 9A Part 3, §35).
 *
 * Deliberately separate from lib/analytics.js: that module's
 * trackSessionStart/trackPageView/trackFeatureUse post to the existing
 * first-party POST /api/session/event pipeline, which requires an
 * authenticated session — it cannot carry events from an anonymous visitor
 * on the landing/pricing/contact/signup pages, which is most of what the
 * commercial funnel needs to measure. This module instead uses the
 * existing PostHog integration (public/analytics-init.js), which already
 * works pre-auth and already owns the GDPR consent gate
 * (posthog.opt_in_capturing/opt_out_capturing, driven by the same cookie-
 * consent banner) — it does not init or configure PostHog itself.
 *
 * Once a visitor signs up and becomes an authenticated user, subsequent
 * in-app engagement should go through lib/analytics.js's existing
 * pipeline instead, not this one — see Onboarding.jsx's onboarding_completed
 * call for that boundary in practice.
 *
 * Never pass free-text research-question content as an event property.
 */
export function trackMarketingEvent(event, properties = {}) {
  try {
    if (typeof window !== "undefined" && window.posthog && typeof window.posthog.capture === "function") {
      window.posthog.capture(event, properties);
    }
  } catch {
    // Analytics must never break the product.
  }
}
