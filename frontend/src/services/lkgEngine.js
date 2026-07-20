import api from "../lib/api";

// ── Node queries ──────────────────────────────────────────────────────────

export const getStats          = ()                     => api.get("/lkg/stats");
export const listNodes         = (nodeType, limit = 50) => api.get("/lkg/nodes", { params: { node_type: nodeType, limit } });
export const getNode           = (nodeId)               => api.get(`/lkg/nodes/${encodeURIComponent(nodeId)}`);
export const getNodeEdges      = (nodeId, direction)    => api.get(`/lkg/nodes/${encodeURIComponent(nodeId)}/edges`, { params: { direction } });
export const getNeighbors      = (nodeId, depth = 1)    => api.get(`/lkg/nodes/${encodeURIComponent(nodeId)}/neighbors`, { params: { depth } });
export const getSubgraph       = (nodeId, depth = 2)    => api.get(`/lkg/nodes/${encodeURIComponent(nodeId)}/subgraph`, { params: { depth } });
export const getNodeTimeline   = (nodeId)               => api.get(`/lkg/nodes/${encodeURIComponent(nodeId)}/timeline`);

// ── Path finding ──────────────────────────────────────────────────────────

export const findPath = (fromId, toId, maxDepth = 4) =>
  api.get("/lkg/path", { params: { from_id: fromId, to_id: toId, max_depth: maxDepth } });

// ── Search ────────────────────────────────────────────────────────────────

export const searchGraph = (q, types, limit = 20) =>
  api.get("/lkg/search", { params: { q, types, limit } });

// ── Analytics ─────────────────────────────────────────────────────────────

export const getTopicTrends    = (months = 12)    => api.get("/lkg/analytics/topic-trends",         { params: { months } });
export const getEntityGrowth   = (nodeType, months = 12) => api.get("/lkg/analytics/entity-growth", { params: { node_type: nodeType, months } });
export const getCollabDensity  = ()               => api.get("/lkg/analytics/collaboration-density");

// ── Temporal ─────────────────────────────────────────────────────────────

export const getSnapshot = (year, month) => api.get("/lkg/snapshot", { params: { year, month } });

// ── Reasoning ─────────────────────────────────────────────────────────────

export const getCommunities  = ()       => api.get("/lkg/reasoning/communities");
export const getCentrality   = (nodeType, limit = 20) => api.get("/lkg/reasoning/centrality", { params: { node_type: nodeType, limit } });

// ── Insights ──────────────────────────────────────────────────────────────

export const getMyInsights       = () => api.get("/lkg/insights/me");
export const getPlatformInsights = () => api.get("/lkg/insights/platform");

// ── Discovery ─────────────────────────────────────────────────────────────

export const discoverCollaborators = () => api.get("/lkg/discovery/collaborators");
export const discoverTopics        = () => api.get("/lkg/discovery/topics");
export const discoverFunding       = () => api.get("/lkg/discovery/funding");
export const discoverReviewers     = (manuscriptId) => api.get(`/lkg/discovery/reviewers/${manuscriptId}`);

// ── My graph ──────────────────────────────────────────────────────────────

export const getMyNode     = ()                   => api.get("/lkg/my-node");
export const getMySubgraph = (depth = 2)          => api.get("/lkg/my-subgraph", { params: { depth } });

// ── Admin ─────────────────────────────────────────────────────────────────

export const runIngestion  = (connector, topics = []) => api.post("/lkg/admin/ingest", { connector, topics });
export const initIndexes   = ()                       => api.post("/lkg/admin/init-indexes");
export const getJobs       = ()                       => api.get("/lkg/admin/jobs");
