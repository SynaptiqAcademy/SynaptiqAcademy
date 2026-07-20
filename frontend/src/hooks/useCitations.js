/**
 * React hooks for the Citation Monitoring module.
 *
 * All hooks use local state + useEffect (no external state library required).
 * Each hook returns { data, loading, error, refetch }.
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

// ─────────────────────────── dashboard ───────────────────────────────────────

export function useCitationDashboard() {
  return useFetch("/citations/dashboard");
}

// ─────────────────────────── research areas ───────────────────────────────────

export function useResearchAreas() {
  return useFetch("/citations/research-areas");
}

// ─────────────────────────── impact score ────────────────────────────────────

export function useCitationImpactScore() {
  return useFetch("/citations/impact-score");
}

// ─────────────────────────── alerts ──────────────────────────────────────────

export function useCitationAlerts({ unreadOnly = false } = {}) {
  const url = `/citations/alerts${unreadOnly ? "?unread_only=true" : ""}`;
  return useFetch(url);
}

// ─────────────────────────── publication detail ───────────────────────────────

export function usePublicationDetail(pubId) {
  return useFetch(`/citations/publications/${pubId}`, { skip: !pubId });
}

// ─────────────────────────── gap opportunities ───────────────────────────────

export function useGapOpportunities({ topic = "", keywords = "", gapId = null, skip = false } = {}) {
  const params = new URLSearchParams();
  if (topic)    params.set("topic",    topic);
  if (keywords) params.set("keywords", keywords);
  if (gapId)    params.set("gap_id",  gapId);
  const url = `/citations/gap-opportunities?${params.toString()}`;
  return useFetch(url, { skip });
}

// ─────────────────────────── sync actions ────────────────────────────────────

export function useCitationSync() {
  const [syncing, setSyncing]   = useState(false);
  const [result,  setResult]    = useState(null);
  const [error,   setError]     = useState(null);

  const syncAll = useCallback(async () => {
    setSyncing(true);
    setError(null);
    try {
      const r = await api.post("/citations/sync");
      setResult(r.data);
      return r.data;
    } catch (e) {
      const msg = e?.response?.data?.detail || "Sync failed";
      setError(msg);
      throw new Error(msg);
    } finally {
      setSyncing(false);
    }
  }, []);

  const syncOne = useCallback(async (pubId) => {
    setSyncing(true);
    setError(null);
    try {
      const r = await api.post(`/citations/sync/${pubId}`);
      setResult(r.data);
      return r.data;
    } catch (e) {
      const msg = e?.response?.data?.detail || "Sync failed";
      setError(msg);
      throw new Error(msg);
    } finally {
      setSyncing(false);
    }
  }, []);

  const importOrcid = useCallback(async () => {
    setSyncing(true);
    setError(null);
    try {
      const r = await api.post("/citations/import-orcid");
      setResult(r.data);
      return r.data;
    } catch (e) {
      const msg = e?.response?.data?.detail || "ORCID import failed";
      setError(msg);
      throw new Error(msg);
    } finally {
      setSyncing(false);
    }
  }, []);

  return { syncing, result, error, syncAll, syncOne, importOrcid };
}
