/* eslint-disable */
import React, { useState, useRef, useEffect } from "react";
import { Link } from "react-router-dom";
import MarketingLayout from "../components/layout/MarketingLayout";
import {
  ArrowRight, BrainCircuit, BookOpen, Search, FlaskConical, BarChart3,
  FileText, Mic, Award, Users, Star, Shield, Lock, Database, Zap,
  CheckCircle2, ChevronRight, Sparkles, Target, MessageSquare, Globe,
  Eye, BookMarked, TrendingUp, GitMerge, Activity,
} from "lucide-react";

/* ─── Shared hooks ───────────────────────────────────────────────────────────── */
function useReveal(threshold = 0.07) {
  const ref = useRef(null);
  useEffect(() => {
    const el = ref.current; if (!el) return;
    if (typeof IntersectionObserver === "undefined") { el.classList.add("ai-in"); return; }
    const obs = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) { el.classList.add("ai-in"); obs.disconnect(); }
    }, { threshold });
    obs.observe(el);
    return () => obs.disconnect();
  }, []);
  return ref;
}

/* ─── Design tokens ──────────────────────────────────────────────────────────── */
const DARK   = "#040f1c";        // hero bg
const DARK2  = "#071828";
const BLUE   = "#3b82f6";        // primary accent (AI blue)
const BLUE2  = "#1d4ed8";
const NAVY   = "#0F2847";
const BORDER = "#E4EBF2";
const SLATE  = "#475569";
const BODY   = "#334155";
const LIGHT  = "#F8FAFB";

/* ─── Global styles ─────────────────────────────────────────────────────────── */
const GLOBAL_CSS = `
  .ai-fade { opacity: 0; transform: translateY(24px); transition: opacity 0.65s ease, transform 0.65s ease; }
  .ai-fade.ai-in { opacity: 1; transform: none; }
  .ai-fade-d1.ai-in { transition-delay: 0.1s; }
  .ai-fade-d2.ai-in { transition-delay: 0.2s; }
  .ai-fade-d3.ai-in { transition-delay: 0.3s; }
  .ai-fade-d4.ai-in { transition-delay: 0.4s; }

  .ai-tool-card { transition: border-color 180ms, background 180ms, box-shadow 180ms; }
  .ai-tool-card:hover { border-color: rgba(59,130,246,0.4) !important; background: rgba(59,130,246,0.06) !important; box-shadow: 0 4px 24px rgba(59,130,246,0.1); }

  .ai-priv-card { transition: border-color 180ms, box-shadow 180ms; }
  .ai-priv-card:hover { border-color: rgba(16,185,129,0.4) !important; box-shadow: 0 6px 24px rgba(16,185,129,0.08); }

  .ai-cta-btn { transition: opacity 160ms, transform 160ms; }
  .ai-cta-btn:hover { opacity: 0.88; transform: translateY(-1px); }

  .ai-quote-card { transition: box-shadow 200ms; }
  .ai-quote-card:hover { box-shadow: 0 12px 40px rgba(0,0,0,0.1); }

  @keyframes ai-stream {
    0%   { opacity: 0; transform: translateX(-6px); }
    100% { opacity: 1; transform: none; }
  }

  @keyframes ai-blink {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0; }
  }

  @keyframes ai-pulse-ring {
    0%   { transform: scale(1); opacity: 0.6; }
    100% { transform: scale(2); opacity: 0; }
  }

  @media (max-width: 900px) {
    .ai-feat-split { flex-direction: column !important; }
    .ai-feat-split-rev { flex-direction: column !important; }
    .ai-tools-grid { grid-template-columns: repeat(2, 1fr) !important; }
    .ai-priv-grid  { grid-template-columns: repeat(2, 1fr) !important; }
    .ai-quotes-grid { grid-template-columns: 1fr !important; }
    .ai-hero-btns { flex-direction: column !important; align-items: stretch !important; }
  }
  @media (max-width: 600px) {
    .ai-tools-grid { grid-template-columns: 1fr !important; }
  }
`;

function InjectStyles() {
  return <style>{GLOBAL_CSS}</style>;
}

function Inner({ children, mw = 1160 }) {
  return (
    <div style={{ maxWidth: mw, margin: "0 auto", padding: "0 32px" }}>{children}</div>
  );
}

function Eyebrow({ children, dark = false }) {
  return (
    <div style={{
      display: "inline-flex", alignItems: "center", gap: 6,
      fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase",
      color: dark ? BLUE : BLUE,
      padding: "5px 12px", borderRadius: 20,
      background: dark ? "rgba(59,130,246,0.12)" : "rgba(59,130,246,0.08)",
      border: `1px solid ${dark ? "rgba(59,130,246,0.3)" : "rgba(59,130,246,0.2)"}`,
      marginBottom: 20,
    }}>
      {children}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════════
   AI ASSISTANT INTERFACE MOCKUP
═══════════════════════════════════════════════════════════════════════════════ */
function AIInterfaceMockup() {
  const [streaming, setStreaming] = useState(false);
  const [tick, setTick] = useState(0);

  const streamedText = "Analyzing 1,247 papers on CRISPR delivery mechanisms across Nature, Cell, and Science (2018–2025).\n\nKey finding: Lipid nanoparticles show 2.4× higher in vivo efficiency than viral vectors in publications post-2022, with significantly reduced immunogenicity profiles (p < 0.001).\n\nI've identified 3 underexplored research gaps that align with your current project…";

  const visible = streaming ? streamedText.slice(0, tick * 4) : "";

  useEffect(() => {
    const t = setInterval(() => {
      setStreaming(true);
      setTick((prev) => {
        if (prev >= streamedText.length / 4) { clearInterval(t); return prev; }
        return prev + 1;
      });
    }, 28);
    return () => clearInterval(t);
  }, []);

  return (
    <div aria-hidden="true" style={{ width: "100%", maxWidth: 660, userSelect: "none" }}>
      {/* Outer chrome */}
      <div style={{
        background: DARK, border: "1px solid rgba(255,255,255,0.07)",
        borderRadius: 16, overflow: "hidden",
        boxShadow: "0 60px 160px rgba(0,0,0,0.55), 0 16px 48px rgba(0,0,0,0.3)",
      }}>
        {/* Window bar */}
        <div style={{ background: "#020b18", borderBottom: "1px solid rgba(255,255,255,0.05)", padding: "9px 16px", display: "flex", alignItems: "center", gap: 8 }}>
          <div style={{ display: "flex", gap: 5 }}>
            {["#ff5f57","#febc2e","#28c840"].map((c) => (
              <div key={c} style={{ width: 9, height: 9, borderRadius: "50%", background: c }} />
            ))}
          </div>
          <div style={{ flex: 1, display: "flex", justifyContent: "center" }}>
            <div style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 5, padding: "2px 36px", fontSize: "0.6rem", color: "rgba(255,255,255,0.22)", fontFamily: "system-ui" }}>
              app.synaptiq.academy/ai
            </div>
          </div>
          <div style={{ padding: "3px 10px", borderRadius: 4, background: "rgba(59,130,246,0.15)", border: "1px solid rgba(59,130,246,0.25)" }}>
            <span style={{ fontSize: "0.52rem", color: "#93c5fd", fontWeight: 700, fontFamily: "system-ui" }}>AI ACTIVE</span>
          </div>
        </div>

        {/* Chat area */}
        <div style={{ display: "flex", height: 440 }}>
          {/* Sidebar — AI Tools */}
          <div style={{ width: 180, background: "#020b18", borderRight: "1px solid rgba(255,255,255,0.05)", padding: "14px 0", overflowY: "auto", scrollbarWidth: "none" }}>
            <div style={{ padding: "0 12px", marginBottom: 12 }}>
              <div style={{ fontSize: "0.55rem", color: "rgba(255,255,255,0.25)", letterSpacing: "0.1em", textTransform: "uppercase", fontFamily: "system-ui" }}>AI Tools</div>
            </div>
            {[
              { label: "AI Assistant",      active: true,  col: BLUE    },
              { label: "Literature Review", active: false, col: "#8b5cf6" },
              { label: "Gap Finder",        active: false, col: "#10b981" },
              { label: "Study Design",      active: false, col: "#f59e0b" },
              { label: "Statistics",        active: false, col: "#ec4899" },
              { label: "Manuscript AI",     active: false, col: "#06b6d4" },
              { label: "Grant Assistant",   active: false, col: "#f97316" },
              { label: "Rewriter",          active: false, col: "#84cc16" },
            ].map((item) => (
              <div
                key={item.label}
                style={{
                  padding: "7px 12px", fontSize: "0.58rem", fontFamily: "system-ui",
                  color: item.active ? "#fff" : "rgba(255,255,255,0.35)",
                  background: item.active ? "rgba(59,130,246,0.12)" : "transparent",
                  borderLeft: item.active ? `2px solid ${BLUE}` : "2px solid transparent",
                  cursor: "pointer",
                }}
              >
                {item.active && (
                  <div style={{ width: 5, height: 5, borderRadius: "50%", background: item.col, display: "inline-block", marginRight: 6 }} />
                )}
                {item.label}
              </div>
            ))}
          </div>

          {/* Chat */}
          <div style={{ flex: 1, display: "flex", flexDirection: "column" }}>
            {/* Messages */}
            <div style={{ flex: 1, padding: 16, overflowY: "auto", scrollbarWidth: "none", display: "flex", flexDirection: "column", gap: 14 }}>
              {/* User message */}
              <div style={{ display: "flex", justifyContent: "flex-end" }}>
                <div style={{ maxWidth: "75%", background: NAVY, borderRadius: "12px 12px 2px 12px", padding: "9px 14px" }}>
                  <span style={{ fontSize: "0.62rem", color: "rgba(255,255,255,0.85)", lineHeight: 1.6, fontFamily: "system-ui" }}>
                    Analyze recent literature on CRISPR delivery mechanisms and identify research gaps in my field.
                  </span>
                </div>
              </div>

              {/* AI response */}
              <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
                <div style={{ width: 24, height: 24, borderRadius: 6, background: "rgba(59,130,246,0.15)", border: "1px solid rgba(59,130,246,0.2)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                  <BrainCircuit size={11} style={{ color: BLUE }} />
                </div>
                <div style={{ flex: 1, background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.07)", borderRadius: "2px 12px 12px 12px", padding: "10px 13px" }}>
                  <div style={{ fontSize: "0.6rem", color: BLUE, fontWeight: 700, fontFamily: "system-ui", marginBottom: 6, letterSpacing: "0.04em" }}>
                    Synaptiq AI · Literature Intelligence
                  </div>
                  <div style={{ fontSize: "0.6rem", color: "rgba(255,255,255,0.7)", lineHeight: 1.7, fontFamily: "system-ui", whiteSpace: "pre-line" }}>
                    {visible}
                    {streaming && tick * 4 < streamedText.length && (
                      <span style={{ display: "inline-block", width: 7, height: 11, background: BLUE, borderRadius: 1, marginLeft: 2, animation: "ai-blink 1s steps(1) infinite", verticalAlign: "text-bottom" }} />
                    )}
                  </div>
                  {tick * 4 >= streamedText.length && (
                    <div style={{ display: "flex", gap: 6, marginTop: 10, flexWrap: "wrap" }}>
                      {["View gap analysis", "Export literature map", "Generate hypotheses"].map((a) => (
                        <div key={a} style={{ padding: "4px 10px", borderRadius: 6, background: "rgba(59,130,246,0.1)", border: "1px solid rgba(59,130,246,0.2)", fontSize: "0.53rem", color: "#93c5fd", fontWeight: 600, fontFamily: "system-ui", cursor: "pointer" }}>
                          {a}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Input bar */}
            <div style={{ padding: "10px 14px", borderTop: "1px solid rgba(255,255,255,0.06)", background: "#020b18" }}>
              <div style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 10, padding: "9px 12px", display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontSize: "0.6rem", color: "rgba(255,255,255,0.2)", flex: 1, fontFamily: "system-ui" }}>Ask Synaptiq AI anything about your research…</span>
                <div style={{ width: 22, height: 22, borderRadius: 6, background: BLUE, display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <ArrowRight size={10} style={{ color: "#fff" }} />
                </div>
              </div>
            </div>
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
    <section style={{ background: DARK, paddingTop: 96, paddingBottom: 0, position: "relative", overflow: "hidden" }}>
      {/* Background glows */}
      <div style={{ position: "absolute", inset: 0, pointerEvents: "none" }}>
        <div style={{ position: "absolute", top: -200, left: "50%", transform: "translateX(-50%)", width: 900, height: 600, background: "radial-gradient(ellipse at center, rgba(59,130,246,0.14) 0%, transparent 65%)", borderRadius: "50%" }} />
        <div style={{ position: "absolute", top: 100, left: "15%", width: 400, height: 400, background: "radial-gradient(ellipse at center, rgba(139,92,246,0.07) 0%, transparent 70%)", borderRadius: "50%" }} />
        <div style={{ position: "absolute", top: 200, right: "10%", width: 300, height: 300, background: "radial-gradient(ellipse at center, rgba(59,130,246,0.05) 0%, transparent 70%)", borderRadius: "50%" }} />
      </div>

      <Inner>
        {/* Top label */}
        <div style={{ textAlign: "center", marginBottom: 28 }}>
          <Eyebrow dark>AI Research Workspace</Eyebrow>
        </div>

        <h1 style={{
          fontFamily: "Georgia, 'Times New Roman', serif",
          fontSize: "clamp(2.4rem, 5vw, 4rem)",
          fontWeight: 700,
          color: "#fff",
          textAlign: "center",
          lineHeight: 1.1,
          letterSpacing: "-0.03em",
          margin: "0 auto 20px",
          maxWidth: 820,
        }}>
          The AI workspace built<br />for modern research.
        </h1>

        <p style={{
          textAlign: "center", fontSize: "1.1rem", color: "rgba(255,255,255,0.52)",
          lineHeight: 1.75, maxWidth: 540, margin: "0 auto 40px",
        }}>
          Every research task. One intelligent workspace. From literature review to grant writing — trained for academia.
        </p>

        {/* Stat pills */}
        <div style={{ display: "flex", justifyContent: "center", gap: 10, marginBottom: 36, flexWrap: "wrap" }}>
          {[
            { v: "11", l: "AI tools built for research" },
            { v: "100M+", l: "papers indexed" },
            { v: "Zero", l: "AI data retention" },
          ].map((s) => (
            <div key={s.l} style={{ display: "flex", alignItems: "center", gap: 7, padding: "7px 14px", borderRadius: 20, background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.09)" }}>
              <span style={{ fontSize: "0.78rem", fontWeight: 700, color: "#fff" }}>{s.v}</span>
              <span style={{ fontSize: "0.68rem", color: "rgba(255,255,255,0.35)" }}>{s.l}</span>
            </div>
          ))}
        </div>

        {/* CTAs */}
        <div className="ai-hero-btns" style={{ display: "flex", justifyContent: "center", gap: 12, marginBottom: 64 }}>
          <Link
            to="/register"
            className="ai-cta-btn"
            style={{
              display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 8,
              padding: "14px 28px", borderRadius: 10,
              background: BLUE, color: "#fff",
              fontSize: "0.9rem", fontWeight: 600, textDecoration: "none",
              letterSpacing: "-0.01em",
              boxShadow: "0 4px 24px rgba(59,130,246,0.4)",
            }}
          >
            Start with AI <ArrowRight size={15} />
          </Link>
          <Link
            to="/pricing"
            style={{
              display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 8,
              padding: "14px 28px", borderRadius: 10,
              background: "rgba(255,255,255,0.06)", color: "#fff",
              border: "1.5px solid rgba(255,255,255,0.14)",
              fontSize: "0.9rem", fontWeight: 600, textDecoration: "none",
              letterSpacing: "-0.01em",
            }}
          >
            See Pricing
          </Link>
        </div>

        {/* Product mockup */}
        <div style={{ display: "flex", justifyContent: "center", paddingBottom: 0 }}>
          <div style={{ width: "100%", maxWidth: 880, position: "relative" }}>
            <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: 120, background: `linear-gradient(to bottom, transparent 0%, ${DARK} 100%)`, zIndex: 2, pointerEvents: "none" }} />
            <AIInterfaceMockup />
          </div>
        </div>
      </Inner>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════════
   AI TOOLS GRID
═══════════════════════════════════════════════════════════════════════════════ */
const AI_TOOLS = [
  { icon: BrainCircuit, title: "AI Assistant",           desc: "Context-aware research co-pilot that understands your field, your papers, and your goals.", color: BLUE,      bg: "rgba(59,130,246,0.1)"  },
  { icon: BookOpen,     title: "Literature Review",      desc: "Synthesize 100M+ papers in seconds. Identify trends, conflicts, and consensus across your field.", color: "#8b5cf6", bg: "rgba(139,92,246,0.1)" },
  { icon: Search,       title: "Research Gap Finder",    desc: "Detect what no one has studied yet. Surface unexplored questions with commercial and scientific significance.", color: "#10b981", bg: "rgba(16,185,129,0.1)" },
  { icon: FlaskConical, title: "Study Design Advisor",   desc: "Get methodology recommendations tailored to your research question, sample size, and field norms.", color: "#f59e0b", bg: "rgba(245,158,11,0.1)"  },
  { icon: BarChart3,    title: "Statistical Analysis",   desc: "Describe your data and let AI recommend the right statistical approach, detect errors, and explain results.", color: "#ec4899", bg: "rgba(236,72,153,0.1)" },
  { icon: FileText,     title: "Academic Rewriter",      desc: "Polish prose, adjust register, and match the writing conventions of your target journal.", color: "#06b6d4", bg: "rgba(6,182,212,0.1)"  },
  { icon: BookMarked,   title: "Manuscript Review",      desc: "Get instant peer-reviewer-level feedback on structure, argument, and methodological rigor before submission.", color: "#f97316", bg: "rgba(249,115,22,0.1)" },
  { icon: Award,        title: "Grant Assistant",        desc: "Write winning applications with AI trained on successful grants across NSF, NIH, ERC, and Wellcome Trust.", color: "#84cc16", bg: "rgba(132,204,22,0.1)" },
  { icon: MessageSquare,title: "Conference Assistant",   desc: "Identify the best conferences for your research, draft abstracts, and prepare presentation materials.", color: "#6366f1", bg: "rgba(99,102,241,0.1)" },
  { icon: Users,        title: "Reviewer Assistant",     desc: "Write structured, thorough peer reviews faster. Maintain a consistent standard across all journals.", color: "#14b8a6", bg: "rgba(20,184,166,0.1)" },
  { icon: TrendingUp,   title: "Citation Intelligence",  desc: "Understand how your citations build your field reputation and optimize your publication strategy.", color: "#a855f7", bg: "rgba(168,85,247,0.1)" },
];

function AIToolsSection() {
  const ref = useReveal();
  return (
    <section style={{ background: "#fff", padding: "100px 0" }}>
      <Inner>
        <div ref={ref} className="ai-fade" style={{ textAlign: "center", marginBottom: 60 }}>
          <Eyebrow>11 AI research tools</Eyebrow>
          <h2 style={{ fontFamily: "Georgia, serif", fontSize: "clamp(1.8rem, 3vw, 2.6rem)", fontWeight: 700, color: "#0c1a2e", lineHeight: 1.2, letterSpacing: "-0.02em", margin: "0 0 16px" }}>
            One workspace.<br />Every research task.
          </h2>
          <p style={{ fontSize: "1rem", color: SLATE, maxWidth: 500, margin: "0 auto" }}>
            Every AI tool is trained on academic literature and research workflows — not generic internet content.
          </p>
        </div>

        <div className="ai-tools-grid" style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16 }}>
          {AI_TOOLS.map((t, i) => (
            <div
              key={t.title}
              className={`ai-fade ai-fade-d${Math.min(i % 3 + 1, 4)} ai-tool-card`}
              style={{ background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 12, padding: "22px 22px" }}
            >
              <div style={{ width: 40, height: 40, borderRadius: 10, background: t.bg, display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 14 }}>
                <t.icon size={18} strokeWidth={1.4} style={{ color: t.color }} />
              </div>
              <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "#0f172a", marginBottom: 6 }}>{t.title}</div>
              <div style={{ fontSize: "0.78rem", color: SLATE, lineHeight: 1.65 }}>{t.desc}</div>
            </div>
          ))}
        </div>
      </Inner>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════════
   SHOWCASE SECTIONS (alternating)
═══════════════════════════════════════════════════════════════════════════════ */
function LiteratureMockup() {
  return (
    <div aria-hidden="true" style={{ width: "100%", maxWidth: 520 }}>
      <div style={{ background: DARK, border: "1px solid rgba(255,255,255,0.07)", borderRadius: 12, overflow: "hidden", boxShadow: "0 24px 80px rgba(0,0,0,0.38)" }}>
        <div style={{ background: "#020b18", borderBottom: "1px solid rgba(255,255,255,0.05)", padding: "8px 14px", display: "flex", gap: 4 }}>
          {["#ff5f57","#febc2e","#28c840"].map((c) => <div key={c} style={{ width: 8, height: 8, borderRadius: "50%", background: c }} />)}
          <span style={{ fontSize: "0.56rem", color: "rgba(255,255,255,0.18)", marginLeft: 8, fontFamily: "system-ui" }}>Literature Review · CRISPR Research</span>
        </div>
        <div style={{ padding: 16 }}>
          <div style={{ display: "flex", gap: 8, marginBottom: 14 }}>
            {[{ v: "1,247", l: "Papers" }, { v: "847", l: "Relevant" }, { v: "12", l: "Must-reads" }].map((s) => (
              <div key={s.l} style={{ flex: 1, background: "rgba(255,255,255,0.04)", borderRadius: 7, padding: "8px", textAlign: "center", border: "1px solid rgba(255,255,255,0.06)" }}>
                <div style={{ fontSize: "0.9rem", fontWeight: 700, color: "#93c5fd", fontFamily: "system-ui" }}>{s.v}</div>
                <div style={{ fontSize: "0.52rem", color: "rgba(255,255,255,0.3)", fontFamily: "system-ui" }}>{s.l}</div>
              </div>
            ))}
          </div>
          {[
            { title: "Lipid nanoparticle-mediated CRISPR delivery: 2025 review", year: "2025", score: 98, col: "#10b981" },
            { title: "Off-target effects in somatic gene editing at scale",          year: "2024", score: 94, col: "#3b82f6" },
            { title: "Comparative viral vs non-viral delivery: meta-analysis",       year: "2024", score: 89, col: "#8b5cf6" },
            { title: "CRISPR-Cas9 therapeutic window in mammalian models",           year: "2023", score: 85, col: "#f59e0b" },
          ].map((p) => (
            <div key={p.title} style={{ background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 8, padding: "9px 11px", marginBottom: 7, display: "flex", gap: 10, alignItems: "center" }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: "0.58rem", fontWeight: 600, color: "rgba(255,255,255,0.75)", lineHeight: 1.4, fontFamily: "system-ui" }}>{p.title}</div>
                <div style={{ fontSize: "0.52rem", color: "rgba(255,255,255,0.25)", fontFamily: "system-ui", marginTop: 3 }}>{p.year}</div>
              </div>
              <div style={{ width: 36, height: 36, borderRadius: "50%", background: p.col + "18", border: `1px solid ${p.col}30`, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                <span style={{ fontSize: "0.58rem", fontWeight: 700, color: p.col, fontFamily: "system-ui" }}>{p.score}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function GrantMockup() {
  return (
    <div aria-hidden="true" style={{ width: "100%", maxWidth: 520 }}>
      <div style={{ background: DARK, border: "1px solid rgba(255,255,255,0.07)", borderRadius: 12, overflow: "hidden", boxShadow: "0 24px 80px rgba(0,0,0,0.38)" }}>
        <div style={{ background: "#020b18", borderBottom: "1px solid rgba(255,255,255,0.05)", padding: "8px 14px", display: "flex", gap: 4 }}>
          {["#ff5f57","#febc2e","#28c840"].map((c) => <div key={c} style={{ width: 8, height: 8, borderRadius: "50%", background: c }} />)}
          <span style={{ fontSize: "0.56rem", color: "rgba(255,255,255,0.18)", marginLeft: 8, fontFamily: "system-ui" }}>Grant Assistant · NIH R01 Draft</span>
        </div>
        <div style={{ padding: 16 }}>
          <div style={{ fontSize: "0.58rem", color: "rgba(255,255,255,0.25)", letterSpacing: "0.08em", marginBottom: 10, fontFamily: "system-ui" }}>APPLICATION SECTIONS</div>
          {[
            { label: "Specific Aims",       status: "Complete",  pct: 100, col: "#10b981" },
            { label: "Research Strategy",   status: "In Review",  pct: 78,  col: "#3b82f6" },
            { label: "Significance",        status: "Complete",  pct: 100, col: "#10b981" },
            { label: "Innovation",          status: "Drafting",  pct: 55,  col: "#f59e0b" },
            { label: "Approach",            status: "Drafting",  pct: 42,  col: "#f59e0b" },
            { label: "Budget Justification",status: "Pending",   pct: 0,   col: "#475569" },
          ].map((s) => (
            <div key={s.label} style={{ marginBottom: 9 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                <span style={{ fontSize: "0.58rem", color: "rgba(255,255,255,0.6)", fontFamily: "system-ui" }}>{s.label}</span>
                <span style={{ fontSize: "0.52rem", color: s.col, fontWeight: 600, fontFamily: "system-ui" }}>{s.status}</span>
              </div>
              <div style={{ height: 3, background: "rgba(255,255,255,0.06)", borderRadius: 2 }}>
                <div style={{ width: `${s.pct}%`, height: 3, background: s.col, borderRadius: 2 }} />
              </div>
            </div>
          ))}
          <div style={{ marginTop: 14, padding: "10px 12px", background: "rgba(59,130,246,0.08)", border: "1px solid rgba(59,130,246,0.2)", borderRadius: 8 }}>
            <div style={{ fontSize: "0.58rem", fontWeight: 700, color: "#93c5fd", marginBottom: 5, fontFamily: "system-ui" }}>AI REVIEW</div>
            <div style={{ fontSize: "0.56rem", color: "rgba(255,255,255,0.5)", lineHeight: 1.5, fontFamily: "system-ui" }}>Specific Aims aligns well with PA-24-185. Strengthen the innovation section by citing 3 more recent gaps.</div>
          </div>
        </div>
      </div>
    </div>
  );
}

const SHOWCASES = [
  {
    eyebrow: "Literature Review AI",
    title: "Synthesize 100 million papers in the time it takes to read one.",
    body: "Synaptiq scans every major academic database — PubMed, Scopus, Web of Science, arXiv, and more — and returns a curated, ranked, and synthesized literature map specific to your research question. Gaps, conflicts, and consensus surfaces automatically.",
    points: ["Ranked by relevance to your project", "Conflict and consensus detection", "Auto-generated synthesis summaries"],
    mockup: "literature",
    reverse: false,
    bg: "#fff",
  },
  {
    eyebrow: "Grant Writing AI",
    title: "Win more grants with AI trained on successful applications.",
    body: "Synaptiq's Grant Assistant knows the structure, language, and evaluation criteria of every major funding body — NIH, NSF, ERC, Wellcome Trust, and 40+ more. Draft, review, and refine your application section by section.",
    points: ["Trained on successful grant applications", "Section-by-section AI review", "Budget and timeline AI assistance"],
    mockup: "grant",
    reverse: true,
    bg: LIGHT,
  },
];

function ShowcaseSection({ s }) {
  const ref = useReveal();
  return (
    <section style={{ background: s.bg, padding: "96px 0" }}>
      <Inner>
        <div
          ref={ref}
          className={`ai-fade ai-feat-split${s.reverse ? "-rev" : ""}`}
          style={{ display: "flex", flexDirection: s.reverse ? "row-reverse" : "row", alignItems: "center", gap: 72 }}
        >
          {/* Text */}
          <div style={{ flex: 1, minWidth: 280 }}>
            <Eyebrow>{s.eyebrow}</Eyebrow>
            <h2 style={{ fontFamily: "Georgia, serif", fontSize: "clamp(1.7rem, 3vw, 2.3rem)", fontWeight: 700, color: "#0c1a2e", lineHeight: 1.18, letterSpacing: "-0.02em", margin: "0 0 18px" }}>
              {s.title}
            </h2>
            <p style={{ fontSize: "0.975rem", color: SLATE, lineHeight: 1.75, marginBottom: 28 }}>{s.body}</p>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {s.points.map((p) => (
                <div key={p} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <CheckCircle2 size={16} strokeWidth={2} style={{ color: BLUE, flexShrink: 0 }} />
                  <span style={{ fontSize: "0.875rem", color: BODY, fontWeight: 500 }}>{p}</span>
                </div>
              ))}
            </div>
            <Link
              to="/register"
              style={{ display: "inline-flex", alignItems: "center", gap: 6, marginTop: 28, fontSize: "0.875rem", fontWeight: 600, color: NAVY, textDecoration: "none" }}
            >
              Try it free <ArrowRight size={14} />
            </Link>
          </div>

          {/* Mockup */}
          <div style={{ flex: 1, display: "flex", justifyContent: "center" }}>
            {s.mockup === "literature" && <LiteratureMockup />}
            {s.mockup === "grant"      && <GrantMockup />}
          </div>
        </div>
      </Inner>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════════
   PRIVACY & TRUST
═══════════════════════════════════════════════════════════════════════════════ */
const PRIVACY_POINTS = [
  {
    icon: Lock,
    title: "Private AI",
    desc: "Your research data never leaves your account. AI processing runs in isolated, encrypted environments.",
    color: "#10b981",
  },
  {
    icon: Shield,
    title: "Academic integrity",
    desc: "Built-in citation tracking and attribution so every AI-assisted output is fully traceable.",
    color: "#3b82f6",
  },
  {
    icon: Eye,
    title: "No model training",
    desc: "Your papers, notes, and conversations are never used to train or improve AI models.",
    color: "#8b5cf6",
  },
  {
    icon: Database,
    title: "Encrypted data",
    desc: "All data is encrypted at rest (AES-256) and in transit (TLS 1.3) with per-user key isolation.",
    color: "#f59e0b",
  },
];

function PrivacySection() {
  const ref = useReveal();
  return (
    <section style={{ background: "#0c1a2e", padding: "100px 0" }}>
      <Inner>
        <div ref={ref} className="ai-fade" style={{ textAlign: "center", marginBottom: 56 }}>
          <div style={{ fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "rgba(16,185,129,0.7)", marginBottom: 16 }}>
            Privacy by design
          </div>
          <h2 style={{ fontFamily: "Georgia, serif", fontSize: "clamp(1.8rem, 3vw, 2.6rem)", fontWeight: 700, color: "#fff", lineHeight: 1.2, letterSpacing: "-0.02em", margin: "0 0 16px" }}>
            Your research. Your data. Always.
          </h2>
          <p style={{ fontSize: "1rem", color: "rgba(255,255,255,0.45)", maxWidth: 480, margin: "0 auto" }}>
            We built Synaptiq AI specifically for academic contexts, where data integrity and intellectual property are non-negotiable.
          </p>
        </div>

        <div className="ai-priv-grid" style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
          {PRIVACY_POINTS.map((p, i) => (
            <div
              key={p.title}
              className={`ai-fade ai-fade-d${i + 1} ai-priv-card`}
              style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 12, padding: "26px 22px" }}
            >
              <div style={{ width: 44, height: 44, borderRadius: 12, background: p.color + "18", display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 16 }}>
                <p.icon size={20} strokeWidth={1.4} style={{ color: p.color }} />
              </div>
              <div style={{ fontSize: "0.9rem", fontWeight: 700, color: "#fff", marginBottom: 8 }}>{p.title}</div>
              <div style={{ fontSize: "0.78rem", color: "rgba(255,255,255,0.42)", lineHeight: 1.65 }}>{p.desc}</div>
            </div>
          ))}
        </div>

        {/* Compliance badges */}
        <div style={{ display: "flex", justifyContent: "center", gap: 16, flexWrap: "wrap", marginTop: 48 }}>
          {["GDPR Compliant", "SOC 2 Type II", "HIPAA Ready", "ISO 27001"].map((b) => (
            <div key={b} style={{ display: "flex", alignItems: "center", gap: 6, padding: "8px 16px", borderRadius: 20, background: "rgba(255,255,255,0.05)", border: "1px solid rgba(255,255,255,0.1)" }}>
              <CheckCircle2 size={12} strokeWidth={2} style={{ color: "#10b981" }} />
              <span style={{ fontSize: "0.72rem", fontWeight: 600, color: "rgba(255,255,255,0.55)" }}>{b}</span>
            </div>
          ))}
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
    quote: "The Literature Review AI saved me six weeks on my last project. It surfaced three papers I'd never have found on my own — two of them became key references in my submission.",
    name: "Dr. Amara Diallo",
    title: "Research Fellow, Computational Biology",
    institution: "Karolinska Institute",
    stars: 5,
  },
  {
    quote: "I used the Grant Assistant for an NIH R01 application. The feedback on my Specific Aims section was more actionable than anything I received from my department review committee.",
    name: "Prof. Thomas Eriksen",
    title: "Chair, Department of Neuroscience",
    institution: "University of Copenhagen",
    stars: 5,
  },
  {
    quote: "The Statistical Analysis tool caught a methodological error that would have come back in peer review. It paid for itself on day one.",
    name: "Dr. Yuki Yamamoto",
    title: "Assistant Professor, Medical Statistics",
    institution: "University of Tokyo",
    stars: 5,
  },
];

function TestimonialsSection() {
  const ref = useReveal();
  return (
    <section style={{ background: "#fff", padding: "100px 0" }}>
      <Inner>
        <div ref={ref} className="ai-fade" style={{ textAlign: "center", marginBottom: 52 }}>
          <Eyebrow>Researcher stories</Eyebrow>
          <h2 style={{ fontFamily: "Georgia, serif", fontSize: "clamp(1.8rem, 3vw, 2.4rem)", fontWeight: 700, color: "#0c1a2e", letterSpacing: "-0.02em", margin: 0 }}>
            What researchers say.
          </h2>
        </div>

        <div className="ai-quotes-grid" style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 20 }}>
          {TESTIMONIALS.map((t, i) => (
            <div
              key={t.name}
              className={`ai-fade ai-fade-d${i + 1} ai-quote-card`}
              style={{ background: "#fff", border: `1px solid ${BORDER}`, borderRadius: 14, padding: "28px 28px" }}
            >
              <div style={{ display: "flex", gap: 3, marginBottom: 16 }}>
                {Array(t.stars).fill(0).map((_, j) => (
                  <Star key={j} size={13} fill="#f59e0b" style={{ color: "#f59e0b" }} />
                ))}
              </div>
              <p style={{ fontSize: "0.875rem", color: BODY, lineHeight: 1.75, marginBottom: 24, fontStyle: "italic" }}>
                "{t.quote}"
              </p>
              <div style={{ display: "flex", alignItems: "center", gap: 12, paddingTop: 20, borderTop: `1px solid ${BORDER}` }}>
                <div style={{ width: 38, height: 38, borderRadius: "50%", background: BLUE + "18", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                  <span style={{ fontSize: "0.72rem", fontWeight: 700, color: BLUE }}>{t.name.split(" ").map((w) => w[0]).slice(0, 2).join("")}</span>
                </div>
                <div>
                  <div style={{ fontSize: "0.78rem", fontWeight: 700, color: "#0f172a" }}>{t.name}</div>
                  <div style={{ fontSize: "0.68rem", color: "#94a3b8" }}>{t.title}</div>
                  <div style={{ fontSize: "0.65rem", color: BLUE, fontWeight: 600 }}>{t.institution}</div>
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
    <section style={{ background: DARK, padding: "120px 0", position: "relative", overflow: "hidden" }}>
      <div style={{ position: "absolute", inset: 0, background: "radial-gradient(ellipse 800px 400px at 50% 50%, rgba(59,130,246,0.1) 0%, transparent 70%)", pointerEvents: "none" }} />
      <Inner>
        <div ref={ref} className="ai-fade" style={{ textAlign: "center" }}>
          <div style={{ fontSize: "0.68rem", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", color: "rgba(59,130,246,0.6)", marginBottom: 20 }}>Start today</div>
          <h2 style={{ fontFamily: "Georgia, serif", fontSize: "clamp(2rem, 4vw, 3.2rem)", fontWeight: 700, color: "#fff", lineHeight: 1.12, letterSpacing: "-0.025em", margin: "0 0 20px", maxWidth: 620, marginLeft: "auto", marginRight: "auto" }}>
            Experience the future of academic AI.
          </h2>
          <p style={{ fontSize: "1.05rem", color: "rgba(255,255,255,0.45)", maxWidth: 440, margin: "0 auto 40px", lineHeight: 1.7 }}>
            The most advanced AI research tools ever built for academia. Now available to every researcher.
          </p>
          <div style={{ display: "flex", justifyContent: "center", gap: 12, flexWrap: "wrap" }}>
            <Link
              to="/register"
              className="ai-cta-btn"
              style={{
                display: "inline-flex", alignItems: "center", gap: 8,
                padding: "15px 30px", borderRadius: 10,
                background: BLUE, color: "#fff",
                fontSize: "0.9rem", fontWeight: 700, textDecoration: "none",
                letterSpacing: "-0.01em",
                boxShadow: "0 6px 30px rgba(59,130,246,0.45)",
              }}
            >
              Start with AI Free <ArrowRight size={15} />
            </Link>
            <Link
              to="/pricing"
              style={{
                display: "inline-flex", alignItems: "center", gap: 8,
                padding: "15px 30px", borderRadius: 10,
                background: "rgba(255,255,255,0.06)", color: "#fff",
                border: "1.5px solid rgba(255,255,255,0.16)",
                fontSize: "0.9rem", fontWeight: 600, textDecoration: "none",
                letterSpacing: "-0.01em",
              }}
            >
              View Pricing
            </Link>
          </div>
          <p style={{ marginTop: 28, fontSize: "0.78rem", color: "rgba(255,255,255,0.24)" }}>No credit card required · Free plan forever</p>
        </div>
      </Inner>
    </section>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════════
   PAGE
═══════════════════════════════════════════════════════════════════════════════ */
export default function AIWorkspaceLanding() {
  useEffect(() => {
    document.title = "AI Workspace — Synaptiq";
    return () => { document.title = "Synaptiq"; };
  }, []);
  return (
    <MarketingLayout>
      <InjectStyles />
      <HeroSection />
      <AIToolsSection />
      {SHOWCASES.map((s) => <ShowcaseSection key={s.eyebrow} s={s} />)}
      <PrivacySection />
      <TestimonialsSection />
      <CTASection />
    </MarketingLayout>
  );
}
