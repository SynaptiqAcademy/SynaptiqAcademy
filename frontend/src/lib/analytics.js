/**
 * analytics — lightweight first-party usage tracking.
 *
 * Posts to the existing, already-built backend pipeline
 * (POST /api/session/event -> session_events collection ->
 * services/engagement.py's compute_engagement()/platform_analytics(),
 * consumed by the Admin OS analytics dashboard). That pipeline has existed
 * for a while but nothing in the frontend ever called it, so the admin
 * dashboard has been showing zero real usage data. This is the missing
 * client-side half.
 *
 * Respects the existing GDPR consent manager (lib/cookieConsent.js) —
 * tracking only runs when the user has enabled the "analytics" category,
 * and starts/stops live as consent changes without needing a reload.
 *
 * Only ever called for authenticated, protected-route views (see
 * components/layout/AppShell.jsx) — the backend endpoint requires a
 * logged-in session anyway.
 */
import api, { API } from "./api";
import { isCategoryEnabled, CONSENT_EVENT } from "./cookieConsent";

let sessionStartedAt = null;
let sessionStarted = false;
let unloadListenersBound = false;

function getCsrfToken() {
  const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

function post(body) {
  if (!isCategoryEnabled("analytics")) return;
  api.post("/session/event", body).catch(() => {});
}

// pagehide (tab close / navigate away / refresh) is more reliable than
// beforeunload for bfcache-eligible pages, and unlike a normal axios call —
// which the browser can cancel mid-flight once unload starts — fetch with
// keepalive:true is specifically designed to survive it.
function sendSessionEnd() {
  if (!sessionStartedAt || !isCategoryEnabled("analytics")) return;
  const minutes = (Date.now() - sessionStartedAt) / 60000;
  sessionStartedAt = null;
  const token = getCsrfToken();
  try {
    fetch(`${API}/session/event`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { "X-CSRF-Token": token } : {}),
      },
      credentials: "include",
      keepalive: true,
      body: JSON.stringify({ event: "session_end", duration_minutes: minutes }),
    });
  } catch {
    /* best-effort — never block unload */
  }
}

/** Call once when an authenticated shell mounts. Idempotent per tab session. */
export function trackSessionStart() {
  if (sessionStarted) return;
  sessionStarted = true;
  sessionStartedAt = Date.now();
  post({ event: "session_start" });

  if (!unloadListenersBound) {
    unloadListenersBound = true;
    window.addEventListener("pagehide", sendSessionEnd);
  }

  // If the user grants analytics consent mid-session (banner was previously
  // rejected/dismissed), start counting from that moment rather than losing
  // the whole session.
  window.addEventListener(CONSENT_EVENT, () => {
    if (isCategoryEnabled("analytics") && !sessionStartedAt) {
      sessionStartedAt = Date.now();
    }
  });
}

/** Call on every route change within the authenticated app. */
export function trackPageView(path) {
  post({ event: "page_view", path });
}

/** Optional: call at a meaningful feature-usage moment not already captured
 * by credit consumption (e.g. a free action worth knowing is popular). */
export function trackFeatureUse(feature, metadata) {
  post({ event: "feature_use", feature, metadata });
}
