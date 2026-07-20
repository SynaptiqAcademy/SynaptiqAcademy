/* eslint-disable */
import React, { useState, useRef, useEffect } from "react";
import { Link } from "react-router-dom";
import MarketingLayout from "../components/layout/MarketingLayout";
import {
  ArrowRight, CheckCircle2, Star, Users, BrainCircuit, FileText,
  BookOpen, BarChart3, Globe, Shield, Building2, Database,
  GraduationCap, FlaskConical, Microscope, Briefcase, Network,
  Sparkles, BookMarked, GitMerge, Target, Award, Layers, Lock,
  Eye, Lightbulb, TrendingUp, Zap, Search, UploadCloud, Bell,
  MessageSquare, GitBranch, CheckSquare, ChevronRight,
} from "lucide-react";

/* ─── Shared hooks ─────────────────────────────────────────────────────────── */

function useReveal(threshold = 0.07) {
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current; if (!el) return;
    if (typeof IntersectionObserver === "undefined") { el.classList.add("sq-in"); return; }
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting) { el.classList.add("sq-in"); obs.disconnect(); } }, { threshold });
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
    const el = ref.current; if (!el) return;
    const obs = new IntersectionObserver(([e]) => { if (e.isIntersecting && !started) { setStarted(true); obs.disconnect(); } }, { threshold: 0.5 });
    obs.observe(el); return () => obs.disconnect();
  }, [started]);
  useEffect(() => {
    if (!started) return;
    let start = null;
    const step = (ts) => { if (!start) start = ts; const p = Math.min((ts - start) / duration, 1); const ease = 1 - Math.pow(1 - p, 3); setValue(Math.round(ease * target)); if (p < 1) requestAnimationFrame(step); };
    requestAnimationFrame(step);
  }, [started, target, duration]);
  return { ref, value };
}

/* ─── Design tokens ────────────────────────────────────────────────────────── */
const NAVY  = "#0F2847";
const NAVY2 = "#1e3a5f";
const SLATE = "#475569";
const LIGHT = "#f8fafc";
const BORDER= "#e8edf3";

/* ══════════════════ ILLUSTRATIONS ══════════════════════════════════════════ */

/* Hero — platform command center mockup */
function HeroMockup() {
  const tabs = ["Literature Review", "Gap Detection", "Manuscript", "Statistics", "Network"];
  const [active, setActive] = useState(0);
  return (
    <div aria-hidden="true" style={{ width: "100%", maxWidth: 580, userSelect: "none" }}>
      {/* Outer frame */}
      <div style={{
        background: "#051224", border: "1px solid rgba(255,255,255,0.08)",
        borderRadius: 16, overflow: "hidden",
        boxShadow: "0 40px 120px rgba(0,0,0,0.4), 0 8px 32px rgba(0,0,0,0.25)",
      }}>
        {/* Window chrome */}
        <div style={{ background: "#030d1a", borderBottom: "1px solid rgba(255,255,255,0.06)", padding: "10px 16px", display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ display: "flex", gap: 6 }}>
            {["#ff5f57","#febc2e","#28c840"].map((c) => <div key={c} style={{ width: 10, height: 10, borderRadius: "50%", background: c }} />)}
          </div>
          <div style={{ flex: 1, display: "flex", justifyContent: "center" }}>
            <div style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 5, padding: "3px 40px", fontSize: "0.65rem", color: "rgba(255,255,255,0.25)", fontFamily: "system-ui" }}>
              synaptiq.ai/workspace
            </div>
          </div>
        </div>

        {/* App shell: sidebar + main */}
        <div style={{ display: "flex", height: 380 }}>
          {/* Left sidebar */}
          <div style={{ width: 54, background: "#030d1a", borderRight: "1px solid rgba(255,255,255,0.05)", display: "flex", flexDirection: "column", alignItems: "center", paddingTop: 14, gap: 16 }}>
            <div style={{ width: 28, height: 28, borderRadius: 7, background: NAVY, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <div style={{ fontSize: 10, fontWeight: 800, color: "#fff", fontFamily: "system-ui" }}>S</div>
            </div>
            {[BrainCircuit, Users, FileText, BarChart3, Globe, Database].map((Icon, i) => (
              <div key={i} style={{ width: 34, height: 34, borderRadius: 8, background: i === 0 ? "rgba(255,255,255,0.09)" : "transparent", display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}>
                <Icon size={14} strokeWidth={1.4} style={{ color: i === 0 ? "#fff" : "rgba(255,255,255,0.25)" }} />
              </div>
            ))}
          </div>

          {/* Main content */}
          <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
            {/* Tab bar */}
            <div style={{ background: "#071828", borderBottom: "1px solid rgba(255,255,255,0.05)", display: "flex", gap: 0, overflowX: "auto", scrollbarWidth: "none" }}>
              {tabs.map((t, i) => (
                <button key={t} onClick={() => setActive(i)} style={{
                  padding: "9px 16px", fontSize: "0.62rem", fontWeight: 600,
                  color: active === i ? "#fff" : "rgba(255,255,255,0.3)",
                  background: active === i ? "#0F2847" : "transparent",
                  borderBottom: active === i ? "2px solid rgba(255,255,255,0.4)" : "2px solid transparent",
                  whiteSpace: "nowrap", fontFamily: "system-ui", letterSpacing: "0.02em", cursor: "pointer", border: "none",
                }}>
                  {t}
                </button>
              ))}
            </div>

            {/* Content area */}
            <div style={{ flex: 1, padding: 18, overflowY: "auto", scrollbarWidth: "none" }}>
              {active === 0 && (
                <>
                  <div style={{ fontSize: "0.62rem", color: "rgba(255,255,255,0.3)", marginBottom: 12, fontFamily: "system-ui" }}>AI LITERATURE REVIEW · 847 papers analyzed</div>
                  {[
                    { pct: 92, label: "Methodological fit" },
                    { pct: 88, label: "Topic relevance" },
                    { pct: 76, label: "Citation strength" },
                  ].map(({ pct, label }) => (
                    <div key={label} style={{ marginBottom: 10 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                        <span style={{ fontSize: "0.6rem", color: "rgba(255,255,255,0.5)", fontFamily: "system-ui" }}>{label}</span>
                        <span style={{ fontSize: "0.6rem", color: "rgba(255,255,255,0.7)", fontFamily: "system-ui", fontWeight: 700 }}>{pct}%</span>
                      </div>
                      <div style={{ height: 4, background: "rgba(255,255,255,0.07)", borderRadius: 2 }}>
                        <div style={{ width: `${pct}%`, height: 4, background: "#3b82f6", borderRadius: 2 }} />
                      </div>
                    </div>
                  ))}
                  <div style={{ marginTop: 16, background: "rgba(255,255,255,0.04)", borderRadius: 8, padding: "10px 12px", border: "1px solid rgba(255,255,255,0.06)" }}>
                    <div style={{ fontSize: "0.6rem", fontWeight: 700, color: "rgba(255,255,255,0.4)", marginBottom: 6, letterSpacing: "0.08em", fontFamily: "system-ui" }}>AI SYNTHESIS</div>
                    {["3 underexplored gaps in CRISPR delivery mechanisms identified", "Key finding: lipid nanoparticles show 2× efficiency over viral vectors in 2023–25 literature", "Recommended journals: Nature Methods, Molecular Therapy"].map((line, i) => (
                      <div key={i} style={{ display: "flex", gap: 6, marginBottom: 5, alignItems: "flex-start" }}>
                        <div style={{ width: 4, height: 4, borderRadius: "50%", background: "#3b82f6", marginTop: 4, flexShrink: 0 }} />
                        <span style={{ fontSize: "0.58rem", color: "rgba(255,255,255,0.5)", lineHeight: 1.5, fontFamily: "system-ui" }}>{line}</span>
                      </div>
                    ))}
                  </div>
                </>
              )}
              {active === 1 && (
                <>
                  <div style={{ fontSize: "0.62rem", color: "rgba(255,255,255,0.3)", marginBottom: 12, fontFamily: "system-ui" }}>RESEARCH GAP DETECTION · 12 gaps found</div>
                  {["Longitudinal studies on mRNA stability in vivo", "Cross-species CRISPR off-target profiling at scale", "Economic modeling of gene therapy accessibility"].map((gap, i) => (
                    <div key={i} style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: 7, padding: "8px 10px", marginBottom: 8 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                        <span style={{ fontSize: "0.6rem", fontWeight: 600, color: "rgba(255,255,255,0.7)", fontFamily: "system-ui" }}>Gap #{i+1}</span>
                        <span style={{ fontSize: "0.55rem", padding: "1px 7px", borderRadius: 10, background: i === 0 ? "#0F2847" : "rgba(255,255,255,0.07)", color: i === 0 ? "#7dd3fc" : "rgba(255,255,255,0.3)", fontFamily: "system-ui" }}>
                          {["High priority","Medium","Emerging"][i]}
                        </span>
                      </div>
                      <div style={{ fontSize: "0.58rem", color: "rgba(255,255,255,0.4)", fontFamily: "system-ui", lineHeight: 1.4 }}>{gap}</div>
                    </div>
                  ))}
                </>
              )}
              {active >= 2 && (
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  <div style={{ fontSize: "0.62rem", color: "rgba(255,255,255,0.3)", fontFamily: "system-ui" }}>
                    {["MANUSCRIPT REVIEW · 94/100 readiness score", "STATISTICAL ANALYSIS · 6 tests recommended", "COLLABORATION NETWORK · 28 connections"][active-2]}
                  </div>
                  {[4,3,3][active-2] && Array.from({ length: [4,3,3][active-2] }).map((_,i) => (
                    <div key={i} style={{ height: 8, borderRadius: 4, background: "rgba(255,255,255,0.06)", width: `${[95,80,70,55,90,75,85,60,70][i]}%` }} />
                  ))}
                  <div style={{ height: 80, background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 8, marginTop: 4 }} />
                </div>
              )}
            </div>
          </div>

          {/* Right panel — collaborators */}
          <div style={{ width: 130, background: "#030d1a", borderLeft: "1px solid rgba(255,255,255,0.05)", padding: "14px 10px", display: "flex", flexDirection: "column", gap: 12 }}>
            <div style={{ fontSize: "0.55rem", fontWeight: 700, color: "rgba(255,255,255,0.25)", letterSpacing: "0.1em", fontFamily: "system-ui" }}>TEAM</div>
            {[
              { init: "KW", name: "Dr. Watanabe", status: "Online",   color: "#059669" },
              { init: "IS", name: "Prof. Sörensen",status: "Editing", color: "#3b82f6" },
              { init: "AD", name: "Dr. Diallo",   status: "Away",    color: "#f59e0b" },
              { init: "MR", name: "Dr. Romano",   status: "Online",  color: "#059669" },
            ].map(({ init, name, status, color }) => (
              <div key={init} style={{ display: "flex", alignItems: "center", gap: 7 }}>
                <div style={{ position: "relative" }}>
                  <div style={{ width: 24, height: 24, borderRadius: "50%", background: NAVY, display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.48rem", fontWeight: 800, color: "#fff", fontFamily: "system-ui" }}>{init}</div>
                  <div style={{ position: "absolute", bottom: 0, right: 0, width: 7, height: 7, borderRadius: "50%", background: color, border: "1.5px solid #030d1a" }} />
                </div>
                <div>
                  <div style={{ fontSize: "0.55rem", fontWeight: 600, color: "rgba(255,255,255,0.6)", fontFamily: "system-ui", lineHeight: 1.2 }}>{name}</div>
                  <div style={{ fontSize: "0.48rem", color: "rgba(255,255,255,0.2)", fontFamily: "system-ui" }}>{status}</div>
                </div>
              </div>
            ))}
            <div style={{ marginTop: "auto", background: "rgba(255,255,255,0.04)", borderRadius: 6, padding: "7px 8px", border: "1px solid rgba(255,255,255,0.06)" }}>
              <div style={{ fontSize: "0.5rem", fontWeight: 700, color: "rgba(255,255,255,0.3)", letterSpacing: "0.08em", fontFamily: "system-ui", marginBottom: 4 }}>NEXT</div>
              <div style={{ fontSize: "0.52rem", color: "rgba(255,255,255,0.4)", fontFamily: "system-ui", lineHeight: 1.4 }}>Review manuscript draft · Tomorrow 14:00 CET</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* Ecosystem SVG */
function EcosystemDiagram() {
  const modules = [
    { angle: -90, label: "AI Workspace",    color: "#1d4ed8" },
    { angle: -30, label: "Research Network",color: "#0891b2" },
    { angle:  30, label: "Projects",        color: "#059669" },
    { angle:  90, label: "Repository",      color: "#7c3aed" },
    { angle: 150, label: "Publications",    color: "#dc2626" },
    { angle: 210, label: "Teaching",        color: "#d97706" },
    { angle: 270, label: "Marketplace",     color: "#0F2847" },
    { angle: 330, label: "Verification",    color: "#475569" },
    { angle:  -5, label: "Institutions",    color: "#1e40af", r: 180 },
    { angle:  95, label: "Analytics",       color: "#065f46", r: 180 },
    { angle: 195, label: "Knowledge Graph", color: "#4c1d95", r: 180 },
  ];
  const W = 480, H = 440, cx = 240, cy = 220, R1 = 130, R2 = 175;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", maxWidth: W, height: "auto" }} aria-hidden="true">
      {/* Orbit rings */}
      <circle cx={cx} cy={cy} r={R1} fill="none" stroke="#e2e8f0" strokeWidth="1" strokeDasharray="4 4" />
      <circle cx={cx} cy={cy} r={R2} fill="none" stroke="#f1f5f9" strokeWidth="1" strokeDasharray="3 6" />

      {/* Connection lines */}
      {modules.map(({ angle, label, r }) => {
        const rad = (angle * Math.PI) / 180;
        const radius = r || R1;
        const mx = cx + radius * Math.cos(rad);
        const my = cy + radius * Math.sin(rad);
        return <line key={label} x1={cx} y1={cy} x2={mx} y2={my} stroke="#e2e8f0" strokeWidth="1" strokeDasharray="3 3" />;
      })}

      {/* Module nodes */}
      {modules.map(({ angle, label, color, r }) => {
        const rad = (angle * Math.PI) / 180;
        const radius = r || R1;
        const mx = cx + radius * Math.cos(rad);
        const my = cy + radius * Math.sin(rad);
        const words = label.split(" ");
        return (
          <g key={label}>
            <circle cx={mx} cy={my} r="26" fill="#fff" stroke={color} strokeWidth="1.5" />
            {words.map((w, i) => (
              <text key={i} x={mx} y={my + (i - (words.length - 1) / 2) * 9 + 1} textAnchor="middle"
                style={{ fontSize: 6.5, fill: color, fontWeight: 700, fontFamily: "system-ui" }}>
                {w}
              </text>
            ))}
          </g>
        );
      })}

      {/* Center core */}
      <circle cx={cx} cy={cy} r="46" fill={NAVY} />
      <text x={cx} y={cy - 5} textAnchor="middle" style={{ fontSize: 10, fill: "#fff", fontWeight: 800, fontFamily: "system-ui" }}>Synaptiq</text>
      <text x={cx} y={cy + 8} textAnchor="middle" style={{ fontSize: 7, fill: "rgba(255,255,255,0.45)", fontFamily: "system-ui" }}>CORE</text>
    </svg>
  );
}

/* World map — abstract with connection arcs */
function WorldMap() {
  const points = [
    { x: 115, y: 95,  city: "New York",    size: 5 },
    { x: 210, y: 78,  city: "London",      size: 6 },
    { x: 240, y: 85,  city: "Paris",       size: 5 },
    { x: 285, y: 73,  city: "Berlin",      size: 4 },
    { x: 195, y: 130, city: "Cairo",       size: 4 },
    { x: 320, y: 90,  city: "Moscow",      size: 4 },
    { x: 360, y: 108, city: "Delhi",       size: 6 },
    { x: 400, y: 105, city: "Beijing",     size: 6 },
    { x: 430, y: 130, city: "Tokyo",       size: 5 },
    { x: 410, y: 160, city: "Singapore",   size: 4 },
    { x: 135, y: 165, city: "São Paulo",   size: 5 },
    { x: 240, y: 195, city: "Nairobi",     size: 4 },
    { x: 430, y: 200, city: "Sydney",      size: 4 },
    { x: 80,  y: 75,  city: "Vancouver",   size: 3 },
    { x: 302, y: 83,  city: "Uppsala",     size: 3 },
  ];
  const arcs = [
    [1, 6], [1, 9], [0, 4], [2, 7], [5, 8], [3, 10], [6, 12], [0, 11], [7, 9], [4, 6], [8, 12], [1, 11],
  ];
  const W = 540, H = 260;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", maxWidth: W, height: "auto" }} aria-hidden="true">
      {/* Continent blobs */}
      {[
        "M80,60 Q100,40 160,55 Q200,60 220,85 Q200,110 160,120 Q110,115 80,95 Z",
        "M180,65 Q230,50 290,60 Q330,65 360,85 Q340,110 300,115 Q250,112 210,100 Q190,88 180,65 Z",
        "M310,65 Q360,50 440,70 Q480,80 490,110 Q470,140 430,155 Q390,155 360,140 Q330,130 310,110 Q300,90 310,65 Z",
        "M100,140 Q130,130 170,145 Q185,165 170,195 Q145,210 115,195 Q95,178 100,140 Z",
        "M200,165 Q235,155 265,165 Q270,185 255,205 Q230,215 205,200 Q195,185 200,165 Z",
        "M390,160 Q430,155 460,175 Q465,200 445,215 Q415,220 395,205 Q380,188 390,160 Z",
      ].map((d, i) => (
        <path key={i} d={d} fill="none" stroke="#0F2847" strokeWidth="1.2" opacity="0.12" />
      ))}

      {/* Connection arcs */}
      {arcs.map(([a, b], i) => {
        const p1 = points[a], p2 = points[b];
        const mx = (p1.x + p2.x) / 2;
        const my = (p1.y + p2.y) / 2 - 40 - Math.abs(p1.x - p2.x) * 0.08;
        return (
          <path key={i} d={`M${p1.x},${p1.y} Q${mx},${my} ${p2.x},${p2.y}`}
            fill="none" stroke="#0F2847" strokeWidth="0.7" opacity="0.2" strokeDasharray="4 4" />
        );
      })}

      {/* City dots */}
      {points.map(({ x, y, city, size }) => (
        <g key={city}>
          <circle cx={x} cy={y} r={size + 3} fill={NAVY} opacity="0.06" />
          <circle cx={x} cy={y} r={size} fill={NAVY} opacity="0.65" />
        </g>
      ))}
    </svg>
  );
}

/* ─── Static data ──────────────────────────────────────────────────────────── */

const WORKFLOW_STEPS = [
  { icon: Lightbulb,   label: "Research Idea",        color: "#f59e0b" },
  { icon: Search,      label: "Find Collaborators",   color: "#3b82f6" },
  { icon: Users,       label: "Build Team",           color: "#0891b2" },
  { icon: Layers,      label: "Create Workspace",     color: "#7c3aed" },
  { icon: Microscope,  label: "Conduct Research",     color: "#059669" },
  { icon: FileText,    label: "Write Manuscript",     color: "#0F2847" },
  { icon: Eye,         label: "Peer Review",          color: "#dc2626" },
  { icon: UploadCloud, label: "Publish",              color: "#1d4ed8" },
  { icon: BarChart3,   label: "Measure Impact",       color: "#9333ea" },
];

const MODULES = [
  {
    icon: BrainCircuit, title: "AI Workspace",
    desc: "Literature review, gap detection, statistical analysis and manuscript review — all AI-powered.",
    preview: ["Literature Review", "Gap Detection", "Statistical Analysis", "Study Design"],
    color: "#1d4ed8",
  },
  {
    icon: Network, title: "Research Network",
    desc: "Discover and connect with 50K+ researchers across 150 countries by field, method and institution.",
    preview: ["Discover Researchers", "Send Invitations", "Collaboration Requests", "Mentorship"],
    color: "#0891b2",
  },
  {
    icon: Layers, title: "Projects",
    desc: "Structured research projects with tasks, milestones, team roles, timelines and deliverables.",
    preview: ["Task Management", "Milestones", "Deliverables", "Research Timeline"],
    color: "#059669",
  },
  {
    icon: GitMerge, title: "Workspaces",
    desc: "Real-time collaborative documents with version control, comments and co-authorship attribution.",
    preview: ["Co-authoring", "Version History", "Comments", "Change Tracking"],
    color: "#7c3aed",
  },
  {
    icon: BookOpen, title: "Publication Hub",
    desc: "Journal matching, cover letter generation, submission tracking and citation monitoring.",
    preview: ["Journal Matching", "Cover Letters", "Submission Tracking", "Citation Monitor"],
    color: "#dc2626",
  },
  {
    icon: Database, title: "Repository",
    desc: "Secure research data, files, datasets and protocols — versioned, tagged and searchable.",
    preview: ["File Storage", "Dataset Management", "Protocol Library", "DOI Assignment"],
    color: "#0F2847",
  },
  {
    icon: Briefcase, title: "Academic Marketplace",
    desc: "Vetted experts for statistical consulting, peer review, translation and academic editing.",
    preview: ["Statistical Consulting", "Peer Review", "Academic Editing", "Translation"],
    color: "#d97706",
  },
  {
    icon: Building2, title: "Institution Dashboard",
    desc: "Analytics, faculty management, grant pipelines and research governance for universities.",
    preview: ["Faculty Analytics", "Grant Pipeline", "Research Benchmarking", "Governance"],
    color: "#1e40af",
  },
  {
    icon: BookMarked, title: "Teaching Hub",
    desc: "Course creation, student research supervision and academic mentorship tools.",
    preview: ["Courses", "Supervision", "Assignments", "Mentorship"],
    color: "#b45309",
  },
  {
    icon: BarChart3, title: "Research Analytics",
    desc: "H-index tracking, citation trends, collaboration metrics and impact forecasting.",
    preview: ["H-index", "Citation Trends", "Impact Score", "Forecasting"],
    color: "#065f46",
  },
  {
    icon: Shield, title: "Verification Center",
    desc: "Academic identity verification, ORCID integration and an 8-level trust score system.",
    preview: ["ORCID Integration", "Identity Verification", "Trust Score", "Badges"],
    color: "#374151",
  },
  {
    icon: Globe, title: "Knowledge Graph",
    desc: "A living map of concepts, papers, researchers and institutions — all semantically linked.",
    preview: ["Concept Mapping", "Entity Relations", "Semantic Search", "Citation Paths"],
    color: "#4c1d95",
  },
];

const AI_FEATURES = [
  { title: "Literature Review",      body: "Reads thousands of papers, surfaces the most relevant findings, and synthesizes key themes with full citations — in minutes." },
  { title: "Research Gap Detection", body: "Identifies underexplored areas across your field, ranked by novelty and feasibility, with evidence from existing literature." },
  { title: "Study Design Advisor",   body: "Recommends methodology, statistical power, sample size and measurement frameworks based on your research question." },
  { title: "Statistical Analysis",   body: "Suggests appropriate tests, reviews assumptions, flags common errors, and explains results in plain scientific language." },
  { title: "Writing Assistant",      body: "Restructures arguments, improves academic language, maintains your voice, and checks for logical flow — never ghostwrites." },
  { title: "Peer Review Assistant",  body: "Evaluates manuscript structure, methodology consistency, citation completeness and readiness for target journals." },
  { title: "Research Integrity",     body: "Checks for statistical anomalies, citation accuracy, data duplication patterns and reporting bias — before submission." },
  { title: "Citation Intelligence",  body: "Tracks how your work is cited, who cites it, in what context, and alerts you when new citations appear." },
  { title: "Knowledge Graph",        body: "Maps every concept, paper, and researcher in your field into a navigable network of semantic connections." },
  { title: "Recommendations",        body: "Proactively surfaces collaborators, papers, grant opportunities and next-research suggestions based on your profile." },
];

const GLOBAL_STATS = [
  { target: 150,  suffix: "+",  label: "Countries" },
  { target: 50,   suffix: "K+", label: "Researchers" },
  { target: 8,    suffix: "K+", label: "Universities" },
  { target: 250,  suffix: "K+", label: "Research Teams" },
  { target: 1200, suffix: "K+", label: "Projects" },
  { target: 2,    suffix: "M+", label: "AI Sessions" },
  { target: 90,   suffix: "K+", label: "Publications" },
  { target: 340,  suffix: "+",  label: "Institutions" },
];

const USER_PROFILES = [
  { icon: GraduationCap, title: "Undergraduate Students",  body: "Build a research profile, find mentors, and contribute to real projects early." },
  { icon: GraduationCap, title: "Master's Students",       body: "Discover thesis supervisors and join international research collaborations." },
  { icon: FlaskConical,  title: "PhD Candidates",          body: "Manage your entire project: literature, writing, team and publications." },
  { icon: Microscope,    title: "Researchers",             body: "Form teams, conduct research, publish, and track your global impact." },
  { icon: Award,         title: "Professors",              body: "Lead groups, supervise students, and benchmark your department's output." },
  { icon: Building2,     title: "Universities",            body: "Institutional analytics, faculty management and grant tracking at scale." },
  { icon: Target,        title: "Research Institutes",     body: "Multi-team management, cross-institutional consortia, and outcomes reporting." },
  { icon: BookOpen,      title: "Publishers",              body: "Connect journals directly to a verified pipeline of global researchers." },
  { icon: Briefcase,     title: "Funding Agencies",        body: "Evaluate grant applicants, track outcomes and surface high-impact research." },
];

const ENTERPRISE_FEATURES = [
  { icon: Shield,       title: "Academic Identity",         body: "Verified researcher profiles with ORCID integration and institutional affiliation confirmation." },
  { icon: Users,        title: "Role-Based Access",         body: "Granular permissions by workspace — lead author, co-author, reviewer, supervisor, or institutional admin." },
  { icon: GitBranch,    title: "Version History",           body: "Full revision history on all documents, datasets and protocols. Revert any change with one click." },
  { icon: Eye,          title: "Audit Logs",                body: "Complete, tamper-proof logs of every action taken in workspaces, projects and institution dashboards." },
  { icon: Lock,         title: "Data Encryption",           body: "TLS 1.2+ in transit and AES-256 at rest. Your research data never leaves your control." },
  { icon: Building2,    title: "Institution Management",    body: "Seat administration, department grouping, SSO/SAML authentication and enterprise billing." },
  { icon: CheckSquare,  title: "Research Governance",       body: "Approval workflows, institutional policies, compliance dashboards and GDPR data exports." },
  { icon: Zap,          title: "Academic Integrity",        body: "Built-in integrity checks: duplication detection, citation accuracy and statistical anomaly flags." },
];

const COLLAB_FEATURES = [
  { icon: Users,       title: "Real-time Co-authoring",   body: "Multiple researchers edit the same document simultaneously with conflict-free merging." },
  { icon: CheckSquare, title: "Task Assignment",          body: "Assign research tasks to team members with deadlines, priorities and progress tracking." },
  { icon: Bell,        title: "Smart Notifications",      body: "Contextual alerts for mentions, document changes, new collaborator activity and deadlines." },
  { icon: GitBranch,   title: "Version Control",          body: "Track every change with full history, compare versions, and restore any previous state." },
  { icon: MessageSquare,title:"Research Discussions",     body: "Threaded discussions tied to specific paragraphs, figures, or data — not a separate inbox." },
  { icon: Eye,         title: "Document Reviews",         body: "Formal review rounds with structured feedback, inline annotations and resolution tracking." },
  { icon: BrainCircuit,title: "AI Recommendations",      body: "Inline suggestions for citations, methodological improvements and writing quality." },
  { icon: Network,     title: "Activity Feed",            body: "A chronological timeline of everything your research team has done in one shared view." },
];

const JOURNEY_STEPS = [
  { num: "01", title: "Research Idea",        body: "Define your question. The AI immediately surfaces related literature, open gaps and potential co-investigators." },
  { num: "02", title: "Find Experts",         body: "Search 50K+ researchers by field, method, institution, and availability. Filter by verified credentials." },
  { num: "03", title: "Invite Team",          body: "Send structured collaboration requests with your brief, expected roles, timeline and institutional affiliation." },
  { num: "04", title: "Research",             body: "Work in a shared workspace: literature, protocols, datasets, and notes — all synced and version-controlled." },
  { num: "05", title: "AI Assistance",        body: "Run literature reviews, gap detection, statistical analysis and integrity checks at any point in the workflow." },
  { num: "06", title: "Writing",              body: "Co-author your manuscript with full revision history, inline AI suggestions and authorship attribution." },
  { num: "07", title: "Review",               body: "Internal structured review before submission. AI checks readiness and flags issues for each target journal." },
  { num: "08", title: "Publication",          body: "Submit to matched journals directly. Track status, respond to reviewers and store acceptance records." },
  { num: "09", title: "Impact Measurement",   body: "Monitor citations, H-index, altmetrics and network reach — updated in real time, for the life of your paper." },
];

/* ─── Sub-components ────────────────────────────────────────────────────────── */

function StatCounter({ target, suffix, label }) {
  const { ref, value } = useCounter(target);
  return (
    <div ref={ref} style={{ textAlign: "center" }}>
      <div style={{ fontSize: "clamp(2.2rem, 4vw, 3.2rem)", fontWeight: 900, color: "#0a0f1a", lineHeight: 1, letterSpacing: "-0.04em" }}>
        {value.toLocaleString()}{suffix}
      </div>
      <div style={{ fontSize: "0.82rem", fontWeight: 600, color: "#64748b", marginTop: 8 }}>{label}</div>
    </div>
  );
}

function ModuleCard({ icon: Icon, title, desc, preview, color }) {
  const [hovered, setHovered] = useState(false);
  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        background: "#fff", border: `1px solid ${hovered ? color : BORDER}`,
        borderRadius: 14, padding: "24px 22px",
        boxShadow: hovered ? `0 12px 40px ${color}18` : "none",
        transition: "border-color 200ms, box-shadow 200ms, transform 200ms",
        transform: hovered ? "translateY(-3px)" : "none",
        cursor: "default",
      }}
    >
      <div style={{ width: 40, height: 40, borderRadius: 10, background: `${color}12`, border: `1px solid ${color}22`, display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 14 }}>
        <Icon size={18} strokeWidth={1.5} style={{ color }} />
      </div>
      <div style={{ fontSize: "0.92rem", fontWeight: 700, color: "#0a0f1a", marginBottom: 8 }}>{title}</div>
      <div style={{ fontSize: "0.78rem", color: "#64748b", lineHeight: 1.65, marginBottom: 16 }}>{desc}</div>
      <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
        {preview.map((p) => (
          <span key={p} style={{ fontSize: "0.62rem", fontWeight: 600, color, background: `${color}10`, border: `1px solid ${color}20`, borderRadius: 5, padding: "2px 8px" }}>{p}</span>
        ))}
      </div>
    </div>
  );
}

/* ─── Page ──────────────────────────────────────────────────────────────────── */
export default function Platform() {
  useEffect(() => {
    document.title = "Platform — Synaptiq";
    return () => { document.title = "Synaptiq"; };
  }, []);
  const [activeAI, setActiveAI] = useState(0);
  const rWorkflow    = useReveal();
  const rModules     = useReveal();
  const rEcosystem   = useReveal();
  const rAI          = useReveal();
  const rGlobal      = useReveal();
  const rUsers       = useReveal();
  const rEnterprise  = useReveal();
  const rComparison  = useReveal();
  const rJourney     = useReveal();
  const rCollab      = useReveal();
  const rStats       = useReveal();
  const rFuture      = useReveal();

  return (
    <MarketingLayout>

      {/* ══════ HERO ══════════════════════════════════════════════════════════ */}
      <section style={{ background: "#fff", borderBottom: `1px solid ${BORDER}`, paddingTop: 80 }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10">
          <div className="grid lg:grid-cols-[1fr_auto] gap-12 items-end">
            <div style={{ paddingBottom: 72 }}>
              <div style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 20 }}>
                The Synaptiq Platform
              </div>
              <h1 style={{
                fontSize: "clamp(2.8rem, 5.5vw, 4.8rem)", fontWeight: 900,
                letterSpacing: "-0.045em", color: "#0a0f1a", lineHeight: 1.02,
                textWrap: "balance", marginBottom: 24, maxWidth: 720,
              }}>
                The Operating System for Global Research.
              </h1>
              <p style={{ fontSize: "clamp(1rem, 1.4vw, 1.1rem)", color: SLATE, lineHeight: 1.8, maxWidth: 560, marginBottom: 36 }}>
                Everything researchers need to discover collaborators, build international teams, conduct research, write publications and measure scientific impact — inside one intelligent platform.
              </p>
              <div className="flex flex-wrap gap-4">
                <Link to="/register"
                  className="inline-flex items-center gap-2 font-semibold active:scale-[.98]"
                  style={{ background: NAVY, color: "#fff", padding: "13px 28px", borderRadius: 9, fontSize: "0.92rem" }}
                >
                  Start Free <ArrowRight size={14} strokeWidth={2.5} />
                </Link>
                <Link to="/contact"
                  className="inline-flex items-center gap-2 font-semibold"
                  style={{ border: `1px solid ${BORDER}`, color: "#0a0f1a", padding: "12px 22px", borderRadius: 9, fontSize: "0.92rem" }}
                >
                  Book a Demo
                </Link>
              </div>
              <p style={{ fontSize: "0.73rem", color: "#94a3b8", marginTop: 14 }}>Free plan available · No credit card required · ORCID compatible</p>
            </div>
            <div className="hidden lg:block" style={{ paddingBottom: 0, marginBottom: "-2px" }}>
              <HeroMockup />
            </div>
          </div>
        </div>
      </section>

      {/* ══════ SECTION 1 — WORKFLOW ═══════════════════════════════════════════ */}
      <section style={{ background: LIGHT, borderBottom: `1px solid ${BORDER}` }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-24 lg:py-32">
          <div ref={rWorkflow} className="sq-reveal">
            <div style={{ textAlign: "center", marginBottom: 64 }}>
              <div className="overline mb-3">One Platform</div>
              <h2 style={{ fontSize: "clamp(1.8rem, 3.5vw, 3rem)", fontWeight: 900, letterSpacing: "-0.035em", color: "#0a0f1a", lineHeight: 1.08, textWrap: "balance" }}>
                Every Research Workflow.
              </h2>
              <p style={{ fontSize: "0.92rem", color: "#64748b", lineHeight: 1.75, maxWidth: 520, margin: "14px auto 0" }}>
                From the first spark of an idea to a published paper and beyond — one continuous, connected journey.
              </p>
            </div>

            {/* Step row */}
            <div style={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: 0, justifyContent: "center" }}>
              {WORKFLOW_STEPS.map(({ icon: Icon, label, color }, i) => (
                <React.Fragment key={label}>
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12, padding: "0 4px" }}>
                    <div style={{ width: 52, height: 52, borderRadius: 14, background: `${color}12`, border: `1.5px solid ${color}30`, display: "flex", alignItems: "center", justifyContent: "center" }}>
                      <Icon size={22} strokeWidth={1.5} style={{ color }} />
                    </div>
                    <div style={{ fontSize: "0.72rem", fontWeight: 700, color: "#334155", textAlign: "center", lineHeight: 1.3, maxWidth: 68 }}>{label}</div>
                  </div>
                  {i < WORKFLOW_STEPS.length - 1 && (
                    <ChevronRight size={16} strokeWidth={1.5} style={{ color: "#cbd5e1", flexShrink: 0, margin: "0 2px", marginBottom: 20 }} />
                  )}
                </React.Fragment>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ══════ SECTION 2 — MODULE GRID ════════════════════════════════════════ */}
      <section style={{ background: "#fff", borderBottom: `1px solid ${BORDER}` }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-24 lg:py-32">
          <div ref={rModules} className="sq-reveal">
            <div style={{ marginBottom: 56 }}>
              <div className="overline mb-3">Explore the Platform</div>
              <div className="flex items-end justify-between flex-wrap gap-4">
                <h2 style={{ fontSize: "clamp(1.8rem, 3.5vw, 3rem)", fontWeight: 900, letterSpacing: "-0.035em", color: "#0a0f1a", lineHeight: 1.08, textWrap: "balance" }}>
                  12 integrated modules.
                </h2>
                <Link to="/pricing" style={{ fontSize: "0.85rem", fontWeight: 600, color: NAVY, display: "flex", alignItems: "center", gap: 5 }}>
                  See all features <ArrowRight size={13} strokeWidth={2} />
                </Link>
              </div>
            </div>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
              {MODULES.map((m) => <ModuleCard key={m.title} {...m} />)}
            </div>
          </div>
        </div>
      </section>

      {/* ══════ SECTION 3 — ECOSYSTEM ══════════════════════════════════════════ */}
      <section style={{ background: LIGHT, borderBottom: `1px solid ${BORDER}` }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-24 lg:py-32">
          <div ref={rEcosystem} className="sq-reveal">
            <div className="grid lg:grid-cols-2 gap-16 items-center">
              <div>
                <div className="overline mb-4">The Synaptiq Ecosystem</div>
                <h2 style={{ fontSize: "clamp(1.8rem, 3.5vw, 3rem)", fontWeight: 900, letterSpacing: "-0.035em", color: "#0a0f1a", lineHeight: 1.08, textWrap: "balance", marginBottom: 20 }}>
                  Everything works together.
                </h2>
                <p style={{ fontSize: "0.92rem", color: SLATE, lineHeight: 1.8, marginBottom: 28 }}>
                  Unlike a collection of disconnected tools, Synaptiq is a unified system. Your profile, your network, your research, your publications and your AI assistant all share the same data model — so every module knows what every other module knows.
                </p>
                <div className="flex flex-col gap-4">
                  {[
                    "A collaborator found in the Network automatically appears in your Project team",
                    "Literature reviewed in the AI Workspace is stored in the shared Repository",
                    "Publication metrics feed back into your Analytics and Reputation score",
                    "Institution dashboards aggregate across every individual module in real time",
                  ].map((item) => (
                    <div key={item} style={{ display: "flex", gap: 12, alignItems: "flex-start" }}>
                      <CheckCircle2 size={15} strokeWidth={2} style={{ color: NAVY, flexShrink: 0, marginTop: 3 }} />
                      <span style={{ fontSize: "0.84rem", color: "#334155", lineHeight: 1.65 }}>{item}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="flex justify-center">
                <EcosystemDiagram />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ══════ SECTION 4 — AI FEATURES ════════════════════════════════════════ */}
      <section style={{ background: "#fff", borderBottom: `1px solid ${BORDER}` }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-24 lg:py-32">
          <div ref={rAI} className="sq-reveal">
            <div style={{ marginBottom: 56 }}>
              <div className="overline mb-3">AI Workspace</div>
              <h2 style={{ fontSize: "clamp(1.8rem, 3.5vw, 3rem)", fontWeight: 900, letterSpacing: "-0.035em", color: "#0a0f1a", lineHeight: 1.08, textWrap: "balance", maxWidth: 560 }}>
                AI built into every step.
              </h2>
              <p style={{ fontSize: "0.92rem", color: "#64748b", lineHeight: 1.75, maxWidth: 520, marginTop: 14 }}>
                Academic AI, not generic AI. Every capability is designed around research methodology, academic publishing standards and scientific integrity.
              </p>
            </div>

            <div className="grid lg:grid-cols-[280px_1fr] gap-8">
              {/* Left — tab list */}
              <div className="flex flex-col gap-1">
                {AI_FEATURES.map(({ title }, i) => (
                  <button key={title} onClick={() => setActiveAI(i)}
                    style={{
                      textAlign: "left", padding: "12px 16px", borderRadius: 9,
                      background: activeAI === i ? NAVY : "transparent",
                      color: activeAI === i ? "#fff" : "#475569",
                      fontSize: "0.85rem", fontWeight: activeAI === i ? 700 : 500,
                      border: "none", cursor: "pointer", transition: "all 160ms",
                      display: "flex", alignItems: "center", justifyContent: "space-between",
                    }}
                  >
                    {title}
                    {activeAI === i && <ChevronRight size={14} strokeWidth={2} style={{ color: "rgba(255,255,255,0.5)" }} />}
                  </button>
                ))}
              </div>

              {/* Right — detail card */}
              <div style={{ background: LIGHT, border: `1px solid ${BORDER}`, borderRadius: 16, padding: "40px 44px", minHeight: 280 }}>
                <div style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 16 }}>AI CAPABILITY</div>
                <h3 style={{ fontSize: "clamp(1.4rem, 2.5vw, 2rem)", fontWeight: 900, letterSpacing: "-0.03em", color: "#0a0f1a", lineHeight: 1.1, marginBottom: 20 }}>
                  {AI_FEATURES[activeAI].title}
                </h3>
                <p style={{ fontSize: "0.95rem", color: SLATE, lineHeight: 1.85, maxWidth: 480 }}>
                  {AI_FEATURES[activeAI].body}
                </p>
                <div style={{ marginTop: 32, paddingTop: 24, borderTop: `1px solid ${BORDER}` }}>
                  <div style={{ fontSize: "0.72rem", fontWeight: 700, color: "#94a3b8", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 12 }}>Academic Design Principles</div>
                  <div className="flex flex-wrap gap-3">
                    {["Verified citations only", "Researcher controls output", "No hallucinated data", "Methodology-aware"].map((p) => (
                      <span key={p} style={{ fontSize: "0.7rem", fontWeight: 600, color: NAVY, background: `${NAVY}0d`, border: `1px solid ${NAVY}20`, borderRadius: 6, padding: "4px 10px" }}>{p}</span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ══════ SECTION 5 — GLOBAL NETWORK ════════════════════════════════════ */}
      <section style={{ background: LIGHT, borderBottom: `1px solid ${BORDER}` }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-24 lg:py-32">
          <div ref={rGlobal} className="sq-reveal">
            <div className="grid lg:grid-cols-2 gap-16 items-center">
              <div>
                <div className="overline mb-4">Global Academic Collaboration</div>
                <h2 style={{ fontSize: "clamp(1.8rem, 3.5vw, 3rem)", fontWeight: 900, letterSpacing: "-0.035em", color: "#0a0f1a", lineHeight: 1.08, textWrap: "balance", marginBottom: 20 }}>
                  Research without geographical borders.
                </h2>
                <p style={{ fontSize: "0.92rem", color: SLATE, lineHeight: 1.8, marginBottom: 32 }}>
                  A researcher in Nairobi can form a team with a professor in Uppsala and a PhD candidate in Kyoto — discovered by AI, connected in minutes, collaborating in a shared workspace without friction.
                </p>
                <div className="grid grid-cols-2 gap-5">
                  {GLOBAL_STATS.map(({ target, suffix, label }) => (
                    <StatCounter key={label} target={target} suffix={suffix} label={label} />
                  ))}
                </div>
              </div>
              <div className="flex flex-col items-center gap-6">
                <WorldMap />
                <div style={{ fontSize: "0.72rem", color: "#94a3b8", textAlign: "center" }}>
                  Active research connections across 150+ countries
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ══════ SECTION 6 — USER PROFILES ══════════════════════════════════════ */}
      <section style={{ background: "#fff", borderBottom: `1px solid ${BORDER}` }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-24 lg:py-32">
          <div ref={rUsers} className="sq-reveal">
            <div style={{ textAlign: "center", marginBottom: 56 }}>
              <div className="overline mb-3">Built for Every Researcher</div>
              <h2 style={{ fontSize: "clamp(1.8rem, 3.5vw, 3rem)", fontWeight: 900, letterSpacing: "-0.035em", color: "#0a0f1a", lineHeight: 1.08, textWrap: "balance" }}>
                The platform adapts to your role.
              </h2>
            </div>
            <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-5">
              {USER_PROFILES.map(({ icon: Icon, title, body }) => (
                <div key={title} style={{ border: `1px solid ${BORDER}`, borderRadius: 14, padding: "22px 20px", display: "flex", gap: 14, alignItems: "flex-start" }}>
                  <div style={{ width: 40, height: 40, borderRadius: 10, background: `${NAVY}0d`, border: `1px solid ${NAVY}18`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                    <Icon size={17} strokeWidth={1.5} style={{ color: NAVY }} />
                  </div>
                  <div>
                    <div style={{ fontSize: "0.87rem", fontWeight: 700, color: "#0a0f1a", marginBottom: 6 }}>{title}</div>
                    <div style={{ fontSize: "0.77rem", color: "#64748b", lineHeight: 1.65 }}>{body}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ══════ SECTION 7 — ENTERPRISE INFRASTRUCTURE ══════════════════════════ */}
      <section style={{ background: LIGHT, borderBottom: `1px solid ${BORDER}` }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-24 lg:py-32">
          <div ref={rEnterprise} className="sq-reveal">
            <div className="grid lg:grid-cols-[360px_1fr] gap-16">
              <div>
                <div className="overline mb-4">Enterprise Infrastructure</div>
                <h2 style={{ fontSize: "clamp(1.8rem, 3vw, 2.6rem)", fontWeight: 900, letterSpacing: "-0.035em", color: "#0a0f1a", lineHeight: 1.1, textWrap: "balance", marginBottom: 20 }}>
                  Built for institutional trust.
                </h2>
                <p style={{ fontSize: "0.9rem", color: SLATE, lineHeight: 1.8 }}>
                  Universities, research centers and funding agencies require infrastructure that goes beyond consumer tools. Synaptiq is designed from the ground up for institutional-grade security, governance and compliance.
                </p>
                <div style={{ marginTop: 28, padding: "18px 20px", background: NAVY, borderRadius: 12 }}>
                  <div style={{ fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "rgba(255,255,255,0.4)", marginBottom: 10 }}>Certifications</div>
                  {["ORCID Integrated", "GDPR Aligned", "TLS 1.2+ Encrypted", "SOC 2 (Coming Soon)"].map((b) => (
                    <div key={b} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
                      <CheckCircle2 size={12} strokeWidth={2} style={{ color: "#4ade80" }} />
                      <span style={{ fontSize: "0.78rem", color: "rgba(255,255,255,0.6)", fontWeight: 500 }}>{b}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="grid sm:grid-cols-2 gap-5">
                {ENTERPRISE_FEATURES.map(({ icon: Icon, title, body }) => (
                  <div key={title} style={{ background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 14, padding: "22px 20px" }}>
                    <div style={{ width: 38, height: 38, borderRadius: 9, background: `${NAVY}0d`, border: `1px solid ${NAVY}18`, display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 14 }}>
                      <Icon size={16} strokeWidth={1.5} style={{ color: NAVY }} />
                    </div>
                    <div style={{ fontSize: "0.87rem", fontWeight: 700, color: "#0a0f1a", marginBottom: 7 }}>{title}</div>
                    <div style={{ fontSize: "0.76rem", color: "#64748b", lineHeight: 1.65 }}>{body}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ══════ SECTION 8 — COMPARISON ═════════════════════════════════════════ */}
      <section style={{ background: "#fff", borderBottom: `1px solid ${BORDER}` }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-24 lg:py-32">
          <div ref={rComparison} className="sq-reveal">
            <div style={{ textAlign: "center", marginBottom: 56 }}>
              <div className="overline mb-3">Traditional Research vs Synaptiq</div>
              <h2 style={{ fontSize: "clamp(1.8rem, 3.5vw, 3rem)", fontWeight: 900, letterSpacing: "-0.035em", color: "#0a0f1a", lineHeight: 1.08 }}>
                The old way vs the right way.
              </h2>
            </div>
            <div className="grid md:grid-cols-2 gap-6 max-w-4xl mx-auto">
              {/* Traditional */}
              <div style={{ border: "1px solid #fecaca", borderRadius: 16, overflow: "hidden" }}>
                <div style={{ background: "#fff5f5", padding: "18px 24px", borderBottom: "1px solid #fecaca" }}>
                  <div style={{ fontSize: "0.75rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "#dc2626" }}>Traditional Research</div>
                  <div style={{ fontSize: "0.8rem", color: "#ef4444", marginTop: 4 }}>12+ disconnected tools</div>
                </div>
                <div style={{ padding: "20px 24px" }}>
                  {[
                    ["Email & Messaging apps",    "Collaboration & communication"],
                    ["Google Docs / Word",        "Document writing"],
                    ["Dropbox / Drive",           "File storage"],
                    ["Excel / SPSS",              "Data & statistics"],
                    ["Separate reference manager","Literature management"],
                    ["Manual journal search",     "Publication matching"],
                    ["Personal alumni network",   "Collaborator discovery"],
                    ["Disconnected analytics",    "Impact measurement"],
                  ].map(([tool, use]) => (
                    <div key={tool} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "9px 0", borderBottom: "1px solid #fff5f5" }}>
                      <div style={{ fontSize: "0.82rem", fontWeight: 600, color: "#7f1d1d" }}>{tool}</div>
                      <div style={{ fontSize: "0.7rem", color: "#b91c1c", textAlign: "right", maxWidth: "45%" }}>{use}</div>
                    </div>
                  ))}
                  <div style={{ marginTop: 16, padding: "12px 14px", background: "#fef2f2", borderRadius: 8, border: "1px solid #fecaca" }}>
                    <div style={{ fontSize: "0.75rem", color: "#dc2626", fontWeight: 600 }}>Result: Fragmentation, version conflicts, missed collaborations, duplicated work</div>
                  </div>
                </div>
              </div>

              {/* Synaptiq */}
              <div style={{ border: `1px solid ${NAVY}30`, borderRadius: 16, overflow: "hidden" }}>
                <div style={{ background: NAVY, padding: "18px 24px", borderBottom: `1px solid ${NAVY}` }}>
                  <div style={{ fontSize: "0.75rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", color: "rgba(255,255,255,0.5)" }}>Synaptiq</div>
                  <div style={{ fontSize: "0.8rem", color: "rgba(255,255,255,0.7)", marginTop: 4 }}>One unified platform</div>
                </div>
                <div style={{ padding: "20px 24px", background: "#f8fafc" }}>
                  {[
                    ["Research Workspace",         "Real-time collaboration"],
                    ["AI Writing Assistant",       "Document writing"],
                    ["Research Repository",        "Versioned file storage"],
                    ["Statistical Intelligence",   "Data & statistics"],
                    ["AI Literature Review",       "Literature management"],
                    ["Publication Hub",            "Journal matching & tracking"],
                    ["AI-powered Network",         "Collaborator discovery"],
                    ["Research Analytics",         "Impact measurement"],
                  ].map(([tool, use]) => (
                    <div key={tool} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "9px 0", borderBottom: "1px solid #e2e8f0" }}>
                      <div style={{ fontSize: "0.82rem", fontWeight: 600, color: NAVY }}>{tool}</div>
                      <div style={{ fontSize: "0.7rem", color: "#475569", textAlign: "right", maxWidth: "45%" }}>{use}</div>
                    </div>
                  ))}
                  <div style={{ marginTop: 16, padding: "12px 14px", background: "#f0f9f4", borderRadius: 8, border: "1px solid #86efac" }}>
                    <div style={{ fontSize: "0.75rem", color: "#166534", fontWeight: 600 }}>Result: One workspace, zero friction, full history, every collaborator connected</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ══════ SECTION 9 — RESEARCH JOURNEY ═══════════════════════════════════ */}
      <section style={{ background: LIGHT, borderBottom: `1px solid ${BORDER}` }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-24 lg:py-32">
          <div ref={rJourney} className="sq-reveal">
            <div style={{ textAlign: "center", marginBottom: 64 }}>
              <div className="overline mb-3">Research Journey</div>
              <h2 style={{ fontSize: "clamp(1.8rem, 3.5vw, 3rem)", fontWeight: 900, letterSpacing: "-0.035em", color: "#0a0f1a", lineHeight: 1.08, textWrap: "balance" }}>
                One continuous, connected journey.
              </h2>
            </div>
            <div className="flex flex-col gap-0">
              {JOURNEY_STEPS.map(({ num, title, body }, i) => (
                <div key={num}
                  style={{
                    display: "grid", gridTemplateColumns: "80px 1fr",
                    borderTop: i === 0 ? `1px solid ${BORDER}` : "none",
                    borderBottom: `1px solid ${BORDER}`,
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = "#fafbff"}
                  onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
                >
                  <div style={{ display: "flex", alignItems: "flex-start", padding: "26px 0", paddingTop: 28 }}>
                    <span style={{ fontSize: "0.65rem", fontWeight: 800, color: "#cbd5e1", letterSpacing: "0.08em" }}>{num}</span>
                  </div>
                  <div style={{ padding: "26px 0", paddingLeft: 20, borderLeft: `1px solid ${BORDER}` }}>
                    <div style={{ fontSize: "0.95rem", fontWeight: 700, color: "#0a0f1a", marginBottom: 6 }}>{title}</div>
                    <div style={{ fontSize: "0.83rem", color: "#64748b", lineHeight: 1.7, maxWidth: 640 }}>{body}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ══════ SECTION 10 — COLLABORATION ════════════════════════════════════ */}
      <section style={{ background: "#fff", borderBottom: `1px solid ${BORDER}` }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-24 lg:py-32">
          <div ref={rCollab} className="sq-reveal">
            <div className="grid lg:grid-cols-[400px_1fr] gap-16 items-start">
              <div>
                <div className="overline mb-4">Collaboration</div>
                <h2 style={{ fontSize: "clamp(1.8rem, 3vw, 2.6rem)", fontWeight: 900, letterSpacing: "-0.035em", color: "#0a0f1a", lineHeight: 1.1, textWrap: "balance", marginBottom: 20 }}>
                  Designed around collaboration.
                </h2>
                <p style={{ fontSize: "0.9rem", color: SLATE, lineHeight: 1.8 }}>
                  Research has always been collaborative. Synaptiq makes the collaboration invisible — so you spend your mental energy on the research, not on coordinating the team.
                </p>
                <Link to="/register" className="inline-flex items-center gap-2 mt-8" style={{ fontSize: "0.87rem", fontWeight: 700, color: NAVY }}>
                  Explore collaboration tools <ArrowRight size={13} strokeWidth={2.5} />
                </Link>
              </div>
              <div className="grid sm:grid-cols-2 gap-5">
                {COLLAB_FEATURES.map(({ icon: Icon, title, body }) => (
                  <div key={title} style={{ padding: "20px 0", borderTop: `2px solid ${NAVY}` }}>
                    <div style={{ width: 36, height: 36, borderRadius: 8, background: `${NAVY}0d`, display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 12 }}>
                      <Icon size={16} strokeWidth={1.5} style={{ color: NAVY }} />
                    </div>
                    <div style={{ fontSize: "0.87rem", fontWeight: 700, color: "#0a0f1a", marginBottom: 6 }}>{title}</div>
                    <div style={{ fontSize: "0.76rem", color: "#64748b", lineHeight: 1.65 }}>{body}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ══════ SECTION 11 — STATS ═════════════════════════════════════════════ */}
      <section style={{ background: NAVY }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-24 lg:py-28">
          <div ref={rStats} className="sq-reveal">
            <div style={{ textAlign: "center", marginBottom: 56 }}>
              <div style={{ fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "rgba(255,255,255,0.3)", marginBottom: 14 }}>Platform Statistics</div>
              <h2 style={{ fontSize: "clamp(1.8rem, 3.5vw, 2.8rem)", fontWeight: 900, letterSpacing: "-0.035em", color: "#fff", lineHeight: 1.08 }}>
                The numbers speak for themselves.
              </h2>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
              {GLOBAL_STATS.map(({ target, suffix, label }) => (
                <div key={label} className="text-center">
                  <StatCtrDark target={target} suffix={suffix} label={label} />
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ══════ SECTION 12 — FUTURE VISION ════════════════════════════════════ */}
      <section style={{ background: LIGHT, borderBottom: `1px solid ${BORDER}` }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-24 lg:py-32">
          <div ref={rFuture} className="sq-reveal">
            <div style={{ textAlign: "center", maxWidth: 720, margin: "0 auto" }}>
              <div className="overline mb-4">Future Vision</div>
              <h2 style={{ fontSize: "clamp(2rem, 4vw, 3.4rem)", fontWeight: 900, letterSpacing: "-0.04em", color: "#0a0f1a", lineHeight: 1.06, textWrap: "balance", marginBottom: 20 }}>
                Building the Digital Infrastructure for Global Science.
              </h2>
              <p style={{ fontSize: "0.95rem", color: SLATE, lineHeight: 1.85, marginBottom: 48 }}>
                Synaptiq will become the central ecosystem connecting every researcher, institution, AI agent and piece of scientific knowledge on the planet. Not a tool — an operating system for science itself.
              </p>
              <div className="grid sm:grid-cols-3 gap-6 text-left">
                {[
                  { num: "Phase I",   title: "Foundation",           body: "A unified platform replacing the fragmented toolchain for 50K+ researchers worldwide." },
                  { num: "Phase II",  title: "Intelligence Layer",   body: "Autonomous AI agents assisting every stage of the research lifecycle with full academic rigor." },
                  { num: "Phase III", title: "Global Infrastructure",body: "The world's largest verified network of researchers, institutions and scientific knowledge." },
                ].map(({ num, title, body }) => (
                  <div key={num} style={{ padding: "24px 0", borderTop: `2px solid ${NAVY}` }}>
                    <div style={{ fontSize: "0.65rem", fontWeight: 800, color: "#94a3b8", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 10 }}>{num}</div>
                    <div style={{ fontSize: "1rem", fontWeight: 800, color: "#0a0f1a", marginBottom: 8 }}>{title}</div>
                    <div style={{ fontSize: "0.79rem", color: "#64748b", lineHeight: 1.7 }}>{body}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ══════ SECTION 13 — CTA ═══════════════════════════════════════════════ */}
      <section style={{ background: "#fff" }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-32 lg:py-44">
          <div style={{ textAlign: "center", maxWidth: 640, margin: "0 auto" }}>
            <div style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 24 }}>Get Started</div>
            <h2 style={{
              fontSize: "clamp(2.2rem, 5vw, 4.2rem)", fontWeight: 900,
              letterSpacing: "-0.04em", color: "#0a0f1a", lineHeight: 1.04, textWrap: "balance", marginBottom: 20,
            }}>
              Start Your Next Research Collaboration Today.
            </h2>
            <p style={{ fontSize: "1rem", color: "#64748b", lineHeight: 1.75, maxWidth: 460, margin: "0 auto 40px" }}>
              Join 50,000+ researchers already building, collaborating, and publishing with Synaptiq.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Link to="/register"
                className="inline-flex items-center gap-2.5 font-semibold active:scale-[.98]"
                style={{ background: NAVY, color: "#fff", padding: "15px 32px", borderRadius: 10, fontSize: "0.95rem", boxShadow: "0 4px 24px rgba(15,40,71,0.2)" }}
              >
                Start Free <ArrowRight size={15} strokeWidth={2.5} />
              </Link>
              <Link to="/contact"
                className="inline-flex items-center gap-2 font-semibold"
                style={{ border: `1px solid ${BORDER}`, color: "#0a0f1a", padding: "14px 28px", borderRadius: 10, fontSize: "0.93rem" }}
              >
                Book a Demo
              </Link>
            </div>
            <p style={{ fontSize: "0.75rem", color: "#94a3b8", marginTop: 18 }}>
              Free plan available · No credit card required · GDPR aligned
            </p>
          </div>
        </div>
      </section>

    </MarketingLayout>
  );
}

/* Dark-background stat counter for Section 11 */
function StatCtrDark({ target, suffix, label }) {
  const { ref, value } = useCounter(target);
  return (
    <div ref={ref}>
      <div style={{ fontSize: "clamp(2rem, 3.5vw, 3rem)", fontWeight: 900, color: "#fff", lineHeight: 1, letterSpacing: "-0.04em" }}>
        {value.toLocaleString()}{suffix}
      </div>
      <div style={{ fontSize: "0.8rem", fontWeight: 600, color: "rgba(255,255,255,0.4)", marginTop: 8 }}>{label}</div>
    </div>
  );
}
