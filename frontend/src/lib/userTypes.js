export const USER_TYPE_LABELS = {
  undergraduate_student:   "Undergraduate Student",
  masters_student:         "Master's Student",
  phd_candidate:           "PhD Candidate",
  postdoctoral_researcher: "Postdoctoral Researcher",
  researcher:              "Researcher",
  educator:                "Educator",
  university_faculty:      "University Faculty",
  trainer:                 "Trainer",
  industry_professional:   "Industry Professional",
};

export const PRIMARY_DOMAIN_LABELS = {
  research: "Research",
  teaching: "Teaching",
  both:     "Research & Teaching",
};

export const USER_TYPE_OPTIONS = Object.entries(USER_TYPE_LABELS).map(
  ([value, label]) => ({ value, label })
);

export const PRIMARY_DOMAIN_OPTIONS = Object.entries(PRIMARY_DOMAIN_LABELS).map(
  ([value, label]) => ({ value, label })
);

/** Returns the display label for a user's type, falling back to academic_role then a default. */
export function userTypeLabel(user, fallback = "") {
  return USER_TYPE_LABELS[user?.user_type] || user?.academic_role || fallback;
}
