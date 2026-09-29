import { getAuthenticatedOrcidId, isOrcidAuthenticated } from "./orcid";

describe("getAuthenticatedOrcidId", () => {
  it("returns the orcid_id for an authenticated dict shape", () => {
    expect(getAuthenticatedOrcidId({ orcid_id: "0000-0001-2345-6789", access_token: "x" })).toBe("0000-0001-2345-6789");
  });

  it("returns null for a bare legacy string", () => {
    expect(getAuthenticatedOrcidId("0000-0001-2345-6789")).toBeNull();
  });

  it("returns null for a dict without orcid_id", () => {
    expect(getAuthenticatedOrcidId({ access_token: "x" })).toBeNull();
  });

  it("returns null for null/undefined", () => {
    expect(getAuthenticatedOrcidId(null)).toBeNull();
    expect(getAuthenticatedOrcidId(undefined)).toBeNull();
  });
});

describe("isOrcidAuthenticated", () => {
  it("is true only for an authenticated dict shape", () => {
    expect(isOrcidAuthenticated({ orcid_id: "0000-0001-2345-6789" })).toBe(true);
    expect(isOrcidAuthenticated("0000-0001-2345-6789")).toBe(false);
    expect(isOrcidAuthenticated({})).toBe(false);
    expect(isOrcidAuthenticated(null)).toBe(false);
  });
});
