/**
 * Product notes — the single source for /resources/whats-new.
 *
 * Editorial rules (enforced by tests):
 * - A note describes a user-facing change that reached production. The date
 *   is the production deployment date, verifiable in the deploy history; it
 *   is never inferred from a commit or backfilled.
 * - Only `status: "published"` notes are shown. Drafts never render.
 * - `number` is assigned once in release order and never reused.
 * - No version numbers, no roadmap, no metrics, no hype.
 * - type: new | improved | fixed | changed (see TYPES).
 * - availability states who can use it today, in current plan names.
 * - link points to a public page only.
 */

export const TYPES = {
  new: { label: "New", meaning: "A capability that didn't exist before." },
  improved: { label: "Improved", meaning: "An existing capability works meaningfully better." },
  fixed: { label: "Fixed", meaning: "Something that didn't behave as it should now does." },
  changed: { label: "Changed", meaning: "Behaviour you should know about is different." },
};

export const AREAS = {
  passport: "Academic Passport",
  network: "Network",
  research: "Research",
  collaboration: "Collaboration",
  publishing: "Publishing",
  ai: "AI Workspace",
  institutions: "Institutions",
  plans: "Plans",
};

export const NOTES = [
  {
    number: 1, slug: "real-journal-conference-grant-records", status: "published",
    released_at: "2026-09-28", type: "changed", area: "publishing",
    title: "Journal, conference and grant discovery shows real records only",
    summary: "Results now come from records collected from public sources such as OpenAlex, Crossref and DOAJ.",
    details: [
      "Figures with no reliable free source, such as impact factors and predicted acceptance rates, are no longer shown.",
      "Missing information appears as missing rather than estimated.",
      "Journals suggested during a manuscript review are kept only when they match a real journal record.",
    ],
    availability: "Pro and Pro Advanced",
  },
  {
    number: 2, slug: "one-record-per-publication", status: "published",
    released_at: "2026-09-28", type: "improved", area: "passport",
    title: "One record per publication",
    summary: "Publications imported from ORCID or added by hand are matched by DOI, so the same work isn't listed twice.",
    availability: "All plans, including Free",
  },
  {
    number: 3, slug: "discovery-privacy-everywhere", status: "published",
    released_at: "2026-09-28", type: "improved", area: "network",
    title: "Discovery applies the same privacy settings everywhere",
    summary: "Profiles that are private, hidden from discovery or blocked no longer appear in researcher listings.",
    availability: "All plans",
  },
  {
    number: 4, slug: "passport-sources-orcid-verification", status: "published",
    released_at: "2026-09-29", type: "improved", area: "passport",
    title: "Your Passport shows where each detail comes from",
    summary: "Publications show their source, ORCID connects directly from the Passport, and institutional affiliation can be verified.",
    details: [
      "Each publication shows its source, such as ORCID, OpenAlex or a DOI lookup.",
      "Affiliation is verified through your institutional email or an admin's review of evidence. It confirms the affiliation only.",
    ],
    availability: "All plans, including Free",
  },
  {
    number: 5, slug: "research-need", status: "published",
    released_at: "2026-09-29", type: "new", area: "research",
    title: "Research Need",
    summary: "Describe a research problem and it is structured into domains, required and complementary expertise, methods and professional roles.",
    details: [
      "You review and edit the need before anyone is searched.",
      "Interpretation can use AI, which uses AI Credits, or a fixed research vocabulary at no cost.",
    ],
    availability: "Pro and Pro Advanced",
    link: { href: "/research", label: "See the research workflow" },
  },
  {
    number: 6, slug: "matches-with-reasons", status: "published",
    released_at: "2026-09-29", type: "new", area: "research",
    title: "Suggested people come with their reasons",
    summary: "People found for a Research Need are grouped as directly relevant, complementary, methods or context, each with the profile evidence behind the suggestion.",
    details: ["Matching is rule-based and doesn't use AI Credits."],
    availability: "Pro and Pro Advanced",
    link: { href: "/research", label: "See the research workflow" },
  },
  {
    number: 7, slug: "requests-from-a-research-need", status: "published",
    released_at: "2026-09-29", type: "improved", area: "collaboration",
    title: "Invite someone straight from a Research Need",
    summary: "A collaboration request can now be sent from a Research Need result, stating what the collaboration is for and keeping the need as context.",
    details: ["The other person accepts or declines. People who have blocked you can't receive your requests."],
    availability: "Pro and Pro Advanced",
  },
  {
    number: 8, slug: "team-builder", status: "published",
    released_at: "2026-09-30", type: "new", area: "collaboration",
    title: "Team Builder",
    summary: "Turn a Research Need into roles, see eligible members for each, and invite people one at a time.",
    details: [
      "Roles are marked essential, useful or optional, and you can mark the ones you cover yourself.",
      "When you're ready, create a project and workspace. Only people who accepted join it, with their team roles.",
    ],
    availability: "Pro and Pro Advanced",
    link: { href: "/research", label: "See the research workflow" },
  },
  {
    number: 9, slug: "institution-area-for-members", status: "published",
    released_at: "2026-09-30", type: "changed", area: "institutions",
    title: "The Institution area appears only to approved members",
    summary: "Institution pages are shown to people with approved membership of an institution, not based on plan or a typed affiliation.",
    availability: "Approved institution members",
    link: { href: "/for-institutions", label: "For Institutions" },
  },
  {
    number: 10, slug: "plans-free-pro-pro-advanced", status: "published",
    released_at: "2026-10-05", type: "changed", area: "plans",
    title: "Plans are now Free, Pro and Pro Advanced",
    summary: "Free covers your Academic Passport, public research page and ORCID. Pro adds the network, collaboration, projects and AI; Pro Advanced adds deeper research tools and impact.",
    details: ["Online purchase isn't open yet."],
    availability: "Everyone",
    link: { href: "/pricing", label: "See Pricing" },
  },
  {
    number: 11, slug: "ai-cost-before-it-runs", status: "published",
    released_at: "2026-10-05", type: "improved", area: "ai",
    title: "AI actions show their cost before they run",
    summary: "Each AI action has a fixed credit cost, shown before you run it. If an action fails, its credits are returned.",
    availability: "Pro and Pro Advanced",
    link: { href: "/ai-workspace", label: "Explore AI Workspace" },
  },
  {
    number: 12, slug: "copilot-references", status: "published",
    released_at: "2026-10-05", type: "fixed", area: "ai",
    title: "Manuscript Copilot no longer writes references for you",
    summary: "Asked to format references, Copilot now works only with the references you provide and marks missing details instead of filling them in.",
    availability: "Pro and Pro Advanced",
    link: { href: "/ai-workspace", label: "Explore AI Workspace" },
  },
  {
    number: 13, slug: "institution-invitations-and-access", status: "published",
    released_at: "2026-10-06", type: "fixed", area: "institutions",
    title: "Institution invitations can be accepted, and member details are better protected",
    summary: "Accepting an admin's invitation now makes you a member with the invited role.",
    details: ["Member lists and departments are visible only to members, and colleagues' email addresses only to admins."],
    availability: "Approved institution members",
    link: { href: "/for-institutions", label: "For Institutions" },
  },
];

const REQUIRED = ["number", "slug", "released_at", "type", "area", "title", "summary", "availability"];

export function isPublished(n) {
  return n && n.status === "published"
    && REQUIRED.every((k) => n[k] !== undefined && n[k] !== null && String(n[k]).trim() !== "")
    && Object.prototype.hasOwnProperty.call(TYPES, n.type)
    && Object.prototype.hasOwnProperty.call(AREAS, n.area)
    && /^\d{4}-\d{2}-\d{2}$/.test(n.released_at);
}

/** Newest first; ties broken by note number (later number = later release). */
export function publishedNotes(list = NOTES) {
  return list.filter(isPublished).sort((a, b) => (b.released_at.localeCompare(a.released_at)) || (b.number - a.number));
}

const MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];

/** "2026-09-30" → "30 SEP 2026" (one fixed format, independent of locale). */
export function formatDay(iso) {
  const [y, m, d] = iso.split("-");
  return `${d} ${MONTHS[Number(m) - 1]} ${y}`;
}
