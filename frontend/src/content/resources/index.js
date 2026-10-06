/**
 * The Synaptiq research library — single source for /resources and
 * /resources/guides/:slug.
 *
 * A guide is published only when `status: "published"` AND it passes
 * isPublishable() below. Anything else (draft, missing fields) is never
 * listed, routed or indexed. Reading time is calculated from the body, never
 * typed in. Numbers are assigned once and never reused, so a guide keeps its
 * catalogue number for life.
 *
 * Guide shape:
 * {
 *   number: 1,                         // stable catalogue number
 *   slug: "turning-a-topic-into-a-research-question",
 *   title: "…",
 *   description: "…",                  // one sentence, used in the index and meta description
 *   type: "guide",                     // guide | explainer | workflow | reference (see TYPES)
 *   task: "define",                    // key of TASKS
 *   status: "draft",                   // draft | published
 *   published_at: "2026-10-06",        // ISO date, required to publish
 *   updated_at: "2026-10-06",          // optional
 *   byline: "Synaptiq Editorial",      // publisher identity; real names only with consent
 *   featured: false,                   // editorial "Start here" choice, not popularity
 *   related_product: { label: "Research Need", href: "/research" },   // optional, public routes only
 *   body: [                            // structured blocks — no HTML injection
 *     { h: "Section heading" },
 *     { p: "Paragraph text." },
 *     { list: ["Item", "Item"] },
 *     { note: "A short aside." },
 *   ],
 *   references: [                      // real, checkable sources only — never generated
 *     { text: "Author (Year). Title. Publisher.", url: "https://…" },
 *   ],
 * }
 */

/** Research tasks the library is organised by (what the reader is trying to do). */
export const TASKS = {
  define: "Define the research",
  evidence: "Find the evidence",
  design: "Design the study",
  collaborate: "Work with others",
  write: "Write and publish",
  record: "Build your research record",
  ai: "Use AI responsibly",
};

export const TYPES = {
  guide: "Guide",
  explainer: "Explainer",
  workflow: "Workflow",
  reference: "Reference",
};

/** No guides are published yet. Add entries here as they pass editorial review. */
export const RESOURCES = [];

const REQUIRED = ["number", "slug", "title", "description", "type", "task", "published_at", "byline"];

export function isPublishable(r) {
  return r && r.status === "published"
    && REQUIRED.every((k) => r[k] !== undefined && r[k] !== null && String(r[k]).trim() !== "")
    && Object.prototype.hasOwnProperty.call(TASKS, r.task)
    && Object.prototype.hasOwnProperty.call(TYPES, r.type)
    && Array.isArray(r.body) && r.body.length > 0;
}

export function bodyWords(r) {
  const text = (r.body || []).map((b) => b.h || b.p || b.note || (b.list || []).join(" ") || "").join(" ");
  return (text.match(/\S+/g) || []).length;
}

/** Minutes at 220 words a minute, rounded up, minimum 1. */
export function readingMinutes(r) {
  return Math.max(1, Math.ceil(bodyWords(r) / 220));
}

export function publishedResources(list = RESOURCES) {
  return list.filter(isPublishable).sort((a, b) => a.number - b.number);
}

export function findPublished(slug, list = RESOURCES) {
  return publishedResources(list).find((r) => r.slug === slug) || null;
}

export function formatDate(iso) {
  const d = new Date(`${iso}T00:00:00Z`);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric", timeZone: "UTC" });
}
