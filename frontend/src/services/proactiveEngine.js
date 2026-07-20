/**
 * proactiveEngine.js — Proactive AI client service (Phase XXX).
 *
 * Wraps all /api/proactive/* calls with a 10-minute in-memory cache
 * so components don't hammer the API on every render.
 *
 * Usage:
 *   import { getBriefing, getRecommendations, dismissRec } from "../services/proactiveEngine";
 */

import api from "../lib/api";

// ── Cache ──────────────────────────────────────────────────────────────────────

const CACHE_TTL = 10 * 60 * 1000; // 10 minutes

const _cache = {};

function getCached(key) {
  const entry = _cache[key];
  if (!entry) return null;
  if (Date.now() - entry.ts > CACHE_TTL) {
    delete _cache[key];
    return null;
  }
  return entry.data;
}

function setCache(key, data) {
  _cache[key] = { ts: Date.now(), data };
}

function invalidate(...keys) {
  keys.forEach(k => delete _cache[k]);
}

// ── API calls ──────────────────────────────────────────────────────────────────

/**
 * Daily personalized briefing.
 * Returns: { greeting, date, summary_items, profile_completion, top_recommendation, total_recs }
 */
export async function getBriefing(forceRefresh = false) {
  const key = "briefing";
  if (!forceRefresh) {
    const cached = getCached(key);
    if (cached) return cached;
  }
  try {
    const { data } = await api.get("/proactive/briefing");
    setCache(key, data);
    return data;
  } catch {
    return null;
  }
}

/**
 * Paginated recommendations, optionally filtered.
 * @param {{ category?: string, limit?: number, offset?: number }} opts
 */
export async function getRecommendations({ category, limit = 20, offset = 0 } = {}) {
  const key = `recs:${category || "all"}:${offset}`;
  const cached = getCached(key);
  if (cached) return cached;
  try {
    const params = { limit, offset };
    if (category) params.category = category;
    const { data } = await api.get("/proactive/recommendations", { params });
    setCache(key, data);
    return data;
  } catch {
    return { recommendations: [], total: 0 };
  }
}

/**
 * Highest-priority next action for the current page.
 * @param {string} page - current pathname
 */
export async function getNextAction(page = "/") {
  const key = `next:${page}`;
  const cached = getCached(key);
  if (cached) return cached;
  try {
    const { data } = await api.get("/proactive/next-action", { params: { page } });
    setCache(key, data);
    return data;
  } catch {
    return { action: null };
  }
}

/**
 * Dismiss a recommendation (negative signal). Clears rec caches.
 */
export async function dismissRec(recId) {
  try {
    await api.post(`/proactive/recommendations/${recId}/dismiss`);
    invalidate("briefing", "recs:all:0", ...Object.keys(_cache).filter(k => k.startsWith("recs:")));
    return true;
  } catch {
    return false;
  }
}

/**
 * Accept/click a recommendation (positive signal).
 */
export async function acceptRec(recId) {
  try {
    await api.post(`/proactive/recommendations/${recId}/accept`);
    invalidate(...Object.keys(_cache).filter(k => k.startsWith("next:")));
    return true;
  } catch {
    return false;
  }
}

/**
 * Weekly behavioral + research insights.
 */
export async function getInsights() {
  const key = "insights";
  const cached = getCached(key);
  if (cached) return cached;
  try {
    const { data } = await api.get("/proactive/insights");
    setCache(key, data);
    return data;
  } catch {
    return { insights: [] };
  }
}

/**
 * Research health score with breakdown.
 */
export async function getHealthScore() {
  const key = "health";
  const cached = getCached(key);
  if (cached) return cached;
  try {
    const { data } = await api.get("/proactive/health-score");
    setCache(key, data);
    return data;
  } catch {
    return null;
  }
}

/**
 * Opportunity score with open item counts.
 */
export async function getOpportunityScore() {
  const key = "opportunity";
  const cached = getCached(key);
  if (cached) return cached;
  try {
    const { data } = await api.get("/proactive/opportunity-score");
    setCache(key, data);
    return data;
  } catch {
    return null;
  }
}
