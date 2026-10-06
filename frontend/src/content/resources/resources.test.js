import {
  RESOURCES, TASKS, TYPES, isPublishable, publishedResources, findPublished, readingMinutes, formatDate,
} from "./index";

const guide = (over = {}) => ({
  number: 1, slug: "a-guide", title: "A guide", description: "One sentence.", type: "guide", task: "define",
  status: "published", published_at: "2026-10-06", byline: "Synaptiq Editorial",
  body: [{ h: "Heading" }, { p: "word ".repeat(440).trim() }], ...over,
});

describe("research library content model", () => {
  test("library entries have unique slugs and catalogue numbers", () => {
    const slugs = RESOURCES.map((r) => r.slug);
    const nums = RESOURCES.map((r) => r.number);
    expect(new Set(slugs).size).toBe(slugs.length);
    expect(new Set(nums).size).toBe(nums.length);
  });

  test("every published entry is complete, uses a known task/type and has a real date", () => {
    publishedResources().forEach((r) => {
      expect(TASKS[r.task]).toBeTruthy();
      expect(TYPES[r.type]).toBeTruthy();
      expect(formatDate(r.published_at)).not.toBe("");
    });
  });

  test("drafts and incomplete entries are never published or routable", () => {
    const list = [guide({ slug: "draft", status: "draft" }), guide({ slug: "no-date", published_at: "" }),
      guide({ slug: "bad-task", task: "nope" }), guide({ slug: "empty", body: [] }), guide({ slug: "ok", number: 2 })];
    expect(publishedResources(list).map((r) => r.slug)).toEqual(["ok"]);
    expect(findPublished("draft", list)).toBeNull();
    expect(isPublishable(guide())).toBe(true);
  });

  test("reading time is calculated from the body, not typed", () => {
    expect(readingMinutes(guide())).toBe(Math.ceil(441 / 220));
    expect(readingMinutes(guide({ body: [{ p: "short" }] }))).toBe(1);
  });
});
