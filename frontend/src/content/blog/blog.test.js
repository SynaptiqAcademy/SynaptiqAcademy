import { POSTS, CATEGORIES, isPublished, publishedPosts, findPost, readingMinutes, tocFor, formatDate } from "./index";

const post = (over = {}) => ({
  slug: "an-essay", title: "An essay", deck: "A deck.", category: "collaboration", status: "published",
  published_at: "2026-10-06", author: { name: "Synaptiq Editorial" },
  body: [{ h: "One" }, { p: "word ".repeat(660).trim() }], ...over,
});

describe("blog content model", () => {
  test("posts have unique slugs", () => {
    expect(new Set(POSTS.map((p) => p.slug)).size).toBe(POSTS.length);
  });

  test("published posts are complete, categorised, dated and bylined", () => {
    publishedPosts().forEach((p) => {
      expect(CATEGORIES[p.category]).toBeTruthy();
      expect(formatDate(p.published_at)).not.toBe("");
      expect(p.author.name.trim()).not.toBe("");
    });
  });

  test("drafts, archived and incomplete posts never surface", () => {
    const list = [post({ slug: "d", status: "draft" }), post({ slug: "a", status: "archived" }),
      post({ slug: "noauthor", author: { name: "" } }), post({ slug: "nodate", published_at: "June 2026" }), post({ slug: "ok" })];
    expect(publishedPosts(list).map((p) => p.slug)).toEqual(["ok"]);
    expect(findPost("d", list)).toBeNull();
    expect(isPublished(post())).toBe(true);
  });

  test("reading time is calculated; a table of contents only for long pieces", () => {
    expect(readingMinutes(post())).toBe(Math.ceil(661 / 220));
    expect(tocFor(post())).toEqual([]);
    const long = post({ body: [{ h: "A" }, { p: "w ".repeat(1900) }, { h: "B" }, { h: "C" }] });
    expect(tocFor(long).map((t) => t.id)).toEqual(["a", "b", "c"]);
  });
});
