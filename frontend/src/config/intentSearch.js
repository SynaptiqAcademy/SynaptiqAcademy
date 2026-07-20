/**
 * intentSearch.js — Smart intent-based search for the CommandPalette (Phase XXIX).
 *
 * When a user types a goal ("submit paper", "find grant", "teach lesson") the
 * palette returns relevant pages even if their label doesn't match the query.
 *
 * Usage:
 *   import { intentSearch } from "../config/intentSearch";
 *   const results = intentSearch(query, getAllPages());
 */

const INTENT_MAP = [
  {
    phrases: ["submit", "publish paper", "submit paper", "submission", "where to publish", "send manuscript"],
    routes:  ["/manuscripts", "/journals", "/publication-hub", "/manuscript-review"],
  },
  {
    phrases: ["write", "writing", "draft", "paper", "manuscript"],
    routes:  ["/manuscripts", "/manuscript-review", "/ai/rewrite", "/ai/abstract"],
  },
  {
    phrases: ["grant", "funding", "apply", "fund my research", "scholarship", "research funding"],
    routes:  ["/grants", "/funding", "/grant-applications", "/grant-collaboration-hub"],
  },
  {
    phrases: ["collaborat", "partner", "coauthor", "co-author", "find people", "team up", "co-investigator"],
    routes:  ["/collaboration-intelligence", "/collaborations", "/network"],
  },
  {
    phrases: ["review", "reviewer", "peer review", "review request", "referee"],
    routes:  ["/manuscript-review", "/reviewer-marketplace", "/reviews"],
  },
  {
    phrases: ["stat", "statistics", "analysis", "data analysis", "methodology", "study design", "method"],
    routes:  ["/statistical-review", "/research-design-advisor"],
  },
  {
    phrases: ["gap", "research gap", "research question", "unexplored", "open problem"],
    routes:  ["/research-gap-finder"],
  },
  {
    phrases: ["literature", "read papers", "synthesis", "meta-analysis", "survey", "systematic review"],
    routes:  ["/literature-review"],
  },
  {
    phrases: ["teach", "lesson", "course", "class", "assessment", "syllabus", "students", "learning"],
    routes:  ["/teaching/lesson-planner", "/teaching/assessment-builder", "/teaching/workspaces", "/teaching"],
  },
  {
    phrases: ["institution", "department", "faculty", "university admin", "administration", "unit"],
    routes:  ["/institution-hub", "/institution/departments", "/institution/analytics"],
  },
  {
    phrases: ["profile", "orcid", "reputation", "h-index", "academic profile", "bio"],
    routes:  ["/academic-passport", "/research-impact", "/reputation"],
  },
  {
    phrases: ["citation", "cite", "citing", "track citation", "who cited", "citation alert"],
    routes:  ["/citation-monitoring", "/citations"],
  },
  {
    phrases: ["journal", "journal finder", "impact factor", "open access", "best journal"],
    routes:  ["/journals"],
  },
  {
    phrases: ["abstract", "generate abstract", "write abstract", "summarize paper"],
    routes:  ["/ai/abstract"],
  },
  {
    phrases: ["network", "discover researchers", "find researchers", "meet researchers", "community"],
    routes:  ["/network", "/collaboration-intelligence"],
  },
  {
    phrases: ["plan", "roadmap", "goals", "research plan", "schedule", "agenda", "planner"],
    routes:  ["/sie/goals", "/sie/planning", "/timeline"],
  },
  {
    phrases: ["impact", "metrics", "influence", "benchmark", "h index", "research output"],
    routes:  ["/research-impact", "/analytics"],
  },
  {
    phrases: ["verify", "trust", "credential", "verified", "verification", "badge"],
    routes:  ["/verification", "/trust"],
  },
  {
    phrases: ["ai", "assistant", "research ai", "synaptiq ai", "ask ai", "ai chat"],
    routes:  ["/ai"],
  },
  {
    phrases: ["project", "workspace", "new project", "start project", "research project"],
    routes:  ["/projects", "/workspaces"],
  },
  {
    phrases: ["rewrite", "paraphrase", "improve writing", "edit text", "rephrase"],
    routes:  ["/ai/rewrite"],
  },
  {
    phrases: ["conference", "conference finder", "cfp", "call for papers"],
    routes:  ["/conferences"],
  },
  {
    phrases: ["knowledge graph", "graph", "explore connections", "semantic", "ontology"],
    routes:  ["/akg", "/akg/explorer"],
  },
  {
    phrases: ["marketplace", "service", "expert", "hire researcher"],
    routes:  ["/academic-marketplace", "/expertise"],
  },
  {
    phrases: ["today", "daily", "agenda", "what to do", "priority", "tasks"],
    routes:  ["/today", "/sie/daily-agenda"],
  },
];

/**
 * Returns page objects that match the user's intent (not just page name).
 * Returns [] when query is too short or has no intent match.
 *
 * @param {string} query    Raw search query
 * @param {Array}  allPages Full page list from getAllPages()
 * @returns {Array}         Ranked page objects
 */
export function intentSearch(query, allPages) {
  const q = query.toLowerCase().trim();
  if (q.length < 2) return [];

  const matched = [];
  for (const { phrases, routes } of INTENT_MAP) {
    if (phrases.some(p => q.includes(p) || p.includes(q))) {
      routes.forEach(r => { if (!matched.includes(r)) matched.push(r); });
    }
  }
  if (matched.length === 0) return [];

  const rank = {};
  matched.forEach((r, i) => { rank[r] = i; });

  return allPages
    .filter(p => rank[p.to] !== undefined)
    .sort((a, b) => rank[a.to] - rank[b.to]);
}
