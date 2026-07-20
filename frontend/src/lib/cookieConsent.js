/**
 * cookieConsent — GDPR-compliant consent manager.
 *
 * Single source of truth for cookie consent state. Plain JS (no React
 * dependency) so it can be called from React components, from Settings,
 * and from non-React scripts (public/analytics-init.js) via localStorage
 * and the `synaptiq:consent-changed` window event.
 *
 * Storage: localStorage key `synaptiq_consent_v1` (also mirrored to
 * `window.synaptiqConsent` for quick inspection), best-effort audit copy
 * sent to POST /api/consent (anonymous-friendly, never blocks the UI).
 *
 * Consent expires after CONSENT_EXPIRY_MONTHS — after that readConsent()
 * treats it as absent and the banner will ask again, per GDPR guidance
 * that consent shouldn't be considered valid indefinitely.
 */
import api from "./api";

export const STORAGE_KEY = "synaptiq_consent_v1";
export const CONSENT_ID_KEY = "synaptiq_consent_id_v1";
export const CONSENT_EVENT = "synaptiq:consent-changed";
export const OPEN_PREFERENCES_EVENT = "synaptiq:open-cookie-preferences";

const CONSENT_EXPIRY_MONTHS = 12;

export const CATEGORY_META = [
  {
    id: "essential",
    label: "Essential",
    locked: true,
    description: "Required for sign-in, security, and core platform function.",
    explanation:
      "These cookies are strictly necessary — session/auth tokens, CSRF protection, and load-balancing. The platform cannot function without them, so they cannot be disabled.",
  },
  {
    id: "preferences",
    label: "Preferences",
    locked: false,
    description: "Remember your UI choices (theme, sidebar state, recent searches).",
    explanation:
      "Lets Synaptiq remember non-essential settings across visits, like sidebar collapse state or recently used sections, so you don't have to reconfigure them every time.",
  },
  {
    id: "analytics",
    label: "Analytics",
    locked: false,
    description: "Anonymous usage metrics to help us improve Synaptiq.",
    explanation:
      "Powers aggregate product analytics (PostHog) — which features are used, error rates, and performance. Disabling this stops all analytics scripts from running.",
  },
  {
    id: "marketing",
    label: "Marketing",
    locked: false,
    description: "Personalised research-community communications.",
    explanation:
      "Used only if you opt in to tailored communications about the platform. We do not currently serve advertising, and no ad-tracking pixels run on Synaptiq.",
  },
];

export const DEFAULT_PREFS = { essential: true, analytics: false, marketing: false, preferences: false };
export const ALL_ACCEPTED_PREFS = { essential: true, analytics: true, marketing: true, preferences: true };

function uuid() {
  // Lightweight v4-ish UUID; collision risk is fine for a consent_id.
  return ([1e7] + -1e3 + -4e3 + -8e3 + -1e11).replace(/[018]/g, (c) =>
    (c ^ (crypto.getRandomValues(new Uint8Array(1))[0] & (15 >> (c / 4)))).toString(16)
  );
}

function isExpired(record) {
  if (!record?.at) return true;
  const ageMs = Date.now() - new Date(record.at).getTime();
  return ageMs > CONSENT_EXPIRY_MONTHS * 30 * 24 * 60 * 60 * 1000;
}

function getOrCreateConsentId() {
  let id = null;
  try { id = localStorage.getItem(CONSENT_ID_KEY); } catch { /* no-op */ }
  if (!id) {
    id = uuid();
    try { localStorage.setItem(CONSENT_ID_KEY, id); } catch { /* no-op */ }
  }
  return id;
}

/** Returns the current consent record, or null if none/expired. */
export function readConsent() {
  let record;
  try { record = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null"); }
  catch { return null; }
  if (!record) return null;
  if (isExpired(record)) {
    try { localStorage.removeItem(STORAGE_KEY); } catch { /* no-op */ }
    return null;
  }
  return record;
}

/** True once the user has made (and not outgrown) a consent decision. */
export function hasConsent() {
  return !!readConsent();
}

/** Is a given category ("essential"|"analytics"|"marketing"|"preferences") enabled right now? */
export function isCategoryEnabled(category) {
  if (category === "essential") return true;
  const record = readConsent();
  return !!record?.prefs?.[category];
}

/**
 * Persists a consent decision: writes localStorage, mirrors to
 * window.synaptiqConsent, notifies listeners (same-tab custom event +
 * cross-tab `storage` event fires natively), and best-effort logs to the
 * backend. Never throws — a failed backend call must not block the UI.
 */
export function saveConsent(prefs, status, source = "banner") {
  const consent_id = getOrCreateConsentId();
  const finalPrefs = { ...DEFAULT_PREFS, ...prefs, essential: true };
  const record = { consent_id, status, prefs: finalPrefs, source, at: new Date().toISOString() };

  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(record)); } catch { /* no-op */ }
  window.synaptiqConsent = record;
  window.dispatchEvent(new CustomEvent(CONSENT_EVENT, { detail: record }));

  api.post("/consent", { consent_id, status, prefs: finalPrefs, source }).catch(() => {});
  return record;
}

export function acceptAll(source = "banner") {
  return saveConsent(ALL_ACCEPTED_PREFS, "accepted_all", source);
}

export function rejectOptional(source = "banner") {
  return saveConsent(DEFAULT_PREFS, "rejected_non_essential", source);
}

/** Clears the stored decision so the banner will ask again. */
export function resetConsent() {
  try { localStorage.removeItem(STORAGE_KEY); } catch { /* no-op */ }
  window.synaptiqConsent = null;
  window.dispatchEvent(new CustomEvent(CONSENT_EVENT, { detail: null }));
}

/** Tell any mounted banner to (re)open the preferences modal, e.g. from Settings. */
export function openPreferences() {
  window.dispatchEvent(new Event(OPEN_PREFERENCES_EVENT));
}

// Hidden developer helper — not linked from any UI, console/testing only:
//   window.__resetSynaptiqConsent()
if (typeof window !== "undefined") {
  window.__resetSynaptiqConsent = resetConsent;
}
