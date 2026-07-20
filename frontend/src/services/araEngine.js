import api from "../lib/api";

// Missions
export const createMission    = (data)          => api.post("/ara/missions", data);
export const listMissions     = (status, limit) => api.get("/ara/missions", { params: { status, limit } });
export const getMission       = (id)            => api.get(`/ara/missions/${id}`);
export const approvePlan      = (id)            => api.post(`/ara/missions/${id}/approve-plan`);
export const refinePlan       = (id, data)      => api.post(`/ara/missions/${id}/refine-plan`, data);
export const pauseMission     = (id)            => api.post(`/ara/missions/${id}/pause`);
export const cancelMission    = (id)            => api.post(`/ara/missions/${id}/cancel`);
export const deleteMission    = (id)            => api.delete(`/ara/missions/${id}`);
export const getMissionSteps  = (id)            => api.get(`/ara/missions/${id}/steps`);
export const getMissionLogs   = (id, limit)     => api.get(`/ara/missions/${id}/logs`, { params: { limit } });
export const getMissionApprovals = (id)         => api.get(`/ara/missions/${id}/approvals`);

// Approvals
export const getPendingApprovals = ()          => api.get("/ara/approvals/pending");
export const approveAction       = (id)        => api.post(`/ara/approvals/${id}/approve`);
export const rejectAction        = (id, reason)=> api.post(`/ara/approvals/${id}/reject`, { reason });

// Agents
export const listAgents   = ()     => api.get("/ara/agents");
export const getAgent     = (name) => api.get(`/ara/agents/${name}`);

// Schedules
export const listSchedules  = ()     => api.get("/ara/schedules");
export const createSchedule = (data) => api.post("/ara/schedules", data);
export const deleteSchedule = (id)   => api.delete(`/ara/schedules/${id}`);

// Monitors
export const runMonitors   = ()      => api.post("/ara/monitors/run");
export const getMonitorAlerts = (limit) => api.get("/ara/monitors/alerts", { params: { limit } });

// Autonomy info
export const getAutonomyLevels = () => api.get("/ara/autonomy-levels");
