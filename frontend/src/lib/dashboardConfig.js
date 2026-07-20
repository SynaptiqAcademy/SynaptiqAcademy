// Dashboard personalization — all logic driven by user_type + primary_domain.
// getDashboardMode() is the single source of truth for the active mode.

export function getDashboardMode(user) {
  const d = user?.primary_domain;
  if (d === "teaching") return "teaching";
  if (d === "both")     return "hybrid";
  return "research"; // null / undefined → research (backward compat)
}

// ─── Quick actions by user_type (research context) ───────────────────────────

const QA_RESEARCH_DEFAULT = [
  { label: "New Manuscript",      to: "/manuscripts" },
  { label: "Find Journal",        to: "/journals" },
  { label: "Find Conference",     to: "/conferences" },
  { label: "Statistical Review",  to: "/statistical-review" },
  { label: "New Project",         to: "/projects" },
];

const QA_TEACHING_DEFAULT = [
  { label: "Lesson Planner",      to: "/teaching/lesson-planner" },
  { label: "Assessment Builder",  to: "/teaching/assessment-builder" },
  { label: "Teaching Portfolio",  to: "/teaching/portfolio" },
];

const USER_TYPE_QA = {
  undergraduate_student: [
    { label: "Browse Collaborations", to: "/collaborations" },
    { label: "Explore Network",       to: "/network" },
    { label: "Literature Review AI",  to: "/literature-review" },
    { label: "New Project",           to: "/projects" },
  ],
  masters_student: [
    { label: "New Manuscript",        to: "/manuscripts" },
    { label: "Statistical Review",    to: "/statistical-review" },
    { label: "Find Journal",          to: "/journals" },
    { label: "Browse Collaborations", to: "/collaborations" },
    { label: "Research Gap Finder",   to: "/research-gap-finder" },
  ],
  phd_candidate: [
    { label: "New Manuscript",        to: "/manuscripts" },
    { label: "Statistical Review",    to: "/statistical-review" },
    { label: "Research Gap Finder",   to: "/research-gap-finder" },
    { label: "Find Journal",          to: "/journals" },
    { label: "Citation Monitoring",   to: "/citation-monitoring" },
  ],
  postdoctoral_researcher: [
    { label: "Find Grant",            to: "/grants" },
    { label: "Research Impact",       to: "/research-impact" },
    { label: "New Manuscript",        to: "/manuscripts" },
    { label: "Collaboration AI",      to: "/collaboration-intelligence" },
    { label: "Statistical Review",    to: "/statistical-review" },
  ],
  researcher: [
    { label: "Research Impact",       to: "/research-impact" },
    { label: "Citation Monitoring",   to: "/citation-monitoring" },
    { label: "Find Grant",            to: "/grants" },
    { label: "Collaboration AI",      to: "/collaboration-intelligence" },
    { label: "New Manuscript",        to: "/manuscripts" },
  ],
  educator: [
    { label: "Lesson Planner",        to: "/teaching/lesson-planner" },
    { label: "Assessment Builder",    to: "/teaching/assessment-builder" },
    { label: "Teaching Workspaces",   to: "/teaching/workspaces" },
    { label: "Teaching Portfolio",    to: "/teaching/portfolio" },
  ],
  trainer: [
    { label: "Lesson Planner",        to: "/teaching/lesson-planner" },
    { label: "Assessment Builder",    to: "/teaching/assessment-builder" },
    { label: "Teaching Workspaces",   to: "/teaching/workspaces" },
    { label: "Teaching Portfolio",    to: "/teaching/portfolio" },
  ],
  university_faculty: [
    { label: "New Manuscript",        to: "/manuscripts" },
    { label: "Research Impact",       to: "/research-impact" },
    { label: "Lesson Planner",        to: "/teaching/lesson-planner" },
    { label: "Find Grant",            to: "/grants" },
    { label: "Citation Monitoring",   to: "/citation-monitoring" },
  ],
  industry_professional: [
    { label: "Marketplace",           to: "/marketplace" },
    { label: "New Project",           to: "/projects" },
    { label: "Browse Collaborations", to: "/collaborations" },
    { label: "Expertise Requests",    to: "/expertise" },
    { label: "Analytics",             to: "/analytics" },
  ],
};

export function getQuickActions(user, dashboardMode) {
  if (dashboardMode === "teaching") {
    return USER_TYPE_QA[user?.user_type] || QA_TEACHING_DEFAULT;
  }
  if (dashboardMode === "hybrid") {
    if (user?.user_type === "university_faculty") return USER_TYPE_QA.university_faculty;
    return [
      { label: "New Manuscript",     to: "/manuscripts" },
      { label: "Lesson Planner",     to: "/teaching/lesson-planner" },
      { label: "Find Journal",       to: "/journals" },
      { label: "Teaching Workspaces", to: "/teaching/workspaces" },
      { label: "Assessment Builder", to: "/teaching/assessment-builder" },
    ];
  }
  // Research mode
  return USER_TYPE_QA[user?.user_type] || QA_RESEARCH_DEFAULT;
}

// ─── Profile completeness ─────────────────────────────────────────────────────

export function getProfileCompletenessFields(user) {
  const mode = getDashboardMode(user);
  const missing = [];

  if (mode === "research" || mode === "hybrid") {
    if (!(user?.research_interests?.length || user?.research_areas?.length)) {
      missing.push({ key: "research_interests", label: "Research Interests" });
    }
    if (!user?.institution) missing.push({ key: "institution",    label: "Institution" });
    if (!user?.orcid?.orcid_id) missing.push({ key: "orcid",     label: "ORCID" });
  }

  if (mode === "teaching" || mode === "hybrid") {
    if (!user?.institution && !missing.find((f) => f.key === "institution")) {
      missing.push({ key: "institution", label: "Institution" });
    }
  }

  return missing;
}

// ─── Personalization matrix (priority modules per user_type) ──────────────────

export const PERSONA_PRIORITY = {
  undergraduate_student:   ["projects", "collaborations", "network"],
  masters_student:         ["manuscripts", "journals", "collaborations"],
  phd_candidate:           ["manuscripts", "statistical_review", "journals", "publications"],
  postdoctoral_researcher: ["grants", "publications", "collaborations"],
  researcher:              ["research_impact", "publications", "grants"],
  educator:                ["teaching_hub", "lesson_planning", "assessment"],
  university_faculty:      ["research", "teaching"],
  trainer:                 ["teaching_hub", "course_design", "assessment"],
  industry_professional:   ["projects", "collaborations", "analytics"],
};
