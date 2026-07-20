/* eslint-disable */
import React, { useState, useRef, useEffect } from "react";
import { Link } from "react-router-dom";
import MarketingLayout from "../../components/layout/MarketingLayout";
import { ArrowRight, ChevronDown, ChevronUp, Sparkles, Zap, Shield, Building2, BookOpen, Globe, BrainCircuit, Network, GitMerge, BarChart3, CheckCircle2, Star } from "lucide-react";

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

/* ─── Release data ────────────────────────────────────────────────────────── */
const RELEASES = [
  {
    version: "3.0",
    date: "June 2026",
    label: "Major",
    title: "Synaptiq 3.0 — The Academic Operating System",
    summary: "A complete reimagination of the platform. Synaptiq 3.0 unifies every research workflow into one intelligent ecosystem — from first idea to published paper.",
    categories: {
      "New": [
        "Synaptiq AI OS: 9-agent orchestration layer across all platform modules",
        "Research OS: unified timeline, global search, action center",
        "Digital Research Twin: private simulation layer for research trajectories",
        "Living Knowledge Graph: real-time semantic network of papers, concepts and researchers",
        "Academic Marketplace: vetted expert services (stats, editing, translation, review)",
        "Multi-Agent Copilot: 14 specialized agents, 15 workflows, SSE streaming",
      ],
      "Improved": [
        "Platform redesign: white-background design system, premium typography",
        "Dashboard: adaptive modes (discovery, project, writing, institution)",
        "Navigation: 8-section accordion sidebar with smart grouping",
        "Command Palette (⌘K): global search across all platform entities",
      ],
      "Security": [
        "Zero Trust Security layer: 16-file zt/ package, identity + policy + classification",
        "Enterprise Observability: distributed tracing, structured logs, audit trail",
        "Break-glass access with MFA approval for super-admin actions",
      ],
      "Performance": [
        "Redis session caching across all platform modules",
        "Atlas vector search for semantic similarity at scale",
        "Worker platform: 4-worker pool with circuit breakers and DLQ",
      ],
    },
  },
  {
    version: "2.9",
    date: "May 2026",
    label: "AI",
    title: "AI Workspace 2.0 — Academic Intelligence Engine",
    summary: "A complete overhaul of the AI research suite. Every capability is now academically rigorous, evidence-based and transparent.",
    categories: {
      "AI": [
        "Literature Review Intelligence 2.0: 6 review types, 11 paper sources, 6 export formats",
        "Research Gap Intelligence 2.0: 18 gap types, 10-dim scoring, 7 export formats",
        "Manuscript Intelligence 2.0: 5 rule reviewers, AI reviewer, 25 journal profiles",
        "Statistical Intelligence 2.0: 6 rule reviewers, AI statistical advisor",
        "Academic Copilot: proactive AI advisor with 10-engine orchestration",
        "Publishing Intelligence: 27-journal database, 6 match types, cover letter generation",
      ],
      "New": [
        "Evidence policy: every AI recommendation traces to verified data — no fabricated stats",
        "Proactive AI briefing: morning digest of personalized research recommendations",
        "Autonomous Research Agents: 20 specialized agents with mission state machine",
      ],
      "Improved": [
        "AI responses now include confidence scores derived from data quality",
        "Citation accuracy checking before every recommendation",
        "Context truncation protection for long research sessions",
      ],
    },
  },
  {
    version: "2.8",
    date: "April 2026",
    label: "Institution",
    title: "Institution Intelligence Platform",
    summary: "A full institutional analytics and governance suite for universities, research offices and funding agencies.",
    categories: {
      "New": [
        "Institution Intelligence Engine: 20 KPIs, 12 visualization types, 7 export formats",
        "Academic Benchmarking: compare institution performance against global peers",
        "Doctoral School management: cohort tracking, supervision and outcome analytics",
        "Research Office dashboard: grant pipeline, faculty output, collaboration map",
        "Institution Hub: IIS scoring, 6 service modules, 24-endpoint API",
        "Seat Administration: department grouping, role management, billing visibility",
      ],
      "Improved": [
        "Institution Analytics Center: 65KB upgraded dashboard with 7 service files",
        "Grant Intelligence: 29 new endpoints, team/budget/deliverables CRUD",
        "Faculty publication tracking with journal impact factor integration",
      ],
      "Security": [
        "SSO/SAML configuration for institution-wide rollout",
        "Audit logs for all admin-level actions within institution scope",
      ],
    },
  },
  {
    version: "2.7",
    date: "March 2026",
    label: "New",
    title: "Academic Knowledge Graph",
    summary: "A living, semantic map of research concepts, papers, researchers and institutions — navigable and always up to date.",
    categories: {
      "New": [
        "35 node types and 26 relationship types in the core graph model",
        "Force-directed SVG graph explorer with zoom, pan and node inspection",
        "Semantic reasoning: find analogous concepts and unexplored connections",
        "Community detection: automatic clustering of related research topics",
        "Graph embeddings: similarity search across the full knowledge space",
        "BM25 + RRF hybrid retrieval for transparent AI injection",
      ],
      "AI": [
        "TF-IDF + Ollama + OpenAI embedding support for graph vectors",
        "RAG integration: knowledge graph as grounding context for all AI responses",
        "Concept mapping from uploaded papers and preprints",
      ],
      "Performance": [
        "numpy vector store for sub-100ms similarity queries at 1M+ nodes",
        "Incremental graph updates as new papers are ingested",
      ],
    },
  },
  {
    version: "2.6",
    date: "February 2026",
    label: "New",
    title: "Research OS & Adaptive Dashboard",
    summary: "A new operating layer that brings together projects, activity, AI recommendations and team updates into one unified daily view.",
    categories: {
      "New": [
        "Today.jsx: personalized daily research briefing with priority recommendations",
        "Research OS: unified timeline, global action search, mode-aware interface",
        "Adaptive dashboard: 4 modes (discovery, project, writing, institution)",
        "Intent search: type what you want to do, get ranked platform actions",
        "Focus Mode: distraction-free writing and analysis environment",
      ],
      "Improved": [
        "Dashboard personalization matrix: 12 widget types, drag-to-reorder",
        "Real-time collaboration notifications with smart batching",
        "Sidebar V2: 8-section accordion with pinned items and recently used",
      ],
    },
  },
  {
    version: "2.5",
    date: "January 2026",
    label: "Teaching",
    title: "Teaching Hub & Academic Analytics",
    summary: "A complete teaching and mentorship suite for professors, supervisors and academic departments.",
    categories: {
      "New": [
        "Teaching Hub: course creation, student supervision, assignment management",
        "Teaching Analytics: 11 endpoints, 3 new pages, engagement scoring models",
        "Mentorship management: match students with supervisors by research area",
        "Academic Passport: portable research identity across institutions",
        "Research Timeline: heatmap, milestones, insights — 18-endpoint engine",
      ],
      "Improved": [
        "Student project tracking with deliverable milestones",
        "Supervisor feedback workflows with structured review rounds",
        "Department-level teaching analytics aggregation",
      ],
    },
  },
  {
    version: "2.4",
    date: "December 2025",
    label: "New",
    title: "Verification & Trust System",
    summary: "An 8-level academic identity verification system with a 0–1000 trust score and 16 trust badges.",
    categories: {
      "New": [
        "Verification Center: 8-level verification, 6 service files, 24-endpoint router",
        "Trust Score: 0–1000 composite scoring across identity, publications and network",
        "ORCID deep integration: pull publications, affiliations and funding records",
        "Academic Passport: verified credentials portable across institutions and countries",
        "Verification badge system: 16 badge types displayed on public researcher profiles",
      ],
      "Security": [
        "Anti-gaming engine: multi-signal anomaly detection for trust score manipulation",
        "Institutional verification via signed email domain + admin confirmation",
        "Document-based verification for research appointments and affiliations",
      ],
    },
  },
  {
    version: "2.3",
    date: "November 2025",
    label: "Research",
    title: "Reputation & Research Impact",
    summary: "A 4-dimension reputation engine and 10-tab Research Impact Dashboard with H-index tracking, benchmarking and forecasting.",
    categories: {
      "New": [
        "Research Impact Dashboard (SIS 0–10000): H-index, benchmarking, forecasting",
        "Reputation System: 4-dimension scoring (quality, influence, collaboration, integrity)",
        "Research leaderboards: global, field-specific and institution-level rankings",
        "Citation Intelligence: real-time citation monitoring, context analysis",
        "Career Intelligence: 12 career stages, promotion readiness, skill gap analysis",
      ],
      "Improved": [
        "Analytics page overhauled: fake metric detection and replacement with real data",
        "H-index calculation engine with backward-compatible citation history",
        "Research output timeline with publication milestone markers",
      ],
    },
  },
  {
    version: "2.2",
    date: "October 2025",
    label: "New",
    title: "Collaboration Intelligence & Reviewer Marketplace",
    summary: "AI-powered team formation, collaboration matching and a structured peer review marketplace.",
    categories: {
      "New": [
        "Collaboration Intelligence: 9-dimension matching engine, team optimizer",
        "Reviewer Marketplace: 7 collections, conflict detection, quality scoring",
        "Grant Collaboration Hub: consortium builder, partner matching, readiness engine",
        "Public Research Profiles: slug system, follow system, research showcase",
        "Real-time collaboration: WebSocket-powered co-authoring with merge protection",
      ],
      "Improved": [
        "Collaboration requests: structured brief with roles, timeline and goals",
        "Network discovery: filter by field, methodology, institution, availability",
        "Team workspace: shared literature, protocols and manuscript in one view",
      ],
    },
  },
  {
    version: "2.0",
    date: "September 2025",
    label: "Security",
    title: "Zero-Trust Hardening & MFA",
    summary: "Enterprise-grade security: TOTP-based MFA, device trust, IP allowlisting and risk-based access controls.",
    categories: {
      "Security": [
        "TOTP MFA with backup codes and recovery flow",
        "Device trust registry: known device tracking per user account",
        "Risk engine: behavioral anomaly detection with automatic step-up auth",
        "IP allowlist management for institution-wide access control",
        "Break-glass emergency access with dual-approval MFA",
        "Session management: Redis-backed, geo-tagged, revocable per device",
      ],
      "Fixed": [
        "Session fixation vulnerability in Google OAuth callback flow",
        "CSRF token rotation on privilege elevation actions",
        "Rate limiting bypass via header manipulation — patched",
      ],
    },
  },
];

const LABEL_COLORS = {
  Major:      { bg: "#eff6ff", text: "#1d4ed8", border: "#bfdbfe" },
  AI:         { bg: "#f0f9ff", text: "#0369a1", border: "#bae6fd" },
  Institution:{ bg: "#f0fdf4", text: "#15803d", border: "#bbf7d0" },
  New:        { bg: "#faf5ff", text: "#7c3aed", border: "#e9d5ff" },
  Teaching:   { bg: "#fff7ed", text: "#c2410c", border: "#fed7aa" },
  Research:   { bg: `${NAVY}0d`, text: NAVY,   border: `${NAVY}20` },
  Security:   { bg: "#fef2f2", text: "#dc2626", border: "#fecaca" },
};

/* ─── Illustration ────────────────────────────────────────────────────────── */
function WhatsNewIllus() {
  return (
    <svg viewBox="0 0 300 260" style={{ width: "100%", maxWidth: 300, height: "auto" }} aria-hidden="true">
      {/* Document stack */}
      <rect x="60" y="80" width="160" height="140" rx="6" fill="none" stroke={NAVY} strokeWidth="1.5" opacity="0.15" transform="rotate(-4,140,150)" />
      <rect x="55" y="75" width="160" height="140" rx="6" fill="#fff" stroke={NAVY} strokeWidth="1.5" opacity="0.3" transform="rotate(-2,135,145)" />
      <rect x="50" y="70" width="165" height="145" rx="6" fill="#fff" stroke={NAVY} strokeWidth="1.8" />

      {/* Version badge */}
      <rect x="60" y="82" width="42" height="18" rx="9" fill={NAVY} />
      <text x="81" y="94" textAnchor="middle" style={{ fontSize: 8, fill: "#fff", fontWeight: 800, fontFamily: "system-ui" }}>v3.0</text>

      {/* Content lines */}
      <text x="112" y="94" style={{ fontSize: 9, fill: NAVY, fontWeight: 700, fontFamily: "system-ui" }}>What's New</text>
      <line x1="60" y1="108" x2="205" y2="108" stroke={NAVY} strokeWidth="0.8" opacity="0.15" />
      {[[60,120,145,6],[60,130,180,5],[60,140,160,5],[60,150,190,5],[60,160,135,5]].map(([x,y,w,h],i)=>(
        <rect key={i} x={x} y={y} width={w} height={h} rx="2" fill={NAVY} opacity="0.08" />
      ))}

      {/* Stars / sparkles */}
      <text x="200" y="50" style={{ fontSize: 22, fontFamily: "system-ui" }} opacity="0.5">✦</text>
      <text x="30"  y="60" style={{ fontSize: 14, fontFamily: "system-ui" }} opacity="0.3">✦</text>
      <text x="220" y="180" style={{ fontSize: 10, fontFamily: "system-ui" }} opacity="0.25">✦</text>

      {/* Notification dot */}
      <circle cx="205" cy="82" r="10" fill="#ef4444" opacity="0.85" />
      <text x="205" y="86" textAnchor="middle" style={{ fontSize: 9, fill: "#fff", fontWeight: 800, fontFamily: "system-ui" }}>3</text>

      {/* Arrow */}
      <line x1="140" y1="225" x2="140" y2="250" stroke={NAVY} strokeWidth="1.5" opacity="0.3" strokeLinecap="round" />
      <polyline points="133,243 140,250 147,243" fill="none" stroke={NAVY} strokeWidth="1.5" opacity="0.3" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/* ─── Release card ────────────────────────────────────────────────────────── */
function ReleaseCard({ release }) {
  const [expanded, setExpanded] = useState({});
  const ref = useReveal();

  const toggle = (cat) => setExpanded(prev => ({ ...prev, [cat]: !prev[cat] }));
  const colors = LABEL_COLORS[release.label] || LABEL_COLORS["New"];
  const catIcons = { New: Sparkles, AI: BrainCircuit, Improved: Zap, Security: Shield, Institution: Building2, Teaching: BookOpen, Research: BarChart3, Fixed: CheckCircle2, Performance: Star };

  return (
    <div ref={ref} className="sq-reveal" style={{ display: "grid", gridTemplateColumns: "1fr", gap: 0 }}>
      {/* Main card */}
      <div style={{ background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 16, overflow: "hidden", boxShadow: "0 2px 12px rgba(0,0,0,0.04)" }}>
        {/* Header */}
        <div style={{ padding: "28px 32px 24px", borderBottom: `1px solid ${BORDER}` }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16, flexWrap: "wrap" }}>
            <div style={{ fontSize: "0.72rem", fontWeight: 800, letterSpacing: "0.04em", padding: "3px 10px", borderRadius: 20, background: colors.bg, color: colors.text, border: `1px solid ${colors.border}` }}>
              {release.label}
            </div>
            <div style={{ fontSize: "0.7rem", fontWeight: 600, color: "#94a3b8" }}>{release.date}</div>
          </div>
          <h3 style={{ fontSize: "clamp(1.2rem, 2.5vw, 1.7rem)", fontWeight: 900, letterSpacing: "-0.03em", color: "#0a0f1a", lineHeight: 1.15, marginBottom: 12 }}>{release.title}</h3>
          <p style={{ fontSize: "0.87rem", color: "#475569", lineHeight: 1.75, maxWidth: 640 }}>{release.summary}</p>
        </div>

        {/* Categories */}
        <div style={{ padding: "0 32px 28px" }}>
          {Object.entries(release.categories).map(([cat, items]) => {
            const Icon = catIcons[cat] || Sparkles;
            const open = expanded[cat] !== false; // default open
            return (
              <div key={cat} style={{ borderBottom: `1px solid ${BORDER}`, paddingTop: 20 }}>
                <button
                  onClick={() => toggle(cat)}
                  style={{ display: "flex", alignItems: "center", gap: 10, width: "100%", background: "none", border: "none", cursor: "pointer", padding: "0 0 16px", textAlign: "left" }}
                >
                  <div style={{ width: 28, height: 28, borderRadius: 7, background: `${NAVY}0a`, display: "flex", alignItems: "center", justifyContent: "center" }}>
                    <Icon size={13} strokeWidth={2} style={{ color: NAVY }} />
                  </div>
                  <span style={{ fontSize: "0.78rem", fontWeight: 700, color: "#0a0f1a", letterSpacing: "0.02em" }}>{cat}</span>
                  <span style={{ fontSize: "0.68rem", color: "#94a3b8", marginLeft: 2 }}>{items.length} {items.length === 1 ? "change" : "changes"}</span>
                  <div style={{ marginLeft: "auto" }}>
                    {open ? <ChevronUp size={14} style={{ color: "#94a3b8" }} /> : <ChevronDown size={14} style={{ color: "#94a3b8" }} />}
                  </div>
                </button>
                {open && (
                  <ul style={{ margin: "0 0 16px", padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 8 }}>
                    {items.map((item, i) => (
                      <li key={i} style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
                        <div style={{ width: 5, height: 5, borderRadius: "50%", background: NAVY, opacity: 0.3, flexShrink: 0, marginTop: 7 }} />
                        <span style={{ fontSize: "0.82rem", color: "#334155", lineHeight: 1.65 }}>{item}</span>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

/* ─── Page ─────────────────────────────────────────────────────────────────── */
export default function WhatsNew() {
  React.useEffect(() => {
    document.title = "What's New — Synaptiq";
    return () => { document.title = "Synaptiq"; };
  }, []);
  return (
    <MarketingLayout>

      {/* Hero */}
      <section style={{ background: "#fff", borderBottom: `1px solid ${BORDER}`, paddingTop: 72, paddingBottom: 64 }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10">
          <div className="grid lg:grid-cols-[1fr_auto] gap-12 items-center">
            <div>
              <div style={{ fontSize: "0.7rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 16 }}>Resources</div>
              <h1 style={{ fontSize: "clamp(2.8rem, 6vw, 5rem)", fontWeight: 900, letterSpacing: "-0.045em", color: "#0a0f1a", lineHeight: 1.0, marginBottom: 18 }}>
                What's New
              </h1>
              <p style={{ fontSize: "1rem", color: "#64748b", lineHeight: 1.75, maxWidth: 480 }}>
                See everything that has recently improved across Synaptiq — releases, AI capabilities, enterprise features and fixes.
              </p>
              <div className="flex gap-3 mt-6 flex-wrap">
                {Object.entries(LABEL_COLORS).map(([label, { bg, text, border }]) => (
                  <span key={label} style={{ fontSize: "0.65rem", fontWeight: 700, padding: "3px 10px", borderRadius: 20, background: bg, color: text, border: `1px solid ${border}` }}>{label}</span>
                ))}
              </div>
            </div>
            <div className="hidden lg:flex items-center justify-end">
              <WhatsNewIllus />
            </div>
          </div>
        </div>
      </section>

      {/* Release timeline */}
      <section style={{ background: LIGHT }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-16 lg:py-24">
          <div className="grid lg:grid-cols-[200px_1fr] gap-10">

            {/* Sticky left — version index */}
            <div className="hidden lg:block">
              <div style={{ position: "sticky", top: 80 }}>
                <div style={{ fontSize: "0.65rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 16 }}>All Releases</div>
                <div className="flex flex-col gap-1">
                  {RELEASES.map((r) => (
                    <a key={r.version} href={`#v${r.version}`}
                      style={{ fontSize: "0.8rem", color: "#64748b", fontWeight: 600, padding: "6px 12px", borderRadius: 7, textDecoration: "none", transition: "all 150ms", display: "flex", alignItems: "center", gap: 8 }}
                      onMouseEnter={(e) => { e.currentTarget.style.background = "#fff"; e.currentTarget.style.color = NAVY; }}
                      onMouseLeave={(e) => { e.currentTarget.style.background = "transparent"; e.currentTarget.style.color = "#64748b"; }}
                    >
                      <span style={{ fontSize: "0.65rem", fontWeight: 800, color: "#cbd5e1" }}>v{r.version}</span>
                      <span style={{ fontSize: "0.72rem" }}>{r.date}</span>
                    </a>
                  ))}
                </div>
              </div>
            </div>

            {/* Right — release cards */}
            <div className="flex flex-col gap-8">
              {RELEASES.map((r) => (
                <div key={r.version} id={`v${r.version}`}>
                  <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
                    <div style={{ width: 36, height: 36, borderRadius: 10, background: NAVY, display: "flex", alignItems: "center", justifyContent: "center" }}>
                      <span style={{ fontSize: "0.6rem", fontWeight: 800, color: "#fff", fontFamily: "system-ui" }}>v{r.version}</span>
                    </div>
                    <div style={{ flex: 1, height: 1, background: BORDER }} />
                  </div>
                  <ReleaseCard release={r} />
                </div>
              ))}
            </div>

          </div>
        </div>
      </section>

      {/* Footer CTA */}
      <section style={{ background: NAVY }}>
        <div className="max-w-[1280px] mx-auto px-6 lg:px-10 py-20 text-center">
          <div style={{ fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "rgba(255,255,255,0.3)", marginBottom: 18 }}>Ready to get started?</div>
          <h2 style={{ fontSize: "clamp(1.8rem, 3.5vw, 2.8rem)", fontWeight: 900, letterSpacing: "-0.04em", color: "#fff", lineHeight: 1.08, marginBottom: 16 }}>
            Every one of these features is available to you today.
          </h2>
          <p style={{ fontSize: "0.92rem", color: "rgba(255,255,255,0.5)", marginBottom: 32 }}>Start for free. No credit card required.</p>
          <div className="flex justify-center gap-4 flex-wrap">
            <Link to="/register" style={{ background: "#fff", color: NAVY, padding: "13px 28px", borderRadius: 9, fontWeight: 700, fontSize: "0.9rem", display: "inline-flex", alignItems: "center", gap: 6 }}>
              Start Free <ArrowRight size={14} strokeWidth={2.5} />
            </Link>
            <Link to="/pricing" style={{ border: "1px solid rgba(255,255,255,0.2)", color: "rgba(255,255,255,0.7)", padding: "12px 24px", borderRadius: 9, fontWeight: 600, fontSize: "0.9rem", display: "inline-flex", alignItems: "center" }}>
              Explore Pricing
            </Link>
          </div>
        </div>
      </section>

    </MarketingLayout>
  );
}
