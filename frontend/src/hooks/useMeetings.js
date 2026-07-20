import { useState, useEffect, useCallback, useRef } from "react";
import api from "@/lib/api";

/**
 * Meetings data hooks — plain useState/useEffect + the shared `api` axios
 * instance, matching the pattern used across Messages.jsx / Workspaces (no
 * SWR/react-query in this codebase).
 */

function useApiResource(fetcher, deps) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const mounted = useRef(true);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetcher();
      if (mounted.current) setData(res);
    } catch (e) {
      if (mounted.current) setError(e);
    } finally {
      if (mounted.current) setLoading(false);
    }
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    mounted.current = true;
    reload();
    return () => { mounted.current = false; };
  }, [reload]);

  return { data, loading, error, reload, setData };
}

export function useMeetingsList(filters = {}) {
  const key = JSON.stringify(filters);
  return useApiResource(
    async () => (await api.get("/meetings", { params: filters })).data,
    [key],
  );
}

export function useMeetingKpis() {
  return useApiResource(async () => (await api.get("/meetings/kpis")).data, []);
}

export function useMeetingCategories() {
  return useApiResource(async () => (await api.get("/meetings/categories")).data, []);
}

export function useMeetingCalendar(month) {
  return useApiResource(
    async () => (await api.get("/meetings/calendar", { params: month ? { month } : {} })).data,
    [month],
  );
}

export function useMeetingDetail(id) {
  return useApiResource(
    async () => (id ? (await api.get(`/meetings/${id}`)).data : null),
    [id],
  );
}

export function useMeetingActionItems(filters = {}) {
  const key = JSON.stringify(filters);
  return useApiResource(
    async () => (await api.get("/meetings/action-items", { params: filters })).data,
    [key],
  );
}

export async function createMeeting(payload) {
  return (await api.post("/meetings", payload)).data;
}

export async function updateMeeting(id, payload) {
  return (await api.patch(`/meetings/${id}`, payload)).data;
}

export async function deleteMeeting(id) {
  return (await api.delete(`/meetings/${id}`)).data;
}

export async function addMeetingNote(id, body) {
  return (await api.post(`/meetings/${id}/notes`, { body })).data;
}

export async function addActionItem(meetingId, payload) {
  return (await api.post(`/meetings/${meetingId}/action-items`, payload)).data;
}

export async function updateActionItem(itemId, payload) {
  return (await api.patch(`/meetings/action-items/${itemId}`, payload)).data;
}

export async function deleteActionItem(itemId) {
  return (await api.delete(`/meetings/action-items/${itemId}`)).data;
}

export async function importIcs(file) {
  const form = new FormData();
  form.append("file", file);
  return (await api.post("/meetings/import-ics", form, {
    headers: { "Content-Type": "multipart/form-data" },
  })).data;
}

const AI_ENDPOINTS = {
  agenda: "agenda",
  summary: "summary",
  actionItems: "action-items",
  decisions: "decisions",
  followUpEmail: "follow-up-email",
  nextSteps: "next-steps",
  manuscriptTodo: "manuscript-todo",
  grantFollowUp: "grant-follow-up",
};

export async function runMeetingAI(meetingId, kind, instructions) {
  const path = AI_ENDPOINTS[kind] || kind;
  return (await api.post(`/meetings/${meetingId}/ai/${path}`, { instructions })).data;
}
