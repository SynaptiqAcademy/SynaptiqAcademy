/**
 * profileCompletion.js
 *
 * Client-side profile completion scoring from the user object.
 * Mirrors (but does not replace) the server-side endpoint at
 * GET /api/users/me/profile-completion.
 *
 * Client-side scoring is intentionally simpler so it can run
 * synchronously from cached user state without an async fetch.
 * The server endpoint is used for the detailed breakdown UI.
 *
 * Unlock threshold is exported so it can be read wherever needed.
 */

/** Percentage required to unlock the community */
export const COMMUNITY_UNLOCK_THRESHOLD = 50;

/** Routes that are always accessible regardless of profile completion */
export const ALWAYS_ALLOWED_ROUTES = [
  "/profile-setup",
  "/onboarding",
  "/settings",
  "/settings/billing",
  "/settings/security",
  "/settings/mfa",
  "/settings/orcid",
  "/settings/notifications",
  "/email-preferences",
  "/billing",
  "/profile",
  "/academic-passport",
  "/verify-email",
  "/verify-email-pending",
];

/**
 * Return true if pathname is always accessible (never gated).
 */
export function isAlwaysAllowed(pathname) {
  return ALWAYS_ALLOWED_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(route + "/")
  );
}

/**
 * Compute a 0-100 completion score from the user object.
 *
 * Scoring breakdown:
 *   Name complete          +10  first_name + last_name both set
 *   Country set            +5
 *   Role set               +5   user_type
 *   Institution            +10
 *   Biography              +10  > 20 characters
 *   Research areas         +15  ≥ 1 area in research_areas OR research_interests
 *   Keywords               +10  ≥ 2 items in research_keywords
 *   Academic link          +10  any of: orcid_id / google_scholar / researchgate / linkedin
 *   Availability           +5
 *   Skills / looking_for   +10  ≥ 1 item in skills OR looking_for
 *   Teaching (faculty)     +10  teaching_areas ≥ 1 (only for teaching/hybrid domains)
 *   ───────────────────────────
 *   Max                    100
 *
 * @param {object} user - serialized user from /auth/me
 * @returns {number} 0-100
 */
export function computeProfileScore(user) {
  if (!user) return 0;

  let score = 0;

  // Name
  if (user.first_name && user.last_name) score += 10;

  // Country
  if (user.country) score += 5;

  // Role
  if (user.user_type) score += 5;

  // Institution
  if (user.institution) score += 10;

  // Biography (meaningful length)
  if ((user.biography || "").trim().length > 20) score += 10;

  // Research areas
  const researchAreas =
    (user.research_areas || []).length + (user.research_interests || []).length;
  if (researchAreas >= 1) score += 15;

  // Keywords
  if ((user.research_keywords || []).length >= 2) score += 10;

  // Academic link
  const orcidId =
    user.orcid && typeof user.orcid === "object"
      ? user.orcid.orcid_id
      : user.orcid;
  if (orcidId || user.google_scholar || user.researchgate || user.linkedin) {
    score += 10;
  }

  // Availability
  if (user.availability) score += 5;

  // Skills / looking_for
  if (
    (user.skills || []).length >= 1 ||
    (user.looking_for || []).length >= 1 ||
    (user.can_contribute || []).length >= 1
  ) {
    score += 10;
  }

  // Teaching (only counts for teaching or hybrid domain users)
  if (
    (user.primary_domain === "teaching" || user.primary_domain === "both") &&
    (user.teaching_areas || []).length >= 1
  ) {
    score += 10;
  }

  return Math.min(score, 100);
}

/**
 * Return true if the user has unlocked community access.
 * @param {object} user
 */
export function isCommunityUnlocked(user) {
  if (!user) return false;
  return computeProfileScore(user) >= COMMUNITY_UNLOCK_THRESHOLD;
}

/**
 * Describe each completion item for the verification panel UI.
 * @param {object} user
 * @returns {Array<{key, label, earned, points, hint}>}
 */
export function getCompletionItems(user) {
  if (!user) return [];

  const orcidId =
    user.orcid && typeof user.orcid === "object"
      ? user.orcid.orcid_id
      : user.orcid;

  const hasResearch =
    (user.research_areas || []).length >= 1 ||
    (user.research_interests || []).length >= 1;

  const isTeaching =
    user.primary_domain === "teaching" || user.primary_domain === "both";

  return [
    {
      key: "name",
      label: "Full name",
      earned: !!(user.first_name && user.last_name),
      points: 10,
      hint: "Add your first and last name",
    },
    {
      key: "country",
      label: "Country",
      earned: !!user.country,
      points: 5,
      hint: "Set your country",
    },
    {
      key: "user_type",
      label: "Academic role",
      earned: !!user.user_type,
      points: 5,
      hint: "Select your role (PhD candidate, Faculty…)",
    },
    {
      key: "institution",
      label: "Institution",
      earned: !!user.institution,
      points: 10,
      hint: "Add your university or organisation",
    },
    {
      key: "biography",
      label: "Biography",
      earned: (user.biography || "").trim().length > 20,
      points: 10,
      hint: "Write a short academic biography",
    },
    {
      key: "research",
      label: "Research areas",
      earned: hasResearch,
      points: 15,
      hint: "Add at least one research field",
    },
    {
      key: "keywords",
      label: "Research keywords",
      earned: (user.research_keywords || []).length >= 2,
      points: 10,
      hint: "Add at least 2 keywords",
    },
    {
      key: "link",
      label: "Academic profile linked",
      earned: !!(orcidId || user.google_scholar || user.researchgate || user.linkedin),
      points: 10,
      hint: "Connect ORCID, Google Scholar, or LinkedIn",
    },
    {
      key: "availability",
      label: "Availability set",
      earned: !!user.availability,
      points: 5,
      hint: "Set your collaboration availability",
    },
    {
      key: "skills",
      label: "Skills or collaboration interests",
      earned:
        (user.skills || []).length >= 1 ||
        (user.looking_for || []).length >= 1 ||
        (user.can_contribute || []).length >= 1,
      points: 10,
      hint: "Add skills or what you are looking for",
    },
    ...(isTeaching
      ? [
          {
            key: "teaching",
            label: "Teaching areas",
            earned: (user.teaching_areas || []).length >= 1,
            points: 10,
            hint: "Add at least one teaching field",
          },
        ]
      : []),
  ];
}
