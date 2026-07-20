import api from "../lib/api";

// ── Core twin ─────────────────────────────────────────────────────────────────

export const getMyTwin       = ()             => api.get("/twin/me");
export const syncTwin        = ()             => api.post("/twin/sync");
export const getProfile      = ()             => api.get("/twin/profile");
export const getWorkingStyle = ()             => api.get("/twin/working-style");
export const getHealth       = ()             => api.get("/twin/health");
export const getAIContext    = ()             => api.get("/twin/ai-context");

// ── Goals ─────────────────────────────────────────────────────────────────────

export const listGoals   = (status)     => api.get("/twin/goals", { params: status ? { status } : {} });
export const createGoal  = (body)       => api.post("/twin/goals", body);
export const updateGoal  = (id, body)   => api.put(`/twin/goals/${id}`, body);
export const deleteGoal  = (id)         => api.delete(`/twin/goals/${id}`);

// ── Timeline ──────────────────────────────────────────────────────────────────

export const getTimeline       = ()     => api.get("/twin/timeline");
export const getDomainEvolution = ()    => api.get("/twin/timeline/domains");

// ── Recommendations ───────────────────────────────────────────────────────────

export const getRecommendations = ()    => api.get("/twin/recommendations");

// ── Simulations ───────────────────────────────────────────────────────────────

export const runSimulation = (body)     => api.post("/twin/simulation", body);

// ── Events ────────────────────────────────────────────────────────────────────

export const getEvents  = (limit = 20)  => api.get("/twin/events", { params: { limit } });
export const emitEvent  = (event_type, payload = {}) => api.post("/twin/events", { event_type, payload });

// ── Explainability ────────────────────────────────────────────────────────────

export const explainDomain       = (domain)        => api.get(`/twin/explain/domain/${encodeURIComponent(domain)}`);
export const explainWorkingStyle = (index)         => api.get(`/twin/explain/working-style/${index}`);
export const explainHealth       = (indicatorId)   => api.get(`/twin/explain/health/${indicatorId}`);

// ── History ───────────────────────────────────────────────────────────────────

export const getHistory = (limit = 10)  => api.get("/twin/history", { params: { limit } });

// ── Settings / User control ───────────────────────────────────────────────────

export const updatePrivacy   = (body)              => api.put("/twin/settings/privacy", body);
export const correctInsight  = (field, value)      => api.post("/twin/settings/correct", { field, value });
export const resetPreferences = ()                 => api.post("/twin/settings/reset");
export const excludeItem     = (item_type, item_id) => api.post("/twin/settings/exclude", { item_type, item_id });
