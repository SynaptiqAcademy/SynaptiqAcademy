/* eslint-disable */
import React, { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import MarketingLayout from "../components/layout/MarketingLayout";
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

  const nodes = [
    { id: "a", x: 52, y: 28, label: "Dr. K. Sato",  sub: "Kyoto Univ.", color: "#0F2847", initials: "KS" },
    { id: "b", x: 82, y: 52, label: "Prof. M. Osei",sub: "ETH Zürich",  color: "#1d4ed8", initials: "MO" },
    { id: "c", x: 60, y: 78, label: "Dr. R. Silva",  sub: "USP Brazil",  color: "#0F2847", initials: "RS" },
    { id: "d", x: 22, y: 72, label: "Dr. I. Patel",  sub: "Oxford",      color: "#1d4ed8", initials: "IP" },
    { id: "e", x: 14, y: 40, label: "J. Williams",   sub: "MIT",         color: "#0F2847", initials: "JW" },
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

        {/* Bottom status bar */}
        <div style={{ padding: "12px 20px", borderTop: "1px solid #f1f5f9", display: "flex", alignItems: "center", gap: 16 }}>
          {[
            { label: "Researchers", value: "142K+", color: "#0F2847" },
            { label: "Countries", value: "150+", color: "#1d4ed8" },
            { label: "Collaborations", value: "250K+", color: "#059669" },
          ].map(({ label, value, color }) => (
            <div key={label} style={{ flex: 1, textAlign: "center" }}>
              <div style={{ fontSize: "1rem", fontWeight: 800, color, lineHeight: 1 }}>{value}</div>
              <div style={{ fontSize: "0.62rem", color: "#94a3b8", marginTop: 2 }}>{label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Floating notification card */}
      <div style={{
        position: "absolute", top: 8, right: "0%",
        background: "#fff", borderRadius: 10, border: "1px solid #e2e8f0",
        boxShadow: "0 4px 20px rgba(15,40,71,0.1)", padding: "10px 14px",
        maxWidth: 200, zIndex: 10,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <div style={{ width: 6, height: 6, borderRadius: "50%", background: "#10b981", flexShrink: 0 }} />
          <span style={{ fontSize: "0.65rem", fontWeight: 700, color: "#0f172a" }}>New match found</span>
        </div>
        <div style={{ fontSize: "0.6rem", color: "#64748b", marginTop: 4, lineHeight: 1.5 }}>Prof. S. Nakamura · Osaka Univ.<br />Quantum Computing · 3 papers in common</div>
      </div>

      {/* Floating quality card */}
      <div style={{
        position: "absolute", bottom: 16, left: "2%",
        background: "#0F2847", borderRadius: 10,
        boxShadow: "0 4px 20px rgba(15,40,71,0.25)", padding: "12px 16px",
        maxWidth: 180, zIndex: 10,
      }}>
        <div style={{ fontSize: "0.6rem", color: "rgba(255,255,255,0.55)", fontWeight: 600, letterSpacing: "0.08em", textTransform: "uppercase" }}>AI Manuscript Review</div>
        <div style={{ fontSize: "1.4rem", fontWeight: 800, color: "#fff", lineHeight: 1, marginTop: 4 }}>89<span style={{ fontSize: "0.8rem" }}>%</span></div>
        <div style={{ height: 3, background: "rgba(255,255,255,0.15)", borderRadius: 2, marginTop: 8 }}>
          <div style={{ width: "89%", height: "100%", background: "#10b981", borderRadius: 2 }} />
        </div>
        <div style={{ fontSize: "0.58rem", color: "rgba(255,255,255,0.45)", marginTop: 4 }}>Ready for submission</div>
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
      borderRadius: 16, overflow: "hidden",
    }}>
      {/* Toolbar */}
      <div style={{ background: "rgba(255,255,255,0.04)", padding: "10px 20px", borderBottom: "1px solid rgba(255,255,255,0.06)", display: "flex", alignItems: "center", gap: 8 }}>
        <div style={{ width: 8, height: 8, borderRadius: "50%", background: "rgba(255,255,255,0.2)" }} />
        <div style={{ flex: 1, background: "rgba(255,255,255,0.06)", borderRadius: 4, height: 6 }} />
        <div style={{ fontSize: "0.6rem", color: "rgba(255,255,255,0.4)", fontWeight: 600, letterSpacing: "0.06em" }}>AI COPILOT</div>
      </div>
      {/* Tool tabs */}
      <div style={{ display: "flex", borderBottom: "1px solid rgba(255,255,255,0.06)", padding: "0 20px" }}>
        {["Literature Review", "Gap Detection", "Manuscript", "Statistics"].map((t, i) => (
          <div key={t} style={{
            padding: "10px 12px", fontSize: "0.62rem", fontWeight: i === 0 ? 700 : 400,
            color: i === 0 ? "#fff" : "rgba(255,255,255,0.4)",
            borderBottom: i === 0 ? "2px solid #fff" : "2px solid transparent",
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
    eyebrow: "Verification & Trust",
    title: "Your Academic Passport.",
    body: "Build a verified academic identity with ORCID integration, institutional verification, publication credentials, and a trust score that travels with you.",
    features: ["ORCID integration", "Institutional verify", "Publication credentials", "Trust score"],
    bg: "#f5f0ff",
  },
];

const TESTIMONIALS = [
  {
    quote: "Synaptiq didn't just help me find collaborators — it rebuilt how I run research. The workspace keeps the entire team aligned without the email overhead.",
    author: "Dr. Mara Osei", role: "Postdoctoral Researcher", institution: "ETH Zürich",
    initials: "MO", color: "#0F2847",
  },
  {
    quote: "I submitted my manuscript three weeks after finding a co-author through Synaptiq. The AI review caught methodological gaps I'd missed after three rounds of revision.",
    author: "Kenji Watanabe", role: "PhD Candidate", institution: "Kyoto University",
    initials: "KW", color: "#1d4ed8",
  },
  {
    quote: "Running an institution plan for our department. The analytics alone justified the cost — we now track our collective research output in one dashboard.",
    author: "Prof. Ingrid Sörensen", role: "Head of Research Office", institution: "Uppsala University",
    initials: "IS", color: "#059669",
  },
];

const PRICING_TIERS = [
  {
    name: "Free",         price: "€0",     period: "/mo",
    desc: "Start exploring — no credit card required.",
    features: ["50 AI credits / month", "Researcher profile", "Discovery network", "1 active project", "Community access"],
    cta: "Start free", featured: false, href: "/register",
  },
  {
    name: "Researcher",   price: "€9.99",  period: "/mo",
    desc: "The complete research and publishing toolkit.",
    features: ["300 AI credits / month", "Unlimited projects", "AI Research Assistant", "AI Manuscript Copilot", "Publication tracking", "Priority support"],
    cta: "Get started", featured: true, href: "/register",
  },
  {
    name: "Pro Researcher", price: "€29.99", period: "/mo",
    desc: "For high-output researchers and senior academics.",
    features: ["1,000 AI credits / month", "Unlimited workspaces", "Collaboration Intelligence", "Research Analytics Suite", "Citation monitoring", "Impact dashboard"],
    cta: "Get started", featured: false, href: "/register",
  },
  {
    name: "Institution",  price: "€299",   period: "/mo",
    desc: "For research offices and university departments.",
    features: ["20,000 AI credits / month", "25 researcher seats", "Institutional analytics", "Department management", "SSO / SAML integration", "Dedicated support"],
    cta: "Contact sales", featured: false, href: "/contact",
  },
];

const FAQ = [
  { q: "What is Synaptiq?", a: "Synaptiq is the world's academic collaboration platform. It unifies researcher networking, project management, manuscript workflows, AI assistance, and publication tools into one workspace — built for the full academic lifecycle." },
  { q: "Who is Synaptiq for?", a: "Synaptiq supports undergraduate students, PhD candidates, postdoctoral researchers, professors, educators, research offices, and industry professionals. The platform adapts to your role." },
  { q: "How does collaboration work?", a: "Post an open collaboration with your requirements. Other researchers apply with a pitch. You accept, and a shared workspace is automatically created with literature, tasks, milestones, and manuscript." },
  { q: "Is ORCID supported?", a: "Yes. Link your ORCID iD and your public publications sync automatically via the ORCID API." },
  { q: "How is research data protected?", a: "All data is encrypted in transit (TLS 1.2+) and at rest. Authentication uses httpOnly cookies and bcrypt. We are GDPR-aligned and never sell user data." },
  { q: "Can universities use Synaptiq?", a: "Yes. The Institution plan includes 25 seats, institutional analytics, department management, and dedicated support." },
];

const TRUSTED_LOGOS = [
  "MIT", "Oxford", "ETH Zürich", "Kyoto Univ.", "Uppsala", "TU Berlin",
  "Nature Publishing", "IEEE", "Springer", "Elsevier",
];

/* ─── Landing Page ───────────────────────────────────────────────────────── */

export default function Landing() {
  useEffect(() => {
    document.title = "Synaptiq — Research Platform for Academics";
    return () => { document.title = "Synaptiq"; };
  }, []);
  const refTrusted   = useReveal();
  const refPlatform  = useReveal();
  const refCollab    = useReveal();
  const refAI        = useReveal();
  const refWorkflow  = useReveal();
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
                Build Research Teams<br />
                <span style={{ color: "#0F2847" }}>Without Borders.</span>
              </h1>

              <p className="sq-fade-up sq-delay-2" style={{
                fontSize: "clamp(1rem, 1.6vw, 1.15rem)",
                color: "#475569", lineHeight: 1.75,
                maxWidth: 520, marginTop: 24,
              }}>
                Synaptiq connects researchers, PhD candidates, professors and universities worldwide into collaborative research workspaces powered by AI.
              </p>

              <div className="flex items-center gap-4 flex-wrap sq-fade-up sq-delay-3" style={{ marginTop: 36 }}>
                <Link
                  to="/register"
                  data-testid={TID.landingGetStarted}
                  className="inline-flex items-center gap-2.5 font-semibold transition-all duration-150 active:scale-[.98]"
                  style={{ background: "#0F2847", color: "#fff", padding: "13px 28px", borderRadius: 10, fontSize: "0.93rem" }}
                >
                  Start Free <ArrowRight size={15} strokeWidth={2.5} />
                </Link>
                <Link
                  to="/contact"
                  className="inline-flex items-center gap-2 font-semibold transition-colors"
                  style={{ color: "#0F2847", fontSize: "0.93rem", border: "1px solid #e2e8f0", padding: "12px 24px", borderRadius: 10 }}
                >
                  Book a Demo
                </Link>
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
          SECTION 2 — TRUSTED BY
      ══════════════════════════════════════════════════════════════════════ */}
      <section style={{ background: "#f8fafc", borderBottom: "1px solid #f1f5f9" }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-14">
          <div ref={refTrusted} className="sq-reveal">
            <div style={{ textAlign: "center", fontSize: "0.75rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 24 }}>
              Trusted by researchers worldwide
            </div>
            <div className="flex flex-wrap items-center justify-center gap-x-10 gap-y-6">
              {TRUSTED_LOGOS.map((logo) => (
                <div key={logo} style={{
                  fontSize: "0.82rem", fontWeight: 700, color: "#94a3b8",
                  letterSpacing: "0.04em", padding: "6px 16px",
                  border: "1px solid #e2e8f0", borderRadius: 8, background: "#fff",
                }}>
                  {logo}
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
                Post a collaboration call, get matched by AI, and create a shared workspace in minutes. Synaptiq's network spans 150+ countries and every academic discipline.
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
          SECTION 5 — AI RESEARCH WORKSPACE  (dark)
      ══════════════════════════════════════════════════════════════════════ */}
      <section style={{ background: "#0F2847" }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-24 lg:py-32">
          <div ref={refAI} className="sq-reveal grid lg:grid-cols-2 gap-16 items-start">

            {/* Left: mockup */}
            <AIWorkspaceMockup />

            {/* Right: text */}
            <div>
              <div style={{ fontSize: "0.72rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "rgba(255,255,255,0.4)", marginBottom: 16 }}>AI Research Suite</div>
              <h2 style={{ fontSize: "clamp(1.8rem, 3.2vw, 2.9rem)", fontWeight: 900, letterSpacing: "-0.035em", color: "#fff", lineHeight: 1.1, textWrap: "balance", marginBottom: 20 }}>
                AI built for academic rigor.
              </h2>
              <p style={{ fontSize: "0.95rem", color: "rgba(255,255,255,0.6)", lineHeight: 1.75, marginBottom: 36, maxWidth: 460 }}>
                Synaptiq's AI understands methodology, statistical design, and academic publishing standards — not just autocomplete.
              </p>

              <div className="grid grid-cols-2 gap-4">
                {AI_FEATURES.map(({ icon: Icon, label, body }) => (
                  <div key={label} style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
                    <div style={{ width: 28, height: 28, borderRadius: 7, background: "rgba(255,255,255,0.08)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                      <Icon size={13} strokeWidth={1.5} style={{ color: "rgba(255,255,255,0.7)" }} />
                    </div>
                    <div>
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
          SECTION 6 — RESEARCH WORKFLOW
      ══════════════════════════════════════════════════════════════════════ */}
      <section className="bg-white" style={{ borderBottom: "1px solid #f1f5f9" }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-24 lg:py-32">
          <div ref={refWorkflow} className="sq-reveal">
            <div style={{ textAlign: "center", marginBottom: 64 }}>
              <div className="overline mb-3">Research workflow</div>
              <h2 style={{ fontSize: "clamp(1.8rem, 3.2vw, 2.8rem)", fontWeight: 900, letterSpacing: "-0.035em", color: "#0a0f1a", lineHeight: 1.1, textWrap: "balance" }}>
                From first question to final publication.
              </h2>
            </div>

            {/* 8-step timeline */}
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-1">
              {WORKFLOW.map(({ step, title, icon: Icon, body }, i) => (
                <div key={step} style={{ position: "relative", textAlign: "center", padding: "0 8px" }}>
                  {/* Connector */}
                  {i < WORKFLOW.length - 1 && (
                    <div className="hidden lg:block" style={{
                      position: "absolute", top: 20, left: "calc(50% + 20px)", right: 0, height: 1,
                      background: "linear-gradient(to right, #cbd5e1, #e2e8f0)",
                    }} />
                  )}
                  {/* Icon circle */}
                  <div style={{
                    width: 40, height: 40, borderRadius: "50%",
                    background: i === 0 ? "#0F2847" : "#f1f5f9",
                    border: i === 0 ? "none" : "1px solid #e2e8f0",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    margin: "0 auto 14px",
                  }}>
                    <Icon size={16} strokeWidth={1.5} style={{ color: i === 0 ? "#fff" : "#64748b" }} />
                  </div>
                  <div style={{ fontSize: "0.6rem", fontWeight: 800, color: "#94a3b8", letterSpacing: "0.08em", marginBottom: 4 }}>{step}</div>
                  <div style={{ fontSize: "0.78rem", fontWeight: 700, color: "#0a0f1a", marginBottom: 5, lineHeight: 1.3 }}>{title}</div>
                  <div style={{ fontSize: "0.68rem", color: "#64748b", lineHeight: 1.55 }}>{body}</div>
                </div>
              ))}
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
          SECTION 8 — STATISTICS  (dark)
      ══════════════════════════════════════════════════════════════════════ */}
      <section style={{ background: "#0a1220" }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-24 lg:py-32">
          <div ref={refStats} className="sq-reveal">
            <div style={{ textAlign: "center", marginBottom: 64 }}>
              <div style={{ fontSize: "0.72rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "rgba(255,255,255,0.35)", marginBottom: 16 }}>By the numbers</div>
              <h2 style={{ fontSize: "clamp(1.8rem, 3.2vw, 2.8rem)", fontWeight: 900, letterSpacing: "-0.035em", color: "#fff", lineHeight: 1.1, textWrap: "balance" }}>
                Researchers worldwide trust Synaptiq.
              </h2>
            </div>

            <div className="grid grid-cols-2 lg:grid-cols-5 gap-10 lg:gap-8">
              <StatCounter target={150} suffix="+"  label="Countries"         sub="Global research coverage" />
              <StatCounter target={50}  suffix="K+" label="Researchers"       sub="Active platform users" />
              <StatCounter target={8}   suffix="K+" label="Institutions"      sub="Universities & research centers" />
              <StatCounter target={250} suffix="K+" label="Collaborations"    sub="Teams formed on the platform" />
              <StatCounter target={2}   suffix="M+" label="AI Interactions"   sub="Research queries processed" />
            </div>
          </div>
        </div>
      </section>

      {/* ══════════════════════════════════════════════════════════════════════
          SECTION 9 — TESTIMONIALS
      ══════════════════════════════════════════════════════════════════════ */}
      <section style={{ background: "#f8fafc", borderBottom: "1px solid #f1f5f9" }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-24 lg:py-32">
          <div ref={refTestimonials} className="sq-reveal">
            <div style={{ textAlign: "center", marginBottom: 56 }}>
              <div className="overline mb-3">Testimonials</div>
              <h2 style={{ fontSize: "clamp(1.8rem, 3.2vw, 2.8rem)", fontWeight: 900, letterSpacing: "-0.035em", color: "#0a0f1a", lineHeight: 1.1, textWrap: "balance" }}>
                What researchers say.
              </h2>
            </div>

            <div className="grid md:grid-cols-3 gap-6">
              {TESTIMONIALS.map(({ quote, author, role, institution, initials, color }) => (
                <div key={author} style={{
                  background: "#fff", border: "1px solid #e8edf3", borderRadius: 16,
                  padding: "32px 28px", boxShadow: "0 2px 12px rgba(15,40,71,0.04)",
                  display: "flex", flexDirection: "column",
                }}>
                  <div className="flex gap-0.5 mb-6">
                    {[1,2,3,4,5].map((s) => <Star key={s} size={12} fill="#0F2847" strokeWidth={0} style={{ color: "#0F2847" }} />)}
                  </div>
                  <p style={{ fontSize: "0.87rem", color: "#334155", lineHeight: 1.8, flex: 1, marginBottom: 24 }}>
                    &ldquo;{quote}&rdquo;
                  </p>
                  <div style={{ display: "flex", alignItems: "center", gap: 12, paddingTop: 20, borderTop: "1px solid #f1f5f9" }}>
                    <div style={{
                      width: 38, height: 38, borderRadius: "50%", background: color,
                      color: "#fff", fontSize: "0.68rem", fontWeight: 800,
                      display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
                    }}>{initials}</div>
                    <div>
                      <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "#0a0f1a" }}>{author}</div>
                      <div style={{ fontSize: "0.72rem", color: "#64748b", marginTop: 1 }}>{role} · {institution}</div>
                    </div>
                  </div>
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
              {PRICING_TIERS.map(({ name, price, period, desc, features, cta, featured, href }) => (
                <div key={name} style={{
                  borderRadius: 16, padding: "28px 24px",
                  border: featured ? "2px solid #0F2847" : "1px solid #e8edf3",
                  background: featured ? "#0F2847" : "#fff",
                  boxShadow: featured ? "0 20px 60px rgba(15,40,71,0.2)" : "0 2px 12px rgba(15,40,71,0.03)",
                  display: "flex", flexDirection: "column",
                  transform: featured ? "scale(1.02)" : "none",
                }}>
                  {featured && (
                    <div style={{ fontSize: "0.6rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "rgba(255,255,255,0.6)", background: "rgba(255,255,255,0.12)", padding: "3px 10px", borderRadius: 999, display: "inline-block", marginBottom: 14, alignSelf: "flex-start" }}>
                      Most popular
                    </div>
                  )}
                  <div style={{ fontSize: "0.78rem", fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase", color: featured ? "rgba(255,255,255,0.6)" : "#94a3b8", marginBottom: 8 }}>{name}</div>
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
              Join 50,000+ researchers already using Synaptiq to discover collaborators, write better manuscripts, and measure their impact.
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
