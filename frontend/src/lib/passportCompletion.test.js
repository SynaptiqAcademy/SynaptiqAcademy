import { pickNextBestAction } from "./passportCompletion";

const item = (key, points, earned) => ({ key, points, earned, label: key, action: `/x/${key}`, action_label: key });

describe("pickNextBestAction", () => {
  it("returns null when completion is missing", () => {
    expect(pickNextBestAction(null)).toBeNull();
    expect(pickNextBestAction(undefined)).toBeNull();
  });

  it("returns null when every item is already earned", () => {
    const completion = { items: [item("avatar", 10, true), item("biography", 10, true)] };
    expect(pickNextBestAction(completion)).toBeNull();
  });

  it("picks the highest-point unearned item, ignoring earned ones", () => {
    const completion = {
      items: [
        item("avatar", 10, true),
        item("methods", 5, false),
        item("orcid_connected", 15, false),
        item("keywords", 10, false),
      ],
    };
    expect(pickNextBestAction(completion).key).toBe("orcid_connected");
  });

  it("is deterministic — same input always yields the same pick", () => {
    const completion = { items: [item("a", 10, false), item("b", 10, false)] };
    const first = pickNextBestAction(completion);
    const second = pickNextBestAction(completion);
    expect(first.key).toBe(second.key);
  });
});
