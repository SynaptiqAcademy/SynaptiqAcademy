/**
 * React hooks for Department Management (institutional subscribers).
 * All hooks use the same useFetch pattern as useCitations.js.
 */
import { useState, useEffect, useCallback } from "react";
import api from "../lib/api";

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

  const depsKey = JSON.stringify(deps);
  useEffect(() => { fetch_(); }, [fetch_, depsKey]);
  return { data, loading, error, refetch: fetch_ };
}

// ─────────────────────────────────────────────────────────────────────────────

export function useDepartments(institutionId, query = "") {
  const url = institutionId
    ? `/institutions/${institutionId}/departments${query ? `?q=${encodeURIComponent(query)}` : ""}`
    : null;
  return useFetch(url, { skip: !institutionId, deps: [institutionId, query] });
}

export function useDepartment(did) {
  return useFetch(did ? `/departments/${did}` : null, { skip: !did, deps: [did] });
}

export function useDeptMembers(did) {
  return useFetch(did ? `/departments/${did}/members` : null, { skip: !did, deps: [did] });
}

export function useDeptProjects(did) {
  return useFetch(did ? `/departments/${did}/projects` : null, { skip: !did, deps: [did] });
}

export function useDeptMetrics(did, refresh = false) {
  const url = did ? `/departments/${did}/metrics${refresh ? "?refresh=true" : ""}` : null;
  return useFetch(url, { skip: !did, deps: [did, refresh] });
}

export function useDeptRankings(did) {
  return useFetch(did ? `/departments/${did}/rankings` : null, { skip: !did, deps: [did] });
}

export function useDeptCollaboration(did) {
  return useFetch(did ? `/departments/${did}/collaboration` : null, { skip: !did, deps: [did] });
}

export function useDeptPublications(did) {
  return useFetch(did ? `/departments/${did}/publications` : null, { skip: !did, deps: [did] });
}

export function useDeptFunding(did) {
  return useFetch(did ? `/departments/${did}/funding` : null, { skip: !did, deps: [did] });
}

// ─────────────────────────── mutations ───────────────────────────────────────

export function useDeptMutations() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  const run = useCallback(async (fn) => {
    setBusy(true);
    setError(null);
    try {
      return await fn();
    } catch (e) {
      const msg = e?.response?.data?.detail?.message
        || e?.response?.data?.detail
        || e?.response?.data
        || "Operation failed";
      setError(typeof msg === "string" ? msg : JSON.stringify(msg));
      throw e;
    } finally {
      setBusy(false);
    }
  }, []);

  const createDepartment = useCallback((iid, payload) =>
    run(() => api.post(`/institutions/${iid}/departments`, payload).then((r) => r.data)),
    [run]);

  const updateDepartment = useCallback((did, payload) =>
    run(() => api.patch(`/departments/${did}`, payload).then((r) => r.data)),
    [run]);

  const deleteDepartment = useCallback((did) =>
    run(() => api.delete(`/departments/${did}`).then((r) => r.data)),
    [run]);

  const manageMembers = useCallback((did, user_ids, action) =>
    run(() => api.post(`/departments/${did}/members`, { user_ids, action }).then((r) => r.data)),
    [run]);

  const updateRole = useCallback((did, uid, role) =>
    run(() => api.patch(`/departments/${did}/members/${uid}/role`, { role }).then((r) => r.data)),
    [run]);

  const linkProject = useCallback((did, project_id) =>
    run(() => api.post(`/departments/${did}/projects`, { project_id }).then((r) => r.data)),
    [run]);

  const unlinkProject = useCallback((did, pid) =>
    run(() => api.delete(`/departments/${did}/projects/${pid}`).then((r) => r.data)),
    [run]);

  return {
    busy, error, setError,
    createDepartment, updateDepartment, deleteDepartment,
    manageMembers, updateRole, linkProject, unlinkProject,
  };
}
