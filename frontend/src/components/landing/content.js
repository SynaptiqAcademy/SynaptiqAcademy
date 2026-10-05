/**
 * Landing-page copy that states commercial facts. Kept in one place so the
 * backend regression tests (backend/tests/test_landing_commercial_truth.py)
 * can check it against plans_catalogue.py — the canonical source for every
 * price, AI-credit allocation and storage limit shown here.
 *
 * Pricing CTAs never open checkout from the Landing page: paid plans go to
 * /pricing, which handles billing readiness honestly.
 */

export const PLAN_PREVIEW = [
  {
    key: "free",
    name: "Free",
    price: "€0",
    period: "",
    status: null,
    futurePrice: null,
    credits: "0 AI Credits",
    role: "Academic identity and visibility",
    includes: [
      "Academic Passport and public research page",
      "ORCID connection and publication import",
      "Can be found by Pro members",
    ],
    cta: "Get Started Free",
    href: "/register",
  },
  {
    key: "pro",
    name: "Pro",
    price: "€9.99",
    period: "/ month",
    status: "Early Access",
    futurePrice: "Future price €14.99/month",
    credits: "200 AI Credits / month",
    role: "Active research, collaboration and AI-assisted work",
    includes: [
      "Research network, matching and messaging",
      "Collaboration requests and workflows",
      "Unlimited projects, 10 workspaces, 10 GB storage",
      "Journal, conference and grant discovery",
      "AI Research Assistant and Manuscript Copilot",
      "Teaching Hub, publication tracking, research analytics",
    ],
    cta: "Choose Pro",
    href: "/pricing",
  },
  {
    key: "pro_advanced",
    name: "Pro Advanced",
    price: "€29.99",
    period: "/ month",
    status: null,
    futurePrice: null,
    credits: "750 AI Credits / month",
    role: "Advanced research intelligence, analysis and impact",
    includes: [
      "Everything in Pro",
      "Unlimited workspaces, 50 GB storage",
      "Advanced AI Research Assistant with extended context",
      "Collaboration Intelligence",
      "Research Impact Dashboard and Citation Monitoring",
      "Advanced analytics, manuscript intelligence and AI teaching tools",
    ],
    cta: "Choose Pro Advanced",
    href: "/pricing",
  },
  {
    key: "institutional",
    name: "Institutional",
    price: "Custom",
    period: "",
    status: null,
    futurePrice: null,
    credits: "Set per agreement",
    role: "For universities, research institutions and organizations",
    includes: [
      "Institution workspace for approved members",
      "Member and department management",
      "Institutional analytics",
    ],
    cta: "Contact Sales",
    href: "/contact?topic=institution",
  },
];

export const FAQ = [
  {
    q: "What is Synaptiq?",
    a: "A place to do research with other people. You describe what you're working on, Synaptiq shows the expertise it calls for and helps you find people who have it, and the collaboration, project and writing that follow stay connected to that starting point.",
  },
  {
    q: "Who can use it?",
    a: "Anyone who does research, as their job or alongside it: academic and doctoral researchers, educators, clinicians and scientists, people in policy and the public sector, and people whose work crosses disciplines. Your plan reflects what you use, not your job title.",
  },
  {
    q: "What can I do with a free account?",
    a: "Build your Academic Passport and public research page, connect ORCID and import your publications. Pro members can find you and invite you to collaborate. Messaging, collaboration, projects, workspaces, discovery and AI tools are part of Pro.",
  },
  {
    q: "What changes with Pro?",
    a: "You can take part, not just be found: search the research network, message people, send and accept collaboration requests, run projects and workspaces, use journal, conference and grant discovery, and use AI tools with 200 AI Credits a month.",
  },
  {
    q: "What is Pro Advanced?",
    a: "Pro plus a deeper layer of analysis: the Advanced AI Research Assistant with extended context, Advanced Manuscript Intelligence, Collaboration Intelligence, Citation Monitoring, the Research Impact Dashboard, advanced analytics and advanced AI teaching tools, with 750 AI Credits a month.",
  },
  {
    q: "What are AI Credits?",
    a: "The unit AI-assisted actions are paid in. Different actions cost different amounts, and the cost is shown before you run one; a request that fails is refunded. Profiles, networking, messaging and collaboration don't use AI Credits. Monthly credits reset at each renewal.",
  },
  {
    q: "Do I need ORCID?",
    a: "No. Connecting ORCID lets you import your publications and shows that you control that ORCID account, but you can build a Passport without it.",
  },
  {
    q: "Does Synaptiq verify professional qualifications?",
    a: "No. Synaptiq can verify an institutional affiliation, through an institutional email or the institution's approval, and show that an ORCID account is connected. It does not verify degrees, professional licences or competence, and the Passport marks which entries are self-declared.",
  },
  {
    q: "Does Synaptiq guarantee publication or funding?",
    a: "No. It can help you find people, methods, venues and calls. Acceptance, peer review and funding decisions belong to journals, conferences and funders, and AI suggestions can be wrong.",
  },
  {
    q: "Can universities use Synaptiq?",
    a: "Yes, through an Institutional agreement: an institution workspace for approved members, member and department management, and institutional analytics. Pricing is agreed with each organization. An individual subscription doesn't grant institution administration.",
  },
];
