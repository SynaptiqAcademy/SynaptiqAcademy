import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

if (!BACKEND_URL) {
  console.error(
    "[AUTH] REACT_APP_BACKEND_URL is not set. " +
      "Create frontend/.env.local with REACT_APP_BACKEND_URL=https://api.synaptiq.academy"
  );
}

export { BACKEND_URL };
export const API = `${BACKEND_URL || "https://api.synaptiq.academy"}/api`;

const api = axios.create({
  baseURL: API,
  withCredentials: true,
  timeout: 40000, // 40s — covers 3 × 10s Resend retries + backoff overhead
});

// ─── Helpers ─────────────────────────────────────────────────────────────────

function getCsrfToken() {
  const match = document.cookie.match(/(?:^|;\s*)csrf_token=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

const _CSRF_SAFE_METHODS = new Set(["get", "head", "options"]);

// ─── Request interceptor: attach CSRF token (AUTH-007) ───────────────────────
api.interceptors.request.use((config) => {
  if (!_CSRF_SAFE_METHODS.has((config.method || "get").toLowerCase())) {
    const token = getCsrfToken();
    if (token) {
      config.headers["X-CSRF-Token"] = token;
    }
  }
  return config;
});

// ─── Response interceptor: 401 → refresh → retry; 402 → upgrade modal ────────
let _refreshing = false;
let _refreshQueue = [];

function _drainQueue(error) {
  _refreshQueue.forEach((cb) => cb(error));
  _refreshQueue = [];
}

api.interceptors.response.use(
  (r) => r,
  async (err) => {
    const status = err?.response?.status;
    const detail = err?.response?.data?.detail;
    const config = err?.config;

    if (status === 402 && detail && typeof detail === "object" && detail.code && !config?.silentGate) {
      try {
        window.dispatchEvent(new CustomEvent("synaptiq:gate", { detail }));
      } catch (_) {}
    }

    const isAuthEndpoint =
      config?.url &&
      (config.url.includes("/auth/refresh") ||
        config.url.includes("/auth/login") ||
        config.url.includes("/auth/register"));

    // AUTH-BUG-004: one automatic retry for login/register on a genuine
    // no-response failure (dropped connection, transient DNS/TLS blip, brief
    // backend restart). Safe to retry blindly here because the request never
    // reached the server (no response at all) — there's no risk of a duplicate
    // side effect the way there would be retrying an already-answered request.
    // Does NOT apply to 401/403/429/5xx — those are real answers, not dropped
    // connections, and must be shown to the user as-is.
    const isRetryableAuthCall =
      config?.url && (config.url.includes("/auth/login") || config.url.includes("/auth/register"));
    const isNoResponseFailure = !err?.response && (err?.code === "ERR_NETWORK" || err?.code === "ECONNABORTED");
    if (isRetryableAuthCall && isNoResponseFailure && !config?._networkRetried) {
      config._networkRetried = true;
      await new Promise((r) => setTimeout(r, 1200));
      return api(config);
    }

    if (status === 401 && !config?._retried && !isAuthEndpoint) {
      if (_refreshing) {
        return new Promise((resolve, reject) => {
          _refreshQueue.push((refreshErr) => {
            if (refreshErr) return reject(refreshErr);
            config._retried = true;
            resolve(api(config));
          });
        });
      }

      config._retried = true;
      _refreshing = true;
      try {
        await api.post("/auth/refresh");
        _refreshing = false;
        _drainQueue(null);
        return api(config);
      } catch (refreshErr) {
        _refreshing = false;
        _drainQueue(refreshErr);
        console.warn("[AUTH] Session expired — refresh failed");
        try {
          window.dispatchEvent(new CustomEvent("synaptiq:session-expired"));
        } catch (_) {}
        return Promise.reject(refreshErr);
      }
    }

    // Normalize detail to always be a string so callers can safely render it
    // without type-checking. Billing-gate events have already been dispatched
    // above (with the original object), so it's safe to flatten them here too.
    if (err?.response?.data?.detail != null) {
      const d = err.response.data.detail;
      if (typeof d !== "string") {
        err.response.data.detail = formatApiError(d);
      }
    }

    return Promise.reject(err);
  }
);

export default api;

export function formatApiError(detail) {
  if (detail == null) return "";
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((e) => (e && typeof e.msg === "string" ? e.msg : JSON.stringify(e)))
      .filter(Boolean)
      .join(" ");
  }
  if (detail && typeof detail.msg === "string") return detail.msg;
  if (detail && typeof detail === "object") return JSON.stringify(detail);
  return String(detail);
}

// ─── User-facing error catalog ───────────────────────────────────────────────
// One rule: never show a generic "network" message for something the server
// actually told us about. `e.response` present means the server responded —
// that's always a real, specific condition (wrong password, locked account,
// rate limited, database down), never "check your internet connection".
// Only the true no-response cases (ERR_NETWORK / ECONNABORTED) are about the
// network itself, and even those are split into what's actually distinguishable.

export function getErrorMessage(e) {
  if (!e.response) {
    if (e.code === "ECONNABORTED") {
      return "Request timed out. The server is taking too long to respond — please try again.";
    }
    if (e.code === "ERR_NETWORK" || e.message === "Network Error") {
      return navigator.onLine === false
        ? "You're offline. Check your internet connection and try again."
        : "Unable to reach the server. Please check your connection and try again.";
    }
    return "Something went wrong. Please try again.";
  }
  const { status, data } = e.response;
  const detail = formatApiError(data?.detail);
  if (status === 401) return detail || "Incorrect email or password.";
  if (status === 403) return detail || "Access denied.";
  if (status === 429) return detail || "Too many attempts. Please wait a moment and try again.";
  if (status === 503) return detail || "Authentication service is temporarily unavailable. Please try again shortly.";
  if (status >= 500) return "Server temporarily unavailable. Please try again later.";
  return detail || "Something went wrong. Please try again.";
}

export function safeErrorMessage(e, fallback = "Something went wrong. Please try again.") {
  const detail = e?.response?.data?.detail;
  if (detail != null) return formatApiError(detail) || fallback;
  if (!e?.response) return getErrorMessage(e);
  return fallback;
}
