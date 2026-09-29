import { MATCHING_INPUT_FIELDS } from "./ProvenanceTag";

// P1 Phase 6/7 audit: these are the ONLY fields the canonical matcher
// (services/collab_intelligence/matching_engine.py +
// researcher_profiler.py) actually consumes. This test guards against
// silently adding a field to the Passport's "used for matching" UI
// indicator that the backend doesn't really use — or vice versa.
describe("MATCHING_INPUT_FIELDS", () => {
  it("includes exactly the audited canonical matching-input fields", () => {
    const expected = new Set([
      "research_areas",
      "research_interests",
      "research_keywords",
      "methods",
      "software_skills",
      "institution",
      "academic_role",
      "user_type",
    ]);
    expect(MATCHING_INPUT_FIELDS).toEqual(expected);
  });

  it("does NOT include fields the Phase 6 audit confirmed are not matching inputs", () => {
    for (const field of ["skills", "methodological_expertise", "primary_domain", "department", "bio"]) {
      expect(MATCHING_INPUT_FIELDS.has(field)).toBe(false);
    }
  });

  it("does NOT include collaboration-preference fields", () => {
    for (const field of ["can_contribute", "looking_for", "available_for_collaboration"]) {
      expect(MATCHING_INPUT_FIELDS.has(field)).toBe(false);
    }
  });
});
