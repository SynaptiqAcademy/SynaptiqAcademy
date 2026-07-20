/**
 * React hooks for the Research Impact Dashboard (pro_researcher gate).
 * All hooks use the same useFetch pattern as useCitations.js.
 */
import { useState, useEffect, useCallback } from "react";
import api from "../lib/api";

// ─────────────────────────── generic fetcher ──────────────────────────────────

function useFetch(url, { skip = false, deps = [] } = {}) {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(!skip);
  const [error, setError]     = useState(null);

  const fetch_ = useCallback(() => {
    if (skip) return;
    setLoading(true);
    setError(null);
    api.get(url)
      .then((r) => setData(r.data))
      .catch((e) => setError(e?.response?.data?.detail || "Request failed"))
      .finally(() => setLoading(false));
  }, [url, skip]);

  useEffect(() => { fetch_(); }, [fetch_, ...deps]);

  return { data, loading, error, refetch: fetch_ };
}

// ─────────────────────────── full dashboard ───────────────────────────────────

export function useResearchImpactDashboard() {
  return useFetch("/research-impact/dashboard");
}

// ─────────────────────────── citation chart ───────────────────────────────────

export function useImpactCitationChart(period = "365d") {
  return useFetch(`/research-impact/citations?period=${period}`, { deps: [period] });
}

// ─────────────────────────── goals ────────────────────────────────────────────

export function useResearchGoals() {
  return useFetch("/research-impact/goals");
}

export function useSaveGoals() {
  const [saving, setSaving] = useState(false);
  const [error, setError]   = useState(null);

  const save = useCallback(async (goals) => {
    setSaving(true);
    setError(null);
    try {
      const { data } = await api.put("/research-impact/goals", goals);
      return data;
    } catch (e) {
      const msg = e?.response?.data?.detail || "Failed to save goals";
      setError(msg);
      throw new Error(msg);
    } finally {
      setSaving(false);
    }
  }, []);

  return { save, saving, error };
}
