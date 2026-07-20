import {
  NAV_SECTIONS,
  findSectionForPath,
  findSubGroupForPath,
  getAllPages,
} from "@/config/navigation";

// Build a static pathname → page label map
const LABEL_MAP = (() => {
  const m = {};
  getAllPages().forEach((p) => { m[p.to] = p.label; });
  return m;
})();

// Paths where breadcrumbs should not appear (home-like pages)
const HIDDEN = new Set(["/", "/discover", "/today", "/copilot", "/living-graph", "/twin", "/agent-workforce"]);

/**
 * getBreadcrumbTrail — the one breadcrumb-trail derivation used by both the
 * app and admin shells (via ds/ContentFrame). Returns null when no trail
 * should render (home-like pages, unrecognised routes).
 *
 * Dynamic detail routes (e.g. /projects/:id) aren't in the page label map,
 * so the trail falls back to ending at the nearest known section/subgroup
 * crumb (shown as the current, unlinked page) rather than a raw id segment.
 *
 * Returns [{ label, to? }] — ds/Breadcrumb's items shape (last entry has no
 * `to`, rendered as the current page).
 */
export function getBreadcrumbTrail(pathname) {
  if (HIDDEN.has(pathname)) return null;

  const sectionId = findSectionForPath(pathname);
  if (!sectionId) return null;

  const section = NAV_SECTIONS[sectionId];

  // First direct-route item in the section (skip subgroups) → used as section link
  const sectionTo = section.items.find((i) => !i._type && i.to)?.to;

  const crumbs = [{ label: section.label, to: sectionTo }];

  // Sub-group label (if the current path lives inside one)
  const subgroupId = findSubGroupForPath(sectionId, pathname);
  if (subgroupId) {
    const sg = section.items.find((i) => i.id === subgroupId);
    if (sg) {
      crumbs.push({ label: sg.label, to: sg.items[0]?.to });
    }
  }

  // Leaf page label — only add when it's different from the last crumb.
  // (ds/Breadcrumb always renders the final item as the current, unlinked
  // page regardless of its `to`, so dynamic/unknown segments — e.g.
  // /projects/abc123 — correctly fall back to the section/sub-group crumb.)
  const pageLabel = LABEL_MAP[pathname];
  if (pageLabel && pageLabel !== crumbs[crumbs.length - 1].label) {
    crumbs.push({ label: pageLabel, to: null });
  }

  return crumbs.length > 0 ? crumbs : null;
}

export default getBreadcrumbTrail;
