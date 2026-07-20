import { getAllAdminPages } from "../config/adminNavigation";

// Separate localStorage key from the researcher-facing sq_recent_pages, so
// admin navigation doesn't pollute the researcher "Recent" list and vice versa.
const LS_KEY = "sq_admin_recent_pages";
const MAX_RECENT = 8;

const PAGE_MAP = (() => {
  const map = {};
  getAllAdminPages().forEach((p) => { map[p.to] = p; });
  return map;
})();

export function trackAdminPageVisit(pathname) {
  if (!PAGE_MAP[pathname]) return;
  try {
    const saved = JSON.parse(localStorage.getItem(LS_KEY) || "[]");
    const next = [pathname, ...saved.filter((p) => p !== pathname)].slice(0, MAX_RECENT);
    localStorage.setItem(LS_KEY, JSON.stringify(next));
  } catch {}
}

export function getRecentAdminPages() {
  try {
    const saved = JSON.parse(localStorage.getItem(LS_KEY) || "[]");
    return saved.map((to) => PAGE_MAP[to]).filter(Boolean);
  } catch {
    return [];
  }
}
