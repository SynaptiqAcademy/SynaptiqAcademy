/* eslint-disable */
import React, { useState, useRef, useEffect } from "react";
import { Link } from "react-router-dom";
import MarketingLayout from "../components/layout/MarketingLayout";
import {
  ArrowRight, BookOpen, FlaskConical, BarChart3, Users, FileText,
  Globe, GitBranch, TrendingUp, ChevronRight, CheckCircle2, Star,
  Search, Database, Layers, Award, Clock, Folder, MessageSquare,
  BookMarked, Microscope, Target, UploadCloud, Network, Shield,
  Activity, Zap, ChevronDown,
} from "lucide-react";

/* ─── Shared hooks ───────────────────────────────────────────────────────────── */

function useReveal(threshold = 0.07) {
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current; if (!el) return;
    if (typeof IntersectionObserver === "undefined") { el.classList.add("rl-in"); return; }
    const obs = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { el.classList.add("rl-in"); obs.disconnect(); }
    }, { threshold });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);
  return ref;
}

/* ─── Design tokens ──────────────────────────────────────────────────────────── */
const NAVY  = "#0F2847";
const NAVY2 = "#1B3B6F";
const SAGE  = "#4A7C59";   // research-specific green accent
const LIGHT = "#F8FAFB";
const BORDER= "#E4EBF2";
const SLATE = "#475569";
const BODY  = "#334155";

/* ─── Global styles ─────────────────────────────────────────────────────────── */
const GLOBAL_CSS = `
  .rl-fade { opacity: 0; transform: translateY(24px); transition: opacity 0.65s ease, transform 0.65s ease; }
  .rl-fade.rl-in { opacity: 1; transform: none; }
  .rl-fade-d1.rl-in { transition-delay: 0.1s; }
  .rl-fade-d2.rl-in { transition-delay: 0.2s; }
  .rl-fade-d3.rl-in { transition-delay: 0.3s; }
  .rl-fade-d4.rl-in { transition-delay: 0.4s; }

  .rl-stage-card { transition: border-color 180ms, box-shadow 180ms, background 180ms; }
  .rl-stage-card:hover { border-color: ${NAVY} !important; box-shadow: 0 4px 24px rgba(15,40,71,0.12); background: #fff !important; }

  .rl-feat-card { transition: box-shadow 200ms, border-color 200ms; }
  .rl-feat-card:hover { box-shadow: 0 8px 32px rgba(15,40,71,0.11); border-color: #cbd5e1 !important; }

  .rl-cta-btn { transition: opacity 160ms, transform 160ms; }
  .rl-cta-btn:hover { opacity: 0.88; transform: translateY(-1px); }

  .rl-secondary-btn { transition: background 160ms, border-color 160ms; }
  .rl-secondary-btn:hover { background: ${LIGHT} !important; border-color: ${NAVY} !important; }

  .rl-uni-logo { transition: opacity 200ms; }
  .rl-uni-logo:hover { opacity: 0.7; }

  .rl-quote-card { transition: box-shadow 200ms; }
  .rl-quote-card:hover { box-shadow: 0 12px 48px rgba(15,40,71,0.13); }

  @media (max-width: 900px) {
    .rl-hero-split { flex-direction: column !important; }
    .rl-feat-split { flex-direction: column !important; }
    .rl-feat-split-rev { flex-direction: column !important; }
    .rl-stages-grid { grid-template-columns: repeat(3, 1fr) !important; }
    .rl-feats-grid { grid-template-columns: 1fr !important; }
    .rl-quotes-grid { grid-template-columns: 1fr !important; }
  }
  @media (max-width: 600px) {
    .rl-stages-grid { grid-template-columns: repeat(2, 1fr) !important; }
    .rl-hero-headline { font-size: 2.4rem !important; }
  }
`;

function InjectStyles() {
  return <style>{GLOBAL_CSS}</style>;
}

/* ─── Inner container ────────────────────────────────────────────────────────── */
function Inner({ children, mw = 1160 }) {
  return (
    <div style={{ maxWidth: mw, margin: "0 auto", padding: "0 32px" }}>{children}</div>
  );
}

/* ─── Eyebrow label ──────────────────────────────────────────────────────────── */
function Eyebrow({ children }) {
  return (
    <div style={{
      display: "inline-flex", alignItems: "center", gap: 6,
      fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.1em",
      textTransform: "uppercase", color: SAGE,
      padding: "5px 12px", borderRadius: 20,
      background: "rgba(74,124,89,0.08)", border: "1px solid rgba(74,124,89,0.2)",
      marginBottom: 20,
    }}>
      {children}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════════
   RESEARCH WORKSPACE MOCKUP
═══════════════════════════════════════════════════════════════════════════════ */
function ResearchMockup() {
  const [activeTab, setActiveTab] = useState(0);
  const tabs = ["Projects", "Literature", "Analysis", "Manuscript"];
  const stages = [
    { label: "Discovery",  pct: 100, color: "#10b981" },
    { label: "Review",     pct: 80,  color: "#3b82f6" },
    { label: "Design",     pct: 65,  color: "#8b5cf6" },
    { label: "Collection", pct: 40,  color: "#f59e0b" },
    { label: "Analysis",   pct: 20,  color: "#ef4444" },
  ];

  return (
    <div aria-hidden="true" style={{ width: "100%", maxWidth: 640, userSelect: "none" }}>
      {/* Outer chrome */}
      <div style={{
        background: "#040e1d",
        border: "1px solid rgba(255,255,255,0.08)",
        borderRadius: 14, overflow: "hidden",
        boxShadow: "0 48px 140px rgba(0,0,0,0.38), 0 12px 40px rgba(0,0,0,0.22)",
      }}>
        {/* Window bar */}
        <div style={{ background: "#020a16", borderBottom: "1px solid rgba(255,255,255,0.05)", padding: "9px 16px", display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ display: "flex", gap: 5 }}>
            {["#ff5f57","#febc2e","#28c840"].map((c) => (
              <div key={c} style={{ width: 9, height: 9, borderRadius: "50%", background: c }} />
            ))}
          </div>
          <div style={{ flex: 1, display: "flex", justifyContent: "center" }}>
            <div style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 5, padding: "2px 36px", fontSize: "0.6rem", color: "rgba(255,255,255,0.22)", fontFamily: "system-ui" }}>
              app.synaptiq.academy/research
            </div>
          </div>
        </div>

        {/* App layout */}
        <div style={{ display: "flex", height: 400 }}>
          {/* Sidebar */}
          <div style={{ width: 46, background: "#020a16", borderRight: "1px solid rgba(255,255,255,0.05)", display: "flex", flexDirection: "column", alignItems: "center", paddingTop: 12, gap: 10 }}>
            <div style={{ width: 26, height: 26, borderRadius: 6, background: NAVY, display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 4 }}>
              <span style={{ fontSize: 9, fontWeight: 800, color: "#fff", fontFamily: "system-ui" }}>S</span>
            </div>
            {[Folder, BookOpen, FlaskConical, BarChart3, FileText, Users].map((Icon, i) => (
              <div key={i} style={{ width: 30, height: 30, borderRadius: 7, background: i === 0 ? "rgba(255,255,255,0.08)" : "transparent", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <Icon size={12} strokeWidth={1.4} style={{ color: i === 0 ? "#93c5fd" : "rgba(255,255,255,0.2)" }} />
              </div>
            ))}
          </div>

          {/* Main panel */}
          <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
            {/* Tab row */}
            <div style={{ background: "#06121f", borderBottom: "1px solid rgba(255,255,255,0.05)", display: "flex", overflowX: "auto", scrollbarWidth: "none" }}>
              {tabs.map((t, i) => (
                <button key={t} onClick={() => setActiveTab(i)} style={{
                  padding: "8px 14px", fontSize: "0.59rem", fontWeight: 600, whiteSpace: "nowrap",
                  color: activeTab === i ? "#fff" : "rgba(255,255,255,0.28)",
                  background: activeTab === i ? "rgba(255,255,255,0.05)" : "transparent",
                  borderBottom: activeTab === i ? "2px solid #3b82f6" : "2px solid transparent",
                  border: "none", cursor: "pointer", fontFamily: "system-ui", letterSpacing: "0.04em",
                }}>
                  {t}
                </button>
              ))}
            </div>

            {/* Content */}
            <div style={{ flex: 1, padding: 16, overflowY: "auto", scrollbarWidth: "none" }}>
              {activeTab === 0 && (
                <>
                  <div style={{ fontSize: "0.58rem", color: "rgba(255,255,255,0.28)", marginBottom: 10, fontFamily: "system-ui", letterSpacing: "0.08em" }}>ACTIVE PROJECTS · 4</div>
                  {[
                    { title: "CRISPR Delivery Mechanisms", status: "Analysis", pct: 68, col: "#8b5cf6" },
                    { title: "Longitudinal Cognitive Study", status: "Collection", pct: 42, col: "#f59e0b" },
                    { title: "Climate Adaptation Survey", status: "Writing", pct: 84, col: "#10b981" },
                    { title: "mRNA Stability Research", status: "Discovery", pct: 15, col: "#3b82f6" },
                  ].map((p) => (
                    <div key={p.title} style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 8, padding: "9px 11px", marginBottom: 7 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                        <span style={{ fontSize: "0.6rem", fontWeight: 600, color: "rgba(255,255,255,0.75)", fontFamily: "system-ui" }}>{p.title}</span>
                        <span style={{ fontSize: "0.52rem", padding: "2px 6px", borderRadius: 4, background: "rgba(255,255,255,0.07)", color: "rgba(255,255,255,0.4)", fontFamily: "system-ui" }}>{p.status}</span>
                      </div>
                      <div style={{ height: 3, background: "rgba(255,255,255,0.06)", borderRadius: 2 }}>
                        <div style={{ width: `${p.pct}%`, height: 3, borderRadius: 2, background: p.col }} />
                      </div>
                    </div>
                  ))}
                </>
              )}
              {activeTab === 1 && (
                <>
                  <div style={{ fontSize: "0.58rem", color: "rgba(255,255,255,0.28)", marginBottom: 10, fontFamily: "system-ui", letterSpacing: "0.08em" }}>LITERATURE REVIEW · 1,240 papers</div>
                  {[
                    "High-efficiency lipid nanoparticle delivery of CRISPR-Cas9",
                    "Comparative analysis of viral vs non-viral delivery vectors",
                    "Off-target effects in somatic gene editing: 5-year review",
                    "In vivo mRNA stability mechanisms in mammalian cells",
                  ].map((title, i) => (
                    <div key={i} style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.05)", borderRadius: 7, padding: "8px 10px", marginBottom: 7, display: "flex", gap: 8, alignItems: "flex-start" }}>
                      <div style={{ width: 16, height: 16, borderRadius: 4, background: [  "rgba(59,130,246,0.2)","rgba(139,92,246,0.2)","rgba(16,185,129,0.2)","rgba(245,158,11,0.2)"][i], display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, marginTop: 1 }}>
                        <BookOpen size={8} style={{ color: ["#93c5fd","#c4b5fd","#6ee7b7","#fcd34d"][i] }} />
                      </div>
                      <span style={{ fontSize: "0.57rem", color: "rgba(255,255,255,0.55)", lineHeight: 1.5, fontFamily: "system-ui" }}>{title}</span>
                    </div>
                  ))}
                </>
              )}
              {activeTab === 2 && (
                <>
                  <div style={{ fontSize: "0.58rem", color: "rgba(255,255,255,0.28)", marginBottom: 10, fontFamily: "system-ui", letterSpacing: "0.08em" }}>STATISTICAL ANALYSIS · CRISPR Study</div>
                  {stages.map((s) => (
                    <div key={s.label} style={{ marginBottom: 9 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                        <span style={{ fontSize: "0.57rem", color: "rgba(255,255,255,0.45)", fontFamily: "system-ui" }}>{s.label}</span>
                        <span style={{ fontSize: "0.57rem", fontWeight: 700, color: "rgba(255,255,255,0.7)", fontFamily: "system-ui" }}>{s.pct}%</span>
                      </div>
                      <div style={{ height: 4, background: "rgba(255,255,255,0.06)", borderRadius: 2 }}>
                        <div style={{ width: `${s.pct}%`, height: 4, borderRadius: 2, background: s.color }} />
                      </div>
                    </div>
                  ))}
                </>
              )}
              {activeTab === 3 && (
                <>
                  <div style={{ fontSize: "0.58rem", color: "rgba(255,255,255,0.28)", marginBottom: 10, fontFamily: "system-ui", letterSpacing: "0.08em" }}>MANUSCRIPT DRAFT · v1.4</div>
                  {["Abstract", "Introduction", "Methodology", "Results", "Discussion", "References"].map((s, i) => (
                    <div key={s} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 8px", background: i === 2 ? "rgba(59,130,246,0.08)" : "transparent", borderRadius: 6, marginBottom: 3 }}>
                      <div style={{ width: 5, height: 5, borderRadius: "50%", background: [  "#10b981","#10b981","#3b82f6","#f59e0b","#f59e0b","#94a3b8"][i] }} />
                      <span style={{ fontSize: "0.6rem", color: i === 2 ? "#93c5fd" : "rgba(255,255,255,0.5)", fontFamily: "system-ui", fontWeight: i === 2 ? 600 : 400 }}>{s}</span>
                      <span style={{ marginLeft: "auto", fontSize: "0.52rem", color: "rgba(255,255,255,0.25)", fontFamily: "system-ui" }}>{["✓","✓","editing","draft","draft","—"][i]}</span>
                    </div>
                  ))}
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════════
   FEATURE MOCKUPS (for alternating sections)
═══════════════════════════════════════════════════════════════════════════════ */
function ProjectsMockup() {
  return (
    <div aria-hidden="true" style={{ width: "100%", maxWidth: 520, userSelect: "none" }}>
      <div style={{ background: "#040e1d", borderRadius: 12, overflow: "hidden", border: "1px solid rgba(255,255,255,0.07)", boxShadow: "0 24px 80px rgba(0,0,0,0.3), 0 6px 20px rgba(0,0,0,0.18)" }}>
        <div style={{ background: "#020a16", borderBottom: "1px solid rgba(255,255,255,0.05)", padding: "8px 14px", display: "flex", alignItems: "center", gap: 6 }}>
          <div style={{ display: "flex", gap: 4 }}>{["#ff5f57","#febc2e","#28c840"].map((c) => <div key={c} style={{ width: 8, height: 8, borderRadius: "50%", background: c }} />)}</div>
          <span style={{ fontSize: "0.58rem", color: "rgba(255,255,255,0.2)", marginLeft: 8, fontFamily: "system-ui" }}>Projects — CRISPR Delivery</span>
        </div>
        <div style={{ padding: 16 }}>
          <div style={{ fontSize: "0.58rem", color: "rgba(255,255,255,0.25)", letterSpacing: "0.08em", marginBottom: 10, fontFamily: "system-ui" }}>WORKSPACE OVERVIEW</div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8, marginBottom: 12 }}>
            {[{ v: "6", l: "Team members" }, { v: "1,240", l: "Sources indexed" }, { v: "847", l: "Notes created" }, { v: "3", l: "Manuscripts" }].map((s) => (
              <div key={s.l} style={{ background: "rgba(255,255,255,0.04)", borderRadius: 8, padding: "10px 12px", border: "1px solid rgba(255,255,255,0.06)" }}>
                <div style={{ fontSize: "0.9rem", fontWeight: 700, color: "#fff", fontFamily: "system-ui" }}>{s.v}</div>
                <div style={{ fontSize: "0.55rem", color: "rgba(255,255,255,0.35)", fontFamily: "system-ui" }}>{s.l}</div>
              </div>
            ))}
          </div>
          <div style={{ fontSize: "0.58rem", color: "rgba(255,255,255,0.25)", letterSpacing: "0.08em", marginBottom: 8, fontFamily: "system-ui" }}>RECENT ACTIVITY</div>
          {[
            { user: "Dr. Chen", action: "Uploaded dataset: CRISPR-Cas9 efficacy", time: "2m ago", col: "#60a5fa" },
            { user: "Dr. Patel", action: "Added 12 papers to literature review", time: "1h ago", col: "#a78bfa" },
            { user: "Prof. Kim", action: "Commented on methodology section", time: "3h ago", col: "#34d399" },
          ].map((a) => (
            <div key={a.user} style={{ display: "flex", gap: 8, alignItems: "flex-start", marginBottom: 8 }}>
              <div style={{ width: 18, height: 18, borderRadius: "50%", background: a.col + "30", border: `1px solid ${a.col}50`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                <span style={{ fontSize: "0.5rem", color: a.col, fontWeight: 700, fontFamily: "system-ui" }}>{a.user[3]}</span>
              </div>
              <div>
                <span style={{ fontSize: "0.56rem", color: "rgba(255,255,255,0.6)", fontFamily: "system-ui" }}><strong style={{ color: "rgba(255,255,255,0.8)", fontWeight: 600 }}>{a.user}</strong> {a.action}</span>
                <div style={{ fontSize: "0.5rem", color: "rgba(255,255,255,0.25)", fontFamily: "system-ui" }}>{a.time}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function ImpactMockup() {
  return (
    <div aria-hidden="true" style={{ width: "100%", maxWidth: 520, userSelect: "none" }}>
      <div style={{ background: "#040e1d", borderRadius: 12, overflow: "hidden", border: "1px solid rgba(255,255,255,0.07)", boxShadow: "0 24px 80px rgba(0,0,0,0.3), 0 6px 20px rgba(0,0,0,0.18)" }}>
        <div style={{ background: "#020a16", borderBottom: "1px solid rgba(255,255,255,0.05)", padding: "8px 14px", display: "flex", alignItems: "center", gap: 6 }}>
          <div style={{ display: "flex", gap: 4 }}>{["#ff5f57","#febc2e","#28c840"].map((c) => <div key={c} style={{ width: 8, height: 8, borderRadius: "50%", background: c }} />)}</div>
          <span style={{ fontSize: "0.58rem", color: "rgba(255,255,255,0.2)", marginLeft: 8, fontFamily: "system-ui" }}>Research Impact · h-index dashboard</span>
        </div>
        <div style={{ padding: 16 }}>
          <div style={{ display: "flex", gap: 10, marginBottom: 14 }}>
            {[{ v: "h-31", l: "h-index", col: "#3b82f6" }, { v: "2,840", l: "Citations", col: "#10b981" }, { v: "92", l: "SIS Score", col: "#8b5cf6" }].map((s) => (
              <div key={s.l} style={{ flex: 1, background: "rgba(255,255,255,0.04)", borderRadius: 8, padding: "10px", border: "1px solid rgba(255,255,255,0.06)", textAlign: "center" }}>
                <div style={{ fontSize: "0.85rem", fontWeight: 700, color: s.col, fontFamily: "system-ui" }}>{s.v}</div>
                <div style={{ fontSize: "0.52rem", color: "rgba(255,255,255,0.3)", fontFamily: "system-ui" }}>{s.l}</div>
              </div>
            ))}
          </div>
          <div style={{ fontSize: "0.56rem", color: "rgba(255,255,255,0.25)", letterSpacing: "0.08em", marginBottom: 8, fontFamily: "system-ui" }}>CITATIONS OVER TIME</div>
          <div style={{ display: "flex", alignItems: "flex-end", gap: 3, height: 60, marginBottom: 12 }}>
            {[12,18,22,19,28,35,42,38,52,61,58,74,88,92,84,96].map((v, i) => (
              <div key={i} style={{ flex: 1, background: `rgba(59,130,246,${0.2 + (v/120)*0.7})`, borderRadius: "2px 2px 0 0", height: `${(v/96)*100}%` }} />
            ))}
          </div>
          <div style={{ fontSize: "0.56rem", color: "rgba(255,255,255,0.25)", letterSpacing: "0.08em", marginBottom: 8, fontFamily: "system-ui" }}>FIELD PERCENTILE</div>
          <div style={{ height: 4, background: "rgba(255,255,255,0.06)", borderRadius: 2 }}>
            <div style={{ width: "92%", height: 4, background: "linear-gradient(90deg, #3b82f6, #8b5cf6)", borderRadius: 2 }} />
          </div>
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4 }}>
            <span style={{ fontSize: "0.5rem", color: "rgba(255,255,255,0.2)", fontFamily: "system-ui" }}>0</span>
            <span style={{ fontSize: "0.5rem", color: "#8b5cf6", fontFamily: "system-ui", fontWeight: 600 }}>Top 8%</span>
            <span style={{ fontSize: "0.5rem", color: "rgba(255,255,255,0.2)", fontFamily: "system-ui" }}>100</span>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════════
   HERO
═══════════════════════════════════════════════════════════════════════════════ */
function HeroSection() {
  return (
    <section style={{ background: "#fff", paddingTop: 96, paddingBottom: 0, position: "relative", overflow: "hidden" }}>
      {/* Background tint */}
      <div style={{ position: "absolute", inset: 0, background: "radial-gradient(ellipse 900px 500px at 50% -60px, rgba(15,40,71,0.05) 0%, transparent 70%)", pointerEvents: "none" }} />
      <Inner>
        {/* Top label */}
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <Eyebrow>Research Platform</Eyebrow>
        </div>

        {/* Headline */}
        <h1
          className="rl-hero-headline"
          style={{
            fontFamily: "Georgia, 'Times New Roman', serif",
            fontSize: "clamp(2.6rem, 5vw, 4rem)",
            fontWeight: 700,
            color: "#0c1a2e",
            textAlign: "center",
            lineHeight: 1.12,
            letterSpacing: "-0.03em",
            margin: "0 auto 20px",
            maxWidth: 800,
          }}
        >
          Research without<br />fragmentation.
        </h1>

        <p style={{
          textAlign: "center", fontSize: "1.1rem", color: SLATE,
          lineHeight: 1.75, maxWidth: 560, margin: "0 auto 36px", fontWeight: 400,
        }}>
          One workspace for every stage of academic research — from first search to final publication and beyond.
        </p>

        {/* CTAs */}
        <div style={{ display: "flex", justifyContent: "center", gap: 12, marginBottom: 60 }}>
          <Link
            to="/register"
            className="rl-cta-btn"
            style={{
              display: "inline-flex", alignItems: "center", gap: 8,
              padding: "14px 28px", borderRadius: 10,
              background: NAVY, color: "#fff",
              fontSize: "0.9rem", fontWeight: 600, textDecoration: "none",
              letterSpacing: "-0.01em",
            }}
          >
            Get Started <ArrowRight size={15} />
          </Link>
          <Link
            to="/pricing"
            className="rl-secondary-btn"
            style={{
              display: "inline-flex", alignItems: "center", gap: 8,
              padding: "14px 28px", borderRadius: 10,
              background: "#fff", color: NAVY,
              border: `1.5px solid ${BORDER}`,
              fontSize: "0.9rem", fontWeight: 600, textDecoration: "none",
              letterSpacing: "-0.01em",
            }}
          >
            See Pricing
          </Link>
        </div>

        {/* Product mockup */}
        <div style={{ display: "flex", justifyContent: "center", padding: "0 0 0" }}>
          <div style={{ width: "100%", maxWidth: 860, position: "relative" }}>
            <div style={{ position: "absolute", inset: 0, background: "linear-gradient(to bottom, transparent 60%, #fff 100%)", zIndex: 2, borderRadius: 14, pointerEvents: "none" }} />
            <div style={{ borderRadius: 14, overflow: "hidden", border: "1px solid rgba(0,0,0,0.08)", boxShadow: "0 60px 160px rgba(0,0,0,0.22), 0 12px 48px rgba(0,0,0,0.12)" }}>
              {/* Browser chrome */}
              <div style={{ background: "#f1f4f8", borderBottom: "1px solid #e2e6ed", padding: "9px 16px", display: "flex", alignItems: "center", gap: 8 }}>
                <div style={{ display: "flex", gap: 5 }}>{["#ff5f57","#febc2e","#28c840"].map((c) => <div key={c} style={{ width: 9, height: 9, borderRadius: "50%", background: c }} />)}</div>
                <div style={{ flex: 1, display: "flex", justifyContent: "center" }}>
                  <div style={{ background: "#fff", border: "1px solid #dde2e8", borderRadius: 5, padding: "3px 36px", fontSize: "0.6rem", color: "#94a3b8", fontFamily: "system-ui" }}>
                    app.synaptiq.academy/research
                  </div>
                </div>
              </div>
              {/* App layout preview — light mode */}
              <div style={{ background: "#fff", display: "flex", height: 320 }}>
                {/* Left nav */}
                <div style={{ width: 200, background: "#f8fafb", borderRight: "1px solid #eef1f5", padding: "14px 0" }}>
                  <div style={{ padding: "0 14px", marginBottom: 14 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      <div style={{ width: 22, height: 22, borderRadius: 5, background: NAVY, display: "flex", alignItems: "center", justifyContent: "center" }}>
                        <span style={{ fontSize: 8, fontWeight: 800, color: "#fff", fontFamily: "system-ui" }}>S</span>
                      </div>
                      <span style={{ fontSize: "0.65rem", fontWeight: 700, color: "#0f172a", fontFamily: "system-ui" }}>Synaptiq</span>
                    </div>
                  </div>
                  {[
                    { label: "Projects",          active: true  },
                    { label: "Literature Review", active: false },
                    { label: "Research Notes",    active: false },
                    { label: "Collaborations",    active: false },
                    { label: "Manuscripts",       active: false },
                    { label: "Research Impact",   active: false },
                    { label: "AI Workspace",      active: false },
                  ].map((item) => (
                    <div key={item.label} style={{
                      padding: "5px 14px", fontSize: "0.6rem", fontFamily: "system-ui",
                      color: item.active ? NAVY : "#64748b",
                      background: item.active ? "rgba(15,40,71,0.06)" : "transparent",
                      fontWeight: item.active ? 600 : 400,
                      borderLeft: item.active ? `2px solid ${NAVY}` : "2px solid transparent",
                    }}>
                      {item.label}
                    </div>
                  ))}
                </div>

                {/* Main content */}
                <div style={{ flex: 1, padding: 20, overflowY: "auto", scrollbarWidth: "none" }}>
                  <div style={{ fontSize: "0.62rem", fontWeight: 700, color: "#0f172a", fontFamily: "system-ui", marginBottom: 4 }}>My Research Projects</div>
                  <div style={{ fontSize: "0.56rem", color: "#94a3b8", marginBottom: 14, fontFamily: "system-ui" }}>4 active · 2 completed</div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                    {[
                      { name: "CRISPR Delivery", field: "Molecular Biology", stage: "Analysis", pct: 68 },
                      { name: "Cognitive Study",  field: "Neuroscience",      stage: "Collection", pct: 42 },
                      { name: "Climate Survey",   field: "Environmental Sci.", stage: "Writing", pct: 84 },
                      { name: "mRNA Stability",   field: "Biochemistry",       stage: "Discovery", pct: 15 },
                    ].map((p) => (
                      <div key={p.name} style={{ background: "#f8fafb", border: "1px solid #eef1f5", borderRadius: 8, padding: "10px 12px" }}>
                        <div style={{ fontSize: "0.6rem", fontWeight: 600, color: "#0f172a", fontFamily: "system-ui", marginBottom: 2 }}>{p.name}</div>
                        <div style={{ fontSize: "0.53rem", color: "#94a3b8", fontFamily: "system-ui", marginBottom: 8 }}>{p.field}</div>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 5 }}>
                          <span style={{ fontSize: "0.5rem", color: NAVY, fontFamily: "system-ui", fontWeight: 600 }}>{p.stage}</span>
                          <span style={{ fontSize: "0.5rem", color: "#64748b", fontFamily: "system-ui" }}>{p.pct}%</span>
                        </div>
                        <div style={{ height: 3, background: "#e2e8f0", borderRadius: 2 }}>
                          <div style={{ width: `${p.pct}%`, height: 3, background: NAVY, borderRadius: 2, opacity: 0.7 }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </Inner>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════════
   TRUSTED BY RESEARCHERS
═══════════════════════════════════════════════════════════════════════════════ */
function TrustedSection() {
  const ref = useReveal();
  const unis = [
    "MIT", "Stanford", "Oxford", "Cambridge", "Harvard",
    "ETH Zürich", "Toronto", "Sorbonne", "NUS", "TU Delft",
  ];
  return (
    <section style={{ background: LIGHT, padding: "48px 0" }}>
      <Inner>
        <div ref={ref} className="rl-fade" style={{ textAlign: "center" }}>
          <div style={{ fontSize: "0.72rem", fontWeight: 600, color: "#94a3b8", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 28 }}>
            Trusted by researchers at leading institutions
          </div>
          <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: "16px 36px", alignItems: "center" }}>
            {unis.map((u) => (
              <div
                key={u}
                className="rl-uni-logo"
                style={{ fontSize: "0.85rem", fontWeight: 700, color: "#94a3b8", fontFamily: "Georgia, serif", letterSpacing: "-0.01em", opacity: 0.55 }}
              >
                {u}
              </div>
            ))}
          </div>
        </div>
      </Inner>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════════
   RESEARCH LIFECYCLE TIMELINE
═══════════════════════════════════════════════════════════════════════════════ */
const LIFECYCLE_STAGES = [
  { icon: Search,       label: "Discover",       desc: "Find research opportunities and gaps through intelligent discovery tools.", color: "#3b82f6" },
  { icon: BookOpen,     label: "Review",          desc: "Synthesize literature from 100M+ papers across all major databases.", color: "#8b5cf6" },
  { icon: FlaskConical, label: "Design",          desc: "Build rigorous study designs with AI-powered methodology guidance.", color: "#ec4899" },
  { icon: Database,     label: "Collect data",    desc: "Organize, annotate, and store research data in one secure place.", color: "#f59e0b" },
  { icon: BarChart3,    label: "Analyze",         desc: "Run statistical analysis and visualize results with precision.", color: "#10b981" },
  { icon: FileText,     label: "Write",           desc: "Draft manuscripts with real-time co-authoring and version control.", color: "#06b6d4" },
  { icon: Users,        label: "Collaborate",     desc: "Invite co-investigators and share data across your institution.", color: "#f97316" },
  { icon: Globe,        label: "Publish",         desc: "Match your work to top journals and navigate peer review.", color: "#6366f1" },
  { icon: TrendingUp,   label: "Measure impact",  desc: "Track citations, h-index, and field influence over time.", color: "#84cc16" },
];

function LifecycleSection() {
  const [active, setActive] = useState(0);
  const ref = useReveal();
  const stage = LIFECYCLE_STAGES[active];
  return (
    <section style={{ background: "#fff", padding: "100px 0" }}>
      <Inner>
        <div ref={ref} className="rl-fade" style={{ textAlign: "center", marginBottom: 60 }}>
          <Eyebrow>Complete lifecycle</Eyebrow>
          <h2 style={{ fontFamily: "Georgia, serif", fontSize: "clamp(2rem, 3.5vw, 2.8rem)", fontWeight: 700, color: "#0c1a2e", lineHeight: 1.2, letterSpacing: "-0.02em", margin: "0 0 16px" }}>
            Every stage of research,<br />in one place.
          </h2>
          <p style={{ fontSize: "1rem", color: SLATE, maxWidth: 520, margin: "0 auto" }}>
            From the first literature search to tracking your citation impact — Synaptiq covers the entire research lifecycle without switching tools.
          </p>
        </div>

        {/* Stage pills */}
        <div style={{ display: "flex", flexWrap: "wrap", justifyContent: "center", gap: 8, marginBottom: 48 }}>
          {LIFECYCLE_STAGES.map((s, i) => (
            <button
              key={s.label}
              onClick={() => setActive(i)}
              style={{
                display: "inline-flex", alignItems: "center", gap: 6,
                padding: "8px 16px", borderRadius: 20,
                background: active === i ? NAVY : "#fff",
                color: active === i ? "#fff" : SLATE,
                border: `1.5px solid ${active === i ? NAVY : BORDER}`,
                fontSize: "0.78rem", fontWeight: 600, cursor: "pointer",
                transition: "all 150ms", fontFamily: "inherit",
              }}
            >
              <s.icon size={13} strokeWidth={1.6} />
              {s.label}
            </button>
          ))}
        </div>

        {/* Active stage detail */}
        <div style={{ background: LIGHT, border: `1px solid ${BORDER}`, borderRadius: 16, padding: "40px 48px", display: "flex", alignItems: "center", gap: 40, flexWrap: "wrap" }}>
          <div style={{ width: 64, height: 64, borderRadius: 16, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0, background: stage.color + "18" }}>
            <stage.icon size={28} strokeWidth={1.4} style={{ color: stage.color }} />
          </div>
          <div style={{ flex: 1, minWidth: 220 }}>
            <div style={{ fontSize: "0.62rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "#94a3b8", marginBottom: 6 }}>Stage {active + 1} of {LIFECYCLE_STAGES.length}</div>
            <h3 style={{ fontFamily: "Georgia, serif", fontSize: "1.6rem", fontWeight: 700, color: "#0c1a2e", margin: "0 0 10px", letterSpacing: "-0.02em" }}>{stage.label}</h3>
            <p style={{ fontSize: "0.95rem", color: SLATE, lineHeight: 1.7, margin: 0 }}>{stage.desc}</p>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 6, minWidth: 180 }}>
            {["No tool-switching", "AI-assisted at every step", "Fully integrated"].map((f) => (
              <div key={f} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <CheckCircle2 size={14} strokeWidth={2} style={{ color: SAGE, flexShrink: 0 }} />
                <span style={{ fontSize: "0.8rem", color: BODY }}>{f}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Stage grid */}
        <div className="rl-stages-grid" style={{ display: "grid", gridTemplateColumns: "repeat(9, 1fr)", gap: 6, marginTop: 20 }}>
          {LIFECYCLE_STAGES.map((s, i) => (
            <button
              key={s.label}
              onClick={() => setActive(i)}
              className="rl-stage-card"
              style={{
                background: active === i ? "#fff" : "#f8fafb",
                border: `1px solid ${active === i ? NAVY : BORDER}`,
                borderRadius: 8, padding: "10px 6px", textAlign: "center", cursor: "pointer",
                fontFamily: "inherit",
              }}
            >
              <s.icon size={15} strokeWidth={1.5} style={{ color: active === i ? NAVY : "#94a3b8", display: "block", margin: "0 auto 5px" }} />
              <div style={{ fontSize: "0.55rem", fontWeight: 600, color: active === i ? NAVY : "#94a3b8" }}>{s.label}</div>
            </button>
          ))}
        </div>
      </Inner>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════════
   FEATURE SECTIONS (alternating)
═══════════════════════════════════════════════════════════════════════════════ */
const FEATURES = [
  {
    eyebrow: "Projects",
    title: "A home for every research project.",
    body: "Each project gets its own workspace — team, literature, data, notes, and manuscripts all in one place. No more scattered folders or lost context.",
    points: ["Shared team workspace", "Version-controlled documents", "Unlimited project members"],
    mockup: "projects",
    reverse: false,
  },
  {
    eyebrow: "Research Impact",
    title: "Know exactly where you stand in your field.",
    body: "Track your h-index, citation count, and field percentile in real time. Understand which of your papers drive the most influence and where your next breakthrough should come from.",
    points: ["Live citation tracking", "Field benchmarking", "h-index forecasting"],
    mockup: "impact",
    reverse: true,
  },
  {
    eyebrow: "Collaborations",
    title: "Research is a team sport.",
    body: "Invite co-investigators from any institution, assign roles, share documents securely, and co-author in real time. Every collaboration is tracked, versioned, and attributable.",
    points: ["Cross-institution invites", "Real-time co-authoring", "Contribution tracking"],
    mockup: null,
    reverse: false,
  },
];

function FeatureSection({ feature }) {
  const ref = useReveal();
  return (
    <section style={{ background: feature.reverse ? LIGHT : "#fff", padding: "90px 0" }}>
      <Inner>
        <div
          ref={ref}
          className={`rl-fade rl-feat-split${feature.reverse ? "-rev" : ""}`}
          style={{
            display: "flex",
            flexDirection: feature.reverse ? "row-reverse" : "row",
            alignItems: "center",
            gap: 72,
          }}
        >
          {/* Text */}
          <div style={{ flex: 1, minWidth: 280 }}>
            <Eyebrow>{feature.eyebrow}</Eyebrow>
            <h2 style={{ fontFamily: "Georgia, serif", fontSize: "clamp(1.7rem, 3vw, 2.4rem)", fontWeight: 700, color: "#0c1a2e", lineHeight: 1.2, letterSpacing: "-0.02em", margin: "0 0 18px" }}>
              {feature.title}
            </h2>
            <p style={{ fontSize: "1rem", color: SLATE, lineHeight: 1.75, marginBottom: 28 }}>{feature.body}</p>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {feature.points.map((p) => (
                <div key={p} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <CheckCircle2 size={16} strokeWidth={2} style={{ color: SAGE, flexShrink: 0 }} />
                  <span style={{ fontSize: "0.875rem", color: BODY, fontWeight: 500 }}>{p}</span>
                </div>
              ))}
            </div>
            <Link
              to="/register"
              style={{ display: "inline-flex", alignItems: "center", gap: 6, marginTop: 28, fontSize: "0.875rem", fontWeight: 600, color: NAVY, textDecoration: "none" }}
            >
              Get started <ArrowRight size={14} />
            </Link>
          </div>

          {/* Visual */}
          <div style={{ flex: 1, display: "flex", justifyContent: "center" }}>
            {feature.mockup === "projects" && <ProjectsMockup />}
            {feature.mockup === "impact"   && <ImpactMockup />}
            {feature.mockup === null && (
              <div style={{ width: "100%", maxWidth: 480, background: LIGHT, border: `1px solid ${BORDER}`, borderRadius: 16, padding: 36 }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
                  {[
                    { initial: "LC", name: "Dr. L. Chen", role: "Co-PI", color: "#3b82f6" },
                    { initial: "SP", name: "Dr. S. Patel", role: "Researcher", color: "#8b5cf6" },
                    { initial: "MK", name: "Prof. M. Kim", role: "Supervisor", color: "#10b981" },
                    { initial: "AJ", name: "Dr. A. Jones", role: "Data Analyst", color: "#f59e0b" },
                  ].map((m) => (
                    <div key={m.initial} style={{ background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 10, padding: "14px", display: "flex", alignItems: "center", gap: 10 }}>
                      <div style={{ width: 34, height: 34, borderRadius: "50%", background: m.color + "20", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                        <span style={{ fontSize: "0.65rem", fontWeight: 700, color: m.color }}>{m.initial}</span>
                      </div>
                      <div>
                        <div style={{ fontSize: "0.62rem", fontWeight: 600, color: "#0f172a" }}>{m.name}</div>
                        <div style={{ fontSize: "0.55rem", color: "#94a3b8" }}>{m.role}</div>
                      </div>
                    </div>
                  ))}
                </div>
                <div style={{ marginTop: 16, padding: "12px 14px", background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 10 }}>
                  <div style={{ fontSize: "0.6rem", fontWeight: 700, color: NAVY, marginBottom: 8 }}>Collaboration Activity</div>
                  {["Dr. Chen shared a dataset", "Prof. Kim commented on §3.2", "Dr. Jones updated analysis"].map((a, i) => (
                    <div key={i} style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 6, paddingBottom: 6, borderBottom: i < 2 ? `1px solid ${BORDER}` : "none" }}>
                      <div style={{ width: 5, height: 5, borderRadius: "50%", background: SAGE, flexShrink: 0 }} />
                      <span style={{ fontSize: "0.57rem", color: SLATE }}>{a}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </Inner>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════════
   ALL FEATURES GRID
═══════════════════════════════════════════════════════════════════════════════ */
const ALL_FEATURES = [
  { icon: Folder,       title: "Projects",            desc: "Dedicated workspaces for every research endeavor." },
  { icon: BookMarked,   title: "Repository",           desc: "Centralized library for all your papers and sources." },
  { icon: MessageSquare,title: "Research Notes",       desc: "Annotate, synthesize, and link ideas as you read." },
  { icon: GitBranch,    title: "Version History",      desc: "Track every change across documents and datasets." },
  { icon: Network,      title: "Research Workspaces",  desc: "Shared environments for entire research groups." },
  { icon: FileText,     title: "Publications",         desc: "Manage submissions, revisions, and publication records." },
  { icon: TrendingUp,   title: "Research Impact",      desc: "Live h-index, citation analytics, and field ranking." },
  { icon: Users,        title: "Collaborations",       desc: "Invite, manage, and track cross-institution teams." },
];

function AllFeaturesSection() {
  const ref = useReveal();
  return (
    <section style={{ background: NAVY, padding: "100px 0" }}>
      <Inner>
        <div ref={ref} className="rl-fade" style={{ textAlign: "center", marginBottom: 56 }}>
          <div style={{ fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "rgba(255,255,255,0.35)", marginBottom: 16 }}>Everything in one platform</div>
          <h2 style={{ fontFamily: "Georgia, serif", fontSize: "clamp(1.8rem, 3vw, 2.6rem)", fontWeight: 700, color: "#fff", lineHeight: 1.2, letterSpacing: "-0.02em", margin: "0 0 16px" }}>
            Every tool your research requires.
          </h2>
          <p style={{ fontSize: "1rem", color: "rgba(255,255,255,0.55)", maxWidth: 480, margin: "0 auto" }}>
            Stop paying for five different tools and managing them across browser tabs.
          </p>
        </div>

        <div className="rl-feats-grid" style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
          {ALL_FEATURES.map((f, i) => (
            <div
              key={f.title}
              className={`rl-fade rl-fade-d${Math.min(i % 4 + 1, 4)}`}
              style={{ background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 12, padding: "24px 22px", transition: "background 180ms" }}
              onMouseEnter={(e) => { e.currentTarget.style.background = "rgba(255,255,255,0.09)"; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = "rgba(255,255,255,0.05)"; }}
            >
              <div style={{ width: 40, height: 40, borderRadius: 10, background: "rgba(255,255,255,0.08)", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 14 }}>
                <f.icon size={18} strokeWidth={1.4} style={{ color: "rgba(255,255,255,0.75)" }} />
              </div>
              <div style={{ fontSize: "0.875rem", fontWeight: 600, color: "#fff", marginBottom: 6 }}>{f.title}</div>
              <div style={{ fontSize: "0.78rem", color: "rgba(255,255,255,0.45)", lineHeight: 1.6 }}>{f.desc}</div>
            </div>
          ))}
        </div>
      </Inner>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════════
   WORKFLOW SECTION (large screenshots)
═══════════════════════════════════════════════════════════════════════════════ */
function WorkflowSection() {
  const ref = useReveal();
  return (
    <section style={{ background: "#fff", padding: "100px 0" }}>
      <Inner>
        <div ref={ref} className="rl-fade" style={{ textAlign: "center", marginBottom: 56 }}>
          <Eyebrow>How researchers work</Eyebrow>
          <h2 style={{ fontFamily: "Georgia, serif", fontSize: "clamp(1.8rem, 3vw, 2.6rem)", fontWeight: 700, color: "#0c1a2e", lineHeight: 1.2, letterSpacing: "-0.02em", margin: "0 0 16px" }}>
            One day in the life of a Synaptiq researcher.
          </h2>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          {[
            { time: "08:30", label: "Morning: Literature Review", desc: "Start the day with AI-curated papers ranked by relevance to your research questions. Annotate, highlight, and save to your repository.", bg: "#EFF6FF", accent: "#3b82f6" },
            { time: "10:00", label: "Mid-morning: Analysis", desc: "Run statistical models on your dataset. Synaptiq checks your methodology and flags potential issues before you submit.", bg: "#ECFDF5", accent: "#10b981" },
            { time: "14:00", label: "Afternoon: Writing", desc: "Draft your manuscript with live section-by-section feedback. Your co-authors contribute in real time, with every change tracked.", bg: "#F5F3FF", accent: "#8b5cf6" },
            { time: "17:00", label: "End of day: Collaborate", desc: "Review your team's contributions, leave comments, and assign next steps. All in the same workspace as your data and writing.", bg: "#FFF7ED", accent: "#f97316" },
          ].map((step, i) => {
            const stepRef = useReveal();
            return (
              <div key={step.time} ref={stepRef} className={`rl-fade rl-fade-d${i + 1}`} style={{ background: step.bg, border: `1px solid ${BORDER}`, borderRadius: 14, padding: "28px 32px", display: "flex", gap: 28, alignItems: "center", flexWrap: "wrap" }}>
                <div style={{ minWidth: 80 }}>
                  <div style={{ fontSize: "0.62rem", color: "#94a3b8", fontWeight: 600, marginBottom: 4 }}>TODAY</div>
                  <div style={{ fontSize: "1.1rem", fontWeight: 700, color: step.accent, fontFamily: "system-ui, monospace" }}>{step.time}</div>
                </div>
                <div style={{ width: 1, height: 48, background: BORDER, flexShrink: 0 }} />
                <div style={{ flex: 1, minWidth: 200 }}>
                  <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "#0f172a", marginBottom: 6 }}>{step.label}</div>
                  <div style={{ fontSize: "0.84rem", color: SLATE, lineHeight: 1.65 }}>{step.desc}</div>
                </div>
                <div style={{ padding: "5px 12px", borderRadius: 20, background: step.accent + "18", border: `1px solid ${step.accent}30` }}>
                  <span style={{ fontSize: "0.65rem", fontWeight: 700, color: step.accent }}>{["Literature","Analysis","Manuscript","Collaboration"][i]}</span>
                </div>
              </div>
            );
          })}
        </div>
      </Inner>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════════
   TESTIMONIALS
═══════════════════════════════════════════════════════════════════════════════ */
const TESTIMONIALS = [
  {
    quote: "Synaptiq eliminated the gap between reading a paper and actually using it in my work. Everything I annotate shows up exactly where I need it.",
    name: "Dr. Fatima Al-Rashid",
    title: "Associate Professor of Molecular Biology",
    institution: "King's College London",
    stars: 5,
  },
  {
    quote: "I used to switch between seven different tools to manage one project. Now everything — collaborators, data, literature, and my manuscript — lives in one place.",
    name: "Prof. James Osei",
    title: "Principal Investigator, Computational Neuroscience",
    institution: "University of Toronto",
    stars: 5,
  },
  {
    quote: "The research impact dashboard helped me realize one of my 2019 papers was gaining unexpected traction in clinical circles. That insight shaped my next grant application.",
    name: "Dr. Mei-Ling Tan",
    title: "Senior Research Fellow",
    institution: "National University of Singapore",
    stars: 5,
  },
];

function TestimonialsSection() {
  const ref = useReveal();
  return (
    <section style={{ background: LIGHT, padding: "100px 0" }}>
      <Inner>
        <div ref={ref} className="rl-fade" style={{ textAlign: "center", marginBottom: 52 }}>
          <Eyebrow>From researchers</Eyebrow>
          <h2 style={{ fontFamily: "Georgia, serif", fontSize: "clamp(1.8rem, 3vw, 2.4rem)", fontWeight: 700, color: "#0c1a2e", letterSpacing: "-0.02em", margin: 0 }}>
            What researchers say.
          </h2>
        </div>

        <div className="rl-quotes-grid" style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 20 }}>
          {TESTIMONIALS.map((t, i) => (
            <div
              key={t.name}
              className={`rl-fade rl-fade-d${i + 1} rl-quote-card`}
              style={{ background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 14, padding: "28px 28px" }}
            >
              <div style={{ display: "flex", gap: 3, marginBottom: 16 }}>
                {Array(t.stars).fill(0).map((_, j) => (
                  <Star key={j} size={13} fill="#f59e0b" style={{ color: "#f59e0b" }} />
                ))}
              </div>
              <p style={{ fontSize: "0.9rem", color: BODY, lineHeight: 1.75, marginBottom: 24, fontStyle: "italic" }}>
                "{t.quote}"
              </p>
              <div style={{ display: "flex", alignItems: "center", gap: 12, paddingTop: 20, borderTop: `1px solid ${BORDER}` }}>
                <div style={{ width: 38, height: 38, borderRadius: "50%", background: NAVY + "18", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                  <span style={{ fontSize: "0.72rem", fontWeight: 700, color: NAVY }}>{t.name.split(" ").map((w) => w[0]).slice(0, 2).join("")}</span>
                </div>
                <div>
                  <div style={{ fontSize: "0.78rem", fontWeight: 700, color: "#0f172a" }}>{t.name}</div>
                  <div style={{ fontSize: "0.68rem", color: "#94a3b8" }}>{t.title}</div>
                  <div style={{ fontSize: "0.65rem", color: SAGE, fontWeight: 600 }}>{t.institution}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Inner>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════════
   FINAL CTA
═══════════════════════════════════════════════════════════════════════════════ */
function CTASection() {
  const ref = useReveal();
  return (
    <section style={{ background: NAVY, padding: "120px 0" }}>
      <Inner>
        <div ref={ref} className="rl-fade" style={{ textAlign: "center" }}>
          <div style={{ fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "rgba(255,255,255,0.35)", marginBottom: 20 }}>Start today</div>
          <h2 style={{ fontFamily: "Georgia, serif", fontSize: "clamp(2rem, 4vw, 3.2rem)", fontWeight: 700, color: "#fff", lineHeight: 1.12, letterSpacing: "-0.025em", margin: "0 0 20px", maxWidth: 600, marginLeft: "auto", marginRight: "auto" }}>
            Start your next research project.
          </h2>
          <p style={{ fontSize: "1.05rem", color: "rgba(255,255,255,0.55)", maxWidth: 440, margin: "0 auto 40px", lineHeight: 1.7 }}>
            Join thousands of researchers who manage their entire academic career in Synaptiq.
          </p>
          <div style={{ display: "flex", justifyContent: "center", gap: 12, flexWrap: "wrap" }}>
            <Link
              to="/register"
              className="rl-cta-btn"
              style={{
                display: "inline-flex", alignItems: "center", gap: 8,
                padding: "15px 30px", borderRadius: 10,
                background: "#fff", color: NAVY,
                fontSize: "0.9rem", fontWeight: 700, textDecoration: "none",
                letterSpacing: "-0.01em",
              }}
            >
              Get Started Free <ArrowRight size={15} />
            </Link>
            <Link
              to="/pricing"
              style={{
                display: "inline-flex", alignItems: "center", gap: 8,
                padding: "15px 30px", borderRadius: 10,
                background: "rgba(255,255,255,0.08)", color: "#fff",
                border: "1.5px solid rgba(255,255,255,0.2)",
                fontSize: "0.9rem", fontWeight: 600, textDecoration: "none",
                letterSpacing: "-0.01em",
              }}
            >
              View Pricing
            </Link>
          </div>
          <p style={{ marginTop: 28, fontSize: "0.78rem", color: "rgba(255,255,255,0.3)" }}>No credit card required · Free plan forever</p>
        </div>
      </Inner>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════════
   PAGE
═══════════════════════════════════════════════════════════════════════════════ */
export default function ResearchLanding() {
  useEffect(() => {
    document.title = "Research Workspace — Synaptiq";
    return () => { document.title = "Synaptiq"; };
  }, []);
  return (
    <MarketingLayout>
      <InjectStyles />
      <HeroSection />
      <TrustedSection />
      <LifecycleSection />
      {FEATURES.map((f) => <FeatureSection key={f.eyebrow} feature={f} />)}
      <AllFeaturesSection />
      <WorkflowSection />
      <TestimonialsSection />
      <CTASection />
    </MarketingLayout>
  );
}
