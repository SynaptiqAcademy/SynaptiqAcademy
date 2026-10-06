/**
 * The Synaptiq Blog — single source for /resources/blog and
 * /resources/blog/:slug.
 *
 * Editorial rules (enforced by tests):
 * - A post is public only with `status: "published"` and complete metadata.
 *   Drafts and archived posts are never listed, routed, linked or indexed.
 * - Bylines are real: a named person with an approved short bio, or the
 *   publisher identity "Synaptiq Editorial". No invented roles or credentials.
 * - Dates are real. `updated_at` only for substantive revisions.
 * - Reading time is calculated from the body.
 * - Any factual or numerical claim carries a real, checkable reference.
 *
 * Post shape:
 * {
 *   slug, title, deck,                    // deck: one or two sentences under the title
 *   category: "collaboration",            // key of CATEGORIES
 *   status: "draft" | "published" | "archived",
 *   published_at: "2026-10-06", updated_at?: "…",
 *   author: { name: "Synaptiq Editorial", bio?: "…" },
 *   featured?: true,                      // editorial selection, never popularity
 *   body: [{ h }, { p }, { quote }, { list: [] }, { figure: { caption, alt, rows?: [[…]] } }],
 *   references?: [{ text, url? }],
 *   related?: { resources?: ["slug"], posts?: ["slug"], product?: { label, href } },
 * }
 */

export const CATEGORIES = {
  practice: "Research practice",
  collaboration: "Collaboration",
  publishing: "Publishing",
  technology: "Research technology",
  teaching: "Teaching",
  institutions: "Institutions",
};

/** No posts are published yet. Add posts here once they pass editorial review. */
export const POSTS = [];

const REQUIRED = ["slug", "title", "deck", "category", "published_at"];

export function isPublished(p) {
  return p && p.status === "published"
    && REQUIRED.every((k) => p[k] !== undefined && p[k] !== null && String(p[k]).trim() !== "")
    && Object.prototype.hasOwnProperty.call(CATEGORIES, p.category)
    && /^\d{4}-\d{2}-\d{2}$/.test(p.published_at)
    && p.author && String(p.author.name || "").trim() !== ""
    && Array.isArray(p.body) && p.body.length > 0;
}

export function wordCount(p) {
  const text = (p.body || []).map((b) => b.h || b.p || b.quote || (b.list || []).join(" ") || "").join(" ");
  return (text.match(/\S+/g) || []).length;
}

/** Minutes at 220 words a minute, rounded up, minimum 1. */
export function readingMinutes(p) {
  return Math.max(1, Math.ceil(wordCount(p) / 220));
}

/** Newest first. */
export function publishedPosts(list = POSTS) {
  return list.filter(isPublished).sort((a, b) => b.published_at.localeCompare(a.published_at));
}

export function findPost(slug, list = POSTS) {
  return publishedPosts(list).find((p) => p.slug === slug) || null;
}

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export function formatDate(iso) {
  const [y, m, d] = String(iso).split("-");
  return y && m && d ? `${Number(d)} ${MONTHS[Number(m) - 1]} ${y}` : "";
}

/** Headings for a table of contents, only for long pieces. */
export function tocFor(p, minWords = 1800) {
  if (wordCount(p) < minWords) return [];
  return (p.body || []).filter((b) => b.h).map((b) => ({ id: slugify(b.h), text: b.h }));
}

export function slugify(s) {
  return String(s).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}
