/* eslint-disable */
import React, { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import MarketingLayout from "../components/layout/MarketingLayout";
import ResearchPreviewDemo from "../components/marketing/ResearchPreviewDemo";
import ResearchThread from "../components/marketing/ResearchThread";
import ProductProof from "../components/marketing/ProductProof";
import { trackMarketingEvent as track } from "../lib/marketingAnalytics";
import { setPageSeo } from "../lib/seo";
import {
  ArrowRight, Users, FileText, Globe, Shield, BarChart3, Sparkles,
  CheckCircle2, Building2, Zap, FlaskConical, BrainCircuit, Target,
  BookMarked, ChevronRight, Star, GraduationCap, Microscope, TrendingUp,
  FolderOpen, LayoutGrid, Archive, BookOpen, BadgeDollarSign, Award,
  Network, Briefcase, ChevronDown, AlignLeft, PenLine, Activity,
} from "lucide-react";
import { TID } from "../lib/testIds";

/* ─── Hooks ──────────────────────────────────────────────────────────────── */

function useReveal(threshold = 0.08) {
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (typeof IntersectionObserver === "undefined") { el.classList.add("sq-in"); return; }
    const obs = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) { el.classList.add("sq-in"); obs.disconnect(); } },
      { threshold }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, []);
  return ref;
}

function useCounter(target, duration = 1800) {
  const [value, setValue] = useState(0);
  const [started, setStarted] = useState(false);
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting && !started) { setStarted(true); obs.disconnect(); } },
      { threshold: 0.5 }
    );
    obs.observe(el);
    return () => obs.disconnect();
  }, [started]);
  useEffect(() => {
    if (!started) return;
    let start = null;
    const step = (ts) => {
      if (!start) start = ts;
      const p = Math.min((ts - start) / duration, 1);
      const ease = 1 - Math.pow(1 - p, 3);
      setValue(Math.round(ease * target));
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [started, target, duration]);
  return { ref, value };
}

/* ─── Hero Illustration ──────────────────────────────────────────────────── */

function HeroIllustration() {
  const [activeNode, setActiveNode] = useState(null);

  {/* Illustrative expertise areas, not real people or matches — see §6/§7:
      the public site must never fabricate researchers or fake matches. */}
  const nodes = [
    { id: "a", x: 52, y: 28, label: "Machine Learning",     sub: "Expertise area", color: "#0F2847", initials: "ML" },
    { id: "b", x: 82, y: 52, label: "Public Health",        sub: "Expertise area", color: "#1d4ed8", initials: "PH" },
    { id: "c", x: 60, y: 78, label: "Policy Research",      sub: "Expertise area", color: "#0F2847", initials: "PR" },
    { id: "d", x: 22, y: 72, label: "Clinical Methods",     sub: "Expertise area", color: "#1d4ed8", initials: "CM" },
    { id: "e", x: 14, y: 40, label: "Data Science",         sub: "Expertise area", color: "#0F2847", initials: "DS" },
  ];

  const edges = [["a","b"],["b","c"],["c","d"],["d","e"],["e","a"],["a","c"],["b","d"]];

  return (
    <div style={{ position: "relative", width: "100%", height: 480, userSelect: "none" }}>

      {/* Main workspace card */}
      <div style={{
        position: "absolute", top: 20, left: "5%", right: "2%",
        background: "#fff", borderRadius: 16, border: "1px solid #e2e8f0",
        boxShadow: "0 16px 64px rgba(15,40,71,0.12), 0 4px 16px rgba(15,40,71,0.06)",
        overflow: "hidden",
      }}>
        {/* Card header */}
        <div style={{ background: "#0F2847", padding: "12px 20px", display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{ display: "flex", gap: 5 }}>
            {["#ff5f56","#febc2e","#28c840"].map((c) => <div key={c} style={{ width: 10, height: 10, borderRadius: "50%", background: c }} />)}
          </div>
          <div style={{ flex: 1, textAlign: "center", fontSize: "0.65rem", color: "rgba(255,255,255,0.7)", fontWeight: 600, letterSpacing: "0.08em" }}>Synaptiq Research Workspace</div>
        </div>

        {/* Network SVG visualization */}
        <div style={{ padding: "24px 20px 16px", background: "#f8fafc" }}>
          <svg viewBox="0 0 100 90" style={{ width: "100%", height: 260, overflow: "visible" }}>
            {/* Connection lines */}
            {edges.map(([a, b]) => {
              const na = nodes.find((n) => n.id === a);
              const nb = nodes.find((n) => n.id === b);
              return (
                <line key={`${a}-${b}`}
                  x1={na.x} y1={na.y} x2={nb.x} y2={nb.y}
                  stroke="#e2e8f0" strokeWidth="0.6" strokeDasharray="2 1.5"
                />
              );
            })}
            {/* Highlight active edges */}
            {activeNode && edges.filter(([a, b]) => a === activeNode || b === activeNode).map(([a, b]) => {
              const na = nodes.find((n) => n.id === a);
              const nb = nodes.find((n) => n.id === b);
              return (
                <line key={`hl-${a}-${b}`}
                  x1={na.x} y1={na.y} x2={nb.x} y2={nb.y}
                  stroke="#0F2847" strokeWidth="0.8" opacity="0.4"
                />
              );
            })}

            {/* Center node — AI Copilot */}
            <circle cx="48" cy="50" r="9" fill="#0F2847" />
            <text x="48" y="47.5" textAnchor="middle" style={{ fontSize: "3.5px", fill: "#fff", fontWeight: 700, fontFamily: "system-ui" }}>AI</text>
            <text x="48" y="52.5" textAnchor="middle" style={{ fontSize: "2.8px", fill: "rgba(255,255,255,0.7)", fontFamily: "system-ui" }}>Copilot</text>

            {/* Lines from center to each node */}
            {nodes.map((n) => (
              <line key={`c-${n.id}`}
                x1={48} y1={50} x2={n.x} y2={n.y}
                stroke={activeNode === n.id ? "#0F2847" : "#cbd5e1"}
                strokeWidth={activeNode === n.id ? "0.8" : "0.5"}
                opacity={activeNode === n.id ? 0.7 : 0.5}
              />
            ))}

            {/* Researcher nodes */}
            {nodes.map((n) => (
              <g key={n.id}
                style={{ cursor: "pointer" }}
                onMouseEnter={() => setActiveNode(n.id)}
                onMouseLeave={() => setActiveNode(null)}
              >
                <circle cx={n.x} cy={n.y} r={activeNode === n.id ? 7 : 6}
                  fill={n.color}
                  style={{ transition: "r 150ms ease" }}
                  stroke={activeNode === n.id ? "#fff" : "transparent"}
                  strokeWidth={2}
                />
                <text x={n.x} y={n.y + 1.2} textAnchor="middle"
                  style={{ fontSize: "3px", fill: "#fff", fontWeight: 700, fontFamily: "system-ui", pointerEvents: "none" }}>
                  {n.initials}
                </text>
                {activeNode === n.id && (
                  <>
                    <rect x={n.x - 16} y={n.y + 8} width={32} height={14} rx="1.5" fill="#0F2847" />
                    <text x={n.x} y={n.y + 14} textAnchor="middle" style={{ fontSize: "2.8px", fill: "#fff", fontWeight: 700, fontFamily: "system-ui" }}>{n.label}</text>
                    <text x={n.x} y={n.y + 19} textAnchor="middle" style={{ fontSize: "2.4px", fill: "rgba(255,255,255,0.65)", fontFamily: "system-ui" }}>{n.sub}</text>
                  </>
                )}
              </g>
            ))}
          </svg>
        </div>

        {/* Bottom status bar — qualitative, not fabricated usage numbers */}
        <div style={{ padding: "12px 20px", borderTop: "1px solid #f1f5f9", display: "flex", alignItems: "center", gap: 16 }}>
          {[
            { label: "Explainable matches", color: "#0F2847" },
            { label: "Real profiles only", color: "#1d4ed8" },
            { label: "Human-approved contact", color: "#059669" },
          ].map(({ label, color }) => (
            <div key={label} style={{ flex: 1, textAlign: "center" }}>
              <div style={{ width: 6, height: 6, borderRadius: "50%", background: color, margin: "0 auto 4px" }} />
              <div style={{ fontSize: "0.62rem", color: "#64748b", fontWeight: 600 }}>{label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Floating notification card — illustrative UI state, not a real match */}
      <div style={{
        position: "absolute", top: 8, right: "0%",
        background: "#fff", borderRadius: 10, border: "1px solid #e2e8f0",
        boxShadow: "0 4px 20px rgba(15,40,71,0.1)", padding: "10px 14px",
        maxWidth: 200, zIndex: 10,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#10b981", flexShrink: 0 }} />
          <span style={{ fontSize: "0.65rem", fontWeight: 700, color: "#0f172a" }}>Relevant expertise found</span>
        </div>
        <div style={{ fontSize: "0.6rem", color: "#64748b", marginTop: 4, lineHeight: 1.5 }}>Complementary methods identified<br />You decide who to contact</div>
      </div>
    </div>
  );
}

/* ─── World Map Visualization ────────────────────────────────────────────── */

function WorldMap() {
  const dots = [
    // North America
    { x: 18, y: 28 }, { x: 22, y: 32 }, { x: 15, y: 35 }, { x: 26, y: 26 },
    // Europe
    { x: 48, y: 22 }, { x: 50, y: 25 }, { x: 52, y: 20 }, { x: 46, y: 28 }, { x: 54, y: 24 },
    // Africa
    { x: 50, y: 42 }, { x: 52, y: 48 }, { x: 48, y: 50 },
    // Asia
    { x: 68, y: 22 }, { x: 72, y: 28 }, { x: 76, y: 32 }, { x: 64, y: 30 }, { x: 78, y: 24 }, { x: 74, y: 20 },
    // South America
    { x: 28, y: 50 }, { x: 30, y: 56 }, { x: 26, y: 58 },
    // Oceania
    { x: 80, y: 55 }, { x: 84, y: 52 },
  ];

  const connections = [
    [{ x: 22, y: 32 }, { x: 48, y: 22 }],
    [{ x: 48, y: 22 }, { x: 68, y: 22 }],
    [{ x: 50, y: 25 }, { x: 72, y: 28 }],
    [{ x: 22, y: 32 }, { x: 30, y: 56 }],
    [{ x: 50, y: 25 }, { x: 50, y: 42 }],
    [{ x: 68, y: 22 }, { x: 80, y: 55 }],
    [{ x: 26, y: 26 }, { x: 48, y: 22 }],
  ];

  return (
    <div style={{ position: "relative", background: "#f8fafc", borderRadius: 16, border: "1px solid #e8edf3", padding: 32, overflow: "hidden" }}>
      <svg viewBox="0 0 100 72" style={{ width: "100%", height: "auto" }}>
        {/* Subtle globe grid */}
        {[20, 40, 60, 80].map((x) => (
          <line key={`vg-${x}`} x1={x} y1={0} x2={x} y2={72} stroke="#e2e8f0" strokeWidth="0.3" />
        ))}
        {[18, 36, 54].map((y) => (
          <line key={`hg-${y}`} x1={0} y1={y} x2={100} y2={y} stroke="#e2e8f0" strokeWidth="0.3" />
        ))}

        {/* Simplified continent shapes (abstract) */}
        {/* N America */}
        <ellipse cx="22" cy="30" rx="10" ry="11" fill="#e8edf3" opacity="0.7" />
        {/* S America */}
        <ellipse cx="28" cy="54" rx="6" ry="8" fill="#e8edf3" opacity="0.7" />
        {/* Europe */}
        <ellipse cx="50" cy="24" rx="7" ry="6" fill="#e8edf3" opacity="0.7" />
        {/* Africa */}
        <ellipse cx="50" cy="46" rx="7" ry="10" fill="#e8edf3" opacity="0.7" />
        {/* Asia */}
        <ellipse cx="72" cy="26" rx="16" ry="12" fill="#e8edf3" opacity="0.7" />
        {/* Oceania */}
        <ellipse cx="82" cy="54" rx="6" ry="4" fill="#e8edf3" opacity="0.7" />

        {/* Connection arcs */}
        {connections.map(([a, b], i) => (
          <line key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y}
            stroke="#0F2847" strokeWidth="0.4" opacity="0.25" strokeDasharray="1.5 1"
          />
        ))}

        {/* Research dots */}
        {dots.map(({ x, y }, i) => (
          <circle key={i} cx={x} cy={y} r="1.2" fill="#0F2847" opacity="0.7" />
        ))}

        {/* Active connection dots */}
        {[{ x: 22, y: 32 }, { x: 48, y: 22 }, { x: 68, y: 22 }].map(({ x, y }, i) => (
          <circle key={`ac-${i}`} cx={x} cy={y} r="2.2" fill="#0F2847" opacity="0.15" />
        ))}
        {[{ x: 22, y: 32 }, { x: 48, y: 22 }, { x: 68, y: 22 }].map(({ x, y }, i) => (
          <circle key={`ac2-${i}`} cx={x} cy={y} r="1.4" fill="#0F2847" opacity="0.9" />
        ))}
      </svg>

      {/* Legend */}
      <div style={{ marginTop: 16, display: "flex", alignItems: "center", gap: 16, justifyContent: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
          <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#0F2847" }} />
          <span style={{ fontSize: "0.68rem", color: "#64748b" }}>Research nodes</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
          <div style={{ width: 16, height: 1, borderTop: "1px dashed #0F2847", opacity: 0.4 }} />
          <span style={{ fontSize: "0.68rem", color: "#64748b" }}>Active collaborations</span>
        </div>
      </div>
    </div>
  );
}

/* ─── AI Workspace Mockup ────────────────────────────────────────────────── */

function AIWorkspaceMockup() {
  return (
    <div style={{
      background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)",
      borderRadius: 16, overflow: "hidden", minWidth: 0, maxWidth: "100%",
    }}>
      {/* Toolbar */}
      <div style={{ background: "rgba(255,255,255,0.04)", padding: "10px 20px", borderBottom: "1px solid rgba(255,255,255,0.06)", display: "flex", alignItems: "center", gap: 8 }}>
        <div style={{ width: 8, height: 8, borderRadius: "50%", background: "rgba(255,255,255,0.2)" }} />
        <div style={{ flex: 1, background: "rgba(255,255,255,0.06)", borderRadius: 4, height: 6 }} />
        <div style={{ fontSize: "0.6rem", color: "rgba(255,255,255,0.4)", fontWeight: 600, letterSpacing: "0.06em" }}>AI COPILOT</div>
      </div>
      {/* Explicit "example" label — this mockup's numbers are illustrative,
          not a real live result; never blur that boundary (§7). */}
      <div style={{ padding: "8px 20px 0" }}>
        <span style={{ fontSize: "0.58rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "#f59e0b", background: "rgba(245,158,11,0.12)", padding: "3px 8px", borderRadius: 4 }}>
          Example output
        </span>
      </div>
      {/* Tool tabs — horizontally scrollable so 4 fixed labels never force the
          grid cell (and the page) wider than the viewport on narrow screens */}
      <div style={{ display: "flex", borderBottom: "1px solid rgba(255,255,255,0.06)", padding: "0 20px", overflowX: "auto", WebkitOverflowScrolling: "touch" }}>
        {["Literature Review", "Gap Detection", "Manuscript", "Statistics"].map((t, i) => (
          <div key={t} style={{
            padding: "10px 12px", fontSize: "0.62rem", fontWeight: i === 0 ? 700 : 400,
            color: i === 0 ? "#fff" : "rgba(255,255,255,0.4)",
            borderBottom: i === 0 ? "2px solid #fff" : "2px solid transparent",
            whiteSpace: "nowrap", flexShrink: 0,
          }}>{t}</div>
        ))}
      </div>
      {/* Content */}
      <div style={{ padding: 24 }}>
        {/* User query */}
        <div style={{ background: "rgba(255,255,255,0.06)", borderRadius: 8, padding: "10px 14px", marginBottom: 16 }}>
          <div style={{ fontSize: "0.6rem", color: "rgba(255,255,255,0.3)", marginBottom: 4, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em" }}>Your query</div>
          <div style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.8)", lineHeight: 1.6 }}>
            Summarize current literature on CRISPR off-target effects in therapeutic applications
          </div>
        </div>
        {/* AI response */}
        <div style={{ borderLeft: "2px solid rgba(255,255,255,0.15)", paddingLeft: 16, marginBottom: 16 }}>
          <div style={{ fontSize: "0.6rem", color: "rgba(255,255,255,0.4)", marginBottom: 8, fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.08em" }}>Synaptiq AI · Literature Analysis</div>
          {[
            "Analyzed 847 papers across PubMed, Semantic Scholar, and bioRxiv (2019–2024).",
            "Key finding: 73% of studies report off-target rates below 0.1% with modern guide RNA design.",
            "Research gap identified: Long-term in vivo studies in primate models are underrepresented (n=12).",
          ].map((line, i) => (
            <div key={i} style={{ display: "flex", gap: 8, marginBottom: 8 }}>
              <div style={{ width: 4, height: 4, borderRadius: "50%", background: "rgba(255,255,255,0.3)", flexShrink: 0, marginTop: 6 }} />
              <div style={{ fontSize: "0.73rem", color: "rgba(255,255,255,0.65)", lineHeight: 1.65 }}>{line}</div>
            </div>
          ))}
        </div>
        {/* Tags */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
          {["847 papers", "6 journals", "12 key themes", "3 research gaps"].map((t) => (
            <span key={t} style={{ fontSize: "0.6rem", color: "rgba(255,255,255,0.5)", background: "rgba(255,255,255,0.07)", padding: "3px 9px", borderRadius: 5, fontWeight: 600 }}>{t}</span>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ─── Stat Counter ───────────────────────────────────────────────────────── */

function StatCounter({ target, suffix = "", label, sub }) {
  const { ref, value } = useCounter(target);
  return (
    <div ref={ref} style={{ textAlign: "center" }}>
      <div style={{ fontSize: "clamp(2.4rem, 4vw, 3.5rem)", fontWeight: 900, color: "#fff", lineHeight: 1, letterSpacing: "-0.04em" }}>
        {value.toLocaleString()}{suffix}
      </div>
      <div style={{ fontSize: "1rem", fontWeight: 700, color: "rgba(255,255,255,0.75)", marginTop: 8 }}>{label}</div>
      {sub && <div style={{ fontSize: "0.78rem", color: "rgba(255,255,255,0.4)", marginTop: 4 }}>{sub}</div>}
    </div>
  );
}

/* ─── Static data ─────────────────────────────────────────────────────────── */

const PLATFORM_CARDS = [
  { icon: Users,         title: "Find Collaborators",      body: "AI-matched co-authors, mentors, and research partners across 150+ countries." },
  { icon: BrainCircuit,  title: "AI Research Workspace",   body: "Copilot for literature review, manuscript writing, statistical analysis, and more." },
  { icon: Network,       title: "Academic Networking",     body: "Connect with researchers, professors, and institutions worldwide." },
  { icon: FolderOpen,    title: "Project Management",      body: "Manage research projects with tasks, milestones, and collaborative workspaces." },
  { icon: BookMarked,    title: "Literature Discovery",    body: "Semantic search, synthesis, citation monitoring, and research gap detection." },
  { icon: BadgeDollarSign,title: "Grant Discovery",        body: "Funding calls surfaced and matched to your research profile and area." },
  { icon: FileText,      title: "Publication Hub",         body: "Journal matching, manuscript workflows, peer review, and submission tools." },
  { icon: BarChart3,     title: "Research Analytics",      body: "Impact scores, H-index tracking, citation monitoring, and benchmarking." },
];

const COLLAB_STEPS = [
  "Find collaborators using AI-powered matching across disciplines and institutions.",
  "Send collaboration requests with a short pitch and research brief.",
  "Create a shared research workspace in seconds.",
  "Assign roles — lead author, co-author, reviewer, data analyst.",
  "Manage tasks, milestones, and manuscript versions together.",
  "Review and track contributions with full audit trail.",
];

const AI_FEATURES = [
  { icon: BookMarked,  label: "Literature Review",      body: "Synthesize hundreds of papers into structured insights." },
  { icon: Target,      label: "Research Gap Detection", body: "Identify unanswered questions in your field." },
  { icon: FlaskConical,label: "Study Design Advisor",   body: "Design robust methodologies with expert guidance." },
  { icon: BarChart3,   label: "Statistics Assistant",   body: "Power analysis, method selection, and validation." },
  { icon: PenLine,     label: "Writing Assistant",      body: "Draft, rewrite, and improve your academic prose." },
  { icon: Microscope,  label: "Peer Review AI",         body: "Structural review and journal fit scoring before submission." },
  { icon: Archive,     label: "Reference Management",   body: "Citation formatting, deduplication, and monitoring." },
  { icon: Sparkles,    label: "AI Recommendations",     body: "Personalized suggestions based on your research goals." },
];

const WORKFLOW = [
  { step: "01", title: "Discover",     icon: Globe,         body: "Find open collaborations, grants, and venues matching your research." },
  { step: "02", title: "Connect",      icon: Users,         body: "Match with researchers whose methods and goals align with yours." },
  { step: "03", title: "Create Team",  icon: Building2,     body: "Form a research team with defined roles and shared workspace." },
  { step: "04", title: "Research",     icon: FlaskConical,  body: "Conduct literature review, gap analysis, and study design together." },
  { step: "05", title: "Write",        icon: PenLine,       body: "Co-author manuscripts with version control and AI assistance." },
  { step: "06", title: "Review",       icon: Microscope,    body: "Get AI feedback and peer review before submission." },
  { step: "07", title: "Publish",      icon: FileText,      body: "Submit to matched journals with full submission packages." },
  { step: "08", title: "Measure",      icon: TrendingUp,    body: "Track citations, impact scores, and research reputation." },
];

const SHOWCASE = [
  {
    eyebrow: "Projects & Workspaces",
    title: "Your entire research project in one place.",
    body: "Create structured research projects with tasks, milestones, document management, and team collaboration — all connected to your literature review and manuscript.",
    features: ["Task management", "Milestone tracking", "Document versioning", "Team roles"],
    bg: "#f0f4ff",
  },
  {
    eyebrow: "Academic Marketplace",
    title: "Find and offer expert research services.",
    body: "Connect with statistical consultants, peer reviewers, editors, and translators. Build a secondary income from your academic expertise or get the help your research needs.",
    features: ["Browse expert services", "Post your own services", "Secure payments", "Quality reviews"],
    bg: "#f0fdf4",
  },
  {
    eyebrow: "Institution Dashboard",
    title: "Enterprise intelligence for research offices.",
    body: "Monitor your institution's research output, faculty performance, grant pipeline, and collaboration network through a unified analytics dashboard.",
    features: ["Faculty analytics", "Grant intelligence", "Collaboration tracking", "Benchmark reports"],
    bg: "#fef9f0",
  },
  {
    eyebrow: "Research Identity",
    title: "Your Academic Passport.",
    body: "Research areas, methods, and expertise you declare yourself, alongside what's independently connected — ORCID, institutional affiliation, your publication record. Each element shows its own status; the Passport as a whole isn't marketed as \"verified.\"",
    features: ["Connected: ORCID", "Verified: institution", "Self-declared: expertise", "Research record"],
    bg: "#f5f0ff",
  },
];

// featured: false on every tier — §24/§42, no popularity badge without real
// usage data. Institution shows no public price (§37) — organization
// billing doesn't exist yet; a number here would imply self-service
// purchase that isn't real.
// Summary only — the canonical plan definitions are served by
// GET /api/billing/plans (backend/plans_catalogue.py) and rendered in full on
// /pricing. Paid CTAs go to /pricing, never straight to checkout.
const PRICING_TIERS = [
  {
    name: "Free",         price: "€0",     period: "/mo",
    desc: "Build your academic presence.",
    features: ["Academic profile & public research page", "ORCID integration & publication import", "Discoverable by Pro researchers", "Receive collaboration invitations"],
    cta: "Create Free Profile", featured: false, href: "/register",
  },
  {
    name: "Pro",   price: "€9.99",  period: "/mo", badge: "Early Access · Recommended",
    desc: "For active research, collaboration and AI-assisted workflows.",
    features: ["200 AI credits / month", "Research network, messaging & collaboration", "Unlimited projects, up to 10 workspaces", "Journal, conference & grant discovery", "AI Research Assistant & Manuscript Copilot", "10 GB storage"],
    cta: "See plans", featured: true, href: "/pricing",
  },
  {
    name: "Pro Advanced", price: "€29.99", period: "/mo",
    desc: "For advanced research intelligence, analysis and impact workflows.",
    features: ["Everything in Pro", "750 AI credits / month", "Unlimited workspaces, 50 GB storage", "Collaboration Intelligence & Impact Dashboard", "Citation Monitoring & Advanced Analytics", "Advanced Manuscript Intelligence"],
    cta: "See plans", featured: false, href: "/pricing",
  },
  {
    name: "Institution",  price: "Custom",   period: "",
    desc: "For universities, research institutions and organizations.",
    features: ["Institution workspace for approved members", "Member and department management", "Institutional analytics", "Admin permissions", "Seats and credits set per agreement"],
    cta: "Contact sales", featured: false, href: "/contact?topic=institution",
  },
];

const FAQ = [
  { q: "What is Synaptiq?", a: "Synaptiq is a research collaboration platform. It connects researcher identity, expert discovery, collaboration, project workspaces, AI-assisted research tools, and publication workflows into one environment — built for the full academic lifecycle." },
  { q: "Who is Synaptiq for?", a: "Researchers, doctoral candidates, educators, health and scientific professionals, policy and public-sector experts, and interdisciplinary collaborators. The platform adapts to how you use it, not to a fixed role." },
  { q: "Can I use Synaptiq without ORCID?", a: "Yes. ORCID is optional — connecting it strengthens your research record with synced publications, but you can create a full profile and use Synaptiq without it." },
  { q: "What is Academic Passport?", a: "Academic Passport is your structured research identity: research areas and interests, methods, professional expertise, institution affiliation, ORCID connection, research record, and collaboration preferences. Different elements have different verification states — it isn't marketed as universally \"verified.\"" },
  { q: "What does \"verified\" mean on Synaptiq?", a: "It depends on the specific badge. ORCID connection confirms you control that ORCID account. Institution verification confirms an affiliation claim, typically via an institutional email or admin approval. Neither verifies a professional license or credential — see below." },
  { q: "Can I use Synaptiq if my university doesn't subscribe?", a: "Yes. An individual account (Free, Pro or Pro Advanced) works independently of any institutional subscription. Institutional features are separate and only apply to verified members of a Synaptiq institution." },
  { q: "What's the difference between Pro and Institutional?", a: "Pro and Pro Advanced are individual subscriptions for one person's research, collaboration, and teaching work. Institutional is an organization product — it provisions a shared institution workspace with member management and departments for a university or research organization. No individual subscription grants institutional access, and institutional membership isn't purchased on an individual account." },
  { q: "What does the Free plan include?", a: "Free is your academic identity: a profile and public research page, ORCID integration and publication import, and being discoverable by Pro researchers — who can invite you to collaborate. Messaging, collaboration, projects, workspaces, discovery and AI tools are part of Pro." },
  { q: "Do I need a paid plan for Teaching?", a: "Yes. The Teaching Hub — courses, lesson planner, assessment builder and teaching workspaces — is part of Pro. AI-assisted teaching actions, like generating a lesson or assessment, use AI credits; advanced AI teaching is part of Pro Advanced." },
  { q: "What uses AI credits?", a: "AI-assisted actions — literature synthesis, manuscript review, statistical review, journal/conference/grant fit and similar — have a fixed, published credit cost, shown before you run them. Pro includes 200 AI credits a month and Pro Advanced 750; monthly credits reset at each renewal, and extra credit packs never expire. Failed requests are refunded automatically." },
  { q: "Does finding or collaborating with people use AI credits?", a: "No. On Pro, discovery, messaging and sending or responding to collaboration requests never use credits — only optional AI-assisted steps (like interpreting a research question with AI) do, and the cost is shown before you commit to it." },
  { q: "Can Synaptiq guarantee publication or funding?", a: "No. Synaptiq can help you find relevant people, methods, and opportunities, but it doesn't and can't guarantee publication acceptance, peer-review outcomes, or funding success." },
  { q: "Does Synaptiq verify professional licenses or credentials?", a: "No. Synaptiq doesn't independently verify professional licensure (e.g., that someone is a licensed physician or lawyer). ORCID and institution verification confirm specific, narrower claims — see \"What does verified mean\" above." },
  { q: "How does collaboration work?", a: "Post an open collaboration with your requirements, or send a direct collaboration request to someone you've discovered. The other person reviews and accepts — nothing is sent on your behalf without your approval, and acceptance creates a shared workspace." },
  { q: "How is research data protected?", a: "All data is encrypted in transit (TLS 1.2+) and at rest. Authentication uses httpOnly cookies and bcrypt. We are GDPR-aligned and never sell user data." },
  { q: "Can I cancel a paid plan?", a: "Yes, any time from your account settings. You keep access until the end of your current billing period, then your plan reverts to Free." },
  { q: "What happens to my work if I cancel or downgrade?", a: "Nothing is deleted. Your projects, workspaces and files are kept. Anything above your new plan's limits becomes read-only until you upgrade again or make room. Purchased credits are kept too, ready for when you're back on a paid plan." },
];

/* ─── Landing Page ───────────────────────────────────────────────────────── */

export default function Landing() {
  useEffect(() => {
    return setPageSeo({
      title: "Synaptiq — Research starts with a question",
      description: "Synaptiq connects research identity, expert discovery, collaboration, and project workspaces in one environment — with AI assistance, never AI in charge.",
      path: "/",
    });
  }, []);
  const refTrusted   = useReveal();
  const refPlatform  = useReveal();
  const refCollab    = useReveal();
  const refAI        = useReveal();
  const refShowcase  = useReveal();
  const refStats     = useReveal();
  const refTestimonials = useReveal();
  const refPricing   = useReveal();
  const refFaq       = useReveal();
  const refCta       = useReveal();
  const [openFaq, setOpenFaq] = useState(null);

  return (
    <MarketingLayout>

      {/* ══════════════════════════════════════════════════════════════════════
          SECTION 1 — HERO
      ══════════════════════════════════════════════════════════════════════ */}
      <section
        data-testid={TID.landingHero}
        className="bg-white"
        style={{ borderBottom: "1px solid #f1f5f9" }}
      >
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 pt-20 pb-0 lg:pt-28">
          <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">

            {/* Left: text */}
            <div>
              {/* Badge */}
              <div className="inline-flex items-center gap-2 sq-fade-up" style={{
                background: "#f0f4ff", border: "1px solid #c7d7fe",
                borderRadius: 999, padding: "5px 14px", marginBottom: 32,
              }}>
                <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#0F2847" }} />
                <span style={{ fontSize: "0.72rem", fontWeight: 700, color: "#0F2847", letterSpacing: "0.06em", textTransform: "uppercase" }}>
                  The Academic Collaboration Platform
                </span>
              </div>

              <h1 className="sq-fade-up sq-delay-1" style={{
                fontSize: "clamp(2.8rem, 5vw, 4.2rem)",
                lineHeight: 1.06, fontWeight: 900,
                letterSpacing: "-0.04em", color: "#0a0f1a",
                textWrap: "balance",
              }}>
                Research starts with<br />
                <span style={{ color: "#0F2847" }}>a question.</span>
              </h1>

              <p className="sq-fade-up sq-delay-2" style={{
                fontSize: "clamp(1rem, 1.6vw, 1.15rem)",
                color: "#475569", lineHeight: 1.75,
                maxWidth: 520, marginTop: 24,
              }}>
                Synaptiq turns it into expertise, then people, then a collaboration —
                with a research identity, AI-assisted tools, and project workspaces to carry the work forward.
              </p>

              <div className="flex items-center gap-4 flex-wrap sq-fade-up sq-delay-3" style={{ marginTop: 36 }}>
                <Link
                  to="/register"
                  data-testid={TID.landingGetStarted}
                  onClick={() => track("landing_primary_cta", { label: "Start Free" })}
                  className="inline-flex items-center gap-2.5 font-semibold transition-all duration-150 active:scale-[.98]"
                  style={{ background: "#0F2847", color: "#fff", padding: "13px 28px", borderRadius: 10, fontSize: "0.93rem" }}
                >
                  Start Free <ArrowRight size={15} strokeWidth={2.5} />
                </Link>
                <a
                  href="#research-preview"
                  onClick={(e) => {
                    e.preventDefault();
                    document.getElementById("research-preview")?.scrollIntoView({ behavior: "smooth", block: "start" });
                  }}
                  className="inline-flex items-center gap-2 font-semibold transition-colors"
                  style={{ color: "#0F2847", fontSize: "0.93rem", border: "1px solid #e2e8f0", padding: "12px 24px", borderRadius: 10, cursor: "pointer" }}
                >
                  See how it works
                </a>
              </div>

              <div className="flex flex-wrap items-center gap-6 sq-fade-up sq-delay-4" style={{ marginTop: 32 }}>
                {["ORCID Integrated", "GDPR Aligned", "Free plan forever"].map((label) => (
                  <div key={label} className="flex items-center gap-1.5">
                    <CheckCircle2 size={13} strokeWidth={2} style={{ color: "#10b981" }} />
                    <span style={{ fontSize: "0.78rem", color: "#64748b", fontWeight: 500 }}>{label}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Right: illustration */}
            <div className="sq-fade-up sq-delay-2 hidden lg:block">
              <HeroIllustration />
            </div>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════════════
          SIGNATURE MOMENT — "What are you researching?" (§17-19)
      ══════════════════════════════════════════════════════════════════════ */}
      <ResearchPreviewDemo />
      <ResearchThread />
      <ProductProof />

      {/* ══════════════════════════════════════════════════════════════════════
          SECTION 2 — WHAT SYNAPTIQ CONNECTS (replaces a fake "trusted by"
          logo wall — no real customer/partner relationships to show yet;
          an honest capability strip instead of vanity social proof)
      ══════════════════════════════════════════════════════════════════════ */}
      <section style={{ background: "#f8fafc", borderBottom: "1px solid #f1f5f9" }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-14">
          <div ref={refTrusted} className="sq-reveal">
            <div className="flex flex-wrap items-center justify-center gap-x-10 gap-y-6">
              {["Identity", "Expertise", "Discovery", "Collaboration", "Research Execution", "Publishing"].map((label) => (
                <div key={label} style={{
                  fontSize: "0.82rem", fontWeight: 700, color: "#64748b",
                  letterSpacing: "0.04em", padding: "6px 16px",
                  border: "1px solid #e2e8f0", borderRadius: 8, background: "#fff",
                }}>
                  {label}
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════════════
          SECTION 3 — PLATFORM OVERVIEW
      ══════════════════════════════════════════════════════════════════════ */}
      <section className="bg-white" style={{ borderBottom: "1px solid #f1f5f9" }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-24 lg:py-32">
          <div ref={refPlatform} className="sq-reveal">
            <div style={{ textAlign: "center", marginBottom: 64 }}>
              <div className="overline mb-3">Platform</div>
              <h2 style={{ fontSize: "clamp(1.8rem, 3.5vw, 3rem)", fontWeight: 900, letterSpacing: "-0.035em", color: "#0a0f1a", lineHeight: 1.1, textWrap: "balance" }}>
                Everything you need to conduct research.
              </h2>
              <p style={{ fontSize: "1rem", color: "#64748b", lineHeight: 1.7, maxWidth: 520, margin: "16px auto 0" }}>
                One platform for the entire academic lifecycle — discovery, collaboration, writing, and impact.
              </p>
            </div>

            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
              {PLATFORM_CARDS.map(({ icon: Icon, title, body }) => (
                <div key={title}
                  className="group"
                  style={{
                    background: "#fff", border: "1px solid #e8edf3", borderRadius: 14,
                    padding: 24, transition: "box-shadow 200ms ease, transform 200ms ease",
                    cursor: "default",
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.boxShadow = "0 8px 32px rgba(15,40,71,0.1)"; e.currentTarget.style.transform = "translateY(-2px)"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.boxShadow = "none"; e.currentTarget.style.transform = "none"; }}
                >
                  <div style={{
                    width: 42, height: 42, borderRadius: 10,
                    background: "rgba(15,40,71,0.05)", border: "1px solid rgba(15,40,71,0.08)",
                    display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 16,
                  }}>
                    <Icon size={18} strokeWidth={1.5} style={{ color: "#0F2847" }} />
                  </div>
                  <div style={{ fontSize: "0.9rem", fontWeight: 700, color: "#0a0f1a", marginBottom: 8 }}>{title}</div>
                  <div style={{ fontSize: "0.78rem", color: "#64748b", lineHeight: 1.65 }}>{body}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════════════
          SECTION 4 — GLOBAL COLLABORATION
      ══════════════════════════════════════════════════════════════════════ */}
      <section style={{ background: "#f8fafc", borderBottom: "1px solid #f1f5f9" }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-24 lg:py-32">
          <div ref={refCollab} className="sq-reveal grid lg:grid-cols-2 gap-16 items-center">

            {/* Left: world map */}
            <WorldMap />

            {/* Right: text */}
            <div>
              <div className="overline mb-4">Global Network</div>
              <h2 style={{ fontSize: "clamp(1.8rem, 3.2vw, 2.8rem)", fontWeight: 900, letterSpacing: "-0.035em", color: "#0a0f1a", lineHeight: 1.1, textWrap: "balance", marginBottom: 20 }}>
                Find collaborators.<br />Build global research teams.
              </h2>
              <p style={{ fontSize: "0.95rem", color: "#64748b", lineHeight: 1.75, marginBottom: 32, maxWidth: 460 }}>
                Post a collaboration call, get AI-assisted matches with a clear explanation of why each one is relevant, and create a shared workspace in minutes. You decide who to contact — Synaptiq never sends outreach on your behalf.
              </p>

              <div className="flex flex-col gap-4">
                {COLLAB_STEPS.map((step, i) => (
                  <div key={i} className="flex gap-4 items-start">
                    <div style={{
                      width: 26, height: 26, borderRadius: "50%", background: "#0F2847",
                      color: "#fff", fontSize: "0.65rem", fontWeight: 800,
                      display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
                    }}>
                      {i + 1}
                    </div>
                    <div style={{ fontSize: "0.85rem", color: "#334155", lineHeight: 1.6, paddingTop: 3 }}>{step}</div>
                  </div>
                ))}
              </div>

              <div style={{ marginTop: 32 }}>
                <Link to="/register"
                  className="inline-flex items-center gap-2 font-semibold text-[#0F2847] hover:opacity-75 transition-opacity"
                  style={{ fontSize: "0.9rem", borderBottom: "1px solid #0F2847", paddingBottom: 2 }}
                >
                  Join the network <ArrowRight size={13} strokeWidth={2} />
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════════════
          SECTION 7 — FEATURE SHOWCASE (alternating)
      ══════════════════════════════════════════════════════════════════════ */}
      <section style={{ background: "#f8fafc" }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-24 lg:py-32">
          <div ref={refShowcase} className="sq-reveal">
            <div style={{ textAlign: "center", marginBottom: 72 }}>
              <div className="overline mb-3">Features</div>
              <h2 style={{ fontSize: "clamp(1.8rem, 3.2vw, 2.8rem)", fontWeight: 900, letterSpacing: "-0.035em", color: "#0a0f1a", lineHeight: 1.1, textWrap: "balance" }}>
                Built for how researchers actually work.
              </h2>
            </div>

            <div className="flex flex-col gap-20">
              {SHOWCASE.map(({ eyebrow, title, body, features, bg }, i) => (
                <div key={eyebrow} className={`grid lg:grid-cols-2 gap-16 items-center ${i % 2 === 1 ? "lg:[&>*:first-child]:order-2" : ""}`}>
                  {/* Visual */}
                  <div style={{ background: bg, borderRadius: 20, padding: 40, border: "1px solid rgba(0,0,0,0.04)", minHeight: 280, display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <div style={{ width: "100%", maxWidth: 400 }}>
                      {/* Feature preview card */}
                      <div style={{ background: "#fff", borderRadius: 12, border: "1px solid #e2e8f0", boxShadow: "0 8px 32px rgba(0,0,0,0.08)", overflow: "hidden" }}>
                        <div style={{ padding: "14px 20px", borderBottom: "1px solid #f1f5f9", display: "flex", alignItems: "center", gap: 8 }}>
                          <div style={{ width: 8, height: 8, borderRadius: "50%", background: "#0F2847" }} />
                          <span style={{ fontSize: "0.7rem", fontWeight: 700, color: "#0F2847" }}>{eyebrow}</span>
                        </div>
                        <div style={{ padding: "20px", display: "flex", flexDirection: "column", gap: 10 }}>
                          {features.map((f) => (
                            <div key={f} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                              <CheckCircle2 size={14} strokeWidth={2} style={{ color: "#10b981", flexShrink: 0 }} />
                              <span style={{ fontSize: "0.8rem", color: "#334155", fontWeight: 500 }}>{f}</span>
                            </div>
                          ))}
                        </div>
                        <div style={{ background: "#f8fafc", padding: "12px 20px", borderTop: "1px solid #f1f5f9" }}>
                          <div style={{ height: 4, background: "#e2e8f0", borderRadius: 2, overflow: "hidden" }}>
                            <div style={{ width: "75%", height: "100%", background: "#0F2847", borderRadius: 2 }} />
                          </div>
                          <div style={{ fontSize: "0.6rem", color: "#94a3b8", marginTop: 6 }}>Platform coverage</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Text */}
                  <div>
                    <div className="overline mb-4">{eyebrow}</div>
                    <h3 style={{ fontSize: "clamp(1.5rem, 2.5vw, 2.2rem)", fontWeight: 900, letterSpacing: "-0.03em", color: "#0a0f1a", lineHeight: 1.15, textWrap: "balance", marginBottom: 16 }}>
                      {title}
                    </h3>
                    <p style={{ fontSize: "0.93rem", color: "#64748b", lineHeight: 1.75, marginBottom: 28 }}>{body}</p>
                    <Link to="/register"
                      className="inline-flex items-center gap-2 font-semibold hover:opacity-75 transition-opacity"
                      style={{ color: "#0F2847", fontSize: "0.88rem" }}
                    >
                      Explore {eyebrow} <ChevronRight size={14} strokeWidth={2} />
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════════════
          AI ASSISTANCE — repositioned later and reframed as contextual
          assistance rather than an early defining pillar (§16: the public
          hierarchy should primarily communicate research/expertise/people/
          collaboration/work, with AI appearing as assistance within that,
          not the other way around). Genuine capability, not hidden — just
          not the second thing a visitor sees.
      ══════════════════════════════════════════════════════════════════════ */}
      <section style={{ background: "#0F2847" }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-24 lg:py-32">
          <div ref={refAI} className="sq-reveal grid lg:grid-cols-2 gap-16 items-start">

            {/* Left: mockup */}
            <AIWorkspaceMockup />

            {/* Right: text */}
            <div>
              <div style={{ fontSize: "0.72rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "rgba(255,255,255,0.4)", marginBottom: 16 }}>AI Assistance</div>
              <h2 style={{ fontSize: "clamp(1.8rem, 3.2vw, 2.9rem)", fontWeight: 900, letterSpacing: "-0.035em", color: "#fff", lineHeight: 1.1, textWrap: "balance", marginBottom: 20 }}>
                AI that assists the research, not the other way around.
              </h2>
              <p style={{ fontSize: "0.95rem", color: "rgba(255,255,255,0.6)", lineHeight: 1.75, marginBottom: 36, maxWidth: 460 }}>
                Synaptiq's AI understands methodology, statistical design, and academic publishing standards — assistance within your workflow, not the product itself.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {AI_FEATURES.map(({ icon: Icon, label, body }) => (
                  <div key={label} style={{ display: "flex", gap: 12, alignItems: "flex-start", minWidth: 0 }}>
                    <div style={{ width: 28, height: 28, borderRadius: 7, background: "rgba(255,255,255,0.08)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                      <Icon size={13} strokeWidth={1.5} style={{ color: "rgba(255,255,255,0.7)" }} />
                    </div>
                    <div style={{ minWidth: 0 }}>
                      <div style={{ fontSize: "0.8rem", fontWeight: 700, color: "#fff", marginBottom: 2 }}>{label}</div>
                      <div style={{ fontSize: "0.72rem", color: "rgba(255,255,255,0.45)", lineHeight: 1.55 }}>{body}</div>
                    </div>
                  </div>
                ))}
              </div>

              <div style={{ marginTop: 36 }}>
                <Link to="/register"
                  className="inline-flex items-center gap-2.5 font-semibold transition-all active:scale-[.98]"
                  style={{ background: "#fff", color: "#0F2847", padding: "12px 24px", borderRadius: 10, fontSize: "0.9rem" }}
                >
                  Try the AI tools <ArrowRight size={14} strokeWidth={2.5} />
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════════════
          SECTION 8 — WHY SYNAPTIQ  (dark) — replaces a fabricated "by the
          numbers" vanity-metrics section (Synaptiq is early-stage; per the
          Phase 9A audit, none of those figures were real). Structural
          differentiators instead of scale, per §11/§25.
      ══════════════════════════════════════════════════════════════════════ */}
      <section style={{ background: "#0a1220" }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-24 lg:py-32">
          <div ref={refStats} className="sq-reveal">
            <div style={{ textAlign: "center", marginBottom: 64 }}>
              <div style={{ fontSize: "0.72rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "rgba(255,255,255,0.35)", marginBottom: 16 }}>Why Synaptiq</div>
              <h2 style={{ fontSize: "clamp(1.8rem, 3.2vw, 2.8rem)", fontWeight: 900, letterSpacing: "-0.035em", color: "#fff", lineHeight: 1.1, textWrap: "balance" }}>
                Structural differences, not just more features.
              </h2>
            </div>

            {/* Trimmed from 4 to 3 pillars (§19) — "From question to
                collaboration" and "Work after discovery" are now shown,
                not just claimed, by the Research Thread and Product Proof
                sections above; keeping them here too was pure repetition.
                These three are the ground neither section covers. */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-10 lg:gap-8">
              {[
                { title: "Explainable discovery", desc: "See why a profile is relevant instead of receiving an unexplained recommendation." },
                { title: "Interdisciplinary by design", desc: "A research problem can surface complementary disciplines, not only similar profiles." },
                { title: "Human-approved contact", desc: "Synaptiq identifies the expertise. You decide who to contact — nothing is sent on your behalf." },
              ].map(({ title, desc }) => (
                <div key={title}>
                  <div style={{ fontSize: "0.92rem", fontWeight: 800, color: "#fff", marginBottom: 8, letterSpacing: "-0.01em" }}>{title}</div>
                  <div style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.45)", lineHeight: 1.65 }}>{desc}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════════════
          SECTION 10 — PRICING PREVIEW
      ══════════════════════════════════════════════════════════════════════ */}
      <section className="bg-white" style={{ borderBottom: "1px solid #f1f5f9" }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-24 lg:py-32">
          <div ref={refPricing} className="sq-reveal">
            <div style={{ textAlign: "center", marginBottom: 56 }}>
              <div className="overline mb-3">Pricing</div>
              <h2 style={{ fontSize: "clamp(1.8rem, 3.2vw, 2.8rem)", fontWeight: 900, letterSpacing: "-0.035em", color: "#0a0f1a", lineHeight: 1.1, textWrap: "balance" }}>
                Start free. Scale when you&rsquo;re ready.
              </h2>
              <p style={{ fontSize: "0.95rem", color: "#64748b", lineHeight: 1.7, maxWidth: 480, margin: "14px auto 0" }}>
                Free plan is permanent — no trial, no credit card required.
              </p>
            </div>

            <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-5 items-stretch">
              {PRICING_TIERS.map(({ name, price, period, desc, features, cta, featured, href, badge }) => (
                <div key={name} style={{
                  borderRadius: 16, padding: "28px 24px",
                  border: featured ? "2px solid #0F2847" : "1px solid #e8edf3",
                  background: featured ? "#0F2847" : "#fff",
                  boxShadow: featured ? "0 20px 60px rgba(15,40,71,0.2)" : "0 2px 12px rgba(15,40,71,0.03)",
                  display: "flex", flexDirection: "column",
                  transform: featured ? "scale(1.02)" : "none",
                }}>
                  <div style={{ fontSize: "0.78rem", fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase", color: featured ? "rgba(255,255,255,0.6)" : "#94a3b8", marginBottom: 8 }}>{name}</div>
                  {badge && <div style={{ fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.04em", color: featured ? "#fff" : "#0F2847", marginBottom: 8 }}>{badge}</div>}
                  <div style={{ display: "flex", alignItems: "baseline", gap: 3, marginBottom: 8 }}>
                    <span style={{ fontSize: "2.4rem", fontWeight: 900, color: featured ? "#fff" : "#0a0f1a", lineHeight: 1, letterSpacing: "-0.04em" }}>{price}</span>
                    <span style={{ fontSize: "0.78rem", color: featured ? "rgba(255,255,255,0.4)" : "#94a3b8" }}>{period}</span>
                  </div>
                  <div style={{ fontSize: "0.8rem", color: featured ? "rgba(255,255,255,0.55)" : "#64748b", lineHeight: 1.55, marginBottom: 24 }}>{desc}</div>
                  <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 10, marginBottom: 24 }}>
                    {features.map((f) => (
                      <div key={f} style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
                        <CheckCircle2 size={13} strokeWidth={2} style={{ color: featured ? "rgba(255,255,255,0.5)" : "#10b981", flexShrink: 0, marginTop: 2 }} />
                        <span style={{ fontSize: "0.78rem", color: featured ? "rgba(255,255,255,0.7)" : "#475569", lineHeight: 1.5 }}>{f}</span>
                      </div>
                    ))}
                  </div>
                  <Link
                    to={href}
                    className="block text-center font-semibold transition-all active:scale-[.98]"
                    style={{
                      background: featured ? "#fff" : "#f1f5f9",
                      color: "#0F2847", padding: "11px 20px", borderRadius: 8, fontSize: "0.85rem",
                    }}
                  >
                    {cta}
                  </Link>
                </div>
              ))}
            </div>

            <div style={{ textAlign: "center", marginTop: 24 }}>
              <Link to="/pricing" className="inline-flex items-center gap-1.5 text-slate-500 hover:text-slate-800 transition-colors" style={{ fontSize: "0.85rem" }}>
                See full pricing details <ChevronRight size={13} strokeWidth={2} />
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════════════
          SECTION 11 — FAQ
      ══════════════════════════════════════════════════════════════════════ */}
      <section id="faq" data-testid="landing-faq" style={{ background: "#f8fafc", borderBottom: "1px solid #f1f5f9" }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-24 lg:py-32">
          <div ref={refFaq} className="sq-reveal grid lg:grid-cols-3 gap-16">
            <div>
              <div className="overline mb-4">FAQ</div>
              <h2 style={{ fontSize: "clamp(1.8rem, 2.8vw, 2.6rem)", fontWeight: 900, letterSpacing: "-0.035em", color: "#0a0f1a", lineHeight: 1.1, textWrap: "balance" }}>
                Answered, honestly.
              </h2>
              <p style={{ fontSize: "0.88rem", color: "#64748b", lineHeight: 1.75, marginTop: 16 }}>
                Still have questions?{" "}
                <Link to="/contact" style={{ color: "#0F2847", fontWeight: 600 }}>Talk to us.</Link>
              </p>
            </div>
            <div className="lg:col-span-2 flex flex-col gap-3">
              {FAQ.map((item, i) => (
                <div key={i}
                  data-testid={`faq-item-${i}`}
                  style={{ border: `1px solid ${openFaq === i ? "#0F2847" : "#e8edf3"}`, borderRadius: 12, overflow: "hidden", transition: "border-color 150ms" }}
                >
                  <button
                    onClick={() => setOpenFaq(openFaq === i ? null : i)}
                    className="w-full flex items-center justify-between gap-4 text-left"
                    style={{ padding: "18px 22px" }}
                    aria-expanded={openFaq === i}
                  >
                    <span style={{ fontSize: "0.9rem", fontWeight: 600, color: "#0a0f1a" }}>{item.q}</span>
                    <ChevronDown size={15} strokeWidth={2} style={{ color: "#0F2847", flexShrink: 0, transform: openFaq === i ? "rotate(180deg)" : "rotate(0)", transition: "transform 200ms ease" }} />
                  </button>
                  {openFaq === i && (
                    <div style={{ padding: "0 22px 18px", fontSize: "0.85rem", color: "#475569", lineHeight: 1.75 }}>{item.a}</div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════════════
          SECTION 12 — FINAL CTA  (dark)
      ══════════════════════════════════════════════════════════════════════ */}
      <section style={{ background: "#0F2847" }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-32 lg:py-40">
          <div ref={refCta} className="sq-reveal" style={{ textAlign: "center", maxWidth: 640, margin: "0 auto" }}>
            <div style={{ fontSize: "0.72rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "rgba(255,255,255,0.35)", marginBottom: 24 }}>
              Get started today
            </div>
            <h2 style={{ fontSize: "clamp(2.2rem, 5vw, 4rem)", fontWeight: 900, letterSpacing: "-0.04em", color: "#fff", lineHeight: 1.05, textWrap: "balance" }}>
              Ready to build your next research collaboration?
            </h2>
            <p style={{ fontSize: "1rem", color: "rgba(255,255,255,0.55)", lineHeight: 1.75, marginTop: 20, maxWidth: 480, marginLeft: "auto", marginRight: "auto" }}>
              Discover collaborators, run your research, and track your impact — all in one place. Free to start.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4" style={{ marginTop: 40 }}>
              <Link
                to="/register"
                className="inline-flex items-center gap-2.5 font-semibold transition-all active:scale-[.98]"
                style={{ background: "#fff", color: "#0F2847", padding: "15px 32px", borderRadius: 10, fontSize: "0.95rem", boxShadow: "0 4px 24px rgba(0,0,0,0.2)" }}
              >
                Start Free <ArrowRight size={15} strokeWidth={2.5} />
              </Link>
              <Link
                to="/contact"
                className="inline-flex items-center gap-2 font-semibold transition-colors"
                style={{ color: "rgba(255,255,255,0.65)", fontSize: "0.93rem", border: "1px solid rgba(255,255,255,0.2)", padding: "14px 28px", borderRadius: 10 }}
              >
                Request Demo
              </Link>
            </div>
            <p style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.3)", marginTop: 20 }}>
              Free plan available · No credit card required · GDPR aligned
            </p>
          </div>
        </div>
      </section>

    </MarketingLayout>
  );
}
