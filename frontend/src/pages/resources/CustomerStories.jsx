/* eslint-disable */
import React, { useState, useRef, useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import MarketingLayout from "../../components/layout/MarketingLayout";
import { ArrowRight, Search, Building2, Globe, ChevronRight, Star, TrendingUp, Users, BarChart3, BookOpen, Award, Filter, X } from "lucide-react";

const NAVY  = "#0F2847";
const LIGHT = "#f8fafc";
const BORDER= "#e8edf3";

function useReveal(threshold = 0.06) {
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current; if (!el) return;
    if (typeof IntersectionObserver === "undefined") { el.classList.add("sq-in"); return; }
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) { el.classList.add("sq-in"); obs.disconnect(); } }, { threshold });
    obs.observe(el); return () => obs.disconnect();
  }, []);
  return ref;
}

/* ─── Case study data ─────────────────────────────────────────────────────── */
const STORIES = [
  {
    id: 1,
    institution: "Uppsala University",
    country: "Sweden",
    category: "Research",
    size: "Large",
    logo: "UU",
    logoColor: "#8B0000",
    title: "How Uppsala's Research Office replaced 7 disconnected tools with one platform",
    challenge: "140 faculty across 12 departments were using incompatible tools for project management, publication tracking and grant reporting, creating critical data gaps for the VP of Research.",
    solution: "Synaptiq's Institution Dashboard provided unified visibility into all faculty output, grant pipelines and collaboration activity. Department grouping allowed the research office to run benchmarks across disciplines for the first time.",
    results: [
      { metric: "38%", label: "Reduction in admin time" },
      { metric: "94%", label: "Faculty adoption in 6 weeks" },
      { metric: "€2.1M", label: "Additional grants identified" },
    ],
    quote: "We finally have a single source of truth for our research portfolio. The grant pipeline visibility alone justified the investment in the first month.",
    author: "Prof. Ingrid Sörensen",
    role: "Head of Research Office",
    tags: ["Institution Analytics", "Grant Management", "Research Governance"],
    featured: true,
  },
  {
    id: 2,
    institution: "ETH Zürich",
    country: "Switzerland",
    category: "Research",
    size: "Large",
    logo: "ETH",
    logoColor: "#1a5276",
    title: "ETH Zürich: Building international research consortia with AI-powered partner matching",
    challenge: "A Department of Biochemistry group needed to form a 9-institution EU consortium within 6 weeks, requiring expertise across molecular biology, data science and regulatory science in 5 countries.",
    solution: "Synaptiq's Grant Collaboration Hub and AI partner matching assembled a verified team, generated the consortium agreement scaffold, and tracked readiness across all institutions through a shared workspace.",
    results: [
      { metric: "9", label: "Countries in consortium" },
      { metric: "6 weeks", label: "From idea to submitted proposal" },
      { metric: "€4.8M", label: "Horizon Europe grant awarded" },
    ],
    quote: "The gap detection tool identified three underexplored areas in our field that became the backbone of our Horizon proposal. That alone was worth every credit.",
    author: "Dr. Klaus Mettler",
    role: "Group Leader, Biochemistry",
    tags: ["Consortium Building", "AI Research", "Grant Hub"],
    featured: false,
  },
  {
    id: 3,
    institution: "Kyoto University Medical Center",
    country: "Japan",
    category: "Healthcare",
    size: "Large",
    logo: "KU",
    logoColor: "#922b21",
    title: "International medical research team publishes in Nature Methods 3 months after first contact",
    challenge: "Dr. Kenji Watanabe needed an immunology expert with specific in-vivo methodology experience. Traditional conference-based networking had failed for two years. Geographic barriers meant European collaborators were effectively invisible.",
    solution: "Synaptiq's Research Network and AI matching connected Dr. Watanabe with an immunologist at Oxford within 48 hours. The joint workspace enabled seamless co-authoring across 9 time zones.",
    results: [
      { metric: "48h", label: "Time to find the right collaborator" },
      { metric: "3 months", label: "From connection to Nature Methods submission" },
      { metric: "9", label: "Time zones coordinated without friction" },
    ],
    quote: "Synaptiq found me a co-author who had the exact methodology I needed, 9,000 km away. That collaboration would have taken 5 years through traditional channels.",
    author: "Dr. Kenji Watanabe",
    role: "Associate Professor of Immunology",
    tags: ["Collaboration Network", "Medical Research", "Publications"],
    featured: false,
  },
  {
    id: 4,
    institution: "MIT Media Lab",
    country: "United States",
    category: "Research",
    size: "Large",
    logo: "MIT",
    logoColor: "#8B0000",
    title: "MIT Media Lab cuts literature review time by 78% with Synaptiq AI Workspace",
    challenge: "Research groups were spending 3–5 weeks on literature reviews before every project. With fast-moving AI and HCI research, delays at this stage often meant losing first-mover advantage to competing groups.",
    solution: "Synaptiq's Literature Review Intelligence 2.0 reduced average literature review time from 24 days to 5 days. Gap Detection provided ranked, evidence-backed opportunities that shaped 3 successful NSF grant applications.",
    results: [
      { metric: "78%", label: "Reduction in literature review time" },
      { metric: "3", label: "NSF grants shaped by gap detection" },
      { metric: "24→5", label: "Days per literature review" },
    ],
    quote: "The AI doesn't replace the thinking — it removes the noise so we can think better. Every research group here now runs their literature phase through Synaptiq.",
    author: "Dr. Sarah Chen",
    role: "Principal Research Scientist",
    tags: ["AI Workspace", "Literature Review", "Research Analytics"],
    featured: false,
  },
  {
    id: 5,
    institution: "Oxford Department of Oncology",
    country: "United Kingdom",
    category: "Healthcare",
    size: "Medium",
    logo: "OX",
    logoColor: "#003366",
    title: "How Oxford Oncology managed 47 concurrent clinical trial publications",
    challenge: "The department was managing 47 concurrent publication workflows across 6 clinical trials, 14 co-authors per paper on average, and 3 different journal submission systems with no unified tracking.",
    solution: "Synaptiq's Publication Hub consolidated all 47 workflows. Journal matching reduced desk rejections by 82%. The manuscript review AI caught 3 statistical reporting issues before submission across two trials.",
    results: [
      { metric: "47", label: "Active publication workflows managed" },
      { metric: "82%", label: "Fewer desk rejections" },
      { metric: "3", label: "Critical statistical issues caught pre-submission" },
    ],
    quote: "The journal matching alone saved us from submitting the wrong paper to the wrong journal twice. For clinical trial data, that's not a minor issue.",
    author: "Prof. Margaret Thornton",
    role: "Department Head, Oncology",
    tags: ["Publication Hub", "Clinical Research", "Manuscript Review"],
    featured: false,
  },
  {
    id: 6,
    institution: "TU Berlin Innovation Lab",
    country: "Germany",
    category: "Teaching",
    size: "Medium",
    logo: "TUB",
    logoColor: "#cc0000",
    title: "TU Berlin digitizes doctoral supervision for 240 PhD candidates across 3 faculties",
    challenge: "240 PhD candidates across Engineering, Computer Science and Management were supervised through email chains, PDF forms and semi-annual departmental reports. Supervisors had no real-time view of candidate progress.",
    solution: "Synaptiq's Teaching Hub gave every PhD candidate a structured research timeline, milestones and a shared workspace with their supervisor. The Teaching Analytics dashboard gave faculty a real-time cohort view.",
    results: [
      { metric: "240", label: "PhD candidates onboarded" },
      { metric: "91%", label: "Supervisor satisfaction (up from 44%)" },
      { metric: "8 months", label: "Average time saved per completion cycle" },
    ],
    quote: "For the first time, I can see exactly where each of my 14 candidates is in their research journey without a single email. That's transformative at scale.",
    author: "Prof. Hans Richter",
    role: "Director of Doctoral Studies",
    tags: ["Teaching Hub", "Doctoral School", "Academic Analytics"],
    featured: false,
  },
  {
    id: 7,
    institution: "Science Foundation Ireland",
    country: "Ireland",
    category: "Government",
    size: "Large",
    logo: "SFI",
    logoColor: "#005e30",
    title: "Science Foundation Ireland automates grant evaluation for €180M annual funding program",
    challenge: "SFI received 3,400 grant applications per year. The manual review process took 6 months and relied on a fragmented spreadsheet system maintained by 12 program officers across 8 research themes.",
    solution: "Synaptiq's Institution Platform and Grant Hub provided structured application workflows, automated initial screening against published criteria, and a shared evaluation dashboard for all program officers.",
    results: [
      { metric: "6→3", label: "Months per evaluation cycle" },
      { metric: "€12M", label: "Administrative cost reduction annually" },
      { metric: "98%", label: "Reviewer satisfaction with digital workflow" },
    ],
    quote: "The platform cut our pre-screening workload by 60% and gave us data quality we'd never had before. We can now make evidence-based funding decisions at scale.",
    author: "Dr. Aoife Murphy",
    role: "Head of Digital Research Programs",
    tags: ["Grant Management", "Institution Dashboard", "Government"],
    featured: false,
  },
  {
    id: 8,
    institution: "Charité — Universitätsmedizin Berlin",
    country: "Germany",
    category: "Healthcare",
    size: "Large",
    logo: "CH",
    logoColor: "#004B87",
    title: "Charité runs 14-institution COVID-19 long-haul research consortium on Synaptiq",
    challenge: "A fast-assembled 14-institution research consortium across 6 European countries had zero shared infrastructure. Data governance, authorship agreements and IRB protocol sharing were being managed by email.",
    solution: "Synaptiq's Research Governance module, shared workspaces and Verification Center gave the consortium a compliant, auditable collaboration environment. The Academic Integrity Engine ensured data reporting consistency.",
    results: [
      { metric: "14", label: "Institutions on one platform" },
      { metric: "6", label: "Countries, zero friction" },
      { metric: "2", label: "NEJM papers submitted from consortium" },
    ],
    quote: "Running a multi-national clinical study without a shared research platform in 2026 would be unthinkable. Synaptiq became our consortium OS from week one.",
    author: "Prof. Dr. Andrea Weller",
    role: "Principal Investigator, COVID Long-Haul Study",
    tags: ["Consortium", "Healthcare", "Research Governance"],
    featured: false,
  },
  {
    id: 9,
    institution: "CNRS — French National Research Center",
    country: "France",
    category: "Research",
    size: "Large",
    logo: "CNRS",
    logoColor: "#003189",
    title: "CNRS adopts Synaptiq Academic Integrity Engine across 32 research units",
    challenge: "Following high-profile retraction cases across European institutions, CNRS initiated a proactive integrity review across 32 research units covering 800 active research projects and 6 years of historical outputs.",
    solution: "Synaptiq's Academic Integrity Engine ran statistical anomaly detection and citation accuracy checks across 6 years of publications. Three units received early intervention before submission. Zero retractions in the 18 months following rollout.",
    results: [
      { metric: "800", label: "Active projects reviewed" },
      { metric: "0", label: "Retractions in 18 months post-deployment" },
      { metric: "3", label: "Early interventions that prevented retraction" },
    ],
    quote: "We needed a systematic way to support researchers before problems became retractions. Synaptiq is now part of our mandatory pre-submission workflow.",
    author: "Dr. Marie Lefevre",
    role: "Scientific Integrity Officer",
    tags: ["Academic Integrity", "Research Ethics", "Institution"],
    featured: false,
  },
  {
    id: 10,
    institution: "National University of Singapore",
    country: "Singapore",
    category: "Research",
    size: "Large",
    logo: "NUS",
    logoColor: "#003D7C",
    title: "NUS Research Office benchmarks 42 departments against Asia-Pacific peers for the first time",
    challenge: "NUS had no standardized way to compare research performance across faculties or against peer institutions in the Asia-Pacific region. Reporting to the Board of Trustees required weeks of manual data compilation.",
    solution: "Synaptiq's Institution Analytics Center and Research Impact Dashboard provided a live benchmarking layer across all 42 departments. The SIS scoring system gave a single comparable number per researcher and per department.",
    results: [
      { metric: "42", label: "Departments benchmarked simultaneously" },
      { metric: "6 weeks", label: "Saved per board reporting cycle" },
      { metric: "Top 8", label: "Global research university ranking maintained" },
    ],
    quote: "The benchmarking module gave us data we simply didn't have before. For the first time, faculty could see how their research output compared to peers at Nanyang and Tokyo.",
    author: "Assoc. Prof. Lim Wei",
    role: "Deputy VP Research",
    tags: ["Institution Analytics", "Benchmarking", "Research Impact"],
    featured: false,
  },
  {
    id: 11,
    institution: "Karolinska Institutet",
    country: "Sweden",
    category: "Healthcare",
    size: "Large",
    logo: "KI",
    logoColor: "#004B87",
    title: "Karolinska builds the world's first neuroscience knowledge graph for clinical translation",
    challenge: "Translational neuroscience research requires linking bench findings to clinical studies to patient outcomes — across 15 years of institutional research, 9,000 papers and data from 23 active clinical trials.",
    solution: "Synaptiq's Living Knowledge Graph ingested and semantically linked 9,000 papers, 23 trial datasets and 6 decades of faculty expertise. Researchers can now navigate from a molecular finding to relevant clinical trials in 3 clicks.",
    results: [
      { metric: "9,000", label: "Papers linked in knowledge graph" },
      { metric: "23", label: "Active clinical trial datasets connected" },
      { metric: "3 clicks", label: "From molecule to clinical application" },
    ],
    quote: "We always knew this knowledge existed inside the institution. Synaptiq made it navigable for the first time. That's genuinely transformative for translational medicine.",
    author: "Prof. Stefan Lindqvist",
    role: "Head of Translational Research",
    tags: ["Knowledge Graph", "Medical Research", "AI"],
    featured: false,
  },
  {
    id: 12,
    institution: "African Research Universities Alliance",
    country: "Pan-African",
    category: "Research",
    size: "Large",
    logo: "ARUA",
    logoColor: "#8B4513",
    title: "ARUA connects 16 African research universities on a shared academic collaboration platform",
    challenge: "16 leading African universities in 10 countries had no shared digital infrastructure for joint research. Geography, bandwidth constraints and institutional silos prevented meaningful collaboration at scale.",
    solution: "Synaptiq's platform was deployed across all 16 ARUA member institutions with a shared consortium workspace, joint grant tracking and cross-institutional researcher discovery. The mobile-first optimization addressed bandwidth constraints.",
    results: [
      { metric: "16", label: "Universities on one platform" },
      { metric: "10", label: "Countries in the network" },
      { metric: "340", label: "Cross-institutional collaborations formed in Year 1" },
    ],
    quote: "Every African researcher should have access to the same quality of collaboration infrastructure as their peers in Europe and North America. Synaptiq is getting us there.",
    author: "Prof. Barnabas Nawangwe",
    role: "ARUA Chair",
    tags: ["Global Collaboration", "Consortium", "Research Network"],
    featured: false,
  },
];

const FILTERS = {
  Category: ["Research", "Teaching", "Healthcare", "Government", "Industry"],
  Size: ["Small", "Medium", "Large"],
  Country: ["Sweden", "Switzerland", "Japan", "United States", "United Kingdom", "Germany", "Ireland", "France", "Singapore", "Pan-African"],
};

const STATS = [
  { value: "50K+",  label: "Researchers" },
  { value: "340+",  label: "Institutions" },
  { value: "150+",  label: "Countries" },
  { value: "1.2M+", label: "Projects" },
  { value: "90K+",  label: "Publications" },
  { value: "2M+",   label: "AI Analyses" },
];

const LOGOS = ["MIT", "Oxford", "ETH Zürich", "Kyoto", "Uppsala", "TU Berlin", "CNRS", "NUS", "Charité", "SFI", "Karolinska", "ARUA"];

/* ─── Story card ──────────────────────────────────────────────────────────── */
function StoryCard({ story }) {
  return (
    <div style={{ background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 16, overflow: "hidden", display: "flex", flexDirection: "column",
      transition: "box-shadow 200ms, transform 200ms" }}
      onMouseEnter={e => { e.currentTarget.style.boxShadow = "0 12px 40px rgba(15,40,71,0.09)"; e.currentTarget.style.transform = "translateY(-2px)"; }}
      onMouseLeave={e => { e.currentTarget.style.boxShadow = "none"; e.currentTarget.style.transform = "none"; }}
    >
      {/* Color band / logo area */}
      <div style={{ background: `${story.logoColor}12`, borderBottom: `1px solid ${BORDER}`, padding: "20px 24px", display: "flex", alignItems: "center", gap: 12 }}>
        <div style={{ width: 44, height: 44, borderRadius: 10, background: story.logoColor, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <span style={{ fontSize: "0.58rem", fontWeight: 900, color: "#fff", fontFamily: "system-ui", letterSpacing: "0.03em" }}>{story.logo}</span>
        </div>
        <div>
          <div style={{ fontSize: "0.82rem", fontWeight: 700, color: "#0a0f1a" }}>{story.institution}</div>
          <div style={{ fontSize: "0.7rem", color: "#64748b", display: "flex", alignItems: "center", gap: 5 }}>
            <Globe size={10} strokeWidth={1.5} /> {story.country}
          </div>
        </div>
        <div style={{ marginLeft: "auto" }}>
          <span style={{ fontSize: "0.62rem", fontWeight: 700, color: story.logoColor, background: `${story.logoColor}15`, border: `1px solid ${story.logoColor}25`, padding: "2px 8px", borderRadius: 20 }}>
            {story.category}
          </span>
        </div>
      </div>

      {/* Content */}
      <div style={{ padding: "20px 24px", flex: 1, display: "flex", flexDirection: "column" }}>
        <h3 style={{ fontSize: "0.88rem", fontWeight: 700, color: "#0a0f1a", lineHeight: 1.45, marginBottom: 12 }}>{story.title}</h3>

        {/* Impact metrics */}
        <div style={{ display: "flex", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
          {story.results.slice(0, 2).map(({ metric, label }) => (
            <div key={label} style={{ background: LIGHT, borderRadius: 8, padding: "6px 10px" }}>
              <div style={{ fontSize: "0.9rem", fontWeight: 900, color: NAVY, letterSpacing: "-0.03em" }}>{metric}</div>
              <div style={{ fontSize: "0.6rem", color: "#64748b", lineHeight: 1.3 }}>{label}</div>
            </div>
          ))}
        </div>

        {/* Quote */}
        <blockquote style={{ margin: 0, padding: "10px 14px", background: LIGHT, borderLeft: `3px solid ${NAVY}`, borderRadius: "0 8px 8px 0", flex: 1 }}>
          <p style={{ fontSize: "0.77rem", color: "#334155", lineHeight: 1.65, margin: 0, fontStyle: "italic" }}>
            &ldquo;{story.quote}&rdquo;
          </p>
          <footer style={{ fontSize: "0.68rem", color: "#94a3b8", marginTop: 6, fontStyle: "normal" }}>— {story.author}, {story.role}</footer>
        </blockquote>

        {/* Tags */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginTop: 14 }}>
          {story.tags.map(t => (
            <span key={t} style={{ fontSize: "0.58rem", fontWeight: 600, color: "#64748b", background: "#f1f5f9", borderRadius: 4, padding: "2px 7px" }}>{t}</span>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ─── Featured story ──────────────────────────────────────────────────────── */
function FeaturedStory({ story }) {
  const ref = useReveal();
  return (
    <div ref={ref} className="sq-reveal" style={{ background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 20, overflow: "hidden", boxShadow: "0 4px 24px rgba(0,0,0,0.05)" }}>
      <div className="grid lg:grid-cols-2">
        {/* Left — visual */}
        <div style={{ background: `${story.logoColor}0f`, borderRight: `1px solid ${BORDER}`, padding: "48px 44px", display: "flex", flexDirection: "column", justifyContent: "space-between", minHeight: 380 }}>
          <div>
            <div style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 16 }}>Featured Story</div>
            <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 24 }}>
              <div style={{ width: 56, height: 56, borderRadius: 14, background: story.logoColor, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <span style={{ fontSize: "0.7rem", fontWeight: 900, color: "#fff", letterSpacing: "0.02em" }}>{story.logo}</span>
              </div>
              <div>
                <div style={{ fontSize: "1rem", fontWeight: 800, color: "#0a0f1a" }}>{story.institution}</div>
                <div style={{ fontSize: "0.78rem", color: "#64748b" }}>{story.country}</div>
              </div>
            </div>
            <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
              {story.results.map(({ metric, label }) => (
                <div key={label}>
                  <div style={{ fontSize: "1.6rem", fontWeight: 900, letterSpacing: "-0.04em", color: NAVY }}>{metric}</div>
                  <div style={{ fontSize: "0.72rem", color: "#64748b", lineHeight: 1.4 }}>{label}</div>
                </div>
              ))}
            </div>
          </div>
          <div style={{ display: "flex", gap: 3, marginTop: 32 }}>
            {[1,2,3,4,5].map(s => <Star key={s} size={13} fill={NAVY} strokeWidth={0} style={{ color: NAVY }} />)}
          </div>
        </div>

        {/* Right — story */}
        <div style={{ padding: "48px 44px", display: "flex", flexDirection: "column", justifyContent: "center" }}>
          <span style={{ fontSize: "0.65rem", fontWeight: 700, color: story.logoColor, background: `${story.logoColor}15`, border: `1px solid ${story.logoColor}25`, padding: "3px 10px", borderRadius: 20, alignSelf: "flex-start", marginBottom: 18 }}>{story.category}</span>
          <h2 style={{ fontSize: "clamp(1.1rem, 2vw, 1.5rem)", fontWeight: 900, letterSpacing: "-0.03em", color: "#0a0f1a", lineHeight: 1.25, marginBottom: 16, textWrap: "balance" }}>{story.title}</h2>
          <p style={{ fontSize: "0.84rem", color: "#475569", lineHeight: 1.8, marginBottom: 20 }}>{story.challenge}</p>
          <blockquote style={{ margin: "0 0 24px", padding: "14px 18px", background: LIGHT, borderLeft: `3px solid ${NAVY}`, borderRadius: "0 10px 10px 0" }}>
            <p style={{ fontSize: "0.83rem", color: "#334155", lineHeight: 1.7, margin: 0, fontStyle: "italic" }}>&ldquo;{story.quote}&rdquo;</p>
            <footer style={{ fontSize: "0.7rem", color: "#94a3b8", marginTop: 8, fontStyle: "normal" }}>— {story.author}, {story.role}</footer>
          </blockquote>
          <Link to="/contact" style={{ alignSelf: "flex-start", background: NAVY, color: "#fff", padding: "10px 20px", borderRadius: 8, fontSize: "0.82rem", fontWeight: 700, display: "inline-flex", alignItems: "center", gap: 6 }}>
            Read Case Study <ArrowRight size={13} strokeWidth={2.5} />
          </Link>
        </div>
      </div>
    </div>
  );
}

/* ─── Page ─────────────────────────────────────────────────────────────────── */
export default function CustomerStories() {
  useEffect(() => {
    document.title = "Customer Stories — Synaptiq";
    return () => { document.title = "Synaptiq"; };
  }, []);
  const [activeCategory, setActiveCategory] = useState("All");
  const [search, setSearch] = useState("");
  const rGrid = useReveal();
  const rStats = useReveal();

  const categories = ["All", ...FILTERS.Category];
  const featured = STORIES.find(s => s.featured);
  const rest = STORIES.filter(s => !s.featured);

  const filtered = useMemo(() => {
    return rest.filter(s => {
      const matchCat  = activeCategory === "All" || s.category === activeCategory;
      const matchSearch = search === "" || s.title.toLowerCase().includes(search.toLowerCase()) || s.institution.toLowerCase().includes(search.toLowerCase()) || s.country.toLowerCase().includes(search.toLowerCase());
      return matchCat && matchSearch;
    });
  }, [activeCategory, search, rest]);

  return (
    <MarketingLayout>

      {/* Hero */}
      <section style={{ background: "#fff", borderBottom: `1px solid ${BORDER}`, paddingTop: 72, paddingBottom: 64 }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10">
          <div style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 16 }}>Resources</div>
          <div className="grid lg:grid-cols-2 gap-12 items-end">
            <div>
              <h1 style={{ fontSize: "clamp(2.8rem, 6vw, 5rem)", fontWeight: 900, letterSpacing: "-0.045em", color: "#0a0f1a", lineHeight: 1.0, marginBottom: 18 }}>
                Customer Stories
              </h1>
              <p style={{ fontSize: "1rem", color: "#64748b", lineHeight: 1.75, maxWidth: 480 }}>
                Illustrative scenarios showing how universities, research institutes and funding agencies can use Synaptiq to transform their research operations.
              </p>
              <p style={{ fontSize: "0.72rem", color: "#94a3b8", marginTop: 10 }}>These are illustrative examples based on platform capabilities, not verified customer testimonials.</p>
            </div>
            <div>
              {/* Logo strip */}
              <div style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 14 }}>Trusted by</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {LOGOS.map(name => (
                  <div key={name} style={{ background: LIGHT, border: `1px solid ${BORDER}`, borderRadius: 8, padding: "6px 14px", fontSize: "0.78rem", fontWeight: 700, color: "#64748b" }}>{name}</div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Featured story */}
      <section style={{ background: LIGHT, borderBottom: `1px solid ${BORDER}` }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-16 lg:py-20">
          {featured && <FeaturedStory story={featured} />}
        </div>
      </section>

      {/* Filter bar + grid */}
      <section style={{ background: "#fff" }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-16 lg:py-20">

          {/* Filters */}
          <div className="flex flex-wrap items-center gap-3 mb-10">
            <div style={{ display: "flex", alignItems: "center", gap: 8, background: LIGHT, border: `1px solid ${BORDER}`, borderRadius: 9, padding: "9px 14px", flex: 1, maxWidth: 320 }}>
              <Search size={14} strokeWidth={1.5} style={{ color: "#94a3b8", flexShrink: 0 }} />
              <input
                value={search}
                onChange={e => setSearch(e.target.value)}
                placeholder="Search by institution, country…"
                style={{ border: "none", background: "transparent", outline: "none", fontSize: "0.83rem", color: "#0a0f1a", width: "100%" }}
              />
              {search && <button onClick={() => setSearch("")} style={{ border: "none", background: "none", cursor: "pointer", color: "#94a3b8" }}><X size={12} /></button>}
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {categories.map(cat => (
                <button key={cat} onClick={() => setActiveCategory(cat)}
                  style={{
                    padding: "7px 14px", borderRadius: 20, fontSize: "0.78rem", fontWeight: 600, cursor: "pointer", border: "1px solid",
                    background: activeCategory === cat ? NAVY : "#fff",
                    color: activeCategory === cat ? "#fff" : "#64748b",
                    borderColor: activeCategory === cat ? NAVY : BORDER,
                    transition: "all 150ms",
                  }}
                >{cat}</button>
              ))}
            </div>
          </div>

          {/* Results count */}
          <div style={{ fontSize: "0.78rem", color: "#94a3b8", marginBottom: 24 }}>
            Showing {filtered.length} {filtered.length === 1 ? "story" : "stories"}
            {activeCategory !== "All" && ` in ${activeCategory}`}
            {search && ` matching "${search}"`}
          </div>

          {/* Grid */}
          {filtered.length > 0 ? (
            <div ref={rGrid} className="sq-reveal grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {filtered.map(story => <StoryCard key={story.id} story={story} />)}
            </div>
          ) : (
            <div style={{ textAlign: "center", padding: "64px 0" }}>
              <div style={{ fontSize: "2rem", marginBottom: 16, opacity: 0.2 }}>🔍</div>
              <div style={{ fontSize: "0.92rem", fontWeight: 600, color: "#64748b" }}>No stories found for that search.</div>
              <button onClick={() => { setSearch(""); setActiveCategory("All"); }} style={{ marginTop: 16, fontSize: "0.82rem", color: NAVY, fontWeight: 700, border: "none", background: "none", cursor: "pointer" }}>Clear filters</button>
            </div>
          )}
        </div>
      </section>

      {/* Stats band */}
      <section style={{ background: NAVY }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-20">
          <div ref={rStats} className="sq-reveal">
            <div style={{ textAlign: "center", marginBottom: 48 }}>
              <h2 style={{ fontSize: "clamp(1.8rem, 3.5vw, 2.8rem)", fontWeight: 900, letterSpacing: "-0.04em", color: "#fff", lineHeight: 1.1 }}>
                The platform behind the world's research.
              </h2>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-8">
              {STATS.map(({ value, label }) => (
                <div key={label} style={{ textAlign: "center" }}>
                  <div style={{ fontSize: "clamp(1.6rem, 3vw, 2.4rem)", fontWeight: 900, letterSpacing: "-0.04em", color: "#fff", lineHeight: 1 }}>{value}</div>
                  <div style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.4)", marginTop: 8, fontWeight: 600 }}>{label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section style={{ background: LIGHT }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-24 text-center">
          <h2 style={{ fontSize: "clamp(1.8rem, 3.5vw, 3rem)", fontWeight: 900, letterSpacing: "-0.04em", color: "#0a0f1a", lineHeight: 1.08, marginBottom: 16 }}>
            Join 50,000+ researchers who chose Synaptiq.
          </h2>
          <p style={{ fontSize: "0.92rem", color: "#64748b", marginBottom: 32 }}>Start for free. No credit card required.</p>
          <div className="flex justify-center gap-4 flex-wrap">
            <Link to="/register" style={{ background: NAVY, color: "#fff", padding: "13px 28px", borderRadius: 9, fontWeight: 700, fontSize: "0.9rem", display: "inline-flex", alignItems: "center", gap: 6 }}>
              Start Free <ArrowRight size={14} strokeWidth={2.5} />
            </Link>
            <Link to="/contact" style={{ border: `1px solid ${BORDER}`, color: "#0a0f1a", padding: "12px 24px", borderRadius: 9, fontWeight: 600, fontSize: "0.9rem" }}>
              Request a Demo
            </Link>
          </div>
        </div>
      </section>

    </MarketingLayout>
  );
}
