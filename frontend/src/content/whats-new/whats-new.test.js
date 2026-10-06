import { NOTES, TYPES, AREAS, isPublished, publishedNotes, formatDay } from "./index";

describe("product notes", () => {
  test("unique slugs, and numbers run 1..n in release order with no gaps", () => {
    expect(new Set(NOTES.map((n) => n.slug)).size).toBe(NOTES.length);
    const byNumber = [...NOTES].sort((a, b) => a.number - b.number);
    byNumber.forEach((n, i) => expect(n.number).toBe(i + 1));
    for (let i = 1; i < byNumber.length; i += 1) {
      expect(byNumber[i].released_at >= byNumber[i - 1].released_at).toBe(true);
    }
  });

  test("every published note is complete and uses the small taxonomy", () => {
    publishedNotes().forEach((n) => {
      expect(TYPES[n.type]).toBeTruthy();
      expect(AREAS[n.area]).toBeTruthy();
      expect(n.released_at >= "2026-07-20").toBe(true);   // nothing before the product's own history
    });
  });

  test("drafts never render", () => {
    const list = [{ ...NOTES[0], slug: "d", status: "draft" }, { ...NOTES[0], slug: "p" }];
    expect(publishedNotes(list).map((n) => n.slug)).toEqual(["p"]);
    expect(isPublished({ ...NOTES[0], released_at: "June 2026" })).toBe(false);
  });

  test("newest first", () => {
    const p = publishedNotes();
    for (let i = 1; i < p.length; i += 1) expect(p[i - 1].released_at >= p[i].released_at).toBe(true);
  });

  test("dates use one fixed format", () => {
    expect(formatDay("2026-09-30")).toBe("30 SEP 2026");
  });
});
