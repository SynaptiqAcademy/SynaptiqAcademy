import { getAllPages } from "../config/navigation";

const LS_KEY = "sq_recent_pages";
const MAX_RECENT = 8;

// Build a static lookup: pathname → page object (label, icon, group)
const PAGE_MAP = (() => {
  const map = {};
  getAllPages().forEach((p) => { map[p.to] = p; });
  return map;
})();

/**
 * Record a page visit. Call this on every route change (e.g. in AppShell useEffect).
 * Only tracks known static paths — dynamic segments like /manuscripts/123 are silently skipped.
 */
export function trackPageVisit(pathname) {
  if (!PAGE_MAP[pathname]) return;
  try {
    const saved = JSON.parse(localStorage.getItem(LS_KEY) || "[]");
    const next = [pathname, ...saved.filter((p) => p !== pathname)].slice(0, MAX_RECENT);
    localStorage.setItem(LS_KEY, JSON.stringify(next));
  } catch {}
}

/**
 * Returns the most recently visited pages as page objects, most-recent first.
 * Safe to call outside of a React component (e.g. in CommandPalette's open effect).
 */
export function getRecentPages() {
  try {
    const saved = JSON.parse(localStorage.getItem(LS_KEY) || "[]");
    return saved.map((to) => PAGE_MAP[to]).filter(Boolean);
  } catch {
    return [];
  }
}
