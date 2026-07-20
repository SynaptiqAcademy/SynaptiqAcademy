/**
 * useUserMemory — Synaptiq adaptive intelligence layer (Phase XXIX).
 *
 * Pure JS module (no React hooks), safe to call anywhere.
 * Stores visit frequency + weekly stats in localStorage.
 * Used by: Today.jsx, WorkflowLauncher, CommandPalette, AppShell.
 *
 * localStorage key: sq_mem_v1
 */

const KEY = "sq_mem_v1";

// ── ISO week key (Mon-start) ──────────────────────────────────────────────────

function weekKey(date = new Date()) {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  d.setUTCDate(d.getUTCDate() + 4 - (d.getUTCDay() || 7));
  const yr = d.getUTCFullYear();
  const wk = Math.ceil(((d - Date.UTC(yr, 0, 1)) / 86400000 + 1) / 7);
  return `${yr}-W${String(wk).padStart(2, "0")}`;
}

// ── Storage ───────────────────────────────────────────────────────────────────

function defaults() {
  return { visits: {}, lastVisit: {}, week: { key: null, visits: {} } };
}

function load() {
  try {
    return Object.assign(defaults(), JSON.parse(localStorage.getItem(KEY) || "{}"));
  } catch {
    return defaults();
  }
}

function save(mem) {
  try { localStorage.setItem(KEY, JSON.stringify(mem)); } catch {}
}

// ── Public API ────────────────────────────────────────────────────────────────

/** Record a page visit. Call on every pathname change (AppShell). */
export function recordVisit(pathname) {
  if (!pathname || pathname.length < 2) return;
  const mem = load();
  mem.visits[pathname] = (mem.visits[pathname] || 0) + 1;
  mem.lastVisit[pathname] = Date.now();
  const wk = weekKey();
  if (mem.week.key !== wk) mem.week = { key: wk, visits: {} };
  mem.week.visits[pathname] = (mem.week.visits[pathname] || 0) + 1;
  save(mem);
}

/** Top n most-visited paths overall (most-visited first). */
export function getTopPaths(n = 8) {
  const mem = load();
  return Object.entries(mem.visits)
    .sort(([, a], [, b]) => b - a)
    .slice(0, n)
    .map(([p]) => p);
}

/** Top n most-visited paths this ISO week. */
export function getWeekTopPaths(n = 6) {
  const mem = load();
  const wk = weekKey();
  if (mem.week.key !== wk) return [];
  return Object.entries(mem.week.visits)
    .sort(([, a], [, b]) => b - a)
    .slice(0, n)
    .map(([p]) => p);
}

/** Total visit count across all pages. */
export function getTotalVisits() {
  const mem = load();
  return Object.values(mem.visits).reduce((a, b) => a + b, 0);
}

/**
 * Infer working mode from recent paths.
 * Returns: "writing" | "grant" | "teaching" | "admin" | "review" | "research"
 */
export function inferMode(paths = []) {
  const str = paths.join(" ");
  const score = {
    writing:  (str.match(/\/manuscript|\/abstract|\/rewrite|\/publication-hub/g) || []).length,
    grant:    (str.match(/\/grant|\/funding/g) || []).length,
    teaching: (str.match(/\/teaching|\/lesson|\/assessment|\/portfolio/g) || []).length,
    admin:    (str.match(/\/institution-platform|\/executive|\/institution-hub/g) || []).length,
    review:   (str.match(/\/manuscript-review|\/reviewer/g) || []).length,
  };
  const max = Math.max(...Object.values(score));
  if (max === 0) return "research";
  return Object.entries(score).find(([, v]) => v === max)?.[0] || "research";
}

/**
 * Re-rank QUICK_ACTIONS by the user's most-visited tools.
 * Returns a copy with most-used tools first.
 * Falls back to original order when fewer than 4 visits are recorded.
 */
export function rankActions(quickActions) {
  const top = getTopPaths(20);
  if (top.length < 4) return quickActions;
  const rank = {};
  top.forEach((p, i) => { rank[p] = i; });
  return [...quickActions].sort((a, b) => (rank[a.to] ?? 999) - (rank[b.to] ?? 999));
}

/**
 * Generate behavioral insights for the Today page.
 * Returns array of { id, text, icon, to? }
 * icon is one of: "brain" | "trending" | "star" | "arrow" | "activity"
 */
export function generateInsights() {
  const top      = getTopPaths(5);
  const weekTop  = getWeekTopPaths(3);
  const total    = getTotalVisits();
  const mode     = inferMode(top);
  const results  = [];

  const modeLabel = {
    writing:  "manuscript writing",
    grant:    "grant applications",
    teaching: "teaching preparation",
    admin:    "institution management",
    review:   "manuscript review",
  }[mode];

  if (modeLabel && top.length > 2) {
    results.push({
      id: "mode", icon: "brain",
      text: `Your recent activity centers on ${modeLabel}. Quick Actions are sorted accordingly.`,
    });
  }

  if (weekTop.length > 0) {
    const name = weekTop[0].split("/").filter(Boolean).pop()?.replace(/-/g, " ") || weekTop[0];
    results.push({
      id: "week_top", icon: "trending",
      text: `Most-used tool this week: ${name.charAt(0).toUpperCase() + name.slice(1)}.`,
    });
  }

  if (total > 0 && total >= 50 && total % 50 === 0) {
    results.push({ id: "milestone", icon: "star", text: `Milestone: ${total} tool visits on Synaptiq.` });
  }

  // Workflow continuation suggestions
  const has = (kw) => top.some(p => p.includes(kw));

  if (has("manuscript") && !has("journal")) {
    results.push({ id: "next_journal", icon: "arrow", to: "/journals",
      text: "You've been writing — Journal Finder is your natural next step." });
  }
  if ((has("grant") || has("funding")) && !has("collaboration")) {
    results.push({ id: "next_collab", icon: "arrow", to: "/grant-collaboration-hub",
      text: "Grant applications are stronger with collaborators. Consider Grant Teams." });
  }
  if (has("literature-review") && !has("research-gap")) {
    results.push({ id: "next_gap", icon: "arrow", to: "/research-gap-finder",
      text: "After Literature Review, Research Gap Finder is the logical next step." });
  }
  if (has("research-gap") && !has("statistical")) {
    results.push({ id: "next_stat", icon: "arrow", to: "/statistical-review",
      text: "Ready to validate your gap? Statistical Review helps with study design." });
  }

  return results.slice(0, 4);
}
