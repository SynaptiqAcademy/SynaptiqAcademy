import { useEffect, useState, useCallback } from "react";
import api from "../lib/api";

/**
 * useReputation — fetch reputation for own user or a specific user ID.
 *
 * Returns { data, loading, error, refetch }.
 * data shape: { overall, research_score, teaching_score, community_score,
 *               collaboration, publication, reviewer, funding, activity, teaching,
 *               badges, computed_at, ... }
 */
export function useReputation(userId = "me") {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  const fetch_ = useCallback(async (force = false) => {
    setLoading(true);
    setError(null);
    try {
      const endpoint = userId === "me" ? "/reputation/me" : `/reputation/${userId}`;
      const { data: rep } = await api.get(endpoint, force ? { params: { force: true } } : {});
      setData(rep);
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => { fetch_(); }, [fetch_]);

  return { data, loading, error, refetch: () => fetch_(true) };
}

/**
 * useReputationBatch — batch-fetch reputation for an array of user IDs.
 * Returns a map { [userId]: reputationDoc }.
 */
export function useReputationBatch(userIds) {
  const [data, setData]       = useState({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!userIds || userIds.length === 0) return;
    setLoading(true);
    api
      .post("/reputation/batch", { user_ids: userIds.slice(0, 50) })
      .then(({ data: d }) => setData(d || {}))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [JSON.stringify(userIds)]); // eslint-disable-line react-hooks/exhaustive-deps

  return { data, loading };
}

// ── Helpers ──────────────────────────────────────────────────────────────────

export const LEVELS = [
  { min: 0,  max: 19,  label: "New Member",             short: "New",         tone: "border-slate-200 bg-slate-50 text-slate-500" },
  { min: 20, max: 39,  label: "Contributor",            short: "Contributor", tone: "border-slate-300 bg-slate-50 text-slate-700" },
  { min: 40, max: 59,  label: "Active Contributor",     short: "Active",      tone: "border-emerald-300 bg-emerald-50 text-emerald-800" },
  { min: 60, max: 79,  label: "Established Contributor", short: "Established", tone: "border-[#0F2847]/40 bg-[#0F2847]/5 text-[#0F2847]" },
  { min: 80, max: 100, label: "Distinguished Contributor", short: "Distinguished", tone: "border-amber-400 bg-amber-50 text-amber-800" },
];

export function getLevel(score) {
  const s = Math.round(score || 0);
  return LEVELS.find((l) => s >= l.min && s <= l.max) || LEVELS[0];
}

export function getNextLevel(score) {
  const s = Math.round(score || 0);
  return LEVELS.find((l) => l.min > s) || null;
}

export function getProgressToNextLevel(score) {
  const s      = Math.round(score || 0);
  const curr   = LEVELS.find((l) => s >= l.min && s <= l.max) || LEVELS[0];
  const range  = curr.max - curr.min + 1;
  const within = s - curr.min;
  return Math.round((within / range) * 100);
}

// ── Phase XX: Points-based reputation system ──────────────────────────────────

export const RESEARCH_LEVELS = [
  { level: 1, label: "Research Explorer",      short: "Explorer",      min: 0,    max: 99,      tone: "border-slate-200 bg-slate-50 text-slate-600" },
  { level: 2, label: "Emerging Researcher",    short: "Emerging",      min: 100,  max: 249,     tone: "border-emerald-200 bg-emerald-50 text-emerald-700" },
  { level: 3, label: "Active Researcher",      short: "Active",        min: 250,  max: 499,     tone: "border-blue-200 bg-blue-50 text-blue-700" },
  { level: 4, label: "Established Researcher", short: "Established",   min: 500,  max: 999,     tone: "border-indigo-200 bg-indigo-50 text-indigo-700" },
  { level: 5, label: "Advanced Researcher",    short: "Advanced",      min: 1000, max: 1999,    tone: "border-violet-200 bg-violet-50 text-violet-700" },
  { level: 6, label: "Research Leader",        short: "Leader",        min: 2000, max: 4999,    tone: "border-amber-300 bg-amber-50 text-amber-800" },
  { level: 7, label: "Distinguished Scholar",  short: "Distinguished", min: 5000, max: 9999999, tone: "border-yellow-400 bg-yellow-50 text-yellow-900" },
];

export function getResearchLevel(score) {
  const s = Math.round(score || 0);
  return RESEARCH_LEVELS.find((l) => s >= l.min && s <= l.max) || RESEARCH_LEVELS[0];
}

export function getResearchNextLevel(score) {
  const s = Math.round(score || 0);
  const idx = RESEARCH_LEVELS.findIndex((l) => s >= l.min && s <= l.max);
  if (idx === -1 || idx === RESEARCH_LEVELS.length - 1) return null;
  return RESEARCH_LEVELS[idx + 1];
}

export function getResearchProgress(score) {
  const s    = Math.round(score || 0);
  const curr = RESEARCH_LEVELS.find((l) => s >= l.min && s <= l.max) || RESEARCH_LEVELS[0];
  const next = getResearchNextLevel(s);
  if (!next) return 100;
  const range  = next.min - curr.min;
  const within = s - curr.min;
  return Math.min(100, Math.round((within / range) * 100));
}

export function useResearchReputation() {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  const fetch_ = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data: rep } = await api.get("/reputation/research/me");
      setData(rep);
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetch_(); }, [fetch_]);

  return { data, loading, error, refetch: fetch_ };
}

export function useReputationEvents(limit = 20) {
  const [data, setData]       = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  const fetch_ = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data: events } = await api.get("/reputation/events/me", { params: { limit } });
      setData(Array.isArray(events) ? events : []);
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }, [limit]);

  useEffect(() => { fetch_(); }, [fetch_]);

  return { data, loading, error, refetch: fetch_ };
}

export function useReputationAnalytics() {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  const fetch_ = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data: analytics } = await api.get("/reputation/analytics/me");
      setData(analytics);
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetch_(); }, [fetch_]);

  return { data, loading, error, refetch: fetch_ };
}
